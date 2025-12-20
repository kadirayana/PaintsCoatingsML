"""
Paint Formulation AI - Optimizasyon Panelleri
==============================================
Çoklu hedef optimizasyonu ve malzeme yönetimi UI bileşenleri
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, List, Optional
import threading


class MaterialsPanel(ttk.LabelFrame):
    """Malzeme yönetim paneli"""
    
    CATEGORIES = [
        ('binder', 'Bağlayıcı'),
        ('pigment', 'Pigment'),
        ('filler', 'Dolgu'),
        ('thickener', 'Koyulaştırıcı'),
        ('additive', 'Katkı Maddesi'),
        ('solvent', 'Çözücü'),
        ('other', 'Diğer')
    ]
    
    def __init__(self, parent, on_save: Callable = None, on_delete: Callable = None):
        super().__init__(parent, text="💰 Malzeme Fiyatları", padding=10)
        
        self.on_save = on_save
        self.on_delete = on_delete
        self.materials = []
        
        # Malzeme listesi
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Treeview
        columns = ('name', 'category', 'price', 'unit')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        
        self.tree.heading('name', text='Malzeme Adı')
        self.tree.heading('category', text='Kategori')
        self.tree.heading('price', text='Fiyat/Birim')
        self.tree.heading('unit', text='Birim')
        
        self.tree.column('name', width=120)
        self.tree.column('category', width=80)
        self.tree.column('price', width=70)
        self.tree.column('unit', width=50)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Giriş alanları
        input_frame = ttk.Frame(self)
        input_frame.pack(fill=tk.X, pady=5)
        
        # Satır 1
        row1 = ttk.Frame(input_frame)
        row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(row1, text="Ad:").pack(side=tk.LEFT)
        self.name_entry = ttk.Entry(row1, width=15)
        self.name_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row1, text="Fiyat:").pack(side=tk.LEFT)
        self.price_entry = ttk.Entry(row1, width=10)
        self.price_entry.pack(side=tk.LEFT, padx=5)
        
        # Satır 2
        row2 = ttk.Frame(input_frame)
        row2.pack(fill=tk.X, pady=2)
        
        ttk.Label(row2, text="Kategori:").pack(side=tk.LEFT)
        self.category_var = tk.StringVar(value='other')
        category_combo = ttk.Combobox(
            row2, 
            textvariable=self.category_var,
            values=[c[1] for c in self.CATEGORIES],
            width=12,
            state='readonly'
        )
        category_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row2, text="Birim:").pack(side=tk.LEFT)
        self.unit_var = tk.StringVar(value='kg')
        unit_combo = ttk.Combobox(
            row2,
            textvariable=self.unit_var,
            values=['kg', 'lt', 'adet'],
            width=6,
            state='readonly'
        )
        unit_combo.pack(side=tk.LEFT, padx=5)
        
        # Butonlar
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="➕ Ekle", command=self._add_material).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑️ Sil", command=self._delete_material).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🔄 Güncelle", command=self._update_material).pack(side=tk.LEFT, padx=2)
        
        # Toplam maliyet göstergesi
        self.total_label = ttk.Label(self, text="Toplam: 0 birim", font=('Helvetica', 10, 'bold'))
        self.total_label.pack(anchor=tk.E)
    
    def _get_category_code(self, name: str) -> str:
        """Kategori adından kod al"""
        for code, label in self.CATEGORIES:
            if label == name:
                return code
        return 'other'
    
    def _get_category_name(self, code: str) -> str:
        """Kategori kodundan ad al"""
        for c, label in self.CATEGORIES:
            if c == code:
                return label
        return 'Diğer'
    
    def _add_material(self):
        """Malzeme ekle"""
        name = self.name_entry.get().strip()
        price = self.price_entry.get().strip()
        
        if not name or not price:
            messagebox.showwarning("Uyarı", "Ad ve fiyat zorunludur!")
            return
        
        try:
            price_val = float(price)
        except ValueError:
            messagebox.showwarning("Uyarı", "Geçerli bir fiyat girin!")
            return
        
        data = {
            'name': name,
            'category': self._get_category_code(self.category_var.get()),
            'unit_price': price_val,
            'unit': self.unit_var.get()
        }
        
        if self.on_save:
            material_id = self.on_save(data)
            data['id'] = material_id
            
        # Listeye ekle
        self.tree.insert('', tk.END, values=(
            name,
            self.category_var.get(),
            f"{price_val:.2f}",
            self.unit_var.get()
        ))
        
        # Formu temizle
        self.name_entry.delete(0, tk.END)
        self.price_entry.delete(0, tk.END)
        
        self._update_total()
    
    def _delete_material(self):
        """Seçili malzemeyi sil"""
        selection = self.tree.selection()
        if not selection:
            return
        
        if messagebox.askyesno("Onay", "Malzemeyi silmek istiyor musunuz?"):
            for item in selection:
                self.tree.delete(item)
            
            if self.on_delete:
                self.on_delete()
            
            self._update_total()
    
    def _update_material(self):
        """Seçili malzemeyi güncelle"""
        selection = self.tree.selection()
        if not selection:
            return
        
        name = self.name_entry.get().strip()
        price = self.price_entry.get().strip()
        
        if name and price:
            try:
                price_val = float(price)
                self.tree.item(selection[0], values=(
                    name,
                    self.category_var.get(),
                    f"{price_val:.2f}",
                    self.unit_var.get()
                ))
                self._update_total()
            except ValueError:
                pass
    
    def _update_total(self):
        """Toplam maliyeti güncelle"""
        total = 0
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            try:
                total += float(values[2])
            except (ValueError, IndexError):
                pass
        
        self.total_label.config(text=f"Toplam: {total:.2f} birim")
    
    def load_materials(self, materials: List[Dict]):
        """Malzemeleri yükle"""
        self.tree.delete(*self.tree.get_children())
        
        for m in materials:
            self.tree.insert('', tk.END, values=(
                m.get('name', ''),
                self._get_category_name(m.get('category', 'other')),
                f"{m.get('unit_price', 0):.2f}",
                m.get('unit', 'kg')
            ))
        
        self._update_total()
    
    def get_price_dict(self) -> Dict[str, float]:
        """Kategori bazlı fiyat sözlüğü döndür"""
        prices = {}
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            try:
                cat = self._get_category_code(values[1])
                prices[cat] = float(values[2])
            except (ValueError, IndexError):
                pass
        return prices


class MultiObjectiveOptimizationPanel(ttk.LabelFrame):
    """Çoklu hedef optimizasyon paneli"""
    
    def __init__(self, parent, on_optimize: Callable = None, on_load_file: Callable = None):
        super().__init__(parent, text="🎯 Çoklu Hedef Optimizasyonu", padding=10)
        
        self.on_optimize = on_optimize
        self.on_load_file = on_load_file
        self.objective_vars = {}
        self.selected_file = None
        self.selected_project = None
        
        # === VERİ KAYNAĞI SEÇİMİ ===
        source_frame = ttk.LabelFrame(self, text="📂 Veri Kaynağı", padding=5)
        source_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Kaynak tipi
        self.source_type = tk.StringVar(value="all")
        
        row1 = ttk.Frame(source_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Radiobutton(row1, text="Tüm Veriler", variable=self.source_type, value="all").pack(side=tk.LEFT)
        ttk.Radiobutton(row1, text="Proje Seç", variable=self.source_type, value="project").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(row1, text="Dosya Seç", variable=self.source_type, value="file").pack(side=tk.LEFT)
        
        # Proje seçici
        row2 = ttk.Frame(source_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="Proje:").pack(side=tk.LEFT)
        self.project_combo = ttk.Combobox(row2, width=25, state='readonly')
        self.project_combo.pack(side=tk.LEFT, padx=5)
        
        # Dosya seçici
        row3 = ttk.Frame(source_frame)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text="Dosya:").pack(side=tk.LEFT)
        self.file_label = ttk.Label(row3, text="Seçilmedi", width=20)
        self.file_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(row3, text="📁 Seç", command=self._select_file).pack(side=tk.LEFT)
        
        # Açıklama
        desc = ttk.Label(
            self, 
            text="Birden fazla hedefe göre optimum formülasyon hesaplayın",
            font=('Helvetica', 9, 'italic')
        )
        desc.pack(anchor=tk.W, pady=(0, 10))
        
        # Hedefler
        objectives_frame = ttk.LabelFrame(self, text="Hedefler", padding=5)
        objectives_frame.pack(fill=tk.X, pady=5)
        
        self.objectives = [
            ('opacity', 'Örtücülük (%)', 'max'),
            ('gloss', 'Parlaklık (GU)', 'max'),
            ('corrosion_resistance', 'Korozyon Direnci', 'max'),
            ('total_cost', 'Toplam Maliyet (Birim)', 'min'),
            ('quality_score', 'Kalite Skoru (1-10)', 'max'),
            ('adhesion', 'Yapışma (0-5)', 'max'),
            ('hardness', 'Sertlik (H)', 'max'),
            ('flexibility', 'Esneklik', 'max'),
            ('chemical_resistance', 'Kimyasal Dayanım', 'max'),
            ('uv_resistance', 'UV Dayanımı', 'max'),
            ('abrasion_resistance', 'Aşınma Direnci', 'max'),
        ]
        
        for i, (key, label, default_dir) in enumerate(self.objectives):
            row = ttk.Frame(objectives_frame)
            row.pack(fill=tk.X, pady=2)
            
            # Aktif/Pasif
            active_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(row, variable=active_var).pack(side=tk.LEFT)
            
            # Etiket
            ttk.Label(row, text=label, width=20).pack(side=tk.LEFT)
            
            # Hedef değer
            target_entry = ttk.Entry(row, width=8)
            target_entry.pack(side=tk.LEFT, padx=5)
            
            # Ağırlık
            ttk.Label(row, text="Ağırlık:").pack(side=tk.LEFT)
            weight_entry = ttk.Entry(row, width=5)
            weight_entry.insert(0, "1.0")
            weight_entry.pack(side=tk.LEFT, padx=5)
            
            # Yön
            direction_var = tk.StringVar(value=default_dir)
            ttk.Radiobutton(row, text="Max", variable=direction_var, value="max").pack(side=tk.LEFT)
            ttk.Radiobutton(row, text="Min", variable=direction_var, value="min").pack(side=tk.LEFT)
            
            self.objective_vars[key] = {
                'active': active_var,
                'target': target_entry,
                'weight': weight_entry,
                'direction': direction_var
            }
        
        # Kısıtlamalar
        constraints_frame = ttk.LabelFrame(self, text="Parametre Sınırları", padding=5)
        constraints_frame.pack(fill=tk.X, pady=10)
        
        self.constraint_vars = {}
        constraints = [
            ('viscosity', 'Viskozite', 500, 8000),
            ('ph', 'pH', 6.0, 10.0),
            ('density', 'Yoğunluk', 0.8, 1.5),
            ('coating_thickness', 'Kaplama Kalınlığı (µm)', 10, 500),
        ]
        
        for key, label, default_min, default_max in constraints:
            row = ttk.Frame(constraints_frame)
            row.pack(fill=tk.X, pady=2)
            
            ttk.Label(row, text=label, width=20).pack(side=tk.LEFT)
            ttk.Label(row, text="Min:").pack(side=tk.LEFT)
            
            min_entry = ttk.Entry(row, width=8)
            min_entry.insert(0, str(default_min))
            min_entry.pack(side=tk.LEFT, padx=2)
            
            ttk.Label(row, text="Max:").pack(side=tk.LEFT)
            
            max_entry = ttk.Entry(row, width=8)
            max_entry.insert(0, str(default_max))
            max_entry.pack(side=tk.LEFT, padx=2)
            
            self.constraint_vars[key] = {'min': min_entry, 'max': max_entry}
        
        # Optimize butonu
        ttk.Button(
            self,
            text="🚀 Optimizasyonu Başlat",
            command=self._start_optimization
        ).pack(fill=tk.X, pady=10)
        
        # Sonuç alanı
        ttk.Label(self, text="Sonuçlar:").pack(anchor=tk.W)
        
        self.result_text = tk.Text(self, height=8, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        self.result_text.insert(tk.END, "Optimizasyon sonuçları burada görünecek...")
        self.result_text.config(state=tk.DISABLED)
    
    def _start_optimization(self):
        """Optimizasyonu başlat"""
        # Aktif hedefleri topla
        objectives = {}
        for key, vars in self.objective_vars.items():
            if vars['active'].get():
                target_str = vars['target'].get().strip()
                weight_str = vars['weight'].get().strip()
                
                objectives[key] = {
                    'target': float(target_str) if target_str else 100,
                    'weight': float(weight_str) if weight_str else 1.0,
                    'direction': vars['direction'].get()
                }
        
        if not objectives:
            messagebox.showwarning("Uyarı", "En az bir hedef seçmelisiniz!")
            return
        
        # Kısıtlamaları topla
        constraints = {}
        for key, vars in self.constraint_vars.items():
            min_str = vars['min'].get().strip()
            max_str = vars['max'].get().strip()
            
            constraints[key] = {
                'min': float(min_str) if min_str else 0,
                'max': float(max_str) if max_str else 100
            }
        
        # Sonuç alanını güncelle
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "Optimizasyon hesaplanıyor...\n")
        self.result_text.config(state=tk.DISABLED)
        
        # Arka planda çalıştır
        if self.on_optimize:
            threading.Thread(
                target=self._run_optimization,
                args=(objectives, constraints),
                daemon=True
            ).start()
    
    def _run_optimization(self, objectives: Dict, constraints: Dict):
        """Optimizasyonu arka planda çalıştır"""
        try:
            if self.on_optimize:
                result = self.on_optimize(objectives, constraints)
                self._display_result(result)
        except Exception as e:
            self._display_result({'success': False, 'message': str(e)})
    
    def _display_result(self, result: Dict):
        """Sonucu göster"""
        def update():
            self.result_text.config(state=tk.NORMAL)
            self.result_text.delete(1.0, tk.END)
            
            if result.get('success'):
                text = "✅ OPTİMİZASYON TAMAMLANDI\n"
                text += "=" * 40 + "\n\n"
                
                text += "📊 OPTİMUM PARAMETRELER:\n"
                for param, value in result.get('optimal_params', {}).items():
                    param_names = {'viscosity': 'Viskozite', 'ph': 'pH', 'density': 'Yoğunluk'}
                    text += f"  • {param_names.get(param, param)}: {value}\n"
                
                text += "\n🎯 TAHMİN EDİLEN SONUÇLAR:\n"
                for target, value in result.get('predicted_results', {}).items():
                    target_names = {
                        'opacity': 'Örtücülük',
                        'gloss': 'Parlaklık',
                        'total_cost': 'Maliyet',
                        'quality_score': 'Kalite',
                        'corrosion_resistance': 'Korozyon Direnci'
                    }
                    text += f"  • {target_names.get(target, target)}: {value}\n"
                
                text += f"\n📈 Optimizasyon Skoru: {result.get('optimization_score', 0)}\n"
                
                objectives_met = result.get('objectives_met', {})
                if objectives_met:
                    text += "\n✓ HEDEF DURUMU:\n"
                    for target, info in objectives_met.items():
                        status = "✅" if info.get('met') else "⚠️"
                        text += f"  {status} {target}: {info.get('predicted')} (Hedef: {info.get('target')})\n"
            else:
                text = f"❌ HATA: {result.get('message', 'Bilinmeyen hata')}"
            
            self.result_text.insert(tk.END, text)
            self.result_text.config(state=tk.DISABLED)
        
        self.after(0, update)
    
    def _select_file(self):
        """Dosya seç"""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Optimizasyon için Veri Dosyası Seç",
            filetypes=[
                ("Excel Dosyaları", "*.xlsx *.xls"),
                ("CSV Dosyaları", "*.csv"),
                ("Tüm Dosyalar", "*.*")
            ]
        )
        if file_path:
            self.selected_file = file_path
            # Dosya adını göster
            import os
            filename = os.path.basename(file_path)
            self.file_label.config(text=filename[:20] + "..." if len(filename) > 20 else filename)
            self.source_type.set("file")
            
            # Dosyayı yükle
            if self.on_load_file:
                self.on_load_file(file_path)
    
    def load_projects(self, projects: list):
        """Proje listesini yükle"""
        project_names = [p.get('name', '') for p in projects if p.get('name')]
        self.project_combo['values'] = project_names
        if project_names:
            self.project_combo.current(0)
    
    def get_source_info(self) -> dict:
        """Seçili veri kaynağı bilgisini döndür"""
        return {
            'type': self.source_type.get(),
            'project': self.project_combo.get() if self.source_type.get() == 'project' else None,
            'file': self.selected_file if self.source_type.get() == 'file' else None
        }
    
    def load_custom_objectives(self):
        """Özel test metodlarını hedef olarak yükle"""
        import json
        import os
        
        config_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data_storage', 'custom_test_methods.json'
        )
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    methods = json.load(f)
                
                # Her özel metod için hedef satırı ekle
                for key, data in methods.items():
                    if key not in self.objective_vars:
                        self._add_objective_row(key, data.get('name', key), data.get('unit', ''), 'max')
            except Exception:
                pass
    
    def _add_objective_row(self, key: str, name: str, unit: str, default_dir: str):
        """Dinamik hedef satırı ekle"""
        # objectives_frame'i bul
        for widget in self.winfo_children():
            if isinstance(widget, ttk.LabelFrame) and 'Hedefler' in str(widget.cget('text')):
                objectives_frame = widget
                break
        else:
            return
        
        label = f"{name} ({unit})" if unit else name
        
        row = ttk.Frame(objectives_frame)
        row.pack(fill=tk.X, pady=2)
        
        # Aktif/Pasif
        active_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, variable=active_var).pack(side=tk.LEFT)
        
        # Etiket (özel metod işareti)
        ttk.Label(row, text=f"✨ {label}", width=20).pack(side=tk.LEFT)
        
        # Hedef değer
        target_entry = ttk.Entry(row, width=8)
        target_entry.pack(side=tk.LEFT, padx=5)
        
        # Ağırlık
        ttk.Label(row, text="Ağırlık:").pack(side=tk.LEFT)
        weight_entry = ttk.Entry(row, width=5)
        weight_entry.insert(0, "1.0")
        weight_entry.pack(side=tk.LEFT, padx=5)
        
        # Yön
        direction_var = tk.StringVar(value=default_dir)
        ttk.Radiobutton(row, text="Max", variable=direction_var, value="max").pack(side=tk.LEFT)
        ttk.Radiobutton(row, text="Min", variable=direction_var, value="min").pack(side=tk.LEFT)
        
        self.objective_vars[key] = {
            'active': active_var,
            'target': target_entry,
            'weight': weight_entry,
            'direction': direction_var,
            'custom': True
        }


class MLStatusPanel(ttk.LabelFrame):
    """ML model durumu paneli"""
    
    def __init__(self, parent, on_train: Callable = None):
        super().__init__(parent, text="🧠 ML Model Durumu", padding=10)
        
        self.on_train = on_train
        
        # Durum bilgileri
        self.status_labels = {}
        
        info_frame = ttk.Frame(self)
        info_frame.pack(fill=tk.X, pady=5)
        
        labels = [
            ('trained', 'Model Durumu:', 'Eğitilmedi'),
            ('samples', 'Veri Sayısı:', '0'),
            ('last_training', 'Son Eğitim:', '-'),
            ('r2_score', 'R² Skoru:', '-'),
        ]
        
        for i, (key, label, default) in enumerate(labels):
            row = ttk.Frame(info_frame)
            row.pack(fill=tk.X, pady=1)
            
            ttk.Label(row, text=label, width=15).pack(side=tk.LEFT)
            value_label = ttk.Label(row, text=default, font=('Helvetica', 9, 'bold'))
            value_label.pack(side=tk.LEFT)
            
            self.status_labels[key] = value_label
        
        # Progress bar
        self.progress = ttk.Progressbar(self, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=5)
        
        # Eğit butonu
        ttk.Button(
            self,
            text="🔄 Modeli Eğit",
            command=self._train_model
        ).pack(fill=tk.X, pady=5)
        
        # Uyarı
        self.warning_label = ttk.Label(
            self, 
            text="",
            foreground="orange",
            wraplength=200
        )
        self.warning_label.pack(pady=5)
    
    def update_status(self, status: Dict):
        """Durumu güncelle"""
        if status.get('trained'):
            self.status_labels['trained'].config(text="✅ Eğitildi", foreground="green")
        else:
            self.status_labels['trained'].config(text="⚠️ Eğitilmedi", foreground="orange")
        
        self.status_labels['samples'].config(text=str(status.get('samples', 0)))
        
        last_training = status.get('last_training')
        if last_training:
            self.status_labels['last_training'].config(text=last_training[:10])
        
        r2 = status.get('r2_score')
        if r2:
            color = "green" if r2 > 0.7 else "orange" if r2 > 0.5 else "red"
            self.status_labels['r2_score'].config(text=f"{r2:.3f}", foreground=color)
        
        # Uyarı
        min_samples = status.get('min_samples_required', 3)
        current_samples = status.get('samples', 0)
        
        if current_samples < min_samples:
            self.warning_label.config(
                text=f"⚠️ En az {min_samples} kayıt gerekli. Mevcut: {current_samples}"
            )
        else:
            self.warning_label.config(text="")
    
    def _train_model(self):
        """Modeli eğit"""
        self.progress.start()
        
        if self.on_train:
            threading.Thread(
                target=self._do_train,
                daemon=True
            ).start()
    
    def _do_train(self):
        """Eğitimi arka planda çalıştır"""
        try:
            if self.on_train:
                result = self.on_train()
                
                def finish():
                    self.progress.stop()
                    
                    if result.get('success'):
                        msg = f"Model başarıyla eğitildi!\n"
                        msg += f"Örnek sayısı: {result.get('samples', 0)}"
                        messagebox.showinfo("Başarılı", msg)
                    else:
                        messagebox.showwarning("Uyarı", result.get('message', 'Eğitim başarısız'))
                
                self.after(0, finish)
        except Exception as e:
            def show_error():
                self.progress.stop()
                messagebox.showerror("Hata", str(e))
            self.after(0, show_error)


class PredictionPanel(ttk.LabelFrame):
    """
    Test Sonuçları Tahmin Paneli
    
    Formülasyon parametreleri girildiğinde ML model ile
    korozyon direnci, çizilme direnci, yapışma vb. test sonuçlarını tahmin eder.
    """
    
    def __init__(self, parent, on_predict: Callable = None):
        super().__init__(parent, text="🔮 Test Sonuçları Tahmini", padding=10)
        
        self.on_predict = on_predict
        self.input_entries = {}
        
        # Açıklama
        desc = ttk.Label(
            self,
            text="Formülasyon parametrelerini girin, ML model test sonuçlarını tahmin etsin",
            font=('Helvetica', 9, 'italic'),
            wraplength=300
        )
        desc.pack(anchor=tk.W, pady=(0, 10))
        
        # Girdi parametreleri
        input_frame = ttk.LabelFrame(self, text="Formülasyon Parametreleri", padding=5)
        input_frame.pack(fill=tk.X, pady=5)
        
        input_params = [
            ("Viskozite (cP):", "viscosity", "2000"),
            ("pH Değeri:", "ph", "8.0"),
            ("Yoğunluk (g/ml):", "density", "1.2"),
            ("Kaplama Kalınlığı (µm):", "coating_thickness", "50"),
        ]
        
        for i, (label, key, default) in enumerate(input_params):
            row = ttk.Frame(input_frame)
            row.pack(fill=tk.X, pady=2)
            
            ttk.Label(row, text=label, width=22).pack(side=tk.LEFT)
            entry = ttk.Entry(row, width=12)
            entry.insert(0, default)
            entry.pack(side=tk.LEFT, padx=5)
            self.input_entries[key] = entry
        
        # Tahmin butonu
        ttk.Button(
            self,
            text="🧠 Test Sonuçlarını Tahmin Et",
            command=self._predict
        ).pack(fill=tk.X, pady=10)
        
        # Sonuç alanı
        result_frame = ttk.LabelFrame(self, text="Tahmin Edilen Test Sonuçları", padding=5)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Treeview ile sonuçları göster
        columns = ('test', 'value', 'confidence')
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show='headings', height=10)
        
        self.result_tree.heading('test', text='Test Parametresi')
        self.result_tree.heading('value', text='Tahmin Değeri')
        self.result_tree.heading('confidence', text='Güven')
        
        self.result_tree.column('test', width=150)
        self.result_tree.column('value', width=100)
        self.result_tree.column('confidence', width=70)
        
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=scrollbar.set)
        
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Durum etiketi
        self.status_label = ttk.Label(self, text="", foreground="gray")
        self.status_label.pack(anchor=tk.W, pady=5)
    
    def _predict(self):
        """Tahmin yap"""
        # Girdileri topla
        params = {}
        for key, entry in self.input_entries.items():
            try:
                params[key] = float(entry.get())
            except ValueError:
                messagebox.showwarning("Uyarı", f"Geçerli bir {key} değeri girin!")
                return
        
        self.status_label.config(text="Tahmin yapılıyor...", foreground="blue")
        
        # Arka planda çalıştır
        if self.on_predict:
            threading.Thread(
                target=self._do_predict,
                args=(params,),
                daemon=True
            ).start()
    
    def _do_predict(self, params: dict):
        """Tahmini arka planda çalıştır"""
        try:
            if self.on_predict:
                result = self.on_predict(params)
                self._display_predictions(result)
        except Exception as e:
            self._show_error(str(e))
    
    def _display_predictions(self, result: dict):
        """Tahmin sonuçlarını göster"""
        def update():
            # Mevcut sonuçları temizle
            self.result_tree.delete(*self.result_tree.get_children())
            
            if result.get('success'):
                predictions = result.get('predictions', {})
                
                # Test parametresi isimleri
                param_names = {
                    'opacity': 'Örtücülük (%)',
                    'gloss': 'Parlaklık (GU)',
                    'quality_score': 'Kalite Skoru (1-10)',
                    'total_cost': 'Toplam Maliyet',
                    'corrosion_resistance': 'Korozyon Direnci',
                    'adhesion': 'Yapışma (0-5)',
                    'hardness': 'Sertlik (H)',
                    'flexibility': 'Esneklik',
                    'chemical_resistance': 'Kimyasal Dayanım',
                    'uv_resistance': 'UV Dayanımı',
                    'abrasion_resistance': 'Aşınma Direnci',
                    'scratch_resistance': 'Çizilme Direnci',
                }
                
                for key, value in predictions.items():
                    name = param_names.get(key, key)
                    # Güven seviyesi (basit tahmin)
                    confidence = "Yüksek" if value > 0 else "Düşük"
                    
                    self.result_tree.insert('', tk.END, values=(
                        name,
                        f"{value:.2f}" if isinstance(value, (int, float)) else str(value),
                        confidence
                    ))
                
                self.status_label.config(
                    text=f"✅ {len(predictions)} test sonucu tahmin edildi",
                    foreground="green"
                )
            else:
                self.status_label.config(
                    text=f"❌ {result.get('message', 'Tahmin başarısız')}",
                    foreground="red"
                )
        
        self.after(0, update)
    
    def _show_error(self, message: str):
        """Hata göster"""
        def update():
            self.status_label.config(text=f"❌ Hata: {message}", foreground="red")
        self.after(0, update)
