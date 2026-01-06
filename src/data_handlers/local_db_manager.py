"""
Paint Formulation AI - Yerel Veritabanı Yöneticisi
===================================================
SQLite tabanlı gömülü veritabanı işlemleri
"""

import os
import sqlite3
import logging
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class LocalDBManager:
    """SQLite veritabanı yöneticisi"""
    
    # Malzeme önbelleği
    _material_cache = {}
    _material_cache_valid = False
    
    def __init__(self, db_path: str):
        """
        Args:
            db_path: Veritabanı dosya yolu
        """
        self.db_path = db_path
        self._connection = None
        self._invalidate_cache()
    
    def _invalidate_cache(self):
        self._material_cache = {}
        self._material_cache_valid = False

    @contextmanager
    def get_connection(self):
        """Thread-safe bağlantı yönetimi"""
        conn = sqlite3.connect(self.db_path, timeout=30)
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
        """Old DB initialization - Calls schema migration"""
        self._migrate_schema()

    def _migrate_schema(self):
        """
        Migrate database to V2 Schema:
        Hierarchy: Project -> Parent Formulation (Concept) -> Trial (Variation/Recipe)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Projects (Update existing or create)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    customer_name TEXT,       -- New
                    target_cost REAL,         -- New
                    deadline TIMESTAMP,       -- New
                    status TEXT DEFAULT 'active', -- New
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            # Attempt to add columns if they don't exist (SQLite limitation bypass)
            for col in ['customer_name', 'target_cost', 'deadline', 'status']:
                try:
                    cursor.execute(f'ALTER TABLE projects ADD COLUMN {col} TEXT')
                except Exception:
                    pass

            # 2. Parent Formulations (The "Concept")
            # This replaces the old use of 'formulations' as the recipe holder.
            # It now represents the ABSTRACT concept.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS parent_formulations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    concept_name TEXT NOT NULL,
                    concept_code TEXT,
                    target_properties TEXT, -- JSON of target specs
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            ''')

            # 3. Trials (The "Variation" / "Actual Recipe")
            # This holds the specific physical results AND is the anchor for ingredients now.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_formulation_id INTEGER, -- Link to Concept
                    trial_code TEXT,          -- Unique code for this variation (e.g. F-101-A)
                    trial_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Physical Properties (Results)
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
                    
                    FOREIGN KEY (parent_formulation_id) REFERENCES parent_formulations(id)
                )
            ''')
            
            # Add linkage column if missing
            try:
                cursor.execute('ALTER TABLE trials ADD COLUMN parent_formulation_id INTEGER REFERENCES parent_formulations(id)')
            except Exception:
                pass
            try:
                cursor.execute('ALTER TABLE trials ADD COLUMN trial_code TEXT')
            except Exception:
                pass
            try:
                cursor.execute('ALTER TABLE trials ADD COLUMN is_deleted INTEGER DEFAULT 0')
            except Exception:
                pass
            try:
                cursor.execute('ALTER TABLE trials ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            except Exception:
                pass
            # Also add is_deleted to parent_formulations for consistency
            try:
                cursor.execute('ALTER TABLE parent_formulations ADD COLUMN is_deleted INTEGER DEFAULT 0')
            except Exception:
                pass

            # 4. Components (Ingredients)
            # CRITICAL CHANGE: Now linked to TRIALS (Variations), not Abstract Formulations.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS components (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trial_id INTEGER,          -- Changed from formulation_id
                    component_name TEXT NOT NULL,
                    component_type TEXT,
                    amount REAL,
                    unit TEXT DEFAULT 'kg',
                    percentage REAL,
                    FOREIGN KEY (trial_id) REFERENCES trials(id)
                )
            ''')
            # We can't easily rename formulation_id to trial_id in SQLite without recreating.
            # For now, we assume 'formulation_id' in legacy components might correspond to 'trial_id' logic if we migrated.
            # But strictly speaking, we need a new column.
            try:
                cursor.execute('ALTER TABLE components ADD COLUMN trial_id INTEGER REFERENCES trials(id)')
            except Exception:
                pass
            
            # 5. Materials (Shared Master Data - No Change)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    category TEXT DEFAULT 'other',
                    unit_price REAL DEFAULT 0,
                    unit TEXT DEFAULT 'kg',
                    supplier TEXT,
                    oh_value REAL,
                    glass_transition REAL,
                    molecular_weight REAL,
                    solid_content REAL,
                    oil_absorption REAL,
                    particle_size REAL,
                    boiling_point REAL,
                    evaporation_rate REAL,
                    density REAL,
                    voc_g_l REAL,
                    code TEXT,
                    min_limit REAL DEFAULT 0,
                    max_limit REAL DEFAULT 100,
                    hansen_d REAL,
                    hansen_p REAL,
                    hansen_h REAL,
                    interaction_radius REAL,
                    ph REAL,
                    is_incomplete INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ML History (No Change)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ml_training_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    training_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    samples_count INTEGER,
                    r2_score REAL,
                    targets TEXT
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
            
            # Eksik sütunları ekle (Migration)
            self._migrate_db(cursor)
            self._create_indexes(cursor)
            
            logger.info("Veritabanı tabloları başarıyla oluşturuldu")

    def _migrate_db(self, cursor):
        """Eksik sütunları eklemek için basit bir migrasyon"""
        # Trials table migrations
        cursor.execute("PRAGMA table_info(trials)")
        cols = [col[1] for col in cursor.fetchall()]
        if 'coating_thickness' not in cols:
            cursor.execute("ALTER TABLE trials ADD COLUMN coating_thickness REAL")
        if 'flexibility' not in cols:
            cursor.execute("ALTER TABLE trials ADD COLUMN flexibility REAL")
        
        # Materials table migrations - add is_incomplete flag for lazy creation
        cursor.execute("PRAGMA table_info(materials)")
        mat_cols = [col[1] for col in cursor.fetchall()]
        if 'is_incomplete' not in mat_cols:
            cursor.execute("ALTER TABLE materials ADD COLUMN is_incomplete INTEGER DEFAULT 0")
            logger.info("Added 'is_incomplete' column to materials table")

    def _create_indexes(self, cursor):
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_formulations_project ON formulations(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_components_formulation ON components(formulation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trials_formulation ON trials(formulation_id)")

    # === PROJE İŞLEMLERİ ===
    
    def create_project(self, data: Dict) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO projects (name, description)
                VALUES (?, ?)
            ''', (data['name'], data.get('description', '')))
            return cursor.lastrowid
    
    def get_all_projects(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM projects WHERE is_active = 1 ORDER BY updated_at DESC')
            return [dict(row) for row in cursor.fetchall()]

    def get_project_by_name(self, name: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM projects WHERE name = ? AND is_active = 1', (name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_project_by_name(self, name: str, cascade: bool = True) -> bool:
        """
        Soft-delete a project and optionally cascade delete its formulations.
        
        Args:
            name: Project name to delete
            cascade: If True, also delete all associated formulations, trials, and components
        
        Returns:
            True if project was deleted
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get project ID first
            cursor.execute('SELECT id FROM projects WHERE name = ? AND is_active = 1', (name,))
            row = cursor.fetchone()
            if not row:
                return False
            
            project_id = row[0]
            
            if cascade:
                # Get all formulations for this project
                cursor.execute('SELECT id FROM formulations WHERE project_id = ?', (project_id,))
                formulation_ids = [r[0] for r in cursor.fetchall()]
                
                if formulation_ids:
                    placeholders = ','.join('?' * len(formulation_ids))
                    # Delete components
                    cursor.execute(f'DELETE FROM components WHERE formulation_id IN ({placeholders})', formulation_ids)
                    # Delete trials
                    cursor.execute(f'DELETE FROM trials WHERE formulation_id IN ({placeholders})', formulation_ids)
                    # Delete formulations
                    cursor.execute(f'DELETE FROM formulations WHERE id IN ({placeholders})', formulation_ids)
                    
                    logger.info(f"Cascade deleted {len(formulation_ids)} formulations for project '{name}'")
            
            # Soft-delete the project
            cursor.execute('UPDATE projects SET is_active = 0 WHERE id = ?', (project_id,))
            return True
    
    def cleanup_orphaned_formulations(self) -> int:
        """
        Remove formulations whose parent project is deleted (is_active = 0) or doesn't exist.
        Also removes associated components and trials.
        
        Returns:
            Number of formulations cleaned up
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Find orphaned formulations (project deleted or doesn't exist)
            cursor.execute('''
                SELECT f.id FROM formulations f
                LEFT JOIN projects p ON f.project_id = p.id
                WHERE p.id IS NULL OR p.is_active = 0
            ''')
            orphaned_ids = [row[0] for row in cursor.fetchall()]
            
            if not orphaned_ids:
                return 0
            
            # Delete associated data
            placeholders = ','.join('?' * len(orphaned_ids))
            cursor.execute(f'DELETE FROM components WHERE formulation_id IN ({placeholders})', orphaned_ids)
            cursor.execute(f'DELETE FROM trials WHERE formulation_id IN ({placeholders})', orphaned_ids)
            cursor.execute(f'DELETE FROM formulations WHERE id IN ({placeholders})', orphaned_ids)
            
            logger.info(f"Cleaned up {len(orphaned_ids)} orphaned formulations")
            return len(orphaned_ids)

    def get_active_formulations(self) -> List[Dict]:
        """
        Compatibility method: Get active formulations for UI dropdowns.
        Maps V2 schema (trials + parent_formulations) to legacy output format.
        
        Returns:
            List of dicts with keys: id, formula_code, formula_name, created_at, total_cost
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Query trials joined with parent_formulations to build the expected structure
            cursor.execute('''
                SELECT 
                    t.id,
                    t.trial_code as formula_code,
                    COALESCE(pf.concept_name, '') || ' - ' || COALESCE(t.trial_code, 'V' || t.id) as formula_name,
                    t.trial_date as created_at,
                    t.total_cost,
                    pf.project_id
                FROM trials t
                LEFT JOIN parent_formulations pf ON t.parent_formulation_id = pf.id
                ORDER BY t.trial_date DESC
            ''')
            results = [dict(row) for row in cursor.fetchall()]
            
            # Fallback: Also include legacy formulations table data if it exists
            try:
                cursor.execute('''
                    SELECT 
                        f.id,
                        f.formula_code,
                        f.formula_name,
                        f.created_at,
                        0 as total_cost,
                        f.project_id
                    FROM formulations f
                    JOIN projects p ON f.project_id = p.id
                    WHERE p.is_active = 1
                    ORDER BY f.created_at DESC
                ''')
                legacy_results = [dict(row) for row in cursor.fetchall()]
                # Merge, avoiding duplicates by formula_code
                existing_codes = {r.get('formula_code') for r in results if r.get('formula_code')}
                for lr in legacy_results:
                    if lr.get('formula_code') not in existing_codes:
                        results.append(lr)
            except Exception:
                pass  # Legacy table may not exist
            
            return results

    # === FORMÜLASYON İŞLEMLERİ ===
    
    # === FORMÜLASYON İŞLEMLERİ (V2 SCHEMA ADAPTER) ===
    
    def create_parent_formulation(self, project_id: int, name: str, code: str = None) -> int:
        """Create a generic Parent Formulation (Concept)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO parent_formulations (project_id, concept_name, concept_code)
                VALUES (?, ?, ?)
            ''', (project_id, name, code))
            return cursor.lastrowid

    def create_formulation(self, project_id: Optional[int], data: Dict) -> int:
        """
        Refactored: Creates a Trial (Variation) and ensures a Parent Formulation exists.
        Returns: trial_id
        """
        if not project_id:
             # Handle default/orphaned
             pass
             
        formula_name = data.get('formula_name', 'Untitled Concept')
        formula_code = data.get('formula_code', '')
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Find or Create Parent Formulation
            parent_id = None
            if project_id:
                cursor.execute('''
                    SELECT id FROM parent_formulations 
                    WHERE project_id = ? AND concept_name = ?
                ''', (project_id, formula_name))
                row = cursor.fetchone()
                if row:
                    parent_id = row[0]
                else:
                    cursor.execute('''
                        INSERT INTO parent_formulations (project_id, concept_name, concept_code)
                        VALUES (?, ?, ?)
                    ''', (project_id, formula_name, formula_code))
                    parent_id = cursor.lastrowid
            
            # 2. Create Trial (The Variation)
            trial_code = formula_code 
            
            cursor.execute('''
                INSERT INTO trials (
                    parent_formulation_id, trial_code, 
                    trial_date, result, notes, created_by,
                    viscosity, ph, density, opacity, gloss, 
                    quality_score, total_cost, coating_thickness
                )
                VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                parent_id, trial_code,
                data.get('status', 'draft'), data.get('notes', ''), 'User',
                data.get('viscosity'), data.get('ph'), data.get('density'),
                data.get('opacity'), data.get('gloss'), data.get('quality_score'),
                data.get('total_cost'), data.get('coating_thickness')
            ))
            trial_id = cursor.lastrowid
            
            # Legacy Compatibility
            try:
                cursor.execute('''
                    INSERT INTO formulations (project_id, formula_code, formula_name, status)
                    VALUES (?, ?, ?, ?)
                ''', (project_id, formula_code, formula_name, data.get('status', 'draft')))
            except Exception:
                pass

            return trial_id

    def update_formulation(self, formulation_id: int, data: Dict):
        """
        Update a Trial (Variation).
        formulation_id currently maps to trial_id in V2 schema.
        """
        with self.get_connection() as conn:
            # Update Trial (V2)
            try:
                conn.execute('''
                    UPDATE trials SET 
                        viscosity = COALESCE(?, viscosity),
                        ph = COALESCE(?, ph),
                        density = COALESCE(?, density),
                        opacity = COALESCE(?, opacity),
                        gloss = COALESCE(?, gloss),
                        quality_score = COALESCE(?, quality_score),
                        total_cost = COALESCE(?, total_cost),
                        coating_thickness = COALESCE(?, coating_thickness),
                        notes = COALESCE(?, notes),
                        result = COALESCE(?, result)
                    WHERE id = ?
                ''', (
                    data.get('viscosity'), data.get('ph'), data.get('density'),
                    data.get('opacity'), data.get('gloss'), data.get('quality_score'),
                    data.get('total_cost'), data.get('coating_thickness'),
                    data.get('notes'), data.get('status'),
                    formulation_id
                ))
            except Exception as e:
                logger.error(f"V2 Update failed: {e}")

            # Update Legacy Formulations (Safety net)
            fields = []
            values = []
            for k, v in data.items():
                if k in ['formula_name', 'formula_code', 'status']: # Only update core fields
                    fields.append(f"{k} = ?")
                    values.append(v)
            
            if fields:
                values.append(formulation_id)
                try:
                    conn.execute(f"UPDATE formulations SET {', '.join(fields)} WHERE id = ?", values)
                except Exception:
                    pass

    def delete_formulation(self, formulation_id: int):
        with self.get_connection() as conn:
            conn.execute('DELETE FROM components WHERE formulation_id = ?', (formulation_id,))
            conn.execute('DELETE FROM trials WHERE formulation_id = ?', (formulation_id,))
            conn.execute('DELETE FROM formulations WHERE id = ?', (formulation_id,))

    def delete_formulation_components(self, formulation_id: int):
        with self.get_connection() as conn:
            conn.execute('DELETE FROM components WHERE formulation_id = ?', (formulation_id,))

    def get_project_hierarchy(self) -> List[Dict]:
        """
        Fetches the complete hierarchy for the sidebar:
        Projects -> Parent Formulations -> Trials
        
        Returns:
            List of Project dicts, each containing:
                - 'concepts': List of Parent Formulations, each containing:
                    - 'trials': List of Trials
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Get Active Projects
            cursor.execute('SELECT * FROM projects WHERE is_active = 1 ORDER BY updated_at DESC')
            projects = [dict(row) for row in cursor.fetchall()]
            
            for project in projects:
                # 2. Get Concepts (Parent Formulations) for each project
                cursor.execute('''
                    SELECT * FROM parent_formulations 
                    WHERE project_id = ? 
                    ORDER BY created_at DESC
                ''', (project['id'],))
                concepts = [dict(row) for row in cursor.fetchall()]
                project['concepts'] = concepts
                
                for concept in concepts:
                    # 3. Get Trials (Variations) for each concept
                    cursor.execute('''
                        SELECT * FROM trials 
                        WHERE parent_formulation_id = ? 
                        ORDER BY trial_date DESC
                    ''', (concept['id'],))
                    trials = [dict(row) for row in cursor.fetchall()]
                    concept['trials'] = trials
                    
            return projects

    # === BİLEŞEN İŞLEMLERİ (V2 Schema Support) ===
    
    def add_component(self, owner_id: int, data: Dict):
        """
        Add component to Trial (owner_id is trial_id).
        Also populates formulation_id for legacy safety if possible (though ambiguous).
        """
        with self.get_connection() as conn:
            # Try to insert using trial_id
            try:
                conn.execute('''
                    INSERT INTO components (trial_id, component_name, component_type, amount, unit, percentage)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (owner_id, data['component_name'], data.get('component_type', ''), 
                      data.get('amount', 0), data.get('unit', 'kg'), data.get('percentage', 0)))
            except Exception:
                # Fallback implementation if schema not fully migrated or for legacy constraint
                conn.execute('''
                    INSERT INTO components (formulation_id, component_name, component_type, amount, unit, percentage)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (owner_id, data['component_name'], data.get('component_type', ''), 
                      data.get('amount', 0), data.get('unit', 'kg'), data.get('percentage', 0)))

    def get_formulation_materials(self, formulation_id: int) -> List[Dict]:
        """Get materials for a trial (variation)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Query matches either trial_id (new) or formulation_id (old)
            # Since create_formulation now returns trial_id, this works.
            cursor.execute('''
                SELECT component_name as name, component_type as code, percentage, amount 
                FROM components 
                WHERE trial_id = ? OR formulation_id = ?
            ''', (formulation_id, formulation_id))
            return [dict(row) for row in cursor.fetchall()]

    def get_recipe_with_properties(self, formulation_id: int) -> List[Dict]:
        """Get enriched recipe with material properties"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.*, m.category as material_category, m.oh_value, m.glass_transition, 
                       m.solid_content, m.density
                FROM components c
                LEFT JOIN materials m ON c.component_name = m.name
                WHERE c.trial_id = ? OR c.formulation_id = ?
            ''', (formulation_id, formulation_id))
            return [dict(row) for row in cursor.fetchall()]

    # === DENEME İŞLEMLERİ ===
    
    def save_trial(self, data: Dict):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            formulation_id = data.get('formulation_id')
            if not formulation_id and data.get('formula_code'):
                cursor.execute('SELECT id FROM formulations WHERE formula_code = ?', (data['formula_code'],))
                row = cursor.fetchone()
                if row: formulation_id = row['id']
            
            # Basitleştirilmiş trial kaydı
            cursor.execute('''
                INSERT INTO trials (formulation_id, trial_date, viscosity, ph, density, opacity, gloss, 
                                  quality_score, total_cost, notes, coating_thickness)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (formulation_id, data.get('trial_date', datetime.now().isoformat()),
                  data.get('viscosity'), data.get('ph'), data.get('density'), 
                  data.get('opacity'), data.get('gloss'), data.get('quality_score'),
                  data.get('total_cost'), data.get('notes'), data.get('coating_thickness')))

    def get_recent_trials(self, limit: int = 50) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, f.formula_code, f.formula_name
                FROM trials t
                LEFT JOIN formulations f ON t.formulation_id = f.id
                ORDER BY t.trial_date DESC LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_latest_trial_by_formula_code(self, formula_code: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.* FROM trials t
                JOIN formulations f ON t.formulation_id = f.id
                WHERE f.formula_code = ? ORDER BY t.trial_date DESC LIMIT 1
            ''', (formula_code,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_trial_with_materials(self, trial_id: int) -> Optional[Dict]:
        """
        Get trial details with full material data for editor loading.
        
        Returns dict with:
        - formula_code: trial code
        - formula_name: parent formulation name
        - components: list of materials with code, name, weight, solid_content, unit_price
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Get trial info with parent formulation name
            cursor.execute('''
                SELECT 
                    t.id, t.trial_code, t.total_cost, t.notes,
                    pf.concept_name as formula_name,
                    pf.project_id
                FROM trials t
                LEFT JOIN parent_formulations pf ON t.parent_formulation_id = pf.id
                WHERE t.id = ?
            ''', (trial_id,))
            
            trial_row = cursor.fetchone()
            if not trial_row:
                return None
            
            trial_info = dict(trial_row)
            
            # 2. Get components JOINed with materials for full property data
            cursor.execute('''
                SELECT 
                    c.component_name,
                    c.component_type,
                    c.amount,
                    c.percentage,
                    COALESCE(m.code, c.component_type) as material_code,
                    COALESCE(m.name, c.component_name) as material_name,
                    COALESCE(m.solid_content, 100) as solid_content,
                    COALESCE(m.unit_price, 0) as unit_price,
                    COALESCE(m.density, 1.0) as density
                FROM components c
                LEFT JOIN materials m ON c.component_name = m.name OR c.component_name = m.code
                WHERE c.trial_id = ? OR c.formulation_id = ?
            ''', (trial_id, trial_id))
            
            components = []
            for row in cursor.fetchall():
                comp = dict(row)
                components.append({
                    'material_code': comp.get('material_code') or comp.get('component_type', ''),
                    'material_name': comp.get('material_name') or comp.get('component_name', ''),
                    'weight': comp.get('amount', 0) or 0,
                    'solid_content': comp.get('solid_content', 100) or 100,
                    'unit_price': comp.get('unit_price', 0) or 0,
                })
            
            return {
                'id': trial_info.get('id'),
                'formula_code': trial_info.get('trial_code', ''),
                'formula_name': trial_info.get('formula_name', ''),
                'components': components,
                'total_cost': trial_info.get('total_cost'),
                'notes': trial_info.get('notes', ''),
                'project_id': trial_info.get('project_id')
            }
    
    def get_material_by_code(self, code: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM materials WHERE name = ? OR code = ?', (code, code))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_materials(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM materials ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]

    def add_material(self, data: Dict) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO materials (name, category, unit_price, code, is_incomplete)
                VALUES (?, ?, ?, ?, ?)
            ''', (data['name'], data.get('category', 'other'), 
                  data.get('unit_price', 0), data.get('code'),
                  1 if data.get('is_incomplete', False) else 0))
            return cursor.lastrowid
    
    def get_incomplete_materials(self) -> List[Dict]:
        """Get all materials flagged as incomplete (missing physical properties)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM materials WHERE is_incomplete = 1 ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_complete_materials(self) -> List[Dict]:
        """Get all materials with complete physical properties"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM materials WHERE is_incomplete = 0 OR is_incomplete IS NULL ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_material_complete(self, material_id: int) -> bool:
        """Mark a material as complete (has physical properties)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE materials SET is_incomplete = 0 WHERE id = ?', (material_id,))
            return cursor.rowcount > 0
    
    def get_material_by_code_or_name(self, identifier: str) -> Optional[Dict]:
        """Get material by code OR name (for two-way binding)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM materials WHERE code = ? OR name = ?', (identifier, identifier))
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_material_if_not_exists(self, code: str, name: str = None) -> tuple:
        """
        Insert a material ONLY if the code doesn't already exist.
        Uses INSERT OR IGNORE to prevent duplicates within batch imports.
        
        Args:
            code: Raw material code (primary identifier)
            name: Optional material name (defaults to code if not provided)
            
        Returns:
            (material_id, was_created) tuple
            - material_id: ID of existing or newly created material
            - was_created: True if material was just created
        """
        if not code:
            return (None, False)
        
        material_name = name.strip() if name and name.strip() else code
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Step 1: Check if material already exists by code
            cursor.execute('SELECT id FROM materials WHERE code = ?', (code,))
            existing = cursor.fetchone()
            
            if existing:
                return (existing['id'], False)
            
            # Step 2: Also check by name to avoid conflicts
            cursor.execute('SELECT id FROM materials WHERE name = ?', (material_name,))
            existing_by_name = cursor.fetchone()
            
            if existing_by_name:
                return (existing_by_name['id'], False)
            
            # Step 3: Insert new material with defaults
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO materials 
                    (name, code, category, unit_price, solid_content, density, is_incomplete)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (material_name, code, 'other', 0, 100.0, 1.0, 1))
                
                new_id = cursor.lastrowid
                if new_id:
                    self._invalidate_cache()
                    logger.info(f"Created new material on-the-fly: {code} ({material_name})")
                    return (new_id, True)
                else:
                    # INSERT OR IGNORE returns 0 if ignored, re-query
                    cursor.execute('SELECT id FROM materials WHERE code = ?', (code,))
                    row = cursor.fetchone()
                    return (row['id'] if row else None, False)
            except Exception as e:
                logger.error(f"Failed to create material {code}: {e}")
                return (None, False)

    # === ML VERİLERİ ===
    
    def get_ml_training_data(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM trials WHERE quality_score IS NOT NULL')
            return [dict(row) for row in cursor.fetchall()]

    def get_ml_training_data_by_project(self, project_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # User requirement: Count ONLY unique, valid formulations (GROUP BY formulation_id)
            cursor.execute('''
                SELECT t.* FROM trials t
                JOIN formulations f ON t.formulation_id = f.id
                WHERE f.project_id = ? AND t.quality_score IS NOT NULL
                GROUP BY t.formulation_id
            ''', (project_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_valid_ml_training_data(self) -> List[Dict]:
        """
        Get ML training data excluding formulations with incomplete materials.
        Returns ONE representative trial per formulation (GROUP BY formulation_id).
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get formulation IDs that contain incomplete materials
            cursor.execute('''
                SELECT DISTINCT fm.formulation_id 
                FROM formulation_materials fm
                JOIN materials m ON fm.material_id = m.id
                WHERE m.is_incomplete = 1
            ''')
            incomplete_formulation_ids = {row['formulation_id'] for row in cursor.fetchall()}
            
            # Get unique trials (grouped by formulation)
            # Logic: SELECT COUNT(DISTINCT formulation_id) behavior
            cursor.execute('''
                SELECT * FROM trials 
                WHERE quality_score IS NOT NULL 
                GROUP BY formulation_id
            ''')
            all_trials = [dict(row) for row in cursor.fetchall()]
            
            # Filter out trials for formulations with incomplete materials
            valid_trials = [
                trial for trial in all_trials 
                if trial.get('formulation_id') not in incomplete_formulation_ids
            ]
            
            if len(valid_trials) < len(all_trials):
                logger.info(
                    f"ML training data: Excluded {len(all_trials) - len(valid_trials)} formulations "
                    f"with incomplete materials (using {len(valid_trials)} unique formulations)"
                )
            
            return valid_trials

    def save_ml_training_history(self, data: Dict):
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO ml_training_history (samples_count, r2_score, targets)
                VALUES (?, ?, ?)
            ''', (data.get('samples_count'), data.get('r2_score'), json.dumps(data.get('targets'))))

    # === DASHBOARD ===
    
    def get_dashboard_stats(self) -> Dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as c FROM formulations')
            total = cursor.fetchone()['c']
            # Count distinct formulas that have at least one trial
            cursor.execute("SELECT COUNT(DISTINCT formulation_id) as c FROM trials WHERE formulation_id IS NOT NULL")
            tested = cursor.fetchone()['c']
            # Count formulas added this month
            cursor.execute("SELECT COUNT(*) as c FROM formulations WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')")
            this_month = cursor.fetchone()['c']
            return {
                'Toplam Formül': total,
                'Bu Ay Eklenen': this_month,
                'Test Bekleyen': max(0, total - tested),
                'Başarılı': tested
            }

    def get_monthly_formulation_counts(self) -> List[Dict]:
        """Returns monthly formulation counts for the last 6 months"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
                FROM formulations
                WHERE created_at >= date('now', '-6 months')
                GROUP BY strftime('%Y-%m', created_at)
                ORDER BY month ASC
            ''')
            return [{'month': row['month'], 'count': row['count']} for row in cursor.fetchall()]

    def get_dashboard_insights(self) -> List[str]:
        return ["Sistem başarıyla başlatıldı."]
    
    def get_all_formulations(self) -> List[Dict]:
        """
        Get all active formulations/trials for 'Total Formulas' dashboard card.
        Uses trials table as the source (V2 schema).
        
        Returns:
            List of trial dicts
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, pf.concept_name, p.name as project_name
                FROM trials t
                LEFT JOIN parent_formulations pf ON t.parent_formulation_id = pf.id
                LEFT JOIN projects p ON pf.project_id = p.id
                WHERE t.is_deleted = 0 OR t.is_deleted IS NULL
                ORDER BY t.created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_formulations_this_month(self) -> List[Dict]:
        """
        Get formulations created in the current month for 'Added This Month' card.
        
        Returns:
            List of trial dicts created this month
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, pf.concept_name, p.name as project_name
                FROM trials t
                LEFT JOIN parent_formulations pf ON t.parent_formulation_id = pf.id
                LEFT JOIN projects p ON pf.project_id = p.id
                WHERE (t.is_deleted = 0 OR t.is_deleted IS NULL)
                  AND strftime('%Y-%m', t.created_at) = strftime('%Y-%m', 'now')
                ORDER BY t.created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_formulations_without_trials(self) -> List[Dict]:
        """
        Get formulations (trials) that have NO test results yet.
        For 'Pending Tests' dashboard card.
        
        Returns:
            List of trial dicts without test results
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, pf.concept_name, p.name as project_name
                FROM trials t
                LEFT JOIN parent_formulations pf ON t.parent_formulation_id = pf.id
                LEFT JOIN projects p ON pf.project_id = p.id
                LEFT JOIN test_results tr ON t.id = tr.trial_id
                WHERE tr.id IS NULL
                  AND (t.is_deleted = 0 OR t.is_deleted IS NULL)
                ORDER BY t.created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]

    def find_nearest_trial(self, params: Dict) -> Optional[Dict]:
        return None # Basitleştirildi

    def import_data(self, data: List[Dict]):
        for row in data:
            self.save_trial(row)
