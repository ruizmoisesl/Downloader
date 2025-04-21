from flask import request, jsonify
import os
import subprocess
import yt_dlp
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import hashlib
import time
import shutil
import logging
from database.core import db
from typing import Dict, List, Optional
from datetime import datetime

# Configuración del logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, "downloads")
CACHE_FOLDER = os.path.join(BASE_DIR, "cache")
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.txt")

# Configuración de FFmpeg
FFMPEG_BIN = "/bin/ffmpeg"
FFMPEG_PATH = os.path.join(FFMPEG_BIN)

# Configurar el PATH para incluir FFmpeg
os.environ["PATH"] = FFMPEG_BIN + os.pathsep + os.environ.get("PATH", "")
os.environ["FFMPEG_PATH"] = FFMPEG_PATH

MAX_CACHE_AGE = 24 * 60 * 60  # 24 horas en segundos
MAX_WORKERS = 4

# Crear carpetas necesarias
os.makedirs(CACHE_FOLDER, exist_ok=True)

# Pool de hilos para descargas asíncronas
thread_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# Funciones para el historial de descargas
def register_new_download(user_id: int, url: str, filename: str = "", status: str = 'success', error_message: str = None) -> int:
    """Registra una descarga en el historial"""
    try:
        return db.register_download(user_id, url, filename, status, error_message)
    except Exception as e:
        logger.error(f"Error al registrar descarga: {e}")
        return None

def register_download_error(download_id: int, error_message: str) -> bool:
    """Actualiza el registro de descarga con un error"""
    try:
        download = db.get_download_by_id(download_id)
        if download:
            return db.register_download(
                download['user_id'],
                download['url'],
                download['filename'],
                'failed',
                error_message
            )
        return False
    except Exception:
        return False

def get_user_download_history(user_id: int, page: int = 1, per_page: int = 10) -> List[Dict]:
    """Obtiene el historial de descargas de un usuario con paginación"""
    offset = (page - 1) * per_page
    try:
        downloads = db.get_user_downloads(user_id, per_page, offset)
        return downloads
    except Exception:
        return []

def get_download_stats(user_id: int) -> Dict:
    """Obtiene estadísticas de descargas del usuario"""
    try:
        stats = db.get_download_stats(user_id)
        return stats or {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0
        }
    except Exception:
        return {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0
        }

def clear_user_download_history(user_id: int, download_id: Optional[int] = None) -> bool:
    """Limpia el historial de descargas de un usuario"""
    try:
        return db.delete_download_history(user_id, download_id)
    except Exception:
        return False

def get_cache_path(url, user_id):
    """Genera una ruta única para cachear el archivo"""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return os.path.join(CACHE_FOLDER, f"{user_id}_{url_hash}.mp3")

def cleanup_old_files(folder, max_age):
    """Elimina archivos más antiguos que max_age segundos"""
    current_time = time.time()
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        if os.path.getmtime(filepath) < current_time - max_age:
            try:
                os.remove(filepath)
            except OSError:
                pass

def get_user_folder(session_user):
    """Obtiene y crea la carpeta del usuario si no existe
    
    Args:
        session_user: Diccionario con los datos del usuario
    """
    if session_user and 'username' in session_user:
        user_folder = os.path.join(DOWNLOAD_FOLDER, session_user['username'])
    else:
        user_folder = DOWNLOAD_FOLDER
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

@lru_cache(maxsize=100)
def get_cached_download(url, user_id):
    """Verifica si la URL ya está cacheada"""
    cache_path = get_cache_path(url, user_id)
    if os.path.exists(cache_path):
        return cache_path
    return None

