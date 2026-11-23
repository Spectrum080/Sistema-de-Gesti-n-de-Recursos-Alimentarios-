# Importa date y datetime para convertir y comparar fechas de caducidad de forma segura
from datetime import date, datetime
# Importa timezone para obtener la fecha actual del servidor Django
from django.utils import timezone

# Constantes de roles de destino para mantener coherencia en todo el módulo de alertas
ROL_DONANTE = 'donante'
ROL_RECEPTOR = 'receptor'
ROL_GENERAL = 'general'

# Días máximos para considerar una donación como de alto riesgo por caducidad próxima
DIAS_ALTO_RIESGO = 3


def _parsear_fecha_caducidad(valor_fecha):
    """
    Convierte un valor de fecha (date, datetime o texto 'YYYY-MM-DD') a objeto date.
    Retorna None si el valor está vacío o no tiene un formato válido.
    """
    # Si no se proporcionó fecha, retorna None
    if not valor_fecha:
        return None
    # Si ya es un objeto datetime, extrae solo la parte de la fecha
    if isinstance(valor_fecha, datetime):
        return valor_fecha.date()
    # Si ya es un objeto date, lo devuelve directamente
    if isinstance(valor_fecha, date):
        return valor_fecha
    # Si viene como texto (ej. desde request.POST), intenta convertirlo con formato ISO
    try:
        return date.fromisoformat(str(valor_fecha).strip())
    except ValueError:
        return None


def _evaluar_riesgo_caducidad(donacion):
    """
    Evalúa si una donación es de alto riesgo según su fecha de caducidad y tipo.
    Retorna una tupla (es_alto_riesgo: bool, motivo: str).
    """
    # Obtiene la fecha de caducidad desde la donación o, si falta, desde el alimento vinculado
    fecha_raw = getattr(donacion, 'fecha_caducidad', None) or (
        donacion.alimento.fecha_caducidad if getattr(donacion, 'alimento', None) else None
    )
    # Convierte la fecha a un objeto date comparable
    fecha_cad = _parsear_fecha_caducidad(fecha_raw)
    # Si no hay fecha registrada, no se puede marcar riesgo por caducidad
    if fecha_cad is None:
        return False, ''

    # Obtiene la fecha de hoy según la zona horaria configurada en Django
    hoy = timezone.localdate()
    # Calcula cuántos días faltan para que caduque el alimento
    dias_restantes = (fecha_cad - hoy).days

    # Si los días son negativos, el alimento ya está vencido (alto riesgo crítico)
    if dias_restantes < 0:
        return True, f"ALTO RIESGO: caducó el {fecha_cad.strftime('%d/%m/%Y')}"
    # Si caduca hoy mismo, requiere atención inmediata
    if dias_restantes == 0:
        return True, "ALTO RIESGO: caduca HOY"
    # Si caduca dentro del umbral configurado (1 a 3 días), se marca como alto riesgo
    if dias_restantes <= DIAS_ALTO_RIESGO:
        return True, f"ALTO RIESGO: caduca en {dias_restantes} día(s) ({fecha_cad.strftime('%d/%m/%Y')})"

    # En cualquier otro caso, la donación no está en riesgo inmediato
    return False, ''


def crear_notificacion(destiny, titulo, mensaje, rol_destino=ROL_GENERAL, level='info'):
    """
    Crea un registro de Notificacion en la base de datos si existe un destinatario válido.
    """
    # Importación local para evitar dependencias circulares al cargar alertas.models
    from alertas.models import Notificacion

    # Si no hay usuario destinatario, no se crea notificación
    if destiny is None:
        return None

    # Normaliza el título a texto y respeta el límite de 150 caracteres del modelo
    titulo_limpio = str(titulo).strip()[:150]

    # Inserta la notificación en la base de datos con el rol y nivel visual indicados
    return Notificacion.objects.create(
        destiny=destiny,
        titulo=titulo_limpio,
        mensaje=str(mensaje).strip(),
        rol_destino=rol_destino,
        level=level,
    )


