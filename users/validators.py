# Módulo centralizado de validaciones y sanitización de entradas (Python / Django)
import re
from datetime import date, time
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.utils import timezone
from django.utils.html import strip_tags

# Mapa de dominios de correo tipográficamente erróneos frecuentes -> dominio correcto sugerido
TYPOS_DOMINIOS_CORREO = {
    'gmai.com': 'gmail.com',
    'gmial.com': 'gmail.com',
    'gamil.com': 'gmail.com',
    'gnail.com': 'gmail.com',
    'gmali.com': 'gmail.com',
    'gmaill.com': 'gmail.com',
    'gmail.co': 'gmail.com',
    'gmail.con': 'gmail.com',
    'gmail.cm': 'gmail.com',
    'gmail.om': 'gmail.com',
    'hotmial.com': 'hotmail.com',
    'hotmal.com': 'hotmail.com',
    'hotamil.com': 'hotmail.com',
    'hotmaill.com': 'hotmail.com',
    'hotmail.co': 'hotmail.com',
    'hotmail.con': 'hotmail.com',
    'outlok.com': 'outlook.com',
    'outllok.com': 'outlook.com',
    'outloook.com': 'outlook.com',
    'outlook.co': 'outlook.com',
    'outlook.con': 'outlook.com',
    'yaho.com': 'yahoo.com',
    'yahooo.com': 'yahoo.com',
    'yhaoo.com': 'yahoo.com',
    'yahoo.co': 'yahoo.com',
    'yahoo.con': 'yahoo.com',
    'icloud.co': 'icloud.com',
    'icloud.con': 'icloud.com',
    'iclud.com': 'icloud.com',
    'live.co': 'live.com',
    'live.con': 'live.com',
}

# Expresiones regulares de validación estricta
_RE_TELEFONO_PERMITIDO = re.compile(r'^\+?[\d\s\-()]+$')
_RE_RAZON_SOCIAL = re.compile(r"^[A-Za-zÁÉÍÓÚáéíóúÑñÜü0-9\s.,&'()/#\-]+$")
_RE_DIRECCION = re.compile(r"^[A-Za-zÁÉÍÓÚáéíóúÑñÜü0-9\s.,#\-°/()']+$")
_RE_TLD_VALIDO = re.compile(r'^[a-z]{2,24}$')
_EMAIL_VALIDATOR = EmailValidator()


def limpiar_texto_seguro(valor, max_len=None):
    """Elimina etiquetas HTML, caracteres de control y espacios redundantes."""
    texto = strip_tags(str(valor or ''))
    # Remueve caracteres de control invisibles
    texto = re.sub(r'[\x00-\x1f\x7f]', '', texto)
    # Colapsa múltiples espacios en uno solo
    texto = re.sub(r'\s+', ' ', texto).strip()
    if max_len is not None:
        texto = texto[:max_len]
    return texto


def validar_correo_estricto(correo):
    """
    Valida sintaxis RFC 5322 y consistencia semántica básica del dominio del correo.
    Rechaza dominios tipográficamente erróneos conocidos (ej. 'gmai.com').
    Retorna (correo_normalizado, mensaje_error_o_None).
    """
    email = limpiar_texto_seguro(correo, max_len=254).lower()
    if not email:
        return '', 'El correo electrónico es obligatorio.'

    try:
        _EMAIL_VALIDATOR(email)
    except ValidationError:
        return email, 'Ingresa un correo electrónico con formato válido (ej. nombre@dominio.com).'

    partes = email.rsplit('@', 1)
    if len(partes) != 2 or '.' not in partes[1]:
        return email, 'El correo electrónico debe incluir un dominio válido.'

    dominio = partes[1]
    # Verifica typos frecuentes en proveedores populares
    if dominio in TYPOS_DOMINIOS_CORREO:
        sugerido = TYPOS_DOMINIOS_CORREO[dominio]
        return email, (
            f"El dominio '{dominio}' parece tener un error tipográfico. "
            f"¿Quisiste decir '{sugerido}'?"
        )

    # Valida que el TLD final sea exclusivamente alfabético (ej. com, mx, org, edu)
    etiquetas = dominio.split('.')
    tld = etiquetas[-1]
    if not _RE_TLD_VALIDO.match(tld) or any(not e or e.startswith('-') or e.endswith('-') for e in etiquetas):
        return email, 'El dominio del correo electrónico no es válido.'

    return email, None


def validar_telefono(telefono):
    """
    Valida que el teléfono contenga únicamente dígitos (y opcionalmente +, espacios, guiones o paréntesis),
    tenga entre 10 y 15 dígitos reales y respete la longitud máxima del campo (20 caracteres).
    Retorna (telefono_limpio, mensaje_error_o_None).
    """
    tel = limpiar_texto_seguro(telefono)
    if not tel:
        return '', 'El teléfono de contacto es obligatorio.'

    if len(tel) > 20:
        return tel, 'El teléfono no puede exceder los 20 caracteres.'

    if not _RE_TELEFONO_PERMITIDO.match(tel):
        return tel, 'El teléfono solo puede contener números y separadores básicos (+, espacios, guiones).'

    digitos = re.sub(r'\D', '', tel)
    if len(digitos) < 10 or len(digitos) > 15:
        return tel, 'El teléfono debe contener entre 10 y 15 dígitos numéricos (ej. 55 1234 5678).'

    if len(set(digitos)) == 1:
        return tel, 'Ingresa un número telefónico real y válido.'

    return tel, None


