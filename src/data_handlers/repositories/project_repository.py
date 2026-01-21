"""
Project Repository - Proje veri erişim katmanı
===============================================
Repository Pattern ile proje CRUD operasyonlarını izole eder.

Avantajlar:
- Tek sorumluluk (SRP)
- Test edilebilirlik (mock-friendly)
- Tutarlı API
"""
import logging
from typing import List, Dict, Optional
import sqlite3

logger = logging.getLogger(__name__)


class ProjectRepository:
    """
    Proje veri erişim sınıfı.
    
    LocalDBManager'ı sararak domain-specific bir interface sağlar.
    
    Usage:
        from src.data_handlers.repositories.project_repository import ProjectRepository
        
        repo = ProjectRepository(db_manager)
        
        # Create
        project_id = repo.create({'name': 'New Project', 'description': 'Test'})
        
        # Read
        project = repo.get_by_id(project_id)
        all_projects = repo.get_all()
        
        # Update
        repo.update(project_id, {'description': 'Updated'})
        
        # Delete
        repo.delete(project_id)
    """
    
    def __init__(self, db_manager):
        """
        Args:
            db_manager: LocalDBManager instance
        """
        self._db = db_manager
    
    def create(self, data: Dict) -> int:
        """
        Yeni proje oluştur.
        
        Args:
            data: Proje verileri (name, description, customer_name, etc.)
        
        Returns:
            Oluşturulan proje ID
        """
        return self._db.create_project(data)
    
    def get_by_id(self, project_id: int) -> Optional[Dict]:
        """
        ID ile proje getir.
        
        Args:
            project_id: Proje ID
            
        Returns:
            Proje dict veya None
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM projects WHERE id = ? AND is_active = 1', 
                (project_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all(self) -> List[Dict]:
        """Tüm aktif projeleri getir"""
        return self._db.get_all_projects()
    
    def get_by_name(self, name: str) -> Optional[Dict]:
        """
        İsme göre proje bul.
        
        Args:
            name: Proje adı
            
        Returns:
            Proje dict veya None
        """
        return self._db.get_project_by_name(name)
    
    def update(self, project_id: int, data: Dict) -> bool:
        """
        Proje güncelle.
        
        Args:
            project_id: Güncellenecek proje ID
            data: Güncellenecek alanlar
            
        Returns:
            Güncelleme başarılı ise True
        """
        # Whitelist approach - sadece izin verilen alanları güncelle
        ALLOWED_FIELDS = {'name', 'description', 'customer_name', 'target_cost', 'deadline', 'status'}
        
        fields = []
        values = []
        for k, v in data.items():
            if k in ALLOWED_FIELDS:
                fields.append(f"{k} = ?")
                values.append(v)
        
        if not fields:
            return False
        
        try:
            with self._db.get_connection() as conn:
                values.append(project_id)
                conn.execute(
                    f"UPDATE projects SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    values
                )
            return True
        except sqlite3.Error as e:
            logger.error(f"Project update failed: {project_id}, {e}")
            return False
    
    def delete(self, project_id: int, cascade: bool = True) -> bool:
        """
        Projeyi sil (soft delete).
        
        Args:
            project_id: Silinecek proje ID
            cascade: İlişkili verileri de sil
            
        Returns:
            Silme başarılı ise True
        """
        try:
            # Önce proje adını bul
            project = self.get_by_id(project_id)
            if project:
                return self._db.delete_project_by_name(project['name'], cascade)
            return False
        except Exception as e:
            logger.error(f"Project delete failed: {project_id}, {e}")
            return False
    
    def count(self) -> int:
        """
        Aktif proje sayısını getir.
        
        Returns:
            Proje sayısı
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as c FROM projects WHERE is_active = 1')
            return cursor.fetchone()['c']
    
    def get_with_formulation_count(self) -> List[Dict]:
        """
        Projeleri formülasyon sayılarıyla birlikte getir.
        
        Returns:
            Proje listesi (her biri formulation_count içerir)
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    p.*,
                    COUNT(DISTINCT pf.id) as concept_count,
                    COUNT(DISTINCT t.id) as trial_count
                FROM projects p
                LEFT JOIN parent_formulations pf ON p.id = pf.project_id
                LEFT JOIN trials t ON pf.id = t.parent_formulation_id
                WHERE p.is_active = 1
                GROUP BY p.id
                ORDER BY p.updated_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Projelerde arama yap.
        
        Args:
            query: Arama metni
            limit: Maksimum sonuç sayısı
            
        Returns:
            Eşleşen projeler
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            search_pattern = f"%{query}%"
            cursor.execute('''
                SELECT * FROM projects 
                WHERE is_active = 1 
                  AND (name LIKE ? OR description LIKE ? OR customer_name LIKE ?)
                ORDER BY updated_at DESC
                LIMIT ?
            ''', (search_pattern, search_pattern, search_pattern, limit))
            return [dict(row) for row in cursor.fetchall()]
