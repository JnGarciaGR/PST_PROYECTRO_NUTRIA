# Importaciones necesarias para el bot
from telebot import TeleBot
from config import TELEGRAM_TOKEN, OPENAI_API_KEY # <-- Modificación aquí: Importar OPENAI_API_KEY
from telebot.types import ReplyKeyboardMarkup, ForceReply, ReplyKeyboardRemove
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import firebase_admin
from firebase_admin import credentials, db
import logging
import openai
import re
from datetime import date

# Inicialización del bot
bot = TeleBot(TELEGRAM_TOKEN)

# Inicialización de Firebase
print("Inicializando Firebase...")
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://nutribot-3d198-default-rtdb.firebaseio.com/'
})
print("Firebase inicializado correctamente.")

# Referencia a la base de datos
db_ref = db.reference('usuarios')

# Inicialización de OpenAI
openai.api_key = OPENAI_API_KEY # <-- Modificación aquí: Asignar la clave de la API
print("OpenAI inicializado correctamente.")

# Habilitar logs para debugging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Diccionarios para manejar el estado y los datos de los usuarios
estado_usuarios = {}
usuarios_datos = {}

# --- FUNCIONES DE COMANDOS GLOBALES ---

@bot.message_handler(commands=['start'])
def saludar_usuario(message):
    chat_id = message.chat.id
    
    # Comprobar si el usuario ya existe en Firebase
    usuario_existente = db_ref.child(str(chat_id)).child('perfil').get()
    if usuario_existente:
        estado_usuarios[chat_id] = "menu"
        bot.send_message(chat_id, "🦦⚠️ Ya estás registrado.\n\nUsa /menu para ver las opciones.")
        return
    
    # Si es nuevo, comienza el registro
    estado_usuarios[chat_id] = "esperando_nombre"
    usuarios_datos[chat_id] = {}
    bot.send_message(chat_id, "👋 Hola, soy *NutrIA*. Un gusto saludarte.\n\n¿Cómo te llamas?", parse_mode="Markdown")

@bot.message_handler(commands=['menu'])
def mostrar_menu(message):
    chat_id = message.chat.id
    # Solo muestra el menú si el usuario está registrado
    if db_ref.child(str(chat_id)).child('perfil').get():
        estado_usuarios[chat_id] = "menu"
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

@bot.message_handler(commands=['reset'])
def reset_perfil(message):
    chat_id = message.chat.id
    usuario_existente = db_ref.child(str(chat_id)).child('perfil').get()
    if not usuario_existente:
        bot.send_message(chat_id, "⚠️ No tienes un perfil registrado para borrar. Usa /start para crear uno.")
        return
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Confirmar", callback_data='confirmar_reset'),
               InlineKeyboardButton("❌ Cancelar", callback_data='cancelar_reset'))
    bot.send_message(chat_id, "⚠️ Estás a punto de borrar todos tus datos de perfil.\n¿Estás seguro de que quieres continuar?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ['confirmar_reset', 'cancelar_reset'])
def handle_reset_callback(call):
    chat_id = call.message.chat.id
    bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)
    if call.data == 'confirmar_reset':
        try:
            db_ref.child(str(chat_id)).delete()
            if chat_id in estado_usuarios:
                del estado_usuarios[chat_id]
            if chat_id in usuarios_datos:
                del usuarios_datos[chat_id]
            bot.send_message(chat_id, "✅ Tu perfil ha sido borrado exitosamente. Usa /start para crear uno nuevo.")
            logger.info(f"Perfil del usuario {chat_id} borrado de Firebase.")
        except Exception as e:
            bot.send_message(chat_id, "❌ Ocurrió un error al intentar borrar tu perfil. Inténtalo de nuevo más tarde.")
            logger.error(f"Error al borrar el perfil del usuario {chat_id}: {e}")
    elif call.data == 'cancelar_reset':
        bot.send_message(chat_id, "👍 El borrado ha sido cancelado. Tus datos están a salvo.")


