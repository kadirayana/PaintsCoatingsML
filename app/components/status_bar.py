"""
Paint Formulation AI - Status Bar Component
============================================
Durum çubuğu bileşeni
"""

import tkinter as tk
from tkinter import ttk


from src.core.i18n import t, I18nMixin
from src.core.translation_keys import TK


class StatusBar(ttk.Frame, I18nMixin):
    """
    Durum çubuğu bileşeni
    
    Sol tarafta durum mesajı, sağ tarafta bağlantı durumu gösterir.
    """
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.status_label = ttk.Label(self, text="", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.connection_label = ttk.Label(self, text="", anchor=tk.E)
        self.connection_label.pack(side=tk.RIGHT, padx=5)
        
        self._is_online = False
        self._is_processing = False
        
        self.setup_i18n()
        self._update_texts()
    
    def _update_texts(self):
        """Update texts on language change"""
        self.set_online(self._is_online)
        if self._is_processing:
            self.set_processing(True)
        else:
            self.set_status(t(TK.STATUS_READY))

    def set_status(self, message: str):
        """
        Durum mesajını güncelle
        
        Args:
            message: Gösterilecek mesaj
        """
        self.status_label.config(text=message)
    
    def set_online(self, is_online: bool):
        """
        Bağlantı durumunu güncelle
        
        Args:
            is_online: True ise online, False ise offline
        """
        self._is_online = is_online
        if is_online:
            self.connection_label.config(text=t(TK.STATUS_ONLINE), foreground="green")
        else:
            self.connection_label.config(text=t(TK.STATUS_OFFLINE), foreground="red")
    
    def set_processing(self, is_processing: bool = True):
        """
        İşlem durumunu göster
        
        Args:
            is_processing: True ise işlem yapılıyor
        """
        self._is_processing = is_processing
        if is_processing:
            self.set_status("⏳ " + t(TK.STATUS_PROCESSING))
        else:
            self.set_status(t(TK.STATUS_READY))
    
    def update_status(self, message: str):
        """Alias for set_status (backward compatibility)"""
        self.set_status(message)
