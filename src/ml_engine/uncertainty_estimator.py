"""
Paint Formulation AI - Uncertainty Estimation Modülü
=====================================================
Model tahminlerinin güven aralığını hesaplayan sistem.

Yöntemler:
- Ensemble Varyans: Birden fazla model tahminlerinin varyansı
- Bootstrap Sampling: Tekrarlı örnekleme ile güven aralığı
- Cold-Start Algılama: Yetersiz veri durumunda uyarı
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceResult:
    """Güven tahmini sonucu"""
    confidence_percent: float  # 0-100 arası güven yüzdesi
    prediction: float          # Ana tahmin değeri
    lower_bound: float         # Alt sınır (%95 güven)
    upper_bound: float         # Üst sınır (%95 güven)
    variance: float            # Varyans
    is_cold_start: bool        # Cold-start durumu mu?
    sample_count: int          # Eğitim veri sayısı


class UncertaintyEstimator:
    """
    Model tahminlerinin belirsizliğini (uncertainty) hesaplar.
    
    Düşük veri durumunda düşük güven skoru,
    yeterli veri ve tutarlı tahminlerde yüksek güven skoru verir.
    """
    
    # Cold-start eşikleri
    COLD_START_THRESHOLD = 10      # 10'dan az veri = cold-start
    LOW_CONFIDENCE_THRESHOLD = 30  # 30'dan az veri = düşük güven
    HIGH_CONFIDENCE_THRESHOLD = 100  # 100+ veri = yüksek güven
    
    # Varyans -> Güven dönüşüm faktörleri
    VARIANCE_SCALE = 0.1  # Varyansı normalize etmek için
    
    def __init__(self, n_bootstrap: int = 10):
        """
        Args:
            n_bootstrap: Bootstrap iterasyon sayısı
        """
        self.n_bootstrap = n_bootstrap
    
    def estimate_confidence(
        self, 
        prediction: float,
        model,
        X: np.ndarray,
        training_samples: int
    ) -> ConfidenceResult:
        """
        Tek bir tahmin için güven tahmini yap.
        
        Args:
            prediction: Model tahmini
            model: Eğitilmiş model (GradientBoostingRegressor vb.)
            X: Girdi verisi (ölçeklenmiş)
            training_samples: Eğitimde kullanılan örnek sayısı
            
        Returns:
            ConfidenceResult: Güven sonucu
        """
        is_cold_start = training_samples < self.COLD_START_THRESHOLD
        
        # GradientBoostingRegressor için staged_predict kullan
        if hasattr(model, 'staged_predict'):
            # Her aşamanın tahminlerinden varyans hesapla
            staged_preds = list(model.staged_predict(X))
            if len(staged_preds) > 5:
                # Son 5 aşamanın varyansı
                recent_preds = staged_preds[-5:]
                variance = np.var([p[0] for p in recent_preds])
            else:
                variance = 0.1  # Varsayılan düşük varyans
        else:
            # Fallback: Sabit varyans tahmini
            variance = 0.1
        
        # Varyans + Veri miktarından güven hesapla
        confidence = self._calculate_confidence(variance, training_samples)
        
        # Güven aralığı hesapla (%95)
        std_dev = np.sqrt(variance) if variance > 0 else 0.1
        z_score = 1.96  # %95 güven için
        margin = z_score * std_dev
        
        lower_bound = prediction - margin
        upper_bound = prediction + margin
        
        return ConfidenceResult(
            confidence_percent=round(confidence, 1),
            prediction=prediction,
            lower_bound=round(lower_bound, 2),
            upper_bound=round(upper_bound, 2),
            variance=round(variance, 4),
            is_cold_start=is_cold_start,
            sample_count=training_samples
        )
    
    def estimate_ensemble_confidence(
        self,
        models: Dict,
        X: np.ndarray,
        training_samples: int
    ) -> Dict[str, ConfidenceResult]:
        """
        Tüm hedef modeller için güven tahmini yap.
        
        Args:
            models: {target_name: model} sözlüğü
            X: Girdi verisi
            training_samples: Eğitimde kullanılan örnek sayısı
            
        Returns:
            {target_name: ConfidenceResult} sözlüğü
        """
        results = {}
        
        for target_name, model in models.items():
            try:
                prediction = model.predict(X)[0]
                result = self.estimate_confidence(
                    prediction, model, X, training_samples
                )
                results[target_name] = result
            except Exception as e:
                logger.warning(f"Güven tahmini hatası ({target_name}): {e}")
                # Fallback: Düşük güvenli sonuç
                results[target_name] = ConfidenceResult(
                    confidence_percent=0.0,
                    prediction=0.0,
                    lower_bound=0.0,
                    upper_bound=0.0,
                    variance=1.0,
                    is_cold_start=True,
                    sample_count=training_samples
                )
        
        return results
    
    def get_overall_confidence(self, results: Dict[str, ConfidenceResult]) -> float:
        """
        Tüm hedeflerin ortalama güven skorunu döndür.
        
        Args:
            results: {target_name: ConfidenceResult} sözlüğü
            
        Returns:
            Ortalama güven yüzdesi (0-100)
        """
        if not results:
            return 0.0
        
        confidences = [r.confidence_percent for r in results.values()]
        return round(sum(confidences) / len(confidences), 1)
    
    def is_cold_start_scenario(self, training_samples: int) -> bool:
        """
        Cold-start durumu mu kontrol et.
        
        Args:
            training_samples: Eğitim verisi sayısı
            
        Returns:
            True ise cold-start durumu
        """
        return training_samples < self.COLD_START_THRESHOLD
    
    def get_confidence_message(self, confidence: float, is_cold_start: bool) -> str:
        """
        Kullanıcıya gösterilecek güven mesajını oluştur.
        
        Args:
            confidence: Güven yüzdesi
            is_cold_start: Cold-start durumu mu
            
        Returns:
            Türkçe açıklama mesajı
        """
        if is_cold_start:
            return "⚠️ Yetersiz veri: Tahminler güvenilir olmayabilir"
        elif confidence < 30:
            return f"📉 Düşük güven (%{confidence:.0f}): Daha fazla test verisi gerekli"
        elif confidence < 60:
            return f"📊 Orta güven (%{confidence:.0f}): Tahminler kabul edilebilir"
        elif confidence < 80:
            return f"📈 İyi güven (%{confidence:.0f}): Tahminler güvenilir"
        else:
            return f"✅ Yüksek güven (%{confidence:.0f}): Tahminler çok güvenilir"
    
    def _calculate_confidence(self, variance: float, training_samples: int) -> float:
        """
        Varyans ve veri miktarından güven yüzdesi hesapla.
        
        Args:
            variance: Tahmin varyansı
            training_samples: Eğitim verisi sayısı
            
        Returns:
            Güven yüzdesi (0-100)
        """
        # Veri miktarı faktörü (0-50 puan)
        if training_samples < self.COLD_START_THRESHOLD:
            data_score = training_samples * 2  # 0-20 arası
        elif training_samples < self.LOW_CONFIDENCE_THRESHOLD:
            data_score = 20 + (training_samples - 10) * 1.5  # 20-50 arası
        elif training_samples < self.HIGH_CONFIDENCE_THRESHOLD:
            data_score = 50 + (training_samples - 30) * 0.3  # 50-71 arası
        else:
            data_score = min(50, 50)  # Max 50 puan
        
        # Varyans faktörü (0-50 puan)
        # Düşük varyans = yüksek puan
        normalized_var = variance * self.VARIANCE_SCALE
        if normalized_var < 0.01:
            var_score = 50
        elif normalized_var < 0.1:
            var_score = 40
        elif normalized_var < 0.5:
            var_score = 30
        elif normalized_var < 1.0:
            var_score = 20
        else:
            var_score = max(0, 10 - normalized_var)
        
        # Toplam güven
        confidence = data_score + var_score
        return min(100, max(0, confidence))
