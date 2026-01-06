"""
Paint Formulation AI - Status Bar Component
============================================
Durum çubuğu bileşeni
"""

import tkinter as tk
from tkinter import ttk


class StatusBar(ttk.Frame):
    """
    Durum çubuğu bileşeni
    
    Sol tarafta durum mesajı, sağ tarafta bağlantı durumu gösterir.
    """
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.status_label = ttk.Label(self, text="Hazır", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.connection_label = ttk.Label(self, text="⚫ Offline", anchor=tk.E)
        self.connection_label.pack(side=tk.RIGHT, padx=5)
    
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
        if is_online:
            self.connection_label.config(text="🟢 Online", foreground="green")
        else:
            self.connection_label.config(text="🔴 Offline", foreground="red")
    
    def set_processing(self, is_processing: bool = True):
        """
        İşlem durumunu göster
        
        Args:
            is_processing: True ise işlem yapılıyor
        """
        if is_processing:
            self.set_status("⏳ İşlem yapılıyor...")
        else:
            self.set_status("Hazır")
