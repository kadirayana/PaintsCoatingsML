"""
Paint Formulation AI - Global Öğrenme Modeli
=============================================
Tüm projelerden öğrenen ve bilgi sentezi yapan model

Özellikler:
- Federated learning yaklaşımı
- Transfer learning ile projelere aktarım
- hammadde-performans pattern analizi
"""

import os
import pickle
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import warnings

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class GlobalLearner:
    """
    Global (Federated) Öğrenme Modeli
    
    Tüm projelerden edinilen bilgiyi birleştirir ve genel kalıplar çıkarır:
    - hammadde-performans ilişkileri
    - Maliyet-kalite trade-off'ları
    - Optimum formülasyon kuralları
    """
    
    MIN_TRAINING_SAMPLES = 10  # Global model için daha fazla veri gerekli
    
    def __init__(self, models_dir: str = 'assets/models'):
        """
        Args:
            models_dir: Model dosyalarının kaydedileceği dizin
        """
        self.models_dir = models_dir
        os.makedirs(models_dir, exist_ok=True)
        
        self.model_path = os.path.join(models_dir, 'global_model.pkl')
        
        # Feature ve target tanımları
        self.feature_names = ['viscosity', 'ph', 'density', 'coating_thickness']
        self.target_names = [
            'opacity', 'gloss', 'quality_score', 'total_cost',
            'corrosion_resistance', 'adhesion', 'hardness',
            'flexibility', 'chemical_resistance', 'uv_resistance', 'abrasion_resistance'
        ]
        
        # Global model cache
        self._model_data: Optional[Dict] = None
        self._load_model()
    
    def _load_model(self):
        """Global modeli yükle"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    self._model_data = pickle.load(f)
                logger.info("Global model yüklendi")
            except Exception as e:
                logger.error(f"Global model yükleme hatası: {e}")
    
    def _save_model(self):
        """Global modeli kaydet"""
        if self._model_data:
            try:
                with open(self.model_path, 'wb') as f:
                    pickle.dump(self._model_data, f)
                logger.info("Global model kaydedildi")
            except Exception as e:
                logger.error(f"Global model kayıt hatası: {e}")
    
    def train_global_model(self, all_training_data: List[Dict], 
                           project_summaries: List[Dict] = None) -> Dict:
        """
        Tüm projelerden global model eğit
        
        Args:
            all_training_data: Tüm projelerden toplanan eğitim verisi
            project_summaries: Proje bazlı özet bilgileri
            
        Returns:
            Eğitim sonuçları ve öğrenilen kalıplar
        """
        logger.info(f"Global model eğitimi başlatıldı. Toplam veri: {len(all_training_data)}")
        
        if len(all_training_data) < self.MIN_TRAINING_SAMPLES:
            return {
                'success': False,
                'message': f'Global model için en az {self.MIN_TRAINING_SAMPLES} kayıt gerekli. Mevcut: {len(all_training_data)}',
                'samples': len(all_training_data)
            }
        
        try:
            import numpy as np
            from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
            from sklearn.preprocessing import StandardScaler
            from sklearn.model_selection import cross_val_score
            
            # Veriyi hazırla
            X, y_dict = self._prepare_data(all_training_data)
            
            if len(X) < self.MIN_TRAINING_SAMPLES:
                return {
                    'success': False,
                    'message': 'Yeterli geçerli veri yok',
                    'samples': len(X)
                }
            
            X = np.array(X)
            
            # Scaler
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            models = {}
            patterns = {}
            results = {
                'success': True,
                'targets': {},
                'samples': len(X),
                'trained_at': datetime.now().isoformat(),
                'projects_included': len(project_summaries) if project_summaries else 0
            }
            
            # Her hedef için model eğit
            for target_name in self.target_names:
                if target_name in y_dict and len(y_dict[target_name]) == len(X):
                    y = np.array(y_dict[target_name])
                    
                    valid_mask = ~np.isnan(y)
                    if valid_mask.sum() >= 5:  # Global için minimum 5 örnek
                        X_valid = X_scaled[valid_mask]
                        y_valid = y[valid_mask]
                        
                        # Ensemble model kullan (daha robust)
                        model = GradientBoostingRegressor(
                            n_estimators=100,
                            max_depth=4,
                            learning_rate=0.1,
                            random_state=42
                        )
                        model.fit(X_valid, y_valid)
                        
                        # Cross-validation
                        cv_folds = min(5, len(X_valid))
                        cv_scores = cross_val_score(model, X_valid, y_valid, cv=cv_folds, scoring='r2')
                        r2_score = max(cv_scores.mean(), 0)
                        
                        models[target_name] = model
                        
                        # Feature importance analizi
                        importance = dict(zip(
                            self.feature_names,
                            [round(float(x), 3) for x in model.feature_importances_]
                        ))
                        
                        results['targets'][target_name] = {
                            'r2_score': round(r2_score, 3),
                            'samples': int(valid_mask.sum()),
                            'feature_importance': importance
                        }
                        
                        # Pattern analizi
                        patterns[target_name] = self._analyze_patterns(
                            X_valid, y_valid, self.feature_names
                        )
            
            # Öğrenilen kalıpları çıkar
            learned_patterns = self._extract_global_patterns(patterns, all_training_data)
            
            # Model verisini kaydet
            self._model_data = {
                'models': models,
                'scaler': scaler,
                'feature_names': self.feature_names,
                'target_names': list(models.keys()),
                'results': results,
                'patterns': patterns,
                'learned_patterns': learned_patterns,
                'trained_at': datetime.now(),
                'samples_count': len(X)
            }
            
            self._save_model()
            
            # Ortalama R² hesapla
            if results['targets']:
                avg_r2 = sum(t['r2_score'] for t in results['targets'].values()) / len(results['targets'])
                results['avg_r2_score'] = round(avg_r2, 3)
            
            results['learned_patterns'] = learned_patterns
            
            logger.info(f"Global model eğitimi tamamlandı. Pattern sayısı: {len(learned_patterns)}")
            return results
            
        except Exception as e:
            logger.error(f"Global model eğitim hatası: {e}")
            return {'success': False, 'message': str(e)}
    
    def _analyze_patterns(self, X, y, feature_names: List[str]) -> Dict:
        """Feature-target ilişki pattern'lerini analiz et"""
        import numpy as np
        
        patterns = {}
        
        for i, feat in enumerate(feature_names):
            feat_values = X[:, i]
            
            # Korelasyon
            if len(feat_values) > 2:
                correlation = np.corrcoef(feat_values, y)[0, 1]
                if not np.isnan(correlation):
                    patterns[feat] = {
                        'correlation': round(float(correlation), 3),
                        'effect': 'positive' if correlation > 0.3 else 'negative' if correlation < -0.3 else 'neutral',
                        'strength': 'strong' if abs(correlation) > 0.7 else 'moderate' if abs(correlation) > 0.4 else 'weak'
                    }
        
        return patterns
    
    def _extract_global_patterns(self, target_patterns: Dict, data: List[Dict]) -> List[Dict]:
        """Global kalıpları çıkar ve Türkçe açıklamalar oluştur"""
        insights = []
        
        # Viskozite pattern'i
        if 'quality_score' in target_patterns:
            qs_pattern = target_patterns['quality_score']
            if 'viscosity' in qs_pattern and qs_pattern['viscosity']['strength'] != 'weak':
                effect = 'artırır' if qs_pattern['viscosity']['effect'] == 'positive' else 'azaltır'
                insights.append({
                    'type': 'parameter_effect',
                    'title': 'Viskozite-Kalite İlişkisi',
                    'message': f'Viskozite artışı kalite skorunu {effect}.',
                    'confidence': abs(qs_pattern['viscosity']['correlation']),
                    'recommendation': 'Optimum viskozite aralığını test verilerinden belirleyin.'
                })
        
        # Kaplama kalınlığı pattern'i
        if 'corrosion_resistance' in target_patterns:
            cr_pattern = target_patterns['corrosion_resistance']
            if 'coating_thickness' in cr_pattern:
                corr = cr_pattern['coating_thickness']['correlation']
                if corr > 0.5:
                    insights.append({
                        'type': 'parameter_effect',
                        'title': 'Kaplama Kalınlığı-Korozyon Direnci',
                        'message': 'Kaplama kalınlığı arttıkça korozyon direnci belirgin şekilde artıyor.',
                        'confidence': corr,
                        'recommendation': 'Korozyon direnci kritik ise minimum 60µm kalınlık hedefleyin.'
                    })
        
        # pH pattern'i
        if 'adhesion' in target_patterns:
            ad_pattern = target_patterns['adhesion']
            if 'ph' in ad_pattern and ad_pattern['ph']['strength'] != 'weak':
                insights.append({
                    'type': 'parameter_effect',
                    'title': 'pH-Yapışma İlişkisi',
                    'message': 'pH değeri yapışma performansını etkiliyor.',
                    'confidence': abs(ad_pattern['ph']['correlation']),
                    'recommendation': 'Optimum yapışma için pH 7-9 aralığını hedefleyin.'
                })
        
        return insights
    
    def predict(self, features: Dict) -> Dict:
        """Global model ile tahmin yap"""
        if not self._model_data:
            return {'success': False, 'message': 'Global model henüz eğitilmedi'}
        
        try:
            import numpy as np
            
            models = self._model_data['models']
            scaler = self._model_data['scaler']
            
            X = [[
                self._get_numeric(features.get(f, 0)) or 0
                for f in self.feature_names
            ]]
            X = np.array(X)
            X_scaled = scaler.transform(X)
            
            predictions = {}
            for target_name, model in models.items():
                pred = model.predict(X_scaled)[0]
                predictions[target_name] = round(float(pred), 2)
            
            return {
                'success': True,
                'predictions': predictions,
                'model_type': 'global'
            }
            
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def get_status(self) -> Dict:
        """Global model durumunu döndür"""
        if not self._model_data:
            return {
                'trained': False,
                'samples': 0,
                'targets': [],
                'message': 'Global model henüz eğitilmedi'
            }
        
        results = self._model_data.get('results', {})
        
        return {
            'trained': True,
            'samples': self._model_data.get('samples_count', 0),
            'targets': list(self._model_data.get('models', {}).keys()),
            'trained_at': self._model_data.get('trained_at'),
            'avg_r2_score': results.get('avg_r2_score', 0),
            'learned_patterns': self._model_data.get('learned_patterns', [])
        }
    
    def get_insights(self) -> List[Dict]:
        """Öğrenilen içgörüleri döndür"""
        if not self._model_data:
            return []
        
        return self._model_data.get('learned_patterns', [])
    
    def _prepare_data(self, data: List[Dict]) -> Tuple[List, Dict]:
        """Eğitim verisini hazırla"""
        X = []
        y_dict = {target: [] for target in self.target_names}
        
        for row in data:
            features = []
            valid = True
            
            for feat in self.feature_names:
                val = self._get_numeric(row.get(feat))
                if val is not None:
                    features.append(val)
                else:
                    valid = False
                    break
            
            if valid:
                X.append(features)
                for target in self.target_names:
                    val = self._get_numeric(row.get(target))
                    y_dict[target].append(val if val is not None else float('nan'))
        
        return X, y_dict
    
    @staticmethod
    def _get_numeric(value) -> Optional[float]:
        """Değeri sayıya dönüştür"""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
