from flask import request, jsonify
import os
import subprocess
import yt_dlp
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import hashlib
import time
import shutil

# Configuración
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, "downloads")
CACHE_FOLDER = os.path.join(BASE_DIR, "cache")
FFMPEG_PATH = "/root/.spotdl/ffmpeg"
MAX_CACHE_AGE = 24 * 60 * 60  # 24 horas en segundos
MAX_WORKERS = 4

# Crear carpetas necesarias
os.makedirs(CACHE_FOLDER, exist_ok=True)

# Pool de hilos para descargas asíncronas
thread_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)

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
    """Configuración optimizada para yt-dlp con soporte para carátulas"""
    return {
        # Formato de audio
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": os.path.join(user_folder, "%(title)s.%(ext)s"),
        
        # Postprocesadores en orden
        "postprocessors": [
            {
                # Primero extraer el audio
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"
            },
            {
                # Luego descargar y embeber la miniatura
                "key": "EmbedThumbnail",
            },
            {
                # Finalmente, agregar metadatos
                "key": "FFmpegMetadata",
                "add_metadata": True,
            }
        ],
        
        
        "writethumbnail": True,        
        "embedthumbnail": True,       
        
        # Configuración general
        "ffmpeg_location": FFMPEG_PATH,
        "quiet": True,
        "no_warnings": True,
        "extract_audio": True,
        "audio_quality": 0,
        "nocheckcertificate": True,
        "ignoreerrors": True,
        "noplaylist": True,
        
        
        "parse_metadata": [
            "title:%(title)s",
            "artist:%(uploader)s",
            "album:%(album)s",
            "date:%(upload_date)s",
            "description:%(description)s",
            "comment:Downloaded with yt-dlp"
        ],
        "add_metadata": True           
    }

def download_file(url, user_folder, cache_path=None):
    """Función de descarga real"""
    ydl_opts = optimize_ydl_opts(user_folder)
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Encontrar el archivo descargado
        archivos = [f for f in os.listdir(user_folder) if f.endswith(".mp3")]
        if not archivos:
            raise Exception("No se encontró el archivo descargado")
            
        # Cachear el archivo si se proporcionó una ruta de caché
        if cache_path:
            shutil.copy2(os.path.join(user_folder, archivos[0]), cache_path)
            
        return archivos[0]
    except Exception as e:
        raise Exception(f"Error en la descarga: {str(e)}")

