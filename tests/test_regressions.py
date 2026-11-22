"""
İnceleme sırasında bulunan hatalar için regresyon testleri
"""
import random

from src.ml_engine.continuous_learner import ContinuousLearner


def test_fresh_db_legacy_trial_queries(temp_db):
    """Yeni kurulan veritabanında legacy formulation_id sütunu bulunmalı"""
    temp_db.save_trial({'gloss': 80, 'viscosity': 1000})

    trials = temp_db.get_recent_trials(10)

    assert len(trials) == 1
    assert trials[0]['gloss'] == 80


def test_learner_persists_training_sample_count(tmp_path):
    random.seed(0)
    data = [
        {'viscosity': random.uniform(500, 1500), 'ph': 8, 'density': 1.2,
         'coating_thickness': 50, 'gloss': random.uniform(40, 90)}
        for _ in range(6)
    ]
    learner = ContinuousLearner(str(tmp_path))
    assert learner.train(data)['success']

    reloaded = ContinuousLearner(str(tmp_path))

    assert reloaded.training_sample_count == 6
    assert 'gloss' in reloaded.models


def test_recipe_transformer_handles_null_material_properties():
    """DB'den gelen NULL fiziksel özellikler çökme yaratmamalı"""
    from src.ml_engine.recipe_transformer import RecipeTransformer
    recipe = [
        {'name': 'Reçine', 'material_category': 'binder', 'amount': 50, 'percentage': None,
         'oh_value': None, 'molecular_weight': None, 'unit_price': None},
        {'name': 'Su', 'material_category': None, 'amount': 50, 'solid_content': None},
    ]

    features = RecipeTransformer().transform(recipe)

    assert len(features) == RecipeTransformer().feature_count


def test_fresh_db_get_formulation_materials(temp_db):
    """Karşılaştırma paneli bu sorguyu kullanıyor; yeni DB'de çökmemeli"""
    assert temp_db.get_formulation_materials(1) == []
