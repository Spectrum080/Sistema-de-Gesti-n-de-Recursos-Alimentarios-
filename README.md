<div align="center">

# Sistema de Gestión de Recursos Alimentarios (Hambre Cero)

<p align="center">
  <strong>Plataforma web desarrollada en Python y Django orientada a mitigar el desperdicio de alimentos en comercios y restaurantes, optimizando la gestión de inventarios, alertas de caducidad y la canalización de excedentes hacia organizaciones receptoras antes de su vencimiento.</strong>
</p>

<!-- Badges de Tecnologías principales -->
<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django" />
  <img src="https://img.shields.io/badge/HTML5%20%26%20CSS3-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5 y CSS3" />
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/Google%20Gemini-8E75C2?style=for-the-badge&logo=googlegemini&logoColor=white" alt="Google Gemini" />
</p>

</div>

---

## Descripción Académica

Proyecto Integrador desarrollado en la **Universidad del Valle de México** <img src="https://img.shields.io/badge/UVM-E31B23?style=flat-square" alt="UVM" /> — **Campus Reforma**, para la carrera de **Ingeniería en Sistemas Computacionales**, tercer semestre, en la materia de **Programación Orientada a Objetos**, impartida por el profesor **César Antonio Ríos Olivares**.

---

## Arquitectura y Principios de POO Aplicados

El sistema aplica **Herencia**, **Encapsulamiento** y **Polimorfismo** tanto en el backend de Django como en las plantillas HTML:

- **Herencia de Modelos (`users/models.py`)**:
  - `Usuario` hereda de `AbstractUser` y añade `telefono`, `direccion` y métodos encapsulados de consulta (`obtener_mis_donaciones`, `obtener_donaciones_para_receptor`, `obtener_mi_historial_receptor`).
  - `Donante(Usuario)` extiende `Usuario` con `nombre_local` y `tipo`.
  - `Receptor(Usuario)` extiende `Usuario` con `nombre_org` y `capacidad`.
  - `Administrador(Usuario)` extiende `Usuario` para supervisión general.
- **Herencia de Plantillas HTML**:
  - Todas las vistas autenticadas (`dashboardDonante`, `dashboardReceptor`, `perfil`, `configuracion`, `cargarDonaciones`, `consultarDonaciones`, `historialDonaciones`, `mis_notificaciones` y `responderDonacion`) heredan de `users/dashboard.html`.
  - Las vistas de acceso (`Sing_up`, `reset_password`, `reset_done`, `reset_confirm`, `reset_complete`) heredan de `users/login.html`.
  - Los modales de cambio de estado y comentarios se reutilizan mediante componentes parciales (`_modal_estado_donacion.html` y `_modal_comentarios_donacion.html`) compartidos entre **Consultar Donaciones** e **Historial de Donaciones**.
- **Encapsulamiento y Privacidad por Rol**:
  - **Donante**: solo visualiza y consulta sus propias donaciones (`Mis Donaciones` y detalle); no puede ver entregas de otros donantes ni acceder a vistas de receptor aunque manipule parámetros `?rol=` en la URL.
  - **Receptor**: en **Aceptar Donaciones** (`consultarDonaciones`) visualiza únicamente las donaciones **pendientes por atender** (incluyendo las creadas antes de su registro). Su **Historial de Donaciones** (`historialDonaciones`) es estrictamente privado y no se comparte entre receptores.

---

## Funcionalidades Implementadas

### 1. Autenticación, Roles y Menú de Cuenta
- Registro de usuarios eligiendo rol (**Donante** o **Receptor**), inicio de sesión, recuperación de contraseña y cierre de sesión seguro (`POST /users/logout/`).
- Menú desplegable en la esquina superior derecha (junto al nombre y avatar del usuario) con acceso a:
  - **Mi Perfil** (`/users/mi-perfil/`): edición de Razón Social / Organización, Teléfono y Dirección. Muestra aviso de validación únicamente mientras el perfil esté incompleto.
  - **Configuración** (`/users/configuracion/`): preferencias de accesibilidad persistidas en sesión.
  - **Soporte Técnico**: ventana modal funcional con correo, teléfono y horario de atención.
  - **Cerrar Sesión**: finaliza la sesión y redirige automáticamente al login.

