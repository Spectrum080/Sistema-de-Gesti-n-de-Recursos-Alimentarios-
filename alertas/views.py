import re
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import Donacion, Alimento, CategoriaAlimento, CentroAcopio, MovimientoInventario
from users.models import Donante, Receptor


# Detecta y sincroniza en sesión si la vista actual corresponde al rol Receptor o Donante
def _es_rol_receptor(request):
    rol_param = request.GET.get('rol') or request.POST.get('rol')
    if rol_param in ('receptor', 'donante'):
        request.session['rol_activo'] = rol_param
        request.session.modified = True
    if rol_param == 'receptor':
        return True
    if rol_param == 'donante':
        return False
    if request.user.is_authenticated and hasattr(request.user, 'receptor'):
        return True
    if request.user.is_authenticated and hasattr(request.user, 'donante'):
        return False
    return request.session.get('rol_activo') == 'receptor'


# Obtiene y filtra en Python las donaciones desde db.sqlite3 mostrando primero las nuevas
def _obtener_lista_donaciones(categoria='TODAS'):
    queryset = list(
        Donacion.objects.select_related(
            'alimento', 'donante', 'receptor', 'centro_acopio'
        ).order_by('id')
    )
    nuevas = sorted([d for d in queryset if d.id > 13], key=lambda x: -x.id)
    base = [d for d in queryset if d.id <= 13]
    ordenadas = nuevas + base
    total_general = len(ordenadas)

    donaciones = []
    for d in ordenadas:
        clave_cat = d.alimento.clasificacion if d.alimento else 'OTRO'
        if categoria and categoria != 'TODAS' and clave_cat != categoria:
            continue

        donante_txt = (
            d.nombre_donante
            or (d.donante.nombre_local if d.donante and d.donante.nombre_local else None)
            or (d.donante.username if d.donante else 'Donante General')
        )
        caducidad_txt = (
            d.fecha_caducidad.strftime('%d/%m/%Y')
            if d.fecha_caducidad
            else (
                d.alimento.fecha_caducidad.strftime('%d/%m/%Y')
                if d.alimento and d.alimento.fecha_caducidad
                else 'No aplica'
            )
        )
        donaciones.append({
            'id': f"{d.id:03d}",
            'raw_id': d.id,
            'donante': donante_txt,
            'alimento': d.alimento.nombre if d.alimento else 'Alimento',
            'clasificacion': d.alimento.get_clasificacion_display() if d.alimento else 'General',
            'clasificacion_clave': clave_cat,
            'cantidad': d.cantidad,
            'peso': f"{float(d.peso_kg):g} kg" if d.peso_kg else '1 kg',
            'tipo': d.get_tipo_display(),
            'caducidad': caducidad_txt,
            'ubicacion': d.alimento.ubicacion_almacen if d.alimento and d.alimento.ubicacion_almacen else 'Recepción Acopio',
            'estado': d.estado,
        })
    return donaciones, total_general


# Vista en Python: gestiona cambio de estado por POST, filtro por categoría y paginación con Paginator
def consultarDonaciones(request):
    es_receptor = _es_rol_receptor(request)
    rol_actual = 'receptor' if es_receptor else 'donante'
    categoria_actual = request.GET.get('categoria') or request.POST.get('categoria') or 'TODAS'
    pagina_actual = request.GET.get('page') or request.POST.get('page') or 1

    # Actualiza en BD el estado de la donación y del alimento (Aceptado, Reservado o Rechazado)
    if request.method == 'POST':
        donacion_id = request.POST.get('donacion_id')
        accion = (request.POST.get('nuevo_estado') or '').strip()
        mapa_estados = {
            'Aceptado': 'Aceptado',
            'Reservado': 'Reservado',
            'Rechazado': 'Rechazado',
            'Recibido': 'Recibido',
        }
        nuevo_estado = mapa_estados.get(accion)
        if donacion_id and nuevo_estado:
            donacion = get_object_or_404(Donacion.objects.select_related('alimento'), pk=donacion_id)
            donacion.estado = nuevo_estado
            if nuevo_estado == 'Aceptado':
                donacion.fecha_recepcion = timezone.now()
                donacion.save(update_fields=['estado', 'fecha_recepcion'])
            else:
                donacion.save(update_fields=['estado'])

            if donacion.alimento:
                if nuevo_estado == 'Aceptado':
                    donacion.alimento.estado = 'ENTREGADO'
                elif nuevo_estado == 'Reservado':
                    donacion.alimento.estado = 'RESERVADA'
                elif nuevo_estado == 'Rechazado':
                    donacion.alimento.estado = 'EN_REVISION'
                donacion.alimento.save(update_fields=['estado'])

        return redirect(
            f"/alertas/consultarDonaciones/?rol={rol_actual}&categoria={categoria_actual}&page={pagina_actual}"
        )

    donaciones_filtradas, total_general = _obtener_lista_donaciones(categoria=categoria_actual)
    paginator = Paginator(donaciones_filtradas, 5)
    page_obj = paginator.get_page(pagina_actual)

    return render(request, 'alertas/consultarDonaciones.html', {
        'donaciones': page_obj,
        'page_obj': page_obj,
        'total_registros': len(donaciones_filtradas),
        'total_general': total_general,
        'categoria_actual': categoria_actual,
        'rol_actual': rol_actual,
        'es_receptor': es_receptor,
    })


