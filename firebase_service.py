"""
Servicio de integración con Firebase para el bot NutrIA.

Maneja todas las operaciones de base de datos:
- Gestión de perfiles de usuarios (creación, actualizaciones, eliminación)
- Almacenamiento y recuperación de datos nutricionales
- Seguimiento de progreso y análisis
- Caché de recetas para evitar repetición
"""

import firebase_admin
from firebase_admin import credentials, db
import logging
from typing import Optional, Dict, Any
from datetime import date
import hashlib

from user_model import User, NutritionData

# Configurar logger para debugging
logger = logging.getLogger(__name__)


class FirebaseService:
    """
    Punto de acceso centralizado para todas las operaciones de base de datos Firebase.
    
    Este servicio maneja perfiles de usuarios, seguimiento nutricional, análisis
    de progreso y gestión de recetas. Abstrae la complejidad de la API de Firebase
    y proporciona métodos limpios para que los utilice el bot.
    """
    
    def __init__(self, service_account_path: str, database_url: str):
        """
        Inicializa la conexión con Firebase.
        
        Configura la autenticación usando un archivo JSON de cuenta de servicio y
        se conecta a la Base de Datos en Tiempo Real. Maneja casos donde Firebase
        ya está inicializado (reutiliza la aplicación existente).
        
        Args:
            service_account_path: Ruta al archivo JSON de cuenta de servicio de Firebase
            database_url: URL de la Base de Datos en Tiempo Real
            
        Raises:
            FileNotFoundError: Si el archivo de credenciales no existe
            ValueError: Si la inicialización falla
        """
        try:
            cred = credentials.Certificate(service_account_path)
            
            # Verificar si Firebase ya está inicializado
            try:
                firebase_admin.initialize_app(cred, {
                    'databaseURL': database_url
                })
                logger.info("Firebase inicializado correctamente")
            except ValueError as e:
                if "already exists" in str(e):
                    logger.info("Firebase ya estaba inicializado, reutilizando app existente")
                else:
                    raise
            
            self.db_ref = db.reference('usuarios')
            logger.info("Connected to 'usuarios' reference: " + str(self.db_ref))
            
        except FileNotFoundError:
            logger.error(f"Credentials file not found: {service_account_path}")
            raise
        except Exception as e:
            logger.error(f"Error initializing Firebase: {e}", exc_info=True)
            raise ValueError(f"Could not initialize Firebase: {e}")
    
    # ========== PERFILES DE USUARIO ==========
    
    def usuario_existe(self, chat_id: int) -> bool:
        """
        Verifica si un usuario ya está registrado.
        
        Args:
            chat_id: ID de usuario en Telegram
            
        Returns:
            True si el usuario existe; False en caso contrario
        """
        try:
            usuario = self.db_ref.child(str(chat_id)).child('perfil').get()
            
            # Manejo correcto: .get() puede retornar dict o DataSnapshot
            if isinstance(usuario, dict):
                existe = usuario is not None and len(usuario) > 0
                usuario_val = usuario
            else:
                # Es un objeto DataSnapshot con método .val()
                existe = usuario.val() is not None
                usuario_val = usuario.val()
            
            logger.debug(
                f"Verificando usuario {chat_id}: existe={existe}, "
                f"perfil_data={usuario_val}"
            )
            return existe
        except Exception as e:
            logger.error(
                f"Error checking if user {chat_id} exists: {e}",
                exc_info=True
            )
            return False
    
    def guardar_usuario(self, user: User) -> bool:
        """
        Guarda un perfil de usuario completo en Firebase.
        
        Almacena datos de perfil, inicializa estructuras de seguimiento nutricional,
        y pre-calcula objetivos de macros diarios en función de su perfil.
        
        Args:
            user: Objeto User con datos del perfil
            
        Returns:
            True si se guardó correctamente; False en caso contrario
        """
        try:
            if not user.esta_completo():
                logger.warning(
                    f"Perfil de usuario {user.chat_id} incompleto. "
                    f"Campos: nombre={user.nombre}, cedula={user.cedula}, "
                    f"genero={user.genero}, peso={user.peso}, "
                    f"altura={user.altura_cm}, edad={user.edad}, "
                    f"actividad={user.actividad_fisica}, "
                    f"economia={user.economia}, dieta={user.dieta}"
                )
                return False
            
            # Calcular objetivos diarios de macros
            macros_necesarios = self._calcular_macros_necesarios(user)
            
            estructura_usuario = {
                'perfil': user.a_dict(),
                'comidas': {},
                'historial': {},
                'registros': {
                    'diario': {},
                    'semanal': {},
                    'mensual': {}
                },
                'macros_necesarios': macros_necesarios
            }
            
            logger.debug(
                f"Guardando usuario {user.chat_id} con datos: "
                f"{estructura_usuario['perfil']}"
            )
            
            self.db_ref.child(str(user.chat_id)).set(estructura_usuario)
            logger.info(
                f"Usuario {user.chat_id} guardado exitosamente con macros: "
                f"{macros_necesarios}"
            )
            
            # Verificar que se guardó correctamente
            verificacion = self.usuario_existe(user.chat_id)
            if verificacion:
                logger.info(
                    f"Verificación exitosa: usuario {user.chat_id} "
                    f"existe en Firebase"
                )
            else:
                logger.warning(
                    f"Verificación fallida: usuario {user.chat_id} "
                    f"guardado pero no se puede verificar"
                )
            
            return True
        except Exception as e:
            logger.error(
                f"Error guardando usuario {user.chat_id}: {e}",
                exc_info=True
            )
            return False
    
    def actualizar_dato_usuario(
        self, chat_id: int, campo: str, valor: any
    ) -> bool:
        """
        Actualiza un campo específico del perfil de un usuario.
        
        Args:
            chat_id: ID del usuario en Telegram
            campo: Nombre del campo a actualizar
                   (economia, actividad_fisica, dieta)
            valor: Nuevo valor del campo
            
        Returns:
            True si se actualizó correctamente, False en caso contrario
        """
        try:
            logger.debug(
                f"Actualizando {campo}={valor} para usuario {chat_id}"
            )
            
            # Update the field in profile
            self.db_ref.child(str(chat_id)).child('perfil').child(campo).set(valor)
            
            # If macro-affecting field changed, recalculate targets
            if campo in ['economia', 'actividad_fisica', 'dieta']:
                user = self.cargar_usuario(chat_id)
                if user:
                    macros_necesarios = self._calcular_macros_necesarios(user)
                    self.db_ref.child(str(chat_id)).child('macros_necesarios').set(
                        macros_necesarios
                    )
                    logger.info(
                        f"Macros recalculated for user {chat_id}: {macros_necesarios}"
                    )
            
            logger.info(
                f"User {chat_id}: {campo} updated to {valor}"
            )
            return True
        
        except Exception as e:
            logger.error(
                f"Error updating {campo} for user {chat_id}: {e}",
                exc_info=True
            )
            return False
    
    def _calcular_macros_necesarios(self, user: 'User') -> Dict[str, float]:
        """
        Calcula los macros necesarios diarios basado en el perfil del usuario.
        
        ✅ MEJORADO 2026-03-27:
        - Usa Mifflin-St Jeor (más preciso, más moderno)
        - Ajusta proteína dinámicamente según tipo de dieta
        - Distribuye carbohidratos inteligentemente
        
        Fórmula base: Mifflin-St Jeor (1990)
            Hombre: TMB = (10×peso) + (6.25×altura) - (5×edad) + 5
            Mujer:  TMB = (10×peso) + (6.25×altura) - (5×edad) - 161
        
        Validado por:
        - American Academy of Nutrition and Dietetics ✓
        - ISSN (International Society of Sports Nutrition) ✓
        - NIH (National Institutes of Health) ✓
        
        Args:
            user: Objeto User con datos del usuario
            
        Returns:
            Diccionario con calorías, proteína, grasa y carbohidratos
        """
        try:
            # MIFFLIN-ST JEOR (More accurate, ±10-20% error)
            if user.genero.lower() == "hombre":
                tmb = (10 * user.peso) + (6.25 * user.altura_cm) - (5 * user.edad) + 5
            else:
                tmb = (10 * user.peso) + (6.25 * user.altura_cm) - (5 * user.edad) - 161
            
            # Factores de actividad física (Validados)
            factores_actividad = {
                "Sedentario": 1.2,
                "Ligera": 1.375,
                "Moderada": 1.55,
                "Intensa": 1.725,
                "Muy intensa": 1.9
            }
            
            factor_actividad = factores_actividad.get(
                user.actividad_fisica, 1.55
            )
            
            # TDEE (Total Daily Energy Expenditure)
            tdee = tmb * factor_actividad
            
            # Adjust based on diet type and calculate protein dynamically
            if user.dieta == "Déficit calórico":
                calorias_diarias = tdee * 0.85  # 15% déficit (pérdida 0.5-0.75kg/semana)
                # Proteína más alta en déficit para preservar músculo (2.3g/kg)
                proteina = user.peso * 2.3
                logger.info(f"DEFICIT diet: -15% calories, protein increased to 2.3g/kg")
                
            elif user.dieta == "Superávit calórico":
                calorias_diarias = tdee * 1.15  # 15% superávit (ganancia 0.5-0.75kg/semana)
                # Proteína más baja en superávit (1.8g/kg, suficiente para ganancia)
                proteina = user.peso * 1.8
                logger.info(f"SURPLUS diet: +15% calories, protein at 1.8g/kg")
                
            else:  # Recomposición muscular
                calorias_diarias = tdee  # Mantenimiento calórico
                # Proteína estándar (2.0g/kg optimo para recomposición)
                proteina = user.peso * 2.0
                logger.info(f"Dieta RECOMPOSICIÓN: Mantenimiento calórico, proteína 2.0g/kg")
            
            # Macro distribution
            # Fats: 25% of calories (validated range: 20-35%)
            grasa = (calorias_diarias * 0.25) / 9  # 9 kcal/g
            
            # Carbs: Remaining calories (validated scientific method)
            carbohidratos = (calorias_diarias - (proteina * 4) - (grasa * 9)) / 4
            
            macros = {
                'calorias': round(calorias_diarias, 1),
                'proteina': round(proteina, 1),
                'grasa': round(grasa, 1),
                'carbohidratos': round(carbohidratos, 1)
            }
            
            logger.debug(
                f"Macros calculated for {user.chat_id}: {macros}"
            )
            
            return macros
        except Exception as e:
            logger.error(
                f"Error calculating macros for user {user.chat_id}: {e}",
                exc_info=True
            )
            # Return default values if error
            return {
                'calorias': 2000,
                'proteina': 150,
                'grasa': 65,
                'carbohidratos': 200
            }
    
    def guardar_password(self, chat_id: int, contraseña: str, usuario: str = None) -> bool:
        """
        Store the user's hashed password in Firebase.
        
        Uses SHA256 hashing (same as React dashboard) and stores it in the
        user's profile. The 'usuario' parameter is deprecated but kept for
        backwards compatibility.
        
        Args:
            chat_id: Telegram user ID (primary identifier)
            contraseña: Password in plain text
            usuario: (DEPRECATED) Custom username - now ignored
            
        Returns:
            True if saved successfully; False otherwise
        """
        try:
            logger.info(
                f"[GUARDAR_PASSWORD] Iniciando. "
                f"chat_id={chat_id}, contraseña='***'"
            )
            
            # Hash SHA256 como en el dashboard React
            hashed_password = hashlib.sha256(contraseña.encode()).hexdigest()
            logger.debug(
                f"[GUARDAR_PASSWORD] Hash calculado: {hashed_password[:16]}..."
            )
            
            # Guardar contraseña en el perfil (ÚNICO lugar de almacenamiento)
            logger.info(
                f"[GUARDAR_PASSWORD] Guardando contraseña en "
                f"/usuarios/{chat_id}/perfil/hashed_password"
            )
            self.db_ref.child(str(chat_id)).child('perfil').child('hashed_password').set(hashed_password)
            logger.info(f"[GUARDAR_PASSWORD] ✅ Contraseña guardada correctamente")
            
            if usuario:
                logger.info(
                    f"[GUARDAR_PASSWORD] ⚠️ Parámetro 'usuario' proporcionado ('{usuario}') "
                    f"pero será ignorado. Sistema usa SOLO chat_id como identificador."
                )
            
            logger.info(
                f"[GUARDAR_PASSWORD] ✅ Credenciales guardadas correctamente (chat_id only)"
            )
            return True
        except Exception as e:
            logger.error(
                f"[SAVE_PASSWORD] Error saving credentials for "
                f"user {chat_id}: {e}",
                exc_info=True
            )
            return False
    
    def usuario_tiene_password(self, chat_id: int) -> bool:
        """
        Check if a user already has a password registered.
        
        Args:
            chat_id: Telegram user ID
            
        Returns:
            True if password exists; False otherwise
        """
        try:
            password_ref = self.db_ref.child(str(chat_id)).child('perfil').child('hashed_password').get()
            
            # Manejo correcto: .get() puede retornar string directamente, dict o DataSnapshot
            if isinstance(password_ref, str):
                # Pyrebase4 retorna un string directamente para valores simples
                tiene_password = len(password_ref) > 0
                logger.debug(f"[CHECK_PASSWORD] User {chat_id}: has_password={tiene_password} (direct string)")
            elif isinstance(password_ref, dict):
                # If a dictionary, check if it has content and if value is valid
                tiene_password = (password_ref is not None and 
                                 len(password_ref) > 0 and 
                                 password_ref.get('hashed_password') is not None)
                logger.debug(f"[CHECK_PASSWORD] User {chat_id}: has_password={tiene_password} (dict)")
            else:
                # Es un objeto DataSnapshot
                valor = password_ref.val() if password_ref else None
                tiene_password = valor is not None
                logger.debug(f"[CHECK_PASSWORD] User {chat_id}: has_password={tiene_password} (DataSnapshot)")
            
            logger.info(
                f"[CHECK_PASSWORD] Verificación de password para usuario {chat_id}: {tiene_password}"
            )
            return tiene_password
        except Exception as e:
            logger.error(
                f"[CHECK_PASSWORD] Error al verificar password del usuario {chat_id}: {e}",
                exc_info=True
            )
            return False
    
    def cargar_usuario(self, chat_id: int) -> Optional[User]:
        """
        Load a user's profile from Firebase.
        
        Args:
            chat_id: Telegram user ID
            
        Returns:
            User object if found; None otherwise
        """
        try:
            resultado = self.db_ref.child(str(chat_id)).child('perfil').get()
            
            # Manejo correcto: .get() puede retornar dict o DataSnapshot
            if isinstance(resultado, dict):
                resultado_val = resultado if resultado else None
            else:
                resultado_val = resultado.val() if resultado else None
            
            if resultado_val is None:
                return None
            
            user = User.desde_dict(chat_id, resultado_val)
            return user
        except Exception as e:
            logger.error(f"Error loading user {chat_id}: {e}")
            return None
    
    def eliminar_usuario(self, chat_id: int) -> bool:
        """
        Completely delete a user's profile and all data.
        
        Args:
            chat_id: Telegram user ID to delete
            
        Returns:
            True if deleted successfully; False otherwise
        """
        try:
            self.db_ref.child(str(chat_id)).delete()
            logger.info(f"User {chat_id} deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Error deleting user {chat_id}: {e}")
            return False
    
    # ========== REGISTROS NUTRICIONALES ==========
    
    def guardar_registro_diario(self, chat_id: int, nutrition: NutritionData) -> bool:
        """
        Save or update the user's daily nutrition record.
        
        Accumulates nutrient totals throughout the day. If a record
        already exists, adds new values to existing totals.
        
        Args:
            chat_id: Telegram user ID
            nutrition: NutritionData object with meal nutrients
            
        Returns:
            True if saved successfully; False otherwise
        """
        try:
            hoy = date.today().isoformat()  # Format YYYY-MM-DD
            registro_ref = self.db_ref.child(str(chat_id)).child('registros').child('diario').child(hoy)
            
            logger.debug(
                f"Saving daily record for user {chat_id} "
                f"on {hoy} with data: protein={nutrition.proteina}, "
                f"fat={nutrition.grasa}, carbs={nutrition.carbohidratos}, "
                f"calories={nutrition.calorias}"
            )
            
            # Check if user exists first
            usuario_data = self.db_ref.child(str(chat_id)).get()
            
            # Manejo correcto: .get() puede retornar dict o DataSnapshot
            if isinstance(usuario_data, dict):
                usuario_data_val = usuario_data if usuario_data else None
            else:
                usuario_data_val = usuario_data.val() if usuario_data else None
            
            if usuario_data_val is None:
                logger.error(
                    f"User {chat_id} does not exist in Firebase. "
                    f"Cannot save record."
                )
                return False
            
            # Get current record if exists
            try:
                registro_actual = registro_ref.get()
                logger.debug(f"registro_actual type: {type(registro_actual)}")
            except Exception as e:
                logger.warning(
                    f"Error retrieving previous record: {e}. "
                    f"Continuing with new record."
                )
                registro_actual = None
            
            # Process the retrieved data
            # Correct handling: registro_actual can be dict or DataSnapshot
            if isinstance(registro_actual, dict):
                registro_actual_val = registro_actual if registro_actual else None
            else:
                registro_actual_val = registro_actual.val() if registro_actual else None
            
            if registro_actual_val is not None:
                logger.debug(
                    f"Found previous record for {chat_id} on {hoy}: "
                    f"{registro_actual_val}"
                )
                # Accumulate values
                nutrition_existente = NutritionData.desde_dict(registro_actual_val)
                nutrition_total = nutrition_existente + nutrition
            else:
                logger.debug(
                    f"No previous record for {chat_id} on {hoy}, "
                    f"creating new one"
                )
                nutrition_total = nutrition
            
            # Save accumulated data USING UPDATE (NOT set) to not overwrite meals
            logger.debug(
                f"Saving to Firebase: {nutrition_total.a_dict()}"
            )
            registro_ref.update(nutrition_total.a_dict())
            logger.info(
                f"Daily record saved for user {chat_id}, "
                f"date: {hoy}, totals: protein={nutrition_total.proteina}, "
                f"fat={nutrition_total.grasa}, "
                f"carbs={nutrition_total.carbohidratos}, "
                f"calories={nutrition_total.calorias}"
            )
            return True
        except Exception as e:
            logger.error(
                f"Error saving daily record for {chat_id}: {e}",
                exc_info=True
            )
            return False
    
    def cargar_registro_diario(self, chat_id: int, fecha: Optional[str] = None) -> Optional[NutritionData]:
        """
        Carga el registro nutricional de un día específico.
        
        Args:
            chat_id: ID del usuario
            fecha: Fecha en formato YYYY-MM-DD. Si es None, usa hoy
            
        Returns:
            Objeto NutritionData si existe, None en caso contrario
        """
        try:
            if fecha is None:
                fecha = date.today().isoformat()
            
            resultado = self.db_ref.child(str(chat_id)).child('registros').child('diario').child(fecha).get()
            
            # Manejo correcto: .get() puede retornar dict o DataSnapshot
            if isinstance(resultado, dict):
                resultado_val = resultado if resultado else None
            else:
                resultado_val = resultado.val() if resultado else None
            
            if resultado_val is None:
                return None
            
            return NutritionData.desde_dict(resultado_val)
        except Exception as e:
            logger.error(f"Error loading daily record for {chat_id}: {e}")
            return None
    
    def guardar_comida(self, chat_id: int, nombre_comida: str, nutrition: NutritionData) -> bool:
        """
        Guarda una comida específica DENTRO DEL REGISTRO DIARIO.
        
        Guarda en: /usuarios/{chat_id}/registros/diario/{fecha}/comidas/{nombre_comida}
        
        IMPORTANTE: Esta función guarda DETALLES de la comida para que el Dashboard
        pueda mostrar cada comida registrada en el día.
        
        Args:
            chat_id: ID del usuario
            nombre_comida: Nombre de la comida
            nutrition: Datos nutricionales de la comida
            
        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        try:
            today = date.today().isoformat()  # YYYY-MM-DD
            
            # Structure expected by dashboard:
            # /registros/diario/{date}/comidas/{meal_name}/
            #   {
            #     calorias: 300,
            #     proteinas: 20,
            #     carbohidratos: 45,
            #     grasas: 10
            #   }
            
            comida_data = {
                'calorias': nutrition.calorias,
                'proteinas': nutrition.proteina,
                'carbohidratos': nutrition.carbohidratos,
                'grasas': nutrition.grasa
            }
            
            logger.debug(
                f"Saving meal '{nombre_comida}' for {chat_id} on {today}: "
                f"{comida_data}"
            )
            
            # Save at: /usuarios/{chat_id}/registros/diario/{date}/comidas/{meal_name}
            comida_ref = (
                self.db_ref
                .child(str(chat_id))
                .child('registros')
                .child('diario')
                .child(today)
                .child('comidas')
                .child(nombre_comida)  # Keep capitalization (do not use .lower())
            )
            comida_ref.set(comida_data)
            
            logger.info(
                f"Meal '{nombre_comida}' saved in daily record for user {chat_id}"
            )
            return True
        except Exception as e:
            logger.error(
                f"Error saving meal '{nombre_comida}' for {chat_id}: {e}",
                exc_info=True
            )
            return False
    
    def cargar_todas_comidas(self, chat_id: int) -> Dict[str, Any]:
        """
        Load all meals ever recorded by a user.
        
        Args:
            chat_id: Telegram user ID
            
        Returns:
            Dictionary with all meals; empty dict if none found
        """
        try:
            resultado = self.db_ref.child(str(chat_id)).child('comidas').get()
            
            # Manejo correcto: .get() puede retornar dict o DataSnapshot
            if isinstance(resultado, dict):
                resultado_val = resultado if resultado else None
            else:
                resultado_val = resultado.val() if resultado else None
            
            if resultado_val is None:
                return {}
            
            return resultado_val
        except Exception as e:
            logger.error(f"Error loading meals for {chat_id}: {e}")
            return {}
    
    # ========== PROGRESO Y ANÁLISIS DE USUARIO ==========
    
    def obtener_totales_dia(self, chat_id: int, fecha: str) -> Dict[str, float]:
        """
        Obtiene los totales de macronutrientes consumidos en un día específico.
        
        Estructura en Firebase:
        /usuarios/{chat_id}/registros/diario/{fecha}/comidas/{comida_nombre}
        
        Args:
            chat_id: ID del usuario
            fecha: Fecha en formato YYYY-MM-DD
            
        Returns:
            Diccionario con totales: {calorias, proteina, grasa, carbohidratos}
        """
        try:
            from datetime import datetime
            
            # Load all meals for the day
            comidas_ref = (
                self.db_ref
                .child(str(chat_id))
                .child('registros')
                .child('diario')
                .child(fecha)
                .child('comidas')
                .get()
            )
            
            # Manejo correcto del resultado (comidas_ref puede ser None)
            if comidas_ref is None:
                comidas_dict = {}
            elif isinstance(comidas_ref, dict):
                comidas_dict = comidas_ref if comidas_ref else {}
            else:
                comidas_dict = comidas_ref.val() if comidas_ref.val() else {}
            
            if not comidas_dict:
                logger.debug(f"No meals recorded for {chat_id} on {fecha}")
                return {
                    'calorias': 0,
                    'proteina': 0,
                    'grasa': 0,
                    'carbohidratos': 0
                }
            
            # Accumulate macros from all meals
            totales = {
                'calorias': 0,
                'proteina': 0,
                'grasa': 0,
                'carbohidratos': 0
            }
            
            for comida_nombre, comida_data in comidas_dict.items():
                if isinstance(comida_data, dict):
                    # Each meal has: {name, calories, protein, fat, carbs, timestamp}
                    totales['calorias'] += float(comida_data.get('calorias', 0))
                    totales['proteina'] += float(comida_data.get('proteina', 0))
                    totales['grasa'] += float(comida_data.get('grasa', 0))
                    totales['carbohidratos'] += float(comida_data.get('carbohidratos', 0))
            
            # Round
            totales = {k: round(v, 1) for k, v in totales.items()}
            
            logger.debug(
                f"Totals for {chat_id} on {fecha}: {totales}"
            )
            return totales
            
        except Exception as e:
            logger.error(
                f"Error getting daily totals for {chat_id} ({fecha}): {e}",
                exc_info=True
            )
            return {
                'calorias': 0,
                'proteina': 0,
                'grasa': 0,
                'carbohidratos': 0
            }
    
    def obtener_progreso_usuario(
        self, 
        chat_id: int, 
        dias: int = 7
    ) -> Dict[str, Any]:
        """
        Calculate user progress over the last N days.
        
        Compares average consumed nutrients vs daily targets.
        Useful for tailoring recommendations based on actual progress.
        
        Args:
            chat_id: Telegram user ID
            dias: Number of days to analyze (default: 7)
            
        Returns:
            Dictionary with:
            - average_consumed: {calories, protein, fat, carbs}
            - macro_targets: {calories, protein, fat, carbs}
            - difference: {calories, protein, fat, carbs}
            - days_recorded: count of days with data
            - compliance_percentage: for each macro
        """
        try:
            from datetime import datetime, timedelta
            
            # Load user to get target macros
            user = self.cargar_usuario(chat_id)
            if not user:
                logger.warning(f"User {chat_id} not found for progress calculation")
                return None
            
            # Load target macros
            macros_objetivo = self._calcular_macros_necesarios(user)
            logger.debug(f"Target macros for {chat_id}: {macros_objetivo}")
            
            # Calculate dates
            hoy = datetime.now().date()
            hace_n_dias = hoy - timedelta(days=dias - 1)
            
            # Accumulate data from last N days
            totales_acumulados = {
                'calorias': 0,
                'proteina': 0,
                'grasa': 0,
                'carbohidratos': 0
            }
            dias_registrados = 0
            
            for i in range(dias):
                fecha_actual = hace_n_dias + timedelta(days=i)
                fecha_str = fecha_actual.strftime('%Y-%m-%d')
                
                totales_dia = self.obtener_totales_dia(chat_id, fecha_str)
                
                # Si hay data para este día, contar
                if any(totales_dia.values()):
                    dias_registrados += 1
                    for macro in totales_acumulados:
                        totales_acumulados[macro] += totales_dia[macro]
            
            # Calculate average
            if dias_registrados > 0:
                promedio_consumido = {
                    k: round(v / dias_registrados, 1) 
                    for k, v in totales_acumulados.items()
                }
            else:
                # No data, use 0
                promedio_consumido = {
                    'calorias': 0,
                    'proteina': 0,
                    'grasa': 0,
                    'carbohidratos': 0
                }
                logger.warning(
                    f"No consumption data for {chat_id} in last {dias} days"
                )
            
            # Calculate difference vs targets
            diferencia = {}
            porcentaje_cumplimiento = {}
            
            for macro in ['calorias', 'proteina', 'grasa', 'carbohidratos']:
                diff = promedio_consumido[macro] - macros_objetivo[macro]
                diferencia[macro] = round(diff, 1)
                
                # Compliance percentage (normally 0-200%)
                if macros_objetivo[macro] > 0:
                    pct = (promedio_consumido[macro] / macros_objetivo[macro]) * 100
                    porcentaje_cumplimiento[macro] = round(pct, 1)
                else:
                    porcentaje_cumplimiento[macro] = 0
            
            resultado = {
                'promedio_consumido': promedio_consumido,
                'macros_objetivo': macros_objetivo,
                'diferencia': diferencia,
                'porcentaje_cumplimiento': porcentaje_cumplimiento,
                'dias_registrados': dias_registrados,
                'periodo_dias': dias
            }
            
            logger.info(
                f"Progress for {chat_id}: {dias_registrados} days recorded, "
                f"calorie compliance: {porcentaje_cumplimiento['calorias']}%"
            )
            
            return resultado
            
        except Exception as e:
            logger.error(
                f"Error calculating progress for {chat_id}: {e}",
                exc_info=True
            )
            return None
    
    # ========== RECETAS GENERADAS (ANTI-REPETICIÓN) ==========
    
    def guardar_receta_generada(
        self, 
        chat_id: int, 
        tipo_comida: str, 
        nombre_receta: str, 
        contenido: str
    ) -> bool:
        """
        Save a generated recipe to prevent repetition.
        
        Stores in: /usuarios/{chat_id}/recetas_generadas/{meal_type}/{timestamp}
        
        Args:
            chat_id: Telegram user ID
            tipo_comida: Meal type (Breakfast, Lunch, Dinner)
            nombre_receta: Name of the dish (e.g. "Rice with Chicken")
            contenido: Full recipe content generated by AI
            
        Returns:
            True if saved successfully; False otherwise
        """
        try:
            from datetime import datetime
            
            # Use timestamp without illegal Firebase characters (: and . are illegal in paths)
            timestamp_full = datetime.now().isoformat()
            timestamp_clean = timestamp_full.replace(':', '-').replace('.', '-')
            tipo_comida_lower = tipo_comida.lower()
            
            receta_data = {
                'nombre': nombre_receta,
                'contenido': contenido,
                'fecha_generada': timestamp_full,
                'tipo_comida': tipo_comida
            }
            
            # Save under meal type (use timestamp_clean for Firebase path)
            self.db_ref.child(str(chat_id)).child('recetas_generadas').child(
                tipo_comida_lower
            ).child(timestamp_clean).set(receta_data)
            
            logger.info(
                f"Recipe '{nombre_receta}' saved for {chat_id} "
                f"({tipo_comida})"
            )
            return True
        except Exception as e:
            logger.error(
                f"Error saving recipe for {chat_id}: {e}",
                exc_info=True
            )
            return False
    
    def cargar_recetas_generadas_recientes(
        self, 
        chat_id: int, 
        tipo_comida: str, 
        dias: int = 7
    ) -> list:
        """
        Load recently generated recipes for a meal type.
        
        Args:
            chat_id: Telegram user ID
            tipo_comida: Meal type (Breakfast, Lunch, Dinner)
            dias: How many days back to check (default: 7)
            
        Returns:
            List of recipe names generated recently
        """
        try:
            from datetime import datetime, timedelta
            
            tipo_comida_lower = tipo_comida.lower()
            hace_n_dias = datetime.now() - timedelta(days=dias)
            
            resultado = self.db_ref.child(str(chat_id)).child(
                'recetas_generadas'
            ).child(tipo_comida_lower).get()
            
            # Manejo correcto del resultado (resultado puede ser None)
            if resultado is None:
                recetas_dict = {}
            elif isinstance(resultado, dict):
                recetas_dict = resultado if resultado else {}
            else:
                recetas_dict = resultado.val() if resultado.val() else {}
            
            if not recetas_dict:
                logger.debug(
                    f"No hay recetas para {chat_id} en últimos {dias} días"
                )
                return []
            
            # Filtrar por fecha reciente
            recetas_recientes = []
            for timestamp_str, receta_data in recetas_dict.items():
                if isinstance(receta_data, dict):
                    try:
                        fecha_str = receta_data.get('fecha_generada', timestamp_str)
                        fecha_receta = datetime.fromisoformat(fecha_str)
                        
                        if fecha_receta > hace_n_dias:
                            nombre = receta_data.get('nombre', '')
                            if nombre:
                                recetas_recientes.append(nombre.lower())
                    except:
                        # Si hay error parsando la fecha, ignorar
                        pass
            
            logger.debug(
                f"Recent recipes for {chat_id} ({tipo_comida}): "
                f"{len(recetas_recientes)} found"
            )
            return recetas_recientes
        except Exception as e:
            logger.error(
                f"Error loading recent recipes for {chat_id}: {e}",
                exc_info=True
            )
            return []
    
    def existe_receta_duplicada(
        self, 
        chat_id: int, 
        tipo_comida: str, 
        nombre_receta: str
    ) -> bool:
        """
        Check if a recipe was recently generated (to avoid repetition).
        
        Args:
            chat_id: Telegram user ID
            tipo_comida: Meal type (Breakfast, Lunch, Dinner)
            nombre_receta: Dish name to check
            
        Returns:
            True if duplicate found; False otherwise
        """
        try:
            recetas_recientes = self.cargar_recetas_generadas_recientes(
                chat_id, 
                tipo_comida, 
                dias=7
            )
            
            nombre_lower = nombre_receta.lower().strip()
            
            # Check exact or partial match (first 3 words)
            palabras_nombre = nombre_lower.split()[:3]
            nombre_busqueda = ' '.join(palabras_nombre)
            
            for receta in recetas_recientes:
                palabras_receta = receta.split()[:3]
                receta_busqueda = ' '.join(palabras_receta)
                
                if nombre_busqueda in receta_busqueda or receta_busqueda in nombre_busqueda:
                    logger.info(
                        f"Duplicate detected: '{nombre_receta}' similar to "
                        f"'{receta}' for {chat_id}"
                    )
                    return True
            
            return False
        except Exception as e:
            logger.error(
                f"Error checking for duplicate recipe for {chat_id}: {e}",
                exc_info=True
            )
            return False
    
    # ========== VALIDACIÓN Y UTILIDADES ==========
    
    def verificar_conexion(self) -> bool:
        """
        Test that the Firebase connection is working.
        
        Returns:
            True if connection is valid; False otherwise
        """
        try:
            self.db_ref.get()
            logger.info("Firebase connection verified")
            return True
        except Exception as e:
            logger.error(f"Error verifying Firebase connection: {e}")
            return False