def notificar_donacion_registrada(donacion):
    """
    Genera notificaciones cuando se crea una nueva donación:
    1. Al donante confirmando su registro (y avisando si es de alto riesgo).
    2. A todos los receptores activos avisando que hay una nueva donación por atender
       (con alerta prioritaria 'danger' si es de alto riesgo por caducidad).
    """
    # Importación local de Receptor para notificar a las cuentas receptoras registradas
    from users.models import Receptor

    # Obtiene el usuario donante que registró la entrega
    usuario_donante = getattr(donacion, 'usuario_donante', None)
    # Obtiene el nombre del alimento de forma segura
    nombre_alimento = donacion.alimento.nombre if donacion.alimento else 'Alimento'
    # Verifica si la donación recién creada es de alto riesgo por fecha de caducidad
    es_alto_riesgo, motivo_riesgo = _evaluar_riesgo_caducidad(donacion)

    # 1) Notificación para el DONANTE dueño de la donación
    if usuario_donante is not None:
        # Si la donación es de alto riesgo, se destaca en rojo ('danger') con el motivo
        if es_alto_riesgo:
            crear_notificacion(
                destiny=usuario_donante,
                titulo=f"Alerta de alto riesgo: {nombre_alimento}",
                mensaje=(
                    f"Registraste la donación #{donacion.id} de '{nombre_alimento}' "
                    f"({donacion.cantidad}). {motivo_riesgo}."
                ),
                rol_destino=ROL_DONANTE,
                level='danger',
            )
        # Si es una donación normal, se envía confirmación estándar en verde ('success')
        else:
            crear_notificacion(
                destiny=usuario_donante,
                titulo=f"Donación registrada: {nombre_alimento}",
                mensaje=(
                    f"Registraste la donación #{donacion.id} de '{nombre_alimento}' "
                    f"({donacion.cantidad}) en estado '{donacion.estado}'."
                ),
                rol_destino=ROL_DONANTE,
                level='success',
            )

    # 2) Notificación para todos los RECEPTORES para que atiendan la nueva donación
    for receptor in Receptor.objects.all():
        # Evita notificar al mismo usuario si por alguna razón coincidiera con el donante
        if usuario_donante is not None and receptor.pk == usuario_donante.pk:
            continue
        # Si la donación es de alto riesgo, envía alerta prioritaria ('danger') al receptor
        if es_alto_riesgo:
            crear_notificacion(
                destiny=receptor,
                titulo=f"Donación de alto riesgo: {nombre_alimento}",
                mensaje=(
                    f"Nueva donación #{donacion.id} de '{nombre_alimento}' "
                    f"({donacion.cantidad}) por atender. {motivo_riesgo}."
                ),
                rol_destino=ROL_RECEPTOR,
                level='danger',
            )
        # Si no es de alto riesgo, informa que hay una nueva donación disponible ('info')
        else:
            crear_notificacion(
                destiny=receptor,
                titulo=f"Nueva donación disponible: {nombre_alimento}",
                mensaje=(
                    f"Se registró la donación #{donacion.id} de '{nombre_alimento}' "
                    f"({donacion.cantidad}) lista para atender."
                ),
                rol_destino=ROL_RECEPTOR,
                level='info',
            )


def sincronizar_alertas_alto_riesgo(usuario):
    """
    Revisa donaciones activas por atender del usuario (o del acopio si es receptor)
    y crea alertas de alto riesgo (caducidad <= 3 días o vencida) sin duplicarlas.
    """
    # Importaciones locales para evitar ciclos de importación
    from alertas.models import Notificacion

    # Si no hay usuario autenticado, no realiza ninguna consulta
    if usuario is None or not getattr(usuario, 'is_authenticated', False):
        return

    # Determina el rol y el conjunto de donaciones que corresponden a este usuario
    if hasattr(usuario, 'receptor'):
        rol_objetivo = ROL_RECEPTOR
        donaciones_qs = usuario.obtener_donaciones_para_receptor()
    elif hasattr(usuario, 'donante'):
        rol_objetivo = ROL_DONANTE
        donaciones_qs = usuario.obtener_mis_donaciones().filter(
            estado__in=['Pendiente', 'Recibido', 'Activa']
        )
    else:
        return

    # Recorre cada donación pendiente evaluando si entró en estado de alto riesgo
    for donacion in donaciones_qs:
        es_alto_riesgo, motivo_riesgo = _evaluar_riesgo_caducidad(donacion)
        if not es_alto_riesgo:
            continue

        # Construye la etiqueta única '#ID' para verificar que no exista ya una alerta de riesgo igual
        marca_id = f"#{donacion.id} "
        ya_existe = Notificacion.objects.filter(
            destiny=usuario,
            rol_destino=rol_objetivo,
            level='danger',
            mensaje__contains=marca_id,
        ).exists()
        # Si ya se notificó antes el riesgo de esta donación, no la duplica
        if ya_existe:
            continue

        # Obtiene el nombre del alimento y crea la notificación de alto riesgo
        nombre_alimento = donacion.alimento.nombre if donacion.alimento else 'Alimento'
        crear_notificacion(
            destiny=usuario,
            titulo=f"Alerta de alto riesgo: {nombre_alimento}",
            mensaje=(
                f"La donación #{donacion.id} de '{nombre_alimento}' "
                f"({donacion.cantidad}) requiere atención urgente. {motivo_riesgo}."
            ),
            rol_destino=rol_objetivo,
            level='danger',
        )