# Muestra el historial paginado y filtrado 100% desde Python con Django Paginator
def historialDonaciones(request):
    es_receptor = _es_rol_receptor(request)
    rol_actual = 'receptor' if es_receptor else 'donante'
    categoria_actual = request.GET.get('categoria', 'TODAS')
    pagina_actual = request.GET.get('page', 1)

    donaciones_filtradas, total_general = _obtener_lista_donaciones(categoria=categoria_actual)
    paginator = Paginator(donaciones_filtradas, 5)
    page_obj = paginator.get_page(pagina_actual)

    return render(request, 'alertas/historialDonaciones.html', {
        'donaciones': page_obj,
        'page_obj': page_obj,
        'total_registros': len(donaciones_filtradas),
        'total_general': total_general,
        'categoria_actual': categoria_actual,
        'rol_actual': rol_actual,
        'es_receptor': es_receptor,
    })


# Registra manualmente un nuevo alimento, su donación y el movimiento de entrada en inventario
def cargarDonaciones(request):
    request.session['rol_activo'] = 'donante'
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        tipo = request.POST.get('tipo', 'NO_PERECEDERO')
        clasificacion = request.POST.get('clasificacion', 'OTRO')
        cantidad_txt = request.POST.get('cantidad', '1 unidad').strip()
        fecha_caducidad = request.POST.get('fecha_caducidad') or None
        descripcion = request.POST.get('descripcion', '').strip()

        match_num = re.search(r'(\d+(?:\.\d+)?)', cantidad_txt)
        cantidad_num = float(match_num.group(1)) if match_num else 1.0

        centro = CentroAcopio.objects.first()
        categoria = CategoriaAlimento.objects.filter(clave=clasificacion).first()

        alimento = Alimento.objects.create(
            nombre=titulo,
            categoria=categoria,
            clasificacion=clasificacion,
            tipo=tipo,
            cantidad=cantidad_num,
            peso_unitario_kg=1.0,
            fecha_caducidad=fecha_caducidad,
            estado='DISPONIBLE',
            descripcion=descripcion,
            centro_acopio=centro,
        )

        donante_obj = getattr(request.user, 'donante', None) if request.user.is_authenticated else Donante.objects.first()
        nombre_donante = (
            (donante_obj.nombre_local or donante_obj.username)
            if donante_obj
            else (request.user.username if request.user.is_authenticated else 'Donante Directo')
        )

        Donacion.objects.create(
            donante=donante_obj,
            nombre_donante=nombre_donante,
            receptor=Receptor.objects.first(),
            centro_acopio=centro,
            alimento=alimento,
            cantidad=cantidad_txt,
            peso_kg=cantidad_num,
            tipo=tipo,
            estado='Recibido',
            fecha_caducidad=fecha_caducidad,
            descripcion=descripcion,
        )

        MovimientoInventario.objects.create(
            alimento=alimento,
            centro_acopio=centro,
            tipo_movimiento='ENTRADA',
            cantidad=cantidad_num,
            responsable=request.user if request.user.is_authenticated else None,
            motivo='Registro desde formulario de Nueva Donación',
        )

        return redirect('/alertas/consultarDonaciones/?rol=donante')

    return render(request, 'alertas/cargarDonaciones.html')
