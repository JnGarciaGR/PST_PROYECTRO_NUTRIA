from telebot import TeleBot
from config import TELEGRAM_TOKEN
from telebot.types import ReplyKeyboardMarkup
from telebot.types import ForceReply
from telebot.types import InlineKeyboardMarkup #crear botones inline
from telebot.types import InlineKeyboardButton #definir botones inline
from telebot.types import ReplyKeyboardRemove
bot = TeleBot(TELEGRAM_TOKEN)

estado_usuarios = {}
usuarios_datos = {}

# INICIO DE REGISTRO
@bot.message_handler(commands=['start'])
def saludar_usuario(message):
    chat_id = message.chat.id

    #Verifica si el usuario ya completó el registro
    if estado_usuarios.get(chat_id) == "menu":
        bot.send_message(chat_id, "🦦⚠️ Ya estás registrado.\n\nUsa /menu para ver las opciones.")
        return
    
    #Si es nuevo, comienza el registro
    estado_usuarios[chat_id] = "esperando_nombre"
    usuarios_datos[chat_id] = {}
    bot.send_message(chat_id, "👋 Hola, soy *NutrIA*. Un gusto saludarte.\n\n¿Cómo te llamas?", parse_mode="Markdown")

# NOMBRE
@bot.message_handler(func=lambda m: estado_usuarios.get(m.chat.id) == "esperando_nombre")
def registrar_nombre(message):
    markup = ForceReply()
    chat_id = message.chat.id
    nombre = message.text.strip().capitalize()
    
    usuarios_datos[chat_id]["nombre"] = nombre
    estado_usuarios[chat_id] = "esperando_cedula"
    bot.send_message(chat_id, f"🦦 ¡Mucho gusto, {nombre}!")
    bot.send_message(chat_id, f"📄 Ingresa tu número de cédula:", reply_markup=markup)

# CÉDULA
@bot.message_handler(func=lambda m: estado_usuarios.get(m.chat.id) == "esperando_cedula")
def registrar_cedula(message):
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, 
                                 input_field_placeholder="Pulsa un botón",
                                 resize_keyboard=True
                                 )
    chat_id = message.chat.id
    texto = message.text.strip()
    if len(texto) == 10 and texto.isdigit():
        usuarios_datos[chat_id]["cedula"] = texto
        estado_usuarios[chat_id] = "esperando_genero"
        #bot.send_message(chat_id, "🦦 Indica tu género: [M] Masculino / [F] Femenino")
        markup.add("Hombre", "Mujer")
        bot.send_message(chat_id, "🦦 Indica tu sexo:", reply_markup=markup)
    else:
        bot.send_message(chat_id, "❌ Cédula inválida. Debe contener exactamente 10 dígitos.")

# GÉNERO
@bot.message_handler(func=lambda m: estado_usuarios.get(m.chat.id) == "esperando_genero")
def registrar_genero(message):
    
    chat_id = message.chat.id
    #texto = message.text
    if message.text != "Hombre" and message.text != "Mujer":
        bot.send_message(chat_id,"❌ ERROR: Sexo no válido. \nPulsa un botón" )
    else:
        usuarios_datos[chat_id]["genero"] = message.text
        estado_usuarios[chat_id] = "esperando_peso"
        markup = ReplyKeyboardRemove()
        bot.send_message(chat_id, "🦦 Ingresa tu peso en kilogramos (ej. 70.5):", reply_markup=markup)

#    if texto in ["m", "f"]:
#        genero = "Masculino" if texto == "m" else "Femenino"
#        usuarios_datos[chat_id]["genero"] = genero
#        estado_usuarios[chat_id] = "esperando_peso"
#        bot.send_message(chat_id, "🦦 Ingresa tu peso en kilogramos (ej. 70.5):")
#    else:
#        bot.send_message(chat_id, "❗ Escribe 'M' para Masculino o 'F' para Femenino.")

