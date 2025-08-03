import time
from config import * #Importacion token
import telebot #Manejo de la API de Telegram
import threading
from telebot.types import ReplyKeyboardMarkup #Crear botones

#Instanciamos el bot de Telegram
bot = telebot.TeleBot(TELEGRAM_TOKEN)

#Responde a los mensajes de texto que no son comandos
#@bot.message_handler(content_types=["text"])
#def bot_mensajes_texto(message):
#    """Gestiona los mensajes de texto recibidos"""
#    bot.send_message(message.chat.id, "Hola, soy NutrIA")




#Responde al comando /start
@bot.message_handler(commands=["start"])
def cmd_start(message):
    """Da la bienvenida al usuario del bot"""
    bot.reply_to(message, "Hola, Soy NutrIA. Un gusto saludarte.")
    time.sleep(1)
    bot.reply_to(message, "Para el registro...")

#def recibir_mensajes():
#    bot.infinity_polling()
# ------------------- MAIN --------------------
if __name__ == "__main__":
    bot.set_my_commands([
        telebot.types.BotCommand("/start", "Activa a NutrIA"),
        telebot.types.BotCommand("/menu", "Da acceso al menú de NutrIA")
        ])
    print("Iniciando el bot")
    bot.infinity_polling()
    print("NutrIA Iniciado")
    #hilo_bot = threading.Thread(name="hilo_bot", target=recibir_mensajes)
    #hilo_bot.start()
    
    print("Fin")

#Responde a los mensajes de texto que no son comandos
#@bot.message_handler(content_types=["text"])
#def bot_mensajes_texto(message):
#    """Gestiona los mensajes de texto recibidos"""
#    if message.text.startwith("/"):
#        bot.send_message(message.chat.id, "Comando no disponible")
#    else:
#        bot.send_message(message.chat.id, "hola")