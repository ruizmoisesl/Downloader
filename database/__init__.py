from .core import DatabaseManager, DatabaseError

# Crear una instancia global del DatabaseManager
db = DatabaseManager()

# Importar después de crear db para evitar importación circular
from .setup import init_db, register_download

__all__ = ['db', 'DatabaseError', 'DatabaseManager', 'init_db', 'register_download']
