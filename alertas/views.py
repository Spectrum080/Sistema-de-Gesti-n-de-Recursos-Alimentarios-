# Importa base64 para codificar imágenes de evidencia fotográfica en Python puro
import base64
# Importa expresiones regulares para extraer valores numéricos de las cantidades
import re
# Importa el paginador nativo de Django para dividir registros sin usar JavaScript
from django.core.paginator import Paginator
# Importa funciones de atajo para renderizar vistas, redirigir y buscar objetos
from django.shortcuts import render, redirect, get_object_or_404
# Importa los modelos del centro de acopio y donaciones
from .models import Donacion, Alimento, CategoriaAlimento, CentroAcopio, MovimientoInventario, Notificacion
# Importación local para notificar únicamente al donante sobre su nueva entrega
from alertas.utils.notificaciones import notificar_donacion_registrada

# Importa el sistema de mensajes de Django para avisos de validación (ej. perfil incompleto)
from django.contrib import messages
# Importa el decorador para exigir sesión iniciada en vistas protegidas
from django.contrib.auth.decorators import login_required




# Función que determina y guarda en sesión si el usuario opera bajo el rol de Receptor o Donante
def _es_rol_receptor(request):
    # Verifica primero si hay un usuario autenticado para aplicar su rol real de base de datos
    if request.user.is_authenticated:
        # Si la cuenta pertenece al modelo Receptor, fuerza siempre el modo receptor
        if hasattr(request.user, 'receptor'):
            request.session['rol_activo'] = 'receptor'
            return True
        # Si la cuenta pertenece al modelo Donante, fuerza siempre el modo donante (impide usar ?rol=receptor)
        if hasattr(request.user, 'donante'):
            request.session['rol_activo'] = 'donante'
            return False

    # Solo para cuentas genéricas (ej. administrador), lee el parámetro 'rol' de GET o POST
    rol_param = request.GET.get('rol') or request.POST.get('rol')
    # Si el parámetro recibido es válido, lo guarda en la sesión
    if rol_param in ('receptor', 'donante'):
        request.session['rol_activo'] = rol_param
        request.session.modified = True
    # Retorna True si se pidió explícitamente modo receptor
    if rol_param == 'receptor':
        return True
    # Retorna False si se pidió explícitamente modo donante
    if rol_param == 'donante':
        return False
    # Si no hubo parámetro, consulta el último rol guardado en la sesión
    return request.session.get('rol_activo') == 'receptor'


