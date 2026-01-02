from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Iterable, Optional, Set, Tuple

# Rutas base (ajusta si cambia tu entorno)
BASE_ROOT = Path("C:\\Users\\javie\\OneDrive - Universidad Aut\u00f3noma del Estado de M\u00e9xico")
CALIFICAR_ROOT = Path(r"D:\tareas\Calificar")

# Constantes
EQUIPOS_DIRNAME = "Equipos"
DEFAULT_TEAM_ID = 1
CALIFICADO_DIRNAME = "Calificado"


def pick(options, prompt, allow_empty=False):
    if not options:
        if allow_empty:
            return None
        raise SystemExit(f"No hay opciones para '{prompt}'.")
    while True:
        print(f"\n{prompt}")
        for i, opt in enumerate(options, 1):
            print(f" {i}. {opt}")
        sel = input("Elige numero: ").strip()
        if sel.isdigit() and 1 <= int(sel) <= len(options):
            return options[int(sel) - 1]
        print("Opcion invalida, intenta de nuevo.")


def latest_version_dir(task_dir: Path) -> Path:
    version_dirs: list[Tuple[int, Path]] = []
    for p in task_dir.iterdir():
        if p.is_dir() and p.name.lower().startswith(("versi\u00f3n", "version")):
            try:
                num = int("".join(ch for ch in p.name if ch.isdigit()))
            except ValueError:
                continue
            version_dirs.append((num, p))
    if version_dirs:
        version_dirs.sort(key=lambda x: x[0])
        return version_dirs[-1][1]
    return task_dir


def latest_pdf_from_task(task_dir: Path) -> Optional[Path]:
    base = latest_version_dir(task_dir)
    pdfs = list(base.glob("*.pdf"))
    if not pdfs:
        pdfs = list(base.rglob("*.pdf"))
    if not pdfs:
        return None
    pdfs.sort(key=lambda p: p.stat().st_mtime)
    return pdfs[-1]


def count_ungraded_files(group_dir: Path) -> int:
    """Cuenta archivos sin calificar en un grupo"""
    count = 0
    for student_dir in group_dir.iterdir():
        if not student_dir.is_dir():
            continue
        for tdir in student_dir.iterdir():
            if not tdir.is_dir():
                continue
            # Buscar en la última versión
            latest_ver = latest_version_dir(tdir)
            calificado_dir = latest_ver / CALIFICADO_DIRNAME
            # Si no existe carpeta Calificado o está vacía, contar como sin calificar
            if not calificado_dir.exists() or not any(calificado_dir.glob("*.pdf")):
                count += 1
    return count


def list_groups(root: Path):
    """Devuelve lista de tuplas (nombre_limpio, path_completo, num_sin_calificar)"""
    groups = []
    for p in root.glob("*Submitted files"):
        if not p.is_dir():
            continue
        # Quitar " - Submitted files" del nombre
        clean_name = p.name.replace(" - Submitted files", "")
        # Contar archivos sin calificar
        ungraded_count = count_ungraded_files(p)
        groups.append((clean_name, p.name, ungraded_count))
    return sorted(groups, key=lambda x: x[0])


def list_tasks(root: Path, group: str):
    """Devuelve lista de tuplas (nombre_limpio, nombre_original, calificadas, sin_calificar)"""
    group_dir = root / group
    tasks = {}

    # Primero recolectar todas las tareas y contar por cada una
    for student_dir in group_dir.iterdir():
        if not student_dir.is_dir():
            continue
        for tdir in student_dir.iterdir():
            if tdir.is_dir():
                original_name = tdir.name
                # Eliminar número al inicio si existe (ej: "1. " o "12. ")
                clean_name = re.sub(r'^\d+\.\s*', '', original_name)

                if original_name not in tasks:
                    tasks[original_name] = {'clean_name': clean_name, 'graded': 0, 'ungraded': 0}

                # Verificar si esta tarea está calificada para este estudiante
                latest_ver = latest_version_dir(tdir)
                calificado_dir = latest_ver / CALIFICADO_DIRNAME

                if calificado_dir.exists() and any(calificado_dir.glob("*.pdf")):
                    tasks[original_name]['graded'] += 1
                else:
                    tasks[original_name]['ungraded'] += 1

    # Convertir a lista de tuplas (nombre_limpio, nombre_original, calificadas, sin_calificar)
    result = []
    for original_name, data in tasks.items():
        result.append((data['clean_name'], original_name, data['graded'], data['ungraded']))

    return sorted(result, key=lambda x: x[1])


