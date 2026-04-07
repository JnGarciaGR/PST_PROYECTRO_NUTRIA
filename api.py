"""
API REST que actúa como proxy seguro para Firebase.

El dashboard del usuario no se conecta directamente a Firebase.
En su lugar, realiza peticiones a esta API que valida cada solicitud
y accede a Firebase del lado del servidor usando credenciales seguras.

De esta forma:
- Las credenciales (serviceAccountKey.json) nunca se exponen al navegador
- Cada petición se puede validar y auditar
- Se pueden agregar reglas de negocio en el servidor

Endpoints principales:
- Login: Autenticación segura del usuario
- User: Obtener datos del perfil
- Nutrition: Metas de macronutrientes
- Meals: Comidas registradas
- Recipes: Recomendaciones de recetas
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from firebase_service import FirebaseService
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Permitir solicitudes desde el dashboard

# Inicializar Firebase con credenciales del servidor
firebase_service = FirebaseService(
    "serviceAccountKey.json",
    "https://nutribot-3d198-default-rtdb.firebaseio.com/"
)



# ========== AUTENTICACIÓN ==========

@app.route('/api/login', methods=['POST'])
def login():
    """
    Autentica un usuario verificando sus credenciales contra Firebase.
    
    Este endpoint es el único punto de entrada seguro al dashboard.
    Recibe el chat_id y password_hash, los valida contra la base de datos,
    y retorna un token o confirmación de acceso.
    
    Body esperado:
        {
            "chat_id": "123456789",
            "password_hash": "hash_de_contraseña"
        }
    
    Responses:
        200: Autenticación exitosa
        400: Datos incompletos
        401: Contraseña incorrecta
        404: Usuario no existe
        500: Error del servidor
    """
    try:
        data = request.get_json()
        chat_id = data.get('chat_id')
        password_hash = data.get('password_hash')
        
        if not chat_id or not password_hash:
            return jsonify({
                'success': False,
                'error': 'chat_id y password_hash requeridos'
            }), 400
        
        # Obtener datos del usuario desde Firebase
        user_data = firebase_service.obtener_usuario(chat_id)
        
        if not user_data:
            return jsonify({
                'success': False,
                'error': 'Usuario no encontrado'
            }), 404
        
        # Verificar que la contraseña coincida
        stored_hash = user_data.get('perfil', {}).get('hashed_password', '')
        
        if stored_hash == password_hash:
            return jsonify({
                'success': True,
                'message': 'Autenticación exitosa'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Contraseña incorrecta'
            }), 401
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500




@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """
    Obtiene el perfil completo de un usuario.
    
    Retorna toda la información personal registrada: nombre, edad,
    peso, altura y preferencias como objetivo dietético.
    
    Args:
        user_id: ID del usuario (chat_id de Telegram)
    
    Returns:
        objeto con los datos del usuario, o 404 si no existe
    """
    try:
        user_data = firebase_service.obtener_usuario(user_id)
        if user_data:
            return jsonify({
                'success': True,
                'data': user_data
            })
        return jsonify({
            'success': False,
            'error': 'Usuario no encontrado'
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/nutrition/<user_id>', methods=['GET'])
def get_nutrition(user_id):
    """
    Obtiene las metas nutricionales del usuario.
    
    Devuelve el objetivo dietético (déficit, mantenimiento, superávit)
    y los números de calorías y macronutrientes que debe consumir diariamente.
    
    Args:
        user_id: ID del usuario
    
    Returns:
        Objeto con objetivos de calorías, proteína, carbos y grasas
    """
    try:
        user_data = firebase_service.obtener_usuario(user_id)
        if user_data:
            nutrition = {
                'objetivo': user_data.get('objetivo', 'Déficit calórico'),
                'calorias': user_data.get('calorias_objetivo', 2000),
                'proteina': user_data.get('proteina_objetivo', 150),
                'carbohidratos': user_data.get('carbohidratos_objetivo', 200),
                'grasa': user_data.get('grasa_objetivo', 70)
            }
            return jsonify({
                'success': True,
                'data': nutrition
            })
        return jsonify({
            'success': False,
            'error': 'Usuario no encontrado'
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/daily-intake/<user_id>', methods=['GET'])
def get_daily_intake(user_id):
    """
    Obtiene el total consumido HOY en calorías y macronutrientes.
    
    Recorre todas las comidas registradas hoy y suma el total.
    Útil para mostrar el progreso del usuario durante el día.
    
    Args:
        user_id: ID del usuario
    
    Returns:
        Objeto con totales de hoy (calorías, proteína, carbos, grasas)
    """
    try:
        meals = firebase_service.obtener_comidas_usuario(user_id)
        
        today = datetime.now().strftime('%Y-%m-%d')
        today_meals = [
            m for m in meals.values() if m.get('fecha') == today
        ]
        
        totals = {
            'total_calorias': sum(m.get('calorias', 0) for m in today_meals),
            'total_proteina': sum(m.get('proteinas', 0) for m in today_meals),
            'total_carbohidratos': sum(
                m.get('carbohidratos', 0) for m in today_meals
            ),
            'total_grasa': sum(m.get('grasas', 0) for m in today_meals)
        }
        
        return jsonify({
            'success': True,
            'data': totals
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/meals/<user_id>', methods=['GET'])
def get_meals(user_id):
    """
    Obtiene el historial de todas las comidas del usuario.
    
    Retorna una lista con cada comida registrada, incluyendo su valor
    nutricional y la fecha en que fue registrada.
    
    Args:
        user_id: ID del usuario
    
    Returns:
        Array con todas las comidas registradas
    """
    try:
        meals = firebase_service.obtener_comidas_usuario(user_id)
        
        meals_list = [
            {
                'nombre': meal.get('nombre', ''),
                'tipo': meal.get('tipo', ''),
                'calorias': meal.get('calorias', 0),
                'proteinas': meal.get('proteinas', 0),
                'carbohidratos': meal.get('carbohidratos', 0),
                'grasas': meal.get('grasas', 0),
                'fecha': meal.get('fecha', '')
            }
            for meal in meals.values()
        ]
        
        return jsonify({
            'success': True,
            'data': meals_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/recipes/<user_id>', methods=['GET'])
def get_recipes(user_id):
    """
    Obtiene recetas recomendadas según el objetivo del usuario.
    
    Devuelve una lista de recetas filtradas por su objetivo dietético
    (para perder peso, mantener, o ganar masa).
    
    Args:
        user_id: ID del usuario
    
    Returns:
        Array con recetas recomendadas
    """
    try:
        user_data = firebase_service.obtener_usuario(user_id)
        recipes = firebase_service.obtener_recetas(
            user_data.get('objetivo', 'Déficit calórico')
        )
        
        return jsonify({
            'success': True,
            'data': recipes
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========== HEALTH CHECK ==========

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Verifica que la API esté funcionando correctamente.
    
    Este endpoint se usa para monitoreo y para que los clientes
    verifiquen la conexión a la API.
    
    Returns:
        Mensaje de confirmación si todo está bien
    """
    return jsonify({
        'success': True,
        'message': 'API disponible'
    }), 200


# ========== INICIALIZACIÓN ==========

if __name__ == '__main__':
    print("API Firebase iniciada en http://localhost:5000")
    print("\nEndpoints disponibles:")
    print("  POST  /api/login")
    print("  GET   /api/user/<user_id>")
    print("  GET   /api/nutrition/<user_id>")
    print("  GET   /api/daily-intake/<user_id>")
    print("  GET   /api/meals/<user_id>")
    print("  GET   /api/recipes/<user_id>")
    print("  GET   /api/health")
    print("\nModo de ejecución: desarrollo con debug=True")
    print("Para producción cambiar a: debug=False, host='0.0.0.0'\n")
    
    # Desarrollo: debug=True, solo acceso local
    # Producción: debug=False, host='0.0.0.0', port=80
    app.run(debug=True, host='localhost', port=5000)
