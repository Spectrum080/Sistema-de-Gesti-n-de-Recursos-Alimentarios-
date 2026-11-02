from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Donacion(models.Model):
    TIPO_CHOICES = [
        ('PERECEDERO', 'Perecedero'),
        ('NO_PERECEDERO', 'No Perecedero'),
    ]

    donante = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    cantidad = models.CharField(max_length=100)
    fecha_caducidad = models.DateField()
    descripcion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo