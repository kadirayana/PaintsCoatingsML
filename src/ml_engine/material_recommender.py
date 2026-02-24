"""
Paint Formulation AI - Akıllı hammadde Öneri Sistemi
====================================================
Kimya mühendisi gibi düşünen öneri motoru

Özellikler:
- Alternatif hammadde önerisi
- Maliyet-performans trade-off analizi
- Kimyasal uyumluluk kontrolü
- Formülasyon iyileştirme önerileri
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MaterialRecommendation:
    """hammadde önerisi veri sınıfı"""
    current_material: str
    recommended_material: str
    reason: str
    confidence: float
    trade_offs: Dict[str, float]
    chemistry_notes: str
    cost_change_percent: float


@dataclass
class FormulationSuggestion:
    """Formülasyon iyileştirme önerisi"""
    suggestion_type: str  # 'cost_reduction', 'performance_boost', 'balanced'
    title: str
    description: str
    expected_impact: Dict[str, float]
    implementation_steps: List[str]
    confidence: float


class MaterialRecommender:
    """
    Akıllı hammadde Öneri Sistemi
    
    Kimya mühendisliği bilgisi ile:
    - hammadde-performans ilişkilerini öğrenir
    - Alternatif hammaddeler önerir
    - Maliyet optimizasyonu yapar
    - Kimyasal uyumluluk kontrol eder
    """
    
    def __init__(self, knowledge_path: str = 'data_storage/chemical_knowledge.json',
                 models_dir: str = 'assets/models'):
        """
        Args:
            knowledge_path: Kimyasal bilgi veritabanı yolu
            models_dir: ML model dizini
        """
        self.knowledge_path = knowledge_path
        self.models_dir = models_dir
        
        # Kimyasal bilgi veritabanı
        self.chemical_knowledge = self._load_chemical_knowledge()
        
        # Öğrenilmiş hammadde pattern'leri
        self.material_patterns: Dict = {}
        
        # Formülasyon geçmişi (benzerlik araması için)
        self.formulation_history: List[Dict] = []
    
    def _load_chemical_knowledge(self) -> Dict:
        """Kimyasal bilgi veritabanını yükle"""
        if os.path.exists(self.knowledge_path):
            try:
                with open(self.knowledge_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Kimyasal bilgi yüklenemedi: {e}")
        
        # Varsayılan bilgi tabanı
        return self._get_default_knowledge()
    
    def _get_default_knowledge(self) -> Dict:
        """Varsayılan kimyasal bilgi tabanı"""
        return {
            "material_categories": {
                "binder": {
                    "epoxy": {
                        "name_tr": "Epoksi Reçine",
                        "properties": {
                            "chemical_resistance": 9,
                            "flexibility": 3,
                            "uv_resistance": 2,
                            "adhesion": 9,
                            "hardness": 8,
                            "cost_level": 7
                        },
                        "compatible_with": ["polyamide", "amine", "polyester"],
                        "incompatible_with": ["silicone", "wax"],
                        "typical_usage": ["zemin boyaları", "deniz boyaları", "endüstriyel kaplamalar"],
                        "substitutes": ["polyurethane", "vinyl_ester"]
                    },
                    "polyurethane": {
                        "name_tr": "Poliüretan Reçine",
                        "properties": {
                            "chemical_resistance": 7,
                            "flexibility": 9,
                            "uv_resistance": 7,
                            "adhesion": 8,
                            "hardness": 7,
                            "abrasion_resistance": 9,
                            "cost_level": 8
                        },
                        "compatible_with": ["isocyanate", "polyol", "acrylic"],
                        "incompatible_with": ["water_excess", "amine_excess"],
                        "typical_usage": ["otomotiv boyaları", "mobilya vernikleri", "spor sahaları"],
                        "substitutes": ["epoxy", "acrylic"]
                    },
                    "alkyd": {
                        "name_tr": "Alkid Reçine",
                        "properties": {
                            "chemical_resistance": 5,
                            "flexibility": 6,
                            "uv_resistance": 5,
                            "adhesion": 7,
                            "hardness": 6,
                            "cost_level": 4
                        },
                        "compatible_with": ["drier", "solvent"],
                        "typical_usage": ["ev boyaları", "metal astarları", "dekoratif boyalar"],
                        "substitutes": ["acrylic", "polyester"]
                    },
                    "acrylic": {
                        "name_tr": "Akrilik Reçine",
                        "properties": {
                            "chemical_resistance": 6,
                            "flexibility": 7,
                            "uv_resistance": 9,
                            "adhesion": 7,
                            "hardness": 6,
                            "cost_level": 5
                        },
                        "compatible_with": ["water", "coalescent", "surfactant"],
                        "typical_usage": ["dış cephe boyaları", "su bazlı boyalar", "mimari kaplamalar"],
                        "substitutes": ["styrene_acrylic", "vinyl_acrylic"]
                    }
                },
                "pigment": {
                    "titanium_dioxide": {
                        "name_tr": "Titanyum Dioksit",
                        "properties": {
                            "opacity": 10,
                            "uv_absorption": 8,
                            "cost_level": 8
                        },
                        "substitutes": ["zinc_oxide", "lithopone"],
                        "substitution_notes": "ZnO benzer örtücülük, daha düşük maliyet ama UV koruma azalır"
                    },
                    "iron_oxide": {
                        "name_tr": "Demir Oksit",
                        "properties": {
                            "opacity": 7,
                            "weather_resistance": 9,
                            "cost_level": 4
                        },
                        "substitutes": ["synthetic_iron_oxide"],
                        "typical_usage": ["astar boyaları", "pas önleyiciler"]
                    }
                },
                "filler": {
                    "calcium_carbite": {
                        "name_tr": "Kalsiyum Karbonat",
                        "properties": {
                            "cost_level": 2,
                            "grind_ease": 8,
                            "film_hardness": 5
                        },
                        "substitutes": ["talc", "barium_sulfate"],
                        "notes": "En ekonomik dolgu maddesi"
                    },
                    "talc": {
                        "name_tr": "Talk",
                        "properties": {
                            "cost_level": 3,
                            "barrier_effect": 8,
                            "film_hardness": 6
                        },
                        "substitutes": ["ite", "calcium_carbonate"],
                        "notes": "Nem bariyeri olarak etkili"
                    }
                }
            },
            "formulation_rules": {
                "pvc_cpvc": {
                    "rule": "PVC değeri CPVC'nin altında olmalı",
                    "explanation": "PVC > CPVC olduğunda film pürüzlü ve porous olur",
                    "typical_cpvc_ranges": {
                        "gloss_paint": "30-40%",
                        "semi_gloss": "40-50%",
                        "flat_paint": "50-70%"
                    }
                },
                "voc_limits": {
                    "interior_flat": 50,
                    "interior_non_flat": 150,
                    "exterior_flat": 100,
                    "exterior_non_flat": 200,
                    "industrial": 340,
                    "unit": "g/L"
                },
                "solid_content": {
                    "water_based": "35-55%",
                    "solvent_based": "40-70%",
                    "high_solid": "70-90%"
                }
            },
            "compatibility_matrix": {
                "epoxy_amine": {"compatible": True, "notes": "Standart sertleştirme sistemi"},
                "epoxy_water": {"compatible": False, "notes": "Su bazlı için özel emülsiyon gerekli"},
                "polyurethane_isocyanate": {"compatible": True, "notes": "2K sistem"},
                "acrylic_water": {"compatible": True, "notes": "Su bazlı formülasyonlar için ideal"}
            }
        }
    
    
    def suggest_materials(
        self,
        target_properties: Dict,
        constraints: Dict = None,
        top_n: int = 5
    ) -> List[Dict]:
        """
        Hedef özelliklere uygun hammaddeleri öner (Kısıtlara uygun olarak)
        
        Args:
            target_properties: Hedeflenen özellikler (örn: {'gloss': 'high', 'cost_level': 'low'})
            constraints: Proje kısıtları (max_cost, prohibited_materials vb.)
            top_n: Öneri sayısı
            
        Returns:
            Önerilen hammaddeler listesi
        """
        suggestions = []
        constraints = constraints or {}
        
        max_cost = constraints.get('max_cost')
        prohibited = [p.lower() for p in constraints.get('prohibited_materials', [])]
        
        # Tüm kategorileri tara
        for cat_name, items in self.chemical_knowledge.get('material_categories', {}).items():
            for mat_key, data in items.items():
                
                # 1. Yasaklı hammadde kontrolü
                if mat_key.lower() in prohibited or data.get('name_tr', '').lower() in prohibited:
                    continue
                    
                props = data.get('properties', {})
                
                # 2. Maliyet kontrolü (Basit seviye kontrolü: 1-10 arası)
                # Not: Gerçek fiyat kontrolü DB'den yapılmalı, burası bilgi tabanı seviyesi
                cost_level = props.get('cost_level', 5)
                if max_cost and max_cost < 50 and cost_level > 7: # Basit heuristic
                    continue

                # 3. Uygunluk skoru
                score = 0
                match_count = 0
                
                # Parlaklık hedefi
                if 'gloss' in target_properties:
                    target = target_properties['gloss']
                    # Pigment/Filler etkisi
                    if 'opacity' in props and target == 'high':
                        # Düşük yağ emilimi genelde parlaklık için iyidir (burada basitleştirilmiş)
                        score += 1
                        
                # Maliyet hedefi
                if 'total_cost' in target_properties:
                     if cost_level <= 3: score += 2
                     elif cost_level <= 5: score += 1
                     
                suggestions.append({
                    'material': mat_key,
                    'name': data.get('name_tr', mat_key),
                    'category': cat_name,
                    'score': score,
                    'properties': props
                })
        
        # Skora göre sırala
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        return suggestions[:top_n]

    def recommend_alternatives(
        self,
        current_material: str,
        current_category: str,
        target_properties: Dict = None,
        constraints: Dict = None
    ) -> List[MaterialRecommendation]:
        """
        Alternatif hammadde öner
        
        Args:
            current_material: Mevcut hammadde kodu/adı
            current_category: hammadde kategorisi (binder, pigment, filler)
            target_properties: Hedeflenen özellikler
            constraints: Kısıtlar (maliyet, tedarik, vb.)
            
        Returns:
            Öneri listesi
        """
        recommendations = []
        
        # Kategori bilgisini al
        category_data = self.chemical_knowledge.get('material_categories', {}).get(current_category, {})
        
        # Mevcut hammadde bilgisini bul
        current_data = None
        current_key = None
        for key, data in category_data.items():
            if key == current_material or data.get('name_tr', '').lower() == current_material.lower():
                current_data = data
                current_key = key
                break
        
        if not current_data:
            logger.warning(f"hammadde bulunamadı: {current_material}")
            return recommendations
        
        # Alternatifleri değerlendir
        substitutes = current_data.get('substitutes', [])
        current_props = current_data.get('properties', {})
        
        for sub_key in substitutes:
            sub_data = category_data.get(sub_key)
            if not sub_data:
                continue
            
            sub_props = sub_data.get('properties', {})
            
            # Trade-off analizi
            trade_offs = {}
            for prop, current_val in current_props.items():
                if prop in sub_props:
                    diff = sub_props[prop] - current_val
                    if abs(diff) > 0.5:  # Önemli fark
                        trade_offs[prop] = round(diff / max(current_val, 1) * 100, 1)
            
            # Maliyet değişimi
            current_cost = current_props.get('cost_level', 5)
            sub_cost = sub_props.get('cost_level', 5)
            cost_change = round((sub_cost - current_cost) / current_cost * 100, 1)
            
            # Güven skoru hesapla
            confidence = self._calculate_substitution_confidence(
                current_props, sub_props, target_properties
            )
            
            # Kimya notu oluştur
            chemistry_note = self._generate_chemistry_note(
                current_key, sub_key, current_data, sub_data, trade_offs
            )
            
            # Öneri oluştur
            recommendation = MaterialRecommendation(
                current_material=current_data.get('name_tr', current_material),
                recommended_material=sub_data.get('name_tr', sub_key),
                reason=self._generate_reason(trade_offs, cost_change, target_properties),
                confidence=confidence,
                trade_offs=trade_offs,
                chemistry_notes=chemistry_note,
                cost_change_percent=cost_change
            )
            
            recommendations.append(recommendation)
        
        # Güvene göre sırala
        recommendations.sort(key=lambda x: x.confidence, reverse=True)
        
        return recommendations
    
    def _calculate_substitution_confidence(
        self,
        current_props: Dict,
        substitute_props: Dict,
        target_props: Dict = None
    ) -> float:
        """İkame güven skorunu hesapla"""
        # Temel benzerlik
        common_props = set(current_props.keys()) & set(substitute_props.keys())
        if not common_props:
            return 0.5
        
        similarity = 0
        for prop in common_props:
            curr_val = current_props[prop]
            sub_val = substitute_props[prop]
            # Normalize fark
            diff = abs(curr_val - sub_val) / max(curr_val, sub_val, 1)
            similarity += (1 - diff)
        
        base_confidence = similarity / len(common_props)
        
        # Hedef özelliklere uygunluk bonusu
        if target_props:
            target_bonus = 0
            for prop, target_val in target_props.items():
                if prop in substitute_props:
                    sub_val = substitute_props[prop]
                    if sub_val >= target_val:
                        target_bonus += 0.1
            base_confidence += min(target_bonus, 0.2)
        
        return min(round(base_confidence, 2), 1.0)
    
    def _generate_reason(
        self,
        trade_offs: Dict,
        cost_change: float,
        target_props: Dict = None
    ) -> str:
        """Öneri nedeni oluştur"""
        reasons = []
        
        # Maliyet
        if cost_change < -10:
            reasons.append(f"%{abs(cost_change):.0f} daha düşük maliyet")
        elif cost_change > 10:
            reasons.append(f"%{cost_change:.0f} daha yüksek maliyet ancak performans artışı")
        
        # Performans artışları
        improvements = [k for k, v in trade_offs.items() if v > 10 and k != 'cost_level']
        if improvements:
            props_tr = {
                'flexibility': 'esneklik',
                'chemical_resistance': 'kimyasal dayanım',
                'uv_resistance': 'UV direnci',
                'adhesion': 'yapışma',
                'hardness': 'sertlik',
                'abrasion_resistance': 'aşınma direnci'
            }
            improved = [props_tr.get(p, p) for p in improvements[:2]]
            reasons.append(f"Artan: {', '.join(improved)}")
        
        # Performans düşüşleri (uyarı)
        decreases = [k for k, v in trade_offs.items() if v < -10 and k != 'cost_level']
        if decreases:
            props_tr = {
                'flexibility': 'esneklik',
                'chemical_resistance': 'kimyasal dayanım',
                'uv_resistance': 'UV direnci'
            }
            decreased = [props_tr.get(p, p) for p in decreases[:1]]
            reasons.append(f"Dikkat: {', '.join(decreased)} azalabilir")
        
        return '; '.join(reasons) if reasons else 'Benzer performans profili'
    
    def _generate_chemistry_note(
        self,
        current_key: str,
        substitute_key: str,
        current_data: Dict,
        substitute_data: Dict,
        trade_offs: Dict
    ) -> str:
        """Kimya mühendisliği notu oluştur"""
        notes = []
        
        # Uyumluluk kontrolü
        current_compat = set(current_data.get('compatible_with', []))
        sub_compat = set(substitute_data.get('compatible_with', []))
        
        # Ortak uyumluluk
        common = current_compat & sub_compat
        if common:
            notes.append(f"Her iki hammadde de {', '.join(list(common)[:2])} ile uyumlu")
        
        # Yeni gereksinimler
        new_reqs = sub_compat - current_compat
        if new_reqs:
            notes.append(f"Dikkat: {substitute_data.get('name_tr', substitute_key)} için {', '.join(list(new_reqs)[:1])} gerekebilir")
        
        # Tipik kullanım
        typical = substitute_data.get('typical_usage', [])
        if typical:
            notes.append(f"Tipik kullanım: {', '.join(typical[:2])}")
        
        # Ek notlar
        if 'substitution_notes' in substitute_data:
            notes.append(substitute_data['substitution_notes'])
        
        return '. '.join(notes) if notes else 'Ek bilgi mevcut değil'
    
    def suggest_formulation_improvements(
        self,
        formulation: Dict,
        improvement_type: str = 'balanced'
    ) -> List[FormulationSuggestion]:
        """
        Formülasyon iyileştirme önerileri
        
        Args:
            formulation: Mevcut formülasyon verisi
            improvement_type: 'cost', 'performance', 'balanced'
            
        Returns:
            İyileştirme önerileri listesi
        """
        suggestions = []
        
        # PVC kontrolü
        pvc = formulation.get('pvc', 0)
        if pvc > 60:
            suggestions.append(FormulationSuggestion(
                suggestion_type='performance',
                title='PVC Oranı Yüksek',
                description=f'PVC oranınız %{pvc:.1f} ile yüksek. Film kalitesi etkilenebilir.',
                expected_impact={'gloss': -15, 'durability': -10},
                implementation_steps=[
                    'Dolgu oranını %5-10 azaltın',
                    'Bağlayıcı oranını artırın',
                    'Alternatif olarak daha yüksek yağ emme kapasiteli dolgu kullanın'
                ],
                confidence=0.85
            ))
        
        # VOC kontrolü
        voc = formulation.get('voc', 0)
        voc_limit = self.chemical_knowledge.get('formulation_rules', {}).get('voc_limits', {}).get('interior_non_flat', 150)
        if voc > voc_limit:
            suggestions.append(FormulationSuggestion(
                suggestion_type='compliance',
                title='VOC Limiti Aşımı',
                description=f'VOC değeriniz ({voc} g/L) yasal limiti ({voc_limit} g/L) aşıyor.',
                expected_impact={'compliance': 100},
                implementation_steps=[
                    'Düşük VOC veya VOC-free çözücülere geçin',
                    'Su bazlı alternatifi değerlendirin',
                    'Yüksek katı oranlı formülasyon geliştirin'
                ],
                confidence=0.95
            ))
        
        # Maliyet optimizasyonu
        if improvement_type in ['cost', 'balanced']:
            total_cost = formulation.get('total_cost', 0)
            if total_cost > 0:
                suggestions.append(FormulationSuggestion(
                    suggestion_type='cost',
                    title='Maliyet Optimizasyonu',
                    description='Performansı koruyarak maliyet düşürme fırsatları.',
                    expected_impact={'cost': -15},
                    implementation_steps=[
                        'Pahalı pigmentlerin bir kısmını dolgu ile değiştirin',
                        'Daha ekonomik katkı maddesi alternatifleri araştırın',
                        'Toplu alım fırsatlarıyla birim maliyeti düşürün'
                    ],
                    confidence=0.70
                ))
        
        return suggestions
    
    def find_similar_formulations(
        self,
        target_formulation: Dict,
        formulation_history: List[Dict],
        top_n: int = 5
    ) -> List[Dict]:
        """
        Benzer formülasyonları bul
        
        Args:
            target_formulation: Hedef formülasyon
            formulation_history: Geçmiş formülasyonlar
            top_n: Döndürülecek sonuç sayısı
            
        Returns:
            Benzer formülasyon listesi
        """
        similarities = []
        
        target_components = set(c.get('code', c.get('name', '')) 
                               for c in target_formulation.get('components', []))
        
        for hist in formulation_history:
            hist_components = set(c.get('code', c.get('name', '')) 
                                 for c in hist.get('components', []))
            
            # Jaccard benzerliği
            if target_components or hist_components:
                intersection = len(target_components & hist_components)
                union = len(target_components | hist_components)
                similarity = intersection / union if union > 0 else 0
            else:
                similarity = 0
            
            # Parametre benzerliği
            param_sim = 0
            param_count = 0
            for param in ['viscosity', 'ph', 'density']:
                target_val = target_formulation.get(param)
                hist_val = hist.get(param)
                if target_val and hist_val:
                    param_sim += 1 - abs(target_val - hist_val) / max(target_val, hist_val)
                    param_count += 1
            
            if param_count > 0:
                param_sim /= param_count
                similarity = 0.6 * similarity + 0.4 * param_sim
            
            similarities.append({
                'formulation': hist,
                'similarity': round(similarity * 100, 1),
                'common_components': list(target_components & hist_components),
                'formula_code': hist.get('formula_code', 'N/A'),
                'quality_score': hist.get('quality_score')
            })
        
        # Benzerliğe göre sırala
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        return similarities[:top_n]
    
    def save_knowledge(self):
        """Kimyasal bilgi tabanını kaydet"""
        try:
            os.makedirs(os.path.dirname(self.knowledge_path), exist_ok=True)
            with open(self.knowledge_path, 'w', encoding='utf-8') as f:
                json.dump(self.chemical_knowledge, f, ensure_ascii=False, indent=2)
            logger.info("Kimyasal bilgi tabanı kaydedildi")
        except Exception as e:
            logger.error(f"Kimyasal bilgi kayıt hatası: {e}")
    
    def add_material_knowledge(self, category: str, material_key: str, data: Dict):
        """Yeni hammadde bilgisi ekle"""
        if 'material_categories' not in self.chemical_knowledge:
            self.chemical_knowledge['material_categories'] = {}
        
        if category not in self.chemical_knowledge['material_categories']:
            self.chemical_knowledge['material_categories'][category] = {}
        
        self.chemical_knowledge['material_categories'][category][material_key] = data
        self.save_knowledge()
