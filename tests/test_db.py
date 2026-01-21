"""
Veritabanı CRUD operasyonları için unit testler
===============================================
LocalDBManager sınıfının temel işlevselliğini test eder.
"""
import pytest
from src.data_handlers.local_db_manager import LocalDBManager


class TestDatabaseConnection:
    """Veritabanı bağlantı testleri"""
    
    def test_connection_creates_tables(self, temp_db):
        """Bağlantı kurulduğunda tablolar oluşturulmalı"""
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row['name'] for row in cursor.fetchall()}
        
        expected_tables = {'projects', 'materials', 'trials', 'components'}
        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"
    
    def test_connection_context_manager_commits(self, temp_db):
        """Context manager başarılı işlemlerde commit yapmalı"""
        with temp_db.get_connection() as conn:
            conn.execute("INSERT INTO projects (name) VALUES (?)", ("Test",))
        
        # Yeni bağlantıda veri görünmeli
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as c FROM projects")
            assert cursor.fetchone()['c'] == 1
    
    def test_connection_context_manager_rollback_on_error(self, temp_db):
        """Context manager hata durumunda rollback yapmalı"""
        try:
            with temp_db.get_connection() as conn:
                conn.execute("INSERT INTO projects (name) VALUES (?)", ("Test1",))
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Rollback yapılmış olmalı
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as c FROM projects")
            assert cursor.fetchone()['c'] == 0


class TestProjectCRUD:
    """Proje CRUD operasyonları"""
    
    def test_create_project(self, temp_db, sample_project):
        """Proje oluşturma testi"""
        project_id = temp_db.create_project(sample_project)
        assert project_id is not None
        assert project_id > 0
    
    def test_get_all_projects(self, temp_db, sample_project):
        """Tüm projeleri listeleme testi"""
        temp_db.create_project(sample_project)
        temp_db.create_project({'name': 'İkinci Proje', 'description': ''})
        
        projects = temp_db.get_all_projects()
        assert len(projects) == 2
    
    def test_get_project_by_name(self, temp_db, sample_project):
        """İsme göre proje bulma testi"""
        temp_db.create_project(sample_project)
        
        found = temp_db.get_project_by_name('Test Projesi')
        assert found is not None
        assert found['name'] == 'Test Projesi'
    
    def test_get_project_by_name_not_found(self, temp_db):
        """Olmayan proje sorgusu None dönmeli"""
        found = temp_db.get_project_by_name('Olmayan Proje')
        assert found is None
    
    def test_delete_project_soft_delete(self, temp_db, sample_project):
        """Proje silme (soft delete) testi"""
        temp_db.create_project(sample_project)
        
        result = temp_db.delete_project_by_name('Test Projesi')
        assert result is True
        
        # Soft delete - aktifler arasında görünmemeli
        projects = temp_db.get_all_projects()
        assert len(projects) == 0
    
    def test_delete_project_not_found(self, temp_db):
        """Olmayan proje silme False dönmeli"""
        result = temp_db.delete_project_by_name('Olmayan Proje')
        assert result is False


class TestMaterialCRUD:
    """Malzeme CRUD operasyonları"""
    
    def test_add_material(self, temp_db, sample_material):
        """Malzeme ekleme testi"""
        material_id = temp_db.add_material(sample_material)
        assert material_id > 0
    
    def test_get_material_by_code(self, temp_db, sample_material):
        """Koda göre malzeme bulma testi"""
        temp_db.add_material(sample_material)
        
        found = temp_db.get_material_by_code('TM001')
        assert found is not None
        assert found['name'] == 'TEST-MAT-001'
    
    def test_get_material_by_name(self, temp_db, sample_material):
        """İsme göre malzeme bulma testi"""
        temp_db.add_material(sample_material)
        
        found = temp_db.get_material_by_code('TEST-MAT-001')
        assert found is not None
    
    def test_get_all_materials(self, temp_db, sample_material):
        """Tüm malzemeleri listeleme testi"""
        temp_db.add_material(sample_material)
        temp_db.add_material({'name': 'MAT-002', 'code': 'M002', 'category': 'pigment'})
        
        materials = temp_db.get_all_materials()
        assert len(materials) == 2
    
    def test_add_material_if_not_exists_creates_new(self, temp_db):
        """Yeni malzeme oluşturma testi"""
        material_id, was_created = temp_db.add_material_if_not_exists('NEW-001', 'New Material')
        
        assert material_id is not None
        assert was_created is True
    
    def test_add_material_if_not_exists_returns_existing(self, temp_db, sample_material):
        """Var olan malzeme için mevcut ID dönmeli"""
        temp_db.add_material(sample_material)
        
        material_id, was_created = temp_db.add_material_if_not_exists('TM001', 'Ignored Name')
        
        assert material_id is not None
        assert was_created is False


class TestFormulationCRUD:
    """Formülasyon CRUD operasyonları"""
    
    def test_create_formulation(self, temp_db, sample_project):
        """Formülasyon oluşturma testi"""
        project_id = temp_db.create_project(sample_project)
        
        formulation_data = {
            'formula_name': 'Test Formula',
            'formula_code': 'TF-001'
        }
        
        trial_id = temp_db.create_formulation(project_id, formulation_data)
        assert trial_id is not None
        assert trial_id > 0
    
    def test_get_active_formulations(self, temp_db, sample_project):
        """Aktif formülasyonları listeleme testi"""
        project_id = temp_db.create_project(sample_project)
        
        temp_db.create_formulation(project_id, {'formula_name': 'F1', 'formula_code': 'TF-001'})
        temp_db.create_formulation(project_id, {'formula_name': 'F2', 'formula_code': 'TF-002'})
        
        formulations = temp_db.get_active_formulations()
        assert len(formulations) >= 2
    
    def test_get_project_hierarchy(self, temp_db, sample_project):
        """Proje hiyerarşisi testi"""
        project_id = temp_db.create_project(sample_project)
        temp_db.create_formulation(project_id, {'formula_name': 'Concept A', 'formula_code': 'CA-001'})
        
        hierarchy = temp_db.get_project_hierarchy()
        
        assert len(hierarchy) == 1
        assert hierarchy[0]['name'] == 'Test Projesi'
        assert 'concepts' in hierarchy[0]


class TestDashboard:
    """Dashboard istatistik testleri"""
    
    def test_get_dashboard_stats(self, temp_db, sample_project):
        """Dashboard istatistikleri testi"""
        project_id = temp_db.create_project(sample_project)
        temp_db.create_formulation(project_id, {'formula_name': 'F1', 'formula_code': 'TF-001'})
        
        stats = temp_db.get_dashboard_stats()
        
        assert 'Toplam Formül' in stats
        assert 'Bu Ay Eklenen' in stats
