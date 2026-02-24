import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, List, Optional, Any, Tuple
import logging
import re
from src.core.i18n import t, I18nMixin
from src.core.translation_keys import TK

logger = logging.getLogger(__name__)


def safe_float(value: Any, default: float = 0.0) -> Tuple[Optional[float], bool]:
    """
    Safely convert value to float.
    
    Returns:
        Tuple of (converted_value, is_valid)
        If invalid, converted_value is the default
    """
    if value is None or value == '':
        return default, True
    
    try:
        # Handle string values
        if isinstance(value, str):
            # Remove whitespace and common formatting
            cleaned = value.strip().replace(',', '.').replace(' ', '')
            if not cleaned:
                return default, True
            return float(cleaned), True
        return float(value), True
    except (ValueError, TypeError):
        return default, False


def is_numeric_string(value: str) -> bool:
    """Check if string represents a valid number."""
    if not value or not value.strip():
        return True  # Empty is allowed
    
    # Allow: digits, one decimal point, leading minus
    pattern = r'^-?\d*\.?\d*$'
    return bool(re.match(pattern, value.strip().replace(',', '.')))


class EditableCell(ttk.Entry):
    """Floating entry widget for inline cell editing"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.tree = None
        self.item_id = None
        self.column = None
        self.original_value = ""
        
        # Bindings
        self.bind('<Return>', self._on_confirm)
        self.bind('<Escape>', self._on_cancel)
        self.bind('<Tab>', self._on_tab)
        self.bind('<FocusOut>', self._on_focus_out)
    
    def show(self, tree: ttk.Treeview, item_id: str, column: str, x: int, y: int, width: int, height: int):
        """Show the edit widget at specified position"""
        self.tree = tree
        self.item_id = item_id
        self.column = column
        
        # Get current value
        values = tree.item(item_id, 'values')
        col_idx = int(column.replace('#', '')) - 1
        self.original_value = str(values[col_idx]) if col_idx < len(values) else ""
        
        # Position and show
        self.place(x=x, y=y, width=width, height=height)
        self.delete(0, tk.END)
        self.insert(0, self.original_value)
        self.select_range(0, tk.END)
        self.focus_set()
    
    def hide(self):
        """Hide the edit widget"""
        self.place_forget()
        self.tree = None
        self.item_id = None
        self.column = None
    
    def get_value(self) -> str:
        """Get current value"""
        return self.get().strip()
    
    def _on_confirm(self, event=None):
        """Confirm edit on Enter"""
        if self.tree and self.item_id:
            self.event_generate('<<CellEditConfirm>>')
        return 'break'
    
    def _on_cancel(self, event=None):
        """Cancel edit on Escape"""
        self.delete(0, tk.END)
        self.insert(0, self.original_value)
        self.hide()
        if self.tree:
            self.tree.focus_set()
        return 'break'
    
    def _on_tab(self, event=None):
        """Move to next cell on Tab"""
        self.event_generate('<<CellEditTab>>')
        return 'break'
    
    def _on_focus_out(self, event=None):
        """Confirm on focus out"""
        # Small delay to allow tab navigation
        self.after(100, self._check_focus_out)
    
    def _check_focus_out(self):
        """Check if focus truly left"""
        if not self.focus_get():
            self._on_confirm()


class MaterialAutocompleteCell(ttk.Combobox):
    """Combobox for material selection with autocomplete"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.tree = None
        self.item_id = None
        self.column = None
        self.original_value = ""
        self.all_values = []
        
        # Bindings
        self.bind('<Return>', self._on_confirm)
        self.bind('<Escape>', self._on_cancel)
        self.bind('<Tab>', self._on_tab)
        self.bind('<<ComboboxSelected>>', self._on_selected)
        self.bind('<KeyRelease>', self._on_key_release)
        self.bind('<FocusOut>', self._on_focus_out)
    
    def show(self, tree: ttk.Treeview, item_id: str, column: str, x: int, y: int, width: int, height: int, values: List[str] = None):
        """Show the combo at specified position"""
        self.tree = tree
        self.item_id = item_id
        self.column = column
        
        if values:
            self.all_values = values
            self['values'] = values
        
        # Get current value
        tree_values = tree.item(item_id, 'values')
        col_idx = int(column.replace('#', '')) - 1
        self.original_value = str(tree_values[col_idx]) if col_idx < len(tree_values) else ""
        
        # Position and show
        self.place(x=x, y=y, width=width, height=height)
        self.set(self.original_value)
        self.focus_set()
        self.icursor(tk.END)
    
    def hide(self):
        """Hide the combo"""
        self.place_forget()
        self.tree = None
        self.item_id = None
        self.column = None
    
    def get_value(self) -> str:
        return self.get().strip()
    
    def _on_confirm(self, event=None):
        if self.tree and self.item_id:
            self.event_generate('<<CellEditConfirm>>')
        return 'break'
    
    def _on_cancel(self, event=None):
        self.set(self.original_value)
        self.hide()
        if self.tree:
            self.tree.focus_set()
        return 'break'
    
    def _on_tab(self, event=None):
        self.event_generate('<<CellEditTab>>')
        return 'break'
    
    def _on_selected(self, event=None):
        self.event_generate('<<materialselected>>')
    
    def _on_key_release(self, event=None):
        """Filter dropdown on typing"""
        typed = self.get().lower()
        if not typed:
            self['values'] = self.all_values
        else:
            filtered = [v for v in self.all_values if typed in v.lower()]
            self['values'] = filtered if filtered else self.all_values
    
    def _on_focus_out(self, event=None):
        self.after(100, self._check_focus_out)
    
    def _check_focus_out(self):
        if not self.focus_get():
            self._on_confirm()


