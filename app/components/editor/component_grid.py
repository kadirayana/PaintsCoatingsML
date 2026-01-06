"""
Paint Formulation AI - Component Grid
======================================
Formülasyon bileşenlerini gösteren Treeview tabanlı grid
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ComponentGrid(ttk.Frame):
    """
    Formülasyon bileşenleri grid'i
    
    Excel benzeri görünüm sağlar. Hammadde kodu, adı, miktar, 
    katı miktarı, yüzde ve fiyat bilgilerini içerir.
    """
    
    # Sütun tanımları: (id, başlık, genişlik, anchor)
    COLUMNS = [
        ('code', 'Hammadde Kodu', 120, 'w'),
        ('name', 'Hammadde Adı', 200, 'w'),
        ('amount', 'Miktar (kg)', 90, 'e'),
        ('solid_content', 'Katı %', 70, 'e'),
        ('solid_amount', 'Katı (kg)', 90, 'e'),
        ('percentage', '%', 60, 'e'),
        ('unit_price', 'Birim Fiyat', 90, 'e'),
        ('total_price', 'Toplam Fiyat', 100, 'e'),
    ]
    
    def __init__(self, parent, on_selection_change: Callable = None,
                 on_double_click: Callable = None):
        """
        Args:
            parent: Üst widget
            on_selection_change: Seçim değiştiğinde callback
            on_double_click: Çift tıklamada callback
        """
        super().__init__(parent)
        
        self.on_selection_change = on_selection_change
        self.on_double_click = on_double_click
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Widget'ları oluştur"""
        # Treeview
        columns = [col[0] for col in self.COLUMNS]
        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show='headings',
            height=15
        )
        
        # Sütun başlıkları ve genişlikleri
        for col_id, heading, width, anchor in self.COLUMNS:
            self.tree.heading(col_id, text=heading)
            self.tree.column(col_id, width=width, anchor=anchor)
        
        # Scrollbar'lar
        v_scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Layout
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        
        # Event bindings
        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        self.tree.bind('<Double-1>', self._on_dbl_click)
    
    def _on_select(self, event=None):
        """Seçim değiştiğinde"""
        if self.on_selection_change:
            data = self.get_selected_data()
            self.on_selection_change(data)
    
    def _on_dbl_click(self, event=None):
        """Çift tıklamada"""
        if self.on_double_click:
            data = self.get_selected_data()
            if data:
                self.on_double_click(data)
    
    # =========================================================================
    # CRUD Operations
    # =========================================================================
    
    def add_row(self, data: Dict) -> str:
        """
        Yeni satır ekle
        
        Args:
            data: Satır verileri
            
        Returns:
            str: Eklenen satırın item ID'si
        """
        values = self._dict_to_values(data)
        item_id = self.tree.insert('', tk.END, values=values)
        return item_id
    
    def update_row(self, item_id: str, data: Dict):
        """
        Mevcut satırı güncelle
        
        Args:
            item_id: Güncellenecek satır ID'si
            data: Yeni veriler
        """
        values = self._dict_to_values(data)
        self.tree.item(item_id, values=values)
    
    def delete_row(self, item_id: str = None):
        """
        Satırı sil
        
        Args:
            item_id: Silinecek satır ID'si (None ise seçili satır)
        """
        if item_id is None:
            selection = self.tree.selection()
            if selection:
                item_id = selection[0]
        
        if item_id:
            self.tree.delete(item_id)
    
    def clear_all(self):
        """Tüm satırları temizle"""
        for item in self.tree.get_children():
            self.tree.delete(item)
    
    def get_all_data(self) -> List[Dict]:
        """
        Tüm satır verilerini döndür
        
        Returns:
            List[Dict]: Tüm satırların verileri
        """
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            data.append(self._values_to_dict(values))
        return data
    
    def get_selected_id(self) -> Optional[str]:
        """Seçili satır ID'sini döndür"""
        selection = self.tree.selection()
        return selection[0] if selection else None
    
    def get_selected_data(self) -> Optional[Dict]:
        """Seçili satır verilerini döndür"""
        item_id = self.get_selected_id()
        if item_id:
            values = self.tree.item(item_id)['values']
            return self._values_to_dict(values)
        return None
    
    def get_row_count(self) -> int:
        """Satır sayısını döndür"""
        return len(self.tree.get_children())
    
    # =========================================================================
    # Calculations
    # =========================================================================
    
    def calculate_totals(self) -> Dict:
        """
        Toplam değerleri hesapla
        
        Returns:
            Dict: Toplam değerler
        """
        total_amount = 0.0
        total_solid = 0.0
        total_price = 0.0
        
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            try:
                total_amount += float(values[2] or 0)  # amount
                total_solid += float(values[4] or 0)   # solid_amount
                total_price += float(values[7] or 0)   # total_price
            except (ValueError, IndexError):
                pass
        
        return {
            'total_amount': total_amount,
            'total_solid': total_solid,
            'total_price': total_price,
            'row_count': self.get_row_count()
        }
    
    def recalculate_percentages(self):
        """Tüm satırların yüzdelerini yeniden hesapla"""
        totals = self.calculate_totals()
        total_amount = totals['total_amount']
        
        if total_amount <= 0:
            return
        
        for item in self.tree.get_children():
            values = list(self.tree.item(item)['values'])
            try:
                amount = float(values[2] or 0)
                percentage = (amount / total_amount) * 100
                values[5] = f"{percentage:.2f}"
                self.tree.item(item, values=values)
            except (ValueError, IndexError):
                pass
    
    # =========================================================================
    # Helpers
    # =========================================================================
    
    def _dict_to_values(self, data: Dict) -> Tuple:
        """Dict'i Treeview values tuple'ına çevir"""
        return (
            data.get('code', ''),
            data.get('name', ''),
            data.get('amount', ''),
            data.get('solid_content', ''),
            data.get('solid_amount', ''),
            data.get('percentage', ''),
            data.get('unit_price', ''),
            data.get('total_price', '')
        )
    
    def _values_to_dict(self, values: Tuple) -> Dict:
        """Treeview values tuple'ını Dict'e çevir"""
        keys = [col[0] for col in self.COLUMNS]
        return dict(zip(keys, values))
    
    def select_row(self, item_id: str):
        """Belirtilen satırı seç"""
        self.tree.selection_set(item_id)
        self.tree.focus(item_id)
        self.tree.see(item_id)
    
    def load_data(self, data_list: List[Dict]):
        """
        Veri listesini yükle
        
        Args:
            data_list: Satır verileri listesi
        """
        self.clear_all()
        for data in data_list:
            self.add_row(data)
        self.recalculate_percentages()
