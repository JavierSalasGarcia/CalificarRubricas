from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from typing import Dict, Iterable, Optional, Set, Tuple

try:
    import sounddevice as sd
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("[!] Advertencia: sounddevice y/o numpy no están instalados.")
    print("[!] Para usar la función de grabación, instala con: pip install sounddevice numpy")

# Variable global para el micrófono seleccionado
SELECTED_MIC_ID = None

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


def list_microphones():
    """Lista todos los dispositivos de entrada de audio disponibles"""
    if not AUDIO_AVAILABLE:
        return []

    devices = sd.query_devices()
    input_devices = []

    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            input_devices.append({
                'id': i,
                'name': device['name'],
                'channels': device['max_input_channels'],
                'sample_rate': device['default_samplerate']
            })

    return input_devices


def test_microphone(mic_id: int, duration: int = 3, sample_rate: int = 44100) -> tuple[bool, Optional[Path]]:
    """
    Realiza una grabación de prueba con el micrófono seleccionado.
    Retorna (éxito, ruta_archivo_temporal)
    """
    if not AUDIO_AVAILABLE:
        print("[!] No se puede grabar audio. Instala sounddevice y numpy.")
        return False, None

    temp_file = Path("temp_mic_test.wav")

    try:
        print(f"\n[+] Grabando {duration} segundos de prueba...")
        print("[+] Habla ahora para probar el micrófono...")

        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            device=mic_id,
            dtype=np.float32
        )
        sd.wait()  # Espera a que termine la grabación

        # Guardar como WAV
        with wave.open(str(temp_file), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16 bits
            wf.setframerate(sample_rate)
            wf.writeframes((recording * 32767).astype(np.int16).tobytes())

        print(f"[+] Grabación de prueba completada")
        return True, temp_file

    except Exception as e:
        print(f"[!] Error al grabar prueba: {e}")
        return False, None


def play_audio(audio_file: Path, sample_rate: int = 44100) -> bool:
    """Reproduce un archivo de audio WAV"""
    if not AUDIO_AVAILABLE:
        print("[!] No se puede reproducir audio. Instala sounddevice y numpy.")
        return False

    try:
        # Leer el archivo WAV
        with wave.open(str(audio_file), 'rb') as wf:
            sample_rate = wf.getframerate()
            n_frames = wf.getnframes()
            audio_data = wf.readframes(n_frames)
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32767.0

        print("\n[+] Reproduciendo grabación de prueba...")
        sd.play(audio_array, samplerate=sample_rate)
        sd.wait()  # Espera a que termine la reproducción
        print("[+] Reproducción completada")
        return True

    except Exception as e:
        print(f"[!] Error al reproducir audio: {e}")
        return False


def setup_microphone() -> bool:
    """
    Configura el micrófono permitiendo al usuario seleccionar y probar.
    Retorna True si se configuró correctamente.
    """
    global SELECTED_MIC_ID

    if not AUDIO_AVAILABLE:
        print("\n[!] La funcionalidad de audio no está disponible.")
        print("[!] Instala las dependencias con: pip install sounddevice numpy")
        return False

    print("\n" + "="*60)
    print("CONFIGURACIÓN DE MICRÓFONO")
    print("="*60)

    # Listar micrófonos disponibles
    microphones = list_microphones()

    if not microphones:
        print("[!] No se encontraron micrófonos disponibles.")
        return False

    print("\nMicrófonos disponibles:")
    for i, mic in enumerate(microphones, 1):
        print(f"  {i}. {mic['name']}")
        print(f"     Canales: {mic['channels']}, Sample Rate: {mic['sample_rate']:.0f} Hz")

    # Seleccionar micrófono
    while True:
        try:
            seleccion = input(f"\nSelecciona el micrófono a usar (1-{len(microphones)}): ").strip()
            if seleccion.isdigit():
                idx = int(seleccion) - 1
                if 0 <= idx < len(microphones):
                    SELECTED_MIC_ID = microphones[idx]['id']
                    print(f"\n[+] Micrófono seleccionado: {microphones[idx]['name']}")
                    break
            print("Opción inválida. Intenta de nuevo.")
        except Exception as e:
            print(f"Error: {e}")

    # Realizar prueba de grabación
    while True:
        print("\n" + "-"*60)
        respuesta = input("¿Deseas hacer una prueba de grabación? (s/n): ").strip().lower()

        if respuesta not in ['s', 'si', 'sí', 'y', 'yes']:
            break

        # Grabar prueba
        success, temp_file = test_microphone(SELECTED_MIC_ID, duration=3)

        if not success or not temp_file:
            retry = input("¿Intentar con otro micrófono? (s/n): ").strip().lower()
            if retry in ['s', 'si', 'sí', 'y', 'yes']:
                return setup_microphone()  # Reiniciar configuración
            else:
                return False

        # Reproducir prueba
        reproducir = input("\n¿Reproducir la grabación de prueba? (s/n): ").strip().lower()
        if reproducir in ['s', 'si', 'sí', 'y', 'yes']:
            play_audio(temp_file)

        # Preguntar si está satisfecho
        satisfecho = input("\n¿Estás satisfecho con la calidad del audio? (s/n): ").strip().lower()

        # Limpiar archivo temporal
        if temp_file.exists():
            temp_file.unlink()

        if satisfecho in ['s', 'si', 'sí', 'y', 'yes']:
            print("\n[+] Configuración de micrófono completada exitosamente")
            print("="*60)
            return True
        else:
            repetir = input("\n¿Intentar con otro micrófono? (s/n): ").strip().lower()
            if repetir in ['s', 'si', 'sí', 'y', 'yes']:
                return setup_microphone()  # Reiniciar configuración
            else:
                return False

    print("\n[+] Configuración guardada")
    print("="*60)
    return True


def record_audio(output_file: Path, sample_rate: int = 44100) -> bool:
    """
    Graba audio desde el micrófono y lo guarda como WAV.
    Presiona Enter para detener la grabación.
    """
    global SELECTED_MIC_ID

    if not AUDIO_AVAILABLE:
        print("[!] No se puede grabar audio. Instala sounddevice y numpy.")
        return False

    print("\n" + "="*60)
    print("GRABANDO... Presiona ENTER para detener la grabación")
    print("="*60)

    recording = []

    def callback(indata, frames, time, status):
        if status:
            print(f"[!] Estado: {status}")
        recording.append(indata.copy())

    try:
        # Usar el micrófono seleccionado si está configurado
        device = SELECTED_MIC_ID if SELECTED_MIC_ID is not None else None

        with sd.InputStream(samplerate=sample_rate, channels=1, callback=callback, device=device):
            input()  # Espera a que el usuario presione Enter

        if not recording:
            print("[!] No se grabó audio")
            return False

        # Concatenar todos los fragmentos
        audio_data = np.concatenate(recording, axis=0)

        # Guardar como WAV
        with wave.open(str(output_file), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16 bits
            wf.setframerate(sample_rate)
            wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())

        print(f"[+] Audio guardado: {output_file}")
        return True

    except Exception as e:
        print(f"[!] Error al grabar audio: {e}")
        return False


def convert_wav_to_mp3(wav_file: Path, mp3_file: Path) -> bool:
    """
    Convierte archivo WAV a MP3 usando ffmpeg.
    """
    try:
        result = subprocess.run(
            ['ffmpeg', '-i', str(wav_file), '-codec:a', 'libmp3lame', '-qscale:a', '2', str(mp3_file), '-y'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            # Eliminar el archivo WAV temporal
            wav_file.unlink()
            return True
        else:
            print(f"[!] Error al convertir a MP3: {result.stderr}")
            return False

    except FileNotFoundError:
        print("[!] ffmpeg no está instalado. Instálalo desde https://ffmpeg.org/")
        print(f"[!] Manteniendo archivo WAV: {wav_file}")
        # Renombrar WAV a MP3 (aunque no sea MP3 real)
        wav_file.rename(mp3_file.with_suffix('.wav'))
        return False
    except Exception as e:
        print(f"[!] Error inesperado al convertir: {e}")
        return False


def get_progress_file(dest_dir: Path) -> Path:
    """Retorna la ruta del archivo de progreso"""
    return dest_dir / ".grading_progress.json"


def load_progress(dest_dir: Path) -> dict:
    """Carga el progreso de calificación guardado"""
    progress_file = get_progress_file(dest_dir)
    if progress_file.exists():
        try:
            return json.loads(progress_file.read_text(encoding="utf-8"))
        except Exception:
            return {"graded_files": [], "last_index": 0}
    return {"graded_files": [], "last_index": 0}


def save_progress(dest_dir: Path, graded_files: list, last_index: int) -> None:
    """Guarda el progreso de calificación"""
    progress_file = get_progress_file(dest_dir)
    progress = {
        "graded_files": graded_files,
        "last_index": last_index,
        "timestamp": dt.datetime.now().isoformat()
    }
    progress_file.write_text(json.dumps(progress, indent=2, ensure_ascii=False), encoding="utf-8")


def review_and_grade_files(dest_dir: Path, individual_flag: bool) -> None:
    """
    Proceso interactivo para revisar y calificar archivos con grabación de audio.
    Modo secuencial con capacidad de pausar y reanudar.
    """
    if not AUDIO_AVAILABLE:
        print("\n[!] La función de grabación de audio no está disponible.")
        return

    # Obtener lista de PDFs descargados
    if individual_flag:
        pdf_pattern = "*.pdf"
    else:
        pdf_pattern = "*_Equipo_*.pdf"

    all_pdfs = sorted([p for p in dest_dir.glob(pdf_pattern) if not p.name.startswith("Cal_")])

    if not all_pdfs:
        print("\n[!] No se encontraron archivos PDF para revisar.")
        return

    # Cargar progreso previo
    progress = load_progress(dest_dir)
    graded_files = set(progress.get("graded_files", []))

    # Filtrar archivos ya calificados
    pdfs = [p for p in all_pdfs if p.name not in graded_files]

    total_files = len(all_pdfs)
    remaining_files = len(pdfs)
    completed_files = total_files - remaining_files

    print(f"\n{'='*60}")
    print(f"ESTADO DE CALIFICACIÓN")
    print(f"{'='*60}")
    print(f"Total de archivos: {total_files}")
    print(f"Ya calificados: {completed_files}")
    print(f"Por calificar: {remaining_files}")
    print(f"{'='*60}")

    if remaining_files == 0:
        print("\n[+] ¡Todas las tareas ya han sido calificadas!")
        respuesta = input("\n¿Deseas reiniciar el proceso de calificación? (s/n): ").strip().lower()
        if respuesta in ['s', 'si', 'sí', 'y', 'yes']:
            # Limpiar progreso
            progress_file = get_progress_file(dest_dir)
            if progress_file.exists():
                progress_file.unlink()
            pdfs = all_pdfs
            graded_files = set()
            completed_files = 0
            print("\n[+] Progreso reiniciado. Comenzando desde el principio...")
        else:
            return

    # Preguntar si desea iniciar/continuar el proceso de calificación
    if completed_files > 0:
        mensaje = f"\n¿Deseas CONTINUAR el proceso de calificación desde donde lo dejaste? (s/n): "
    else:
        mensaje = f"\n¿Deseas INICIAR el proceso de calificación con grabación de audio? (s/n): "

    respuesta = input(mensaje).strip().lower()
    if respuesta not in ['s', 'si', 'sí', 'y', 'yes']:
        print("Proceso de calificación cancelado.")
        return

    print(f"\n[+] Iniciando calificación secuencial...")
    print(f"[+] Puedes pausar en cualquier momento y continuar después")

    for i, pdf in enumerate(pdfs, 1):
        current_number = completed_files + i

        print(f"\n{'='*60}")
        print(f"Archivo {current_number}/{total_files}: {pdf.name}")
        print(f"{'='*60}")

        # Verificar si ya tiene audio grabado
        cal_pdf_name = f"Cal_{pdf.name}"
        audio_mp3 = dest_dir / cal_pdf_name.replace('.pdf', '.mp3')
        audio_wav = dest_dir / cal_pdf_name.replace('.pdf', '.wav')

        if audio_mp3.exists() or audio_wav.exists():
            print(f"[!] Este archivo ya tiene retroalimentación de audio grabada")
            regrabar = input("¿Deseas regrabar la retroalimentación? (s/n): ").strip().lower()
            if regrabar not in ['s', 'si', 'sí', 'y', 'yes']:
                print("[+] Manteniendo audio existente y marcando como completado...")
                graded_files.add(pdf.name)
                save_progress(dest_dir, list(graded_files), current_number)
                continue

        # Abrir el PDF
        try:
            if os.name == 'nt':  # Windows
                os.startfile(pdf)
            elif os.name == 'posix':
                if 'darwin' in sys.platform:
                    subprocess.run(['open', str(pdf)])
                else:
                    subprocess.run(['xdg-open', str(pdf)])
            print(f"[+] Abriendo: {pdf.name}")
        except Exception as e:
            print(f"[!] No se pudo abrir el archivo: {e}")

        # Proceso de grabación automático
        print("\nPresiona ENTER cuando estés listo para GRABAR la retroalimentación...")
        print("(o escribe 'saltar' para omitir este archivo, 'pausar' para detener el proceso)")

        opcion = input("\n> ").strip().lower()

        if opcion in ['pausar', 'pausa', 'pause', 'p']:
            print("\n[+] Proceso pausado. Tu progreso ha sido guardado.")
            print(f"[+] Archivos completados: {current_number - 1}/{total_files}")
            print("[+] Puedes continuar después ejecutando el programa nuevamente.")
            break
        elif opcion in ['saltar', 'skip', 's']:
            print("[!] Saltando archivo sin grabar...")
            continue

        # Grabar audio
        print("\n[+] Preparando grabación...")
        print("[+] Cuando presiones ENTER comenzará la grabación")
        print("[+] Presiona ENTER nuevamente para DETENER la grabación")
        input("\nPresiona ENTER para comenzar a grabar...")

        if record_audio(audio_wav):
            print("\n[+] Convirtiendo a MP3...")
            convert_wav_to_mp3(audio_wav, audio_mp3)
            print(f"[+] Retroalimentación guardada: {audio_mp3.name}")

            # Marcar como completado
            graded_files.add(pdf.name)
            save_progress(dest_dir, list(graded_files), current_number)
            print(f"[+] Progreso guardado ({current_number}/{total_files})")
        else:
            print("[!] No se pudo grabar el audio. Intenta de nuevo.")
            retry = input("¿Reintentar grabación? (s/n): ").strip().lower()
            if retry in ['s', 'si', 'sí', 'y', 'yes']:
                # Reintentar
                if record_audio(audio_wav):
                    print("\n[+] Convirtiendo a MP3...")
                    convert_wav_to_mp3(audio_wav, audio_mp3)
                    print(f"[+] Retroalimentación guardada: {audio_mp3.name}")
                    graded_files.add(pdf.name)
                    save_progress(dest_dir, list(graded_files), current_number)

        # Mensaje de progreso
        if current_number < total_files:
            print(f"\n[+] Continuando con el siguiente archivo ({current_number + 1}/{total_files})...")
        else:
            print("\n[+] ¡Has completado todas las calificaciones!")
            # Limpiar archivo de progreso
            progress_file = get_progress_file(dest_dir)
            if progress_file.exists():
                progress_file.unlink()
            print("[+] Archivo de progreso eliminado.")

    print("\n[+] Proceso de calificación finalizado.")


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
            if 'darwin' in sys.platform:  # macOS
                subprocess.run(['open', str(dest_dir)])
            else:  # Linux
                subprocess.run(['xdg-open', str(dest_dir)])
        print(f"[+] Carpeta abierta en el explorador de archivos")
    except Exception as e:
        print(f"[!] No se pudo abrir la carpeta automáticamente: {e}")

    # Iniciar proceso de calificación con grabación de audio
    review_and_grade_files(dest_dir, individual_flag)


def return_all_feedback(root: Path, group: str, graded_root: Path) -> None:
    """
    Procesa TODAS las tareas calificadas de un grupo.
    Busca todos los archivos Cal_*.pdf en todas las carpetas de tareas del grupo.
    """
    group_dir_path = graded_root / group
    if not group_dir_path.is_dir():
        print(f"[!] No existe carpeta de calificación para el grupo: {group_dir_path}")
        return

    print(f"\n{'='*60}")
    print(f"BUSCANDO TAREAS CALIFICADAS EN: {group}")
    print(f"{'='*60}")

    total_procesados = 0
    tareas_procesadas = []

    # Recorrer todas las carpetas de tareas en el grupo
    for task_dir in sorted(group_dir_path.iterdir()):
        if not task_dir.is_dir():
            continue

        task_name = task_dir.name

        # Buscar archivos Cal_*.pdf en esta carpeta de tarea
        cal_pdfs = list(task_dir.glob("Cal_*.pdf"))

        if not cal_pdfs:
            continue

        print(f"\n[+] Procesando tarea: {task_name}")
        print(f"    Archivos encontrados: {len(cal_pdfs)}")

        # Cargar el archivo de equipos para obtener el mapping y el modo
        equipos_file = graded_root / EQUIPOS_DIRNAME / f"{group}.json"
        if not equipos_file.exists():
            print(f"[!] No existe archivo de equipos: {equipos_file}")
            print(f"[!] Saltando tarea: {task_name}")
            continue

        try:
            data = json.loads(equipos_file.read_text(encoding="utf-8"))
            mapping = {entry["name"]: entry.get("team_id", DEFAULT_TEAM_ID)
                      for entry in data.get("students", []) if "name" in entry}
            individual_flag = data.get("individual", False)
        except Exception as e:
            print(f"[!] Error leyendo archivo de equipos: {e}")
            continue

        # Procesar cada PDF calificado
        archivos_copiados = 0

        for pdf in cal_pdfs:
            try:
                if individual_flag:
                    # Modo individual
                    name_wo_prefix = pdf.stem[4:] if pdf.stem.lower().startswith("cal_") else pdf.stem
                    parts = name_wo_prefix.split("_")
                    if len(parts) < 2:
                        print(f"[!] Nombre inesperado: {pdf.name}")
                        continue

                    alumno = "_".join(parts[1:])
                    student_dir = root / group / alumno

                    if not student_dir.is_dir():
                        print(f"[!] No existe carpeta del alumno: {alumno}")
                        continue

                    task_dir_student = next((tdir for tdir in student_dir.iterdir()
                                            if tdir.is_dir() and tdir.name.lower() == task_name.lower()), None)
                    if not task_dir_student:
                        print(f"[!] No se encontró tarea '{task_name}' para {alumno}")
                        continue

                    destino = latest_version_dir(task_dir_student) / CALIFICADO_DIRNAME
                    destino.mkdir(exist_ok=True)
                    shutil.copy2(pdf, destino / pdf.name)
                    print(f"    ✓ {alumno}")
                    archivos_copiados += 1

                    # Copiar archivos de audio
                    for ext in ['.mp3', '.wav']:
                        audio_file = pdf.with_suffix(ext)
                        if audio_file.exists():
                            shutil.copy2(audio_file, destino / audio_file.name)

                else:
                    # Modo equipos
                    name_wo_prefix = pdf.stem[4:] if pdf.stem.lower().startswith("cal_") else pdf.stem

                    if "_Equipo_" not in name_wo_prefix and "_equipo_" not in name_wo_prefix.lower():
                        print(f"[!] Nombre inesperado: {pdf.name}")
                        continue

                    # Extraer team_id
                    parts = name_wo_prefix.split("_")
                    team_id = None
                    for i, part in enumerate(parts):
                        if part.lower() == "equipo" and i + 1 < len(parts):
                            team_id = int(parts[i + 1])
                            break

                    if team_id is None:
                        print(f"[!] No se pudo extraer team_id: {pdf.name}")
                        continue

                    # Obtener miembros del equipo
                    teams: Dict[int, Set[str]] = {}
                    for name, tid in mapping.items():
                        teams.setdefault(tid, set()).add(name)

                    miembros = teams.get(team_id, set())
                    if not miembros:
                        print(f"[!] Equipo {team_id} sin miembros")
                        continue

                    # Copiar a todos los miembros
                    for alumno in miembros:
                        student_dir = root / group / alumno
                        if not student_dir.is_dir():
                            continue

                        task_dir_student = next((tdir for tdir in student_dir.iterdir()
                                                if tdir.is_dir() and tdir.name.lower() == task_name.lower()), None)
                        if not task_dir_student:
                            continue

                        destino = latest_version_dir(task_dir_student) / CALIFICADO_DIRNAME
                        destino.mkdir(exist_ok=True)
                        shutil.copy2(pdf, destino / pdf.name)
                        archivos_copiados += 1

                        # Copiar archivos de audio
                        for ext in ['.mp3', '.wav']:
                            audio_file = pdf.with_suffix(ext)
                            if audio_file.exists():
                                shutil.copy2(audio_file, destino / audio_file.name)

                    print(f"    ✓ Equipo {team_id} ({len(miembros)} miembros)")

            except Exception as e:
                print(f"[!] Error procesando {pdf.name}: {e}")

        if archivos_copiados > 0:
            total_procesados += archivos_copiados
            tareas_procesadas.append(f"{task_name}: {len(cal_pdfs)} archivos")

    # Resumen final
    print(f"\n{'='*60}")
    print(f"RESUMEN DE ENVÍO")
    print(f"{'='*60}")
    if tareas_procesadas:
        print(f"Tareas procesadas:")
        for tarea in tareas_procesadas:
            print(f"  • {tarea}")
        print(f"\nTotal de archivos copiados: {total_procesados}")
    else:
        print("No se encontraron tareas calificadas para enviar.")
    print(f"{'='*60}\n")


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

            # Copiar archivo de audio MP3 si existe
            audio_mp3 = pdf.with_suffix('.mp3')
            if audio_mp3.exists():
                shutil.copy2(audio_mp3, destino / audio_mp3.name)
                print(f"[OK] Audio copiado a {alumno} -> {destino/audio_mp3.name}")
            # También buscar archivo WAV por si no se pudo convertir a MP3
            audio_wav = pdf.with_suffix('.wav')
            if audio_wav.exists():
                shutil.copy2(audio_wav, destino / audio_wav.name)
                print(f"[OK] Audio WAV copiado a {alumno} -> {destino/audio_wav.name}")
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

                    # Copiar archivo de audio MP3 si existe
                    audio_mp3 = pdf.with_suffix('.mp3')
                    if audio_mp3.exists():
                        shutil.copy2(audio_mp3, destino / audio_mp3.name)
                        print(f"[OK] Audio copiado a {alumno} -> {destino/audio_mp3.name}")
                    # También buscar archivo WAV por si no se pudo convertir a MP3
                    audio_wav = pdf.with_suffix('.wav')
                    if audio_wav.exists():
                        shutil.copy2(audio_wav, destino / audio_wav.name)
                        print(f"[OK] Audio WAV copiado a {alumno} -> {destino/audio_wav.name}")
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

    # Configurar micrófono al inicio si está disponible
    if AUDIO_AVAILABLE:
        print("\n" + "="*60)
        print("BIENVENIDO AL SISTEMA DE CALIFICACIÓN")
        print("="*60)

        config_mic = input("\n¿Deseas configurar el micrófono ahora? (s/n): ").strip().lower()
        if config_mic in ['s', 'si', 'sí', 'y', 'yes']:
            if not setup_microphone():
                print("\n[!] No se configuró el micrófono. Puedes continuar sin grabación de audio.")
                input("Presiona ENTER para continuar...")
        else:
            print("\n[!] Micrófono no configurado. Se usará el dispositivo predeterminado del sistema.")

    while True:
        groups_data = list_groups(root)

        # Formatear opciones con archivos sin calificar
        group_options = [f"{clean_name} ({ungraded} sin calificar)" for clean_name, _, ungraded in groups_data]
        selected_option = pick(group_options, "Elige grupo:")

        # Obtener el nombre real del grupo (path completo)
        selected_index = group_options.index(selected_option)
        group = groups_data[selected_index][1]  # nombre completo con " - Submitted files"

        # Preguntar qué acción quiere hacer
        action = pick(
            ["Descargar para calificar", "Regresar TODAS las calificadas", "Configurar micrófono"],
            "¿Que quieres hacer?",
        )

        if action.startswith("Configurar"):
            if AUDIO_AVAILABLE:
                setup_microphone()
            else:
                print("\n[!] La funcionalidad de audio no está disponible.")
                print("[!] Instala las dependencias con: pip install sounddevice numpy")
            continue

        # Si elige "Regresar TODAS las calificadas"
        if action.startswith("Regresar"):
            graded_root = input(f"Carpeta Calificar [Enter para {CALIFICAR_ROOT}]: ").strip() or str(CALIFICAR_ROOT)
            graded_root_path = Path(graded_root)

            # Verificar que existe el archivo de equipos
            equipos_file = graded_root_path / EQUIPOS_DIRNAME / f"{group}.json"
            if not equipos_file.exists():
                print(f"\n[!] No existe archivo de equipos: {equipos_file}")
                print(f"[!] Debes descargar al menos una tarea primero.")
                continue

            # Procesar todas las tareas calificadas
            return_all_feedback(root, group, graded_root_path)

            # Preguntar si desea continuar
            continuar = input("\n¿Deseas realizar otra operacion? (s/n): ").strip().lower()
            if continuar not in ['s', 'si', 'sí', 'y', 'yes']:
                print("Saliendo del programa...")
                break
            continue

        # Si elige "Descargar para calificar"
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

        # Descargar tarea
        dest = input(f"Destino [Enter para {CALIFICAR_ROOT}]: ").strip() or str(CALIFICAR_ROOT)
        download_task(root, group, task, Path(dest), individual_flag)

        # Preguntar si desea continuar
        continuar = input("\n¿Deseas realizar otra operacion? (s/n): ").strip().lower()
        if continuar not in ['s', 'si', 'sí', 'y', 'yes']:
            print("Saliendo del programa...")
            break


if __name__ == "__main__":
    main()