# Función que obtiene y filtra las donaciones respetando el encapsulamiento de cada rol
def _obtener_lista_donaciones(request, modo='consulta', categoria='TODAS', es_receptor=False):
    # Si el usuario está autenticado, aplica los métodos encapsulados del modelo Usuario
    if request.user.is_authenticated:
        # Si se consulta el historial del receptor, obtiene solo las gestionadas por esa cuenta
        if modo == 'historial':
            queryset = list(request.user.obtener_mi_historial_receptor())
        # Si es el rol Receptor en consulta general, obtiene todas las donaciones disponibles para analizar
        elif es_receptor:
            queryset = list(request.user.obtener_donaciones_para_receptor())
        # Si es el rol Donante en Mis Donaciones, obtiene únicamente sus propias entregas
        else:
            queryset = list(request.user.obtener_mis_donaciones())
    # Si no hay sesión iniciada, retorna lista vacía por seguridad de encapsulamiento
    else:
        queryset = []

    # Cuenta el total de registros antes de aplicar el filtro de categoría
    total_general = len(queryset)
    # Inicializa la lista de diccionarios formateados para la plantilla HTML
    donaciones = []

    # Recorre cada objeto Donacion obtenido de la base de datos
    for d in queryset:
        # Obtiene la clave de categoría del alimento o asigna 'OTRO' por defecto
        clave_cat = d.alimento.clasificacion if d.alimento else 'OTRO'
        # Si se seleccionó una categoría específica y no coincide, omite este registro
        if categoria and categoria != 'TODAS' and clave_cat != categoria:
            continue

        # Determina el nombre del donante a mostrar en la tabla
        donante_txt = (
            d.nombre_donante
            or (d.donante.nombre_local if d.donante and d.donante.nombre_local else None)
            or (d.usuario_donante.username if d.usuario_donante else None)
            or (d.donante.username if d.donante else 'Donante General')
        )
        # Formatea la fecha de caducidad en día/mes/año
        caducidad_txt = (
            d.fecha_caducidad.strftime('%d/%m/%Y')
            if d.fecha_caducidad
            else (
                d.alimento.fecha_caducidad.strftime('%d/%m/%Y')
                if d.alimento and d.alimento.fecha_caducidad
                else 'No aplica'
            )
        )
        # Agrega el diccionario con todos los atributos encapsulados para la vista HTML
        donaciones.append({
            'id': f"{d.id:03d}",
            'raw_id': d.id,
            'donante': donante_txt,
            'alimento': d.alimento.nombre if d.alimento else 'Alimento',
            'clasificacion': d.alimento.get_clasificacion_display() if d.alimento else 'Otro',
            'clasificacion_clave': clave_cat,
            'cantidad': d.cantidad,
            'peso': f"{float(d.peso_kg):g} kg" if d.peso_kg else '1 kg',
            'tipo': d.get_tipo_display(),
            'caducidad': caducidad_txt,
            'ubicacion': d.alimento.ubicacion_almacen if d.alimento and d.alimento.ubicacion_almacen else 'Recepción Acopio',
            'estado': d.estado,
            'feedback': d.feedback,
            # Usa la imagen base64 o, si existe archivo subido en ImageField, su URL pública
            'evidencia_imagen': d.evidencia_imagen or (d.imagen_evidencia.url if d.imagen_evidencia else ''),
        })
    # Retorna la lista filtrada y el conteo general
    return donaciones, total_general


# Vista de detalle completo de una donación (mezcla del commit 67de301 con encapsulamiento por rol)
@login_required
def detalle_donacion(request, donacion_id):
    # Recupera la donación junto con su alimento y donante asociados o retorna 404 si no existe
    donacion = get_object_or_404(Donacion.objects.select_related('alimento', 'donante', 'receptor'), id=donacion_id)
    # Verifica si el usuario actual es Donante para impedir que consulte donaciones de otros donantes
    if hasattr(request.user, 'donante'):
        es_propietario = (
            donacion.usuario_donante_id == request.user.pk
            or donacion.donante_id == request.user.pk
        )
        if not es_propietario:
            return redirect('/alertas/consultarDonaciones/?rol=donante')
    # Si el usuario actual es Receptor, impide ver donaciones ya atendidas por otro receptor distinto
    elif hasattr(request.user, 'receptor'):
        atendida_por_otro = (
            (donacion.usuario_receptor_id is not None and donacion.usuario_receptor_id != request.user.pk)
            or (donacion.receptor_id is not None and donacion.receptor_id != request.user.pk)
        )
        if atendida_por_otro:
            return redirect('/alertas/consultarDonaciones/?rol=receptor')

    # Renderiza la plantilla de detalle que hereda de users/dashboard.html
    return render(request, 'alertas/responderDonacion.html', {'donacion': donacion})


