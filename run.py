import logging

from app import create_app
from flask import Flask, request, jsonify
import requests
import os

app = create_app()

if __name__ == "__main__":
    logging.info("Flask app started")
    app.run(host="0.0.0.0", port=8000)

#######

app = Flask(__name__)

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# Enviar mensaje por WhatsApp
def send_whatsapp(to, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }
    requests.post(url, headers=headers, json=data)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = message["from"]
        user_input = message["text"]["body"].strip().lower()

        # 🟢 RESPUESTA FIJA: Saludo + menú
        mensaje_menu = (
            f"👋 ¡Hola! Bienvenido/a.\n"
            f"Selecciona una opción:\n"
            f"1️⃣ Ingresar comida\n"
            f"2️⃣ Recomendaciones\n"
            f"3️⃣ Registro\n"
            f"Escribe el número de la opción."
        )
        send_whatsapp(from_number, mensaje_menu)

    except Exception as e:
        print("No es un mensaje válido:", e)

    return "ok", 200

@app.route("/webhook", methods=["GET"])
def verify():
    VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

