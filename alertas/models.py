# Importa timedelta para cálculos de fechas próximas a vencer
from datetime import timedelta
# Importa el módulo de modelos de Django ORM
from django.db import models
# Importa utilidades de zona horaria de Django
from django.utils import timezone
# Importa los modelos de usuarios y roles del sistema
from users.models import Usuario, Donante, Receptor
# Importa la configuración del proyecto (incluye AUTH_USER_MODEL)
from django.conf import settings
# Importación local para notificar a donante y receptor sin ciclos de importación
from alertas.utils.notificaciones import notificar_decision_receptor
# Importación local para alertar al donante antes de borrar la donación
from alertas.utils.notificaciones import notificar_donacion_eliminada

# Define el QuerySet personalizado para encapsular los filtros de alimentos en acopio
class AlimentoQuerySet(models.QuerySet):
    # Filtra los alimentos que están disponibles y con cantidad mayor a cero
    def disponibles(self):
        # Retorna los registros con estado DISPONIBLE y stock positivo
        return self.filter(estado='DISPONIBLE', cantidad__gt=0)

    # Filtra únicamente los alimentos perecederos
    def perecederos(self):
        # Retorna alimentos cuyo tipo sea PERECEDERO
        return self.filter(tipo='PERECEDERO')

    # Filtra únicamente los alimentos no perecederos
    def no_perecederos(self):
        # Retorna alimentos cuyo tipo sea NO_PERECEDERO
        return self.filter(tipo='NO_PERECEDERO')

    # Filtra los registros correspondientes a agua embotellada y bebidas
    def aguas_embotelladas(self):
        # Retorna alimentos con clasificación AGUA_EMBOTELLADA
        return self.filter(clasificacion='AGUA_EMBOTELLADA')

    # Filtra los registros correspondientes a comida enlatada y conservas
    def comida_enlatada(self):
        # Retorna alimentos con clasificación COMIDA_ENLATADA
        return self.filter(clasificacion='COMIDA_ENLATADA')

    # Filtra los registros de granos, semillas y abarrotes
    def granos_y_abarrotes(self):
        # Retorna alimentos con clasificación GRANOS_ABARROTES
        return self.filter(clasificacion='GRANOS_ABARROTES')

    # Filtra los registros de comida preparada lista para consumo
    def comida_preparada(self):
        # Retorna alimentos con clasificación COMIDA_PREPARADA
        return self.filter(clasificacion='COMIDA_PREPARADA')

    # Filtra los alimentos que necesitan cadena de frío
    def requieren_refrigeracion(self):
        # Retorna alimentos donde requiere_refrigeracion es verdadero
        return self.filter(requiere_refrigeracion=True)

    # Filtra los alimentos que caducan dentro del número de días indicado
    def proximos_a_caducar(self, dias=7):
        # Obtiene la fecha actual del servidor
        hoy = timezone.now().date()
        # Calcula la fecha límite sumando los días especificados
        limite = hoy + timedelta(days=dias)
        # Retorna los alimentos cuya caducidad está entre hoy y la fecha límite
        return self.filter(
            fecha_caducidad__isnull=False,
            fecha_caducidad__gte=hoy,
            fecha_caducidad__lte=limite,
        )

    # Filtra los alimentos cuya fecha de caducidad ya venció
    def caducados(self):
        # Obtiene la fecha actual
        hoy = timezone.now().date()
        # Retorna alimentos con fecha de caducidad anterior a hoy
        return self.filter(
            fecha_caducidad__isnull=False,
            fecha_caducidad__lt=hoy,
        )

    # Método general para aplicar múltiples criterios de filtrado combinados
    def filtrar(
        self,
        clasificacion=None,
        tipo=None,
        tipo_envase=None,
        estado=None,
        categoria_id=None,
        centro_acopio_id=None,
        requiere_refrigeracion=None,
        busqueda=None,
    ):
        # Inicia con el conjunto de consulta actual
        qs = self
        # Si se especifica clasificación, filtra por ese campo
        if clasificacion:
            qs = qs.filter(clasificacion=clasificacion)
        # Si se especifica tipo, filtra por perecedero/no perecedero/etc.
        if tipo:
            qs = qs.filter(tipo=tipo)
        # Si se especifica envase, filtra por tipo de empaque
        if tipo_envase:
            qs = qs.filter(tipo_envase=tipo_envase)
        # Si se especifica estado, filtra por disponibilidad actual
        if estado:
            qs = qs.filter(estado=estado)
        # Si se indica categoría por ID, filtra por llave foránea
        if categoria_id:
            qs = qs.filter(categoria_id=categoria_id)
        # Si se indica centro de acopio, filtra por sede
        if centro_acopio_id:
            qs = qs.filter(centro_acopio_id=centro_acopio_id)
        # Si se indica refrigeración booleana, aplica el filtro
        if requiere_refrigeracion is not None:
            qs = qs.filter(requiere_refrigeracion=requiere_refrigeracion)
        # Si hay texto de búsqueda, busca coincidencias en nombre, marca, descripción o lote
        if busqueda:
            qs = qs.filter(
                models.Q(nombre__icontains=busqueda)
                | models.Q(marca__icontains=busqueda)
                | models.Q(descripcion__icontains=busqueda)
                | models.Q(codigo_lote__icontains=busqueda)
            )
        # Devuelve el QuerySet resultante
        return qs


