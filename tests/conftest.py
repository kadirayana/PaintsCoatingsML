"""
Paint Formulation AI - Test Konfigürasyonu
==========================================
pytest fixtures ve test yardımcıları
"""
import os
import sys
import pytest
import tempfile

# Proje kökünü path'e ekle
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.data_handlers.local_db_manager import LocalDBManager


@pytest.fixture
def temp_db():
    """Geçici test veritabanı oluştur"""
    with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as f:
        db_path = f.name
    
    db_manager = LocalDBManager(db_path)
    db_manager.initialize()
    
    yield db_manager
    
    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def sample_project():
    """Örnek proje verisi"""
    return {
        'name': 'Test Projesi',
        'description': 'Test açıklaması'
    }


@pytest.fixture
def sample_material():
    """Örnek malzeme verisi"""
    return {
        'name': 'TEST-MAT-001',
        'code': 'TM001',
        'category': 'binder',
        'unit_price': 15.50
    }


@pytest.fixture
def sample_formulation(sample_project, temp_db):
    """Örnek formülasyon verisi (proje ile birlikte)"""
    project_id = temp_db.create_project(sample_project)
    return {
        'project_id': project_id,
        'formula_name': 'Test Formülasyonu',
        'formula_code': 'TF-001',
        'status': 'draft'
    }