class ExcelStyleGrid(ttk.Frame, I18nMixin):
    """
    Excel-style editable grid for formulation editing.
    
    8-Column Structure:
    - row_num, material_code, material_name, weight, solid_pct, solid_weight, unit_price, total_price
    """
    
    COLUMNS = [
        ('row_num', TK.GRID_ROW, 40, False, 'text', 'readonly'),
        ('material_code', TK.GRID_CODE, 120, True, 'text', 'input'),
        ('material_name', TK.GRID_NAME, 180, 'conditional', 'text', 'readonly'),
        ('weight', TK.GRID_WEIGHT, 100, True, 'number', 'input'),
        ('solid_pct', TK.GRID_SOLID_PCT, 60, 'conditional', 'number', 'input'),
        ('solid_weight', TK.GRID_SOLID_WEIGHT, 80, False, 'number', 'readonly'),
        ('unit_price', TK.GRID_UNIT_PRICE, 70, 'conditional', 'currency', 'input'),
        ('total_price', TK.GRID_TOTAL_PRICE, 80, False, 'currency', 'readonly'),
    ]
    
    MANUAL_MARKER = '📝 '
    
    def __init__(
        self,
        parent,
        on_row_changed: Callable = None,
        on_material_lookup: Callable = None,
        on_get_materials: Callable = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.on_row_changed = on_row_changed
        self.on_material_lookup = on_material_lookup
        self.on_get_materials = on_get_materials
        
        self.row_count = 0
        self.row_data = {}  # item_id -> {source_type, solid_content, unit_price}
        
        self.setup_i18n()
        self._create_ui()
        self._create_edit_widgets()
        
        # Add initial empty rows
        for _ in range(5):
            self._add_empty_row()
    
    def _create_ui(self):
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)
        
        columns = tuple(col[0] for col in self.COLUMNS)
        self.tree = ttk.Treeview(container, columns=columns, show='headings', selectmode='browse')
        
        for key, header_key, width, editable, col_type, bg_type in self.COLUMNS:
            anchor = 'e' if col_type in ('number', 'percent', 'currency') else 'w'
            if key == 'row_num':
                anchor = 'center'
            self.tree.column(key, width=width, anchor=anchor, minwidth=width//2)
        
        y_scroll = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree.yview)
        x_scroll = ttk.Scrollbar(container, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<Double-1>', self._on_double_click)
        self.tree.bind('<Return>', self._on_enter_key)
        self.tree.bind('<Delete>', self._on_delete_key)
        
        self.tree.tag_configure('empty', foreground='gray')
        self.tree.tag_configure('edited', foreground='#1565C0')
        self.tree.tag_configure('warning', foreground='#FF5722')
        self.tree.tag_configure('error_row', background='#FFEBEE', foreground='#C62828')
        self.tree.tag_configure('db_row', foreground='#1B5E20')
        self.tree.tag_configure('manual_row', foreground='#E65100')
        
        self._update_texts()

    def _update_texts(self):
        """Update grid headers"""
        for key, header_key, width, editable, col_type, bg_type in self.COLUMNS:
            self.tree.heading(key, text=t(header_key), anchor='center')

    def _create_edit_widgets(self):
        self.edit_entry = EditableCell(self)
        self.edit_combo = MaterialAutocompleteCell(self)
        
        self.edit_entry.bind('<<CellEditConfirm>>', self._on_edit_confirm)
        self.edit_entry.bind('<<CellEditTab>>', self._on_edit_tab)
        
        self.edit_combo.bind('<<CellEditConfirm>>', self._on_edit_confirm)
        self.edit_combo.bind('<<CellEditTab>>', self._on_edit_tab)
        self.edit_combo.bind('<<materialselected>>', self._on_material_selected)

    def _on_double_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != 'cell': return
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item_id or not column: return
        
        col_idx = int(column.replace('#', '')) - 1
        if col_idx < 0 or col_idx >= len(self.COLUMNS): return
        
        col_key, header_key, col_width, editable, col_type, bg_type = self.COLUMNS[col_idx]
        
        if editable == 'conditional':
            if item_id not in self.row_data or self.row_data.get(item_id, {}).get('source_type') != 'manual':
                return
        elif not editable:
            return
        
        bbox = self.tree.bbox(item_id, column)
        if not bbox: return
        x, y, width, height = bbox
        self.edit_entry.show(self.tree, item_id, column, x, y, width, height)

    def _on_enter_key(self, event):
        selection = self.tree.selection()
        if selection:
            item_id = selection[0]
            for col_idx, (key, h, w, editable, ct, bt) in enumerate(self.COLUMNS):
                if editable:
                    self._start_editing(item_id, f'#{col_idx + 1}')
                    break

    def _on_delete_key(self, event):
        selection = self.tree.selection()
        if selection:
            self.delete_row(selection[0])

    def _on_edit_confirm(self, event=None):
        if self.edit_entry.tree: widget = self.edit_entry
        elif self.edit_combo.tree: widget = self.edit_combo
        else: return
        
        item_id = widget.item_id
        column = widget.column
        new_value = widget.get_value()
        col_idx = int(column.replace('#', '')) - 1
        col_key = self.COLUMNS[col_idx][0]
        
        values = list(self.tree.item(item_id, 'values'))
        old_value = values[col_idx] if col_idx < len(values) else ""
        
        if new_value != old_value:
            values[col_idx] = new_value
            self.tree.item(item_id, values=values, tags=('edited',))
            self._on_value_changed(item_id, col_key, new_value)
        
        widget.hide()
        self.tree.focus_set()
        self._ensure_empty_row()

    def _on_edit_tab(self, event=None):
        if self.edit_entry.tree: widget = self.edit_entry
        elif self.edit_combo.tree: widget = self.edit_combo
        else: return
        
        item_id = widget.item_id
        column = widget.column
        new_value = widget.get_value()
        col_idx = int(column.replace('#', '')) - 1
        
        values = list(self.tree.item(item_id, 'values'))
        if col_idx < len(values):
            values[col_idx] = new_value
            self.tree.item(item_id, values=values)
            self._on_value_changed(item_id, self.COLUMNS[col_idx][0], new_value)
        
        widget.hide()
        
        next_col_idx = col_idx + 1
        while next_col_idx < len(self.COLUMNS):
            if self.COLUMNS[next_col_idx][3]:
                self._start_editing(item_id, f'#{next_col_idx + 1}')
                return
            next_col_idx += 1
        
        next_item = self.tree.next(item_id)
        if next_item:
            for nci, (k, h, w, ed, ct, bt) in enumerate(self.COLUMNS):
                if ed:
                    self._start_editing(next_item, f'#{nci + 1}')
                    return
        
        new_item = self._add_empty_row()
        for nci, (k, h, w, ed, ct, bt) in enumerate(self.COLUMNS):
            if ed:
                self._start_editing(new_item, f'#{nci + 1}')
                return

    def _on_material_selected(self, event=None): pass

    def _on_value_changed(self, item_id: str, column_key: str, value: str):
        values = list(self.tree.item(item_id, 'values'))
        while len(values) < 8: values.append('')
        
        if column_key == 'material_code':
            material = None
            if self.on_material_lookup and value:
                material = self.on_material_lookup(value)
            
            if material:
                material_name = material.get('name', value)
                solid_content = material.get('solid_content', 100) or 100
                unit_price = material.get('unit_price', 0) or 0
                values[2] = material_name
                values[4] = f"{solid_content:.0f}"
                values[6] = f"{unit_price:.2f}" if unit_price else ""
                self.row_data[item_id] = {
                    'source_type': 'db',
                    'solid_content': solid_content,
                    'unit_price': unit_price,
                    'material_id': material.get('id'),
                }
                self.tree.item(item_id, values=values, tags=('db_row',))
            elif value:
                values[2] = f"{self.MANUAL_MARKER}{value}"
                values[4] = "100"
                values[6] = ""
                self.row_data[item_id] = {
                    'source_type': 'manual',
                    'solid_content': 100,
                    'unit_price': 0,
                }
                self.tree.item(item_id, values=values, tags=('manual_row',))
            else:
                for i in range(2, 8): values[i] = ''
                self.tree.item(item_id, values=values, tags=('empty',))
                self.row_data.pop(item_id, None)
            
            if values[3]: self._recalculate_row(item_id)
        
        elif column_key == 'material_name':
            row_info = self.row_data.get(item_id, {})
            if row_info.get('source_type') == 'manual':
                values[2] = f"{self.MANUAL_MARKER}{value}" if not value.startswith(self.MANUAL_MARKER) else value
                self.tree.item(item_id, values=values)
        
        elif column_key == 'solid_pct':
            row_info = self.row_data.get(item_id, {})
            if row_info.get('source_type') == 'manual':
                try:
                    solid_content = float(value) if value else 100
                    row_info['solid_content'] = solid_content
                    values[4] = f"{solid_content:.0f}"
                    self.tree.item(item_id, values=values)
                    self._recalculate_row(item_id)
                except ValueError: pass
        
        elif column_key == 'unit_price':
            row_info = self.row_data.get(item_id, {})
            if row_info.get('source_type') == 'manual':
                try:
                    unit_price = float(value) if value else 0
                    row_info['unit_price'] = unit_price
                    values[6] = f"{unit_price:.2f}" if unit_price else ""
                    self.tree.item(item_id, values=values)
                    self._recalculate_row(item_id)
                except ValueError: pass
        
        elif column_key == 'weight':
            self._recalculate_row(item_id)
        
        if self.on_row_changed:
            self.on_row_changed(item_id)

    def _start_editing(self, item_id: str, column: str):
        col_idx = int(column.replace('#', '')) - 1
        if col_idx < 0 or col_idx >= len(self.COLUMNS): return
        if not self.COLUMNS[col_idx][3]: return
        self.tree.see(item_id)
        self.tree.selection_set(item_id)
        self.update_idletasks()
        bbox = self.tree.bbox(item_id, column)
        if not bbox: return
        x, y, width, height = bbox
        self.edit_entry.show(self.tree, item_id, column, x, y, width, height)

    def _add_empty_row(self) -> str:
        self.row_count += 1
        values = [str(self.row_count), '', '', '', '', '', '', '']
        item_id = self.tree.insert('', 'end', values=values, tags=('empty',))
        return item_id

    def _ensure_empty_row(self):
        children = self.tree.get_children()
        if children:
            last_values = self.tree.item(children[-1], 'values')
            if last_values[1] or last_values[3]:
                self._add_empty_row()
        else:
            self._add_empty_row()

    def _recalculate_row(self, item_id: str):
        values = list(self.tree.item(item_id, 'values'))
        while len(values) < 8: values.append('')
        try: weight = float(values[3]) if values[3] else 0
        except ValueError: weight = 0
        row_info = self.row_data.get(item_id, {})
        try: solid_content = float(values[4]) if values[4] else row_info.get('solid_content', 100)
        except ValueError: solid_content = row_info.get('solid_content', 100)
        try: unit_price = float(values[6]) if values[6] else row_info.get('unit_price', 0)
        except ValueError: unit_price = row_info.get('unit_price', 0)
        solid_weight = weight * (solid_content / 100)
        values[5] = f"{solid_weight:.2f}" if solid_weight > 0 else ""
        total_price = weight * unit_price
        values[7] = f"{total_price:.2f}" if total_price > 0 else ""
        self.tree.item(item_id, values=values)

    def delete_row(self, item_id: str):
        self.tree.delete(item_id)
        self.row_data.pop(item_id, None)
        self._renumber_rows()
        self._ensure_empty_row()

    def _renumber_rows(self):
        for idx, item_id in enumerate(self.tree.get_children(), 1):
            values = list(self.tree.item(item_id, 'values'))
            values[0] = str(idx)
            self.tree.item(item_id, values=values)
        self.row_count = len(self.tree.get_children())

    def clear_all(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        self.row_count = 0
        self.row_data.clear()
        for _ in range(5): self._add_empty_row()

    def get_data(self) -> List[Dict]:
        data = []
        errors = []
        for item_id in self.tree.get_children():
            tags = list(self.tree.item(item_id, 'tags'))
            if 'error_row' in tags:
                tags.remove('error_row')
                self.tree.item(item_id, tags=tuple(tags))
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id, 'values')
            if not values[1] and not values[3]: continue
            row_info = self.row_data.get(item_id, {})
            row_num = values[0]
            material_name = values[2] if len(values) > 2 else ''
            if material_name.startswith(self.MANUAL_MARKER):
                material_name = material_name[len(self.MANUAL_MARKER):]
            weight, weight_valid = safe_float(values[3] if len(values) > 3 else '', 0)
            solid_pct, solid_valid = safe_float(values[4] if len(values) > 4 else '', 100)
            solid_weight, sw_valid = safe_float(values[5] if len(values) > 5 else '', 0)
            unit_price, up_valid = safe_float(values[6] if len(values) > 6 else '', 0)
            total_price, tp_valid = safe_float(values[7] if len(values) > 7 else '', 0)
            if not all([weight_valid, solid_valid, sw_valid, up_valid, tp_valid]):
                invalid_fields = []
                if not weight_valid: invalid_fields.append(t(TK.GRID_WEIGHT))
                if not solid_valid: invalid_fields.append(t(TK.GRID_SOLID_PCT))
                if not up_valid: invalid_fields.append(t(TK.GRID_UNIT_PRICE))
                errors.append(f"{t(TK.FORM_ROW_COUNT)} {row_num}: {', '.join(invalid_fields)} {t(TK.ERROR)}")
                self.tree.item(item_id, tags=('error_row',))
            row_data = {
                'row_num': row_num,
                'material_code': values[1],
                'material_name': material_name,
                'weight': weight,
                'solid_pct': solid_pct,
                'solid_weight': solid_weight,
                'unit_price': unit_price,
                'total_price': total_price,
                'source_type': row_info.get('source_type', 'manual'),
                'material_id': row_info.get('material_id'),
                'solid_content': row_info.get('solid_content', 100),
                '_valid': all([weight_valid, solid_valid, sw_valid, up_valid, tp_valid]),
            }
            data.append(row_data)
        self._last_validation_errors = errors
        return data

    def validate_and_get_data(self) -> Tuple[Optional[List[Dict]], List[str]]:
        data = self.get_data()
        errors = getattr(self, '_last_validation_errors', [])
        if errors:
            messagebox.showerror(t(TK.ERROR), "\n".join(errors[:5]) + ("\n..." if len(errors) > 5 else ""))
            return None, errors
        return data, []

    def get_totals(self) -> Dict:
        total_weight = 0
        total_solid = 0
        total_price = 0
        row_count = 0
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id, 'values')
            if not values[1] and not values[3]: continue
            row_count += 1
            try:
                weight = float(values[3]) if len(values) > 3 and values[3] else 0
                solid = float(values[5]) if len(values) > 5 and values[5] else 0
                price = float(values[7]) if len(values) > 7 and values[7] else 0
                total_weight += weight
                total_solid += solid
                total_price += price
            except ValueError: pass
        return {
            'total_quantity': total_weight,
            'total_solid': total_solid,
            'total_cost': total_price,
            'solid_percent': (total_solid / total_weight * 100) if total_weight > 0 else 0,
            'row_count': row_count
        }
