"""
Módulo de validaciones para NutrIA.

Centraliza toda la lógica de validación de datos del usuario.
Valida tanto información personal (peso, altura, edad, etc.) como
preferencias (género, nivel de actividad, economía, tipo de dieta).

Todas las funciones retornan una tupla (es_válido, mensaje) para
facilitar el debugging y permitir mensajes personalizados de error.
"""

import logging
from typing import Tuple

# Configurar logger para debugging
logger = logging.getLogger(__name__)


# ========== CONSTANTES DE VALIDACIÓN ==========
# Límites y valores válidos usados en todas las validaciones.
# Centralizados aquí para cambiarlos fácilmente en el futuro.

CEDULA_LENGTH = 10
MIN_PESO = 30
MAX_PESO = 300
MIN_ALTURA = 100
MAX_ALTURA = 250
MIN_EDAD = 10
MAX_EDAD = 120

GENEROS_VALIDOS = ["Hombre", "Mujer"]
ACTIVIDADES_VALIDAS = [
    "Sedentario",
    "Ligera",
    "Moderada",
    "Intensa",
    "Muy intensa"
]
ECONOMIA_VALIDA = ["Alta", "Media", "Baja"]
DIETAS_VALIDAS = [
    "Déficit calórico",
    "Recomposición muscular",
    "Superávit calórico"
]


# ========== VALIDACIONES DE DATOS PERSONALES ==========

def validar_pais(pais: str) -> Tuple[bool, str]:
    """
    Valida que el país ingresado por el usuario sea un país real.
    
    El nombre del país se valida de forma muy permisiva aquí porque
    la validación real se hace con Groq en el bot principal.
    
    Args:
        pais: Nombre del país ingresado por el usuario
        
    Returns:
        Tupla (válido, mensaje) indicando si el país es válido
    """
    if not pais or len(pais.strip()) == 0:
        return False, "Por favor, ingresa un país válido"
    
    logger.debug(f"País ingresado: {pais}")
    return True, "País recibido, validando..."


def validar_peso(peso: float) -> Tuple[bool, str]:
    """
    Verifica que el peso esté dentro de rangos humanamente realistas.
    
    Rechaza pesos muy bajos (menos de 30 kg) o muy altos (más de 300 kg)
    para evitar errores de entrada del usuario.
    
    Args:
        peso: Peso en kilogramos (como float)
        
    Returns:
        Tupla (válido, mensaje) con el resultado de la validación
    """
    if peso < MIN_PESO or peso > MAX_PESO:
        return False, (
            f"Peso debe estar entre {MIN_PESO} y {MAX_PESO} kg"
        )
    
    logger.debug(f"Peso validado: {peso}kg")
    return True, "Peso válido"


def validar_altura(altura: float) -> Tuple[bool, str]:
    """
    Verifica que la altura esté dentro de rangos humanamente realistas.
    
    Rechaza alturas muy bajas (menos de 100 cm) o muy altas (más de 250 cm)
    para evitar errores de entrada del usuario.
    
    Args:
        altura: Altura en centímetros (como float)
        
    Returns:
        Tupla (válido, mensaje) con el resultado de la validación
    """
    if altura < MIN_ALTURA or altura > MAX_ALTURA:
        return False, (
            f"Altura debe estar entre {MIN_ALTURA} y "
            f"{MAX_ALTURA} cm"
        )
    
    logger.debug(f"Altura validada: {altura}cm")
    return True, "Altura válida"


def validar_edad(edad: int) -> Tuple[bool, str]:
    """
    Verifica que la edad esté dentro del rango permitido.
    
    Rechaza menores de 10 años (por restricciones de uso infantil)
    y mayores de 120 años (por ser poco realista).
    
    Args:
        edad: Edad en años (como int)
        
    Returns:
        Tupla (válido, mensaje) con el resultado de la validación
    """
    if edad < MIN_EDAD or edad > MAX_EDAD:
        return False, (
            f"Edad debe estar entre {MIN_EDAD} y {MAX_EDAD} años"
        )
    
    logger.debug(f"Edad validada: {edad} años")
    return True, "Edad válida"


# ========== VALIDACIONES DE PREFERENCIAS ==========

