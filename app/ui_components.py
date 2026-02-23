"""
Paint Formulation AI - UI Bileşenleri
=====================================
Tkinter tabanlı kullanıcı arayüzü bileşenleri

NOT: Bu dosya artık bir facade olarak çalışmaktadır.
Bileşenler app/components/ altında modüler olarak tanımlanmıştır.
Geriye uyumluluk için burada re-export edilmektedir.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from configparser import ConfigParser
from typing import Optional, Callable, Dict, List
import threading
import logging

from src.core.i18n import t, I18nMixin, I18n
from src.core.translation_keys import TK

# Core architecture
from src.core.project_context import ProjectContext, ContextEvent

# Modüler bileşenlerden import (Yeni özellikler bu dosyalarda)
from app.components.status_bar import StatusBar
from app.components.project_panel import ProjectPanel
from app.components.quick_actions import QuickActionsPanel
from app.components.dashboard import DashboardPanel
from app.components.ml_panel import MLRecommendationPanel
from app.components.material_panel import MaterialManagementPanel
from app.components.dialogs.project_dialog import ProjectDialog
from app.components.dialogs.formulation_list_dialog import FormulationListDialog
from app.components.dialogs.trial_list_dialog import TrialListDialog
from src.ml_engine.recipe_transformer import RecipeTransformer
from app.theme import apply_dark_theme, COLORS, ICONS, create_icon_button, configure_treeview_tags

logger = logging.getLogger(__name__)


class ModernButton(ttk.Button):
    """Modern görünümlü özelleştirilmiş buton"""
    def __init__(self, parent, text, command=None, style="Modern.TButton", **kwargs):
        super().__init__(parent, text=text, command=command, style=style, **kwargs)


class TrialRecordPanel(ttk.LabelFrame):
    """Deneme kayıt paneli"""
    def __init__(self, parent, on_save: Callable = None):
        super().__init__(parent, text="🧪 Deneme Kaydı", padding=10)
        
        self.on_save = on_save
        self.entries = {}
        
        # Formülasyon bilgileri
        info_frame = ttk.Frame(self)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        fields = [
            ("Formül Kodu:", "formula_code"),
            ("Formül Adı:", "formula_name"),
            ("Tarih:", "date"),
        ]
        
        for i, (label, key) in enumerate(fields):
            ttk.Label(info_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=2)
            entry = ttk.Entry(info_frame, width=30)
            entry.grid(row=i, column=1, sticky=tk.EW, padx=5, pady=2)
            self.entries[key] = entry
        
        info_frame.columnconfigure(1, weight=1)
        
        # Test parametreleri
        params_frame = ttk.LabelFrame(self, text="Test Parametreleri", padding=5)
        params_frame.pack(fill=tk.X, pady=10)
        
        test_params = [
            ("Viskozite (cP):", "viscosity"),
            ("pH Değeri:", "ph"),
            ("Yoğunluk (g/ml):", "density"),
            ("Örtücülük (%):", "opacity"),
            ("Parlaklık (GU):", "gloss"),
            ("Kalite Skoru (1-10):", "quality_score"),
        ]
        
        for i, (label, key) in enumerate(test_params):
            row = i // 2
            col = (i % 2) * 2
            ttk.Label(params_frame, text=label).grid(row=row, column=col, sticky=tk.W, pady=2)
            entry = ttk.Entry(params_frame, width=15)
            entry.grid(row=row, column=col+1, sticky=tk.EW, padx=5, pady=2)
            self.entries[key] = entry
        
        # Kaplama testleri
        coating_frame = ttk.LabelFrame(self, text="Kaplama Testleri", padding=5)
        coating_frame.pack(fill=tk.X, pady=5)
        
        coating_params = [
            ("Kaplama Kalınlığı (µm):", "coating_thickness"),
            ("Korozyon Direnci:", "corrosion_resistance"),
            ("Yapışma (0-5):", "adhesion"),
            ("Sertlik (H):", "hardness"),
            ("Esneklik:", "flexibility"),
            ("Toplam Maliyet:", "total_cost"),
        ]
        
        for i, (label, key) in enumerate(coating_params):
            row = i // 2
            col = (i % 2) * 2
            ttk.Label(coating_frame, text=label).grid(row=row, column=col, sticky=tk.W, pady=2)
            entry = ttk.Entry(coating_frame, width=15)
            entry.grid(row=row, column=col+1, sticky=tk.EW, padx=5, pady=2)
            self.entries[key] = entry
        
        # Notlar
        ttk.Label(self, text="Notlar:").pack(anchor=tk.W)
        self.notes_text = tk.Text(self, height=4, wrap=tk.WORD)
        self.notes_text.pack(fill=tk.X, pady=5)
        
        # Kaydet butonu
        ttk.Button(self, text="💾 Kaydet", command=self._save_trial).pack(fill=tk.X)
    
    def _save_trial(self):
        """Denemeyi kaydet"""
        data = {key: entry.get() for key, entry in self.entries.items()}
        data['notes'] = self.notes_text.get(1.0, tk.END).strip()
        
        if self.on_save:
            self.on_save(data)
            self._clear_form()
            messagebox.showinfo("Başarılı", "Deneme kaydedildi!")
    
    def _clear_form(self):
        """Formu temizle"""
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.notes_text.delete(1.0, tk.END)


class PaintFormulationApp(I18nMixin):
    """Ana uygulama sınıfı"""
    def __init__(self, config: ConfigParser, db_manager, network_checker, app_dir: str):
        self.config = config
        self.db_manager = db_manager
        self.network_checker = network_checker
        self.app_dir = app_dir
        
        # Initialize i18n
        lang = config.get('Application', 'language', fallback='tr')
        I18n().load(lang)
        self.setup_i18n()
        
        # Ana pencere
        self.root = tk.Tk()
        self.root.title(f"{config.get('Application', 'name', fallback='Paint Formulation AI')} v{config.get('Application', 'version', fallback='1.0')}")
        
        # Pencere boyutu
        width = config.getint('UI', 'window_width', fallback=1200)
        height = config.getint('UI', 'window_height', fallback=800)
        self.root.geometry(f"{width}x{height}")
        
        # Project Context (Single Source of Truth for project/formulation state)
        self.context = ProjectContext(db_manager)
        self.context.add_listener(self._on_context_changed)
        
        # Tema
        self._setup_theme()
        
        # Menü Sistemi
        self._create_menu()
        
        # UI oluştur
        self._create_ui()
        
        # Başlangıç verileri
        self._load_initial_data()
        
        # Background Learning Controller
        self._setup_learning_controller()
    
    def _setup_theme(self):
        """Apply modern dark theme using centralized theme module"""
        theme = self.config.get('UI', 'theme', fallback='dark')
        
        if theme == 'dark':
            apply_dark_theme(self.root)
            
    def _update_texts(self):
        """Tüm ana UI metinlerini güncelle"""
        logger.info(f"MainApp._update_texts called. Current lang: {get_i18n().current_language}")
        # Menü isimlerini güncelle
        self.menubar.entryconfig(0, label=t(TK.MENU_FILE))
        self.menubar.entryconfig(1, label=t(TK.MENU_SETTINGS))
        
        self.file_menu.entryconfig(0, label=t(TK.MENU_EXIT))
        self.settings_menu.entryconfig(0, label=t(TK.SETTINGS_LANGUAGE))
        
        # Notebook sekmelerini güncelle
        all_tabs = self.notebook.tabs()
        nav_keys = [TK.NAV_DASHBOARD, TK.NAV_MATERIALS, TK.NAV_FORMULATIONS, 
                    TK.NAV_TEST_RESULTS, TK.NAV_ML_CENTER, TK.NAV_OPTIMIZATION]
        
        for i, key in enumerate(nav_keys):
            if i < len(all_tabs):
                tab_id = all_tabs[i]
                new_text = t(key)
                logger.info(f"MainApp: Updating notebook tab {i} (widget: {tab_id}) to '{new_text}' (key: {key})")
                self.notebook.tab(tab_id, text=new_text)
        
        # Explicitly refresh sub-panels just in case
        for attr in ['dashboard', 'material_panel', 'formulation_editor', 
                     'test_results_panel', 'ml_panel', 'comparison_panel',
                     'sidebar', 'status_bar']:
            if hasattr(self, attr):
                panel = getattr(self, attr)
                if hasattr(panel, '_update_texts'):
                    panel._update_texts()

        # Force refresh UI
        self.root.update_idletasks()

    def _create_menu(self):
        """Uygulama menüsünü oluştur"""
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        
        # Dosya Menüsü
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(menu=self.file_menu, label=t(TK.MENU_FILE))
        self.file_menu.add_command(label=t(TK.MENU_EXIT), command=self.root.quit)
        
        # Ayarlar/Dil Menüsü
        self.settings_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(menu=self.settings_menu, label=t(TK.MENU_SETTINGS))
        
        self.lang_menu = tk.Menu(self.settings_menu, tearoff=0)
        self.settings_menu.add_cascade(menu=self.lang_menu, label=t(TK.SETTINGS_LANGUAGE))
        
        self.lang_var = tk.StringVar(value=I18n()._lang)
        self.lang_menu.add_radiobutton(label="Türkçe", variable=self.lang_var, value="tr", command=lambda: self._switch_language("tr"))
        self.lang_menu.add_radiobutton(label="English", variable=self.lang_var, value="en", command=lambda: self._switch_language("en"))

    def _switch_language(self, lang: str):
        """Dil değiştir ve konfigürasyona kaydet"""
        from src.core.i18n import switch_language
        if switch_language(lang):
            self.config.set('Application', 'language', lang)
            self._update_texts() # Refresh tab names and menus immediately

    
    def _create_ui(self):
        """Kullanıcı arayüzünü oluştur (Split Layout: Sidebar + Content)"""
        from app.components.sidebar_navigator import SidebarNavigator, TYPE_PROJECT, TYPE_CONCEPT, TYPE_TRIAL
        
        # Aktif proje/formül state
        self.active_project_id = None
        self.active_project_name = None
        self.active_formulation_id = None
        self.active_formulation_code = None
        self._projects_cache = []
        self._formulations_cache = []
        
        # Main Split Container
        self.main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=4, bg="#2b2b2b")
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        # === LEFT SIDEBAR ===
        self.sidebar_frame = ttk.Frame(self.main_paned, width=250)
        self.sidebar = SidebarNavigator(
            self.sidebar_frame, 
            self.db_manager, 
            self._on_sidebar_selection,
            on_project_change=self._refresh_all_panels,
            context=self.context  # Pass ProjectContext for unified state
        )
        self.sidebar.pack(fill=tk.BOTH, expand=True)
        self.main_paned.add(self.sidebar_frame, minsize=200)
        
        # Compatibility Alias
        self.project_panel = self.sidebar
        
        # === RIGHT CONTENT AREA ===
        self.content_frame = ttk.Frame(self.main_paned, padding=10)
        self.main_paned.add(self.content_frame, minsize=600)
        
        # Notebook for Content Views (Home, Editor, ML)
        self.notebook = ttk.Notebook(self.content_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # === SEKME 1: Ana Sayfa (Dashboard) ===
        main_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(main_tab, text=t(TK.NAV_DASHBOARD))
        
        # Dashboard Content
        self.dashboard = DashboardPanel(main_tab, self._on_dashboard_navigate)
        self.dashboard.pack(fill=tk.BOTH, expand=True)

        # === SEKME 2: Malzemeler ===
        material_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(material_tab, text=t(TK.NAV_MATERIALS))
        
        self.material_panel = MaterialManagementPanel(
            material_tab,
            self.db_manager,
            on_material_change=self._on_material_list_change
        )
        self.material_panel.pack(fill=tk.BOTH, expand=True)
        
        # === SEKME 3: Formülasyon Editörü ===
        from app.components.editor.modern_formulation_editor import ModernFormulationEditor
        formulation_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(formulation_tab, text=t(TK.NAV_FORMULATIONS))
        
        self.formulation_editor = ModernFormulationEditor(
            formulation_tab, 
            on_save=self._on_save_formulation,
            on_calculate=self._on_calculate_formulation,
            on_load_formulation=self._on_load_detailed_formulation,
            on_lookup_material=self.db_manager.get_material_by_code,
            on_get_material_list=self.db_manager.get_all_materials,
            on_create_material=self._on_create_material_from_import
        )
        self.formulation_editor.pack(fill=tk.BOTH, expand=True)
        
        # === SEKME 4: Test Sonuçları (V2 - Decision Support) ===
        from app.test_results_panel_v2 import TestResultsPanelV2
        test_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(test_tab, text=t(TK.NAV_TEST_RESULTS))
        
        self.test_results_panel = TestResultsPanelV2(
            test_tab,
            on_save=self._on_save_test_results,
            on_load_formulations=self._on_load_formulations,
            on_load_trial=self._on_load_trial,
            db_manager=self.db_manager
        )
        self.test_results_panel.pack(fill=tk.BOTH, expand=True)
        
        # === SEKME 5: ML Merkezi (Passive Assistant) ===
        from app.components.passive_ml_panel import PassiveMLPanel
        ml_tab = ttk.Frame(self.notebook)
        self.notebook.add(ml_tab, text=t(TK.NAV_ML_CENTER))
        
        self.ml_panel = PassiveMLPanel(
            ml_tab,
            db_manager=self.db_manager,
            on_get_project_suggestions=self._get_project_suggestions,
            on_get_global_trends=self._get_global_trends
        )
        self.ml_panel.pack(fill=tk.BOTH, expand=True)

        # === SEKME 6: Karşılaştırma ===
        from app.components.comparison_panel import VariationComparisonPanel
        comp_tab = ttk.Frame(self.notebook)
        self.notebook.add(comp_tab, text=t(TK.NAV_OPTIMIZATION)) 
        self.comparison_panel = VariationComparisonPanel(comp_tab, self.db_manager)
        self.comparison_panel.pack(fill=tk.BOTH, expand=True)
        
        # Status Bar
        self.status_bar = StatusBar(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _on_sidebar_selection(self, item_type, item_id):
        """Handle Sidebar Clicks"""
        from app.components.sidebar_navigator import TYPE_PROJECT, TYPE_CONCEPT, TYPE_TRIAL
        
        if item_type == TYPE_PROJECT:
            # Show Dashboard
            self.active_project_id = item_id
            self.notebook.select(0) # Main Tab
            self.status_bar.update_status(f"{t(TK.FORM_PROJECT)} {t(TK.common_success if hasattr(TK, 'common_success') else TK.SUCCESS)}: ID {item_id}")
            # TODO: Refresh dashboard for this project
            
        elif item_type == TYPE_CONCEPT:
            # Show Concept Comparison
            self.notebook.select(5) # Comparison Tab (Index 5)
            self.comparison_panel.load_concept(item_id)
            self.status_bar.update_status(f"{t(TK.NAV_OPTIMIZATION)}: ID {item_id}")
            
        elif item_type == TYPE_TRIAL:
            # Load Trial into Editor
            self.notebook.select(2)  # Formülasyon Tab (Index 2)
            self.active_formulation_id = item_id # Maps to trial_id in V2
            self._on_load_detailed_formulation(item_id)
            self.status_bar.set_status(f"{t(TK.FORM_SAVED_FORMULAS)} {t(TK.common_loading if hasattr(TK, 'common_loading') else TK.LOADING)}: ID {item_id}")
            
        elif item_type == "new_trial_request":
            # Parent ID is passed as item_id
            self.notebook.select(2)  # Formülasyon Tab (Index 2)
            self.formulation_editor._clear_form()
            # We should set context that we are creating for this parent
            self.active_project_id = None # Concept linkage handles it?
            self.formulation_editor.current_parent_id = item_id # TODO: Handle this in editor
            self.status_bar.set_status(t(TK.FORM_NEW_VARIATION))
    
    def _load_initial_data(self):
        """Başlangıç verilerini yükle"""
        try:
            # Cleanup orphaned formulations from deleted projects (from previous sessions)
            cleaned = self.db_manager.cleanup_orphaned_formulations()
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} orphaned formulations on startup")
            
            projects = self.db_manager.get_all_projects()
            logger.info(f"Başlangıç: {len(projects)} proje yüklendi")
            
            # Sidebar'ı güncelle (Legacy self.project_panel yerine)
            if hasattr(self, 'sidebar'):
                self.sidebar.refresh()
            
            # Proje cache'i güncelle
            self._projects_cache = projects
            
            # Projeleri tüm panellere yükle
            if hasattr(self, 'optimization_panel') and hasattr(self.optimization_panel, 'load_projects'):
                self.optimization_panel.load_projects(projects)
                logger.info("optimization_panel'e projeler yüklendi")
            
            if hasattr(self, 'formulation_editor'):
                self.formulation_editor.load_projects(projects)
                logger.info("formulation_editor'e projeler yüklendi")
                # Kayıtlı formülasyonları dropdown'a yükle (only from active projects)
                formulations = self.db_manager.get_active_formulations()
                logger.info(f"Başlangıç: {len(formulations)} aktif formülasyon yüklendi")
                self.formulation_editor.load_formulation_list(formulations)
                logger.info("formulation_editor'e formülasyonlar yüklendi")
            
            if hasattr(self, 'test_results_panel'):
                self.test_results_panel.load_projects(projects)
                logger.info("test_results_panel'e projeler yüklendi")
                # Formülasyonları da yükle (only from active projects)
                formulations = self.db_manager.get_active_formulations()
                self.test_results_panel.load_formulations(formulations)
                logger.info("test_results_panel'e formülasyonlar yüklendi")
                # Geçmiş test sonuçlarını yükle
                trials = self.db_manager.get_recent_trials(50)
                self.test_results_panel.load_history(trials)
            
            stats = self.db_manager.get_dashboard_stats()
            monthly_data = self.db_manager.get_monthly_formulation_counts()
            self.dashboard.update_stats(stats, monthly_data)
            
            # Özel test metodlarını optimizasyon hedeflerine yükle
            if hasattr(self, 'optimization_panel') and hasattr(self.optimization_panel, 'load_custom_objectives'):
                self.optimization_panel.load_custom_objectives()
            
            # Gelişmiş ML paneline projeleri yükle
            if hasattr(self, 'advanced_ml_panel'):
                self.advanced_ml_panel.load_projects(projects)
                logger.info("advanced_ml_panel'e projeler yüklendi")
            
            self.status_bar.set_status(t(TK.MSG_OPERATION_COMPLETE if hasattr(TK, 'MSG_OPERATION_COMPLETE') else TK.SUCCESS))
            logger.info("Tüm başlangıç verileri yüklendi")
        except Exception as e:
            logger.error(f"Veri yükleme hatası: {str(e)}", exc_info=True)
            self.status_bar.set_status(f"Veri yükleme hatası: {str(e)}")
    
    def _on_custom_method_changed(self):
        """Özel test metodu eklendiğinde optimizasyon panelini güncelle"""
        if hasattr(self, 'optimization_panel'):
            self.optimization_panel.load_custom_objectives()
            self.status_bar.set_status("✅ Özel test metodları güncellendi")
    
    def _on_material_list_change(self):
        """Malzeme listesi değiştiğinde formülasyon editörünü güncelle"""
        if hasattr(self, 'formulation_editor'):
            # Malzeme listesini yeniden yükle
            materials = self.db_manager.get_all_materials()
            if hasattr(self.formulation_editor, 'refresh_materials'):
                self.formulation_editor.refresh_materials()
            self.status_bar.set_status("✅ Malzeme listesi güncellendi")
    
    def _on_create_material_from_import(self, code: str, name: str = None) -> bool:
        """
        Callback for on-the-fly material creation during Excel import.
        
        Args:
            code: Material code (required)
            name: Material name (optional, uses code if not provided)
            
        Returns:
            True if material was newly created, False if already existed
        """
        try:
            material_id, was_created = self.db_manager.add_material_if_not_exists(code, name)
            if was_created:
                logger.info(f"Created new material on-the-fly: {code}")
                # Refresh material panel if visible
                if hasattr(self, 'material_panel'):
                    self.material_panel.refresh()
            return was_created
        except Exception as e:
            logger.error(f"Failed to create material {code}: {e}")
            return False
    
    def _setup_learning_controller(self):
        """Initialize the background learning controller and toast manager"""
        try:
            from src.ml_engine.learning_controller import get_learning_controller
            from app.components.toast_notification import ToastManager
            
            self.learning_controller = get_learning_controller(
                db_manager=self.db_manager,
                root=self.root
            )
            self.learning_controller.set_result_callback(self._on_learning_complete)
            
            # Initialize toast notification manager
            self.toast_manager = ToastManager(self.root)
            
            logger.info("LearningController and ToastManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LearningController: {e}")
            self.learning_controller = None
            self.toast_manager = None
    
    def _on_learning_complete(self, result):
        """Handle background learning completion"""
        try:
            # Update ML panel status
            if hasattr(self, 'ml_panel') and self.ml_panel:
                self.ml_panel.set_learning_status(False)
                self.ml_panel.update_insights(result)
            
            if result.success:
                # Show toast notification (non-blocking)
                if hasattr(self, 'toast_manager') and self.toast_manager:
                    samples = result.global_metrics.get('samples', 0) if result.global_metrics else 0
                    self.toast_manager.show_ml_update(
                        f"AI Model son formülasyonla güncellendi ({samples} örnek)"
                    )
                
                # Log metrics
                if result.global_metrics:
                    logger.info(f"Global ML metrics: {result.global_metrics}")
                if result.project_metrics:
                    logger.info(f"Project ML metrics: {result.project_metrics}")
            else:
                if result.error_message:
                    logger.warning(f"ML learning failed: {result.error_message}")
        except Exception as e:
            logger.error(f"Error handling learning result: {e}")
    
    def _trigger_background_learning(self, project_id: int = None, formulation_data: dict = None):
        """Trigger background ML learning (called after save operations)"""
        if hasattr(self, 'learning_controller') and self.learning_controller:
            # Use active project if not specified
            if project_id is None:
                project_id = getattr(self, 'active_project_id', None)
            
            # Update ML panel status to "learning"
            if hasattr(self, 'ml_panel') and self.ml_panel:
                self.ml_panel.set_learning_status(True)
            
            self.learning_controller.trigger_learning(
                project_id=project_id,
                formulation_data=formulation_data
            )

    def _get_project_suggestions(self, project_id: int) -> list:
        """Get project-specific suggestions from ML model"""
        try:
            from src.ml_engine.continuous_learner import ContinuousLearner
            
            learner = ContinuousLearner(model_dir=f'assets/models/project_{project_id}')
            status = learner.get_model_status()
            
            if not status.get('trained'):
                return [t(TK.ML_EMPTY_RULES)]
            
            # Get feature importance as suggestions
            importance = learner.get_feature_importance()
            suggestions = []
            
            for target, features in importance.items():
                if target in ['quality_score', 'opacity', 'corrosion_resistance']:
                    sorted_features = sorted(features.items(), key=lambda x: x[1], reverse=True)[:2]
                    for feature, imp in sorted_features:
                        if imp > 0.15:
                            # Localized template
                            msg = t(TK.ML_COMMENT_ABOVE).replace('{label}', feature).replace('{pct}', f"{imp*100:.0f}")
                            suggestions.append(msg)
            
            return suggestions[:5] if suggestions else [t(TK.ML_EMPTY_RULES)]
        except Exception as e:
            logger.warning(f"Failed to get project suggestions: {e}")
            return []
    
    def _get_global_trends(self) -> dict:
        """Get global trends from ML model"""
        try:
            from src.ml_engine.continuous_learner import ContinuousLearner
            
            learner = ContinuousLearner()
            status = learner.get_model_status()
            
            if not status.get('trained'):
                return {'feature_importance': {}, 'rules': []}
            
            return {
                'feature_importance': learner.get_feature_importance(),
                'rules': []
            }
        except Exception as e:
            logger.warning(f"Failed to get global trends: {e}")
            return {'feature_importance': {}, 'rules': []}

    def _on_project_change(self, project_data: dict):
        """Proje değişikliği olayı"""
        action = project_data.get('action', '')
        
        if action == 'open':
            project_name = project_data['name']
            logger.info(f"Proje açılıyor: {project_name}")
            
            # Projeyi veritabanından doğrudan ara
            project = self.db_manager.get_project_by_name(project_name)
            if project:
                self.active_project_id = project.get('id')
                self.active_project_name = project_name
                logger.info(f"Aktif proje ID: {self.active_project_id}")
            else:
                # Cache'den ara
                for p in self._projects_cache:
                    if p.get('name') == project_name:
                        self.active_project_id = p.get('id')
                        self.active_project_name = project_name
                        break
            
            # Projeye ait formülasyonları yükle
            if self.active_project_id:
                formulations = self.db_manager.get_formulations(self.active_project_id)
                self._formulations_cache = formulations
                logger.info(f"Projede {len(formulations)} formül bulundu")
                
                # Formülasyon editörüne yükle
                if hasattr(self, 'formulation_editor'):
                    self.formulation_editor.load_formulation_list(formulations)
                    logger.info("Formülasyon editörüne yüklendi")
                
                # Test sonuçları paneline yükle
                if hasattr(self, 'test_results_panel'):
                    self.test_results_panel.load_formulations(formulations)
                    logger.info("Test sonuçları paneline yüklendi")
                
                self.status_bar.set_status(f"Proje açıldı: {project_name} ({len(formulations)} formül)")
                messagebox.showinfo("Proje Açıldı", f"'{project_name}' projesi açıldı.\n\n{len(formulations)} formül yüklendi.")
            else:
                self.status_bar.set_status(f"Proje açıldı: {project_name}")
                logger.warning(f"Proje ID bulunamadı: {project_name}")
                
        elif action == 'delete':
            # Projeyi veritabanından sil
            try:
                self.db_manager.delete_project_by_name(project_data['name'])
                self.status_bar.set_status(f"Proje silindi: {project_data['name']}")
                # Aktif proje silinmişse temizle
                if self.active_project_name == project_data['name']:
                    self.active_project_id = None
                    self.active_project_name = None
                # Tüm panelleri yenile
                self._refresh_all_panels()
            except Exception as e:
                self.status_bar.set_status(f"Silme hatası: {str(e)}")
        else:
            # Yeni proje oluştur
            self.db_manager.create_project(project_data)
            self.status_bar.set_status(f"Proje oluşturuldu: {project_data['name']}")
            # Tüm panelleri yenile
            self._refresh_all_panels()
    
    def _on_context_changed(self, event: ContextEvent, ctx):
        """
        ProjectContext değişikliklerine tepki ver.
        
        Bu metod tüm panelleri context değişikliklerinden haberdar eder.
        EventBus patternı sayesinde her panel sadece ilgili event'leri dinler.
        """
        if event == ContextEvent.PROJECT_CHANGED:
            # Proje değişti - tüm panelleri güncelle
            project_name = ctx.project_name or "—"
            self.status_bar.set_status(f"Proje seçildi: {project_name}")
            
            # Formülasyon editörünü güncelle
            if hasattr(self, 'formulation_editor'):
                self.formulation_editor.load_formulation_list(ctx.formulations)
            
            # Test sonuçları panelini güncelle
            if hasattr(self, 'test_results_panel'):
                self.test_results_panel.load_formulations(ctx.formulations)
            
            # ML panelini güncelle (proje model durumu için)
            if hasattr(self, 'ml_panel') and hasattr(self.ml_panel, 'refresh_for_project'):
                self.ml_panel.refresh_for_project(ctx.project_id)
            
            # Dashboard'u güncelle
            self._refresh_dashboard()
            
            logger.info(f"Context: Project changed to {ctx.project_id} ({project_name}), {len(ctx.formulations)} formulations")
            
        elif event == ContextEvent.FORMULATION_CHANGED:
            # Formülasyon değişti - detay panellerini güncelle
            if ctx.formulation_id:
                self.status_bar.set_status(f"Formülasyon: {ctx.formulation_code}")
                
                # Aktif sekmeye göre yükle
                self._load_formulation_to_current_tab()
            
        elif event == ContextEvent.DATA_SAVED:
            # Veri kaydedildi - ML öğrenme tetikle
            self._trigger_background_learning(project_id=ctx.project_id)
            
        elif event == ContextEvent.ML_MODEL_UPDATED:
            # ML modeli güncellendi
            if hasattr(self, 'ml_panel'):
                self.ml_panel.refresh()
    
    def _refresh_all_panels(self):
        """Tüm panellerin proje ve formülasyon listelerini yenile"""
        try:
            # Güncel proje listesini al
            projects = self.db_manager.get_all_projects()
            
            # Formülasyon editörünü güncelle
            if hasattr(self, 'formulation_editor'):
                self.formulation_editor.load_projects(projects)
                # Context'e göre formülasyonları yükle
                if self.context.project_id:
                    self.formulation_editor.load_formulation_list(self.context.formulations)
            
            # Test sonuçları panelini güncelle
            if hasattr(self, 'test_results_panel'):
                self.test_results_panel.load_projects(projects)
                # Context'e göre formülasyonları yükle
                if self.context.project_id:
                    self.test_results_panel.load_formulations(self.context.formulations)
                else:
                    formulations = self.db_manager.get_active_formulations()
                    self.test_results_panel.load_formulations(formulations)
            
            # Optimizasyon panelini güncelle
            if hasattr(self, 'optimization_panel'):
                self.optimization_panel.load_projects(projects)
            
            # Dashboard güncelle
            self._refresh_dashboard()
            
        except Exception as e:
            self.status_bar.set_status(f"Panel yenileme hatası: {str(e)}")
    
    def _on_global_project_change(self, event=None):
        """Global proje seçimi değiştiğinde"""
        project_name = self.global_project_combo.get()
        if not project_name:
            return
        
        # Proje ID'sini bul
        for p in self._projects_cache:
            if p.get('name') == project_name:
                self.active_project_id = p.get('id')
                self.active_project_name = project_name
                break
        
        # Formülasyonları güncelle
        if self.active_project_id:
            formulations = self.db_manager.get_formulations(self.active_project_id)
            self._formulations_cache = formulations
            formula_items = [f"{f.get('formula_code', '')} - {f.get('formula_name', '')}" for f in formulations]
            self.global_formula_combo['values'] = formula_items
            self.global_formula_combo.set('')  # Seçimi temizle
            
            # Aktif formülü sıfırla
            self.active_formulation_id = None
            self.active_formulation_code = None
            
            # Göstergeyi güncelle
            self.active_selection_label.config(text=f"📁 {project_name} ({len(formulations)} {t(TK.FORM_SAVED_FORMULAS).lower()})")
            self.status_bar.set_status(f"{t(TK.FORM_PROJECT)} {t(TK.common_success if hasattr(TK, 'common_success') else TK.SUCCESS)}: {project_name}")
    
    def _on_global_formula_change(self, event=None):
        """Global formül seçimi değiştiğinde"""
        formula_text = self.global_formula_combo.get()
        if not formula_text or not hasattr(self, '_formulations_cache'):
            return
        
        # Formül kodunu çıkar (ilk kısım)
        formula_code = formula_text.split(' - ')[0].strip()
        
        # Formül ID'sini bul
        for f in self._formulations_cache:
            if f.get('formula_code') == formula_code:
                self.active_formulation_id = f.get('id')
                self.active_formulation_code = formula_code
                break
        
        # Göstergeyi güncelle
        self.active_selection_label.config(text=f"📁 {self.active_project_name} / 📋 {formula_code}")
        self.status_bar.set_status(f"{t(TK.FORM_SAVED_FORMULAS)} {t(TK.common_success if hasattr(TK, 'common_success') else TK.SUCCESS)}: {formula_code}")
        
        # Aktif sekmeye göre detayları yükle
        self._load_formulation_to_current_tab()
    
    def _load_formulation_to_current_tab(self):
        """Seçili formülasyonu aktif sekmeye yükle"""
        if not self.active_formulation_id:
            return
        
        current_tab = self.notebook.index(self.notebook.select())
        
        # Sekme 3: Formülasyon (index 2)
        if current_tab == 2 and hasattr(self, 'formulation_editor'):
            # Formülasyon editörüne yükle
            self.formulation_editor.load_formulation(self.active_formulation_id)
        
        # Sekme 4: Test Sonuçları (index 3)
        elif current_tab == 3 and hasattr(self, 'test_results_panel'):
            # Test sonuçlarını yükle
            trial_data = self.db_manager.get_latest_trial_by_formula_code(self.active_formulation_code)
            if trial_data:
                self.test_results_panel._fill_form_with_trial(trial_data)
            # Formül combobox'ını da güncelle
            self.test_results_panel.formulation_combo.set(self.active_formulation_code)
    
    def _on_dashboard_navigate(self, card_label: str):
        """Dashboard kartına tıklandığında filtrelenmiş popup göster"""
        try:
            # Kart tipine göre formülasyonları getir
            # card_label is usually the TK key from DashboardPanel
            total_keys = [TK.DASHBOARD_STATS_TOTAL, "Toplam Formül", "Total Formulas"]
            monthly_keys = [TK.DASHBOARD_STATS_MONTHLY, "Bu Ay Eklenen", "Added This Month"]
            waiting_keys = [TK.DASHBOARD_STATS_WAITING, "Test Bekleyen", "Waiting for Test"]
            success_keys = [TK.DASHBOARD_STATS_SUCCESS, "Başarılı", "Successful"]
            
            if card_label in total_keys:
                formulations = self.db_manager.get_all_formulations()
                title = f"📋 {t(TK.DASHBOARD_TOTAL_FORMULAS)}"
            elif card_label in monthly_keys:
                formulations = self.db_manager.get_formulations_this_month()
                title = f"📅 {t(TK.DASHBOARD_ADDED_THIS_MONTH)}"
            elif card_label in waiting_keys:
                formulations = self.db_manager.get_formulations_without_trials()
                title = f"⏳ {t(TK.DASHBOARD_WAITING_TEST)}"
            elif card_label in success_keys:
                # Başarılı için test sonuçlarını göster
                trials = self.db_manager.get_recent_trials(100)
                title = f"✅ {t(TK.DASHBOARD_SUCCESSFUL)}"
                if trials:
                    TrialListDialog(self.root, title, trials)
                else:
                    messagebox.showinfo(t(TK.common_info if hasattr(TK, 'common_info') else TK.INFO), f"{title}\n\n{t(TK.MSG_NO_PREV_TEST)}")
                self.status_bar.set_status(f"{card_label}: {len(trials)} test")
                return
            else:
                formulations = []
                title = t(TK.FORM_SAVED_FORMULAS)
            
            # Formülasyon popup aç
            if formulations:
                FormulationListDialog(
                    self.root, 
                    title, 
                    formulations,
                    on_edit=self._on_edit_formulation,
                    on_delete=self._on_delete_formulation
                )
            else:
                messagebox.showinfo("Bilgi", f"{title}\n\nHenüz formülasyon bulunmuyor.")
            
            self.status_bar.set_status(f"{card_label}: {len(formulations)} formülasyon")
            
        except Exception as e:
            self.status_bar.set_status(f"Hata: {str(e)}")
    
    def _on_quick_action(self, action: str, tab_index: int = None):
        """Hızlı işlem butonlarına tıklandığında"""
        if action == "new_formulation":
            self.notebook.select(2)  # Formülasyon sekmesi
            self.status_bar.set_status(t(TK.MSG_READY))
        elif action == "new_test":
            self.notebook.select(3)  # Test sonuçları sekmesi
            self.status_bar.set_status(t(TK.MSG_READY))
        elif action == "ml_predict":
            self.notebook.select(4)  # Optimizasyon sekmesi
            self.status_bar.set_status(t(TK.ML_AI_ENGINE))
        elif action == "report":
            self._generate_report()
        elif action == "import":
            self._import_file_dialog()
    
    def _import_file_dialog(self):
        """Dosya içe aktarma diyaloğu"""
        file_path = filedialog.askopenfilename(
            title="Dosya Seç",
            filetypes=[("Excel Dosyaları", "*.xlsx *.xls"), ("CSV Dosyaları", "*.csv"), ("Tüm Dosyalar", "*.*")]
        )
        if file_path:
            self._on_import(file_path)
    
    def _generate_report(self):
        """Rapor oluştur"""
        try:
            stats = self.db_manager.get_dashboard_stats()
            report = f"""
