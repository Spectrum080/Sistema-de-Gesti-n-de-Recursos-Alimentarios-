# Importa el módulo csv para la generación de reportes descargables
import csv
# Importa timedelta para filtrar donaciones por periodo (último día / última semana)
from datetime import timedelta
# Importa la función de agregación Sum y consultas Q
from django.db.models import Sum, Q
# Importa utilidades de zona horaria de Django
from django.utils import timezone
# Importa HttpResponse para devolver archivos PDF y CSV al navegador
from django.http import HttpResponse
# Importa funciones para renderizar plantillas y redirigir rutas
from django.shortcuts import render, redirect
# Importa el sistema de mensajes de Django para notificaciones de usuario
from django.contrib import messages
# Importa el decorador que protege vistas exclusivas para usuarios autenticados
from django.contrib.auth.decorators import login_required
# Importa los modelos de usuarios y roles
from .models import Usuario, Donante, Receptor
# Importa los generadores de PDF formales para Donante y Receptor
from .pdf_utils import generar_pdf_donante, generar_pdf_receptor
# Importa validadores estrictos y sanitización de entradas
from .validators import (
    limpiar_texto_seguro,
    validar_correo_estricto,
    validar_direccion,
    validar_razon_social,
    validar_telefono,
)
# Importa el modelo Notificacion para consultar alertas pendientes
from alertas.models import Notificacion


# Calcula las métricas del dashboard respetando el encapsulamiento del rol activo
def _obtener_contexto_dashboard(request, es_receptor=False):
    # Si el usuario está en modo Receptor, contabiliza todas las donaciones visibles en acopio
    if es_receptor:
        donaciones_qs = request.user.obtener_donaciones_para_receptor()
    # Si el usuario está en modo Donante, contabiliza únicamente sus propias entregas
    else:
        donaciones_qs = request.user.obtener_mis_donaciones()

    pendientes_qs = Notificacion.objects.filter(
        destiny=request.user,
        read=False,
    )
    # Cuenta el total de donaciones correspondientes al rol
    total_donaciones = donaciones_qs.count()
    # Suma el peso en kilogramos de dichas donaciones
    suma_peso = donaciones_qs.aggregate(total=Sum('peso_kg'))['total'] or 0
    # Da formato legible al peso acumulado en KG
    peso_formateado = f"{float(suma_peso):,.1f} KG".replace('.0 KG', ' KG')

    # Retorna el diccionario de contexto para la plantilla del dashboard
    return {
        'total_donaciones': total_donaciones,
        'peso_total': peso_formateado,
        'estatus': 'ACTIVO' if total_donaciones > 0 else 'SIN REGISTROS',
        'donaciones': donaciones_qs,
        'es_receptor': es_receptor,
    }


# Redirige al panel correspondiente según el tipo de cuenta del usuario autenticado
@login_required
def dashboard(request):
    # Si el usuario tiene perfil de Donante, activa el rol donante y redirige a su panel
    if hasattr(request.user, 'donante'):
        request.session['rol_activo'] = 'donante'
        return redirect('dashboardDonante')
    # Si el usuario tiene perfil de Receptor, activa el rol receptor y redirige a su panel
    elif hasattr(request.user, 'receptor'):
        request.session['rol_activo'] = 'receptor'
        return redirect('dashboardReceptor')
    # Si la sesión actual estaba en modo receptor, mantiene ese panel
    elif request.session.get('rol_activo') == 'receptor':
        return redirect('dashboardReceptor')
    # Por defecto muestra el dashboard en modo donante con sus métricas encapsuladas
    else:
        request.session['rol_activo'] = 'donante'
        context = _obtener_contexto_dashboard(request, es_receptor=False)
        return render(request, 'users/dashboard.html', context)