# Función auxiliar compartida que procesa decisiones del Receptor tanto en Consulta como en Historial
def _procesar_accion_receptor(request):
    # Obtiene el identificador de la donación a modificar, regresar o eliminar
    donacion_id = request.POST.get('donacion_id')
    # Obtiene la acción solicitada (Aceptado, Reservado, Rechazado, Regresar, GuardarFeedback o Eliminar)
    accion = (request.POST.get('nuevo_estado') or '').strip()
    # Obtiene el comentario de retroalimentación (feedback) escrito por el receptor
    comentario_feedback = request.POST.get('feedback')

    # Si se proporcionó un ID de donación válido, busca el registro en la base de datos
    if donacion_id:
        # Recupera la donación junto con su alimento asociado
        donacion = get_object_or_404(Donacion.objects.select_related('alimento'), pk=donacion_id)
        # Encapsulamiento: impide modificar donaciones ya atendidas por otro receptor distinto
        ya_asignada_a_otro = (
            (donacion.usuario_receptor_id is not None and donacion.usuario_receptor_id != request.user.pk)
            or (donacion.receptor_id is not None and donacion.receptor_id != request.user.pk)
        )
        if not ya_asignada_a_otro:
            # Si el receptor presionó el botón para quitar/eliminar la donación
            if accion == 'Eliminar':
                donacion.eliminar_por_receptor()
            # Si el receptor decidió regresar la donación al menú de Consultar Donaciones (por error)
            elif accion == 'Regresar':
                donacion.regresar_a_consulta(
                    request.user,
                    comentario_feedback=comentario_feedback,
                )
            # Si el receptor guardó únicamente el motivo/feedback sin cambiar el estado
            elif accion == 'GuardarFeedback':
                donacion.aplicar_decision_receptor(
                    request.user,
                    nuevo_estado=None,
                    comentario_feedback=comentario_feedback,
                )
            # Si el receptor seleccionó Aceptar, Reservar o Rechazar la donación (o corrigió su estado)
            elif accion in ('Aceptado', 'Reservado', 'Rechazado', 'Recibido'):
                donacion.aplicar_decision_receptor(
                    request.user,
                    nuevo_estado=accion,
                    comentario_feedback=comentario_feedback,
                )


# Vista para consultar donaciones (Donante ve solo las suyas; Receptor ve todas las que están por atender)
@login_required
def consultarDonaciones(request):
    # Verifica si la vista se abre como Receptor o como Donante
    es_receptor = _es_rol_receptor(request)
    # Define la cadena del rol activo para mantenerla en los enlaces de paginación
    rol_actual = 'receptor' if es_receptor else 'donante'
    # Lee la categoría seleccionada en el filtro superior
    categoria_actual = request.GET.get('categoria') or request.POST.get('categoria') or 'TODAS'
    # Lee el número de página actual
    pagina_actual = request.GET.get('page') or request.POST.get('page') or 1

    # Procesa las acciones enviadas por método POST desde los formularios de la tabla
    if request.method == 'POST' and es_receptor:
        _procesar_accion_receptor(request)
        # Redirige a la misma página y categoría tras procesar la acción en Python
        return redirect(
            f"/alertas/consultarDonaciones/?rol={rol_actual}&categoria={categoria_actual}&page={pagina_actual}"
        )

    # Obtiene la lista de donaciones respetando el encapsulamiento del rol activo
    donaciones_filtradas, total_general = _obtener_lista_donaciones(
        request,
        modo='consulta',
        categoria=categoria_actual,
        es_receptor=es_receptor,
    )
    # Pagina los resultados de 5 en 5 usando Paginator de Django
    paginator = Paginator(donaciones_filtradas, 5)
    # Obtiene los registros correspondientes a la página solicitada
    page_obj = paginator.get_page(pagina_actual)

    # Renderiza la plantilla enviando el contexto procesado en Python
    return render(request, 'alertas/consultarDonaciones.html', {
        'donaciones': page_obj,
        'page_obj': page_obj,
        'total_registros': len(donaciones_filtradas),
        'total_general': total_general,
        'categoria_actual': categoria_actual,
        'rol_actual': rol_actual,
        'es_receptor': es_receptor,
    })