═══════════════════════════════════════
       FORMÜLASYON SİSTEMİ RAPORU
═══════════════════════════════════════

📊 İstatistikler:
  • Toplam Formül: {stats.get('Toplam Formül', 0)}
  • Bu Ay Eklenen: {stats.get('Bu Ay Eklenen', 0)}
  • Test Bekleyen: {stats.get('Test Bekleyen', 0)}
  • Test Edilmiş: {stats.get('Başarılı', 0)}

═══════════════════════════════════════
"""
            messagebox.showinfo("Rapor", report)
            self.status_bar.set_status("Rapor oluşturuldu")
        except Exception as e:
            messagebox.showerror("Hata", f"Rapor oluşturulamadı: {str(e)}")
    
    def _on_edit_formulation(self, formulation_id: int):
        """Formülasyonu düzenle - Formülasyon sekmesine yönlendir"""
        self.notebook.select(2)
        self.status_bar.set_status(f"Formülasyon #{formulation_id} düzenleniyor")
        # TODO: Formülasyon editörünü bu ID ile doldur
    
    def _on_delete_formulation(self, formulation_id: int):
        """Formülasyonu sil"""
        try:
            self.db_manager.delete_formulation(formulation_id)
            self.status_bar.set_status(f"{t(TK.FORM_SAVED_FORMULAS)} #{formulation_id} {t(TK.common_delete if hasattr(TK, 'common_delete') else TK.DELETE)}")
            # Dashboard güncelle
            self._refresh_dashboard()
        except Exception as e:
            messagebox.showerror(t(TK.common_error if hasattr(TK, 'common_error') else TK.ERROR), f"{t(TK.MSG_ERROR_SAVE)}: {str(e)}")
    
    def _refresh_dashboard(self):
        """Dashboard verilerini yenile"""
        try:
            stats = self.db_manager.get_dashboard_stats()
            monthly_data = self.db_manager.get_monthly_formulation_counts()
            insights = self.db_manager.get_dashboard_insights()
            self.dashboard.update_stats(stats, monthly_data, insights)
        except Exception:
            pass
    
    def _on_import(self, file_path: str):
        """Dosya import olayı - arka planda çalışır"""
        self.status_bar.set_status(f"İçe aktarılıyor: {os.path.basename(file_path)}")
        
        # Import işlemini arka planda çalıştır (UI donmasını önler)
        def do_import():
            try:
                from src.data_handlers.file_system_manager import FileSystemManager
                fs_manager = FileSystemManager()
                data = fs_manager.read_excel(file_path)
                
                # Veritabanına kaydet
                self.db_manager.import_data(data)
                
                # UI güncellemelerini ana thread'de yap
                def update_ui():
                    self._refresh_dashboard()
                    self.status_bar.set_status(f"İçe aktarma tamamlandı: {len(data)} kayıt")
                    messagebox.showinfo("Başarılı", f"{len(data)} kayıt içe aktarıldı!")
                
                self.root.after(0, update_ui)
                
            except Exception as e:
                def show_error():
                    self.status_bar.set_status(f"İçe aktarma hatası: {str(e)}")
                    messagebox.showerror("Hata", f"İçe aktarma başarısız: {str(e)}")
                self.root.after(0, show_error)
        
        # Arka plan thread'i başlat
        threading.Thread(target=do_import, daemon=True).start()
    
    def _on_save_trial(self, data: dict):
        """Deneme kaydetme olayı"""
        try:
            self.db_manager.save_trial(data)
            
            # Dashboard güncelle
            # Dashboard güncelle
            self._refresh_dashboard()
            
            self.status_bar.set_status("Deneme kaydedildi")
        except Exception as e:
            self.status_bar.set_status(f"Kaydetme hatası: {str(e)}")
            messagebox.showerror("Hata", f"Kaydetme başarısız: {str(e)}")
    
    def _on_get_recommendation(self, mode: str) -> str:
        """ML öneri alma olayı"""
        from src.ml_engine.router import MLRouter
        
        router = MLRouter(
            self.network_checker,
            self.config.get('ML', 'local_model', fallback=''),
            self.config.get('ML', 'api_endpoint', fallback='')
        )
        
        # Son verileri al
        recent_data = self.db_manager.get_recent_trials(limit=10)
        
        # Öneri al
        result = router.get_recommendation(recent_data, mode=mode)
        
        return result
    
    def _on_save_material(self, data: dict) -> int:
        """Malzeme kaydetme olayı"""
        try:
            material_id = self.db_manager.add_material(data)
            self.status_bar.set_status(f"Malzeme eklendi: {data['name']}")
            return material_id
        except Exception as e:
            self.status_bar.set_status(f"Malzeme ekleme hatası: {str(e)}")
            return 0
    
    def _on_delete_material(self):
        """Malzeme silme olayı"""
        self.status_bar.set_status("Malzeme silindi")
    
    def _on_material_list_change(self):
        """Malzeme listesi değiştiğinde çağrılır"""
        self.status_bar.set_status("Malzeme verileri güncellendi")
        # Malzeme cache'ini temizle
        if hasattr(self.db_manager, '_material_cache'):
            self.db_manager._material_cache = {}
            self.db_manager._material_cache_valid = False

    def _enrich_training_data_with_recipe(self, training_data: list) -> list:
        """Eğitim verilerini reçete özellikleri ile zenginleştir"""
        if not training_data:
            return []
            
        try:
            transformer = RecipeTransformer()
            enriched_data = []
            feature_names = transformer.get_feature_names()
            
            for row in training_data:
                new_row = row.copy()
                formulation_id = row.get('formulation_id')
                
                if formulation_id:
                    # Reçete ve özellikleri getir
                    recipe = self.db_manager.get_recipe_with_properties(formulation_id)
                    # Dönüştür
                    features = transformer.transform(recipe)
                    # Sözlüğe ekle
                    for name, val in zip(feature_names, features):
                        new_row[name] = val
                
                enriched_data.append(new_row)
                
            return enriched_data
        except Exception as e:
            logger.error(f"Veri zenginleştirme hatası: {e}")
            return training_data
    
    def _on_train_model(self) -> dict:
        """ML model eğitim olayı"""
        from src.ml_engine.continuous_learner import ContinuousLearner
        
        # Eğitim verilerini al (aktif proje varsa filtrele)
        if self.active_project_id:
            raw_data = self.db_manager.get_ml_training_data_by_project(self.active_project_id)
            project_info = f" (Proje: {self.active_project_name})"
        else:
            raw_data = self.db_manager.get_valid_ml_training_data()
            project_info = ""
            
        # Veriyi zenginleştir (Reçete özellikleri ekle)
        training_data = self._enrich_training_data_with_recipe(raw_data)
        
        # Model oluştur ve eğit
        learner = ContinuousLearner(os.path.join(self.app_dir, 'assets', 'models'))
        result = learner.train(training_data)
        if not result.get('success'):
            logger.warning(f"ML Eğitimi Başarısız: {result}")
        else:
            logger.info(f"ML Eğitimi Başarılı: {result.keys()}")
            
            # Durum detaylarını sonuca ekle
            status = learner.get_model_status()
            
            # R2 skorunu öncelikli hedeften al (status.update'den önce)
            targets_dict = result.get('targets', {})
            if targets_dict and isinstance(targets_dict, dict):
                # Quality score varsa onu kullan, yoksa ilk hedefi
                target_key = 'quality_score' if 'quality_score' in targets_dict else list(targets_dict.keys())[0]
                result['r2_score'] = targets_dict[target_key].get('r2_score', 0)
            
            # Status'u result'a ekle (targets key'ini koruyarak)
            status_targets = status.pop('targets', [])  # targets listesini çıkar
            result.update(status)
            result['target_names'] = status_targets  # farklı key ile ekle
            
            # Eğitim geçmişini kaydet
            try:
                self.db_manager.save_ml_training_history({
                    'samples_count': status.get('samples', 0),
                    'r2_score': result.get('r2_score', 0),
                    'targets': list(result.get('targets', {}).keys())
                })
            except Exception as e:
                logger.warning(f"Eğitim geçmişi kaydedilemedi: {e}")

        return result
    
    def _on_train_project_model(self, project_id: int, project_name: str) -> dict:
        """Proje bazlı ML model eğitimi"""
        from src.ml_engine.project_learner import ProjectLearner
        
        logger.info(f"Proje bazlı eğitim başlatıldı: {project_name} (ID: {project_id})")
        
        # Proje verilerini al
        raw_data = self.db_manager.get_ml_training_data_by_project(project_id)
        
        # Veriyi zenginleştir
        training_data = self._enrich_training_data_with_recipe(raw_data)
        
        if not training_data:
            return {
                'success': False,
                'message': f'"{project_name}" projesi için eğitim verisi bulunamadı.',
                'samples': 0
            }
        
        # Proje modeli oluştur ve eğit
        project_learner = ProjectLearner(
            os.path.join(self.app_dir, 'assets', 'models', 'projects')
        )
        result = project_learner.train_project_model(project_id, training_data, project_name)
        
        if result.get('success'):
            logger.info(f"Proje {project_name} modeli başarıyla eğitildi")
            self.status_bar.set_status(f"✅ {project_name} modeli eğitildi")
        else:
            logger.warning(f"Proje {project_name} eğitimi başarısız: {result.get('message')}")
        
        return result
    
    def _on_train_global_model(self) -> dict:
        """Global ML model eğitimi - Tüm projelerden öğrenme"""
        from src.ml_engine.global_learner import GlobalLearner
        
        logger.info("Global model eğitimi başlatıldı")
        
        # Tüm eğitim verilerini al
        raw_data = self.db_manager.get_valid_ml_training_data()
        
        # Veriyi zenginleştir
        all_training_data = self._enrich_training_data_with_recipe(raw_data)
        
        if not all_training_data:
            return {
                'success': False,
                'message': 'Hiç eğitim verisi bulunamadı.',
                'samples': 0
            }
        
        # Proje özetlerini hazırla
        projects = self.db_manager.get_all_projects()
        project_summaries = [{'id': p['id'], 'name': p['name']} for p in projects]
        
        # Global model oluştur ve eğit
        global_learner = GlobalLearner(
            os.path.join(self.app_dir, 'assets', 'models')
        )
        result = global_learner.train_global_model(all_training_data, project_summaries)
        
        if result.get('success'):
            logger.info(f"Global model başarıyla eğitildi. İçgörüler: {len(result.get('learned_patterns', []))}")
            self.status_bar.set_status("✅ Global model eğitildi")
        else:
            logger.warning(f"Global model eğitimi başarısız: {result.get('message')}")
        
        return result

    def _on_ml_predict(self, params: dict, model_type: str, project_id: int = None) -> dict:
        """ML modeli ile tahmin yap"""
        if model_type == "global":
            from src.ml_engine.global_learner import GlobalLearner
            learner = GlobalLearner(os.path.join(self.app_dir, 'assets', 'models'))
            return learner.predict(params)
        else:
            from src.ml_engine.project_learner import ProjectLearner
            learner = ProjectLearner(os.path.join(self.app_dir, 'assets', 'models', 'projects'))
            if project_id:
                return learner.predict_for_project(project_id, params)
            else:
                return {'success': False, 'message': 'Proje seçilmedi'}
    
    def _on_ml_recommend(self, action: str, material: str = None, category: str = None) -> dict:
        """ML bazlı öneri al"""
        from src.ml_engine.material_recommender import MaterialRecommender
        
        recommender = MaterialRecommender(
            os.path.join(self.app_dir, 'data_storage', 'chemical_knowledge.json'),
            os.path.join(self.app_dir, 'assets', 'models')
        )
        
        if action == 'alternatives':
            # Kategori dönüşümü
            category_map = {'Bağlayıcı': 'binder', 'Pigment': 'pigment', 'Dolgu': 'filler', 'Çözücü': 'solvent'}
            cat_code = category_map.get(category, 'binder')
            
            recommendations = recommender.recommend_alternatives(material, cat_code)
            return {'success': True, 'recommendations': recommendations}
        
        return {'success': False, 'message': 'Bilinmeyen aksiyon'}
    
    def _on_get_improvements(self, improvement_type: str, formulation: dict = None) -> dict:
        """Formülasyon iyileştirme önerileri al - Gerçek ML kullanır"""
        from src.ml_engine.material_recommender import MaterialRecommender
        
        recommender = MaterialRecommender(
            os.path.join(self.app_dir, 'data_storage', 'chemical_knowledge.json'),
            os.path.join(self.app_dir, 'assets', 'models')
        )
        
        # Aktif formülasyon verisi yoksa boş dict gönder
        if not formulation:
            formulation = {}
        
        try:
            suggestions = recommender.suggest_formulation_improvements(formulation, improvement_type)
            return {
                'success': True,
                'suggestions': suggestions,
                'improvement_type': improvement_type
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    def _on_find_similar_formulations(self, target_formulation: dict, top_n: int = 5) -> dict:
        """Benzer formülasyonları bul"""
        from src.ml_engine.material_recommender import MaterialRecommender
        
        recommender = MaterialRecommender(
            os.path.join(self.app_dir, 'data_storage', 'chemical_knowledge.json'),
            os.path.join(self.app_dir, 'assets', 'models')
        )
        
        # Formülasyon geçmişini al
        formulation_history = self.db_manager.get_valid_ml_training_data()
        
        try:
            similar = recommender.find_similar_formulations(
                target_formulation,
                formulation_history,
                top_n
            )
            return {
                'success': True,
                'similar_formulations': similar
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    def _on_get_project_status(self, project_id: int) -> dict:
        """Proje model durumunu getir"""
        from src.ml_engine.project_learner import ProjectLearner
        
        project_learner = ProjectLearner(
            os.path.join(self.app_dir, 'assets', 'models', 'projects')
        )
        
        try:
            status = project_learner.get_project_model_status(project_id)
            return status if status else {'success': False}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _on_get_global_status(self) -> dict:
        """Global model durumunu ve içgörüleri getir"""
        from src.ml_engine.global_learner import GlobalLearner
        
        global_learner = GlobalLearner(
            os.path.join(self.app_dir, 'assets', 'models')
        )
        
        try:
            status = global_learner.get_status()
            insights = global_learner.get_insights()
            if status:
                status['insights'] = insights
            return status if status else {'success': False}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    
    def _on_optimize(self, objectives: dict, constraints: dict) -> dict:
        """Çoklu hedef optimizasyon olayı"""
        from src.ml_engine.continuous_learner import ContinuousLearner
        from src.ml_engine.optimizer import MLOptimizer
        
        # Önce modeli yükle/eğit
        learner = ContinuousLearner(os.path.join(self.app_dir, 'assets', 'models'))
        
        # Model eğitilmemişse eğit
        if not learner.models:
            training_data = self.db_manager.get_ml_training_data()
            train_result = learner.train(training_data)
            
            if not train_result.get('success'):
                return train_result
        
        # Optimizer instance oluştur
        optimizer = MLOptimizer(learner, self.db_manager)
        
        # Proje kısıtlarını uygula
        project_id = self.active_project_id
        if constraints.get('scope') == 'project' and project_id:
            try:
                # Proje detaylarını çek (hedef maliyet vb.)
                project = self.db_manager.get_project(project_id)
                if project:
                    if project.get('target_cost'):
                         constraints['max_cost'] = float(project['target_cost'])
                    
                    # Log
                    logger.info(f"Proje kısıtları aktif: ID={project_id}, MaxCost={constraints.get('max_cost')}")
            except Exception as e:
                logger.error(f"Proje kısıtları uygulanamadı: {e}")

        # Malzeme fiyatlarını al
        material_costs = self.material_panel.get_price_dict() if hasattr(self, 'material_panel') else {}
        
        # Optimizasyonu çalıştır (MLOptimizer.optimize kullanmalıyız, learner değil)
        # NOT: Orijinal kodda learner.optimize_multi_objective kullanılıyordu, ama biz MLOptimizer'ı güncelledik.
        # Bu yüzden MLOptimizer.optimize çağırmalıyız.
        
        try:
             result = optimizer.optimize(objectives, project_id=project_id, constraints=constraints)
        except Exception as e:
             logger.error(f"Optimizasyon hatası: {e}")
             return {'success': False, 'message': str(e)}
        
        # En yakın reçeteyi bul (Active Learning / Inverse Design)
        if result.get('success'):
            try:
                optimal_params = result.get('optimal_params', {})
                nearest_trial = self.db_manager.find_nearest_trial(optimal_params)
                
                if nearest_trial:
                    result['nearest_trial'] = nearest_trial
                    
                    if nearest_trial.get('formulation_id'):
                        # Reçete detaylarını çek
                        recipe = self.db_manager.get_formulation_materials(nearest_trial['formulation_id'])
                        result['recommended_recipe'] = recipe
                        
                        # Formülasyon bilgilerini çek
                        form_info = self.db_manager.get_formulation(nearest_trial['formulation_id'])
                        result['recommended_formulation'] = form_info
            except Exception as e:
                pass  # Öneri hatası ana işlemi durdurmasın
        
        self.status_bar.set_status("Optimizasyon tamamlandı" if result.get('success') else "Optimizasyon başarısız")
        return result
    
    def _on_predict_test_results(self, params: dict) -> dict:
        """Test sonuçlarını tahmin et"""
        from src.ml_engine.continuous_learner import ContinuousLearner
        
        # Model yükle
        learner = ContinuousLearner(os.path.join(self.app_dir, 'assets', 'models'))
        
        # Model eğitilmemişse eğit
        if not learner.models:
            training_data = self.db_manager.get_ml_training_data()
            train_result = learner.train(training_data)
            
            if not train_result.get('success'):
                return train_result
        
        # Tahmin yap
        result = learner.predict(params)
        
        self.status_bar.set_status("Tahmin tamamlandı" if result.get('success') else "Tahmin başarısız")
        return result
    
    def _on_save_formulation(self, data: dict):
        """Formülasyonu kaydet"""
        try:
            formula_code = data.get('formula_code', '')
            existing = self.db_manager.get_formulation_by_code(formula_code)
            
            formulation_id = 0
            
            if existing:
                msg = f"'{formula_code}' kodlu bir formülasyon zaten mevcut.\n\n" \
                      "[Evet]: Mevcut kaydın üzerine yaz\n" \
                      "[Hayır]: Yeni revizyon oluştur\n" \
                      "[İptal]: İşlemi iptal et"
                choice = messagebox.askyesnocancel("Kayıt Çakışması", msg)
                
                if choice is None: # İptal
                    return
                    
                if choice: # Evet -> Overwrite
                    formulation_id = existing['id']
                    # Başlığı güncelle
                    self.db_manager.update_formulation(formulation_id, {
                        'formula_name': data.get('formula_name', ''),
                        'status': 'draft'
                    })
                    # Bileşenleri temizle
                    self.db_manager.delete_formulation_components(formulation_id)
                    
                else: # Hayır -> Revision
                    # Yeni kod üret
                    import re
                    match = re.match(r"(.*)-REV(\d+)$", formula_code)
                    if match:
                        base = match.group(1)
                        rev = int(match.group(2)) + 1
                        new_code = f"{base}-REV{rev}"
                    else:
                        new_code = f"{formula_code}-REV1"
                    
                    messagebox.showinfo("Revizyon", f"Yeni revizyon oluşturuluyor: {new_code}")
                    data['formula_code'] = new_code
                    
                    # Create new
                    formulation_id = self.db_manager.create_formulation(
                        project_id=None,
                        data={
                            'formula_code': new_code,
                            'formula_name': data.get('formula_name', ''),
                            'status': 'draft'
                        }
                    )
            else:
                # Yeni kayıt
                formulation_id = self.db_manager.create_formulation(
                    project_id=None,  # Aktif proje yoksa None
                    data={
                        'formula_code': formula_code,
                        'formula_name': data.get('formula_name', ''),
                        'status': 'draft'
                    }
                )
            
            # Bileşenleri kaydet
            for comp in data.get('components', []):
                self.db_manager.add_component(formulation_id, {
                    'component_name': comp.get('name', ''),
                    'component_type': comp.get('code', ''),
                    'amount': comp.get('amount', 0), # Total amount
                    'percentage': comp.get('percentage', 0),
                    'unit': 'kg'
                })
            
            self.status_bar.set_status(f"Formülasyon kaydedildi: {data.get('formula_code', '')}")
            
            # Dashboard güncelle
            # Dashboard güncelle
            self._refresh_dashboard()
            
            # Güncel formülasyon listesi (only from active projects)
            formulations = self.db_manager.get_active_formulations()
            
            # Test sonuçları panelindeki formülasyon listesini güncelle
            if hasattr(self, 'test_results_panel'):
                self.test_results_panel.load_formulations(formulations)
            
            # Formülasyon editöründeki dropdown'ı güncelle
            if hasattr(self, 'formulation_editor'):
                self.formulation_editor.load_formulation_list(formulations)
            
            # Trigger background ML learning
            self._trigger_background_learning(
                project_id=self.active_project_id,
                formulation_data=data
            )
            
            return True  # Indicate success
            
        except Exception as e:
            self.status_bar.set_status(f"Kaydetme hatası: {str(e)}")
    
    def _on_calculate_formulation(self, data: dict):
        """Formülasyon hesaplama"""
        total_cost = data.get('total_cost', 0)
        total_percent = data.get('total_percent', 0)
        
        self.status_bar.set_status(
            f"Hesaplandı: %{total_percent:.1f} - Toplam Maliyet: {total_cost:.2f} birim"
        )
    
    def _on_save_test_results(self, data: dict):
        """Test sonuçlarını kaydet"""
        try:
            # Trial olarak kaydet
            trial_data = {
                'formulation_id': None,
                'trial_date': data.get('date'),
                'coating_thickness': data['coating'].get('coating_thickness'),
                'notes': data.get('notes', '')
            }
            
            # Test sonuçlarını ekle
            for key, value in data.get('results', {}).items():
                trial_data[key] = value
            
            self.db_manager.save_trial(trial_data)
            
            # ML modeli yeni veri ile güncelle (arka planda)
            self._refresh_dashboard()
            self.status_bar.set_status(f"Test sonuçları kaydedildi")
            
            # Dashboard güncelle
            stats = self.db_manager.get_dashboard_stats()
            self.dashboard.update_stats(stats)
            
            # Trigger background ML learning with new test data
            self._trigger_background_learning(
                project_id=self.active_project_id,
                formulation_data=trial_data
            )
            
        except Exception as e:
            self.status_bar.set_status(f"Kaydetme hatası: {str(e)}")
    
    def _on_load_formulations(self, project_name: str) -> list:
        """Proje için formülasyonları yükle"""
        try:
            # Formülasyonları getir (only from active projects)
            formulations = self.db_manager.get_active_formulations()
            return [f.get('formula_code', f.get('name', '')) for f in formulations]
        except Exception as e:
            self.status_bar.set_status(f"Formülasyon yükleme hatası: {str(e)}")
            return []
    
    def _on_load_trial(self, formula_code: str) -> dict:
        """Formül kodu için mevcut test verilerini yükle"""
        try:
            trial_data = self.db_manager.get_latest_trial_by_formula_code(formula_code)
            return trial_data
        except Exception as e:
            self.status_bar.set_status(f"Test verisi yükleme hatası: {str(e)}")
            return None
    def _on_apply_formulation_from_recommendation(self, result: dict):
        """Önerilen reçeteyi formülasyon editörüne aktar"""
        recipe = result.get('recommended_recipe')
        form_info = result.get('recommended_formulation', {})
        
        if not recipe:
            return
            
        # Formülasyon verisini hazırla
        # FormulationEditor.load_formulation component yapısını bekler
        data = {
            'formula_code': f"AI-{form_info.get('formula_code', 'REC')}",
            'formula_name': f"Öneri: {form_info.get('formula_name', 'Bilinmiyor')}",
            'components': recipe
        }
        
        # Sekmeyi değiştir (Index 2: Formülasyon)
        self.notebook.select(2) 
        
        # Editöre yükle
        if hasattr(self, 'formulation_editor'):
            # Küçük bir gecikme ile yükle ki UI render olsun
            def do_load():
                self.formulation_editor.load_formulation(data)
                self.status_bar.set_status("Önerilen formülasyon editöre yüklendi")
                messagebox.showinfo("Bilgi", "Önerilen reçete editöre aktarıldı.\nLütfen oranları kontrol edip kaydedin.")
            
            self.root.after(100, do_load)
            
    def _on_load_detailed_formulation(self, trial_id: int) -> dict:
        """Load trial details and recipe into Formulation Editor"""
        try:
            # Use new function that properly JOINs with materials
            data = self.db_manager.get_trial_with_materials(trial_id)
            
            if data:
                # Load into editor
                self.formulation_editor.load_formulation(data)
                self.status_bar.set_status(f"Deneme yüklendi: {data.get('formula_code', '')}")
                return data
            else:
                self.status_bar.set_status(f"Deneme bulunamadı: ID {trial_id}")
                return {}
        except Exception as e:
            logger.error(f"Trial loading error: {e}")
            self.status_bar.set_status(f"Detay yükleme hatası: {str(e)}")
            return {}
    
    def run(self):
        """Uygulamayı çalıştır"""
        self.root.mainloop()
    def _on_generate_recipe(self, targets: dict) -> dict:
        """ML ile reçete optimizasyonu (Genetik Algoritma)
        
        Validates that the model is properly trained before attempting optimization.
        Does NOT auto-train to avoid unreliable results with insufficient data.
        """
        from src.ml_engine.optimizer import MLOptimizer
        from src.ml_engine.continuous_learner import ContinuousLearner
        
        logger.info(f"Reçete optimizasyonu başlatıldı. Hedefler: {targets}")
        
        try:
            # =====================================================
            # PRE-FLIGHT VALIDATION - Check before optimization
            # =====================================================
            
            # 1. Check if we have any formulation data
            training_data = self.db_manager.get_ml_training_data()
            if not training_data or len(training_data) < 3:
                return {
                    'success': False,
                    'message': f'Yetersiz veri: En az 3 formülasyon kaydı gerekli. Mevcut: {len(training_data) if training_data else 0}. '
                              f'Lütfen "Formülasyon" ve "Test Sonuçları" sekmelerinden veri girin.',
                    'error_code': 'INSUFFICIENT_DATA'
                }
            
            # 2. Load learner (do NOT auto-train)
            learner = ContinuousLearner(os.path.join(self.app_dir, 'assets', 'models'))
            
            # 3. Check if model is trained
            if not learner.models:
                return {
                    'success': False,
                    'message': 'ML modeli eğitilmedi. Lütfen önce "Optimizasyon&ML" sekmesinden modeli eğitin.\n\n'
                              'Adımlar:\n'
                              '1. "Optimizasyon&ML" sekmesine gidin\n'
                              '2. "ML Model Durumu" panelinden projeyi seçin\n'
                              '3. "Projeyi Eğit" veya "Global Eğit" butonuna basın',
                    'error_code': 'MODEL_NOT_TRAINED'
                }
            
            # 4. Validate targets
            if not targets:
                return {
                    'success': False,
                    'message': 'En az bir hedef seçmelisiniz.',
                    'error_code': 'NO_TARGETS'
                }
            
            # =====================================================
            # OPTIMIZATION - Proceed with validated model
            # =====================================================
            
            # Optimizer başlat
            optimizer = MLOptimizer(learner, self.db_manager)
            
            # Proje ID (İsteğe bağlı)
            project_id = self.active_project_id
            
            # Çalıştır
            result = optimizer.optimize(targets, project_id=project_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Optimizasyon hatası: {e}")
            return {'success': False, 'message': str(e)}


    def _on_apply_optimization_recipe(self, recipe: list):
        """Önerilen reçeteyi Formülasyon Editörüne aktar"""
        if not recipe:
            messagebox.showwarning("Uyarı", "Aktarılacak reçete bulunamadı.")
            return
            
        # Formülasyon sekmesine geç
        self.notebook.select(2)  # "Formülasyon" sekmesi (index 2)
        
        # Formülasyon editörüne bileşenleri aktar
        try:
            # Mevcut bileşenleri temizle
            self.formulation_editor.clear_components()
            
            # Yeni bileşenleri ekle
            for comp in recipe:
                material_code = comp.get('code', comp.get('id', ''))
                material_name = comp.get('name', '')
                amount = comp.get('amount', 0)
                
                # Formülasyon editörüne satır ekle
                self.formulation_editor.add_component_row(
                    code=str(material_code),
                    name=material_name,
                    percentage=amount
                )
            
            messagebox.showinfo(t(TK.common_success if hasattr(TK, 'common_success') else TK.SUCCESS), f"{len(recipe)} {t(TK.MAT_TITLE)} {t(TK.MSG_SAVE_SUCCESS if hasattr(TK, 'MSG_SAVE_SUCCESS') else TK.SUCCESS)}")
            
        except AttributeError as e:
            # Formülasyon editöründe gerekli metodlar yoksa
            logger.warning(f"Formülasyon editörü uyumsuz: {e}")
            messagebox.showwarning(t(TK.common_warning if hasattr(TK, 'common_warning') else TK.WARNING), t(TK.MSG_CHOOSE_FORMULATION))
