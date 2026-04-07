"""
Punto de entrada principal del bot NutrIA en Telegram.

Este archivo orquesta todos los servicios (Firebase, Groq, Telegram)
y maneja cada evento que llega del usuario. La arquitectura es modular:
cada handler recibe un evento y delega el trabajo a los servicios.

Estructura:
- Inicialización de servicios (Telegram, Firebase, Groq)
- Comandos globales (/start, /menu, /help, /reset)
- Lógica de registro de usuario
- Lógica de análisis de comidas
- Lógica de edición de perfil
- Manejo de estados y errores
"""

import logging
import requests
import subprocess
import sys
import time
from pathlib import Path
from config import TELEGRAM_TOKEN, GROQ_API_KEY
from telebot import TeleBot
from telebot.types import Message, ReplyKeyboardRemove

from user_model import User, NutritionData
from firebase_service import FirebaseService
from groq_service import GroqService
from state_manager import StateManager
import validators
import formatters

# Configurar logging para que vemos todo lo que hace el bot
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Inicializar todos los servicios principales
bot = TeleBot(TELEGRAM_TOKEN)
firebase_service = FirebaseService(
    "serviceAccountKey.json",
    "https://nutribot-3d198-default-rtdb.firebaseio.com/"
)
groq_service = GroqService(GROQ_API_KEY, firebase_service)
state_manager = StateManager()

logger.info("NutrIA Bot inicializado - servicios listos")


# ========== COMANDOS GLOBALES ==========
# Estos comandos están disponibles en cualquier momento

@bot.message_handler(commands=['start'])
def handle_start(message: Message) -> None:
    """
    Recibe el comando /start y comienza el flujo apropiado.
    
    Si es un usuario nuevo, inicia el flujo de registro.
    Si ya está registrado, lo lleva directo al menú principal.
    
    Args:
        message: Objeto Message de Telegram con info del usuario
    """
    chat_id = message.chat.id
    
    # Verificar si usuario existe
    if firebase_service.usuario_existe(chat_id):
        state_manager.establecer_estado(chat_id, "menu")
        bot.send_message(
            chat_id,
            formatters.crear_mensaje_ya_registrado()
        )
        return
    
    # Inicializar nuevo usuario
    state_manager.inicializar_usuario(chat_id)
    bot.send_message(
        chat_id,
        formatters.crear_mensaje_bienvenida(""),
        parse_mode="Markdown"
    )


@bot.message_handler(commands=['menu'])
def handle_menu(message: Message) -> None:
    """
    Recibe el comando /menu para mostrar las opciones principales.
    
    Valida que el usuario esté registrado, y si no, lo avisa.
    Luego muestra el menú con los 4 botones principales.
    
    Args:
        message: Objeto Message de Telegram
    """
    chat_id = message.chat.id
    
    # Verificar que esté registrado
    if not firebase_service.usuario_existe(chat_id):
        bot.send_message(
            chat_id,
            formatters.mensaje_sin_perfil()
        )
        return
    
    state_manager.establecer_estado(chat_id, "menu")
    menu_texto, menu_teclado = (
        formatters.crear_menu_principal()
    )
    bot.send_message(
        chat_id,
        menu_texto,
        parse_mode="Markdown",
        reply_markup=menu_teclado
    )


@bot.message_handler(commands=['help'])
def handle_help(message: Message) -> None:
    """
    Recibe el comando /help para mostrar la guía de uso.
    
    Explica de forma detallada qué es cada opción del menú
    y cómo usarla. Es el punto de entrada para usuarios que no saben qué hacer.
    
    Args:
        message: Objeto Message de Telegram
    """
    chat_id = message.chat.id
    
    ayuda = (
        f"{formatters.EMOJI_BOT} "
        f"<u>¿Cómo usar NutrIA Assistant?</u> "
        f"{formatters.EMOJI_BOT}\n\n"
        f"Aquí tienes una guía de lo que puedes hacer "
        f"con el bot:\n\n"
        f"1️⃣ <b>Registro / Análisis de comida</b>\n"
        f"Escribe lo que comiste o piensas comer. "
        f"NutrIA te dirá cuántas <u>calorías, proteínas, "
        f"carbohidratos y grasas</u> contiene tu alimento. "
        f"Podrás decidir si deseas guardar ese análisis "
        f"como parte de tu seguimiento.\n\n"
        f"2️⃣ <b>Recomendaciones de comidas</b>\n"
        f"NutrIA te sugiere recetas saludables y "
        f"económicas según tu tipo de dieta "
        f"<b>(déficit calórico, recomposición muscular "
        f"o superávit calórico)</b> y tu estabilidad "
        f"económica.\n\n"
        f"3️⃣ <b>Seguimiento nutricional</b>\n"
        f"Aquí se guarda todo lo que decidiste registrar. "
        f"Puedes revisar tu consumo diario, semanal o "
        f"mensual.\n\n"
        f"4️⃣ <b>Editar perfil</b>\n"
        f"¿Cambió tu situación económica? Aquí puedes "
        f"actualizar tus datos para que NutrIA siga "
        f"adaptándose a tus necesidades.\n\n"
        f"---\n\n"
        f"Para volver al menú principal escribe /menu."
    )
    
    bot.send_message(chat_id, ayuda, parse_mode="html")


@bot.message_handler(commands=['reset'])
def handle_reset(message: Message) -> None:
    """
    Recibe el comando /reset para borrar el perfil del usuario.
    
    Antes de eliminar, pide confirmación con botones porque es una
    operación destructiva. Si confirma, borra todo de Firebase.
    
    Args:
        message: Objeto Message de Telegram
    """
    chat_id = message.chat.id
    
    # Verificar que exista
    if not firebase_service.usuario_existe(chat_id):
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_ADVERTENCIA} "
            f"No tienes un perfil registrado para borrar. "
            f"Usa /start para crear uno."
        )
        return
    
    # Pedir confirmación
    mensaje_confirmation = (
        f"{formatters.EMOJI_ADVERTENCIA} "
        f"Estás a punto de borrar todos tus datos "
        f"de perfil.\n¿Estás seguro de que quieres "
        f"continuar?"
    )
    teclado = (
        formatters.crear_teclado_confirmar_reset()
    )
    
    bot.send_message(
        chat_id,
        mensaje_confirmation,
        reply_markup=teclado
    )


