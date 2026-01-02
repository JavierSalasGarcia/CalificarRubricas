"""
Script para crear las tablas de la base de datos MySQL
Para el sistema de calificación automática con Gemini

Ejecutar una sola vez para inicializar la base de datos
"""

import json
import mysql.connector
from pathlib import Path


def cargar_credenciales():
    """Carga las credenciales desde credentials.json"""
    cred_file = Path(__file__).parent / "credentials.json"
    if not cred_file.exists():
        raise FileNotFoundError(
            "No se encontró credentials.json. "
            "Crea el archivo con las credenciales de la base de datos."
        )

    with open(cred_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data['db_config']


def conectar_db(config):
    """Establece conexión con la base de datos MySQL"""
    try:
        conn = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            port=config.get('port', 3306)
        )
        print(f"[+] Conectado a la base de datos: {config['database']}")
        return conn
    except mysql.connector.Error as e:
        print(f"[!] Error al conectar a la base de datos: {e}")
        raise


def crear_tablas(conn):
    """Crea todas las tablas necesarias para el sistema"""
    cursor = conn.cursor()

    # Tabla de Grupos
    print("\n[+] Creando tabla 'grupos'...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grupos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(255) UNIQUE NOT NULL,
            semestre VARCHAR(50),
            anio INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    # Tabla de Alumnos
    print("[+] Creando tabla 'alumnos'...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alumnos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            numero_cuenta VARCHAR(20) UNIQUE NOT NULL,
            nombre VARCHAR(255) NOT NULL,
            nombref2 VARCHAR(255) NOT NULL,
            grupo_id INT,
            team_id INT DEFAULT 1,
            email VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (grupo_id) REFERENCES grupos(id) ON DELETE CASCADE,
            INDEX idx_numero_cuenta (numero_cuenta),
            INDEX idx_nombre (nombre)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    # Tabla de Tareas
    print("[+] Creando tabla 'tareas'...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tareas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            grupo_id INT NOT NULL,
            nombre VARCHAR(255) NOT NULL,
            descripcion TEXT,
            fecha_limite DATE,
            puntos_maximos DECIMAL(3,1) DEFAULT 10.0,
            rubrica TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (grupo_id) REFERENCES grupos(id) ON DELETE CASCADE,
            UNIQUE KEY unique_tarea_grupo (grupo_id, nombre),
            INDEX idx_grupo_tarea (grupo_id, nombre)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    # Tabla de Calificaciones
    print("[+] Creando tabla 'calificaciones'...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calificaciones (
            id INT AUTO_INCREMENT PRIMARY KEY,
            alumno_id INT NOT NULL,
            tarea_id INT NOT NULL,
            calificacion DECIMAL(3,1) NOT NULL,
            ruta_pdf_calificado VARCHAR(500),
            ruta_audio VARCHAR(500),
            ruta_transcripcion VARCHAR(500),
            fecha_calificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (alumno_id) REFERENCES alumnos(id) ON DELETE CASCADE,
            FOREIGN KEY (tarea_id) REFERENCES tareas(id) ON DELETE CASCADE,
            UNIQUE KEY unique_calificacion (alumno_id, tarea_id),
            INDEX idx_alumno (alumno_id),
            INDEX idx_tarea (tarea_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    # Tabla de Asistencias
    print("[+] Creando tabla 'asistencias'...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS asistencias (
            id INT AUTO_INCREMENT PRIMARY KEY,
            alumno_id INT NOT NULL,
            grupo_id INT NOT NULL,
            fecha DATE NOT NULL,
            presente BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (alumno_id) REFERENCES alumnos(id) ON DELETE CASCADE,
            FOREIGN KEY (grupo_id) REFERENCES grupos(id) ON DELETE CASCADE,
            UNIQUE KEY unique_asistencia (alumno_id, fecha),
            INDEX idx_fecha (fecha),
            INDEX idx_grupo_fecha (grupo_id, fecha)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    conn.commit()
    cursor.close()
    print("\n[✓] Todas las tablas creadas exitosamente")


def mostrar_estructura(conn):
    """Muestra la estructura de las tablas creadas"""
    cursor = conn.cursor()

    print("\n" + "="*60)
    print("ESTRUCTURA DE LA BASE DE DATOS")
    print("="*60)

    tablas = ['grupos', 'alumnos', 'tareas', 'calificaciones', 'asistencias']

    for tabla in tablas:
        cursor.execute(f"DESCRIBE {tabla}")
        columns = cursor.fetchall()

        print(f"\n📋 Tabla: {tabla}")
        print("-" * 60)
        for col in columns:
            campo = col[0]
            tipo = col[1]
            null = "NULL" if col[2] == "YES" else "NOT NULL"
            key = col[3] if col[3] else ""
            default = f"DEFAULT {col[4]}" if col[4] else ""
            extra = col[5] if col[5] else ""

            print(f"  {campo:20} {tipo:20} {null:10} {key:5} {default:15} {extra}")

    cursor.close()


def verificar_conexion(conn):
    """Verifica que la conexión esté funcionando"""
    cursor = conn.cursor()
    cursor.execute("SELECT VERSION()")
    version = cursor.fetchone()
    print(f"[+] Versión de MySQL: {version[0]}")
    cursor.close()


def main():
    """Función principal"""
    print("="*60)
    print("CONFIGURACIÓN DE BASE DE DATOS")
    print("Sistema de Calificación Automática con Gemini")
    print("="*60)

    try:
        # Cargar credenciales
        config = cargar_credenciales()

        # Conectar a la base de datos
        conn = conectar_db(config)

        # Verificar conexión
        verificar_conexion(conn)

        # Crear tablas
        crear_tablas(conn)

        # Mostrar estructura
        mostrar_estructura(conn)

        # Cerrar conexión
        conn.close()
        print("\n[+] Conexión cerrada")
        print("\n✓ Base de datos configurada correctamente")
        print("\nPróximos pasos:")
        print("  1. Usa cargar_alumnos.py para importar alumnos desde CSV")
        print("  2. Ejecuta transcribir_audios.py para transcribir audios")
        print("  3. Ejecuta calificar_gemini.py para calificar con IA")

    except Exception as e:
        print(f"\n[!] Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
