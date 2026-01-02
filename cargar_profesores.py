"""
Script para cargar profesores desde archivos CSV a la base de datos
Formato del CSV: profesores.csv con columnas: numero_empleado,nombre,nombref2,email,especialidad,rol,grupos

nombre = Formato sistema (Nombre Apellidos)
nombref2 = Formato oficial (Apellidos, Nombre)
rol = 'profesor' o 'admin'
grupos = Lista de grupos que imparte, separados por | (pipe), ejemplo: "Grupo1|Grupo2"

Un profesor puede impartir múltiples grupos
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


def leer_csv_profesores(csv_path: Path) -> List[Dict]:
    """
    Lee el archivo CSV de profesores
    Formato esperado: numero_empleado,nombre,nombref2,email,especialidad,rol,grupos
    """
    profesores = []

    if not csv_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {csv_path}")

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        # Verificar que existan las columnas necesarias
        columnas_requeridas = {'numero_empleado', 'nombre', 'nombref2'}
        columnas_archivo = set(reader.fieldnames)

        if not columnas_requeridas.issubset(columnas_archivo):
            faltantes = columnas_requeridas - columnas_archivo
            raise ValueError(
                f"El CSV no tiene las columnas requeridas. Faltan: {faltantes}\n"
                f"Columnas encontradas: {columnas_archivo}"
            )

        for row in reader:
            # Limpiar espacios en blanco
            profesor = {
                'numero_empleado': row['numero_empleado'].strip(),
                'nombre': row['nombre'].strip(),
                'nombref2': row['nombref2'].strip(),
                'email': row.get('email', '').strip() if row.get('email') else None,
                'especialidad': row.get('especialidad', '').strip() if row.get('especialidad') else None,
                'rol': row.get('rol', 'profesor').strip().lower(),  # Default: profesor
                'grupos': []
            }

            # Validar rol
            if profesor['rol'] not in ['profesor', 'admin']:
                print(f"[!] Advertencia: Rol inválido '{profesor['rol']}' para {profesor['nombre']}, usando 'profesor'")
                profesor['rol'] = 'profesor'

            # Procesar grupos (pueden ser múltiples separados por |)
            if 'grupos' in row and row['grupos']:
                grupos_raw = row['grupos'].strip()
                if grupos_raw:
                    profesor['grupos'] = [g.strip() for g in grupos_raw.split('|') if g.strip()]

            # Validar que al menos tenga número de empleado y nombre
            if not profesor['numero_empleado'] or not profesor['nombre']:
                print(f"[!] Advertencia: Fila ignorada por datos incompletos: {row}")
                continue

            profesores.append(profesor)

    return profesores


def obtener_o_crear_grupos(conn, nombres_grupos: List[str]) -> Dict[str, int]:
    """
    Obtiene o crea múltiples grupos
    Retorna diccionario {nombre_grupo: grupo_id}
    """
    cursor = conn.cursor()
    grupo_ids = {}

    for nombre_grupo in nombres_grupos:
        # Verificar si el grupo ya existe
        cursor.execute("SELECT id FROM grupos WHERE nombre = %s", (nombre_grupo,))
        result = cursor.fetchone()

        if result:
            grupo_ids[nombre_grupo] = result[0]
            print(f"[+] Grupo existente: {nombre_grupo} (ID: {result[0]})")
        else:
            # Crear nuevo grupo (el profesor se asignará después)
            cursor.execute(
                "INSERT INTO grupos (nombre) VALUES (%s)",
                (nombre_grupo,)
            )
            conn.commit()
            grupo_ids[nombre_grupo] = cursor.lastrowid
            print(f"[+] Nuevo grupo creado: {nombre_grupo} (ID: {cursor.lastrowid})")

    cursor.close()
    return grupo_ids


def cargar_profesores_db(conn, profesores: List[Dict]) -> Dict:
    """
    Carga los profesores a la base de datos y los asocia con sus grupos
    Retorna estadísticas de la carga
    """
    cursor = conn.cursor()
    stats = {
        'insertados': 0,
        'actualizados': 0,
        'grupos_asignados': 0,
        'errores': 0
    }

    # Recolectar todos los nombres de grupos únicos
    todos_grupos = set()
    for profesor in profesores:
        todos_grupos.update(profesor['grupos'])

    # Crear/obtener IDs de todos los grupos
    if todos_grupos:
        print(f"\n[+] Procesando {len(todos_grupos)} grupos...")
        grupo_ids_map = obtener_o_crear_grupos(conn, list(todos_grupos))
    else:
        grupo_ids_map = {}

    # Procesar cada profesor
    print(f"\n[+] Procesando {len(profesores)} profesores...")
    for profesor in profesores:
        try:
            # Verificar si el profesor ya existe (por número de empleado)
            cursor.execute(
                "SELECT id FROM profesores WHERE numero_empleado = %s",
                (profesor['numero_empleado'],)
            )
            result = cursor.fetchone()

            if result:
                # Actualizar profesor existente (no actualizar password)
                profesor_id = result[0]
                cursor.execute("""
                    UPDATE profesores
                    SET nombre = %s, nombref2 = %s, email = %s, especialidad = %s, rol = %s
                    WHERE numero_empleado = %s
                """, (
                    profesor['nombre'],
                    profesor['nombref2'],
                    profesor['email'],
                    profesor['especialidad'],
                    profesor['rol'],
                    profesor['numero_empleado']
                ))
                stats['actualizados'] += 1
                print(f"  ↻ Actualizado: {profesor['nombre']} ({profesor['numero_empleado']}) - Rol: {profesor['rol']}")
            else:
                # Insertar nuevo profesor
                # Password por defecto = número de empleado
                password_default = profesor['numero_empleado']

                cursor.execute("""
                    INSERT INTO profesores
                    (numero_empleado, nombre, nombref2, password, rol, primer_login, email, especialidad)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    profesor['numero_empleado'],
                    profesor['nombre'],
                    profesor['nombref2'],
                    password_default,
                    profesor['rol'],
                    True,  # Primer login = True
                    profesor['email'],
                    profesor['especialidad']
                ))
                profesor_id = cursor.lastrowid
                stats['insertados'] += 1
                print(f"  ✓ Insertado: {profesor['nombre']} ({profesor['numero_empleado']}) - Rol: {profesor['rol']} - Pass: {password_default}")

            conn.commit()

            # Asociar profesor con sus grupos (actualizar profesor_id en tabla grupos)
            if profesor['grupos']:
                for nombre_grupo in profesor['grupos']:
                    if nombre_grupo in grupo_ids_map:
                        grupo_id = grupo_ids_map[nombre_grupo]

                        # Asignar profesor al grupo
                        cursor.execute("""
                            UPDATE grupos
                            SET profesor_id = %s
                            WHERE id = %s
                        """, (profesor_id, grupo_id))
                        stats['grupos_asignados'] += 1

                conn.commit()

        except mysql.connector.Error as e:
            stats['errores'] += 1
            print(f"  ✗ Error con {profesor['numero_empleado']}: {e}")
            conn.rollback()

    cursor.close()
    return stats


