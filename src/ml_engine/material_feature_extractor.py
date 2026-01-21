"""
Material Feature Extractor - Functional Fingerprint Generator
==============================================================
Converts raw TDS (Technical Data Sheet) values into a normalized 
"functional fingerprint" vector that encodes material behavior.

This is a RULE-BASED system, NOT ML-trained.
Domain knowledge is encoded directly into the derivation rules.

Key Design Principles:
- All outputs are normalized to 0-1 range
- Missing values are handled gracefully with sensible defaults
- Each feature has a clear, explainable derivation
- Mask output indicates confidence (1=derived from data, 0=imputed)

Usage:
    from src.ml_engine.material_feature_extractor import MaterialFeatureExtractor
    
    extractor = MaterialFeatureExtractor()
    fingerprint, mask = extractor.extract(material_dict)
    
    # fingerprint: np.ndarray of shape (14,), values 0-1
    # mask: np.ndarray of shape (14,), confidence indicators
"""

import math
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try numpy, fall back to list operations
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("NumPy not available, using pure Python")


@dataclass
class FingerprintResult:
    """Result of fingerprint extraction with metadata."""
    fingerprint: List[float]
    mask: List[float]
    feature_names: List[str]
    material_id: Optional[int] = None
    material_name: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'fingerprint': self.fingerprint,
            'mask': self.mask,
            'features': dict(zip(self.feature_names, self.fingerprint)),
            'confidence': dict(zip(self.feature_names, self.mask)),
            'material_id': self.material_id,
            'material_name': self.material_name,
            'overall_completeness': sum(self.mask) / len(self.mask) if self.mask else 0
        }


