"""
Paint Formulation AI - Feature Engineer
========================================
Enhanced feature engineering for paint formulation ML models.

Calculates domain-specific mixture properties:
- PVC (Pigment Volume Concentration)
- CPVC (Critical PVC) estimation
- Lambda ratio (PVC/CPVC)
- Solid content percentages
- Weighted average properties (density, Tg, etc.)
- VOC content estimation
"""

import numpy as np
from typing import Dict, List, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Enhanced feature engineering for paint formulation prediction.
    
    Calculates mixture properties based on paint chemistry principles,
    focusing on key parameters that affect final coating properties.
    """
    
    # Feature names for the engineered features
    MIXTURE_FEATURE_NAMES = [
        # Volume-based metrics
        'pvc',                      # Pigment Volume Concentration
        'cpvc_estimated',           # Critical PVC (estimated)
        'lambda_ratio',             # PVC / CPVC
        
        # Mass-based metrics
        'solid_content_weight',     # Weight % solids
        'solid_content_volume',     # Volume % solids (estimated)
        'binder_pigment_ratio',     # B/P ratio by mass
        'pigment_binder_ratio',     # P/B ratio by mass
        
        # Weighted average properties
        'weighted_avg_density',     # Mixture density
        'weighted_avg_tg',          # Glass transition temperature
        'weighted_avg_oh_value',    # OH value (for polyurethanes)
        
        # Solvent properties
        'voc_content',              # VOC g/L estimate
        'solvent_ratio',            # Total solvent %
        'avg_evaporation_rate',     # Evaporation rate
        
        # Category ratios
        'binder_ratio',             # Binder %
        'pigment_ratio',            # Pigment + Filler %
        'additive_ratio',           # Additive %
        
        # Cost
        'theoretical_cost',         # Cost per kg
    ]
    
    # Default material properties (used when data is missing)
    DEFAULT_PROPERTIES = {
        'density': 1.0,            # g/cm³
        'solid_content': 100,      # %
        'oil_absorption': 20,      # g/100g
        'glass_transition': 25,    # °C
        'oh_value': 0,             # mg KOH/g
        'voc_g_l': 0,              # g/L
        'evaporation_rate': 1.0,   # BuAc = 1
        'unit_price': 10,          # TL/kg
    }
    
    # Category mappings
    CATEGORY_GROUPS = {
        'binder': ['binder', 'resin', 'polymer', 'alkyd', 'acrylic', 'epoxy', 'polyurethane'],
        'pigment': ['pigment', 'filler', 'extender', 'titanium', 'iron oxide', 'carbon'],
        'solvent': ['solvent', 'thinner', 'water', 'coalescent'],
        'additive': ['additive', 'defoamer', 'thickener', 'dispersant', 'drier', 'biocide', 
                     'rheology', 'leveling', 'wetting']
    }
    
    def __init__(self, material_lookup: Callable = None):
        """
        Initialize the feature engineer.
        
        Args:
            material_lookup: Optional callback to fetch material properties from database.
                            Signature: material_lookup(code: str) -> Dict
        """
        self.material_lookup = material_lookup
        self.feature_count = len(self.MIXTURE_FEATURE_NAMES)
    
    def engineer_features(self, formulation: Dict) -> np.ndarray:
        """
        Engineer features from a formulation dictionary.
        
        Args:
            formulation: Dictionary containing:
                - 'components': List of ingredient dictionaries
                - Optional: 'coating_thickness', 'target_viscosity', etc.
                
        Returns:
            numpy array of engineered features
        """
        components = formulation.get('components', [])
        
        if not components:
            return np.zeros(self.feature_count)
        
        # Enrich component data if we have material lookup
        enriched_components = self._enrich_components(components)
        
        # Calculate all mixture properties
        features = self._calculate_mixture_properties(enriched_components)
        
        return np.array([features.get(name, 0.0) for name in self.MIXTURE_FEATURE_NAMES])
    
    def get_feature_names(self) -> List[str]:
        """Return the list of feature names."""
        return self.MIXTURE_FEATURE_NAMES.copy()
    
    def _enrich_components(self, components: List[Dict]) -> List[Dict]:
        """
        Enrich component data with properties from database if available.
        """
        enriched = []
        
        for comp in components:
            enriched_comp = comp.copy()
            
            # Try to lookup additional properties if we have the function
            if self.material_lookup and 'code' in comp:
                try:
                    material_data = self.material_lookup(comp['code'])
                    if material_data:
                        # Merge database properties (don't overwrite existing)
                        for key, value in material_data.items():
                            if key not in enriched_comp or enriched_comp[key] is None:
                                enriched_comp[key] = value
                except Exception as e:
                    logger.debug(f"Could not lookup material {comp.get('code')}: {e}")
            
            # Apply defaults for missing properties
            for prop, default in self.DEFAULT_PROPERTIES.items():
                if prop not in enriched_comp or enriched_comp[prop] is None:
                    enriched_comp[prop] = default
            
            enriched.append(enriched_comp)
        
        return enriched
    
    def _get_category_group(self, category: str) -> str:
        """Map a material category to its group (binder, pigment, solvent, additive)."""
        if not category:
            return 'additive'
        
        category_lower = category.lower()
        
        for group, keywords in self.CATEGORY_GROUPS.items():
            for keyword in keywords:
                if keyword in category_lower:
                    return group
        
        return 'additive'  # Default
    
    def _calculate_mixture_properties(self, components: List[Dict]) -> Dict[str, float]:
        """
        Calculate mixture properties from component list.
        
        Based on paint chemistry principles:
        - PVC = Vp / (Vp + Vb) where V = mass / density
        - CPVC ≈ 1 / (1 + OA × density / 93.5) (Stieg equation approximation)
        """
        features = {name: 0.0 for name in self.MIXTURE_FEATURE_NAMES}
        
        # Calculate total amount
        total_amount = sum(self._get_amount(c) for c in components)
        if total_amount <= 0:
            return features
        
        # Category accumulators
        category_amounts = {'binder': 0.0, 'pigment': 0.0, 'solvent': 0.0, 'additive': 0.0}
        category_volumes = {'binder': 0.0, 'pigment': 0.0, 'solvent': 0.0, 'additive': 0.0}
        
        # Weighted property accumulators
        total_solid_mass = 0.0
        total_volume = 0.0
        
        weighted_density = 0.0
        weighted_tg = 0.0
        weighted_oh = 0.0
        weighted_evap = 0.0
        
        total_voc = 0.0
        total_cost = 0.0
        
        # Pigment-specific for CPVC calculation
        pigment_oa_sum = 0.0  # Oil absorption weighted sum
        pigment_mass = 0.0
        
        # Binder totals for Tg calculation
        binder_mass = 0.0
        
        for comp in components:
            amount = self._get_amount(comp)
            if amount <= 0:
                continue
            
            ratio = amount / total_amount
            
            # Material properties
            density = float(comp.get('density') or self.DEFAULT_PROPERTIES['density'])
            solid_content = float(comp.get('solid_content') or self.DEFAULT_PROPERTIES['solid_content']) / 100
            oil_absorption = float(comp.get('oil_absorption') or self.DEFAULT_PROPERTIES['oil_absorption'])
            tg = float(comp.get('glass_transition') or self.DEFAULT_PROPERTIES['glass_transition'])
            oh_value = float(comp.get('oh_value') or self.DEFAULT_PROPERTIES['oh_value'])
            voc = float(comp.get('voc_g_l') or self.DEFAULT_PROPERTIES['voc_g_l'])
            evap_rate = float(comp.get('evaporation_rate') or self.DEFAULT_PROPERTIES['evaporation_rate'])
            price = float(comp.get('unit_price') or self.DEFAULT_PROPERTIES['unit_price'])
            
            # Determine category group
            category = comp.get('category') or comp.get('material_category') or comp.get('type') or ''
            group = self._get_category_group(category)
            
            # Calculate volume (mass / density)
            volume = amount / density if density > 0 else amount
            
            # Accumulate by category
            category_amounts[group] += amount
            category_volumes[group] += volume * solid_content  # Solid volume only
            
            # Accumulate total solid mass
            total_solid_mass += amount * solid_content
            total_volume += volume
            
            # Weighted properties
            weighted_density += density * ratio
            
            if group == 'binder':
                binder_mass += amount
                weighted_tg += tg * amount
                weighted_oh += oh_value * amount
            
            if group == 'pigment':
                pigment_mass += amount
                pigment_oa_sum += oil_absorption * amount
            
            if group == 'solvent':
                weighted_evap += evap_rate * amount
                total_voc += voc * volume / 1000  # Convert to kg
            
            total_cost += price * ratio
        
        # Calculate final features
        
        # Category ratios
        features['binder_ratio'] = category_amounts['binder'] / total_amount
        features['pigment_ratio'] = category_amounts['pigment'] / total_amount
        features['solvent_ratio'] = category_amounts['solvent'] / total_amount
        features['additive_ratio'] = category_amounts['additive'] / total_amount
        
        # P/B and B/P ratios
        if category_amounts['pigment'] > 0:
            features['binder_pigment_ratio'] = category_amounts['binder'] / category_amounts['pigment']
        if category_amounts['binder'] > 0:
            features['pigment_binder_ratio'] = category_amounts['pigment'] / category_amounts['binder']
        
        # Solid content
        features['solid_content_weight'] = (total_solid_mass / total_amount) * 100 if total_amount > 0 else 0
        
        # PVC calculation
        # PVC = Volume of pigment / (Volume of pigment + Volume of binder)
        v_pigment = category_volumes['pigment']
        v_binder = category_volumes['binder']
        
        if v_pigment + v_binder > 0:
            features['pvc'] = (v_pigment / (v_pigment + v_binder)) * 100
        
        # CPVC estimation using Stieg equation approximation
        # CPVC ≈ 1 / (1 + OA × ρ_pigment / 93.5)
        if pigment_mass > 0:
            avg_oa = pigment_oa_sum / pigment_mass
            # Assume average pigment density ~2.5 g/cm³
            avg_pigment_density = 2.5
            cpvc = 100 / (1 + avg_oa * avg_pigment_density / 93.5)
            features['cpvc_estimated'] = cpvc
            
            # Lambda ratio
            if cpvc > 0:
                features['lambda_ratio'] = features['pvc'] / cpvc
        
        # Volume % solids estimation
        solid_volume = category_volumes['binder'] + category_volumes['pigment'] + category_volumes['additive']
        if total_volume > 0:
            features['solid_content_volume'] = (solid_volume / total_volume) * 100
        
        # Weighted averages
        features['weighted_avg_density'] = weighted_density
        
        if binder_mass > 0:
            features['weighted_avg_tg'] = weighted_tg / binder_mass
            features['weighted_avg_oh_value'] = weighted_oh / binder_mass
        
        if category_amounts['solvent'] > 0:
            features['avg_evaporation_rate'] = weighted_evap / category_amounts['solvent']
        
        # VOC content (g/L of wet paint)
        if total_volume > 0:
            features['voc_content'] = (total_voc / total_volume) * 1000  # g/L
        
        # Cost
        features['theoretical_cost'] = total_cost
        
        return features
    
    def _get_amount(self, component: Dict) -> float:
        """Get the amount from a component dictionary."""
        amount = component.get('amount') or component.get('percentage') or 0
        try:
            return float(amount)
        except (ValueError, TypeError):
            return 0.0
    
    def transform_batch(self, formulations: List[Dict]) -> np.ndarray:
        """
        Transform a batch of formulations to feature arrays.
        
        Args:
            formulations: List of formulation dictionaries
            
        Returns:
            2D numpy array of shape (n_formulations, n_features)
        """
        return np.array([self.engineer_features(f) for f in formulations])
    
    def get_feature_descriptions(self) -> Dict[str, str]:
        """Return descriptions for each feature."""
        return {
            'pvc': 'Pigment Volume Concentration (%)',
            'cpvc_estimated': 'Critical PVC estimated from oil absorption (%)',
            'lambda_ratio': 'PVC/CPVC ratio (>1 means above CPVC)',
            'solid_content_weight': 'Non-volatile content by weight (%)',
            'solid_content_volume': 'Non-volatile content by volume (%)',
            'binder_pigment_ratio': 'Binder to Pigment mass ratio',
            'pigment_binder_ratio': 'Pigment to Binder mass ratio (P/B)',
            'weighted_avg_density': 'Mixture density (g/cm³)',
            'weighted_avg_tg': 'Glass transition temperature of binder blend (°C)',
            'weighted_avg_oh_value': 'OH value of binder blend (mg KOH/g)',
            'voc_content': 'Volatile Organic Compound content (g/L)',
            'solvent_ratio': 'Solvent content (%)',
            'avg_evaporation_rate': 'Average solvent evaporation rate (BuAc=1)',
            'binder_ratio': 'Binder content (%)',
            'pigment_ratio': 'Pigment + Filler content (%)',
            'additive_ratio': 'Additive content (%)',
            'theoretical_cost': 'Theoretical cost (per kg)',
        }