def listar_archivos_csv():
    """Lista todos los archivos CSV disponibles para profesores"""
    csv_files = list(Path.cwd().glob("*profesor*.csv"))
    csv_files.extend(Path.cwd().glob("ejemplo_profesores.csv"))
    return sorted(set(csv_files))


def seleccionar_csv():
    """Permite al usuario seleccionar un archivo CSV"""
    csv_files = listar_archivos_csv()

    if not csv_files:
        print("\n[!] No se encontraron archivos CSV de profesores")
        print("    Crea un archivo 'profesores.csv' o 'ejemplo_profesores.csv' con el formato:")
        print("    numero_empleado,nombre,nombref2,email,especialidad,rol,grupos")
        print("    Ejemplo grupos: 'Grupo1|Grupo2' (múltiples grupos separados por |)")
        print("    Ejemplo rol: 'profesor' o 'admin'")
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
    print("CARGA DE PROFESORES DESDE CSV")
    print("Sistema de Calificación Automática")
    print("="*60)

    try:
        # Seleccionar archivo CSV
        csv_path = seleccionar_csv()
        if not csv_path:
            print("\n[!] Proceso cancelado")
            return 1

        print(f"\n[+] Procesando archivo: {csv_path.name}")

        # Leer CSV
        print("\n[+] Leyendo archivo CSV...")
        profesores = leer_csv_profesores(csv_path)
        print(f"[+] Se encontraron {len(profesores)} profesores en el CSV")

        if not profesores:
            print("[!] No hay profesores para procesar")
            return 1

        # Mostrar vista previa
        print("\n📋 Vista previa de los primeros 3 profesores:")
        for i, profesor in enumerate(profesores[:3], 1):
            print(f"\n  {i}. {profesor['nombre']}")
            print(f"     Empleado: {profesor['numero_empleado']}")
            print(f"     Formato oficial: {profesor['nombref2']}")
            print(f"     Email: {profesor['email'] or 'N/A'}")
            print(f"     Especialidad: {profesor['especialidad'] or 'N/A'}")
            print(f"     Rol: {profesor['rol'].upper()}")
            print(f"     Grupos: {', '.join(profesor['grupos']) if profesor['grupos'] else 'Sin grupos asignados'}")

        if len(profesores) > 3:
            print(f"\n  ... y {len(profesores) - 3} profesores más")

        # Confirmar antes de continuar
        confirmar = input("\n¿Continuar con la carga a la base de datos? (s/n): ").strip().lower()
        if confirmar not in ['s', 'si', 'sí', 'y', 'yes']:
            print("\n[!] Carga cancelada por el usuario")
            return 1

        # Conectar a la base de datos
        print("\n[+] Conectando a la base de datos...")
        config = cargar_credenciales()
        conn = conectar_db(config)

        # Cargar profesores
        stats = cargar_profesores_db(conn, profesores)

        # Mostrar resumen
        print("\n" + "="*60)
        print("RESUMEN DE LA CARGA")
        print("="*60)
        print(f"Profesores insertados: {stats['insertados']}")
        print(f"Profesores actualizados: {stats['actualizados']}")
        print(f"Grupos asignados: {stats['grupos_asignados']}")
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
