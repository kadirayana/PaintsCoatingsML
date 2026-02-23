from src.core.i18n import t, I18nMixin
from src.core.translation_keys import TK

# Constants for Treeview Items
TYPE_PROJECT = "project"
TYPE_CONCEPT = "concept"
TYPE_TRIAL = "trial"

class SidebarNavigator(ttk.Frame, I18nMixin):
    """
    Hierarchical Sidebar Navigation (Project > Concept > Variation)
    Mimics QTreeWidget behavior.
    """
    def __init__(self, parent, db_manager, on_selection_change: Callable):
        super().__init__(parent, width=250)
        self.pack_propagate(False) # Fixed width
        
        self.db_manager = db_manager
        self.on_selection_change = on_selection_change
        self.setup_i18n()
        
        self._create_ui()
        self.refresh()
        
    def _create_ui(self):
        # Header
        self.header_frame = ttk.Frame(self, padding=5)
        self.header_frame.pack(fill=tk.X)
        self.header_label = ttk.Label(self.header_frame, font=("Segoe UI", 10, "bold"))
        self.header_label.pack(side=tk.LEFT)
        ttk.Button(self.header_frame, text="🔄", width=3, command=self.refresh).pack(side=tk.RIGHT)
        
        # New Project Button
        self.action_frame = ttk.Frame(self, padding=(5, 0, 5, 5))
        self.action_frame.pack(fill=tk.X)
        
        self.new_project_btn = ttk.Button(
            self.action_frame, 
            command=self._open_new_project_dialog
        )
        self.new_project_btn.pack(fill=tk.X)
        
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
        
        self._update_texts()

    def _update_texts(self):
        """Update static UI texts"""
        self.header_label.config(text=t(TK.NAV_PROJECT_EXPLORER))
        self.new_project_btn.config(text=t(TK.NAV_NEW_PROJECT))

    def _open_new_project_dialog(self):
        """Open dialog to create a new project"""
        from tkinter import simpledialog
        name = simpledialog.askstring(
            t(TK.NAV_NEW_PROJECT), 
            t(TK.FORM_NAME),
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
                messagebox.showinfo(t(TK.SUCCESS), t(TK.MSG_SAVE_SUCCESS))
            except Exception as e:
                messagebox.showerror(t(TK.ERROR), f"{t(TK.MSG_DB_ERROR)}: {e}")
        
    def refresh(self):
        """Rebuilds the tree from DB"""
        # Save selection
        selected = self.tree.selection()
        
        # Clear
        self.tree.delete(*self.tree.get_children())
        
        # Fetch Data
        try:
            projects = self.db_manager.get_project_hierarchy()
        except Exception as e:
            logging.error(f"Failed to fetch hierarchy: {e}")
            return
            
        # Repopulate
        for proj in projects:
            proj_id = f"p_{proj['id']}"
            self.tree.insert(
                "", "end", proj_id, 
                text=f"📁 {proj['name']}", 
                tags=("project",),
                values=(TYPE_PROJECT, proj['id'])
            )
            
            # Concepts
            for concept in proj.get('concepts', []):
                conc_id = f"c_{concept['id']}"
                self.tree.insert(
                    proj_id, "end", conc_id,
                    text=f"🧪 {concept['concept_name']}",
                    tags=("concept",),
                    values=(TYPE_CONCEPT, concept['id'])
                )
                
                # Trials
                for trial in concept.get('trials', []):
                    trial_id = f"t_{trial['id']}"
                    
                    # Determine icon/color based on result
                    status = trial.get('result', '').lower()
                    icon = "📉" if "fail" in status else "📈"
                    tag = "trial_draft"
                    if "success" in status or "pass" in status:
                        tag = "trial_success"
                        icon = "✅"
                    elif "fail" in status:
                        tag = "trial_fail"
                        icon = "❌"
                        
                    self.tree.insert(
                        conc_id, "end", trial_id,
                        text=f"{icon} {trial.get('trial_code', 'Trial')}",
                        tags=(tag,),
                        values=(TYPE_TRIAL, trial['id'])
                    )
        
    def _on_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
            
        item = selection[0]
        values = self.tree.item(item, "values")
        
        if values:
            item_type, item_id = values[0], int(values[1])
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
            menu.add_command(label="➕ Yeni Konsept", command=lambda: self._add_concept(db_id))
            menu.add_separator()
            menu.add_command(label="🗑️ Projeyi Sil", command=lambda: self._delete_item(item_type, db_id))
            
        elif item_type == TYPE_CONCEPT:
            menu.add_command(label="➕ Yeni Deneme (Varyasyon)", command=lambda: self._add_trial(db_id))
            
        elif item_type == TYPE_TRIAL:
            menu.add_command(label="✏️ Düzenle", command=lambda: self.on_selection_change(TYPE_TRIAL, db_id))
            
        menu.post(event.x_root, event.y_root)
        
    def _add_concept(self, project_id):
        from tkinter import simpledialog
        name = simpledialog.askstring("Yeni Konsept", "Konsept Adı (örn: High Gloss Topcoat):")
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
            if messagebox.askyesno("Onay", "Proje ve tüm içeriği silinsin mi?"):
                 # Assuming delete by ID exists or we fetch name
                 # self.db_manager.delete_project... (Needs update in Manager)
                 pass

    def load_projects(self, projects=None):
        """Compatibility method for legacy ProjectPanel calls"""
        self.refresh()
