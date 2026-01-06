"""
Paint Formulation AI - Gelişmiş Optimizasyon Paneli
====================================================
ML eğitimi, tahmin ve akıllı öneriler için entegre panel
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, List, Optional
import threading


class AdvancedMLPanel(ttk.Frame):
    """
    Gelişmiş ML Paneli - Proje bazlı eğitim, global öğrenme ve akıllı öneriler
    
    İç sekmeler:
    1. Eğitim - Proje/Global model eğitimi
    2. Tahmin - Formülasyon sonuç tahmini
    3. Öneriler - Malzeme ve formülasyon önerileri
    """
    
    def __init__(self, parent, 
                 on_train_project: Callable = None,
                 on_train_global: Callable = None,
                 on_predict: Callable = None,
                 on_recommend: Callable = None,
                 on_get_improvements: Callable = None,
                 on_find_similar: Callable = None,
                 on_get_project_status: Callable = None,
                 on_get_global_status: Callable = None,
                 on_generate_recipe: Callable = None,
                 on_apply_recipe: Callable = None): # Reçeteyi uygula callback'i
        super().__init__(parent)
        
        self.on_train_project = on_train_project
        self.on_train_global = on_train_global
        self.on_predict = on_predict
        self.on_recommend = on_recommend
        self.on_get_improvements = on_get_improvements
        self.on_find_similar = on_find_similar
        self.on_get_project_status = on_get_project_status
        self.on_get_global_status = on_get_global_status
        self.on_generate_recipe = on_generate_recipe
        self.on_apply_recipe = on_apply_recipe
        
        self.current_project_id = None
        self.current_project_name = None
        self.project_list = []
        
        self._create_ui()
        
        # Sayfa açılışında model durumlarını yükle
        self.after(500, self.refresh_model_statuses)
    
    def _create_ui(self):
        """UI oluştur"""
        # Başlık
        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            header, 
            text="🧠 Makine Öğrenmesi Merkezi",
            font=('Helvetica', 14, 'bold')
        ).pack(side=tk.LEFT)
        
        # İç sekmeler
        self.inner_notebook = ttk.Notebook(self)
        self.inner_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Sekme 1: Eğitim
        self.training_tab = self._create_training_tab()
        self.inner_notebook.add(self.training_tab, text="📚 Eğitim")
        
        # Sekme 2: Tahmin
        self.prediction_tab = self._create_prediction_tab()
        self.inner_notebook.add(self.prediction_tab, text="🔮 Tahmin")
        
        # Sekme 3: Öneriler
        self.recommendation_tab = self._create_recommendation_tab()
        self.inner_notebook.add(self.recommendation_tab, text="💡 Öneriler")
        
        # Note: Optimization tab removed - feature available in main "Optimizasyon" tab
    
    def _create_training_tab(self) -> ttk.Frame:
        """Eğitim sekmesi - Clean 2-column layout"""
        tab = ttk.Frame(self.inner_notebook, padding=15)
        
        # Main 2-column grid
        tab.columnconfigure(0, weight=1) # Training Controls (Left)
        tab.columnconfigure(1, weight=1) # Learned Insights (Right)
        tab.rowconfigure(0, weight=1)
        
        # =====================================================
        # LEFT COLUMN: Training Controls
        # =====================================================
        left_column = ttk.Frame(tab)
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # 1. Project Based Training Section
        project_frame = ttk.LabelFrame(left_column, text="📁 Proje Bazlı Eğitim", padding=15)
        project_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Project selector
        proj_sel_frame = ttk.Frame(project_frame)
        proj_sel_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(proj_sel_frame, text="Proje:", font=('Segoe UI', 10)).pack(side=tk.LEFT)
        self.project_combo = ttk.Combobox(proj_sel_frame, state='readonly', font=('Segoe UI', 10))
        self.project_combo.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        self.project_combo.bind('<<ComboboxSelected>>', self._on_project_selected)
        
        # Project stats
        self.project_status_labels = {}
        p_stats_frame = ttk.Frame(project_frame)
        p_stats_frame.pack(fill=tk.X, pady=5)
        
        p_items = [
            ('status', 'Durum', 'Eğitilmedi'),
            ('samples', 'Veri', '0'),
            ('r2', 'R²', '-')
        ]
        
        for i, (key, label, default) in enumerate(p_items):
            f = ttk.Frame(p_stats_frame)
            f.pack(side=tk.LEFT, expand=True, fill=tk.X)
            ttk.Label(f, text=label, font=('Segoe UI', 8, 'bold'), foreground='gray').pack(anchor='w')
            lbl = ttk.Label(f, text=default, font=('Segoe UI', 11, 'bold'))
            lbl.pack(anchor='w')
            self.project_status_labels[key] = lbl

        # Project Train Button
        self.project_train_btn = ttk.Button(
            project_frame, 
            text="🚀 PROJE MODELİNİ EĞİT",
            command=self._train_project,
            style='Accent.TButton'
        )
        self.project_train_btn.pack(fill=tk.X, pady=(15, 5), ipady=5)
        
        # Project Progress
        self.project_status_text = ttk.Label(project_frame, text="Hazır", font=('Segoe UI', 9), foreground='gray')
        self.project_status_text.pack(anchor='w')
        self.project_progress = ttk.Progressbar(project_frame, mode='indeterminate')
        self.project_progress.pack(fill=tk.X, pady=(2, 0))

        # 2. Global Model Training Section
        global_frame = ttk.LabelFrame(left_column, text="🌐 Global Model", padding=15)
        global_frame.pack(fill=tk.X)
        
        ttk.Label(
            global_frame,
            text="Tüm projelerden öğrenerek genel kalıpları analiz eder.",
            font=('Segoe UI', 9), foreground='gray', wraplength=300
        ).pack(fill=tk.X, pady=(0, 10))
        
        # Global stats
        self.global_status_labels = {}
        g_stats_frame = ttk.Frame(global_frame)
        g_stats_frame.pack(fill=tk.X, pady=5)
        
        g_items = [
            ('status', 'Durum', 'Eğitilmedi'),
            ('samples', 'Toplam Veri', '0'),
            ('projects', 'Projeler', '-')
        ]
        
        for i, (key, label, default) in enumerate(g_items):
            f = ttk.Frame(g_stats_frame)
            f.pack(side=tk.LEFT, expand=True, fill=tk.X)
            ttk.Label(f, text=label, font=('Segoe UI', 8, 'bold'), foreground='gray').pack(anchor='w')
            lbl = ttk.Label(f, text=default, font=('Segoe UI', 11, 'bold'))
            lbl.pack(anchor='w')
            self.global_status_labels[key] = lbl
            
        # Global Train Button
        self.global_train_btn = ttk.Button(
            global_frame,
            text="🌍 GLOBAL MODELİ EĞİT",
            command=self._train_global,
            style='Accent.TButton'
        )
        self.global_train_btn.pack(fill=tk.X, pady=(15, 5), ipady=5)
        
        # Global Progress
        self.global_status_text = ttk.Label(global_frame, text="Hazır", font=('Segoe UI', 9), foreground='gray')
        self.global_status_text.pack(anchor='w')
        self.global_progress = ttk.Progressbar(global_frame, mode='indeterminate')
        self.global_progress.pack(fill=tk.X, pady=(2, 0))
        
        # =====================================================
        # RIGHT COLUMN: Learned Insights
        # =====================================================
        right_column = ttk.LabelFrame(tab, text="💡 Öğrenilen İçgörüler", padding=2)
        right_column.grid(row=0, column=1, sticky="nsew")
        
        self.insights_text = tk.Text(
            right_column,
            wrap=tk.WORD,
            state='disabled',
            bg='#1E1E1E', fg='#00FF00', insertbackground='#00FF00', # Matrix style
            font=('Consolas', 10),
            relief=tk.FLAT,
            padx=15, pady=15
        )
        self.insights_text.pack(fill=tk.BOTH, expand=True)
        
        # Initial Message
        self._show_insights_empty_state()
        
        return tab
    
    def _show_insights_empty_state(self):
        """Show placeholder text when no insights available"""
        self.insights_text.config(state='normal')
        self.insights_text.delete(1.0, tk.END)
        
        center_padding = "\n" * 8
        msg = """
        ⚠️ MODEL EĞİTİLMEDİ
        
        İçgörüleri ve özellik önem düzeylerini görmek için
        sol taraftaki panellerden bir eğitim başlatın.
        
        1. Proje Modeli: Spesifik proje verileriyle çalışır.
        2. Global Model: Tüm verilerden genel kuralları öğrenir.
        """
        
        self.insights_text.insert(tk.END, center_padding)
        self.insights_text.insert(tk.END, msg)
        self.insights_text.tag_add("center", "1.0", "end")
        self.insights_text.tag_config("center", justify='center')
        self.insights_text.config(state='disabled')
    
    def _create_prediction_tab(self) -> ttk.Frame:
        """Tahmin sekmesi"""
        tab = ttk.Frame(self.inner_notebook, padding=10)
        
        # Giriş parametreleri
        input_frame = ttk.LabelFrame(tab, text="📊 Formülasyon Parametreleri", padding=10)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.prediction_inputs = {}
        params = [
            ('viscosity', 'Viskozite (cP)', '2000'),
            ('ph', 'pH', '8.0'),
            ('density', 'Yoğunluk (g/mL)', '1.2'),
            ('coating_thickness', 'Kaplama Kalınlığı (µm)', '50'),
        ]
        
        for i, (key, label, default) in enumerate(params):
            row = ttk.Frame(input_frame)
            row.pack(fill=tk.X, pady=2)
            
            ttk.Label(row, text=label, width=25).pack(side=tk.LEFT)
            entry = ttk.Entry(row, width=15)
            entry.insert(0, default)
            entry.pack(side=tk.LEFT, padx=5)
            self.prediction_inputs[key] = entry
        
        # Model seçimi
        model_frame = ttk.Frame(input_frame)
        model_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(model_frame, text="Model:").pack(side=tk.LEFT)
        self.prediction_model_var = tk.StringVar(value="global")
        ttk.Radiobutton(model_frame, text="Global", variable=self.prediction_model_var, value="global").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(model_frame, text="Proje", variable=self.prediction_model_var, value="project").pack(side=tk.LEFT, padx=5)
        
        # Tahmin butonu
        ttk.Button(
            input_frame,
            text="🔮 Tahmin Et",
            command=self._predict
        ).pack(fill=tk.X, pady=5)
        
        # Sonuçlar
        results_frame = ttk.LabelFrame(tab, text="📈 Tahmin Sonuçları", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sonuç grid
        self.prediction_result_labels = {}
        result_params = [
            ('opacity', 'Örtücülük', '%'),
            ('gloss', 'Parlaklık', 'GU'),
            ('adhesion', 'Yapışma', '0-5'),
            ('hardness', 'Sertlik', 'H'),
            ('corrosion_resistance', 'Korozyon Direnci', 'saat'),
            ('flexibility', 'Esneklik', '-'),
            ('chemical_resistance', 'Kimyasal Dayanım', '-'),
            ('quality_score', 'Kalite Skoru', '1-10'),
        ]
        
        # 2 sütunlu grid
        for i, (key, label, unit) in enumerate(result_params):
            col = i % 2
            row_num = i // 2
            
            if col == 0:
                result_row = ttk.Frame(results_frame)
                result_row.pack(fill=tk.X, pady=2)
            
            cell = ttk.Frame(result_row)
            cell.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            ttk.Label(cell, text=f"{label}:", width=18).pack(side=tk.LEFT)
            val_label = ttk.Label(cell, text="-", font=('Helvetica', 10, 'bold'), width=10)
            val_label.pack(side=tk.LEFT)
            ttk.Label(cell, text=unit, foreground='gray').pack(side=tk.LEFT)
            
            self.prediction_result_labels[key] = val_label
        
        return tab
    
    def _create_recommendation_tab(self) -> ttk.Frame:
        """Öneriler sekmesi"""
        tab = ttk.Frame(self.inner_notebook, padding=10)
        
        # Malzeme önerisi
        material_frame = ttk.LabelFrame(tab, text="🧪 Malzeme Alternatifleri", padding=10)
        material_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Mevcut malzeme seçimi
        select_frame = ttk.Frame(material_frame)
        select_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(select_frame, text="Mevcut Malzeme:").pack(side=tk.LEFT)
        self.current_material_combo = ttk.Combobox(select_frame, width=25, state='readonly')
        self.current_material_combo['values'] = ['Epoksi Reçine', 'Poliüretan Reçine', 'Alkid Reçine', 'Akrilik Reçine', 'Titanyum Dioksit']
        self.current_material_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(select_frame, text="Kategori:").pack(side=tk.LEFT, padx=(10, 0))
        self.material_category_combo = ttk.Combobox(select_frame, width=15, state='readonly')
        self.material_category_combo['values'] = ['Bağlayıcı', 'Pigment', 'Dolgu', 'Çözücü']
        self.material_category_combo.current(0)
        self.material_category_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            select_frame,
            text="🔍 Alternatif Bul",
            command=self._find_alternatives
        ).pack(side=tk.LEFT, padx=10)
        
        # Öneri sonuçları
        self.recommendation_text = tk.Text(material_frame, height=8, wrap=tk.WORD, state='disabled')
        self.recommendation_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Formülasyon iyileştirme
        improvement_frame = ttk.LabelFrame(tab, text="📈 Formülasyon İyileştirme", padding=10)
        improvement_frame.pack(fill=tk.BOTH, expand=True)
        
        # İyileştirme tipi
        type_frame = ttk.Frame(improvement_frame)
        type_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(type_frame, text="Hedef:").pack(side=tk.LEFT)
        self.improvement_type_var = tk.StringVar(value="balanced")
        ttk.Radiobutton(type_frame, text="💰 Maliyet Düşür", variable=self.improvement_type_var, value="cost").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="📈 Performans Artır", variable=self.improvement_type_var, value="performance").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="⚖️ Dengeli", variable=self.improvement_type_var, value="balanced").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            type_frame,
            text="🎯 Önerileri Göster",
            command=self._get_improvements
        ).pack(side=tk.LEFT, padx=10)
        
        # İyileştirme sonuçları
        self.improvement_text = tk.Text(improvement_frame, height=6, wrap=tk.WORD, state='disabled')
        self.improvement_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Benzer Formülasyonlar Bölümü (Yeni)
        similar_frame = ttk.LabelFrame(tab, text="🔍 Benzer Formülasyonlar", padding=10)
        similar_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Buton satırı
        similar_btn_frame = ttk.Frame(similar_frame)
        similar_btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(similar_btn_frame, text="Mevcut formülasyona benzer olanları bul:").pack(side=tk.LEFT)
        
        ttk.Button(
            similar_btn_frame,
            text="🔍 Benzer Formülasyonları Bul",
            command=self._find_similar
        ).pack(side=tk.LEFT, padx=10)
        
        # Benzer formülasyon sonuçları
        self.similar_text = tk.Text(similar_frame, height=5, wrap=tk.WORD, state='disabled')
        self.similar_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        return tab
    
    # === Event Handlers ===
    
    def _on_project_selected(self, event=None):
        """Proje seçildiğinde"""
        selection = self.project_combo.get()
        if selection and self.project_list:
            for p in self.project_list:
                if p.get('name') == selection:
                    self.current_project_id = p.get('id')
                    self.current_project_name = selection
                    break
    
    def load_projects(self, projects: list):
        """Projeleri yükle"""
        self.project_list = projects
        project_names = [p.get('name', '') for p in projects if p.get('name')]
        self.project_combo['values'] = project_names
        if project_names:
            self.project_combo.current(0)
            self._on_project_selected()
    
    def refresh_model_statuses(self):
        """Model durumlarını sayfa açılışında veya proje değişikliğinde yenile"""
        try:
            # Proje modeli durumu
            if self.current_project_id and self.on_get_project_status:
                status = self.on_get_project_status(self.current_project_id)
                if status:
                    self._update_project_status(status)
            
            # Global model durumu
            if self.on_get_global_status:
                status = self.on_get_global_status()
                if status:
                    self._update_global_status(status)
                    # İçgörüleri de göster
                    if status.get('insights'):
                        self._display_insights(status.get('insights', []))
        except Exception as e:
            # Sessizce başarısız ol - model henüz eğitilmemiş olabilir
            pass
    
    def _train_project(self):
        """Proje modeli eğit"""
        if not self.current_project_id:
            messagebox.showwarning("Uyarı", "Lütfen bir proje seçin!", parent=self)
            return
        
        self.project_progress.start(10)
        self.project_status_text.config(text=f"⏳ {self.current_project_name} eğitiliyor...", foreground='blue')
        self.project_train_btn.config(state='disabled')
        
        threading.Thread(
            target=self._do_train_project,
            daemon=True
        ).start()
    
    def _do_train_project(self):
        """Proje eğitimini arka planda çalıştır"""
        try:
            result = None
            if self.on_train_project:
                result = self.on_train_project(self.current_project_id, self.current_project_name)
            
            def finish():
                self.project_progress.stop()
                self.project_train_btn.config(state='normal')
                
                if result and result.get('success'):
                    self.project_status_text.config(text="✅ Eğitim tamamlandı", foreground='green')
                    self._update_project_status(result)
                    messagebox.showinfo(
                        "Başarılı",
                        f"{self.current_project_name} modeli eğitildi!\n"
                        f"Veri sayısı: {result.get('samples', 0)}\n"
                        f"R² Skoru: {result.get('avg_r2_score', 'N/A')}",
                        parent=self
                    )
                else:
                    self.project_status_text.config(text="❌ Eğitim başarısız", foreground='red')
                    messagebox.showerror("Hata", result.get('message', 'Bilinmeyen hata'), parent=self)
            
            self.after(0, finish)
        except Exception as e:
            error_msg = str(e)
            def show_error():
                self.project_progress.stop()
                self.project_train_btn.config(state='normal')
                self.project_status_text.config(text="❌ Hata", foreground='red')
                messagebox.showerror("Hata", error_msg, parent=self)
            self.after(0, show_error)
    
    def _train_global(self):
        """Global model eğit"""
        self.global_progress.start(10)
        self.global_status_text.config(text="⏳ Global model eğitiliyor...", foreground='blue')
        self.global_train_btn.config(state='disabled')
        
        threading.Thread(
            target=self._do_train_global,
            daemon=True
        ).start()
    
    def _do_train_global(self):
        """Global eğitimi arka planda çalıştır"""
        try:
            result = None
            if self.on_train_global:
                result = self.on_train_global()
            
            def finish():
                self.global_progress.stop()
                self.global_train_btn.config(state='normal')
                
                if result and result.get('success'):
                    self.global_status_text.config(text="✅ Eğitim tamamlandı", foreground='green')
                    self._update_global_status(result)
                    self._display_insights(result.get('learned_patterns', []))
                    messagebox.showinfo(
                        "Başarılı",
                        f"Global model eğitildi!\n"
                        f"Toplam veri: {result.get('samples', 0)}\n"
                        f"R² Skoru: {result.get('avg_r2_score', 'N/A')}\n"
                        f"İçgörüler: {len(result.get('learned_patterns', []))}",
                        parent=self
                    )
                else:
                    self.global_status_text.config(text="❌ Eğitim başarısız", foreground='red')
                    messagebox.showerror("Hata", result.get('message', 'Bilinmeyen hata'), parent=self)
            
            self.after(0, finish)
        except Exception as e:
            error_msg = str(e)
            def show_error():
                self.global_progress.stop()
                self.global_train_btn.config(state='normal')
                self.global_status_text.config(text="❌ Hata", foreground='red')
                messagebox.showerror("Hata", error_msg, parent=self)
            self.after(0, show_error)
    
    def _update_project_status(self, result: dict):
        """Proje model durumunu güncelle"""
        if result.get('success'):
            self.project_status_labels['status'].config(text="✅ Eğitildi", foreground='green')
        else:
            self.project_status_labels['status'].config(text="⚠️ Eğitilmedi", foreground='orange')
        
        self.project_status_labels['samples'].config(text=str(result.get('samples', 0)))
        
        r2 = result.get('avg_r2_score', result.get('r2_score'))
        if r2:
            color = 'green' if r2 > 0.7 else 'orange' if r2 > 0.4 else 'red'
            self.project_status_labels['r2'].config(text=f"{r2:.3f}", foreground=color)
    
    def _update_global_status(self, result: dict):
        """Global model durumunu güncelle"""
        if result.get('success'):
            self.global_status_labels['status'].config(text="✅ Eğitildi", foreground='green')
        else:
            self.global_status_labels['status'].config(text="⚠️ Eğitilmedi", foreground='orange')
        
        self.global_status_labels['samples'].config(text=str(result.get('samples', 0)))
        self.global_status_labels['projects'].config(text=str(result.get('projects_included', '-')))
    
    def _display_insights(self, insights: List[Dict]):
        """İçgörüleri göster - Terminal style formatting"""
        self.insights_text.config(state='normal')
        self.insights_text.delete(1.0, tk.END)
        
        if not insights:
            self._show_insights_empty_state()
            return
        
        # Terminal-style header
        self.insights_text.insert(tk.END, "┌─────────────────────────────────────────────────┐\n")
        self.insights_text.insert(tk.END, "│  LEARNED PATTERNS & INSIGHTS                    │\n")
        self.insights_text.insert(tk.END, "└─────────────────────────────────────────────────┘\n\n")
        
        for i, insight in enumerate(insights, 1):
            title = insight.get('title', f'Insight {i}')
            message = insight.get('message', '')
            
            # Format each insight
            self.insights_text.insert(tk.END, f"[{i}] {title}\n")
            if message:
                self.insights_text.insert(tk.END, f"    → {message}\n")
            self.insights_text.insert(tk.END, "\n")
        
        # Footer with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.insights_text.insert(tk.END, f"─────────────────────────────────────────────────\n")
        self.insights_text.insert(tk.END, f"Last updated: {timestamp}\n")
        
        self.insights_text.config(state='disabled')
    
    def _predict(self):
        """Tahmin yap"""
        # Girdileri topla
        params = {}
        for key, entry in self.prediction_inputs.items():
            try:
                params[key] = float(entry.get())
            except ValueError:
                params[key] = 0
        
        model_type = self.prediction_model_var.get()
        
        if self.on_predict:
            result = self.on_predict(params, model_type, self.current_project_id)
            
            if result and result.get('success'):
                predictions = result.get('predictions', {})
                for key, label in self.prediction_result_labels.items():
                    val = predictions.get(key)
                    if val is not None:
                        label.config(text=f"{val:.1f}", foreground='blue')
                    else:
                        label.config(text="-", foreground='gray')
            else:
                messagebox.showwarning("Uyarı", result.get('message', 'Tahmin yapılamadı'), parent=self)
    
    def _find_alternatives(self):
        """Alternatif malzeme bul"""
        material = self.current_material_combo.get()
        category = self.material_category_combo.get()
        
        if not material:
            messagebox.showwarning("Uyarı", "Lütfen bir malzeme seçin!", parent=self)
            return
        
        if self.on_recommend:
            result = self.on_recommend('alternatives', material, category)
            self._display_recommendations(result)
        else:
            # Demo öneriler
            self._show_demo_recommendations(material)
    
    def _show_demo_recommendations(self, material: str):
        """Demo öneriler göster"""
        self.recommendation_text.config(state='normal')
        self.recommendation_text.delete(1.0, tk.END)
        
        recommendations = {
            'Epoksi Reçine': """