def download_task(root: Path, group: str, task: str, dest_root: Path, individual_flag: bool):
    """
    Descarga la tarea:
      - Modo equipo (individual_flag = False): Calificar/<grupo>/<tarea>/Equipo_<id>/<tarea>Equipo_<id>.pdf (1 PDF por equipo)
      - Modo individual (individual_flag = True): Calificar/<grupo>/<tarea>/<tarea>_<alumno>.pdf (1 PDF por alumno)
    Genera metadata y actualiza archivo de equipos.
    """
    group_dir = root / group
    dest_dir = dest_root / group / task
    dest_dir.mkdir(parents=True, exist_ok=True)

    student_names = {p.name for p in group_dir.iterdir() if p.is_dir()}
    mapping = update_teams_file(dest_root, group, student_names, individual_flag)

    copied = []

    if individual_flag:
        for student_dir in group_dir.iterdir():
            if not student_dir.is_dir():
                continue
            match = next((tdir for tdir in student_dir.iterdir() if tdir.is_dir() and tdir.name.lower() == task.lower()), None)
            if not match:
                continue
            pdf = latest_pdf_from_task(match)
            if not pdf:
                continue
            dest_file = dest_dir / f"{task}_{student_dir.name}.pdf"
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf, dest_file)
            copied.append({"student": student_dir.name, "team_id": mapping.get(student_dir.name, DEFAULT_TEAM_ID), "source": str(pdf), "dest": str(dest_file)})
    else:
        team_choice: Dict[int, Tuple[Path, str]] = {}
        for student_dir in group_dir.iterdir():
            if not student_dir.is_dir():
                continue
            match = next((tdir for tdir in student_dir.iterdir() if tdir.is_dir() and tdir.name.lower() == task.lower()), None)
            if not match:
                continue
            pdf = latest_pdf_from_task(match)
            if not pdf:
                continue
            team_id = mapping.get(student_dir.name, DEFAULT_TEAM_ID)
            prev = team_choice.get(team_id)
            if prev is None or pdf.stat().st_mtime > prev[0].stat().st_mtime:
                team_choice[team_id] = (pdf, student_dir.name)
        for team_id, (pdf, owner) in team_choice.items():
            # Guardar directamente en dest_dir sin subcarpeta
            dest_file = dest_dir / f"{task}_Equipo_{team_id}.pdf"
            shutil.copy2(pdf, dest_file)
            copied.append({"team_id": team_id, "chosen_from": owner, "source": str(pdf), "dest": str(dest_file)})

    metadata = {
        "group": group,
        "task": task,
        "mode": "individual" if individual_flag else "equipos",
        "source_root": str(group_dir),
        "dest_root": str(dest_dir),
        "students": copied,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    (dest_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDescarga completa en: {dest_dir}")
    if individual_flag:
        print(f"Para calificar: usa los PDFs en {dest_dir} y renombra cada uno con prefijo 'Cal_' (ej. Cal_<tarea>_<alumno>.pdf) en la misma carpeta.")
    else:
        print(f"Para calificar: usa los PDFs en {dest_dir} y renombra cada uno con prefijo 'Cal_' (ej. Cal_<tarea>_Equipo_<id>.pdf) en la misma carpeta.")

    # Abrir la carpeta en el explorador de archivos
    try:
        if os.name == 'nt':  # Windows
            os.startfile(dest_dir)
        elif os.name == 'posix':  # macOS y Linux
            if 'darwin' in os.sys.platform:  # macOS
                subprocess.run(['open', str(dest_dir)])
            else:  # Linux
                subprocess.run(['xdg-open', str(dest_dir)])
        print(f"[+] Carpeta abierta en el explorador de archivos")
    except Exception as e:
        print(f"[!] No se pudo abrir la carpeta automáticamente: {e}")


def return_feedback(root: Path, group: str, task: str, graded_root: Path, individual_flag: bool, mapping: Dict[str, int]) -> None:
    graded_task_dir = graded_root / group / task
    if not graded_task_dir.is_dir():
        raise SystemExit(f"No existe carpeta de calificacion: {graded_task_dir}")

    if individual_flag:
        for pdf in graded_task_dir.glob("Cal_*.pdf"):
            name_wo_prefix = pdf.stem[4:] if pdf.stem.lower().startswith("cal_") else pdf.stem
            parts = name_wo_prefix.split("_", 1)
            if len(parts) != 2:
                print(f"[!] Nombre inesperado (se omite): {pdf.name}")
                continue
            alumno = parts[1]
            student_dir = root / group / alumno
            if not student_dir.is_dir():
                print(f"[!] No se encontro carpeta del alumno {alumno}; se omite.")
                continue
            task_dir = next((tdir for tdir in student_dir.iterdir() if tdir.is_dir() and tdir.name.lower() == task.lower()), None)
            if not task_dir:
                print(f"[!] No se encontro la tarea '{task}' para {alumno}; se omite.")
                continue
            destino = latest_version_dir(task_dir) / CALIFICADO_DIRNAME
            destino.mkdir(exist_ok=True)
            shutil.copy2(pdf, destino / pdf.name)
            print(f"[OK] Copiado a {alumno} -> {destino/pdf.name}")
    else:
        # equipos - ahora los PDFs están directamente en graded_task_dir
        teams: Dict[int, Set[str]] = {}
        for name, tid in mapping.items():
            teams.setdefault(tid, set()).add(name)

        # Buscar PDFs con patrón Cal_*_Equipo_*.pdf directamente en la carpeta
        for pdf in graded_task_dir.glob("Cal_*_Equipo_*.pdf"):
            # Extraer el team_id del nombre del archivo
            # Formato esperado: Cal_<tarea>_Equipo_<id>.pdf
            try:
                name_wo_prefix = pdf.stem[4:] if pdf.stem.lower().startswith("cal_") else pdf.stem
                # Buscar "_Equipo_" en el nombre
                if "_Equipo_" not in name_wo_prefix and "_equipo_" not in name_wo_prefix.lower():
                    print(f"[!] Nombre inesperado (se omite): {pdf.name}")
                    continue

                # Extraer team_id
                parts = name_wo_prefix.split("_")
                team_id = None
                for i, part in enumerate(parts):
                    if part.lower() == "equipo" and i + 1 < len(parts):
                        team_id = int(parts[i + 1])
                        break

                if team_id is None:
                    print(f"[!] No se pudo extraer team_id de: {pdf.name}")
                    continue

                miembros = teams.get(team_id, set())
                if not miembros:
                    print(f"[!] Equipo {team_id} sin miembros en JSON; se omite.")
                    continue

                # Copiar a todos los miembros del equipo
                for alumno in miembros:
                    student_dir = root / group / alumno
                    if not student_dir.is_dir():
                        print(f"[!] No se encontro carpeta del alumno {alumno}; se omite.")
                        continue
                    task_dir = next((tdir for tdir in student_dir.iterdir() if tdir.is_dir() and tdir.name.lower() == task.lower()), None)
                    if not task_dir:
                        print(f"[!] No se encontro la tarea '{task}' para {alumno}; se omite.")
                        continue
                    destino = latest_version_dir(task_dir) / CALIFICADO_DIRNAME
                    destino.mkdir(exist_ok=True)
                    shutil.copy2(pdf, destino / pdf.name)
                    print(f"[OK] Feedback de Equipo {team_id} copiado a {alumno} -> {destino/pdf.name}")
            except Exception as e:
                print(f"[!] Error procesando {pdf.name}: {e}")
    print("\nEnvio de calificados completado.")


def update_teams_file(dest_root: Path, group: str, student_names: Set[str], individual_flag: bool) -> Dict[str, int]:
    """
    Crea o complementa el archivo JSON de equipos con los alumnos del grupo.
    Actualiza el campo 'individual' con el valor proporcionado.
    Si no existe, asigna DEFAULT_TEAM_ID a todos.
    Devuelve mapping {alumno: team_id}.
    """
    equipos_dir = dest_root / EQUIPOS_DIRNAME
    equipos_dir.mkdir(parents=True, exist_ok=True)
    equipos_file = equipos_dir / f"{group}.json"

    mapping: Dict[str, int] = {}

    if equipos_file.exists():
        try:
            data = json.loads(equipos_file.read_text(encoding="utf-8"))
            for entry in data.get("students", []):
                name = entry.get("name")
                team_id = entry.get("team_id", DEFAULT_TEAM_ID)
                if name:
                    mapping[name] = team_id
        except Exception as exc:
            print(f"[!] No se pudo leer {equipos_file}: {exc}")

    updated = False
    for name in sorted(student_names):
        if name not in mapping:
            mapping[name] = DEFAULT_TEAM_ID
            updated = True

    # Siempre actualizar el archivo con el nuevo flag individual
    data = {
        "group": group,
        "individual": individual_flag,
        "students": [{"name": name, "team_id": mapping[name]} for name in sorted(mapping)],
        "default_team_id": DEFAULT_TEAM_ID,
    }
    equipos_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    if updated:
        print(f"[+] Archivo de equipos actualizado: {equipos_file}")

    return mapping


def main():
    root = BASE_ROOT

    while True:
        groups_data = list_groups(root)

        # Formatear opciones con archivos sin calificar
        group_options = [f"{clean_name} ({ungraded} sin calificar)" for clean_name, _, ungraded in groups_data]
        selected_option = pick(group_options, "Elige grupo:")

        # Obtener el nombre real del grupo (path completo)
        selected_index = group_options.index(selected_option)
        group = groups_data[selected_index][1]  # nombre completo con " - Submitted files"

        tasks_data = list_tasks(root, group)

        # Formatear opciones de tareas con nombres limpios y conteos
        task_options = [f"{clean_name} ({graded} calificadas, {ungraded} sin calificar)"
                       for clean_name, _, graded, ungraded in tasks_data]
        selected_task = pick(task_options, "Elige tarea:", allow_empty=True)

        # Si no hay tareas, regresar al menú principal
        if selected_task is None:
            print("\nNo hay tareas disponibles. Regresando al menu principal...")
            continue

        # Obtener el nombre original de la tarea seleccionada
        task_index = task_options.index(selected_task)
        task = tasks_data[task_index][1]  # nombre original de la tarea

        # Preguntar modo de trabajo
        mode_choice = pick(
            ["Equipos", "Individual"],
            "¿Trabajar por equipo o individual?",
        )
        individual_flag = (mode_choice == "Individual")

        action = pick(
            ["Descargar para calificar", "Regresar calificados"],
            "¿Que quieres hacer?",
        )
        if action.startswith("Descargar"):
            dest = input(f"Destino [Enter para {CALIFICAR_ROOT}]: ").strip() or str(CALIFICAR_ROOT)
            download_task(root, group, task, Path(dest), individual_flag)
        else:
            graded_root = input(f"Carpeta Calificar [Enter para {CALIFICAR_ROOT}]: ").strip() or str(CALIFICAR_ROOT)
            equipos_file = Path(graded_root) / EQUIPOS_DIRNAME / f"{group}.json"
            if not equipos_file.exists():
                raise SystemExit(f"No existe archivo de equipos: {equipos_file}")
            data = json.loads(equipos_file.read_text(encoding="utf-8"))
            mapping = {entry["name"]: entry.get("team_id", DEFAULT_TEAM_ID) for entry in data.get("students", []) if "name" in entry}
            return_feedback(root, group, task, Path(graded_root), individual_flag, mapping)

        # Preguntar si desea continuar
        continuar = input("\n¿Deseas realizar otra operacion? (s/n): ").strip().lower()
        if continuar not in ['s', 'si', 'sí', 'y', 'yes']:
            print("Saliendo del programa...")
            break


if __name__ == "__main__":
    main()