# --- FUNCIÓN DE GUARDADO EN FIREBASE (TU CÓDIGO) ---
def guardar_perfil_en_firebase(chat_id):
    """Guarda los datos del perfil del usuario y la estructura completa en Firebase."""
    try:
        perfil_usuario = usuarios_datos.get(chat_id, {})
        if not perfil_usuario:
            logger.warning(f"No se encontraron datos para el chat_id {chat_id}. No se guardó en Firebase.")
            return

        nuevo_usuario = {
            'perfil': {
                'nombre': perfil_usuario.get('nombre'),
                'cedula': perfil_usuario.get('cedula'),
                'genero': perfil_usuario.get('genero'),
                'peso': perfil_usuario.get('peso'),
                'altura': perfil_usuario.get('altura_cm'),
                'edad': perfil_usuario.get('edad'),
                'nivelActividad': perfil_usuario.get('actividad_fisica'),
                'economia': perfil_usuario.get('economia'),
                'tipoDieta': perfil_usuario.get('dieta'),
            },
            'comidas': {},
            'historial': {},
            'registros': {
                'diario': {},
                'mensual': {},
                'semanal': {}
            }
        }
        
        db_ref.child(str(chat_id)).set(nuevo_usuario)
        logger.info(f"Datos del usuario {chat_id} con estructura completa guardados en Firebase.")
        
    except Exception as e:
        logger.error(f"Error al guardar los datos en Firebase para el chat_id {chat_id}: {e}")

# --- TU CÓDIGO DE REGISTRO DE USUARIO (SIN CAMBIOS) ---

@bot.message_handler(func=lambda m: estado_usuarios.get(m.chat.id) == "esperando_nombre")
def registrar_nombre(message):
    markup = ForceReply()
    chat_id = message.chat.id
    nombre = message.text.strip().capitalize()
    usuarios_datos[chat_id]["nombre"] = nombre
    estado_usuarios[chat_id] = "esperando_cedula"
    bot.send_message(chat_id, f"🦦 ¡Mucho gusto, {nombre}!")
    bot.send_message(chat_id, f"📄 Ingresa tu número de cédula:", reply_markup=markup)

@bot.message_handler(func=lambda m: estado_usuarios.get(m.chat.id) == "esperando_cedula")
def registrar_cedula(message):
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, 
                                 input_field_placeholder="Pulsa un botón",
                                 resize_keyboard=True)
    chat_id = message.chat.id
    texto = message.text.strip()
    if len(texto) == 10 and texto.isdigit():
        usuarios_datos[chat_id]["cedula"] = texto
        estado_usuarios[chat_id] = "esperando_genero"
        markup.add("Hombre", "Mujer")
        bot.send_message(chat_id, "🦦 Indica tu sexo:", reply_markup=markup)
    else:
        bot.send_message(chat_id, "❌ Cédula inválida. Debe contener exactamente 10 dígitos.")

@bot.message_handler(func=lambda m: estado_usuarios.get(m.chat.id) == "esperando_genero")
def registrar_genero(message):
    chat_id = message.chat.id
    if message.text not in ["Hombre", "Mujer"]:
        bot.send_message(chat_id,"❌ ERROR: Sexo no válido. \nPulsa un botón" )
    else:
        usuarios_datos[chat_id]["genero"] = message.text
        estado_usuarios[chat_id] = "esperando_peso"
        markup = ReplyKeyboardRemove()
        bot.send_message(chat_id, "🦦 Ingresa tu peso en kilogramos (ej. 70.5):", reply_markup=markup)

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
        markup = ReplyKeyboardMarkup(one_time_keyboard=True, 
                                     resize_keyboard=True, 
                                     input_field_placeholder="Pulsa un botón")
        markup.add("Alta", "Media", "Baja")
        bot.send_message(chat_id, "🦦 ¿Cuál es tu estabilidad económica?", reply_markup=markup)

@bot.message_handler(func=lambda m: estado_usuarios.get(m.chat.id) == "esperando_economia")
def registrar_economia(message):
    chat_id = message.chat.id
    texto = message.text.strip().capitalize()
    opciones = ["Alta", "Media", "Baja"]
    if texto in opciones:
        usuarios_datos[chat_id]["economia"] = texto
        estado_usuarios[chat_id] = "esperando_dieta"
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
        markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, input_field_placeholder="Pulsa un botón")
        markup.add("Alta", "Media", "Baja")
        bot.send_message(chat_id, "❗ Opción no válida. Pulsa un botón:", reply_markup=markup)

