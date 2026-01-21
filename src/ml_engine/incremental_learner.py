"""
Incremental Learner - Safe, Versioned Continuous Learning
=========================================================
Implements safe model retraining with versioning and rollback capabilities.

Key Features:
- Only retrains when enough new validated samples are available
- Validates new model is better than current before deploying
- Full version history with rollback support
- Thread-safe operation for background training

Safety Mechanisms:
- Minimum sample threshold before retraining
- Minimum R² improvement requirement
- Version comparison before deployment
- Human validation integration points

Usage:
    from src.ml_engine.incremental_learner import IncrementalLearner
    
    learner = IncrementalLearner(model_dir='data_storage/models')
    
    # Check if retraining is warranted
    should_train, reason = learner.should_retrain('viscosity')
    
    # Train with validation
    result = learner.train_with_validation('viscosity', training_data)
    
    # Rollback if needed
    learner.rollback('viscosity', 'v001')
"""

import os
import json
import pickle
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import threading

logger = logging.getLogger(__name__)

# Try to import scikit-learn
try:
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logger.warning("scikit-learn not available. Training will be disabled.")

# Try numpy
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


@dataclass
class ModelVersion:
    """Represents a single model version."""
    version_id: str           # e.g., 'v001'
    target: str              # e.g., 'viscosity'
    created_at: str          # ISO timestamp
    r2_score: float          # Cross-validated R² score
    samples_count: int       # Number of training samples
    model_path: str          # Path to pickle file
    is_active: bool          # Currently deployed?
    training_data_hash: str  # Hash of training data for tracking
    metadata: Dict = None    # Additional info
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TrainingResult:
    """Result of a training operation."""
    status: str              # 'deployed', 'skipped', 'failed'
    version: Optional[str]   # Version ID if deployed
    r2_score: float         # New model's R² (or 0 if failed)
    previous_r2: float      # Previous model's R² (or 0)
    improvement: float      # R² improvement (can be negative)
    samples_count: int
    reason: str             # Human-readable explanation
    
    def to_dict(self) -> Dict:
        return asdict(self)


