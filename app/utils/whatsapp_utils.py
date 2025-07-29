import logging
from flask import current_app, jsonify
import json
import requests
import unicodedata
from app.services.openai_service import generate_response
import re


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


#def generate_response(response):
    # Return text in uppercase
#    return response.upper()


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text

estado_usuarios = {}
usuarios_datos = {}

def normalizar_texto(texto):
    texto = texto.lower()
    texto = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode("utf-8")
    return texto.strip()

def registro_nuevo_user(wa_id, name):
    estado_usuarios[wa_id] = "esperando_cedula"
    usuarios_datos[wa_id] = {"nombre": name}
    return f"Hola {name},\nPara comenzar a usar *NutrIA*, necesitamos que completes algunas asignaciones.\n\n📄 Ingrese tu número de cédula:"

def registro_cedula(wa_id, mensaje):
    if len(mensaje) == 10 and mensaje.isdigit():
        usuarios_datos[wa_id]["cedula"] = mensaje
        estado_usuarios[wa_id] = "esperando_genero"
        return "Indique su género: [M] Masculino / [F] Femenino"
    return "❌ Cédula inválida. \n\nDebe contener exactamente 10 dígitos numéricos."

def registro_genero(wa_id, mensaje):
    if mensaje.lower() in ["m", "f"]:
        genero = "Masculino" if mensaje.lower() == "m" else "Femenino"
        usuarios_datos[wa_id]["genero"] = genero
        estado_usuarios[wa_id] = "esperando_peso"
        return "Indique su peso en kilogramos (kg). Ej: 70 ó 72.5):"
    return "❗ Escriba 'M' para Masculino o 'F' para Femenino."

def registro_peso(wa_id, mensaje):
    try:
        peso = float(mensaje.replace(",", "."))
        if 30 <= peso <= 300:
            usuarios_datos[wa_id]["peso"] = peso
            estado_usuarios[wa_id] = "esperando_altura"
            return "Indique su altura en centímetros (cm). Ej: 170 ó 175.5):"
        else:
            return "⚠️ Peso fuera de rango. Ingrese un valor entre 30 y 300 kg:"
    except ValueError:
        return "❗ Ingrese solo números. Ejemplo válido: 70 ó 70.5"

def registro_altura(wa_id, mensaje):
    try:
        altura = float(mensaje.replace(",", "."))
        if 100 <= altura <= 250:
            usuarios_datos[wa_id]["altura_cm"] = altura
            estado_usuarios[wa_id] = "esperando_edad"
            return "Indique su edad en años:"
        else:
            return "⚠️ Altura fuera de rango. Ingrese un valor entre 100 y 250 cm:"
    except ValueError:
        return "❗ Ingrese solo números. Ej: 170 ó 175.5"

def registro_edad(wa_id, mensaje):
    if mensaje.isdigit():
        edad = int(mensaje)
        if 10 <= edad <= 120:
            usuarios_datos[wa_id]["edad"] = edad
            estado_usuarios[wa_id] = "esperando_actividad"
            return (
                "Indique su nivel de actividad física:\n\n"
                "1️⃣ Sedentario\n2️⃣ Ligera\n3️⃣ Moderada\n4️⃣ Intensa\n5️⃣ Muy intensa"
            )
        else:
            return "⚠️ Edad fuera de rango. Ingrese un valor entre 10 y 120:"
    return "❗ Ingrese solo números. Ejemplo válido: 25"

def registro_actividad(wa_id, mensaje):
    niveles = {
        "1": "Sedentario",
        "2": "Ligera",
        "3": "Moderada",
        "4": "Intensa",
        "5": "Muy intensa"
    }
    if mensaje in niveles:
        usuarios_datos[wa_id]["actividad_fisica"] = niveles[mensaje]
        estado_usuarios[wa_id] = "esperando_economia"
        return "¿Cuál es tu estabilidad económica?\nEscriba: *alta*, *media* o *baja*"
    return "❗ Escriba un número del 1 al 5 según su nivel de actividad."

