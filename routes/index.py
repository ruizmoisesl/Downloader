from flask import Flask, render_template, request, jsonify, send_file, session
import os


DOWNLOAD_FOLDER = 'downloads'

def limpiar_carpeta():
    for archivo in os.listdir(DOWNLOAD_FOLDER):
        archivo_path = os.path.join(DOWNLOAD_FOLDER, archivo)
        if os.path.isfile(archivo_path):
            os.remove(archivo_path)

def index():
    session_user = session.get('user')
    if session_user:
        # Crear carpeta personal del usuario si no existe
        user_folder = os.path.join(DOWNLOAD_FOLDER, session_user['username'])
        os.makedirs(user_folder, exist_ok=True)
    
    return render_template('index.html', session_user=session_user)