# Modelo que representa la sede física del centro de acopio
class CentroAcopio(models.Model):
    # Nombre identificador del centro de acopio
    nombre = models.CharField(max_length=150)
    # Dirección física donde se reciben las donaciones
    direccion = models.CharField(max_length=255)
    # Teléfono de contacto de la sede
    telefono = models.CharField(max_length=20, blank=True)
    # Capacidad máxima de almacenamiento medida en kilogramos
    capacidad_maxima_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # Indica si el centro cuenta con cámaras de refrigeración
    tiene_refrigeracion = models.BooleanField(default=True)
    # Usuario encargado de administrar la sede de acopio
    responsable = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='centros_acopio',
    )
    # Estado operativo del centro de acopio
    activo = models.BooleanField(default=True)
    # Fecha y hora en que se dio de alta la sede
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # Configuración de metadatos del modelo CentroAcopio
    class Meta:
        # Nombre legible en singular
        verbose_name = 'Centro de Acopio'
        # Nombre legible en plural
        verbose_name_plural = 'Centros de Acopio'
        # Ordenamiento alfabético por nombre
        ordering = ['nombre']

    # Representación en texto del centro de acopio
    def __str__(self):
        # Retorna el nombre de la sede
        return self.nombre


# Catálogo de categorías para clasificar los insumos recibidos
class CategoriaAlimento(models.Model):
    # Nombre descriptivo de la categoría
    nombre = models.CharField(max_length=100, unique=True)
    # Clave interna única para relacionar con el filtro superior
    clave = models.CharField(max_length=50, unique=True)
    # Descripción detallada de los alimentos que incluye
    descripcion = models.TextField(blank=True)
    # Define si por defecto la categoría corresponde a perecederos
    es_perecedero_default = models.BooleanField(default=False)
    # Define si por defecto requiere refrigeración
    requiere_refrigeracion_default = models.BooleanField(default=False)

    # Metadatos del catálogo de categorías
    class Meta:
        # Nombre en singular
        verbose_name = 'Categoría de Alimento'
        # Nombre en plural
        verbose_name_plural = 'Categorías de Alimentos'
        # Ordenado por nombre
        ordering = ['nombre']

    # Representación en cadena de la categoría
    def __str__(self):
        # Devuelve el nombre de la categoría
        return self.nombre


