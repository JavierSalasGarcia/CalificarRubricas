/**
 * Sistema de Calificaciones - JavaScript Principal
 * Estilo: Starlink Hi-Tech Minimalista
 */

// ===== AUTO-CERRAR MENSAJES FLASH =====
document.addEventListener('DOMContentLoaded', function() {
    // Auto-cerrar mensajes flash después de 5 segundos
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.opacity = '0';
            setTimeout(function() {
                message.remove();
            }, 300);
        }, 5000);
    });
});

// ===== ANIMACIÓN DE ENTRADA DE ELEMENTOS =====
function animateOnScroll() {
    const elements = document.querySelectorAll('.stat-card, .action-card, .section');

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, {
        threshold: 0.1
    });

    elements.forEach(function(element) {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        element.style.transition = 'all 0.5s ease-out';
        observer.observe(element);
    });
}

// Ejecutar animación al cargar
document.addEventListener('DOMContentLoaded', animateOnScroll);

// ===== EFECTO PARALLAX SUAVE EN EL FONDO =====
document.addEventListener('mousemove', function(e) {
    const stars1 = document.querySelector('.stars');
    const stars2 = document.querySelector('.stars2');
    const stars3 = document.querySelector('.stars3');

    if (stars1 && stars2 && stars3) {
        const moveX = (e.clientX - window.innerWidth / 2) * 0.01;
        const moveY = (e.clientY - window.innerHeight / 2) * 0.01;

        stars1.style.transform = `translate(${moveX}px, ${moveY}px)`;
        stars2.style.transform = `translate(${moveX * 1.5}px, ${moveY * 1.5}px)`;
        stars3.style.transform = `translate(${moveX * 2}px, ${moveY * 2}px)`;
    }
});

// ===== VALIDACIÓN DE FORMULARIOS =====
const forms = document.querySelectorAll('form');
forms.forEach(function(form) {
    form.addEventListener('submit', function(e) {
        const inputs = form.querySelectorAll('input[required]');
        let valid = true;

        inputs.forEach(function(input) {
            if (!input.value.trim()) {
                input.classList.add('invalid');
                valid = false;
            } else {
                input.classList.remove('invalid');
            }
        });

        if (!valid) {
            e.preventDefault();
        }
    });
});

// ===== EFECTOS DE HOVER MEJORADOS =====
document.addEventListener('DOMContentLoaded', function() {
    const cards = document.querySelectorAll('.stat-card, .action-card, .login-card');

    cards.forEach(function(card) {
        card.addEventListener('mouseenter', function() {
            this.style.boxShadow = '0 8px 32px rgba(0, 212, 255, 0.2)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.boxShadow = '';
        });
    });
});

// ===== COPIAR NÚMERO DE CUENTA (útil) =====
function copiarTexto(texto) {
    const tempInput = document.createElement('input');
    tempInput.value = texto;
    document.body.appendChild(tempInput);
    tempInput.select();
    document.execCommand('copy');
    document.body.removeChild(tempInput);

    // Mostrar notificación
    mostrarNotificacion('Copiado al portapapeles', 'success');
}

// ===== NOTIFICACIONES PERSONALIZADAS =====
function mostrarNotificacion(mensaje, tipo = 'info') {
    const container = document.querySelector('.flash-container') ||
                     createFlashContainer();

    const iconos = {
        'success': '✓',
        'danger': '✗',
        'warning': '⚠',
        'info': 'ℹ'
    };

    const notification = document.createElement('div');
    notification.className = `flash-message flash-${tipo}`;
    notification.innerHTML = `
        <span class="flash-icon">${iconos[tipo]}</span>
        <span class="flash-text">${mensaje}</span>
        <button class="flash-close" onclick="this.parentElement.remove()">&times;</button>
    `;

    container.appendChild(notification);

    // Auto-cerrar después de 3 segundos
    setTimeout(function() {
        notification.style.opacity = '0';
        setTimeout(function() {
            notification.remove();
        }, 300);
    }, 3000);
}

function createFlashContainer() {
    const container = document.createElement('div');
    container.className = 'flash-container';
    document.body.appendChild(container);
    return container;
}

// ===== PROGRESS BAR ANIMACIÓN =====
document.addEventListener('DOMContentLoaded', function() {
    const progressBars = document.querySelectorAll('.progress-bar');

    progressBars.forEach(function(bar) {
        const width = bar.style.width;
        bar.style.width = '0';

        setTimeout(function() {
            bar.style.width = width;
        }, 500);
    });
});

