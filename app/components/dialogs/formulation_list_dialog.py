"""
Paint Formulation AI - Formulation List Dialog
===============================================
Formülasyon listesi popup penceresi
"""

import tkinter as tk
from tkinter import ttk, messagebox
from src.core.i18n import t
from src.core.translation_keys import TK
from typing import Callable, List, Dict, Optional


class FormulationListDialog(tk.Toplevel):
    """
    Formülasyon listesi popup penceresi
    
    Formülasyonları tablo halinde gösterir, düzenleme ve silme işlemleri sağlar.
    """
    
    def __init__(self, parent, title: str, formulations: List[Dict],
                 on_edit: Callable = None, on_delete: Callable = None):
        """
        Args:
            parent: Üst pencere
            title: Dialog başlığı
            formulations: Formülasyon listesi
            on_edit: Düzenleme callback'i (formulation_id)
            on_delete: Silme callback'i (formulation_id)
        """
        super().__init__(parent)
        self.title(title)
        self.geometry("750x550")
        self.transient(parent)
        self.grab_set()
        
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.formulations = formulations
        
        self._create_widgets()
        self._load_formulations()
    
    def _create_widgets(self):
        """Widget'ları oluştur"""
        # Başlık
        header_frame = ttk.Frame(self, padding=10)
        header_frame.pack(fill=tk.X)
        
        ttk.Label(
            header_frame,
            text=self.title(),
            font=("Helvetica", 14, "bold")
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            header_frame,
            text=f"Toplam: {len(self.formulations)} formülasyon"
        ).pack(side=tk.RIGHT)
        
        # Arama
        search_frame = ttk.Frame(self, padding=(10, 0, 10, 10))
        search_frame.pack(fill=tk.X)
        
        ttk.Label(search_frame, text="🔍 Ara:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        
        # Treeview
        tree_frame = ttk.Frame(self, padding=(10, 0, 10, 10))
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('id', 'code', 'name', 'project', 'created', 'status')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=18)
        
        # Sütun başlıkları
        self.tree.heading('id', text='ID')
        self.tree.heading('code', text='Formül Kodu')
        self.tree.heading('name', text='Formül Adı')
        self.tree.heading('project', text='Proje')
        self.tree.heading('created', text='Oluşturulma')
        self.tree.heading('status', text='Durum')
        
        # Sütun genişlikleri
        self.tree.column('id', width=40, anchor=tk.CENTER)
        self.tree.column('code', width=100)
        self.tree.column('name', width=200)
        self.tree.column('project', width=120)
        self.tree.column('created', width=100, anchor=tk.CENTER)
        self.tree.column('status', width=80, anchor=tk.CENTER)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Çift tıklama ile düzenleme
        self.tree.bind('<Double-1>', lambda e: self._edit_selected())
        
        # Butonlar
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(
            btn_frame,
            text="✏️ Düzenle",
            command=self._edit_selected
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="🗑️ Sil",
            command=self._delete_selected
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="📋 Kopyala",
            command=self._copy_selected
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="Kapat",
            command=self.destroy
        ).pack(side=tk.RIGHT, padx=5)
    
    def _load_formulations(self, filter_text: str = ''):
        """Formülasyonları tabloya yükle"""
        # Mevcut verileri temizle
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Formülasyonları ekle
        status_map = {
            'draft': 'Taslak',
            'approved': 'Onaylı',
            'tested': 'Test Edildi'
        }
        
        filter_lower = filter_text.lower()
        
        for f in self.formulations:
            # Filtre kontrolü
            if filter_text:
                name = str(f.get('name', '') or f.get('formula_name', '')).lower()
                code = str(f.get('code', '') or f.get('formula_code', '')).lower()
                if filter_lower not in name and filter_lower not in code:
                    continue
            
            status = status_map.get(
                f.get('status', 'draft'),
                f.get('status', 'Taslak')
            )
            
            created = f.get('created_at', '')
            if created and len(created) > 10:
                created = created[:10]
            
            self.tree.insert('', tk.END, values=(
                f.get('id', ''),
                f.get('code', '') or f.get('formula_code', ''),
                f.get('name', '') or f.get('formula_name', ''),
                f.get('project_name', '-'),
                created,
                status
            ))
    
    def _on_search(self, *args):
        """Arama değiştiğinde"""
        self._load_formulations(self.search_var.get())
    
    def _get_selected_id(self) -> Optional[int]:
        """Seçili formülasyon ID'sini döndür"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            return item['values'][0]
        return None
    
    def _edit_selected(self):
        """Seçili formülasyonu düzenle"""
        formulation_id = self._get_selected_id()
        if formulation_id is None:
            messagebox.showwarning("Uyarı", "Lütfen bir formülasyon seçin.")
            return
        
        if self.on_edit:
            self.on_edit(formulation_id)
            self.destroy()
    
    def _delete_selected(self):
        """Seçili formülasyonu sil"""
        formulation_id = self._get_selected_id()
        if formulation_id is None:
            messagebox.showwarning("Uyarı", "Lütfen bir formülasyon seçin.")
            return
        
        if messagebox.askyesno(t(TK.common_confirm if hasattr(TK, 'common_confirm') else TK.CONFIRM), t(TK.MSG_ARE_YOU_SURE)):
            if self.on_delete:
                self.on_delete(formulation_id)
            
            # Tablodan sil
            selection = self.tree.selection()
            if selection:
                self.tree.delete(selection[0])
    
    def _copy_selected(self):
        """Seçili formülasyonu panoya kopyala"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Uyarı", "Lütfen bir formülasyon seçin.")
            return
        
        item = self.tree.item(selection[0])
        values = item['values']
        text = f"Formül: {values[2]} ({values[1]})"
        
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Bilgi", "Formülasyon bilgisi panoya kopyalandı.")
