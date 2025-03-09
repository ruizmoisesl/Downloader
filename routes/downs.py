from flask import Flask, render_template, request, jsonify, send_file
import os
import shutil

DOWNLOAD_FOLDER = "downloads"

def descargar_archivo(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "Archivo no encontrado", 404

def descargar_todo():
    zip_path = "downloads.zip"
    shutil.make_archive("downloads", "zip", DOWNLOAD_FOLDER)
    return send_file(zip_path, as_attachment=True)