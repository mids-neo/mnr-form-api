"""
CRUD operations package

Contains Create, Read, Update, Delete operations for database entities.
Follows the repository pattern for data access.
"""

from .user_crud import UserCRUD
from .form_crud import FormCRUD

__all__ = ["UserCRUD", "FormCRUD"]