# DIETA (AQUÍ SE GUARDAN LOS DATOS Y SE MUESTRA EL MENÚ)
@bot.message_handler(func=lambda m: estado_usuarios.get(m.chat.id) == "esperando_dieta")
def registrar_dieta(message):
    chat_id = message.chat.id
    texto = message.text.strip()
    opciones_validas = ["Déficit calórico", "Recomposición muscular", "Superávit calórico"]
    if texto in opciones_validas:
        usuarios_datos[chat_id]["dieta"] = texto
        estado_usuarios[chat_id] = "menu"
        guardar_perfil_en_firebase(chat_id)
        markup = ReplyKeyboardRemove()
        bot.send_message(chat_id, "✅ ¡Registro completo!\n🎉 Bienvenido a *NutrIA*", parse_mode="Markdown", reply_markup=markup)
        # Llamar al menú después de completar el registro
        mostrar_menu(message)
        print(usuarios_datos)
    else:
        markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, input_field_placeholder="Selecciona una opción")
        markup.add("Déficit calórico", "Recomposición muscular", "Superávit calórico")
        bot.send_message(chat_id, "❗ Pulsa un botón, no escribas manualmente:", reply_markup=markup)


# --- NUEVAS FUNCIONES PARA LA LÓGICA DE TU MENÚ ---

def guardar_registro_diario(chat_id, proteina_nueva, grasa_nueva, carbohidratos_nuevos, calorias_nuevas):
    """
    Guarda y acumula los macronutrientes y calorías del día para un usuario en Firebase.
    """
    try:
        hoy = date.today().isoformat()  # Formato YYYY-MM-DD
        registro_diario_ref = db_ref.child(str(chat_id)).child('registros').child('diario').child(hoy)
        registro_actual = registro_diario_ref.get()
        
        if registro_actual:
            proteina_total = registro_actual.get('total_proteina', 0) + proteina_nueva
            grasa_total = registro_actual.get('total_grasa', 0) + grasa_nueva
            carbohidratos_total = registro_actual.get('total_carbohidratos', 0) + carbohidratos_nuevos
            calorias_total = registro_actual.get('total_calorias', 0) + calorias_nuevas
        else:
            proteina_total = proteina_nueva
            grasa_total = grasa_nueva
            carbohidratos_total = carbohidratos_nuevos
            calorias_total = calorias_nuevas

        datos_a_guardar = {
            'total_proteina': proteina_total,
            'total_grasa': grasa_total,
            'total_carbohidratos': carbohidratos_total,
            'total_calorias': calorias_total
        }
        
        registro_diario_ref.set(datos_a_guardar)
        logger.info(f"Registro diario para {chat_id} actualizado. Fecha: {hoy}")

    except Exception as e:
        logger.error(f"Error al guardar el registro diario para {chat_id}: {e}")
        bot.send_message(chat_id, "❌ Ocurrió un error al registrar tu comida. Inténtalo de nuevo más tarde.")


# Manejador para la selección del tipo de comida para la recomendación
@bot.message_handler(func=lambda m: estado_usuarios.get(m.chat.id) == "esperando_tipo_comida_recomendacion")
def registrar_tipo_comida_recomendacion(message):
    chat_id = message.chat.id
    tipo_comida = message.text.strip().capitalize()
    opciones_validas = ["Desayuno", "Almuerzo", "Cena"]
    if tipo_comida not in opciones_validas:
        bot.send_message(chat_id, "❌ Opción no válida. Por favor, elige 'Desayuno', 'Almuerzo' o 'Cena'.")
        return
    usuarios_datos[chat_id]["tipo_comida_recomendacion"] = tipo_comida
    bot.send_message(chat_id, "⏳ Generando tu recomendación...")
    recomendacion_completa = obtener_recomendacion_chatgpt(chat_id, tipo_comida)
    
    match_plato = re.search(r'te prepares (.+?), ya que es rico', recomendacion_completa, re.IGNORECASE)
    nombre_plato_recomendado = match_plato.group(1).strip() if match_plato else "Receta Recomendada"
    usuarios_datos[chat_id]["ultimo_item_para_registrar"] = {
        "tipo": "recomendacion",
        "nombre": nombre_plato_recomendado,
        "analisis": recomendacion_completa
    }
    bot.send_message(chat_id, recomendacion_completa, parse_mode="Markdown")
    estado_usuarios[chat_id] = "confirmar_registro_item"
    bot.send_message(chat_id, "📝 ¿Deseas registrar este alimento/receta para tu seguimiento nutricional?\nResponde *sí* o *no*.", parse_mode="Markdown")


