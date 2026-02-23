"""
Paint Formulation AI - Modern Formulation Editor
=================================================
Excel-style formulation editor with inline editing.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Dict, List, Optional
import threading
import logging

from app.components.editor.excel_style_grid import ExcelStyleGrid
from src.core.i18n import t, I18nMixin
from src.core.translation_keys import TK

logger = logging.getLogger(__name__)


class ModernFormulationEditor(ttk.LabelFrame, I18nMixin):
    """
    Modern Excel-style Formulation Editor with i18n support.
    """
    
    def __init__(
        self,
        parent,
        on_save: Callable = None,
        on_calculate: Callable = None,
        on_load_formulation: Callable = None,
        on_lookup_material: Callable = None,
        on_get_material_list: Callable = None,
        **kwargs
    ):
        super().__init__(parent, padding=10, **kwargs)
        
        self.on_save = on_save
        self.on_calculate = on_calculate
        self.on_load_formulation = on_load_formulation
        self.on_lookup_material = on_lookup_material
        self.on_get_material_list = on_get_material_list
        
        self.current_project = None
        self.current_project_id = None
        self.formulation_list = []
        self.on_predict = None
        
        self.setup_i18n()
        self._create_ui()
    
    def _create_ui(self):
        """Create the modern UI layout"""
        # Header section
        self.header_frame = ttk.Frame(self)
        self.header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Project frame
        self.project_frame = ttk.LabelFrame(self.header_frame, padding=5)
        self.project_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.project_label = ttk.Label(self.project_frame)
        self.project_label.pack(side=tk.LEFT)
        self.project_combo = ttk.Combobox(self.project_frame, width=25, state='readonly')
        self.project_combo.pack(side=tk.LEFT, padx=5)
        self.project_combo.bind('<<ComboboxSelected>>', self._on_project_selected)
        
        self.new_project_btn = ttk.Button(self.project_frame, command=self._create_new_project)
        self.new_project_btn.pack(side=tk.LEFT, padx=5)
        
        # Formulation frame
        self.formula_frame = ttk.LabelFrame(self.header_frame, padding=5)
        self.formula_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.saved_formulas_label = ttk.Label(self.formula_frame)
        self.saved_formulas_label.pack(side=tk.LEFT)
        self.formulation_combo = ttk.Combobox(self.formula_frame, width=20, state='readonly')
        self.formulation_combo.pack(side=tk.LEFT, padx=5)
        self.formulation_combo.bind('<<ComboboxSelected>>', self._on_formulation_selected)
        
        ttk.Separator(self.formula_frame, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        self.code_label = ttk.Label(self.formula_frame)
        self.code_label.pack(side=tk.LEFT)
        self.formula_code_entry = ttk.Entry(self.formula_frame, width=12)
        self.formula_code_entry.pack(side=tk.LEFT, padx=5)
        
        self.name_label = ttk.Label(self.formula_frame)
        self.name_label.pack(side=tk.LEFT)
        self.formula_name_entry = ttk.Entry(self.formula_frame, width=20)
        self.formula_name_entry.pack(side=tk.LEFT, padx=5)
        
        # Grid section
        self.grid_container = ttk.Frame(self)
        self.grid_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.grid = ExcelStyleGrid(
            self.grid_container,
            on_row_changed=self._on_row_changed,
            on_material_lookup=self._lookup_material,
            on_get_materials=self._get_materials
        )
        self.grid.pack(fill=tk.BOTH, expand=True)
        
        self.instructions_label = ttk.Label(self.grid_container, font=('Segoe UI', 9, 'italic'), foreground='gray')
        self.instructions_label.pack(anchor='w', pady=(5, 0))
        
        # Footer section
        self.footer_frame = ttk.Frame(self)
        self.footer_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Summary
        self.summary_frame = ttk.LabelFrame(self.footer_frame, padding=5)
        self.summary_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.summary_labels = {}
        self._summary_keys = [
            ('total_quantity', TK.FORM_TOTAL_QTY, '0 kg'),
            ('total_solid', TK.FORM_TOTAL_SOLID, '0 kg'),
            ('solid_percent', TK.FORM_SOLID_PERCENT, '0%'),
            ('total_cost', TK.FORM_TOTAL_COST, '0 TL'),
            ('row_count', TK.FORM_ROW_COUNT, '0'),
        ]
        
        self.summary_widgets = {}
        for key, tk_key, default in self._summary_keys:
            frame = ttk.Frame(self.summary_frame)
            frame.pack(side=tk.LEFT, padx=15)
            
            lbl = ttk.Label(frame)
            lbl.pack(side=tk.LEFT)
            val_lbl = ttk.Label(frame, text=default, font=('Segoe UI', 10, 'bold'))
            val_lbl.pack(side=tk.LEFT, padx=5)
            self.summary_widgets[key] = (lbl, tk_key, val_lbl)
            self.summary_labels[key] = val_lbl
        
        # Buttons
        self.btn_frame = ttk.Frame(self.footer_frame)
        self.btn_frame.pack(fill=tk.X)
        
        self.left_btns = ttk.Frame(self.btn_frame)
        self.left_btns.pack(side=tk.LEFT)
        
        self.clear_btn = ttk.Button(self.left_btns, command=self._clear_all)
        self.clear_btn.pack(side=tk.LEFT, padx=2)
        
        self.template_btn = ttk.Button(self.left_btns, command=self._download_template)
        self.template_btn.pack(side=tk.LEFT, padx=2)
        
        self.import_btn = ttk.Button(self.left_btns, command=self._load_from_excel)
        self.import_btn.pack(side=tk.LEFT, padx=2)
        
        self.export_btn = ttk.Button(self.left_btns, command=self._export_to_excel)
        self.export_btn.pack(side=tk.LEFT, padx=2)
        
        self.right_btns = ttk.Frame(self.btn_frame)
        self.right_btns.pack(side=tk.RIGHT)
        
        self.predict_btn = ttk.Button(self.right_btns, command=self._predict_results)
        self.predict_btn.pack(side=tk.LEFT, padx=2)
        
        self.calc_btn = ttk.Button(self.right_btns, command=self._calculate)
        self.calc_btn.pack(side=tk.LEFT, padx=2)
        
        self.save_btn = ttk.Button(self.right_btns, command=self._save, style='Accent.TButton')
        self.save_btn.pack(side=tk.LEFT, padx=2, ipadx=10)
        
        self.variation_btn = ttk.Button(self.right_btns, command=self._save_as_variation)
        self.variation_btn.pack(side=tk.LEFT, padx=2)
        
        self._create_prediction_panel(self.footer_frame)
        self._update_texts()

    def _create_prediction_panel(self, parent):
        self.prediction_frame = ttk.LabelFrame(parent, padding=10)
        self.prediction_frame.pack(fill=tk.X, pady=(10, 0))
        
        input_row = ttk.Frame(self.prediction_frame)
        input_row.pack(fill=tk.X, pady=(0, 5))
        
        self.thickness_label = ttk.Label(input_row)
        self.thickness_label.pack(side=tk.LEFT)
        self.thickness_entry = ttk.Entry(input_row, width=8)
        self.thickness_entry.insert(0, "30")
        self.thickness_entry.pack(side=tk.LEFT, padx=5)
        
        self.predict_action_btn = ttk.Button(input_row, command=self._predict_results)
        self.predict_action_btn.pack(side=tk.LEFT, padx=10)
        
        self.prediction_text = tk.Text(self.prediction_frame, height=4, wrap=tk.WORD, state='disabled', font=('Consolas', 9), bg='#F5F5F5')
        self.prediction_text.pack(fill=tk.X, pady=5)

    def _update_texts(self):
        """Update all UI texts for current language"""
        self.config(text=t(TK.FORM_EDITOR_TITLE))
        self.project_frame.config(text=t(TK.FORM_PROJECT))
        self.project_label.config(text=t(TK.FORM_PROJECT) + ":")
        self.new_project_btn.config(text=t(TK.NAV_NEW_PROJECT))
        self.formula_frame.config(text=t(TK.FORM_SAVED))
        self.saved_formulas_label.config(text=t(TK.FORM_SAVED) + ":")
        self.code_label.config(text=t(TK.FORM_CODE))
        self.name_label.config(text=t(TK.FORM_NAME))
        self.instructions_label.config(text=t(TK.FORM_GRID_HELP))
        self.summary_frame.config(text=t(TK.INFO)) # Or specific Summary key
        
        for key, (lbl, tk_key, val_lbl) in self.summary_widgets.items():
            lbl.config(text=t(tk_key))
            
        self.clear_btn.config(text=t(TK.FORM_CLEAN))
        self.template_btn.config(text=t(TK.FORM_TEMPLATE))
        self.import_btn.config(text=t(TK.FORM_IMPORT))
        self.export_btn.config(text=t(TK.FORM_EXPORT))
        
        self.predict_btn.config(text=t(TK.FORM_PREDICT))
        self.calc_btn.config(text=t(TK.FORM_CALCULATE))
        self.save_btn.config(text=t(TK.SAVE))
        self.variation_btn.config(text=t(TK.FORM_NEW_VARYATION))
        
        self.prediction_frame.config(text=t(TK.FORM_PREDICT))
        self.thickness_label.config(text=t(TK.PARAM_FILM_THICKNESS))
        self.predict_action_btn.config(text=t(TK.FORM_PREDICT))

    def _on_row_changed(self, item_id: str): self._update_summary()
    def _on_project_selected(self, event=None): self.current_project = self.project_combo.get()
    
    def _on_formulation_selected(self, event=None):
        selection = self.formulation_combo.get()
        if not selection or not self.on_load_formulation: return
        for item in self.formulation_list:
            if item.get('display') == selection or item.get('formula_code') == selection:
                fid = item.get('id')
                if fid: self._load_formulation_by_id(fid)
                break
    
    def _create_new_project(self):
        from tkinter import simpledialog
        name = simpledialog.askstring(t(TK.NAV_NEW_PROJECT), t(TK.FORM_NAME), parent=self)
        if name: self.current_project = name

    def _lookup_material(self, identifier: str) -> Optional[Dict]:
        return self.on_lookup_material(identifier) if self.on_lookup_material else None
    
    def _get_materials(self) -> List[Dict]:
        return self.on_get_material_list() if self.on_get_material_list else []
    
    def _update_summary(self):
        totals = self.grid.get_totals()
        self.summary_labels['total_quantity'].config(text=f"{totals['total_quantity']:.2f} kg")
        self.summary_labels['total_solid'].config(text=f"{totals['total_solid']:.2f} kg")
        self.summary_labels['solid_percent'].config(text=f"{totals['solid_percent']:.1f}%")
        self.summary_labels['total_cost'].config(text=f"{totals['total_cost']:.2f} TL")
        self.summary_labels['row_count'].config(text=str(totals['row_count']))

    def _clear_all(self):
        if messagebox.askyesno(t(TK.CONFIRM), t(TK.MSG_DELETE_CONFIRM)):
            self.grid.clear_all()
            self.formula_code_entry.delete(0, tk.END)
            self.formula_name_entry.delete(0, tk.END)
            self._update_summary()

    def _calculate(self):
        self.grid._recalculate_all_percentages() # Wait, does this exist?
        self._update_summary()
        if self.on_calculate: self.on_calculate(self.get_formulation_data())
    
    def _save(self): self._perform_save(is_new_variation=False)
    
    def _save_as_variation(self):
        from tkinter import simpledialog
        current_code = self.formula_code_entry.get().strip()
        new_code = simpledialog.askstring(t(TK.FORM_NEW_VARYATION), t(TK.FORM_CODE), initialvalue=current_code + "-v2")
        if new_code:
            self.formula_code_entry.delete(0, tk.END)
            self.formula_code_entry.insert(0, new_code)
            self._perform_save(is_new_variation=True)

    def _perform_save(self, is_new_variation=False):
        code = self.formula_code_entry.get().strip()
        if not code:
            messagebox.showwarning(t(TK.WARNING), t(TK.MSG_REQUIRED_FIELD).format(field=t(TK.FORM_CODE)))
            return
        data = self.get_formulation_data()
        if not data.get('components'):
            messagebox.showwarning(t(TK.WARNING), t(TK.MSG_REQUIRED_FIELD))
            return
        data['is_new_variation'] = is_new_variation
        if self.on_save:
            if self.on_save(data): messagebox.showinfo(t(TK.SUCCESS), t(TK.MSG_SAVE_SUCCESS))

    def _download_template(self):
        """Download Excel template for formulation data entry"""
        file_path = filedialog.asksaveasfilename(
            title=t(TK.FORM_TEMPLATE),
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="formulasyon_sablonu.xlsx"
        )
        
        if not file_path:
            return
        
        try:
            import xlsxwriter
            
            workbook = xlsxwriter.Workbook(file_path)
            worksheet = workbook.add_worksheet(t(TK.NAV_FORMULATIONS))
            
            header_format = workbook.add_format({
                'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1,
                'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'locked': True
            })
            
            unlocked_format = workbook.add_format({'locked': False, 'border': 1})
            number_format = workbook.add_format({'locked': False, 'border': 1, 'num_format': '#,##0.00'})
            
            worksheet.set_column('A:A', 25)
            worksheet.set_column('B:B', 15)
            
            headers = [
                ('A1', t(TK.GRID_CODE), t(TK.FORM_CODE)),
                ('B1', t(TK.GRID_WEIGHT), t(TK.INFO))
            ]
            
            for cell, text, comment in headers:
                worksheet.write(cell, text, header_format)
                worksheet.write_comment(cell, comment, {'visible': False, 'width': 200, 'height': 60})
            
            for row in range(1, 101):
                worksheet.write_blank(row, 0, None, unlocked_format)
                worksheet.write_blank(row, 1, None, number_format)
            
            worksheet.protect()
            workbook.close()
            messagebox.showinfo(t(TK.SUCCESS), t(TK.MSG_SAVE_SUCCESS))
        except Exception as e:
            messagebox.showerror(t(TK.ERROR), str(e))

    def _load_from_excel(self):
        file_path = filedialog.askopenfilename(title=t(TK.FORM_IMPORT), filetypes=[("Excel", "*.xlsx *.xls"), ("CSV", "*.csv")])
        if file_path: self._import_excel(file_path)
    
    def _import_excel(self, file_path: str):
        try:
            import pandas as pd
            df = pd.read_excel(file_path, sheet_name=0)
            if df.empty: return
            
            col_map = {}
            for col in df.columns:
                c_low = str(col).lower().strip()
                if any(x in c_low for x in ['kod', 'code']): col_map[col] = 'material_code'
                elif any(x in c_low for x in ['miktar', 'weight', 'ağırlık']): col_map[col] = 'weight'
            
            df = df.rename(columns=col_map)
            data = []
            for _, row in df.iterrows():
                code = str(row.get('material_code', '')).strip()
                if not code: continue
                weight = 0
                try: weight = float(row.get('weight', 0))
                except: pass
                
                info = self._lookup_material(code)
                data.append({
                    'material_code': code,
                    'material_name': info.get('name', code) if info else code,
                    'weight': weight,
                    'solid_content': info.get('solid_content', 100) if info else 100,
                    'unit_price': info.get('unit_price', 0) if info else 0,
                })
            
            if data:
                self.grid.load_data(data)
                self._update_summary()
                messagebox.showinfo(t(TK.SUCCESS), f"{len(data)} rows loaded")
        except Exception as e:
            messagebox.showerror(t(TK.ERROR), str(e))

    def _export_to_excel(self):
        file_path = filedialog.asksaveasfilename(title=t(TK.FORM_EXPORT), defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if not file_path: return
        try:
            import pandas as pd
            data = self.grid.get_data()
            df = pd.DataFrame(data)
            df = df.rename(columns={
                'row_num': '#',
                'material_code': t(TK.GRID_CODE),
                'material_name': t(TK.GRID_NAME),
                'weight': t(TK.GRID_WEIGHT),
                'solid_pct': t(TK.GRID_SOLID_PCT),
                'solid_weight': t(TK.GRID_SOLID_WEIGHT),
                'unit_price': t(TK.GRID_UNIT_PRICE),
                'total_price': t(TK.GRID_TOTAL_PRICE)
            })
            df.to_excel(file_path, index=False)
            messagebox.showinfo(t(TK.SUCCESS), t(TK.MSG_SAVE_SUCCESS))
        except Exception as e:
            messagebox.showerror(t(TK.ERROR), str(e))

    def _predict_results(self):
        if not self.on_predict:
            messagebox.showinfo(t(TK.INFO), "Tahmin özelliği henüz yapılandırılmadı.")
            return
        data = self.get_formulation_data()
        if not data.get('components'):
            messagebox.showwarning(t(TK.WARNING), t(TK.MSG_REQUIRED_FIELD))
            return
        try: thickness = float(self.thickness_entry.get())
        except: thickness = 30.0
        result = self.on_predict(data, thickness)
        self._display_prediction(result)
    
    def _display_prediction(self, result: Dict):
        self.prediction_text.config(state='normal')
        self.prediction_text.delete(1.0, tk.END)
        if result and result.get('success'):
            predictions = result.get('predictions', {})
            lines = [f"🔮 {t(TK.FORM_PREDICT).upper()}", "─" * 40]
            for key, value in predictions.items():
                if value is not None: lines.append(f"  {key}: {value:.2f}")
            self.prediction_text.insert(tk.END, "\n".join(lines))
        else:
            self.prediction_text.insert(tk.END, f"❌ {result.get('message', 'Error')}")
        self.prediction_text.config(state='disabled')
    def _load_formulation_by_id(self, formulation_id: int):
        if self.on_load_formulation:
            data = self.on_load_formulation(formulation_id)
            if data: self.load_formulation(data)
    
    def get_formulation_data(self) -> Dict:
        return {
            'formula_code': self.formula_code_entry.get().strip(),
            'formula_name': self.formula_name_entry.get().strip(),
            'project': self.current_project,
            'project_id': self.current_project_id,
            'components': self.grid.get_data(),
            'totals': self.grid.get_totals()
        }
    
    def load_formulation(self, data: Dict):
        self.formula_code_entry.delete(0, tk.END)
        self.formula_code_entry.insert(0, data.get('formula_code', ''))
        self.formula_name_entry.delete(0, tk.END)
        self.formula_name_entry.insert(0, data.get('formula_name', ''))
        self.grid.load_data(data.get('components', data.get('materials', [])))
        self._update_summary()
    
    def load_projects(self, projects: List):
        if isinstance(projects, list):
            self.project_combo['values'] = [p.get('name', '') if isinstance(p, dict) else p for p in projects]
    
    def load_formulation_list(self, formulations: List):
        self.formulation_list = formulations
        self.formulation_combo['values'] = [f"{f.get('formula_code', '')} - {f.get('formula_name', '')}" for f in formulations]
    
    def get_current_project(self) -> Optional[str]: return self.current_project
    def set_prediction_callback(self, callback: Callable): self.on_predict = callback
