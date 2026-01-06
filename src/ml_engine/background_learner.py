"""
Paint Formulation AI - Background Learner Thread
=================================================
Thread-based background ML training for autonomous learning.

Triggered after each formulation/test save to:
1. Train global model on entire dataset
2. Train project-specific model
3. Generate improvement suggestions
"""

import threading
import logging
import queue
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LearningResult:
    """Result container for background learning"""
    success: bool
    global_metrics: Dict = None
    project_metrics: Dict = None
    suggestions: List[str] = None
    error_message: str = None


class BackgroundLearner(threading.Thread):
    """
    Background ML training thread.
    
    Runs training asynchronously to avoid blocking UI.
    Uses callback queue for thread-safe UI updates.
    """
    
    def __init__(
        self,
        db_manager,
        project_id: Optional[int] = None,
        formulation_data: Dict = None,
        result_callback: Callable[[LearningResult], None] = None
    ):
        """
        Initialize background learner.
        
        Args:
            db_manager: Database manager for fetching training data
            project_id: Current project ID for project-specific training
            formulation_data: Latest formulation that triggered training
            result_callback: Callback to invoke with results (UI thread)
        """
        super().__init__(daemon=True)
        self.db_manager = db_manager
        self.project_id = project_id
        self.formulation_data = formulation_data or {}
        self.result_callback = result_callback
        self._cancelled = threading.Event()
    
    def cancel(self):
        """Request cancellation of the training"""
        self._cancelled.set()
    
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested"""
        return self._cancelled.is_set()
    
    def run(self):
        """
        Main training logic.
        
        1. Global Training: Train on entire dataset
        2. Project Training: Filter by project_id and train
        3. Generate improvement suggestions
        """
        result = LearningResult(success=False)
        
        try:
            from src.ml_engine.continuous_learner import ContinuousLearner
            
            learner = ContinuousLearner()
            
            # Check for cancellation
            if self.is_cancelled():
                return
            
            # === 1. GLOBAL TRAINING ===
            logger.info("Background Learning: Starting global training...")
            global_data = self.db_manager.get_ml_training_data()
            
            if len(global_data) >= 3:
                global_result = learner.train(global_data)
                result.global_metrics = {
                    'success': global_result.get('success', False),
                    'samples': global_result.get('samples', 0),
                    'targets': list(global_result.get('targets', {}).keys()),
                    'feature_importance': learner.get_feature_importance()
                }
                logger.info(f"Global training complete: {result.global_metrics['samples']} samples")
            else:
                result.global_metrics = {'success': False, 'message': 'Insufficient data'}
            
            # Check for cancellation
            if self.is_cancelled():
                return
            
            # === 2. PROJECT TRAINING ===
            if self.project_id:
                logger.info(f"Background Learning: Starting project training for ID {self.project_id}...")
                project_data = self.db_manager.get_ml_training_data_by_project(self.project_id)
                
                if len(project_data) >= 3:
                    # Create a separate learner for project model
                    project_learner = ContinuousLearner(
                        model_dir=f'assets/models/project_{self.project_id}'
                    )
                    project_result = project_learner.train(project_data)
                    result.project_metrics = {
                        'success': project_result.get('success', False),
                        'samples': project_result.get('samples', 0),
                        'targets': list(project_result.get('targets', {}).keys()),
                        'feature_importance': project_learner.get_feature_importance()
                    }
                    logger.info(f"Project training complete: {result.project_metrics['samples']} samples")
                else:
                    result.project_metrics = {
                        'success': False, 
                        'message': f'Project needs at least 3 samples (has {len(project_data)})'
                    }
            
            # Check for cancellation
            if self.is_cancelled():
                return
            
            # === 3. GENERATE SUGGESTIONS ===
            result.suggestions = self._generate_suggestions(learner)
            
            result.success = True
            logger.info(f"Background learning complete. Suggestions: {len(result.suggestions or [])}")
            
        except Exception as e:
            logger.error(f"Background learning error: {e}", exc_info=True)
            result.error_message = str(e)
        
        finally:
            # Invoke callback with results
            if self.result_callback and not self.is_cancelled():
                try:
                    self.result_callback(result)
                except Exception as e:
                    logger.error(f"Result callback error: {e}")
    
    def _generate_suggestions(self, learner) -> List[str]:
        """
        Generate 3 improvement suggestions based on the latest formula.
        
        Uses feature importance to identify which parameters to adjust.
        """
        suggestions = []
        
        try:
            importance = learner.get_feature_importance()
            
            if not importance:
                return ["Model eğitildi. Daha fazla veri ile daha iyi öneriler alabilirsiniz."]
            
            # Get top parameters for key targets
            target_priorities = ['quality_score', 'opacity', 'gloss', 'total_cost']
            
            for target in target_priorities:
                if target in importance and len(suggestions) < 3:
                    target_importance = importance[target]
                    # Get top 2 most important features
                    sorted_features = sorted(
                        target_importance.items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )[:2]
                    
                    for feature, imp in sorted_features:
                        if imp > 0.1 and len(suggestions) < 3:
                            suggestion = self._format_suggestion(target, feature, imp)
                            if suggestion and suggestion not in suggestions:
                                suggestions.append(suggestion)
            
            if not suggestions:
                suggestions = ["Model eğitimi tamamlandı. Öneriler için daha fazla test verisi gerekli."]
            
        except Exception as e:
            logger.warning(f"Suggestion generation error: {e}")
            suggestions = ["Model başarıyla eğitildi."]
        
        return suggestions[:3]
    
    def _format_suggestion(self, target: str, feature: str, importance: float) -> str:
        """Format a single suggestion string"""
        target_names = {
            'quality_score': 'Kalite Skoru',
            'opacity': 'Örtücülük',
            'gloss': 'Parlaklık',
            'total_cost': 'Maliyet'
        }
        
        feature_names = {
            'viscosity': 'Viskozite',
            'ph': 'pH',
            'density': 'Yoğunluk',
            'coating_thickness': 'Kaplama Kalınlığı',
            'binder_ratio': 'Binder Oranı',
            'pigment_ratio': 'Pigment Oranı',
            'solvent_ratio': 'Solvent Oranı',
            'additive_ratio': 'Katkı Oranı'
        }
        
        target_tr = target_names.get(target, target)
        feature_tr = feature_names.get(feature, feature)
        
        # Determine direction based on target
        if target == 'total_cost':
            action = "azaltarak"
        else:
            action = "optimize ederek"
        
        return f"{feature_tr} değerini {action} {target_tr} iyileştirilebilir (etki: %{int(importance*100)})"
