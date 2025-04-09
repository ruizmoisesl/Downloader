from flask import send_file, jsonify
import os
import shutil
import zipfile
from datetime import datetime, timedelta
import hashlib
from functools import lru_cache
import mimetypes
import logging

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

def cleanup_old_files(folder, max_age=MAX_CACHE_AGE):
    """Elimina archivos más antiguos que max_age segundos."""
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

def descargar_archivo(session_user):
    """Descarga el archivo de música más reciente del usuario."""
    try:
        # Obtener todas las carpetas posibles donde podría estar el archivo
        carpetas_busqueda = [DOWNLOAD_FOLDER]  # Carpeta principal
        
        if session_user and len(session_user) > 1:
            user_folder = get_user_folder(session_user)
            carpetas_busqueda.append(user_folder)
            
        # Buscar archivos MP3 en todas las carpetas
        archivos_encontrados = []
        for carpeta in carpetas_busqueda:
            if os.path.exists(carpeta):
                archivos = [f for f in os.listdir(carpeta) 
                           if f.lower().endswith('.mp3')]
                archivos_encontrados.extend(
                    [(f, os.path.getmtime(os.path.join(carpeta, f)), carpeta) 
                     for f in archivos]
                )
        
        if not archivos_encontrados:
            return jsonify({
                "error": "No hay archivos de música disponibles",
                "carpetas_buscadas": carpetas_busqueda
            }), 404

        # Ordenar por fecha de modificación y obtener el más reciente
        archivo_info = max(archivos_encontrados, key=lambda x: x[-1])
        nombre_archivo, _, carpeta = archivo_info
        file_path = os.path.join(carpeta, nombre_archivo)

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
        response = send_file(
            file_path,
            mimetype=mime_type,
            as_attachment=True,
            download_name=nombre_archivo
        )
        
        # Asegurar que no se interprete como JSON
        response.headers['Content-Type'] = mime_type
        return response

    except Exception as e:
        logger.error(f"Error en descargar_archivo: {e}")
        return jsonify({"error": str(e)}), 500

def descargar_todo(session_user):
    """Descarga todos los archivos del usuario en un ZIP manteniendo los originales."""
    try:
        # Obtener carpeta del usuario
        user_folder = get_user_folder(session_user)
        logger.info(f"Preparando ZIP de la carpeta: {user_folder}")

        # Verificar si hay archivos para comprimir
        archivos = [f for f in os.listdir(user_folder) if f.lower().endswith(('.mp3', '.m4a', '.wav'))]
        if not archivos:
            return jsonify({"error": "No hay archivos de música para descargar"}), 404

        # Ordenar archivos por fecha de modificación (más recientes primero)
        archivos.sort(key=lambda x: os.path.getmtime(os.path.join(user_folder, x)), reverse=True)
        
        # Calcular tamaño total
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

        # Crear nombre único para el ZIP incluyendo el nombre de usuario si está disponible
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        username = session_user.get('username', 'user') if session_user else 'user'
        zip_name = f"music_{username}_{timestamp}.zip"
        
        # Crear el ZIP en una carpeta temporal
        temp_folder = os.path.join(DOWNLOAD_FOLDER, "temp")
        os.makedirs(temp_folder, exist_ok=True)
        zip_path = os.path.join(temp_folder, zip_name)

        # Crear archivo ZIP con barra de progreso en el log
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            total_files = len(archivos)
            for i, archivo in enumerate(archivos, 1):
                file_path = os.path.join(user_folder, archivo)
                try:
                    # Guardar el archivo en el ZIP con su nombre original
                    zipf.write(file_path, os.path.basename(file_path))
                    logger.info(f"Progreso: {i}/{total_files} - Añadido: {os.path.basename(file_path)}")
                except Exception as e:
                    logger.error(f"Error al comprimir {archivo}: {e}")

        if not os.path.exists(zip_path):
            return jsonify({"error": "Error al crear el archivo ZIP"}), 500

        # Obtener el tamaño final del ZIP
        zip_size = os.path.getsize(zip_path)
        logger.info(f"ZIP creado: {zip_name} ({zip_size / (1024*1024):.2f} MB)")

        # Programar eliminación del ZIP temporal después de la descarga
        def cleanup_zip():
            try:
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                    logger.info(f"ZIP temporal eliminado: {zip_path}")
            except OSError as e:
                logger.error(f"Error al eliminar ZIP temporal {zip_path}: {e}")

        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_name,
            max_age=0
        )

    except Exception as e:
        logger.error(f"Error en descargar_todo: {e}")
        return jsonify({
            "error": "Error al crear el archivo ZIP",
            "details": str(e)
        }), 500