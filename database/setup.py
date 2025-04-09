import os
from .core import DatabaseError, DatabaseManager
import logging

# Obtener la instancia global
db = DatabaseManager()

logger = logging.getLogger(__name__)

def init_db():
    """Inicializar la base de datos con el schema"""
    try:
        # Leer el archivo schema.sql
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = f.read()

        # Dividir en comandos individuales (separados por ;)
        commands = schema.split(';')

        # Ejecutar cada comando
        for command in commands:
            command = command.strip()
            if command:  # Ignorar líneas vacías
                try:
                    db.execute_query(command)
                    logger.info("Schema command executed successfully")
                except DatabaseError as e:
                    logger.error(f"Error executing schema command: {e}")
                    logger.error(f"Command was: {command}")
                    raise

        logger.info("Database schema initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

def register_download(user_id, url, filename, status='success', error_message=None):
    """Registrar una descarga en el historial"""
    try:
        db.execute_query(
            "CALL register_download(%s, %s, %s, %s, %s)",
            (user_id, url, filename, status, error_message)
        )
        logger.info(f"Download registered for user {user_id}: {filename}")
        return True
    except DatabaseError as e:
        logger.error(f"Error registering download: {e}")
        return False

if __name__ == "__main__":
    # Inicializar la base de datos
    if init_db():
        print("Database initialized successfully")
    else:
        print("Error initializing database")
