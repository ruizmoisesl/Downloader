from flask import Flask, render_template, request, jsonify, send_file
import subprocess
import os
import shutil

DOWNLOAD_FOLDER = "downloads"
FFMPEG_PATH = os.path.abspath(os.path.join("ffmpeg","bin","ffmpeg.exe"))

def download_spdl():
    data = request.get_json()
    url = data.get("url")

    if not url:
        return jsonify({"error": "No se proporcionó una URL"}), 400

    try:
        subprocess.run(["spotdl", url, "--output", DOWNLOAD_FOLDER], check=True)
        archivos = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.endswith(".mp3")]
        if not archivos:
            return jsonify({"error": "No se encontró el archivo descargado"}), 500

        archivo_mp3 = archivos[0]
        return jsonify({
            "message": "Descarga completada",
            "file_url": f"/descargar/{archivo_mp3}"
        }), 200

    except subprocess.CalledProcessError:
        return jsonify({"error": "Error al descargar la canción"}), 500
    
def download_ytdl():
    data = request.get_json()
    url = data.get("url")

    if not url:
        return jsonify({"error": "No se proporcionó una URL"}), 400

    try:
        subprocess.run(["yt-dlp", "-P", DOWNLOAD_FOLDER, "-x", "--audio-format", "mp3","--ffmpeg-location",FFMPEG_PATH,url], check=True)
        archivos = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.endswith(".mp3")]
        if not archivos:
            return jsonify({"error": "No se encontró el archivo descargado"}), 500

        archivo_mp3 = archivos[0]
        return jsonify({
            "message": "Descarga completada",
            "file_url": f"/descargar/{archivo_mp3}"
        }), 200

    except subprocess.CalledProcessError:
        return jsonify({"error": "Error al descargar la canción"}), 500