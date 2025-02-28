from flask import Flask, render_template, request, jsonify, send_file
import subprocess
import os
import shutil

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def limpiar_carpeta():
    for archivo in os.listdir(DOWNLOAD_FOLDER):
        archivo_path = os.path.join(DOWNLOAD_FOLDER, archivo)
        if os.path.isfile(archivo_path):
            os.remove(archivo_path)

@app.route("/")
def index():
    limpiar_carpeta()
    return render_template("index.html")

@app.route("/download", methods=["POST"])
def download():
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

@app.route("/descargar/<filename>")
def descargar_archivo(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "Archivo no encontrado", 404

@app.route("/descargar_todo")
def descargar_todo():
    zip_path = "downloads.zip"
    shutil.make_archive("downloads", "zip", DOWNLOAD_FOLDER)
    return send_file(zip_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