# Renderiza el panel exclusivo del Donante con las métricas de sus propias entregas
@login_required
def dashboardDonante(request):
    # Verifica si la cuenta es de tipo Receptor para impedir que entre al panel de Donante
    if hasattr(request.user, 'receptor'):
        # Redirige automáticamente al panel correspondiente de Receptor
        return redirect('dashboardReceptor')
    # Establece el rol activo en sesión como donante
    request.session['rol_activo'] = 'donante'
    # Obtiene las métricas encapsuladas únicamente para este donante
    context = _obtener_contexto_dashboard(request, es_receptor=False)
    # Renderiza la plantilla que hereda de dashboard.html
    return render(request, 'users/dashboardDonante.html', context)


# Renderiza el panel exclusivo del Receptor con las métricas del centro de acopio
@login_required
def dashboardReceptor(request):
    # Verifica si la cuenta es de tipo Donante para impedir que entre al panel de Receptor
    if hasattr(request.user, 'donante'):
        # Redirige automáticamente al panel correspondiente de Donante
        return redirect('dashboardDonante')
    # Establece el rol activo en sesión como receptor
    request.session['rol_activo'] = 'receptor'
    # Obtiene las métricas encapsuladas para el receptor
    context = _obtener_contexto_dashboard(request, es_receptor=True)
    # Renderiza la plantilla que hereda de dashboard.html
    return render(request, 'users/dashboardReceptor.html', context)


# Gestiona el registro de nuevas cuentas de usuario como Donante o Receptor con validación estricta
def Sing_up(request):
    # Si se envió el formulario de registro por POST
    if request.method == 'POST':
        # Captura y limpia los datos ingresados por el usuario
        username = limpiar_texto_seguro(request.POST.get('username', ''), max_len=150)
        email_raw = request.POST.get('email', '')
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')
        tipo = request.POST.get('UserTypes', '').strip()
        form_data = {'username': username, 'email': email_raw.strip(), 'UserTypes': tipo}

        # Valida nombre de usuario
        if len(username) < 3:
            messages.error(request, 'El nombre de usuario debe tener al menos 3 caracteres.')
            return render(request, 'users/Sing_up.html', {'form_data': form_data})

        # Valida formato sintáctico y dominio semántico del correo (bloquea typos como 'gmai.com')
        email, err_email = validar_correo_estricto(email_raw)
        if err_email:
            messages.error(request, err_email)
            return render(request, 'users/Sing_up.html', {'form_data': form_data})

        # Verifica que ambas contraseñas coincidan y tengan longitud mínima
        if password != confirm:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'users/Sing_up.html', {'form_data': form_data})
        if len(password) < 6:
            messages.error(request, 'La contraseña debe tener al menos 6 caracteres.')
            return render(request, 'users/Sing_up.html', {'form_data': form_data})

        # Valida tipo de usuario permitido
        if tipo not in ('Donante', 'Receptor'):
            messages.error(request, 'Selecciona un tipo de usuario válido (Donante o Receptor).')
            return render(request, 'users/Sing_up.html', {'form_data': form_data})

        # Verifica que el nombre de usuario y correo no estén duplicados
        if Usuario.objects.filter(username__iexact=username).exists():
            messages.error(request, 'Ese nombre de usuario ya existe.')
            return render(request, 'users/Sing_up.html', {'form_data': form_data})
        if Usuario.objects.filter(email__iexact=email).exists():
            messages.error(request, 'Ese correo electrónico ya está registrado.')
            return render(request, 'users/Sing_up.html', {'form_data': form_data})

        # Selecciona la clase Donante o Receptor según el rol elegido
        Modelo = Donante if tipo == 'Donante' else Receptor
        # Instancia el nuevo usuario con su nombre y correo normalizado
        user = Modelo(username=username, email=email)
        # Encripta la contraseña de forma segura
        user.set_password(password)
        # Guarda el usuario en la base de datos
        user.save()

        # Redirige a la pantalla de inicio de sesión
        return redirect('login')

    # Si es petición GET, muestra el formulario de registro
    return render(request, 'users/Sing_up.html')


