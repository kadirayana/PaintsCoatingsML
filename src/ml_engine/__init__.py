"""
Paint Formulation AI - ML Engine Package
========================================

Provides machine learning capabilities for paint formulation:
- Feature engineering (PVC, solid content, mixture properties)
- XGBoost multi-output prediction
- Recipe optimization (inverse design)
"""

from .router import MLRouter
from .local_models import LocalMLModel, FormulationOptimizer
from .feature_engineer import FeatureEngineer
from .xgboost_predictor import XGBoostPredictor, predict_properties, train_model
from .recipe_optimizer import RecipeOptimizer, optimize_recipe

__all__ = [
    # Legacy
    'MLRouter',
    'LocalMLModel',
    'FormulationOptimizer',
    
    # New ML Pipeline
    'FeatureEngineer',
    'XGBoostPredictor',
    'RecipeOptimizer',
    
    # Convenience functions
    'predict_properties',
    'train_model',
    'optimize_recipe',
]

