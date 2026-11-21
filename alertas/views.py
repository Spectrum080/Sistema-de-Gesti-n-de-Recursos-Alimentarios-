import re  # Permite trabajar con expresiones regulares para buscar y validar patrones de texto.
from django.core.paginator import Paginator  # Divide los registros en páginas.
from django.shortcuts import render, redirect, get_object_or_404  # get_object_or_404: Busca un registro o devuelve un error 404.
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Donacion, Alimento, CategoriaAlimento, CentroAcopio, MovimientoInventario, Notificacion
from users.models import Donante, Receptor  # Importa los modelos de donantes y receptores.


# Detecta y sincroniza en sesión si la vista actual corresponde al rol Receptor o Donante
def _es_rol_receptor(request):
    rol_param = request.GET.get('rol') or request.POST.get('rol') # Obtiene el rol enviado mediante GET o POST.
    if rol_param in ('receptor', 'donante'): # Si el rol es válido, lo guarda en la sesión.
        request.session['rol_activo'] = rol_param
        request.session.modified = True 
    if rol_param == 'receptor': # Si el rol es receptor, devuelve True.
        return True
    if rol_param == 'donante': # Si el rol es donante, devuelve False.
        return False
    if request.user.is_authenticated and hasattr(request.user, 'receptor'): # Comprueba si el usuario autenticado tiene un perfil de receptor.
        return True
    if request.user.is_authenticated and hasattr(request.user, 'donante'): # Comprueba si el usuario autenticado tiene un perfil de donante.
        return False
    return request.session.get('rol_activo') == 'receptor' # Si no se encontró un rol, consulta el rol guardado en la sesión.


# Obtiene y filtra en Python las donaciones desde db.sqlite3 mostrando primero las nuevas
def _obtener_lista_donaciones(categoria='TODAS'):
    queryset = list( # Obtiene todas las donaciones junto con sus relaciones para evitar consultas adicionales.
        Donacion.objects.select_related(
            'alimento', 'donante', 'receptor', 'centro_acopio'
        ).order_by('id')
    )
    nuevas = sorted([d for d in queryset if d.id > 13], key=lambda x: -x.id)  # Obtiene las donaciones nuevas (ID mayor a 13) y las ordena de más reciente a más antigua.
    base = [d for d in queryset if d.id <= 13] # Obtiene las donaciones antiguas (ID menor o igual a 13).
    ordenadas = nuevas + base # Coloca primero las donaciones nuevas y después las antiguas.
    total_general = len(ordenadas) # Cuenta el total de donaciones antes de aplicar filtros.

    donaciones = [] # Lista donde se almacenarán las donaciones filtradas y organizadas.
    for d in ordenadas: # Recorre cada donación.
        clave_cat = d.alimento.clasificacion if d.alimento else 'OTRO' # Obtiene la categoría del alimento; si no existe, asigna 'OTRO'.
        if categoria and categoria != 'TODAS' and clave_cat != categoria: # Si se seleccionó una categoría específica, descarta las demás.
            continue

        donante_txt = ( # Obtiene el nombre del donante según la información disponible.
            d.nombre_donante
            or (d.donante.nombre_local if d.donante and d.donante.nombre_local else None)
            or (d.donante.username if d.donante else 'Donante General')
        )
        caducidad_txt = ( # Obtiene la fecha de caducidad de la donación o del alimento.
            d.fecha_caducidad.strftime('%d/%m/%Y')
            if d.fecha_caducidad
            else (
                d.alimento.fecha_caducidad.strftime('%d/%m/%Y')
                if d.alimento and d.alimento.fecha_caducidad
                else 'No aplica'
            )
        )
        donaciones.append({
            'id': f"{d.id:03d}", # ID con tres dígitos.
            'raw_id': d.id, # ID original de la base de datos.
            'donante': donante_txt, # Nombre del donante.
            'alimento': d.alimento.nombre if d.alimento else 'Alimento', # Nombre del alimento.
            'clasificacion': d.alimento.get_clasificacion_display() if d.alimento else 'General', # Categoría visible.
            'clasificacion_clave': clave_cat, # Categoría original.
            'cantidad': d.cantidad, # Cantidad de alimentos.
            'peso': f"{float(d.peso_kg):g} kg" if d.peso_kg else '1 kg', # Peso en kilogramos.
            'tipo': d.get_tipo_display(), # Tipo de donación.
            'caducidad': caducidad_txt, # Fecha de caducidad.
            'ubicacion': d.alimento.ubicacion_almacen if d.alimento and d.alimento.ubicacion_almacen else 'Recepción Acopio', # Ubicación del alimento.
            'estado': d.estado, # Estado actual de la donación.
        })
    return donaciones, total_general # Devuelve la lista de donaciones y el total general.

def detalle_donacion(request, donacion_id):
    donacion = get_object_or_404(Donacion, id=donacion_id)
    context = {
        'donacion': donacion
    }
    return render(request, 'alertas/responderDonacion.html', context)