# Muestra la pantalla de recuperación de contraseña
def reset_password(request):
    # Renderiza la plantilla informativa
    return render(request, 'users/reset_password.html')


# Guarda las preferencias de accesibilidad y apariencia en la sesión del usuario
@login_required
def configuracion(request):
    # Si el usuario guardó cambios mediante POST
    if request.method == 'POST':
        # Actualiza el estado del modo oscuro
        request.session['tema_oscuro'] = request.POST.get('tema_oscuro') == 'on'
        # Actualiza el estado de bordes de alto contraste
        request.session['alto_contraste'] = request.POST.get('alto_contraste') == 'on'
        # Actualiza la escala del tamaño de fuente
        request.session['tamano_fuente'] = request.POST.get('tamano_fuente', '100%')
        # Actualiza las notificaciones de caducidad
        request.session['notif_caducidad'] = request.POST.get('notif_caducidad') == 'on'

        # Marca la sesión como modificada
        request.session.modified = True
        # Redirige de vuelta a configuración
        return redirect('configuracion')

    # Muestra la plantilla de configuración
    return render(request, 'users/configuracion.html')

# Verifica que telefono, dirección y razon social del usuario estén completos Y tengan formato válido
def perfil_completo(user):
    # Por defecto evalua al usuario base, por ejemplo un Administrador
    usuario = user
    # Variable para identificar el campo de razón social segun el rol
    campo = None
    # Si es Donante, evalua su registro propio y el campo nombre_local
    if hasattr(user, 'donante'):
        usuario = user.donante
        campo = 'nombre_local'
    # Si es Receptor, evalúa su registro propio y el campo nombre_org
    elif hasattr(user, 'receptor'):
        usuario = user.receptor
        campo = 'nombre_org'

    # Valida formato real de teléfono y dirección (no permite datos corruptos o basura)
    _, err_tel = validar_telefono(usuario.telefono)
    _, err_dir = validar_direccion(usuario.direccion)
    if err_tel or err_dir:
        return False
    # Si el rol tiene razón social/organización, también verifica que sea válida
    if campo:
        _, err_razon = validar_razon_social(getattr(usuario, campo, ''))
        if err_razon:
            return False
    return True


# Permite visualizar y actualizar los datos del perfil del usuario autenticado con validación estricta
@login_required
def perfil(request):
    # Obtiene la instancia del usuario en sesión
    usuario = request.user
    # Variable para identificar el campo de razón social según el rol
    campo_razon = None
    etiqueta_razon = 'Nombre / Razón Social'
    # Si es Donante, usa el campo nombre_local
    if hasattr(usuario, 'donante'):
        usuario = usuario.donante
        campo_razon = 'nombre_local'
        etiqueta_razon = 'Nombre del Local / Razón Social'
    # Si es Receptor, usa el campo nombre_org
    elif hasattr(usuario, 'receptor'):
        usuario = usuario.receptor
        campo_razon = 'nombre_org'
        etiqueta_razon = 'Nombre de la Organización'

    # Si se enviaron cambios por POST, valida y sanitiza todos los campos antes de persistir
    if request.method == 'POST':
        raw_tel = request.POST.get('telefono', '')
        raw_dir = request.POST.get('direccion', '')
        raw_razon = request.POST.get('razon_social', '')

        errores = []
        tel_limpio, err_tel = validar_telefono(raw_tel)
        if err_tel:
            errores.append(err_tel)

        dir_limpia, err_dir = validar_direccion(raw_dir)
        if err_dir:
            errores.append(err_dir)

        razon_limpia = ''
        if campo_razon:
            razon_limpia, err_razon = validar_razon_social(raw_razon, etiqueta=etiqueta_razon)
            if err_razon:
                errores.append(err_razon)

        # Si hay errores, NO guarda en base de datos y muestra cada error al usuario
        if errores:
            for err in errores:
                messages.error(request, err)
            return render(request, 'users/perfil.html', {
                'razon_social': raw_razon.strip(),
                'telefono_valor': raw_tel.strip(),
                'direccion_valor': raw_dir.strip(),
                'perfil_incompleto': not perfil_completo(request.user),
            })

        # Guarda únicamente datos validados y sanitizados
        usuario.telefono = tel_limpio
        usuario.direccion = dir_limpia
        if campo_razon:
            setattr(usuario, campo_razon, razon_limpia)
        usuario.save()
        messages.success(request, 'Perfil actualizado correctamente.')
        return redirect('perfil')

    # Obtiene el valor actual de los campos para mostrarlos en el formulario
    razon_social = getattr(usuario, campo_razon, '') if campo_razon else ''
    # Renderiza la vista de perfil indicando si aún falta completar datos obligatorios válidos
    return render(request, 'users/perfil.html', {
        'razon_social': razon_social,
        'telefono_valor': usuario.telefono,
        'direccion_valor': usuario.direccion,
        'perfil_incompleto': not perfil_completo(request.user),
    })


