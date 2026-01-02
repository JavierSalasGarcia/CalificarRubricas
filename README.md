# 📚 Sistema de Calificación Automática con Gemini y Whisper

Sistema completo para calificar tareas académicas usando inteligencia artificial. Combina grabación de audio, transcripción automática con Whisper y calificación inteligente con Gemini 1.5 Flash.

## 🎯 Características

- **Fase 1**: Descarga de tareas y grabación de retroalimentación en audio
- **Fase 2**: Transcripción automática de audios con Whisper (modelo medium)
- **Fase 3**: Calificación automática con Gemini analizando PDFs, imágenes y transcripciones
- **Base de datos**: Almacenamiento de calificaciones, alumnos y asistencias en MySQL
- **PDFs profesionales**: Generación de página de calificación fusionada con el trabajo original

---

## 📋 Requisitos Previos

### Software Necesario

1. **Python 3.10** (recomendado)
2. **ffmpeg** (para conversión de audio WAV → MP3)
3. **MySQL** (base de datos)
4. **Conexión a internet** (primera vez para descargar modelo Whisper)

### Windows - Instalación de ffmpeg

```powershell
# Opción A: Con Chocolatey (recomendado)
choco install ffmpeg

# Opción B: Descarga manual desde https://ffmpeg.org/download.html
# Luego agregar al PATH del sistema
```

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd CalificarRubricas
```

### 2. Instalar dependencias de Python

```bash
pip install -r requirements.txt
```

**Nota**: La primera vez que ejecutes Whisper, descargará el modelo medium (~1.5 GB). Ten paciencia.

### 3. Configurar credenciales

Edita el archivo `credentials.json` con tus credenciales:

```json
{
  "gemini_api_key": "TU_API_KEY_AQUI",
  "db_config": {
    "host": "electrokumo.com",
    "user": "tu_usuario",
    "password": "tu_password",
    "database": "nombre_base_datos",
    "port": 3306
  }
}
```

### 4. Configurar rúbricas

Edita el archivo `rubricas.json` para definir las rúbricas de cada tarea:

```json
{
  "rubricas": {
    "1. Conectarse a una Raspberry desde cualquier": {
      "archivo": "rubricas/raspberry_conexion.txt",
      "puntos_maximos": 10.0,
      "criterios": [
        {"nombre": "Configuración correcta", "puntos": 3.0},
        {"nombre": "Documentación clara", "puntos": 3.0},
        {"nombre": "Pruebas realizadas", "puntos": 2.0},
        {"nombre": "Capturas de pantalla", "puntos": 2.0}
      ]
    }
  }
}
```

Crea una carpeta `rubricas/` y coloca los archivos .txt de cada rúbrica.

### 5. Crear la base de datos

```bash
python db_setup.py
```

Esto creará todas las tablas necesarias: `grupos`, `alumnos`, `tareas`, `calificaciones`, `asistencias`.

### 6. Cargar alumnos

Crea un archivo CSV por grupo con el formato:

**Ejemplo**: `MCI-2025B Instrumentación Electrónica.csv`

```csv
numero_cuenta,nombre,nombref2,email
12345,Carlos Alejandro Guadarrama Romero,"Guadarrama Romero, Carlos Alejandro",carlos@correo.com
67890,Citlali Irais Cano Del Razo,"Cano Del Razo, Citlali Irais",citlali@correo.com
```

Ejecuta:

```bash
python cargar_alumnos.py
```

Selecciona el archivo CSV del grupo que deseas cargar.

---

## 🎬 Uso del Sistema

### **FASE 1: Descargar Tareas y Grabar Retroalimentación**

```bash
python tareas.py
```

**Flujo**:
1. Selecciona el grupo
2. Elige "Descargar para calificar"
3. Selecciona la tarea específica
4. Elige modo: Individual o Equipos
5. El sistema descarga los PDFs y abre la carpeta
6. **Proceso de calificación secuencial**:
   - El sistema abre cada PDF automáticamente
   - Presiona ENTER para iniciar grabación de audio
   - Graba tus observaciones
   - Presiona ENTER nuevamente para detener
   - El audio se guarda como `Cal_<nombrearchivo>.mp3`
   - Continúa automáticamente con el siguiente archivo
7. Puedes escribir "pausar" para detener (tu progreso se guarda)
8. Puedes escribir "saltar" para omitir un archivo

**Resultado**: Carpeta con PDFs originales y archivos `Cal_*.mp3` con retroalimentación grabada.

**📁 Ubicación**: `D:\tareas\Calificar\<grupo>\<tarea>\`

---

### **FASE 2: Transcribir Audios con Whisper**

```bash
python transcribir_audios.py
```

**Qué hace**:
- Busca todos los archivos `Cal_*.mp3` en todas las carpetas
- Los transcribe usando Whisper (modelo medium, en español)
- Guarda transcripciones como `Cal_<nombrearchivo>_transcripcion.json`

**Ejemplo de transcripción**:
```json
{
  "alumno": "Carlos Alejandro Guadarrama Romero",
  "tarea": "1. Conectarse a una Raspberry desde cualquier",
  "audio_file": "Cal_1. Conectarse_Carlos.mp3",
  "transcripcion": "El trabajo está bien desarrollado pero le falta profundidad en la sección de configuración...",
  "duracion_segundos": 45.2,
  "idioma_detectado": "es",
  "tiempo_procesamiento": 12.3
}
```

**Tiempo estimado**: ~30 segundos por cada minuto de audio.

---

### **FASE 3: Calificar con Gemini y Subir a BD**

**IMPORTANTE**: Antes de ejecutar esta fase, debes **renombrar manualmente** los PDFs:

```
Original: 1. Conectarse_Carlos.pdf
Renombrar a: Cal_1. Conectarse_Carlos.pdf
```

Luego ejecuta:

```bash
python calificar_gemini.py
```

**Qué hace**:
1. Busca todos los PDFs originales (sin prefijo `Cal_`)
2. Para cada PDF:
   - Carga la rúbrica correspondiente
   - Busca la transcripción de audio (si existe)
   - Envía PDF + rúbrica + transcripción a Gemini 1.5 Flash
   - Gemini analiza TODO: texto, fórmulas, diagramas e imágenes
   - Recibe calificación en JSON estructurado
   - Genera página profesional de calificación con ReportLab
   - Fusiona la página de calificación con el PDF original
   - Guarda como `Cal_<nombrearchivo>.pdf`
   - Sube calificación a la base de datos MySQL

**Resultado**:
- PDFs calificados: `Cal_*.pdf` (página de calificación + PDF original)
- Calificaciones en la base de datos

**Ejemplo de página de calificación**:

```
┌────────────────────────────────────────────┐
│     CALIFICACIÓN AUTOMÁTICA                │
│                                            │
│ Alumno: Carlos Alejandro Guadarrama Romero│
│ Tarea: 1. Conectarse a una Raspberry      │
│ Fecha: 02/01/2026 14:30                   │
│                                            │
│   CALIFICACIÓN TOTAL: 8.5 / 10.0          │
│                                            │
├────────────────────────────────────────────┤
│ DESGLOSE POR CRITERIOS                    │
├────────────────────────────────────────────┤
│ • Configuración correcta: 2.5/3.0         │
│   Buena configuración pero faltó detalle  │
│                                            │
│ • Documentación clara: 3.0/3.0            │
│   Excelente documentación                 │
│                                            │
│ FORTALEZAS:                               │
│ • Capturas de pantalla muy claras         │
│ • Procedimiento bien estructurado         │
│                                            │
│ ÁREAS DE MEJORA:                          │
│ • Profundizar en configuración de red     │
└────────────────────────────────────────────┘
[PDF original del alumno]
```

---

### **REGRESAR CALIFICACIONES A ESTUDIANTES**

```bash
python tareas.py
```

1. Selecciona el grupo
2. Elige "Regresar TODAS las calificadas"
3. El sistema:
   - Busca TODOS los `Cal_*.pdf` en todas las tareas del grupo
   - Los copia automáticamente a las carpetas de OneDrive de cada estudiante
   - Copia también los archivos de audio (.mp3/.wav)
   - Muestra resumen de cuántas tareas fueron procesadas

---

## 📊 Estructura de la Base de Datos

### Tabla: `grupos`
- `id`, `nombre`, `semestre`, `anio`, `created_at`

### Tabla: `alumnos`
- `id`, `numero_cuenta`, `nombre`, `nombref2`, `grupo_id`, `team_id`, `email`, `created_at`

### Tabla: `tareas`
- `id`, `grupo_id`, `nombre`, `descripcion`, `fecha_limite`, `puntos_maximos`, `rubrica`, `created_at`

### Tabla: `calificaciones`
- `id`, `alumno_id`, `tarea_id`, `calificacion` (0.0-10.0), `ruta_pdf_calificado`, `ruta_audio`, `ruta_transcripcion`, `fecha_calificacion`

### Tabla: `asistencias`
- `id`, `alumno_id`, `grupo_id`, `fecha`, `presente`, `created_at`

---

## 📁 Estructura de Archivos

```
CalificarRubricas/
├── credentials.json              # Credenciales (¡NO SUBIR A GIT!)
├── rubricas.json                 # Configuración de rúbricas
├── tareas.py                     # Fase 1: Descarga y grabación
├── transcribir_audios.py         # Fase 2: Transcripción Whisper
├── calificar_gemini.py           # Fase 3: Calificación IA
├── db_setup.py                   # Setup de base de datos
├── cargar_alumnos.py             # Importar alumnos desde CSV
├── requirements.txt              # Dependencias Python
├── README.md                     # Este archivo
│
├── rubricas/                     # Archivos de rúbricas (.txt)
│   ├── raspberry_conexion.txt
│   └── otra_tarea.txt
│
└── <Grupo>.csv                   # CSVs de alumnos por grupo

