from django.urls import path
from . import views

# Rutas principales del módulo de alertas y gestión de donaciones
urlpatterns = [
    path('consultarDonaciones/', views.consultarDonaciones, name='consultarDonaciones'),  # Consulta (Donante) y aceptación/rechazo (Receptor)
    path('historialDonaciones/', views.historialDonaciones, name='historialDonaciones'),  # Bitácora histórica de donaciones
    path('cargarDonaciones/', views.cargarDonaciones, name='cargarDonaciones'),           # Formulario para registrar una nueva donación
    path('donacion/<int:donacion_id>/', views.detalle_donacion, name='detalle_donacion'), # Vista de detalle completo de una donación
    path('mis-notificaciones/', views.mis_notificaciones, name='mis_notificaciones'),     # Vista de la tabla completa de notificaciones
]
