"""
FASE 2: Transcripción de Audios con Whisper

Este script busca todos los archivos Cal_*.mp3 en las carpetas de tareas,
los transcribe usando Whisper (modelo medium) y guarda las transcripciones
en formato JSON con metadata.

Uso:
    python transcribir_audios.py

El script procesará todos los audios que no tengan transcripción aún.
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Optional
import whisper


# Configuración
CALIFICAR_ROOT = Path(r"D:\tareas\Calificar")
WHISPER_MODEL = "medium"  # Opciones: tiny, base, small, medium, large
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a']


def cargar_modelo_whisper(model_name: str = WHISPER_MODEL):
    """
    Carga el modelo de Whisper.
    La primera vez descargará el modelo (puede tardar varios minutos).
    """
    print(f"\n[+] Cargando modelo Whisper '{model_name}'...")
    print("    (Esto puede tardar unos minutos la primera vez)")

    try:
        model = whisper.load_model(model_name)
        print(f"[✓] Modelo '{model_name}' cargado exitosamente")
        return model
    except Exception as e:
        print(f"[!] Error al cargar el modelo: {e}")
        print("\n    Si el modelo no está instalado, se descargará automáticamente.")
        print("    Asegúrate de tener conexión a internet.")
        raise


def buscar_audios_sin_transcribir(root_dir: Path) -> List[Dict]:
    """
    Busca todos los archivos Cal_*.mp3 que no tengan transcripción.
    Retorna lista de diccionarios con información del audio.
    """
    audios_pendientes = []

    print(f"\n[+] Buscando archivos de audio en: {root_dir}")

    if not root_dir.exists():
        print(f"[!] No existe el directorio: {root_dir}")
        return []

    # Recorrer todas las carpetas de grupos y tareas
    for grupo_dir in root_dir.iterdir():
        if not grupo_dir.is_dir():
            continue

        for tarea_dir in grupo_dir.iterdir():
            if not tarea_dir.is_dir():
                continue

            # Buscar archivos de audio con prefijo "Cal_"
            for ext in AUDIO_EXTENSIONS:
                for audio_file in tarea_dir.glob(f"Cal_*{ext}"):
                    # Verificar si ya existe la transcripción
                    json_file = audio_file.with_suffix('.json')
                    transcripcion_file = audio_file.parent / f"{audio_file.stem}_transcripcion.json"

                    if json_file.exists() or transcripcion_file.exists():
                        continue  # Ya tiene transcripción

                    # Agregar a la lista de pendientes
                    audios_pendientes.append({
                        'ruta': audio_file,
                        'grupo': grupo_dir.name,
                        'tarea': tarea_dir.name,
                        'archivo': audio_file.name
                    })

    print(f"[+] Se encontraron {len(audios_pendientes)} audios sin transcribir")
    return audios_pendientes


def transcribir_audio(model, audio_path: Path, verbose: bool = False) -> Dict:
    """
    Transcribe un archivo de audio usando Whisper.
    Retorna diccionario con la transcripción y metadata.
    """
    print(f"\n[→] Transcribiendo: {audio_path.name}")

    try:
        # Transcribir con Whisper
        inicio = time.time()

        result = model.transcribe(
            str(audio_path),
            language='es',  # Español
            verbose=verbose,
            fp16=False  # Desactivar fp16 para compatibilidad con CPU
        )

        duracion = time.time() - inicio

        # Extraer información
        transcripcion_data = {
            'alumno': extraer_nombre_alumno(audio_path.name),
            'tarea': audio_path.parent.name,
            'audio_file': audio_path.name,
            'transcripcion': result['text'].strip(),
            'duracion_segundos': round(result.get('duration', 0), 2),
            'idioma_detectado': result.get('language', 'es'),
            'tiempo_procesamiento': round(duracion, 2)
        }

        print(f"[✓] Transcripción completada en {duracion:.1f}s")
        print(f"    Duración del audio: {transcripcion_data['duracion_segundos']}s")
        print(f"    Texto ({len(transcripcion_data['transcripcion'])} caracteres): "
              f"{transcripcion_data['transcripcion'][:100]}...")

        return transcripcion_data

    except Exception as e:
        print(f"[!] Error al transcribir {audio_path.name}: {e}")
        return None


def extraer_nombre_alumno(filename: str) -> str:
    """
    Extrae el nombre del alumno del nombre del archivo.
    Formato esperado: Cal_<tarea>_<nombre_alumno>.mp3
    """
    # Quitar extensión
    name_without_ext = Path(filename).stem

    # Quitar prefijo "Cal_"
    if name_without_ext.startswith("Cal_"):
        name_without_ext = name_without_ext[4:]

    # Dividir por underscore y tomar desde el segundo elemento
    # (el primero es parte del nombre de la tarea)
    parts = name_without_ext.split("_")

    if len(parts) >= 2:
        # Reunir todo excepto la primera parte (que es la tarea)
        # Buscar donde termina el nombre de la tarea
        # Usualmente es "1. Nombre de Tarea_Nombre Alumno"
        # Entonces buscamos el patrón después del último "_"

        # Estrategia simple: tomar todo después del primer "_Equipo_" o
        # después de la numeración de tarea
        nombre = "_".join(parts[1:])
        return nombre.replace("_", " ")

    return name_without_ext


def guardar_transcripcion(audio_path: Path, transcripcion_data: Dict):
    """
    Guarda la transcripción en un archivo JSON junto al audio.
    """
    json_path = audio_path.parent / f"{audio_path.stem}_transcripcion.json"

    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(transcripcion_data, f, indent=2, ensure_ascii=False)

        print(f"[✓] Transcripción guardada: {json_path.name}")
        return True

    except Exception as e:
        print(f"[!] Error al guardar transcripción: {e}")
        return False


def mostrar_resumen(total: int, exitosos: int, fallidos: int, saltados: int, tiempo_total: float):
    """Muestra un resumen del proceso de transcripción"""
    print("\n" + "="*60)
    print("RESUMEN DE TRANSCRIPCIONES")
    print("="*60)
    print(f"Total de audios procesados: {total}")
    print(f"Transcripciones exitosas: {exitosos}")
    print(f"Errores: {fallidos}")
    print(f"Saltados (ya transcritos): {saltados}")
    print(f"Tiempo total: {tiempo_total/60:.1f} minutos")

    if exitosos > 0:
        print(f"Tiempo promedio por audio: {tiempo_total/exitosos:.1f} segundos")

    print("="*60)


def main():
    """Función principal"""
    print("="*60)
    print("TRANSCRIPCIÓN DE AUDIOS CON WHISPER")
    print("Sistema de Calificación Automática - Fase 2")
    print("="*60)

    try:
        # Buscar audios sin transcribir
        audios_pendientes = buscar_audios_sin_transcribir(CALIFICAR_ROOT)

        if not audios_pendientes:
            print("\n[+] No hay audios pendientes de transcribir")
            print("    Todos los audios ya tienen su transcripción")
            return 0

        # Mostrar lista de audios a procesar
        print("\n📋 Audios a transcribir:")
        for i, audio_info in enumerate(audios_pendientes[:10], 1):
            print(f"  {i}. {audio_info['grupo']} / {audio_info['tarea']}")
            print(f"     {audio_info['archivo']}")

        if len(audios_pendientes) > 10:
            print(f"  ... y {len(audios_pendientes) - 10} audios más")

        # Confirmar antes de continuar
        print(f"\n[!] Se procesarán {len(audios_pendientes)} audios")
        print("    Esto puede tomar varios minutos dependiendo de la duración de los audios")

        confirmar = input("\n¿Continuar con la transcripción? (s/n): ").strip().lower()
        if confirmar not in ['s', 'si', 'sí', 'y', 'yes']:
            print("\n[!] Proceso cancelado por el usuario")
            return 1

        # Cargar modelo de Whisper
        model = cargar_modelo_whisper(WHISPER_MODEL)

        # Procesar cada audio
        print("\n" + "="*60)
        print("INICIANDO TRANSCRIPCIONES")
        print("="*60)

        estadisticas = {
            'exitosos': 0,
            'fallidos': 0,
            'saltados': 0
        }

        inicio_total = time.time()

        for i, audio_info in enumerate(audios_pendientes, 1):
            print(f"\n[{i}/{len(audios_pendientes)}] Procesando: {audio_info['archivo']}")

            # Transcribir
            transcripcion_data = transcribir_audio(model, audio_info['ruta'])

            if transcripcion_data:
                # Guardar transcripción
                if guardar_transcripcion(audio_info['ruta'], transcripcion_data):
                    estadisticas['exitosos'] += 1
                else:
                    estadisticas['fallidos'] += 1
            else:
                estadisticas['fallidos'] += 1

            # Pequeña pausa entre transcripciones
            if i < len(audios_pendientes):
                time.sleep(0.5)

        tiempo_total = time.time() - inicio_total

        # Mostrar resumen
        mostrar_resumen(
            len(audios_pendientes),
            estadisticas['exitosos'],
            estadisticas['fallidos'],
            estadisticas['saltados'],
            tiempo_total
        )

        print("\n✓ Proceso de transcripción completado")
        print("\nPróximo paso:")
        print("  Ejecuta calificar_gemini.py para calificar las tareas con IA")

    except Exception as e:
        print(f"\n[!] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