@bot.callback_query_handler(
    func=lambda call: call.data in [
        'confirmar_reset', 'cancelar_reset'
    ]
)
def handle_reset_callback(call) -> None:
    """
    Procesa la respuesta del usuario a la confirmación de borrado.
    
    Si confirma, elimina al usuario completamente de Firebase
    y de la memoria local del bot. Si cancela, no hace nada.
    
    Args:
        call: Callback query cuando el usuario pulsa un botón
    """
    chat_id = call.message.chat.id
    
    bot.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=call.message.message_id,
        reply_markup=None
    )
    
    if call.data == 'confirmar_reset':
        # Eliminar de Firebase
        if firebase_service.eliminar_usuario(chat_id):
            # Limpiar completamente del state_manager
            state_manager.limpiar_usuario_completamente(chat_id)
            bot.send_message(
                chat_id,
                formatters.mensaje_reset_confirmado()
            )
            logger.info(f"✅ Usuario {chat_id} eliminado (Firebase + caché)")
        else:
            bot.send_message(
                chat_id,
                f"{formatters.EMOJI_ERROR} "
                f"Ocurrió un error al intentar borrar "
                f"tu perfil."
            )
    else:
        bot.send_message(
            chat_id,
            formatters.mensaje_reset_cancelado()
        )


# ========== EDITAR PERFIL - CALLBACKS INLINE ==========
# El usuario pulsa botones para elegir qué campo editar

@bot.callback_query_handler(
    func=lambda call: call.data in [
        'editar_economia', 'editar_actividad', 'editar_dieta',
        'editar_password', 'volver_menu_principal'
    ]
)
def handle_editar_perfil_callback(call) -> None:
    """
    Procesa cuando el usuario pulsa un botón del menú de edición.
    
    Cada botón lleva a un estado diferente del bot que espera una respuesta
    específica (seleccionar economía, actividad, etc.).
    
    Args:
        call: Callback query cuando el usuario pulsa un botón inline
    """
    chat_id = call.message.chat.id
    callback_data = call.data
    
    # Eliminar el "loading" de Telegram
    bot.answer_callback_query(call.id)
    
    # Editar el mensaje anterior para remover los botones
    try:
        bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=None
        )
    except Exception as e:
        logger.debug(f"No se pudo editar el mensaje: {e}")
    
    if callback_data == 'editar_economia':
        state_manager.establecer_estado(
            chat_id, "editar_economia"
        )
        teclado = formatters.crear_teclado_economia()
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_BOT} Selecciona tu nueva economía:",
            reply_markup=teclado
        )
    
    elif callback_data == 'editar_actividad':
        logger.info(f"[CALLBACK] Usuario {chat_id}: Entrando a editar_actividad")
        state_manager.establecer_estado(
            chat_id, "editar_actividad"
        )
        estado_verificado = state_manager.obtener_estado(chat_id)
        logger.info(f"[CALLBACK] Estado después de establecer: {estado_verificado}")
        teclado = formatters.crear_teclado_actividad()
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_BOT} Selecciona tu nueva actividad física:",
            reply_markup=teclado
        )
    
    elif callback_data == 'editar_dieta':
        state_manager.establecer_estado(
            chat_id, "editar_dieta"
        )
        teclado = formatters.crear_teclado_dieta()
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_BOT} Selecciona tu nuevo tipo de dieta:",
            reply_markup=teclado
        )
    
    elif callback_data == 'editar_password':
        state_manager.establecer_estado(
            chat_id, "editar_password"
        )
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_CANDADO} Ingresa una nueva contraseña "
            f"(mínimo 6 caracteres):"
        )
    
    elif callback_data == 'volver_menu_principal':
        state_manager.establecer_estado(chat_id, "menu")
        menu_texto, menu_teclado = (
            formatters.crear_menu_principal()
        )
        bot.send_message(
            chat_id,
            menu_texto,
            parse_mode="Markdown",
            reply_markup=menu_teclado
        )


# ========== EDITAR PERFIL - HANDLERS DE TEXTO ==========
# El usuario ingresa su nueva selección (luego de pulsar un botón)

@bot.message_handler(
    func=lambda m: (
        state_manager.obtener_estado(m.chat.id)
        == "editar_economia"
    )
)
def handle_editar_economia(message: Message) -> None:
    """
    Recibe la nueva economía que eligió el usuario.
    
    Valida que sea una opción válida, actualiza Firebase,
    y muestra el menú de edición nuevamente para que siga editando
    o vuelva al menú principal.
    
    Args:
        message: Objeto Message con el texto que escribió el usuario
    """
    chat_id = message.chat.id
    economia = message.text.strip().capitalize()
    
    valido, msg = validators.validar_economia(economia)
    if not valido:
        bot.send_message(
            chat_id,
            formatters.mensaje_error_opcion_invalida("Economía")
        )
        teclado = formatters.crear_teclado_economia()
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_BOT} Pulsa un botón:",
            reply_markup=teclado
        )
        return
    
    if firebase_service.actualizar_dato_usuario(chat_id, 'economia', economia):
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_EXITO} ¡Economía actualizada a: {economia}!"
        )
        logger.info(f"Usuario {chat_id} actualizó economía a {economia}")
    else:
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_ERROR} Error al actualizar datos."
        )
    
    user = firebase_service.cargar_usuario(chat_id)
    if user:
        menu_texto, menu_teclado = formatters.crear_menu_editar_perfil_inline(user)
        bot.send_message(chat_id, menu_texto, parse_mode="Markdown", reply_markup=menu_teclado)


@bot.message_handler(
    func=lambda m: (
        state_manager.obtener_estado(m.chat.id)
        == "editar_actividad"
    )
)
def handle_editar_actividad(message: Message) -> None:
    """
    Recibe el nuevo nivel de actividad que eligió el usuario.
    
    Valida, actualiza Firebase, y vuelve a mostrar el menú de edición.
    
    Args:
        message: Objeto Message con el texto que escribió el usuario
    """
    chat_id = message.chat.id
    actividad = message.text.strip()
    logger.info(f"[handle_editar_actividad] Usuario {chat_id}: '{actividad}'")
    
    valido, msg = validators.validar_actividad_fisica(actividad)
    if not valido:
        bot.send_message(
            chat_id,
            formatters.mensaje_error_opcion_invalida("Actividad física")
        )
        teclado = formatters.crear_teclado_actividad()
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_BOT} Pulsa un botón:",
            reply_markup=teclado
        )
        return
    
    if firebase_service.actualizar_dato_usuario(chat_id, 'actividad_fisica', actividad):
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_EXITO} ¡Actividad actualizada a: {actividad}!"
        )
        logger.info(f"Usuario {chat_id} actualizó actividad a {actividad}")
    else:
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_ERROR} Error al actualizar datos."
        )
    
    user = firebase_service.cargar_usuario(chat_id)
    if user:
        menu_texto, menu_teclado = formatters.crear_menu_editar_perfil_inline(user)
        bot.send_message(chat_id, menu_texto, parse_mode="Markdown", reply_markup=menu_teclado)