# Modelo principal que abstrae los alimentos y bebidas registrados en acopio
class Alimento(models.Model):
    # Catálogo de categorías válidas para selección y filtrado en todo el sistema
    CLASIFICACION_CHOICES = [
        ('AGUA_EMBOTELLADA', 'Agua Embotellada y Bebidas'),
        ('COMIDA_ENLATADA', 'Comida Enlatada y Conservas'),
        ('GRANOS_ABARROTES', 'Granos, Semillas y Abarrotes'),
        ('FRUTAS_VERDURAS', 'Frutas y Verduras Frescas'),
        ('LACTEOS', 'Lácteos y Derivados'),
        ('PROTEINAS_CARNES', 'Carnes, Embutidos y Proteínas'),
        ('COMIDA_PREPARADA', 'Comida Preparada'),
        ('PANADERIA', 'Panadería y Tortillería'),
        ('INFANTIL', 'Alimento Infantil y Fórmula'),
        ('DESPENSA', 'Despensa Básica Armable'),
        ('OTRO', 'Otro'),
    ]

    # Opciones de naturaleza y conservación del alimento
    TIPO_CHOICES = [
        ('PERECEDERO', 'Perecedero'),
        ('NO_PERECEDERO', 'No Perecedero'),
        ('PREPARADO', 'Preparado'),
        ('BEBIDA', 'Bebida / Líquido'),
    ]

    # Tipos de envase aceptados en el centro de acopio
    ENVASE_CHOICES = [
        ('BOTELLA_PLASTICO', 'Botella / Garrafón'),
        ('LATA', 'Lata / Conserva'),
        ('CAJA', 'Caja / Tetra Pak'),
        ('BOLSA', 'Bolsa / Paquete Sellado'),
        ('COSTAL', 'Costal / Saco'),
        ('FRASCO', 'Frasco de Vidrio'),
        ('CHAROLA', 'Charola / Contenedor'),
        ('GRANEL', 'A Granel'),
        ('OTRO', 'Otro'),
    ]

    # Unidades de medida estándar para inventario
    UNIDAD_CHOICES = [
        ('UNIDAD', 'Unidades / Piezas'),
        ('BOTELLA', 'Botellas'),
        ('GARRAFON', 'Garrafones'),
        ('LATA', 'Latas'),
        ('LITRO', 'Litros (L)'),
        ('MILILITRO', 'Mililitros (ml)'),
        ('KILOGRAMO', 'Kilogramos (kg)'),
        ('GRAMO', 'Gramos (g)'),
        ('CAJA', 'Cajas'),
        ('PAQUETE', 'Paquetes'),
        ('PORCION', 'Porciones / Raciones'),
    ]

    # Estado físico y sanitario del producto
    CONDICION_CHOICES = [
        ('OPTIMO', 'Óptimo / Sellado'),
        ('BUENO', 'Buen Estado'),
        ('PROXIMO_VENCER', 'Próximo a Vencer'),
        ('RECHAZADO', 'No Apto / Dañado'),
    ]

    # Estado de disponibilidad dentro del inventario
    ESTADO_CHOICES = [
        ('DISPONIBLE', 'Disponible en Acopio'),
        ('ACTIVA', 'Activa'),
        ('RESERVADA', 'Reservada'),
        ('ENTREGADO', 'Entregado / Distribuido'),
        ('CADUCADO', 'Caducado / Baja'),
        ('EN_REVISION', 'En Revisión'),
    ]

    # Nombre o descripción principal del alimento
    nombre = models.CharField(max_length=150)
    # Marca comercial opcional del producto
    marca = models.CharField(max_length=100, blank=True)
    # Relación opcional con la tabla de categorías
    categoria = models.ForeignKey(
        CategoriaAlimento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alimentos',
    )
    # Clave de categoría indexada para filtrado rápido
    clasificacion = models.CharField(
        max_length=30,
        choices=CLASIFICACION_CHOICES,
        default='OTRO',
        db_index=True,
    )
    # Tipo de conservación indexado
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='NO_PERECEDERO',
        db_index=True,
    )
    # Tipo de empaque del alimento
    tipo_envase = models.CharField(
        max_length=25,
        choices=ENVASE_CHOICES,
        default='OTRO',
        db_index=True,
    )
    # Cantidad numérica registrada
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    # Unidad de medida asociada a la cantidad
    unidad_medida = models.CharField(
        max_length=20,
        choices=UNIDAD_CHOICES,
        default='UNIDAD',
    )
    # Detalle de presentación física
    presentacion = models.CharField(
        max_length=100,
        blank=True,
        help_text='Ej. Botella 1.5L, Lata 400g, Caja con 12 unidades',
    )
    # Peso por unidad en kilogramos
    peso_unitario_kg = models.DecimalField(max_digits=8, decimal_places=3, default=0.0)
    # Raciones estimadas por pieza
    personas_por_pieza = models.IntegerField(default=1)
    # Condición física de ingreso
    condicion = models.CharField(
        max_length=20,
        choices=CONDICION_CHOICES,
        default='OPTIMO',
    )
    # Indica si requiere refrigeración
    requiere_refrigeracion = models.BooleanField(default=False)
    # Rango de temperatura sugerido
    temperatura_recomendada = models.CharField(max_length=50, blank=True)
    # Código de lote para trazabilidad
    codigo_lote = models.CharField(max_length=80, blank=True)
    # Fecha de alta automática
    fecha_ingreso = models.DateTimeField(auto_now_add=True)
    # Fecha límite de consumo o caducidad
    fecha_caducidad = models.DateField(null=True, blank=True, db_index=True)
    # Estado actual del lote en almacén
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='DISPONIBLE',
        db_index=True,
    )
    # Ubicación dentro del centro de acopio
    ubicacion_almacen = models.CharField(max_length=100, blank=True)
    # Requisito de conservación o notas adicionales
    descripcion = models.TextField(blank=True)
    # Centro de acopio donde se resguarda
    centro_acopio = models.ForeignKey(
        CentroAcopio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventario',
    )

    # Asigna el manager personalizado a la clase Alimento
    objects = AlimentoQuerySet.as_manager()

    # Configuración de metadatos e índices de base de datos
    class Meta:
        # Nombre singular en admin
        verbose_name = 'Alimento'
        # Nombre plural en admin
        verbose_name_plural = 'Alimentos'
        # Ordenado por caducidad más próxima y nombre
        ordering = ['fecha_caducidad', 'nombre']
        # Índices compuestos para optimizar consultas en SQLite
        indexes = [
            models.Index(fields=['clasificacion', 'estado']),
            models.Index(fields=['tipo', 'fecha_caducidad']),
        ]

    # Representación legible del alimento
    def __str__(self):
        # Retorna nombre, cantidad y unidad
        return f"{self.nombre} ({self.cantidad} {self.get_unidad_medida_display()})"

    # Propiedad que expone el nombre como título para compatibilidad con plantillas
    @property
    def titulo(self):
        # Retorna el nombre del alimento
        return self.nombre

    # Propiedad que calcula el peso total del lote en kilogramos
    @property
    def peso_total_kg(self):
        # Multiplica la cantidad por el peso unitario
        return float(self.cantidad) * float(self.peso_unitario_kg)

    # Método para actualizar la cantidad disponible del alimento
    def cambiar_cantidad(self, nueva_cantidad):
        # Asigna el nuevo valor de stock
        self.cantidad = nueva_cantidad
        # Si llega a cero, marca el alimento como entregado
        if self.cantidad <= 0:
            self.estado = 'ENTREGADO'
        # Guarda los cambios en la base de datos
        self.save(update_fields=['cantidad', 'estado'])


