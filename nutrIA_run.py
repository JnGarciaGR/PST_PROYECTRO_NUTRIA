import time
from config import * #Importacion token
import telebot #Manejo de la API de Telegram
import threading
from telebot.types import ReplyKeyboardMarkup #Crear botones
from telebot.types import ForceReply

from funciones_nutrIA import bot


if __name__ == "__main__":
    bot.set_my_commands([
        telebot.types.BotCommand("/start", "Iniciar Registro en NutrIA"),
        telebot.types.BotCommand("/menu", "Menú Principal de NutrIA"),
        telebot.types.BotCommand("/help", "Guía de uso NutrIA")]) #/reset
    #print("🤖 NutrIA está corriendo...")
    bot.infinity_polling()