"""
Sistema de gestión de estado para el bot NutrIA.

Este módulo realiza seguimiento de dónde se encuentra cada usuario en su flujo
(registrándose, navegando el menú, registrando comidas, etc.) sin
necesidad de variables globales. El estado de cada usuario está seguramente aislado.
"""

import logging
from typing import Dict, Optional, Any

from user_model import User

# Configurar logger para debugging
logger = logging.getLogger(__name__)


class StateManager:
    """
    Realiza seguimiento de dónde se encuentra cada usuario en su flujo.
    
    En lugar de usar variables globales (que son desordenadas y difíciles
    de probar), encapsulamos todo en esta clase. Cada usuario
    obtiene su propio estado y almacenamiento temporal durante el registro.
    
    El usuario pasa a través de estos estados:
    - inicio: Nuevo usuario, aún no registrado
    - registro_* estados: Recopilando información personal (nombre, cédula,
      género, peso, altura, edad, nivel de actividad, presupuesto, dieta)
    - menu: Usuario viendo el menú principal
    - registro_comida: Registrando una comida
    - espera_tipo_comida: Esperando el tipo de comida
    - confirmar_registro: Confirmando entrada de comida
    - editar_* estados: Modificando información de perfil existente
    - registro_*_dashboard: Flujo de registro en dashboard
    """
    
    # Estados válidos del sistema
    ESTADOS_VALIDOS = {
        "inicio",
        "registro_nombre",
        "registro_pais",
        "registro_genero",
        "registro_peso",
        "registro_altura",
        "registro_edad",
        "registro_actividad",
        "registro_economia",
        "registro_dieta",
        "menu",
        "registro_comida",
        "espera_tipo_comida",
        "confirmar_registro",
        "registro_usuario_dashboard",
        "registro_password_dashboard",
        "editar_economia",
        "editar_actividad",
        "editar_dieta",
        "editar_password"
    }
    
    def __init__(self):
        """
        Configura el sistema de gestión de estado para esta sesión del bot.
        
        Crea tres diccionarios internos para realizar seguimiento:
        1. El estado actual de cada usuario en el flujo
        2. Datos temporales recopilados durante el registro
        3. Elementos pendientes esperando confirmación del usuario
        """
        # Mapea cada usuario (por chat_id) a su estado actual
        self._estados: Dict[int, str] = {}
        
        # Almacenamiento temporal para datos del usuario durante el registro
        self._datos_usuario: Dict[int, Dict[str, Any]] = {}
        
        # Elementos de comida pendientes esperando confirmación del usuario
        self._items_pendientes: Dict[int, Dict[str, Any]] = {}
        
        logger.info("Gestor de estado inicializado correctamente")
    
    # ========== GESTIÓN DE ESTADOS ==========
    
    def obtener_estado(self, chat_id: int) -> str:
        """
        Verifica en qué estado se encuentra actualmente un usuario.
        
        Los nuevos usuarios que aún no están en el sistema por defecto tienen el estado 'inicio'
        (estado de inicio), que activa el flujo de registro.
        
        Args:
            chat_id: ID único del usuario en Telegram
            
        Returns:
            Cadena de estado actual (por ej. 'menu', 'registro_nombre')
        """
        return self._estados.get(chat_id, "inicio")
    
    def establecer_estado(
        self, chat_id: int, nuevo_estado: str
    ) -> bool:
        """
        Mueve un usuario a un nuevo estado en el flujo.
        
        Validamos que el estado sea legítimo antes de permitirlo.
        Esto previene que typos o estados inválidos rompan el flujo.
        
        Args:
            chat_id: ID único del usuario en Telegram
            nuevo_estado: El nuevo estado hacia el que moverlo
            
        Returns:
            True si el cambio de estado funcionó; False si el estado es inválido
        """
        if nuevo_estado not in self.ESTADOS_VALIDOS:
            logger.warning(
                f"Intento de estado inválido para {chat_id}: "
                f"{nuevo_estado}"
            )
            return False
        
        self._estados[chat_id] = nuevo_estado
        logger.info(
            f"Usuario {chat_id} cambió a estado: {nuevo_estado}"
        )
        return True
    
    def esta_en_registro(self, chat_id: int) -> bool:
        """
        Verifica si un usuario actualmente está en el flujo de registro.
        
        Útil para que los manejadores sepan si mostrar
        mensajes de registro u opciones de menú regular.
        
        Args:
            chat_id: ID único del usuario en Telegram
            
        Returns:
            True si el usuario está registrándose activamente; False en caso contrario
        """
        estado = self.obtener_estado(chat_id)
        return estado.startswith("registro_")
    
    # ========== DATOS TEMPORALES ==========
    
    def obtener_datos_usuario(self, chat_id: int) -> Dict[str, Any]:
        """
        Retrieve temporary data collected from a user.
        
        This is useful during registration—we collect name, age,
        weight, etc., piece by piece, storing them here until
        the registration is complete.
        
        Args:
            chat_id: Unique ID of the Telegram user
            
        Returns:
            Dictionary with all temporary user data collected so far
        """
        if chat_id not in self._datos_usuario:
            self._datos_usuario[chat_id] = {}
        
        return self._datos_usuario[chat_id]
    
    def guardar_dato_usuario(
        self, chat_id: int, clave: str, valor: Any
    ) -> None:
        """
        Almacena una pieza de datos de usuario temporal.
        
        Llamado durante el registro: cuando el usuario proporciona su nombre,
        lo guardamos; cuando dan su edad, también lo guardamos.
        Todo se recopila aquí hasta que se completa el registro.
        
        Args:
            chat_id: ID único del usuario en Telegram
            clave: Nombre del campo (por ej. 'nombre', 'peso', 'edad')
            valor: El valor a almacenar para ese campo
        """
        if chat_id not in self._datos_usuario:
            self._datos_usuario[chat_id] = {}
        
        self._datos_usuario[chat_id][clave] = valor
        logger.debug(
            f"Datos guardados para {chat_id}: {clave}={valor}"
        )
    
    def limpiar_datos_usuario(self, chat_id: int) -> None:
        """
        Limpia todos los datos temporales recopilados de un usuario.
        
        Después de que se completa el registro o si se cancela,
        limpiamos el almacenamiento temporal para liberar memoria y prevenir
        que datos obsoletos se arrastren.
        
        Args:
            chat_id: ID único del usuario en Telegram
        """
        if chat_id in self._datos_usuario:
            del self._datos_usuario[chat_id]
        
        logger.info(f"Datos limpios para usuario {chat_id}")
    
    # ========== ITEMS PENDIENTES ==========
    
    def guardar_item_pendiente(
        self, chat_id: int, item_data: Dict[str, Any]
    ) -> None:
        """
        Store a food item waiting for user confirmation.
        
        When the user logs food, we parse it (using AI), show them
        what we found, and wait for them to confirm. This method
        holds that food item until they click 'confirm'.
        
        Args:
            chat_id: Unique ID of the Telegram user
            item_data: Dictionary with the parsed food details
        """
        self._items_pendientes[chat_id] = item_data
        logger.debug(
            f"Item pendiente guardado para {chat_id}"
        )
    
    def obtener_item_pendiente(
        self, chat_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve the pending food item awaiting confirmation.
        
        Returns None if there's nothing pending, or the food data
        if the user is in the confirmation flow.
        
        Args:
            chat_id: Unique ID of the Telegram user
            
        Returns:
            Food item data, or None if nothing is pending
        """
        return self._items_pendientes.get(chat_id)
    
    def limpiar_item_pendiente(self, chat_id: int) -> None:
        """
        Remove a pending food item after the user confirms it.
        
        Once a user clicks 'confirm', we save the food to their
        daily intake and clean up the pending storage.
        
        Args:
            chat_id: Unique ID of the Telegram user
        """
        if chat_id in self._items_pendientes:
            del self._items_pendientes[chat_id]
        
        logger.debug(
            f"Item pendiente limpiado para {chat_id}"
        )
    
    # ========== CICLO COMPLETO ==========
    
    def inicializar_usuario(self, chat_id: int) -> None:
        """
        Set up a brand new user in the system.
        
        When they first contact the bot (/start), we create their
        empty data structures and kick off the registration flow.
        
        Args:
            chat_id: Unique ID of the Telegram user
        """
        self._estados[chat_id] = "registro_nombre"
        self._datos_usuario[chat_id] = {}
        
        logger.info(f"User {chat_id} initialized for registration")
    
    def completar_registro(
        self, chat_id: int
    ) -> Optional[User]:
        """
        Finalize a user's registration.
        
        Take all the temporary data we collected (name, age, weight,
        etc.) and bundle it into a proper User object. Then move
        them to the 'menu' state so they can start using the app.
        
        Args:
            chat_id: Unique ID of the Telegram user
            
        Returns:
            The new User object, or None if something went wrong
        """
        try:
            datos = self._datos_usuario.get(chat_id, {})
            
            if not datos:
                logger.warning(
                    f"No temporary data found for {chat_id} "
                    f"during registration completion"
                )
                return None
            
            # Crear objeto User
            user = User(chat_id)
            user.nombre = datos.get('nombre')
            user.cedula = datos.get('cedula')
            user.genero = datos.get('genero')
            user.peso = datos.get('peso')
            user.altura_cm = datos.get('altura_cm')
            user.edad = datos.get('edad')
            user.actividad_fisica = datos.get(
                'actividad_fisica'
            )
            user.economia = datos.get('economia')
            user.dieta = datos.get('dieta')
            
            # Cambiar estado
            self.establecer_estado(chat_id, "menu")
            
            logger.info(
                f"Registration complete for user {chat_id}"
            )
            return user
            
        except Exception as e:
            logger.error(
                f"Error completing registration for {chat_id}: {e}"
            )
            return None
    
    def eliminar_usuario(self, chat_id: int) -> None:
        """
        Remove all traces of a user from memory.
        
        Called when a user requests profile deletion or when they
        explicitly want to stop using the bot. Clears their state,
        temporary data, and any pending items.
        
        Args:
            chat_id: Unique ID of the Telegram user
        """
        if chat_id in self._estados:
            del self._estados[chat_id]
        
        if chat_id in self._datos_usuario:
            del self._datos_usuario[chat_id]
        
        if chat_id in self._items_pendientes:
            del self._items_pendientes[chat_id]
        
        logger.info(f"User {chat_id} deleted from system")
    
    # ========== INFORMACIÓN Y DEBUG ==========
    
    def obtener_resumen(self, chat_id: int) -> Dict[str, Any]:
        """
        Get a quick snapshot of a user's current state.
        
        Useful for debugging, logging, or when the bot needs to
        understand the full picture of where a user is at.
        
        Args:
            chat_id: Unique ID of the Telegram user
            
        Returns:
            Dictionary with user info: current state, whether they
            have temporary data stored, and pending items
        """
        return {
            'chat_id': chat_id,
            'estado': self.obtener_estado(chat_id),
            'tiene_datos': chat_id in self._datos_usuario,
            'tiene_item_pendiente': (
                chat_id in self._items_pendientes
            )
        }
    
    def limpiar_usuario_completamente(self, chat_id: int) -> None:
        """
        Purge all user data from memory (for sync after Firebase deletion).
        
        When a user is deleted from Firebase (via delete_user.py),
        we need to also clean up their in-memory cache here to keep
        things in sync. This method wipes their state, temporary data,
        and pending items completely.
        
        Args:
            chat_id: Unique ID of the Telegram user to purge
        """
        try:
            # Remove user state
            if chat_id in self._estados:
                del self._estados[chat_id]
                logger.debug(f"State removed for user {chat_id}")
            
            # Remove temporary data
            if chat_id in self._datos_usuario:
                del self._datos_usuario[chat_id]
                logger.debug(f"Temporary data removed for {chat_id}")
            
            # Remove pending items
            if chat_id in self._items_pendientes:
                del self._items_pendientes[chat_id]
                logger.debug(f"Pending items removed for {chat_id}")
            
            logger.info(f"User {chat_id} completely removed from memory")
            
        except Exception as e:
            logger.error(f"Error completely removing user {chat_id}: {e}")