@bot.message_handler(
    func=lambda m: (
        state_manager.obtener_estado(m.chat.id)
        == "editar_dieta"
    )
)
def handle_editar_dieta(message: Message) -> None:
    """
    Recibe el nuevo tipo de dieta que eligió el usuario.
    
    Valida, actualiza Firebase, y vuelve a mostrar el menú de edición.
    
    Args:
        message: Objeto Message con el texto que escribió el usuario
    """
    chat_id = message.chat.id
    dieta = message.text.strip()
    
    valido, msg = validators.validar_dieta(dieta)
    if not valido:
        bot.send_message(
            chat_id,
            formatters.mensaje_error_opcion_invalida("Tipo de dieta")
        )
        teclado = formatters.crear_teclado_dieta()
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_BOT} Pulsa un botón:",
            reply_markup=teclado
        )
        return
    
    if firebase_service.actualizar_dato_usuario(chat_id, 'dieta', dieta):
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_EXITO} ¡Dieta actualizada a: {dieta}!"
        )
        logger.info(f"Usuario {chat_id} actualizó dieta a {dieta}")
    else:
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_ERROR} Error al actualizar datos."
        )
    
    user = firebase_service.cargar_usuario(chat_id)
    if user:
        menu_texto, menu_teclado = formatters.crear_menu_editar_perfil_inline(user)
        bot.send_message(chat_id, menu_texto, parse_mode="Markdown", reply_markup=menu_teclado)


@bot.message_handler(
    func=lambda m: (
        state_manager.obtener_estado(m.chat.id)
        == "editar_password"
    )
)
def handle_editar_password(message: Message) -> None:
    """
    Recibe la nueva contraseña que ingresó el usuario.
    
    Valida que tenga mínimo 6 caracteres, la guarda en Firebase (hasheada),
    y vuelve a mostrar el menú de edición.
    
    Args:
        message: Objeto Message con el texto que escribió el usuario
    """
    chat_id = message.chat.id
    contraseña = message.text.strip()
    
    if len(contraseña) < 6:
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_ERROR} La contraseña debe tener al menos 6 caracteres."
        )
        return
    
    if firebase_service.guardar_password(chat_id, contraseña):
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_EXITO} ¡Contraseña actualizada correctamente!"
        )
        logger.info(f"Usuario {chat_id} actualizó contraseña")
    else:
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_ERROR} Error al actualizar contraseña."
        )
    
    user = firebase_service.cargar_usuario(chat_id)
    if user:
        menu_texto, menu_teclado = formatters.crear_menu_editar_perfil_inline(user)
        bot.send_message(chat_id, menu_texto, parse_mode="Markdown", reply_markup=menu_teclado)


# ========== REGISTRO DE USUARIO ==========
# El usuario pasa por varios pasos: nombre, edad, peso, altura, etc.

@bot.message_handler(
    func=lambda m: (
        state_manager.obtener_estado(m.chat.id)
        == "registro_nombre"
    )
)
def handle_registro_nombre(message: Message) -> None:
    """
    Maneja el registro del nombre del usuario.
    
    Args:
        message: Mensaje de Telegram
    """
    chat_id = message.chat.id
    nombre = message.text.strip().capitalize()
    
    # Validar nombre
    valido, msg = validators.validar_nombre(nombre)
    if not valido:
        bot.send_message(chat_id, msg)
        return
    
    # Guardar y continuar
    state_manager.guardar_dato_usuario(
        chat_id, 'nombre', nombre
    )
    state_manager.establecer_estado(
        chat_id, "registro_pais"
    )
    
    bot.send_message(
        chat_id,
        f"{formatters.EMOJI_BOT} ¡Mucho gusto, {nombre}!"
    )
    bot.send_message(
        chat_id,
        f"{formatters.EMOJI_BOT} ¿En qué país resides?"
    )


@bot.message_handler(
    func=lambda m: (
        state_manager.obtener_estado(m.chat.id)
        == "registro_pais"
    )
)
def handle_registro_pais(message: Message) -> None:
    """
    Maneja el registro del país del usuario.
    
    Valida que el país ingresado sea real usando Groq.
    
    Args:
        message: Mensaje de Telegram
    """
    chat_id = message.chat.id
    pais = message.text.strip()
    
    # Validación básica
    valido, msg = validators.validar_pais(pais)
    if not valido:
        bot.send_message(chat_id, msg)
        return
    
    # Validar que sea un país real usando Groq
    es_pais = groq_service.validar_es_pais(pais)
    if not es_pais:
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_ERROR} '{pais}' no corresponde a un país válido. "
            f"Por favor, ingresa el nombre de un país real (ej: Colombia, España, Perú, etc.):"
        )
        return
    
    # Guardar y continuar
    state_manager.guardar_dato_usuario(
        chat_id, 'pais', pais
    )
    state_manager.establecer_estado(
        chat_id, "registro_genero"
    )
    
    teclado = formatters.crear_teclado_genero()
    bot.send_message(
        chat_id,
        f"{formatters.EMOJI_BOT} Indica tu sexo:",
        reply_markup=teclado
    )


@bot.message_handler(
    func=lambda m: (
        state_manager.obtener_estado(m.chat.id)
        == "registro_genero"
    )
)
def handle_registro_genero(message: Message) -> None:
    """
    Maneja el registro del género del usuario.
    
    Args:
        message: Mensaje de Telegram
    """
    chat_id = message.chat.id
    genero = message.text.strip()
    
    # Validar género
    valido, msg = (
        validators.validar_genero(genero)
    )
    if not valido:
        bot.send_message(
            chat_id,
            formatters.mensaje_error_opcion_invalida(
                "Sexo"
            )
        )
        teclado = (
            formatters.crear_teclado_genero()
        )
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_BOT} Indica tu sexo:",
            reply_markup=teclado
        )
        return
    
    # Guardar y continuar
    state_manager.guardar_dato_usuario(
        chat_id, 'genero', genero
    )
    state_manager.establecer_estado(
        chat_id, "registro_peso"
    )
    
    bot.send_message(
        chat_id,
        f"{formatters.EMOJI_BOT} Ingresa tu peso "
        f"en kilogramos (ej. 70.5):"
    )


