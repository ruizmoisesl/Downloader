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
    'pool_size': 3,  # Reduced pool size for better stability
    'connect_timeout': 30,  # Increased timeout
    'connection_timeout': 30,  # Additional timeout setting
    'time_zone': '+00:00',
    'get_warnings': True,  # Enable warnings
    'raise_on_warnings': True,  # Raise on warnings
    'autocommit': True,  # Enable autocommit
    'buffered': True,  # Enable buffered cursors by default
    'consume_results': True  # Consume results automatically
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
        """Configurar el pool de conexiones con reintentos"""
        max_retries = 3
        retry_delay = 5
        last_error = None

        for attempt in range(max_retries):
            try:
                if cls._pool is not None:
                    try:
                        cls._pool.close()
                    except:
                        pass
                    cls._pool = None

                config = {k: v for k, v in DB_CONFIG.items() if k not in ['pool_name', 'pool_size']}
                cls._pool = mysql.connector.pooling.MySQLConnectionPool(
                    pool_name=DB_CONFIG['pool_name'],
                    pool_size=DB_CONFIG['pool_size'],
                    **config
                )
                
                # Verificar la conexión
                with cls._pool.get_connection() as test_conn:
                    with test_conn.cursor() as cursor:
                        cursor.execute('SELECT 1')
                        cursor.fetchone()
                
                logger.info("Connection pool created and verified successfully")
                return
                
            except Error as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                raise DatabaseError(f"Failed to setup connection pool after {max_retries} attempts: {last_error}")

    @contextmanager
    def get_connection(self):
        """Obtener una conexión del pool usando context manager"""
        conn = None
        try:
            conn = self._pool.get_connection()
            yield conn
        except Error as e:
            raise DatabaseError(f"Error getting connection from pool: {e}")
        finally:
            if conn:
                try:
                    conn.close()
                except Error:
                    pass

    @retry_on_error()
    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False, return_last_id=False):
        """Ejecutar una consulta con reintentos automáticos"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(query, params)
                    
                    if return_last_id:
                        return cursor.lastrowid
                    elif fetch_one:
                        return cursor.fetchone()
                    elif fetch_all:
                        return cursor.fetchall()
                    return True
                    
                except Error as e:
                    conn.rollback()
                    raise DatabaseError(f"Error executing query: {e}")

    @retry_on_error()
    def execute_many(self, query, params_list):
        """Ejecutar múltiples consultas en una transacción"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
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

    @retry_on_error()
    def health_check(self) -> bool:
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

    # Funciones de Usuario
    @retry_on_error()
    def create_user(self, username: str, email: str, password: str) -> int:
        """Crear un nuevo usuario"""
        query = "INSERT INTO USER (username, email, password) VALUES (%s, %s, %s)"
        params = (username, email, password)
        return self.execute_query(query, params, return_last_id=True)

    @retry_on_error()
    def get_user_by_id(self, user_id: int) -> dict:
        """Obtener usuario por ID"""
        query = "SELECT id, username, email, created_at, last_login, is_active FROM USER WHERE id = %s"
        result = self.execute_query(query, (user_id,), fetch_one=True)
        return dict(zip(['id', 'username', 'email', 'created_at', 'last_login', 'is_active'], result)) if result else None

    @retry_on_error()
    def get_user_by_username(self, username: str) -> dict:
        """Obtener usuario por nombre de usuario"""
        query = "SELECT id, username, email, password, created_at, last_login, is_active FROM USER WHERE username = %s"
        result = self.execute_query(query, (username,), fetch_one=True)
        return dict(zip(['id', 'username', 'email', 'password', 'created_at', 'last_login', 'is_active'], result)) if result else None

    @retry_on_error()
    def update_user_last_login(self, user_id: int) -> bool:
        """Actualizar última fecha de inicio de sesión"""
        query = "UPDATE USER SET last_login = CURRENT_TIMESTAMP WHERE id = %s"
        return self.execute_query(query, (user_id,))

    @retry_on_error()
    def update_user(self, user_id: int, username: str = None, email: str = None, password: str = None, is_active: bool = None) -> bool:
        """Actualizar información del usuario"""
        updates = []
        params = []

        if username is not None:
            updates.append("username = %s")
            params.append(username)

        if email is not None:
            updates.append("email = %s")
            params.append(email)

        if password is not None:
            updates.append("password = %s")
            params.append(password)

        if is_active is not None:
            updates.append("is_active = %s")
            params.append(is_active)

        if not updates:
            return False

        query = f"UPDATE USER SET {', '.join(updates)} WHERE id = %s"
        params.append(user_id)
        return self.execute_query(query, tuple(params))

    @retry_on_error()
    def delete_user(self, user_id: int) -> bool:
        """Eliminar usuario"""
        query = "DELETE FROM USER WHERE id = %s"
        return self.execute_query(query, (user_id,))

    # Funciones de Historial de Descargas
    @retry_on_error()
    def register_download(self, user_id: int, url: str, filename: str, status: str, error_message: str = None) -> int:
        """Registrar una nueva descarga"""
        query = "CALL register_download(%s, %s, %s, %s, %s)"
        params = (user_id, url, filename, status, error_message)
        return self.execute_query(query, params, return_last_id=True)

    @retry_on_error()
    def get_user_downloads(self, user_id: int, limit: int = 10, offset: int = 0) -> list:
        """Obtener historial de descargas de un usuario"""
        query = """
        SELECT id, url, filename, download_date, status, error_message 
        FROM DOWNLOAD_HISTORY 
        WHERE user_id = %s 
        ORDER BY download_date DESC 
        LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (user_id, limit, offset), fetch_all=True)
        return [dict(zip(['id', 'url', 'filename', 'download_date', 'status', 'error_message'], row)) for row in results]

    @retry_on_error()
    def get_download_by_id(self, download_id: int) -> dict:
        """Obtener una descarga específica por ID"""
        query = "SELECT id, user_id, url, filename, download_date, status, error_message FROM DOWNLOAD_HISTORY WHERE id = %s"
        result = self.execute_query(query, (download_id,), fetch_one=True)
        return dict(zip(['id', 'user_id', 'url', 'filename', 'download_date', 'status', 'error_message'], result)) if result else None

    @retry_on_error()
    def get_download_stats(self, user_id: int) -> dict:
        """Obtener estadísticas de descargas de un usuario"""
        query = """
        SELECT 
            COUNT(*) as total_downloads,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_downloads,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_downloads
        FROM DOWNLOAD_HISTORY
        WHERE user_id = %s
        """
        result = self.execute_query(query, (user_id,), fetch_one=True)
        return dict(zip(['total_downloads', 'successful_downloads', 'failed_downloads'], result)) if result else None

    @retry_on_error()
    def delete_download_history(self, user_id: int, download_id: int = None) -> bool:
        """Eliminar historial de descargas de un usuario"""
        if download_id:
            query = "DELETE FROM DOWNLOAD_HISTORY WHERE user_id = %s AND id = %s"
            return self.execute_query(query, (user_id, download_id))
        else:
            query = "DELETE FROM DOWNLOAD_HISTORY WHERE user_id = %s"
            return self.execute_query(query, (user_id,))

# Instancia global del manejador de base de datos
db = DatabaseManager()
