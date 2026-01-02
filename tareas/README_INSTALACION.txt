INSTRUCCIONES DE INSTALACIÓN - Sistema de Calificación con Audio
================================================================

Para usar la funcionalidad de grabación de audio, necesitas instalar las siguientes dependencias:

1. DEPENDENCIAS DE PYTHON:
   -----------------------
   Ejecuta el siguiente comando en tu terminal/PowerShell:

   pip install sounddevice numpy

   Esto instalará:
   - sounddevice: Para grabar audio desde el micrófono
   - numpy: Para procesar los datos de audio


2. FFMPEG (Para convertir WAV a MP3):
   ----------------------------------

   Opción A - Usando Chocolatey (recomendado):

   1. Abre PowerShell como Administrador
   2. Instala Chocolatey si no lo tienes:
      Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
   3. Instala ffmpeg:
      choco install ffmpeg

   Opción B - Descarga manual:

   1. Descarga ffmpeg desde: https://ffmpeg.org/download.html
   2. Extrae el archivo ZIP a una carpeta (ej. C:\ffmpeg)
   3. Agrega la carpeta bin de ffmpeg al PATH del sistema:
      - Abre "Variables de entorno" desde el Panel de Control
      - Edita la variable "Path"
      - Agrega la ruta (ej. C:\ffmpeg\bin)
      - Reinicia la terminal


3. VERIFICAR INSTALACIÓN:
   ----------------------

   Ejecuta estos comandos para verificar:

   python -c "import sounddevice; print('sounddevice OK')"
   python -c "import numpy; print('numpy OK')"
   ffmpeg -version


4. USO DEL SISTEMA:
   ---------------

   Una vez instalado todo, ejecuta:

   python tareas.py

   CONFIGURACIÓN INICIAL DEL MICRÓFONO:
   -----------------------------------
   Al iniciar el programa por primera vez:

   1. El sistema te preguntará si deseas configurar el micrófono
   2. Verás una lista de todos los micrófonos disponibles
   3. Selecciona el micrófono que deseas usar
   4. Opcionalmente, puedes hacer una prueba de grabación de 3 segundos
   5. El sistema reproducirá la grabación para que verifiques la calidad
   6. Si estás satisfecho, confirma y el micrófono quedará configurado
   7. Si no, puedes seleccionar otro micrófono y repetir la prueba

   FLUJO DEL SISTEMA:
   -----------------
   El sistema te guiará paso a paso:

   1. Selecciona grupo
   2. Elige acción: "Descargar para calificar", "Regresar TODAS las calificadas" o "Configurar micrófono"

   OPCIÓN A - DESCARGAR PARA CALIFICAR:
   -------------------------------------
   3. Selecciona tarea específica
   4. Elige modo (Equipos o Individual)
   5. Se descarga y abre la carpeta automáticamente
   6. Se te preguntará si deseas iniciar el proceso de calificación
   7. PROCESO SECUENCIAL AUTOMÁTICO:
      - El sistema procesará TODOS los archivos uno por uno
      - Para cada archivo:
        * Se abrirá el PDF automáticamente
        * Presiona ENTER cuando estés listo para grabar
        * Presiona ENTER nuevamente para DETENER la grabación
        * El audio se guardará como Cal_<nombrearchivo>.mp3
        * El sistema continuará automáticamente con el siguiente archivo

   OPCIÓN B - REGRESAR TODAS LAS CALIFICADAS:
   -------------------------------------------
   3. El sistema busca TODOS los archivos Cal_*.pdf en TODAS las tareas del grupo
   4. Los copia automáticamente a las carpetas de OneDrive de los estudiantes
   5. Junto con los PDFs, copia los archivos de audio MP3/WAV correspondientes
   6. Muestra un resumen de cuántas tareas y archivos fueron procesados

   OPCIONES ADICIONALES:
   ---------------------
   - RECONFIGURAR MICRÓFONO:
     * En cualquier momento puedes elegir "Configurar micrófono" del menú
     * Esto te permite cambiar de micrófono o hacer nuevas pruebas

   - OPCIONES DURANTE LA CALIFICACIÓN:
     * Escribe "pausar" para detener el proceso (tu progreso se guarda)
     * Escribe "saltar" para omitir un archivo sin grabar
     * Si un archivo ya tiene audio, puedes elegir mantenerlo o regrabarlo

   - REANUDAR CALIFICACIÓN:
     * Si pausaste, ejecuta el programa nuevamente
     * El sistema detectará tu progreso y preguntará si deseas continuar
     * Continuará desde donde te quedaste


NOTAS IMPORTANTES:
-----------------
- ✅ MODO SECUENCIAL: El proceso continúa automáticamente hasta completar TODOS los archivos
- ✅ SISTEMA DE PROGRESO: Tu avance se guarda en .grading_progress.json
- ✅ REANUDAR EN CUALQUIER MOMENTO: Puedes pausar y continuar después
- ✅ CONTADOR DE PROGRESO: Verás cuántos archivos has completado (ej: 5/15)
- ✅ DETECCIÓN AUTOMÁTICA: Si un archivo ya tiene audio, te pregunta si deseas regrabarlo
- ✅ ENVÍO MASIVO: "Regresar TODAS las calificadas" procesa automáticamente TODAS las tareas del grupo
- ✅ Los archivos de audio se copian automáticamente junto con los PDFs
- ⚠️  IMPORTANTE: Debes renombrar los PDFs con prefijo "Cal_" (igual que los audios)
- ⚠️  Si no instalas ffmpeg, los archivos de audio se guardarán como WAV en lugar de MP3
- ⚠️  El sistema detectará automáticamente si las dependencias están instaladas


EJEMPLO DE FLUJO COMPLETO:
--------------------------
PASO 1 - DESCARGAR Y CALIFICAR:
1. Ejecutas: python tareas.py
2. Seleccionas grupo: "Grupo A"
3. Seleccionas acción: "Descargar para calificar"
4. Seleccionas tarea: "1. Conectarse a una Raspberry"
5. Eliges modo: "Individual"
6. Se descargan 15 archivos → "Archivo 1/15"
7. Se abre el PDF, presionas ENTER para grabar
8. Grabas tu retroalimentación, presionas ENTER para detener
9. Automáticamente → "Archivo 2/15" (continúa solo)
10. Si necesitas pausar, escribes "pausar"

PASO 2 - RENOMBRAR PDFs:
11. Vas a D:\tareas\Calificar\Grupo A\1. Conectarse a una Raspberry\
12. IMPORTANTE: Renombras los PDFs agregando prefijo "Cal_"
    Ejemplo: "1. Conectarse_Juan_Perez.pdf" → "Cal_1. Conectarse_Juan_Perez.pdf"
    (Los archivos de audio ya tienen el prefijo "Cal_" automáticamente)

PASO 3 - REGRESAR CALIFICADOS:
13. Ejecutas nuevamente: python tareas.py
14. Seleccionas grupo: "Grupo A"
15. Seleccionas acción: "Regresar TODAS las calificadas"
16. El sistema busca TODOS los Cal_*.pdf en todas las tareas de Grupo A
17. Los copia junto con los audios a OneDrive
18. Muestra resumen: "1. Conectarse a una Raspberry: 15 archivos"
19. ¡Listo! Las tareas ahora aparecen como calificadas en el menú
