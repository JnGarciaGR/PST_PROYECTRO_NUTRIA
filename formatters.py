"""
Módulo de formateo de mensajes para NutrIA.

Gestiona todo el formato de los mensajes que el bot envía a Telegram.
Incluye menús interactivos, teclados, análisis nutricional y respuestas
de error. El objetivo es centralizar toda la lógica de presentación
para que sea fácil de mantener y consistente.
"""

import logging
from typing import List, Tuple
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup
from telebot.types import InlineKeyboardButton

# Configurar logger para debugging
logger = logging.getLogger(__name__)


# ========== EMOJIS Y SÍMBOLOS ==========
# Constantes de emojis usados en los mensajes.
# Los mantenemos aquí para cambiarlos fácilmente en el futuro.

EMOJI_BOT = "🦦"
EMOJI_INICIO = "👋"
EMOJI_MENU = "📋"
EMOJI_COMIDA = "🍽️"
EMOJI_ERROR = "❌"
EMOJI_EXITO = "✅"
EMOJI_INFO = "ℹ️"
EMOJI_ADVERTENCIA = "⚠️"
EMOJI_PENSANDO = "🤔"
EMOJI_CARGA = "⏳"
EMOJI_GRAFICO = "📊"
EMOJI_CANDADO = "🔒"
EMOJI_COMPLETADO = "✨"


# ========== MENÚ PRINCIPAL ==========

def crear_mensaje_bienvenida(nombre: str) -> str:
    """
    Crea un mensaje de bienvenida personalizado.
    
    Args:
        nombre: Nombre del usuario
        
    Returns:
        String con el mensaje de bienvenida
    """
    mensaje = (
        f"{EMOJI_INICIO} Hola, soy *NutrIA*. "
        f"Un gusto saludarte.\n\n"
        f"¿Cómo te llamas?"
    )
    return mensaje


def crear_mensaje_ya_registrado() -> str:
    """
    Crea un mensaje para usuario ya registrado.
    
    Returns:
        String con el mensaje
    """
    mensaje = (
        f"{EMOJI_BOT}{EMOJI_ADVERTENCIA} "
        f"Ya estás registrado.\n\n"
        f"Usa /menu para ver las opciones."
    )
    return mensaje


def crear_menu_principal() -> Tuple[str, ReplyKeyboardMarkup]:
    """
    Crea el menú principal con opciones interactivas.
    
    Retorna:
        Tupla (mensaje: str, teclado: ReplyKeyboardMarkup)
    """
    mensaje = (
        f"{EMOJI_BOT}{EMOJI_MENU} *MENÚ PRINCIPAL:*\n"
        f"1️⃣ Registro/Análisis de Comida\n"
        f"2️⃣ Recomendaciones de recetas\n"
        f"3️⃣ Seguimiento Nutricional\n"
        f"4️⃣ Editar Perfil\n\n"
        f"{EMOJI_INFO} ¿Tienes dudas? "
        f"Usa /help para aprender cómo usar NutrIA."
    )
    
    teclado = ReplyKeyboardMarkup(
        one_time_keyboard=True,
        resize_keyboard=True,
        input_field_placeholder="Pulsa una opción"
    )
    teclado.add("1", "2", "3", "4")
    
    return mensaje, teclado


def crear_mensaje_registro_completado(
    nombre: str
) -> str:
    """
    Crea un mensaje de registro completado.
    
    Args:
        nombre: Nombre del usuario
        
    Returns:
        String con el mensaje
    """
    mensaje = (
        f"{EMOJI_EXITO} ¡Registro completo!\n"
        f"🎉 Bienvenido a *NutrIA*, {nombre}"
    )
    return mensaje


# ========== SELECCIÓN SIMPLE ==========

def crear_teclado_opciones(
    opciones: List[str]
) -> ReplyKeyboardMarkup:
    """
    Crea un teclado con opciones simples.
    
    Parámetros:
        opciones: Lista de opciones para mostrar en botones
        
    Retorna:
        Teclado de Telegram con las opciones
    """
    teclado = ReplyKeyboardMarkup(
        one_time_keyboard=True,
        resize_keyboard=True,
        input_field_placeholder="Pulsa una opción"
    )
    teclado.add(*opciones)
    return teclado


