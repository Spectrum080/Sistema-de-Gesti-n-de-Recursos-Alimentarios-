from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.CharField(max_length=255, blank=True)

class Donante(Usuario):
    nombre_local = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20)


class Receptor(Usuario):
    nombre_org = models.CharField(max_length=150)
    capacidad = models.IntegerField(default=0)


class Administrador(Usuario):
    pass