@bot.message_handler(
    func=lambda m: (
        state_manager.obtener_estado(m.chat.id)
        == "registro_peso"
    )
)
def handle_registro_peso(message: Message) -> None:
    """
    Maneja el registro del peso del usuario.
    
    Args:
        message: Mensaje de Telegram
    """
    chat_id = message.chat.id
    
    # Convertir a float
    valido, peso = (
        validators.validar_numero(message.text)
    )
    if not valido:
        bot.send_message(
            chat_id,
            formatters.mensaje_error_numero()
        )
        return
    
    # Validar peso
    valido, msg = validators.validar_peso(peso)
    if not valido:
        bot.send_message(chat_id, msg)
        return
    
    # Guardar y continuar
    state_manager.guardar_dato_usuario(
        chat_id, 'peso', peso
    )
    state_manager.establecer_estado(
        chat_id, "registro_altura"
    )
    
    bot.send_message(
        chat_id,
        f"{formatters.EMOJI_BOT} Ingresa tu altura "
        f"en centímetros (ej. 170):"
    )


@bot.message_handler(
    func=lambda m: (
        state_manager.obtener_estado(m.chat.id)
        == "registro_altura"
    )
)
def handle_registro_altura(message: Message) -> None:
    """
    Maneja el registro de la altura del usuario.
    
    Args:
        message: Mensaje de Telegram
    """
    chat_id = message.chat.id
    
    # Convertir a float
    valido, altura = (
        validators.validar_numero(message.text)
    )
    if not valido:
        bot.send_message(
            chat_id,
            formatters.mensaje_error_numero()
        )
        return
    
    # Validar altura
    valido, msg = (
        validators.validar_altura(altura)
    )
    if not valido:
        bot.send_message(chat_id, msg)
        return
    
    # Guardar y continuar
    state_manager.guardar_dato_usuario(
        chat_id, 'altura_cm', altura
    )
    state_manager.establecer_estado(
        chat_id, "registro_edad"
    )
    
    bot.send_message(
        chat_id,
        f"{formatters.EMOJI_BOT} Indica tu edad:"
    )


@bot.message_handler(
    func=lambda m: (
        state_manager.obtener_estado(m.chat.id)
        == "registro_edad"
    )
)
def handle_registro_edad(message: Message) -> None:
    """
    Maneja el registro de la edad del usuario.
    
    Args:
        message: Mensaje de Telegram
    """
    chat_id = message.chat.id
    
    # Convertir a int
    valido, edad = (
        validators.validar_entero(message.text)
    )
    if not valido:
        bot.send_message(
            chat_id,
            formatters.mensaje_error_numero()
        )
        return
    
    # Validar edad
    valido, msg = validators.validar_edad(edad)
    if not valido:
        bot.send_message(chat_id, msg)
        return
    
    # Guardar y continuar
    state_manager.guardar_dato_usuario(
        chat_id, 'edad', edad
    )
    state_manager.establecer_estado(
        chat_id, "registro_actividad"
    )
    
    teclado = (
        formatters.crear_teclado_actividad()
    )
    bot.send_message(
        chat_id,
        f"{formatters.EMOJI_BOT} Indica tu nivel de "
        f"actividad física:",
        reply_markup=teclado
    )


@bot.message_handler(
    func=lambda m: (
        state_manager.obtener_estado(m.chat.id)
        == "registro_actividad"
    )
)
def handle_registro_actividad(message: Message) -> None:
    """
    Maneja el registro de la actividad física.
    
    Args:
        message: Mensaje de Telegram
    """
    chat_id = message.chat.id
    actividad = message.text.strip()
    
    # Validar actividad
    valido, msg = (
        validators.validar_actividad_fisica(actividad)
    )
    if not valido:
        bot.send_message(
            chat_id,
            formatters.mensaje_error_opcion_invalida(
                "Actividad"
            )
        )
        teclado = (
            formatters.crear_teclado_actividad()
        )
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_BOT} Indica tu nivel:",
            reply_markup=teclado
        )
        return
    
    # Guardar y continuar
    state_manager.guardar_dato_usuario(
        chat_id, 'actividad_fisica', actividad
    )
    state_manager.establecer_estado(
        chat_id, "registro_economia"
    )
    
    teclado = (
        formatters.crear_teclado_economia()
    )
    bot.send_message(
        chat_id,
        f"{formatters.EMOJI_BOT} ¿Cuál es tu "
        f"estabilidad económica?",
        reply_markup=teclado
    )


@bot.message_handler(
    func=lambda m: (
        state_manager.obtener_estado(m.chat.id)
        == "registro_economia"
    )
)
def handle_registro_economia(message: Message) -> None:
    """
    Maneja el registro de la economía del usuario.
    
    Args:
        message: Mensaje de Telegram
    """
    chat_id = message.chat.id
    economia = message.text.strip().capitalize()
    
    # Validar economía
    valido, msg = (
        validators.validar_economia(economia)
    )
    if not valido:
        bot.send_message(
            chat_id,
            formatters.mensaje_error_opcion_invalida(
                "Economía"
            )
        )
        teclado = (
            formatters.crear_teclado_economia()
        )
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_BOT} Pulsa un botón:",
            reply_markup=teclado
        )
        return
    
    # Guardar y continuar
    state_manager.guardar_dato_usuario(
        chat_id, 'economia', economia
    )
    state_manager.establecer_estado(
        chat_id, "registro_dieta"
    )
    
    teclado = formatters.crear_teclado_dieta()
    bot.send_message(
        chat_id,
        f"{formatters.EMOJI_BOT} ¿Cuál es tu tipo "
        f"de dieta realizas o desea realizar?",
        reply_markup=teclado
    )
    
    info_dieta = (
        f"{formatters.EMOJI_INFO} <b>Déficit "
        f"calórico:</b> Pierdes grasa corporal "
        f"consumiendo menos calorías.\n"
        f"{formatters.EMOJI_INFO} <b>Recomposición "
        f"muscular:</b> Ganas músculo y pierdes grasa "
        f"con una dieta balanceada.\n"
        f"{formatters.EMOJI_INFO} <b>Superávit "
        f"calórico:</b> Aumentas masa muscular "
        f"comiendo más calorías."
    )
    bot.send_message(chat_id, info_dieta, parse_mode="html")