def crear_teclado_genero() -> ReplyKeyboardMarkup:
    """
    Crea teclado para seleccionar género.
    
    Returns:
        ReplyKeyboardMarkup con opciones de género
    """
    return crear_teclado_opciones(["Hombre", "Mujer"])


def crear_teclado_actividad() -> ReplyKeyboardMarkup:
    """
    Crea teclado para seleccionar actividad física.
    
    Returns:
        ReplyKeyboardMarkup con opciones de actividad
    """
    actividades = [
        "Sedentario", "Ligera", "Moderada",
        "Intensa", "Muy intensa"
    ]
    return crear_teclado_opciones(actividades)


def crear_teclado_economia() -> ReplyKeyboardMarkup:
    """
    Crea teclado para seleccionar nivel económico.
    
    Returns:
        ReplyKeyboardMarkup con opciones de economía
    """
    return crear_teclado_opciones(["Alta", "Media", "Baja"])


def crear_teclado_dieta() -> ReplyKeyboardMarkup:
    """
    Crea teclado para seleccionar tipo de dieta.
    
    Returns:
        ReplyKeyboardMarkup con opciones de dieta
    """
    dietas = [
        "Déficit calórico",
        "Recomposición muscular",
        "Superávit calórico"
    ]
    return crear_teclado_opciones(dietas)


def crear_teclado_tipo_comida() -> ReplyKeyboardMarkup:
    """
    Crea teclado para seleccionar tipo de comida.
    
    Returns:
        ReplyKeyboardMarkup con opciones de comida
    """
    return crear_teclado_opciones(
        ["Desayuno", "Almuerzo", "Cena"]
    )


# ========== MENSAJES CON BOTONES INLINE ==========

def crear_teclado_confirmar_reset() -> InlineKeyboardMarkup:
    """
    Crea teclado con botones de confirmar/cancelar reset.
    
    Returns:
        InlineKeyboardMarkup con los botones
    """
    teclado = InlineKeyboardMarkup()
    teclado.add(
        InlineKeyboardButton(
            "✅ Confirmar",
            callback_data='confirmar_reset'
        ),
        InlineKeyboardButton(
            "❌ Cancelar",
            callback_data='cancelar_reset'
        )
    )
    return teclado


# ========== MENSAJES DE ERROR ==========
# Funciones para generar mensajes de error formateados


def _crear_mensaje_error(campo: str, descripcion: str) -> str:
    """
    Función auxiliar para crear mensajes de error genéricos.
    
    Evita repetición de código en mensajes de error similares.
    
    Parámetros:
        campo: Nombre del campo (ej: "Cédula", "Peso")
        descripcion: Descripción del error (ej: "10 dígitos")
        
    Retorna:
        Mensaje de error formateado
    """
    return f"{EMOJI_ADVERTENCIA} {campo} inválido. {descripcion}"


def mensaje_error_cedula() -> str:
    """
    Mensaje de error para cédula inválida.
    
    Retorna:
        String con el mensaje de error
    """
    return _crear_mensaje_error(
        "Cédula",
        "Debe contener exactamente 10 dígitos."
    )


def mensaje_error_peso() -> str:
    """
    Mensaje de error para peso fuera de rango.
    
    Retorna:
        String con el mensaje de error
    """
    return _crear_mensaje_error(
        "Peso",
        "Fuera de rango (30–300 kg)."
    )


def mensaje_error_altura() -> str:
    """
    Mensaje de error para altura fuera de rango.
    
    Retorna:
        String con el mensaje de error
    """
    return _crear_mensaje_error(
        "Altura",
        "Fuera de rango (100–250 cm)."
    )


def mensaje_error_edad() -> str:
    """
    Mensaje de error para edad fuera de rango.
    
    Retorna:
        String con el mensaje de error
    """
    return _crear_mensaje_error(
        "Edad",
        "Fuera de rango (10–120 años)."
    )


def mensaje_error_numero() -> str:
    """
    Mensaje de error para número inválido.
    
    Retorna:
        String con el mensaje de error
    """
    return (
        f"{EMOJI_ERROR} Solo números. Ej: 70.5 o 170"
    )


def mensaje_error_opcion_invalida(contexto: str) -> str:
    """
    Mensaje genérico para opción de menú inválida.
    
    Parámetros:
        contexto: Contexto (ej: 'género', 'actividad')
        
    Retorna:
        String con el mensaje de error
    """
    return (
        f"{EMOJI_ERROR} ERROR: {contexto} no válido. "
        f"\nPulsa un botón."
    )