def validar_genero(genero: str) -> Tuple[bool, str]:
    """
    Verifica que el género sea uno de los valores permitidos.
    
    Actualmente solo permitimos "Hombre" y "Mujer" porque la API
    de Groq usa estos valores para cálculos de nutrición.
    
    Args:
        genero: Género del usuario ingresado
        
    Returns:
        Tupla (válido, mensaje) con el resultado de la validación
    """
    if genero not in GENEROS_VALIDOS:
        opciones = ", ".join(GENEROS_VALIDOS)
        return False, (
            f"Género debe ser uno de: {opciones}"
        )
    
    logger.debug(f"Género validado: {genero}")
    return True, "Género válido"


def validar_actividad_fisica(
    actividad: str
) -> Tuple[bool, str]:
    """
    Verifica que el nivel de actividad sea uno de los permitidos.
    
    Se usa para calcular el gasto calórico del usuario.
    De menor a mayor intensidad: Sedentario, Ligera, Moderada, Intensa, Muy intensa.
    
    Args:
        actividad: Nivel de actividad física ingresado
        
    Returns:
        Tupla (válido, mensaje) con el resultado de la validación
    """
    if actividad not in ACTIVIDADES_VALIDAS:
        opciones = ", ".join(ACTIVIDADES_VALIDAS)
        return False, (
            f"Actividad debe ser una de: {opciones}"
        )
    
    logger.debug(f"Actividad validada: {actividad}")
    return True, "Actividad válida"


def validar_economia(economia: str) -> Tuple[bool, str]:
    """
    Verifica que el nivel económico sea uno de los permitidos.
    
    Se usa para recomendar alimentos más o menos caros
    según el presupuesto del usuario.
    
    Args:
        economia: Nivel económico ingresado (Alta, Media, Baja)
        
    Returns:
        Tupla (válido, mensaje) con el resultado de la validación
    """
    if economia not in ECONOMIA_VALIDA:
        opciones = ", ".join(ECONOMIA_VALIDA)
        return False, (
            f"Economía debe ser una de: {opciones}"
        )
    
    logger.debug(f"Economía validada: {economia}")
    return True, "Economía válida"


def validar_dieta(dieta: str) -> Tuple[bool, str]:
    """
    Verifica que el tipo de dieta sea uno de los permitidos.
    
    Hay tres opciones: déficit calórico (perder peso), recomposición
    muscular (ganar músculo manteniendo peso) o superávit calórico (ganar peso).
    
    Args:
        dieta: Tipo de dieta ingresada
        
    Returns:
        Tupla (válido, mensaje) con el resultado de la validación
    """
    if dieta not in DIETAS_VALIDAS:
        opciones = ", ".join(DIETAS_VALIDAS)
        return False, (
            f"Dieta debe ser una de: {opciones}"
        )
    
    logger.debug(f"Dieta validada: {dieta}")
    return True, "Dieta válida"


# ========== VALIDACIONES DE FORMATO ==========

def validar_cedula(cedula: str) -> Tuple[bool, str]:
    """
    Verifica que la cédula tenga el formato correcto.
    
    Debe ser exactamente 10 dígitos numéricos sin caracteres especiales.
    
    Args:
        cedula: Cédula ingresada por el usuario
        
    Returns:
        Tupla (válido, mensaje) con el resultado de la validación
    """
    cedula_limpia = cedula.strip()
    
    if not cedula_limpia.isdigit():
        return False, "La cédula solo puede contener números"
    
    if len(cedula_limpia) != CEDULA_LENGTH:
        return (
            False,
            f"La cédula debe tener exactamente {CEDULA_LENGTH} dígitos"
        )
    
    logger.debug(f"Cédula validada: {cedula_limpia}")
    return True, "Cédula válida"


def validar_nombre(nombre: str) -> Tuple[bool, str]:
    """
    Verifica que el nombre sea válido y tenga una longitud razonable.
    
    Rechaza nombres vacíos o muy cortos, y también los que sean muy largos
    para evitar problemas de almacenamiento y display.
    
    Args:
        nombre: Nombre del usuario ingresado
        
    Returns:
        Tupla (válido, mensaje) con el resultado de la validación
    """
    nombre = nombre.strip()
    
    if not nombre:
        return False, "El nombre no puede estar vacío"
    
    if len(nombre) < 2:
        return False, "El nombre debe tener al menos 2 caracteres"
    
    if len(nombre) > 100:
        return False, "El nombre es muy largo (máx 100 caracteres)"
    
    logger.debug(f"Nombre validado: {nombre}")
    return True, "Nombre válido"


