"""
Paint Formulation AI - Yerel Veritabanı Yöneticisi
===================================================
SQLite tabanlı gömülü veritabanı işlemleri
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class LocalDBManager:
    """SQLite veritabanı yöneticisi"""
    
    def __init__(self, db_path: str):
        """
        Args:
            db_path: Veritabanı dosya yolu
        """
        self.db_path = db_path
        self._connection = None
    
    @contextmanager
    def get_connection(self):
        """Thread-safe bağlantı yönetimi"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def initialize(self) -> None:
        """Veritabanı tablolarını oluştur"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Projeler tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            
            # Formülasyonlar tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS formulations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    formula_code TEXT NOT NULL,
                    formula_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'draft',
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            ''')
            
            # Bileşenler tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS components (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    formulation_id INTEGER,
                    component_name TEXT NOT NULL,
                    component_type TEXT,
                    amount REAL,
                    unit TEXT DEFAULT 'kg',
                    percentage REAL,
                    FOREIGN KEY (formulation_id) REFERENCES formulations(id)
                )
            ''')
            
            # Denemeler/Testler tablosu (geliştirilmiş)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    formulation_id INTEGER,
                    trial_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    viscosity REAL,
                    ph REAL,
                    density REAL,
                    opacity REAL,
                    gloss REAL,
                    quality_score REAL,
                    total_cost REAL,
                    corrosion_resistance REAL,
                    adhesion REAL,
                    hardness REAL,
                    notes TEXT,
                    result TEXT,
                    created_by TEXT,
                    FOREIGN KEY (formulation_id) REFERENCES formulations(id)
                )
            ''')
            
            # Malzemeler tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    category TEXT DEFAULT 'other',
                    unit_price REAL DEFAULT 0,
                    unit TEXT DEFAULT 'kg',
                    supplier TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Formülasyon bileşenleri fiyat bilgisi ile
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS formulation_materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    formulation_id INTEGER,
                    material_id INTEGER,
                    amount REAL,
                    unit_price_at_time REAL,
                    FOREIGN KEY (formulation_id) REFERENCES formulations(id),
                    FOREIGN KEY (material_id) REFERENCES materials(id)
                )
            ''')
            
            # Ham veri tablosu (Excel import için)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS raw_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_file TEXT,
                    data_json TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            ''')
            
            # Ayarlar tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ML model geçmişi tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ml_training_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    training_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    samples_count INTEGER,
                    r2_score REAL,
                    targets TEXT,
                    model_path TEXT
                )
            ''')
            
            # Eksik sütunları ekle (mevcut veritabanları için migration)
            self._migrate_trials_table(cursor)
            
            logger.info("Veritabanı tabloları başarıyla oluşturuldu")
    
    def _migrate_trials_table(self, cursor):
        """Trials tablosuna eksik sütunları ekle"""
        # Mevcut sütunları kontrol et
        cursor.execute("PRAGMA table_info(trials)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        # Eklenmesi gereken sütunlar
        required_columns = [
            ('quality_score', 'REAL'),
            ('total_cost', 'REAL'),
            ('corrosion_resistance', 'REAL'),
            ('adhesion', 'REAL'),
            ('hardness', 'REAL'),
            ('flexibility', 'REAL'),
            ('chemical_resistance', 'REAL'),
            ('uv_resistance', 'REAL'),
            ('abrasion_resistance', 'REAL'),
            ('scratch_resistance', 'REAL'),
            ('coating_thickness', 'REAL'),
            ('drying_time', 'REAL'),
            ('application_method', 'TEXT'),
            ('substrate_type', 'TEXT'),
        ]
        
        for col_name, col_type in required_columns:
            if col_name not in existing_columns:
                try:
                    cursor.execute(f'ALTER TABLE trials ADD COLUMN {col_name} {col_type}')
                    logger.info(f"Sütun eklendi: trials.{col_name}")
                except Exception as e:
                    # Sütun zaten varsa hata vermez
                    pass
    
    # === PROJE İŞLEMLERİ ===
    
    def create_project(self, data: Dict) -> int:
        """Yeni proje oluştur"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO projects (name, description)
                VALUES (?, ?)
            ''', (data['name'], data.get('description', '')))
            
            project_id = cursor.lastrowid
            logger.info(f"Proje oluşturuldu: {data['name']} (ID: {project_id})")
            return project_id
    
    def get_all_projects(self) -> List[Dict]:
        """Tüm projeleri getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, description, created_at, updated_at, is_active
                FROM projects
                WHERE is_active = 1
                ORDER BY updated_at DESC
            ''')
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_project(self, project_id: int) -> Optional[Dict]:
        """Belirli bir projeyi getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM projects WHERE id = ?
            ''', (project_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_project(self, project_id: int, data: Dict) -> bool:
        """Projeyi güncelle"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE projects
                SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (data['name'], data.get('description', ''), project_id))
            
            return cursor.rowcount > 0
    
    def delete_project(self, project_id: int) -> bool:
        """Projeyi soft-delete yap"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE projects
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (project_id,))
            
            return cursor.rowcount > 0
    
    # === FORMÜLASYON İŞLEMLERİ ===
    
    def create_formulation(self, project_id: int, data: Dict) -> int:
        """Yeni formülasyon oluştur"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO formulations (project_id, formula_code, formula_name, status)
                VALUES (?, ?, ?, ?)
            ''', (project_id, data['formula_code'], data.get('formula_name', ''), data.get('status', 'draft')))
            
            return cursor.lastrowid
    
    def get_formulations(self, project_id: int) -> List[Dict]:
        """Projeye ait formülasyonları getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM formulations
                WHERE project_id = ?
                ORDER BY created_at DESC
            ''', (project_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_formulations(self) -> List[Dict]:
        """Tüm formülasyonları getir (proje fark etmeksizin)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM formulations
                ORDER BY created_at DESC
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_formulation(self, formulation_id: int) -> Optional[Dict]:
        """Belirli bir formülasyonu getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM formulations WHERE id = ?
            ''', (formulation_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # === BİLEŞEN İŞLEMLERİ ===
    
    def add_component(self, formulation_id: int, data: Dict) -> int:
        """Formülasyona bileşen ekle"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO components (formulation_id, component_name, component_type, amount, unit, percentage)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                formulation_id,
                data['component_name'],
                data.get('component_type', ''),
                data.get('amount', 0),
                data.get('unit', 'kg'),
                data.get('percentage', 0)
            ))
            
            return cursor.lastrowid
    
    def get_components(self, formulation_id: int) -> List[Dict]:
        """Formülasyonun bileşenlerini getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM components
                WHERE formulation_id = ?
            ''', (formulation_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # === DENEME İŞLEMLERİ ===
    
    def save_trial(self, data: Dict) -> int:
        """Deneme kaydı oluştur"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Formülasyon ID'sini bul veya oluştur
            formulation_id = data.get('formulation_id')
            
            if not formulation_id and data.get('formula_code'):
                cursor.execute('''
                    SELECT id FROM formulations WHERE formula_code = ?
                ''', (data['formula_code'],))
                row = cursor.fetchone()
                
                if row:
                    formulation_id = row['id']
                else:
                    # Yeni formülasyon oluştur
                    cursor.execute('''
                        INSERT INTO formulations (formula_code, formula_name)
                        VALUES (?, ?)
                    ''', (data['formula_code'], data.get('formula_name', '')))
                    formulation_id = cursor.lastrowid
            
            # Deneme kaydını oluştur - dinamik sütunlar
            # Mevcut sütunları al
            cursor.execute("PRAGMA table_info(trials)")
            valid_columns = [col[1] for col in cursor.fetchall()]
            
            # Eklenecek sütunları belirle
            insert_columns = ['formulation_id', 'trial_date']
            insert_values = [formulation_id, data.get('trial_date', data.get('date', datetime.now().isoformat()))]
            
            # Tüm data'daki değerleri ekle (geçerli sütunlar için)
            for key, value in data.items():
                if key in valid_columns and key not in ['id', 'formulation_id', 'trial_date']:
                    insert_columns.append(key)
                    if isinstance(value, (int, float)):
                        insert_values.append(value)
                    else:
                        insert_values.append(self._parse_float(value) if key not in ['notes', 'result', 'application_method', 'substrate_type'] else value)
            
            placeholders = ', '.join(['?' for _ in insert_columns])
            columns_str = ', '.join(insert_columns)
            
            cursor.execute(f'''
                INSERT INTO trials ({columns_str})
                VALUES ({placeholders})
            ''', insert_values)
            
            logger.info(f"Deneme kaydedildi: Formülasyon ID {formulation_id}, {len(insert_columns)} sütun")
            return cursor.lastrowid
    
    def get_recent_trials(self, limit: int = 10) -> List[Dict]:
        """Son denemeleri getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, f.formula_code, f.formula_name
                FROM trials t
                LEFT JOIN formulations f ON t.formulation_id = f.id
                ORDER BY t.trial_date DESC
                LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_trials_by_formulation(self, formulation_id: int) -> List[Dict]:
        """Formülasyona ait denemeleri getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM trials
                WHERE formulation_id = ?
                ORDER BY trial_date DESC
            ''', (formulation_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # === VERİ İÇE AKTARMA ===
    
    def import_data(self, data: List[Dict], project_id: int = None, source_file: str = None) -> int:
        """Excel/CSV verisini içe aktar"""
        import json
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Ham veriyi kaydet
            cursor.execute('''
                INSERT INTO raw_data (project_id, source_file, data_json)
                VALUES (?, ?, ?)
            ''', (project_id, source_file, json.dumps(data, ensure_ascii=False)))
            
            # Her satır için formülasyon/deneme oluştur
            imported_count = 0
            for row in data:
                try:
                    self.save_trial(row)
                    imported_count += 1
                except Exception as e:
                    logger.warning(f"Satır import hatası: {e}")
            
            logger.info(f"{imported_count} kayıt içe aktarıldı")
            return imported_count
    
    # === DASHBOARD İSTATİSTİKLERİ ===
    
    def get_dashboard_stats(self) -> Dict:
        """Dashboard istatistiklerini getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Toplam formül sayısı
            cursor.execute('SELECT COUNT(*) as count FROM formulations')
            total = cursor.fetchone()['count']
            
            # Bu ay eklenen
            cursor.execute('''
                SELECT COUNT(*) as count FROM formulations
                WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
            ''')
            this_month = cursor.fetchone()['count']
            
            # Test bekleyen (status = 'draft')
            cursor.execute('''
                SELECT COUNT(*) as count FROM formulations
                WHERE status = 'draft'
            ''')
            pending = cursor.fetchone()['count']
            
            # Başarılı (status = 'approved')
            cursor.execute('''
                SELECT COUNT(*) as count FROM formulations
                WHERE status = 'approved'
            ''')
            approved = cursor.fetchone()['count']
            
            return {
                'Toplam Formül': total,
                'Bu Ay Eklenen': this_month,
                'Test Bekleyen': pending,
                'Başarılı': approved
            }
    
    def get_ml_training_data(self) -> List[Dict]:
        """ML eğitimi için deneme verilerini getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, f.formula_code, f.formula_name
                FROM trials t
                LEFT JOIN formulations f ON t.formulation_id = f.id
                ORDER BY t.trial_date DESC
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
    
    # === AYARLAR ===
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Ayar değerini getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            return row['value'] if row else default
    
    def set_setting(self, key: str, value: Any) -> None:
        """Ayar değerini kaydet"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, str(value)))
    
    # === YARDIMCI METODLAR ===
    
    @staticmethod
    def _parse_float(value) -> Optional[float]:
        """String'i float'a dönüştür"""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def vacuum(self) -> None:
        """Veritabanını optimize et"""
        with self.get_connection() as conn:
            conn.execute('VACUUM')
            logger.info("Veritabanı optimize edildi")
    
    def get_db_size(self) -> int:
        """Veritabanı boyutunu döndür (bytes)"""
        return os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
    
    # === MALZEME İŞLEMLERİ ===
    
    def add_material(self, data: Dict) -> int:
        """Malzeme ekle"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO materials (name, category, unit_price, unit, supplier)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                data['name'],
                data.get('category', 'other'),
                data.get('unit_price', 0),
                data.get('unit', 'kg'),
                data.get('supplier', '')
            ))
            return cursor.lastrowid
    
    def update_material(self, material_id: int, data: Dict) -> bool:
        """Malzeme güncelle"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE materials
                SET name = ?, category = ?, unit_price = ?, unit = ?, supplier = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                data.get('name'),
                data.get('category'),
                data.get('unit_price'),
                data.get('unit'),
                data.get('supplier'),
                material_id
            ))
            return cursor.rowcount > 0
    
    def delete_material(self, material_id: int) -> bool:
        """Malzeme sil"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM materials WHERE id = ?', (material_id,))
            return cursor.rowcount > 0
    
    def get_all_materials(self) -> List[Dict]:
        """Tüm malzemeleri getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM materials ORDER BY category, name')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_material(self, material_id: int) -> Optional[Dict]:
        """Malzeme getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM materials WHERE id = ?', (material_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # === ML EĞİTİM VERİLERİ ===
    
    def get_ml_training_data(self) -> List[Dict]:
        """ML eğitimi için tüm denemeleri getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    t.viscosity, t.ph, t.density,
                    t.opacity, t.gloss, t.quality_score, t.total_cost,
                    t.corrosion_resistance, t.adhesion, t.hardness
                FROM trials t
                WHERE t.viscosity IS NOT NULL 
                   OR t.ph IS NOT NULL 
                   OR t.density IS NOT NULL
                ORDER BY t.trial_date DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_trial_count(self) -> int:
        """Deneme sayısını getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM trials')
            return cursor.fetchone()['count']
    
    def save_ml_training_history(self, data: Dict) -> int:
        """ML eğitim geçmişi kaydet"""
        import json
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ml_training_history (samples_count, r2_score, targets, model_path)
                VALUES (?, ?, ?, ?)
            ''', (
                data.get('samples_count', 0),
                data.get('r2_score', 0),
                json.dumps(data.get('targets', [])),
                data.get('model_path', '')
            ))
            return cursor.lastrowid
