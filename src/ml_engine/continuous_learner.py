"""
Paint Formulation AI - Sürekli Öğrenen ML Motoru
=================================================
Formülasyon verileriyle sürekli öğrenen ve optimize eden ML sistemi

Özellikler:
- Otomatik model eğitimi (min 3 kayıt)
- Çoklu hedef optimizasyonu (kalite + maliyet)
- Değişken önem analizi
- Optimum parametre tahmini
"""

import os
import pickle
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import warnings

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class ContinuousLearner:
    """
    Sürekli öğrenen ML motoru
    
    Her yeni veri girişinde model güncellenir ve optimum değerler hesaplanır.
    """
    
    MIN_TRAINING_SAMPLES = 3  # Minimum eğitim verisi sayısı
    
    def __init__(self, model_dir: str = None):
        """
        Args:
            model_dir: Model dosyalarının kaydedileceği dizin
        """
        self.model_dir = model_dir or 'assets/models'
        self.models = {}  # Hedef değişken -> model
        self.scalers = {}  # Hedef değişken -> scaler
        self.feature_names = []
        self.target_names = []
        self.training_history = []
        self.last_training_date = None
        self.training_sample_count = 0  # Eğitim verisi sayısı (uncertainty için)
        
        # Uncertainty Estimator (lazy loading)
        self._uncertainty_estimator = None
        
        # Modelleri yükle (varsa)
        self._load_models()
    
    def _load_models(self):
        """Kayıtlı modelleri yükle"""
        model_path = os.path.join(self.model_dir, 'continuous_model.pkl')
        
        if os.path.exists(model_path):
            try:
                with open(model_path, 'rb') as f:
                    data = pickle.load(f)
                
                self.models = data.get('models', {})
                self.scalers = data.get('scalers', {})
                self.feature_names = data.get('feature_names', [])
                self.target_names = data.get('target_names', [])
                self.training_history = data.get('training_history', [])
                
                logger.info(f"Modeller yüklendi: {len(self.models)} hedef")
            except Exception as e:
                logger.error(f"Model yükleme hatası: {e}")
    
    def _save_models(self):
        """Modelleri kaydet"""
        os.makedirs(self.model_dir, exist_ok=True)
        model_path = os.path.join(self.model_dir, 'continuous_model.pkl')
        
        try:
            data = {
                'models': self.models,
                'scalers': self.scalers,
                'feature_names': self.feature_names,
                'target_names': self.target_names,
                'training_history': self.training_history,
                'last_training': datetime.now().isoformat()
            }
            
            with open(model_path, 'wb') as f:
                pickle.dump(data, f)
            
            logger.info("Modeller kaydedildi")
        except Exception as e:
            logger.error(f"Model kaydetme hatası: {e}")
    
    def train(self, data: List[Dict]) -> Dict:
        """
        Model eğitimi
        
        Args:
            data: Formülasyon verileri listesi
            
        Returns:
            Eğitim sonuçları
        """
        logger.info(f"ML Eğitimi Başlatıldı. Gelen veri sayısı: {len(data)}")
        if data:
            logger.info(f"Örnek veri (ID: {data[0].get('id')}): {list(data[0].keys())}")

        if len(data) < self.MIN_TRAINING_SAMPLES:
            return {
                'success': False,
                'message': f'Eğitim için en az {self.MIN_TRAINING_SAMPLES} kayıt gerekli. Mevcut: {len(data)}',
                'samples': len(data)
            }
        
        try:
            import numpy as np
            from sklearn.ensemble import GradientBoostingRegressor
            from sklearn.preprocessing import StandardScaler
            from sklearn.model_selection import cross_val_score
            
            # Özellik ve hedef sütunları belirle
            from src.ml_engine.recipe_transformer import RecipeTransformer
            recipe_transformer = RecipeTransformer()
            
            # Temel özellikler + Reçete özellikleri
            base_features = ['viscosity', 'ph', 'density', 'coating_thickness']
            self.feature_names = base_features + recipe_transformer.get_feature_names()
            
            self.target_names = [
                'opacity', 'gloss', 'quality_score', 'total_cost',
                'corrosion_resistance', 'adhesion', 'hardness', 
                'flexibility', 'chemical_resistance', 'uv_resistance', 'abrasion_resistance'
            ]
            
            # Özel test metodlarını yükle ve hedeflere ekle
            custom_methods = self._load_custom_methods()
            for method_key in custom_methods:
                if method_key not in self.target_names:
                    self.target_names.append(method_key)
            
            # Veriyi hazırla
            X, y_dict = self._prepare_training_data(data)
            
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
            self.scalers['main'] = scaler
            
            results = {'success': True, 'targets': {}, 'samples': len(X)}
            
            # Her hedef için model eğit
            for target_name in self.target_names:
                if target_name in y_dict and len(y_dict[target_name]) == len(X):
                    y = np.array(y_dict[target_name])
                    
                    # NaN olmayan değerler
                    valid_mask = ~np.isnan(y)
                    if valid_mask.sum() >= self.MIN_TRAINING_SAMPLES:
                        X_valid = X_scaled[valid_mask]
                        y_valid = y[valid_mask]
                        
                        # Model eğit
                        model = GradientBoostingRegressor(
                            n_estimators=50,
                            max_depth=3,
                            learning_rate=0.1,
                            random_state=42
                        )
                        model.fit(X_valid, y_valid)
                        
                        # Cross-validation skoru
                        if len(X_valid) >= 3:
                            cv_folds = min(3, len(X_valid))
                            cv_scores = cross_val_score(model, X_valid, y_valid, cv=cv_folds, scoring='r2')
                            r2_score = cv_scores.mean()
                        else:
                            r2_score = model.score(X_valid, y_valid)
                        
                        self.models[target_name] = model
                        
                        results['targets'][target_name] = {
                            'r2_score': round(r2_score, 3),
                            'samples': int(valid_mask.sum()),
                            'feature_importance': dict(zip(
                                self.feature_names,
                                [round(x, 3) for x in model.feature_importances_]
                            ))
                        }
            
            # E\u011fitim ge\u00e7mi\u015fine ekle
            self.training_history.append({
                'date': datetime.now().isoformat(),
                'samples': len(X),
                'targets': list(results['targets'].keys())
            })
            
            self.last_training_date = datetime.now()
            self.training_sample_count = len(X)  # Uncertainty i\u00e7in sakla
            
            # Son eğitim sonuçlarını kaydet (get_model_status için)
            self._last_training_results = results.get('targets', {})
            
            # Modelleri kaydet
            self._save_models()
            
            return results
            
        except ImportError as e:
            return {'success': False, 'message': f'Kütüphane eksik: {e}'}
        except Exception as e:
            logger.error(f"Eğitim hatası: {e}")
            return {'success': False, 'message': str(e)}
    
    def _prepare_training_data(self, data: List[Dict]) -> Tuple[List, Dict]:
        """Eğitim verisini hazırla"""
        X = []
        y_dict = {target: [] for target in self.target_names}
        
        for i, row in enumerate(data):
            # Özellikleri al
            features = []
            valid = True
            for feat in self.feature_names:
                val = self._get_numeric_value(row.get(feat))
                if val is not None:
                    features.append(val)
                else:
                    # Eksik özellik (özellikle yeni reçete özellikleri) için 0.0 kullan
                    # Bu sayede eski veri setleri ile de eğitim yapılabilir (Backward Compatibility)
                    features.append(0.0)
            
            # Her halükarda ekle (yeterli veri olması için)
            X.append(features)
                
            # Hedefleri al
            for target in self.target_names:
                val = self._get_numeric_value(row.get(target))
                y_dict[target].append(val if val is not None else float('nan'))
        
        return X, y_dict
        
        return X, y_dict
    
    def predict(self, features: Dict) -> Dict:
        """
        Tahmin yap
        
        Args:
            features: Girdi parametreleri
            
        Returns:
            Tahmin sonuçları
        """
        if not self.models:
            return {'success': False, 'message': 'Model henüz eğitilmedi'}
        
        try:
            import numpy as np
            
            # Feature Enrichment (Reçete Girdisi Varsa)
            if 'formulation' in features and isinstance(features['formulation'], dict):
                recipe = features['formulation'].get('components', [])
                if recipe:
                    from src.ml_engine.recipe_transformer import RecipeTransformer
                    transformer = RecipeTransformer()
                    
                    recipe_features = list(transformer.transform(recipe))
                    recipe_feature_names = transformer.get_feature_names()
                    
                    # features sözlüğüne ekle (mevcut değerleri ezmemek için kontrol edilebilir ama ML tahmini için reçetedeki değerler esastır)
                    for name, val in zip(recipe_feature_names, recipe_features):
                        features[name] = val
            
            # Girdi hazırla
            X = [[
                self._get_numeric_value(features.get(f, 0)) or 0
                for f in self.feature_names
            ]]
            X = np.array(X)
            
            # Ölçekle
            if 'main' in self.scalers:
                X = self.scalers['main'].transform(X)
            
            predictions = {}
            confidence_info = {}
            
            # Uncertainty Estimator lazy loading
            if self._uncertainty_estimator is None:
                from src.ml_engine.uncertainty_estimator import UncertaintyEstimator
                self._uncertainty_estimator = UncertaintyEstimator()
            
            for target_name, model in self.models.items():
                pred = model.predict(X)[0]
                predictions[target_name] = round(pred, 2)
                
                # G\u00fcven tahmini yap
                try:
                    conf_result = self._uncertainty_estimator.estimate_confidence(
                        pred, model, X, self.training_sample_count
                    )
                    confidence_info[target_name] = {
                        'confidence': conf_result.confidence_percent,
                        'lower': conf_result.lower_bound,
                        'upper': conf_result.upper_bound,
                        'is_cold_start': conf_result.is_cold_start
                    }
                except Exception:
                    confidence_info[target_name] = {'confidence': 0, 'is_cold_start': True}
            
            # Genel g\u00fcven
            overall_confidence = self._uncertainty_estimator.get_overall_confidence(
                {k: self._uncertainty_estimator.estimate_confidence(
                    predictions[k], self.models[k], X, self.training_sample_count
                ) for k in predictions}
            ) if predictions else 0
            
            confidence_message = self._uncertainty_estimator.get_confidence_message(
                overall_confidence, 
                self.training_sample_count < 10
            )
            
            return {
                'success': True, 
                'predictions': predictions,
                'confidence': {
                    'overall': overall_confidence,
                    'message': confidence_message,
                    'sample_count': self.training_sample_count,
                    'details': confidence_info
                }
            }
            
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def optimize_multi_objective(
        self,
        objectives: Dict[str, Dict],
        constraints: Dict = None,
        material_costs: Dict = None
    ) -> Dict:
        """
        Çoklu hedef optimizasyonu
        
        Args:
            objectives: Hedefler ve ağırlıkları
                {'opacity': {'target': 95, 'weight': 0.4, 'direction': 'max'},
                 'total_cost': {'target': 100, 'weight': 0.6, 'direction': 'min'}}
            constraints: Parametre sınırları
                {'viscosity': {'min': 1000, 'max': 5000}}
            material_costs: hammadde fiyatları
            
        Returns:
            Optimum parametreler
        """
        if not self.models:
            return {'success': False, 'message': 'Model henüz eğitilmedi'}
        
        try:
            import numpy as np
            
            # Varsayılan sınırlar
            default_constraints = {
                'viscosity': {'min': 500, 'max': 8000},
                'ph': {'min': 6, 'max': 10},
                'density': {'min': 0.8, 'max': 1.5},
                'coating_thickness': {'min': 10, 'max': 500}
            }
            
            if constraints:
                for k, v in constraints.items():
                    if k in default_constraints:
                        default_constraints[k].update(v)
            
            constraints = default_constraints
            
            # Grid search ile optimum bul (Optimized)
            n_points = 10  # Reduced from 20 for speed
            
            # Create parameter grids
            param_grids = {k: np.linspace(v['min'], v['max'], n_points) 
                          for k, v in constraints.items() if k in self.feature_names}
            
            # Generate all combinations using meshgrid
            grid_arrays = [param_grids.get(f, np.array([1.0])) for f in self.feature_names]
            mesh = np.meshgrid(*grid_arrays, indexing='ij')
            X_grid = np.column_stack([m.ravel() for m in mesh])
            
            # Batch prediction
            if 'main' in self.scalers:
                X_scaled = self.scalers['main'].transform(X_grid)
            else:
                X_scaled = X_grid
            
            # Predict all targets at once
            all_predictions = {}
            for target_name, model in self.models.items():
                all_predictions[target_name] = model.predict(X_scaled)
            
            # Calculate scores for all combinations
            n_samples = X_grid.shape[0]
            scores = np.zeros(n_samples)
            
            total_weight = sum(obj.get('weight', 1) for obj in objectives.values())
            
            for target, obj in objectives.items():
                if target in all_predictions:
                    pred_values = all_predictions[target]
                    target_value = obj.get('target', 100)
                    weight = obj.get('weight', 1) / total_weight
                    direction = obj.get('direction', 'max')
                    
                    if direction == 'max':
                        normalized = np.minimum(pred_values / max(target_value, 0.01), 1.5)
                    elif direction == 'min':
                        normalized = np.minimum(target_value / np.maximum(pred_values, 0.01), 1.5)
                    else:
                        diff = np.abs(pred_values - target_value)
                        normalized = 1 / (1 + diff / max(target_value, 1))
                    
                    scores += weight * normalized
            
            # Find best
            best_idx = np.argmax(scores)
            best_x = X_grid[best_idx]
            
            best_params = dict(zip(self.feature_names, best_x))
            best_predictions = {t: float(all_predictions[t][best_idx]) for t in all_predictions}
            best_score = scores[best_idx]
            
            return {
                'success': True,
                'optimal_params': {k: round(v, 2) for k, v in best_params.items()},
                'predicted_results': {k: round(v, 2) for k, v in best_predictions.items()},
                'optimization_score': round(float(best_score), 3),
                'objectives_met': self._check_objectives_met(best_predictions, objectives)
            }
                
        except Exception as e:
            logger.error(f"Optimizasyon hatası: {e}")
            return {'success': False, 'message': str(e)}
    
    def _calculate_multi_objective_score(self, predictions: Dict, objectives: Dict) -> float:
        """Çoklu hedef skoru hesapla"""
        score = 0
        total_weight = sum(obj.get('weight', 1) for obj in objectives.values())
        
        for target, obj in objectives.items():
            if target in predictions:
                pred_value = predictions[target]
                target_value = obj.get('target', pred_value)
                weight = obj.get('weight', 1) / total_weight
                direction = obj.get('direction', 'max')
                
                if direction == 'max':
                    # Hedefe yakınlık (yüksek iyi)
                    normalized = min(pred_value / target_value, 1.5) if target_value > 0 else 0
                elif direction == 'min':
                    # Hedefe yakınlık (düşük iyi)
                    normalized = min(target_value / pred_value, 1.5) if pred_value > 0 else 0
                else:
                    # Hedefe eşitlik
                    diff = abs(pred_value - target_value)
                    normalized = 1 / (1 + diff / max(target_value, 1))
                
                score += weight * normalized
        
        return score
    
    def _check_objectives_met(self, predictions: Dict, objectives: Dict) -> Dict:
        """Hedeflerin karşılanıp karşılanmadığını kontrol et"""
        results = {}
        
        for target, obj in objectives.items():
            if target in predictions:
                pred_value = predictions[target]
                target_value = obj.get('target', pred_value)
                direction = obj.get('direction', 'max')
                
                if direction == 'max':
                    met = pred_value >= target_value * 0.95  # %5 tolerans
                elif direction == 'min':
                    met = pred_value <= target_value * 1.05  # %5 tolerans
                else:
                    met = abs(pred_value - target_value) / max(target_value, 1) < 0.1
                
                results[target] = {
                    'target': target_value,
                    'predicted': round(pred_value, 2),
                    'met': met
                }
        
        return results
    
    def _calculate_cost(self, params: Dict, material_costs: Dict) -> float:
        """Formülasyon maliyetini hesapla"""
        total = 0
        
        # Basit maliyet modeli (gerçek uygulamada formüle göre hesaplanmalı)
        # Viskozite yüksekse koyulaştırıcı maliyeti
        if 'thickener' in material_costs:
            visc_factor = params.get('viscosity', 2000) / 2000
            total += material_costs['thickener'] * visc_factor
        
        # Yoğunluk yüksekse dolgu maliyeti  
        if 'filler' in material_costs:
            density_factor = params.get('density', 1.1) / 1.1
            total += material_costs['filler'] * density_factor
        
        # Genel hammadde maliyetleri
        for material, cost in material_costs.items():
            if material not in ['thickener', 'filler']:
                total += cost
        
        return round(total, 2)
    
    def get_feature_importance(self) -> Dict:
        """Tüm hedefler için özellik önemlerini al"""
        importance = {}
        
        for target_name, model in self.models.items():
            if hasattr(model, 'feature_importances_'):
                importance[target_name] = dict(zip(
                    self.feature_names,
                    [round(x, 3) for x in model.feature_importances_]
                ))
        
        return importance
    
    def get_model_status(self) -> Dict:
        """Model durumunu ve performans metriklerini döndür"""
        status = {
            'trained': len(self.models) > 0,
            'models_count': len(self.models),
            'targets': list(self.models.keys()),
            'features': self.feature_names,
            'last_training': self.last_training_date.isoformat() if self.last_training_date else None,
            'training_count': len(self.training_history),
            'min_samples_required': self.MIN_TRAINING_SAMPLES
        }
        
        # Son eğitim detaylarını ekle
        if self.training_history:
            last_training = self.training_history[-1]
            status['last_training_details'] = {
                'date': last_training.get('date'),
                'samples': last_training.get('samples'),
                'targets_trained': last_training.get('targets', [])
            }
        
        # Model metriklerini ekle (eğer kaydedildiyse)
        if hasattr(self, '_last_training_results'):
            status['performance_metrics'] = self._last_training_results
        
        return status
    
    def suggest_improvements(self, current_results: Dict, target_improvements: Dict) -> List[Dict]:
        """
        İyileştirme önerileri sun
        
        Args:
            current_results: Mevcut sonuçlar
            target_improvements: Hedef iyileştirmeler
            
        Returns:
            Öneri listesi
        """
        suggestions = []
        importance = self.get_feature_importance()
        
        for target, improvement in target_improvements.items():
            if target in importance:
                # En etkili parametreyi bul
                target_importance = importance[target]
                sorted_params = sorted(target_importance.items(), key=lambda x: x[1], reverse=True)
                
                direction = improvement.get('direction', 'increase')
                
                if sorted_params:
                    top_param, top_importance = sorted_params[0]
                    
                    suggestions.append({
                        'target': target,
                        'most_effective_param': top_param,
                        'importance': top_importance,
                        'suggestion': self._generate_suggestion(top_param, direction, improvement)
                    })
        
        return suggestions
    
    def _generate_suggestion(self, param: str, direction: str, improvement: Dict) -> str:
        """Öneri metni oluştur"""
        param_names = {
            'viscosity': 'Viskozite',
            'ph': 'pH',
            'density': 'Yoğunluk'
        }
        
        param_tr = param_names.get(param, param)
        
        if direction == 'increase':
            return f"{param_tr} değerini artırmayı deneyin"
        elif direction == 'decrease':
            return f"{param_tr} değerini azaltmayı deneyin"
        else:
            target_val = improvement.get('target_value', 'optimum')
            return f"{param_tr} değerini {target_val} civarına ayarlayın"
    
    @staticmethod
    def _get_numeric_value(value) -> Optional[float]:
        """Değeri sayıya dönüştür"""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _load_custom_methods(self) -> list:
        """Özel test metodlarını JSON dosyasından yükle"""
        import json
        
        # data_storage klasöründeki custom_test_methods.json'u bul
        possible_paths = [
            os.path.join(os.path.dirname(self.model_dir), '..', 'data_storage', 'custom_test_methods.json'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                        'data_storage', 'custom_test_methods.json'),
        ]
        
        for config_file in possible_paths:
            config_file = os.path.abspath(config_file)
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        methods = json.load(f)
                    
                    logger.info(f"Özel test metodları yüklendi: {list(methods.keys())}")
                    return list(methods.keys())
                except Exception as e:
                    logger.warning(f"Özel metodlar yüklenemedi: {e}")
        
        return []

