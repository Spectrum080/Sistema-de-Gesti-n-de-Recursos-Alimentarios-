import csv
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Usuario, Donante, Receptor

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
        return render(request, 'users/dashboard.html')

@login_required
def dashboardDonante(request):
    request.session['rol_activo'] = 'donante'
    context = {
        'total_donaciones': 2,
        'peso_total': '35 KG',
        'estatus': 'ACTIVO',
    }
    return render(request, 'users/dashboardDonante.html', context)

@login_required
def dashboardReceptor(request):
    request.session['rol_activo'] = 'receptor'
    context = {
        'total_donaciones': 2,
        'peso_total': '35 KG',
        'estatus': 'ACTIVO',
    }
    return render(request, 'users/dashboardReceptor.html', context)

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

def reset_password(request):
    return render(request, 'users/reset_password.html')

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

@login_required
def exportar_informe(request):
    formato = request.GET.get('formato', 'csv')

    # TODO: Preparar la consulta real a la base de datos (ej. Donacion.objects.all())
    # Por el momento dejamos los valores estáticos listos para meter la base de datos
    registros = [
        ['Lentejas', '10 kg', 'Preparado', 'Hoy 21:30', 'Activa'],
        ['Arroz', '25 kg', 'No perecedero', '12/07/2026', 'Reservada']
    ]

    if formato == 'pdf':
        # Generación de PDF
        lineas = [
            "REPORTE DE INVENTARIO - HAMBRE CERO",
            "----------------------------------------------------------------",
            "ALIMENTO           CANTIDAD     TIPO            CADUCIDAD     ESTADO",
            "------------------------------------------------------------------",
        ]
        for r in registros:
            # Espaciado para mantener orden en texto plano
            lineas.append(f"{r[0]:<18} {r[1]:<12} {r[2]:<15} {r[3]:<13} {r[4]}")

        contenido_stream = "BT /F1 10 Tf 40 750 Td 16 TL "
        for linea in lineas:
            texto_limpio = linea.replace("(", "\\(").replace(")", "\\)")
            contenido_stream += f"({texto_limpio}) Tj T* "
        contenido_stream += "ET"
        stream_bytes = contenido_stream.encode('latin-1')

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
