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

from django.contrib.auth.decorators import login_required




# Función que determina y guarda en sesión si el usuario opera bajo el rol de Receptor o Donante
def _es_rol_receptor(request):
    # Obtiene el parámetro 'rol' enviado por GET o POST si existe
    rol_param = request.GET.get('rol') or request.POST.get('rol')
    # Si el parámetro es válido, actualiza la sesión activa del usuario
    if rol_param in ('receptor', 'donante'):
        # Guarda el rol activo en la sesión
        request.session['rol_activo'] = rol_param
        # Marca la sesión como modificada para que Django persista el cambio
        request.session.modified = True
    # Si el usuario pidió explícitamente vista de receptor, retorna verdadero
    if rol_param == 'receptor':
        return True
    # Si el usuario pidió explícitamente vista de donante, retorna falso
    if rol_param == 'donante':
        return False
    # Si el usuario autenticado pertenece a la clase Receptor, retorna verdadero
    if request.user.is_authenticated and hasattr(request.user, 'receptor'):
        return True
    # Si el usuario autenticado pertenece a la clase Donante, retorna falso
    if request.user.is_authenticated and hasattr(request.user, 'donante'):
        return False
    # En caso contrario, consulta el último rol guardado en la sesión
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
            'evidencia_imagen': d.evidencia_imagen,
        })
    # Retorna la lista filtrada y el conteo general
    return donaciones, total_general


# Vista para consultar donaciones (Donante ve las suyas; Receptor ve todas, cambia estado, da feedback y elimina)
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
        # Obtiene el identificador de la donación a modificar o eliminar
        donacion_id = request.POST.get('donacion_id')
        # Obtiene la acción solicitada (Aceptado, Reservado, Rechazado, GuardarFeedback o Eliminar)
        accion = (request.POST.get('nuevo_estado') or '').strip()
        # Obtiene el comentario de retroalimentación (feedback) escrito por el receptor
        comentario_feedback = request.POST.get('feedback')

        # Si se proporcionó un ID de donación válido, busca el registro en la base de datos
        if donacion_id:
            # Recupera la donación junto con su alimento asociado
            donacion = get_object_or_404(Donacion.objects.select_related('alimento'), pk=donacion_id)
            # Si el receptor presionó el botón para quitar/eliminar la donación
            if accion == 'Eliminar':
                # Ejecuta el método encapsulado que borra la donación de la base de datos
                donacion.eliminar_por_receptor()
            # Si el receptor guardó únicamente el motivo/feedback sin cambiar el estado
            elif accion == 'GuardarFeedback':
                # Guarda el feedback y vincula la gestión al receptor actual
                donacion.aplicar_decision_receptor(
                    request.user,
                    nuevo_estado=None,
                    comentario_feedback=comentario_feedback,
                )
            # Si el receptor seleccionó Aceptar, Reservar o Rechazar la donación
            elif accion in ('Aceptado', 'Reservado', 'Rechazado', 'Recibido'):
                # Ejecuta el método encapsulado que actualiza el estado, guarda el feedback y asigna el receptor
                donacion.aplicar_decision_receptor(
                    request.user,
                    nuevo_estado=accion,
                    comentario_feedback=comentario_feedback,
                )

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
def historialDonaciones(request):
    # Sincroniza el rol activo como receptor
    es_receptor = _es_rol_receptor(request)
    # Define la etiqueta de rol para conservarla en la navegación
    rol_actual = 'receptor' if es_receptor else 'donante'
    # Obtiene la categoría filtrada por GET
    categoria_actual = request.GET.get('categoria', 'TODAS')
    # Obtiene el número de página actual por GET
    pagina_actual = request.GET.get('page', 1)

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