# PESO
@bot.message_handler(func=lambda m: estado_usuarios.get(m.chat.id) == "esperando_peso")
def registrar_peso(message):
    markup = ForceReply()
    chat_id = message.chat.id
    try:
        peso = float(message.text.replace(",", "."))
        if 30 <= peso <= 300:
            usuarios_datos[chat_id]["peso"] = peso
            estado_usuarios[chat_id] = "esperando_altura"
            bot.send_message(chat_id, "🦦 Ingresa tu altura en centímetros (ej. 170):", reply_markup=markup)
        else:
            bot.send_message(chat_id, "⚠️ Peso fuera de rango (30–300 kg).")
    except ValueError:
        bot.send_message(chat_id, "❗ Escribe un número válido. Ej: 70.5")

# ALTURA
@bot.message_handler(func=lambda m: estado_usuarios.get(m.chat.id) == "esperando_altura")
def registrar_altura(message):
    markup = ForceReply()
    chat_id = message.chat.id
    try:
        altura = float(message.text.replace(",", "."))
        if 100 <= altura <= 250:
            usuarios_datos[chat_id]["altura_cm"] = altura
            estado_usuarios[chat_id] = "esperando_edad"
            bot.send_message(chat_id, "🦦 Indica tu edad:", reply_markup=markup)
        else:
            bot.send_message(chat_id, "⚠️ Altura fuera de rango (100–250 cm).")
    except ValueError:
        bot.send_message(chat_id, "❗ Solo números. Ej: 170")

# EDAD
@bot.message_handler(func=lambda m: estado_usuarios.get(m.chat.id) == "esperando_edad")
def registrar_edad(message):
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, 
                                 input_field_placeholder="Pulsa un botón",
                                 resize_keyboard=True)
    chat_id = message.chat.id
    texto = message.text
    if texto.isdigit():
        edad = int(texto)
        if 10 <= edad <= 120:
            usuarios_datos[chat_id]["edad"] = edad
            estado_usuarios[chat_id] = "esperando_actividad"
            markup.add("Sedentario", "Ligera", "Moderada", "Intensa", "Muy intensa")
            bot.send_message(chat_id, "🦦 Indica tu nivel de actividad física:", reply_markup=markup)
            
        else:
            bot.send_message(chat_id, "⚠️ Edad fuera de rango (10–120 años).")
    else:
        bot.send_message(chat_id, "❗ Solo números. Ej: 25")


# ACTIVIDAD
from telebot.types import ReplyKeyboardMarkup

@bot.message_handler(func=lambda m: estado_usuarios.get(m.chat.id) == "esperando_actividad")
def registrar_actividad(message):
    chat_id = message.chat.id
    texto = message.text.strip()

    opciones_validas = ["Sedentario", "Ligera", "Moderada", "Intensa", "Muy intensa"]

    if texto not in opciones_validas:
        bot.send_message(chat_id, "❌ Opción no válida. Pulsa un botón para seleccionar tu nivel de actividad.")
    else:
        usuarios_datos[chat_id]["actividad_fisica"] = texto
        estado_usuarios[chat_id] = "esperando_economia"

        # ✅ Mostrar botones de estabilidad económica inmediatamente
        markup = ReplyKeyboardMarkup(one_time_keyboard=True, 
                                     resize_keyboard=True, 
                                     input_field_placeholder="Pulsa un botón")
        markup.add("Alta", "Media", "Baja")

        bot.send_message(chat_id, "🦦 ¿Cuál es tu estabilidad económica?", reply_markup=markup)


# ECONOMÍA
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

@bot.message_handler(func=lambda m: estado_usuarios.get(m.chat.id) == "esperando_economia")
def registrar_economia(message):
    chat_id = message.chat.id
    texto = message.text.strip().capitalize()

    opciones = ["Alta", "Media", "Baja"]

    if texto in opciones:
        usuarios_datos[chat_id]["economia"] = texto
        estado_usuarios[chat_id] = "esperando_dieta"

        # ✅ Mostrar botones de tipo de dieta
        markup = ReplyKeyboardMarkup(one_time_keyboard=True, 
                                     resize_keyboard= False, 
                                     input_field_placeholder="Pulsa un botón")
        markup.add("Déficit calórico", "Recomposición muscular", "Superávit calórico")

        bot.send_message(chat_id, "🦦 ¿Cuál es tu tipo de dieta realizas o desea realizar?", reply_markup=markup)
        bot.send_message(chat_id,
        """ℹ️ <b>Déficit calórico:</b> Pierdes grasa corporal consumiendo menos calorías.
ℹ️ <b>Recomposición muscular:</b> Ganas músculo y pierdes grasa con una dieta balanceada.
ℹ️ <b>Superávit calórico:</b> Aumentas masa muscular comiendo más calorías.""",
parse_mode = "html")
    else:
        # Si el usuario escribe algo no válido
        markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, input_field_placeholder="Pulsa un botón")
        markup.add("Alta", "Media", "Baja")
        bot.send_message(chat_id, "❗ Opción no válida. Pulsa un botón:", reply_markup=markup)

