from django.urls import path
from . import views

urlpatterns = [
    path('consultarDonaciones/', views.consultarDonaciones, name='consultarDonaciones'),
    path('historialDonaciones/', views.historialDonaciones, name='historialDonaciones'),
    path('cargarDonaciones/', views.cargarDonaciones, name='cargarDonaciones'),
]
