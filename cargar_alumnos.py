"""
Script para cargar alumnos desde archivos CSV a la base de datos
Formato del CSV: <grupo>.csv con columnas: numero_cuenta,nombre,nombref2,email

nombre = Formato sistema (Nombre Apellidos) - usado en tareas.py
nombref2 = Formato oficial (Apellidos, Nombre)
"""

import csv
import json
import mysql.connector
from pathlib import Path
from typing import List, Dict


def cargar_credenciales():
    """Carga las credenciales desde credentials.json"""
    cred_file = Path(__file__).parent / "credentials.json"
    if not cred_file.exists():
        raise FileNotFoundError("No se encontró credentials.json")

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
        return conn
    except mysql.connector.Error as e:
        print(f"[!] Error al conectar a la base de datos: {e}")
        raise


def leer_csv_alumnos(csv_path: Path) -> List[Dict]:
    """
    Lee el archivo CSV de alumnos
    Formato esperado: numero_cuenta,nombre,nombref2,email
    """
    alumnos = []

    if not csv_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {csv_path}")

    with open(csv_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig para eliminar BOM
        reader = csv.DictReader(f)

        # Verificar que existan las columnas necesarias
        columnas_requeridas = {'numero_cuenta', 'nombre', 'nombref2', 'email'}
        columnas_archivo = set(reader.fieldnames)

        if not columnas_requeridas.issubset(columnas_archivo):
            faltantes = columnas_requeridas - columnas_archivo
            raise ValueError(
                f"El CSV no tiene las columnas requeridas. Faltan: {faltantes}\n"
                f"Columnas encontradas: {columnas_archivo}"
            )

        for row in reader:
            # Limpiar espacios en blanco
            alumno = {
                'numero_cuenta': row['numero_cuenta'].strip(),
                'nombre': row['nombre'].strip(),
                'nombref2': row['nombref2'].strip(),
                'email': row['email'].strip() if row['email'] else None
            }

            # Validar que al menos tenga número de cuenta y nombre
            if not alumno['numero_cuenta'] or not alumno['nombre']:
                print(f"[!] Advertencia: Fila ignorada por datos incompletos: {row}")
                continue

            alumnos.append(alumno)

    return alumnos


def obtener_o_crear_grupo(conn, nombre_grupo: str, semestre: str = None, anio: int = None) -> int:
    """
    Obtiene el ID del grupo o lo crea si no existe
    Retorna el group_id
    """
    cursor = conn.cursor()

    # Verificar si el grupo ya existe
    cursor.execute("SELECT id FROM grupos WHERE nombre = %s", (nombre_grupo,))
    result = cursor.fetchone()

    if result:
        grupo_id = result[0]
        print(f"[+] Grupo existente encontrado: {nombre_grupo} (ID: {grupo_id})")
    else:
        # Crear nuevo grupo
        cursor.execute(
            "INSERT INTO grupos (nombre, semestre, anio) VALUES (%s, %s, %s)",
            (nombre_grupo, semestre, anio)
        )
        conn.commit()
        grupo_id = cursor.lastrowid
        print(f"[+] Nuevo grupo creado: {nombre_grupo} (ID: {grupo_id})")

    cursor.close()
    return grupo_id


def cargar_alumnos_db(conn, grupo_id: int, alumnos: List[Dict]) -> Dict:
    """
    Carga los alumnos a la base de datos
    Retorna estadísticas de la carga
    """
    cursor = conn.cursor()
    stats = {
        'insertados': 0,
        'actualizados': 0,
        'errores': 0
    }

    for alumno in alumnos:
        try:
            # Verificar si el alumno ya existe (por número de cuenta)
            cursor.execute(
                "SELECT id FROM alumnos WHERE numero_cuenta = %s",
                (alumno['numero_cuenta'],)
            )
            result = cursor.fetchone()

            if result:
                # Actualizar alumno existente
                cursor.execute("""
                    UPDATE alumnos
                    SET nombre = %s, nombref2 = %s, grupo_id = %s, email = %s
                    WHERE numero_cuenta = %s
                """, (
                    alumno['nombre'],
                    alumno['nombref2'],
                    grupo_id,
                    alumno['email'],
                    alumno['numero_cuenta']
                ))
                stats['actualizados'] += 1
                print(f"  ↻ Actualizado: {alumno['nombre']} ({alumno['numero_cuenta']})")
            else:
                # Insertar nuevo alumno
                cursor.execute("""
                    INSERT INTO alumnos (numero_cuenta, nombre, nombref2, grupo_id, email)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    alumno['numero_cuenta'],
                    alumno['nombre'],
                    alumno['nombref2'],
                    grupo_id,
                    alumno['email']
                ))
                stats['insertados'] += 1
                print(f"  ✓ Insertado: {alumno['nombre']} ({alumno['numero_cuenta']})")

            conn.commit()

        except mysql.connector.Error as e:
            stats['errores'] += 1
            print(f"  ✗ Error con {alumno['numero_cuenta']}: {e}")
            conn.rollback()

    cursor.close()
    return stats


def listar_archivos_csv():
    """Lista todos los archivos CSV disponibles en el directorio actual"""
    csv_files = list(Path.cwd().glob("*.csv"))
    return sorted(csv_files)


def seleccionar_csv():
    """Permite al usuario seleccionar un archivo CSV"""
    csv_files = listar_archivos_csv()

    if not csv_files:
        print("\n[!] No se encontraron archivos CSV en el directorio actual")
        print("    Crea un archivo <grupo>.csv con el formato:")
        print("    numero_cuenta,nombre,nombref2,email")
        return None

    print("\n" + "="*60)
    print("ARCHIVOS CSV DISPONIBLES")
    print("="*60)

    for i, csv_file in enumerate(csv_files, 1):
        print(f"  {i}. {csv_file.name}")

    while True:
        try:
            opcion = input("\nSelecciona el número del archivo CSV (o 'q' para salir): ").strip()

            if opcion.lower() == 'q':
                return None

            idx = int(opcion) - 1
            if 0 <= idx < len(csv_files):
                return csv_files[idx]
            else:
                print("[!] Opción inválida. Intenta de nuevo.")
        except ValueError:
            print("[!] Ingresa un número válido.")


def main():
    """Función principal"""
    print("="*60)
    print("CARGA DE ALUMNOS DESDE CSV")
    print("Sistema de Calificación Automática")
    print("="*60)

    try:
        # Seleccionar archivo CSV
        csv_path = seleccionar_csv()
        if not csv_path:
            print("\n[!] Proceso cancelado")
            return 1

        # Extraer nombre del grupo del nombre del archivo (sin extensión)
        nombre_grupo = csv_path.stem

        print(f"\n[+] Procesando archivo: {csv_path.name}")
        print(f"[+] Grupo detectado: {nombre_grupo}")

        # Leer CSV
        print("\n[+] Leyendo archivo CSV...")
        alumnos = leer_csv_alumnos(csv_path)
        print(f"[+] Se encontraron {len(alumnos)} alumnos en el CSV")

        if not alumnos:
            print("[!] No hay alumnos para procesar")
            return 1

        # Mostrar vista previa
        print("\n📋 Vista previa de los primeros 3 alumnos:")
        for i, alumno in enumerate(alumnos[:3], 1):
            print(f"\n  {i}. {alumno['nombre']}")
            print(f"     Cuenta: {alumno['numero_cuenta']}")
            print(f"     Formato oficial: {alumno['nombref2']}")
            print(f"     Email: {alumno['email'] or 'N/A'}")

        if len(alumnos) > 3:
            print(f"\n  ... y {len(alumnos) - 3} alumnos más")

        # Confirmar antes de continuar
        confirmar = input("\n¿Continuar con la carga a la base de datos? (s/n): ").strip().lower()
        if confirmar not in ['s', 'si', 'sí', 'y', 'yes']:
            print("\n[!] Carga cancelada por el usuario")
            return 1

        # Conectar a la base de datos
        print("\n[+] Conectando a la base de datos...")
        config = cargar_credenciales()
        conn = conectar_db(config)

        # Obtener o crear grupo
        grupo_id = obtener_o_crear_grupo(conn, nombre_grupo)

        # Cargar alumnos
        print(f"\n[+] Cargando alumnos al grupo '{nombre_grupo}'...")
        stats = cargar_alumnos_db(conn, grupo_id, alumnos)

        # Mostrar resumen
        print("\n" + "="*60)
        print("RESUMEN DE LA CARGA")
        print("="*60)
        print(f"Grupo: {nombre_grupo} (ID: {grupo_id})")
        print(f"Alumnos insertados: {stats['insertados']}")
        print(f"Alumnos actualizados: {stats['actualizados']}")
        print(f"Errores: {stats['errores']}")
        print(f"Total procesados: {stats['insertados'] + stats['actualizados']}")
        print("="*60)

        # Cerrar conexión
        conn.close()
        print("\n✓ Proceso completado exitosamente")

    except Exception as e:
        print(f"\n[!] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
