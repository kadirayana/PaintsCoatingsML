"""
Paint Formulation AI - Project Panel Component
===============================================
Proje yönetim paneli bileşeni
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, List, Dict

from app.components.dialogs.project_dialog import ProjectDialog
from app.theme import COLORS, ICONS, ThemedListbox


class ProjectPanel(ttk.LabelFrame):
    """
    Proje yönetim paneli
    
    Proje listesi, yeni proje oluşturma, açma ve silme işlemlerini içerir.
    """
    
    def __init__(self, parent, on_project_change: Callable = None):
        """
        Args:
            parent: Üst widget
            on_project_change: Proje değiştiğinde çağrılacak callback
        """
        super().__init__(parent, text="📁 Proje Yönetimi", padding=10)
        
        self.on_project_change = on_project_change
        self.current_project = None
        self._projects_data: List[Dict] = []
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Widget'ları oluştur"""
        # Proje listesi - themed
        self.project_listbox = ThemedListbox(self, height=8, selectmode=tk.SINGLE)
        self.project_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.project_listbox.bind('<<ListboxSelect>>', self._on_selection_change)
        self.project_listbox.bind('<Double-1>', lambda e: self.open_project())
        
        # Butonlar - with themed styling
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text=f"{ICONS['add']} Yeni", command=self.new_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=f"{ICONS['folder_open']} Aç", command=self.open_project, style='Primary.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=f"{ICONS['delete']} Sil", command=self.delete_project, style='Danger.TButton').pack(side=tk.LEFT, padx=2)
    
    def _on_selection_change(self, event=None):
        """Seçim değiştiğinde"""
        selection = self.project_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self._projects_data):
                self.current_project = self._projects_data[index]
    
    def new_project(self):
        """Yeni proje oluştur"""
        dialog = ProjectDialog(self.winfo_toplevel(), "Yeni Proje Oluştur")
        if dialog.result:
            # Listeye ekle
            self.project_listbox.insert(tk.END, dialog.result['name'])
            self._projects_data.append(dialog.result)
            
            # Callback çağır
            if self.on_project_change:
                self.on_project_change({
                    **dialog.result,
                    'action': 'create'
                })
    
    def open_project(self):
        """Seçili projeyi aç"""
        selection = self.project_listbox.curselection()
        if not selection:
            messagebox.showwarning("Uyarı", "Lütfen bir proje seçin.")
            return
        
        index = selection[0]
        project_name = self.project_listbox.get(index)
        
        # current_project'i güncelle
        if index < len(self._projects_data):
            self.current_project = self._projects_data[index]
        else:
            self.current_project = {'name': project_name}
        
        if self.on_project_change:
            self.on_project_change({
                **self.current_project,
                'action': 'open'
            })
    
    def delete_project(self):
        """Seçili projeyi sil"""
        selection = self.project_listbox.curselection()
        if not selection:
            messagebox.showwarning("Uyarı", "Lütfen bir proje seçin.")
            return
        
        index = selection[0]
        project_name = self.project_listbox.get(index)
        
        if messagebox.askyesno("Onay", f"'{project_name}' projesini silmek istediğinizden emin misiniz?"):
            # Callback ile veritabanından sil
            if self.on_project_change:
                project_data = self._projects_data[index] if index < len(self._projects_data) else {'name': project_name}
                self.on_project_change({
                    **project_data,
                    'action': 'delete'
                })
            
            # Listeden sil
            self.project_listbox.delete(index)
            if index < len(self._projects_data):
                self._projects_data.pop(index)
            
            self.current_project = None
    
    def load_projects(self, projects: List[Dict]):
        """
        Proje listesini yükle
        
        Args:
            projects: Proje sözlüklerinin listesi (her biri 'name' içermeli)
        """
        self.project_listbox.delete(0, tk.END)
        self._projects_data = projects.copy()
        
        for project in projects:
            name = project.get('name', 'İsimsiz Proje')
            self.project_listbox.insert(tk.END, name)
    
    def get_current_project(self) -> Optional[Dict]:
        """Seçili projeyi döndür"""
        return self.current_project
    
    def select_project_by_name(self, name: str) -> bool:
        """
        İsme göre proje seç
        
        Args:
            name: Proje adı
            
        Returns:
            bool: Proje bulunup seçildiyse True
        """
        for i, project in enumerate(self._projects_data):
            if project.get('name') == name:
                self.project_listbox.selection_clear(0, tk.END)
                self.project_listbox.selection_set(i)
                self.project_listbox.see(i)
                self.current_project = project
                return True
        return False
    
    def refresh(self):
        """Listeyi yenile (callback ile veri çek)"""
        if self.on_project_change:
            self.on_project_change({'action': 'refresh'})