@bot.message_handler(
    func=lambda m: (
        state_manager.obtener_estado(m.chat.id)
        == "registro_dieta"
    )
)
def handle_registro_dieta(message: Message) -> None:
    """
    Maneja el registro del tipo de dieta y completa
    el registro del usuario.
    
    Args:
        message: Mensaje de Telegram
    """
    chat_id = message.chat.id
    dieta = message.text.strip()
    
    # Validar dieta
    valido, msg = validators.validar_dieta(dieta)
    if not valido:
        bot.send_message(
            chat_id,
            formatters.mensaje_error_opcion_invalida(
                "Dieta"
            )
        )
        teclado = formatters.crear_teclado_dieta()
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_BOT} Selecciona una "
            f"opción:",
            reply_markup=teclado
        )
        return
    
    # Guardar dieta
    state_manager.guardar_dato_usuario(
        chat_id, 'dieta', dieta
    )
    
    # Crear User ANTES de guardar en Firebase
    datos = state_manager._datos_usuario.get(chat_id, {})
    logger.debug(
        f"Datos temporales para usuario {chat_id}: {datos}"
    )
    
    user = User(chat_id)
    user.nombre = datos.get('nombre')
    user.pais = datos.get('pais')
    user.genero = datos.get('genero')
    user.peso = datos.get('peso')
    user.altura_cm = datos.get('altura_cm')
    user.edad = datos.get('edad')
    user.actividad_fisica = datos.get('actividad_fisica')
    user.economia = datos.get('economia')
    user.dieta = datos.get('dieta')
    
    logger.debug(
        f"User construido para {chat_id}: completo={user.esta_completo()}, "
        f"nombre={user.nombre}, pais={user.pais}, genero={user.genero}, "
        f"peso={user.peso}, altura={user.altura_cm}, edad={user.edad}, "
        f"actividad={user.actividad_fisica}, economia={user.economia}, "
        f"dieta={user.dieta}"
    )
    
    # Guardar en Firebase PRIMERO
    if firebase_service.guardar_usuario(user):
        # DESPUÉS de guardar, LIMPIAR datos temporales
        state_manager.limpiar_datos_usuario(chat_id)
        
        # DESPUÉS de guardar, establecer estado a menu
        state_manager.establecer_estado(chat_id, "menu")
        
        # Éxito
        bot.send_message(
            chat_id,
            formatters.crear_mensaje_registro_completado(
                user.nombre
            ),
            parse_mode="Markdown"
        )
        
        # Mostrar menú
        menu_texto, menu_teclado = (
            formatters.crear_menu_principal()
        )
        bot.send_message(
            chat_id,
            menu_texto,
            parse_mode="Markdown",
            reply_markup=menu_teclado
        )
        
        logger.info(
            f"Usuario {chat_id} registrado exitosamente"
        )
    else:
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_ERROR} Error al "
            f"guardar tu perfil."
        )
        logger.error(
            f"Error guardando usuario {chat_id}"
        )


# ========== FUNCIÓN AUXILIAR PARA MANEJADORES ==========

def deberia_usar_handle_default(m: Message) -> bool:
    """
    Determina si un mensaje debe ser capturado por handle_default.
    
    Retorna False para estados que tienen manejadores específicos.
    Esto previene conflictos cuando el usuario está en un estado
    específico (como editar_perfil_menu) y presiona un número.
    
    NOTA: "registro_comida" y "espera_tipo_comida" NO están excluidos
    porque SÍ tienen manejo específico dentro de handle_default.
    
    Args:
        m: Mensaje de Telegram
        
    Returns:
        True si handle_default debe procesar, False si otro manejador es responsable
    """
    chat_id = m.chat.id
    estado = state_manager.obtener_estado(chat_id)
    
    # Estados que tienen manejadores específicos del decorador
    # handle_default NO captura estos (registros que tienen @decorador específico)
    estados_exclusivos = {
        "registro_nombre", "registro_pais", "registro_genero",
        "registro_peso", "registro_altura", "registro_edad",
        "registro_actividad", "registro_economia", "registro_dieta",
        "editar_economia", "editar_actividad",
        "editar_dieta", "editar_password"
    }
    # NOTA: Estos estados SÍ tienen código en handle_default:
    # - "confirmar_registro"
    # - "registro_usuario_dashboard"
    # - "registro_password_dashboard"
    
    return estado not in estados_exclusivos


# ========== MANEJADOR GENERAL ==========

