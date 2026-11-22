import csv # Importa el módulo csv para generar archivos en formato CSV
from django.db.models import Sum # Importa Sum para realizar sumas de valores en consultas a la base de datos
from django.http import HttpResponse # Importa HttpResponse para enviar respuestas HTTP al navegador
from django.shortcuts import render, redirect # Importa render para mostrar plantillas HTML y redirect para redirigir a otras páginas
from django.contrib import messages # Importa messages para mostrar mensajes informativos o de error al usuario
from django.contrib.auth.decorators import login_required # Importa login_required para restringir el acceso a usuarios que hayan iniciado sesión
from alertas.models import Donacion, Alimento # Importa los modelos Donacion y Alimento de la aplicación alertas
from .models import Usuario, Donante, Receptor # Importa los modelos Donacion y Alimento de la aplicación alertas


# Calcula en tiempo real las métricas del dashboard (total de donaciones y peso en KG) desde db.sqlite3
def _obtener_contexto_dashboard(): #Se declara una función privada para obtener el contexto del dashboard
    donaciones_qs = Donacion.objects.select_related( #Pide a la base de datos todas las donaciones y sus relaciones
        'alimento', 'donante', 'receptor', 'centro_acopio'
    ).all()
    total_donaciones = donaciones_qs.count() #Toma el total de donaciones registradas en la base de datos
    suma_peso = donaciones_qs.aggregate(total=Sum('peso_kg'))['total'] or 0 #aggregate(Sum('peso_kg')): Le pide a la base de datos que sume todos los valores de la columna peso_kg de todas las donaciones.
    peso_formateado = f"{float(suma_peso):,.1f} KG".replace('.0 KG', ' KG') #Toma el número de la suma (por ejemplo, 1250) y lo convierte en un texto bonito para el usuario: "1,250 KG"

    return { #La función termina devolviendo (con return) un diccionario de Python. Este diccionario es el "paquete" que se enviará al diseño web del dashboard.
        'total_donaciones': total_donaciones,
        'peso_total': peso_formateado,
        'estatus': 'ACTIVO' if total_donaciones > 0 else 'SIN REGISTROS',
        'donaciones': donaciones_qs,
        'alimentos': Alimento.objects.select_related('categoria', 'centro_acopio').all(),
    }


# Redirige al panel correspondiente según el rol del usuario e inyecta las métricas reales
@login_required #Si una persona intenta entrar al dashboard sin haber iniciado sesión con su correo y contraseña, este código la detiene y la envía automáticamente a la pantalla de "Iniciar sesión".
def dashboard(request): #El parámetro request contiene toda la información de la persona que está intentando entrar a la página (quién es, qué navegador usa, su historial de sesión, etc.).
    if hasattr(request.user, 'donante'): #hasattr(request.user, 'donante'): Comprueba si el usuario tiene un perfil de donante asociado.
        request.session['rol_activo'] = 'donante' #request.session['rol_activo'] = 'donante': Guarda en la sesión que el rol activo del usuario es donante.
        return redirect('dashboardDonante') #Expulsa al usuario de esta función y lo redirige (como un salto automático) a otra dirección web específica diseñada exclusivamente para los donantes.
    elif hasattr(request.user, 'receptor'): #Si es así, hace exactamente lo mismo que en el paso anterior: guarda en la sesión que su rol es "receptor" y lo redirige a la pantalla exclusiva para los receptores (dashboardReceptor).
        request.session['rol_activo'] = 'receptor'
        return redirect('dashboardReceptor')
    elif request.session.get('rol_activo') == 'receptor': #request.session.get('rol_activo') == 'receptor': Comprueba si el rol activo guardado en la sesión del usuario es receptor para redirigirlo a su dashboard.
        return redirect('dashboardReceptor')
    else:
        request.session['rol_activo'] = 'donante' #Si no se cumple ninguna de las condiciones anteriores, se asume que el usuario es un donante y se guarda en la sesión que su rol activo es "donante".
        context = _obtener_contexto_dashboard()
        return render(request, 'users/dashboard.html', context)


