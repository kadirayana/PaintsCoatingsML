"""
Paint Formulation AI - Lokal ML Modelleri
==========================================
Scikit-learn tabanlı offline ML modelleri
"""

import os
import pickle
import logging
from typing import Dict, List, Any, Optional
import warnings

# Scikit-learn uyarılarını sustur
warnings.filterwarnings('ignore', category=UserWarning)

logger = logging.getLogger(__name__)


class LocalMLModel:
    """
    Lokal ML modeli yöneticisi
    
    Scikit-learn modelleri (Random Forest, vb.) ile offline tahminler yapar.
    """
    
    def __init__(self, model_path: str = None):
        """
        Args:
            model_path: .pkl model dosya yolu
        """
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.feature_names = None
        
        if model_path and os.path.exists(model_path):
            self._load_model()
    
    def _load_model(self) -> bool:
        """Model dosyasını yükle"""
        try:
            with open(self.model_path, 'rb') as f:
                data = pickle.load(f)
            
            if isinstance(data, dict):
                self.model = data.get('model')
                self.scaler = data.get('scaler')
                self.feature_names = data.get('feature_names', [])
            else:
                self.model = data
            
            logger.info(f"Model yüklendi: {self.model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Model yükleme hatası: {e}")
            return False
    
    def predict(self, data: List[Dict]) -> Dict:
        """
        Tahmin yap
        
        Args:
            data: Giriş verileri
            
        Returns:
            Tahmin sonuçları
        """
        if not data:
            return {'error': 'Veri yok'}
        
        # Model yoksa veya yüklenemiyorsa kural tabanlı analiz yap
        if self.model is None:
            return self._rule_based_analysis(data)
        
        try:
            # Veriyi hazırla
            X = self._prepare_features(data)
            
            # Tahmin yap
            if hasattr(self.model, 'predict_proba'):
                probas = self.model.predict_proba(X)
                predictions = self.model.predict(X)
                confidence = probas.max(axis=1).mean()
            else:
                predictions = self.model.predict(X)
                confidence = 0.7  # Varsayılan güven
            
            # Özellik önemini al
            feature_importance = self._get_feature_importance()
            
            # Önerileri oluştur
            recommendations = self._generate_recommendations(data, predictions)
            
            return {
                'prediction': predictions.tolist() if hasattr(predictions, 'tolist') else predictions,
                'confidence': float(confidence),
                'feature_importance': feature_importance,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Tahmin hatası: {e}")
            return self._rule_based_analysis(data)
    
    def _prepare_features(self, data: List[Dict]) -> Any:
        """Özellikleri hazırla"""
        try:
            import numpy as np
            
            feature_cols = self.feature_names or ['viscosity', 'ph', 'density', 'opacity', 'gloss']
            
            X = []
            for row in data:
                features = []
                for col in feature_cols:
                    val = row.get(col, 0)
                    features.append(float(val) if val is not None else 0.0)
                X.append(features)
            
            X = np.array(X)
            
            # Scaler varsa uygula
            if self.scaler is not None:
                X = self.scaler.transform(X)
            
            return X
            
        except ImportError:
            logger.warning("numpy bulunamadı, basit liste döndürülüyor")
            return [[row.get(col, 0) for col in ['viscosity', 'ph', 'density', 'opacity', 'gloss']] for row in data]
    
    def _get_feature_importance(self) -> Dict[str, float]:
        """Özellik önemlerini al"""
        if self.model is None:
            return {}
        
        try:
            feature_names = self.feature_names or ['Viskozite', 'pH', 'Yoğunluk', 'Örtücülük', 'Parlaklık']
            
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
                return {name: float(imp) for name, imp in zip(feature_names, importances)}
            
            return {}
            
        except Exception:
            return {}
    
    def _generate_recommendations(self, data: List[Dict], predictions: Any) -> List[str]:
        """Önerileri oluştur"""
        recommendations = []
        
        if not data:
            return ["Veri yetersiz, öneri oluşturulamadı"]
        
        # Son kayıttan öneriler çıkar
        last_record = data[-1] if data else {}
        
        viscosity = last_record.get('viscosity')
        if viscosity:
            if viscosity < 1000:
                recommendations.append("Viskozite artırıcı (Hidroksietil selüloz) ekleyin")
            elif viscosity > 5000:
                recommendations.append("Su veya seyreltici ile viskoziteyi düşürün")
        
        ph = last_record.get('ph')
        if ph:
            if ph < 7:
                recommendations.append("pH'ı yükseltmek için amonyak veya sodyum hidroksit ekleyin")
            elif ph > 9.5:
                recommendations.append("pH'ı düşürmek için asetik asit ekleyin")
        
        opacity = last_record.get('opacity')
        if opacity:
            if opacity < 85:
                recommendations.append("Örtücülüğü artırmak için TiO2 oranını yükseltin")
        
        if not recommendations:
            recommendations.append("Mevcut formülasyon parametreleri optimum görünüyor")
        
        return recommendations
    
    def _rule_based_analysis(self, data: List[Dict]) -> Dict:
        """Kural tabanlı analiz (model yoksa)"""
        recommendations = []
        analysis = {}
        
        # İstatistikleri hesapla
        for key in ['viscosity', 'ph', 'density', 'opacity', 'gloss']:
            values = [d.get(key) for d in data if d.get(key) is not None]
            if values:
                analysis[key] = {
                    'mean': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'count': len(values)
                }
        
        # Öneriler
        if 'viscosity' in analysis:
            avg = analysis['viscosity']['mean']
            if avg < 1500:
                recommendations.append("Viskozite düşük - HEC veya HEUR tipi koyulaştırıcı ekleyin")
            elif avg > 4000:
                recommendations.append("Viskozite yüksek - Su ekleyerek seyreltin")
        
        if 'ph' in analysis:
            avg = analysis['ph']['mean']
            if avg < 7.5:
                recommendations.append("pH düşük - Amonyak ekleyerek yükseltin")
            elif avg > 9:
                recommendations.append("pH yüksek - Asit ile dengeleme yapın")
        
        if 'opacity' in analysis:
            avg = analysis['opacity']['mean']
            if avg < 90:
                recommendations.append("Örtücülük yetersiz - TiO2 oranını artırın veya grind kalitesini iyileştirin")
        
        if not recommendations:
            recommendations.append("Formülasyon parametreleri kabul edilebilir sınırlar içinde")
        
        return {
            'prediction': 'Kural tabanlı analiz',
            'confidence': 0.6,
            'analysis': analysis,
            'recommendations': recommendations,
            'feature_importance': {
                'Viskozite': 0.25,
                'pH': 0.20,
                'Yoğunluk': 0.15,
                'Örtücülük': 0.25,
                'Parlaklık': 0.15
            }
        }
    
    def train(self, X: List[List[float]], y: List[Any], feature_names: List[str] = None) -> bool:
        """
        Model eğit (opsiyonel - kullanıcı veri topladıkça)
        
        Args:
            X: Özellik matrisi
            y: Hedef değerler
            feature_names: Özellik isimleri
            
        Returns:
            Başarı durumu
        """
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.preprocessing import StandardScaler
            import numpy as np
            
            X = np.array(X)
            y = np.array(y)
            
            # Scaler
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
            
            # Model
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            self.model.fit(X_scaled, y)
            
            self.feature_names = feature_names or [f'feature_{i}' for i in range(X.shape[1])]
            
            logger.info("Model eğitildi")
            return True
            
        except ImportError:
            logger.error("scikit-learn bulunamadı: pip install scikit-learn")
            return False
        except Exception as e:
            logger.error(f"Eğitim hatası: {e}")
            return False
    
    def save(self, path: str = None) -> bool:
        """Modeli kaydet"""
        save_path = path or self.model_path
        
        if not save_path:
            logger.error("Kayıt yolu belirtilmedi")
            return False
        
        try:
            data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names
            }
            
            with open(save_path, 'wb') as f:
                pickle.dump(data, f)
            
            logger.info(f"Model kaydedildi: {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Kaydetme hatası: {e}")
            return False