# Vista de Historial exclusivo y encapsulado para la cuenta del Receptor autenticada
@login_required
def historialDonaciones(request):
    # Sincroniza el rol activo como receptor
    es_receptor = _es_rol_receptor(request)
    # Un donante no tiene acceso al historial de receptores
    if not es_receptor:
        return redirect('/alertas/consultarDonaciones/?rol=donante')
    # Define la etiqueta de rol para conservarla en la navegación
    rol_actual = 'receptor' if es_receptor else 'donante'
    # Obtiene la categoría filtrada por GET o POST
    categoria_actual = request.GET.get('categoria') or request.POST.get('categoria') or 'TODAS'
    # Obtiene el número de página actual por GET o POST
    pagina_actual = request.GET.get('page') or request.POST.get('page') or 1

    # Permite al receptor corregir estado, editar comentarios o regresar la donación a Consultar Donaciones
    if request.method == 'POST' and es_receptor:
        _procesar_accion_receptor(request)
        return redirect(
            f"/alertas/historialDonaciones/?rol={rol_actual}&categoria={categoria_actual}&page={pagina_actual}"
        )

    # Consulta únicamente el historial de donaciones aceptadas, rechazadas o reservadas por este receptor
    donaciones_filtradas, total_general = _obtener_lista_donaciones(
        request,
        modo='historial',
        categoria=categoria_actual,
        es_receptor=True,
    )
    # Divide el historial en páginas de 5 registros con Django Paginator
    paginator = Paginator(donaciones_filtradas, 5)
    # Obtiene la página solicitada
    page_obj = paginator.get_page(pagina_actual)

    # Renderiza la plantilla de historial con sus datos encapsulados
    return render(request, 'alertas/historialDonaciones.html', {
        'donaciones': page_obj,
        'page_obj': page_obj,
        'total_registros': len(donaciones_filtradas),
        'total_general': total_general,
        'categoria_actual': categoria_actual,
        'rol_actual': rol_actual,
        'es_receptor': es_receptor,
    })


