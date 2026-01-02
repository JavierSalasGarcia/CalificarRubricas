"""
Sistema de Calificaciones - Plataforma Web
Estilo: Starlink Hi-Tech Minimalista Oscuro

Servidor Flask para gestión de calificaciones académicas
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
import json
from pathlib import Path
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_super_segura_cambiar_en_produccion'  # Cambiar en producción

# Configuración
CREDENTIALS_PATH = Path(__file__).parent.parent / "credentials.json"


def cargar_credenciales():
    """Carga credenciales desde el archivo JSON"""
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError("No se encontró credentials.json")

    with open(CREDENTIALS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def conectar_db():
    """Conecta a la base de datos MySQL"""
    config = cargar_credenciales()['db_config']
    try:
        conn = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            port=config.get('port', 3306)
        )
        return conn
    except mysql.connector.Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None


def login_required(f):
    """Decorador para rutas que requieren login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorador para rutas que requieren rol de admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión', 'warning')
            return redirect(url_for('login'))
        if session.get('rol') != 'admin':
            flash('No tienes permisos de administrador', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    """Página principal - redirige a login o dashboard"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión"""
    if request.method == 'POST':
        numero_cuenta = request.form.get('numero_cuenta', '').strip()
        password = request.form.get('password', '').strip()

        if not numero_cuenta or not password:
            flash('Por favor ingresa número de cuenta y contraseña', 'danger')
            return render_template('login.html')

        conn = conectar_db()
        if not conn:
            flash('Error de conexión con la base de datos', 'danger')
            return render_template('login.html')

        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, numero_cuenta, nombre, nombref2, password, rol, primer_login, email
                FROM alumnos
                WHERE numero_cuenta = %s
            """, (numero_cuenta,))

            usuario = cursor.fetchone()
            cursor.close()
            conn.close()

            if usuario and usuario['password'] == password:
                # Login exitoso
                session['user_id'] = usuario['id']
                session['numero_cuenta'] = usuario['numero_cuenta']
                session['nombre'] = usuario['nombre']
                session['nombref2'] = usuario['nombref2']
                session['rol'] = usuario['rol']
                session['email'] = usuario['email']

                # Verificar si es primer login
                if usuario['primer_login']:
                    flash('Es tu primer inicio de sesión. Por seguridad, debes cambiar tu contraseña.', 'warning')
                    return redirect(url_for('cambiar_password'))

                flash(f'Bienvenido, {usuario["nombre"]}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Número de cuenta o contraseña incorrectos', 'danger')

        except mysql.connector.Error as e:
            flash(f'Error al verificar credenciales: {e}', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Cerrar sesión"""
    session.clear()
    flash('Has cerrado sesión correctamente', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal - diferente para admin y alumno"""
    if session.get('rol') == 'admin':
        return redirect(url_for('dashboard_admin'))
    else:
        return redirect(url_for('dashboard_alumno'))


@app.route('/dashboard/alumno')
@login_required
def dashboard_alumno():
    """Dashboard para alumnos - ver sus calificaciones"""
    conn = conectar_db()
    if not conn:
        flash('Error de conexión con la base de datos', 'danger')
        return redirect(url_for('logout'))

    try:
        cursor = conn.cursor(dictionary=True)

        # Obtener calificaciones del alumno
        cursor.execute("""
            SELECT
                t.nombre as tarea,
                t.puntos_maximos,
                c.calificacion,
                c.fecha_calificacion,
                c.ruta_pdf_calificado,
                c.ruta_audio,
                g.nombre as grupo
            FROM calificaciones c
            INNER JOIN tareas t ON c.tarea_id = t.id
            INNER JOIN alumnos a ON c.alumno_id = a.id
            INNER JOIN grupos g ON t.grupo_id = g.id
            WHERE a.id = %s
            ORDER BY c.fecha_calificacion DESC
        """, (session['user_id'],))

        calificaciones = cursor.fetchall()

        # Calcular estadísticas
        if calificaciones:
            promedio = sum(c['calificacion'] for c in calificaciones) / len(calificaciones)
            tareas_completadas = len(calificaciones)
        else:
            promedio = 0
            tareas_completadas = 0

        cursor.close()
        conn.close()

        return render_template('dashboard_alumno.html',
                             calificaciones=calificaciones,
                             promedio=promedio,
                             tareas_completadas=tareas_completadas)

    except mysql.connector.Error as e:
        flash(f'Error al cargar calificaciones: {e}', 'danger')
        return redirect(url_for('logout'))


@app.route('/dashboard/admin')
@admin_required
def dashboard_admin():
    """Dashboard para administradores - estadísticas generales"""
    conn = conectar_db()
    if not conn:
        flash('Error de conexión con la base de datos', 'danger')
        return redirect(url_for('logout'))

    try:
        cursor = conn.cursor(dictionary=True)

        # Estadísticas generales
        cursor.execute("SELECT COUNT(*) as total FROM alumnos WHERE rol='alumno'")
        total_alumnos = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM tareas")
        total_tareas = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM calificaciones")
        total_calificaciones = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM grupos")
        total_grupos = cursor.fetchone()['total']

        # Últimas calificaciones registradas
        cursor.execute("""
            SELECT
                a.nombre as alumno,
                t.nombre as tarea,
                c.calificacion,
                c.fecha_calificacion
            FROM calificaciones c
            INNER JOIN alumnos a ON c.alumno_id = a.id
            INNER JOIN tareas t ON c.tarea_id = t.id
            ORDER BY c.fecha_calificacion DESC
            LIMIT 10
        """)
        ultimas_calificaciones = cursor.fetchall()

        # Promedio general
        cursor.execute("SELECT AVG(calificacion) as promedio FROM calificaciones")
        promedio_result = cursor.fetchone()
        promedio_general = promedio_result['promedio'] if promedio_result['promedio'] else 0

        cursor.close()
        conn.close()

        return render_template('dashboard_admin.html',
                             total_alumnos=total_alumnos,
                             total_tareas=total_tareas,
                             total_calificaciones=total_calificaciones,
                             total_grupos=total_grupos,
                             promedio_general=promedio_general,
                             ultimas_calificaciones=ultimas_calificaciones)

    except mysql.connector.Error as e:
        flash(f'Error al cargar estadísticas: {e}', 'danger')
        return redirect(url_for('logout'))


@app.route('/cambiar-password', methods=['GET', 'POST'])
@login_required
def cambiar_password():
    """Cambiar contraseña del usuario"""
    if request.method == 'POST':
        password_actual = request.form.get('password_actual', '').strip()
        password_nueva = request.form.get('password_nueva', '').strip()
        password_confirmar = request.form.get('password_confirmar', '').strip()

        # Validaciones
        if not password_actual or not password_nueva or not password_confirmar:
            flash('Todos los campos son obligatorios', 'danger')
            return render_template('cambiar_password.html')

        if password_nueva != password_confirmar:
            flash('Las contraseñas nuevas no coinciden', 'danger')
            return render_template('cambiar_password.html')

        if len(password_nueva) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
            return render_template('cambiar_password.html')

        conn = conectar_db()
        if not conn:
            flash('Error de conexión con la base de datos', 'danger')
            return render_template('cambiar_password.html')

        try:
            cursor = conn.cursor(dictionary=True)

            # Verificar contraseña actual
            cursor.execute("""
                SELECT password FROM alumnos WHERE id = %s
            """, (session['user_id'],))

            usuario = cursor.fetchone()

            if not usuario or usuario['password'] != password_actual:
                flash('La contraseña actual es incorrecta', 'danger')
                cursor.close()
                conn.close()
                return render_template('cambiar_password.html')

            # Actualizar contraseña
            cursor.execute("""
                UPDATE alumnos
                SET password = %s, primer_login = FALSE
                WHERE id = %s
            """, (password_nueva, session['user_id']))

            conn.commit()
            cursor.close()
            conn.close()

            flash('Contraseña actualizada exitosamente', 'success')
            return redirect(url_for('dashboard'))

        except mysql.connector.Error as e:
            flash(f'Error al actualizar contraseña: {e}', 'danger')

    return render_template('cambiar_password.html')


@app.route('/api/calificaciones/<int:alumno_id>')
@admin_required
def api_calificaciones_alumno(alumno_id):
    """API para obtener calificaciones de un alumno (solo admin)"""
    conn = conectar_db()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                t.nombre as tarea,
                c.calificacion,
                c.fecha_calificacion
            FROM calificaciones c
            INNER JOIN tareas t ON c.tarea_id = t.id
            WHERE c.alumno_id = %s
            ORDER BY c.fecha_calificacion DESC
        """, (alumno_id,))

        calificaciones = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convertir datetime a string
        for cal in calificaciones:
            if cal['fecha_calificacion']:
                cal['fecha_calificacion'] = cal['fecha_calificacion'].strftime('%Y-%m-%d %H:%M')

        return jsonify(calificaciones)

    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("="*60)
    print("SISTEMA DE CALIFICACIONES")
    print("Starlink Hi-Tech Style")
    print("="*60)
    print("\nIniciando servidor...")
    print("Accede en: http://localhost:5000")
    print("="*60)

    app.run(debug=True, host='0.0.0.0', port=5000)