def validar_numero(numero: str) -> Tuple[bool, float]:
    """
    Intenta convertir un string a número decimal.
    
    Acepta comas y puntos como separador decimal. Es muy permisivo
    para facilitar entrada desde diferentes teclados.
    
    Args:
        numero: String con el número (puede tener coma o punto)
        
    Returns:
        Tupla (válido, valor). Si es válido, devuelve el float convertido.
        Si no, devuelve 0.0.
    """
    try:
        # Reemplazar coma por punto para decimales
        numero_limpio = numero.strip().replace(",", ".")
        valor = float(numero_limpio)
        
        logger.debug(f"Número validado: {valor}")
        return True, valor
        
    except ValueError:
        return False, 0.0


def validar_entero(numero: str) -> Tuple[bool, int]:
    """
    Intenta convertir un string a número entero.
    
    Se usa para campos como edad que requieren números sin decimales.
    
    Args:
        numero: String con el número entero
        
    Returns:
        Tupla (válido, valor). Si es válido devuelve el int convertido.
        Si no, devuelve 0.
    """
    try:
        numero_limpio = numero.strip()
        valor = int(numero_limpio)
        
        logger.debug(f"Entero validado: {valor}")
        return True, valor
        
    except ValueError:
        return False, 0


# ========== VALIDACIONES COMBINADAS ==========

def validar_usuario_datos(
    nombre: str, cedula: str, genero: str,
    peso: float, altura: float, edad: int,
    actividad: str, economia: str, dieta: str
) -> Tuple[bool, str]:
    """
    Valida todos los datos de un usuario en una sola llamada.
    
    Se ejecuta al final del registro. Si algo falla, devuelve
    un mensaje específico indicando qué campo tiene error.
    
    Args:
        nombre: Nombre del usuario
        cedula: Cédula de identidad
        genero: Género (Hombre/Mujer)
        peso: Peso en kilogramos
        altura: Altura en centímetros
        edad: Edad en años
        actividad: Nivel de actividad física
        economia: Nivel económico (Alta/Media/Baja)
        dieta: Tipo de dieta
        
    Returns:
        Tupla (válido, mensaje). Si hay error, el mensaje especifica
        qué campo falló.
    """
    # Validar nombre
    valido_nombre, msg_nombre = validar_nombre(nombre)
    if not valido_nombre:
        return False, f"Nombre: {msg_nombre}"
    
    # Validar cédula
    valido_cedula, msg_cedula = validar_cedula(cedula)
    if not valido_cedula:
        return False, f"Cédula: {msg_cedula}"
    
    # Validar género
    valido_genero, msg_genero = validar_genero(genero)
    if not valido_genero:
        return False, f"Género: {msg_genero}"
    
    # Validar peso
    valido_peso, msg_peso = validar_peso(peso)
    if not valido_peso:
        return False, f"Peso: {msg_peso}"
    
    # Validar altura
    valido_altura, msg_altura = validar_altura(altura)
    if not valido_altura:
        return False, f"Altura: {msg_altura}"
    
    # Validar edad
    valido_edad, msg_edad = validar_edad(edad)
    if not valido_edad:
        return False, f"Edad: {msg_edad}"
    
    # Validar actividad física
    valido_act, msg_act = validar_actividad_fisica(actividad)
    if not valido_act:
        return False, f"Actividad: {msg_act}"
    
    # Validar nivel económico
    valido_eco, msg_eco = validar_economia(economia)
    if not valido_eco:
        return False, f"Economía: {msg_eco}"
    
    # Validar tipo de dieta
    valido_dieta, msg_dieta = validar_dieta(dieta)
    if not valido_dieta:
        return False, f"Dieta: {msg_dieta}"
    
    logger.info("Todos los datos del usuario validados correctamente")
    return True, "Todos los datos son válidos"