🔄 ÖNERİLEN ALTERNATİFLER:

1. Poliüretan Reçine
   ✅ Avantajlar: Daha yüksek esneklik, iyi UV direnci
   ⚠️ Dikkat: Kimyasal dayanım biraz düşük
   💰 Maliyet: +15%

2. Vinil Ester Reçine
   ✅ Avantajlar: Mükemmel korozyon direnci
   ⚠️ Dikkat: Daha karmaşık kürleme
   💰 Maliyet: +20%

📝 Kimya Notu: Poliüretan'a geçerken izosiyonat/poliol oranına dikkat edin.
""",
            'Titanyum Dioksit': """
🔄 ÖNERİLEN ALTERNATİFLER:

1. Çinko Oksit (ZnO)
   ✅ Avantajlar: Daha düşük maliyet, antimikrobiyal
   ⚠️ Dikkat: UV koruma biraz düşük
   💰 Maliyet: -30%

2. Baryum Sülfat
   ✅ Avantajlar: Ekonomik, iyi dolgu
   ⚠️ Dikkat: Örtücülük TiO2'ye göre düşük
   💰 Maliyet: -50%

📝 Kimya Notu: ZnO ile TiO2 karışımı optimum maliyet-performans sağlar.
"""
        }
        
        text = recommendations.get(material, f"'{material}' için alternatif önerisi bulunamadı.\n\nDaha fazla malzeme bilgisi için veritabanını güncelleyin.")
        self.recommendation_text.insert(tk.END, text)
        self.recommendation_text.config(state='disabled')
    
    def _display_recommendations(self, result):
        """Öneri sonuçlarını göster"""
        self.recommendation_text.config(state='normal')
        self.recommendation_text.delete(1.0, tk.END)
        
        if result:
            self.recommendation_text.insert(tk.END, str(result))
        else:
            self.recommendation_text.insert(tk.END, "Öneri bulunamadı.")
        
        self.recommendation_text.config(state='disabled')
    
    def _get_improvements(self):
        """İyileştirme önerileri al - Gerçek ML kullanır"""
        improvement_type = self.improvement_type_var.get()
        
        self.improvement_text.config(state='normal')
        self.improvement_text.delete(1.0, tk.END)
        self.improvement_text.insert(tk.END, "⏳ Öneriler hesaplanıyor...\n")
        self.improvement_text.config(state='disabled')
        
        # Gerçek ML callback varsa kullan
        if self.on_get_improvements:
            try:
                result = self.on_get_improvements(improvement_type, {})
                
                self.improvement_text.config(state='normal')
                self.improvement_text.delete(1.0, tk.END)
                
                if result.get('success'):
                    suggestions = result.get('suggestions', [])
                    
                    if suggestions:
                        # Başlık
                        type_labels = {
                            'cost': '💰 MALİYET DÜŞÜRME ÖNERİLERİ',
                            'performance': '📈 PERFORMANS ARTIRMA ÖNERİLERİ',
                            'balanced': '⚖️ DENGELİ İYİLEŞTİRME ÖNERİLERİ'
                        }
                        self.improvement_text.insert(tk.END, f"{type_labels.get(improvement_type, 'ÖNERİLER')}:\n\n")
                        
                        # Önerileri göster
                        for i, suggestion in enumerate(suggestions, 1):
                            title = suggestion.title if hasattr(suggestion, 'title') else suggestion.get('title', f'Öneri {i}')
                            desc = suggestion.description if hasattr(suggestion, 'description') else suggestion.get('description', '')
                            
                            self.improvement_text.insert(tk.END, f"{i}. {title}\n")
                            if desc:
                                self.improvement_text.insert(tk.END, f"   {desc}\n")
                            
                            # Beklenen etki
                            impact = suggestion.expected_impact if hasattr(suggestion, 'expected_impact') else suggestion.get('expected_impact', {})
                            if impact:
                                for key, val in impact.items():
                                    direction = "↑" if val > 0 else "↓"
                                    self.improvement_text.insert(tk.END, f"   • {key}: {direction} {abs(val):.0%}\n")
                            
                            # Uygulama adımları
                            steps = suggestion.implementation_steps if hasattr(suggestion, 'implementation_steps') else suggestion.get('implementation_steps', [])
                            if steps:
                                self.improvement_text.insert(tk.END, "   Adımlar:\n")
                                for step in steps:
                                    self.improvement_text.insert(tk.END, f"     → {step}\n")
                            
                            self.improvement_text.insert(tk.END, "\n")
                    else:
                        self.improvement_text.insert(tk.END, "📝 Bu formülasyon için henüz öneri oluşturulamadı.\n\n")
                        self.improvement_text.insert(tk.END, "Daha fazla test verisi girildikçe ML modeli daha iyi öneriler sunacaktır.")
                else:
                    error_msg = result.get('message', 'Bilinmeyen hata')
                    self.improvement_text.insert(tk.END, f"⚠️ Öneri alınamadı: {error_msg}")
                
                self.improvement_text.config(state='disabled')
                return
                
            except Exception as e:
                self.improvement_text.config(state='normal')
                self.improvement_text.delete(1.0, tk.END)
                self.improvement_text.insert(tk.END, f"❌ Hata: {str(e)}")
                self.improvement_text.config(state='disabled')
                return
        
        # Fallback - callback yoksa demo göster
        self.improvement_text.config(state='normal')
        self.improvement_text.delete(1.0, tk.END)
        
        if improvement_type == 'cost':
            text = """💰 MALİYET DÜŞÜRME ÖNERİLERİ:

1. Dolgu Oranını Artırın
   • CaCO3 oranını %5 artırarak maliyeti %8-12 düşürebilirsiniz
   • Performans etkisi: Parlaklıkta hafif düşüş beklenir

2. Alternatif Pigment Kullanın
   • TiO2'nin bir kısmını ZnO ile değiştirin
   • Maliyet tasarrufu: %15-20
"""
        elif improvement_type == 'performance':
            text = """📈 PERFORMANS ARTIRMA ÖNERİLERİ:

1. Reçine Kalitesini Yükseltin
   • Yüksek molekül ağırlıklı reçine kullanın
   • Beklenen etki: Kimyasal dayanım +20%

2. Katkı Maddesi Ekleyin
   • UV stabilizatör: Dış mekan uygulamaları için
   • Akış katkısı: Yüzey kalitesi için
"""
        else:
            text = """⚖️ DENGELİ İYİLEŞTİRME ÖNERİLERİ:

1. Formülasyonu Optimize Edin
   • Mevcut malzemelerle en iyi dengeyi bulun
   • Küçük ayarlamalarla büyük gelişmeler mümkün

2. Sürekli İyileştirme
   • Her test sonucunu kaydedin
   • ML modeli zamanla daha iyi öneriler sunacak
"""
        
        self.improvement_text.insert(tk.END, text)
        self.improvement_text.config(state='disabled')
    
    def _find_similar(self):
        """Benzer formülasyonları bul - ML kullanır"""
        self.similar_text.config(state='normal')
        self.similar_text.delete(1.0, tk.END)
        self.similar_text.insert(tk.END, "⏳ Benzer formülasyonlar aranıyor...\n")
        self.similar_text.config(state='disabled')
        
        # Callback varsa kullan
        if self.on_find_similar:
            try:
                # Mevcut tahmin parametrelerini al (varsa)
                target_params = {}
                for key, entry in self.prediction_inputs.items():
                    try:
                        target_params[key] = float(entry.get())
                    except ValueError:
                        pass
                
                result = self.on_find_similar(target_params, 5)
                
                self.similar_text.config(state='normal')
                self.similar_text.delete(1.0, tk.END)
                
                if result.get('success'):
                    similar_list = result.get('similar_formulations', [])
                    
                    if similar_list:
                        self.similar_text.insert(tk.END, "🔍 BENZER FORMÜLASYONLAR:\n\n")
                        
                        for i, item in enumerate(similar_list, 1):
                            if isinstance(item, dict):
                                code = item.get('formula_code', item.get('formulation', {}).get('formula_code', 'Bilinmiyor'))
                                name = item.get('formula_name', item.get('formulation', {}).get('formula_name', ''))
                                similarity = item.get('similarity_score', item.get('similarity', 0))
                                
                                self.similar_text.insert(tk.END, f"{i}. {code}")
                                if name:
                                    self.similar_text.insert(tk.END, f" - {name}")
                                self.similar_text.insert(tk.END, f"\n   Benzerlik: {similarity:.0%}\n\n")
                            else:
                                self.similar_text.insert(tk.END, f"{i}. {str(item)}\n")
                    else:
                        self.similar_text.insert(tk.END, "📝 Benzer formülasyon bulunamadı.\n\n")
                        self.similar_text.insert(tk.END, "Daha fazla test verisi girildikçe karşılaştırma yapılabilecektir.")
                else:
                    error_msg = result.get('message', 'Bilinmeyen hata')
                    self.similar_text.insert(tk.END, f"⚠️ Arama yapılamadı: {error_msg}")
                
                self.similar_text.config(state='disabled')
                return
                
            except Exception as e:
                self.similar_text.config(state='normal')
                self.similar_text.delete(1.0, tk.END)
                self.similar_text.insert(tk.END, f"❌ Hata: {str(e)}")
                self.similar_text.config(state='disabled')
                return
        
        # Fallback
        self.similar_text.config(state='normal')
        self.similar_text.delete(1.0, tk.END)
        self.similar_text.insert(tk.END, "⚠️ Benzer formülasyon arama servisi yapılandırılmamış.\n\n")
        self.similar_text.insert(tk.END, "Bu özelliği kullanmak için yeterli test verisi girin.")
        self.similar_text.config(state='disabled')

    def _create_optimization_tab(self) -> ttk.Frame:
        """Optimizasyon sekmesi"""
        try:
            from app.optimization_panels import MultiObjectiveOptimizationPanel
        except ImportError:
            # Fallback
            return ttk.Frame(self.inner_notebook)
            
        tab = ttk.Frame(self.inner_notebook, padding=10)
        
        # Optimizasyon paneli
        self.optimization_panel = MultiObjectiveOptimizationPanel(
            tab,
            on_optimize=None,
            on_apply_recipe=self.on_apply_recipe,
            on_generate_recipe=self.on_generate_recipe
        )
        self.optimization_panel.pack(fill=tk.BOTH, expand=True)
        
        return tab
