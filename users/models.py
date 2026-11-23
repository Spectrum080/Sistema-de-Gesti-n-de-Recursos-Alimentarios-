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
        # Consulta las donaciones precargando sus relaciones para mayor rendimiento
        return Donacion.objects.select_related(
            'alimento', 'donante', 'receptor', 'centro_acopio'
        ).filter(
            # Coincide si el usuario autenticado es el autor directo de la donación
            models.Q(usuario_donante=self)
            # O si coincide con el perfil Donante vinculado a esta misma cuenta
            | models.Q(donante__pk=self.pk)
            # O para registros antiguos sin usuario/donante asignado cuyo nombre coincida con su username
            | models.Q(usuario_donante__isnull=True, donante__isnull=True, nombre_donante__iexact=self.username)
        # Ordena de la donación más reciente a la más antigua
        ).order_by('-id')

    # Método encapsulado que obtiene SOLAMENTE las donaciones por atender visibles para el receptor
    # Incluye donaciones registradas antes o después del alta del receptor mientras sigan pendientes
    def obtener_donaciones_para_receptor(self):
        # Importación local del modelo Donacion
        from alertas.models import Donacion
        # Consulta donaciones precargando sus relaciones clave
        return Donacion.objects.select_related(
            'alimento', 'donante', 'receptor', 'centro_acopio'
        ).filter(
            # Restringe únicamente a estados que aún están pendientes por atender
            estado__in=['Pendiente', 'Recibido', 'Activa'],
        ).filter(
            # Permite ver donaciones que todavía no han sido tomadas por ningún receptor
            models.Q(usuario_receptor__isnull=True, receptor__isnull=True)
            # O las que este mismo receptor comentó temporalmente sin cambiar aún su estado
            | models.Q(usuario_receptor=self)
            # O las asociadas a su instancia de Receptor mientras sigan pendientes
            | models.Q(receptor__pk=self.pk)
        # Ordena de la donación más reciente a la más antigua
        ).order_by('-id')

    # Método encapsulado que obtiene exclusivamente el historial privado de este usuario receptor
    def obtener_mi_historial_receptor(self):
        # Importación local del modelo Donacion
        from alertas.models import Donacion
        # Filtra únicamente las donaciones que fueron atendidas por esta cuenta de receptor
        return Donacion.objects.select_related(
            'alimento', 'donante', 'receptor', 'centro_acopio'
        ).filter(
            # Garantiza privacidad: solo registros donde este usuario es el receptor asignado
            models.Q(usuario_receptor=self) | models.Q(receptor__pk=self.pk),
            # Incluye únicamente estados ya gestionados (aceptados, reservados, rechazados, etc.)
            estado__in=['Aceptado', 'Rechazado', 'Reservado', 'Reservada', 'Entregada', 'Cancelada'],
        # Ordena de la más reciente a la más antigua
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
