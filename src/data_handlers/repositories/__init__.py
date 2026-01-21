"""
Data Access Layer - Repository Pattern
=======================================
Tüm veritabanı işlemleri için repository sınıfları.

Kullanım:
    from src.data_handlers.repositories import (
        FormulationRepository,
        ProjectRepository,
        MaterialRepository
    )
    
    # Her repository LocalDBManager instance'ı alır
    project_repo = ProjectRepository(db_manager)
    material_repo = MaterialRepository(db_manager)
    formulation_repo = FormulationRepository(db_manager)
"""
from src.data_handlers.repositories.formulation_repository import FormulationRepository
from src.data_handlers.repositories.project_repository import ProjectRepository
from src.data_handlers.repositories.material_repository import MaterialRepository

__all__ = [
    'FormulationRepository',
    'ProjectRepository',
    'MaterialRepository',
]