# Vista que procesa en Python el registro de nuevas donaciones, sus datos de logística y su evidencia fotográfica
@login_required
def cargarDonaciones(request):
    # Un receptor no puede subir donaciones desde el flujo de donante
    if hasattr(request.user, 'receptor'):
        return redirect('dashboardReceptor')
    # Fija el rol en sesión como donante al abrir el formulario de carga
    request.session['rol_activo'] = 'donante'

    # Bloqueo del commit 67de301: exige que el donante complete su perfil antes de subir una donación
    if request.user.is_authenticated and hasattr(request.user, 'donante'):
        perfil = request.user.donante
        if not perfil.nombre_local or not perfil.telefono or not perfil.direccion:
            messages.warning(
                request,
                "Para subir una donación, primero debes completar tu Nombre/Razón Social, Teléfono y Dirección.",
            )
            return redirect('perfil')

    # Si el formulario fue enviado mediante POST
    if request.method == 'POST':
        # Obtiene el nombre o descripción del contenido (soporta ambos nombres de campo por compatibilidad)
        titulo = (
            request.POST.get('descripcion_contenido')
            or request.POST.get('titulo')
            or ''
        ).strip()
        # Obtiene la categoría seleccionada (soporta el campo de 67de301 y el anterior)
        clasificacion = (
            request.POST.get('tipo_de_categoria_comida')
            or request.POST.get('clasificacion')
            or 'OTRO'
        ).strip() or 'OTRO'
        # Obtiene el tipo de conservación o lo deduce automáticamente según la categoría
        tipo = request.POST.get('tipo', '').strip()
        if not tipo:
            if clasificacion == 'AGUA_EMBOTELLADA':
                tipo = 'BEBIDA'
            elif clasificacion == 'COMIDA_PREPARADA':
                tipo = 'PREPARADO'
            elif clasificacion in ('FRUTAS_VERDURAS', 'LACTEOS', 'PROTEINAS_CARNES', 'PANADERIA'):
                tipo = 'PERECEDERO'
            else:
                tipo = 'NO_PERECEDERO'

        # Obtiene la cantidad numérica y la unidad de medida (soporta formulario de 67de301 y anterior)
        num_cantidad = (
            request.POST.get('numero_cantidad')
            or request.POST.get('num_cantidad')
            or ''
        ).strip()
        txt_unidad = (
            request.POST.get('tipo_de_unidad_medida')
            or request.POST.get('txt_unidad')
            or ''
        ).strip()
        cantidad_directa = request.POST.get('cantidad', '').strip()

        # Construye la cantidad legible evitando duplicar la unidad
        if num_cantidad:
            if txt_unidad and txt_unidad.lower() not in num_cantidad.lower():
                cantidad_txt = f"{num_cantidad} {txt_unidad}"
            else:
                cantidad_txt = num_cantidad
        else:
            cantidad_txt = cantidad_directa or '1 unidad'

        # Obtiene fecha de caducidad, datos de contacto y logística de entrega (commit 67de301)
        fecha_caducidad = request.POST.get('fecha_caducidad') or None
        tipo_de_conservacion = request.POST.get('tipo_de_conservacion', '').strip()
        descripcion = (request.POST.get('descripcion') or tipo_de_conservacion or titulo).strip()
        telefono = request.POST.get('telefono', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        nombre_donante_form = request.POST.get('nombre_donante', '').strip()
        metodo_entrega = request.POST.get('metodo_entrega', 'A_CONVENIR').strip()
        fecha_entrega = request.POST.get('fecha_entrega') or None
        hora_desde = request.POST.get('hora_desde') or None
        hora_hasta = request.POST.get('hora_hasta') or None
        notas_entrega = request.POST.get('notas_entrega', '').strip()
        declaracion = request.POST.get('declaracion') in ('on', 'si', 'True', 'true')
        requiere_frio = tipo_de_conservacion in ('REFRIGERADO', 'CONGELADO')

        # Extrae la parte numérica de la cantidad para cálculos de inventario y peso
        match_num = re.search(r'(\d+(?:\.\d+)?)', cantidad_txt)
        cantidad_num = float(match_num.group(1)) if match_num else 1.0

        # Recupera la fotografía subida (soporta el input de 67de301 y el anterior)
        evidencia_data_uri = ''
        archivo_imagen = request.FILES.get('imagen_evidencia_donacion') or request.FILES.get('imagen')
        if archivo_imagen:
            # Genera respaldo en Base64 para el modal rápido de la tabla sin perder el archivo original
            mime_type = archivo_imagen.content_type or 'image/jpeg'
            b64_contenido = base64.b64encode(archivo_imagen.read()).decode('ascii')
            evidencia_data_uri = f"data:{mime_type};base64,{b64_contenido}"
            # Rebobina el puntero del archivo para que Django pueda guardarlo en ImageField
            archivo_imagen.seek(0)

        # Obtiene el centro de acopio principal y la categoría correspondiente
        centro = CentroAcopio.objects.first()
        categoria = CategoriaAlimento.objects.filter(clave=clasificacion).first()

        # Crea el registro del alimento en el inventario del centro de acopio
        alimento = Alimento.objects.create(
            nombre=titulo,
            categoria=categoria,
            clasificacion=clasificacion,
            tipo=tipo,
            cantidad=cantidad_num,
            peso_unitario_kg=1.0,
            fecha_caducidad=fecha_caducidad,
            requiere_refrigeracion=requiere_frio,
            estado='DISPONIBLE',
            descripcion=descripcion,
            centro_acopio=centro,
        )

        # Obtiene el perfil Donante y define el nombre visible del donante
        donante_obj = getattr(request.user, 'donante', None) if request.user.is_authenticated else None
        nombre_donante = (
            nombre_donante_form
            or (donante_obj.nombre_local if donante_obj and donante_obj.nombre_local else None)
            or (request.user.username if request.user.is_authenticated else 'Donante Directo')
        )

        # Crea la donación encapsulada al Donante (receptor queda vacío hasta ser atendida) con todos los campos de 67de301
        nueva_donacion = Donacion.objects.create(
            donante=donante_obj,
            usuario_donante=request.user if request.user.is_authenticated else None,
            nombre_donante=nombre_donante,
            receptor=None,
            usuario_receptor=None,
            centro_acopio=centro,
            alimento=alimento,
            cantidad=cantidad_txt,
            peso_kg=cantidad_num,
            tipo=tipo,
            estado='Recibido',
            direccion_entrega=direccion,
            evidencia_imagen=evidencia_data_uri,
            fecha_caducidad=fecha_caducidad,
            descripcion=descripcion,
            telefono_contacto=telefono,
            tipo_conservacion=tipo_de_conservacion,
            requiere_refrigeracion=requiere_frio,
            metodo_envio=metodo_entrega,
            fecha_entrega=fecha_entrega,
            hora_desde=hora_desde,
            hora_hasta=hora_hasta,
            notas_entrega=notas_entrega,
            imagen_evidencia=archivo_imagen,
            declaracion_aceptada=declaracion,
        )

        # Registra el movimiento de entrada en la bitácora del inventario
        MovimientoInventario.objects.create(
            alimento=alimento,
            centro_acopio=centro,
            tipo_movimiento='ENTRADA',
            cantidad=cantidad_num,
            responsable=request.user if request.user.is_authenticated else None,
            motivo='Registro desde formulario de Nueva Donación',
        )

        # Genera las notificaciones para el donante y para los receptores (incluyendo alerta de alto riesgo)
        notificar_donacion_registrada(nueva_donacion)

        # Redirige a Mis Donaciones para que el donante vea reflejada su entrega
        return redirect('/alertas/consultarDonaciones/?rol=donante')

    # Prellena los datos del donante en GET usando su perfil (lógica del commit 67de301)
    datos_donante = {
        'nombre': '',
        'telefono': '',
        'direccion': '',
    }
    if request.user.is_authenticated and hasattr(request.user, 'donante'):
        perfil = request.user.donante
        datos_donante['nombre'] = perfil.nombre_local or request.user.username
        datos_donante['telefono'] = getattr(perfil, 'telefono', '')
        datos_donante['direccion'] = getattr(perfil, 'direccion', '')

    # Muestra el formulario de carga con los datos prellenados
    return render(request, 'alertas/cargarDonaciones.html', {'datos': datos_donante})


# Protege la vista para que solo usuarios con sesión iniciada puedan ver y gestionar sus notificaciones
@login_required
def mis_notificaciones(request):
    """
    Muestra la vista de la tabla completa de notificaciones del usuario actual
    y procesa las acciones POST para marcar una o todas las notificaciones como leídas.
    """
    # Si el usuario presionó un botón de acción (marcar leída o marcar todas)
    if request.method == 'POST':
        # Obtiene el tipo de acción enviado por el formulario oculto
        accion = request.POST.get('accion', '').strip()
        # Si solicitó marcar todas sus notificaciones pendientes como leídas
        if accion == 'marcar_todas':
            Notificacion.objects.filter(destiny=request.user, read=False).update(read=True)
        # Si solicitó marcar como leída una notificación individual
        elif accion == 'marcar_leida':
            # Lee el identificador de la notificación seleccionada
            notif_id = request.POST.get('notif_id')
            # Actualiza solo si pertenece al usuario autenticado (encapsulamiento)
            if notif_id:
                Notificacion.objects.filter(pk=notif_id, destiny=request.user).update(read=True)
        # Redirige a la misma vista para reflejar los cambios y evitar reenvío del formulario
        return redirect('mis_notificaciones')

    # Obtiene únicamente las notificaciones dirigidas al usuario en sesión
    notificaciones = Notificacion.objects.filter(destiny=request.user)

    # Filtra por rol real de la cuenta (incluyendo 'general') para mantener coherencia con la campanita
    if hasattr(request.user, 'donante'):
        notificaciones = notificaciones.filter(rol_destino__in=['donante', 'general'])
    elif hasattr(request.user, 'receptor'):
        notificaciones = notificaciones.filter(rol_destino__in=['receptor', 'general'])

    # Contexto enviado al template de la tabla completa (que hereda de users/dashboard.html)
    contexto = {
        'notificaciones': notificaciones,
    }
    return render(request, 'alertas/mis_notificaciones.html', contexto)