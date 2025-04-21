from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
from database.core import DatabaseManager, DatabaseError
from datetime import datetime
import os
from routes.downs import clear_user_folder

# Obtener la instancia global del DatabaseManager
db = DatabaseManager()
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

logger = logging.getLogger(__name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in first', 'error')
            return redirect(url_for('index_route'))
        return f(*args, **kwargs)
    return decorated_function

def register():
    # Si el usuario ya está logueado, redirigir al inicio
    if 'user' in session:
        flash('Ya tienes una sesión iniciada', 'info')
        return redirect(url_for('index_route'))

    if request.method == 'GET':
        return render_template('register.html')

    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('password2', '')

            # Validaciones de campos vacíos
            if not username:
                flash('Por favor ingresa un nombre de usuario', 'error')
                return redirect(url_for('register_route'))
            
            if not email:
                flash('Por favor ingresa un correo electrónico', 'error')
                return redirect(url_for('register_route'))
                
            if not password:
                flash('Por favor ingresa una contraseña', 'error')
                return redirect(url_for('register_route'))
                
            if not confirm_password:
                flash('Por favor confirma tu contraseña', 'error')
                return redirect(url_for('register_route'))

            # Validación de longitud de usuario
            if len(username) < 3:
                flash('El nombre de usuario debe tener al menos 3 caracteres', 'error')
                return redirect(url_for('register_route'))

            # Validación de formato de email
            if '@' not in email or '.' not in email:
                flash('Por favor ingresa un correo electrónico válido', 'error')
                return redirect(url_for('register_route'))

            # Validación de contraseñas
            if password != confirm_password:
                flash('Las contraseñas no coinciden', 'error')
                return redirect(url_for('register_route'))

            if len(password) < 8:
                flash('La contraseña debe tener al menos 8 caracteres', 'error')
                return redirect(url_for('register_route'))

            # Verificar si el nombre de usuario ya existe
            existing_username = db.execute_query(
                "SELECT id FROM USER WHERE username = %s",
                (username,),
                fetch_one=True
            )

            if existing_username:
                flash('El nombre de usuario ya está en uso. Por favor, elige otro.', 'error')
                return redirect(url_for('register_route'))

            # Verificar si el email ya existe
            existing_email = db.execute_query(
                "SELECT id FROM USER WHERE email = %s",
                (email,),
                fetch_one=True
            )

            if existing_email:
                flash('Este correo electrónico ya está registrado. ¿Olvidaste tu contraseña?', 'error')
                return redirect(url_for('register_route'))

            # Hash del password
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

            try:
                # Insertar nuevo usuario
                db.execute_query(
                    "INSERT INTO USER (username, email, password) VALUES (%s, %s, %s)",
                    (username, email, hashed_password)
                )

                # Obtener el usuario recién creado
                user = db.execute_query(
                    "SELECT id, username, email FROM USER WHERE username = %s",
                    (username,),
                    fetch_one=True
                )

                if user:
                    # Convertir la tupla en un diccionario
                    user_dict = {
                        'id': user[0],
                        'username': user[1],
                        'email': user[2]
                    }
                    flash('¡Cuenta creada exitosamente! Bienvenido/a.', 'success')
                    session['user'] = user_dict
                    return redirect(url_for('index_route'))
                else:
                    raise DatabaseError('No se pudo obtener el usuario después de crearlo')

            except DatabaseError as e:
                logger.error(f"Error al insertar nuevo usuario: {e}")
                flash('Error al crear la cuenta. Por favor, inténtalo de nuevo.', 'error')
                return redirect(url_for('register_route'))

        except DatabaseError as e:
            logger.error(f"Error de base de datos durante el registro: {e}")
            flash('Ocurrió un error al crear tu cuenta. Por favor, inténtalo de nuevo.', 'error')
            return redirect(url_for('register_route'))
        except Exception as e:
            logger.error(f"Error inesperado durante el registro: {e}")
            flash('Ocurrió un error inesperado. Por favor, inténtalo de nuevo.', 'error')
            return redirect(url_for('register_route'))

    return render_template('register.html')

def login():
    # Si el usuario ya está logueado, redirigir al inicio
    if 'user' in session:
        # Limpiar la carpeta del usuario actual antes de redirigir
        clear_user_folder(session['user'])
        flash('Ya tienes una sesión iniciada', 'info')
        return redirect(url_for('index_route'))

    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

            if not username:
                flash('Por favor ingresa tu nombre de usuario', 'error')
                return redirect(url_for('index_route'))

            if not password:
                flash('Por favor ingresa tu contraseña', 'error')
                return redirect(url_for('index_route'))

            # Buscar usuario
            result = db.execute_query(
                "SELECT id, username, email, password FROM USER WHERE username = %s",
                (username,),
                fetch_one=True
            )

            if not result:
                flash('Usuario o contraseña incorrectos', 'error')
                return redirect(url_for('index_route'))

            # Verificar contraseña
            if check_password_hash(result[3], password):
                # Crear la sesión del usuario
                user_data = {
                    'id': result[0],
                    'username': result[1],
                    'email': result[2]
                }
                
                # Limpiar la carpeta del usuario antes de iniciar sesión
                clear_user_folder(user_data)
                
                session['user'] = user_data
                
                flash('¡Bienvenido!', 'success')
                return redirect(url_for('index_route'))
            else:
                flash('Usuario o contraseña incorrectos', 'error')
                return redirect(url_for('index_route'))

        except DatabaseError as e:
            logger.error(f"Error de base de datos durante el login: {e}")
            flash('Ocurrió un error al iniciar sesión. Por favor, inténtalo de nuevo.', 'error')
            return redirect(url_for('index_route'))
        except Exception as e:
            logger.error(f"Error inesperado durante el login: {e}")
            flash('Ocurrió un error inesperado. Por favor, inténtalo de nuevo.', 'error')
            return redirect(url_for('index_route'))

    return render_template('login.html')

def logout():
    # Limpiar la carpeta del usuario antes de cerrar sesión
    if 'user' in session:
        clear_user_folder(session['user'])
    
    # Cerrar sesión de usuario
    session.pop('user', None)
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('index_route'))