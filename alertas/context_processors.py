# Importa el modelo Notificacion para consultar las alertas pendientes del usuario
from alertas.models import Notificacion
# Importa la función que genera alertas de alto riesgo por caducidad sin duplicarlas
from alertas.utils.notificaciones import sincronizar_alertas_alto_riesgo


def notificaciones_globales(request):
    """
    Context processor que inyecta en todas las plantillas que heredan de dashboard.html:
    - notificaciones_pendientes: lista de notificaciones no leídas del usuario actual.
    - total_no_leidas: total numérico de notificaciones sin leer.
    - cantidad_notis_pendientes: alias usado por el indicador rojo de la campanita.
    """
    # Si el usuario no ha iniciado sesión, retorna valores vacíos seguros
    if not request.user.is_authenticated:
        return {
            'notificaciones_pendientes': [],
            'total_no_leidas': 0,
            'cantidad_notis_pendientes': 0,
        }

    # Si las alertas de caducidad están activas en sesión, sincroniza avisos de alto riesgo
    if request.session.get('notif_caducidad', True):
        sincronizar_alertas_alto_riesgo(request.user)

    # Consulta base: solo notificaciones no leídas dirigidas al usuario en sesión
    pendientes_qs = Notificacion.objects.filter(
        destiny=request.user,
        read=False,
    )

    # Filtra por rol real de la cuenta (incluyendo avisos 'general') para evitar fugas entre roles
    if hasattr(request.user, 'donante'):
        pendientes_qs = pendientes_qs.filter(rol_destino__in=['donante', 'general'])
    elif hasattr(request.user, 'receptor'):
        pendientes_qs = pendientes_qs.filter(rol_destino__in=['receptor', 'general'])
    else:
        # Si es administrador, permite filtrar según la ruta visitada
        path = request.path.lower()
        if 'donante' in path:
            pendientes_qs = pendientes_qs.filter(rol_destino__in=['donante', 'general'])
        elif 'receptor' in path:
            pendientes_qs = pendientes_qs.filter(rol_destino__in=['receptor', 'general'])

    # Calcula una sola vez la cantidad de notificaciones sin leer
    total = pendientes_qs.count()

    # Retorna las variables globales disponibles en cualquier plantilla del proyecto
    return {
        'notificaciones_pendientes': pendientes_qs,
        'total_no_leidas': total,
        'cantidad_notis_pendientes': total,
    }
