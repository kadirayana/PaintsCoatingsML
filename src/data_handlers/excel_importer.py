"""
Paint Formulation AI - Excel Import & Material Synchronization
==============================================================
Advanced Excel import with lazy material creation and two-way binding support.

Features:
- Import formulations from Excel files
- Lazy material creation (auto-create missing materials as incomplete)
- User notification for incomplete materials
- Two-way Code <-> Name binding support
- ML pipeline integrity (excludes incomplete materials)
"""

import os
import logging
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Result of an Excel import operation"""
    success: bool
    message: str
    formulations_imported: int = 0
    materials_created: int = 0
    incomplete_materials: List[Dict] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.incomplete_materials is None:
            self.incomplete_materials = []
        if self.errors is None:
            self.errors = []


class ExcelFormulationImporter:
    """
    Handles Excel import with intelligent material synchronization.
    
    Implements "Lazy Creation" pattern:
    - If material exists (by code OR name), uses existing record
    - If material doesn't exist, creates placeholder with is_incomplete=True
    """
    
    # Expected column mappings (flexible matching)
    COLUMN_MAPPINGS = {
        'material_code': ['material code', 'code', 'hammadde kodu', 'kod', 'mat_code', 'material_code'],
        'material_name': ['material name', 'name', 'hammadde adı', 'hammadde adi', 'ad', 'material_name', 'material'],
        'quantity': ['quantity', 'amount', 'miktar', 'qty', 'percentage', 'oran', '%'],
        'unit': ['unit', 'birim', 'units'],
        'category': ['category', 'kategori', 'type', 'tip']
    }
    
    # Required columns
    REQUIRED_COLUMNS = ['material_code', 'quantity']
    
    def __init__(self, db_manager):
        """
        Initialize the importer.
        
        Args:
            db_manager: LocalDBManager instance
        """
        self.db_manager = db_manager
        self._material_cache = {}
        self._build_material_cache()
    
    def _build_material_cache(self):
        """Build cache of materials for fast lookup"""
        try:
            materials = self.db_manager.get_all_materials()
            for mat in materials:
                # Index by both code and name (lowercase for case-insensitive matching)
                if mat.get('code'):
                    self._material_cache[mat['code'].lower()] = mat
                if mat.get('name'):
                    self._material_cache[mat['name'].lower()] = mat
        except Exception as e:
            logger.warning(f"Could not build material cache: {e}")
    
    def import_formulations_from_excel(
        self,
        file_path: str,
        project_id: Optional[int] = None,
        formula_code_prefix: str = "IMPORT"
    ) -> ImportResult:
        """
        Import formulations from an Excel file.
        
        Args:
            file_path: Path to Excel file
            project_id: Optional project to assign formulations to
            formula_code_prefix: Prefix for auto-generated formula codes
            
        Returns:
            ImportResult with statistics and any incomplete materials
        """
        if not HAS_PANDAS:
            return ImportResult(
                success=False,
                message="Pandas kütüphanesi yüklü değil. Kurulum: pip install pandas openpyxl"
            )
        
        if not os.path.exists(file_path):
            return ImportResult(
                success=False,
                message=f"Dosya bulunamadı: {file_path}"
            )
        
        try:
            # Read Excel file
            df = self._read_excel_file(file_path)
            
            if df is None or df.empty:
                return ImportResult(
                    success=False,
                    message="Excel dosyası boş veya okunamadı."
                )
            
            # Normalize column names
            df = self._normalize_columns(df)
            
            # Validate required columns
            validation_result = self._validate_columns(df)
            if not validation_result['valid']:
                return ImportResult(
                    success=False,
                    message=validation_result['message']
                )
            
            # Process rows
            formulations_created = 0
            materials_created = 0
            incomplete_materials = []
            errors = []
            
            # Group by formulation if there's a formula_code column, otherwise treat as single formulation
            if 'formula_code' in df.columns:
                grouped = df.groupby('formula_code')
            else:
                # Create a default formula code
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                df['formula_code'] = f"{formula_code_prefix}_{timestamp}"
                grouped = df.groupby('formula_code')
            
            for formula_code, group in grouped:
                try:
                    components = []
                    
                    for idx, row in group.iterrows():
                        # Get or create material
                        material_code = str(row.get('material_code', '')).strip()
                        material_name = str(row.get('material_name', material_code)).strip()
                        quantity = self._parse_quantity(row.get('quantity', 0))
                        category = str(row.get('category', 'other')).strip() if 'category' in row else 'other'
                        
                        if not material_code:
                            errors.append(f"Satır {idx+2}: hammadde kodu boş")
                            continue
                        
                        # Lookup or create material
                        material, is_new = self._get_or_create_material(
                            code=material_code,
                            name=material_name,
                            category=category
                        )
                        
                        if is_new:
                            materials_created += 1
                            incomplete_materials.append({
                                'id': material['id'],
                                'code': material_code,
                                'name': material_name,
                                'category': category
                            })
                        
                        components.append({
                            'material_id': material['id'],
                            'material_code': material_code,
                            'material_name': material['name'],
                            'amount': quantity,
                            'percentage': quantity  # Assuming percentage
                        })
                    
                    # Create formulation if we have components
                    if components:
                        formulation_id = self._create_formulation(
                            project_id=project_id,
                            formula_code=str(formula_code),
                            components=components
                        )
                        formulations_created += 1
                        
                except Exception as e:
                    errors.append(f"Formülasyon '{formula_code}': {str(e)}")
            
            # Rebuild cache after import
            self._build_material_cache()
            
            # Build result message
            if formulations_created > 0:
                message = f"{formulations_created} formülasyon başarıyla içe aktarıldı."
                if materials_created > 0:
                    message += f"\n{materials_created} yeni hammadde oluşturuldu (eksik bilgi ile)."
            else:
                message = "Hiçbir formülasyon içe aktarılamadı."
            
            return ImportResult(
                success=formulations_created > 0,
                message=message,
                formulations_imported=formulations_created,
                materials_created=materials_created,
                incomplete_materials=incomplete_materials,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Excel import error: {e}")
            return ImportResult(
                success=False,
                message=f"İçe aktarma hatası: {str(e)}"
            )
    
    def _read_excel_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """Read Excel file with automatic sheet detection"""
        try:
            # Try reading first sheet
            if file_path.endswith('.csv'):
                return pd.read_csv(file_path)
            else:
                return pd.read_excel(file_path, sheet_name=0)
        except Exception as e:
            logger.error(f"Error reading Excel: {e}")
            return None
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to standard format"""
        # Create a mapping from original to normalized names
        column_map = {}
        
        for col in df.columns:
            col_lower = str(col).lower().strip()
            
            for standard_name, variations in self.COLUMN_MAPPINGS.items():
                if col_lower in variations:
                    column_map[col] = standard_name
                    break
        
        return df.rename(columns=column_map)
    
    def _validate_columns(self, df: pd.DataFrame) -> Dict:
        """Validate that required columns exist"""
        missing = []
        
        for req_col in self.REQUIRED_COLUMNS:
            if req_col not in df.columns:
                missing.append(req_col)
        
        if missing:
            return {
                'valid': False,
                'message': f"Eksik sütunlar: {', '.join(missing)}. Beklenen: material_code, quantity"
            }
        
        return {'valid': True}
    
    def _parse_quantity(self, value) -> float:
        """Parse quantity value to float"""
        if pd.isna(value):
            return 0.0
        
        try:
            # Handle percentage strings like "10%"
            if isinstance(value, str):
                value = value.replace('%', '').replace(',', '.').strip()
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _get_or_create_material(
        self,
        code: str,
        name: str,
        category: str = 'other'
    ) -> Tuple[Dict, bool]:
        """
        Get existing material or create new one with is_incomplete flag.
        
        Returns:
            Tuple of (material_dict, is_newly_created)
        """
        # Try to find in cache (case-insensitive)
        code_lower = code.lower()
        name_lower = name.lower()
        
        # Check by code first
        if code_lower in self._material_cache:
            return self._material_cache[code_lower], False
        
        # Check by name
        if name_lower in self._material_cache:
            return self._material_cache[name_lower], False
        
        # Not found - create new incomplete material
        material_data = {
            'name': name or code,  # Use code if name is empty
            'code': code,
            'category': category,
            'is_incomplete': True,  # Flag as incomplete
            'unit_price': 0,
            'density': None,
            'solid_content': None
        }
        
        try:
            material_id = self._add_incomplete_material(material_data)
            material_data['id'] = material_id
            
            # Add to cache
            self._material_cache[code_lower] = material_data
            self._material_cache[name_lower] = material_data
            
            return material_data, True
            
        except Exception as e:
            logger.error(f"Error creating material {code}: {e}")
            raise
    
    def _add_incomplete_material(self, data: Dict) -> int:
        """Add a new material marked as incomplete"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO materials (name, code, category, unit_price, is_incomplete)
                VALUES (?, ?, ?, ?, 1)
            ''', (
                data['name'],
                data['code'],
                data.get('category', 'other'),
                data.get('unit_price', 0)
            ))
            
            return cursor.lastrowid
    
    def _create_formulation(
        self,
        project_id: Optional[int],
        formula_code: str,
        components: List[Dict]
    ) -> int:
        """Create a formulation with its components"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create formulation
            cursor.execute('''
                INSERT INTO formulations (project_id, formula_code, formula_name, status)
                VALUES (?, ?, ?, 'imported')
            ''', (project_id, formula_code, f"Imported: {formula_code}"))
            
            formulation_id = cursor.lastrowid
            
            # Add components
            for comp in components:
                cursor.execute('''
                    INSERT INTO components (formulation_id, component_name, component_type, amount, percentage)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    formulation_id,
                    comp['material_name'],
                    comp.get('material_code', ''),
                    comp['amount'],
                    comp['percentage']
                ))
                
                # Also link to materials table
                cursor.execute('''
                    INSERT INTO formulation_materials (formulation_id, material_id, amount)
                    VALUES (?, ?, ?)
                ''', (formulation_id, comp['material_id'], comp['amount']))
            
            return formulation_id


class MaterialLookupService:
    """
    Provides two-way binding support for Material Code <-> Name.
    
    Used in Formulation Editor for auto-completion.
    """
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self._code_to_name = {}
        self._name_to_code = {}
        self._all_codes = []
        self._all_names = []
        self.refresh_cache()
    
    def refresh_cache(self):
        """Refresh the material lookup cache"""
        self._code_to_name = {}
        self._name_to_code = {}
        self._all_codes = []
        self._all_names = []
        
        try:
            materials = self.db_manager.get_all_materials()
            
            for mat in materials:
                code = mat.get('code', '')
                name = mat.get('name', '')
                
                if code:
                    self._code_to_name[code.lower()] = {
                        'name': name,
                        'id': mat['id'],
                        'is_incomplete': mat.get('is_incomplete', False)
                    }
                    self._all_codes.append(code)
                
                if name:
                    self._name_to_code[name.lower()] = {
                        'code': code,
                        'id': mat['id'],
                        'is_incomplete': mat.get('is_incomplete', False)
                    }
                    self._all_names.append(name)
                    
        except Exception as e:
            logger.warning(f"Error building material lookup cache: {e}")
    
    def get_name_by_code(self, code: str) -> Optional[str]:
        """Get material name by code (two-way binding)"""
        result = self._code_to_name.get(code.lower())
        return result['name'] if result else None
    
    def get_code_by_name(self, name: str) -> Optional[str]:
        """Get material code by name (two-way binding)"""
        result = self._name_to_code.get(name.lower())
        return result['code'] if result else None
    
    def get_material_by_code_or_name(self, identifier: str) -> Optional[Dict]:
        """Get full material info by code or name"""
        identifier_lower = identifier.lower()
        
        # Check code first
        if identifier_lower in self._code_to_name:
            info = self._code_to_name[identifier_lower]
            return self.db_manager.get_material_by_code(identifier)
        
        # Check name
        if identifier_lower in self._name_to_code:
            info = self._name_to_code[identifier_lower]
            return self.db_manager.get_material_by_code(info['code']) if info['code'] else None
        
        return None
    
    def is_valid_material(self, identifier: str) -> bool:
        """Check if material code or name is valid"""
        identifier_lower = identifier.lower()
        return identifier_lower in self._code_to_name or identifier_lower in self._name_to_code
    
    def is_material_complete(self, identifier: str) -> bool:
        """Check if material has complete physical properties"""
        identifier_lower = identifier.lower()
        
        if identifier_lower in self._code_to_name:
            return not self._code_to_name[identifier_lower].get('is_incomplete', False)
        
        if identifier_lower in self._name_to_code:
            return not self._name_to_code[identifier_lower].get('is_incomplete', False)
        
        return False
    
    def get_all_codes(self) -> List[str]:
        """Get all material codes for auto-completion"""
        return self._all_codes.copy()
    
    def get_all_names(self) -> List[str]:
        """Get all material names for auto-completion"""
        return self._all_names.copy()
    
    def get_incomplete_materials(self) -> List[Dict]:
        """Get all materials flagged as incomplete"""
        materials = self.db_manager.get_all_materials()
        return [m for m in materials if m.get('is_incomplete', False)]


def get_incomplete_material_count(db_manager) -> int:
    """Helper function to count incomplete materials"""
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM materials WHERE is_incomplete = 1')
        result = cursor.fetchone()
        return result[0] if result else 0


def import_formulations_from_excel(db_manager, file_path: str, project_id: int = None) -> ImportResult:
    """
    Convenience function for Excel import.
    
    Args:
        db_manager: LocalDBManager instance
        file_path: Path to Excel file
        project_id: Optional project ID
        
    Returns:
        ImportResult
    """
    importer = ExcelFormulationImporter(db_manager)
    return importer.import_formulations_from_excel(file_path, project_id)