// ===== CARGAR CALIFICACIONES DE ALUMNO (ADMIN) =====
async function cargarCalificacionesAlumno(alumnoId) {
    try {
        const response = await fetch(`/api/calificaciones/${alumnoId}`);
        if (!response.ok) {
            throw new Error('Error al cargar calificaciones');
        }

        const calificaciones = await response.json();
        console.log('Calificaciones:', calificaciones);

        // Aquí podrías mostrar las calificaciones en un modal
        mostrarNotificacion('Calificaciones cargadas', 'success');

    } catch (error) {
        console.error(error);
        mostrarNotificacion('Error al cargar calificaciones', 'danger');
    }
}

// ===== CONFIRMAR ACCIÓN =====
function confirmarAccion(mensaje, callback) {
    if (confirm(mensaje)) {
        callback();
    }
}

// ===== EFECTO DE ESCRITURA (Typewriter) OPCIONAL =====
function typeWriter(elemento, texto, velocidad = 50) {
    let i = 0;
    elemento.innerHTML = '';

    function escribir() {
        if (i < texto.length) {
            elemento.innerHTML += texto.charAt(i);
            i++;
            setTimeout(escribir, velocidad);
        }
    }

    escribir();
}

// ===== SMOOTH SCROLL =====
document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));

        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// ===== ATAJOS DE TECLADO =====
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K para buscar (si hay barra de búsqueda)
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('input[type="search"]');
        if (searchInput) {
            searchInput.focus();
        }
    }

    // ESC para cerrar modales o flash messages
    if (e.key === 'Escape') {
        const flashMessages = document.querySelectorAll('.flash-message');
        flashMessages.forEach(function(msg) {
            msg.remove();
        });
    }
});

// ===== MARCAR TABLA COMO ORDENABLE (OPCIONAL) =====
function hacerTablaOrdenable(tabla) {
    const headers = tabla.querySelectorAll('th');

    headers.forEach(function(header, index) {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            const tbody = tabla.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));

            const sortedRows = rows.sort(function(a, b) {
                const aValue = a.cells[index].textContent.trim();
                const bValue = b.cells[index].textContent.trim();

                // Intentar comparar como números
                const aNum = parseFloat(aValue);
                const bNum = parseFloat(bValue);

                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return aNum - bNum;
                }

                // Comparar como texto
                return aValue.localeCompare(bValue);
            });

            // Limpiar tbody
            tbody.innerHTML = '';

            // Agregar filas ordenadas
            sortedRows.forEach(function(row) {
                tbody.appendChild(row);
            });
        });
    });
}

// Aplicar a tablas con clase 'sortable'
document.addEventListener('DOMContentLoaded', function() {
    const tablasOrdenables = document.querySelectorAll('.data-table.sortable');
    tablasOrdenables.forEach(hacerTablaOrdenable);
});

// ===== DARK MODE TOGGLE (ya está oscuro por defecto) =====
// Si quieres agregar modo claro como opción:
function toggleDarkMode() {
    document.body.classList.toggle('light-mode');
    const isDark = !document.body.classList.contains('light-mode');
    localStorage.setItem('darkMode', isDark);
}

// Cargar preferencia guardada
document.addEventListener('DOMContentLoaded', function() {
    const darkMode = localStorage.getItem('darkMode');
    if (darkMode === 'false') {
        document.body.classList.add('light-mode');
    }
});

// ===== UTILIDADES DE FECHA Y HORA =====
function formatearFecha(fecha) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(fecha).toLocaleDateString('es-MX', options);
}

function formatearHora(fecha) {
    const options = { hour: '2-digit', minute: '2-digit' };
    return new Date(fecha).toLocaleTimeString('es-MX', options);
}

// ===== LOG DE ACTIVIDAD (DEBUGGING) =====
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    console.log('%c🚀 Sistema de Calificaciones', 'color: #00d4ff; font-size: 20px; font-weight: bold;');
    console.log('%cModo de desarrollo activado', 'color: #ffa500; font-size: 12px;');
}

// ===== EXPORTAR FUNCIONES GLOBALES =====
window.CalificacionesApp = {
    copiarTexto,
    mostrarNotificacion,
    cargarCalificacionesAlumno,
    confirmarAccion,
    typeWriter,
    formatearFecha,
    formatearHora
};