# Panel del Donante que hereda la estructura y métricas desde dashboard.html
@login_required
def dashboardDonante(request):
    request.session['rol_activo'] = 'donante'
    context = _obtener_contexto_dashboard()
    return render(request, 'users/dashboardDonante.html', context)


# Panel del Receptor que hereda la estructura y métricas desde dashboard.html
@login_required #Verifica que el usuario haya iniciado sesión para acceder al panel.
def dashboardReceptor(request):
    request.session['rol_activo'] = 'receptor' #request.session['rol_activo'] = 'donante': Establece el rol activo del usuario como donante.
    context = _obtener_contexto_dashboard() #context = _obtener_contexto_dashboard(): Obtiene los datos necesarios para mostrar las métricas del dashboard.
    return render(request, 'users/dashboardReceptor.html', context) #return render(...): Carga la plantilla dashboardDonante.html, le pasa los datos de context y muestra el panel del donante.


# Registro de nuevos usuarios asignando el modelo Donante o Receptor según selección
def Sing_up(request):
    if request.method == 'POST': #request.method == 'POST': Comprueba si se envió el formulario.
        username = request.POST['username'] # Obtiene el nombre de usuario ingresado en el formulario
        email = request.POST['email'] # Obtiene el correo electrónico ingresado
        password = request.POST['password'] # Obtiene la contraseña ingresada
        confirm = request.POST['confirm_password'] # Obtiene la confirmación de la contraseña
        tipo = request.POST['UserTypes'] # Obtiene el tipo de usuario seleccionado (Donante o Receptor)

        if password != confirm: # Comprueba si las contraseñas ingresadas son diferentes
            messages.error(request, 'Las contraseñas no coinciden') # Muestra un mensaje indicando que las contraseñas no coinciden
            return render(request, 'users/Sing_up.html') #messages.error(request, 'Las contraseñas no coinciden')

        if Usuario.objects.filter(username=username).exists(): # Comprueba si el nombre de usuario ya existe en la base de datos
            messages.error(request, 'Ese usuario ya existe') # Muestra un mensaje indicando que el usuario ya está registrado
            return render(request, 'users/Sing_up.html') # Vuelve a mostrar el formulario de registro

        Modelo = Donante if tipo == 'Donante' else Receptor # Selecciona el modelo Donante o Receptor según el tipo de usuario elegido
        user = Modelo(username=username, email=email) # Crea una instancia del modelo seleccionado con el nombre y correo
        user.set_password(password) # Establece la contraseña utilizando el sistema de cifrado de Django
        user.save() # Guarda el nuevo usuario en la base de datos

        return redirect('login') # Redirige al usuario a la página de inicio de sesión

    return render(request, 'users/Sing_up.html') # Si no se envió el formulario mediante POST, muestra la página de registro


# Vista informativa para recuperación de contraseña
def reset_password(request):
    return render(request, 'users/reset_password.html')


# Guarda en la sesión las preferencias visuales (modo oscuro, alto contraste, fuente y alertas)
@login_required # Verifica que el usuario haya iniciado sesión para acceder a la configuración
def configuracion(request): # Función encargada de gestionar las preferencias de configuración del usuario
    if request.method == 'POST':  #Comprueba si el formulario fue enviado mediante el método POST
        request.session['tema_oscuro'] = request.POST.get('tema_oscuro') == 'on' # Guarda en la sesión si el tema oscuro está activado
        request.session['alto_contraste'] = request.POST.get('alto_contraste') == 'on' # Guarda en la sesión si el alto contraste está activado
        request.session['tamano_fuente'] = request.POST.get('tamano_fuente', '100%') # Guarda en la sesión el tamaño de fuente seleccionado, por defecto es '100%'
        request.session['notif_caducidad'] = request.POST.get('notif_caducidad') == 'on' # Guarda si las notificaciones de caducidad están activadas

        request.session.modified = True # Indica a Django que la sesión fue modificada y debe guardarse
        return redirect('configuracion') # Redirige nuevamente a la página de configuración

    return render(request, 'users/configuracion.html') # Si no se envió el formulario mediante POST, muestra la plantilla de configuración