@bot.message_handler(func=deberia_usar_handle_default)
def handle_default(message: Message) -> None:
    """
    Manejador por defecto para mensajes no clasificados.
    
    NOTA: No captura mensajes de estados específicos que tienen
    manejadores dedicados (registro, editar, etc.).
    
    Args:
        message: Mensaje de Telegram
    """
    chat_id = message.chat.id
    estado = state_manager.obtener_estado(chat_id)
    logger.debug(f"[handle_default] chat_id={chat_id}, estado='{estado}', texto='{message.text}'")
    
    # Si está en menú, procesar opción
    if estado == "menu":
        opcion = message.text.strip()
        
        # IMPORTANTE: Solo procesar opciones de menú si estamos ÉN EL MENÚ
        # Si el usuario presiona "1", "2", etc. desde otro estado (ej: editar_perfil_menu),
        # eso debe ser manejado por el manejador específico de ese estado
        if len(opcion) == 1 and opcion in ["0", "1", "2", "3", "4"]:
            if opcion == "1":
                state_manager.establecer_estado(
                    chat_id, "registro_comida"
                )
                bot.send_message(
                    chat_id,
                    f"{formatters.EMOJI_COMIDA} Escribe el "
                    f"nombre del plato o comida que deseas "
                    f"analizar:",
                    reply_markup=ReplyKeyboardRemove()
                )
            elif opcion == "2":
                logger.debug(
                    f"Usuario {chat_id} seleccionó opción 2 "
                    f"(recomendaciones). Verificando si existe."
                )
                existe = firebase_service.usuario_existe(chat_id)
                logger.debug(
                    f"Verificación de usuario {chat_id}: existe={existe}"
                )
                
                if existe:
                    state_manager.establecer_estado(
                        chat_id,
                        "espera_tipo_comida"
                    )
                    # Cerrar teclado anterior
                    bot.send_message(
                        chat_id,
                        f"{formatters.EMOJI_BOT} Cargando opciones...",
                        reply_markup=ReplyKeyboardRemove()
                    )
                    teclado = (
                        formatters.crear_teclado_tipo_comida()
                    )
                    bot.send_message(
                        chat_id,
                        f"{formatters.EMOJI_BOT} ¿Para qué "
                        f"comida del día deseas la "
                        f"recomendación?",
                        reply_markup=teclado
                    )
                else:
                    logger.warning(
                        f"Usuario {chat_id} no existe en Firebase"
                    )
                    bot.send_message(
                        chat_id,
                        formatters.mensaje_sin_perfil()
                    )
            elif opcion == "3":
                # Opción 3: Seguimiento Nutricional
                # Verificar si el usuario tiene credenciales registradas
                tiene_password = (
                    firebase_service.usuario_tiene_password(chat_id)
                )
                
                if tiene_password:
                    # Si ya tiene credenciales, enviar enlace al dashboard
                    url_dashboard = (
                        "https://JnGarciaGR.github.io/NutrIA-Dashboard/"
                    )
                    bot.send_message(
                        chat_id,
                        f"{formatters.EMOJI_GRAFICO} "
                        f"Tu Dashboard está listo.\n\n"
                        f"🔗 Accede aquí: {url_dashboard}\n\n"
                        f"ID de Telegram: `{chat_id}`\n"
                        f"Contraseña: La que registraste",
                        parse_mode="Markdown"
                    )
                else:
                    # Si no tiene credenciales, pedir que las registre
                    state_manager.establecer_estado(
                        chat_id, "registro_password_dashboard"
                    )
                    bot.send_message(
                        chat_id,
                        f"{formatters.EMOJI_CANDADO} "
                        f"Para acceder a tu Dashboard nutricional, "
                        f"necesitas crear una contraseña.\n\n"
                        f"Tu ID de acceso es: `{chat_id}`\n\n"
                        f"Ahora ingresa una contraseña segura "
                        f"(mínimo 6 caracteres):",
                        parse_mode="Markdown"
                    )
            elif opcion == "4":
                # Opción 4: Editar Perfil (con InlineKeyboardMarkup)
                user = firebase_service.cargar_usuario(chat_id)
                if user:
                    # Mostrar menú con botones inline
                    menu_texto, menu_teclado = (
                        formatters.crear_menu_editar_perfil_inline(user)
                    )
                    bot.send_message(
                        chat_id,
                        menu_texto,
                        parse_mode="Markdown",
                        reply_markup=menu_teclado
                    )
                else:
                    bot.send_message(
                        chat_id,
                        formatters.mensaje_sin_perfil()
                    )
        else:
            respuesta = (
                groq_service.responder_pregunta(
                    message.text
                )
            )
            if respuesta:
                bot.send_message(chat_id, respuesta)
            else:
                bot.send_message(
                    chat_id,
                    formatters.mensaje_no_entiendo()
                )
    
    # Si está analizando comida
    elif estado == "registro_comida":
        comida = message.text.strip()
        # Capitalizar para formato profesional
        comida = comida.capitalize()
        
        bot.send_message(
            chat_id,
            formatters.mensaje_generando_recomendacion()
        )
        
        analisis = (
            groq_service.analizar_comida(comida)
        )
        
        if analisis is None:
            # El texto NO es una comida válida
            bot.send_message(
                chat_id,
                f"{formatters.EMOJI_ERROR} ¡Eso no parece ser una comida! 🤔\n\n"
                f"Por favor, ingresa el nombre de un alimento, plato o receta real. "
                f"Ejemplos: 'arroz con pollo', 'huevos fritos', 'ensalada de lechuga', etc.\n\n"
                f"¿Cuál es el nombre del plato que deseas analizar?"
            )
            return
        
        if analisis:
            bot.send_message(
                chat_id,
                formatters.crear_mensaje_analisis(
                    comida, analisis
                ),
                parse_mode="Markdown"
            )
            
            # Guardar item pendiente
            state_manager.guardar_item_pendiente(
                chat_id,
                {
                    "tipo": "comida",
                    "nombre": comida,
                    "analisis": analisis
                }
            )
            
            state_manager.establecer_estado(
                chat_id, "confirmar_registro"
            )
            bot.send_message(
                chat_id,
                formatters.crear_mensaje_confirmar_registro(),
                parse_mode="Markdown"
            )
        else:
            bot.send_message(
                chat_id,
                f"{formatters.EMOJI_ERROR} Error al "
                f"analizar la comida."
            )
    
    # Si está esperando tipo de comida
    elif estado == "espera_tipo_comida":
        tipo_comida = message.text.strip()
        opciones_validas = [
            "Desayuno", "Almuerzo", "Cena"
        ]
        
        if tipo_comida not in opciones_validas:
            teclado = (
                formatters.crear_teclado_tipo_comida()
            )
            bot.send_message(
                chat_id,
                f"{formatters.EMOJI_BOT} Selecciona "
                f"una opción:",
                reply_markup=teclado
            )
            return
        
        # Obtener usuario para recomendación
        user = firebase_service.cargar_usuario(chat_id)
        
        if not user:
            bot.send_message(
                chat_id,
                formatters.mensaje_sin_datos_para_recomendacion()
            )
            return
        
        # PHASE 2: Obtener progreso del usuario para personalización
        progreso_usuario = firebase_service.obtener_progreso_usuario(chat_id)
        
        bot.send_message(
            chat_id,
            formatters.mensaje_generando_recomendacion()
        )
        
        # Generar recomendación PERSONALIZADA con progreso del usuario
        recomendacion = (
            groq_service.obtener_recomendacion_receta(
                user, 
                tipo_comida,
                progreso_usuario=progreso_usuario  # ← NUEVO: Pasa análisis de progreso
            )
        )
        
        if recomendacion:
            bot.send_message(
                chat_id,
                recomendacion,
                parse_mode="Markdown"
            )
            
            # Extraer el nombre de la receta - MEJORADO
            import re
            nombre_receta = tipo_comida  # Fallback por defecto
            
            logger.debug(f"📝 Recomendacion recibida (primeros 300 chars):\n{recomendacion[:300]}")
            
            # Estrategia 1: Buscar nombre entre corchetes [Nombre del Plato]
            # Es lo más confiable porque Groq lo pone así en el prompt
            match = re.search(r'\[([^\]]+)\]', recomendacion, re.MULTILINE)
            if match:
                nombre_receta = match.group(1).strip()
                logger.info(f"✅ Receta extraída (corchetes): {nombre_receta}")
            else:
                logger.debug("⚠️ No se encontró nombre en corchetes, intentando estrategia 2...")
                # Estrategia 2: Buscar después de "prepares" (segunda línea aprox)
                # Patrón: "prepares XXXX," donde XXXX es el nombre
                match = re.search(
                    r'prepares\s+(?:los?|las?|una?|unos?|unas?)?\s*([A-Za-záéíóúñÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ\s\-y]+?)(?:\s*,|\s+ya\s+que)',
                    recomendacion,
                    re.IGNORECASE
                )
                if match:
                    nombre_receta = match.group(1).strip()
                    palabras = nombre_receta.split()
                    if len(palabras) > 6:
                        nombre_receta = ' '.join(palabras[:6])
                    # Capitalizar primer letra
                    nombre_receta = nombre_receta.capitalize() if nombre_receta else nombre_receta
                    logger.info(f"✅ Receta extraída (prepares): {nombre_receta}")
                else:
                    logger.debug("⚠️ Estrategia 2 falló, intentando estrategia 3...")
                    # Estrategia 3: Buscar "recomiendo XXXX" (alternativa si prepares no funciona)
                    match = re.search(
                        r'recomiendo\s+que\s+te\s+prepares\s+([A-Za-záéíóúñÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ\s\-y]+?)(?:\s*,|\s+ya\s+que)',
                        recomendacion,
                        re.IGNORECASE
                    )
                    if match:
                        nombre_receta = match.group(1).strip()
                        palabras = nombre_receta.split()
                        if len(palabras) > 6:
                            nombre_receta = ' '.join(palabras[:6])
                        nombre_receta = nombre_receta.capitalize() if nombre_receta else nombre_receta
                        logger.info(f"✅ Receta extraída (recomiendo): {nombre_receta}")
                    else:
                        logger.debug("⚠️ Estrategia 3 falló, usando fallback...")
                        logger.warning(f"⚠️ No se pudo extraer nombre, usando fallback: {tipo_comida}")
            
            # Limpiar espacios y puntuación extra
            nombre_receta = nombre_receta.strip()
            nombre_receta = re.sub(r'\s+', ' ', nombre_receta)  # Espacios múltiples -> uno solo
            
            # Agregar sufijo para diferenciar de análisis
            nombre_final = f"{nombre_receta} (Recomendación)"
            
            state_manager.guardar_item_pendiente(
                chat_id,
                {
                    "tipo": "recomendacion",
                    "nombre": nombre_final,
                    "analisis": recomendacion
                }
            )
            
            state_manager.establecer_estado(
                chat_id, "confirmar_registro"
            )
            bot.send_message(
                chat_id,
                formatters.crear_mensaje_confirmar_registro(),
                parse_mode="Markdown"
            )
        else:
            bot.send_message(
                chat_id,
                f"{formatters.EMOJI_ERROR} Error al "
                f"generar la recomendación."
            )
    
    # Confirmación de registro
    elif estado == "confirmar_registro":
        respuesta = message.text.lower().strip()
        item = (
            state_manager.obtener_item_pendiente(chat_id)
        )
        
        if not item:
            logger.warning(
                f"No hay item pendiente para {chat_id}"
            )
            state_manager.establecer_estado(
                chat_id, "menu"
            )
            return
        
        # Verificar que el usuario existe ANTES de guardar
        logger.debug(
            f"Verificando si usuario {chat_id} existe "
            f"antes de guardar confirmación"
        )
        if not firebase_service.usuario_existe(chat_id):
            logger.error(
                f"Usuario {chat_id} no existe en Firebase. "
                f"No se puede guardar registro de comida."
            )
            bot.send_message(
                chat_id,
                formatters.mensaje_sin_perfil()
            )
            state_manager.establecer_estado(
                chat_id, "menu"
            )
            return
        
        if respuesta in ["sí", "si"]:
            logger.debug(
                f"Usuario {chat_id} confirmó guardar comida"
            )
            # Extraer macronutrientes
            analisis = item.get("analisis", "")
            proteina, grasa, carbs, calorias = (
                GroqService.extraer_macronutrientes(
                    analisis
                )
            )
            
            logger.debug(
                f"Macronutrientes extraídos: proteina={proteina}, "
                f"grasa={grasa}, carbs={carbs}, calorias={calorias}"
            )
            
            nutrition = NutritionData(
                proteina, grasa, carbs, calorias
            )
            
            # Guardar registros
            resultado_diario = firebase_service.guardar_registro_diario(
                chat_id, nutrition
            )
            logger.debug(
                f"Resultado guardar_registro_diario: {resultado_diario}"
            )
            
            if resultado_diario:
                firebase_service.guardar_comida(
                    chat_id,
                    item.get("nombre", "Comida"),
                    nutrition
                )
                
                # Limpiar item pendiente y volver a menú
                state_manager.establecer_estado(
                    chat_id, "menu"
                )
                
                bot.send_message(
                    chat_id,
                    formatters.mensaje_comida_registrada()
                )
            else:
                logger.error(
                    f"Fallo al guardar registro diario para {chat_id}"
                )
                bot.send_message(
                    chat_id,
                    f"{formatters.EMOJI_ERROR} Error al "
                    f"registrar."
                )
        
        elif respuesta == "no":
            bot.send_message(
                chat_id,
                formatters.mensaje_comida_no_registrada()
            )
        
        else:
            bot.send_message(
                chat_id,
                f"{formatters.EMOJI_PENSANDO} Responde "
                f"*sí* o *no*.",
                parse_mode="Markdown"
            )
            return
        
        state_manager.limpiar_item_pendiente(chat_id)
        state_manager.establecer_estado(chat_id, "menu")
        
        menu_texto, menu_teclado = (
            formatters.crear_menu_principal()
        )
        bot.send_message(
            chat_id,
            menu_texto,
            parse_mode="Markdown",
            reply_markup=menu_teclado
        )
    
    # Si está registrando contraseña para dashboard
    # (El flujo ahora va directamente aquí, saltando el usuario)
    elif estado == "registro_usuario_dashboard":
        # Este estado DEPRECATED - redirectir directamente a contraseña
        logger.info(
            f"[OPCIÓN 3] DEPRECATED: estado registro_usuario_dashboard detectado. "
            f"Redirigiendo directamente a registro_password_dashboard."
        )
        state_manager.establecer_estado(
            chat_id, "registro_password_dashboard"
        )
        bot.send_message(
            chat_id,
            f"{formatters.EMOJI_CANDADO} Perfecto. Ahora "
            f"ingresa una contraseña segura (mínimo 6 caracteres):"
        )
    
    # Si está registrando contraseña del dashboard
    elif estado == "registro_password_dashboard":
        contraseña = message.text.strip()
        
        logger.info(
            f"[OPCIÓN 3] Contraseña ingresada para chat_id {chat_id}: ***"
        )
        
        # Validar que la contraseña tenga al menos 6 caracteres
        if len(contraseña) < 6:
            bot.send_message(
                chat_id,
                f"{formatters.EMOJI_ERROR} La contraseña "
                f"debe tener al menos 6 caracteres. "
                f"Intenta de nuevo:"
            )
            return
        
        logger.info(
            f"[OPCIÓN 3] Guardando contraseña en Firebase: "
            f"chat_id={chat_id}, password=***"
        )
        
        # Guardar en Firebase (SOLO chat_id, sin username)
        resultado = firebase_service.guardar_password(
            chat_id, contraseña
        )
        
        if resultado:
            url_dashboard = (
                "https://JnGarciaGR.github.io/NutrIA-Dashboard/"
            )
            bot.send_message(
                chat_id,
                f"{formatters.EMOJI_COMPLETADO} "
                f"¡Contraseña registrada! ✅\n\n"
                f"Ya puedes acceder a tu Dashboard:\n"
                f"🔗 {url_dashboard}\n\n"
                f"Usa para iniciar sesión:\n"
                f"📱 ID de Telegram: `{chat_id}`\n"
                f"🔐 Contraseña: La que acabas de crear",
                parse_mode="Markdown"
            )
            logger.info(
                f"Credenciales registradas para usuario {chat_id}: "
                f"chat_id={chat_id}"
            )
        else:
            bot.send_message(
                chat_id,
                f"{formatters.EMOJI_ERROR} Error al "
                f"guardar la contraseña. Intenta de nuevo."
            )
            return
        
        state_manager.establecer_estado(chat_id, "menu")
        
        menu_texto, menu_teclado = (
            formatters.crear_menu_principal()
        )
        bot.send_message(
            chat_id,
            menu_texto,
            parse_mode="Markdown",
            reply_markup=menu_teclado
        )
    
    else:
        bot.send_message(
            chat_id,
            formatters.mensaje_no_entiendo()
        )