class MaterialFeatureExtractor:
    """
    Converts raw TDS values into a normalized functional fingerprint.
    Uses domain knowledge rules, NOT ML training.
    
    The fingerprint captures behavioral tendencies:
    - How will this material affect film formation?
    - Will it make the coating harder or more flexible?
    - What's its VOC risk?
    - How does it contribute to chemical resistance?
    
    Each dimension is derived from specific TDS properties using
    paint chemistry principles that can be explained and audited.
    """
    
    FINGERPRINT_DIMS = 14
    
    # Feature names in order
    FEATURE_NAMES = [
        'film_formation',       # 0: Tendency to form coherent films
        'viscosity_contribution',  # 1: Impact on formulation viscosity
        'hardness_tendency',    # 2: Tendency toward hard coatings
        'flexibility_tendency', # 3: Tendency toward flexible coatings
        'chemical_resistance',  # 4: Resistance to chemicals/solvents
        'water_resistance',     # 5: Hydrophobicity
        'voc_risk',            # 6: Volatile organic compound risk
        'cost_pressure',       # 7: Cost impact (normalized price)
        'opacity_contribution', # 8: Hiding power contribution
        'dispersion_ease',     # 9: How easy to disperse/dissolve
        'drying_speed',        # 10: Evaporation/curing speed
        'reactivity',          # 11: Chemical reactivity potential
        'polarity',            # 12: Polar vs non-polar character
        'completeness',        # 13: Data quality indicator
    ]
    
    # Normalization ranges based on paint industry knowledge
    # Format: (min, max) - values outside are clipped
    NORMALIZATION_RANGES = {
        'oh_value': (0, 300),           # mg KOH/g - polyester/acrylic range
        'acid_value': (0, 50),          # mg KOH/g
        'amine_value': (0, 200),        # mg KOH/g
        'glass_transition': (-40, 120), # °C (Tg)
        'molecular_weight': (500, 50000),  # g/mol, log-scale
        'solid_content': (0, 100),      # %
        'density': (0.7, 4.5),          # g/cm³ (solvent to TiO2)
        'viscosity_mpa_s': (1, 50000),  # mPa·s, log-scale
        'flash_point': (-20, 200),      # °C
        'boiling_point': (30, 300),     # °C
        'evaporation_rate': (0.01, 10), # BuAc=1.0
        'particle_size': (0.01, 50),    # µm (d50), log-scale
        'oil_absorption': (10, 100),    # g oil/100g pigment
        'refractive_index': (1.4, 2.8), # dimensionless
        'unit_price': (0, 50),          # $/kg
        'hansen_p': (0, 20),            # MPa^0.5 (polar)
        'hansen_h': (0, 25),            # MPa^0.5 (hydrogen bonding)
        'hansen_d': (10, 25),           # MPa^0.5 (dispersion)
        'voc_g_l': (0, 800),            # g/L
        'ph': (1, 14),                  # pH scale
    }
    
    # Properties that should use log-scale normalization
    LOG_SCALE_PROPERTIES = {'molecular_weight', 'viscosity_mpa_s', 'particle_size'}
    
    def __init__(self):
        """Initialize the feature extractor."""
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration on startup."""
        assert len(self.FEATURE_NAMES) == self.FINGERPRINT_DIMS, \
            f"Feature names ({len(self.FEATURE_NAMES)}) != dims ({self.FINGERPRINT_DIMS})"
    
    def extract(self, material: Dict) -> Tuple[List[float], List[float]]:
        """
        Extract functional fingerprint from material TDS data.
        
        Args:
            material: Dict with TDS properties. Expected keys include:
                - oh_value, acid_value, amine_value
                - glass_transition, molecular_weight
                - solid_content, density, viscosity_mpa_s
                - flash_point, boiling_point, evaporation_rate
                - particle_size, oil_absorption, refractive_index
                - hansen_d, hansen_p, hansen_h
                - unit_price, voc_g_l, ph
                - is_reactive, is_crosslinker (boolean flags)
                - category (resin, pigment, solvent, additive, filler)
                
        Returns:
            (fingerprint, mask): 
                fingerprint: List[float] of length 14, values 0-1
                mask: List[float] of length 14, confidence indicators
                      1.0 = derived from actual data
                      0.5 = partially estimated
                      0.0 = fully imputed/default
        """
        fp = [0.0] * self.FINGERPRINT_DIMS
        mask = [0.0] * self.FINGERPRINT_DIMS
        
        # Pre-normalize commonly used values
        oh = self._normalize('oh_value', material.get('oh_value'))
        acid = self._normalize('acid_value', material.get('acid_value'))
        amine = self._normalize('amine_value', material.get('amine_value'))
        mw = self._normalize('molecular_weight', material.get('molecular_weight'), log_scale=True)
        tg = self._normalize('glass_transition', material.get('glass_transition'))
        solid = self._normalize('solid_content', material.get('solid_content'))
        visc = self._normalize('viscosity_mpa_s', material.get('viscosity_mpa_s'), log_scale=True)
        flash = self._normalize('flash_point', material.get('flash_point'))
        boil = self._normalize('boiling_point', material.get('boiling_point'))
        evap = self._normalize('evaporation_rate', material.get('evaporation_rate'))
        ps = self._normalize('particle_size', material.get('particle_size'), log_scale=True)
        oil = self._normalize('oil_absorption', material.get('oil_absorption'))
        ri = self._normalize('refractive_index', material.get('refractive_index'))
        hp = self._normalize('hansen_p', material.get('hansen_p'))
        hh = self._normalize('hansen_h', material.get('hansen_h'))
        price = self._normalize('unit_price', material.get('unit_price'))
        
        is_reactive = 1.0 if material.get('is_reactive') else 0.0
        is_crosslinker = 1.0 if material.get('is_crosslinker') else 0.0
        
        # ─────────────────────────────────────────────────────────────
        # 0. FILM FORMATION TENDENCY
        # High OH + high MW + high solid = good film formation
        # ─────────────────────────────────────────────────────────────
        film_values = [v for v in [oh, mw, solid] if v is not None]
        if film_values:
            fp[0] = sum(film_values) / len(film_values)
            mask[0] = 1.0 if len(film_values) >= 2 else 0.5
        else:
            fp[0] = 0.5  # Default to middle
        
        # ─────────────────────────────────────────────────────────────
        # 1. VISCOSITY CONTRIBUTION
        # Direct from viscosity, or estimate from MW
        # ─────────────────────────────────────────────────────────────
        if visc is not None:
            fp[1] = visc
            mask[1] = 1.0
        elif mw is not None:
            # MW correlates with viscosity (higher MW → thicker)
            fp[1] = mw * 0.7
            mask[1] = 0.5
        else:
            fp[1] = 0.5
        
        # ─────────────────────────────────────────────────────────────
        # 2. HARDNESS TENDENCY
        # Primarily driven by Tg (glass transition temperature)
        # Higher Tg → harder coating
        # ─────────────────────────────────────────────────────────────
        if tg is not None:
            fp[2] = tg
            mask[2] = 1.0
        elif is_crosslinker:
            fp[2] = 0.7  # Crosslinkers typically increase hardness
            mask[2] = 0.5
        else:
            fp[2] = 0.5
        
        # ─────────────────────────────────────────────────────────────
        # 3. FLEXIBILITY TENDENCY
        # Inverse of hardness, boosted by high MW
        # Low Tg + high MW = flexible
        # ─────────────────────────────────────────────────────────────
        if tg is not None:
            base_flex = 1.0 - tg
            if mw is not None:
                # High MW polymers tend to be more flexible
                fp[3] = base_flex * 0.7 + mw * 0.3
            else:
                fp[3] = base_flex
            mask[3] = 1.0 if mw is not None else 0.7
        elif mw is not None:
            fp[3] = mw * 0.5 + 0.25  # MW alone gives some flexibility info
            mask[3] = 0.5
        else:
            fp[3] = 0.5
        
        # ─────────────────────────────────────────────────────────────
        # 4. CHEMICAL RESISTANCE
        # Crosslinked + low polarity = resistant
        # ─────────────────────────────────────────────────────────────
        crosslink_potential = 0.0
        crosslink_sources = 0
        
        if oh is not None:
            crosslink_potential += oh * 0.4
            crosslink_sources += 1
        if is_crosslinker:
            crosslink_potential += 0.4
            crosslink_sources += 1
        if is_reactive:
            crosslink_potential += 0.2
            crosslink_sources += 1
        
        polarity_val = 0.5
        if hp is not None or hh is not None:
            polar_values = [v for v in [hp, hh] if v is not None]
            polarity_val = sum(polar_values) / len(polar_values)
        
        if crosslink_sources > 0 or (hp is not None or hh is not None):
            # High crosslinking + low polarity = high resistance
            fp[4] = crosslink_potential * 0.6 + (1 - polarity_val) * 0.4
            mask[4] = 1.0 if crosslink_sources > 0 else 0.5
        else:
            fp[4] = 0.5
        
        # ─────────────────────────────────────────────────────────────
        # 5. WATER RESISTANCE
        # Low hydrogen bonding = hydrophobic = water resistant
        # ─────────────────────────────────────────────────────────────
        if hh is not None:
            fp[5] = 1.0 - hh  # Inverse: low H-bonding = water resistant
            mask[5] = 1.0
        elif hp is not None:
            fp[5] = 1.0 - hp * 0.8  # Polar materials tend to be less water resistant
            mask[5] = 0.5
        else:
            fp[5] = 0.5
        
        # ─────────────────────────────────────────────────────────────
        # 6. VOC RISK
        # Low solid content + low flash point = high VOC risk
        # ─────────────────────────────────────────────────────────────
        voc_raw = material.get('voc_g_l')
        if voc_raw is not None:
            # Direct VOC measurement
            fp[6] = self._normalize('voc_g_l', voc_raw)
            mask[6] = 1.0
        elif solid is not None:
            # Estimate from solid content
            voc_estimate = 1.0 - solid
            if flash is not None:
                # Low flash point increases VOC risk
                voc_estimate = voc_estimate * 0.7 + (1 - flash) * 0.3
            fp[6] = voc_estimate
            mask[6] = 0.7 if flash is not None else 0.5
        else:
            fp[6] = 0.5
        
        # ─────────────────────────────────────────────────────────────
        # 7. COST PRESSURE
        # Direct normalization of unit price
        # ─────────────────────────────────────────────────────────────
        if price is not None:
            fp[7] = price
            mask[7] = 1.0
        else:
            fp[7] = 0.3  # Assume moderate cost if unknown
        
        # ─────────────────────────────────────────────────────────────
        # 8. OPACITY CONTRIBUTION (for pigments)
        # High refractive index + optimal particle size = high hiding
        # TiO2 optimal at ~0.2-0.4 µm
        # ─────────────────────────────────────────────────────────────
        if ri is not None:
            opacity = ri
            if ps is not None:
                # Bell curve around optimal particle size
                raw_ps = material.get('particle_size', 0.3)
                optimal_ps = 0.3  # microns
                # Gaussian-like factor: highest at optimal, decreases away
                ps_deviation = abs(raw_ps - optimal_ps)
                ps_factor = math.exp(-(ps_deviation ** 2) / 0.1)
                opacity = ri * 0.7 + ps_factor * 0.3
            fp[8] = opacity
            mask[8] = 1.0
        elif ps is not None:
            # Particle size alone gives some opacity info
            fp[8] = 1.0 - ps  # Smaller particles generally better for opacity
            mask[8] = 0.5
        else:
            fp[8] = 0.5
        
        # ─────────────────────────────────────────────────────────────
        # 9. DISPERSION EASE
        # Low oil absorption + small particle = easy to disperse
        # ─────────────────────────────────────────────────────────────
        if oil is not None:
            fp[9] = 1.0 - oil  # Lower oil absorption = easier
            mask[9] = 1.0
        elif ps is not None:
            fp[9] = 1.0 - ps  # Smaller particles = easier to disperse
            mask[9] = 0.5
        else:
            fp[9] = 0.5
        
        # ─────────────────────────────────────────────────────────────
        # 10. DRYING SPEED (for solvents)
        # Fast evaporation = quick drying
        # ─────────────────────────────────────────────────────────────
        if evap is not None:
            fp[10] = evap
            mask[10] = 1.0
        elif boil is not None:
            # Lower boiling point = faster evaporation
            fp[10] = 1.0 - boil
            mask[10] = 0.5
        else:
            fp[10] = 0.5
        
        # ─────────────────────────────────────────────────────────────
        # 11. REACTIVITY
        # Combines reactive flags + functional group values
        # ─────────────────────────────────────────────────────────────
        reactivity_score = 0.0
        reactivity_sources = 0
        
        if is_reactive:
            reactivity_score += 0.4
            reactivity_sources += 1
        if oh is not None and oh > 0.1:
            reactivity_score += oh * 0.3
            reactivity_sources += 1
        if acid is not None and acid > 0.1:
            reactivity_score += acid * 0.15
            reactivity_sources += 1
        if amine is not None and amine > 0.1:
            reactivity_score += amine * 0.15
            reactivity_sources += 1
        
        fp[11] = min(1.0, reactivity_score)
        mask[11] = 1.0 if reactivity_sources > 0 else 0.0
        
        # ─────────────────────────────────────────────────────────────
        # 12. POLARITY
        # From Hansen polar + hydrogen bonding parameters
        # ─────────────────────────────────────────────────────────────
        if hp is not None or hh is not None:
            polar_values = [v for v in [hp, hh] if v is not None]
            fp[12] = sum(polar_values) / len(polar_values)
            mask[12] = 1.0 if len(polar_values) == 2 else 0.7
        else:
            fp[12] = 0.5
        
        # ─────────────────────────────────────────────────────────────
        # 13. COMPLETENESS (Data Quality Score)
        # Percentage of properties that have actual values
        # ─────────────────────────────────────────────────────────────
        total_props = len(self.NORMALIZATION_RANGES)
        present = sum(1 for k in self.NORMALIZATION_RANGES 
                     if material.get(k) is not None)
        fp[13] = present / total_props
        mask[13] = 1.0  # Always known
        
        return fp, mask
    
    def extract_with_metadata(self, material: Dict) -> FingerprintResult:
        """
        Extract fingerprint with full metadata for UI display.
        
        Args:
            material: Dict with TDS properties
            
        Returns:
            FingerprintResult with fingerprint, mask, and metadata
        """
        fp, mask = self.extract(material)
        return FingerprintResult(
            fingerprint=fp,
            mask=mask,
            feature_names=self.FEATURE_NAMES.copy(),
            material_id=material.get('id'),
            material_name=material.get('name')
        )
    
    def _normalize(self, key: str, value, log_scale: bool = False) -> Optional[float]:
        """
        Normalize a value to 0-1 range.
        
        Args:
            key: Property name (for looking up range)
            value: Raw value to normalize
            log_scale: Whether to use log-scale normalization
            
        Returns:
            Normalized value (0-1) or None if input was None/invalid
        """
        if value is None:
            return None
        
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        
        lo, hi = self.NORMALIZATION_RANGES.get(key, (0, 1))
        
        if log_scale and value > 0:
            value = math.log10(value)
            lo = math.log10(max(lo, 0.001))
            hi = math.log10(max(hi, 1))
        
        if hi <= lo:
            return 0.5
        
        normalized = (value - lo) / (hi - lo)
        return max(0.0, min(1.0, normalized))
    
    def get_feature_names(self) -> List[str]:
        """Return the list of feature names in order."""
        return self.FEATURE_NAMES.copy()
    
    def get_feature_descriptions(self) -> Dict[str, str]:
        """Return human-readable descriptions for each feature."""
        return {
            'film_formation': "Tendency to form coherent, continuous films (from OH value, MW, solid content)",
            'viscosity_contribution': "Impact on formulation viscosity (from viscosity or MW)",
            'hardness_tendency': "Tendency toward hard coatings (from glass transition temperature)",
            'flexibility_tendency': "Tendency toward flexible coatings (inverse of hardness, modified by MW)",
            'chemical_resistance': "Resistance to chemicals and solvents (from crosslinking potential + low polarity)",
            'water_resistance': "Hydrophobicity / water resistance (from low Hansen H-bonding)",
            'voc_risk': "Volatile organic compound emission risk (from solid content, flash point)",
            'cost_pressure': "Relative cost pressure (normalized unit price)",
            'opacity_contribution': "Hiding power / opacity contribution (from refractive index, particle size)",
            'dispersion_ease': "Ease of dispersion or dissolution (from oil absorption, particle size)",
            'drying_speed': "Evaporation / drying speed (from evaporation rate, boiling point)",
            'reactivity': "Chemical reactivity potential (from functional groups: OH, acid, amine)",
            'polarity': "Polar vs non-polar character (from Hansen P and H parameters)",
            'completeness': "Data quality indicator (percentage of TDS properties available)",
        }
    
    def explain_feature(self, feature_idx: int, material: Dict) -> str:
        """
        Generate a human-readable explanation of how a feature was derived.
        
        Args:
            feature_idx: Index of the feature (0-13)
            material: The material dict that was used
            
        Returns:
            Explanation string
        """
        if feature_idx < 0 or feature_idx >= self.FINGERPRINT_DIMS:
            return "Invalid feature index"
        
        name = self.FEATURE_NAMES[feature_idx]
        fp, mask = self.extract(material)
        value = fp[feature_idx]
        confidence = mask[feature_idx]
        
        # Build explanation based on feature type
        explanations = {
            0: self._explain_film_formation(material, value, confidence),
            1: self._explain_viscosity(material, value, confidence),
            2: self._explain_hardness(material, value, confidence),
            3: self._explain_flexibility(material, value, confidence),
            4: self._explain_chemical_resistance(material, value, confidence),
            5: self._explain_water_resistance(material, value, confidence),
            6: self._explain_voc_risk(material, value, confidence),
            7: self._explain_cost(material, value, confidence),
            8: self._explain_opacity(material, value, confidence),
            9: self._explain_dispersion(material, value, confidence),
            10: self._explain_drying(material, value, confidence),
            11: self._explain_reactivity(material, value, confidence),
            12: self._explain_polarity(material, value, confidence),
            13: self._explain_completeness(material, value, confidence),
        }
        
        return explanations.get(feature_idx, f"{name}: {value:.2f}")
    
    def _explain_film_formation(self, mat: Dict, val: float, conf: float) -> str:
        oh = mat.get('oh_value')
        mw = mat.get('molecular_weight')
        solid = mat.get('solid_content')
        parts = []
        if oh: parts.append(f"OH value={oh}")
        if mw: parts.append(f"MW={mw}")
        if solid: parts.append(f"solid={solid}%")
        source = ", ".join(parts) if parts else "no data (default)"
        return f"Film formation={val:.2f} from {source}"
    
    def _explain_viscosity(self, mat: Dict, val: float, conf: float) -> str:
        visc = mat.get('viscosity_mpa_s')
        mw = mat.get('molecular_weight')
        if visc:
            return f"Viscosity contribution={val:.2f} from viscosity={visc} mPa·s"
        elif mw:
            return f"Viscosity contribution={val:.2f} estimated from MW={mw}"
        return f"Viscosity contribution={val:.2f} (default, no data)"
    
    def _explain_hardness(self, mat: Dict, val: float, conf: float) -> str:
        tg = mat.get('glass_transition')
        if tg is not None:
            return f"Hardness tendency={val:.2f} from Tg={tg}°C"
        return f"Hardness tendency={val:.2f} (default, no Tg data)"
    
    def _explain_flexibility(self, mat: Dict, val: float, conf: float) -> str:
        tg = mat.get('glass_transition')
        mw = mat.get('molecular_weight')
        if tg is not None and mw:
            return f"Flexibility={val:.2f} from Tg={tg}°C (inverse) + MW={mw}"
        elif tg is not None:
            return f"Flexibility={val:.2f} from Tg={tg}°C (inverse)"
        elif mw:
            return f"Flexibility={val:.2f} estimated from MW={mw}"
        return f"Flexibility={val:.2f} (default)"
    
    def _explain_chemical_resistance(self, mat: Dict, val: float, conf: float) -> str:
        oh = mat.get('oh_value')
        reactive = mat.get('is_reactive')
        crosslinker = mat.get('is_crosslinker')
        hp = mat.get('hansen_p')
        parts = []
        if oh: parts.append(f"OH={oh}")
        if reactive: parts.append("reactive")
        if crosslinker: parts.append("crosslinker")
        if hp: parts.append(f"Hansen P={hp}")
        source = ", ".join(parts) if parts else "default"
        return f"Chemical resistance={val:.2f} from {source}"
    
    def _explain_water_resistance(self, mat: Dict, val: float, conf: float) -> str:
        hh = mat.get('hansen_h')
        hp = mat.get('hansen_p')
        if hh is not None:
            return f"Water resistance={val:.2f} from Hansen H={hh} (inverse)"
        elif hp is not None:
            return f"Water resistance={val:.2f} estimated from Hansen P={hp}"
        return f"Water resistance={val:.2f} (default)"
    
    def _explain_voc_risk(self, mat: Dict, val: float, conf: float) -> str:
        voc = mat.get('voc_g_l')
        solid = mat.get('solid_content')
        flash = mat.get('flash_point')
        if voc is not None:
            return f"VOC risk={val:.2f} from VOC={voc} g/L"
        elif solid is not None:
            if flash is not None:
                return f"VOC risk={val:.2f} from solid={solid}%, flash={flash}°C"
            return f"VOC risk={val:.2f} from solid={solid}%"
        return f"VOC risk={val:.2f} (default)"
    
    def _explain_cost(self, mat: Dict, val: float, conf: float) -> str:
        price = mat.get('unit_price')
        if price is not None:
            return f"Cost pressure={val:.2f} from price=${price}/kg"
        return f"Cost pressure={val:.2f} (default, no price data)"
    
    def _explain_opacity(self, mat: Dict, val: float, conf: float) -> str:
        ri = mat.get('refractive_index')
        ps = mat.get('particle_size')
        if ri is not None and ps is not None:
            return f"Opacity={val:.2f} from RI={ri}, particle size={ps}µm"
        elif ri is not None:
            return f"Opacity={val:.2f} from RI={ri}"
        elif ps is not None:
            return f"Opacity={val:.2f} from particle size={ps}µm"
        return f"Opacity={val:.2f} (default)"
    
    def _explain_dispersion(self, mat: Dict, val: float, conf: float) -> str:
        oil = mat.get('oil_absorption')
        ps = mat.get('particle_size')
        if oil is not None:
            return f"Dispersion ease={val:.2f} from oil absorption={oil} (inverse)"
        elif ps is not None:
            return f"Dispersion ease={val:.2f} from particle size={ps}µm (inverse)"
        return f"Dispersion ease={val:.2f} (default)"
    
    def _explain_drying(self, mat: Dict, val: float, conf: float) -> str:
        evap = mat.get('evaporation_rate')
        boil = mat.get('boiling_point')
        if evap is not None:
            return f"Drying speed={val:.2f} from evaporation rate={evap}"
        elif boil is not None:
            return f"Drying speed={val:.2f} from boiling point={boil}°C (inverse)"
        return f"Drying speed={val:.2f} (default)"
    
    def _explain_reactivity(self, mat: Dict, val: float, conf: float) -> str:
        parts = []
        if mat.get('is_reactive'): parts.append("reactive flag")
        if mat.get('oh_value'): parts.append(f"OH={mat['oh_value']}")
        if mat.get('acid_value'): parts.append(f"acid={mat['acid_value']}")
        if mat.get('amine_value'): parts.append(f"amine={mat['amine_value']}")
        source = ", ".join(parts) if parts else "no reactive groups"
        return f"Reactivity={val:.2f} from {source}"
    
    def _explain_polarity(self, mat: Dict, val: float, conf: float) -> str:
        hp = mat.get('hansen_p')
        hh = mat.get('hansen_h')
        if hp is not None and hh is not None:
            return f"Polarity={val:.2f} from Hansen P={hp}, H={hh}"
        elif hp is not None:
            return f"Polarity={val:.2f} from Hansen P={hp}"
        elif hh is not None:
            return f"Polarity={val:.2f} from Hansen H={hh}"
        return f"Polarity={val:.2f} (default)"
    
    def _explain_completeness(self, mat: Dict, val: float, conf: float) -> str:
        total = len(self.NORMALIZATION_RANGES)
        present = sum(1 for k in self.NORMALIZATION_RANGES if mat.get(k) is not None)
        return f"Completeness={val:.2f} ({present}/{total} TDS properties available)"


# Convenience function for one-off extraction
def extract_fingerprint(material: Dict) -> Tuple[List[float], List[float]]:
    """
    Convenience function to extract fingerprint without instantiating class.
    
    Args:
        material: Dict with TDS properties
        
    Returns:
        (fingerprint, mask) tuple
    """
    extractor = MaterialFeatureExtractor()
    return extractor.extract(material)
