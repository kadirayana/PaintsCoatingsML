"""
Paint Formulation AI - Quick Actions Panel
===========================================
Hızlı işlemler paneli bileşeni
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, List, Tuple


class QuickActionsPanel(ttk.LabelFrame):
    """
    Hızlı işlemler paneli
    
    Tek tıkla yaygın işlemlere erişim sağlar.
    """
    
    # Varsayılan aksiyonlar: (Buton metni, Aksiyon adı, Hedef sekme indeksi)
    DEFAULT_ACTIONS: List[Tuple[str, str, Optional[int]]] = [
        ("➕ Yeni Formülasyon", "new_formulation", 1),
        ("🧪 Test Sonucu Gir", "new_test", 2),
        ("📊 Rapor Oluştur", "report", None),
        ("🤖 ML Tahmin Al", "ml_predict", 3),
        ("📁 Dosya İçe Aktar", "import", None),
    ]
    
    def __init__(self, parent, on_action: Callable = None, 
                 actions: List[Tuple[str, str, Optional[int]]] = None):
        """
        Args:
            parent: Üst widget
            on_action: Aksiyon tıklandığında çağrılacak callback(action, tab_index)
            actions: Özel aksiyon listesi (None ise varsayılan kullanılır)
        """
        super().__init__(parent, text="⚡ Hızlı İşlemler", padding=10)
        
        self.on_action = on_action
        self.actions = actions or self.DEFAULT_ACTIONS
        self.buttons = {}
        
        self._create_buttons()
    
    def _create_buttons(self):
        """Butonları oluştur"""
        for text, action, tab_index in self.actions:
            btn = ttk.Button(
                self,
                text=text,
                command=lambda a=action, t=tab_index: self._do_action(a, t)
            )
            btn.pack(fill=tk.X, pady=3)
            self.buttons[action] = btn
    
    def _do_action(self, action: str, tab_index: Optional[int] = None):
        """
        Aksiyon çalıştır
        
        Args:
            action: Aksiyon adı
            tab_index: Hedef sekme indeksi (opsiyonel)
        """
        if self.on_action:
            self.on_action(action, tab_index)
    
    def set_button_state(self, action: str, enabled: bool = True):
        """
        Buton durumunu ayarla
        
        Args:
            action: Aksiyon adı
            enabled: True ise aktif, False ise devre dışı
        """
        if action in self.buttons:
            state = 'normal' if enabled else 'disabled'
            self.buttons[action].config(state=state)
    
    def enable_all(self):
        """Tüm butonları aktif et"""
        for btn in self.buttons.values():
            btn.config(state='normal')
    
    def disable_all(self):
        """Tüm butonları devre dışı bırak"""
        for btn in self.buttons.values():
            btn.config(state='disabled')
    
    def add_action(self, text: str, action: str, tab_index: Optional[int] = None):
        """
        Dinamik olarak yeni aksiyon ekle
        
        Args:
            text: Buton metni
            action: Aksiyon adı
            tab_index: Hedef sekme indeksi
        """
        btn = ttk.Button(
            self,
            text=text,
            command=lambda: self._do_action(action, tab_index)
        )
        btn.pack(fill=tk.X, pady=3)
        self.buttons[action] = btn
        self.actions.append((text, action, tab_index))
