import mysql.connector
from mysql.connector import Error, pooling
from contextlib import contextmanager
import os
import logging
from dotenv import load_dotenv
from functools import wraps
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'crossover.proxy.rlwy.net'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'gMwwIIYRfHPZkaVoRzYJXELGUyyisdkr'),
    'database': os.getenv('DB_NAME', 'railway'),
    'port': int(os.getenv('DB_PORT', '10662')),
    'pool_name': 'mypool',
    'pool_size': 5,
    'connect_timeout': 10,
    'time_zone': '+00:00'
}

class DatabaseError(Exception):
    """Excepción personalizada para errores de base de datos"""
    pass

def retry_on_error(max_retries=3, delay=1):
    """Decorador para reintentar operaciones de base de datos"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Error as e:
                    retries += 1
                    if retries == max_retries:
                        raise DatabaseError(f"Max retries reached: {e}")
                    logger.warning(f"Database operation failed, retrying... ({retries}/{max_retries})")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

class DatabaseManager:
    _instance = None
    _pool = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._setup_pool()
            self._initialized = True

    @classmethod
    def _setup_pool(cls):
        """Configurar el pool de conexiones"""
        try:
            cls._pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name=DB_CONFIG['pool_name'],
                pool_size=DB_CONFIG['pool_size'],
                **{k: v for k, v in DB_CONFIG.items() if k not in ['pool_name', 'pool_size']}
            )
            logger.info("Connection pool created successfully")
        except Error as e:
            logger.error(f"Error creating connection pool: {e}")
            raise DatabaseError(f"Failed to create connection pool: {e}")

    @contextmanager
    def get_connection(self):
        """Obtener una conexión del pool usando context manager"""
        conn = None
        try:
            conn = self._pool.get_connection()
            yield conn
        except Error as e:
            logger.error(f"Database connection error: {e}")
            raise DatabaseError(f"Database connection failed: {e}")
        finally:
            if conn and conn.is_connected():
                conn.close()
                logger.debug("Database connection closed")

    @retry_on_error()
    def execute_query(self, query, params=None):
        """Ejecutar una consulta con reintentos automáticos"""
        with self.get_connection() as conn:
            cursor = None
            try:
                cursor = conn.cursor(dictionary=True, buffered=True)
                cursor.execute(query, params or ())
                
                # Si es un SELECT, devolver resultados
                if query.strip().upper().startswith('SELECT'):
                    result = cursor.fetchall()
                else:
                    conn.commit()
                    result = None
                    
                return result
            except Error as e:
                if conn.is_connected():
                    conn.rollback()
                logger.error(f"Query execution failed: {e}\nQuery: {query}\nParams: {params}")
                raise
            finally:
                if cursor:
                    # Consumir cualquier resultado no leído
                    try:
                        while cursor.nextset():
                            pass
                    except:
                        pass
                    cursor.close()

    def execute_many(self, query, params_list):
        """Ejecutar múltiples consultas en una transacción"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                conn.start_transaction()
                cursor.executemany(query, params_list)
                conn.commit()
            except Error as e:
                conn.rollback()
                logger.error(f"Batch execution failed: {e}\nQuery: {query}")
                raise DatabaseError(f"Batch execution failed: {e}")
            finally:
                cursor.close()

    def health_check(self):
        """Verificar el estado de la conexión"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                result = cursor.fetchone()
                return bool(result)
        except Error as e:
            logger.error(f"Health check failed: {e}")
            return False

# Instancia global del manejador de base de datos
db = DatabaseManager()

# Ejemplo de uso:
'''
if __name__ == "__main__":
    try:
        # Verificar la conexión
        if db.health_check():
            print("Database connection is healthy")
            
            # Ejemplo de consulta
            result = db.execute_query("SELECT * FROM users WHERE id = %s", (1,))
            print(f"Query result: {result}")
            
            # Ejemplo de inserción múltiple
            users = [("user1", "pass1"), ("user2", "pass2")]
            db.execute_many("INSERT INTO users (username, password) VALUES (%s, %s)", users)
            
    except DatabaseError as e:
        print(f"Database error: {e}")
'''
