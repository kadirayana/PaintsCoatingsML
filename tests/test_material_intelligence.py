"""
Tests for Material Intelligence System
======================================
Unit tests for MaterialFeatureExtractor, EnhancedRecipeTransformer,
and enhanced MaterialSimilarityEngine.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ml_engine.material_feature_extractor import MaterialFeatureExtractor, FingerprintResult


class TestMaterialFeatureExtractor:
    """Tests for the MaterialFeatureExtractor class."""
    
    @pytest.fixture
    def extractor(self):
        return MaterialFeatureExtractor()
    
    @pytest.fixture
    def complete_resin(self):
        """A complete resin with all TDS properties."""
        return {
            'id': 1,
            'name': 'Polyester Resin A',
            'category': 'resin',
            'oh_value': 120,  # mg KOH/g
            'acid_value': 8,
            'glass_transition': 45,  # °C
            'molecular_weight': 5000,
            'solid_content': 70,  # %
            'viscosity_mpa_s': 3000,
            'density': 1.1,
            'hansen_d': 18,
            'hansen_p': 8,
            'hansen_h': 5,
            'unit_price': 12.5,
            'is_reactive': True,
            'is_crosslinker': False,
        }
    
    @pytest.fixture
    def minimal_material(self):
        """A material with minimal data."""
        return {
            'id': 2,
            'name': 'Unknown Material',
            'category': 'other',
        }
    
    @pytest.fixture
    def solvent(self):
        """A solvent for testing drying speed features."""
        return {
            'id': 3,
            'name': 'Xylene',
            'category': 'solvent',
            'boiling_point': 140,
            'evaporation_rate': 0.7,
            'flash_point': 25,
            'solid_content': 0,
            'hansen_d': 18,
            'hansen_p': 1,
            'hansen_h': 3,
            'voc_g_l': 720,
        }
    
    @pytest.fixture
    def pigment(self):
        """A pigment for testing opacity features."""
        return {
            'id': 4,
            'name': 'TiO2',
            'category': 'pigment',
            'density': 4.2,
            'particle_size': 0.25,
            'oil_absorption': 18,
            'refractive_index': 2.73,
            'unit_price': 3.5,
        }
    
    def test_extract_complete_material(self, extractor, complete_resin):
        """Test extraction from a complete material."""
        fp, mask = extractor.extract(complete_resin)
        
        assert len(fp) == extractor.FINGERPRINT_DIMS
        assert len(mask) == extractor.FINGERPRINT_DIMS
        
        # All values should be in 0-1 range
        for val in fp:
            assert 0 <= val <= 1, f"Fingerprint value {val} out of range"
        
        # Complete material should have high completeness
        completeness_idx = extractor.FEATURE_NAMES.index('completeness')
        assert fp[completeness_idx] > 0.5, "Complete material should have high completeness score"
        
        # Most features should have high confidence
        high_confidence_count = sum(1 for m in mask if m >= 0.5)
        assert high_confidence_count >= 8, "Complete material should have high confidence for most features"
    
    def test_extract_minimal_material(self, extractor, minimal_material):
        """Test extraction from a minimal material with missing data."""
        fp, mask = extractor.extract(minimal_material)
        
        assert len(fp) == extractor.FINGERPRINT_DIMS
        assert len(mask) == extractor.FINGERPRINT_DIMS
        
        # Values should still be valid
        for val in fp:
            assert 0 <= val <= 1
        
        # Completeness should be low
        completeness_idx = extractor.FEATURE_NAMES.index('completeness')
        assert fp[completeness_idx] < 0.2, "Minimal material should have low completeness"
        
        # Most masks should be 0 (imputed)
        low_confidence_count = sum(1 for m in mask if m == 0)
        assert low_confidence_count >= 5
    
    def test_film_formation_feature(self, extractor, complete_resin):
        """Test that film formation is derived from OH, MW, solid content."""
        fp, mask = extractor.extract(complete_resin)
        
        film_idx = extractor.FEATURE_NAMES.index('film_formation')
        
        # High OH (120) + high MW (5000) + high solid (70%) should give high film formation
        assert fp[film_idx] > 0.5
        assert mask[film_idx] == 1.0  # High confidence with 3 inputs
    
    def test_voc_risk_solvent(self, extractor, solvent):
        """Test VOC risk for a solvent."""
        fp, mask = extractor.extract(solvent)
        
        voc_idx = extractor.FEATURE_NAMES.index('voc_risk')
        
        # Solvent with 0 solid content should have high VOC risk
        assert fp[voc_idx] > 0.8
        assert mask[voc_idx] == 1.0  # Direct VOC measurement available
    
    def test_opacity_pigment(self, extractor, pigment):
        """Test opacity contribution for a pigment."""
        fp, mask = extractor.extract(pigment)
        
        opacity_idx = extractor.FEATURE_NAMES.index('opacity_contribution')
        
        # TiO2 with RI=2.73 and optimal particle size should have high opacity
        assert fp[opacity_idx] > 0.7
        assert mask[opacity_idx] == 1.0
    
    def test_drying_speed_solvent(self, extractor, solvent):
        """Test drying speed for a solvent."""
        fp, mask = extractor.extract(solvent)
        
        drying_idx = extractor.FEATURE_NAMES.index('drying_speed')
        
        # Xylene with evap rate 0.7 is on the lower end of 0.01-10 scale
        # So normalized value will be relatively low (around 0.07)
        assert fp[drying_idx] >= 0, "Drying speed should be non-negative"
        assert fp[drying_idx] <= 1, "Drying speed should be normalized"
        assert mask[drying_idx] == 1.0, "Should have full confidence with evap rate data"
    
    def test_extract_with_metadata(self, extractor, complete_resin):
        """Test extract_with_metadata returns proper FingerprintResult."""
        result = extractor.extract_with_metadata(complete_resin)
        
        assert isinstance(result, FingerprintResult)
        assert result.material_id == 1
        assert result.material_name == 'Polyester Resin A'
        assert len(result.feature_names) == extractor.FINGERPRINT_DIMS
        
        # Test to_dict
        result_dict = result.to_dict()
        assert 'fingerprint' in result_dict
        assert 'features' in result_dict
        assert 'overall_completeness' in result_dict
    
    def test_feature_names(self, extractor):
        """Test that feature names are consistent."""
        names = extractor.get_feature_names()
        
        assert len(names) == extractor.FINGERPRINT_DIMS
        assert 'film_formation' in names
        assert 'completeness' in names
        assert 'voc_risk' in names
    
    def test_feature_descriptions(self, extractor):
        """Test that all features have descriptions."""
        descriptions = extractor.get_feature_descriptions()
        names = extractor.get_feature_names()
        
        for name in names:
            assert name in descriptions, f"Missing description for {name}"
            assert len(descriptions[name]) > 10, f"Description too short for {name}"
    
    def test_explain_feature(self, extractor, complete_resin):
        """Test feature explanation generation."""
        # Test film formation explanation
        explanation = extractor.explain_feature(0, complete_resin)
        assert 'Film formation' in explanation
        assert 'OH value=120' in explanation or 'OH' in explanation
        
        # Test completeness explanation
        completeness_idx = extractor.FEATURE_NAMES.index('completeness')
        explanation = extractor.explain_feature(completeness_idx, complete_resin)
        assert 'Completeness' in explanation
    
    def test_normalization_range(self, extractor):
        """Test that normalization handles edge cases."""
        # Test with extreme values
        extreme_material = {
            'oh_value': 1000,  # Way above normal
            'glass_transition': -100,  # Way below normal
        }
        
        fp, mask = extractor.extract(extreme_material)
        
        # Values should still be clipped to 0-1
        for val in fp:
            assert 0 <= val <= 1
    
    def test_polarity_calculation(self, extractor, complete_resin, solvent):
        """Test polarity is calculated from Hansen parameters."""
        resin_fp, resin_mask = extractor.extract(complete_resin)
        solvent_fp, solvent_mask = extractor.extract(solvent)
        
        polarity_idx = extractor.FEATURE_NAMES.index('polarity')
        
        # Resin with hansen_p=8, hansen_h=5 should be more polar than
        # solvent with hansen_p=1, hansen_h=3
        assert resin_fp[polarity_idx] > solvent_fp[polarity_idx]


class TestEnhancedRecipeTransformer:
    """Tests for EnhancedRecipeTransformer."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager for testing."""
        class MockDB:
            def __init__(self):
                self.materials = {
                    'RESIN-001': {
                        'id': 1,
                        'name': 'Polyester Resin',
                        'category': 'resin',
                        'oh_value': 100,
                        'glass_transition': 40,
                        'solid_content': 70,
                        'unit_price': 12.0,
                    },
                    'PIGMENT-001': {
                        'id': 2,
                        'name': 'TiO2',
                        'category': 'pigment',
                        'density': 4.2,
                        'refractive_index': 2.73,
                        'unit_price': 3.5,
                    },
                    'SOLVENT-001': {
                        'id': 3,
                        'name': 'Xylene',
                        'category': 'solvent',
                        'solid_content': 0,
                        'evaporation_rate': 0.7,
                        'unit_price': 1.5,
                    },
                }
            
            def get_material_by_code_or_name(self, code):
                return self.materials.get(code)
        
        return MockDB()
    
    @pytest.fixture
    def transformer(self, mock_db_manager):
        from src.ml_engine.enhanced_recipe_transformer import EnhancedRecipeTransformer
        extractor = MaterialFeatureExtractor()
        return EnhancedRecipeTransformer(extractor, mock_db_manager)
    
    @pytest.fixture
    def sample_recipe(self):
        return [
            {'material_code': 'RESIN-001', 'percentage': 30},
            {'material_code': 'PIGMENT-001', 'percentage': 20},
            {'material_code': 'SOLVENT-001', 'percentage': 50},
        ]
    
    def test_transform_basic(self, transformer, sample_recipe):
        """Test basic recipe transformation."""
        vector, mask, metadata = transformer.transform(sample_recipe)
        
        assert len(vector) == 14  # FINGERPRINT_DIMS
        assert len(mask) == 14
        
        # All values should be in valid range
        for val in vector:
            assert 0 <= val <= 1
        
        # Metadata should have key formulation properties
        assert 'binder_ratio' in metadata
        assert 'solvent_ratio' in metadata
        assert 'pigment_binder_ratio' in metadata
    
    def test_metadata_calculation(self, transformer, sample_recipe):
        """Test that metadata is calculated correctly."""
        vector, mask, metadata = transformer.transform(sample_recipe)
        
        # With 30% binder, 20% pigment, 50% solvent
        assert abs(metadata['binder_ratio'] - 0.3) < 0.01
        assert abs(metadata['solvent_ratio'] - 0.5) < 0.01
        assert abs(metadata['pigment_ratio'] - 0.2) < 0.01
        
        # P/B ratio = 20/30 = 0.667
        assert abs(metadata['pigment_binder_ratio'] - 0.667) < 0.01
        
        # Solid content est = 1 - 0.5 = 0.5
        assert abs(metadata['solid_content_est'] - 0.5) < 0.01
    
    def test_empty_recipe(self, transformer):
        """Test handling of empty recipe."""
        vector, mask, metadata = transformer.transform([])
        
        assert all(v == 0 for v in vector)
        assert all(m == 0 for m in mask)
        assert metadata == {}
    
    def test_missing_material(self, transformer):
        """Test handling of unknown materials."""
        recipe = [
            {'material_code': 'UNKNOWN-001', 'percentage': 50},
            {'material_code': 'RESIN-001', 'percentage': 50},
        ]
        
        vector, mask, metadata = transformer.transform(recipe)
        
        # Should still produce valid output
        assert len(vector) == 14
        assert metadata['material_count'] == 2
    
    def test_transform_with_breakdown(self, transformer, sample_recipe):
        """Test transformation with full breakdown."""
        result = transformer.transform_with_breakdown(sample_recipe)
        
        assert len(result.vector) == 14
        assert len(result.material_breakdown) == 3
        
        # Check breakdown has expected structure
        for mat in result.material_breakdown:
            assert 'code' in mat
            assert 'percentage' in mat
            assert 'category' in mat
            assert 'status' in mat
    
    def test_compare_recipes(self, transformer):
        """Test recipe comparison."""
        recipe1 = [
            {'material_code': 'RESIN-001', 'percentage': 40},
            {'material_code': 'SOLVENT-001', 'percentage': 60},
        ]
        recipe2 = [
            {'material_code': 'RESIN-001', 'percentage': 35},
            {'material_code': 'SOLVENT-001', 'percentage': 65},
        ]
        
        comparison = transformer.compare_recipes(recipe1, recipe2)
        
        assert 'similarity' in comparison
        assert 0 <= comparison['similarity'] <= 1
        assert 'metadata_differences' in comparison
        
        # Similar recipes should have high similarity
        assert comparison['similarity'] > 0.9