### 2. Flujo del Donante
- **Panel Donante** (`/users/dashboardDonante/`): métricas privadas (total de donaciones, peso acumulado en KG, estatus), exportación de informes en **CSV** y **PDF**, y guía visual *"¿Cómo donar en 4 simples pasos?"*.
- **Validación previa de perfil**: antes de registrar una entrega, el sistema verifica que el donante tenga completos su Nombre/Razón Social, Teléfono y Dirección.
- **Formulario de Nueva Donación** (`/alertas/cargarDonaciones/`):
  - Prellenado automático con los datos del perfil.
  - Clasificación de alimento, cantidad, unidad, fecha de caducidad y requisito de conservación (detección automática de refrigeración).
  - Logística de entrega (quién entrega, fecha preferida, horario desde/hasta, indicaciones).
  - Evidencia fotográfica (almacenada en `ImageField` y respaldo Base64 para vista rápida).
  - Declaración obligatoria de responsabilidad e higiene.
- **Mis Donaciones** (`/alertas/consultarDonaciones/?rol=donante`): tabla paginada con filtro por categoría, acceso al detalle completo (`/alertas/donacion/<id>/`), modal de evidencia fotográfica y lectura de comentarios del receptor.

### 3. Flujo del Receptor
- **Panel Receptor** (`/users/dashboardReceptor/`): métricas del acopio pendiente y exportación de reportes en CSV/PDF.
- **Aceptar Donaciones** (`/alertas/consultarDonaciones/?rol=receptor`): bandeja de donaciones por atender con filtro por categoría, paginación, detalle completo, vista de evidencia, comentarios y modal de decisión (**Aceptar**, **Reservar**, **Rechazar** o **Quitar**).
- **Historial de Donaciones** (`/alertas/historialDonaciones/?rol=receptor`):
  - Registro privado del trabajo gestionado por el receptor.
  - **Corrección de errores**: integra la misma mini ventana modal de estado y comentarios que *Consultar Donaciones* para modificar decisiones equivocadas (**Aceptar**, **Reservar**, **Rechazar** o editar comentarios) actualizando automáticamente el estado y notificando al donante.
  - **Regresar a Consultar Donaciones**: permite devolver una donación al estado disponible (`Recibido`, sin receptor asignado) si hubo equivocación, reactivando el alimento en inventario y avisando al donante.

### 4. Sistema de Notificaciones y Alertas de Alto Riesgo
- **Campanita global** (inyectada vía `alertas.context_processors.notificaciones_globales`) con indicador de pendientes reales y vista rápida de las últimas 4 alertas.
- **Centro de Notificaciones** (`/alertas/mis-notificaciones/`): tabla completa filtrada por rol con marcado individual (`Marcar leída`) y masivo (`Marcar todas como leídas`).
- **Eventos notificados automáticamente**:
  - Registro de nueva donación (notifica al Donante y a todos los Receptores).
  - **Alertas de Alto Riesgo (`danger`)**: detección automática de donaciones vencidas o con caducidad `<= 3 días` (tanto al crear la donación como mediante sincronización sin duplicados).
  - Decisiones y correcciones del receptor (Aceptado, Reservado, Rechazado, Comentarios, Regresado a pendientes y Eliminación).

### 5. Accesibilidad y Personalización
- **Modo Oscuro** completo en todas las vistas, tablas, tarjetas y modales.
- **Bordes de Alto Contraste**.
- **Escala global de fuente** (`100%`, `108%`, `115%`).
- Activación/desactivación de **Alertas de Caducidad Inmediata**.

---

## Estructura del Proyecto

```text
Sistema-de-Gesti-n-de-Recursos-Alimentarios--main/
├── manage.py
├── db.sqlite3
├── README.md
├── proyectocomida/
│   ├── settings.py              # Configuración Django, AUTH_USER_MODEL, MEDIA y context processors
│   └── urls.py                  # Enrutamiento raíz y servicio de archivos media en DEBUG
├── core/                        # Aplicación base compartida
├── users/
│   ├── models.py                # Usuario, Donante, Receptor, Administrador y métodos encapsulados
│   ├── views.py                 # Dashboards, perfil, configuración, registro y exportación CSV/PDF
│   ├── urls.py                  # Rutas de autenticación, paneles, perfil y reportes
│   └── templates/users/         # login, Sing_up, reset_*, dashboard, dashboardDonante, dashboardReceptor, perfil, configuracion
└── alertas/
    ├── models.py                # CentroAcopio, CategoriaAlimento, Alimento, Nutrientes, Donacion, MovimientoInventario, Alerta, Notificacion
    ├── views.py                 # cargarDonaciones, consultarDonaciones, historialDonaciones, detalle_donacion, mis_notificaciones
    ├── context_processors.py    # Inyección global de notificaciones por rol
    ├── utils/notificaciones.py  # Generación de notificaciones y evaluación de alto riesgo por caducidad
    ├── migrations/              # Migraciones 0001 a 0004
    └── templates/alertas/       # cargarDonaciones, consultarDonaciones, historialDonaciones, responderDonacion, mis_notificaciones y parciales _modal_*
```

