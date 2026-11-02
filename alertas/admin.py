from django.contrib import admin
from .models import (
    CentroAcopio,
    CategoriaAlimento,
    Alimento,
    Nutrientes,
    Donacion,
    MovimientoInventario,
    Alerta,
)


@admin.register(CentroAcopio)
class CentroAcopioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'telefono', 'capacidad_maxima_kg', 'tiene_refrigeracion', 'activo')
    list_filter = ('tiene_refrigeracion', 'activo')
    search_fields = ('nombre', 'direccion')


@admin.register(CategoriaAlimento)
class CategoriaAlimentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'clave', 'es_perecedero_default', 'requiere_refrigeracion_default')
    list_filter = ('es_perecedero_default', 'requiere_refrigeracion_default')
    search_fields = ('nombre', 'clave', 'descripcion')


@admin.register(Alimento)
class AlimentoAdmin(admin.ModelAdmin):
    list_display = (
        'nombre',
        'clasificacion',
        'tipo',
        'tipo_envase',
        'cantidad',
        'unidad_medida',
        'fecha_caducidad',
        'estado',
        'centro_acopio',
    )
    list_filter = (
        'clasificacion',
        'tipo',
        'tipo_envase',
        'estado',
        'condicion',
        'requiere_refrigeracion',
        'categoria',
        'centro_acopio',
    )
    search_fields = ('nombre', 'marca', 'codigo_lote', 'descripcion', 'ubicacion_almacen')
    ordering = ('fecha_caducidad', 'nombre')


@admin.register(Nutrientes)
class NutrientesAdmin(admin.ModelAdmin):
    list_display = ('alimento', 'calorias', 'proteinas', 'carbohidratos', 'grasas', 'sodio')
    search_fields = ('alimento__nombre', 'descripcion_vitaminas')


@admin.register(Donacion)
class DonacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'alimento', 'donante', 'nombre_donante', 'cantidad', 'tipo', 'estado', 'fecha_registro')
    list_filter = ('estado', 'tipo', 'requiere_refrigeracion', 'centro_acopio')
    search_fields = ('alimento__nombre', 'nombre_donante', 'donante__username', 'donante__nombre_local', 'codigo_confirmacion')


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ('alimento', 'tipo_movimiento', 'cantidad', 'centro_acopio', 'responsable', 'fecha')
    list_filter = ('tipo_movimiento', 'centro_acopio')
    search_fields = ('alimento__nombre', 'motivo')


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('mensaje', 'tipo_alerta', 'nivel_prioridad', 'alimento', 'estado_atendida', 'fecha_emision')
    list_filter = ('tipo_alerta', 'nivel_prioridad', 'estado_atendida')
    search_fields = ('mensaje', 'alimento__nombre')
