"""
Paint Formulation AI - Project Context Manager
==============================================
Tek gerçek kaynak (Single Source of Truth) olarak proje ve formülasyon
state yönetimi. EventBus ile tüm UI panellerini otomatik bilgilendirir.

Kullanım:
    context = ProjectContext(db_manager)
    context.add_listener(my_panel.on_context_changed)
    context.project_id = 5  # Otomatik tüm listener'ları tetikler
"""

import logging
from typing import Callable, Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class ContextEvent(Enum):
    """Context değişiklik event tipleri"""
    PROJECT_CHANGED = "project_changed"
    FORMULATION_CHANGED = "formulation_changed"
    FORMULATION_SAVED = "formulation_saved"  # New: triggers all panel refresh
    FORMULATIONS_REFRESHED = "formulations_refreshed"
    ML_MODEL_UPDATED = "ml_model_updated"
    DATA_SAVED = "data_saved"


@dataclass
class ContextState:
    """Context'in mevcut durumu (snapshot)"""
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    formulation_id: Optional[int] = None
    formulation_code: Optional[str] = None
    formulations: List[Dict] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)


class ProjectContext:
    """
    Proje ve formülasyon state yöneticisi.
    
    Tüm UI panelleri bu sınıfı dinler ve değişikliklerde
    otomatik güncellenir.
    
    Attributes:
        project_id: Aktif proje ID'si
        formulation_id: Aktif formülasyon ID'si
        formulations: Aktif projedeki formülasyonlar
    """
    
    def __init__(self, db_manager):
        """
        Args:
            db_manager: LocalDBManager veya uyumlu DB facade
        """
        self.db = db_manager
        
        # State
        self._project_id: Optional[int] = None
        self._project_name: Optional[str] = None
        self._formulation_id: Optional[int] = None
        self._formulation_code: Optional[str] = None
        self._formulations: List[Dict] = []
        
        # Event listeners
        self._listeners: List[Callable[[ContextEvent, 'ProjectContext'], None]] = []
        
        logger.info("ProjectContext initialized")
    
    # =========================================================================
    # PROPERTIES (değişince otomatik event fırlatır)
    # =========================================================================
    
    @property
    def project_id(self) -> Optional[int]:
        """Aktif proje ID'si"""
        return self._project_id
    
    @project_id.setter
    def project_id(self, value: Optional[int]):
        """Proje değiştiğinde formulations da yenilenir"""
        if self._project_id != value:
            old_id = self._project_id
            self._project_id = value
            
            # Proje adını al
            if value is not None:
                project = self.db.get_project(value)
                self._project_name = project.get('name') if project else None
            else:
                self._project_name = None
            
            # Formülasyonu sıfırla
            self._formulation_id = None
            self._formulation_code = None
            
            # Formülasyonları yükle
            self._load_formulations()
            
            logger.info(f"Project changed: {old_id} -> {value} ({self._project_name})")
            self._notify(ContextEvent.PROJECT_CHANGED)
    
    @property
    def project_name(self) -> Optional[str]:
        """Aktif proje adı (read-only)"""
        return self._project_name
    
    @property
    def formulation_id(self) -> Optional[int]:
        """Aktif formülasyon ID'si"""
        return self._formulation_id
    
    @formulation_id.setter
    def formulation_id(self, value: Optional[int]):
        if self._formulation_id != value:
            old_id = self._formulation_id
            self._formulation_id = value
            
            # Formülasyon kodunu bul
            if value is not None:
                for f in self._formulations:
                    if f.get('id') == value:
                        self._formulation_code = f.get('formula_code')
                        break
            else:
                self._formulation_code = None
            
            logger.info(f"Formulation changed: {old_id} -> {value} ({self._formulation_code})")
            self._notify(ContextEvent.FORMULATION_CHANGED)
    
    @property
    def formulation_code(self) -> Optional[str]:
        """Aktif formülasyon kodu (read-only)"""
        return self._formulation_code
    
    @property
    def formulations(self) -> List[Dict]:
        """Aktif projedeki formülasyonlar (read-only)"""
        return self._formulations.copy()
    
    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================
    
    def add_listener(self, callback: Callable[[ContextEvent, 'ProjectContext'], None]):
        """
        Event listener ekle.
        
        Args:
            callback: (event_type, context) imzalı fonksiyon
            
        Örnek:
            def on_context_changed(event, ctx):
                if event == ContextEvent.PROJECT_CHANGED:
                    self.refresh_formulation_list(ctx.formulations)
                    
            context.add_listener(on_context_changed)
        """
        if callback not in self._listeners:
            self._listeners.append(callback)
            logger.debug(f"Listener added: {callback.__name__ if hasattr(callback, '__name__') else 'lambda'}")
    
    def remove_listener(self, callback: Callable):
        """Listener kaldır"""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def get_state(self) -> ContextState:
        """Mevcut state'in snapshot'ını döndür"""
        return ContextState(
            project_id=self._project_id,
            project_name=self._project_name,
            formulation_id=self._formulation_id,
            formulation_code=self._formulation_code,
            formulations=self._formulations.copy(),
            last_updated=datetime.now()
        )
    
    def refresh_formulations(self):
        """Formülasyon listesini zorunlu yenile"""
        self._load_formulations()
        self._notify(ContextEvent.FORMULATIONS_REFRESHED)
    
    def select_formulation_by_code(self, code: str) -> bool:
        """
        Formülasyonu kod ile seç.
        
        Returns:
            True: bulundu ve seçildi, False: bulunamadı
        """
        for f in self._formulations:
            if f.get('formula_code') == code:
                self.formulation_id = f.get('id')
                return True
        return False
    
    def notify_data_saved(self, data_type: str = "formulation"):
        """Veri kaydedildiğinde çağır (ML trigger için)"""
        logger.info(f"Data saved notification: {data_type}")
        self._notify(ContextEvent.DATA_SAVED)
    
    def notify_ml_updated(self):
        """ML model güncellendiğinde çağır"""
        self._notify(ContextEvent.ML_MODEL_UPDATED)
    
    def get_formulation_details(self, formulation_id: int = None) -> Optional[Dict]:
        """
        Formülasyon detaylarını getir.
        
        Args:
            formulation_id: Belirtilmezse aktif formülasyon
        """
        fid = formulation_id or self._formulation_id
        if fid is None:
            return None
        
        return self.db.get_formulation_with_components(fid)
    
    def get_training_data(self, project_only: bool = True) -> List[Dict]:
        """
        ML eğitim verisini getir.
        
        Args:
            project_only: True ise sadece aktif proje, False ise tüm projeler
        """
        if project_only and self._project_id:
            return self.db.get_training_data(project_id=self._project_id)
        else:
            return self.db.get_training_data(project_id=None)
    
    def save_formulation(self, data: Dict) -> int:
        """
        Formülasyonu kaydet ve tüm panelleri güncelle.
        
        Args:
            data: {formula_code, formula_name, components, ...}
            
        Returns:
            Formulation ID
            
        Side Effects:
            - Emits FORMULATION_SAVED event
            - Refreshes formulation list
            - All listening panels auto-update
        """
        # Ensure project_id is set
        if 'project_id' not in data and self._project_id:
            data['project_id'] = self._project_id
        
        if not data.get('project_id'):
            raise ValueError("project_id is required to save formulation")
        
        # Save to database
        formulation_id = self.db.save_formulation(data)
        
        # Refresh formulation list
        self._load_formulations()
        
        # Update current formulation
        self._formulation_id = formulation_id
        self._formulation_code = data.get('formula_code')
        
        # Emit event - all panels will refresh
        logger.info(f"Formulation saved: {formulation_id}, emitting FORMULATION_SAVED")
        self._notify(ContextEvent.FORMULATION_SAVED)
        
        return formulation_id
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    def _load_formulations(self):
        """Aktif proje için formülasyonları yükle"""
        if self._project_id is not None:
            self._formulations = self.db.get_formulations(self._project_id)
        else:
            self._formulations = []
        
        logger.debug(f"Loaded {len(self._formulations)} formulations for project {self._project_id}")
    
    def _notify(self, event: ContextEvent):
        """Tüm listener'ları bilgilendir"""
        for callback in self._listeners:
            try:
                callback(event, self)
            except Exception as e:
                logger.error(f"Listener error: {e}", exc_info=True)