# Vista en Python: gestiona cambio de estado por POST, filtro por categoría y paginación con Paginator
def consultarDonaciones(request):
    es_receptor = _es_rol_receptor(request) # Detecta si el usuario es receptor o donante.
    rol_actual = 'receptor' if es_receptor else 'donante' # Guarda el rol actual como texto.
    categoria_actual = request.GET.get('categoria') or request.POST.get('categoria') or 'TODAS' # Obtiene la categoría seleccionada o utiliza 'TODAS' por defecto.
    pagina_actual = request.GET.get('page') or request.POST.get('page') or 1 # Obtiene el número de página actual.

    # Actualiza en BD el estado de la donación y del alimento (Aceptado, Reservado o Rechazado)
    if request.method == 'POST':
        donacion_id = request.POST.get('donacion_id') # Obtiene el ID de la donación que se quiere modificar.
        accion = (request.POST.get('nuevo_estado') or '').strip() # Obtiene la acción seleccionada y elimina espacios innecesarios.
        mapa_estados = { # Define los estados permitidos para las donaciones.
            'Aceptado': 'Aceptado',
            'Reservado': 'Reservado',
            'Rechazado': 'Rechazado',
            'Recibido': 'Recibido',
        }
        nuevo_estado = mapa_estados.get(accion) # Busca el nuevo estado correspondiente a la acción.
        if donacion_id and nuevo_estado: # Comprueba que exista un ID y un estado válido.
            donacion = get_object_or_404(Donacion.objects.select_related('alimento'), pk=donacion_id) # Busca la donación junto con su alimento o devuelve error 404.
            donacion.estado = nuevo_estado # Actualiza el estado de la donación.
            if nuevo_estado == 'Aceptado': # Si la donación fue aceptada, registra la fecha de recepción.
                donacion.fecha_recepcion = timezone.now()
                donacion.save(update_fields=['estado', 'fecha_recepcion']) # Guarda únicamente el estado y la fecha de recepción.
            else:
                donacion.save(update_fields=['estado']) # Guarda únicamente el nuevo estado.

            if donacion.alimento: # Comprueba si la donación tiene un alimento relacionado.
                if nuevo_estado == 'Aceptado':  # Si fue aceptada, marca el alimento como entregado.
                    donacion.alimento.estado = 'ENTREGADO'
                elif nuevo_estado == 'Reservado': # Si fue reservado, marca el alimento como reservado.
                    donacion.alimento.estado = 'RESERVADA'
                elif nuevo_estado == 'Rechazado': # Si fue rechazado, lo devuelve a revisión.
                    donacion.alimento.estado = 'EN_REVISION'
                donacion.alimento.save(update_fields=['estado']) # Guarda el nuevo estado del alimento.

        return redirect( # Redirige a la misma vista conservando el rol, categoría y página.
            f"/alertas/consultarDonaciones/?rol={rol_actual}&categoria={categoria_actual}&page={pagina_actual}"
        )

    donaciones_filtradas, total_general = _obtener_lista_donaciones(categoria=categoria_actual) # Obtiene las donaciones filtradas por la categoría seleccionada.
    paginator = Paginator(donaciones_filtradas, 5) # Divide las donaciones en páginas de 5 registros.
    page_obj = paginator.get_page(pagina_actual) # Obtiene la página solicitada.

    return render(request, 'alertas/consultarDonaciones.html', { # Renderiza la plantilla HTML y envía los datos necesarios.
        'donaciones': page_obj, # Donaciones correspondientes a la página actual.
        'page_obj': page_obj, # Información de paginación.
        'total_registros': len(donaciones_filtradas), # Total de donaciones filtradas.
        'total_general': total_general, # Total de donaciones sin filtrar.
        'categoria_actual': categoria_actual, # Categoría seleccionada.
        'rol_actual': rol_actual, # Rol del usuario.
        'es_receptor': es_receptor, # Indica si el usuario es receptor.
    })


# Muestra el historial paginado y filtrado 100% desde Python con Django Paginator
def historialDonaciones(request):
    es_receptor = _es_rol_receptor(request) # Detecta si el usuario es receptor o donante.
    rol_actual = 'receptor' if es_receptor else 'donante' # Guarda el rol actual del usuario.
    categoria_actual = request.GET.get('categoria', 'TODAS') # Obtiene la categoría seleccionada; por defecto muestra todas.
    pagina_actual = request.GET.get('page', 1) # Obtiene el número de página actual.

    donaciones_filtradas, total_general = _obtener_lista_donaciones(categoria=categoria_actual) # Obtiene las donaciones filtradas por la categoría seleccionada.
    paginator = Paginator(donaciones_filtradas, 5) # Divide las donaciones en páginas de 5 registros.
    page_obj = paginator.get_page(pagina_actual) # Obtiene los registros correspondientes a la página solicitada.

    return render(request, 'alertas/historialDonaciones.html', { # Renderiza la plantilla HTML y envía los datos necesarios.
        'donaciones': page_obj, # Lista de donaciones de la página actual.
        'page_obj': page_obj, # Información para controlar la paginación.
        'total_registros': len(donaciones_filtradas), # Total de donaciones filtradas.
        'total_general': total_general, # Total de donaciones sin filtros.
        'categoria_actual': categoria_actual, # Categoría seleccionada.
        'rol_actual': rol_actual, # Rol actual del usuario.
        'es_receptor': es_receptor, # Indica si el usuario es receptor.
    })