# ========== INFORMACIÓN NUTRICIONAL ==========

def crear_mensaje_analisis(
    nombre_comida: str, analisis: str
) -> str:
    """
    Crea mensaje formateado con análisis nutricional.
    
    Args:
        nombre_comida: Nombre de la comida analizada
        analisis: Texto del análisis de nutrientes
        
    Returns:
        String con el mensaje formateado
    """
    mensaje = (
        f"{EMOJI_COMIDA} *Análisis: {nombre_comida}*\n\n"
        f"{analisis}"
    )
    return mensaje


def crear_mensaje_confirmar_registro() -> str:
    """
    Crea mensaje pidiendo confirmar registro de comida.
    
    Returns:
        String con el mensaje de confirmación
    """
    return (
        f"{EMOJI_PENSANDO} ¿Deseas registrar este "
        f"alimento/receta para tu seguimiento "
        f"nutricional?\nResponde *sí* o *no*."
    )


def mensaje_comida_registrada() -> str:
    """
    Crea mensaje de comida registrada exitosamente.
    
    Returns:
        String con el mensaje de éxito
    """
    return (
        f"{EMOJI_EXITO} Alimento/Receta registrada "
        f"exitosamente."
    )


def mensaje_comida_no_registrada() -> str:
    """
    Crea mensaje de comida no registrada.
    
    Returns:
        String con el mensaje
    """
    return (
        f"{EMOJI_COMIDA} Está bien. "
        f"No se registró el alimento/receta."
    )


def mensaje_generando_recomendacion() -> str:
    """
    Crea mensaje mientras se genera recomendación.
    
    Returns:
        String con el mensaje
    """
    return f"{EMOJI_CARGA} Generando tu recomendación..."


# ========== MENSAJES DE AYUDA ==========

def mensaje_sin_perfil() -> str:
    """
    Crea mensaje para usuario sin perfil registrado.
    
    Returns:
        String con el mensaje
    """
    return (
        f"{EMOJI_ADVERTENCIA} Primero debes "
        f"completar el registro usando /start."
    )


def mensaje_sin_datos_para_recomendacion() -> str:
    """
    Crea mensaje cuando faltan datos del usuario.
    
    Returns:
        String con el mensaje
    """
    return (
        f"{EMOJI_ADVERTENCIA} No tengo tus datos de "
        f"registro para darte recomendaciones. "
        f"Por favor, usa /start para registrarte."
    )


def mensaje_no_entiendo() -> str:
    """
    Crea mensaje cuando no entiende el input.
    
    Returns:
        String con el mensaje
    """
    return (
        f"{EMOJI_PENSANDO} No entiendo. "
        f"Usa /menu para ver las opciones "
        f"o /help para una guía."
    )


def mensaje_reset_confirmado() -> str:
    """
    Crea mensaje de reset de perfil confirmado.
    
    Returns:
        String con el mensaje
    """
    return (
        f"{EMOJI_EXITO} Tu perfil ha sido borrado "
        f"exitosamente. Usa /start para crear uno nuevo."
    )


def mensaje_reset_cancelado() -> str:
    """
    Crea mensaje de reset cancelado.
    
    Returns:
        String con el mensaje
    """
    return (
        f"{EMOJI_EXITO} El borrado ha sido cancelado. "
        f"Tus datos están a salvo."
    )


# ========== EDITAR PERFIL ==========