# Información nutricional vinculada uno a uno con Alimento
class Nutrientes(models.Model):
    # Relación 1 a 1 con el alimento correspondiente
    alimento = models.OneToOneField(
        Alimento,
        on_delete=models.CASCADE,
        related_name='nutrientes',
    )
    # Kilocalorías por porción
    calorias = models.FloatField(default=0.0)
    # Gramos de proteína
    proteinas = models.FloatField(default=0.0)
    # Gramos de carbohidratos
    carbohidratos = models.FloatField(default=0.0)
    # Gramos de grasas totales
    grasas = models.FloatField(default=0.0)
    # Miligramos de sodio
    sodio = models.FloatField(default=0.0)
    # Gramos de azúcares
    azucares = models.FloatField(default=0.0)
    # Detalle de vitaminas y minerales
    descripcion_vitaminas = models.CharField(max_length=255, blank=True)

    # Metadatos para el panel de administración
    class Meta:
        # Nombre en singular
        verbose_name = 'Información Nutricional'
        # Nombre en plural
        verbose_name_plural = 'Información Nutricional'

    # Representación en texto de los nutrientes
    def __str__(self):
        # Indica a qué alimento pertenecen los nutrientes
        return f"Nutrientes de {self.alimento.nombre}"


# Modelo que encapsula cada entrega de donación, su evidencia fotográfica, su feedback y los usuarios propietarios
class Donacion(models.Model):
    # Estados posibles del ciclo de vida de una donación
    ESTADO_DONACION_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Recibido', 'Recibido en Centro de Acopio'),
        ('Aceptado', 'Aceptado'),
        ('Activa', 'Activa'),
        ('Reservado', 'Reservado'),
        ('Reservada', 'Reservada'),
        ('Rechazado', 'Rechazado'),
        ('Entregada', 'Entregada a Receptor'),
        ('Cancelada', 'Cancelada'),
    ]

    # Referencia opcional al perfil Donante específico
    donante = models.ForeignKey(
        Donante,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donaciones',
    )
    # Cuenta de usuario exacta que registró la donación (encapsulamiento de Donante)
    usuario_donante = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donaciones_realizadas',
    )
    # Nombre o razón social capturada en el formulario de entrega
    nombre_donante = models.CharField(
        max_length=150,
        blank=True,
        help_text='Nombre del donante o institución cuando se registra directamente en acopio',
    )
    # Referencia opcional al perfil Receptor que gestionó la donación
    receptor = models.ForeignKey(
        Receptor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donaciones_recibidas',
    )
    # Cuenta de usuario Receptor exacta que aceptó, rechazó o reservó la donación (encapsulamiento de Historial)
    usuario_receptor = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donaciones_gestionadas',
    )
    # Sede de acopio donde se recibe el alimento
    centro_acopio = models.ForeignKey(
        CentroAcopio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donaciones',
    )
    # Alimento donado vinculado a este registro
    alimento = models.ForeignKey(
        Alimento,
        on_delete=models.CASCADE,
        related_name='donaciones',
    )
    # Cantidad expresada con su unidad (ej. 10 kg, 5 cajas)
    cantidad = models.CharField(max_length=100, help_text='Ej. 30 cajas, 80 unidades, 10 kg')
    # Peso estimado en kilogramos para métricas del dashboard
    peso_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    # Tipo de conservación (Perecedero / No Perecedero)
    tipo = models.CharField(
        max_length=30,
        choices=Alimento.TIPO_CHOICES,
        default='NO_PERECEDERO',
    )
    # Estado actual de la donación
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_DONACION_CHOICES,
        default='Recibido',
        db_index=True,
    )
    # Retroalimentación (feedback) explicando por qué se aceptó, rechazó o reservó
    feedback = models.TextField(blank=True)
    # Imagen de evidencia fotográfica almacenada en formato Data URI para visualización en modal
    evidencia_imagen = models.TextField(blank=True)
    # Medio de transporte o envío
    metodo_envio = models.CharField(max_length=50, blank=True)
    # Indica si requiere cadena de frío durante el traslado
    requiere_refrigeracion = models.BooleanField(default=False)
    # Dirección de recolección o entrega capturada
    direccion_entrega = models.CharField(max_length=255, blank=True)
    # Código único de seguimiento
    codigo_confirmacion = models.CharField(max_length=50, blank=True)
    # Fecha y hora de creación del registro
    fecha_registro = models.DateTimeField(auto_now_add=True)
    # Fecha y hora en que el receptor procesó la donación
    fecha_recepcion = models.DateTimeField(null=True, blank=True)
    # Fecha de caducidad reportada
    fecha_caducidad = models.DateField(null=True, blank=True)
    # Notas o requisitos de conservación
    descripcion = models.TextField(blank=True)
    # Teléfono de contacto capturado en el formulario de donación (commit 67de301)
    telefono_contacto = models.CharField(max_length=25, blank=True)
    # Requisito específico de conservación (ambiente, refrigerado, congelado, etc.)
    tipo_conservacion = models.CharField(max_length=50, blank=True)
    # Fecha preferida para la entrega o recolección
    fecha_entrega = models.DateField(null=True, blank=True)
    # Hora de inicio de disponibilidad para entrega
    hora_desde = models.TimeField(null=True, blank=True)
    # Hora de fin de disponibilidad para entrega
    hora_hasta = models.TimeField(null=True, blank=True)
    # Indicaciones adicionales para coordinar la entrega
    notas_entrega = models.TextField(blank=True)
    # Archivo de imagen de evidencia almacenado en MEDIA_ROOT/donaciones/
    imagen_evidencia = models.ImageField(upload_to='donaciones/', null=True, blank=True)
    # Confirmación de la declaración de responsabilidad e higiene
    declaracion_aceptada = models.BooleanField(default=False)

    # Metadatos del modelo Donacion
    class Meta:
        # Nombre en singular
        verbose_name = 'Donación'
        # Nombre en plural
        verbose_name_plural = 'Donaciones'
        # Ordenado desde la donación más reciente
        ordering = ['-fecha_registro']

    # Representación en texto de la donación
    def __str__(self):
        # Obtiene el nombre del donante según los datos disponibles
        origen = self.donante.nombre_local if (self.donante and self.donante.nombre_local) else (
            self.donante.username if self.donante else (self.nombre_donante or 'Anónimo')
        )
        # Retorna folio, alimento y donante
        return f"Donación #{self.id} - {self.alimento.nombre} ({origen})"

    # Método encapsulado para que un Receptor registre su decisión (Aceptar, Reservar, Rechazar) y su feedback
    def aplicar_decision_receptor(self, usuario, nuevo_estado=None, comentario_feedback=None):
        # Si el usuario está autenticado, vincula la donación exclusivamente a ese Receptor
        if usuario and usuario.is_authenticated:
            # Guarda la cuenta de usuario receptor para aislar su historial
            self.usuario_receptor = usuario
            # Si el usuario cuenta con instancia en la tabla Receptor, también la enlaza
            if hasattr(usuario, 'receptor'):
                self.receptor = usuario.receptor
        # Si se envió un nuevo estado válido, actualiza el estado y la fecha de recepción
        if nuevo_estado in ('Aceptado', 'Reservado', 'Rechazado', 'Recibido'):
            self.estado = nuevo_estado
            self.fecha_recepcion = timezone.now()
        # Si se proporcionó texto de feedback, actualiza el motivo de la decisión
        if comentario_feedback is not None:
            self.feedback = comentario_feedback.strip()
        # Guarda los cambios en la tabla de donaciones
        self.save()
        # Sincroniza el estado del alimento asociado en el inventario del centro de acopio
        if self.alimento and nuevo_estado:
            if nuevo_estado == 'Aceptado':
                self.alimento.estado = 'ENTREGADO'
            elif nuevo_estado == 'Reservado':
                self.alimento.estado = 'RESERVADA'
            elif nuevo_estado == 'Rechazado':
                self.alimento.estado = 'EN_REVISION'
            elif nuevo_estado == 'Recibido':
                self.alimento.estado = 'DISPONIBLE'
            self.alimento.save(update_fields=['estado'])

        # Almacena la informacion de la decision del receptor
        notificar_decision_receptor(
            donacion=self,
            usuario_receptor=usuario,
            accion=nuevo_estado or 'GuardarFeedback',
            comentario_feedback=comentario_feedback,
        )

    # Método encapsulado para regresar una donación desde el Historial hacia Consultar Donaciones (por atender)
    def regresar_a_consulta(self, usuario, comentario_feedback=None):
        # Libera la asignación del receptor para que vuelva a estar disponible para cualquier receptor
        self.usuario_receptor = None
        self.receptor = None
        # Regresa el estado de la donación a 'Recibido' (por atender) y limpia la fecha de recepción
        self.estado = 'Recibido'
        self.fecha_recepcion = None
        # Si el receptor escribió una aclaración al regresar la donación, actualiza el comentario visible al donante
        if comentario_feedback is not None:
            self.feedback = comentario_feedback.strip()
        # Guarda los cambios en la tabla de donaciones
        self.save()
        # Devuelve el alimento vinculado al estado DISPONIBLE en el inventario
        if self.alimento:
            self.alimento.estado = 'DISPONIBLE'
            self.alimento.save(update_fields=['estado'])
        # Notifica al donante (y confirma al receptor) que la donación regresó a estado por atender
        notificar_decision_receptor(
            donacion=self,
            usuario_receptor=usuario,
            accion='Regresado',
            comentario_feedback=comentario_feedback,
        )

    # Método encapsulado para que el rol Receptor pueda quitar/eliminar una donación del sistema
    def eliminar_por_receptor(self):
        # Notifica al donante antes de borrar el registro de la base de datos
        notificar_donacion_eliminada(self)
        # Guarda referencia al alimento vinculado antes de borrar la donación
        alimento_ref = self.alimento
        # Elimina el registro de donación
        self.delete()
        # Si el alimento no tiene otras donaciones asociadas, lo elimina también del inventario
        if alimento_ref and not alimento_ref.donaciones.exists():
            alimento_ref.delete()


