"""
Paint Formulation AI - Formulation Service
============================================
Formülasyon yönetimi, otomatik hesaplamalar ve anlık tahminler.

Özellikler:
- Formülasyon CRUD
- Otomatik özellik hesaplama (katı, P/B oranı, viskozite)
- Bileşen değişikliğinde anlık ML tahmini
- Maliyet hesaplama
"""

import logging
import json
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class FormulationService:
    """
    Formülasyon yönetim servisi.
    
    Bileşen bazlı reçete oluşturma, otomatik özellik türetme
    ve ML tahminleri ile entegrasyon.
    """
    
    def __init__(self, db_manager, recipe_transformer=None, ml_engine=None):
        """
        Args:
            db_manager: LocalDBManager instance
            recipe_transformer: EnhancedRecipeTransformer (opsiyonel)
            ml_engine: ML tahmin motoru (opsiyonel)
        """
        self.db = db_manager
        self._recipe_transformer = recipe_transformer
        self._ml_engine = ml_engine
        
        # Callbacks for real-time updates
        self._on_prediction_update: Optional[Callable[[Dict], None]] = None
    
    @property
    def recipe_transformer(self):
        """Lazy loading for recipe transformer"""
        if self._recipe_transformer is None:
            try:
                from src.ml_engine.enhanced_recipe_transformer import EnhancedRecipeTransformer
                self._recipe_transformer = EnhancedRecipeTransformer(self.db)
            except ImportError:
                logger.warning("EnhancedRecipeTransformer not available")
        return self._recipe_transformer
    
    def set_prediction_callback(self, callback: Callable[[Dict], None]):
        """Tahmin güncellemesi callback'i ayarla"""
        self._on_prediction_update = callback
    
    # =========================================================================
    # CRUD Operations
    # =========================================================================
    
    def create_formulation(self, project_id: int, code: str, name: str,
                           components: List[Dict]) -> int:
        """
        Yeni formülasyon oluştur.
        
        Args:
            project_id: Proje ID
            code: Formül kodu (unique)
            name: Formül adı
            components: [{'material_id': int, 'percentage': float}, ...]
            
        Returns:
            Yeni formülasyon ID
        """
        # Validate total percentage
        total = sum(c.get('percentage', 0) for c in components)
        if abs(total - 100) > 0.01:
            logger.warning(f"Component total is {total}%, not 100%")
        
        # Calculate properties automatically
        calculated = self.calculate_properties(components)
        
        # Create formulation in DB
        formulation_id = self.db.create_formulation({
            'project_id': project_id,
            'formula_code': code,
            'formula_name': name,
            'calculated_properties': json.dumps(calculated),
            'status': 'draft'
        })
        
        # Add components
        for comp in components:
            self.db.add_formulation_component(
                formulation_id=formulation_id,
                material_id=comp['material_id'],
                percentage=comp['percentage']
            )
        
        logger.info(f"Created formulation {code} with {len(components)} components")
        return formulation_id
    
    def update_formulation(self, formulation_id: int, 
                           components: List[Dict] = None,
                           **kwargs) -> bool:
        """
        Formülasyon güncelle.
        
        Args:
            formulation_id: Formülasyon ID
            components: Yeni bileşen listesi (opsiyonel)
            **kwargs: Diğer alanlar (code, name, status)
        """
        if components is not None:
            # Recalculate properties
            calculated = self.calculate_properties(components)
            kwargs['calculated_properties'] = json.dumps(calculated)
            
            # Update components
            self.db.delete_formulation_components(formulation_id)
            for comp in components:
                self.db.add_formulation_component(
                    formulation_id=formulation_id,
                    material_id=comp['material_id'],
                    percentage=comp['percentage']
                )
        
        return self.db.update_formulation(formulation_id, kwargs)
    
    def get_formulation(self, formulation_id: int) -> Optional[Dict]:
        """Formülasyon detaylarını getir"""
        formulation = self.db.get_formulation_with_components(formulation_id)
        
        if formulation and formulation.get('calculated_properties'):
            try:
                formulation['calculated_properties'] = json.loads(
                    formulation['calculated_properties']
                )
            except:
                pass
        
        return formulation
    
    def get_formulations_for_project(self, project_id: int) -> List[Dict]:
        """Projedeki tüm formülasyonları getir"""
        return self.db.get_formulations(project_id)
    
    def delete_formulation(self, formulation_id: int) -> bool:
        """Formülasyon sil"""
        self.db.delete_formulation_components(formulation_id)
        return self.db.delete_formulation(formulation_id)
    
    # =========================================================================
    # Automatic Calculations
    # =========================================================================
    
    def calculate_properties(self, components: List[Dict]) -> Dict:
        """
        Bileşenlerden otomatik özellik hesapla.
        
        Args:
            components: [{'material_id': int, 'percentage': float}, ...]
            
        Returns:
            {
                'estimated_solid': float,
                'estimated_density': float,
                'pb_ratio': float,
                'total_cost': float,
                'feature_vector': List[float]
            }
        """
        result = {
            'estimated_solid': 0.0,
            'estimated_density': 0.0,
            'pb_ratio': 0.0,
            'total_cost': 0.0,
            'total_percentage': 0.0,
            'component_count': len(components)
        }
        
        total_pct = 0.0
        weighted_solid = 0.0
        weighted_density = 0.0
        total_cost = 0.0
        
        pigment_pct = 0.0
        binder_pct = 0.0
        
        for comp in components:
            material = self.db.get_material(comp['material_id'])
            if not material:
                continue
            
            pct = comp.get('percentage', 0) / 100.0
            total_pct += comp.get('percentage', 0)
            
            # Weighted calculations
            solid = material.get('solid_content', 100) or 100
            density = material.get('density', 1.0) or 1.0
            price = material.get('unit_price', 0) or 0
            
            weighted_solid += solid * pct
            weighted_density += density * pct
            total_cost += price * pct  # per kg basis
            
            # P/B ratio calculation
            category = (material.get('category') or '').lower()
            if category == 'pigment':
                pigment_pct += pct * solid / 100
            elif category == 'resin':
                binder_pct += pct * solid / 100
        
        result['estimated_solid'] = round(weighted_solid, 1)
        result['estimated_density'] = round(weighted_density, 3)
        result['total_cost'] = round(total_cost, 2)
        result['total_percentage'] = round(total_pct, 1)
        
        # P/B ratio
        if binder_pct > 0:
            result['pb_ratio'] = round(pigment_pct / binder_pct, 2)
        
        # Generate feature vector using transformer
        if self.recipe_transformer:
            try:
                recipe = self._components_to_recipe(components)
                fp, mask, metadata = self.recipe_transformer.transform(recipe)
                result['feature_vector'] = fp
                result['confidence_mask'] = mask
                result.update(metadata)
            except Exception as e:
                logger.warning(f"Feature vector generation failed: {e}")
        
        return result
    
    def _components_to_recipe(self, components: List[Dict]) -> List[Dict]:
        """Bileşenleri recipe transformer formatına çevir"""
        recipe = []
        for comp in components:
            material = self.db.get_material(comp['material_id'])
            if material:
                recipe.append({
                    'material': material,
                    'percentage': comp.get('percentage', 0)
                })
        return recipe
    
    # =========================================================================
    # Real-time Predictions
    # =========================================================================
    
    def get_prediction(self, components: List[Dict], project_id: int = None) -> Dict:
        """
        Bileşenler için anlık ML tahmini.
        
        Args:
            components: Bileşen listesi
            project_id: Proje ID (proje modeli için)
            
        Returns:
            {
                'quality_score': float,
                'corrosion_resistance': float,
                'confidence': float,
                'suggestions': List[str]
            }
        """
        prediction = {
            'quality_score': None,
            'corrosion_resistance': None,
            'gloss': None,
            'confidence': 0.0,
            'suggestions': []
        }
        
        if not self._ml_engine:
            return prediction
        
        try:
            # Calculate feature vector
            calculated = self.calculate_properties(components)
            feature_vector = calculated.get('feature_vector')
            
            if feature_vector:
                # Get prediction from ML engine
                ml_result = self._ml_engine.predict(
                    feature_vector, 
                    project_id=project_id
                )
                prediction.update(ml_result)
                
        except Exception as e:
            logger.warning(f"Prediction failed: {e}")
            prediction['suggestions'].append("Tahmin için yeterli veri yok")
        
        return prediction
    
    def on_component_change(self, components: List[Dict], project_id: int = None):
        """
        Bileşen değişikliğinde çağrılır (real-time update için).
        
        UI bu metodu her bileşen değişikliğinde çağırır,
        callback üzerinden güncel tahmin döner.
        """
        if not self._on_prediction_update:
            return
        
        # Calculate and predict
        calculated = self.calculate_properties(components)
        prediction = self.get_prediction(components, project_id)
        
        # Merge results
        result = {
            **calculated,
            'prediction': prediction
        }
        
        # Notify UI
        self._on_prediction_update(result)
    
    # =========================================================================
    # Comparison & History
    # =========================================================================
    
    def compare_formulations(self, formulation_ids: List[int]) -> List[Dict]:
        """
        Birden fazla formülasyonu karşılaştır.
        
        Returns:
            Her formülasyon için özellik ve tahminler
        """
        results = []
        
        for fid in formulation_ids:
            formulation = self.get_formulation(fid)
            if formulation:
                results.append({
                    'id': fid,
                    'code': formulation.get('formula_code'),
                    'name': formulation.get('formula_name'),
                    'properties': formulation.get('calculated_properties', {}),
                    'component_count': len(formulation.get('components', []))
                })
        
        return results
    
    def get_similar_formulations(self, formulation_id: int, top_k: int = 5) -> List[Dict]:
        """
        Benzer formülasyonları bul (feature vector benzerliği).
        """
        formulation = self.get_formulation(formulation_id)
        if not formulation:
            return []
        
        current_vector = formulation.get('calculated_properties', {}).get('feature_vector')
        if not current_vector:
            return []
        
        # Get all formulations and compare
        # (Bu basit implementasyon - büyük veritabanları için optimize edilmeli)
        all_formulations = self.db.get_all_formulations()
        similarities = []
        
        for f in all_formulations:
            if f['id'] == formulation_id:
                continue
            
            props = f.get('calculated_properties')
            if props:
                try:
                    props = json.loads(props) if isinstance(props, str) else props
                    other_vector = props.get('feature_vector')
                    if other_vector:
                        similarity = self._cosine_similarity(current_vector, other_vector)
                        similarities.append({
                            'id': f['id'],
                            'code': f.get('formula_code'),
                            'similarity': similarity
                        })
                except:
                    pass
        
        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:top_k]
    
    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Cosine benzerlik hesapla"""
        if len(v1) != len(v2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