D:\tareas\Calificar\              # Carpeta de trabajo
├── <Grupo>/
│   └── <Tarea>/
│       ├── <tarea>_<alumno>.pdf              # Original
│       ├── Cal_<tarea>_<alumno>.mp3          # Audio grabado
│       ├── Cal_<tarea>_<alumno>_transcripcion.json
│       ├── Cal_<tarea>_<alumno>.pdf          # PDF calificado
│       └── metadata.json
```

---

## ⚙️ Configuración Avanzada

### Cambiar Modelo de Whisper

En `transcribir_audios.py`, línea 23:

```python
WHISPER_MODEL = "medium"  # Opciones: tiny, base, small, medium, large
```

- **tiny**: Más rápido, menos preciso (~75 MB)
- **medium**: Balance óptimo (~1.5 GB) **← Recomendado**
- **large**: Más preciso, más lento (~3 GB)

### Cambiar Modelo de Gemini

En `credentials.json` puedes usar:
- `gemini-1.5-flash` (rápido, económico) **← Actual**
- `gemini-1.5-pro` (más preciso, más costoso)

---

## 🐛 Solución de Problemas

### Error: "No module named 'whisper'"
```bash
pip install openai-whisper
```

### Error: "ffmpeg not found"
- Instala ffmpeg y asegúrate de que esté en el PATH
- En Windows: `choco install ffmpeg`

### Error: "No se encontró alumno en BD"
- Asegúrate de que el nombre del alumno en el CSV coincida exactamente con el formato de tareas.py
- Columna `nombre`: "Carlos Alejandro Guadarrama Romero"

### Whisper muy lento
- Primera ejecución descarga el modelo (~1.5 GB)
- Si tienes GPU NVIDIA, instala CUDA para acelerar
- O usa modelo `small` en lugar de `medium`

### Gemini devuelve error 429 (Rate Limit)
- Has excedido el límite de requests
- Espera unos minutos
- Considera usar Gemini 1.5 Flash (más rápido y económico)

---

## 📝 Notas Importantes

1. **Seguridad**: NUNCA subas `credentials.json` a Git
2. **Respaldo**: Haz backup de la base de datos regularmente
3. **Costos**: Gemini tiene costos por API. Revisa tu consumo en Google Cloud Console
4. **Privacidad**: Los PDFs se envían a Gemini. Asegúrate de que los alumnos estén informados
5. **Nombres**: Los nombres de alumnos deben coincidir exactamente entre:
   - Sistema de tareas (OneDrive)
   - Base de datos (CSV)
   - PDFs descargados

---

## 🔄 Flujo Completo Paso a Paso

```
1. Configurar sistema
   └─> db_setup.py
   └─> cargar_alumnos.py (con CSV)
   └─> Crear archivos de rúbricas

2. Calificar tareas
   └─> tareas.py
       ├─ Descargar PDFs
       └─ Grabar retroalimentación (Cal_*.mp3)

3. Transcribir audios
   └─> transcribir_audios.py
       └─ Genera Cal_*_transcripcion.json

4. RENOMBRAR MANUALMENTE PDFs
   └─> archivo.pdf → Cal_archivo.pdf

5. Calificar con IA
   └─> calificar_gemini.py
       ├─ Analiza PDF + rúbrica + transcripción
       ├─ Genera Cal_*.pdf con calificación
       └─ Sube a base de datos

6. Devolver a estudiantes
   └─> tareas.py → "Regresar TODAS las calificadas"
```

---

## 👥 Soporte

Para problemas o dudas, contacta al administrador del sistema.

---

## 📄 Licencia

Este proyecto es de uso interno académico.

---

**Desarrollado por**: Javier Salas García
**Fecha**: Enero 2026
**Versión**: 1.0
