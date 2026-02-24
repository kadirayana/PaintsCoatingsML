"""
Paint Formulation AI - Kimyasal Kısıtlar Modülü
================================================
Reçetelerin kimyasal geçerliliğini kontrol eden kural motoru.

Kısıt Kategorileri:
- Fiziksel Kısıtlar (Hard): Kütle dengesi, negatif engel
- PVC Kontrolü: Parlak/mat boya için uygunluk
- Hansen Parametreleri: Çözünürlük uyumluluğu
- pH Dengesi: Emülsiyon kararlılığı
- Hammadde Limitleri: Min/Max kullanım oranları
"""

import math
import logging
from typing import List, Dict, Tuple, Optional, NamedTuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ValidationWarning:
    """Doğrulama uyarısı"""
    code: str
    message: str
    severity: str = "warning"  # warning, error
    component: Optional[str] = None


@dataclass
class ValidationResult:
    """Doğrulama sonucu"""
    is_valid: bool
    errors: List[ValidationWarning] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    penalty_score: float = 0.0
    
    def add_error(self, code: str, message: str, component: str = None):
        self.errors.append(ValidationWarning(code, message, "error", component))
        self.is_valid = False
        
    def add_warning(self, code: str, message: str, component: str = None):
        self.warnings.append(ValidationWarning(code, message, "warning", component))