def notificar_decision_receptor(donacion, usuario_receptor, accion, comentario_feedback=None):
    """
    Notifica al DONANTE y al RECEPTOR cuando el receptor acepta, reserva,
    rechaza o guarda feedback sobre una donación.
    """
    # Obtiene el nombre del alimento de forma segura
    nombre_alimento = donacion.alimento.nombre if donacion.alimento else 'Alimento'
    # Normaliza el texto de la acción ejecutada
    accion_texto = (accion or donacion.estado or 'Actualización').strip()
    # Limpia espacios del comentario opcional
    feedback_limpio = (comentario_feedback or '').strip()
    # Prepara el fragmento de texto del comentario si existe
    detalle_feedback = f" Feedback: {feedback_limpio}." if feedback_limpio else ""

    # Configura título y nivel visual según la decisión tomada
    configuracion_accion = {
        'Aceptado': (f"Donación aceptada: {nombre_alimento}", 'success'),
        'Reservado': (f"Donación reservada: {nombre_alimento}", 'info'),
        'Rechazado': (f"Donación rechazada: {nombre_alimento}", 'warning'),
    }
    # Obtiene el par (título, nivel) o usa un valor genérico por defecto
    titulo_donante, level_donante = configuracion_accion.get(
        accion_texto,
        (f"Actualización en donación: {nombre_alimento}", 'info'),
    )

    # 1) Notificación para el donante dueño de la donación
    usuario_donante = getattr(donacion, 'usuario_donante', None)
    if usuario_donante is not None:
        crear_notificacion(
            destiny=usuario_donante,
            titulo=titulo_donante,
            mensaje=(
                f"La donación #{donacion.id} ('{nombre_alimento}', {donacion.cantidad}) "
                f"tuvo la acción '{accion_texto}'.{detalle_feedback}"
            ),
            rol_destino=ROL_DONANTE,
            level=level_donante,
        )

    # 2) Confirmación para el receptor que ejecutó la acción
    if usuario_receptor is not None and getattr(usuario_receptor, 'is_authenticated', False):
        crear_notificacion(
            destiny=usuario_receptor,
            titulo=f"Acción registrada: {nombre_alimento}",
            mensaje=(
                f"Registraste '{accion_texto}' en la donación #{donacion.id} "
                f"('{nombre_alimento}', {donacion.cantidad}).{detalle_feedback}"
            ),
            rol_destino=ROL_RECEPTOR,
            level='info',
        )


def notificar_donacion_eliminada(donacion):
    """
    Genera una notificación al DONANTE cuando una donación es eliminada del sistema.
    Debe invocarse ANTES de eliminar el registro de Donacion en base de datos.
    """
    # Recupera el usuario donante propietario
    usuario_donante = getattr(donacion, 'usuario_donante', None)
    if usuario_donante is None:
        return

    # Captura datos clave antes de borrar el objeto de la base de datos
    donacion_id = donacion.id
    nombre_alimento = donacion.alimento.nombre if donacion.alimento else 'Alimento'
    cantidad_texto = donacion.cantidad

    # Crea la notificación de eliminación en nivel 'danger'
    crear_notificacion(
        destiny=usuario_donante,
        titulo=f"Donación eliminada: {nombre_alimento}",
        mensaje=(
            f"La donación #{donacion_id} de '{nombre_alimento}' ({cantidad_texto}) "
            f"fue eliminada del sistema."
        ),
        rol_destino=ROL_DONANTE,
        level='danger',
    )
