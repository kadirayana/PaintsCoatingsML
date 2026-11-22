"""
İnceleme sırasında bulunan hatalar için regresyon testleri
"""
import random

from src.ml_engine.continuous_learner import ContinuousLearner


def test_fresh_db_recent_trials(temp_db, sample_project):
    """Yeni kurulan veritabanında son varyasyon sorgusu çalışmalı (legacy sütun hatası olmamalı)"""
    project_id = temp_db.create_project(sample_project)
    temp_db.create_formulation(project_id, {'formula_code': 'F-1', 'formula_name': 'Konsept'})

    trials = temp_db.get_recent_trials(10)

    assert [t['formula_code'] for t in trials] == ['F-1']


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


def test_training_data_includes_recipe_features(temp_db, sample_project):
    """ML eğitim satırları reçeteden türetilen özellikleri taşımalı"""
    project_id = temp_db.create_project(sample_project)
    temp_db.add_material({'name': 'Reçine', 'code': 'R1', 'category': 'binder', 'unit_price': 10})
    temp_db.add_material({'name': 'Su', 'code': 'S1', 'category': 'solvent', 'unit_price': 1})
    trial_id = temp_db.create_formulation(project_id, {'formula_code': 'F-1', 'formula_name': 'K'})
    temp_db.replace_trial_components(trial_id, [
        {'component_name': 'Reçine', 'component_type': 'R1', 'amount': 40, 'percentage': 40},
        {'component_name': 'Su', 'component_type': 'S1', 'amount': 60, 'percentage': 60},
    ])
    temp_db.update_trial_results(trial_id, {'gloss': 80, 'quality_score': 75})

    rows = temp_db.get_ml_training_data()

    assert len(rows) == 1
    assert abs(rows[0]['total_binder_ratio'] - 0.4) < 1e-6
    assert abs(rows[0]['total_solvent_ratio'] - 0.6) < 1e-6
    assert temp_db.get_ml_training_data_by_project(project_id)[0]['id'] == trial_id


def test_create_formulation_requires_project(temp_db):
    import pytest
    with pytest.raises(ValueError):
        temp_db.create_formulation(None, {'formula_code': 'X'})


def test_dashboard_stats_count_active_variations(temp_db, sample_project):
    project_id = temp_db.create_project(sample_project)
    a = temp_db.create_formulation(project_id, {'formula_code': 'A', 'formula_name': 'K'})
    temp_db.create_formulation(project_id, {'formula_code': 'B', 'formula_name': 'K'})
    temp_db.update_trial_results(a, {'quality_score': 80})

    stats = temp_db.get_dashboard_stats()

    assert stats == {'total_formulas': 2, 'added_this_month': 2, 'pending_tests': 1,
                     'successful_tests': 1, 'tested': 1}
    assert [f['formula_code'] for f in temp_db.get_formulations_without_trials()] == ['B']


def test_additive_subtypes_count_as_additives():
    """Hammadde formundaki defoamer/thickener... kategorileri ML'de katkı sayılmalı"""
    from src.ml_engine.recipe_transformer import RecipeTransformer
    tr = RecipeTransformer()
    recipe = [{'material_category': 'binder', 'amount': 90},
              {'material_category': 'defoamer', 'amount': 5},
              {'material_category': 'thickener', 'amount': 5}]

    features = dict(zip(tr.get_feature_names(), tr.transform(recipe)))

    assert abs(features['total_additive_ratio'] - 0.10) < 1e-9
