# 🌐 Sitio Web - Sistema de Calificaciones

Plataforma web con diseño **Starlink Hi-Tech Minimalista Oscuro** para visualizar calificaciones académicas.

## 🎨 Características de Diseño

- **Estilo oscuro profesional** inspirado en Starlink
- **Fondo animado** con efecto de estrellas
- **Interfaz hi-tech** con acentos en cyan (#00d4ff)
- **Responsive** adaptable a móviles y tablets
- **Animaciones suaves** y transiciones fluidas
- **Componentes modulares** con cards glassmorphism

---

## 🚀 Instalación Rápida

```bash
cd sitioweb
pip install -r requirements.txt
python app.py
```

Accede en: **http://localhost:5000**

---

## 📁 Estructura del Proyecto

```
sitioweb/
├── app.py                      # Servidor Flask principal
├── requirements.txt            # Dependencias Python
├── README.md                   # Este archivo
│
├── templates/                  # Plantillas HTML (Jinja2)
│   ├── base.html              # Plantilla base
│   ├── login.html             # Página de login
│   ├── dashboard_alumno.html  # Dashboard estudiantes
│   ├── dashboard_admin.html   # Dashboard administradores
│   └── cambiar_password.html  # Cambio de contraseña
│
└── static/                     # Archivos estáticos
    ├── css/
    │   └── style.css          # Estilos globales
    ├── js/
    │   └── main.js            # JavaScript principal
    └── img/                   # Imágenes (opcional)
```

---

## 👤 Usuarios y Roles

### **Sistema Multi-Usuario**

El sistema soporta tres tipos de usuarios con autenticación unificada:

### **Alumnos**
- **Usuario**: Número de cuenta
- **Contraseña inicial**: Número de cuenta (debe cambiarla en el primer login)
- **Tabla**: `alumnos`
- **Permisos**:
  - Ver sus propias calificaciones de TODOS los grupos en los que están inscritos
  - Ver promedio general
  - Descargar PDFs calificados
  - Escuchar retroalimentación en audio
  - Cambiar contraseña
- **Características**:
  - Un alumno puede estar en múltiples grupos simultáneamente
  - Las calificaciones se organizan por grupo

### **Profesores**
- **Usuario**: Número de empleado
- **Contraseña inicial**: Número de empleado (debe cambiarla en el primer login)
- **Tabla**: `profesores` (rol='profesor')
- **Permisos**:
  - Ver todos los grupos que imparten
  - Ver estadísticas de sus grupos (estudiantes, tareas)
  - Ver calificaciones recientes de sus grupos
  - Cambiar contraseña
- **Características**:
  - Un profesor puede impartir múltiples grupos
  - Cada grupo está asignado a un solo profesor
  - Dashboard especializado con información de sus grupos

### **Administradores**
- **Usuario**: Número de empleado
- **Contraseña inicial**: Número de empleado (debe cambiarla en el primer login)
- **Tabla**: `profesores` (rol='admin')
- **Permisos adicionales**:
  - Ver estadísticas generales del sistema completo
  - Ver todas las calificaciones de todos los alumnos
  - Acceso a panel administrativo
  - Acciones rápidas para ejecutar scripts (cargar alumnos/profesores, transcribir, calificar)
  - API endpoints para consultas
- **Características**:
  - Son profesores con privilegios administrativos
  - Pueden ver información de todos los grupos, no solo los suyos

---

## 🔐 Seguridad

⚠️ **IMPORTANTE**: Este sistema almacena contraseñas en **texto plano** para pruebas iniciales.

**Para producción**, implementa:
- Hashing de contraseñas con `bcrypt` o `argon2`
- HTTPS con certificado SSL
- Sesiones seguras con `SECRET_KEY` fuerte
- Rate limiting para prevenir ataques de fuerza bruta
- CSRF protection (Flask-WTF)

---

## 📊 Arquitectura de Base de Datos

### Soporte Multi-Usuario

El sitio web está diseñado para trabajar con la nueva arquitectura de base de datos que soporta:

**Múltiples Profesores:**
- Cada profesor puede impartir múltiples grupos
- Los profesores tienen su propia tabla con autenticación
- Pueden tener rol de `profesor` o `admin`

**Múltiples Grupos por Alumno:**
- Los alumnos pueden estar inscritos en varios grupos simultáneamente
- Relación muchos-a-muchos mediante tabla `alumnos_grupos`
- Las calificaciones se organizan por grupo en el dashboard

**Tablas Principales:**
- `profesores`: Contiene profesores y administradores
- `alumnos`: Contiene estudiantes
- `grupos`: Grupos con referencia a su profesor (`profesor_id`)
- `alumnos_grupos`: Relación muchos-a-muchos (alumno ↔ grupo)
- `calificaciones`: Calificaciones vinculadas a alumnos y tareas
- `tareas`: Tareas vinculadas a grupos

---

## 🛠️ Configuración

### 1. Configurar Secret Key

Edita `app.py` línea 17:

```python
app.secret_key = 'CAMBIAR_POR_CLAVE_SUPER_SEGURA_RANDOM'
```

Genera una clave segura:

```python
import secrets
print(secrets.token_hex(32))
```

### 2. Base de Datos

El sitio web usa las mismas credenciales que el sistema principal:

```
../credentials.json
```

Asegúrate de que la base de datos esté configurada (ejecuta `db_setup.py` primero).

### 3. Variables de Entorno (Opcional)

Crea un archivo `.env`:

```env
FLASK_SECRET_KEY=tu_clave_secreta
FLASK_ENV=development
FLASK_DEBUG=True
```

---

## 🖥️ Rutas Disponibles

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/` | GET | Redirige a login o dashboard | - |
| `/login` | GET, POST | Página de inicio de sesión unificada | - |
| `/logout` | GET | Cerrar sesión | ✓ |
| `/dashboard` | GET | Dashboard (redirige según tipo_usuario) | ✓ |
| `/dashboard/alumno` | GET | Dashboard de estudiante | ✓ Alumno |
| `/dashboard/profesor` | GET | Dashboard de profesor | ✓ Profesor |
| `/dashboard/admin` | GET | Dashboard de administrador | ✓ Admin |
| `/cambiar-password` | GET, POST | Cambiar contraseña | ✓ |
| `/api/calificaciones/<id>` | GET | API calificaciones de alumno | ✓ Admin |

**Autenticación Unificada:**
- El login detecta automáticamente el tipo de usuario (alumno/profesor/admin)
- Busca primero en la tabla `alumnos`, luego en `profesores`
- Redirige al dashboard correspondiente según el tipo de usuario

---

## 🎨 Paleta de Colores

```css
/* Fondos */
--bg-primary:     #0a0e27  /* Oscuro profundo */
--bg-secondary:   #111633  /* Oscuro medio */
--bg-card:        #1a1f3a  /* Cards */

/* Acentos */
--accent-primary:   #00d4ff  /* Cyan brillante */
--accent-secondary: #0099ff  /* Azul */
--accent-tertiary:  #4d6cff  /* Azul-morado */

/* Textos */
--text-primary:   #ffffff
--text-secondary: #a0aec0
--text-muted:     #718096
```

---

## 📱 Responsive Design

El diseño se adapta automáticamente a:
- **Desktop**: 1920px y superiores
- **Laptop**: 1366px - 1919px
- **Tablet**: 768px - 1365px
- **Móvil**: 320px - 767px

---

## 🔧 Desarrollo

### Modo Debug

```bash
export FLASK_ENV=development  # Linux/Mac
set FLASK_ENV=development     # Windows CMD
$env:FLASK_ENV="development"  # Windows PowerShell

python app.py
```

### Hot Reload

Flask recarga automáticamente al detectar cambios en:
- `app.py`
- Templates (`.html`)
- Archivos estáticos (`.css`, `.js`)

---

## 🚀 Despliegue en Producción

### Opción 1: Gunicorn (Linux/Mac)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Opción 2: Waitress (Windows)

```bash
pip install waitress
waitress-serve --host=0.0.0.0 --port=5000 app:app
```

### Opción 3: Docker

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

---

## 🐛 Solución de Problemas

### Error: "No se encontró credentials.json"
```bash
# Verifica que credentials.json exista en el directorio padre
ls ../credentials.json
```

### Error: "Connection refused" a MySQL
```bash
# Verifica que MySQL esté corriendo
# Windows:
net start MySQL80

# Linux:
sudo systemctl start mysql
```

### Error: "Port 5000 already in use"
```bash
# Cambiar puerto en app.py línea final:
app.run(debug=True, host='0.0.0.0', port=8000)
```

### Estilos no se cargan
```bash
# Ctrl+F5 para limpiar caché del navegador
# O verifica la ruta en templates:
{{ url_for('static', filename='css/style.css') }}
```

---

## 📝 Personalización

### Cambiar Colores

Edita `static/css/style.css` líneas 7-24 (variables CSS):

```css
:root {
    --accent-primary: #ff00ff;  /* Tu color personalizado */
}
```

### Agregar Nueva Página

1. Crear template en `templates/nueva_pagina.html`
2. Agregar ruta en `app.py`:

```python
@app.route('/nueva-pagina')
@login_required
def nueva_pagina():
    return render_template('nueva_pagina.html')
```

### Agregar Logo

1. Guardar logo en `static/img/logo.png`
2. Agregar en `base.html`:

```html
<img src="{{ url_for('static', filename='img/logo.png') }}" alt="Logo">
```

---

## 🤝 Contribuir

Este sitio web es parte del **Sistema de Calificación Automática**.

Para contribuir:
1. Mantén el estilo Starlink consistente
2. Prueba en múltiples navegadores
3. Verifica responsive design
4. Documenta cambios importantes

---

## 📄 Licencia

Uso interno académico.

---

**Desarrollado por**: Javier Salas García
**Fecha**: Enero 2026
**Versión**: 1.0