class IncrementalLearner:
    """
    Safe, versioned continuous learning for formulation models.
    
    Philosophy:
    - Never auto-deploy a model that performs worse
    - Keep version history for audit and rollback
    - Require minimum evidence before retraining
    - Support multiple targets (viscosity, gloss, hardness, etc.)
    """
    
    # Configuration
    MIN_NEW_SAMPLES = 5       # Minimum new samples to trigger retraining
    MIN_R2_IMPROVEMENT = 0.01 # Minimum R² improvement to deploy (1%)
    MIN_TOTAL_SAMPLES = 10    # Minimum samples for any model
    MAX_VERSIONS = 10         # Maximum versions to keep per target
    
    def __init__(self, model_dir: str = None):
        """
        Initialize the incremental learner.
        
        Args:
            model_dir: Directory for storing models and registry.
                      Defaults to 'data_storage/models'
        """
        if model_dir is None:
            # Default to data_storage/models relative to project root
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            model_dir = os.path.join(base_dir, 'data_storage', 'models')
        
        self.model_dir = model_dir
        self.registry_path = os.path.join(model_dir, 'model_registry.json')
        self._lock = threading.Lock()
        
        # Ensure directory exists
        os.makedirs(model_dir, exist_ok=True)
        
        # Load registry
        self._registry: Dict[str, List[ModelVersion]] = {}
        self._load_registry()
        
        # In-memory model cache
        self._model_cache: Dict[str, Any] = {}
        self._scaler_cache: Dict[str, StandardScaler] = {}
    
    def _load_registry(self):
        """Load model registry from disk."""
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, 'r') as f:
                    data = json.load(f)
                    for target, versions in data.items():
                        self._registry[target] = [
                            ModelVersion(**v) for v in versions
                        ]
                logger.info(f"Loaded model registry with {len(self._registry)} targets")
            except Exception as e:
                logger.error(f"Failed to load model registry: {e}")
                self._registry = {}
        else:
            self._registry = {}
    
    def _save_registry(self):
        """Save model registry to disk."""
        try:
            data = {
                target: [v.to_dict() for v in versions]
                for target, versions in self._registry.items()
            }
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save model registry: {e}")
    
    def get_active_model(self, target: str) -> Optional[ModelVersion]:
        """
        Get the currently active model for a target.
        
        Args:
            target: Target variable name (e.g., 'viscosity')
            
        Returns:
            Active ModelVersion or None
        """
        versions = self._registry.get(target, [])
        for v in versions:
            if v.is_active:
                return v
        return None
    
    def get_version_history(self, target: str) -> List[ModelVersion]:
        """
        Get all versions for a target, sorted by creation date (newest first).
        
        Args:
            target: Target variable name
            
        Returns:
            List of ModelVersion objects
        """
        versions = self._registry.get(target, [])
        return sorted(versions, key=lambda v: v.created_at, reverse=True)
    
    def should_retrain(self, target: str, new_sample_count: int = None) -> Tuple[bool, str]:
        """
        Check if retraining is warranted for a target.
        
        Args:
            target: Target variable name
            new_sample_count: Optional count of new samples since last training
            
        Returns:
            (should_retrain, reason) tuple
        """
        current = self.get_active_model(target)
        
        if current is None:
            if new_sample_count and new_sample_count >= self.MIN_TOTAL_SAMPLES:
                return True, f"No existing model. {new_sample_count} samples available."
            elif new_sample_count:
                return False, f"Need at least {self.MIN_TOTAL_SAMPLES} samples (have {new_sample_count})."
            return True, "No existing model for this target."
        
        if new_sample_count is None:
            return False, "Cannot determine new sample count."
        
        if new_sample_count < self.MIN_NEW_SAMPLES:
            return False, f"Only {new_sample_count} new samples (need {self.MIN_NEW_SAMPLES})."
        
        return True, f"{new_sample_count} new validated samples available."
    
    def train_with_validation(
        self, 
        target: str, 
        X: List[List[float]], 
        y: List[float],
        force: bool = False
    ) -> TrainingResult:
        """
        Train a new model with safety validation.
        
        Only deploys if the new model is better than the current one.
        
        Args:
            target: Target variable name
            X: Feature matrix (list of feature vectors)
            y: Target values
            force: If True, deploy even without improvement
            
        Returns:
            TrainingResult with status and details
        """
        if not HAS_SKLEARN:
            return TrainingResult(
                status='failed',
                version=None,
                r2_score=0,
                previous_r2=0,
                improvement=0,
                samples_count=len(y) if y else 0,
                reason="scikit-learn not available"
            )
        
        if not X or not y or len(X) != len(y):
            return TrainingResult(
                status='failed',
                version=None,
                r2_score=0,
                previous_r2=0,
                improvement=0,
                samples_count=0,
                reason="Invalid training data"
            )
        
        if len(X) < self.MIN_TOTAL_SAMPLES:
            return TrainingResult(
                status='skipped',
                version=None,
                r2_score=0,
                previous_r2=0,
                improvement=0,
                samples_count=len(y),
                reason=f"Not enough samples ({len(y)}/{self.MIN_TOTAL_SAMPLES})"
            )
        
        with self._lock:
            try:
                # Convert to numpy
                X_arr = np.array(X)
                y_arr = np.array(y)
                
                # Scale features
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X_arr)
                
                # Train model (Gradient Boosting is good for small datasets)
                model = GradientBoostingRegressor(
                    n_estimators=100,
                    max_depth=3,
                    learning_rate=0.1,
                    random_state=42
                )
                
                # Cross-validation score
                cv_folds = min(5, len(y))
                scores = cross_val_score(model, X_scaled, y_arr, cv=cv_folds, scoring='r2')
                new_r2 = float(np.mean(scores))
                
                # Compare with current
                current = self.get_active_model(target)
                previous_r2 = current.r2_score if current else 0
                improvement = new_r2 - previous_r2
                
                # Check if should deploy
                if not force and current and improvement < self.MIN_R2_IMPROVEMENT:
                    return TrainingResult(
                        status='skipped',
                        version=None,
                        r2_score=new_r2,
                        previous_r2=previous_r2,
                        improvement=improvement,
                        samples_count=len(y),
                        reason=f"No improvement (Δ={improvement:.3f}, need >{self.MIN_R2_IMPROVEMENT})"
                    )
                
                # Fit final model on all data
                model.fit(X_scaled, y_arr)
                
                # Generate version ID
                version_id = self._generate_version_id(target)
                
                # Save model
                model_path = self._save_model(target, version_id, model, scaler)
                
                # Calculate data hash
                data_hash = self._hash_data(X, y)
                
                # Create version record
                version = ModelVersion(
                    version_id=version_id,
                    target=target,
                    created_at=datetime.now().isoformat(),
                    r2_score=new_r2,
                    samples_count=len(y),
                    model_path=model_path,
                    is_active=True,
                    training_data_hash=data_hash,
                    metadata={
                        'cv_folds': cv_folds,
                        'cv_std': float(np.std(scores)),
                    }
                )
                
                # Deactivate previous
                if current:
                    current.is_active = False
                
                # Add to registry
                if target not in self._registry:
                    self._registry[target] = []
                self._registry[target].append(version)
                
                # Cleanup old versions
                self._cleanup_old_versions(target)
                
                # Save registry
                self._save_registry()
                
                # Update cache
                self._model_cache[target] = model
                self._scaler_cache[target] = scaler
                
                logger.info(f"Deployed model {version_id} for {target} (R²={new_r2:.3f})")
                
                return TrainingResult(
                    status='deployed',
                    version=version_id,
                    r2_score=new_r2,
                    previous_r2=previous_r2,
                    improvement=improvement,
                    samples_count=len(y),
                    reason=f"Model improved by {improvement:.3f}"
                )
                
            except Exception as e:
                logger.error(f"Training failed for {target}: {e}")
                return TrainingResult(
                    status='failed',
                    version=None,
                    r2_score=0,
                    previous_r2=0,
                    improvement=0,
                    samples_count=len(y) if y else 0,
                    reason=str(e)
                )
    
    def predict(self, target: str, X: List[List[float]]) -> Tuple[List[float], float]:
        """
        Make predictions using the active model.
        
        Args:
            target: Target variable name
            X: Feature matrix
            
        Returns:
            (predictions, confidence) where confidence is the training R²
        """
        if not HAS_SKLEARN:
            return [0.0] * len(X), 0.0
        
        model = self._get_model(target)
        scaler = self._scaler_cache.get(target)
        
        if model is None:
            logger.warning(f"No model available for {target}")
            return [0.0] * len(X), 0.0
        
        try:
            X_arr = np.array(X)
            if scaler:
                X_scaled = scaler.transform(X_arr)
            else:
                X_scaled = X_arr
            
            predictions = model.predict(X_scaled).tolist()
            
            # Get R² as confidence
            active = self.get_active_model(target)
            confidence = active.r2_score if active else 0.5
            
            return predictions, confidence
            
        except Exception as e:
            logger.error(f"Prediction failed for {target}: {e}")
            return [0.0] * len(X), 0.0
    
    def rollback(self, target: str, version_id: str) -> bool:
        """
        Rollback to a previous model version.
        
        Args:
            target: Target variable name
            version_id: Version to rollback to
            
        Returns:
            True if successful
        """
        with self._lock:
            versions = self._registry.get(target, [])
            
            target_version = None
            for v in versions:
                if v.version_id == version_id:
                    target_version = v
                elif v.is_active:
                    v.is_active = False
            
            if target_version is None:
                logger.error(f"Version {version_id} not found for {target}")
                return False
            
            target_version.is_active = True
            self._save_registry()
            
            # Clear cache to force reload
            self._model_cache.pop(target, None)
            self._scaler_cache.pop(target, None)
            
            logger.info(f"Rolled back {target} to {version_id}")
            return True
    
    def get_status(self) -> Dict:
        """
        Get overall status of all models.
        
        Returns:
            Dict with status per target
        """
        status = {}
        for target, versions in self._registry.items():
            active = next((v for v in versions if v.is_active), None)
            status[target] = {
                'has_model': active is not None,
                'active_version': active.version_id if active else None,
                'r2_score': active.r2_score if active else None,
                'samples': active.samples_count if active else 0,
                'last_trained': active.created_at if active else None,
                'version_count': len(versions),
            }
        return status
    
    def _get_model(self, target: str) -> Any:
        """Get model from cache or load from disk."""
        if target in self._model_cache:
            return self._model_cache[target]
        
        active = self.get_active_model(target)
        if not active:
            return None
        
        try:
            model_path = active.model_path
            if not os.path.isabs(model_path):
                model_path = os.path.join(self.model_dir, model_path)
            
            with open(model_path, 'rb') as f:
                data = pickle.load(f)
                self._model_cache[target] = data['model']
                if 'scaler' in data:
                    self._scaler_cache[target] = data['scaler']
                return data['model']
        except Exception as e:
            logger.error(f"Failed to load model for {target}: {e}")
            return None
    
    def _save_model(self, target: str, version_id: str, model: Any, scaler: StandardScaler) -> str:
        """Save model to disk."""
        filename = f"{version_id}_{target}.pkl"
        filepath = os.path.join(self.model_dir, filename)
        
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': model,
                'scaler': scaler,
                'target': target,
                'version': version_id,
            }, f)
        
        return filename
    
    def _generate_version_id(self, target: str) -> str:
        """Generate next version ID for a target."""
        versions = self._registry.get(target, [])
        if not versions:
            return 'v001'
        
        # Find highest version number
        max_num = 0
        for v in versions:
            try:
                num = int(v.version_id[1:])
                max_num = max(max_num, num)
            except:
                pass
        
        return f"v{max_num + 1:03d}"
    
    def _hash_data(self, X: List, y: List) -> str:
        """Generate hash of training data for tracking."""
        # Simple hash for data tracking
        data_str = str(X) + str(y)
        return hashlib.md5(data_str.encode()).hexdigest()[:8]
    
    def _cleanup_old_versions(self, target: str):
        """Remove old versions beyond MAX_VERSIONS."""
        versions = self._registry.get(target, [])
        if len(versions) <= self.MAX_VERSIONS:
            return
        
        # Sort by date, keep newest
        sorted_versions = sorted(versions, key=lambda v: v.created_at, reverse=True)
        
        # Keep active + newest versions up to MAX_VERSIONS
        to_keep = []
        for v in sorted_versions:
            if v.is_active or len(to_keep) < self.MAX_VERSIONS:
                to_keep.append(v)
            else:
                # Delete old model file
                try:
                    model_path = os.path.join(self.model_dir, v.model_path)
                    if os.path.exists(model_path):
                        os.remove(model_path)
                    logger.info(f"Cleaned up old version: {v.version_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete old model: {e}")
        
        self._registry[target] = to_keep


# Convenience functions
def get_learner(model_dir: str = None) -> IncrementalLearner:
    """Get or create a shared IncrementalLearner instance."""
    return IncrementalLearner(model_dir)
