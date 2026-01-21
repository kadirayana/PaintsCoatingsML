"""
Paint Formulation AI - Modern Formulation Editor
=================================================
Excel-style formulation editor with inline editing.

This is a modern replacement for the old split-input layout.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Dict, List, Optional
import threading
import logging

from app.components.editor.excel_style_grid import ExcelStyleGrid

logger = logging.getLogger(__name__)


class ModernFormulationEditor(ttk.LabelFrame):
    """
    Modern Excel-style Formulation Editor.
    
    Features:
    - Inline cell editing (double-click to edit)
    - Tab/Enter navigation between cells
    - Auto-row creation when typing in last row
    - Real-time calculations
    - Material autocomplete
    - Scientific column naming
    """
    
    def __init__(
        self,
        parent,
        on_save: Callable = None,
        on_calculate: Callable = None,
        on_load_formulation: Callable = None,
        on_lookup_material: Callable = None,
        on_get_material_list: Callable = None,
        on_create_material: Callable = None,
        **kwargs
    ):
        super().__init__(parent, text="📋 Formülasyon Editörü", padding=10, **kwargs)
        
        self.on_save = on_save
        self.on_calculate = on_calculate
        self.on_load_formulation = on_load_formulation
        self.on_lookup_material = on_lookup_material
        self.on_get_material_list = on_get_material_list
        self.on_create_material = on_create_material
        
        self.current_project = None
        self.current_project_id = None
        self.formulation_list = []
        self.on_predict = None
        
        self._create_ui()
    
    def _create_ui(self):
        """Create the modern UI layout"""
        
        # === TOP: Project & Formulation Selection ===
        self._create_header_section()
        
        # === MIDDLE: Excel-Style Grid (Full Height) ===
        self._create_grid_section()
        
        # === BOTTOM: Summary & Actions ===
        self._create_footer_section()
    
    def _create_header_section(self):
        """Create project and formulation header"""
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Project selector
        project_frame = ttk.LabelFrame(header_frame, text="📁 Proje", padding=5)
        project_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        ttk.Label(project_frame, text="Proje:").pack(side=tk.LEFT)
        self.project_combo = ttk.Combobox(project_frame, width=25, state='readonly')
        self.project_combo.pack(side=tk.LEFT, padx=5)
        self.project_combo.bind('<<ComboboxSelected>>', self._on_project_selected)
        
        ttk.Button(
            project_frame, 
            text="➕ Yeni Proje",
            command=self._create_new_project
        ).pack(side=tk.LEFT, padx=5)
        
        # Formulation selector
        formula_frame = ttk.LabelFrame(header_frame, text="📋 Formülasyon", padding=5)
        formula_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(formula_frame, text="Kayıtlı:").pack(side=tk.LEFT)
        self.formulation_combo = ttk.Combobox(formula_frame, width=20, state='readonly')
        self.formulation_combo.pack(side=tk.LEFT, padx=5)
        self.formulation_combo.bind('<<ComboboxSelected>>', self._on_formulation_selected)
        
        # Formula code/name
        ttk.Separator(formula_frame, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Label(formula_frame, text="Kod:").pack(side=tk.LEFT)
        self.formula_code_entry = ttk.Entry(formula_frame, width=12)
        self.formula_code_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(formula_frame, text="Ad:").pack(side=tk.LEFT)
        self.formula_name_entry = ttk.Entry(formula_frame, width=20)
        self.formula_name_entry.pack(side=tk.LEFT, padx=5)
    
    def _create_grid_section(self):
        """Create the main Excel-style grid"""
        # Grid container - takes most of the space
        grid_frame = ttk.Frame(self)
        grid_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create Excel-style grid
        self.grid = ExcelStyleGrid(
            grid_frame,
            on_row_changed=self._on_row_changed,
            on_material_lookup=self._lookup_material,
            on_get_materials=self._get_materials
        )
        self.grid.pack(fill=tk.BOTH, expand=True)
        
        # Instructions label
        instructions = ttk.Label(
            grid_frame,
            text="💡 Çift tıklayarak düzenleyin • Tab ile sonraki hücreye geçin • Enter ile onaylayın",
            font=('Segoe UI', 9, 'italic'),
            foreground='gray'
        )
        instructions.pack(anchor='w', pady=(5, 0))
    
    def _create_footer_section(self):
        """Create summary and action buttons"""
        footer_frame = ttk.Frame(self)
        footer_frame.pack(fill=tk.X, pady=(10, 0))
        
        # === Summary Row ===
        summary_frame = ttk.LabelFrame(footer_frame, text=" Özet", padding=5)
        summary_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.summary_labels = {}
        summaries = [
            ('total_quantity', '📦 Toplam Miktar:', '0 kg'),
            ('total_solid', '🔵 Toplam Katı:', '0 kg'),
            ('solid_percent', '📊 Katı %:', '0%'),
            ('total_cost', '💰 Toplam Maliyet:', '0 TL'),
            ('row_count', '📝 Satır:', '0'),
        ]
        
        for key, label, default in summaries:
            frame = ttk.Frame(summary_frame)
            frame.pack(side=tk.LEFT, padx=15)
            
            ttk.Label(frame, text=label).pack(side=tk.LEFT)
            value_lbl = ttk.Label(frame, text=default, font=('Segoe UI', 10, 'bold'))
            value_lbl.pack(side=tk.LEFT, padx=5)
            self.summary_labels[key] = value_lbl
        
        # === Action Buttons ===
        btn_frame = ttk.Frame(footer_frame)
        btn_frame.pack(fill=tk.X)
        
        # Left side - Data operations
        left_btns = ttk.Frame(btn_frame)
        left_btns.pack(side=tk.LEFT)
        
        ttk.Button(
            left_btns,
            text="🧹 Temizle",
            command=self._clear_all
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            left_btns,
            text="📥 Şablon İndir",
            command=self._download_template
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            left_btns,
            text="📥 Excel'den Yükle",
            command=self._load_from_excel
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            left_btns,
            text="📤 Excel'e Aktar",
            command=self._export_to_excel
        ).pack(side=tk.LEFT, padx=2)
        
        # Right side - Main actions
        right_btns = ttk.Frame(btn_frame)
        right_btns.pack(side=tk.RIGHT)
        
        ttk.Button(
            right_btns,
            text="🔮 Tahmin Et",
            command=self._predict_results
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            right_btns,
            text="📊 Hesapla",
            command=self._calculate
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            right_btns,
            text="💾 Kaydet",
            command=self._save,
            style='Accent.TButton'
        ).pack(side=tk.LEFT, padx=2, ipadx=10)
        
        ttk.Button(
            right_btns,
            text="📑 Yeni Varyasyon",
            command=self._save_as_variation
        ).pack(side=tk.LEFT, padx=2)
        
        # === Prediction Panel (Collapsed by default) ===
        self._create_prediction_panel(footer_frame)
    
    def _create_prediction_panel(self, parent):
        """Create the prediction results panel"""
        self.prediction_frame = ttk.LabelFrame(parent, text="🔮 Tahmin Sonuçları", padding=10)
        self.prediction_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Thickness input
        input_row = ttk.Frame(self.prediction_frame)
        input_row.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(input_row, text="Kaplama Kalınlığı (µm):").pack(side=tk.LEFT)
        self.thickness_entry = ttk.Entry(input_row, width=8)
        self.thickness_entry.insert(0, "30")
        self.thickness_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            input_row,
            text="🔮 Tahmin Yap",
            command=self._predict_results
        ).pack(side=tk.LEFT, padx=10)
        
        # Results text
        self.prediction_text = tk.Text(
            self.prediction_frame,
            height=4,
            wrap=tk.WORD,
            state='disabled',
            font=('Consolas', 9),
            bg='#F5F5F5'
        )
        self.prediction_text.pack(fill=tk.X, pady=5)
    
    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================
    
    def _on_row_changed(self, item_id: str):
        """Handle row data change"""
        self._update_summary()
    
    def _on_project_selected(self, event=None):
        """Handle project selection"""
        project_name = self.project_combo.get()
        if project_name:
            self.current_project = project_name
            # Trigger formulation list refresh via callback
    
    def _on_formulation_selected(self, event=None):
        """Handle formulation selection"""
        selection = self.formulation_combo.get()
        if not selection or not self.on_load_formulation:
            return
        
        # Find formulation ID
        for item in self.formulation_list:
            if item.get('display') == selection or item.get('formula_code') == selection:
                formulation_id = item.get('id')
                if formulation_id:
                    self._load_formulation_by_id(formulation_id)
                break
    
    def _create_new_project(self):
        """Create new project dialog"""
        from tkinter import simpledialog
        
        name = simpledialog.askstring(
            "Yeni Proje",
            "Proje adı:",
            parent=self
        )
        
        if name:
            self.current_project = name
            # Should trigger project creation via callback
    
    def _lookup_material(self, identifier: str) -> Optional[Dict]:
        """Lookup material by name or code"""
        if self.on_lookup_material:
            return self.on_lookup_material(identifier)
        return None
    
    def _get_materials(self) -> List[Dict]:
        """Get all materials"""
        if self.on_get_material_list:
            try:
                return self.on_get_material_list()
            except Exception:
                pass
        return []
    
    def _update_summary(self):
        """Update summary labels"""
        totals = self.grid.get_totals()
        
        self.summary_labels['total_quantity'].config(
            text=f"{totals['total_quantity']:.2f} kg"
        )
        self.summary_labels['total_solid'].config(
            text=f"{totals['total_solid']:.2f} kg"
        )
        self.summary_labels['solid_percent'].config(
            text=f"{totals['solid_percent']:.1f}%"
        )
        self.summary_labels['total_cost'].config(
            text=f"{totals['total_cost']:.2f} TL"
        )
        self.summary_labels['row_count'].config(
            text=str(totals['row_count'])
        )
    
    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def _clear_all(self):
        """Clear all data"""
        if messagebox.askyesno("Temizle", "Tüm veriler silinecek. Emin misiniz?"):
            self.grid.clear_all()
            self.formula_code_entry.delete(0, tk.END)
            self.formula_name_entry.delete(0, tk.END)
            self._update_summary()
    
    def _calculate(self):
        """Trigger calculation"""
        self.grid._recalculate_all_percentages()
        self._update_summary()
        
        if self.on_calculate:
            data = self.get_formulation_data()
            self.on_calculate(data)
    
    def _save(self):
        """Save formulation (Overwrites existing trial if ID exists)"""
        self._perform_save(is_new_variation=False)
        
    def _save_as_variation(self):
        """Save as New Variation (Forces new ID)"""
        # Ask for new variation code
        from tkinter import simpledialog
        current_code = self.formula_code_entry.get().strip()
        new_code = simpledialog.askstring("Yeni Varyasyon", "Yeni Varyasyon Kodu:", initialvalue=current_code + "-v2")
        
        if new_code:
            self.formula_code_entry.delete(0, tk.END)
            self.formula_code_entry.insert(0, new_code)
            self._perform_save(is_new_variation=True)

    def _perform_save(self, is_new_variation=False):
        """Internal save logic"""
        formula_code = self.formula_code_entry.get().strip()
        formula_name = self.formula_name_entry.get().strip()
        
        if not formula_code:
            messagebox.showwarning("Uyarı", "Lütfen formül kodu girin!")
            self.formula_code_entry.focus_set()
            return
        
        data = self.get_formulation_data()
        
        if not data.get('components'):
            messagebox.showwarning("Uyarı", "Formülasyonda en az bir bileşen olmalı!")
            return
            
        data['is_new_variation'] = is_new_variation
        
        if self.on_save:
            result = self.on_save(data)
            if result:
                messagebox.showinfo("Başarılı", "Formülasyon kaydedildi!")
    
    def _download_template(self):
        """Download Excel template for formulation data entry"""
        file_path = filedialog.asksaveasfilename(
            title="Şablonu Kaydet",
            defaultextension=".xlsx",
            filetypes=[("Excel Dosyası", "*.xlsx")],
            initialfile="formulasyon_sablonu.xlsx"
        )
        
        if not file_path:
            return
        
        try:
            import xlsxwriter
            
            workbook = xlsxwriter.Workbook(file_path)
            worksheet = workbook.add_worksheet("Formülasyon")
            
            # === FORMATS ===
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True,
                'locked': True
            })
            
            unlocked_format = workbook.add_format({
                'locked': False,
                'border': 1
            })
            
            number_format = workbook.add_format({
                'locked': False,
                'border': 1,
                'num_format': '#,##0.00'
            })
            
            # === COLUMN WIDTHS (4 columns) ===
            worksheet.set_column('A:A', 20)  # Raw Material Code
            worksheet.set_column('B:B', 25)  # Material Name
            worksheet.set_column('C:C', 15)  # Quantity (kg)
            worksheet.set_column('D:D', 30)  # Notes
            
            # === HEADERS (4 columns) ===
            headers = [
                ('A1', 'Raw Material Code', 'Veritabanındaki malzeme kodunu giriniz.\nÖrnek: EP01, TIO2, SOLV-001'),
                ('B1', 'Material Name', 'İsteğe bağlı. Eğer kod yeni ise, bu isim malzemeyi oluşturmak için kullanılacaktır.\n\nOptional. If the code is new, this name will be used to create it.'),
                ('C1', 'Quantity (kg)', 'Kilogram cinsinden miktar giriniz.'),
                ('D1', 'Notes', 'İsteğe bağlı notlar.')
            ]
            
            for cell, text, comment in headers:
                worksheet.write(cell, text, header_format)
                worksheet.write_comment(cell, comment, {'visible': False, 'width': 250, 'height': 80})
            
            # === DATA VALIDATION (Quantity > 0) ===
            worksheet.data_validation('C2:C1000', {
                'validate': 'decimal',
                'criteria': '>',
                'value': 0,
                'error_message': 'Miktar 0\'dan büyük bir sayı olmalıdır.',
                'error_title': 'Geçersiz Değer'
            })
            
            # === FORMAT DATA CELLS ===
            for row in range(1, 101):  # Pre-format first 100 rows
                worksheet.write_blank(row, 0, None, unlocked_format)  # Material Code
                worksheet.write_blank(row, 1, None, unlocked_format)  # Material Name
                worksheet.write_blank(row, 2, None, number_format)    # Quantity
                worksheet.write_blank(row, 3, None, unlocked_format)  # Notes
            
            # === PROTECT WORKSHEET ===
            worksheet.protect('', {
                'format_cells': False,
                'format_columns': False,
                'format_rows': False,
                'insert_columns': False,
                'insert_rows': True,
                'insert_hyperlinks': False,
                'delete_columns': False,
                'delete_rows': True,
                'select_locked_cells': True,
                'sort': True,
                'autofilter': True,
                'pivot_tables': False,
                'select_unlocked_cells': True
            })
            
            # === ADD INSTRUCTIONS ===
            instructions_format = workbook.add_format({
                'italic': True,
                'font_color': '#666666',
                'font_size': 9
            })
            worksheet.write('A102', '💡 Hammadde Kodu giriniz. Yeni kodlar otomatik olarak veritabanına eklenecektir.', instructions_format)
            
            workbook.close()
            
            messagebox.showinfo(
                "Başarılı", 
                f"Şablon dosyası oluşturuldu:\n{file_path}\n\n"
                "Bu şablonu doldurup 'Excel'den Yükle' ile içe aktarabilirsiniz.\n\n"
                "NOT: Yeni malzeme kodları otomatik olarak veritabanına eklenecektir."
            )
            
        except ImportError:
            messagebox.showerror(
                "Hata", 
                "xlsxwriter kütüphanesi bulunamadı.\n\n"
                "Kurulum: pip install xlsxwriter"
            )
        except Exception as e:
            messagebox.showerror("Hata", f"Şablon oluşturma hatası:\n{e}")

    def _load_from_excel(self):
        """Load from Excel file"""
        file_path = filedialog.askopenfilename(
            title="Excel Dosyası Seç",
            filetypes=[
                ("Excel Dosyaları", "*.xlsx *.xls"),
                ("CSV Dosyaları", "*.csv"),
                ("Tüm Dosyalar", "*.*")
            ]
        )
        
        if file_path:
            self._import_excel(file_path)
    
    def _import_excel(self, file_path: str):
        """
        Import data from Excel with on-the-fly material creation.
        
        Logic:
        1. Read Excel columns (supports 4-column and legacy 2-column formats)
        2. For each row:
           A. Check if material exists in DB
           B. If not, create it with default values
           C. Get properties and add to grid
        3. Show feedback about newly created materials
        """
        try:
            import pandas as pd
            
            df = pd.read_excel(file_path, sheet_name=0)
            
            if df.empty:
                messagebox.showwarning("Uyarı", "Excel dosyası boş!")
                return
            
            # Normalize columns - handle template and legacy formats
            col_map = {}
            for col in df.columns:
                col_lower = str(col).lower().strip()
                
                # New 4-column format
                if col_lower in ['raw material code', 'hammadde kodu', 'material code', 'code', 'kod']:
                    col_map[col] = 'material_code'
                elif col_lower in ['material name', 'malzeme adı', 'malzeme ismi', 'name', 'ad', 'isim']:
                    col_map[col] = 'material_name'
                elif col_lower in ['quantity (kg)', 'quantity', 'ağırlık (kg)', 'ağırlık', 'miktar (kg)', 'miktar', 'weight', 'amount', 'qty']:
                    col_map[col] = 'quantity'
                elif col_lower in ['notes', 'notlar', 'note', 'not']:
                    col_map[col] = 'notes'
            
            df = df.rename(columns=col_map)
            
            # Track created materials and grid data
            data = []
            created_materials = []  # New materials created on-the-fly
            processed_codes = set()  # Track codes within this import to avoid duplicate creation attempts
            
            for _, row in df.iterrows():
                # Step 1: Extract material code (required)
                material_code = ''
                if 'material_code' in df.columns:
                    raw_code = row.get('material_code', '')
                    if pd.notna(raw_code):
                        material_code = str(raw_code).strip()
                
                if not material_code:
                    continue
                
                # Step 2: Extract material name (optional, used for new materials)
                material_name = ''
                if 'material_name' in df.columns:
                    raw_name = row.get('material_name', '')
                    if pd.notna(raw_name):
                        material_name = str(raw_name).strip()
                
                # Step 3: Extract quantity
                quantity = 0
                try:
                    qty_val = row.get('quantity', 0)
                    if pd.notna(qty_val):
                        quantity = float(qty_val)
                except (ValueError, TypeError):
                    pass
                
                # Step A: Check if material exists in DB
                material_info = None
                if self.on_lookup_material:
                    material_info = self.on_lookup_material(material_code)
                
                # Step B: Handle missing materials - Create on-the-fly
                if not material_info:
                    if self.on_create_material and material_code not in processed_codes:
                        # Create new material with defaults
                        name_for_new = material_name if material_name else material_code
                        was_created = self.on_create_material(material_code, name_for_new)
                        
                        if was_created:
                            created_materials.append(material_code)
                        
                        # Re-lookup to get the material info
                        material_info = self.on_lookup_material(material_code)
                        processed_codes.add(material_code)
                
                # Step C: Add to formulation data
                if material_info:
                    resolved_name = material_info.get('name', material_code)
                    resolved_code = material_info.get('code', material_code)
                    solid_content = material_info.get('solid_content', 100) or 100
                    unit_price = material_info.get('unit_price', 0) or 0
                else:
                    # Fallback if still not found (shouldn't happen)
                    resolved_name = material_name if material_name else material_code
                    resolved_code = material_code
                    solid_content = 100
                    unit_price = 0
                
                data.append({
                    'material_code': resolved_code,
                    'material_name': resolved_name,
                    'weight': quantity,
                    'solid_content': solid_content,
                    'unit_price': unit_price,
                })
            
            if data:
                self.grid.load_data(data)
                self._update_summary()
                
                # User feedback
                if created_materials:
                    messagebox.showinfo(
                        "İçe Aktarma Tamamlandı",
                        f"{len(data)} satır yüklendi!\n\n"
                        f"🆕 Aşağıdaki YENİ malzemeler varsayılan değerlerle veritabanına eklendi "
                        f"(Fiyat: 0, Katı: 100%). Lütfen Malzemeler sekmesinde güncelleyin:\n\n" +
                        "\n".join(f"• {code}" for code in created_materials[:10]) +
                        (f"\n... ve {len(created_materials) - 10} diğer" if len(created_materials) > 10 else "")
                    )
                else:
                    messagebox.showinfo("Başarılı", f"{len(data)} satır yüklendi!")
            else:
                messagebox.showwarning("Uyarı", "Geçerli veri bulunamadı!")
                
        except Exception as e:
            messagebox.showerror("Hata", f"Excel okuma hatası:\n{e}")
    
    def _export_to_excel(self):
        """Export to Excel file"""
        file_path = filedialog.asksaveasfilename(
            title="Excel'e Kaydet",
            defaultextension=".xlsx",
            filetypes=[("Excel Dosyası", "*.xlsx")]
        )
        
        if file_path:
            try:
                import pandas as pd
                
                data = self.grid.get_data()
                df = pd.DataFrame(data)
                
                # Rename columns to Turkish
                df = df.rename(columns={
                    'row_num': '#',
                    'material': 'Hammadde',
                    'quantity': 'Miktar (kg)',
                    'weight_pct': 'Ağırlık %',
                    'solid_content': 'Katı İçerik %',
                    'solid_mass': 'Katı Kütle (kg)',
                    'cost': 'Maliyet (TL)'
                })
                
                df.to_excel(file_path, index=False)
                messagebox.showinfo("Başarılı", f"Excel dosyası kaydedildi:\n{file_path}")
                
            except Exception as e:
                messagebox.showerror("Hata", f"Excel yazma hatası:\n{e}")
    
    def _predict_results(self):
        """Predict test results"""
        if not self.on_predict:
            messagebox.showinfo("Bilgi", "Tahmin özelliği henüz yapılandırılmadı.")
            return
        
        formulation_data = self.get_formulation_data()
        
        if not formulation_data.get('components'):
            messagebox.showwarning("Uyarı", "Tahmin için en az bir hammadde gerekli!")
            return
        
        try:
            thickness = float(self.thickness_entry.get())
        except ValueError:
            thickness = 30.0
        
        # Call prediction
        result = self.on_predict(formulation_data, thickness)
        self._display_prediction(result)
    
    def _display_prediction(self, result: Dict):
        """Display prediction results"""
        self.prediction_text.config(state='normal')
        self.prediction_text.delete(1.0, tk.END)
        
        if result and result.get('success'):
            predictions = result.get('predictions', {})
            
            lines = ["🔮 TAHMİN SONUÇLARI", "─" * 40]
            
            for key, value in predictions.items():
                if value is not None:
                    lines.append(f"  {key}: {value:.2f}")
            
            self.prediction_text.insert(tk.END, "\n".join(lines))
        else:
            message = result.get('message', 'Tahmin yapılamadı') if result else 'Tahmin yapılamadı'
            self.prediction_text.insert(tk.END, f"❌ {message}")
        
        self.prediction_text.config(state='disabled')
    
    def _load_formulation_by_id(self, formulation_id: int):
        """Load formulation by ID"""
        if self.on_load_formulation:
            data = self.on_load_formulation(formulation_id)
            if data:
                self.load_formulation(data)
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def get_formulation_data(self) -> Dict:
        """Get formulation data as dictionary"""
        totals = self.grid.get_totals()
        components = self.grid.get_data()
        
        return {
            'formula_code': self.formula_code_entry.get().strip(),
            'formula_name': self.formula_name_entry.get().strip(),
            'project': self.current_project,
            'project_id': self.current_project_id,
            'components': components,
            'totals': totals
        }
    
    def load_formulation(self, data: Dict):
        """Load formulation into editor"""
        try:
            # Set header fields - ensure values are strings, not None
            formula_code = data.get('formula_code') or data.get('trial_code') or ''
            formula_name = data.get('formula_name') or data.get('concept_name') or ''
            
            self.formula_code_entry.delete(0, tk.END)
            if formula_code:  # Only insert if there's a value
                self.formula_code_entry.insert(0, str(formula_code))
            
            self.formula_name_entry.delete(0, tk.END)
            if formula_name:  # Only insert if there's a value
                self.formula_name_entry.insert(0, str(formula_name))
            
            # Load components
            components = data.get('components', data.get('materials', []))
            if components:
                self.grid.load_data(components)
            
            self._update_summary()
            
        except Exception as e:
            logger.error(f"Error loading formulation: {e}")
            # Don't propagate error - just log it
    
    def load_projects(self, projects: List):
        """Load projects into dropdown"""
        if isinstance(projects, list):
            if projects and isinstance(projects[0], dict):
                names = [p.get('name', '') for p in projects if p.get('name')]
            else:
                names = [p for p in projects if p]  # Filter empty strings
            
            self.project_combo['values'] = names
    
    def load_formulation_list(self, formulations: List):
        """
        Load VALID formulations into dropdown.
        
        Filters out:
        - Entries without ID (not saved to DB)
        - Entries without valid formula_code
        - Entries with 'None' or placeholder codes
        """
        self.formulation_list = []
        display_values = []
        
        for f in formulations:
            # FILTER 1: Must have valid ID (saved to DB)
            fid = f.get('id')
            if not fid or fid == 'None':
                continue
            
            # FILTER 2: Must have valid formula_code
            code = f.get('formula_code') or f.get('trial_code') or ''
            code = str(code).strip()
            
            # FILTER 3: Skip None, empty, or placeholder codes
            if not code or code.lower() in ['none', 'null', '-', '']:
                continue
            
            # FILTER 4: Skip codes that look like auto-generated placeholders
            if code.startswith('-V') or code.startswith('None-'):
                continue
            
            # Valid entry - add to list
            name = f.get('formula_name') or f.get('concept_name') or ''
            name = str(name).strip() if name else ''
            
            display = f"{code} - {name}" if name else code
            f['display'] = display
            
            self.formulation_list.append(f)
            display_values.append(display)
        
        self.formulation_combo['values'] = display_values
        
        # Clear current selection if it's no longer valid
        current = self.formulation_combo.get()
        if current and current not in display_values:
            self.formulation_combo.set('')
        
        logger.debug(f"Loaded {len(display_values)} valid formulations (filtered from {len(formulations)})")
    
    def _clear_form(self):
        """
        Clear form for new formulation (draft state).
        
        This method:
        - Clears all input fields
        - Resets grid
        - Does NOT create any DB record
        - Keeps project selection
        """
        # Clear formula fields
        self.formula_code_entry.delete(0, tk.END)
        self.formula_name_entry.delete(0, tk.END)
        
        # Clear grid
        self.grid.clear_all()
        
        # Update summary
        self._update_summary()
        
        # Clear ComboBox selection (we're creating new, not editing existing)
        self.formulation_combo.set('')
        
        logger.debug("Form cleared for new formulation (draft state)")
    
    def start_new_formulation(self):
        """
        Start a new formulation in draft state.
        
        Public API for creating new formulation without touching DB.
        """
        self._clear_form()
    
    def get_current_project(self) -> Optional[str]:
        """Get current project name"""
        return self.current_project
    
    def get_current_project_id(self) -> Optional[int]:
        """Get current project ID"""
        return self.current_project_id
    
    def set_project(self, project_id: int, project_name: str):
        """Set current project (called by context)"""
        self.current_project_id = project_id
        self.current_project = project_name
        
        # Update ComboBox selection
        if project_name and project_name in self.project_combo['values']:
            self.project_combo.set(project_name)
    
    def set_prediction_callback(self, callback: Callable):
        """Set prediction callback"""
        self.on_predict = callback