def validar_razon_social(valor, etiqueta='Nombre / Razón Social'):
    """Valida nombre del local, razón social u organización (3 a 150 caracteres, sin símbolos corruptos)."""
    texto = limpiar_texto_seguro(valor)
    if not texto:
        return '', f'El campo {etiqueta} es obligatorio.'
    if len(texto) < 3:
        return texto, f'El campo {etiqueta} debe tener al menos 3 caracteres.'
    if len(texto) > 150:
        return texto, f'El campo {etiqueta} no puede superar los 150 caracteres.'
    if not _RE_RAZON_SOCIAL.match(texto) or len(re.findall(r'[A-Za-zÁÉÍÓÚáéíóúÑñÜü]', texto)) < 2:
        return texto, f'El campo {etiqueta} contiene caracteres no permitidos o es inválido.'
    return texto, None


def validar_direccion(valor):
    """Valida dirección física (5 a 255 caracteres, sin símbolos corruptos ni código HTML)."""
    texto = limpiar_texto_seguro(valor)
    if not texto:
        return '', 'La dirección es obligatoria.'
    if len(texto) < 5:
        return texto, 'La dirección es demasiado corta (mínimo 5 caracteres).'
    if len(texto) > 255:
        return texto, 'La dirección no puede superar los 255 caracteres.'
    if not _RE_DIRECCION.match(texto) or len(re.findall(r'[A-Za-zÁÉÍÓÚáéíóúÑñÜü]', texto)) < 3:
        return texto, 'La dirección contiene caracteres no permitidos. Ingresa una dirección real.'
    return texto, None


def validar_fecha_caducidad(valor_str):
    """
    Valida que la fecha de caducidad sea obligatoria, tenga formato ISO válido
    y NO sea anterior a la fecha actual (impide registrar alimentos caducados).
    Retorna (objeto_date_o_None, mensaje_error_o_None).
    """
    if not valor_str:
        return None, 'La fecha de caducidad es obligatoria.'
    try:
        fecha_cad = date.fromisoformat(str(valor_str).strip())
    except ValueError:
        return None, 'El formato de la fecha de caducidad no es válido.'

    hoy = timezone.localdate()
    if fecha_cad < hoy:
        return None, (
            f"No se pueden registrar alimentos caducados ({fecha_cad.strftime('%d/%m/%Y')}). "
            f"La fecha de caducidad debe ser hoy ({hoy.strftime('%d/%m/%Y')}) o posterior."
        )
    return fecha_cad, None


def validar_fecha_entrega(valor_str, fecha_caducidad=None):
    """
    Valida la fecha preferida de entrega (opcional).
    Si se captura, debe ser hoy o posterior y no posterior a la caducidad del alimento.
    Retorna (objeto_date_o_None, mensaje_error_o_None).
    """
    if not valor_str:
        return None, None
    try:
        fecha_ent = date.fromisoformat(str(valor_str).strip())
    except ValueError:
        return None, 'El formato de la fecha preferida de entrega no es válido.'

    hoy = timezone.localdate()
    if fecha_ent < hoy:
        return None, 'La fecha preferida de entrega no puede ser anterior al día de hoy.'
    if fecha_caducidad and fecha_ent > fecha_caducidad:
        return None, 'La fecha preferida de entrega no puede ser posterior a la fecha de caducidad del alimento.'
    return fecha_ent, None


def validar_rango_horario(hora_desde_str, hora_hasta_str):
    """
    Valida el rango horario de recolección/entrega (Desde < Hasta).
    Si ambos vienen vacíos es válido (opcional). Si solo se llena uno, exige completar el rango.
    Retorna (hora_desde_o_None, hora_hasta_o_None, mensaje_error_o_None).
    """
    desde_txt = str(hora_desde_str or '').strip()
    hasta_txt = str(hora_hasta_str or '').strip()

    if not desde_txt and not hasta_txt:
        return None, None, None

    if bool(desde_txt) != bool(hasta_txt):
        return None, None, 'Si indicas un horario de entrega, debes especificar tanto la hora "Desde" como "Hasta".'

    try:
        hora_desde = time.fromisoformat(desde_txt)
        hora_hasta = time.fromisoformat(hasta_txt)
    except ValueError:
        return None, None, 'El formato de las horas de entrega no es válido.'

    if hora_desde >= hora_hasta:
        return None, None, (
            f"El rango horario es inválido ({desde_txt} a {hasta_txt}): "
            f"la hora 'Desde' debe ser menor que la hora 'Hasta'."
        )

    return hora_desde, hora_hasta, None