@login_required # Verifica que el usuario haya iniciado sesión para acceder al perfil
def perfil(request): # Función encargada de mostrar y actualizar los datos del perfil
    usuario = request.user # Obtiene el usuario que inició sesión
    campo_razon = None # Inicializa la variable sin asignarle un campo específico
    if hasattr(usuario, 'donante'): # Comprueba si el usuario tiene un perfil de donante asociado
        usuario = usuario.donante # Obtiene los datos específicos del perfil de donante
        campo_razon = 'nombre_local' # Establece el nombre del campo que almacena el nombre del local
    elif hasattr(usuario, 'receptor'): # Comprueba si el usuario tiene un perfil de receptor asociado
        usuario = usuario.receptor # Obtiene los datos específicos del perfil de receptor
        campo_razon = 'nombre_org' # Establece el nombre del campo que almacena el nombre de la organización

    if request.method == 'POST': # Comprueba si se enviaron datos mediante el formulario POST
        usuario.telefono = request.POST.get('telefono', '') # Obtiene y actualiza el número telefónico del usuario
        usuario.direccion = request.POST.get('direccion', '') # Obtiene y actualiza la dirección del usuario
        if campo_razon: # Comprueba si existe un campo para almacenar la razón social
            setattr(usuario, campo_razon, request.POST.get('razon_social', '')) # Asigna el valor recibido del formulario al campo correspondiente
        usuario.save() # Guarda los cambios del perfil en la base de datos
        messages.success(request, 'Perfil actualizado') # Muestra un mensaje indicando que el perfil fue actualizado correctamente
        return redirect('perfil') # Redirige nuevamente a la página del perfil

    razon_social = getattr(usuario, campo_razon, '') if campo_razon else '' # Obtiene la razón social del usuario; si no existe el campo, devuelve una cadena vacía
    return render(request, 'users/perfil.html', {'razon_social': razon_social}) # Carga la plantilla del perfil y envía la razón social como contexto


