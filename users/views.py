# Importa el módulo csv para la generación de reportes descargables
import csv
# Importa la función de agregación Sum para sumar el peso de las donaciones
from django.db.models import Sum
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


# Gestiona el registro de nuevas cuentas de usuario como Donante o Receptor
def Sing_up(request):
    # Si se envió el formulario de registro por POST
    if request.method == 'POST':
        # Captura los datos ingresados por el usuario
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm = request.POST['confirm_password']
        tipo = request.POST['UserTypes']

        # Verifica que ambas contraseñas coincidan
        if password != confirm:
            messages.error(request, 'Las contraseñas no coinciden')
            return render(request, 'users/Sing_up.html')

        # Verifica que el nombre de usuario no esté duplicado
        if Usuario.objects.filter(username=username).exists():
            messages.error(request, 'Ese usuario ya existe')
            return render(request, 'users/Sing_up.html')

        # Selecciona la clase Donante o Receptor según el rol elegido
        Modelo = Donante if tipo == 'Donante' else Receptor
        # Instancia el nuevo usuario con su nombre y correo
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

# Verifica que telefono, dirección y razon social del usuario esten completos
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

    # Reúne los datos obligatorios para poder subir formularios
    datos = [usuario.telefono, usuario.direccion]
    # Si el rol tiene razón social, la incluye en la validación
    if campo:
        datos.append(getattr(usuario, campo))
    # Retorna True únicamente si ningún dato está vacío
    return all(dato and dato.strip() for dato in datos)


# Permite visualizar y actualizar los datos del perfil del usuario autenticado
@login_required
def perfil(request):

    # Obtiene la instancia del usuario en sesión
    usuario = request.user
    # Variable para identificar el campo de razón social según el rol
    campo_razon = None
    # Si es Donante, usa el campo nombre_local
    if hasattr(usuario, 'donante'):
        usuario = usuario.donante
        campo_razon = 'nombre_local'
    # Si es Receptor, usa el campo nombre_org
    elif hasattr(usuario, 'receptor'):
        usuario = usuario.receptor
        campo_razon = 'nombre_org'

    # Si se enviaron cambios por POST, actualiza teléfono, dirección y razón social
    if request.method == 'POST':
        usuario.telefono = request.POST.get('telefono', '')
        usuario.direccion = request.POST.get('direccion', '')
        if campo_razon:
            setattr(usuario, campo_razon, request.POST.get('razon_social', ''))
        usuario.save()
        messages.success(request, 'Perfil actualizado')
        return redirect('perfil')

    # Obtiene el valor actual de la razón social para mostrarlo en el formulario
    razon_social = getattr(usuario, campo_razon, '') if campo_razon else ''
    # Renderiza la vista de perfil indicando si aún falta completar datos obligatorios
    return render(request, 'users/perfil.html', {
        'razon_social': razon_social,
        'perfil_incompleto': not perfil_completo(request.user),
    })


# Exporta el informe de donaciones respetando el encapsulamiento del usuario en sesión
@login_required
def exportar_informe(request):
    # Obtiene el formato deseado (csv o pdf)
    formato = request.GET.get('formato', 'csv')
    # Determina si el usuario actual exporta como Receptor o como Donante respetando su rol real
    es_receptor = hasattr(request.user, 'receptor') or (
        not hasattr(request.user, 'donante') and request.session.get('rol_activo') == 'receptor'
    )

    # Obtiene las donaciones correspondientes al rol encapsulado del usuario
    if es_receptor:
        donaciones_qs = request.user.obtener_donaciones_para_receptor()
    else:
        donaciones_qs = request.user.obtener_mis_donaciones()

    # Prepara las filas del reporte
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

    # Si el formato elegido es PDF, construye el documento PDF en binario
    if formato == 'pdf':
        lineas = [
            "REPORTE DE INVENTARIO - HAMBRE CERO",
            "----------------------------------------------------------------",
            "ALIMENTO           CANTIDAD     TIPO            CADUCIDAD     ESTADO",
            "------------------------------------------------------------------",
        ]
        for r in registros:
            nombre_corto = (r[0][:16] + '..') if len(r[0]) > 18 else r[0]
            cant_corta = (r[1][:10] + '..') if len(r[1]) > 12 else r[1]
            lineas.append(f"{nombre_corto:<18} {cant_corta:<12} {r[2]:<15} {r[3]:<13} {r[4]}")

        contenido_stream = "BT /F1 10 Tf 40 750 Td 16 TL "
        for linea in lineas:
            texto_limpio = (
                linea.encode('latin-1', errors='replace').decode('latin-1')
                .replace("(", "\\(")
                .replace(")", "\\)")
            )
            contenido_stream += f"({texto_limpio}) Tj T* "
        contenido_stream += "ET"
        stream_bytes = contenido_stream.encode('latin-1', errors='replace')

        objetos = [
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n",
            b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
            f"5 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode('latin-1') + stream_bytes + b"\nendstream\nendobj\n"
        ]

        pdf = b"%PDF-1.4\n"
        offsets = []
        for obj in objetos:
            offsets.append(len(pdf))
            pdf += obj

        xref_offset = len(pdf)
        pdf += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode('latin-1')
        for off in offsets:
            pdf += f"{off:010d} 00000 n \n".encode('latin-1')
        pdf += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode('latin-1')

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="informe_donaciones.pdf"'
        return response

    # Genera la respuesta en formato CSV compatible con Excel
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="informe_donaciones.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(['Alimento', 'Cantidad', 'Tipo', 'Caducidad', 'Estado'])
    for r in registros:
        writer.writerow(r)

    return response
