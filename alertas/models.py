from datetime import timedelta
from django.db import models
from django.utils import timezone
from users.models import Usuario, Donante, Receptor


# Manager personalizado para filtrar alimentos del centro de acopio (por tipo, categoría o caducidad)
class AlimentoQuerySet(models.QuerySet):
    def disponibles(self):
        return self.filter(estado='DISPONIBLE', cantidad__gt=0)

    def perecederos(self):
        return self.filter(tipo='PERECEDERO')

    def no_perecederos(self):
        return self.filter(tipo='NO_PERECEDERO')

    def aguas_embotelladas(self):
        return self.filter(clasificacion='AGUA_EMBOTELLADA')

    def comida_enlatada(self):
        return self.filter(clasificacion='COMIDA_ENLATADA')

    def granos_y_abarrotes(self):
        return self.filter(clasificacion='GRANOS_ABARROTES')

    def comida_preparada(self):
        return self.filter(clasificacion='COMIDA_PREPARADA')

    def requieren_refrigeracion(self):
        return self.filter(requiere_refrigeracion=True)

    def proximos_a_caducar(self, dias=7):
        hoy = timezone.now().date()
        limite = hoy + timedelta(days=dias)
        return self.filter(
            fecha_caducidad__isnull=False,
            fecha_caducidad__gte=hoy,
            fecha_caducidad__lte=limite,
        )

    def caducados(self):
        hoy = timezone.now().date()
        return self.filter(
            fecha_caducidad__isnull=False,
            fecha_caducidad__lt=hoy,
        )

    # Filtro combinado para búsquedas dinámicas en vistas
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
        qs = self
        if clasificacion:
            qs = qs.filter(clasificacion=clasificacion)
        if tipo:
            qs = qs.filter(tipo=tipo)
        if tipo_envase:
            qs = qs.filter(tipo_envase=tipo_envase)
        if estado:
            qs = qs.filter(estado=estado)
        if categoria_id:
            qs = qs.filter(categoria_id=categoria_id)
        if centro_acopio_id:
            qs = qs.filter(centro_acopio_id=centro_acopio_id)
        if requiere_refrigeracion is not None:
            qs = qs.filter(requiere_refrigeracion=requiere_refrigeracion)
        if busqueda:
            qs = qs.filter(
                models.Q(nombre__icontains=busqueda)
                | models.Q(marca__icontains=busqueda)
                | models.Q(descripcion__icontains=busqueda)
                | models.Q(codigo_lote__icontains=busqueda)
            )
        return qs


# Modelo que representa la sede física del centro de acopio y su capacidad de almacenamiento
class CentroAcopio(models.Model):
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(max_length=20, blank=True)
    capacidad_maxima_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tiene_refrigeracion = models.BooleanField(default=True)
    responsable = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='centros_acopio',
    )
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Centro de Acopio'
        verbose_name_plural = 'Centros de Acopio'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