def download_ytdl(session_user):
    """Manejador principal de descargas de YouTube"""
    data = request.get_json()
    url = data.get("url")
    
    if not url:
        return jsonify({"error": "No se proporcionó una URL"}), 400

    user_id = session_user['username'] if session_user and 'username' in session_user else "anonymous"
    user_folder = get_user_folder(session_user)
    
    try:
        # Verificar caché
        cached_file = get_cached_download(url, user_id)
        if cached_file and os.path.exists(cached_file):
            shutil.copy2(cached_file, user_folder)
            filename = os.path.basename(cached_file)
            return jsonify({
                "message": "Archivo recuperado de caché",
                "file_url": f"/descargar/{filename}"
            }), 200

        # Limpiar archivos antiguos
        cleanup_old_files(CACHE_FOLDER, MAX_CACHE_AGE)
        
        # Iniciar descarga asíncrona
        cache_path = get_cache_path(url, user_id)
        future = thread_pool.submit(download_file, url, user_folder, cache_path)
        filename = future.result()
        
        return jsonify({
            "message": "Descarga completada",
            "file_url": f"/descargar/{filename}"
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error al descargar la canción: {str(e)}"}), 500

def download_spdl(session_user):
    """Manejador de descargas de Spotify"""
    try:
        print("[spotdl] Iniciando descarga de Spotify...")
        print(f"[spotdl] Datos de sesión: {session_user}")

        # Validar request
        if not request.is_json:
            return jsonify({"error": "Se requiere JSON en el request"}), 400

        data = request.get_json()
        url = data.get("url")
        print(f"[spotdl] URL recibida: {url}")
        
        if not url:
            return jsonify({"error": "No se proporcionó una URL"}), 400
            
        if not url.startswith(('https://open.spotify.com/', 'spotify:')):
            return jsonify({"error": "URL inválida. Debe ser una URL de Spotify"}), 400

        # Preparar directorio
        try:
            user_folder = get_user_folder(session_user)
            print(f"[spotdl] Carpeta del usuario: {user_folder}")
            if not os.path.exists(user_folder):
                os.makedirs(user_folder, exist_ok=True)
                print(f"[spotdl] Carpeta creada: {user_folder}")
        except Exception as e:
            print(f"[spotdl] Error al crear carpeta: {str(e)}")
            return jsonify({"error": f"No se pudo crear el directorio de usuario: {str(e)}"}), 500

        # Verificar que ffmpeg esté en el PATH
        ffmpeg_path = os.path.join(FFMPEG_PATH)
        print(f"[spotdl] Ruta de ffmpeg: {ffmpeg_path}")
        if not os.path.exists(ffmpeg_path):
            return jsonify({"error": f"ffmpeg no encontrado en {ffmpeg_path}"}), 500

        # Configurar el entorno para spotdl
        env = os.environ.copy()
        env["PATH"] = FFMPEG_PATH + os.pathsep + env.get("PATH", "")
        print(f"[spotdl] PATH actualizado: {env['PATH']}")

        # Verificar spotdl con el PATH actualizado
        try:
            print("[spotdl] Verificando instalación de spotdl...")
            version_process = subprocess.run(
                ["spotdl", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                check=True
            )
            print(f"[spotdl] Versión instalada: {version_process.stdout.strip()}")
        except subprocess.CalledProcessError as e:
            print(f"[spotdl] Error al verificar spotdl: {e.stderr}")
            return jsonify({
                "error": "Error al verificar spotdl",
                "details": e.stderr
            }), 500
        except FileNotFoundError as e:
            print(f"[spotdl] spotdl no encontrado: {str(e)}")
            return jsonify({"error": "spotdl no está instalado. Por favor, instale spotdl usando: pip install spotdl"}), 500

        # Iniciar proceso de descarga con configuración mejorada
        print(f"[spotdl] Iniciando descarga de: {url}")
        try:
            command = [
                "spotdl",
                url,
                "--output", user_folder,
                "--format", "mp3",
                "--bitrate", "320k",
                "--ffmpeg", ffmpeg_path,
                "--log-level", "DEBUG",
                "--paths", "{title}",
                "--restrict"
            ]
            print(f"[spotdl] Comando a ejecutar: {' '.join(command)}")
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True
            )
        except Exception as e:
            print(f"[spotdl] Error al iniciar el proceso: {str(e)}")
            return jsonify({"error": f"Error al iniciar el proceso de descarga: {str(e)}"}), 500
        
        try:
            stdout, stderr = process.communicate(timeout=120)  # 2 minutos de timeout
            print("Salida de spotdl:")
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            
            if process.returncode != 0:
                return jsonify({
                    "error": "Error en la descarga",
                    "stdout": stdout.strip(),
                    "stderr": stderr.strip()
                }), 500

            # Buscar archivo descargado
            archivos = [f for f in os.listdir(user_folder) if f.endswith(".mp3")]
            archivos.sort(key=lambda x: os.path.getmtime(os.path.join(user_folder, x)), reverse=True)
            
            if not archivos:
                return jsonify({
                    "error": "No se encontró el archivo descargado",
                    "stdout": stdout.strip(),
                    "stderr": stderr.strip(),
                    "files_in_directory": os.listdir(user_folder)
                }), 500

            return jsonify({
                "message": "Descarga completada",
                "file_url": f"/descargar/{archivos[0]}",
                "file_size": os.path.getsize(os.path.join(user_folder, archivos[0]))
            }), 200

        except subprocess.TimeoutExpired:
            process.kill()
            return jsonify({
                "error": "La descarga tomó demasiado tiempo (120 segundos)",
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
        
        return jsonify({
            "error": "Error al descargar la canción",
            "details": str(e),
            "suggestion": "Asegúrese de tener spotdl y ffmpeg instalados correctamente",
            "traceback": error_traceback
        }), 500
