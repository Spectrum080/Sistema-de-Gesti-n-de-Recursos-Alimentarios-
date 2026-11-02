from django.contrib.auth.models import AbstractUser
from django.db import models

# Modelo base de usuario extendido con datos de contacto y ubicación
class Usuario(AbstractUser):
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.CharField(max_length=255, blank=True)

# Perfil de usuario que aporta alimentos o bebidas al centro de acopio
class Donante(Usuario):
    nombre_local = models.CharField(max_length=150, blank=True)
    tipo = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = 'Donante'
        verbose_name_plural = 'Donantes'


# Perfil de organización o beneficiario que recibe y gestiona las donaciones
class Receptor(Usuario):
    nombre_org = models.CharField(max_length=150, blank=True)
    capacidad = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Receptor'
        verbose_name_plural = 'Receptores'


# Perfil con permisos administrativos globales sobre el sistema
class Administrador(Usuario):
    class Meta:
        verbose_name = 'Administrador'
        verbose_name_plural = 'Administradores'
