"""
FASE 3: Calificación Automática con Gemini

Este script:
1. Lee PDFs sin prefijo Cal_
2. Busca transcripciones de audio (si existen)
3. Carga la rúbrica correspondiente
4. Envía PDF + rúbrica + transcripción a Gemini 1.5 Flash
5. Genera página de calificación profesional
6. Fusiona con el PDF original
7. Sube calificación a la base de datos

Uso:
    python calificar_gemini.py
"""

import json
import mysql.connector
import google.generativeai as genai
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re

# Librerías para PDFs
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO


# Configuración
CALIFICAR_ROOT = Path(r"D:\tareas\Calificar")


def cargar_credenciales():
    """Carga credenciales desde credentials.json"""
    cred_file = Path(__file__).parent / "credentials.json"
    if not cred_file.exists():
        raise FileNotFoundError("No se encontró credentials.json")

    with open(cred_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def cargar_rubricas():
    """Carga configuración de rúbricas desde rubricas.json"""
    rub_file = Path(__file__).parent / "rubricas.json"
    if not rub_file.exists():
        raise FileNotFoundError(
            "No se encontró rubricas.json. "
            "Crea el archivo con las rúbricas de cada tarea."
        )

    with open(rub_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data.get('rubricas', {})


def conectar_db(config):
    """Conecta a la base de datos MySQL"""
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


def configurar_gemini(api_key: str):
    """Configura la API de Gemini"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    return model


def buscar_pdfs_sin_calificar(root_dir: Path) -> List[Dict]:
    """
    Busca todos los PDFs que NO tengan prefijo Cal_
    y que NO tengan ya un PDF calificado correspondiente.
    """
    pdfs_pendientes = []

    print(f"\n[+] Buscando PDFs sin calificar en: {root_dir}")

    if not root_dir.exists():
        print(f"[!] No existe el directorio: {root_dir}")
        return []

    for grupo_dir in root_dir.iterdir():
        if not grupo_dir.is_dir():
            continue

        for tarea_dir in grupo_dir.iterdir():
            if not tarea_dir.is_dir():
                continue

            # Buscar PDFs sin prefijo "Cal_"
            for pdf_file in tarea_dir.glob("*.pdf"):
                if pdf_file.name.startswith("Cal_"):
                    continue  # Ya está calificado

                # Verificar si ya existe el PDF calificado
                cal_pdf = tarea_dir / f"Cal_{pdf_file.name}"
                if cal_pdf.exists():
                    continue  # Ya tiene calificación

                pdfs_pendientes.append({
                    'ruta': pdf_file,
                    'grupo': grupo_dir.name,
                    'tarea': tarea_dir.name,
                    'archivo': pdf_file.name
                })

    print(f"[+] Se encontraron {len(pdfs_pendientes)} PDFs sin calificar")
    return pdfs_pendientes


def buscar_transcripcion(pdf_path: Path) -> Optional[Dict]:
    """
    Busca el archivo de transcripción correspondiente al PDF.
    El audio se llama Cal_<nombre>.mp3 y su transcripción Cal_<nombre>_transcripcion.json
    """
    # Construir nombre esperado del archivo de transcripción
    # PDF: <tarea>_<alumno>.pdf
    # Audio: Cal_<tarea>_<alumno>.mp3
    # Transcripción: Cal_<tarea>_<alumno>_transcripcion.json

    base_name = pdf_path.stem  # nombre sin extensión
    transcripcion_file = pdf_path.parent / f"Cal_{base_name}_transcripcion.json"

    if transcripcion_file.exists():
        try:
            with open(transcripcion_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Error al leer transcripción: {e}")
            return None

    return None


def cargar_rubrica(tarea_nombre: str, rubricas_config: Dict) -> Tuple[Optional[str], Optional[Dict]]:
    """
    Carga el texto de la rúbrica correspondiente a la tarea.
    Retorna (texto_rubrica, config_rubrica)
    """
    # Buscar la rúbrica en la configuración
    rubrica_info = rubricas_config.get(tarea_nombre)

    if not rubrica_info:
        print(f"[!] No se encontró configuración de rúbrica para: {tarea_nombre}")
        return None, None

    # Cargar el archivo de rúbrica
    rubrica_path = Path(rubrica_info['archivo'])

    if not rubrica_path.exists():
        print(f"[!] No existe el archivo de rúbrica: {rubrica_path}")
        return None, None

    try:
        with open(rubrica_path, 'r', encoding='utf-8') as f:
            texto_rubrica = f.read()

        return texto_rubrica, rubrica_info

    except Exception as e:
        print(f"[!] Error al leer rúbrica: {e}")
        return None, None


def construir_prompt(rubrica: str, transcripcion: Optional[Dict]) -> str:
    """
    Construye el prompt para enviar a Gemini.
    """
    prompt = f"""Eres un asistente de calificación académica. Debes evaluar el siguiente trabajo estudiantil.

RÚBRICA DE EVALUACIÓN:
{rubrica}

INSTRUCCIONES:
1. Analiza TODO el contenido del PDF adjunto, incluyendo texto, fórmulas, diagramas e imágenes
2. Evalúa cada criterio de la rúbrica de manera justa y objetiva
3. Proporciona retroalimentación constructiva y específica
4. La calificación debe estar en escala de 0.0 a 10.0 con una posición decimal
"""

    if transcripcion:
        prompt += f"""
OBSERVACIONES DEL PROFESOR (Audio transcrito):
El profesor que revisó esta tarea grabó las siguientes observaciones:
"{transcripcion.get('transcripcion', '')}"

Estas observaciones pueden ayudarte a contextualizar mejor la evaluación.
"""

    prompt += """
FORMATO DE RESPUESTA:
Debes responder ÚNICAMENTE en formato JSON válido, sin texto adicional antes ni después.

{
  "calificacion_total": <número entre 0.0 y 10.0>,
  "calificacion_maxima": <número>,
  "criterios": [
    {
      "nombre": "<nombre del criterio>",
      "puntos_obtenidos": <número>,
      "puntos_maximos": <número>,
      "comentario": "<retroalimentación específica del criterio>"
    }
  ],
  "retroalimentacion_general": "<comentarios generales del trabajo>",
  "fortalezas": [
    "<fortaleza 1>",
    "<fortaleza 2>",
    "<fortaleza 3>"
  ],
  "areas_mejora": [
    "<área de mejora 1>",
    "<área de mejora 2>",
    "<área de mejora 3>"
  ]
}

IMPORTANTE: Responde SOLO con el JSON, sin markdown, sin ```json, sin texto adicional.
"""

    return prompt


def calificar_con_gemini(model, pdf_path: Path, prompt: str) -> Optional[Dict]:
    """
    Envía el PDF y el prompt a Gemini para obtener la calificación.
    """
    print(f"\n[→] Calificando con Gemini: {pdf_path.name}")

    try:
        # Cargar el PDF como archivo
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()

        # Crear el objeto de archivo para Gemini
        pdf_part = {
            'mime_type': 'application/pdf',
            'data': pdf_data
        }

        # Enviar a Gemini
        print("    Enviando a Gemini API...")
        response = model.generate_content([prompt, pdf_part])

        # Extraer texto de la respuesta
        response_text = response.text.strip()

        # Intentar parsear JSON
        # Limpiar posibles marcadores de código
        response_text = response_text.replace('```json', '').replace('```', '').strip()

        calificacion_data = json.loads(response_text)

        print(f"[✓] Calificación obtenida: {calificacion_data.get('calificacion_total', 'N/A')}/10.0")

        return calificacion_data

    except json.JSONDecodeError as e:
        print(f"[!] Error al parsear respuesta JSON de Gemini: {e}")
        print(f"    Respuesta recibida: {response_text[:500]}")
        return None
    except Exception as e:
        print(f"[!] Error al calificar con Gemini: {e}")
        return None


def generar_pagina_calificacion(calificacion_data: Dict, tarea_nombre: str, alumno_nombre: str) -> BytesIO:
    """
    Genera una página PDF profesional con la calificación usando ReportLab.
    Retorna un BytesIO con el PDF generado.
    """
    buffer = BytesIO()

    # Crear documento
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    # Contenedor de elementos
    elements = []

    # Estilos
    styles = getSampleStyleSheet()

    # Estilo para título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    # Estilo para subtítulos
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#444444'),
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )

    # Título principal
    elements.append(Paragraph("CALIFICACIÓN AUTOMÁTICA", title_style))
    elements.append(Spacer(1, 0.2*inch))

    # Información general
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    info_data = [
        ['Alumno:', alumno_nombre],
        ['Tarea:', tarea_nombre],
        ['Fecha de calificación:', fecha],
        ['', '']
    ]

    info_table = Table(info_data, colWidths=[2*inch, 4.5*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#555555')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))

    # Calificación total - Destacada
    cal_total = calificacion_data.get('calificacion_total', 0)
    cal_max = calificacion_data.get('calificacion_maxima', 10.0)

    cal_box_data = [[f'CALIFICACIÓN TOTAL: {cal_total:.1f} / {cal_max:.1f}']]
    cal_box = Table(cal_box_data, colWidths=[6.5*inch])
    cal_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#4CAF50')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 16),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#2E7D32')),
    ]))

    elements.append(cal_box)
    elements.append(Spacer(1, 0.3*inch))

    # Desglose por criterios
    elements.append(Paragraph("DESGLOSE POR CRITERIOS", subtitle_style))
    elements.append(Spacer(1, 0.1*inch))

    criterios_data = [['Criterio', 'Puntos', 'Comentario']]

    for criterio in calificacion_data.get('criterios', []):
        criterios_data.append([
            criterio.get('nombre', ''),
            f"{criterio.get('puntos_obtenidos', 0):.1f}/{criterio.get('puntos_maximos', 0):.1f}",
            criterio.get('comentario', '')[:150]  # Limitar longitud
        ])

    criterios_table = Table(criterios_data, colWidths=[1.8*inch, 1*inch, 3.7*inch])
    criterios_table.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2196F3')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

        # Contenido
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Bordes
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#2196F3')),

        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),

        # Alternar colores de filas
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
    ]))

    elements.append(criterios_table)
    elements.append(Spacer(1, 0.3*inch))

    # Retroalimentación general
    elements.append(Paragraph("RETROALIMENTACIÓN GENERAL", subtitle_style))
    elements.append(Spacer(1, 0.1*inch))

    retro_text = calificacion_data.get('retroalimentacion_general', 'Sin comentarios')
    retro_para = Paragraph(retro_text, styles['Normal'])
    elements.append(retro_para)
    elements.append(Spacer(1, 0.2*inch))

    # Fortalezas
    fortalezas = calificacion_data.get('fortalezas', [])
    if fortalezas:
        elements.append(Paragraph("FORTALEZAS", subtitle_style))
        elements.append(Spacer(1, 0.05*inch))

        for fortaleza in fortalezas:
            elements.append(Paragraph(f"• {fortaleza}", styles['Normal']))

        elements.append(Spacer(1, 0.2*inch))

    # Áreas de mejora
    areas_mejora = calificacion_data.get('areas_mejora', [])
    if areas_mejora:
        elements.append(Paragraph("ÁREAS DE MEJORA", subtitle_style))
        elements.append(Spacer(1, 0.05*inch))

        for area in areas_mejora:
            elements.append(Paragraph(f"• {area}", styles['Normal']))

    # Generar PDF
    doc.build(elements)

    buffer.seek(0)
    return buffer


def fusionar_pdfs(pagina_calificacion: BytesIO, pdf_original: Path, salida: Path) -> bool:
    """
    Fusiona la página de calificación con el PDF original del alumno.
    """
    try:
        writer = PdfWriter()

        # Agregar página de calificación
        cal_reader = PdfReader(pagina_calificacion)
        writer.add_page(cal_reader.pages[0])

        # Agregar PDF original
        original_reader = PdfReader(pdf_original)
        for page in original_reader.pages:
            writer.add_page(page)

        # Guardar PDF fusionado
        with open(salida, 'wb') as output_file:
            writer.write(output_file)

        print(f"[✓] PDF calificado generado: {salida.name}")
        return True

    except Exception as e:
        print(f"[!] Error al fusionar PDFs: {e}")
        return False


def extraer_nombre_alumno(filename: str, tarea_nombre: str) -> str:
    """
    Extrae el nombre del alumno del nombre del archivo.
    Formato: <tarea>_<nombre_alumno>.pdf
    """
    name_without_ext = Path(filename).stem

    # Quitar el nombre de la tarea del inicio
    # Reemplazar el nombre de la tarea por vacío
    tarea_clean = tarea_nombre.replace(" ", "_")

    if name_without_ext.startswith(tarea_clean + "_"):
        alumno = name_without_ext[len(tarea_clean) + 1:]
        return alumno.replace("_", " ")

    # Estrategia alternativa: tomar todo después del primer "_"
    parts = name_without_ext.split("_", 1)
    if len(parts) > 1:
        return parts[1].replace("_", " ")

    return name_without_ext.replace("_", " ")


def guardar_calificacion_db(conn, alumno_nombre: str, tarea_nombre: str, grupo_nombre: str,
                            calificacion: float, rutas: Dict) -> bool:
    """
    Guarda la calificación en la base de datos.
    """
    try:
        cursor = conn.cursor()

        # Buscar alumno por nombre
        cursor.execute(
            "SELECT id FROM alumnos WHERE nombre = %s",
            (alumno_nombre,)
        )
        result = cursor.fetchone()

        if not result:
            print(f"[!] No se encontró alumno en BD: {alumno_nombre}")
            return False

        alumno_id = result[0]

        # Buscar o crear tarea
        cursor.execute(
            "SELECT id FROM grupos WHERE nombre = %s",
            (grupo_nombre,)
        )
        grupo_result = cursor.fetchone()

        if not grupo_result:
            print(f"[!] No se encontró grupo en BD: {grupo_nombre}")
            return False

        grupo_id = grupo_result[0]

        # Buscar o crear tarea
        cursor.execute(
            "SELECT id FROM tareas WHERE nombre = %s AND grupo_id = %s",
            (tarea_nombre, grupo_id)
        )
        tarea_result = cursor.fetchone()

        if tarea_result:
            tarea_id = tarea_result[0]
        else:
            # Crear tarea
            cursor.execute(
                "INSERT INTO tareas (grupo_id, nombre) VALUES (%s, %s)",
                (grupo_id, tarea_nombre)
            )
            conn.commit()
            tarea_id = cursor.lastrowid

        # Insertar o actualizar calificación
        cursor.execute("""
            INSERT INTO calificaciones
            (alumno_id, tarea_id, calificacion, ruta_pdf_calificado, ruta_audio, ruta_transcripcion)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            calificacion = VALUES(calificacion),
            ruta_pdf_calificado = VALUES(ruta_pdf_calificado),
            ruta_audio = VALUES(ruta_audio),
            ruta_transcripcion = VALUES(ruta_transcripcion),
            fecha_calificacion = CURRENT_TIMESTAMP
        """, (
            alumno_id,
            tarea_id,
            calificacion,
            rutas.get('pdf_calificado'),
            rutas.get('audio'),
            rutas.get('transcripcion')
        ))

        conn.commit()
        cursor.close()

        print(f"[✓] Calificación guardada en la base de datos")
        return True

    except mysql.connector.Error as e:
        print(f"[!] Error al guardar en BD: {e}")
        conn.rollback()
        return False


def main():
    """Función principal"""
    print("="*60)
    print("CALIFICACIÓN AUTOMÁTICA CON GEMINI")
    print("Sistema de Calificación Automática - Fase 3")
    print("="*60)

    try:
        # Cargar configuración
        print("\n[+] Cargando configuración...")
        credentials = cargar_credenciales()
        rubricas_config = cargar_rubricas()

        # Configurar Gemini
        print("[+] Configurando Gemini API...")
        model = configurar_gemini(credentials['gemini_api_key'])

        # Conectar a la base de datos
        print("[+] Conectando a la base de datos...")
        conn = conectar_db(credentials['db_config'])

        # Buscar PDFs sin calificar
        pdfs_pendientes = buscar_pdfs_sin_calificar(CALIFICAR_ROOT)

        if not pdfs_pendientes:
            print("\n[+] No hay PDFs pendientes de calificar")
            print("    Todos los PDFs ya tienen su calificación")
            conn.close()
            return 0

        # Mostrar lista
        print("\n📋 PDFs a calificar:")
        for i, pdf_info in enumerate(pdfs_pendientes[:10], 1):
            print(f"  {i}. {pdf_info['grupo']} / {pdf_info['tarea']}")
            print(f"     {pdf_info['archivo']}")

        if len(pdfs_pendientes) > 10:
            print(f"  ... y {len(pdfs_pendientes) - 10} PDFs más")

        # Confirmar
        print(f"\n[!] Se calificarán {len(pdfs_pendientes)} PDFs")
        print("    Esto consumirá créditos de la API de Gemini")

        confirmar = input("\n¿Continuar con la calificación? (s/n): ").strip().lower()
        if confirmar not in ['s', 'si', 'sí', 'y', 'yes']:
            print("\n[!] Proceso cancelado")
            conn.close()
            return 1

        # Procesar cada PDF
        print("\n" + "="*60)
        print("INICIANDO CALIFICACIONES")
        print("="*60)

        stats = {'exitosos': 0, 'fallidos': 0}

        for i, pdf_info in enumerate(pdfs_pendientes, 1):
            print(f"\n{'='*60}")
            print(f"[{i}/{len(pdfs_pendientes)}] {pdf_info['archivo']}")
            print(f"{'='*60}")

            # Cargar rúbrica
            rubrica_texto, rubrica_info = cargar_rubrica(pdf_info['tarea'], rubricas_config)
            if not rubrica_texto:
                print(f"[!] Saltando por falta de rúbrica")
                stats['fallidos'] += 1
                continue

            # Buscar transcripción
            transcripcion = buscar_transcripcion(pdf_info['ruta'])
            if transcripcion:
                print(f"[+] Transcripción de audio encontrada")
            else:
                print(f"[+] Sin transcripción de audio")

            # Construir prompt
            prompt = construir_prompt(rubrica_texto, transcripcion)

            # Calificar con Gemini
            calificacion_data = calificar_con_gemini(model, pdf_info['ruta'], prompt)

            if not calificacion_data:
                print(f"[!] Fallo en la calificación")
                stats['fallidos'] += 1
                continue

            # Extraer nombre del alumno
            alumno_nombre = extraer_nombre_alumno(pdf_info['archivo'], pdf_info['tarea'])

            # Generar página de calificación
            print(f"[+] Generando PDF de calificación...")
            pagina_cal = generar_pagina_calificacion(
                calificacion_data,
                pdf_info['tarea'],
                alumno_nombre
            )

            # Fusionar con PDF original
            pdf_calificado = pdf_info['ruta'].parent / f"Cal_{pdf_info['archivo']}"
            if not fusionar_pdfs(pagina_cal, pdf_info['ruta'], pdf_calificado):
                stats['fallidos'] += 1
                continue

            # Guardar en base de datos
            rutas = {
                'pdf_calificado': str(pdf_calificado),
                'audio': str(pdf_info['ruta'].parent / f"Cal_{pdf_info['ruta'].stem}.mp3")
                        if (pdf_info['ruta'].parent / f"Cal_{pdf_info['ruta'].stem}.mp3").exists() else None,
                'transcripcion': str(pdf_info['ruta'].parent / f"Cal_{pdf_info['ruta'].stem}_transcripcion.json")
                                if transcripcion else None
            }

            if guardar_calificacion_db(
                conn,
                alumno_nombre,
                pdf_info['tarea'],
                pdf_info['grupo'],
                calificacion_data.get('calificacion_total', 0),
                rutas
            ):
                stats['exitosos'] += 1
            else:
                stats['fallidos'] += 1

        # Resumen
        print("\n" + "="*60)
        print("RESUMEN DE CALIFICACIONES")
        print("="*60)
        print(f"Total procesados: {len(pdfs_pendientes)}")
        print(f"Exitosos: {stats['exitosos']}")
        print(f"Fallidos: {stats['fallidos']}")
        print("="*60)

        conn.close()
        print("\n✓ Proceso completado")

    except Exception as e:
        print(f"\n[!] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
