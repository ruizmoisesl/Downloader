from flask import Flask, session, redirect, url_for,flash
from routes import index, download, downs, interfaces, sessions
import os


app = Flask(__name__)
app.secret_key = 'JODIAJEOIHDEUAHDOIHEAOUFHKALBAGCLIGFULE'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def limpiar_carpeta():
    for archivo in os.listdir(DOWNLOAD_FOLDER):
        archivo_path = os.path.join(DOWNLOAD_FOLDER, archivo)
        if os.path.isfile(archivo_path):
            os.remove(archivo_path)

@app.route("/")
def index_route():
    return index.index()

@app.route('/register', methods=["GET", "POST"])
def register_route():
    return sessions.register()

@app.route('/login', methods=["GET", "POST"])
def login_route():
    return sessions.login()

@app.route('/logout')
def logout_route():
    if 'user' in session:
        session.pop('user', None)
        flash('Logged out successfully')
    return redirect(url_for('index_route'))
    
@app.route('/spotify-downloader', methods=["GET", "POST"])
def spotify_downloader():
    return interfaces.spotify()

@app.route('/youtube-downloader', methods=["GET", "POST"])
def youtube_downloader():
    return interfaces.youtube()

@app.route('/soundcloud-downloader', methods=["GET", "POST"])
def soundcloud_route():
    session_user = session.get('user')
    return interfaces.soundcloud(session_user= session_user)

@app.route("/download-spdl", methods=["POST"])
def download_route():
    session_user = session.get('user')
    return download.download_spdl(session_user)

@app.route('/download-ytdl', methods=["POST"])
def download_youtube():
    session_user = session.get('user')
    return download.download_ytdl(session_user)

@app.route("/descargar")
def descargar_archivo():
    session_user = session.get('user')
    return downs.descargar_archivo(session_user)

@app.route("/descargar_todo")
def descargar_todo():
    session_user = session.get('user')
    return downs.descargar_todo(session_user)

if __name__ == "__main__":
    app.run(debug=True)
