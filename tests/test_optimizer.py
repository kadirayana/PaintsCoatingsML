"""
MLOptimizer (Genetik Algoritma) testleri
"""
import random

from src.ml_engine.optimizer import MLOptimizer


class FakeLearner:
    """Parlaklığı bağlayıcı oranıyla doğru orantılı tahmin eden sahte model"""
    models = {'gloss': object()}

    def predict(self, params):
        recipe = params['formulation']['components']
        total = sum(c['amount'] for c in recipe) or 1
        binder = sum(c['amount'] for c in recipe if c.get('category') == 'binder')
        return {'success': True, 'predictions': {'gloss': round(100 * binder / total, 2)}}


def _add_materials(db):
    db.add_material({'name': 'Reçine A', 'code': 'R1', 'category': 'binder', 'unit_price': 10})
    db.add_material({'name': 'TiO2', 'code': 'P1', 'category': 'pigment', 'unit_price': 20})
    db.add_material({'name': 'Su', 'code': 'S1', 'category': 'solvent', 'unit_price': 1})
    db.add_material({'name': 'Katkı', 'code': 'A1', 'category': 'additive', 'unit_price': 50})


def _small_optimizer(db, learner=None):
    opt = MLOptimizer(learner or FakeLearner(), db)
    opt.population_size = 20
    opt.generations = 10
    return opt


def test_optimize_returns_normalized_suggestions(temp_db):
    random.seed(0)
    _add_materials(temp_db)

    result = _small_optimizer(temp_db).optimize({'gloss': 60})

    assert result['success'] is True
    assert 1 <= len(result['suggestions']) <= 3
    for s in result['suggestions']:
        assert abs(sum(c['amount'] for c in s['recipe']) - 100) < 1e-6
        assert 'gloss' in s['prediction']
        assert 'total_cost' in s['prediction']
    scores = [s['score'] for s in result['suggestions']]
    assert scores == sorted(scores)


def test_optimize_approaches_target(temp_db):
    random.seed(1)
    _add_materials(temp_db)

    result = _small_optimizer(temp_db).optimize({'gloss': 60})

    best = result['suggestions'][0]['prediction']['gloss']
    assert abs(best - 60) < 15


def test_optimize_without_trained_model(temp_db):
    _add_materials(temp_db)
    learner = FakeLearner()
    learner.models = {}

    result = _small_optimizer(temp_db, learner).optimize({'gloss': 60})

    assert result['success'] is False


def test_optimize_with_unsupported_target(temp_db):
    _add_materials(temp_db)

    result = _small_optimizer(temp_db).optimize({'hardness': 2})

    assert result['success'] is False
    assert 'gloss' in result['message']


def test_optimize_without_materials(temp_db):
    result = _small_optimizer(temp_db).optimize({'gloss': 60})

    assert result['success'] is False


def test_optimize_surfaces_prediction_failure(temp_db):
    _add_materials(temp_db)

    class BrokenLearner(FakeLearner):
        def predict(self, params):
            return {'success': False, 'message': 'boom'}

    try:
        _small_optimizer(temp_db, BrokenLearner()).optimize({'gloss': 60})
    except RuntimeError as e:
        assert 'boom' in str(e)
    else:
        raise AssertionError('RuntimeError bekleniyordu')


def test_suggestions_have_unique_materials(temp_db):
    random.seed(2)
    _add_materials(temp_db)

    result = _small_optimizer(temp_db).optimize({'gloss': 60})

    for s in result['suggestions']:
        names = [c['name'] for c in s['recipe']]
        assert len(names) == len(set(names))
        assert len(names) >= 2