def optimize_ydl_opts(user_folder):
    """Configuración optimizada para yt-dlp con soporte para carátulas y anti-bot"""
    return {
        # Formato de audio
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": os.path.join(user_folder, "%(title)s.%(ext)s"),
        
        # Procesadores de post-descarga
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"
            },
            {   
                "key": "FFmpegMetadata",
                "add_metadata": True,
            },
            {
                "key": "EmbedThumbnail",
                "already_have_thumbnail": False,
            }
        ],
        
        # Manejo de miniaturas
        "writethumbnail": True,
        "embedthumbnail": True,
        "update_thumbnail": True,
        "write_thumbnail": True,
        
        # Configuración de FFmpeg
        "ffmpeg_location": FFMPEG_PATH,
        
        # Configuración anti-bot y optimizaciones
        "quiet": True,
        "no_warnings": True,
        "extract_audio": True,
        "audio_quality": 0,
        "nocheckcertificate": True,
        "ignoreerrors": True,
        "noplaylist": True,
        "cookiefile": COOKIES_FILE,  # Usar archivo de cookies personalizado
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-us,en;q=0.5",
            "Sec-Fetch-Mode": "navigate"
        },
        
        # Metadatos
        "parse_metadata": [
            "title:%(title)s",
            "artist:%(uploader)s",
            "album:%(album)s",
            "date:%(upload_date)s",
            "description:%(description)s",
            "comment:Downloaded with MRZDOWNLOADER"
        ],
        "add_metadata": True,
        "embed_metadata": True,
        "write_info_json": True,
        
        # Configuración de red
        "socket_timeout": 30,
        "retries": 10,
        "fragment_retries": 10,
        "skip_unavailable_fragments": True,
        "hls_prefer_native": True
    }

def download_file(url, user_folder, cache_path=None, user_id=None, download_id=None):
    """Función de descarga real"""
    ydl_opts = optimize_ydl_opts(user_folder)
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
       
        archivos = [f for f in os.listdir(user_folder) if f.endswith(".mp3")]
        if not archivos:
            error_msg = "No se encontró el archivo descargado"
            if download_id:
                register_download_error(download_id, error_msg)
            raise Exception(error_msg)
            
        
        if cache_path:
            shutil.copy2(os.path.join(user_folder, archivos[0]), cache_path)
            
        return archivos[0]
    except Exception as e:
        error_msg = f"Error en la descarga: {str(e)}"
        if download_id:
            register_download_error(download_id, error_msg)
        raise Exception(error_msg)