# Bitácora de movimientos de inventario en el centro de acopio
class MovimientoInventario(models.Model):
    # Tipos de movimiento de almacén
    TIPO_MOVIMIENTO_CHOICES = [
        ('ENTRADA', 'Entrada a Centro de Acopio'),
        ('SALIDA', 'Salida / Entrega a Beneficiario'),
        ('AJUSTE', 'Ajuste de Inventario'),
        ('BAJA_CADUCIDAD', 'Baja por Caducidad o Daño'),
    ]

    # Alimento involucrado en el movimiento
    alimento = models.ForeignKey(
        Alimento,
        on_delete=models.CASCADE,
        related_name='movimientos',
    )
    # Sede donde ocurrió el movimiento
    centro_acopio = models.ForeignKey(
        CentroAcopio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos',
    )
    # Tipo de operación realizada
    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TIPO_MOVIMIENTO_CHOICES,
        default='ENTRADA',
        db_index=True,
    )
    # Cantidad movida
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    # Usuario que registró la operación
    responsable = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_registrados',
    )
    # Receptor beneficiario en caso de salida
    receptor_destino = models.ForeignKey(
        Receptor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entregas_recibidas',
    )
    # Fecha automática del movimiento
    fecha = models.DateTimeField(auto_now_add=True)
    # Descripción del motivo del movimiento
    motivo = models.CharField(max_length=255, blank=True)

    # Metadatos de movimientos de inventario
    class Meta:
        # Nombre en singular
        verbose_name = 'Movimiento de Inventario'
        # Nombre en plural
        verbose_name_plural = 'Movimientos de Inventario'
        # Ordenado del más reciente al más antiguo
        ordering = ['-fecha']

    # Representación en texto del movimiento
    def __str__(self):
        # Retorna tipo de movimiento, alimento y cantidad
        return f"{self.get_tipo_movimiento_display()} - {self.alimento.nombre} ({self.cantidad})"