class TestMaterialSimilarityEngine:
    """Tests for enhanced MaterialSimilarityEngine."""
    
    @pytest.fixture
    def mock_db_for_similarity(self):
        """Mock database for similarity testing."""
        class MockDB:
            def get_complete_materials(self):
                return [
                    {
                        'id': 1,
                        'name': 'Polyester A',
                        'category': 'resin',
                        'hansen_d': 18,
                        'hansen_p': 8,
                        'hansen_h': 5,
                        'density': 1.1,
                        'solid_content': 70,
                        'oh_value': 100,
                        'glass_transition': 40,
                    },
                    {
                        'id': 2,
                        'name': 'Polyester B',
                        'category': 'resin',
                        'hansen_d': 18.5,
                        'hansen_p': 7.5,
                        'hansen_h': 5.5,
                        'density': 1.15,
                        'solid_content': 65,
                        'oh_value': 110,
                        'glass_transition': 42,
                    },
                    {
                        'id': 3,
                        'name': 'Epoxy Resin',
                        'category': 'resin',
                        'hansen_d': 20,
                        'hansen_p': 12,
                        'hansen_h': 10,
                        'density': 1.2,
                        'solid_content': 75,
                        'oh_value': 180,
                        'glass_transition': 55,
                    },
                ]
            
            def get_all_materials(self):
                return self.get_complete_materials()
            
            def get_connection(self):
                import contextlib
                @contextlib.contextmanager
                def mock_conn():
                    yield MockCursor()
                return mock_conn()
        
        class MockCursor:
            def execute(self, *args):
                pass
            def fetchone(self):
                return None
            def fetchall(self):
                return []
        
        return MockDB()
    
    @pytest.fixture
    def similarity_engine(self, mock_db_for_similarity):
        from src.data_handlers.material_similarity import MaterialSimilarityEngine
        engine = MaterialSimilarityEngine(mock_db_for_similarity)
        engine.build_index()
        return engine
    
    def test_build_index(self, similarity_engine):
        """Test index building."""
        assert len(similarity_engine._vectors) == 3
        assert len(similarity_engine._id_to_idx) == 3
    
    def test_find_similar(self, similarity_engine):
        """Test basic similarity search."""
        similar = similarity_engine.find_similar(1, top_k=2)
        
        assert len(similar) == 2
        # Polyester B should be most similar to Polyester A
        assert similar[0][0] == 2  # material_id of Polyester B
    
    def test_find_similar_with_explanation(self, similarity_engine):
        """Test explainable similarity search."""
        results = similarity_engine.find_similar_with_explanation(1, top_k=2)
        
        assert len(results) == 2
        
        for result in results:
            assert 'material_id' in result
            assert 'explanation' in result
            assert 'matching_features' in result
            assert 'diverging_features' in result
            assert len(result['explanation']) > 0
    
    def test_explain_similarity_detail(self, similarity_engine):
        """Test detailed similarity explanation."""
        detail = similarity_engine.explain_similarity_detail(1, 2)
        
        assert detail is not None
        assert 'metrics' in detail
        assert 'cosine_similarity' in detail['metrics']
        assert 'explanation' in detail
        assert 'compatibility_assessment' in detail
    
    def test_get_material_profile(self, similarity_engine):
        """Test material profile retrieval."""
        profile = similarity_engine.get_material_profile(1)
        
        assert profile is not None
        assert profile['name'] == 'Polyester A'
        assert 'features' in profile


# Run tests if executed directly
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
