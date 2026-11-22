# Importa el modelo Notificacion para consultar las alertas pendientes del usuario
from alertas.models import Notificacion


def notificaciones_globales(request):
    """
    Inyecta en todas las plantillas:
    - notificaciones_pendientes: notificaciones no leídas del usuario actual.
    - total_no_leidas: cantidad de notificaciones sin leer.
    """
    # Si el usuario no está autenticado, retorna valores vacíos seguros
    if not request.user.is_authenticated:
        return {
            'notificaciones_pendientes': [],
            'total_no_leidas': 0,
        }

    # Base: notificaciones no leídas dirigidas al usuario en sesión
    pendientes_qs = Notificacion.objects.filter(
        destiny=request.user,
        read=False,
    )

    # Si está en el panel de donante o receptor, filtra por ese rol_destino
    path = request.path.lower()
    if 'donante' in path:
        pendientes_qs = pendientes_qs.filter(rol_destino='donante')
    elif 'receptor' in path:
        pendientes_qs = pendientes_qs.filter(rol_destino='receptor')

    return {
        'notificaciones_pendientes': pendientes_qs,
        'total_no_leidas': pendientes_qs.count(),
    }