# Modelo de alertas para notificar caducidades, cadena de frío o recepciones
class Alerta(models.Model):
    # Categorías de alerta soportadas
    TIPO_ALERTA_CHOICES = [
        ('CADUCIDAD_PROXIMA', 'Caducidad Próxima'),
        ('CADUCIDAD_VENCIDA', 'Alimento Caducado'),
        ('STOCK_BAJO', 'Stock Bajo en Acopio'),
        ('CADENA_FRIO', 'Alerta de Cadena de Frío'),
        ('NUEVA_DONACION', 'Nueva Donación Recibida'),
    ]

    # Niveles de prioridad de atención
    PRIORIDAD_CHOICES = [
        (1, 'Baja'),
        (2, 'Media'),
        (3, 'Alta'),
        (4, 'Crítica'),
    ]

    # Alimento relacionado con la alerta
    alimento = models.ForeignKey(
        Alimento,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alertas',
    )
    # Donación relacionada con la alerta
    donacion = models.ForeignKey(
        Donacion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alertas',
    )
    # Texto descriptivo de la alerta
    mensaje = models.CharField(max_length=255)
    # Clasificación del aviso
    tipo_alerta = models.CharField(
        max_length=25,
        choices=TIPO_ALERTA_CHOICES,
        default='CADUCIDAD_PROXIMA',
    )
    # Prioridad numérica
    nivel_prioridad = models.IntegerField(choices=PRIORIDAD_CHOICES, default=2)
    # Fecha y hora de generación
    fecha_emision = models.DateTimeField(auto_now_add=True)
    # Indica si la alerta ya fue revisada
    estado_atendida = models.BooleanField(default=False)

    # Metadatos de Alerta
    class Meta:
        # Nombre en singular
        verbose_name = 'Alerta'
        # Nombre en plural
        verbose_name_plural = 'Alertas'
        # Ordena primero por mayor prioridad y fecha reciente
        ordering = ['-nivel_prioridad', '-fecha_emision']

    # Representación en cadena de la alerta
    def __str__(self):
        # Muestra prioridad y mensaje
        return f"[{self.get_nivel_prioridad_display()}] {self.mensaje}"

    # Método para marcar una alerta como resuelta
    def marcar_como_atendida(self):
        # Cambia el estado booleano a verdadero
        self.estado_atendida = True
        # Guarda el cambio en la base de datos
        self.save(update_fields=['estado_atendida'])


class Notificacion(models.Model):
    # Usuario que recibe la alerta
    destiny = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notificaciones',
        verbose_name="Destinatario"
    )
    
    # Información primordial (para la cajita desplegable de la campanita)
    titulo = models.CharField(max_length=150, verbose_name="Título Corto")
    
    # Información detallada (para la tabla completa)
    mensaje = models.TextField(verbose_name="Descripción Detallada")
    
    # Diferenciación de roles clave solicitada ('donante', 'receptor', 'general')
    rol_destino = models.CharField(
        max_length=50, 
        default='general', 
        verbose_name="Rol de Destino (Donante/Receptor)"
    )
    
    # Estilos o prioridad ('info', 'success', 'warning', 'danger')
    level = models.CharField(max_length=30, default='info', verbose_name="Nivel")
    
    # Estado de lectura
    read = models.BooleanField(default=False, verbose_name="Leída")
    
    # Marca de tiempo
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.rol_destino.upper()}] {self.titulo} - {self.destiny.username}"