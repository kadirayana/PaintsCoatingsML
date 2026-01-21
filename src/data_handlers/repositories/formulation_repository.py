"""
Formulation Repository - Formülasyon veri erişim katmanı
========================================================
Repository Pattern ile CRUD operasyonlarını izole eder.

Avantajlar:
- Tek sorumluluk (SRP)
- Test edilebilirlik (mock-friendly)
- Gelecekte ORM geçişi kolaylığı
"""
import logging
from typing import List, Dict, Optional
import sqlite3

logger = logging.getLogger(__name__)


class FormulationRepository:
    """
    Formülasyon (Trial) veri erişim sınıfı.
    
    LocalDBManager'ı sararak domain-specific bir interface sağlar.
    
    Usage:
        from src.data_handlers.repositories.formulation_repository import FormulationRepository
        
        repo = FormulationRepository(db_manager)
        
        # Create
        trial_id = repo.create(project_id, {'formula_name': 'Test', 'formula_code': 'T-001'})
        
        # Read
        formulation = repo.get_by_id(trial_id)
        all_formulations = repo.get_all_active()
        
        # Update
        repo.update(trial_id, {'notes': 'Updated notes'})
        
        # Delete
        repo.delete(trial_id)
    """
    
    def __init__(self, db_manager):
        """
        Args:
            db_manager: LocalDBManager instance
        """
        self._db = db_manager
    
    def create(self, project_id: int, data: Dict) -> int:
        """
        Yeni formülasyon (trial) oluştur.
        
        Args:
            project_id: Parent proje ID
            data: Formülasyon verileri (formula_name, formula_code, etc.)
        
        Returns:
            Oluşturulan trial_id
        """
        return self._db.create_formulation(project_id, data)
    
    def get_by_id(self, trial_id: int) -> Optional[Dict]:
        """
        ID ile formülasyon getir (bileşenlerle birlikte).
        
        Returns:
            Formülasyon dict veya None
        """
        return self._db.get_trial_with_materials(trial_id)
    
    def get_all_active(self) -> List[Dict]:
        """Tüm aktif formülasyonları getir"""
        return self._db.get_active_formulations()
    
    def get_by_project(self, project_id: int) -> List[Dict]:
        """
        Projeye ait formülasyonları getir.
        
        Args:
            project_id: Proje ID
            
        Returns:
            Proje formülasyonları listesi
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, pf.concept_name 
                FROM trials t
                JOIN parent_formulations pf ON t.parent_formulation_id = pf.id
                WHERE pf.project_id = ?
                ORDER BY COALESCE(t.created_at, t.trial_date) DESC
            ''', (project_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def update(self, trial_id: int, data: Dict) -> bool:
        """
        Formülasyonu güncelle.
        
        Args:
            trial_id: Güncellenecek trial ID
            data: Güncellenecek alanlar
            
        Returns:
            Güncelleme başarılı ise True
        """
        try:
            self._db.update_formulation(trial_id, data)
            return True
        except Exception as e:
            logger.error(f"Formulation update failed: {trial_id}, {e}")
            return False
    
    def delete(self, trial_id: int) -> bool:
        """
        Formülasyonu sil.
        
        Args:
            trial_id: Silinecek trial ID
            
        Returns:
            Silme başarılı ise True
        """
        try:
            self._db.delete_formulation(trial_id)
            return True
        except Exception as e:
            logger.error(f"Formulation delete failed: {trial_id}, {e}")
            return False
    
    def get_with_components(self, trial_id: int) -> Optional[Dict]:
        """
        Formülasyonu bileşenleriyle birlikte getir.
        
        Returns:
            {
                'id': ...,
                'formula_code': ...,
                'components': [...]
            }
        """
        formulation = self.get_by_id(trial_id)
        if formulation:
            formulation['components'] = self._db.get_formulation_materials(trial_id)
        return formulation
    
    def count_by_project(self, project_id: int) -> int:
        """
        Projedeki formülasyon sayısını getir.
        
        Args:
            project_id: Proje ID
            
        Returns:
            Formülasyon sayısı
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) as count 
                FROM trials t
                JOIN parent_formulations pf ON t.parent_formulation_id = pf.id
                WHERE pf.project_id = ?
            ''', (project_id,))
            return cursor.fetchone()['count']
    
    def get_for_ml_training(self, project_id: Optional[int] = None) -> List[Dict]:
        """
        ML eğitimi için formülasyonları getir.
        
        Args:
            project_id: Spesifik proje için filtrele (opsiyonel)
            
        Returns:
            Quality score'u olan formülasyonlar
        """
        if project_id:
            return self._db.get_ml_training_data_by_project(project_id)
        return self._db.get_ml_training_data()
    
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Formülasyonlarda arama yap.
        
        Args:
            query: Arama metni
            limit: Maksimum sonuç sayısı
            
        Returns:
            Eşleşen formülasyonlar
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            search_pattern = f"%{query}%"
            cursor.execute('''
                SELECT t.id, t.trial_code, pf.concept_name, p.name as project_name
                FROM trials t
                LEFT JOIN parent_formulations pf ON t.parent_formulation_id = pf.id
                LEFT JOIN projects p ON pf.project_id = p.id
                WHERE t.trial_code LIKE ? 
                   OR pf.concept_name LIKE ?
                   OR p.name LIKE ?
                ORDER BY COALESCE(t.created_at, t.trial_date) DESC
                LIMIT ?
            ''', (search_pattern, search_pattern, search_pattern, limit))
            return [dict(row) for row in cursor.fetchall()]
