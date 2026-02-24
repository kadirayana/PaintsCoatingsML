"""
Material Similarity Engine
==========================
Compute similarity between materials based on TDS properties.

Features:
- Cosine similarity for general matching
- Euclidean distance for absolute differences
- Hansen solubility distance (Ra) for solvent compatibility
- Feature vector normalization with log scaling for wide-range properties

Usage:
    from src.data_handlers.material_similarity import MaterialSimilarityEngine
    
    engine = MaterialSimilarityEngine(db_manager)
    engine.build_index()
    
    # Find similar materials
    similar = engine.find_similar(material_id=42, top_k=5)
    
    # Find compatible solvents based on Hansen parameters
    solvents = engine.find_compatible_solvents(resin_id=42)
"""
import math
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import numpy, fall back to pure Python if not available
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("NumPy not available, using pure Python (slower)")


@dataclass
class MaterialVector:
    """Normalized feature vector for a material."""
    material_id: int
    name: str
    category: str
    features: List[float]


class MaterialSimilarityEngine:
    """
    Compute similarity between materials without lab testing.
    
    Uses TDS (Technical Data Sheet) properties to build feature vectors
    and compute similarity metrics.
    """
    
    # Feature configuration - order matters for vector construction
    NUMERIC_FEATURES = [
        'hansen_d', 'hansen_p', 'hansen_h',
        'density', 'solid_content', 'oh_value',
        'glass_transition', 'molecular_weight',
        'acid_value', 'particle_size', 'voc_g_l', 'ph'
    ]
    
    NORMALIZATION_RANGES = {
        'hansen_d': (10, 25),
        'hansen_p': (0, 20),
        'hansen_h': (0, 25),
        'density': (0.7, 3.0),
        'solid_content': (0, 100),
        'oh_value': (0, 500),
        'glass_transition': (-50, 150),
        'molecular_weight': (100, 100000),  # Log scale
        'acid_value': (0, 300),
        'particle_size': (0.01, 100),       # Log scale, microns
        'voc_g_l': (0, 800),
        'ph': (1, 14),
    }
    
    LOG_SCALE_FEATURES = {'molecular_weight', 'particle_size'}
    
    CATEGORIES = ['resin', 'pigment', 'solvent', 'additive', 'filler', 'other']
    
    def __init__(self, db_manager):
        """
        Initialize the similarity engine.
        
        Args:
            db_manager: LocalDBManager instance
        """
        self.db = db_manager
        self._vectors: List[MaterialVector] = []
        self._id_to_idx: Dict[int, int] = {}
        self._materials_cache: Dict[int, dict] = {}
    
    def build_index(self) -> int:
        """
        Build the similarity index from all complete materials.
        
        Returns:
            Number of materials indexed
        """
        try:
            materials = self.db.get_complete_materials()
        except AttributeError:
            # Fallback if method doesn't exist
            materials = self.db.get_all_materials()
            materials = [m for m in materials if not m.get('is_incomplete', False)]
        
        self._vectors = []
        self._id_to_idx = {}
        self._materials_cache = {}
        
        for mat in materials:
            vec = self._to_vector(mat)
            if vec is not None:
                self._id_to_idx[mat['id']] = len(self._vectors)
                self._vectors.append(vec)
                self._materials_cache[mat['id']] = mat
        
        logger.info(f"Built similarity index with {len(self._vectors)} materials")
        return len(self._vectors)
    
    def _to_vector(self, material: dict) -> Optional[MaterialVector]:
        """Convert material dict to normalized feature vector."""
        features = []
        
        # Numeric features
        for feat in self.NUMERIC_FEATURES:
            value = material.get(feat)
            if value is None:
                features.append(0.5)  # Default to middle of range
            else:
                features.append(self._normalize(feat, value))
        
        # Category one-hot encoding
        category = (material.get('category') or 'other').lower()
        for cat in self.CATEGORIES:
            features.append(1.0 if category == cat else 0.0)
        
        return MaterialVector(
            material_id=material['id'],
            name=material.get('name', ''),
            category=category,
            features=features
        )
    
    def _normalize(self, feature: str, value: float) -> float:
        """Normalize value to 0-1 range."""
        try:
            value = float(value)
        except (TypeError, ValueError):
            return 0.5
        
        if feature in self.LOG_SCALE_FEATURES and value > 0:
            value = math.log10(value)
            min_val, max_val = self.NORMALIZATION_RANGES.get(feature, (0, 1))
            min_val = math.log10(max(min_val, 0.001))
            max_val = math.log10(max(max_val, 1))
        else:
            min_val, max_val = self.NORMALIZATION_RANGES.get(feature, (0, 1))
        
        if max_val == min_val:
            return 0.5
        return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))
    
    def _dot_product(self, v1: List[float], v2: List[float]) -> float:
        """Compute dot product of two vectors."""
        return sum(a * b for a, b in zip(v1, v2))
    
    def _magnitude(self, v: List[float]) -> float:
        """Compute magnitude of a vector."""
        return math.sqrt(sum(x * x for x in v))
    
    def cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = self._dot_product(v1, v2)
        mag1 = self._magnitude(v1)
        mag2 = self._magnitude(v2)
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)
    
    def euclidean_distance(self, v1: List[float], v2: List[float]) -> float:
        """Compute Euclidean distance between two vectors."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))
    
    def hansen_distance(self, mat1: dict, mat2: dict) -> float:
        """
        Calculate Hansen solubility distance (Ra).
        
        Ra² = 4(δD₁-δD₂)² + (δP₁-δP₂)² + (δH₁-δH₂)²
        
        materials are compatible if Ra < R₀ (interaction radius).
        Typical R₀ values: 5-10 for good compatibility.
        
        Args:
            mat1: First material dict with hansen_d, hansen_p, hansen_h
            mat2: Second material dict
            
        Returns:
            Hansen Ra distance
        """
        dD = (mat1.get('hansen_d') or 0) - (mat2.get('hansen_d') or 0)
        dP = (mat1.get('hansen_p') or 0) - (mat2.get('hansen_p') or 0)
        dH = (mat1.get('hansen_h') or 0) - (mat2.get('hansen_h') or 0)
        return math.sqrt(4 * dD**2 + dP**2 + dH**2)
    
    def find_similar(
        self, 
        material_id: int, 
        top_k: int = 5,
        category_filter: Optional[str] = None,
        metric: str = 'cosine'
    ) -> List[Tuple[int, str, float]]:
        """
        Find most similar materials to a given material.
        
        Args:
            material_id: Source material ID
            top_k: Number of results to return
            category_filter: Optional category to filter results by
            metric: 'cosine' or 'euclidean'
            
        Returns:
            List of (material_id, name, similarity_score) tuples
            Higher scores = more similar for cosine
            Lower scores = more similar for euclidean
        """
        if material_id not in self._id_to_idx:
            logger.warning(f"Material {material_id} not in index")
            return []
        
        source_idx = self._id_to_idx[material_id]
        source_vec = self._vectors[source_idx]
        
        scores = []
        for i, vec in enumerate(self._vectors):
            if i == source_idx:
                continue
            if category_filter and vec.category != category_filter.lower():
                continue
            
            if metric == 'cosine':
                score = self.cosine_similarity(source_vec.features, vec.features)
            elif metric == 'euclidean':
                # Negate so higher = more similar
                score = -self.euclidean_distance(source_vec.features, vec.features)
            else:
                score = self.cosine_similarity(source_vec.features, vec.features)
            
            scores.append((vec.material_id, vec.name, score))
        
        # Sort by similarity (higher is better)
        scores.sort(key=lambda x: x[2], reverse=True)
        return scores[:top_k]
    
    def find_compatible_solvents(
        self, 
        resin_id: int, 
        max_ra: float = 8.0
    ) -> List[Tuple[int, str, float]]:
        """
        Find solvents compatible with a resin based on Hansen parameters.
        
        Args:
            resin_id: Resin material ID
            max_ra: Maximum Ra distance for compatibility (default 8.0)
            
        Returns:
            List of (solvent_id, name, ra_distance) sorted by Ra ascending
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get resin data
            cursor.execute('SELECT * FROM materials WHERE id = ?', (resin_id,))
            row = cursor.fetchone()
            if not row:
                return []
            resin = dict(row)
            
            # Get all solvents
            cursor.execute(
                "SELECT * FROM materials WHERE LOWER(category) = 'solvent'"
            )
            solvents = [dict(r) for r in cursor.fetchall()]
        
        results = []
        for solvent in solvents:
            ra = self.hansen_distance(resin, solvent)
            if ra <= max_ra:
                results.append((solvent['id'], solvent['name'], ra))
        
        # Sort by Ra (lower = better compatibility)
        results.sort(key=lambda x: x[2])
        return results
    
    def find_substitutes(
        self, 
        material_id: int, 
        top_k: int = 5
    ) -> List[Tuple[int, str, float, str]]:
        """
        Find potential substitutes for a material within the same category.
        
        Args:
            material_id: Material to find substitutes for
            top_k: Number of results
            
        Returns:
            List of (material_id, name, similarity, reason) tuples
        """
        if material_id not in self._id_to_idx:
            return []
        
        source_vec = self._vectors[self._id_to_idx[material_id]]
        category = source_vec.category
        
        # Find similar materials in same category
        similar = self.find_similar(
            material_id, 
            top_k=top_k, 
            category_filter=category
        )
        
        results = []
        for mat_id, name, score in similar:
            # Generate reason based on similarity
            if score > 0.95:
                reason = "Çok benzer özellikler"
            elif score > 0.85:
                reason = "Benzer özellikler"
            elif score > 0.70:
                reason = "Kısmen benzer"
            else:
                reason = "Alternatif seçenek"
            
            results.append((mat_id, name, score, reason))
        
        return results
    
    def get_material_profile(self, material_id: int) -> Optional[Dict]:
        """
        Get a detailed profile of a material's normalized features.
        
        Args:
            material_id: Material ID
            
        Returns:
            Dict with feature names and normalized values
        """
        if material_id not in self._id_to_idx:
            return None
        
        vec = self._vectors[self._id_to_idx[material_id]]
        
        profile = {
            'id': vec.material_id,
            'name': vec.name,
            'category': vec.category,
            'features': {}
        }
        
        # Map features back to names
        for i, feat in enumerate(self.NUMERIC_FEATURES):
            profile['features'][feat] = vec.features[i]
        
        return profile
    
    # =========================================================================
    # EXPLAINABLE SIMILARITY METHODS (Material Intelligence System Extension)
    # =========================================================================
    
    def find_similar_with_explanation(
        self, 
        material_id: int, 
        top_k: int = 5,
        category_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Find similar materials with human-readable explanations.
        
        This method not only finds similar materials but also explains
        WHY they are similar, which features match, and which diverge.
        
        Args:
            material_id: Source material ID
            top_k: Number of results
            category_filter: Optional category filter
            
        Returns:
            List of dicts with:
                - material_id: int
                - name: str
                - similarity: float (0-1)
                - explanation: str (human-readable)
                - matching_features: List[str]
                - diverging_features: List[str]
                - feature_comparison: Dict[str, Dict] (detailed)
        """
        if material_id not in self._id_to_idx:
            logger.warning(f"Material {material_id} not in index")
            return []
        
        source_idx = self._id_to_idx[material_id]
        source_vec = self._vectors[source_idx]
        source_mat = self._materials_cache.get(material_id, {})
        
        results = []
        
        for i, candidate in enumerate(self._vectors):
            if i == source_idx:
                continue
            if category_filter and candidate.category != category_filter.lower():
                continue
            
            # Calculate similarity
            similarity = self.cosine_similarity(source_vec.features, candidate.features)
            
            # Analyze feature-by-feature
            matching, diverging, comparison = self._compare_features(
                source_vec.features, 
                candidate.features
            )
            
            # Generate explanation
            candidate_mat = self._materials_cache.get(candidate.material_id, {})
            explanation = self._generate_explanation(
                source_mat.get('name', 'Source'),
                candidate_mat.get('name', candidate.name),
                matching,
                diverging,
                similarity
            )
            
            results.append({
                'material_id': candidate.material_id,
                'name': candidate.name,
                'category': candidate.category,
                'similarity': similarity,
                'explanation': explanation,
                'matching_features': matching,
                'diverging_features': diverging,
                'feature_comparison': comparison,
            })
        
        # Sort by similarity
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]
    
    def _compare_features(
        self, 
        source: List[float], 
        target: List[float],
        match_threshold: float = 0.15,
        diverge_threshold: float = 0.3
    ) -> Tuple[List[str], List[str], Dict]:
        """
        Compare two feature vectors and identify matching/diverging features.
        
        Args:
            source: Source feature vector
            target: Target feature vector
            match_threshold: Maximum difference to consider "matching"
            diverge_threshold: Minimum difference to consider "diverging"
            
        Returns:
            (matching_features, diverging_features, detailed_comparison)
        """
        matching = []
        diverging = []
        comparison = {}
        
        # Compare numeric features
        for i, feat in enumerate(self.NUMERIC_FEATURES):
            if i >= len(source) or i >= len(target):
                break
            
            diff = abs(source[i] - target[i])
            comparison[feat] = {
                'source': source[i],
                'target': target[i],
                'difference': diff,
            }
            
            if diff <= match_threshold:
                matching.append(feat)
                comparison[feat]['status'] = 'match'
            elif diff >= diverge_threshold:
                diverging.append(feat)
                comparison[feat]['status'] = 'diverge'
            else:
                comparison[feat]['status'] = 'neutral'
        
        return matching, diverging, comparison
    
    def _generate_explanation(
        self, 
        source_name: str,
        target_name: str,
        matching: List[str],
        diverging: List[str],
        similarity: float
    ) -> str:
        """
        Generate a human-readable explanation of similarity.
        
        Args:
            source_name: Name of source material
            target_name: Name of target material
            matching: List of matching feature names
            diverging: List of diverging feature names
            similarity: Overall similarity score
            
        Returns:
            Human-readable explanation string
        """
        # Feature name translations for readability
        FEATURE_TRANSLATIONS = {
            'hansen_d': 'dispersion forces',
            'hansen_p': 'polar character',
            'hansen_h': 'hydrogen bonding',
            'density': 'density',
            'solid_content': 'solid content',
            'oh_value': 'OH value',
            'glass_transition': 'Tg (hardness)',
            'molecular_weight': 'molecular weight',
            'acid_value': 'acid value',
            'particle_size': 'particle size',
            'voc_g_l': 'VOC content',
            'ph': 'pH',
        }
        
        parts = []
        
        # Describe matching features (prioritize important ones)
        priority_features = ['glass_transition', 'oh_value', 'hansen_h', 'solid_content']
        important_matches = [f for f in priority_features if f in matching]
        
        if important_matches:
            translated = [FEATURE_TRANSLATIONS.get(f, f) for f in important_matches[:2]]
            parts.append(f"similar {' and '.join(translated)}")
        elif matching:
            translated = [FEATURE_TRANSLATIONS.get(f, f) for f in matching[:2]]
            parts.append(f"matching {' and '.join(translated)}")
        
        # Note diverging features (limit to most important)
        if diverging:
            important_diverge = [f for f in priority_features if f in diverging]
            if important_diverge:
                translated = [FEATURE_TRANSLATIONS.get(f, f) for f in important_diverge[:2]]
                parts.append(f"differs in {' and '.join(translated)}")
        
        # Build final explanation
        if not parts:
            if similarity > 0.9:
                return f"Very similar overall properties"
            elif similarity > 0.7:
                return f"Moderately similar properties"
            else:
                return f"Some similarity in properties"
        
        explanation = "; ".join(parts)
        return explanation[0].upper() + explanation[1:]  # Capitalize first letter
    
    def explain_similarity_detail(
        self, 
        material_id_1: int, 
        material_id_2: int
    ) -> Optional[Dict]:
        """
        Get detailed explanation of similarity between two specific materials.
        
        Args:
            material_id_1: First material ID
            material_id_2: Second material ID
            
        Returns:
            Detailed comparison dict or None if materials not found
        """
        if material_id_1 not in self._id_to_idx or material_id_2 not in self._id_to_idx:
            return None
        
        vec1 = self._vectors[self._id_to_idx[material_id_1]]
        vec2 = self._vectors[self._id_to_idx[material_id_2]]
        mat1 = self._materials_cache.get(material_id_1, {})
        mat2 = self._materials_cache.get(material_id_2, {})
        
        # Calculate metrics
        cosine_sim = self.cosine_similarity(vec1.features, vec2.features)
        euclidean_dist = self.euclidean_distance(vec1.features, vec2.features)
        hansen_dist = self.hansen_distance(mat1, mat2)
        
        # Feature comparison
        matching, diverging, comparison = self._compare_features(vec1.features, vec2.features)
        
        # Generate explanation
        explanation = self._generate_explanation(
            mat1.get('name', 'Material 1'),
            mat2.get('name', 'Material 2'),
            matching,
            diverging,
            cosine_sim
        )
        
        return {
            'material_1': {
                'id': material_id_1,
                'name': mat1.get('name', ''),
                'category': vec1.category,
            },
            'material_2': {
                'id': material_id_2,
                'name': mat2.get('name', ''),
                'category': vec2.category,
            },
            'metrics': {
                'cosine_similarity': cosine_sim,
                'euclidean_distance': euclidean_dist,
                'hansen_distance': hansen_dist,
            },
            'matching_features': matching,
            'diverging_features': diverging,
            'feature_comparison': comparison,
            'explanation': explanation,
            'compatibility_assessment': self._assess_compatibility(cosine_sim, hansen_dist, vec1.category, vec2.category),
        }
    
    def _assess_compatibility(
        self, 
        similarity: float, 
        hansen_dist: float,
        cat1: str,
        cat2: str
    ) -> str:
        """Generate compatibility assessment text."""
        
        # Same category substitution assessment
        if cat1 == cat2:
            if similarity > 0.9:
                return "Excellent substitute - nearly identical properties"
            elif similarity > 0.8:
                return "Good substitute - minor property differences"
            elif similarity > 0.6:
                return "Possible substitute - verify critical properties"
            else:
                return "Poor substitute - significant property differences"
        
        # Cross-category (e.g., solvent-resin compatibility)
        if 'solvent' in [cat1, cat2] and 'resin' in [cat1, cat2]:
            if hansen_dist < 4:
                return "Excellent compatibility - within solubility sphere"
            elif hansen_dist < 8:
                return "Good compatibility - borderline solubility"
            else:
                return "Poor compatibility - outside solubility sphere"
        
        return "Assessment requires domain-specific evaluation"
    
    def get_fingerprint_comparison(
        self, 
        material_id: int
    ) -> Optional[Dict]:
        """
        Get material's fingerprint for UI visualization.
        
        Combines TDS-based vector with functional fingerprint if available.
        
        Args:
            material_id: Material ID
            
        Returns:
            Dict with normalized feature values for radar chart display
        """
        mat = self._materials_cache.get(material_id)
        if not mat:
            return None
        
        # Try to get functional fingerprint
        try:
            from src.ml_engine.material_feature_extractor import MaterialFeatureExtractor
            extractor = MaterialFeatureExtractor()
            fp, mask = extractor.extract(mat)
            feature_names = extractor.get_feature_names()
            
            return {
                'material_id': material_id,
                'name': mat.get('name', ''),
                'fingerprint': dict(zip(feature_names, fp)),
                'confidence': dict(zip(feature_names, mask)),
                'overall_confidence': sum(mask) / len(mask) if mask else 0,
            }
        except ImportError:
            # Fall back to basic profile
            return self.get_material_profile(material_id)

