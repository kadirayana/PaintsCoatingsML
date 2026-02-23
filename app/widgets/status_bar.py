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
        self.setup_i18n()
        
        self._is_online = False
        self._is_processing = False
        
        self.status_label = ttk.Label(self, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.connection_label = ttk.Label(self, anchor=tk.E)
        self.connection_label.pack(side=tk.RIGHT, padx=5)
        
        self._update_texts()
    
    def _update_texts(self):
        """i18n text update"""
        if self._is_processing:
            self.status_label.config(text=t(TK.STATUS_PROCESSING))
        else:
            self.status_label.config(text=t(TK.STATUS_READY))
            
        if self._is_online:
            self.connection_label.config(text=t(TK.STATUS_ONLINE), foreground="green")
        else:
            self.connection_label.config(text=t(TK.STATUS_OFFLINE), foreground="red")

    def set_status(self, message: str):
        """Override status with custom message (temp)"""
        self.status_label.config(text=message)
    
    def set_online(self, is_online: bool):
        self._is_online = is_online
        self._update_texts()
    
    def set_processing(self, is_processing: bool = True):
        self._is_processing = is_processing
        self._update_texts()
