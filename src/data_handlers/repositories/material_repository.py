"""
Material Repository - hammadde veri erişim katmanı
=================================================
Repository Pattern ile hammadde CRUD operasyonlarını izole eder.

Avantajlar:
- Tek sorumluluk (SRP)
- Test edilebilirlik (mock-friendly)
- Tutarlı API
- Lazy creation desteği
"""
import logging
from typing import List, Dict, Optional, Tuple
import sqlite3

logger = logging.getLogger(__name__)


class MaterialRepository:
    """
    hammadde veri erişim sınıfı.
    
    LocalDBManager'ı sararak domain-specific bir interface sağlar.
    
    Usage:
        from src.data_handlers.repositories.material_repository import MaterialRepository
        
        repo = MaterialRepository(db_manager)
        
        # Create
        material_id = repo.create({'name': 'Titanium Dioxide', 'code': 'TIO2-001'})
        
        # Lazy creation
        id, is_new = repo.create_if_not_exists('TIO2-001', 'Titanium Dioxide')
        
        # Read
        material = repo.get_by_code('TIO2-001')
        incomplete = repo.get_incomplete()
    """
    
    def __init__(self, db_manager):
        """
        Args:
            db_manager: LocalDBManager instance
        """
        self._db = db_manager
    
    def create(self, data: Dict) -> int:
        """
        Yeni hammadde ekle.
        
        Args:
            data: hammadde verileri (name, code, category, etc.)
        
        Returns:
            Oluşturulan hammadde ID
        """
        return self._db.add_material(data)
    
    def get_by_id(self, material_id: int) -> Optional[Dict]:
        """
        ID ile hammadde getir.
        
        Args:
            material_id: hammadde ID
            
        Returns:
            hammadde dict veya None
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM materials WHERE id = ?', (material_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_by_code(self, code: str) -> Optional[Dict]:
        """
        Kod ile hammadde getir.
        
        Args:
            code: hammadde kodu
            
        Returns:
            hammadde dict veya None
        """
        return self._db.get_material_by_code(code)
    
    def get_by_name(self, name: str) -> Optional[Dict]:
        """
        İsim ile hammadde getir.
        
        Args:
            name: hammadde adı
            
        Returns:
            hammadde dict veya None
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM materials WHERE name = ?', (name,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all(self) -> List[Dict]:
        """
        Tüm hammaddeleri getir.
        
        Returns:
            hammadde listesi
        """
        return self._db.get_all_materials()
    
    def get_incomplete(self) -> List[Dict]:
        """
        Eksik bilgili hammaddeleri getir.
        
        Returns:
            is_incomplete=True olan hammaddeler
        """
        return self._db.get_incomplete_materials()
    
    def get_complete(self) -> List[Dict]:
        """
        Tam bilgili hammaddeleri getir (ML için uygun).
        
        Returns:
            is_incomplete=False olan hammaddeler
        """
        return self._db.get_complete_materials()
    
    def create_if_not_exists(self, code: str, name: str = None) -> Tuple[int, bool]:
        """
        Yoksa oluştur, varsa mevcut ID döndür (Lazy Creation).
        
        Args:
            code: hammadde kodu
            name: hammadde adı (opsiyonel, boşsa code kullanılır)
            
        Returns:
            Tuple[int, bool]: (hammadde_id, yeni_mi)
        """
        return self._db.add_material_if_not_exists(code, name)
    
    def update(self, material_id: int, data: Dict) -> bool:
        """
        hammadde güncelle.
        
        Args:
            material_id: Güncellenecek hammadde ID
            data: Güncellenecek alanlar
            
        Returns:
            Güncelleme başarılı ise True
        """
        # Whitelist approach - sadece izin verilen alanları güncelle
        ALLOWED_FIELDS = {
            'name', 'code', 'category', 'unit_price', 'density', 
            'solid_content', 'is_incomplete', 'supplier', 'ph',
            'min_limit', 'max_limit', 'oh_value', 'glass_transition',
            'molecular_weight', 'oil_absorption', 'particle_size',
            'boiling_point', 'evaporation_rate', 'voc_g_l'
        }
        
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
                values.append(material_id)
                conn.execute(
                    f"UPDATE materials SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    values
                )
            return True
        except sqlite3.Error as e:
            logger.error(f"Material update failed: {material_id}, {e}")
            return False
    
    def mark_complete(self, material_id: int) -> bool:
        """
        hammaddeyi tamamlanmış olarak işaretle.
        
        Args:
            material_id: hammadde ID
            
        Returns:
            Başarılı ise True
        """
        return self._db.mark_material_complete(material_id)
    
    def delete(self, material_id: int) -> bool:
        """
        hammadde sil.
        
        Args:
            material_id: Silinecek hammadde ID
            
        Returns:
            Silme başarılı ise True
        """
        try:
            with self._db.get_connection() as conn:
                conn.execute('DELETE FROM materials WHERE id = ?', (material_id,))
            return True
        except sqlite3.Error as e:
            logger.error(f"Material delete failed: {material_id}, {e}")
            return False
    
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """
        hammadde ara.
        
        Args:
            query: Arama metni
            limit: Maksimum sonuç sayısı
            
        Returns:
            Eşleşen hammaddeler
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            pattern = f"%{query}%"
            cursor.execute('''
                SELECT * FROM materials 
                WHERE name LIKE ? OR code LIKE ?
                ORDER BY name
                LIMIT ?
            ''', (pattern, pattern, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def count(self) -> int:
        """
        Toplam hammadde sayısını getir.
        
        Returns:
            hammadde sayısı
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as c FROM materials')
            return cursor.fetchone()['c']
    
    def count_incomplete(self) -> int:
        """
        Eksik bilgili hammadde sayısını getir.
        
        Returns:
            Eksik hammadde sayısı
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as c FROM materials WHERE is_incomplete = 1')
            return cursor.fetchone()['c']
    
    def get_by_category(self, category: str) -> List[Dict]:
        """
        Kategoriye göre hammaddeleri getir.
        
        Args:
            category: hammadde kategorisi
            
        Returns:
            O kategorideki hammaddeler
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM materials WHERE category = ? ORDER BY name',
                (category,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_categories(self) -> List[str]:
        """
        Tüm benzersiz kategorileri getir.
        
        Returns:
            Kategori listesi
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT category FROM materials WHERE category IS NOT NULL ORDER BY category')
            return [row['category'] for row in cursor.fetchall()]