# Vista que procesa en Python el registro de nuevas donaciones, su categoría y su evidencia fotográfica
def cargarDonaciones(request):
    # Fija el rol en sesión como donante al abrir el formulario de carga
    request.session['rol_activo'] = 'donante'
    # Si el formulario fue enviado mediante POST
    if request.method == 'POST':
        # Obtiene la descripción o nombre del alimento
        titulo = request.POST.get('titulo', '').strip()
        # Obtiene la categoría seleccionada (Agua Embotellada, Comida Enlatada, Frutas, etc.)
        clasificacion = request.POST.get('clasificacion', 'OTRO').strip() or 'OTRO'
        # Obtiene el tipo de conservación (Perecedero, No Perecedero, Preparado, Bebida)
        tipo = request.POST.get('tipo', '').strip()
        # Si no se especificó tipo manualmente, lo deduce en Python según la categoría escogida
        if not tipo:
            if clasificacion == 'AGUA_EMBOTELLADA':
                tipo = 'BEBIDA'
            elif clasificacion == 'COMIDA_PREPARADA':
                tipo = 'PREPARADO'
            elif clasificacion in ('FRUTAS_VERDURAS', 'LACTEOS', 'PROTEINAS_CARNES', 'PANADERIA'):
                tipo = 'PERECEDERO'
            else:
                tipo = 'NO_PERECEDERO'

        # Obtiene el valor escrito en el campo de cantidad
        num_cantidad = request.POST.get('num_cantidad', '').strip()
        # Obtiene el valor escrito en el campo de unidad
        txt_unidad = request.POST.get('txt_unidad', '').strip()
        # Obtiene el campo cantidad directo en caso de envío alternativo
        cantidad_directa = request.POST.get('cantidad', '').strip()

        # Une en Python la cantidad y la unidad evitando duplicar palabras si ya se incluyó la unidad
        if num_cantidad:
            if txt_unidad and txt_unidad.lower() not in num_cantidad.lower():
                cantidad_txt = f"{num_cantidad} {txt_unidad}"
            else:
                cantidad_txt = num_cantidad
        else:
            cantidad_txt = cantidad_directa or '1 unidad'

        # Obtiene la fecha de caducidad seleccionada
        fecha_caducidad = request.POST.get('fecha_caducidad') or None
        # Obtiene el requisito de conservación o detalles adicionales
        descripcion = request.POST.get('descripcion', '').strip()
        # Obtiene la dirección de recolección capturada
        direccion = request.POST.get('direccion', '').strip()
        # Obtiene el nombre o razón social capturada en el formulario
        nombre_donante_form = request.POST.get('nombre_donante', '').strip()

        # Extrae la parte numérica de la cantidad para cálculos de inventario y peso
        match_num = re.search(r'(\d+(?:\.\d+)?)', cantidad_txt)
        # Convierte el valor encontrado a flotante o asigna 1.0 por defecto
        cantidad_num = float(match_num.group(1)) if match_num else 1.0

        # Procesa en Python el archivo de imagen subido en el apartado de Evidencia Fotográfica
        evidencia_data_uri = ''
        # Recupera el archivo enviado desde el input file 'imagen'
        archivo_imagen = request.FILES.get('imagen')
        # Si el usuario adjuntó una imagen válida, la convierte a Data URI base64
        if archivo_imagen:
            # Determina el tipo MIME de la imagen (ej. image/jpeg, image/png)
            mime_type = archivo_imagen.content_type or 'image/jpeg'
            # Codifica los bytes de la imagen en texto base64
            b64_contenido = base64.b64encode(archivo_imagen.read()).decode('ascii')
            # Construye la cadena Data URI lista para mostrarse en la etiqueta img del modal
            evidencia_data_uri = f"data:{mime_type};base64,{b64_contenido}"

        # Obtiene el centro de acopio principal registrado
        centro = CentroAcopio.objects.first()
        # Busca en la base de datos la categoría correspondiente a la clave seleccionada
        categoria = CategoriaAlimento.objects.filter(clave=clasificacion).first()

        # Crea el registro del alimento en la base de datos con la categoría elegida
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

        # Obtiene el perfil Donante si el usuario autenticado cuenta con uno
        donante_obj = getattr(request.user, 'donante', None) if request.user.is_authenticated else None
        # Determina el nombre del donante priorizando lo escrito en el formulario o su usuario
        nombre_donante = (
            nombre_donante_form
            or (donante_obj.nombre_local if donante_obj and donante_obj.nombre_local else None)
            or (request.user.username if request.user.is_authenticated else 'Donante Directo')
        )

        # Crea la donación vinculada únicamente al usuario Donante que la subió (receptor queda vacío hasta ser gestionada)
        # Guarda la informacion de la donacion y envia una notificacion al Donante
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

        # Notifica al donante de la donacion registrada
        notificar_donacion_registrada(nueva_donacion)

        # Redirige a Mis Donaciones para que el donante vea reflejada su entrega con su categoría
        return redirect('/alertas/consultarDonaciones/?rol=donante')

    # Si la petición es GET, muestra el formulario para subir donación
    return render(request, 'alertas/cargarDonaciones.html')


@login_required
def mis_notificaciones(request):
    """
    Muestra la vista de la tabla completa de notificaciones del usuario actual.

    Filtra las notificaciones asignadas al usuario autenticado ordenadas
    de la más reciente a la más antigua (según Meta.ordering del modelo).
    """
    # Obtiene únicamente las notificaciones dirigidas al usuario en sesión
    notificaciones = Notificacion.objects.filter(destiny=request.user)

    # Contexto enviado al template de la tabla completa
    contexto = {
        'notificaciones': notificaciones,
    }
    return render(request, 'alertas/mis_notificaciones.html', contexto)