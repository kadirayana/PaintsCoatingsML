"""
Paint Formulation AI - XGBoost Multi-Output Predictor
======================================================
XGBoost-based multi-output regression for paint property prediction.

Predicts multiple properties simultaneously:
- Viscosity, Gloss, Opacity
- Adhesion, Hardness, Flexibility
- Quality scores

Uses MultiOutputRegressor wrapper for simultaneous prediction.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import warnings

import numpy as np

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class XGBoostPredictor:
    """
    XGBoost-based multi-output regression for paint properties.
    
    This predictor uses scikit-learn's MultiOutputRegressor to wrap
    XGBRegressor for simultaneous prediction of multiple targets.
    
    Model is persisted to disk and loaded automatically on startup.
    """
    
    # Target columns to predict
    TARGET_COLUMNS = [
        'viscosity',
        'gloss',
        'opacity',
        'quality_score',
        'adhesion',
        'hardness',
        'flexibility',
        'corrosion_resistance',
        'chemical_resistance',
        'abrasion_resistance',
    ]
    
    # Minimum samples required for training
    MIN_TRAINING_SAMPLES = 5
    
    # Default XGBoost hyperparameters
    DEFAULT_PARAMS = {
        'n_estimators': 100,
        'max_depth': 5,
        'learning_rate': 0.1,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'min_child_weight': 3,
        'reg_alpha': 0.1,
        'reg_lambda': 1.0,
        'random_state': 42,
        'n_jobs': -1,
    }
    
    def __init__(self, model_dir: str = None, material_lookup: callable = None):
        """
        Initialize the XGBoost predictor.
        
        Args:
            model_dir: Directory to save/load models
            material_lookup: Callback to fetch material properties from database
        """
        self.model_dir = model_dir or 'assets/models'
        self.model_path = os.path.join(self.model_dir, 'xgboost_multioutput.pkl')
        
        self.model = None
        self.scaler = None
        self.feature_names = []
        self.target_names = []
        self.training_info = {}
        
        # Feature engineer
        from src.ml_engine.feature_engineer import FeatureEngineer
        self.feature_engineer = FeatureEngineer(material_lookup=material_lookup)
        
        # Recipe transformer for additional features
        from src.ml_engine.recipe_transformer import RecipeTransformer
        self.recipe_transformer = RecipeTransformer()
        
        # Try to load existing model
        self._load_model()
    
    def train_model(
        self,
        training_data: List[Dict],
        xgb_params: Dict = None,
        target_columns: List[str] = None
    ) -> Dict:
        """
        Train the XGBoost multi-output model.
        
        Args:
            training_data: List of formulations with test results.
                Each dict should contain:
                - 'components': list of ingredients
                - Target values: 'viscosity', 'gloss', etc.
            xgb_params: Optional XGBoost hyperparameters
            target_columns: Optional list of targets to predict
            
        Returns:
            Training results with metrics
        """
        try:
            from xgboost import XGBRegressor
            from sklearn.multioutput import MultiOutputRegressor
            from sklearn.preprocessing import StandardScaler
            from sklearn.model_selection import cross_val_score
        except ImportError as e:
            logger.error(f"Missing dependency: {e}")
            return {
                'success': False,
                'message': f'Missing dependency: {e}. Install with: pip install xgboost scikit-learn'
            }
        
        if len(training_data) < self.MIN_TRAINING_SAMPLES:
            return {
                'success': False,
                'message': f'Need at least {self.MIN_TRAINING_SAMPLES} samples. Got: {len(training_data)}',
                'samples': len(training_data)
            }
        
        logger.info(f"Starting XGBoost training with {len(training_data)} samples")
        
        # Determine target columns
        self.target_names = target_columns or self.TARGET_COLUMNS
        
        # Prepare training data
        X, y_dict = self._prepare_training_data(training_data)
        
        if X is None or len(X) < self.MIN_TRAINING_SAMPLES:
            return {
                'success': False,
                'message': 'Insufficient valid data after preprocessing',
                'samples': len(X) if X is not None else 0
            }
        
        # Filter targets with sufficient data
        valid_targets = []
        y_columns = []
        
        for target in self.target_names:
            if target in y_dict:
                y_arr = np.array(y_dict[target])
                valid_mask = ~np.isnan(y_arr)
                if valid_mask.sum() >= self.MIN_TRAINING_SAMPLES:
                    valid_targets.append(target)
                    y_columns.append(y_arr)
        
        if not valid_targets:
            return {
                'success': False,
                'message': 'No targets have sufficient valid data',
                'samples': len(X)
            }
        
        # Stack targets
        y = np.column_stack(y_columns)
        self.target_names = valid_targets
        
        # Handle missing values in y (use column mean)
        for i in range(y.shape[1]):
            col = y[:, i]
            mask = np.isnan(col)
            if mask.any():
                col[mask] = np.nanmean(col)
        
        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Create XGBoost model
        params = {**self.DEFAULT_PARAMS, **(xgb_params or {})}
        
        base_model = XGBRegressor(**params)
        self.model = MultiOutputRegressor(base_model)
        
        # Train
        logger.info(f"Training multi-output model for {len(valid_targets)} targets...")
        self.model.fit(X_scaled, y)
        
        # Calculate metrics
        metrics = self._calculate_metrics(X_scaled, y, valid_targets)
        
        # Store training info
        self.training_info = {
            'date': datetime.now().isoformat(),
            'samples': len(X),
            'targets': valid_targets,
            'feature_count': X.shape[1],
            'metrics': metrics
        }
        
        # Save model
        self._save_model()
        
        logger.info(f"Training complete. Targets: {valid_targets}")
        
        return {
            'success': True,
            'samples': len(X),
            'targets': valid_targets,
            'metrics': metrics,
            'feature_importance': self._get_feature_importance()
        }
    
    def predict_properties(self, formulation: Dict) -> Dict:
        """
        Predict properties for a formulation.
        
        Args:
            formulation: Dictionary with 'components' list
            
        Returns:
            Dictionary of predicted properties
        """
        if self.model is None:
            return {'success': False, 'message': 'Model not trained'}
        
        try:
            # Engineer features
            features = self._extract_features(formulation)
            
            if features is None:
                return {'success': False, 'message': 'Could not extract features'}
            
            # Scale
            features_scaled = self.scaler.transform([features])
            
            # Predict
            predictions = self.model.predict(features_scaled)[0]
            
            # Build result dictionary
            result = {
                'success': True,
                'predictions': {}
            }
            
            for i, target in enumerate(self.target_names):
                result['predictions'][target] = round(float(predictions[i]), 2)
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {'success': False, 'message': str(e)}
    
    def _extract_features(self, formulation: Dict) -> Optional[np.ndarray]:
        """
        Extract all features from a formulation.
        
        Combines:
        1. FeatureEngineer features (PVC, solid content, etc.)
        2. RecipeTransformer features (weighted properties)
        3. Additional input parameters (coating_thickness, etc.)
        """
        components = formulation.get('components', [])
        
        if not components:
            return None
        
        # Get mixture features from FeatureEngineer
        mixture_features = self.feature_engineer.engineer_features(formulation)
        
        # Get recipe features from RecipeTransformer
        recipe_features = np.array(self.recipe_transformer.transform(components))
        
        # Additional parameters
        extra_features = np.array([
            float(formulation.get('coating_thickness', 50) or 50),
            float(formulation.get('target_viscosity', 2000) or 2000),
        ])
        
        # Combine all features
        all_features = np.concatenate([mixture_features, recipe_features, extra_features])
        
        return all_features
    
    def _prepare_training_data(self, data: List[Dict]) -> Tuple[Optional[np.ndarray], Dict]:
        """
        Prepare training data from formulation dictionaries.
        """
        X = []
        y_dict = {target: [] for target in self.target_names}
        
        for item in data:
            # Extract features
            features = self._extract_features(item)
            
            if features is None:
                continue
            
            X.append(features)
            
            # Extract targets
            for target in self.target_names:
                value = item.get(target)
                if value is not None:
                    try:
                        y_dict[target].append(float(value))
                    except (ValueError, TypeError):
                        y_dict[target].append(np.nan)
                else:
                    y_dict[target].append(np.nan)
        
        if not X:
            return None, y_dict
        
        X = np.array(X)
        
        # Store feature names
        self.feature_names = (
            self.feature_engineer.get_feature_names() +
            self.recipe_transformer.get_feature_names() +
            ['coating_thickness', 'target_viscosity']
        )
        
        return X, y_dict
    
    def _calculate_metrics(self, X: np.ndarray, y: np.ndarray, targets: List[str]) -> Dict:
        """Calculate training metrics for each target."""
        from sklearn.model_selection import cross_val_score
        
        metrics = {}
        
        # Calculate R² for each target using the fitted estimators
        for i, (target, estimator) in enumerate(zip(targets, self.model.estimators_)):
            try:
                y_target = y[:, i]
                
                # R² score
                r2 = estimator.score(X, y_target)
                
                # Cross-validation R² (if enough samples)
                if len(X) >= 5:
                    cv_folds = min(5, len(X))
                    cv_scores = cross_val_score(estimator, X, y_target, cv=cv_folds, scoring='r2')
                    cv_r2 = cv_scores.mean()
                else:
                    cv_r2 = r2
                
                metrics[target] = {
                    'r2_score': round(r2, 3),
                    'cv_r2_score': round(cv_r2, 3),
                    'valid_samples': int((~np.isnan(y_target)).sum())
                }
            except Exception as e:
                logger.warning(f"Could not calculate metrics for {target}: {e}")
                metrics[target] = {'r2_score': 0, 'cv_r2_score': 0}
        
        return metrics
    
    def _get_feature_importance(self) -> Dict[str, Dict[str, float]]:
        """Get feature importance for each target."""
        if self.model is None or not hasattr(self.model, 'estimators_'):
            return {}
        
        importance = {}
        
        for target, estimator in zip(self.target_names, self.model.estimators_):
            if hasattr(estimator, 'feature_importances_'):
                imp = estimator.feature_importances_
                
                # Get top 10 most important features
                indices = np.argsort(imp)[::-1][:10]
                
                importance[target] = {
                    self.feature_names[i]: round(float(imp[i]), 4)
                    for i in indices if i < len(self.feature_names)
                }
        
        return importance
    
    def _save_model(self):
        """Save model to disk."""
        try:
            import joblib
        except ImportError:
            import pickle as joblib
        
        os.makedirs(self.model_dir, exist_ok=True)
        
        data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'target_names': self.target_names,
            'training_info': self.training_info
        }
        
        try:
            joblib.dump(data, self.model_path)
            logger.info(f"Model saved to {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
    
    def _load_model(self):
        """Load model from disk."""
        if not os.path.exists(self.model_path):
            return
        
        try:
            try:
                import joblib
            except ImportError:
                import pickle as joblib
            
            data = joblib.load(self.model_path)
            
            self.model = data.get('model')
            self.scaler = data.get('scaler')
            self.feature_names = data.get('feature_names', [])
            self.target_names = data.get('target_names', [])
            self.training_info = data.get('training_info', {})
            
            logger.info(f"Model loaded from {self.model_path}")
            logger.info(f"Targets: {self.target_names}")
            
        except Exception as e:
            logger.warning(f"Could not load model: {e}")
    
    def get_model_status(self) -> Dict:
        """Get current model status and training info."""
        return {
            'trained': self.model is not None,
            'targets': self.target_names,
            'feature_count': len(self.feature_names),
            'training_info': self.training_info
        }
    
    def is_trained(self) -> bool:
        """Check if model is trained and ready."""
        return self.model is not None


# =============================================================================
# Convenience Functions
# =============================================================================

_predictor_instance: Optional[XGBoostPredictor] = None


def get_predictor(model_dir: str = None, material_lookup: callable = None) -> XGBoostPredictor:
    """
    Get or create a singleton XGBoostPredictor instance.
    
    Args:
        model_dir: Model directory path
        material_lookup: Material lookup callback
        
    Returns:
        XGBoostPredictor instance
    """
    global _predictor_instance
    
    if _predictor_instance is None:
        _predictor_instance = XGBoostPredictor(
            model_dir=model_dir,
            material_lookup=material_lookup
        )
    
    return _predictor_instance


def predict_properties(formulation_dict: Dict) -> Dict:
    """
    Convenience function to predict properties for a formulation.
    
    Args:
        formulation_dict: {
            'components': [
                {'code': 'MAT001', 'amount': 100, 'category': 'binder', 
                 'density': 1.2, 'solid_content': 100, ...},
                ...
            ],
            'coating_thickness': 50  # optional
        }
        
    Returns:
        {
            'success': True/False,
            'predictions': {'viscosity': 2500.0, 'gloss': 85.0, ...},
            'message': '...'  # if error
        }
    """
    predictor = get_predictor()
    return predictor.predict_properties(formulation_dict)


def train_model(training_data: List[Dict], **kwargs) -> Dict:
    """
    Convenience function to train the model.
    
    Args:
        training_data: List of formulations with test results
        **kwargs: Additional training parameters
        
    Returns:
        Training results
    """
    predictor = get_predictor()
    return predictor.train_model(training_data, **kwargs)
