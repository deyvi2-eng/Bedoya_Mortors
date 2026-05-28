from django.core.exceptions import ValidationError

def validate_ecuadorian_cedula(value):
    # NUEVO: Si no hay valor (es opcional), dejamos pasar la validación
    if not value:
        return

    if len(value) != 10 or not value.isdigit():
        raise ValidationError("La cédula debe contener exactamente 10 dígitos numéricos.")
    
    provincia = int(value[0:2])
    if provincia < 1 or (provincia > 24 and provincia != 30):
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