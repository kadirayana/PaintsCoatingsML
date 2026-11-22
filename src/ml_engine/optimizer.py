"""
Paint Formulation AI - İleri Seviye Optimizasyon Motoru (Reverse Model)
===================================================================
Genetik Algoritma kullanarak hedeflenen özelliklelere sahip en iyi reçeteyi bulur.

Yöntem:
- İleri Yönlü Model (ContinuousLearner) kullanılarak aday reçeteler değerlendirilir.
- Evrimsel strateji ile reçeteler iyileştirilir.
- Kimyasal kısıtlar (PVC, pH, hammadde limitleri) ile geçersiz reçeteler engellenir.
"""

import random
import numpy as np
from typing import List, Dict
import logging
from copy import deepcopy

from src.ml_engine.continuous_learner import ContinuousLearner
from src.ml_engine.recipe_transformer import RecipeTransformer
from src.core.chemical_constraints import ChemicalValidator

logger = logging.getLogger(__name__)

class MLOptimizer:
    """
    Genetik Algoritma tabanlı reçete optimizasyon motoru.
    Hedef özellikleri (Gloss, Korozyon vb.) alıp uygun reçeteyi üretir.
    """
    
    def __init__(self, learner: ContinuousLearner, db_manager):
        self.learner = learner
        self.db_manager = db_manager
        self.transformer = RecipeTransformer()
        self.validator = ChemicalValidator(db_manager)  # Kimyasal kısıt kontrolü
        
        # GA Parametreleri
        self.population_size = 50
        self.generations = 30
        self.mutation_rate = 0.1
        self.elite_size = 5
        
        # Hedef boya tipi (PVC kontrolü için)
        self.target_type = None
        
    def optimize(self, targets: Dict[str, float], project_id: int = None, constraints: Dict = None) -> Dict:
        """
        Hedeflere ulaşmak için reçete optimizasyonu yapar.

        Args:
            targets: Hedef özellikler, örn. {'gloss': 85, 'total_cost': 50}
            project_id: Aktif proje (bilgi amaçlı)
            constraints: {'scope': 'project'|'global', 'max_cost': ..., 'prohibited_materials': [...]}

        Returns:
            {'success': True, 'suggestions': [{'score', 'recipe', 'prediction'}, ...]}
            veya {'success': False, 'message': ...}
        """
        self.scope = constraints.get('scope', 'global') if constraints else 'global'
        self.project_constraints = constraints if self.scope == 'project' else {}

        if not targets:
            return {'success': False, 'message': 'En az bir hedef seçmelisiniz.'}
        if not self.learner.models:
            return {'success': False, 'message': 'ML modeli henüz eğitilmedi.'}

        # Model tarafından tahmin edilebilen (veya reçeteden hesaplanabilen) hedefler
        supported = set(self.learner.models) | {'total_cost'}
        if not supported & set(targets):
            return {
                'success': False,
                'message': 'Seçilen hedeflerin hiçbiri için eğitilmiş model yok. '
                           f'Kullanılabilir hedefler: {", ".join(sorted(supported))}'
            }

        materials = [m for m in (self.db_manager.get_all_materials() or []) if m.get('name')]
        if len(materials) < 2:
            return {'success': False, 'message': 'Optimizasyon için en az 2 hammadde tanımlı olmalı.'}

        population = self._initialize_population(materials)

        for gen in range(self.generations):
            scored_population = sorted(
                ((self._calculate_fitness(recipe, targets), recipe) for recipe in population),
                key=lambda x: x[0]
            )
            # Elitizm: en iyiler doğrudan aktarılır
            next_population = [deepcopy(r) for _, r in scored_population[:self.elite_size]]
            while len(next_population) < self.population_size:
                parent1 = self._tournament_selection(scored_population)
                parent2 = self._tournament_selection(scored_population)
                child = self._crossover(parent1, parent2)
                self._mutate(child, materials)
                child = self._merge_duplicates(child)
                if len(child) >= 2:  # Tek bileşenli "reçete" anlamsız
                    next_population.append(child)
            population = next_population

        final = sorted(
            ((self._calculate_fitness(recipe, targets), recipe) for recipe in population),
            key=lambda x: x[0]
        )

        suggestions = []
        seen = set()
        for score, recipe in final:
            recipe = self.validator.normalize_recipe(recipe)
            key = self._recipe_to_key(recipe)
            if key in seen:
                continue
            seen.add(key)
            suggestions.append({
                'score': round(score, 4),
                'recipe': recipe,
                'prediction': self._predict_recipe(recipe)
            })
            if len(suggestions) >= 3:
                break

        logger.info(f"Optimizasyon tamamlandı: proje={project_id}, en iyi skor={suggestions[0]['score']}")
        return {'success': True, 'suggestions': suggestions}

    def _initialize_population(self, materials: List[Dict]) -> List[List[Dict]]:
        """Rastgele hammadde seçimi ve oranlarıyla başlangıç popülasyonu oluştur"""
        population = []
        for _ in range(self.population_size):
            k = min(len(materials), random.randint(3, 6))
            chosen = random.sample(materials, k)
            recipe = [self._create_component(m, random.uniform(1, 50)) for m in chosen]
            population.append(self.validator.normalize_recipe(recipe))
        return population

    def _create_component(self, material: Dict, amount: float) -> Dict:
        """Hammadde kaydından reçete bileşeni oluştur (fiziksel özellikler korunur)"""
        comp = dict(material)
        comp['material_id'] = material.get('id')
        comp['code'] = material.get('code') or ''
        comp['material_category'] = material.get('category')
        comp['price'] = material.get('unit_price') or 0
        comp['amount'] = amount
        comp['percentage'] = amount
        return comp

    @staticmethod
    def _merge_duplicates(recipe: List[Dict]) -> List[Dict]:
        """Çaprazlama/mutasyonla aynı hammadde birden fazla kez gelirse miktarlarını birleştir"""
        merged = {}
        for comp in recipe:
            key = comp.get('material_id') or comp.get('name')
            if key in merged:
                merged[key]['amount'] += comp.get('amount', 0)
                merged[key]['percentage'] = merged[key]['amount']
            else:
                merged[key] = comp
        return list(merged.values())

    @staticmethod
    def _recipe_cost(recipe: List[Dict]) -> float:
        """Birim maliyet (TL/kg): miktarlar yüzde olarak kabul edilir"""
        return sum((c.get('amount', 0) or 0) * (c.get('price', 0) or 0) for c in recipe) / 100

    def _calculate_fitness(self, recipe, targets):
        """Fitness fonksiyonu: Hedefe yakınlık (Loss) + Kimyasal Penalty + Proje Penalty"""
        if not recipe: return 9999
        
        # 0. Normalize et
        recipe = self.validator.normalize_recipe(recipe)
        
        # 1. Kimyasal Kısıt Kontrolü
        chemical_penalty = self.validator.get_penalty_score(recipe, self.target_type)
        
        # 2. İleri Yönlü Tahmin
        prediction = self._predict_recipe(recipe)
        
        # 3. Hedef Kaybı
        target_loss = self._calculate_loss(prediction, targets)
        
        # 4. Proje Kısıtı Cezası (Cost & Prohibited)
        project_penalty = 0
        if self.project_constraints:
            # Cost Penalty
            max_cost = self.project_constraints.get('max_cost')
            if max_cost:
                current_cost = self._recipe_cost(recipe)
                if current_cost > max_cost:
                    # Exponential penalty for exceeding cost
                    project_penalty += (current_cost - max_cost) * 10 
            
            # Prohibited Material Penalty
            prohibited = self.project_constraints.get('prohibited_materials', [])
            for c in recipe:
                if (c.get('name') or '').lower() in prohibited or (c.get('code') or '').lower() in prohibited:
                    project_penalty += 500 # Huge penalty
        
        return target_loss + chemical_penalty + project_penalty

    def _predict_recipe(self, recipe):
        """Forward model ile tahmin yap"""
        # RecipeTransformer formatına uygun parametre hazırla
        params = {
            'viscosity': 0, # Bilinmiyor, 0 veriyoruz (veya model ortalamalarla doldurur)
            'ph': 7,
            'formulation': {'components': recipe}
        }
        
        result = self.learner.predict(params)
        if not result.get('success'):
            # Sessizce boş tahminle devam etmek optimizasyonu anlamsız kılar
            raise RuntimeError(f"Model tahmini başarısız: {result.get('message')}")
        prediction = dict(result.get('predictions', {}))
        # Maliyet modelden değil, doğrudan reçeteden hesaplanabilir
        prediction.setdefault('total_cost', round(self._recipe_cost(recipe), 2))
        return prediction

    def _calculate_loss(self, prediction, targets):
        """Hedeflerden sapmayı hesapla"""
        loss = 0
        weights = 0
        
        for target_key, target_val in targets.items():
            if target_key in prediction:
                pred_val = prediction[target_key]
                # Normalize edilmiş fark karesi (Yüzde hata)
                if target_val != 0:
                    diff = ((pred_val - target_val) / target_val) ** 2
                else:
                    diff = (pred_val - target_val) ** 2
                
                loss += diff
                weights += 1

        return loss / weights if weights > 0 else 9999

    def _tournament_selection(self, scored_population, k=3):
        """Turnuva seçimi"""
        tournament = random.sample(scored_population, k)
        return min(tournament, key=lambda x: x[0])[1] # En düşük skor (en iyi)

    def _crossover(self, parent1, parent2):
        """Bileşen bazlı çaprazlama"""
        # Basit strateji: İki reçeteyi birleştir ve normalize et
        child = []
        
        # Parent 1'den yarısını al
        k1 = len(parent1) // 2
        child.extend(deepcopy(parent1[:k1]))
        
        # Parent 2'den kalanları al (Çakışma kontrolü yapılabilir)
        k2 = len(parent2) // 2
        child.extend(deepcopy(parent2[k2:]))
        
        # Bazen çok uzun veya kısa olabilir, düzenle
        if len(child) > 6: child = child[:6]
        
        # Normalizasyon
        total = sum(c['amount'] for c in child)
        if total > 0:
            factor = 100 / total
            for c in child:
                c['amount'] *= factor
                c['percentage'] = c['amount']
                
        return child

    def _mutate(self, recipe, available_materials):
        """Mutasyon: Oran değiştir veya hammadde değiştir"""
        if not recipe: return
        
        if random.random() < self.mutation_rate:
            # Tip 1: Oran Değişimi
            idx = random.randrange(len(recipe))
            change = random.uniform(0.8, 1.2)
            recipe[idx]['amount'] *= change
            
            # Tekrar normalize et
            total = sum(c['amount'] for c in recipe)
            if total > 0:
                for c in recipe:
                    c['amount'] = (c['amount'] / total) * 100
                    c['percentage'] = c['amount']
                    
        if random.random() < (self.mutation_rate / 2):
            # Tip 2: hammadde Ekle/Çıkar
            if len(recipe) < 6:
                # Ekle
                new_mat = random.choice(available_materials)
                recipe.append(self._create_component(new_mat, 5.0)) # %5 ekle
            elif len(recipe) > 2:
                # Çıkar
                recipe.pop(random.randrange(len(recipe)))
                
            # Normalizasyon
            total = sum(c['amount'] for c in recipe)
            if total > 0:
                for c in recipe:
                    c['amount'] = (c['amount'] / total) * 100
                    c['percentage'] = c['amount']

    def _recipe_to_key(self, recipe):
        """Reçete için benzersiz anahtar (Önerileri filtrelemek için)"""
        # Bileşen isimlerini sıralayıp string yap
        comps = sorted([f"{c.get('name', 'uk')}:{int(c.get('amount',0))}" for c in recipe])
        return "|".join(comps)