---

## Mapa de Rutas Principales

| Ruta | Descripción | Rol |
| :--- | :--- | :--- |
| `/users/login/` | Inicio de sesión | Público |
| `/users/Sing_up/` | Registro de cuenta (Donante / Receptor) | Público |
| `/users/logout/` | Cierre de sesión (`POST`) | Autenticado |
| `/users/dashboardDonante/` | Panel principal del Donante | Donante |
| `/users/dashboardReceptor/` | Panel principal del Receptor | Receptor |
| `/users/mi-perfil/` | Consulta y edición del perfil | Autenticado |
| `/users/configuracion/` | Modo oscuro, alto contraste, fuente y alertas | Autenticado |
| `/users/exportar-informe/` | Descarga de reporte en CSV o PDF | Autenticado |
| `/alertas/cargarDonaciones/` | Formulario para publicar una donación | Donante |
| `/alertas/consultarDonaciones/` | Mis Donaciones (Donante) / Por Atender (Receptor) | Autenticado |
| `/alertas/historialDonaciones/` | Historial privado con corrección y devolución | Receptor |
| `/alertas/donacion/<id>/` | Detalle completo de una donación | Autenticado (encapsulado) |
| `/alertas/mis-notificaciones/` | Centro de notificaciones y lectura | Autenticado |

---

## Tecnologías Utilizadas

| Categoría | Tecnología |
| :--- | :--- |
| **Lenguaje Core** | `Python 3.x` |
| **Framework Web** | `Django 5.x` |
| **Frontend** | `HTML5`, `CSS3` (modales y menús puros sin dependencias pesadas) |
| **Base de Datos** | `SQLite3` |
| **Procesamiento de Imágenes** | `Pillow` (`ImageField`) + Base64 |
| **Control de Versiones** | `Git` & `GitHub` |

---

## Instalación y Ejecución

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/Sistema-de-Gestion-de-Recursos-Alimentarios.git
cd Sistema-de-Gestion-de-Recursos-Alimentarios
```

### 2. Instalar dependencias
```bash
pip install django pillow
```

### 3. Aplicar migraciones
```bash
python manage.py migrate
```

### 4. Ejecutar el servidor local
```bash
python manage.py runserver
```
Abre en tu navegador: `http://127.0.0.1:8000/users/login/`

*(Opcional para pruebas desde celular en la misma red local: ejecuta `python manage.py runserver 0.0.0.0:8000` y agrega tu IP local a `ALLOWED_HOSTS` en `proyectocomida/settings.py`.)*

---

## Equipo de Desarrollo

Proyecto desarrollado en equipo, con los siguientes roles asignados:

<p align="left">
  <img src="https://img.shields.io/badge/Carlos-Developer%20Frontend-38B2AC?style=for-the-badge&logo=github&logoColor=white&labelColor=1A202C" alt="Carlos" />
  <img src="https://img.shields.io/badge/Santiago-Developer%20Full%20Stack-805AD5?style=for-the-badge&logo=github&logoColor=white&labelColor=1A202C" alt="Santiago" />
  <img src="https://img.shields.io/badge/Osvaldo-Developer-3182CE?style=for-the-badge&logo=github&logoColor=white&labelColor=1A202C" alt="Osvaldo" />
  <img src="https://img.shields.io/badge/Maximiliano-Developer-3182CE?style=for-the-badge&logo=github&logoColor=white&labelColor=1A202C" alt="Maximiliano" />
  <img src="https://img.shields.io/badge/Christian-Developer-3182CE?style=for-the-badge&logo=github&logoColor=white&labelColor=1A202C" alt="Christian" />
  <img src="https://img.shields.io/badge/Seth-Developer-3182CE?style=for-the-badge&logo=github&logoColor=white&labelColor=1A202C" alt="Seth" />
</p>
