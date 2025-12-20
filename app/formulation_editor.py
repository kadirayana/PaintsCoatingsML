"""
Paint Formulation AI - Formülasyon Editörü
==========================================
Excel benzeri formülasyon giriş ve düzenleme paneli
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Dict, List, Optional
import threading


class FormulationEditorPanel(ttk.LabelFrame):
    """
    Excel benzeri Formülasyon Editörü
    
    Sütunlar:
    - Hammadde Kodu
    - Hammadde Adı
    - Katı Miktarı
    - %
    - Fiyat/Birim
    """
    
    def __init__(self, parent, on_save: Callable = None, on_calculate: Callable = None):
        super().__init__(parent, text="📋 Formülasyon Editörü", padding=10)
        
        self.on_save = on_save
        self.on_calculate = on_calculate
        self.row_count = 0
        self.current_project = None
        
        # Proje seçici
        project_frame = ttk.LabelFrame(self, text="📁 Proje", padding=5)
        project_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(project_frame, text="Proje:").pack(side=tk.LEFT)
        self.project_combo = ttk.Combobox(project_frame, width=30, state='readonly')
        self.project_combo.pack(side=tk.LEFT, padx=5)
        self.project_combo.bind('<<ComboboxSelected>>', self._on_project_selected)
        
        ttk.Button(project_frame, text="➕ Yeni Proje", command=self._create_new_project).pack(side=tk.LEFT, padx=5)
        
        # Üst bilgi alanı
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="Formül Kodu:").pack(side=tk.LEFT)
        self.formula_code_entry = ttk.Entry(header_frame, width=15)
        self.formula_code_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(header_frame, text="Formül Adı:").pack(side=tk.LEFT, padx=(20, 0))
        self.formula_name_entry = ttk.Entry(header_frame, width=25)
        self.formula_name_entry.pack(side=tk.LEFT, padx=5)
        
        # Tablo alanı
        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview - Excel benzeri tablo
        columns = ('row_num', 'code', 'name', 'solid_amount', 'percentage', 'price')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=12)
        
        # Sütun başlıkları
        self.tree.heading('row_num', text='#')
        self.tree.heading('code', text='Hammadde Kodu')
        self.tree.heading('name', text='Hammadde Adı')
        self.tree.heading('solid_amount', text='Katı Miktarı')
        self.tree.heading('percentage', text='%')
        self.tree.heading('price', text='Fiyat/Birim')
        
        # Sütun genişlikleri
        self.tree.column('row_num', width=30, anchor='center')
        self.tree.column('code', width=100)
        self.tree.column('name', width=150)
        self.tree.column('solid_amount', width=100, anchor='e')
        self.tree.column('percentage', width=60, anchor='e')
        self.tree.column('price', width=80, anchor='e')
        
        # Scrollbar
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Selection event
        self.tree.bind('<Double-1>', self._on_double_click)
        
        # Giriş alanları
        input_frame = ttk.LabelFrame(self, text="Satır Ekle/Düzenle", padding=5)
        input_frame.pack(fill=tk.X, pady=10)
        
        self.entry_vars = {}
        entries = [
            ('code', 'Kod:', 12),
            ('name', 'Ad:', 20),
            ('solid_amount', 'Katı Miktarı:', 10),
            ('percentage', '%:', 8),
            ('price', 'Fiyat:', 10),
        ]
        
        row = ttk.Frame(input_frame)
        row.pack(fill=tk.X, pady=2)
        
        for key, label, width in entries:
            ttk.Label(row, text=label).pack(side=tk.LEFT)
            entry = ttk.Entry(row, width=width)
            entry.pack(side=tk.LEFT, padx=2)
            self.entry_vars[key] = entry
        
        # Butonlar
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="➕ Satır Ekle", command=self._add_row).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="✏️ Güncelle", command=self._update_row).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑️ Satır Sil", command=self._delete_row).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🧹 Temizle", command=self._clear_all).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(btn_frame, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Button(btn_frame, text="📊 Hesapla", command=self._calculate).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="💾 Kaydet", command=self._save).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📥 Excel'den Yükle", command=self._load_from_excel).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📤 Excel'e Aktar", command=self._export_to_excel).pack(side=tk.LEFT, padx=2)
        
        # Özet bilgiler
        summary_frame = ttk.Frame(self)
        summary_frame.pack(fill=tk.X, pady=10)
        
        self.summary_labels = {}
        summaries = [
            ('total_solid', 'Toplam Katı:', '0'),
            ('total_percent', 'Toplam %:', '0'),
            ('total_cost', 'Toplam Maliyet:', '0'),
            ('row_count', 'Satır Sayısı:', '0'),
        ]
        
        for key, label, default in summaries:
            lbl_frame = ttk.Frame(summary_frame)
            lbl_frame.pack(side=tk.LEFT, padx=20)
            
            ttk.Label(lbl_frame, text=label).pack(side=tk.LEFT)
            value_lbl = ttk.Label(lbl_frame, text=default, font=('Helvetica', 10, 'bold'))
            value_lbl.pack(side=tk.LEFT, padx=5)
            self.summary_labels[key] = value_lbl
        
        # === TAHMİN SONUÇLARI PANELİ ===
        self.prediction_frame = ttk.LabelFrame(self, text="🔮 Muhtemel Test Sonuçları (Tahmin)", padding=5)
        self.prediction_frame.pack(fill=tk.X, pady=10)
        
        # Kaplama kalınlığı girişi
        thickness_row = ttk.Frame(self.prediction_frame)
        thickness_row.pack(fill=tk.X, pady=5)
        
        ttk.Label(thickness_row, text="Kaplama Kalınlığı (µm):").pack(side=tk.LEFT)
        self.thickness_entry = ttk.Entry(thickness_row, width=8)
        self.thickness_entry.insert(0, "30")
        self.thickness_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(thickness_row, text="🔮 Tahmin Yap", command=self._predict_results).pack(side=tk.LEFT, padx=10)
        
        # Tahmin sonuçları gösterim alanı
        self.prediction_text = tk.Text(self.prediction_frame, height=6, wrap=tk.WORD, state='disabled')
        self.prediction_text.pack(fill=tk.X, pady=5)
        
        # Bilgilendirme etiketi
        info_label = ttk.Label(
            self.prediction_frame, 
            text="💡 Formülasyon hammaddelerinize göre ML modeli muhtemel test sonuçlarını tahmin eder",
            font=('Helvetica', 8, 'italic')
        )
        info_label.pack(anchor=tk.W)
        
        # Tahmin callback
        self.on_predict = None
    
    def _add_row(self):
        """Satır ekle"""
        self.row_count += 1
        
        code = self.entry_vars['code'].get().strip()
        name = self.entry_vars['name'].get().strip()
        solid = self.entry_vars['solid_amount'].get().strip() or '0'
        percent = self.entry_vars['percentage'].get().strip() or '0'
        price = self.entry_vars['price'].get().strip() or '0'
        
        if not code:
            code = f"HM{self.row_count:03d}"
        
        self.tree.insert('', tk.END, values=(
            self.row_count,
            code,
            name,
            solid,
            percent,
            price
        ))
        
        self._clear_inputs()
        self._update_summary()
    
    def _update_row(self):
        """Seçili satırı güncelle"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Uyarı", "Güncellenecek satırı seçin!")
            return
        
        item = selection[0]
        current_values = self.tree.item(item)['values']
        row_num = current_values[0]
        
        code = self.entry_vars['code'].get().strip() or current_values[1]
        name = self.entry_vars['name'].get().strip() or current_values[2]
        solid = self.entry_vars['solid_amount'].get().strip() or current_values[3]
        percent = self.entry_vars['percentage'].get().strip() or current_values[4]
        price = self.entry_vars['price'].get().strip() or current_values[5]
        
        self.tree.item(item, values=(row_num, code, name, solid, percent, price))
        self._update_summary()
    
    def _delete_row(self):
        """Seçili satırı sil"""
        selection = self.tree.selection()
        if not selection:
            return
        
        if messagebox.askyesno("Onay", "Seçili satırı silmek istiyor musunuz?"):
            for item in selection:
                self.tree.delete(item)
            self._update_summary()
    
    def _clear_all(self):
        """Tüm satırları temizle"""
        if messagebox.askyesno("Onay", "Tüm satırları silmek istiyor musunuz?"):
            self.tree.delete(*self.tree.get_children())
            self.row_count = 0
            self._update_summary()
    
    def _clear_inputs(self):
        """Giriş alanlarını temizle"""
        for entry in self.entry_vars.values():
            entry.delete(0, tk.END)
    
    def _on_double_click(self, event):
        """Çift tıklama ile düzenleme"""
        selection = self.tree.selection()
        if selection:
            values = self.tree.item(selection[0])['values']
            
            self.entry_vars['code'].delete(0, tk.END)
            self.entry_vars['code'].insert(0, values[1])
            
            self.entry_vars['name'].delete(0, tk.END)
            self.entry_vars['name'].insert(0, values[2])
            
            self.entry_vars['solid_amount'].delete(0, tk.END)
            self.entry_vars['solid_amount'].insert(0, values[3])
            
            self.entry_vars['percentage'].delete(0, tk.END)
            self.entry_vars['percentage'].insert(0, values[4])
            
            self.entry_vars['price'].delete(0, tk.END)
            self.entry_vars['price'].insert(0, values[5])
    
    def _update_summary(self):
        """Özet bilgileri güncelle"""
        total_solid = 0
        total_percent = 0
        total_cost = 0
        count = 0
        
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            count += 1
            
            # Değerleri güvenli şekilde dönüştür
            solid_val = self._safe_float(values[3])
            percent_val = self._safe_float(values[4])
            price_val = self._safe_float(values[5])
            
            total_solid += solid_val
            total_percent += percent_val
            total_cost += solid_val * price_val
        
        self.summary_labels['total_solid'].config(text=f"{total_solid:.2f}")
        self.summary_labels['total_percent'].config(
            text=f"{total_percent:.1f}%",
            foreground="green" if 99 <= total_percent <= 101 else "red"
        )
        self.summary_labels['total_cost'].config(text=f"{total_cost:.2f}")
        self.summary_labels['row_count'].config(text=str(count))
    
    def _calculate(self):
        """Hesaplama yap"""
        self._update_summary()
        
        if self.on_calculate:
            data = self.get_formulation_data()
            self.on_calculate(data)
    
    def _save(self):
        """Formülasyonu kaydet"""
        formula_code = self.formula_code_entry.get().strip()
        formula_name = self.formula_name_entry.get().strip()
        
        if not formula_code:
            messagebox.showwarning("Uyarı", "Formül kodu girilmelidir!")
            return
        
        data = self.get_formulation_data()
        data['formula_code'] = formula_code
        data['formula_name'] = formula_name
        
        if self.on_save:
            self.on_save(data)
            messagebox.showinfo("Başarılı", f"Formülasyon kaydedildi: {formula_code}")
    
    def _load_from_excel(self):
        """Excel'den yükle"""
        file_path = filedialog.askopenfilename(
            title="Excel Dosyası Seç",
            filetypes=[("Excel", "*.xlsx *.xls"), ("CSV", "*.csv")]
        )
        
        if file_path:
            try:
                from src.data_handlers.file_system_manager import FileSystemManager
                fs = FileSystemManager()
                data = fs.read_excel(file_path)
                
                if not data:
                    messagebox.showwarning("Uyarı", "Dosyada veri bulunamadı!")
                    return
                
                # Verileri tabloya yükle
                self.tree.delete(*self.tree.get_children())
                self.row_count = 0
                
                # İlk satırın sütunlarını al
                first_row = data[0]
                columns = list(first_row.keys())
                
                # Sütun eşleştirmesi - çeşitli varyasyonları destekle
                code_keys = ['hammadde_kodu', 'code', 'kod', 'Kod', 'Hammadde Kodu', 'HAMMADDE KODU', 'Column_0']
                name_keys = ['hammadde_adi', 'name', 'ad', 'Ad', 'Hammadde Adı', 'HAMMADDE ADI', 'Adı', 'Column_1']
                solid_keys = ['kati_miktari', 'solid_amount', 'katı', 'Katı', 'Katı Miktarı', 'KATI MİKTARI', 'miktar', 'Miktar', 'Column_2']
                percent_keys = ['yuzde', 'percentage', '%', 'Yüzde', 'YÜZDE', 'oran', 'Oran', 'Column_3']
                price_keys = ['fiyat', 'price', 'Fiyat', 'FİYAT', 'birim fiyat', 'Birim Fiyat', 'Column_4']
                
                def find_value(row, key_list, default=''):
                    for key in key_list:
                        if key in row:
                            val = row[key]
                            return val if val is not None else default
                    # Eğer eşleşme yoksa sırayla dene
                    row_values = list(row.values())
                    idx = key_list.index(key_list[-1].replace('Column_', '')) if key_list[-1].startswith('Column_') else -1
                    if idx >= 0 and idx < len(row_values):
                        return row_values[idx] if row_values[idx] is not None else default
                    return default
                
                for row in data:
                    self.row_count += 1
                    
                    # Değerleri bul
                    code = find_value(row, code_keys, f'HM{self.row_count:03d}')
                    name = find_value(row, name_keys, '')
                    solid = find_value(row, solid_keys, 0)
                    percent = find_value(row, percent_keys, 0)
                    price = find_value(row, price_keys, 0)
                    
                    # Eğer hala boşsa, sırayla sütunları kullan
                    if not name and len(row) >= 2:
                        values = list(row.values())
                        code = values[0] if len(values) > 0 else code
                        name = values[1] if len(values) > 1 else name
                        solid = values[2] if len(values) > 2 else solid
                        percent = values[3] if len(values) > 3 else percent
                        price = values[4] if len(values) > 4 else price
                    
                    self.tree.insert('', tk.END, values=(
                        self.row_count,
                        code,
                        name,
                        solid,
                        percent,
                        price
                    ))
                
                self._update_summary()
                messagebox.showinfo("Başarılı", f"{len(data)} satır yüklendi!\n\nSütunlar: {', '.join(columns[:5])}")
            except Exception as e:
                messagebox.showerror("Hata", f"Dosya yüklenemedi: {str(e)}")
    
    def _export_to_excel(self):
        """Excel'e aktar"""
        file_path = filedialog.asksaveasfilename(
            title="Excel Dosyası Kaydet",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")]
        )
        
        if file_path:
            try:
                from src.data_handlers.file_system_manager import FileSystemManager
                fs = FileSystemManager()
                
                data = []
                for item in self.tree.get_children():
                    values = self.tree.item(item)['values']
                    data.append({
                        'hammadde_kodu': values[1],
                        'hammadde_adi': values[2],
                        'kati_miktari': values[3],
                        'yuzde': values[4],
                        'fiyat': values[5]
                    })
                
                fs.write_excel(data, file_path)
                messagebox.showinfo("Başarılı", f"Dosya kaydedildi: {file_path}")
            except Exception as e:
                messagebox.showerror("Hata", f"Dosya kaydedilemedi: {str(e)}")
    
    def get_formulation_data(self) -> dict:
        """Formülasyon verilerini al"""
        components = []
        
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            components.append({
                'code': values[1],
                'name': values[2],
                'solid_amount': float(values[3]) if values[3] else 0,
                'percentage': float(values[4]) if values[4] else 0,
                'price': float(values[5]) if values[5] else 0
            })
        
        return {
            'formula_code': self.formula_code_entry.get().strip(),
            'formula_name': self.formula_name_entry.get().strip(),
            'components': components,
            'total_solid': sum(c['solid_amount'] for c in components),
            'total_percent': sum(c['percentage'] for c in components),
            'total_cost': sum(c['solid_amount'] * c['price'] for c in components)
        }
    
    def load_formulation(self, data: dict):
        """Formülasyon yükle"""
        self.tree.delete(*self.tree.get_children())
        self.row_count = 0
        
        self.formula_code_entry.delete(0, tk.END)
        self.formula_code_entry.insert(0, data.get('formula_code', ''))
        
        self.formula_name_entry.delete(0, tk.END)
        self.formula_name_entry.insert(0, data.get('formula_name', ''))
        
        for comp in data.get('components', []):
            self.row_count += 1
            self.tree.insert('', tk.END, values=(
                self.row_count,
                comp.get('code', ''),
                comp.get('name', ''),
                comp.get('solid_amount', 0),
                comp.get('percentage', 0),
                comp.get('price', 0)
            ))
        
        self._update_summary()
    
    def _on_project_selected(self, event=None):
        """Proje seçildiğinde"""
        self.current_project = self.project_combo.get()
    
    def _create_new_project(self):
        """Yeni proje oluştur"""
        from tkinter import simpledialog
        project_name = simpledialog.askstring("Yeni Proje", "Proje adı:")
        if project_name:
            current_values = list(self.project_combo['values']) if self.project_combo['values'] else []
            current_values.append(project_name)
            self.project_combo['values'] = current_values
            self.project_combo.set(project_name)
            self.current_project = project_name
            messagebox.showinfo("Başarılı", f"Proje oluşturuldu: {project_name}")
    
    def load_projects(self, projects: list):
        """Projeleri yükle"""
        project_names = [p.get('name', '') for p in projects if p.get('name')]
        self.project_combo['values'] = project_names
        if project_names:
            self.project_combo.current(0)
            self.current_project = project_names[0]
    
    def get_current_project(self) -> str:
        """Aktif projeyi döndür"""
        return self.current_project or self.project_combo.get()
    
    def set_prediction_callback(self, callback):
        """Tahmin callback fonksiyonunu ayarla"""
        self.on_predict = callback
    
    def _predict_results(self):
        """Formülasyon için test sonuçlarını tahmin et"""
        if not self.on_predict:
            self._show_prediction_message("⚠️ ML modeli henüz bağlanmadı.\nOptimizasyon sekmesinden modeli eğitin.")
            return
        
        # Formülasyon verilerini topla
        formulation = self.get_formulation_data()
        
        if not formulation.get('components'):
            self._show_prediction_message("⚠️ Önce formülasyon hammaddelerini girin.")
            return
        
        try:
            thickness = float(self.thickness_entry.get() or 30)
        except ValueError:
            thickness = 30
        
        # Tahmin için parametreler
        params = {
            'viscosity': 100,  # Varsayılan
            'ph': 7.0,
            'density': 1.0,
            'coating_thickness': thickness,
            'total_cost': formulation.get('total_cost', 0),
            'formulation': formulation
        }
        
        # Tahmin yap
        result = self.on_predict(params)
        
        if result.get('success'):
            self._display_prediction_results(result, thickness)
        else:
            self._show_prediction_message(f"⚠️ {result.get('message', 'Tahmin yapılamadı')}")
    
    def _display_prediction_results(self, result: dict, thickness: float):
        """Tahmin sonuçlarını formatlı göster"""
        predictions = result.get('predictions', {})
        
        lines = [
            f"📊 {thickness}µm Kaplama Kalınlığında Muhtemel Sonuçlar:",
            "-" * 45,
        ]
        
        # Hedef isimleri
        target_names = {
            'opacity': 'Örtücülük',
            'gloss': 'Parlaklık (GU)',
            'corrosion_resistance': 'Korozyon Direnci (saat)',
            'adhesion': 'Yapışma (0-5)',
            'hardness': 'Sertlik (H)',
            'quality_score': 'Kalite Skoru (1-10)',
            'flexibility': 'Esneklik',
            'chemical_resistance': 'Kimyasal Dayanım',
            'uv_resistance': 'UV Dayanımı',
            'abrasion_resistance': 'Aşınma Direnci',
        }
        
        for key, value in predictions.items():
            name = target_names.get(key, key.replace('_', ' ').title())
            
            # Aralık göster (±10%)
            if isinstance(value, (int, float)):
                min_val = value * 0.9
                max_val = value * 1.1
                lines.append(f"  • {name}: {min_val:.1f} - {max_val:.1f} (tahmini: {value:.1f})")
            else:
                lines.append(f"  • {name}: {value}")
        
        lines.append("")
        lines.append("💡 Bu değerler ML modelinin tahminleridir. Gerçek değerler farklılık gösterebilir.")
        
        self._show_prediction_message("\n".join(lines))
    
    def _show_prediction_message(self, message: str):
        """Tahmin mesajını göster"""
        self.prediction_text.config(state='normal')
        self.prediction_text.delete(1.0, tk.END)
        self.prediction_text.insert(tk.END, message)
        self.prediction_text.config(state='disabled')
    
    def _safe_float(self, value) -> float:
        """Değeri güvenli şekilde float'a dönüştür"""
        if value is None or value == '':
            return 0.0
        try:
            # Zaten sayı ise
            if isinstance(value, (int, float)):
                return float(value)
            # String ise
            str_val = str(value).strip()
            # Virgülü noktaya çevir (Türkçe format)
            str_val = str_val.replace(',', '.')
            return float(str_val)
        except (ValueError, TypeError):
            return 0.0
