"""
Paint Formulation AI - Data Handlers Package
============================================
"""

from .local_db_manager import LocalDBManager
from .file_system_manager import FileSystemManager
from .excel_importer import (
    ExcelFormulationImporter,
    MaterialLookupService,
    ImportResult,
    import_formulations_from_excel
)
from .smart_excel_workflow import (
    SmartTemplateGenerator,
    IntelligentImportHandler,
    IntelligentExcelWorkflow,
    TemplateMetadata,
    ImportContext,
    TransactionResult,
    generate_smart_template,
    import_excel_with_transaction
)
from .test_results_workflow import (
    TestResultsTemplateGenerator,
    TestResultsImportHandler,
    TestResultsExcelWorkflow,
    TestImportRow,
    TestImportValidationResult,
    TestImportResult,
    generate_test_template,
    import_test_results
)

__all__ = [
    # Core managers
    'LocalDBManager', 
    'FileSystemManager',
    # Basic Excel import
    'ExcelFormulationImporter',
    'MaterialLookupService',
    'ImportResult',
    'import_formulations_from_excel',
    # Smart Excel workflow (Formulations)
    'SmartTemplateGenerator',
    'IntelligentImportHandler',
    'IntelligentExcelWorkflow',
    'TemplateMetadata',
    'ImportContext',
    'TransactionResult',
    'generate_smart_template',
    'import_excel_with_transaction',
    # Test Results workflow
    'TestResultsTemplateGenerator',
    'TestResultsImportHandler',
    'TestResultsExcelWorkflow',
    'TestImportRow',
    'TestImportValidationResult',
    'TestImportResult',
    'generate_test_template',
    'import_test_results'
]

