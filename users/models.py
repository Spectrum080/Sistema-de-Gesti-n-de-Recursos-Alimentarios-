from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.CharField(max_length=255, blank=True)

class Donante(Usuario):
    nombre_local = models.CharField(max_length=150, blank=True)
    tipo = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = 'Donante'
        verbose_name_plural = 'Donantes'


class Receptor(Usuario):
    nombre_org = models.CharField(max_length=150, blank=True)
    capacidad = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Receptor'
        verbose_name_plural = 'Receptores'


class Administrador(Usuario):
    class Meta:
        verbose_name = 'Administrador'
        verbose_name_plural = 'Administradores'