def download_ytdl(session_user):
    """Manejador principal de descargas de YouTube"""
    data = request.get_json()
    url = data.get("url")
    
    if not url:
        return jsonify({"error": "No se proporcionó una URL"}), 400
        
    if not session_user or 'id' not in session_user:
        return jsonify({"error": "Usuario no autenticado"}), 401

    user_id = session_user['username'] if session_user and 'username' in session_user else "anonymous"
    user_folder = get_user_folder(session_user)
    
    try:
        # Verificar caché
        cached_file = get_cached_download(url, user_id)
        if cached_file and os.path.exists(cached_file):
            shutil.copy2(cached_file, user_folder)
            filename = os.path.basename(cached_file)
            # Registrar descarga desde caché
            register_new_download(session_user['id'], url, filename)
            return jsonify({
                "message": "Archivo recuperado de caché",
                "file_url": f"/descargar/{filename}"
            }), 200

        # Limpiar archivos antiguos
        cleanup_old_files(CACHE_FOLDER, MAX_CACHE_AGE)
        
        # Registrar inicio de descarga
        download_id = register_new_download(session_user['id'], url)
        
        # Iniciar descarga asíncrona
        cache_path = get_cache_path(url, user_id)
        future = thread_pool.submit(download_file, url, user_folder, cache_path, session_user['id'], download_id)
        filename = future.result()
        
        # Actualizar registro con nombre de archivo final
        register_new_download(session_user['id'], url, filename, 'success')
        
        return jsonify({
            "message": "Descarga completada",
            "file_url": f"/descargar/{filename}"
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error al descargar la canción: {str(e)}"}), 500

def download_spdl(session_user):
    """Manejador de descargas de Spotify"""
    try:
        logger.info("[spotdl] Iniciando descarga de Spotify...")
        logger.info(f"[spotdl] Datos de sesión: {session_user}")
        
        if not session_user or 'id' not in session_user:
            return jsonify({"error": "Usuario no autenticado"}), 401
        
        if not session_user or 'id' not in session_user:
            return jsonify({"error": "Usuario no autenticado"}), 401

        # Validar request
        if not request.is_json:
            return jsonify({"error": "Se requiere JSON en el request"}), 400

        data = request.get_json()
        url = data.get("url")
        logger.info(f"[spotdl] URL recibida: {url}")
        
        if not url:
            error_msg = "No se proporcionó una URL"
            register_new_download(session_user['id'], "", "", 'failed', error_msg)
            return jsonify({"error": error_msg}), 400
            
        if not url.startswith(('https://open.spotify.com/', 'spotify:')):
            error_msg = "URL inválida. Debe ser una URL de Spotify"
            register_new_download(session_user['id'], url, "", 'failed', error_msg)
            return jsonify({"error": error_msg}), 400

        # Preparar directorio
        try:
            user_folder = get_user_folder(session_user)
            logger.info(f"[spotdl] Carpeta del usuario: {user_folder}")
            if not os.path.exists(user_folder):
                os.makedirs(user_folder, exist_ok=True)
                logger.info(f"[spotdl] Carpeta creada: {user_folder}")
        except Exception as e:
            error_msg = f"No se pudo crear el directorio de usuario: {str(e)}"
            logger.error(f"[spotdl] Error al crear carpeta: {str(e)}")
            register_new_download(session_user['id'], url, "", 'failed', error_msg)
            return jsonify({"error": error_msg}), 500

        # Verificar que ffmpeg esté en el PATH
        ffmpeg_path = os.path.join(FFMPEG_PATH)
        logger.info(f"[spotdl] Ruta de ffmpeg: {ffmpeg_path}")
        if not os.path.exists(ffmpeg_path):
            error_msg = f"ffmpeg no encontrado en {ffmpeg_path}"
            register_new_download(session_user['id'], url, "", 'failed', error_msg)
            return jsonify({"error": error_msg}), 500

        # Registrar inicio de descarga
        download_id = register_new_download(session_user['id'], url)
        
        # Verificar que ffmpeg existe
        if not os.path.exists(FFMPEG_PATH):
            error_msg = f"ffmpeg no encontrado en {FFMPEG_PATH}"
            register_new_download(session_user['id'], url, "", 'failed', error_msg)
            return jsonify({"error": error_msg}), 500
            
        # Configurar el entorno para spotdl
        env = os.environ.copy()
        env["FFMPEG_PATH"] = FFMPEG_PATH
        logger.info(f"[spotdl] FFMPEG_PATH configurado: {env['FFMPEG_PATH']}")

        # Verificar spotdl con el PATH actualizado
        try:
            logger.info("[spotdl] Verificando instalación de spotdl...")
            version_process = subprocess.run(
                ["spotdl", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                check=True
            )
            logger.info(f"[spotdl] Versión instalada: {version_process.stdout.strip()}")
        except subprocess.CalledProcessError as e:
            error_msg = f"Error al verificar spotdl: {e.stderr}"
            logger.error(f"[spotdl] {error_msg}")
            register_new_download(session_user['id'], url, "", 'failed', error_msg)
            return jsonify({
                "error": error_msg,
                "details": e.stderr
            }), 500
        except FileNotFoundError as e:
            error_msg = "spotdl no está instalado. Por favor, instale spotdl usando: pip install spotdl"
            logger.error(f"[spotdl] {error_msg}: {str(e)}")
            register_new_download(session_user['id'], url, "", 'failed', error_msg)
            return jsonify({"error": error_msg}), 500

        # Iniciar proceso de descarga con configuración mejorada
        logger.info(f"[spotdl] Iniciando descarga de: {url}")
        try:
            command = [
                "spotdl",
                url,
                "--output", user_folder,
                "--format", "mp3",
                "--ffmpeg", FFMPEG_PATH,
                "--bitrate", "320k"
            ]
            logger.info(f"[spotdl] Comando a ejecutar: {' '.join(command)}")
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True
            )
        except Exception as e:
            error_msg = f"Error al iniciar el proceso de descarga: {str(e)}"
            logger.error(f"[spotdl] Error al iniciar el proceso: {str(e)}")
            register_new_download(session_user['id'], url, "", 'failed', error_msg)
            return jsonify({"error": error_msg}), 500
        
        try:
            stdout, stderr = process.communicate(timeout=120)  # 2 minutos de timeout
            logger.info("Salida de spotdl:")
            logger.info(f"STDOUT: {stdout}")
            logger.info(f"STDERR: {stderr}")
            
            # Verificar si hay error de FFmpeg
            if "FFmpegError:" in stdout:
                error_msg = "Error de FFmpeg durante la conversión"
                error_details = stdout.strip()
                logger.error(f"[spotdl] {error_msg}: {error_details}")
                register_new_download(session_user['id'], url, "", 'failed', f"{error_msg}\n{error_details}")
                return jsonify({
                    "error": error_msg,
                    "details": error_details,
                    "suggestion": "Verifica que FFmpeg esté correctamente instalado y configurado"
                }), 500
            
            # Verificar otros errores
            if process.returncode != 0:
                error_msg = "Error en la descarga"
                error_details = f"STDOUT: {stdout.strip()}\nSTDERR: {stderr.strip()}"
                logger.error(f"[spotdl] {error_msg}: {error_details}")
                register_new_download(session_user['id'], url, "", 'failed', f"{error_msg}\n{error_details}")
                return jsonify({
                    "error": error_msg,
                    "stdout": stdout.strip(),
                    "stderr": stderr.strip()
                }), 500

            # Buscar archivo descargado
            archivos = [f for f in os.listdir(user_folder) if f.endswith(".mp3")]
            archivos.sort(key=lambda x: os.path.getmtime(os.path.join(user_folder, x)), reverse=True)
            
            if not archivos:
                error_msg = "No se encontró el archivo descargado"
                # Registrar error en la base de datos
                register_new_download(session_user['id'], url, "", 'failed', error_msg)
                return jsonify({
                    "error": error_msg,
                    "stdout": stdout.strip(),
                    "stderr": stderr.strip(),
                    "files_in_directory": os.listdir(user_folder)
                }), 500

            # Registrar descarga exitosa
            register_new_download(session_user['id'], url, archivos[0])
            
            filename = archivos[0]
            return jsonify({
                "message": "Descarga completada",
                "file_url": f"/descargar/{filename}",
                "filename": filename,
                "file_size": os.path.getsize(os.path.join(user_folder, filename))
            }), 200

        except subprocess.TimeoutExpired:
            process.kill()
            error_msg = "La descarga tomó demasiado tiempo (120 segundos)"
            # Registrar error de timeout
            register_new_download(session_user['id'], url, "", 'failed', error_msg)
            return jsonify({
                "error": error_msg,
                "suggestion": "Intenta con una canción individual en lugar de una playlist"
            }), 500
            
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print("[spotdl] Error completo en download_spdl:")
        print(error_traceback)
        
        # Verificar el estado de spotdl
        try:
            subprocess.run(["spotdl", "--version"], check=True)
        except Exception as spotdl_error:
            print(f"[spotdl] Error adicional al verificar spotdl: {str(spotdl_error)}")
        
        # Verificar el estado de ffmpeg
        try:
            subprocess.run([os.path.join(FFMPEG_PATH), "-version"], check=True)
        except Exception as ffmpeg_error:
            print(f"[spotdl] Error adicional al verificar ffmpeg: {str(ffmpeg_error)}")
        
        error_msg = f"Error al descargar la canción: {str(e)}"
        # Registrar error general
        register_new_download(session_user['id'], url, "", 'failed', error_msg)
        return jsonify({
            "error": error_msg,
            "details": str(e),
            "suggestion": "Asegúrese de tener spotdl y ffmpeg instalados correctamente",
            "traceback": error_traceback
        }), 500
