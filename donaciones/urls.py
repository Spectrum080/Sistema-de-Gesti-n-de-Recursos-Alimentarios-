from django.urls import path
from . import views

urlpatterns = [
    path('subir/', views.subir_donacion, name='subir_donacion'),
]