# ========== PUNTO DE ENTRADA ==========

def iniciar_api_firebase() -> subprocess.Popen:
    """
    Inicia el servidor API Flask que maneja
    los endpoints Firebase.
    
    Retorna el proceso para poder monitorearlo.
    
    Returns:
        subprocess.Popen: Proceso de la API
    """
    proyecto_root = Path(__file__).parent
    api_file = proyecto_root / "api.py"
    
    if not api_file.exists():
        logger.error(f"No se encuentra api.py en {api_file}")
        return None
    
    logger.info("🚀 Iniciando API Firebase (endpoints)...")
    
    api_process = subprocess.Popen(
        [sys.executable, "api.py"],
        cwd=proyecto_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    logger.info("✓ Proceso API iniciado")
    time.sleep(2)  # Esperar a que API esté lista
    
    return api_process


def iniciar_bot_telegram() -> None:
    """
    Inicia el polling del bot de Telegram.
    
    Maneja la reconexión automática y captura
    señales de interrupción.
    """
    logger.info("Bot iniciando...")
    logger.info("(Presiona Ctrl+C para detener el bot)\n")
    
    reconnect_attempts = 0
    max_reconnect_attempts = 5
    commands_set = False
    debe_continuar = True
    
    try:
        while debe_continuar:
            try:
                logger.info("Conectando a Telegram API...")
                
                # Configurar comandos una sola vez
                if not commands_set:
                    try:
                        bot.set_my_commands([
                            {
                                "command": "start",
                                "description": "Iniciar Registro"
                            },
                            {
                                "command": "menu",
                                "description": "Menú Principal"
                            },
                            {
                                "command": "help",
                                "description": "Guía de uso"
                            },
                            {
                                "command": "reset",
                                "description": "Borrar perfil"
                            }
                        ])
                        logger.info("✅ Comandos del bot configurados")
                        commands_set = True
                    except (
                        requests.exceptions.Timeout,
                        requests.exceptions.ConnectionError
                    ) as e:
                        logger.warning(
                            f"⚠️  No se pudieron configurar "
                            f"los comandos: {e}"
                        )
                        logger.warning(
                            "⚠️  El bot continuará funcionando "
                            "sin esto"
                        )
                        commands_set = True
                    except Exception as e:
                        logger.warning(
                            f"⚠️  Error configurando comandos: {e}"
                        )
                        commands_set = True
                
                # Iniciar polling
                bot.infinity_polling(timeout=10, long_polling_timeout=5)
                
                # Si llega aquí, polling terminó correctamente
                debe_continuar = False
                
            except requests.exceptions.ConnectionError as e:
                reconnect_attempts += 1
                wait_time = min(
                    2 ** reconnect_attempts, 60
                )
                
                logger.error(
                    f"❌ Error de conexión con Telegram: {e}"
                )
                logger.info(
                    f"⏳ Reintentando en {wait_time} segundos..."
                )
                
                if reconnect_attempts >= max_reconnect_attempts:
                    logger.error(
                        "❌ Máximo de intentos alcanzado. "
                        "Forzando salida..."
                    )
                    debe_continuar = False
                
                time.sleep(wait_time)
                
            except Exception as e:
                error_str = str(e)
                
                if (
                    "Break infinity polling" in error_str
                    or "StopIteration" in error_str
                ):
                    logger.debug(
                        "✅ Polling detenido normalmente"
                    )
                    debe_continuar = False
                else:
                    logger.error(f"❌ Error inesperado: {e}")
                    debe_continuar = False
    
    except KeyboardInterrupt:
        logger.info("\n" + "="*60)
        logger.info("👋 Deteniendo polling...")
        logger.info("="*60)
        try:
            bot.stop_polling()
        except:
            pass
        logger.info("✅ Bot detenido correctamente")
    
    except Exception as e:
        logger.error(f"❌ Error en el bot: {e}")
    
    finally:
        logger.info("\n" + "="*60)
        logger.info("👋 Bot de NutrIA finalizado")
        logger.info("="*60)


if __name__ == "__main__":
    """
    Punto de entrada del programa.
    
    Inicia:
    1. API Firebase (endpoints para Dashboard y Bot)
    2. Bot de Telegram
    
    Ambos servicios funcionan de forma coordinada.
    """
    api_process = None
    
    try:
        # Mostrar banner de inicio
        print("\n" + "="*60)
        print("🚀 NUTRIIA - INICIANDO TODOS LOS SERVICIOS")
        print("="*60 + "\n")
        
        # 1. Iniciar API Flask
        api_process = iniciar_api_firebase()
        if not api_process:
            logger.error(
                "❌ No se pudo iniciar la API. "
                "Abortando..."
            )
            sys.exit(1)
        
        # Mostrar información de los servicios
        print("\n" + "="*60)
        print("✅ SERVICIOS EN EJECUCIÓN:")
        print("="*60)
        print(f"📡 API Firebase:     http://localhost:5000")
        print(f"💬 Bot Telegram:     Escuchando mensajes")
        print(f"🌐 Dashboard:        https://jnGarciaGR.github.io/NutrIA-Dashboard/")
        print(f"\n⏹️  Presiona CTRL+C para detener todos los servicios\n")
        print("="*60 + "\n")
        
        # 2. Iniciar Bot de Telegram
        logger.info("💬 Iniciando Bot de Telegram...")
        iniciar_bot_telegram()
    
    except KeyboardInterrupt:
        logger.info(
            "\n❌ Interrupción del usuario detectada. "
            "Deteniendo servicios..."
        )
    
    finally:
        # Limpiar procesos
        if api_process and api_process.poll() is None:
            logger.info("🔴 Deteniendo API Firebase...")
            try:
                api_process.terminate()
                api_process.wait(timeout=5)
                logger.info("✅ API detenida")
            except:
                api_process.kill()
                logger.info("✅ API forzosamente detenida")
        
        logger.info("\n" + "="*60)
        logger.info("👋 NutrIA finalizado correctamente")
        logger.info("="*60)

