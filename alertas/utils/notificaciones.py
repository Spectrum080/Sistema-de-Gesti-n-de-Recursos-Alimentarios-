# Constantes de roles de destino para mantener coherencia en todo el módulo de alertas
ROL_DONANTE = 'donante'
ROL_RECEPTOR = 'receptor'
ROL_GENERAL = 'general'


def crear_notificacion(destiny, titulo, mensaje, rol_destino=ROL_GENERAL, level='info'):
    """
    Crea un registro de Notificacion en la base de datos si existe un destinatario válido.

    Args:
        destiny: Instancia de Usuario que recibirá la notificación (puede ser None).
        titulo: Resumen breve (máx. 150 caracteres) para la cajita de la campanita.
        mensaje: Descripción detallada para la tabla completa (mis_notificaciones).
        rol_destino: Rol al que corresponde la alerta ('donante', 'receptor' o 'general').
        level: Nivel visual/semántico ('info', 'success', 'warning', 'danger').

    Returns:
        Notificacion | None: Instancia creada o None si no hay destinatario.
    """
    # Importación local para evitar dependencias circulares al cargar alertas.models
    from alertas.models import Notificacion

    # Si no hay usuario destinatario, no se crea notificación
    if destiny is None:
        return None

    # Normaliza el título a texto y respeta el límite de 150 caracteres del modelo
    titulo_limpio = str(titulo).strip()[:150]

    return Notificacion.objects.create(
        destiny=destiny,
        titulo=titulo_limpio,
        mensaje=str(mensaje).strip(),
        rol_destino=rol_destino,
        level=level,
    )


def notificar_donacion_registrada(donacion):
    """
    Genera una notificación ÚNICAMENTE para el donante cuando registra una donación.

    Args:
        donacion: Instancia recién creada del modelo Donacion.
    """
    # Solo notifica si la donación está vinculada a una cuenta de usuario donante
    usuario_donante = getattr(donacion, 'usuario_donante', None)
    if usuario_donante is None:
        return

    # Obtiene el nombre del alimento de forma segura
    nombre_alimento = donacion.alimento.nombre if donacion.alimento else 'Alimento'

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


def notificar_decision_receptor(donacion, usuario_receptor, accion, comentario_feedback=None):
    """
    Notifica al DONANTE y al RECEPTOR cuando el receptor acepta, reserva,
    rechaza o guarda feedback sobre una donación.

    Args:
        donacion: Instancia de Donacion gestionada.
        usuario_receptor: Instancia de Usuario receptor que realizó la acción.
        accion: Acción ejecutada ('Aceptado', 'Reservado', 'Rechazado', 'GuardarFeedback', etc.).
        comentario_feedback: Texto opcional de retroalimentación del receptor.
    """
    nombre_alimento = donacion.alimento.nombre if donacion.alimento else 'Alimento'
    accion_texto = (accion or donacion.estado or 'Actualización').strip()
    feedback_limpio = (comentario_feedback or '').strip()
    detalle_feedback = f" Feedback: {feedback_limpio}." if feedback_limpio else ""

    # Configura título y nivel visual según la decisión tomada
    configuracion_accion = {
        'Aceptado': (f"Donación aceptada: {nombre_alimento}", 'success'),
        'Reservado': (f"Donación reservada: {nombre_alimento}", 'info'),
        'Rechazado': (f"Donación rechazada: {nombre_alimento}", 'warning'),
    }
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

    Nota: Debe invocarse ANTES de eliminar el registro de Donacion en base de datos.

    Args:
        donacion: Instancia de Donacion próxima a eliminarse.
    """
    usuario_donante = getattr(donacion, 'usuario_donante', None)
    if usuario_donante is None:
        return

    # Captura datos clave antes de borrar el objeto de la base de datos
    donacion_id = donacion.id
    nombre_alimento = donacion.alimento.nombre if donacion.alimento else 'Alimento'
    cantidad_texto = donacion.cantidad

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