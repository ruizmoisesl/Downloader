from flask import Flask
from routes import index, download, downs, interfaces
import os


app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def limpiar_carpeta():
    for archivo in os.listdir(DOWNLOAD_FOLDER):
        archivo_path = os.path.join(DOWNLOAD_FOLDER, archivo)
        if os.path.isfile(archivo_path):
            os.remove(archivo_path)

@app.route("/")
def index_route():
    limpiar_carpeta()
    return index.index()

@app.route('/spotify-downloader', methods=["GET", "POST"])
def spotify_downloader():
    return interfaces.spotify()

@app.route('/youtube-downloader', methods=["GET", "POST"])
def youtube_downloader():
    return interfaces.youtube()

@app.route('/soundcloud-downloader', methods=["GET", "POST"])
def method_name():
    return interfaces.soundcloud()

@app.route("/download-spdl", methods=["POST"])
def download_route():
    return download.download_spdl()

@app.route('/download-ytdl', methods=["POST"])
def download_youtube():
    return download.download_ytdl()

@app.route("/descargar/<filename>")
def descargar_archivo(filename):
    return downs.descargar_archivo(filename)

@app.route("/descargar_todo")
def descargar_todo():
    return downs.descargar_todo()

if __name__ == "__main__":
    app.run(debug=True)
