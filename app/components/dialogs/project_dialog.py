"""
Paint Formulation AI - Project Dialog
=======================================
Proje oluşturma/düzenleme diyaloğu
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict
from src.core.i18n import t, I18nMixin
from src.core.translation_keys import TK


class ProjectDialog(tk.Toplevel, I18nMixin):
    """
    Proje oluşturma/düzenleme diyaloğu
    
    Attributes:
        result: Dialog sonucu (dict veya None)
    """
    
    def __init__(self, parent, title: str, project_data: Dict = None):
        """
        Args:
            parent: Üst pencere
            title: Dialog başlığı
            project_data: Düzenleme için mevcut proje verisi (opsiyonel)
        """
        super().__init__(parent)
        self.title(title)
        self.result: Optional[Dict] = None
        self.project_data = project_data or {}
        
        # Pencere ayarları
        self.geometry("400x250")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Widget'ları oluştur
        self._create_widgets()
        
        # Mevcut veriyi yükle
        if project_data:
            self._load_data()
        
        # Focus ve bekle
        self.name_entry.focus_set()
        # Note: Toplevel doesn't automatically call _update_texts on setup_i18n 
        # because it doesn't inheritance from the same root usually, but here it's fine
        self._update_texts()
        self.wait_window()
    
    def _update_texts(self):
        """Update texts for i18n"""
        self.name_label.config(text=f"{t(TK.FORM_NAME)}:")
        self.desc_label.config(text=f"{t(TK.TEST_NOTES)}:") # Using notes for description
        self.cat_label.config(text=f"{t(TK.MATERIAL_CATEGORY)}:")
        self.save_btn.config(text=f"✓ {t(TK.common_save if hasattr(TK, 'common_save') else TK.SAVE)}")
        self.cancel_btn.config(text=f"✗ {t(TK.common_cancel if hasattr(TK, 'common_cancel') else TK.CANCEL)}")

    def _create_widgets(self):
        """Widget'ları oluştur"""
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Proje adı
        self.name_label = ttk.Label(main_frame)
        self.name_label.pack(anchor=tk.W, pady=(0, 5))
        self.name_entry = ttk.Entry(main_frame, width=45)
        self.name_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Açıklama
        self.desc_label = ttk.Label(main_frame)
        self.desc_label.pack(anchor=tk.W, pady=(0, 5))
        self.desc_entry = ttk.Entry(main_frame, width=45)
        self.desc_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Kategori (opsiyonel)
        self.cat_label = ttk.Label(main_frame)
        self.cat_label.pack(anchor=tk.W, pady=(0, 5))
        self.category_combo = ttk.Combobox(
            main_frame,
            values=[t(TK.common_all if hasattr(TK, 'common_all') else "Genel")],
            state="readonly",
            width=42
        )
        self.category_combo.set(t(TK.common_all if hasattr(TK, 'common_all') else "Genel"))
        self.category_combo.pack(fill=tk.X, pady=(0, 20))
        
        # Butonlar
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        
        self.save_btn = ttk.Button(
            btn_frame,
            command=self._on_ok,
            width=15
        )
        self.save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.cancel_btn = ttk.Button(
            btn_frame,
            command=self.destroy,
            width=15
        )
        self.cancel_btn.pack(side=tk.LEFT)
        
        # Enter tuşu ile kaydet
        self.bind('<Return>', lambda e: self._on_ok())
        self.bind('<Escape>', lambda e: self.destroy())
    
    def _load_data(self):
        """Mevcut veriyi yükle"""
        self.name_entry.insert(0, self.project_data.get('name', ''))
        self.desc_entry.insert(0, self.project_data.get('description', ''))
        
        category = self.project_data.get('category', 'Genel')
        if category in self.category_combo['values']:
            self.category_combo.set(category)
    
    def _on_ok(self):
        """Kaydet butonuna tıklandığında"""
        name = self.name_entry.get().strip()
        
        if not name:
            messagebox.showwarning(t(TK.common_warning if hasattr(TK, 'common_warning') else TK.WARNING), t(TK.MSG_ENTER_NAME if hasattr(TK, 'MSG_ENTER_NAME') else 'Proje adı boş olamaz!'))
            self.name_entry.focus_set()
            return
        
        if len(name) < 2:
            messagebox.showwarning(t(TK.common_warning if hasattr(TK, 'common_warning') else TK.WARNING), t(TK.MSG_NAME_MIN_LENGTH if hasattr(TK, 'MSG_NAME_MIN_LENGTH') else 'Proje adı en az 2 karakter olmalıdır!'))
            self.name_entry.focus_set()
            return
        
        self.result = {
            'name': name,
            'description': self.desc_entry.get().strip(),
            'category': self.category_combo.get()
        }
        
        # Düzenleme modunda ID'yi koru
        if self.project_data.get('id'):
            self.result['id'] = self.project_data['id']
        
        self.destroy()