# Exporta el inventario real de donaciones de db.sqlite3 en formato CSV o PDF
@login_required # Verifica que el usuario haya iniciado sesión para acceder a esta función
def exportar_informe(request): # Función encargada de generar y exportar informes de donaciones
    formato = request.GET.get('formato', 'csv') # Obtiene el formato solicitado; si no se especifica, utiliza CSV por defecto

    # Consulta real a las donaciones registradas en la base de datos
    donaciones_qs = Donacion.objects.select_related('alimento', 'donante').all() # Consulta las donaciones registradas y obtiene también los datos relacionados del alimento y donante
    registros = [] # Crea una lista vacía para almacenar los registros de las donaciones
    for d in donaciones_qs: # Recorre cada donación obtenida de la base de datos
        caducidad_str = ( # Obtiene la fecha de caducidad de la donación o, si no existe, la del alimento
            d.fecha_caducidad.strftime('%d/%m/%Y')
            if d.fecha_caducidad
            else (
                d.alimento.fecha_caducidad.strftime('%d/%m/%Y')
                if d.alimento and d.alimento.fecha_caducidad
                else 'N/A'
            )
        )
        registros.append([  # Agrega los datos de cada donación a la lista de registros
            d.alimento.nombre if d.alimento else 'Alimento',
            d.cantidad,
            d.get_tipo_display(),
            caducidad_str,
            d.estado,
        ])

    if formato == 'pdf': # Comprueba si el formato solicitado es PDF
        # Generación de PDF
        lineas = [ # Genera las líneas que contendrá el reporte PDF
            "REPORTE DE INVENTARIO - HAMBRE CERO",
            "----------------------------------------------------------------",
            "ALIMENTO           CANTIDAD     TIPO            CADUCIDAD     ESTADO",
            "------------------------------------------------------------------",
        ]
        for r in registros: # Recorre los registros para organizar la información del PDF
            nombre_corto = (r[0][:16] + '..') if len(r[0]) > 18 else r[0] # Acorta el nombre del alimento si supera los 18 caracteres
            cant_corta = (r[1][:10] + '..') if len(r[1]) > 12 else r[1] # Acorta la cantidad si supera los 12 caracteres
            lineas.append(f"{nombre_corto:<18} {cant_corta:<12} {r[2]:<15} {r[3]:<13} {r[4]}") # Agrega los datos del registro en una línea con espacios para organizar las columnas

        contenido_stream = "BT /F1 10 Tf 40 750 Td 16 TL " # Inicializa el contenido del PDF indicando la fuente, tamaño y posición del texto
        for linea in lineas: # Recorre cada línea que se mostrará en el documento PDF
            texto_limpio = ( # Convierte el texto a codificación Latin-1 y reemplaza los caracteres no compatibles
                             # También protege los paréntesis para evitar errores en la estructura del PDF
                linea.encode('latin-1', errors='replace').decode('latin-1')
                .replace("(", "\\(")
                .replace(")", "\\)")
            )
            contenido_stream += f"({texto_limpio}) Tj T* " # Agrega el texto al contenido del PDF y establece un salto de línea
        contenido_stream += "ET" # Finaliza las instrucciones de escritura del PDF
        stream_bytes = contenido_stream.encode('latin-1', errors='replace') # Convierte el contenido del documento a bytes utilizando Latin-1

        objetos = [ # Define los objetos internos que conforman la estructura del archivo PDF
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n", # Objeto que define el catálogo principal del documento
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n", # Objeto que define las páginas del documento
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n", # Objeto que configura la página, sus recursos, fuente y contenido
            b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n", # Objeto que establece la fuente Helvetica
            f"5 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode('latin-1') + stream_bytes + b"\nendstream\nendobj\n" # Objeto que contiene el texto generado y su longitud en bytes
        ]

        pdf = b"%PDF-1.4\n" # Inicializa el archivo PDF con su encabezado y versión 1.4
        offsets = [] # Crea una lista para almacenar las posiciones de cada objeto dentro del PDF
        for obj in objetos: # Recorre los objetos para incorporarlos al archivo PDF
            offsets.append(len(pdf)) # Guarda la posición donde comienza cada objeto
            pdf += obj # Agrega el objeto al contenido del PDF

        xref_offset = len(pdf) # Guarda la posición donde comenzará la tabla de referencias cruzadas
        pdf += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode('latin-1') # Genera la tabla de referencias cruzadas para localizar los objetos del PDF
        for off in offsets: # Recorre las posiciones almacenadas para agregarlas a la tabla de referencias
            pdf += f"{off:010d} 00000 n \n".encode('latin-1') # Escribe la posición de cada objeto dentro del archivo PDF
        pdf += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode('latin-1') # Agrega el tráiler, la referencia al catálogo y el cierre del documento PDF

        response = HttpResponse(pdf, content_type='application/pdf') # Crea la respuesta HTTP con el contenido del PDF
        response['Content-Disposition'] = 'attachment; filename="informe_donaciones.pdf"' # Establece el nombre del archivo PDF que se descargará
        return response # Devuelve el archivo PDF al navegador para su descarga

    # Exportación a formato CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8') # Crea una respuesta HTTP indicando que el contenido será un archivo CSV con codificación UTF-8
    response['Content-Disposition'] = 'attachment; filename="informe_donaciones.csv"' # Establece el nombre del archivo CSV que se descargará
    response.write('\ufeff')  # Agrega el BOM para facilitar la compatibilidad de caracteres especiales y acentos con Excel

    writer = csv.writer(response) # Crea un escritor CSV para organizar los datos en filas y columnas
    writer.writerow(['Alimento', 'Cantidad', 'Tipo', 'Caducidad', 'Estado']) # Escribe los encabezados de las columnas del archivo CSV
    for r in registros: # Recorre los registros de las donaciones
        writer.writerow(r) # Escribe cada registro como una fila dentro del archivo CSV

    return response # Devuelve el archivo CSV al navegador para su descarga
