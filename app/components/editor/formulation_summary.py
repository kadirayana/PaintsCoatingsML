"""
Paint Formulation AI - Formulation Summary
===========================================
Formülasyon özet bilgileri bileşeni
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class FormulationSummary(ttk.LabelFrame):
    """
    Formülasyon özet bilgileri paneli
    
    Toplam katı, toplam %, toplam maliyet, PVC, VOC gibi
    hesaplanmış değerleri gösterir.
    """
    
    def __init__(self, parent):
        super().__init__(parent, text="📊 Özet Bilgiler", padding=5)
        
        self.values = {}
        self._create_widgets()
    
    def _create_widgets(self):
        """Widget'ları oluştur"""
        # Sol taraf değerler
        left_frame = ttk.Frame(self)
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Sağ taraf değerler
        right_frame = ttk.Frame(self)
        right_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        # Sol taraf alanları
        left_fields = [
            ('total_solid', 'Toplam Katı:', 'kg'),
            ('total_percent', 'Toplam %:', '%'),
            ('total_cost', 'Toplam Maliyet:', 'TL'),
        ]
        
        for i, (key, label, unit) in enumerate(left_fields):
            ttk.Label(left_frame, text=label).grid(row=0, column=i*3, padx=2)
            value_label = ttk.Label(left_frame, text="0", font=("Helvetica", 10, "bold"))
            value_label.grid(row=0, column=i*3+1, padx=2)
            ttk.Label(left_frame, text=unit).grid(row=0, column=i*3+2, padx=(0, 10))
            self.values[key] = value_label
        
        # Sağ taraf alanları
        right_fields = [
            ('pvc', 'PVC (%):', '%'),
            ('voc', 'VOC (g/L):', 'g/L'),
            ('row_count', 'Satır Sayısı:', ''),
        ]
        
        for i, (key, label, unit) in enumerate(right_fields):
            ttk.Label(right_frame, text=label).grid(row=0, column=i*3, padx=2)
            value_label = ttk.Label(right_frame, text="0", font=("Helvetica", 10, "bold"))
            value_label.grid(row=0, column=i*3+1, padx=2)
            if unit:
                ttk.Label(right_frame, text=unit).grid(row=0, column=i*3+2, padx=(0, 10))
            self.values[key] = value_label
    
    def update(self, data: Dict):
        """
        Özet değerlerini güncelle
        
        Args:
            data: Güncellenecek değerler sözlüğü
        """
        for key, value in data.items():
            if key in self.values:
                if isinstance(value, float):
                    display_value = f"{value:.2f}"
                else:
                    display_value = str(value)
                self.values[key].config(text=display_value)
    
    def update_from_grid(self, grid_totals: Dict):
        """
        Grid toplamlarından özeti güncelle
        
        Args:
            grid_totals: ComponentGrid.calculate_totals() sonucu
        """
        total_amount = grid_totals.get('total_amount', 0)
        total_solid = grid_totals.get('total_solid', 0)
        total_price = grid_totals.get('total_price', 0)
        row_count = grid_totals.get('row_count', 0)
        
        # Yüzde hesapla
        total_percent = 100.0 if total_amount > 0 else 0.0
        
        # PVC hesapla (basit tahmin)
        pvc = 0.0
        if total_amount > 0:
            pvc = (total_solid / total_amount) * 100
        
        # VOC tahmini (varsayılan)
        voc = max(0, (total_amount - total_solid) * 1000 / max(1, total_amount))
        
        self.update({
            'total_solid': total_solid,
            'total_percent': total_percent,
            'total_cost': total_price,
            'pvc': pvc,
            'voc': voc,
            'row_count': row_count
        })
    
    def clear(self):
        """Tüm değerleri sıfırla"""
        for label in self.values.values():
            label.config(text="0")
    
    def get_summary(self) -> Dict:
        """
        Özet değerlerini dict olarak döndür
        
        Returns:
            Dict: Mevcut özet değerleri
        """
        result = {}
        for key, label in self.values.items():
            try:
                result[key] = float(label.cget('text'))
            except ValueError:
                result[key] = label.cget('text')
        return result
