"""
Paint Formulation AI - Excel-Style Editable Grid
=================================================
Modern inline-editable grid widget for formulation editing.

Features:
- Double-click to edit cells
- Tab/Enter navigation
- Auto-row creation
- Real-time calculations
- Material autocomplete
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)


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
        self.event_generate('<<MaterialSelected>>')
    
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


class ExcelStyleGrid(ttk.Frame):
    """
    Excel-style editable grid for formulation editing.
    
    5-Column Structure:
    1. Hammadde Kodu (Raw Material Code) - Editable (triggers lookup)
    2. Hammadde İsmi (Material Name) - Read-only (from DB)
    3. Ağırlık (Weight) - Editable (input)
    4. Katı Ağırlık (Solid Weight) - Read-only (calculated)
    5. Fiyat (Price) - Read-only (calculated)
    """
    
    # Column definitions: (key, header, width, editable, type, bg_color)
    # bg_color: 'input' = white, 'readonly' = light gray
    COLUMNS = [
        ('row_num', '#', 40, False, 'text', 'readonly'),
        ('material_code', 'Hammadde Kodu', 120, True, 'text', 'input'),
        ('material_name', 'Hammadde İsmi', 180, False, 'text', 'readonly'),
        ('weight', 'Ağırlık (gr/kg)', 100, True, 'number', 'input'),
        ('solid_weight', 'Katı Ağırlık', 100, False, 'number', 'readonly'),
        ('price', 'Fiyat', 100, False, 'currency', 'readonly'),
    ]
    
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
        # Store hidden material data per row (solid_content, unit_price)
        self.row_data = {}  # item_id -> {'solid_content': %, 'unit_price': TL}
        
        self._create_ui()
        self._create_edit_widgets()
        
        # Add initial empty rows
        for _ in range(5):
            self._add_empty_row()
    
    def _create_ui(self):
        """Create the grid UI"""
        # Main container with scrollbars
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview
        columns = tuple(col[0] for col in self.COLUMNS)
        self.tree = ttk.Treeview(container, columns=columns, show='headings', selectmode='browse')
        
        # Configure columns
        for key, header, width, editable, col_type, bg_type in self.COLUMNS:
            self.tree.heading(key, text=header, anchor='center')
            
            anchor = 'e' if col_type in ('number', 'percent', 'currency') else 'w'
            if key == 'row_num':
                anchor = 'center'
            
            self.tree.column(key, width=width, anchor=anchor, minwidth=width//2)
        
        # Scrollbars
        y_scroll = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree.yview)
        x_scroll = ttk.Scrollbar(container, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        
        # Pack
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bindings
        self.tree.bind('<Double-1>', self._on_double_click)
        self.tree.bind('<Return>', self._on_enter_key)
        self.tree.bind('<Delete>', self._on_delete_key)
        
        # Configure tags for styling
        self.tree.tag_configure('empty', foreground='gray')
        self.tree.tag_configure('edited', foreground='#1565C0')
        self.tree.tag_configure('warning', foreground='#FF5722')  # Material not found
    
    def _create_edit_widgets(self):
        """Create floating edit widgets"""
        self.edit_entry = EditableCell(self)
        self.edit_combo = MaterialAutocompleteCell(self)
        
        # Bind edit events
        self.edit_entry.bind('<<CellEditConfirm>>', self._on_edit_confirm)
        self.edit_entry.bind('<<CellEditTab>>', self._on_edit_tab)
        
        self.edit_combo.bind('<<CellEditConfirm>>', self._on_edit_confirm)
        self.edit_combo.bind('<<CellEditTab>>', self._on_edit_tab)
        self.edit_combo.bind('<<MaterialSelected>>', self._on_material_selected)
    
    def _on_double_click(self, event):
        """Handle double-click for editing"""
        # Identify clicked cell
        region = self.tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        
        if not item_id or not column:
            return
        
        # Get column info
        col_idx = int(column.replace('#', '')) - 1
        if col_idx < 0 or col_idx >= len(self.COLUMNS):
            return
        
        col_key, col_header, col_width, editable, col_type, bg_type = self.COLUMNS[col_idx]
        
        if not editable:
            return
        
        # Get cell bbox
        bbox = self.tree.bbox(item_id, column)
        if not bbox:
            return
        
        x, y, width, height = bbox
        
        # Show appropriate edit widget
        if col_type == 'autocomplete':
            materials = []
            if self.on_get_materials:
                try:
                    mat_list = self.on_get_materials()
                    materials = [m.get('name', m.get('code', '')) for m in mat_list if m]
                except Exception as e:
                    logger.warning(f"Could not get materials: {e}")
            
            self.edit_combo.show(self.tree, item_id, column, x, y, width, height, materials)
        else:
            self.edit_entry.show(self.tree, item_id, column, x, y, width, height)
    
    def _on_enter_key(self, event):
        """Handle Enter key in treeview"""
        selection = self.tree.selection()
        if selection:
            # Start editing first editable column
            item_id = selection[0]
            for col_idx, (key, header, width, editable, col_type, bg_type) in enumerate(self.COLUMNS):
                if editable:
                    self._start_editing(item_id, f'#{col_idx + 1}')
                    break
    
    def _on_delete_key(self, event):
        """Handle Delete key"""
        selection = self.tree.selection()
        if selection:
            self.delete_row(selection[0])
    
    def _on_edit_confirm(self, event=None):
        """Handle edit confirmation"""
        # Determine which widget
        if self.edit_entry.tree:
            widget = self.edit_entry
        elif self.edit_combo.tree:
            widget = self.edit_combo
        else:
            return
        
        item_id = widget.item_id
        column = widget.column
        new_value = widget.get_value()
        
        col_idx = int(column.replace('#', '')) - 1
        col_key = self.COLUMNS[col_idx][0]
        
        # Update tree
        values = list(self.tree.item(item_id, 'values'))
        old_value = values[col_idx] if col_idx < len(values) else ""
        
        if new_value != old_value:
            values[col_idx] = new_value
            self.tree.item(item_id, values=values, tags=('edited',))
            
            # Trigger calculations
            self._on_value_changed(item_id, col_key, new_value)
        
        widget.hide()
        self.tree.focus_set()
        
        # Check if we need to add a new row
        self._ensure_empty_row()
    
    def _on_edit_tab(self, event=None):
        """Handle Tab to move to next cell"""
        # Determine which widget
        if self.edit_entry.tree:
            widget = self.edit_entry
        elif self.edit_combo.tree:
            widget = self.edit_combo
        else:
            return
        
        item_id = widget.item_id
        column = widget.column
        new_value = widget.get_value()
        
        col_idx = int(column.replace('#', '')) - 1
        
        # Save current value
        values = list(self.tree.item(item_id, 'values'))
        if col_idx < len(values):
            values[col_idx] = new_value
            self.tree.item(item_id, values=values)
            self._on_value_changed(item_id, self.COLUMNS[col_idx][0], new_value)
        
        widget.hide()
        
        # Find next editable cell
        next_col_idx = col_idx + 1
        while next_col_idx < len(self.COLUMNS):
            if self.COLUMNS[next_col_idx][3]:  # editable
                self._start_editing(item_id, f'#{next_col_idx + 1}')
                return
            next_col_idx += 1
        
        # Move to next row
        next_item = self.tree.next(item_id)
        if next_item:
            for next_col_idx, (key, header, width, editable, col_type, bg_type) in enumerate(self.COLUMNS):
                if editable:
                    self._start_editing(next_item, f'#{next_col_idx + 1}')
                    return
        
        # At end, add new row and start editing
        new_item = self._add_empty_row()
        for next_col_idx, (key, header, width, editable, col_type, bg_type) in enumerate(self.COLUMNS):
            if editable:
                self._start_editing(new_item, f'#{next_col_idx + 1}')
                return
    
    def _on_material_selected(self, event=None):
        """Handle material selection from dropdown (if used)"""
        # Not used in new design - material_code is text input
        pass
    
    def _on_value_changed(self, item_id: str, column_key: str, value: str):
        """
        Handle value change and trigger calculations.
        
        Scenario A: User types 'material_code' -> Lookup DB, fill name, store hidden data
        Scenario B: User types 'weight' -> Calculate solid_weight and price
        """
        values = list(self.tree.item(item_id, 'values'))
        
        if column_key == 'material_code':
            # Lookup material from database by code
            material = None
            if self.on_material_lookup and value:
                material = self.on_material_lookup(value)
            
            if material:
                # Material found in DB - use its data
                material_name = material.get('name', value)
                values[2] = material_name
                
                # Store hidden data for calculations
                self.row_data[item_id] = {
                    'solid_content': material.get('solid_content', 100) / 100,  # as ratio
                    'unit_price': material.get('unit_price', 0) or 0
                }
                
                self.tree.item(item_id, values=values, tags=('edited',))
            elif value:
                # Material NOT found in DB - allow manual entry with defaults
                # Use the code itself as the name, show info indicator
                values[2] = f"📝 {value}"  # Manual entry indicator
                
                # Store default values - 100% solid, 0 price (user can still see weight)
                self.row_data[item_id] = {
                    'solid_content': 1.0,  # 100% solid as default
                    'unit_price': 0  # No price info
                }
                
                self.tree.item(item_id, values=values, tags=('edited',))
            else:
                # Empty code - clear everything
                values[2] = ''
                values[4] = ''
                values[5] = ''
                self.tree.item(item_id, values=values)
                self.row_data.pop(item_id, None)
            
            # Recalculate if weight already exists
            if values[3]:  # weight column
                self._recalculate_row(item_id)
        
        elif column_key == 'weight':
            # Recalculate solid_weight and price
            self._recalculate_row(item_id)
        
        # Trigger callback
        if self.on_row_changed:
            self.on_row_changed(item_id)
    
    def _start_editing(self, item_id: str, column: str):
        """Start editing a specific cell"""
        col_idx = int(column.replace('#', '')) - 1
        if col_idx < 0 or col_idx >= len(self.COLUMNS):
            return
        
        col_key, col_header, col_width, editable, col_type, bg_type = self.COLUMNS[col_idx]
        
        if not editable:
            return
        
        # Ensure item is visible
        self.tree.see(item_id)
        self.tree.selection_set(item_id)
        
        # Get bbox after update
        self.update_idletasks()
        bbox = self.tree.bbox(item_id, column)
        
        if not bbox:
            return
        
        x, y, width, height = bbox
        
        # All editable cells use simple entry (no autocomplete in new design)
        self.edit_entry.show(self.tree, item_id, column, x, y, width, height)
    
    def _add_empty_row(self) -> str:
        """Add an empty row and return its ID"""
        self.row_count += 1
        
        # Create values tuple (6 columns)
        values = [
            str(self.row_count),  # row_num
            '',  # material_code
            '',  # material_name
            '',  # weight
            '',  # solid_weight
            '',  # price
        ]
        
        item_id = self.tree.insert('', 'end', values=values, tags=('empty',))
        return item_id
    
    def _ensure_empty_row(self):
        """Ensure there's always at least one empty row at the end"""
        children = self.tree.get_children()
        if children:
            last_values = self.tree.item(children[-1], 'values')
            # Check if last row has data (material_code or weight)
            if last_values[1] or last_values[3]:
                self._add_empty_row()
        else:
            self._add_empty_row()
    
    def _recalculate_row(self, item_id: str):
        """Recalculate solid_weight and price for a row"""
        values = list(self.tree.item(item_id, 'values'))
        
        # Get weight from column index 3
        try:
            weight = float(values[3]) if values[3] else 0
        except ValueError:
            weight = 0
        
        # Get stored hidden data
        row_info = self.row_data.get(item_id, {})
        solid_content = row_info.get('solid_content', 1.0)  # ratio 0-1
        unit_price = row_info.get('unit_price', 0)
        
        # Calculate solid_weight (column index 4)
        solid_weight = weight * solid_content
        values[4] = f"{solid_weight:.2f}" if solid_weight > 0 else ""
        
        # Calculate price (column index 5)
        price = weight * unit_price
        values[5] = f"{price:.2f}" if price > 0 else ""
        
        self.tree.item(item_id, values=values)
    
    def delete_row(self, item_id: str):
        """Delete a row"""
        self.tree.delete(item_id)
        self.row_data.pop(item_id, None)
        self._renumber_rows()
        self._ensure_empty_row()
    
    def _renumber_rows(self):
        """Renumber all rows after deletion"""
        for idx, item_id in enumerate(self.tree.get_children(), 1):
            values = list(self.tree.item(item_id, 'values'))
            values[0] = str(idx)
            self.tree.item(item_id, values=values)
        
        self.row_count = len(self.tree.get_children())
    
    def clear_all(self):
        """Clear all rows"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.row_count = 0
        self.row_data.clear()
        
        for _ in range(5):
            self._add_empty_row()
    
    def get_data(self) -> List[Dict]:
        """Get all row data as list of dicts (5-column format)"""
        data = []
        
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id, 'values')
            
            # Skip empty rows (no material_code and no weight)
            if not values[1] and not values[3]:
                continue
            
            # Get hidden data
            row_info = self.row_data.get(item_id, {})
            
            row_data = {
                'row_num': values[0],
                'material_code': values[1],
                'material_name': values[2],
                'weight': float(values[3]) if values[3] else 0,
                'solid_weight': float(values[4]) if values[4] else 0,
                'price': float(values[5]) if values[5] else 0,
                # Include hidden data for compatibility
                'solid_content': row_info.get('solid_content', 1.0) * 100,
                'unit_price': row_info.get('unit_price', 0),
            }
            
            data.append(row_data)
        
        return data
    
    def load_data(self, data: List[Dict]):
        """Load data into the grid (auto-lookup if needed)"""
        self.clear_all()
        
        # Remove initial empty rows
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.row_count = 0
        
        for row in data:
            self.row_count += 1
            
            # Support multiple input formats
            material_code = row.get('material_code', row.get('code', ''))
            material_name = row.get('material_name', row.get('material', row.get('name', '')))
            weight = row.get('weight', row.get('quantity', row.get('amount', 0)))
            solid_content = row.get('solid_content', 100) / 100  # ratio
            unit_price = row.get('unit_price', 0)
            
            # Calculate derived values
            solid_weight = weight * solid_content
            price = weight * unit_price
            
            values = (
                str(self.row_count),
                material_code,
                material_name,
                f"{weight:.2f}" if weight else "",
                f"{solid_weight:.2f}" if solid_weight > 0 else "",
                f"{price:.2f}" if price > 0 else "",
            )
            
            item_id = self.tree.insert('', 'end', values=values)
            
            # Store hidden data
            self.row_data[item_id] = {
                'solid_content': solid_content,
                'unit_price': unit_price
            }
        
        # Add empty rows
        self._ensure_empty_row()
    
    def get_totals(self) -> Dict:
        """Get summary totals"""
        total_weight = 0
        total_solid = 0
        total_price = 0
        row_count = 0
        
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id, 'values')
            
            # Skip empty rows
            if not values[1] and not values[3]:
                continue
            
            row_count += 1
            
            try:
                weight = float(values[3]) if values[3] else 0
                solid = float(values[4]) if values[4] else 0
                price = float(values[5]) if values[5] else 0
                
                total_weight += weight
                total_solid += solid
                total_price += price
            except ValueError:
                pass
        
        return {
            'total_quantity': total_weight,
            'total_solid': total_solid,
            'total_cost': total_price,
            'solid_percent': (total_solid / total_weight * 100) if total_weight > 0 else 0,
            'row_count': row_count
        }
