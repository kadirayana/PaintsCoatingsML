"""
Paint Formulation AI - Material Service
========================================
TDS tabanlı hammadde yönetimi ve Excel/CSV import.

Özellikler:
- Hammadde CRUD işlemleri
- Excel/CSV toplu import
- TDS özelliklerinden ML fingerprint çıkarma
- Benzer hammadde bulma
"""

import logging
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class materialservice:
    """
    Hammadde yönetim servisi.
    
    TDS (Technical Data Sheet) tabanlı özellik yapısı ile
    ML için vektör çıkarma desteği.
    """
    
    # Kategori bazlı özellik grupları
    PROPERTY_GROUPS = {
        'physical': [
            'density', 'solid_content', 'viscosity_mpa_s', 
            'particle_size', 'oil_absorption'
        ],
        'chemical': [
            'oh_value', 'acid_value', 'amine_value', 
            'molecular_weight', 'ph', 'is_reactive', 'is_crosslinker'
        ],
        'thermal': [
            'glass_transition', 'boiling_point', 
            'flash_point', 'evaporation_rate'
        ],
        'optical': [
            'refractive_index', 'color_index'
        ],
        'hansen': [
            'hansen_d', 'hansen_p', 'hansen_h'
        ]
    }
    
    # Excel import için kolon eşleştirme
    EXCEL_COLUMN_MAP = {
        'kod': 'code',
        'code': 'code',
        'isim': 'name',
        'name': 'name',
        'ad': 'name',
        'kategori': 'category',
        'category': 'category',
        'yoğunluk': 'density',
        'density': 'density',
        'katı içeriği': 'solid_content',
        'solid content': 'solid_content',
        'katı': 'solid_content',
        'viskozite': 'viscosity_mpa_s',
        'viscosity': 'viscosity_mpa_s',
        'oh değeri': 'oh_value',
        'oh value': 'oh_value',
        'asit değeri': 'acid_value',
        'acid value': 'acid_value',
        'fiyat': 'unit_price',
        'price': 'unit_price',
        'tedarikçi': 'supplier',
        'supplier': 'supplier',
    }
    
    def __init__(self, db_manager, feature_extractor=None):
        """
        Args:
            db_manager: LocalDBManager instance
            feature_extractor: MaterialFeatureExtractor (opsiyonel)
        """
        self.db = db_manager
        self._feature_extractor = feature_extractor
    
    @property
    def feature_extractor(self):
        """Lazy loading for feature extractor"""
        if self._feature_extractor is None:
            try:
                from src.ml_engine.material_feature_extractor import MaterialFeatureExtractor
                self._feature_extractor = MaterialFeatureExtractor()
            except ImportError:
                logger.warning("MaterialFeatureExtractor not available")
        return self._feature_extractor
    
    # =========================================================================
    # CRUD Operations
    # =========================================================================
    
    def add_material(self, data: Dict) -> int:
        """
        Yeni hammadde ekle.
        
        Args:
            data: Hammadde verileri
            
        Returns:
            Yeni material ID
        """
        # Validate required fields
        if not data.get('code') or not data.get('name'):
            raise ValueError("Hammadde kodu ve ismi gereklidir")
        
        # Handle custom_properties as JSON
        if 'custom_properties' in data and isinstance(data['custom_properties'], dict):
            data['custom_properties'] = json.dumps(data['custom_properties'])
        
        return self.db.add_material(data)
    
    def update_material(self, material_id: int, data: Dict) -> bool:
        """Hammadde güncelle"""
        if 'custom_properties' in data and isinstance(data['custom_properties'], dict):
            data['custom_properties'] = json.dumps(data['custom_properties'])
        
        return self.db.update_material(material_id, data)
    
    def get_material(self, material_id: int) -> Optional[Dict]:
        """Hammadde detaylarını getir"""
        material = self.db.get_material(material_id)
        if material and material.get('custom_properties'):
            try:
                material['custom_properties'] = json.loads(material['custom_properties'])
            except:
                pass
        return material
    
    def get_all_materials(self, category: str = None) -> List[Dict]:
        """Tüm hammaddeleri getir"""
        materials = self.db.get_all_materials()
        
        if category:
            materials = [m for m in materials if m.get('category') == category]
        
        return materials
    
    def delete_material(self, material_id: int) -> bool:
        """Hammadde sil"""
        return self.db.delete_material(material_id)
    
    # =========================================================================
    # Excel/CSV Import
    # =========================================================================
    
    def import_from_excel(self, file_path: str) -> Dict:
        """
        Excel/CSV dosyasından toplu import.
        
        Args:
            file_path: Dosya yolu (.xlsx, .xls, .csv)
            
        Returns:
            {'imported': int, 'skipped': int, 'errors': List[str]}
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")
        
        # Read file based on extension
        if path.suffix.lower() in ['.xlsx', '.xls']:
            data = self._read_excel(file_path)
        elif path.suffix.lower() == '.csv':
            data = self._read_csv(file_path)
        else:
            raise ValueError(f"Desteklenmeyen dosya formatı: {path.suffix}")
        
        # Process rows
        imported = 0
        skipped = 0
        errors = []
        
        for i, row in enumerate(data, start=2):  # Excel row numbers
            try:
                # Map columns to DB fields
                mapped_row = self._map_excel_row(row)
                
                if not mapped_row.get('code'):
                    skipped += 1
                    continue
                
                # Check if exists
                existing = self.db.get_material_by_code(mapped_row['code'])
                if existing:
                    # Update existing
                    self.update_material(existing['id'], mapped_row)
                else:
                    # Add new
                    self.add_material(mapped_row)
                
                imported += 1
                
            except Exception as e:
                errors.append(f"Satır {i}: {str(e)}")
        
        logger.info(f"Import complete: {imported} imported, {skipped} skipped, {len(errors)} errors")
        
        return {
            'imported': imported,
            'skipped': skipped,
            'errors': errors
        }
    
    def _read_excel(self, file_path: str) -> List[Dict]:
        """Excel dosyası oku"""
        try:
            import openpyxl
            
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            sheet = wb.active
            
            # Get headers from first row
            headers = []
            for cell in sheet[1]:
                headers.append(str(cell.value or '').strip().lower())
            
            # Read data rows
            data = []
            for row in sheet.iter_rows(min_row=2, values_only=True):
                row_dict = {}
                for i, value in enumerate(row):
                    if i < len(headers) and headers[i]:
                        row_dict[headers[i]] = value
                if any(row_dict.values()):  # Skip empty rows
                    data.append(row_dict)
            
            wb.close()
            return data
            
        except ImportError:
            raise ImportError("openpyxl kütüphanesi gerekli: pip install openpyxl")
    
    def _read_csv(self, file_path: str) -> List[Dict]:
        """CSV dosyası oku"""
        import csv
        
        data = []
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Lowercase keys
                data.append({k.lower().strip(): v for k, v in row.items()})
        
        return data
    
    def _map_excel_row(self, row: Dict) -> Dict:
        """Excel kolonlarını DB alanlarına eşle"""
        mapped = {}
        
        for excel_col, value in row.items():
            if not excel_col:
                continue
            
            # Find matching DB column
            db_col = self.EXCEL_COLUMN_MAP.get(excel_col.lower())
            
            if db_col:
                # Convert value type if needed
                if db_col in ['density', 'solid_content', 'viscosity_mpa_s', 
                              'oh_value', 'acid_value', 'unit_price']:
                    try:
                        value = float(value) if value else None
                    except (ValueError, TypeError):
                        value = None
                
                mapped[db_col] = value
        
        return mapped
    
    def get_import_template(self) -> Dict:
        """Import şablonu bilgisi döndür"""
        return {
            'required_columns': ['kod', 'isim'],
            'optional_columns': list(self.EXCEL_COLUMN_MAP.keys()),
            'example_row': {
                'kod': 'R-101',
                'isim': 'Epoksi Reçine',
                'kategori': 'resin',
                'yoğunluk': 1.15,
                'katı içeriği': 75,
                'fiyat': 45.50
            }
        }
    
    # =========================================================================
    # ML Integration
    # =========================================================================
    
    def get_fingerprint(self, material_id: int) -> Optional[Tuple[List[float], List[float]]]:
        """
        Hammadde için ML fingerprint çıkar.
        
        Returns:
            (fingerprint, confidence_mask) tuple veya None
        """
        if not self.feature_extractor:
            return None
        
        material = self.get_material(material_id)
        if not material:
            return None
        
        return self.feature_extractor.extract(material)
    
    def find_similar(self, material_id: int, top_k: int = 5) -> List[Dict]:
        """
        Benzer hammaddeleri bul.
        
        Args:
            material_id: Kaynak hammadde ID
            top_k: Döndürülecek sonuç sayısı
            
        Returns:
            Benzer hammaddeler listesi (similarity score ile)
        """
        try:
            from src.data_handlers.material_similarity import MaterialSimilarityEngine
            
            engine = MaterialSimilarityEngine(self.db)
            return engine.find_similar_with_explanation(material_id, top_k)
        except ImportError:
            logger.warning("MaterialSimilarityEngine not available")
            return []
    
    def get_property_summary(self, material_id: int) -> Dict:
        """
        Hammadde özellik özeti (UI için).
        
        Returns:
            Gruplandırılmış özellikler
        """
        material = self.get_material(material_id)
        if not material:
            return {}
        
        summary = {}
        
        for group_name, properties in self.PROPERTY_GROUPS.items():
            group_values = {}
            for prop in properties:
                value = material.get(prop)
                if value is not None:
                    group_values[prop] = value
            
            if group_values:
                summary[group_name] = group_values
        
        return summary
