from flask import send_file, jsonify
import os
import shutil
import zipfile
from datetime import datetime, timedelta
import hashlib
from functools import lru_cache
import mimetypes
import logging
from database.core import db

# Configuración
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, "downloads")
CACHE_FOLDER = os.path.join(BASE_DIR, "cache")
MAX_CACHE_AGE = 24 * 60 * 60  # 24 horas en segundos
MAX_ZIP_SIZE = 500 * 1024 * 1024  # 500MB

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear carpetas necesarias
for folder in [DOWNLOAD_FOLDER, CACHE_FOLDER]:
    os.makedirs(folder, exist_ok=True)

def get_user_folder(session_user):
    """Obtiene y crea la carpeta del usuario.
    
    Args:
        session_user: Diccionario con los datos del usuario
        
    Returns:
        str: Ruta a la carpeta del usuario
    """
    if session_user and 'username' in session_user:
        user_folder = os.path.join(DOWNLOAD_FOLDER, session_user['username'])
    else:
        user_folder = DOWNLOAD_FOLDER
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

def clear_user_folder(session_user):
    """Limpia la carpeta del usuario eliminando todos los archivos.
    
    Args:
        session_user: Diccionario con los datos del usuario
    """
    if not session_user or 'username' not in session_user:
        return
        
    user_folder = get_user_folder(session_user)
    try:
        # Eliminar todos los archivos en la carpeta
        for filename in os.listdir(user_folder):
            file_path = os.path.join(user_folder, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    logger.info(f"Archivo eliminado: {file_path}")
            except Exception as e:
                logger.error(f"Error al eliminar {file_path}: {e}")
        
        logger.info(f"Carpeta del usuario {session_user['username']} limpiada exitosamente")
    except Exception as e:
        logger.error(f"Error al limpiar la carpeta del usuario {session_user['username']}: {e}")

def cleanup_old_files(folder, max_age=MAX_CACHE_AGE):
    try:
        current_time = datetime.now().timestamp()
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            if os.path.getmtime(filepath) < current_time - max_age:
                try:
                    os.remove(filepath)
                    logger.info(f"Archivo eliminado por antiguo: {filepath}")
                except OSError as e:
                    logger.error(f"Error al eliminar archivo {filepath}: {e}")
    except Exception as e:
        logger.error(f"Error en cleanup_old_files: {e}")

@lru_cache(maxsize=100)
def get_file_hash(file_path):
    """Calcula el hash MD5 de un archivo."""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        logger.error(f"Error calculando hash para {file_path}: {e}")
        return None

def get_last_download(user_id):
    """Obtiene la última descarga exitosa del usuario desde la base de datos."""
    try:
        with db.get_cursor() as cursor:
            query = """
                SELECT filename 
                FROM DOWNLOAD_HISTORY 
                WHERE user_id = %s AND status = 'success'
                ORDER BY download_date DESC 
                LIMIT 1
            """
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error al obtener última descarga: {e}")
        return None

def descargar_archivo(session_user, filename=None):
    """Descarga un archivo de música específico o el más reciente del usuario."""
    try:
        if not session_user or 'username' not in session_user:
            return jsonify({"error": "Usuario no autenticado"}), 401
            
        user_folder = get_user_folder(session_user)
        
        if filename:
            # Si se proporciona un nombre de archivo específico
            file_path = os.path.join(user_folder, filename)
            if not os.path.exists(file_path):
                return jsonify({"error": "Archivo no encontrado"}), 404
        else:
            # Obtener el último archivo descargado de la base de datos
            last_download = get_last_download(session_user['id'])
            
            if last_download:
                file_path = os.path.join(user_folder, last_download)
                if os.path.exists(file_path):
                    filename = last_download
                    logger.info(f"Último archivo descargado encontrado en DB: {filename}")
                else:
                    logger.warning(f"Archivo de DB no encontrado en disco: {last_download}")
            
            # Si no hay archivo en DB o no existe, buscar el más reciente en el sistema de archivos
            if not filename:
                if not os.path.exists(user_folder) or not os.listdir(user_folder):
                    return jsonify({"error": "No hay archivos disponibles"}), 404
                    
                archivos = [f for f in os.listdir(user_folder) if f.lower().endswith(('.mp3', '.m4a', '.wav'))]
                if not archivos:
                    return jsonify({"error": "No hay archivos de música disponibles"}), 404
                    
                # Obtener el archivo más reciente del sistema de archivos
                archivos.sort(key=lambda x: os.path.getmtime(os.path.join(user_folder, x)), reverse=True)
                filename = archivos[0]
                file_path = os.path.join(user_folder, filename)
                logger.info(f"Archivo más reciente encontrado en sistema de archivos: {filename}")

        # Verificar existencia y permisos
        if not os.path.exists(file_path):
            return jsonify({"error": "Archivo no encontrado"}), 404

        if not os.access(file_path, os.R_OK):
            return jsonify({"error": "Sin permiso para acceder al archivo"}), 403

        # Obtener tipo MIME correcto
        mime_type = mimetypes.guess_type(file_path)[0] or 'audio/mpeg'

        # Log para debugging
        logger.info(f"Enviando archivo: {file_path}")
        logger.info(f"Tipo MIME: {mime_type}")

        # Enviar el archivo
        return send_file(
            file_path,
            mimetype=mime_type,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error en descargar_archivo: {e}")
        return jsonify({"error": str(e)}), 500

def descargar_todo(session_user):
    try:
        user_folder = get_user_folder(session_user)
        logger.info(f"Preparando ZIP de la carpeta: {user_folder}")

        archivos = [f for f in os.listdir(user_folder) if f.lower().endswith(('.mp3', '.m4a', '.wav'))]
        if not archivos:
            return jsonify({"error": "No hay archivos de música para descargar"}), 404

        archivos.sort(key=lambda x: os.path.getmtime(os.path.join(user_folder, x)), reverse=True)
        
        total_size = sum(os.path.getsize(os.path.join(user_folder, f)) for f in archivos)
        if total_size > MAX_ZIP_SIZE:
            size_mb = total_size / (1024 * 1024)
            limit_mb = MAX_ZIP_SIZE / (1024 * 1024)
            return jsonify({
                "error": "El tamaño total excede el límite permitido",
                "size_mb": round(size_mb, 2),
                "limit_mb": round(limit_mb, 2),
                "suggestion": "Descargue los archivos individualmente o en grupos más pequeños"
            }), 413
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        username = session_user.get('username', 'user') if session_user else 'user'
        zip_name = f"music_{username}_{timestamp}.zip"
        
        temp_folder = os.path.join(DOWNLOAD_FOLDER, "temp")
        os.makedirs(temp_folder, exist_ok=True)
        zip_path = os.path.join(temp_folder, zip_name)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            total_files = len(archivos)
            for i, archivo in enumerate(archivos, 1):
                file_path = os.path.join(user_folder, archivo)
                try:
                    zipf.write(file_path, os.path.basename(file_path))
                    logger.info(f"Progreso: {i}/{total_files} - Añadido: {os.path.basename(file_path)}")
                except Exception as e:
                    logger.error(f"Error al comprimir {archivo}: {e}")

        if not os.path.exists(zip_path):
            return jsonify({"error": "Error al crear el archivo ZIP"}), 500

        # Obtener el tamaño final del ZIP
        zip_size = os.path.getsize(zip_path)
        logger.info(f"ZIP creado: {zip_name} ({zip_size / (1024*1024):.2f} MB)")

        response = send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_name,
            max_age=0
        )

        def cleanup_zip():
            try:
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                    logger.info(f"ZIP temporal eliminado: {zip_path}")
            except OSError as e:
                logger.error(f"Error al eliminar ZIP temporal {zip_path}: {e}")

        response.call_on_close(cleanup_zip)
        return response

    except Exception as e:
        logger.error(f"Error en descargar_todo: {e}")
        return jsonify({
            "error": "Error al crear el archivo ZIP",
            "details": str(e)
        }), 500