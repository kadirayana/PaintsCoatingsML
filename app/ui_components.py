"""
Paint Formulation AI - UI Bileşenleri
=====================================
Tkinter tabanlı kullanıcı arayüzü bileşenleri
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from configparser import ConfigParser
from typing import Optional, Callable
import threading


class ModernButton(ttk.Button):
    """Modern görünümlü özelleştirilmiş buton"""
    def __init__(self, parent, text, command=None, style="Modern.TButton", **kwargs):
        super().__init__(parent, text=text, command=command, style=style, **kwargs)


class StatusBar(ttk.Frame):
    """Durum çubuğu bileşeni"""
    def __init__(self, parent):
        super().__init__(parent)
        
        self.status_label = ttk.Label(self, text="Hazır", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.connection_label = ttk.Label(self, text="⚫ Offline", anchor=tk.E)
        self.connection_label.pack(side=tk.RIGHT, padx=5)
    
    def set_status(self, message: str):
        """Durum mesajını güncelle"""
        self.status_label.config(text=message)
    
    def set_online(self, is_online: bool):
        """Bağlantı durumunu güncelle"""
        if is_online:
            self.connection_label.config(text="🟢 Online", foreground="green")
        else:
            self.connection_label.config(text="🔴 Offline", foreground="red")


class ProjectPanel(ttk.LabelFrame):
    """Proje yönetim paneli"""
    def __init__(self, parent, on_project_change: Callable = None):
        super().__init__(parent, text="📁 Proje Yönetimi", padding=10)
        
        self.on_project_change = on_project_change
        self.current_project = None
        
        # Proje listesi
        self.project_listbox = tk.Listbox(self, height=8)
        self.project_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Butonlar
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="Yeni Proje", command=self.new_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Aç", command=self.open_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Sil", command=self.delete_project).pack(side=tk.LEFT, padx=2)
    
    def new_project(self):
        """Yeni proje oluştur"""
        dialog = ProjectDialog(self, "Yeni Proje Oluştur")
        if dialog.result:
            self.project_listbox.insert(tk.END, dialog.result['name'])
            if self.on_project_change:
                self.on_project_change(dialog.result)
    
    def open_project(self):
        """Seçili projeyi aç"""
        selection = self.project_listbox.curselection()
        if selection:
            project_name = self.project_listbox.get(selection[0])
            self.current_project = project_name
            if self.on_project_change:
                self.on_project_change({'name': project_name, 'action': 'open'})
    
    def delete_project(self):
        """Seçili projeyi sil"""
        selection = self.project_listbox.curselection()
        if selection:
            if messagebox.askyesno("Onay", "Bu projeyi silmek istediğinizden emin misiniz?"):
                self.project_listbox.delete(selection[0])
    
    def load_projects(self, projects: list):
        """Proje listesini yükle"""
        self.project_listbox.delete(0, tk.END)
        for project in projects:
            self.project_listbox.insert(tk.END, project['name'])


class ProjectDialog(tk.Toplevel):
    """Proje oluşturma diyaloğu"""
    def __init__(self, parent, title):
        super().__init__(parent)
        self.title(title)
        self.result = None
        self.geometry("400x200")
        self.transient(parent)
        self.grab_set()
        
        # Proje adı
        ttk.Label(self, text="Proje Adı:").pack(pady=(20, 5))
        self.name_entry = ttk.Entry(self, width=40)
        self.name_entry.pack(pady=5)
        
        # Açıklama
        ttk.Label(self, text="Açıklama:").pack(pady=5)
        self.desc_entry = ttk.Entry(self, width=40)
        self.desc_entry.pack(pady=5)
        
        # Butonlar
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Oluştur", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="İptal", command=self.destroy).pack(side=tk.LEFT, padx=5)
        
        self.name_entry.focus_set()
        self.wait_window()
    
    def on_ok(self):
        name = self.name_entry.get().strip()
        if name:
            self.result = {
                'name': name,
                'description': self.desc_entry.get().strip()
            }
            self.destroy()
        else:
            messagebox.showwarning("Uyarı", "Proje adı boş olamaz!")


class DataImportPanel(ttk.LabelFrame):
    """Veri import paneli"""
    def __init__(self, parent, on_import: Callable = None):
        super().__init__(parent, text="📊 Veri İçe Aktarma", padding=10)
        
        self.on_import = on_import
        
        # Sürükle bırak alanı
        self.drop_frame = ttk.Frame(self, relief="groove", borderwidth=2)
        self.drop_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        drop_label = ttk.Label(
            self.drop_frame, 
            text="📁 Excel dosyasını buraya sürükleyin\nveya aşağıdaki butonu kullanın",
            justify=tk.CENTER
        )
        drop_label.pack(expand=True, pady=30)
        
        # Butonlar
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="Excel Dosyası Seç", command=self.select_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="CSV Dosyası Seç", command=self.select_csv).pack(side=tk.LEFT, padx=2)
    
    def select_file(self):
        """Excel dosyası seç"""
        file_path = filedialog.askopenfilename(
            title="Excel Dosyası Seç",
            filetypes=[("Excel Dosyaları", "*.xlsx *.xls"), ("Tüm Dosyalar", "*.*")]
        )
        if file_path:
            self._import_file(file_path)
    
    def select_csv(self):
        """CSV dosyası seç"""
        file_path = filedialog.askopenfilename(
            title="CSV Dosyası Seç",
            filetypes=[("CSV Dosyaları", "*.csv"), ("Tüm Dosyalar", "*.*")]
        )
        if file_path:
            self._import_file(file_path)
    
    def _import_file(self, file_path: str):
        """Dosyayı import et"""
        if self.on_import:
            self.on_import(file_path)


class DashboardPanel(ttk.LabelFrame):
    """Dashboard paneli"""
    def __init__(self, parent):
        super().__init__(parent, text="📈 Dashboard", padding=10)
        
        # İstatistik kartları
        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stat_cards = {}
        stats = [
            ("Toplam Formül", "0"),
            ("Bu Ay Eklenen", "0"),
            ("Test Bekleyen", "0"),
            ("Başarılı", "0")
        ]
        
        for i, (label, value) in enumerate(stats):
            card = self._create_stat_card(stats_frame, label, value)
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            self.stat_cards[label] = card
            stats_frame.columnconfigure(i, weight=1)
        
        # Grafik alanı (placeholder)
        self.chart_frame = ttk.Frame(self, relief="sunken", borderwidth=1)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)
        
        chart_placeholder = ttk.Label(
            self.chart_frame, 
            text="📊 Grafikler burada görüntülenecek\n(matplotlib entegrasyonu gerekli)",
            justify=tk.CENTER
        )
        chart_placeholder.pack(expand=True)
    
    def _create_stat_card(self, parent, label: str, value: str) -> ttk.Frame:
        """İstatistik kartı oluştur"""
        card = ttk.Frame(parent, relief="raised", borderwidth=1, padding=10)
        
        ttk.Label(card, text=value, font=("Helvetica", 24, "bold")).pack()
        ttk.Label(card, text=label, font=("Helvetica", 10)).pack()
        
        return card
    
    def update_stats(self, stats: dict):
        """İstatistikleri güncelle"""
        for label, card in self.stat_cards.items():
            if label in stats:
                for widget in card.winfo_children():
                    if isinstance(widget, ttk.Label):
                        font = widget.cget('font')
                        if 'bold' in str(font):
                            widget.config(text=str(stats[label]))
                            break


class MLRecommendationPanel(ttk.LabelFrame):
    """ML Öneri paneli"""
    def __init__(self, parent, on_get_recommendation: Callable = None):
        super().__init__(parent, text="🤖 ML Öneri Sistemi", padding=10)
        
        self.on_get_recommendation = on_get_recommendation
        
        # Mod seçimi
        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(mode_frame, text="Mod:").pack(side=tk.LEFT)
        
        self.mode_var = tk.StringVar(value="auto")
        modes = [("Otomatik", "auto"), ("Lokal", "local"), ("Online", "online")]
        for text, value in modes:
            ttk.Radiobutton(mode_frame, text=text, variable=self.mode_var, value=value).pack(side=tk.LEFT, padx=10)
        
        # Öneri butonu
        self.recommend_btn = ttk.Button(
            self, 
            text="🔮 ML Öneri Al",
            command=self._get_recommendation
        )
        self.recommend_btn.pack(fill=tk.X, pady=10)
        
        # Sonuç alanı
        ttk.Label(self, text="Öneriler:").pack(anchor=tk.W)
        
        self.result_text = tk.Text(self, height=10, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        self.result_text.insert(tk.END, "ML önerileri burada görüntülenecek...")
        self.result_text.config(state=tk.DISABLED)
    
    def _get_recommendation(self):
        """ML önerisi al"""
        if self.on_get_recommendation:
            self.result_text.config(state=tk.NORMAL)
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "Öneri hesaplanıyor...\n")
            self.result_text.config(state=tk.DISABLED)
            
            # Öneriyi arka planda al
            mode = self.mode_var.get()
            threading.Thread(
                target=self._fetch_recommendation,
                args=(mode,),
                daemon=True
            ).start()
    
    def _fetch_recommendation(self, mode: str):
        """Arka planda öneri al"""
        try:
            if self.on_get_recommendation:
                result = self.on_get_recommendation(mode)
                self._display_result(result)
        except Exception as e:
            self._display_result(f"Hata: {str(e)}")
    
    def _display_result(self, result: str):
        """Sonucu göster"""
        def update():
            self.result_text.config(state=tk.NORMAL)
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, result)
            self.result_text.config(state=tk.DISABLED)
        
        self.after(0, update)


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


class PaintFormulationApp:
    """Ana uygulama sınıfı"""
    def __init__(self, config: ConfigParser, db_manager, network_checker, app_dir: str):
        self.config = config
        self.db_manager = db_manager
        self.network_checker = network_checker
        self.app_dir = app_dir
        
        # Ana pencere
        self.root = tk.Tk()
        self.root.title(f"{config.get('Application', 'name', fallback='Paint Formulation AI')} v{config.get('Application', 'version', fallback='1.0')}")
        
        # Pencere boyutu
        width = config.getint('UI', 'window_width', fallback=1200)
        height = config.getint('UI', 'window_height', fallback=800)
        self.root.geometry(f"{width}x{height}")
        
        # Tema
        self._setup_theme()
        
        # UI oluştur
        self._create_ui()
        
        # Başlangıç verileri
        self._load_initial_data()
    
    def _setup_theme(self):
        """Tema ayarlarını uygula"""
        style = ttk.Style()
        
        theme = self.config.get('UI', 'theme', fallback='dark')
        
        if theme == 'dark':
            self.root.configure(bg='#2b2b2b')
            style.configure('TFrame', background='#2b2b2b')
            style.configure('TLabel', background='#2b2b2b', foreground='white')
            style.configure('TLabelframe', background='#2b2b2b', foreground='white')
            style.configure('TLabelframe.Label', background='#2b2b2b', foreground='white')
    
    def _create_ui(self):
        """Kullanıcı arayüzünü oluştur"""
        # Notebook (Sekmeli yapı)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # === SEKME 1: Ana Sayfa ===
        main_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(main_tab, text="🏠 Ana Sayfa")
        
        # Sol panel - Proje ve Import
        left_panel = ttk.Frame(main_tab)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        self.project_panel = ProjectPanel(left_panel, self._on_project_change)
        self.project_panel.pack(fill=tk.X, pady=(0, 10))
        
        self.import_panel = DataImportPanel(left_panel, self._on_import)
        self.import_panel.pack(fill=tk.X)
        
        # Orta panel - Dashboard
        center_panel = ttk.Frame(main_tab)
        center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.dashboard = DashboardPanel(center_panel)
        self.dashboard.pack(fill=tk.BOTH, expand=True)
        
        # Sağ panel - ML Öneri
        right_panel = ttk.Frame(main_tab)
        right_panel.pack(side=tk.LEFT, fill=tk.Y)
        
        self.ml_panel = MLRecommendationPanel(right_panel, self._on_get_recommendation)
        self.ml_panel.pack(fill=tk.BOTH, expand=True)
        
        # === SEKME 2: Formülasyon ===
        from app.formulation_editor import FormulationEditorPanel
        
        formulation_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(formulation_tab, text="📋 Formülasyon")
        
        self.formulation_editor = FormulationEditorPanel(
            formulation_tab, 
            self._on_save_formulation,
            self._on_calculate_formulation
        )
        self.formulation_editor.pack(fill=tk.BOTH, expand=True)
        
        # === SEKME 3: Test Sonuçları ===
        from app.test_results_panel import TestResultsPanel
        
        test_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(test_tab, text="🧪 Test Sonuçları")
        
        self.test_results_panel = TestResultsPanel(
            test_tab, 
            self._on_save_test_results,
            self._on_load_formulations
        )
        self.test_results_panel.pack(fill=tk.BOTH, expand=True)
        
        # === SEKME 4: Optimizasyon ===
        from app.optimization_panels import MultiObjectiveOptimizationPanel, MLStatusPanel
        
        opt_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(opt_tab, text="🎯 Optimizasyon")
        
        # Sol - ML Durumu
        opt_left = ttk.Frame(opt_tab)
        opt_left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        self.ml_status_panel = MLStatusPanel(opt_left, self._on_train_model)
        self.ml_status_panel.pack(fill=tk.X)
        
        # Sağ - Çoklu Hedef Optimizasyonu
        opt_right = ttk.Frame(opt_tab)
        opt_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.optimization_panel = MultiObjectiveOptimizationPanel(opt_right, self._on_optimize)
        self.optimization_panel.pack(fill=tk.BOTH, expand=True)
        
        # Formülasyon editörüne tahmin callback bağla
        if hasattr(self, 'formulation_editor'):
            self.formulation_editor.set_prediction_callback(self._on_predict_test_results)
        
        # Durum çubuğu
        self.status_bar = StatusBar(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bağlantı durumu
        is_online = self.network_checker.check_connection()
        self.status_bar.set_online(is_online)
    
    def _load_initial_data(self):
        """Başlangıç verilerini yükle"""
        try:
            projects = self.db_manager.get_all_projects()
            self.project_panel.load_projects(projects)
            
            # Projeleri tüm panellere yükle
            if hasattr(self, 'optimization_panel'):
                self.optimization_panel.load_projects(projects)
            
            if hasattr(self, 'formulation_editor'):
                self.formulation_editor.load_projects(projects)
            
            if hasattr(self, 'test_results_panel'):
                self.test_results_panel.load_projects(projects)
                # Formülasyonları da yükle
                formulations = self.db_manager.get_all_formulations()
                self.test_results_panel.load_formulations(formulations)
            
            stats = self.db_manager.get_dashboard_stats()
            self.dashboard.update_stats(stats)
            
            # Özel test metodlarını optimizasyon hedeflerine yükle
            if hasattr(self, 'optimization_panel'):
                self.optimization_panel.load_custom_objectives()
            
            self.status_bar.set_status("Veriler yüklendi")
        except Exception as e:
            self.status_bar.set_status(f"Veri yükleme hatası: {str(e)}")
    
    def _on_project_change(self, project_data: dict):
        """Proje değişikliği olayı"""
        if 'action' in project_data and project_data['action'] == 'open':
            self.status_bar.set_status(f"Proje açıldı: {project_data['name']}")
        else:
            # Yeni proje oluştur
            self.db_manager.create_project(project_data)
            self.status_bar.set_status(f"Proje oluşturuldu: {project_data['name']}")
    
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
                    stats = self.db_manager.get_dashboard_stats()
                    self.dashboard.update_stats(stats)
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
            stats = self.db_manager.get_dashboard_stats()
            self.dashboard.update_stats(stats)
            
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
    
    def _on_train_model(self) -> dict:
        """ML model eğitim olayı"""
        from src.ml_engine.continuous_learner import ContinuousLearner
        
        # Eğitim verilerini al
        training_data = self.db_manager.get_ml_training_data()
        
        # Model oluştur ve eğit
        learner = ContinuousLearner(os.path.join(self.app_dir, 'assets', 'models'))
        result = learner.train(training_data)
        
        # Durumu güncelle
        if result.get('success'):
            status = learner.get_model_status()
            status['samples'] = len(training_data)
            if result.get('targets'):
                first_target = list(result['targets'].keys())[0]
                status['r2_score'] = result['targets'][first_target].get('r2_score', 0)
            self.ml_status_panel.update_status(status)
            
            # Eğitim geçmişini kaydet
            self.db_manager.save_ml_training_history({
                'samples_count': len(training_data),
                'r2_score': status.get('r2_score', 0),
                'targets': list(result.get('targets', {}).keys())
            })
        
        self.status_bar.set_status("Model eğitimi tamamlandı" if result.get('success') else "Model eğitimi başarısız")
        return result
    
    def _on_optimize(self, objectives: dict, constraints: dict) -> dict:
        """Çoklu hedef optimizasyon olayı"""
        from src.ml_engine.continuous_learner import ContinuousLearner
        
        # Önce modeli yükle/eğit
        learner = ContinuousLearner(os.path.join(self.app_dir, 'assets', 'models'))
        
        # Model eğitilmemişse eğit
        if not learner.models:
            training_data = self.db_manager.get_ml_training_data()
            train_result = learner.train(training_data)
            
            if not train_result.get('success'):
                return train_result
        
        # Malzeme fiyatlarını al
        material_costs = self.materials_panel.get_price_dict() if hasattr(self, 'materials_panel') else {}
        
        # Optimizasyonu çalıştır
        result = learner.optimize_multi_objective(
            objectives=objectives,
            constraints=constraints,
            material_costs=material_costs
        )
        
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
            # Formülasyonu veritabanına kaydet
            formulation_id = self.db_manager.create_formulation(
                project_id=None,  # Aktif proje yoksa None
                data={
                    'formula_code': data.get('formula_code', ''),
                    'formula_name': data.get('formula_name', ''),
                    'status': 'draft'
                }
            )
            
            # Bileşenleri kaydet
            for comp in data.get('components', []):
                self.db_manager.add_component(formulation_id, {
                    'component_name': comp.get('name', ''),
                    'component_type': comp.get('code', ''),
                    'amount': comp.get('solid_amount', 0),
                    'percentage': comp.get('percentage', 0)
                })
            
            self.status_bar.set_status(f"Formülasyon kaydedildi: {data.get('formula_code', '')}")
            
            # Dashboard güncelle
            stats = self.db_manager.get_dashboard_stats()
            self.dashboard.update_stats(stats)
            
            # Test sonuçları panelindeki formülasyon listesini güncelle
            if hasattr(self, 'test_results_panel'):
                formulations = self.db_manager.get_all_formulations()
                formula_names = [f.get('formula_code', f.get('name', '')) for f in formulations]
                self.test_results_panel.load_formulations(formulations)
            
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
            self.status_bar.set_status(f"Test sonuçları kaydedildi")
            
            # Dashboard güncelle
            stats = self.db_manager.get_dashboard_stats()
            self.dashboard.update_stats(stats)
            
        except Exception as e:
            self.status_bar.set_status(f"Kaydetme hatası: {str(e)}")
    
    def _on_load_formulations(self, project_name: str) -> list:
        """Proje için formülasyonları yükle"""
        try:
            # Tüm formülasyonları getir (proje filtrelemesi DB'de yapılabilir)
            formulations = self.db_manager.get_all_formulations()
            return [f.get('formula_code', f.get('name', '')) for f in formulations]
        except Exception as e:
            self.status_bar.set_status(f"Formülasyon yükleme hatası: {str(e)}")
            return []
    
    def run(self):
        """Uygulamayı çalıştır"""
        self.root.mainloop()