def crear_menu_editar_perfil_inline(user) -> Tuple[str, InlineKeyboardMarkup]:
    """
    Crea menú de edición de perfil con botones inline.
    
    Los botones aparecen DENTRO del mensaje, no ocupan
    toda la pantalla como ReplyKeyboardMarkup.
    
    Parámetros:
        user: Objeto User con datos del usuario
        
    Retorna:
        Tupla (mensaje: str, teclado: InlineKeyboardMarkup)
    """
    mensaje = (
        f"{EMOJI_MENU} *📝 EDITAR PERFIL*\n\n"
        f"Tus datos actuales:\n\n"
        f"👤 *Nombre:* {user.nombre}\n"
        f"🎂 *Edad:* {user.edad} años\n"
        f"💪 *Género:* {user.genero}\n"
        f"⚖️ *Peso:* {user.peso} kg\n"
        f"📏 *Altura:* {user.altura_cm} cm\n"
        f"🏃 *Actividad Física:* {user.actividad_fisica}\n"
        f"💰 *Economía:* {user.economia}\n"
        f"🍽️ *Tipo de Dieta:* {user.dieta}\n\n"
        f"¿Qué deseas editar?"
    )
    
    teclado = InlineKeyboardMarkup(row_width=2)
    teclado.add(
        InlineKeyboardButton(
            "💰 Economía",
            callback_data="editar_economia"
        ),
        InlineKeyboardButton(
            "🏃 Actividad Física",
            callback_data="editar_actividad"
        )
    )
    teclado.add(
        InlineKeyboardButton(
            "🍽️ Tipo Dieta",
            callback_data="editar_dieta"
        ),
        InlineKeyboardButton(
            "🔐 Contraseña",
            callback_data="editar_password"
        )
    )
    teclado.add(
        InlineKeyboardButton(
            "👈 Volver al Menú",
            callback_data="volver_menu_principal"
        )
    )
    
    return mensaje, teclado


def crear_menu_editar_perfil(user) -> tuple:
    """
    Crea el menú de edición de perfil con datos actuales.
    
    DEPRECATED: Usa crear_menu_editar_perfil_inline() en su lugar.
    
    Args:
        user: Objeto User con datos del usuario
        
    Returns:
        Tupla (mensaje: str, teclado: ReplyKeyboardMarkup)
    """
    mensaje = (
        f"{EMOJI_MENU} *📝 EDITAR PERFIL*\n\n"
        f"Tus datos actuales:\n\n"
        f"👤 *Nombre:* {user.nombre}\n"
        f"🎂 *Edad:* {user.edad} años\n"
        f"💪 *Género:* {user.genero}\n"
        f"⚖️  *Peso:* {user.peso} kg\n"
        f"📏 *Altura:* {user.altura_cm} cm\n"
        f"🏃 *Actividad Física:* {user.actividad_fisica}\n"
        f"💰 *Economía:* {user.economia}\n"
        f"🍽️  *Tipo de Dieta:* {user.dieta}\n\n"
        f"¿Qué deseas editar?\n\n"
        f"1️⃣ Economía\n"
        f"2️⃣ Actividad Física\n"
        f"3️⃣ Tipo de Dieta\n"
        f"4️⃣ Contraseña Dashboard\n"
        f"0️⃣ Volver al Menú"
    )
    
    teclado = ReplyKeyboardMarkup(
        one_time_keyboard=True,
        resize_keyboard=True,
        input_field_placeholder="Selecciona una opción"
    )
    teclado.add("1", "2", "3", "4")
    teclado.add("0")
    
    return mensaje, teclado


def crear_teclado_volver_menu() -> ReplyKeyboardMarkup:
    """
    Crea teclado con botón para volver al menú.
    
    Returns:
        ReplyKeyboardMarkup con el botón
    """
    return crear_teclado_opciones(["👈 Volver al Menú"])


def mensaje_dato_actualizado(dato: str, valor: str) -> str:
    """
    Crea mensaje de dato actualizado exitosamente.
    
    Args:
        dato: Nombre del dato actualizado
        valor: Nuevo valor
        
    Returns:
        String con el mensaje de éxito
    """
    return (
        f"{EMOJI_EXITO} ¡Tu {dato} ha sido actualizado!\n\n"
        f"✅ Nuevo valor: *{valor}*"
    )


def mensaje_password_cambio_exitoso() -> str:
    """
    Crea mensaje de cambio de contraseña exitoso.
    
    Returns:
        String con el mensaje
    """
    return (
        f"{EMOJI_EXITO} ¡Contraseña actualizada exitosamente!\n\n"
        f"{EMOJI_CANDADO} Ahora puedes acceder al dashboard con:"
        f"\n• ID: Tu chat_id\n"
        f"• Contraseña: La que acabas de crear"
    )


def mensaje_password_invalido() -> str:
    """
    Crea mensaje cuando la contraseña es inválida.
    
    Returns:
        String con el mensaje
    """
    return (
        f"{EMOJI_ADVERTENCIA} La contraseña debe tener "
        f"al menos 6 caracteres.\n\n"
        f"Intenta de nuevo:"
    )