# Exporta el informe de donaciones respetando el encapsulamiento y el periodo elegido (todas, semana, dia)
@login_required
def exportar_informe(request):
    # Obtiene el formato deseado (pdf o csv) y el periodo seleccionado
    formato = request.GET.get('formato', 'pdf')
    periodo = request.GET.get('periodo', 'todas')
    # Determina si el usuario actual exporta como Receptor o como Donante respetando su rol real
    es_receptor = hasattr(request.user, 'receptor') or (
        not hasattr(request.user, 'donante') and request.session.get('rol_activo') == 'receptor'
    )

    # Obtiene las donaciones encapsuladas: para Receptor su historial de trabajo; para Donante sus entregas
    if es_receptor:
        donaciones_qs = request.user.obtener_mi_historial_receptor()
    else:
        donaciones_qs = request.user.obtener_mis_donaciones()

    # Aplica el filtro de periodo (último 1 día o última semana)
    ahora = timezone.now()
    if periodo == 'dia':
        limite = ahora - timedelta(days=1)
    elif periodo == 'semana':
        limite = ahora - timedelta(days=7)
    else:
        limite = None

    if limite is not None:
        if es_receptor:
            # Para el receptor filtra por fecha en que gestionó la donación (o fecha de registro si falta)
            donaciones_qs = donaciones_qs.filter(
                Q(fecha_recepcion__gte=limite)
                | Q(fecha_recepcion__isnull=True, fecha_registro__gte=limite)
            )
        else:
            donaciones_qs = donaciones_qs.filter(fecha_registro__gte=limite)

    # Si el formato elegido es PDF, genera la plantilla formal correspondiente a cada rol
    if formato == 'pdf':
        if es_receptor:
            pdf_bytes = generar_pdf_receptor(request.user, donaciones_qs, periodo=periodo)
            nombre_archivo = f"informe_gestion_receptor_{periodo}.pdf"
        else:
            pdf_bytes = generar_pdf_donante(request.user, donaciones_qs, periodo=periodo)
            nombre_archivo = f"recibo_donacion_hambre_cero_{periodo}.pdf"

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
        return response

    # Prepara las filas del reporte CSV
    registros = []
    for d in donaciones_qs:
        caducidad_str = (
            d.fecha_caducidad.strftime('%d/%m/%Y')
            if d.fecha_caducidad
            else (
                d.alimento.fecha_caducidad.strftime('%d/%m/%Y')
                if d.alimento and d.alimento.fecha_caducidad
                else 'N/A'
            )
        )
        registros.append([
            d.alimento.nombre if d.alimento else 'Alimento',
            d.cantidad,
            d.get_tipo_display(),
            caducidad_str,
            d.estado,
        ])

    # Genera la respuesta en formato CSV compatible con Excel
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="informe_donaciones_{periodo}.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(['Alimento', 'Cantidad', 'Tipo', 'Caducidad', 'Estado'])
    for r in registros:
        writer.writerow(r)

    return response
