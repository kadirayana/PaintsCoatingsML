import tkinter as tk
from tkinter import ttk
import logging

from src.core.i18n import t, I18nMixin
from src.core.translation_keys import TK

class VariationComparisonPanel(ttk.Frame, I18nMixin):
    """
    Shows multiple variations (Trials) side-by-side for comparison.
    Rows: Metrics (Viscosity, Cost, etc.) + Ingredients
    Columns: Trial 1, Trial 2, etc.
    """
    def __init__(self, parent, db_manager):
        super().__init__(parent, padding=10)
        self.db_manager = db_manager
        self.current_concept_id = None
        
        self.setup_i18n()
        
        self.title_label = ttk.Label(self, font=("Segoe UI", 12, "bold"))
        self.title_label.pack(anchor=tk.W, pady=(0, 10))
        
        self.tree_frame = ttk.Frame(self)
        self.tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Will be created dynamically based on number of variations
        self.tree = None 
        
        # Initial empty state
        self.empty_label = ttk.Label(self.tree_frame, text=t(TK.TEST_MESSAGES_NO_TRIALS), justify=tk.CENTER)
        self.empty_label.pack(expand=True, pady=50)
        
        self._update_texts()

    def _update_texts(self):
        """Update texts for i18n"""
        self.title_label.config(text=t(TK.NAV_OPTIMIZATION)) # Use standard Comparison key
        if self.current_concept_id:
            self.load_concept(self.current_concept_id)

    def load_concept(self, concept_id: int):
        self.current_concept_id = concept_id
        
        # 1. Fetch Data
        trials = self._fetch_trials_for_concept(concept_id)
        
        if not trials:
            # Keep empty state
            return
        
        # Remove empty label if trials exist
        if hasattr(self, 'empty_label') and self.empty_label.winfo_exists():
            self.empty_label.pack_forget()

        # 2. Build Treeview Columns
        columns = ["metric"] + [f"trial_{t['id']}" for t in trials]
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")
        
        # Headers
        self.tree.heading("metric", text=t(TK.TEST_COMPARE_PARAM))
        self.tree.column("metric", width=200, anchor=tk.W)
        
        for trial in trials:
            col_id = f"trial_{trial['id']}"
            trial_label = t(TK.FORM_SAVED_FORMULAS) if trial.get('trial_code') == 'Trial' else trial.get('trial_code', 'Trial')
            header_text = f"{trial_label}\n({trial.get('result', '-')})"
            self.tree.heading(col_id, text=header_text)
            self.tree.column(col_id, width=100, anchor=tk.CENTER)
            
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # 3. Populate Rows
        # -- Physical Properties --
        metrics = [
            (t(TK.PARAM_VISCOSITY), 'viscosity'),
            (t(TK.PARAM_PH), 'ph'),
            (t(TK.PARAM_DENSITY), 'density'),
            (t(TK.TEST_OPACITY), 'opacity'),
            (t(TK.TEST_GLOSS60), 'gloss'),
            (t(TK.FORM_TOTAL_COST), 'total_cost'),
            (t(TK.DASHBOARD_STATS_SUCCESS), 'quality_score')
        ]
        
        props_header = t(TK.TEST_PHYSICAL_PROPS)
        self.tree.insert("", "end", "header_props", text=props_header, values=[props_header] + [""]*len(trials), tags=('section',))
        
        for label, key in metrics:
            values = [label]
            row_vals = []
            for t in trials:
                val = t.get(key)
                str_val = f"{val:.2f}" if isinstance(val, (int, float)) else str(val or "-")
                row_vals.append(val or 0) # Store raw for comparison
                values.append(str_val)
            
            item_id = self.tree.insert("", "end", values=values)
            self._highlight_differences(item_id, row_vals, columns)

        # -- Ingredients (Complex Mapping) --
        ing_header = t(TK.TEST_INGREDIENTS_HEADER)
        self.tree.insert("", "end", "header_ing", text=ing_header, values=[ing_header] + [""]*len(trials), tags=('section',))
        
        # Get all unique ingredients across all trials
        all_ingredients = set()
        trial_components = {} # trial_id -> {comp_name: amount}
        
        for t in trials:
            comps = self.db_manager.get_formulation_materials(t['id']) # Fetch components using existing method (supports trial_id)
            trial_components[t['id']] = {c['name']: c['amount'] for c in comps}
            for c in comps:
                all_ingredients.add(c['name'])
                
        sorted_ing = sorted(list(all_ingredients))
        
        for ing in sorted_ing:
            values = [ing]
            row_vals = []
            for t in trials:
                amt = trial_components.get(t['id'], {}).get(ing, 0)
                values.append(f"{amt:.2f}" if amt > 0 else "-")
                row_vals.append(amt)
            
            item_id = self.tree.insert("", "end", values=values)
            # Highlight if amounts differ significantly
            if max(row_vals) > 0 and max(row_vals) != min(row_vals):
                 self._highlight_differences(item_id, row_vals, columns)

        # Styling
        self.tree.tag_configure('section', background='#e1e1e1', font=('Segoe UI', 9, 'bold'))
        self.tree.tag_configure('diff', background='#fff9c4') # Light yellow
        
    def _fetch_trials_for_concept(self, concept_id):
        # Temporary direct DB access until we add specific method or pass data
        with self.db_manager.get_connection() as conn:
             cursor = conn.cursor()
             cursor.execute("SELECT * FROM trials WHERE parent_formulation_id = ? ORDER BY trial_date ASC", (concept_id,))
             return [dict(row) for row in cursor.fetchall()]

    def _highlight_differences(self, item_id, raw_values, col_ids):
        # Logic: If values differ, tag the row as 'diff' (entire row for now)
        # Note: raw_values matches the trial columns index
        
        # Filter None
        clean_vals = [v for v in raw_values if v is not None]
        if not clean_vals: return
        
        if len(set(clean_vals)) > 1:
            self.tree.item(item_id, tags=('diff',))
