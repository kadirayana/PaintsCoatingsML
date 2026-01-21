"""
Enhanced Recipe Transformer - Fingerprint-Based Recipe Vectorization
====================================================================
Transforms recipes (material lists with percentages) into fixed-length
feature vectors using weighted functional fingerprints.

Key Features:
- Uses MaterialFeatureExtractor for per-material fingerprints
- Weighted average based on material percentages
- Produces confidence mask indicating data quality
- Computes formulation metadata (P/B ratio, solid content, etc.)

Usage:
    from src.ml_engine.enhanced_recipe_transformer import EnhancedRecipeTransformer
    from src.ml_engine.material_feature_extractor import MaterialFeatureExtractor
    
    extractor = MaterialFeatureExtractor()
    transformer = EnhancedRecipeTransformer(extractor, db_manager)
    
    recipe = [
        {'material_code': 'RESIN-001', 'percentage': 30},
        {'material_code': 'PIGMENT-001', 'percentage': 20},
        {'material_code': 'SOLVENT-001', 'percentage': 50},
    ]
    
    vector, mask, metadata = transformer.transform(recipe)
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Try numpy, fall back to list operations
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


@dataclass
class RecipeTransformResult:
    """Result of recipe transformation with full metadata."""
    vector: List[float]           # Weighted fingerprint vector
    mask: List[float]             # Confidence mask
    feature_names: List[str]      # Feature names for interpretation
    metadata: Dict[str, float]    # Computed formulation properties
    material_breakdown: List[Dict] = field(default_factory=list)  # Per-material contribution
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'vector': self.vector,
            'mask': self.mask,
            'features': dict(zip(self.feature_names, self.vector)),
            'confidence': dict(zip(self.feature_names, self.mask)),
            'metadata': self.metadata,
            'overall_confidence': sum(self.mask) / len(self.mask) if self.mask else 0,
            'material_breakdown': self.material_breakdown
        }


class EnhancedRecipeTransformer:
    """
    Transforms recipes into fixed-length feature vectors using
    weighted functional fingerprints.
    
    Design Principles:
    - Each material contributes proportionally to its percentage
    - Missing materials are handled gracefully with warnings
    - Confidence mask shows how much real data vs imputation was used
    - Metadata includes critical formulation parameters
    """
    
    # Category keywords for classification
    CATEGORY_KEYWORDS = {
        'binder': ['binder', 'resin', 'polymer', 'alkyd', 'polyester', 'acrylic', 'epoxy', 'polyurethane'],
        'pigment': ['pigment', 'titanium', 'tio2', 'iron oxide', 'carbon black', 'color'],
        'filler': ['filler', 'extender', 'calcium carbonate', 'talc', 'silica', 'barium'],
        'solvent': ['solvent', 'thinner', 'xylene', 'toluene', 'butyl', 'acetate', 'ketone', 'alcohol'],
        'additive': ['additive', 'dispersant', 'wetting', 'defoamer', 'rheology', 'thickener', 'biocide', 'dryer'],
    }
    
    def __init__(self, feature_extractor, db_manager):
        """
        Initialize the recipe transformer.
        
        Args:
            feature_extractor: MaterialFeatureExtractor instance
            db_manager: LocalDBManager instance for material lookups
        """
        self.extractor = feature_extractor
        self.db = db_manager
        self._material_cache: Dict[str, Dict] = {}
        self._fingerprint_cache: Dict[int, Tuple[List[float], List[float]]] = {}
    
    def transform(self, recipe: List[Dict]) -> Tuple[List[float], List[float], Dict]:
        """
        Transform a recipe to a feature vector.
        
        Args:
            recipe: List of ingredient dicts. Each dict should have:
                - material_code (or component_name): Material identifier
                - percentage (or amount): Weight percentage
                
        Returns:
            (vector, mask, metadata):
                vector: Fixed-length feature vector (weighted fingerprint)
                mask: Confidence mask (how much data was available)
                metadata: Additional computed properties
        """
        dims = self.extractor.FINGERPRINT_DIMS
        
        if not recipe:
            return [0.0] * dims, [0.0] * dims, {}
        
        # Accumulate weighted fingerprints
        weighted_fp = [0.0] * dims
        weighted_mask = [0.0] * dims
        total_weight = 0.0
        
        # Category tracking for metadata
        category_weights = {
            'binder': 0.0,
            'pigment': 0.0,
            'filler': 0.0,
            'solvent': 0.0,
            'additive': 0.0,
            'unknown': 0.0,
        }
        
        # Material breakdown for explainability
        material_breakdown = []
        missing_materials = []
        
        for item in recipe:
            # Get material identifier
            code = (item.get('material_code') or 
                   item.get('component_name') or 
                   item.get('code') or 
                   item.get('name'))
            
            # Get percentage
            pct = (item.get('percentage') or 
                  item.get('amount') or 
                  item.get('weight') or 0)
            
            try:
                pct = float(pct)
            except (TypeError, ValueError):
                pct = 0
            
            if not code or pct <= 0:
                continue
            
            # Get material from database
            mat = self._get_material(code)
            if not mat:
                missing_materials.append(code)
                # Still contribute to category weights if we can guess
                category = self._guess_category(code, item)
                category_weights[category] += pct
                total_weight += pct
                continue
            
            # Get or compute fingerprint
            mat_id = mat.get('id')
            if mat_id and mat_id in self._fingerprint_cache:
                fp, mask = self._fingerprint_cache[mat_id]
            else:
                fp, mask = self.extractor.extract(mat)
                if mat_id:
                    self._fingerprint_cache[mat_id] = (fp, mask)
            
            # Accumulate weighted fingerprint
            for i in range(dims):
                weighted_fp[i] += fp[i] * pct
                weighted_mask[i] += mask[i] * pct
            total_weight += pct
            
            # Track category
            category = self._get_category(mat)
            category_weights[category] += pct
            
            # Record breakdown
            material_breakdown.append({
                'code': code,
                'name': mat.get('name', code),
                'percentage': pct,
                'category': category,
                'fingerprint': fp,
                'confidence': sum(mask) / len(mask) if mask else 0,
            })
        
        # Normalize by total weight
        if total_weight > 0:
            for i in range(dims):
                weighted_fp[i] /= total_weight
                weighted_mask[i] /= total_weight
        
        # Log any missing materials
        if missing_materials:
            logger.warning(f"Materials not found in database: {missing_materials}")
        
        # Compute metadata
        metadata = self._compute_metadata(category_weights, total_weight, recipe)
        
        return weighted_fp, weighted_mask, metadata
    
    def transform_with_breakdown(self, recipe: List[Dict]) -> RecipeTransformResult:
        """
        Transform recipe with full breakdown for UI display.
        
        Args:
            recipe: List of ingredient dicts
            
        Returns:
            RecipeTransformResult with full metadata and breakdown
        """
        # We need to capture material_breakdown during transform
        dims = self.extractor.FINGERPRINT_DIMS
        
        if not recipe:
            return RecipeTransformResult(
                vector=[0.0] * dims,
                mask=[0.0] * dims,
                feature_names=self.extractor.get_feature_names(),
                metadata={},
                material_breakdown=[]
            )
        
        weighted_fp = [0.0] * dims
        weighted_mask = [0.0] * dims
        total_weight = 0.0
        category_weights = {k: 0.0 for k in ['binder', 'pigment', 'filler', 'solvent', 'additive', 'unknown']}
        material_breakdown = []
        
        for item in recipe:
            code = (item.get('material_code') or 
                   item.get('component_name') or 
                   item.get('code') or 
                   item.get('name'))
            pct = float(item.get('percentage') or item.get('amount') or item.get('weight') or 0)
            
            if not code or pct <= 0:
                continue
            
            mat = self._get_material(code)
            if not mat:
                category = self._guess_category(code, item)
                category_weights[category] += pct
                total_weight += pct
                material_breakdown.append({
                    'code': code,
                    'name': code,
                    'percentage': pct,
                    'category': category,
                    'fingerprint': [0.5] * dims,
                    'confidence': 0,
                    'status': 'missing',
                })
                continue
            
            mat_id = mat.get('id')
            if mat_id and mat_id in self._fingerprint_cache:
                fp, mask = self._fingerprint_cache[mat_id]
            else:
                fp, mask = self.extractor.extract(mat)
                if mat_id:
                    self._fingerprint_cache[mat_id] = (fp, mask)
            
            for i in range(dims):
                weighted_fp[i] += fp[i] * pct
                weighted_mask[i] += mask[i] * pct
            total_weight += pct
            
            category = self._get_category(mat)
            category_weights[category] += pct
            
            material_breakdown.append({
                'code': code,
                'name': mat.get('name', code),
                'percentage': pct,
                'category': category,
                'fingerprint': fp,
                'confidence': sum(mask) / len(mask) if mask else 0,
                'status': 'found',
            })
        
        if total_weight > 0:
            for i in range(dims):
                weighted_fp[i] /= total_weight
                weighted_mask[i] /= total_weight
        
        metadata = self._compute_metadata(category_weights, total_weight, recipe)
        
        return RecipeTransformResult(
            vector=weighted_fp,
            mask=weighted_mask,
            feature_names=self.extractor.get_feature_names(),
            metadata=metadata,
            material_breakdown=material_breakdown
        )
    
    def _get_material(self, code: str) -> Optional[Dict]:
        """
        Get material from database with caching.
        
        Args:
            code: Material code or name
            
        Returns:
            Material dict or None if not found
        """
        if code in self._material_cache:
            cached = self._material_cache[code]
            return cached if cached else None
        
        # Try to find in database
        try:
            mat = self.db.get_material_by_code_or_name(code)
        except AttributeError:
            # Fallback if method doesn't exist
            try:
                mat = self.db.get_material_by_code(code)
            except:
                mat = None
        
        self._material_cache[code] = mat
        return mat
    
    def _get_category(self, material: Dict) -> str:
        """
        Get category for a material, normalized to standard categories.
        
        Args:
            material: Material dict with 'category' field
            
        Returns:
            Normalized category name
        """
        cat = (material.get('category') or 'unknown').lower().strip()
        
        for std_cat, keywords in self.CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in cat:
                    return std_cat
        
        return 'unknown'
    
    def _guess_category(self, code: str, item: Dict) -> str:
        """
        Guess category when material is not in database.
        
        Args:
            code: Material code
            item: Recipe item dict
            
        Returns:
            Guessed category name
        """
        # Check if item has a category hint
        cat_hint = (item.get('category') or item.get('component_type') or '').lower()
        
        # Check code and hint against keywords
        text = f"{code} {cat_hint}".lower()
        
        for std_cat, keywords in self.CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return std_cat
        
        return 'unknown'
    
    def _compute_metadata(self, 
                         category_weights: Dict[str, float], 
                         total_weight: float,
                         recipe: List[Dict]) -> Dict[str, float]:
        """
        Compute formulation-level metadata from category breakdown.
        
        Args:
            category_weights: Weight per category
            total_weight: Total recipe weight
            recipe: Original recipe for additional calculations
            
        Returns:
            Dict with computed metadata
        """
        if total_weight == 0:
            return {}
        
        # Normalize weights to ratios
        binder = category_weights['binder'] / total_weight
        pigment = category_weights['pigment'] / total_weight
        filler = category_weights['filler'] / total_weight
        solvent = category_weights['solvent'] / total_weight
        additive = category_weights['additive'] / total_weight
        
        # Calculate P/B ratio (Pigment + Filler to Binder)
        pb_ratio = 0.0
        if binder > 0:
            pb_ratio = (pigment + filler) / binder
        
        # Estimate solid content (everything except solvent)
        solid_content = 1.0 - solvent
        
        # Calculate total cost if prices available
        total_cost = 0.0
        for item in recipe:
            code = (item.get('material_code') or 
                   item.get('component_name') or 
                   item.get('code'))
            pct = float(item.get('percentage') or item.get('amount') or 0)
            
            if code and pct > 0:
                mat = self._get_material(code)
                if mat and mat.get('unit_price'):
                    total_cost += (pct / 100) * mat['unit_price']
        
        return {
            'binder_ratio': binder,
            'pigment_ratio': pigment,
            'filler_ratio': filler,
            'solvent_ratio': solvent,
            'additive_ratio': additive,
            'pigment_binder_ratio': pb_ratio,
            'solid_content_est': solid_content,
            'total_weight': total_weight,
            'theoretical_cost': total_cost,
            'material_count': len(recipe),
        }
    
    def clear_cache(self):
        """Clear material and fingerprint caches."""
        self._material_cache.clear()
        self._fingerprint_cache.clear()
    
    def get_feature_names(self) -> List[str]:
        """Return feature names from the underlying extractor."""
        return self.extractor.get_feature_names()
    
    def compare_recipes(self, recipe1: List[Dict], recipe2: List[Dict]) -> Dict:
        """
        Compare two recipes and highlight differences.
        
        Args:
            recipe1: First recipe
            recipe2: Second recipe
            
        Returns:
            Comparison result with similarity score and key differences
        """
        vec1, mask1, meta1 = self.transform(recipe1)
        vec2, mask2, meta2 = self.transform(recipe2)
        
        # Calculate cosine similarity
        dot = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = sum(a * a for a in vec1) ** 0.5
        mag2 = sum(b * b for b in vec2) ** 0.5
        
        if mag1 > 0 and mag2 > 0:
            similarity = dot / (mag1 * mag2)
        else:
            similarity = 0.0
        
        # Find key differences
        feature_names = self.get_feature_names()
        differences = []
        for i, name in enumerate(feature_names):
            diff = abs(vec1[i] - vec2[i])
            if diff > 0.1:  # Significant difference threshold
                differences.append({
                    'feature': name,
                    'recipe1_value': vec1[i],
                    'recipe2_value': vec2[i],
                    'difference': diff,
                })
        
        differences.sort(key=lambda x: x['difference'], reverse=True)
        
        # Metadata differences
        meta_diffs = {}
        for key in ['pigment_binder_ratio', 'solid_content_est', 'theoretical_cost']:
            if key in meta1 and key in meta2:
                meta_diffs[key] = {
                    'recipe1': meta1[key],
                    'recipe2': meta2[key],
                    'difference': meta2[key] - meta1[key]
                }
        
        return {
            'similarity': similarity,
            'feature_differences': differences[:5],  # Top 5
            'metadata_differences': meta_diffs,
            'recipe1_metadata': meta1,
            'recipe2_metadata': meta2,
        }


# Convenience function
def transform_recipe(recipe: List[Dict], db_manager) -> Tuple[List[float], List[float], Dict]:
    """
    Convenience function to transform a recipe without manual setup.
    
    Args:
        recipe: List of ingredient dicts
        db_manager: Database manager instance
        
    Returns:
        (vector, mask, metadata) tuple
    """
    from src.ml_engine.material_feature_extractor import MaterialFeatureExtractor
    
    extractor = MaterialFeatureExtractor()
    transformer = EnhancedRecipeTransformer(extractor, db_manager)
    return transformer.transform(recipe)