class ChemicalValidator:
    """
    Reçete kimyasal kısıt kontrol sistemi.
    
    MLOptimizer ile entegre çalışarak geçersiz reçeteleri engeller
    ve fitness fonksiyonuna penalty puanı sağlar.
    """
    
    # PVC limitleri (boya tipine göre)
    PVC_LIMITS = {
        'high_gloss': {'max': 25},      # Parlak boya
        'semi_gloss': {'max': 35},      # Yarı parlak
        'satin': {'max': 45},           # Saten
        'matte': {'min': 40, 'max': 85} # Mat boya
    }
    
    # pH kararlılık aralığı (su bazlı sistemler için)
    PH_STABILITY_RANGE = {'min': 8.0, 'max': 9.5}
    
    # Varsayılan hammadde limitleri (kategori bazlı, %)
    DEFAULT_MATERIAL_LIMITS = {
        'defoamer': {'min': 0.0, 'max': 0.5, 'warning': 'Krater oluşumu riski'},
        'thickener': {'min': 0.0, 'max': 2.0, 'warning': 'Akış bozukluğu riski'},
        'dispersant': {'min': 0.0, 'max': 1.0, 'warning': 'Su direnci düşebilir'},
        'drier': {'min': 0.0, 'max': 0.2, 'warning': 'Erken skinning riski'},
        'wetting_agent': {'min': 0.0, 'max': 0.5, 'warning': 'Köpük oluşumu'},
        'biocide': {'min': 0.0, 'max': 0.3, 'warning': 'Toksisite riski'}
    }
    
    def __init__(self, db_manager=None):
        """
        Args:
            db_manager: Veritabanı yöneticisi (hammadde özelliklerini çekmek için)
        """
        self.db_manager = db_manager
        self._material_cache = {}
    
    def validate_recipe(self, recipe: List[Dict], target_type: str = None) -> ValidationResult:
        """
        Reçetenin tüm kimyasal kısıtlarını kontrol et.
        
        Args:
            recipe: Bileşen listesi [{'name': str, 'amount': float, 'category': str, ...}, ...]
            target_type: Hedef boya tipi ('high_gloss', 'matte', vb.)
            
        Returns:
            ValidationResult: Doğrulama sonucu
        """
        result = ValidationResult(is_valid=True)
        
        if not recipe:
            result.add_error('EMPTY_RECIPE', 'Reçete boş olamaz')
            return result
            
        # 1. Fiziksel Kısıtlar
        self._check_mass_balance(recipe, result)
        self._check_negative_amounts(recipe, result)
        
        # 2. PVC Kontrolü
        if target_type:
            self._check_pvc(recipe, target_type, result)
        
        # 3. Hammadde Limitleri
        self._check_material_limits(recipe, result)
        
        # 4. pH Kararlılığı (su bazlı sistemlerde)
        self._check_ph_stability(recipe, result)
        
        # 5. Hansen Çözünürlük (solvent bazlı sistemlerde)
        self._check_hansen_compatibility(recipe, result)
        
        # Toplam penalty skorunu hesapla
        result.penalty_score = self._calculate_penalty(result)
        
        return result
    
    def normalize_recipe(self, recipe: List[Dict]) -> List[Dict]:
        """
        Reçeteyi %100'e normalize et.
        
        Args:
            recipe: Orijinal bileşen listesi
            
        Returns:
            Normalize edilmiş bileşen listesi
        """
        if not recipe:
            return recipe
            
        total = sum(c.get('amount', 0) or 0 for c in recipe)
        
        if total <= 0:
            return recipe
            
        factor = 100.0 / total
        
        normalized = []
        for comp in recipe:
            new_comp = comp.copy()
            new_comp['amount'] = (comp.get('amount', 0) or 0) * factor
            new_comp['percentage'] = new_comp['amount']
            normalized.append(new_comp)
            
        return normalized
    
    def calculate_pvc(self, recipe: List[Dict]) -> float:
        """
        Pigment Hacim Konsantrasyonu hesapla.
        
        PVC = (Pigment Hacmi + Dolgu Hacmi) / (Toplam Kuru Film Hacmi) × 100
        
        Args:
            recipe: Bileşen listesi (density ve solid_content bilgisi gerekli)
            
        Returns:
            PVC değeri (%)
        """
        pigment_filler_volume = 0.0
        binder_volume = 0.0
        
        for comp in recipe:
            amount = comp.get('amount', 0) or 0
            density = comp.get('density', 1.0) or 1.0
            solid_content = comp.get('solid_content', 100) or 100
            category = (comp.get('category', '') or '').lower()
            
            # Katı hacmi hesapla
            solid_mass = amount * (solid_content / 100.0)
            volume = solid_mass / density if density > 0 else 0
            
            if category in ['pigment', 'filler', 'dolgu', 'extender']:
                pigment_filler_volume += volume
            elif category in ['binder', 'resin', 'bağlayıcı', 'reçine']:
                binder_volume += volume
        
        total_dry_volume = pigment_filler_volume + binder_volume
        
        if total_dry_volume <= 0:
            return 0.0
            
        pvc = (pigment_filler_volume / total_dry_volume) * 100
        return round(pvc, 2)
    
    def calculate_hansen_distance(self, binder: Dict, solvents: List[Dict]) -> float:
        """
        Hansen çözünürlük mesafesini hesapla.
        
        Ra = √[4(δD1-δD2)² + (δP1-δP2)² + (δH1-δH2)²]
        
        Args:
            binder: Bağlayıcı hammadde bilgisi (hansen_d, hansen_p, hansen_h)
            solvents: Çözücü listesi (aynı parametrelerle)
            
        Returns:
            Ra değeri (çözünürlük mesafesi)
        """
        if not binder or not solvents:
            return 0.0
        
        binder_d = binder.get('hansen_d', 0) or 0
        binder_p = binder.get('hansen_p', 0) or 0
        binder_h = binder.get('hansen_h', 0) or 0
        
        # Çözücü karışımının ağırlıklı ortalaması
        total_amount = sum(s.get('amount', 0) or 0 for s in solvents)
        if total_amount <= 0:
            return 0.0
        
        mix_d = sum((s.get('hansen_d', 0) or 0) * (s.get('amount', 0) or 0) for s in solvents) / total_amount
        mix_p = sum((s.get('hansen_p', 0) or 0) * (s.get('amount', 0) or 0) for s in solvents) / total_amount
        mix_h = sum((s.get('hansen_h', 0) or 0) * (s.get('amount', 0) or 0) for s in solvents) / total_amount
        
        # Ra hesapla
        ra = math.sqrt(
            4 * (binder_d - mix_d) ** 2 +
            (binder_p - mix_p) ** 2 +
            (binder_h - mix_h) ** 2
        )
        
        return round(ra, 2)
    
    def check_ph_stability(self, recipe: List[Dict]) -> Tuple[bool, Optional[str]]:
        """
        pH kararlılığını kontrol et.
        
        Args:
            recipe: Bileşen listesi
            
        Returns:
            (kararlı_mı, öneri_mesajı)
        """
        # Toplam pH etkisini hesapla (basitleştirilmiş model)
        acidic_effect = 0.0
        basic_effect = 0.0
        
        for comp in recipe:
            amount = comp.get('amount', 0) or 0
            ph_value = comp.get('ph', 7.0) or 7.0
            
            if ph_value < 7:
                acidic_effect += amount * (7 - ph_value)
            elif ph_value > 7:
                basic_effect += amount * (ph_value - 7)
        
        # Net pH tahmini
        net_effect = basic_effect - acidic_effect
        estimated_ph = 7.0 + (net_effect / 100.0)  # Basitleştirilmiş model
        
        if estimated_ph < self.PH_STABILITY_RANGE['min']:
            return False, f"pH çok düşük (~{estimated_ph:.1f}). Amonyak veya MEA ekleyin."
        elif estimated_ph > self.PH_STABILITY_RANGE['max']:
            return False, f"pH çok yüksek (~{estimated_ph:.1f}). Asit ile düşürün."
        
        return True, None
    
    def get_penalty_score(self, recipe: List[Dict], target_type: str = None) -> float:
        """
        GA fitness fonksiyonu için penalty skoru hesapla.
        
        Args:
            recipe: Bileşen listesi
            target_type: Hedef boya tipi
            
        Returns:
            Penalty skoru (0 = mükemmel, yüksek = kötü)
        """
        result = self.validate_recipe(recipe, target_type)
        return result.penalty_score
    
    # === Private Methods ===
    
    def _check_mass_balance(self, recipe: List[Dict], result: ValidationResult):
        """Kütle dengesi kontrolü"""
        total = sum(c.get('amount', 0) or 0 for c in recipe)
        
        if abs(total - 100) > 5:  # %5 tolerans
            result.add_warning(
                'MASS_IMBALANCE',
                f'Toplam miktar %{total:.1f}. %100 olmalı.'
            )
            result.penalty_score += abs(total - 100) * 0.5
    
    def _check_negative_amounts(self, recipe: List[Dict], result: ValidationResult):
        """Negatif miktar kontrolü"""
        for comp in recipe:
            amount = comp.get('amount', 0) or 0
            if amount < 0:
                result.add_error(
                    'NEGATIVE_AMOUNT',
                    f"{comp.get('name', 'Bilinmeyen')} miktarı negatif olamaz.",
                    comp.get('name')
                )
    
    def _check_pvc(self, recipe: List[Dict], target_type: str, result: ValidationResult):
        """PVC kontrolü"""
        pvc = self.calculate_pvc(recipe)
        limits = self.PVC_LIMITS.get(target_type.lower(), {})
        
        if 'max' in limits and pvc > limits['max']:
            result.add_error(
                'PVC_TOO_HIGH',
                f"PVC değeri (%{pvc:.1f}) {target_type} boya için çok yüksek. Max: %{limits['max']}"
            )
            result.penalty_score += (pvc - limits['max']) * 2
            
        if 'min' in limits and pvc < limits['min']:
            result.add_warning(
                'PVC_TOO_LOW',
                f"PVC değeri (%{pvc:.1f}) {target_type} boya için çok düşük. Min: %{limits['min']}"
            )
            result.penalty_score += (limits['min'] - pvc) * 1
    
    def _check_material_limits(self, recipe: List[Dict], result: ValidationResult):
        """Hammadde limit kontrolü"""
        for comp in recipe:
            amount = comp.get('amount', 0) or 0
            category = (comp.get('category', '') or '').lower()
            name = comp.get('name', 'Bilinmeyen')
            
            # Önce hammadde spesifik limitleri kontrol et
            max_limit = comp.get('max_limit')
            min_limit = comp.get('min_limit')
            
            # Yoksa varsayılan kategori limitlerini kullan
            if max_limit is None and category in self.DEFAULT_MATERIAL_LIMITS:
                limits = self.DEFAULT_MATERIAL_LIMITS[category]
                max_limit = limits.get('max')
                min_limit = limits.get('min', 0)
                warning_msg = limits.get('warning', 'Limit aşıldı')
            else:
                warning_msg = 'Kullanım sınırı aşıldı'
            
            # Limit kontrolü
            if max_limit is not None and amount > max_limit:
                result.add_warning(
                    'MATERIAL_LIMIT_EXCEEDED',
                    f"{name}: %{amount:.2f} > Max %{max_limit}. {warning_msg}",
                    name
                )
                result.penalty_score += (amount - max_limit) * 5
                
            if min_limit is not None and amount < min_limit and amount > 0:
                result.add_warning(
                    'MATERIAL_BELOW_MIN',
                    f"{name}: %{amount:.2f} < Min %{min_limit}",
                    name
                )
    
    def _check_ph_stability(self, recipe: List[Dict], result: ValidationResult):
        """pH kararlılık kontrolü"""
        # Su bazlı sistem mi kontrol et
        has_water = any(
            (c.get('category', '') or '').lower() in ['water', 'su', 'solvent'] and
            (c.get('name', '') or '').lower() in ['su', 'water', 'deiyonize su']
            for c in recipe
        )
        
        if not has_water:
            return  # Solvent bazlı sistem, pH kontrolü atla
        
        is_stable, suggestion = self.check_ph_stability(recipe)
        
        if not is_stable:
            result.add_warning('PH_UNSTABLE', suggestion)
            result.penalty_score += 10
    
    def _check_hansen_compatibility(self, recipe: List[Dict], result: ValidationResult):
        """Hansen çözünürlük uyumluluğu kontrolü"""
        # Bağlayıcı ve çözücüleri ayır
        binders = [c for c in recipe if (c.get('category', '') or '').lower() in ['binder', 'resin', 'bağlayıcı']]
        solvents = [c for c in recipe if (c.get('category', '') or '').lower() in ['solvent', 'çözücü']]
        
        if not binders or not solvents:
            return
        
        # Her bağlayıcı için kontrol et
        for binder in binders:
            ro = binder.get('interaction_radius', 8.0) or 8.0  # Varsayılan etkileşim yarıçapı
            ra = self.calculate_hansen_distance(binder, solvents)
            
            if ra > ro:
                result.add_warning(
                    'HANSEN_INCOMPATIBLE',
                    f"{binder.get('name', 'Bağlayıcı')} çözücü karışımında çökebilir. Ra={ra:.1f} > Ro={ro:.1f}",
                    binder.get('name')
                )
                result.penalty_score += (ra - ro) * 3
    
    def _calculate_penalty(self, result: ValidationResult) -> float:
        """
        Toplam penalty skorunu hesapla.
        
        Hata ağırlığı: Error > Warning
        """
        penalty = result.penalty_score
        
        # Her error için ek penalty
        penalty += len(result.errors) * 50
        
        # Her warning için az miktarda penalty
        penalty += len(result.warnings) * 5
        
        return penalty
