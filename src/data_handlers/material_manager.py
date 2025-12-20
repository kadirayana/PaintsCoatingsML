"""
Paint Formulation AI - Malzeme Yönetimi
========================================
Malzeme fiyatları ve maliyet hesaplama modülü
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MaterialManager:
    """
    Malzeme ve fiyat yönetimi
    
    Malzeme fiyatlarını yönetir ve formülasyon maliyetlerini hesaplar.
    """
    
    # Varsayılan malzeme kategorileri
    DEFAULT_CATEGORIES = [
        'binder',      # Bağlayıcı
        'pigment',     # Pigment
        'filler',      # Dolgu
        'thickener',   # Koyulaştırıcı
        'additive',    # Katkı
        'solvent',     # Çözücü
        'other'        # Diğer
    ]
    
    CATEGORY_NAMES_TR = {
        'binder': 'Bağlayıcı',
        'pigment': 'Pigment',
        'filler': 'Dolgu',
        'thickener': 'Koyulaştırıcı',
        'additive': 'Katkı Maddesi',
        'solvent': 'Çözücü',
        'other': 'Diğer'
    }
    
    def __init__(self, db_manager=None):
        """
        Args:
            db_manager: Veritabanı yöneticisi
        """
        self.db_manager = db_manager
        self.materials = {}  # material_id -> material_data
        self._load_materials()
    
    def _load_materials(self):
        """Veritabanından malzemeleri yükle"""
        if self.db_manager:
            try:
                materials = self.db_manager.get_all_materials()
                self.materials = {m['id']: m for m in materials}
            except Exception as e:
                logger.warning(f"Malzeme yükleme hatası: {e}")
    
    def add_material(self, data: Dict) -> int:
        """
        Yeni malzeme ekle
        
        Args:
            data: Malzeme bilgileri
                - name: Malzeme adı
                - category: Kategori
                - unit_price: Birim fiyat (TL/kg)
                - unit: Birim (kg, lt, adet)
                - supplier: Tedarikçi (opsiyonel)
                
        Returns:
            Malzeme ID
        """
        required = ['name', 'unit_price']
        for field in required:
            if field not in data:
                raise ValueError(f"Eksik alan: {field}")
        
        material = {
            'name': data['name'],
            'category': data.get('category', 'other'),
            'unit_price': float(data['unit_price']),
            'unit': data.get('unit', 'kg'),
            'supplier': data.get('supplier', ''),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        if self.db_manager:
            material_id = self.db_manager.add_material(material)
            material['id'] = material_id
            self.materials[material_id] = material
            return material_id
        else:
            # Geçici ID
            material_id = len(self.materials) + 1
            material['id'] = material_id
            self.materials[material_id] = material
            return material_id
    
    def update_material(self, material_id: int, data: Dict) -> bool:
        """Malzeme güncelle"""
        if material_id not in self.materials:
            return False
        
        self.materials[material_id].update(data)
        self.materials[material_id]['updated_at'] = datetime.now().isoformat()
        
        if self.db_manager:
            self.db_manager.update_material(material_id, data)
        
        return True
    
    def delete_material(self, material_id: int) -> bool:
        """Malzeme sil"""
        if material_id not in self.materials:
            return False
        
        del self.materials[material_id]
        
        if self.db_manager:
            self.db_manager.delete_material(material_id)
        
        return True
    
    def get_material(self, material_id: int) -> Optional[Dict]:
        """Malzeme getir"""
        return self.materials.get(material_id)
    
    def get_all_materials(self) -> List[Dict]:
        """Tüm malzemeleri getir"""
        return list(self.materials.values())
    
    def get_materials_by_category(self, category: str) -> List[Dict]:
        """Kategoriye göre malzemeleri getir"""
        return [m for m in self.materials.values() if m.get('category') == category]
    
    def calculate_formulation_cost(
        self,
        formulation: List[Dict],
        batch_size: float = 1.0
    ) -> Dict:
        """
        Formülasyon maliyetini hesapla
        
        Args:
            formulation: Formülasyon bileşenleri
                [{'material_id': 1, 'amount': 10}, ...]
            batch_size: Parti büyüklüğü (çarpan)
            
        Returns:
            Maliyet detayları
        """
        total_cost = 0
        cost_breakdown = []
        
        for component in formulation:
            material_id = component.get('material_id')
            amount = float(component.get('amount', 0)) * batch_size
            
            if material_id in self.materials:
                material = self.materials[material_id]
                unit_price = material.get('unit_price', 0)
                cost = amount * unit_price
                
                cost_breakdown.append({
                    'material': material['name'],
                    'category': material.get('category', 'other'),
                    'amount': amount,
                    'unit': material.get('unit', 'kg'),
                    'unit_price': unit_price,
                    'cost': round(cost, 2)
                })
                
                total_cost += cost
            else:
                # Material_name ile ara
                material_name = component.get('material_name', f'Bilinmeyen ({material_id})')
                amount = float(component.get('amount', 0)) * batch_size
                unit_price = float(component.get('unit_price', 0))
                cost = amount * unit_price
                
                cost_breakdown.append({
                    'material': material_name,
                    'category': 'other',
                    'amount': amount,
                    'unit': 'kg',
                    'unit_price': unit_price,
                    'cost': round(cost, 2)
                })
                
                total_cost += cost
        
        # Kategori bazlı maliyet
        category_costs = {}
        for item in cost_breakdown:
            cat = item['category']
            if cat not in category_costs:
                category_costs[cat] = 0
            category_costs[cat] += item['cost']
        
        return {
            'total_cost': round(total_cost, 2),
            'batch_size': batch_size,
            'breakdown': cost_breakdown,
            'category_costs': {k: round(v, 2) for k, v in category_costs.items()},
            'cost_per_kg': round(total_cost / batch_size, 2) if batch_size > 0 else 0
        }
    
    def get_price_dict(self) -> Dict[str, float]:
        """
        ML optimizasyonu için fiyat sözlüğü
        
        Returns:
            {material_name: unit_price}
        """
        return {m['name'].lower(): m['unit_price'] for m in self.materials.values()}
    
    def get_category_prices(self) -> Dict[str, float]:
        """
        Kategori bazlı ortalama fiyatlar
        
        Returns:
            {category: avg_price}
        """
        category_prices = {}
        category_counts = {}
        
        for material in self.materials.values():
            cat = material.get('category', 'other')
            price = material.get('unit_price', 0)
            
            if cat not in category_prices:
                category_prices[cat] = 0
                category_counts[cat] = 0
            
            category_prices[cat] += price
            category_counts[cat] += 1
        
        return {
            cat: round(total / category_counts[cat], 2)
            for cat, total in category_prices.items()
            if category_counts[cat] > 0
        }
    
    def suggest_cheaper_alternatives(
        self,
        material_id: int,
        max_results: int = 3
    ) -> List[Dict]:
        """
        Daha ucuz alternatifler öner
        
        Args:
            material_id: Malzeme ID
            max_results: Maksimum sonuç sayısı
            
        Returns:
            Alternatif malzemeler
        """
        if material_id not in self.materials:
            return []
        
        material = self.materials[material_id]
        category = material.get('category')
        current_price = material.get('unit_price', 0)
        
        # Aynı kategorideki daha ucuz malzemeler
        alternatives = [
            m for m in self.materials.values()
            if m.get('category') == category
            and m.get('unit_price', float('inf')) < current_price
            and m['id'] != material_id
        ]
        
        # Fiyata göre sırala
        alternatives.sort(key=lambda x: x.get('unit_price', 0))
        
        return alternatives[:max_results]
    
    def get_statistics(self) -> Dict:
        """Malzeme istatistikleri"""
        if not self.materials:
            return {'count': 0}
        
        prices = [m.get('unit_price', 0) for m in self.materials.values()]
        
        return {
            'count': len(self.materials),
            'categories': len(set(m.get('category') for m in self.materials.values())),
            'avg_price': round(sum(prices) / len(prices), 2),
            'min_price': min(prices),
            'max_price': max(prices),
            'total_value': round(sum(prices), 2)
        }