# Catálogo de categorías para clasificar los insumos recibidos (agua, enlatados, granos, etc.)
class CategoriaAlimento(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    clave = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    es_perecedero_default = models.BooleanField(default=False)
    requiere_refrigeracion_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Categoría de Alimento'
        verbose_name_plural = 'Categorías de Alimentos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


# Modelo principal de inventario de alimentos y bebidas registrados en el centro de acopio
class Alimento(models.Model):
    # Opciones de clasificación general para filtrado rápido
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

    # Opciones de conservación y naturaleza del producto
    TIPO_CHOICES = [
        ('PERECEDERO', 'Perecedero'),
        ('NO_PERECEDERO', 'No Perecedero'),
        ('PREPARADO', 'Preparado'),
        ('BEBIDA', 'Bebida / Líquido'),
    ]

    # Tipos de empaque o presentación recibida
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

    # Unidades de medida para control de existencias
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

    CONDICION_CHOICES = [
        ('OPTIMO', 'Óptimo / Sellado'),
        ('BUENO', 'Buen Estado'),
        ('PROXIMO_VENCER', 'Próximo a Vencer'),
        ('RECHAZADO', 'No Apto / Dañado'),
    ]

    ESTADO_CHOICES = [
        ('DISPONIBLE', 'Disponible en Acopio'),
        ('ACTIVA', 'Activa'),
        ('RESERVADA', 'Reservada'),
        ('ENTREGADO', 'Entregado / Distribuido'),
        ('CADUCADO', 'Caducado / Baja'),
        ('EN_REVISION', 'En Revisión'),
    ]

    nombre = models.CharField(max_length=150)
    marca = models.CharField(max_length=100, blank=True)
    categoria = models.ForeignKey(
        CategoriaAlimento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alimentos',
    )
    clasificacion = models.CharField(
        max_length=30,
        choices=CLASIFICACION_CHOICES,
        default='OTRO',
        db_index=True,
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='NO_PERECEDERO',
        db_index=True,
    )
    tipo_envase = models.CharField(
        max_length=25,
        choices=ENVASE_CHOICES,
        default='OTRO',
        db_index=True,
    )
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unidad_medida = models.CharField(
        max_length=20,
        choices=UNIDAD_CHOICES,
        default='UNIDAD',
    )
    presentacion = models.CharField(
        max_length=100,
        blank=True,
        help_text='Ej. Botella 1.5L, Lata 400g, Caja con 12 unidades',
    )
    peso_unitario_kg = models.DecimalField(max_digits=8, decimal_places=3, default=0.0)
    personas_por_pieza = models.IntegerField(default=1)
    condicion = models.CharField(
        max_length=20,
        choices=CONDICION_CHOICES,
        default='OPTIMO',
    )
    requiere_refrigeracion = models.BooleanField(default=False)
    temperatura_recomendada = models.CharField(max_length=50, blank=True)
    codigo_lote = models.CharField(max_length=80, blank=True)
    fecha_ingreso = models.DateTimeField(auto_now_add=True)
    fecha_caducidad = models.DateField(null=True, blank=True, db_index=True)
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='DISPONIBLE',
        db_index=True,
    )
    ubicacion_almacen = models.CharField(max_length=100, blank=True)
    descripcion = models.TextField(blank=True)
    centro_acopio = models.ForeignKey(
        CentroAcopio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventario',
    )

    objects = AlimentoQuerySet.as_manager()

    class Meta:
        verbose_name = 'Alimento'
        verbose_name_plural = 'Alimentos'
        ordering = ['fecha_caducidad', 'nombre']
        # Índices en SQLite para agilizar filtros por clasificación, estado y caducidad
        indexes = [
            models.Index(fields=['clasificacion', 'estado']),
            models.Index(fields=['tipo', 'fecha_caducidad']),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.cantidad} {self.get_unidad_medida_display()})"

    @property
    def titulo(self):
        return self.nombre

    @property
    def peso_total_kg(self):
        return float(self.cantidad) * float(self.peso_unitario_kg)

    def cambiar_cantidad(self, nueva_cantidad):
        self.cantidad = nueva_cantidad
        if self.cantidad <= 0:
            self.estado = 'ENTREGADO'
        self.save(update_fields=['cantidad', 'estado'])


# Información nutricional asociada 1 a 1 con cada Alimento (según diagrama UML)
class Nutrientes(models.Model):
    alimento = models.OneToOneField(
        Alimento,
        on_delete=models.CASCADE,
        related_name='nutrientes',
    )
    calorias = models.FloatField(default=0.0)
    proteinas = models.FloatField(default=0.0)
    carbohidratos = models.FloatField(default=0.0)
    grasas = models.FloatField(default=0.0)
    sodio = models.FloatField(default=0.0)
    azucares = models.FloatField(default=0.0)
    descripcion_vitaminas = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Información Nutricional'
        verbose_name_plural = 'Información Nutricional'

    def __str__(self):
        return f"Nutrientes de {self.alimento.nombre}"


