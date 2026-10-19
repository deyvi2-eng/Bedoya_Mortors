import re

from django.core.exceptions import ValidationError

# Tipos de documento de identidad aceptados para clientes
ID_CEDULA_EC = 'CEDULA_EC'
ID_RUC_EC = 'RUC_EC'
ID_CEDULA_VE = 'CEDULA_VE'
ID_CEDULA_CO = 'CEDULA_CO'

ID_TYPE_CHOICES = [
    (ID_CEDULA_EC, 'Cédula Ecuador'),
    (ID_RUC_EC, 'RUC Ecuador'),
    (ID_CEDULA_VE, 'Cédula Venezuela'),
    (ID_CEDULA_CO, 'Cédula Colombia'),
]

# Etiqueta corta para mostrar junto al número (tablas, PDFs, facturas)
ID_TYPE_SHORT = {
    ID_CEDULA_EC: 'C.I.',
    ID_RUC_EC: 'RUC',
    ID_CEDULA_VE: 'C.I. VE',
    ID_CEDULA_CO: 'C.C. CO',
}


def _provincia_valida(value):
    provincia = int(value[0:2])
    return 1 <= provincia <= 24 or provincia == 30


def validate_ecuadorian_cedula(value):
    # NUEVO: Si no hay valor (es opcional), dejamos pasar la validación
    if not value:
        return

    if len(value) != 10 or not value.isdigit():
        raise ValidationError("La cédula debe contener exactamente 10 dígitos numéricos.")
    
    if not _provincia_valida(value):
        raise ValidationError("Código de provincia inválido.")
    
    tercer_digito = int(value[2])
    if tercer_digito >= 6:
        raise ValidationError("El tercer dígito es inválido para personas naturales.")
    
    coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    total = 0
    
    for i in range(9):
        valor = int(value[i]) * coeficientes[i]
        total += valor if valor < 10 else valor - 9
        
    digito_verificador = int(value[9])
    decena_superior = ((total + 9) // 10) * 10
    calculado = decena_superior - total
    
    if calculado == 10:
        calculado = 0
        
    if calculado != digito_verificador:
        raise ValidationError("La cédula ingresada no es válida matemáticamente.")


def validate_ecuadorian_ruc(value):
    """RUC Ecuador: 13 dígitos.
    - Persona natural (3er dígito 0-5): cédula válida + establecimiento (001...).
    - Entidad pública (3er dígito 6): establecimiento de 4 dígitos (0001...).
    - Sociedad privada (3er dígito 9): establecimiento de 3 dígitos (001...).
    Para sociedades y entidades públicas no se exige el dígito verificador módulo 11,
    porque el SRI ha emitido RUCs nuevos que no lo cumplen.
    """
    if not value:
        return

    if len(value) != 13 or not value.isdigit():
        raise ValidationError("El RUC debe contener exactamente 13 dígitos numéricos.")

    if not _provincia_valida(value):
        raise ValidationError("El RUC tiene un código de provincia inválido.")

    tercer_digito = int(value[2])
    if tercer_digito <= 5:
        try:
            validate_ecuadorian_cedula(value[:10])
        except ValidationError:
            raise ValidationError("Los primeros 10 dígitos del RUC no forman una cédula válida.")
        if value[10:] == '000':
            raise ValidationError("El RUC debe terminar en el número de establecimiento (ej: 001).")
    elif tercer_digito == 6:
        if value[9:] == '0000':
            raise ValidationError("El RUC público debe terminar en el número de establecimiento (ej: 0001).")
    elif tercer_digito == 9:
        if value[10:] == '000':
            raise ValidationError("El RUC debe terminar en el número de establecimiento (ej: 001).")
    else:
        raise ValidationError("El tercer dígito del RUC es inválido (debe ser 0-5, 6 o 9).")


def normalize_venezuelan_cedula(value):
    """Acepta 'V12345678', 'v-12.345.678', '12345678' y devuelve 'V-12345678'."""
    raw = re.sub(r'[\s.\-]', '', value or '').upper()
    if raw and raw[0].isdigit():
        raw = 'V' + raw
    match = re.fullmatch(r'([VE])(\d+)', raw)
    if not match:
        raise ValidationError("La cédula venezolana debe iniciar con V o E seguida de números (ej: V-12345678).")
    letra, numero = match.groups()
    numero = numero.lstrip('0')
    if not 6 <= len(numero) <= 8:
        raise ValidationError("La cédula venezolana debe tener entre 6 y 8 dígitos.")
    return f"{letra}-{numero}"


def normalize_colombian_cedula(value):
    """Cédula de ciudadanía colombiana: 6 a 10 dígitos, se aceptan puntos."""
    raw = re.sub(r'[\s.,]', '', value or '')
    if not raw.isdigit():
        raise ValidationError("La cédula colombiana solo debe contener números.")
    if raw.startswith('0'):
        raise ValidationError("La cédula colombiana no puede iniciar con 0.")
    if not 6 <= len(raw) <= 10:
        raise ValidationError("La cédula colombiana debe tener entre 6 y 10 dígitos.")
    return raw


def normalize_identification(id_type, value):
    """Valida el documento según su tipo y lo devuelve normalizado (o None si viene vacío)."""
    value = (value or '').strip()
    if not value:
        return None

    if id_type == ID_CEDULA_EC:
        value = re.sub(r'[\s\-]', '', value)
        validate_ecuadorian_cedula(value)
        return value
    if id_type == ID_RUC_EC:
        value = re.sub(r'[\s\-]', '', value)
        validate_ecuadorian_ruc(value)
        return value
    if id_type == ID_CEDULA_VE:
        return normalize_venezuelan_cedula(value)
    if id_type == ID_CEDULA_CO:
        return normalize_colombian_cedula(value)
    raise ValidationError("Tipo de documento inválido.")