# Manejador general para todas las respuestas de texto
@bot.message_handler(func=lambda message: True)
def responder_a_todo(message):
    chat_id = message.chat.id
    user_input = message.text.strip()
    
    # Manejo de las opciones del menú
    if estado_usuarios.get(chat_id) == "menu":
        if user_input == "1":
            estado_usuarios[chat_id] = "registro_comida"
            bot.send_message(chat_id, "🍽️ Escribe el nombre del plato o comida que deseas analizar:")
            return
        elif user_input == "2":
            if db_ref.child(str(chat_id)).child('perfil').get():
                estado_usuarios[chat_id] = "esperando_tipo_comida_recomendacion"
                markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, input_field_placeholder="Pulsa una opción")
                markup.add("Desayuno", "Almuerzo", "Cena")
                bot.send_message(chat_id, "¿Para qué comida del día deseas la recomendación? (Desayuno, Almuerzo, Cena)", reply_markup=markup)
            else:
                bot.send_message(chat_id, "⚠️ Para darte recomendaciones, necesito que completes tu registro con /start.")
            return
        elif user_input == "3":
            # Aquí iría la lógica para la opción de seguimiento nutricional
            bot.send_message(chat_id, "Esta opción aún no está implementada. ¡Pronto estará disponible!")
            return
        elif user_input == "4":
            # Aquí iría la lógica para editar perfil
            bot.send_message(chat_id, "Esta opción aún no está implementada. ¡Pronto estará disponible!")
            return
        else:
            # Si el usuario no selecciona una opción del menú, responde como asistente general
            respuesta = responder_chatgpt(user_input)
            bot.send_message(chat_id, respuesta)
            return

    # Si el estado es "registro_comida", analiza la comida
    if estado_usuarios.get(chat_id) == "registro_comida":
        plato_analizar = user_input
        resultado_analisis = analizar_comida_chatgpt(plato_analizar)
        bot.send_message(chat_id, resultado_analisis)
        if chat_id not in usuarios_datos:
            usuarios_datos[chat_id] = {}
        usuarios_datos[chat_id]["ultimo_item_para_registrar"] = {
            "tipo": "comida",
            "nombre": plato_analizar,
            "analisis": resultado_analisis
        }
        estado_usuarios[chat_id] = "confirmar_registro_item"
        bot.send_message(chat_id, "📝 ¿Deseas registrar este alimento/receta para tu seguimiento nutricional?\nResponde *sí* o *no*.", parse_mode="Markdown")
        return
    
    # Manejador para la confirmación de registro
    if estado_usuarios.get(chat_id) == "confirmar_registro_item":
        respuesta = user_input.lower()
        item_data = usuarios_datos[chat_id].get("ultimo_item_para_registrar", {})
        if not item_data:
            bot.send_message(chat_id, "⚠️ No hay alimento/receta para registrar.")
            estado_usuarios[chat_id] = "menu"
            mostrar_menu(message)
            return

        if respuesta in ["sí", "si"]:
            analisis_texto = item_data.get("analisis", "")
            proteina_match = re.search(r'(\d+)\s*g de proteína', analisis_texto)
            grasa_match = re.search(r'(\d+)\s*g de grasa', analisis_texto)
            carbohidratos_match = re.search(r'(\d+)\s*g de carbohidratos', analisis_texto)
            calorias_match = re.search(r'(\d+)\s*calorías', analisis_texto)
            
            proteina = int(proteina_match.group(1)) if proteina_match else 0
            grasa = int(grasa_match.group(1)) if grasa_match else 0
            carbohidratos = int(carbohidratos_match.group(1)) if carbohidratos_match else 0
            calorias = int(calorias_match.group(1)) if calorias_match else 0

            guardar_registro_diario(chat_id, proteina, grasa, carbohidratos, calorias)
            bot.send_message(chat_id, "✅ Alimento/Receta registrada exitosamente.")
        elif respuesta == "no":
            bot.send_message(chat_id, "🍽️ Está bien. No se registró el alimento/receta.")
        else:
            bot.send_message(chat_id, "❗ Responde *sí* o *no* para registrar el alimento/receta.", parse_mode="Markdown")
            return
        
        estado_usuarios[chat_id] = "menu"
        mostrar_menu(message)
        return

    # Si no está en un flujo específico y no es un comando, responde como asistente general
    if estado_usuarios.get(chat_id) == "menu":
        respuesta = responder_chatgpt(user_input)
        bot.send_message(chat_id, respuesta)
    else:
        bot.send_message(chat_id, "🤔 No entiendo. Usa /menu para ver las opciones o /help para una guía.")


