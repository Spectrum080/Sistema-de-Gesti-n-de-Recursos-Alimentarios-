# Importa el modelo de usuario abstracto de Django para extenderlo
from django.contrib.auth.models import AbstractUser
# Importa el módulo de modelos y consultas Q de Django ORM
from django.db import models


# Define la clase base Usuario que hereda de AbstractUser
class Usuario(AbstractUser):
    # Campo de texto opcional para guardar el teléfono del usuario
    telefono = models.CharField(max_length=20, blank=True)
    # Campo de texto opcional para guardar la dirección física del usuario
    direccion = models.CharField(max_length=255, blank=True)

    # Método encapsulado que obtiene únicamente las entregas realizadas por este usuario donante
    def obtener_mis_donaciones(self):
        # Importación local del modelo Donacion para evitar dependencias circulares
        from alertas.models import Donacion
        # Filtra las donaciones donde el usuario sea el autor directo o coincida su perfil de donante
        return Donacion.objects.select_related(
            'alimento', 'donante', 'receptor', 'centro_acopio'
        ).filter(
            models.Q(usuario_donante=self)
            | models.Q(donante__pk=self.pk)
            | models.Q(usuario_donante__isnull=True, nombre_donante__iexact=self.username)
        ).order_by('-id')

    # Método encapsulado que obtiene todas las donaciones visibles para análisis del receptor
    def obtener_donaciones_para_receptor(self):
        # Importación local del modelo Donacion
        from alertas.models import Donacion
        # Retorna donaciones sin asignar o las que han sido gestionadas por este mismo receptor
        return Donacion.objects.select_related(
            'alimento', 'donante', 'receptor', 'centro_acopio'
        ).filter(
            models.Q(usuario_receptor__isnull=True, receptor__isnull=True)
            | models.Q(usuario_receptor=self)
            | models.Q(receptor__pk=self.pk)
        ).order_by('-id')

    # Método encapsulado que obtiene exclusivamente el historial de este usuario receptor
    def obtener_mi_historial_receptor(self):
        # Importación local del modelo Donacion
        from alertas.models import Donacion
        # Filtra solo las donaciones aceptadas, rechazadas o reservadas por esta cuenta de receptor
        return Donacion.objects.select_related(
            'alimento', 'donante', 'receptor', 'centro_acopio'
        ).filter(
            models.Q(usuario_receptor=self) | models.Q(receptor__pk=self.pk),
            estado__in=['Aceptado', 'Rechazado', 'Reservado'],
        ).order_by('-id')


# Define la subclase Donante que hereda todos los atributos y métodos de Usuario
class Donante(Usuario):
    # Campo opcional para almacenar el nombre del comercio o establecimiento donador
    nombre_local = models.CharField(max_length=150, blank=True)
    # Campo opcional para clasificar el giro o tipo de donador
    tipo = models.CharField(max_length=20, blank=True)

    # Configuración de metadatos para mostrar nombres legibles en el panel admin
    class Meta:
        # Nombre en singular dentro del administrador
        verbose_name = 'Donante'
        # Nombre en plural dentro del administrador
        verbose_name_plural = 'Donantes'


# Define la subclase Receptor que hereda de Usuario para organizaciones beneficiarias
class Receptor(Usuario):
    # Campo opcional con el nombre de la organización receptora
    nombre_org = models.CharField(max_length=150, blank=True)
    # Campo entero con la capacidad de atención de personas del receptor
    capacidad = models.IntegerField(default=0)

    # Configuración de metadatos para el panel de administración
    class Meta:
        # Nombre en singular para Receptor
        verbose_name = 'Receptor'
        # Nombre en plural para Receptores
        verbose_name_plural = 'Receptores'


# Define la subclase Administrador con privilegios de supervisión del sistema
class Administrador(Usuario):
    # Configuración de metadatos para el administrador
    class Meta:
        # Nombre en singular para Administrador
        verbose_name = 'Administrador'
        # Nombre en plural para Administradores
        verbose_name_plural = 'Administradores'
