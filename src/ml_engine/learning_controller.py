"""
Paint Formulation AI - Learning Controller
===========================================
Manages background ML training with concurrency safety.

Features:
- Debounce pattern: rapid saves trigger only one training
- Thread-safe UI callback mechanism
- Singleton pattern for app-wide access
"""

import threading
import logging
import time
from typing import Callable, Optional, Any
from dataclasses import dataclass

from src.ml_engine.background_learner import BackgroundLearner, LearningResult

logger = logging.getLogger(__name__)


class LearningController:
    """
    Controls background ML training lifecycle.
    
    Handles:
    - Single active training thread
    - Debounce on rapid saves (300ms delay)
    - Thread-safe result callbacks to UI
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_manager=None, root=None):
        """
        Initialize controller.
        
        Args:
            db_manager: Database manager for training data
            root: Tkinter root window (for thread-safe UI updates)
        """
        if self._initialized:
            # Update references if provided
            if db_manager:
                self.db_manager = db_manager
            if root:
                self.root = root
            return
        
        self.db_manager = db_manager
        self.root = root  # For tk.after() calls
        
        self._current_thread: Optional[BackgroundLearner] = None
        self._pending_request = None
        self._debounce_timer = None
        self._result_callback: Optional[Callable] = None
        self._thread_lock = threading.Lock()
        
        self._debounce_delay = 0.3  # 300ms debounce
        self._is_training = False
        
        self._initialized = True
        logger.info("LearningController initialized")
    
    def set_result_callback(self, callback: Callable[[LearningResult], None]):
        """
        Set callback for training results.
        
        Callback will be invoked in the UI thread via tk.after().
        """
        self._result_callback = callback
    
    def trigger_learning(
        self,
        project_id: Optional[int] = None,
        formulation_data: dict = None
    ):
        """
        Trigger background learning (debounced).
        
        If called multiple times rapidly, only the last request runs.
        
        Args:
            project_id: Current project for project-specific training
            formulation_data: Latest formulation that was saved
        """
        if not self.db_manager:
            logger.warning("LearningController: No db_manager set")
            return
        
        # Store pending request
        self._pending_request = {
            'project_id': project_id,
            'formulation_data': formulation_data or {}
        }
        
        # Cancel existing debounce timer
        if self._debounce_timer:
            self._debounce_timer.cancel()
        
        # Start new debounce timer
        self._debounce_timer = threading.Timer(
            self._debounce_delay,
            self._execute_learning
        )
        self._debounce_timer.start()
        
        logger.info("Learning triggered (debounce started)")
    
    def _execute_learning(self):
        """Execute the pending learning request"""
        with self._thread_lock:
            if self._is_training and self._current_thread:
                # Cancel current training and restart
                logger.info("Cancelling current training for new request")
                self._current_thread.cancel()
                # Wait briefly for cancellation
                self._current_thread.join(timeout=0.5)
            
            if not self._pending_request:
                return
            
            request = self._pending_request
            self._pending_request = None
            
            # Start new background thread
            self._is_training = True
            self._current_thread = BackgroundLearner(
                db_manager=self.db_manager,
                project_id=request['project_id'],
                formulation_data=request['formulation_data'],
                result_callback=self._on_training_complete
            )
            self._current_thread.start()
            
            logger.info(f"Background learning started (project_id={request['project_id']})")
    
    def _on_training_complete(self, result: LearningResult):
        """Handle training completion (called from worker thread)"""
        with self._thread_lock:
            self._is_training = False
            self._current_thread = None
        
        logger.info(f"Background learning complete: success={result.success}")
        
        # Invoke UI callback in main thread
        if self._result_callback:
            if self.root:
                # Thread-safe UI update via tk.after()
                self.root.after(0, lambda: self._result_callback(result))
            else:
                # Direct call (may not be thread-safe for UI)
                try:
                    self._result_callback(result)
                except Exception as e:
                    logger.error(f"Result callback error: {e}")
    
    def is_training(self) -> bool:
        """Check if training is currently in progress"""
        return self._is_training
    
    def get_status(self) -> dict:
        """Get current controller status"""
        return {
            'is_training': self._is_training,
            'has_pending': self._pending_request is not None,
            'initialized': self._initialized
        }
    
    def shutdown(self):
        """Clean shutdown of controller"""
        if self._debounce_timer:
            self._debounce_timer.cancel()
        
        if self._current_thread:
            self._current_thread.cancel()
            self._current_thread.join(timeout=1.0)
        
        logger.info("LearningController shutdown complete")


# Convenience function to get the singleton instance
def get_learning_controller(db_manager=None, root=None) -> LearningController:
    """Get or create the LearningController singleton"""
    return LearningController(db_manager=db_manager, root=root)
