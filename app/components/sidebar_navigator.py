import tkinter as tk
from tkinter import ttk, messagebox
import logging
import re
from typing import Callable, Optional, TYPE_CHECKING

from src.core.i18n import t, I18nMixin
from src.core.translation_keys import TK

if TYPE_CHECKING:
    from src.core.project_context import ProjectContext

# Constants for Treeview Items
TYPE_PROJECT = "project"
TYPE_CONCEPT = "concept"
TYPE_TRIAL = "trial"

class SidebarNavigator(ttk.Frame, I18nMixin):
    """
    Hierarchical Sidebar Navigation (Project > Concept > Variation)
    Mimics QTreeWidget behavior.
    
    Supports both:
    - Legacy callback pattern (on_selection_change)
    - ProjectContext pattern (context.project_id = ...)
    """
    def __init__(self, parent, db_manager, on_selection_change: Callable, 
                 on_project_change: Callable = None,
                 context: 'ProjectContext' = None):
        # DPI ölçeğine göre genişlik (150% ekranda yazılar büyür, piksel genişliği büyümez)
        scale = max(1.0, parent.winfo_fpixels("1i") / 96.0)
        super().__init__(parent, width=int(320 * scale))
        self.pack_propagate(False) # Fixed width
        
        self.db_manager = db_manager
        self.on_selection_change = on_selection_change
        self.on_project_change = on_project_change  # Callback for project changes
        self.context = context  # ProjectContext for unified state management
        
        self.setup_i18n()
        self._create_ui()
        self._update_texts()
        self.refresh()
        
    def _update_texts(self):
        """Update texts for i18n"""
        self.title_label.config(text=t(TK.NAV_PROJECT_EXPLORER))
        self.new_project_btn.config(text=t(TK.NAV_NEW_PROJECT))

    def _create_ui(self):
        # Header
        header = ttk.Frame(self, padding=5)
        header.pack(fill=tk.X)
        self.title_label = ttk.Label(header, font=("Segoe UI", 10, "bold"))
        self.title_label.pack(side=tk.LEFT)
        ttk.Button(header, text="🔄", width=3, command=self.refresh).pack(side=tk.RIGHT)
        
        # New Project Button
        action_frame = ttk.Frame(self, padding=(5, 0, 5, 5))
        action_frame.pack(fill=tk.X)
        
        self.new_project_btn = ttk.Button(
            action_frame, 
            command=self._open_new_project_dialog
        )
        self.new_project_btn.pack(fill=tk.X)

        # Search: project / concept / variation code / raw material in recipe
        search_frame = ttk.Frame(self, padding=(5, 0, 5, 0))
        search_frame.pack(fill=tk.X)
        ttk.Label(search_frame, text="🔍").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self._search_after = None
        self.search_var.trace_add('write', self._on_search_change)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 3))
        self.search_entry.bind('<Escape>', lambda e: self.search_var.set(''))
        ttk.Button(search_frame, text="✕", width=2,
                   command=lambda: self.search_var.set('')).pack(side=tk.RIGHT)
        self.search_info = ttk.Label(self, padding=(8, 0, 5, 0), font=("Segoe UI", 8))
        self.search_info.pack(fill=tk.X)

        # View: flat (project -> Arge No) by default; grouped by concept on demand
        view_frame = ttk.Frame(self, padding=(5, 0, 5, 0))
        view_frame.pack(fill=tk.X)
        self.group_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(view_frame, text="Konseptlere göre grupla", variable=self.group_var,
                        command=lambda: self._populate(set())).pack(side=tk.LEFT)
        ttk.Label(self, text="✅ olumlu   ❌ olumsuz   📈 ölçüm var   ○ sadece reçete",
                  padding=(8, 2, 5, 0), font=("Segoe UI", 8)).pack(fill=tk.X)

        # Treeview
        self.tree = ttk.Treeview(self, show="tree", selectmode="browse")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bindings
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Button-3>", self._on_right_click) # Right click
        
        # Tags for coloring/styling
        self.tree.tag_configure("project", font=("Segoe UI", 9, "bold"))
        self.tree.tag_configure("concept", font=("Segoe UI", 9))
        self.tree.tag_configure("trial_success", foreground="#4CAF50") # Green
        self.tree.tag_configure("trial_fail", foreground="#F44336")    # Red
        self.tree.tag_configure("trial_tested", foreground="#FFC107")  # Orange: has measurements
        self.tree.tag_configure("trial_draft", foreground="#9E9E9E")   # Grey: recipe only
    
    def _open_new_project_dialog(self):
        """Open dialog to create a new project"""
        from tkinter import simpledialog
        name = simpledialog.askstring(
            t(TK.NAV_NEW_PROJECT), 
            f"{t(TK.FORM_PROJECT)} {t(TK.FORM_NAME)}:",
            parent=self
        )
        if name and name.strip():
            try:
                project_data = {
                    "name": name.strip(),
                    "customer_name": "Genel",
                    "status": "active",
                    "description": ""
                }
                self.db_manager.create_project(project_data)
                self.refresh()
                
                # Notify main app to refresh all panels (formulation editor, etc.)
                if self.on_project_change:
                    self.on_project_change()
                
                messagebox.showinfo(t(TK.common_success if hasattr(TK, 'common_success') else TK.SUCCESS), t(TK.MSG_PROJECT_CREATED).replace('{name}', name))
            except Exception as e:
                messagebox.showerror(t(TK.common_error if hasattr(TK, 'common_error') else TK.ERROR), f"{t(TK.ERROR)}: {e}")
        
    def refresh(self):
        """Rebuilds the tree from DB"""
        # Açık dalları koru (her kayıttan sonra ağaç yeniden kurulur). Seçim bilerek geri
        # konmuyor: selection_set <<TreeviewSelect>> tetikler ve kullanıcıyı başka sekmeye atar.
        opened = set()
        stack = list(self.tree.get_children())
        while stack:
            node = stack.pop()
            if self.tree.item(node, 'open'):
                opened.add(node)
            stack.extend(self.tree.get_children(node))
        
        # Fetch Data
        try:
            self._hierarchy = self.db_manager.get_project_hierarchy()
        except Exception as e:
            logging.error(f"Failed to fetch hierarchy: {e}")
            return
        self._trial_materials = self._load_trial_materials()
        self._populate(opened)

    # ---------- search ----------
    _TR = str.maketrans("İIıŞşĞğÜüÖöÇç", "iiissgguuoocc")

    @classmethod
    def _fold(cls, text) -> str:
        return str(text or '').translate(cls._TR).casefold()

    def _load_trial_materials(self) -> dict:
        """trial_id -> folded text of all raw-material names/codes in its recipe"""
        result = {}
        try:
            with self.db_manager.get_connection() as conn:
                for trial_id, name, code in conn.execute(
                        'SELECT trial_id, component_name, component_type FROM components '
                        'WHERE trial_id IS NOT NULL'):
                    result.setdefault(trial_id, []).append(self._fold(f"{name} {code or ''}"))
        except Exception as e:
            logging.warning(f"Search index for materials failed: {e}")
        return {k: ' | '.join(v) for k, v in result.items()}

    def _on_search_change(self, *args):
        if self._search_after:
            self.after_cancel(self._search_after)
        self._search_after = self.after(250, lambda: self._populate(set()))

    def _populate(self, opened: set):
        """Render tree from cached hierarchy, filtered by the search box"""
        self.tree.delete(*self.tree.get_children())
        query = self._fold(self.search_var.get().strip()) if hasattr(self, 'search_var') else ''
        terms = query.split()
        hits = 0
        material_hits = 0

        def match(text):
            folded = self._fold(text)
            return all(term in folded for term in terms)

        if not self.group_var.get():
            hits, material_hits = self._populate_flat(terms, match)
        else:
            hits, material_hits = self._populate_grouped(terms, match)

        if terms:
            info = f"{hits} varyasyon bulundu"
            if material_hits:
                info += f" ({material_hits} hammadde eşleşmesi)"
            self.search_info.config(text=info)
        else:
            self.search_info.config(text='')
            for node in opened:
                if self.tree.exists(node):
                    self.tree.item(node, open=True)

    def _populate_flat(self, terms, match):
        """Project -> variations (Arge No), newest first; the concept (sheet) name becomes the label"""
        hits = material_hits = 0
        projects = []
        for proj in getattr(self, '_hierarchy', []):
            proj_match = bool(terms) and match(proj['name'])
            rows = []
            for concept in proj.get('concepts', []):
                conc_match = proj_match or (bool(terms) and match(concept['concept_name']))
                for trial in concept.get('trials', []):
                    if terms and not conc_match:
                        by_code = match(trial.get('trial_code', ''))
                        by_mat = (not by_code) and match(self._trial_materials.get(trial['id'], ''))
                        if not (by_code or by_mat):
                            continue
                        material_hits += by_mat
                    rows.append((trial, concept['concept_name']))
            if terms and not rows and not proj_match:
                continue
            rows.sort(key=lambda r: (r[0].get('trial_date') or '', r[0].get('trial_code') or ''), reverse=True)
            latest = rows[0][0].get('trial_date') or '' if rows else ''
            projects.append((latest, proj, rows))
        # projects with the most recent work first, undated ones last
        projects.sort(key=lambda p: (p[0], p[1]['name']), reverse=True)
        for _, proj, rows in projects:
            total = sum(len(c.get('trials', [])) for c in proj.get('concepts', []))
            self._insert_project(proj, count=len(rows) if terms else total)
            for trial, concept_name in rows:
                self._insert_trial(f"p_{proj['id']}", trial, concept_name)
                hits += 1
            if terms:
                self.tree.item(f"p_{proj['id']}", open=True)
        return hits, material_hits

    def _populate_grouped(self, terms, match):
        hits = material_hits = 0
        for proj in getattr(self, '_hierarchy', []):
            proj_match = bool(terms) and match(proj['name'])
            proj_iid = f"p_{proj['id']}"
            proj_inserted = False
            for concept in proj.get('concepts', []):
                conc_match = proj_match or (bool(terms) and match(concept['concept_name']))
                conc_iid = f"c_{concept['id']}"
                conc_inserted = False
                for trial in concept.get('trials', []):
                    if terms and not conc_match:
                        by_code = match(trial.get('trial_code', ''))
                        by_mat = (not by_code) and match(self._trial_materials.get(trial['id'], ''))
                        if not (by_code or by_mat):
                            continue
                        material_hits += by_mat
                    if not proj_inserted:
                        self._insert_project(proj)
                        proj_inserted = True
                    if not conc_inserted:
                        self._insert_concept(proj_iid, concept)
                        conc_inserted = True
                    self._insert_trial(conc_iid, trial)
                    hits += 1
                if not conc_inserted and (not terms or conc_match):
                    if not proj_inserted:
                        self._insert_project(proj)
                        proj_inserted = True
                    self._insert_concept(proj_iid, concept)
                if terms and conc_inserted:
                    self.tree.item(conc_iid, open=not conc_match or len(concept.get('trials', [])) <= 20)
            if not proj_inserted and (not terms or proj_match):
                self._insert_project(proj)
            if terms and self.tree.exists(proj_iid):
                self.tree.item(proj_iid, open=True)
        return hits, material_hits

    def _insert_project(self, proj, count=None):
        label = f"📁 {proj['name']}" + (f"  ({count})" if count else "")
        self.tree.insert("", "end", f"p_{proj['id']}", text=label,
                         tags=("project",), values=(TYPE_PROJECT, proj['id']))

    def _insert_concept(self, proj_iid, concept):
        self.tree.insert(proj_iid, "end", f"c_{concept['id']}", text=f"🧪 {concept['concept_name']}",
                         tags=("concept",), values=(TYPE_CONCEPT, concept['id']))

    # imported cards without an Arge No got placeholder codes like "Sayfa1-R2C2" / "Ç5-R2C13-2"
    _PLACEHOLDER = re.compile(r"-R\d+C\d+(-\d+)?$")

    def _trial_label(self, trial, concept_name=None) -> str:
        code = trial.get('trial_code') or 'Trial'
        date = (trial.get('trial_date') or '')[:10]
        if self._PLACEHOLDER.search(code):
            name = concept_name or code
            return f"{name} · {date}" if date else name
        if concept_name and self._fold(concept_name) not in self._fold(code):
            return f"{code} · {concept_name}"
        return code

    def _insert_trial(self, parent_iid, trial, concept_name=None):
        status = (trial.get('result') or '').lower()
        if "success" in status or "pass" in status:
            tag, icon = "trial_success", "✅"
        elif "fail" in status:
            tag, icon = "trial_fail", "❌"
        elif "tested" in status:
            tag, icon = "trial_tested", "📈"
        else:
            tag, icon = "trial_draft", "○"
        self.tree.insert(parent_iid, "end", f"t_{trial['id']}",
                         text=f"{icon} {self._trial_label(trial, concept_name)}",
                         tags=(tag,), values=(TYPE_TRIAL, trial['id']))

    def _on_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
            
        item = selection[0]
        values = self.tree.item(item, "values")
        
        if values:
            item_type, item_id = values[0], int(values[1])
            
            # Update ProjectContext if available (unified state management)
            if self.context is not None:
                if item_type == TYPE_PROJECT:
                    self.context.project_id = item_id
                elif item_type == TYPE_TRIAL:
                    self.context.formulation_id = item_id
            
            # Always call legacy callback for backward compatibility
            self.on_selection_change(item_type, item_id)
            
    def _on_right_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
            
        self.tree.selection_set(item_id)
        values = self.tree.item(item_id, "values")
        
        if not values:
            return
            
        item_type, db_id = values[0], int(values[1])
        
        menu = tk.Menu(self, tearoff=0)
        
        if item_type == TYPE_PROJECT:
            menu.add_command(label=f"➕ {t(TK.FORM_NEW_VARIATION)}", command=lambda: self._add_concept(db_id))
            menu.add_separator()
            menu.add_command(label=f"🗑️ {t(TK.common_delete if hasattr(TK, 'common_delete') else TK.DELETE)}", command=lambda: self._delete_item(item_type, db_id))
            
        elif item_type == TYPE_CONCEPT:
            menu.add_command(label=f"➕ {t(TK.FORM_NEW_VARIATION)}", command=lambda: self._add_trial(db_id))
            
        elif item_type == TYPE_TRIAL:
            menu.add_command(label=f"✏️ {t(TK.common_edit if hasattr(TK, 'common_edit') else TK.EDIT)}", command=lambda: self.on_selection_change(TYPE_TRIAL, db_id))
            menu.add_separator()
            menu.add_command(label=f"🗑️ {t(TK.common_delete if hasattr(TK, 'common_delete') else TK.DELETE)}", command=lambda: self._delete_item(item_type, db_id))
            
        menu.post(event.x_root, event.y_root)
        
    def _add_concept(self, project_id):
        from tkinter import simpledialog
        name = simpledialog.askstring(t(TK.FORM_NEW_VARIATION), f"{t(TK.NAV_OPTIMIZATION)} {t(TK.FORM_NAME)}:")
        if name:
            self.db_manager.create_parent_formulation(project_id, name)
            self.refresh()
            # Expand the project
            self.tree.item(f"p_{project_id}", open=True)
            
    def _add_trial(self, concept_id):
        # Triggering a 'New Trial' action in the main app
        # For now, we interact via the selection callback or a specific event
        # We invoke the callback with a special 'new_trial' type or handle in app
        self.on_selection_change("new_trial_request", concept_id)
        
    def _delete_item(self, item_type, item_id):
        if item_type == TYPE_PROJECT:
            if messagebox.askyesno(t(TK.common_confirm if hasattr(TK, 'common_confirm') else TK.CONFIRM), t(TK.MSG_ARE_YOU_SURE)):
                project = self.db_manager.get_project(item_id)
                if project:
                    # Yumuşak silme: proje pasife alınır, varyasyonları listelerden kalkar
                    self.db_manager.delete_project_by_name(project['name'])
                    if self.context is not None and self.context.project_id == item_id:
                        self.context.project_id = None
                    self.refresh()
                    if self.on_project_change:
                        self.on_project_change()
        elif item_type == TYPE_TRIAL:
            if messagebox.askyesno(t(TK.common_confirm if hasattr(TK, 'common_confirm') else TK.CONFIRM), t(TK.MSG_ARE_YOU_SURE)):
                self.db_manager.delete_trial(item_id)
                if self.context is not None:
                    self.context.refresh_formulations()
                self.refresh()
                if self.on_project_change:
                    self.on_project_change()

    def load_projects(self, projects=None):
        """Compatibility method for legacy ProjectPanel calls"""
        self.refresh()