class ContextAwarePanel:
    """
    Context'i dinleyen panel mixin'i.
    
    Kullanım:
        class MyPanel(ttk.Frame, ContextAwarePanel):
            def __init__(self, parent, context):
                super().__init__(parent)
                self.setup_context(context)
            
            def on_project_changed(self, ctx):
                # Proje değiştiğinde yapılacaklar
                pass
    """
    
    def setup_context(self, context: ProjectContext):
        """Context'e bağlan"""
        self._context = context
        context.add_listener(self._handle_context_event)
    
    @property
    def context(self) -> ProjectContext:
        """Bağlı context"""
        return getattr(self, '_context', None)
    
    def _handle_context_event(self, event: ContextEvent, ctx: ProjectContext):
        """Event'leri ilgili metodlara yönlendir"""
        handlers = {
            ContextEvent.PROJECT_CHANGED: 'on_project_changed',
            ContextEvent.FORMULATION_CHANGED: 'on_formulation_changed',
            ContextEvent.FORMULATION_SAVED: 'on_formulation_saved',
            ContextEvent.FORMULATIONS_REFRESHED: 'on_formulations_refreshed',
            ContextEvent.ML_MODEL_UPDATED: 'on_ml_updated',
            ContextEvent.DATA_SAVED: 'on_data_saved',
        }
        
        handler_name = handlers.get(event)
        if handler_name and hasattr(self, handler_name):
            getattr(self, handler_name)(ctx)
    
    # Override these in subclass
    def on_project_changed(self, ctx: ProjectContext):
        """Proje değiştiğinde çağrılır"""
        pass
    
    def on_formulation_changed(self, ctx: ProjectContext):
        """Formülasyon değiştiğinde çağrılır"""
        pass
    
    def on_formulation_saved(self, ctx: ProjectContext):
        """
        Formülasyon kaydedildiğinde çağrılır.
        
        Default: refresh formulation list for dropdowns.
        """
        # Default implementation for panels with formulation dropdowns
        if hasattr(self, 'load_formulations') and hasattr(ctx, 'formulations'):
            self.load_formulations(ctx.formulations)
    
    def on_formulations_refreshed(self, ctx: ProjectContext):
        """Formülasyon listesi yenilendiğinde çağrılır"""
        pass
    
    def on_ml_updated(self, ctx: ProjectContext):
        """ML model güncellendiğinde çağrılır"""
        pass
    
    def on_data_saved(self, ctx: ProjectContext):
        """Veri kaydedildiğinde çağrılır"""
        pass

