from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
from database.core import DatabaseManager, DatabaseError
from datetime import datetime
import os

# Obtener la instancia global del DatabaseManager
db = DatabaseManager()
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

logger = logging.getLogger(__name__)

def login_required(f):
    """Decorador para proteger rutas que requieren autenticación"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in first', 'error')
            return redirect(url_for('login_route'))
        return f(*args, **kwargs)
    return decorated_function

def register():
    """Registrar un nuevo usuario"""
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('password2')

            # Validaciones
            if not all([username, email, password, confirm_password]):
                flash('All fields are required', 'error')
                return redirect(url_for('index_route'))

            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return redirect(url_for('index_route'))

            if len(password) < 8:
                flash('Password must be at least 8 characters long', 'error')
                return redirect(url_for('index_route'))

            # Verificar si el usuario ya existe
            existing_user = db.execute_query(
                "SELECT id FROM USER WHERE username = %s OR email = %s",
                (username, email)
            )

            if existing_user:
                flash('Username or email already exists', 'error')
                return redirect(url_for('index_route'))

            # Hash del password
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

            # Insertar nuevo usuario
            db.execute_query(
                "INSERT INTO USER (username, email, password) VALUES (%s, %s, %s)",
                (username, email, hashed_password)
            )

            # Obtener el usuario recién creado
            user = db.execute_query(
                "SELECT id, username, email FROM USER WHERE username = %s",
                (username,)
            )[0]

            flash('Account created successfully', 'success')
            session['user'] = user
            return redirect(url_for('index_route'))

        except DatabaseError as e:
            logger.error(f"Database error during registration: {e}")
            flash('An error occurred during registration', 'error')
            return redirect(url_for('index_route'))
        except Exception as e:
            logger.error(f"Unexpected error during registration: {e}")
            flash('An unexpected error occurred', 'error')
            return redirect(url_for('index_route'))

    return render_template('register.html')

def login():
    """Iniciar sesión de usuario"""
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')

            if not all([username, password]):
                flash('Username and password are required', 'error')
                return redirect(url_for('index_route'))

            # Buscar usuario
            result = db.execute_query(
                "SELECT id, username, email, password FROM USER WHERE username = %s",
                (username,)
            )

            if not result or len(result) == 0:
                flash('Invalid username or password', 'error')
                return redirect(url_for('index_route'))

            user = result[0]  # Obtener el primer resultado
            
            # Verificar que tenemos todos los campos necesarios
            required_fields = ['id', 'username', 'email', 'password']
            if not all(field in user for field in required_fields):
                logger.error(f"Missing required fields in user data: {user}")
                flash('An error occurred during login', 'error')
                return redirect(url_for('index_route'))

            # Verificar password
            if not check_password_hash(user['password'], password):
                flash('Invalid username or password', 'error')
                return redirect(url_for('index_route'))

            try:
                # Actualizar último login
                db.execute_query(
                    "UPDATE USER SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
                    (user['id'],)
                )

                # Eliminar el hash del password antes de guardarlo en sesión
                user.pop('password', None)

                # Crear datos de sesión
                session_data = {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'logged_in': True,
                    'login_time': datetime.now().isoformat()
                }

                # Guardar en la sesión de Flask
                session['user'] = session_data
                
                # Crear carpeta personal del usuario si no existe
                user_folder = os.path.join('downloads', user['username'])
                os.makedirs(user_folder, exist_ok=True)

                flash(f'Welcome back, {user["username"]}!', 'success')
                return redirect(url_for('index_route'))

            except Exception as e:
                logger.error(f"Error setting up user session: {e}")
                flash('An error occurred during login', 'error')
                return redirect(url_for('index_route'))

        except DatabaseError as e:
            logger.error(f"Database error during login: {e}")
            flash('An error occurred during login', 'error')
            return redirect(url_for('index_route'))
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            flash('An unexpected error occurred', 'error')
            return redirect(url_for('index_route'))

    return render_template('login.html')

def logout():
    """Cerrar sesión de usuario"""
    session.pop('user', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index_route'))