# --- FUNCIONES DE CHATGPT ---
# Asegúrate de que tu `config.py` tenga `OPENAI_API_KEY`
# Y de que la librería `openai` esté instalada con `pip install openai`
# openai.api_key = OPENAI_API_KEY 

def responder_chatgpt(mensaje_usuario):
    """Función para dar respuestas generales con ChatGPT."""
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente experto en nutrición. Da consejos personalizados sobre alimentación, recetas saludables, déficit calórico y bienestar general. Sé claro y amable."},
                {"role": "user", "content": mensaje_usuario}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Hubo un error al procesar tu solicitud: {e}"

def analizar_comida_chatgpt(plato):
    """Función para analizar una comida con ChatGPT y extraer macronutrientes."""
    prompt = f"""Eres un nutricionista. El usuario te indicará un plato. Tu tarea es DEVOLVER ÚNICAMENTE los valores aproximados de macronutrientes y calorías para ese plato. Es crucial que SIEMPRE respondas en el formato exacto especificado a continuación, incluso si debes hacer una estimación general. NO agregues ningún texto adicional, explicaciones, disculpas, ni menciones que no tienes información. Asegúrate de que los valores numéricos estén presentes.
Para el plato "{plato}" tiene:
• Xg de proteína
• Yg de grasa
• Zg de carbohidratos
• W calorías"""
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un nutricionista especializado en análisis de comidas. Tu respuesta debe ser *siempre* concisa, seguir el formato exacto especificado y *nunca* indicar falta de información. Siempre proporciona una estimación con valores numéricos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error al analizar la comida: {e}"

def obtener_recomendacion_chatgpt(chat_id, tipo_comida):
    """Función para obtener una recomendación de receta con ChatGPT."""
    user_data = usuarios_datos.get(chat_id)
    if not user_data:
        return "⚠️ No tengo tus datos de registro para darte recomendaciones. Por favor, usa /start para registrarte."
    economia = user_data.get("economia", "No especificada").lower()
    dieta = user_data.get("dieta", "No especificada").lower()
    nombre = user_data.get("nombre", "Usuario")
    prompt = f"""Hola {nombre}. Eres un nutricionista experto en dar recomendaciones de recetas.
Considerando que mi estabilidad económica es '{economia}' y mi tipo de dieta es '{dieta}', por favor, sugiere una receta saludable y económica para el '{tipo_comida}'.
Tu respuesta debe seguir el siguiente formato EXACTO, incluyendo la sección de macronutrientes al final. Asegúrate de que los valores numéricos estén presentes.
Para un {tipo_comida} te recomiendo que te prepares [Nombre del Plato], ya que es rico en [cualidades nutricionales, ej., proteínas y fibra].
[Descripción breve de la receta, ingredientes y preparación en 3-5 líneas].
Para [Nombre del Plato] se calcula que:
• Xg de proteína
• Yg de grasa
• Zg de carbohidratos
• W calorías"""
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un nutricionista experto en la creación de recetas saludables y económicas, adaptadas a diferentes tipos de dieta y estabilidad económica. Tu respuesta debe ser concisa y seguir el formato exacto especificado, incluyendo valores numéricos para los macronutrientes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Hubo un error al obtener recomendaciones: {e}"

# Inicia el bot para que escuche mensajes
print("Bot en funcionamiento...")
bot.infinity_polling()