def registro_economia(wa_id, mensaje):
    if mensaje in ["alta", "media", "baja"]:
        usuarios_datos[wa_id]["economia"] = mensaje
        estado_usuarios[wa_id] = "esperando_dieta"
        return "¿Cuál es tu tipo de dieta?\n- déficit calórico\n- recomposición muscular\n- superávit calórico"
    return "❗ Opción no válida. Escriba: *alta*, *media* o *baja*"

def registro_dieta(wa_id, mensaje):
    mensaje_normalizado = normalizar_texto(mensaje)
    opciones = {
        "deficit calorico": "déficit calórico",
        "recomposicion muscular": "recomposición muscular",
        "superavit calorico": "superávit calórico"
    }

    if mensaje_normalizado in opciones:
        usuarios_datos[wa_id]["dieta"] = opciones[mensaje_normalizado]
        estado_usuarios[wa_id] = "menu"
        bienvenida = "✅ ¡Registro completo!\n🎉 Bienvenido a *NutrIA*."
        return f"{bienvenida}\n\n{menu_principal(wa_id, 'menu')}"
    else:
        return (
            "❗ Tipo de dieta no válida. Escriba una de las siguientes opciones:\n"
            "- déficit calórico\n- recomposición muscular\n- superávit calórico"
        )

# -------------------------- MENÚ PRINCIPAL -----------------------

def menu_principal(wa_id, mensaje):
    if mensaje == "1":
        return handle_ingresar_comida(wa_id)
    elif mensaje == "2":
        return handle_recomendaciones(wa_id)
    elif mensaje == "3":
        return handle_registro(wa_id)
    elif normalizar_texto(mensaje) == "menu":
        return "📋 MENÚ PRINCIPAL:\n1️⃣ Ingresar comida\n2️⃣ Recomendaciones\n3️⃣ Registro"

def handle_ingresar_comida(wa_id):
    return "Ingresa lo que comiste hoy."

def handle_recomendaciones(wa_id):
    return "Recomendación saludable próximamente..."

def handle_registro(wa_id):
    return "¿Qué tipo de registro deseas ver?\n1. Diario\n2. Semanal\n3. Mensual"


def menu_principal(wa_id, mensaje):
    if mensaje == "1":
        return handle_ingresar_comida(wa_id)
    elif mensaje == "2":
        return handle_recomendaciones(wa_id)
    elif mensaje == "3":
        return handle_registro(wa_id)
    else:
        return "MENÚ PRINCIPAL:\n1️⃣ Ingresar comida\n2️⃣ Recomendaciones\n3️⃣ Registro"

def handle_ingresar_comida(wa_id):
    return "Ingresa lo que comiste hoy."

def handle_recomendaciones(wa_id):
    return "Aquí tienes una recomendación saludable (próximamente personalizada)..."

def handle_registro(wa_id):
    return "¿Qué tipo de registro deseas ver?\n1. Diario\n2. Semanal\n3. Mensual"


def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    mensaje = message["text"]["body"].strip().lower()

    estado = estado_usuarios.get(wa_id, "nuevo")

    if estado == "nuevo":
        respuesta = registro_nuevo_user(wa_id, name)
    elif estado == "esperando_cedula":
        respuesta = registro_cedula(wa_id, mensaje)
    elif estado == "esperando_genero":
        respuesta = registro_genero(wa_id, mensaje)
    elif estado == "esperando_peso":
        respuesta = registro_peso(wa_id, mensaje)
    elif estado == "esperando_altura":
        respuesta = registro_altura(wa_id, mensaje)
    elif estado == "esperando_edad":
        respuesta = registro_edad(wa_id, mensaje)
    elif estado == "esperando_actividad":
        respuesta = registro_actividad(wa_id, mensaje)
    elif estado == "esperando_economia":
        respuesta = registro_economia(wa_id, mensaje)
    elif estado == "esperando_dieta":
        respuesta = registro_dieta(wa_id, mensaje)
    elif estado == "menu":
        respuesta = menu_principal(wa_id, mensaje)
    else:
        respuesta = "❓ No entendí. Escriba 'menu' para volver al menú principal."


    # ENVÍA respuesta
    from .whatsapp_utils import get_text_message_input, send_message
    data = get_text_message_input(wa_id, respuesta)
    send_message(data)


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