class FormulationOptimizer:
    """Formülasyon optimizasyonu için yardımcı sınıf"""
    
    @staticmethod
    def suggest_adjustments(current_values: Dict, target_values: Dict) -> List[Dict]:
        """
        Hedef değerlere ulaşmak için ayarlama önerileri
        
        Args:
            current_values: Mevcut parametre değerleri
            target_values: Hedef parametre değerleri
            
        Returns:
            Ayarlama önerileri listesi
        """
        adjustments = []
        
        # Viskozite
        if 'viscosity' in current_values and 'viscosity' in target_values:
            diff = target_values['viscosity'] - current_values['viscosity']
            if abs(diff) > 100:
                if diff > 0:
                    adjustments.append({
                        'parameter': 'Viskozite',
                        'action': 'Artır',
                        'suggestion': 'HEC veya HEUR tipi koyulaştırıcı ekle',
                        'amount': f'+{diff:.0f} cP hedef'
                    })
                else:
                    adjustments.append({
                        'parameter': 'Viskozite',
                        'action': 'Azalt',
                        'suggestion': 'Su veya seyreltici ekle',
                        'amount': f'{diff:.0f} cP hedef'
                    })
        
        # pH
        if 'ph' in current_values and 'ph' in target_values:
            diff = target_values['ph'] - current_values['ph']
            if abs(diff) > 0.2:
                if diff > 0:
                    adjustments.append({
                        'parameter': 'pH',
                        'action': 'Artır',
                        'suggestion': 'Amonyak veya sodyum hidroksit ekle',
                        'amount': f'+{diff:.2f} pH hedef'
                    })
                else:
                    adjustments.append({
                        'parameter': 'pH',
                        'action': 'Azalt',
                        'suggestion': 'Asetik asit ekle',
                        'amount': f'{diff:.2f} pH hedef'
                    })
        
        return adjustments
    
    @staticmethod
    def calculate_cost_optimization(components: List[Dict], target_cost: float) -> Dict:
        """
        Maliyet optimizasyonu hesapla
        
        Args:
            components: Bileşen listesi (ad, miktar, birim fiyat)
            target_cost: Hedef maliyet
            
        Returns:
            Optimizasyon önerileri
        """
        total_cost = sum(c.get('amount', 0) * c.get('unit_price', 0) for c in components)
        
        result = {
            'current_cost': total_cost,
            'target_cost': target_cost,
            'difference': target_cost - total_cost,
            'suggestions': []
        }
        
        if total_cost > target_cost:
            # Maliyet düşürme önerileri
            sorted_components = sorted(
                components,
                key=lambda x: x.get('unit_price', 0),
                reverse=True
            )
            
            for comp in sorted_components[:3]:
                result['suggestions'].append(
                    f"'{comp.get('name', 'Bileşen')}' için daha ekonomik alternatif araştırın"
                )
        
        return result