# DIETA
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

@bot.message_handler(func=lambda m: estado_usuarios.get(m.chat.id) == "esperando_dieta")
def registrar_dieta(message):
    chat_id = message.chat.id
    texto = message.text.strip()

    opciones_validas = ["Déficit calórico", "Recomposición muscular", "Superávit calórico"]

    if texto in opciones_validas:
        usuarios_datos[chat_id]["dieta"] = texto
        estado_usuarios[chat_id] = "menu"

        # Eliminar botones después de registrar la dieta
        markup = ReplyKeyboardRemove()

        bot.send_message(chat_id, "✅ ¡Registro completo!\n🎉 Bienvenido a *NutrIA*", parse_mode="Markdown", reply_markup=markup)
        mostrar_menu(message)
        print(usuarios_datos)
    else:
        # Reenviar los botones si escribió algo no válido
        markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, input_field_placeholder="Selecciona una opción")
        markup.add("Déficit calórico", "Recomposición muscular", "Superávit calórico")

        bot.send_message(chat_id, "❗ Pulsa un botón, no escribas manualmente:", reply_markup=markup)

@bot.message_handler(commands=['help'])
def mostrar_help(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, """ 🦦 <u>¿Cómo usar NutrIA Assistant?</u> 🦦

Aquí tienes una guía de lo que puedes hacer con el bot:

1️⃣ <b>Registro / Análisis de comida</b>  
Escribe lo que comiste o piensas comer. NutrIA te dirá cuántas <u>calorías, proteínas, carbohidratos y grasas contiene tu alimento</u>. Podrás decidir si deseas guardar ese análisis como parte de tu seguimiento.

2️⃣ <b>Recomendaciones de comidas</b>  
NutrIA te sugiere recetas saludables y económicas según tu tipo de dieta <b>(déficit calórico, recomposición muscular o superávit calórico)</b> y tu estabilidad económica. También te dirá cuántos nutrientes aporta la receta recomendada.

3️⃣ <b>Seguimiento nutricional</b>  
Aquí se guarda todo lo que decidiste registrar. Puedes revisar tu consumo diario, semanal o mensual. Además, recibirás consejos personalizados para mejorar tu alimentación.

4️⃣ <b>Editar perfil</b>  
¿Cambió tu situación económica? ¿Quieres ajustar tu tipo de dieta o nivel de actividad física? Aquí puedes actualizar tus datos para que NutrIA siga adaptándose a tus necesidades.

---

Para volver al menú principal escribe /menu.
""", parse_mode="html")

@bot.message_handler(commands=['menu'])
def mostrar_menu(message):
    chat_id = message.chat.id

    if estado_usuarios.get(chat_id) == "menu":
        # Crear los botones del menú
        markup = ReplyKeyboardMarkup(one_time_keyboard=True, 
        resize_keyboard=True, 
        input_field_placeholder="Pulsa una opción")
        markup.add("1", "2", "3", "4")

        bot.send_message(chat_id,
            "🦦📋 *MENÚ PRINCIPAL:*\n"
            "1️⃣ Registro/Analisis de Comida\n"
            "2️⃣ Recomendaciones de recetas\n"
            "3️⃣ Seguimiento Nutricional\n"
            "4️⃣ Editar Perfil\n\n"
            "ℹ️ ¿Tienes dudas? Usa /help para aprender cómo usar NutrIA Assistant.",
            parse_mode="Markdown",
            reply_markup=markup
        )
    else:
        bot.send_message(chat_id, "⚠️ Primero debes completar el registro usando /start.")