# Registro de cada donación recibida o canalizada entre donante, centro de acopio y receptor
class Donacion(models.Model):
    ESTADO_DONACION_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Recibido', 'Recibido en Centro de Acopio'),
        ('Activa', 'Activa'),
        ('Reservada', 'Reservada'),
        ('Rechazado', 'Rechazado'),
        ('Entregada', 'Entregada a Receptor'),
        ('Cancelada', 'Cancelada'),
    ]

    donante = models.ForeignKey(
        Donante,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donaciones',
    )
    nombre_donante = models.CharField(
        max_length=150,
        blank=True,
        help_text='Nombre del donante o institución cuando se registra directamente en acopio',
    )
    receptor = models.ForeignKey(
        Receptor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donaciones_recibidas',
    )
    centro_acopio = models.ForeignKey(
        CentroAcopio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donaciones',
    )
    alimento = models.ForeignKey(
        Alimento,
        on_delete=models.CASCADE,
        related_name='donaciones',
    )
    cantidad = models.CharField(max_length=100, help_text='Ej. 30 cajas, 80 unidades, 10 kg')
    peso_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    tipo = models.CharField(
        max_length=30,
        choices=Alimento.TIPO_CHOICES,
        default='NO_PERECEDERO',
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_DONACION_CHOICES,
        default='Recibido',
        db_index=True,
    )
    metodo_envio = models.CharField(max_length=50, blank=True)
    requiere_refrigeracion = models.BooleanField(default=False)
    direccion_entrega = models.CharField(max_length=255, blank=True)
    codigo_confirmacion = models.CharField(max_length=50, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_recepcion = models.DateTimeField(null=True, blank=True)
    fecha_caducidad = models.DateField(null=True, blank=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Donación'
        verbose_name_plural = 'Donaciones'
        ordering = ['-fecha_registro']

    def __str__(self):
        origen = self.donante.nombre_local if (self.donante and self.donante.nombre_local) else (
            self.donante.username if self.donante else (self.nombre_donante or 'Anónimo')
        )
        return f"Donación #{self.id} - {self.alimento.nombre} ({origen})"


# Bitácora de movimientos de entradas, salidas y bajas dentro del almacén del centro de acopio
class MovimientoInventario(models.Model):
    TIPO_MOVIMIENTO_CHOICES = [
        ('ENTRADA', 'Entrada a Centro de Acopio'),
        ('SALIDA', 'Salida / Entrega a Beneficiario'),
        ('AJUSTE', 'Ajuste de Inventario'),
        ('BAJA_CADUCIDAD', 'Baja por Caducidad o Daño'),
    ]

    alimento = models.ForeignKey(
        Alimento,
        on_delete=models.CASCADE,
        related_name='movimientos',
    )
    centro_acopio = models.ForeignKey(
        CentroAcopio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos',
    )
    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TIPO_MOVIMIENTO_CHOICES,
        default='ENTRADA',
        db_index=True,
    )
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    responsable = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_registrados',
    )
    receptor_destino = models.ForeignKey(
        Receptor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entregas_recibidas',
    )
    fecha = models.DateTimeField(auto_now_add=True)
    motivo = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Movimiento de Inventario'
        verbose_name_plural = 'Movimientos de Inventario'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.get_tipo_movimiento_display()} - {self.alimento.nombre} ({self.cantidad})"


# Sistema de avisos y alertas para caducidades próximas, stock bajo o cadena de frío
class Alerta(models.Model):
    TIPO_ALERTA_CHOICES = [
        ('CADUCIDAD_PROXIMA', 'Caducidad Próxima'),
        ('CADUCIDAD_VENCIDA', 'Alimento Caducado'),
        ('STOCK_BAJO', 'Stock Bajo en Acopio'),
        ('CADENA_FRIO', 'Alerta de Cadena de Frío'),
        ('NUEVA_DONACION', 'Nueva Donación Recibida'),
    ]

    PRIORIDAD_CHOICES = [
        (1, 'Baja'),
        (2, 'Media'),
        (3, 'Alta'),
        (4, 'Crítica'),
    ]

    alimento = models.ForeignKey(
        Alimento,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alertas',
    )
    donacion = models.ForeignKey(
        Donacion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alertas',
    )
    mensaje = models.CharField(max_length=255)
    tipo_alerta = models.CharField(
        max_length=25,
        choices=TIPO_ALERTA_CHOICES,
        default='CADUCIDAD_PROXIMA',
    )
    nivel_prioridad = models.IntegerField(choices=PRIORIDAD_CHOICES, default=2)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    estado_atendida = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        ordering = ['-nivel_prioridad', '-fecha_emision']

    def __str__(self):
        return f"[{self.get_nivel_prioridad_display()}] {self.mensaje}"

    def marcar_como_atendida(self):
        self.estado_atendida = True
        self.save(update_fields=['estado_atendida'])