# Registra manualmente un nuevo alimento, su donación y el movimiento de entrada en inventario
def cargarDonaciones(request):
    request.session['rol_activo'] = 'donante' # Guarda el rol de donante en la sesión.
    if request.user.is_authenticated and hasattr(request.user, 'donante'): # Bloqueo si faltan datos en el perfil
        perfil = request.user.donante
        # Comprobamos si alguno de los 3 campos está vacío
        if not perfil.nombre_local or not perfil.telefono or not perfil.direccion:
            messages.warning(request, "Para subir una donación, primero debes completar tu Nombre/Razón Social, Teléfono y Dirección.")
            return redirect('perfil')

    if request.method == 'POST': 
        nombre_donante = request.POST.get('nombre_donante', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        categoria_form = request.POST.get('tipo_de_categoria_comida', 'OTRO') 
        numero_cantidad = request.POST.get('numero_cantidad', '').strip() 
        unidad = request.POST.get('tipo_de_unidad_medida', 'OTRO') 
        cantidad_txt = f"{numero_cantidad} {unidad}" 
        descripccion_contenido = request.POST.get('descripcion_contenido', '').strip() 
        fecha_caducidad = request.POST.get('fecha_caducidad') or None 
        tipo_de_conservacion = request.POST.get('tipo_de_conservacion', 'OTRO') 
        metodo_entrega = request.POST.get('metodo_entrega', 'A_CONVENIR') 
        fecha_entrega = request.POST.get('fecha_entrega') or None 
        hora_desde = request.POST.get('hora_desde') or None 
        hora_hasta = request.POST.get('hora_hasta') or None 
        notas_entrega = request.POST.get('notas_entrega', '').strip() 
        imagen_evidencia = request.FILES.get('imagen_evidencia_donacion') 
        declaracion = request.POST.get('declaracion') == 'on' or request.POST.get('declaracion') == 'si' 

        match_num = re.search(r'(\d+(?:\.\d+)?)', numero_cantidad) 
        cantidad_num = float(match_num.group(1)) if match_num else 1.0 

        centro = CentroAcopio.objects.first() 
        categoria_obj = CategoriaAlimento.objects.filter(clave=categoria_form).first()

        alimento = Alimento.objects.create( 
            nombre=descripccion_contenido,
            categoria=categoria_obj,
            clasificacion=categoria_form,
            tipo=categoria_form,
            cantidad=cantidad_num,
            peso_unitario_kg=1.0,
            fecha_caducidad=fecha_caducidad,
            estado='DISPONIBLE',
            descripcion=descripccion_contenido,
            centro_acopio=centro,
        )

        donante_obj = getattr(request.user, 'donante', None) if request.user.is_authenticated else Donante.objects.first() 
        nombre_donante_final = ( 
            (donante_obj.nombre_local or donante_obj.username)
            if donante_obj
            else (request.user.username if request.user.is_authenticated else nombre_donante)
        )

        # ¡AQUÍ ESTABA EL PROBLEMA! Faltaba agregar todos los campos extra que recibíamos del formulario
        Donacion.objects.create( 
            donante=donante_obj,
            nombre_donante=nombre_donante_final,
            receptor=Receptor.objects.first(),
            centro_acopio=centro,
            alimento=alimento,
            cantidad=cantidad_txt,
            peso_kg=cantidad_num,
            tipo=categoria_form,
            estado='Recibido',
            fecha_caducidad=fecha_caducidad,
            descripcion=descripccion_contenido,
            
            # --- NUEVOS CAMPOS AGREGADOS ---
            telefono_contacto=telefono,
            direccion_entrega=direccion,
            tipo_conservacion=tipo_de_conservacion,
            metodo_envio=metodo_entrega,
            fecha_entrega=fecha_entrega,
            hora_desde=hora_desde,
            hora_hasta=hora_hasta,
            notas_entrega=notas_entrega,
            imagen_evidencia=imagen_evidencia,
            declaracion_aceptada=declaracion
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

    # CÓDIGO PARA PRELLENAR EL FORMULARIO 
    datos_donante = {
        'nombre': '',
        'telefono': '',
        'direccion': ''
    }

    if request.user.is_authenticated and hasattr(request.user, 'donante'):
        perfil = request.user.donante
        datos_donante['nombre'] = perfil.nombre_local or request.user.username
        datos_donante['telefono'] = getattr(perfil, 'telefono', '') 
        datos_donante['direccion'] = getattr(perfil, 'direccion', '')

    return render(request, 'alertas/cargarDonaciones.html', {'datos': datos_donante})

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