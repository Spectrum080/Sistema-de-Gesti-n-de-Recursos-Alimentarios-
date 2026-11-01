from django.urls import path
from . import views

urlpatterns = [
    path('consultarDonaciones/', views.consultarDonaciones, name='consultarDonaciones'),
    path('historialDonaciones/', views.historialDonaciones, name='historialDonaciones'),
    path('cargarDonaciones/', views.cargarDonaciones, name='cargarDonaciones'),
    path('api/donaciones/', views.api_donaciones, name='apiDonaciones'),
    path('api/donaciones/<int:donacion_id>/estado/', views.actualizar_estado_donacion, name='actualizarEstadoDonacion'),
]
