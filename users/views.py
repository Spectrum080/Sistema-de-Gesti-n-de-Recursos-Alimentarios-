import csv
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from alertas.models import Donacion, Alimento
from .models import Usuario, Donante, Receptor


# Calcula en tiempo real las métricas del dashboard (total de donaciones y peso en KG) desde db.sqlite3
def _obtener_contexto_dashboard():
    donaciones_qs = Donacion.objects.select_related(
        'alimento', 'donante', 'receptor', 'centro_acopio'
    ).all()
    total_donaciones = donaciones_qs.count()
    suma_peso = donaciones_qs.aggregate(total=Sum('peso_kg'))['total'] or 0
    peso_formateado = f"{float(suma_peso):,.1f} KG".replace('.0 KG', ' KG')

    return {
        'total_donaciones': total_donaciones,
        'peso_total': peso_formateado,
        'estatus': 'ACTIVO' if total_donaciones > 0 else 'SIN REGISTROS',
        'donaciones': donaciones_qs,
        'alimentos': Alimento.objects.select_related('categoria', 'centro_acopio').all(),
    }


# Redirige al panel correspondiente según el rol del usuario e inyecta las métricas reales
@login_required
def dashboard(request):
    if hasattr(request.user, 'donante'):
        request.session['rol_activo'] = 'donante'
        return redirect('dashboardDonante')
    elif hasattr(request.user, 'receptor'):
        request.session['rol_activo'] = 'receptor'
        return redirect('dashboardReceptor')
    elif request.session.get('rol_activo') == 'receptor':
        return redirect('dashboardReceptor')
    else:
        request.session['rol_activo'] = 'donante'
        context = _obtener_contexto_dashboard()
        return render(request, 'users/dashboard.html', context)


# Panel del Donante que hereda la estructura y métricas desde dashboard.html
@login_required
def dashboardDonante(request):
    request.session['rol_activo'] = 'donante'
    context = _obtener_contexto_dashboard()
    return render(request, 'users/dashboardDonante.html', context)


# Panel del Receptor que hereda la estructura y métricas desde dashboard.html
@login_required
def dashboardReceptor(request):
    request.session['rol_activo'] = 'receptor'
    context = _obtener_contexto_dashboard()
    return render(request, 'users/dashboardReceptor.html', context)


# Registro de nuevos usuarios asignando el modelo Donante o Receptor según selección
def Sing_up(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm = request.POST['confirm_password']
        tipo = request.POST['UserTypes']

        if password != confirm:
            messages.error(request, 'Las contraseñas no coinciden')
            return render(request, 'users/Sing_up.html')

        if Usuario.objects.filter(username=username).exists():
            messages.error(request, 'Ese usuario ya existe')
            return render(request, 'users/Sing_up.html')

        Modelo = Donante if tipo == 'Donante' else Receptor
        user = Modelo(username=username, email=email)
        user.set_password(password)
        user.save()

        return redirect('login')

    return render(request, 'users/Sing_up.html')


# Vista informativa para recuperación de contraseña
def reset_password(request):
    return render(request, 'users/reset_password.html')


# Guarda en la sesión las preferencias visuales (modo oscuro, alto contraste, fuente y alertas)
@login_required
def configuracion(request):
    if request.method == 'POST':
        request.session['tema_oscuro'] = request.POST.get('tema_oscuro') == 'on'
        request.session['alto_contraste'] = request.POST.get('alto_contraste') == 'on'
        request.session['tamano_fuente'] = request.POST.get('tamano_fuente', '100%')
        request.session['notif_caducidad'] = request.POST.get('notif_caducidad') == 'on'

        request.session.modified = True
        return redirect('configuracion')

    return render(request, 'users/configuracion.html')


# Exporta el inventario real de donaciones de db.sqlite3 en formato CSV o PDF
@login_required
def exportar_informe(request):
    formato = request.GET.get('formato', 'csv')

    # Consulta real a las donaciones registradas en la base de datos
    donaciones_qs = Donacion.objects.select_related('alimento', 'donante').all()
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

    if formato == 'pdf':
        # Generación de PDF
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

    # Exportación a formato CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="informe_donaciones.csv"'
    response.write('\ufeff')  # BOM para compatibilidad de acentos con Excel

    writer = csv.writer(response)
    writer.writerow(['Alimento', 'Cantidad', 'Tipo', 'Caducidad', 'Estado'])
    for r in registros:
        writer.writerow(r)

    return response
