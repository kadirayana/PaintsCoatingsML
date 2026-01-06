"""
Paint Formulation AI - Proje Bazlı ML Öğrenici
===============================================
Her proje için ayrı model yönetimi

Özellikler:
- Proje başına bağımsız model eğitimi
- Model durumu ve performans takibi
- Global modele katkı sağlama
"""

import os
import pickle
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import warnings

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class ProjectLearner:
    """
    Proje bazlı ML modeli yöneticisi
    
    Her proje kendi formülasyon özelliklerini öğrenir:
    - Epoksi projesi: Kimyasal dayanım ağırlıklı
    - Alkid projesi: Kuruma süresi, parlaklık ağırlıklı
    - Poliüretan projesi: Esneklik, aşınma direnci ağırlıklı
    """
    
    MIN_TRAINING_SAMPLES = 3
    
    def __init__(self, models_dir: str = 'assets/models/projects'):
        """
        Args:
            models_dir: Proje modellerinin kaydedileceği dizin
        """
        self.models_dir = models_dir
        os.makedirs(models_dir, exist_ok=True)
        
        # Proje modelleri cache
        self._project_models: Dict[int, Dict] = {}
        
        # Feature ve target tanımları
        from src.ml_engine.recipe_transformer import RecipeTransformer
        self.recipe_transformer = RecipeTransformer()
        
        # Temel özelliklere ek olarak reçete özelliklerini ekle
        self.base_features = ['viscosity', 'ph', 'density', 'coating_thickness']
        self.feature_names = self.base_features + self.recipe_transformer.get_feature_names()
        
        self.target_names = [
            'opacity', 'gloss', 'quality_score', 'total_cost',
            'corrosion_resistance', 'adhesion', 'hardness',
            'flexibility', 'chemical_resistance', 'uv_resistance', 'abrasion_resistance'
        ]
    
    def _get_model_path(self, project_id: int) -> str:
        """Proje model dosya yolunu döndür"""
        return os.path.join(self.models_dir, f'project_{project_id}_model.pkl')
    
    def load_project_model(self, project_id: int) -> Optional[Dict]:
        """Proje modelini yükle"""
        # Cache'de var mı?
        if project_id in self._project_models:
            return self._project_models[project_id]
        
        model_path = self._get_model_path(project_id)
        
        if os.path.exists(model_path):
            try:
                with open(model_path, 'rb') as f:
                    model_data = pickle.load(f)
                
                self._project_models[project_id] = model_data
                logger.info(f"Proje {project_id} modeli yüklendi")
                return model_data
            except Exception as e:
                logger.error(f"Proje {project_id} model yükleme hatası: {e}")
        
        return None
    
    def save_project_model(self, project_id: int, model_data: Dict) -> bool:
        """Proje modelini kaydet"""
        try:
            model_path = self._get_model_path(project_id)
            
            with open(model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            # Cache'i güncelle
            self._project_models[project_id] = model_data
            
            logger.info(f"Proje {project_id} modeli kaydedildi: {model_path}")
            return True
        except Exception as e:
            logger.error(f"Proje {project_id} model kayıt hatası: {e}")
            return False
    
    def train_project_model(self, project_id: int, training_data: List[Dict], 
                            project_name: str = None) -> Dict:
        """
        Proje için model eğit
        
        Args:
            project_id: Proje ID
            training_data: Eğitim verileri listesi
            project_name: Proje adı (opsiyonel)
            
        Returns:
            Eğitim sonuçları
        """
        logger.info(f"Proje {project_id} ({project_name}) eğitimi başlatıldı. Veri: {len(training_data)}")
        
        if len(training_data) < self.MIN_TRAINING_SAMPLES:
            return {
                'success': False,
                'message': f'Proje için en az {self.MIN_TRAINING_SAMPLES} kayıt gerekli. Mevcut: {len(training_data)}',
                'project_id': project_id,
                'samples': len(training_data)
            }
        
        try:
            import numpy as np
            from sklearn.ensemble import GradientBoostingRegressor
            from sklearn.preprocessing import StandardScaler
            from sklearn.model_selection import cross_val_score
            
            # Veriyi hazırla
            X, y_dict = self._prepare_data(training_data)
            
            if len(X) < self.MIN_TRAINING_SAMPLES:
                return {
                    'success': False,
                    'message': 'Yeterli geçerli veri yok',
                    'project_id': project_id,
                    'samples': len(X)
                }
            
            X = np.array(X)
            
            # Scaler
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            models = {}
            results = {
                'success': True,
                'project_id': project_id,
                'project_name': project_name,
                'targets': {},
                'samples': len(X),
                'trained_at': datetime.now().isoformat()
            }
            
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
                            r2_score = max(cv_scores.mean(), 0)  # Negatif skorları 0 yap
                        else:
                            r2_score = max(model.score(X_valid, y_valid), 0)
                        
                        models[target_name] = model
                        
                        results['targets'][target_name] = {
                            'r2_score': round(r2_score, 3),
                            'samples': int(valid_mask.sum()),
                            'feature_importance': dict(zip(
                                self.feature_names,
                                [round(float(x), 3) for x in model.feature_importances_]
                            ))
                        }
            
            # Model verisini kaydet
            model_data = {
                'models': models,
                'scaler': scaler,
                'feature_names': self.feature_names,
                'target_names': list(models.keys()),
                'results': results,
                'trained_at': datetime.now(),
                'project_id': project_id,
                'project_name': project_name,
                'samples_count': len(X)
            }
            
            self.save_project_model(project_id, model_data)
            
            # Ortalama R² hesapla
            if results['targets']:
                avg_r2 = sum(t['r2_score'] for t in results['targets'].values()) / len(results['targets'])
                results['avg_r2_score'] = round(avg_r2, 3)
            
            logger.info(f"Proje {project_id} eğitimi tamamlandı. Hedefler: {list(results['targets'].keys())}")
            return results
            
        except ImportError as e:
            return {'success': False, 'message': f'Kütüphane eksik: {e}', 'project_id': project_id}
        except Exception as e:
            logger.error(f"Proje {project_id} eğitim hatası: {e}")
            return {'success': False, 'message': str(e), 'project_id': project_id}
    
    def predict_for_project(self, project_id: int, features: Dict) -> Dict:
        """
        Proje modeli ile tahmin yap
        
        Args:
            project_id: Proje ID
            features: Giriş parametreleri
            
        Returns:
            Tahmin sonuçları
        """
        model_data = self.load_project_model(project_id)
        
        if not model_data:
            return {'success': False, 'message': 'Proje modeli bulunamadı. Önce eğitin.'}
        
        try:
            import numpy as np
            
            models = model_data['models']
            scaler = model_data['scaler']
            
            # Feature Enrichment (Reçete Girdisi Varsa)
            if 'formulation' in features and isinstance(features['formulation'], dict):
                recipe = features['formulation'].get('components', [])
                if recipe:
                    from src.ml_engine.recipe_transformer import RecipeTransformer
                    transformer = RecipeTransformer()
                    
                    recipe_features = list(transformer.transform(recipe))
                    recipe_feature_names = transformer.get_feature_names()
                    
                    # features sözlüğüne ekle
                    for name, val in zip(recipe_feature_names, recipe_features):
                        features[name] = val
            
            # Girdi hazırla
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
                'project_id': project_id,
                'predictions': predictions
            }
            
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def get_project_model_status(self, project_id: int) -> Dict:
        """Proje model durumunu döndür"""
        model_data = self.load_project_model(project_id)
        
        if not model_data:
            return {
                'trained': False,
                'project_id': project_id,
                'samples': 0,
                'targets': [],
                'message': 'Model henüz eğitilmedi'
            }
        
        results = model_data.get('results', {})
        
        return {
            'trained': True,
            'project_id': project_id,
            'project_name': model_data.get('project_name'),
            'samples': model_data.get('samples_count', 0),
            'targets': list(model_data.get('models', {}).keys()),
            'trained_at': model_data.get('trained_at'),
            'avg_r2_score': results.get('avg_r2_score', 0),
            'target_details': results.get('targets', {})
        }
    
    def get_all_project_statuses(self) -> List[Dict]:
        """Tüm proje modellerinin durumunu döndür"""
        statuses = []
        
        for filename in os.listdir(self.models_dir):
            if filename.startswith('project_') and filename.endswith('_model.pkl'):
                try:
                    project_id = int(filename.split('_')[1])
                    status = self.get_project_model_status(project_id)
                    statuses.append(status)
                except (ValueError, IndexError):
                    pass
        
        return statuses
    
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
                    # Eksik verileri 0.0 ile doldur
                    features.append(0.0)
            
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
