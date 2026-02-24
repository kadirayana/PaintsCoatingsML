"""
Paint Formulation AI - Reçete Dönüştürücü (Recipe Transformer)
===========================================================
Reçete verilerini (hammadde listesi ve oranlar) ML modelleri için
sabit boyutlu sayısal vektörlere dönüştürür.

Kullanılan Yöntem: Domain-Specific Feature Engineering
- Basit One-Hot Encoding yerine kimyasal özelliklerin ağırlıklı ortalamaları kullanılır.
- Bu sayede yeni hammaddeler eklense bile modelin yeniden eğitilmesine gerek kalmaz.
- P/B oranı, VOC, katı madde gibi kritik boya parametreleri hesaplanır.
"""

import numpy as np
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class RecipeTransformer:
    """
    Reçete verilerini özellik vektörüne dönüştürür.
    Endüstri standardı 'Mixture Theory' prensiplerini kullanır.
    """
    
    # Çıktı özellik isimleri
    FEATURE_NAMES = [
        # Ana Gruplar (Toplam %)
        'total_binder_ratio',
        'total_pigment_ratio',
        'total_solvent_ratio',
        'total_additive_ratio',
        
        # Kritik Oranlar
        'pigment_binder_ratio',  # P/B
        'solid_content_vol',     # Hacimce katı (tahmini)
        'solid_content_weight',  # Ağırlıkça katı
        
        # Kimyasal Özellikler (Ağırlıklı Ortalamalar)
        'avg_oh_value',
        'avg_molecular_weight',
        'avg_glass_transition',  # Tg
        'avg_oil_absorption',
        'avg_particle_size',
        
        # Solvent Özellikleri
        'avg_boiling_point',
        'avg_evaporation_rate',
        
        # Maliyet
        'theoretical_cost'
    ]
    
    def __init__(self):
        self.feature_count = len(self.FEATURE_NAMES)
    
    def transform(self, recipe: List[Dict]) -> List[float]:
        """
        Bir reçete listesini özellik vektörüne dönüştürür.
        
        Args:
            recipe: hammadde listesi. Her öğe şunları içermeli:
                   - percentage (veya amount)
                   - material_category
                   - kimyasal özellikler (oh_value, density vb.)
                   
        Returns:
            List[float]: Özellik vektörü
        """
        if not recipe:
            return [0.0] * self.feature_count
            
        # Toplam miktarı bul (normalize etmek için)
        total_amount = sum(item.get('percentage', 0) for item in recipe)
        if total_amount == 0:
            total_amount = sum(item.get('amount', 0) for item in recipe)
        
        if total_amount == 0:
            return [0.0] * self.feature_count
            
        # Değişkenler
        features = {name: 0.0 for name in self.FEATURE_NAMES}
        
        # Ağırlıklı toplamlar için geçici değişkenler
        weighted_sums = {
            'oh_value': 0.0,
            'molecular_weight': 0.0,
            'glass_transition': 0.0,
            'oil_absorption': 0.0,
            'particle_size': 0.0,
            'boiling_point': 0.0,
            'evaporation_rate': 0.0
        }
        
        # Kategori toplamları için
        cat_sums = {
            'binder': 0.0,
            'pigment': 0.0,
            'solvent': 0.0,
            'additive': 0.0
        }
        
        total_solid_weight = 0.0
        
        for item in recipe:
            # Oran hesapla (0-1 arası)
            amount = item.get('percentage', 0)
            if amount == 0:
                amount = item.get('amount', 0)
            
            ratio = amount / total_amount if total_amount > 0 else 0
            
            # Kategori
            cat = item.get('material_category', 'other').lower()
            if 'binder' in cat or 'resin' in cat:
                cat_sums['binder'] += ratio
                # Binder özellikleri
                weighted_sums['oh_value'] += item.get('oh_value', 0) * ratio
                weighted_sums['molecular_weight'] += item.get('molecular_weight', 0) * ratio
                weighted_sums['glass_transition'] += item.get('glass_transition', 0) * ratio
                
            elif 'pigment' in cat or 'filler' in cat:
                cat_sums['pigment'] += ratio
                # Pigment özellikleri
                weighted_sums['oil_absorption'] += item.get('oil_absorption', 0) * ratio
                weighted_sums['particle_size'] += item.get('particle_size', 0) * ratio
                
            elif 'solvent' in cat:
                cat_sums['solvent'] += ratio
                # Solvent özellikleri
                weighted_sums['boiling_point'] += item.get('boiling_point', 0) * ratio
                weighted_sums['evaporation_rate'] += item.get('evaporation_rate', 0) * ratio
                
            elif 'additive' in cat:
                cat_sums['additive'] += ratio
            
            # Katı madde (Varsayılan: Solvent %0, Diğerleri %100 katı gibi basit yaklaşım
            # veya veritabanından solid_content gelirse onu kullan)
            item_solid = item.get('solid_content', 0)
            if item_solid is None or item_solid == 0:
                # Tahmini
                if 'solvent' in cat:
                    item_solid = 0
                else:
                    item_solid = 100
            
            total_solid_weight += item_solid * ratio
            
            # Maliyet
            features['theoretical_cost'] += item.get('unit_price', 0) * ratio
            
        # Özelliklere ata
        features['total_binder_ratio'] = cat_sums['binder']
        features['total_pigment_ratio'] = cat_sums['pigment']
        features['total_solvent_ratio'] = cat_sums['solvent']
        features['total_additive_ratio'] = cat_sums['additive']
        
        features['solid_content_weight'] = total_solid_weight
        
        # P/B Oranı
        if cat_sums['binder'] > 0:
            features['pigment_binder_ratio'] = cat_sums['pigment'] / cat_sums['binder']
        else:
            features['pigment_binder_ratio'] = 0
            
        # Kimyasal Özellikler (Normalize edilmiş zaten, çünkü ratio toplamı 1 olmayabilir ama 
        # burada kategori bazlı ağırlıklandırma yapmak daha doğru olurdu. 
        # Şimdilik basitçe tüm reçete üzerindeki ağırlık.)
        # Düzeltme: OH değeri sadece binder'lar üzerinden ortalama alınmalı mı? Evet.
        
        # Binder Normalize
        binder_ratio = cat_sums['binder']
        if binder_ratio > 0:
            features['avg_oh_value'] = weighted_sums['oh_value'] / binder_ratio
            features['avg_molecular_weight'] = weighted_sums['molecular_weight'] / binder_ratio
            features['avg_glass_transition'] = weighted_sums['glass_transition'] / binder_ratio
            
        # Pigment Normalize
        pigment_ratio = cat_sums['pigment']
        if pigment_ratio > 0:
            features['avg_oil_absorption'] = weighted_sums['oil_absorption'] / pigment_ratio
            features['avg_particle_size'] = weighted_sums['particle_size'] / pigment_ratio
            
        # Solvent Normalize
        solvent_ratio = cat_sums['solvent']
        if solvent_ratio > 0:
            features['avg_boiling_point'] = weighted_sums['boiling_point'] / solvent_ratio
            features['avg_evaporation_rate'] = weighted_sums['evaporation_rate'] / solvent_ratio
            
        # Liste olarak döndür (FEATURE_NAMES sırasıyla)
        return [features[name] for name in self.FEATURE_NAMES]
    
    def get_feature_names(self) -> List[str]:
        """Özellik isimlerini döndür"""
        return self.FEATURE_NAMES
