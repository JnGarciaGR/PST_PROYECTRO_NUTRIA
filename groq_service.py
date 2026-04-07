"""
Servicio de integración con Groq IA para NutrIA.

Maneja todas las interacciones con la API de Groq:
- Análisis de comidas y extracción de macronutrientes
- Recomendaciones de recetas con anti-repetición
- Consejos nutricionales inteligentes basados en el progreso del usuario
- Preguntas generales sobre nutrición
"""

from groq import Groq
import logging
import re
from typing import Optional, Dict, List

from user_model import User

# Configurar logger para debugging
logger = logging.getLogger(__name__)


class GroqService:
    """
    Servicio centralizado de IA para análisis nutricional y recomendaciones.
    
    Este servicio envuelve la API de Groq (potenciada por Llama 3.3-70b) para proporcionar:
    - Validación de alimentos y análisis de comidas
    - Extracción de macronutrientes de descripciones de alimentos
    - Recomendaciones inteligentes de recetas adaptadas al progreso del usuario
    - Sistema anti-repetición para evitar sugerir las mismas comidas
    - Preguntas y respuestas generales sobre nutrición
    """
    
    def __init__(self, api_key: str, firebase_service=None):
        """
        Inicializa el servicio de Groq IA.
        
        Args:
            api_key: Clave de API de Groq
            firebase_service: Instancia de FirebaseService para caché de recetas
                             (opcional, pero necesario para anti-repetición)
            
        Raises:
            ValueError: Si la clave de API está vacía
        """
        if not api_key:
            raise ValueError("Groq API key cannot be empty")
        
        self.client = Groq(api_key=api_key)
        self.firebase_service = firebase_service
        logger.info("Servicio de Groq inicializado correctamente")
    
    # ========== ANÁLISIS DE COMIDAS ==========
    
    def validar_es_comida(self, texto: str) -> bool:
        """
        Verifica si el texto ingresado describe una comida o alimento real.
        
        Usa Groq para verificar si es un elemento real y comestible.
        
        Args:
            texto: Texto a validar
            
        Returns:
            True si es una comida real; False en caso contrario
        """
        try:
            prompt = (
                f'¿El siguiente texto describe una comida, alimento, '
                f'bebida, o plato preparado que existe en la realidad? '
                f'Texto: "{texto}"\n\n'
                f'Responde SOLO con "SÍ" si es una comida real '
                f'o "NO" si no es una comida.'
            )
            
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un verificador de alimentos. "
                            "Solo responde SÍ o NO."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            respuesta = response.choices[0].message.content.strip().upper()
            es_comida = "SÍ" in respuesta or "SI" in respuesta
            
            logger.info(
                f"Food validation for '{texto}': {es_comida} "
                f"(response: {respuesta})"
            )
            return es_comida
            
        except Exception as e:
            logger.error(f"Error validating food {texto}: {e}")
            return False
    
    def validar_es_pais(self, texto: str) -> bool:
        """
        Verifica si el texto ingresado nombra un país real.
        
        Usa Groq para verificar que el país existe.
        
        Args:
            texto: Texto con nombre del país
            
        Returns:
            True si es un país válido; False en caso contrario
        """
        try:
            prompt = (
                f'¿El siguiente texto corresponde a un país real que existe en el mundo? '
                f'Texto: "{texto}"\n\n'
                f'Responde SOLO con "SÍ" si es un país real '
                f'o "NO" si no es un país válido.'
            )
            
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un verificador de países. "
                            "Solo responde SÍ o NO. "
                            "Acepta nombres en español (Colombia, España, Perú, etc.) "
                            "e inglés (Colombia, Spain, Peru, etc.)."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            respuesta = response.choices[0].message.content.strip().upper()
            es_pais = "SÍ" in respuesta or "SI" in respuesta
            
            logger.info(
                f"Validación de país para '{texto}': {es_pais} "
                f"(respuesta: {respuesta})"
            )
            return es_pais
            
        except Exception as e:
            logger.error(f"Error validando país {texto}: {e}")
            return False
    
    # ========== ANÁLISIS DE COMIDAS ==========
    
    def analizar_comida(self, nombre_comida: str) -> Optional[str]:
        """
        Analyze a meal and extract its macronutrients.
        
        Process:
        1. Validate that it's actually a real food
        2. Query Groq using real USDA nutrition databases
        3. Return realistic, verifiable values
        4. Return None if not food or on error
        
        Args:
            nombre_comida: Name of the meal to analyze
            
        Returns:
            String with nutritional analysis, or None if error/not food
        """
        try:
            # PASO 1: Validar que es un alimento real
            if not self.validar_es_comida(nombre_comida):
                logger.warning(
                    f"'{nombre_comida}' no es un alimento válido"
                )
                return None
            
            # STEP 2: Analyze meal with realistic values
            prompt = (
                f'You are a certified nutritionist. '
                f'Analyze the following food/meal based on REAL data from '
                f'nutrition databases like USDA FoodData Central.\n\n'
                f'IMPORTANT: Values MUST be realistic and based on '
                f'a 100g serving of "{nombre_comida}".\n\n'
                f'Respond in EXACT format (no extra explanations):\n'
                f'• Xg of protein\n'
                f'• Yg of fat\n'
                f'• Zg of carbohydrates\n'
                f'• W calories\n\n'
                f'VALIDATION: The sum (protein×4 + fat×9 + carbs×4) '
                f'must be VERY CLOSE to total calories.'
            )
            
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a certified nutritionist specialized "
                            "in meal analysis. ALWAYS consult USDA FoodData "
                            "Central or real nutrition databases. NEVER "
                            "hallucinate values. Follow exact format. "
                            "Values must be realistic and verifiable."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=200
            )
            
            resultado = response.choices[0].message.content.strip()
            logger.info(f"Analysis completed for: {nombre_comida}")
            return resultado
            
        except Exception as e:
            logger.error(f"Error analyzing meal {nombre_comida}: {e}")
            return None
    
    # ========== RECOMENDACIONES DE RECETAS ==========
    
    def _extraer_nombre_receta(self, contenido: str) -> Optional[str]:
        """
        Extract recipe name from generated content.
        
        Busca patrones como:
        - "Para el desayuno te recomiendo que prepares [Nombre]"
        - "Te recomiendo [Nombre]"
        - "[Nombre]" entre corchetes (en cualquier contexto)
        
        Args:
            contenido: Texto completo de la recomendación
            
        Returns:
            Nombre de la receta o None si no se puede extraer
        """
        try:
            # Patrón 1: "te recomiendo que te prepares [Nombre]"
            patron1 = r'te\s+recomiendo\s+que\s+te\s+prepares\s+\[(.+?)\]'
            match1 = re.search(patron1, contenido, re.IGNORECASE)
            if match1:
                return match1.group(1).strip()
            
            # Patrón 2: "te recomiendo que te prepares [Nombre]," (sin corchetes)
            patron2 = r'te\s+recomiendo\s+que\s+te\s+prepares\s+([^,\n]+)'
            match2 = re.search(patron2, contenido, re.IGNORECASE)
            if match2:
                nombre = match2.group(1).strip()
                # Limpiar caracteres especiales
                nombre = nombre.replace('[', '').replace(']', '').strip()
                if nombre and len(nombre) > 2:
                    return nombre
            
            # Patrón 3: Cualquier corchete simple [Nombre]
            patron3 = r'\[([^\]]+)\]'
            match3 = re.search(patron3, contenido)
            if match3:
                nombre = match3.group(1).strip()
                if nombre and len(nombre) > 2:
                    return nombre
            
            # Patrón 4: Primera línea que contiene "Para"
            lineas = contenido.split('\n')
            for linea in lineas:
                if 'para' in linea.lower() and ('[' in linea or 'recomiendo' in linea.lower()):
                    # Extraer entre corchetes
                    if '[' in linea and ']' in linea:
                        inicio = linea.index('[') + 1
                        fin = linea.index(']')
                        nombre = linea[inicio:fin].strip()
                        if nombre and len(nombre) > 2:
                            return nombre
            
            return None
        except Exception as e:
            logger.debug(f"Error extrayendo nombre de receta: {e}")
            return None
    
    def _extraer_macros_completos(self, resultado: str) -> Dict[str, float]:
        """
        Extrae los 4 macronutrientes de la respuesta de Groq.
        
        Busca patrones como:
        - "Xg de proteína" o "proteína: Xg"
        - "Yg de grasa" o "grasa: Yg"
        - "Zg de carbohidratos" o "carbohidratos: Zg"
        - "W calórias" o "calórias: W kcal"
        
        Args:
            resultado: Cadena completa de la respuesta de Groq
            
        Returns:
            Dict con claves: protein, fat, carbs, calories
            Establecido a 0.0 si no se encuentra
        """
        try:
            macros = {
                'proteina': 0.0,
                'grasa': 0.0,
                'carbohidratos': 0.0,
                'calorias': 0.0
            }
            
            texto_limpio = resultado.lower()
            
            # Regex patterns for each macro
            patrones = {
                'proteina': [
                    r'(\d+(?:[.,]\d+)?)\s*g\s+de\s+proteína',
                    r'proteína[:\s]+(\d+(?:[.,]\d+)?)\s*g',
                    r'proteína\s+(\d+(?:[.,]\d+)?)',
                ],
                'grasa': [
                    r'(\d+(?:[.,]\d+)?)\s*g\s+de\s+grasa',
                    r'grasa[:\s]+(\d+(?:[.,]\d+)?)\s*g',
                    r'grasa\s+(\d+(?:[.,]\d+)?)',
                ],
                'carbohidratos': [
                    r'(\d+(?:[.,]\d+)?)\s*g\s+de\s+carbohidratos',
                    r'carbohidratos[:\s]+(\d+(?:[.,]\d+)?)\s*g',
                    r'carbohidratos\s+(\d+(?:[.,]\d+)?)',
                ],
                'calorias': [
                    r'(\d+(?:[.,]\d+)?)\s*(?:calorías|kcal)',
                    r'calorías[:\s]+(\d+(?:[.,]\d+)?)',
                    r'energía[:\s]+(\d+(?:[.,]\d+)?)',
                ]
            }
            
            # Intentar extraer cada macro con múltiples patrones
            for macro, patterns_lista in patrones.items():
                for patron in patterns_lista:
                    coincidencia = re.search(patron, texto_limpio)
                    if coincidencia:
                        valor_str = coincidencia.group(1)
                        valor_str = valor_str.replace(',', '.')
                        try:
                            valor_float = float(valor_str)
                            macros[macro] = round(valor_float, 1)
                            logger.debug(f"Macro '{macro}' extracted: {valor_float}g")
                            break  # Pasar al siguiente macro
                        except ValueError:
                            logger.debug(f"No se pudo convertir '{valor_str}' a float")
                            continue
            
            # Minimal validation: if all are 0, probably not found
            if all(v == 0.0 for v in macros.values()):
                logger.debug("No valid macros extracted")
            
            return macros
            
        except Exception as e:
            logger.debug(f"Error extracting full macros: {e}")
            return {
                'proteina': 0.0,
                'grasa': 0.0,
                'carbohidratos': 0.0,
                'calorias': 0.0
            }
    
    def _extraer_pasos_preparacion(self, resultado: str) -> List[str]:
        """
        Extract preparation steps from Groq response.
        
        Looks for patterns like:
        - Numbered: "1. Step..."
        - Bullets: "• Step..."
        - Action verbs: "Heat...", "Mix...", etc.
        
        Args:
            resultado: Full string from Groq response
            
        Returns:
            List of steps (max 7), cleaned and formatted
        """
        try:
            pasos = []
            lineas = resultado.split('\n')
            
            # Patrones para identificar pasos
            patron_numerado = re.compile(r'^\s*\d+\.\s+(.+)$')
            patron_bullet = re.compile(r'^\s*[•\-\*]\s+(.+)$')
            
            for linea in lineas:
                linea = linea.strip()
                if not linea:
                    continue
                
                # Probar patrones
                match = patron_numerado.match(linea)
                if match:
                    paso = match.group(1).strip()
                    if len(paso) > 5:  # Filtrar líneas muy cortas
                        pasos.append(paso)
                    continue
                
                match = patron_bullet.match(linea)
                if match:
                    paso = match.group(1).strip()
                    if len(paso) > 5:
                        pasos.append(paso)
                    continue
                
                # Si empieza con palabra común de acción ("Calentar", "Mezclar", etc)
                palabras_accion = ['calentar', 'mezclar', 'agregar', 'cocinar', 
                                   'freír', 'hervir', 'cortar', 'picar', 'hornear',
                                   'batir', 'servir', 'dejar', 'colocar', 'verter']
                if any(linea.lower().startswith(p) for p in palabras_accion):
                    if len(linea) > 10:
                        pasos.append(linea)
            
            # Limitar a 7 pasos máximo
            pasos = pasos[:7]
            
            logger.debug(f"Se extrajeron {len(pasos)} pasos de preparación")
            return pasos
            
        except Exception as e:
            logger.debug(f"Error extrayendo pasos: {e}")
            return []
    
    def _extraer_beneficios(self, resultado: str, dieta_usuario: str = None) -> str:
        """
        Extrae beneficios nutricionales del texto de la respuesta.
        
        Busca frases relacionadas con beneficios y las formatea.
        Se vincula con el objetivo dietético del usuario para el contexto.
        
        Args:
            resultado: Cadena completa de la respuesta de Groq
            dieta_usuario: Tipo de dieta del usuario (por ej. "pérdida de peso")
            
        Returns:
            Cadena con beneficios formateados (puntos de bala)
        """
        try:
            texto_limpio = resultado.lower()
            
            # Palabras clave que indican beneficios
            claves_beneficios = [
                'rico en', 'fuente de', 'alto en', 'excelente para',
                'ayuda', 'promueve', 'contiene', 'proporciona',
                'beneficio', 'propiedad', 'ventaja', 'ideal para'
            ]
            
            beneficios = []
            lineas = resultado.split('\n')
            
            for linea in lineas:
                linea_limpia = linea.strip()
                if not linea_limpia or len(linea_limpia) < 10:
                    continue
                
                # Verificar si la línea contiene palabras clave
                tiene_clave = any(clave in linea.lower() for clave in claves_beneficios)
                if tiene_clave:
                    # Limpiar bullets si existen
                    linea_limpia = re.sub(r'^[•\-\*]\s+', '', linea_limpia)
                    # Asegurar que empieza con mayúscula
                    if linea_limpia:
                        linea_limpia = linea_limpia[0].upper() + linea_limpia[1:]
                        beneficios.append(linea_limpia)
            
            # Beneficios genéricos basados en dieta si no se encuentran específicos
            if not beneficios and dieta_usuario:
                beneficios_genericos = {
                    'pérdida de peso': ['Bajo en calórias', 'Buena fuente de proteína', 'Promueve saciedad'],
                    'ganancia muscular': ['Alto en calórias', 'Proteína de calidad', 'Reparación muscular'],
                    'recomposición': ['Balance calórico moderado', 'Proteína completa', 'Nutrientes esenciales'],
                    'mantenimiento': ['Nutritivo y equilibrado', 'Macros balanceados', 'Sostenible a largo plazo'],
                }
                dieta_lower = dieta_usuario.lower()
                for clave, benef in beneficios_genericos.items():
                    if clave in dieta_lower:
                        beneficios.extend(benef[:2])
                        break
            
            # Limitar a máximo 4 beneficios
            beneficios = beneficios[:4]
            
            if beneficios:
                resultado_beneficios = "Beneficios:\n"
                for i, beneficio in enumerate(beneficios, 1):
                    resultado_beneficios += f"{i}. {beneficio}\n"
                logger.debug(f"Se extrajeron {len(beneficios)} beneficios")
                return resultado_beneficios.strip()
            
            return ""
            
        except Exception as e:
            logger.debug(f"Error extrayendo beneficios: {e}")
            return ""
    
    def _formatear_receta_mejorada(self, resultado: str, dieta_usuario: str = None) -> str:
        """
        Format recipe by extracting and presenting components clearly.
        
        Process:
        1. Extract recipe name
        2. Extract complete macronutrients (4 values)
        3. Extract preparation steps (up to 7)
        4. Extract nutritional benefits
        5. Format into clear presentation
        
        Args:
            resultado: Full string from Groq response
            dieta_usuario: User's diet type (for context)
            
        Returns:
            String with recipe formatted for clarity
        """
        try:
            # Extract components
            nombre = self._extraer_nombre_receta(resultado)
            macros = self._extraer_macros_completos(resultado)
            pasos = self._extraer_pasos_preparacion(resultado)
            beneficios = self._extraer_beneficios(resultado, dieta_usuario)
            
            # If components were extracted, format nicely
            if nombre or any(v > 0 for v in macros.values()) or pasos or beneficios:
                receta_formateada = resultado + "\n\n" + "="*50 + "\n"
                
                # Add extracted macros if any
                if any(v > 0 for v in macros.values()):
                    receta_formateada += "MACRONUTRIENTS EXTRACTED:\n"
                    if macros['proteina'] > 0:
                        receta_formateada += f"  Protein: {macros['proteina']:.1f}g\n"
                    if macros['grasa'] > 0:
                        receta_formateada += f"  Fat: {macros['grasa']:.1f}g\n"
                    if macros['carbohidratos'] > 0:
                        receta_formateada += f"  Carbs: {macros['carbohidratos']:.1f}g\n"
                    if macros['calorias'] > 0:
                        receta_formateada += f"  Calories: {macros['calorias']:.0f} kcal\n"
                
                # Add steps if any
                if pasos:
                    receta_formateada += "\nPREPARATION STEPS:\n"
                    for i, paso in enumerate(pasos, 1):
                        receta_formateada += f"  {i}. {paso}\n"
                
                # Add benefits if any
                if beneficios:
                    receta_formateada += f"\n{beneficios}\n"
                
                logger.debug(
                    f"Improved recipe formatted: "
                    f"Nombre={nombre}, Macros extraídos={any(v > 0 for v in macros.values())}, "
                    f"Pasos={len(pasos)}, Beneficios={bool(beneficios)}"
                )
                return receta_formateada
            
            # Si no se extrajeron componentes, retornar original
            return resultado
            
        except Exception as e:
            logger.debug(f"Error formatting recipe: {e}")
            return resultado
    
    # ========== ANÁLISIS DE DÉFICITS DE MACROS (NUEVO 2026-04-06) ==========
    
    def calcular_deficit_macros(self, progreso_usuario: dict) -> Dict[str, float]:
        """
        Calculate missing macros for the user TODAY.
        
        Compares current consumption vs targets and returns gaps.
        
        Args:
            progreso_usuario: Dict with structure:
                {
                    'macros_objetivo': {'calories': X, 'protein': Y, 'fat': Z, 'carbs': W},
                    'promedio_consumido': {'calories': X, 'protein': Y, 'fat': Z, 'carbs': W},
                    'comidas_hoy': {...}
                }
        
        Returns:
            Dict with missing macros (negative if over):
            {
                'calorias_faltantes': float,
                'proteina_faltante': float,
                'grasa_faltante': float,
                'carbohidratos_faltantes': float,
                'estado': str  # "equilibrio|deficit|exceso"
            }
        """
        try:
            deficit = {
                'calorias_faltantes': 0.0,
                'proteina_faltante': 0.0,
                'grasa_faltante': 0.0,
                'carbohidratos_faltantes': 0.0,
                'estado': 'equilibrio'
            }
            
            if not progreso_usuario:
                logger.debug("Empty progreso_usuario, returning default deficit")
                return deficit
            
            # Obtener objetivos y consumido
            macros_objetivo = progreso_usuario.get('macros_objetivo', {})
            consumido_hoy = progreso_usuario.get('promedio_consumido', {})
            
            # Obtener valores
            cal_obj = float(macros_objetivo.get('calorias', 2000))
            prot_obj = float(macros_objetivo.get('proteina', 100))
            grasa_obj = float(macros_objetivo.get('grasa', 70))
            carb_obj = float(macros_objetivo.get('carbohidratos', 250))
            
            cal_cons = float(consumido_hoy.get('calorias', 0))
            prot_cons = float(consumido_hoy.get('proteina', 0))
            grasa_cons = float(consumido_hoy.get('grasa', 0))
            carb_cons = float(consumido_hoy.get('carbohidratos', 0))
            
            # Calculate deficits
            deficit['calorias_faltantes'] = max(0, cal_obj - cal_cons)
            deficit['proteina_faltante'] = max(0, prot_obj - prot_cons)
            deficit['grasa_faltante'] = max(0, grasa_obj - grasa_cons)
            deficit['carbohidratos_faltantes'] = max(0, carb_obj - carb_cons)
            
            # Determine general state
            total_faltante = (
                deficit['calorias_faltantes'] +
                deficit['proteina_faltante'] +
                deficit['grasa_faltante'] +
                deficit['carbohidratos_faltantes']
            )
            
            # Calculate excesses
            cal_exceso = max(0, cal_cons - cal_obj)
            prot_exceso = max(0, prot_cons - prot_obj)
            grasa_exceso = max(0, grasa_cons - grasa_obj)
            carb_exceso = max(0, carb_cons - carb_obj)
            
            total_exceso = (
                cal_exceso +
                prot_exceso +
                grasa_exceso +
                carb_exceso
            )
            
            if total_faltante > 0 and total_faltante >= total_exceso:
                deficit['estado'] = 'deficit'
            elif total_exceso > 0:
                deficit['estado'] = 'exceso'
            else:
                deficit['estado'] = 'equilibrio'
            
            logger.info(
                f"Macro deficit calculated: "
                f"Cal={deficit['calorias_faltantes']:.0f}, "
                f"Prot={deficit['proteina_faltante']:.1f}g, "
                f"Fat={deficit['grasa_faltante']:.1f}g, "
                f"Carbs={deficit['carbohidratos_faltantes']:.1f}g | "
                f"Status: {deficit['estado']}"
            )
            
            return deficit
            
        except Exception as e:
            logger.error(f"Error calculating macro deficit: {e}")
            return {
                'calorias_faltantes': 0.0,
                'proteina_faltante': 0.0,
                'grasa_faltante': 0.0,
                'carbohidratos_faltantes': 0.0,
                'estado': 'equilibrio'
            }
    
    def generar_contexto_deficit_personalizado(
        self,
        deficit_macros: dict,
        macros_objetivo: dict,
        consumido_hoy: dict
    ) -> str:
        """
        Genera un contexto ESPECÍFICO para Groq basado en déficits.
        
        Ejemplo:
        "El usuario ha consumido 1800/2000 calorías (falta 200).
         Proteína: 80/100g (falta 20g) ← PRIORIDAD ALTA
         Grasa: 40/70g (falta 30g) ← PRIORIDAD ALTA  
         Carbohidratos: 150/250g (falta 100g) ← PRIORIDAD MAXIMA
         IMPORTANTE: La próxima comida debe enfocarse en aumentar principalmente
         Carbohidratos y Grasa, pero SIN exceder la ingesta de Proteína."
        
        Args:
            deficit_macros: Output de calcular_deficit_macros()
            macros_objetivo: Dict con objetivos diarios
            consumido_hoy: Dict con consumo hasta ahora
            
        Returns:
            String con instrucciones específicas para Groq
        """
        try:
            contexto = "\n>>> ANALISIS DE MACROS DE HOY <<<\n"
            
            # Datos
            cal_obj = float(macros_objetivo.get('calorias', 2000))
            prot_obj = float(macros_objetivo.get('proteina', 100))
            grasa_obj = float(macros_objetivo.get('grasa', 70))
            carb_obj = float(macros_objetivo.get('carbohidratos', 250))
            
            cal_cons = float(consumido_hoy.get('calorias', 0))
            prot_cons = float(consumido_hoy.get('proteina', 0))
            grasa_cons = float(consumido_hoy.get('grasa', 0))
            carb_cons = float(consumido_hoy.get('carbohidratos', 0))
            
            # Línea de estado
            contexto += f"Estado del día: {(cal_cons/cal_obj)*100:.0f}% de calorías consumidas\n\n"
            
            # Detalle de cada macro
            contexto += "DESGLOSE POR MACRONUTRIENTE:\n"
            
            # Proteína
            pct_prot = (prot_cons / prot_obj * 100) if prot_obj > 0 else 0
            deficit_prot = deficit_macros['proteina_faltante']
            contexto += f"🥚 Proteína: {prot_cons:.0f}g / {prot_obj:.0f}g ({pct_prot:.0f}%) "
            if deficit_prot > 5:
                contexto += f"← FALTA {deficit_prot:.0f}g ⚠️\n"
            else:
                contexto += f"(OK)\n"
            
            # Grasa
            pct_grasa = (grasa_cons / grasa_obj * 100) if grasa_obj > 0 else 0
            deficit_grasa = deficit_macros['grasa_faltante']
            contexto += f"🧈 Grasa: {grasa_cons:.0f}g / {grasa_obj:.0f}g ({pct_grasa:.0f}%) "
            if deficit_grasa > 5:
                contexto += f"← FALTA {deficit_grasa:.0f}g ⚠️\n"
            else:
                contexto += f"(OK)\n"
            
            # Carbohidratos
            pct_carb = (carb_cons / carb_obj * 100) if carb_obj > 0 else 0
            deficit_carb = deficit_macros['carbohidratos_faltantes']
            contexto += f"🌾 Carbohidratos: {carb_cons:.0f}g / {carb_obj:.0f}g ({pct_carb:.0f}%) "
            if deficit_carb > 10:
                contexto += f"← FALTA {deficit_carb:.0f}g ⚠️⚠️\n"
            else:
                contexto += f"(OK)\n"
            
            contexto += "\n"
            
            # Calcular prioridades
            macros_faltantes = []
            if deficit_prot > 5:
                macros_faltantes.append(('Proteína', deficit_prot, 'proteína'))
            if deficit_grasa > 5:
                macros_faltantes.append(('Grasa', deficit_grasa, 'grasa'))
            if deficit_carb > 10:
                macros_faltantes.append(('Carbohidratos', deficit_carb, 'carbohidratos'))
            
            # Ordenar por cantidad faltante (mayor primero)
            macros_faltantes.sort(key=lambda x: x[1], reverse=True)
            
            if macros_faltantes:
                contexto += "RECOMENDACION DE RECETA:\n"
                contexto += "La próxima comida debe enfocarse en AUMENTAR principalmente:\n"
                for i, (nombre, cantidad, _) in enumerate(macros_faltantes, 1):
                    contexto += f"  {i}. {nombre} (+{cantidad:.0f}g)\n"
                
                # Prioridades
                if prot_cons >= prot_obj * 0.95:  # Si proteína está cerca del objetivo
                    contexto += "\n⚠️ IMPORTANTE: La Proteína ya está casi al objetivo, "
                    contexto += "NO la aumentes significativamente.\n"
                if grasa_cons >= grasa_obj * 0.95:
                    contexto += "⚠️ IMPORTANTE: La Grasa ya está casi al objetivo, "
                    contexto += "NO la aumentes significativamente.\n"
                if carb_cons >= carb_obj * 0.95:
                    contexto += "⚠️ IMPORTANTE: Los Carbohidratos ya están casi al objetivo, "
                    contexto += "NO los aumentes significativamente.\n"
            else:
                contexto += "✅ Todos los macros están equilibrados o cercanos al objetivo.\n"
                contexto += "La próxima comida puede ser una opción equilibrada y variada.\n"
            
            logger.debug(f"Deficit context generated:\n{contexto}")
            
            return contexto
            
        except Exception as e:
            logger.error(f"Error generating deficit context: {e}")
            return ""
    
    def obtener_recomendacion_receta(
        self, 
        user: User, 
        tipo_comida: str,
        progreso_usuario: dict = None,
        variacion: str = "basica"
    ) -> Optional[str]:
        """
        Generate personalized recipe recommendation with anti-repetition and progress.
        
        Anti-repetition system:
        - Generates recipe
        - Checks if duplicate (last 7 days)
        - Retries if duplicate (max 3 attempts)
        - Saves if unique
        - Returns content
        
        Personalization by progress:
        - Low protein: recommends more protein
        - Low calories: more caloric options
        - Excess: lighter options
        
        Recipe variations:
        - "basica": standard recipe
        - "rapida": prep time <15 minutes
        - "tradicional": typical dish from country
        - "economica": budget-friendly
        
        Args:
            user: User object with profile data
            tipo_comida: Meal type (Breakfast, Lunch, Dinner)
            progreso_usuario: Progress dict (optional)
            variacion: Recipe variation type (default: "basica")
            
        Returns:
            String with recommendation or None on error
        """
        try:
            if not user.esta_completo():
                logger.warning(
                    f"User {user.chat_id} with incomplete profile"
                )
                return None
            
            economia = (user.economia or "No especificada").lower()
            dieta = (user.dieta or "No especificada").lower()
            pais = (user.pais or "No especificado").lower()
            nombre = user.nombre or "Usuario"
            
            # Contexto de progreso si está disponible
            contexto_progreso = ""
            if progreso_usuario:
                try:
                    # NUEVO 2026-04-06: Usar sistema inteligente de déficits
                    deficit_macros = self.calcular_deficit_macros(progreso_usuario)
                    macros_objetivo = progreso_usuario.get('macros_objetivo', {})
                    consumido_hoy = progreso_usuario.get('promedio_consumido', {})
                    
                    # Generar contexto detallado basado en déficits
                    contexto_deficit = self.generar_contexto_deficit_personalizado(
                        deficit_macros,
                        macros_objetivo,
                        consumido_hoy
                    )
                    
                    if contexto_deficit:
                        contexto_progreso = "\n" + contexto_deficit
                        logger.info(
                            f"Contexto de recomendación inteligente generado. "
                            f"Estado: {deficit_macros['estado']}"
                        )
                    else:
                        # Fallback a lógica antigua si falló el nuevo sistema
                        logger.debug("Fallback a contexto_progreso antiguo")
                        calorias_objetivo = progreso_usuario.get('macros_objetivo', {}).get('calorias', 0)
                        calorias_promedio = progreso_usuario.get('promedio_consumido', {}).get('calorias', 0)
                        proteina_promedio = progreso_usuario.get('promedio_consumido', {}).get('proteina', 0)
                        proteina_objetivo = progreso_usuario.get('macros_objetivo', {}).get('proteina', 0)
                        dias_registrados = progreso_usuario.get('dias_registrados', 0)
                        
                        # Construir recomendación personalizada (antigua)
                        if calorias_promedio < calorias_objetivo * 0.85:
                            contexto_progreso += f"\n- FALTA CALORÍAS: Promedio {calorias_promedio:.0f} vs objetivo {calorias_objetivo:.0f}. Sugiere opciones más calóricas."
                        elif calorias_promedio > calorias_objetivo * 1.15:
                            contexto_progreso += f"\n- EXCESO DE CALORÍAS: Promedio {calorias_promedio:.0f} vs objetivo {calorias_objetivo:.0f}. Sugiere opciones más ligeras."
                        
                        if proteina_promedio < proteina_objetivo * 0.85:
                            contexto_progreso += f"\n- PROTEÍNA BAJA: Promedio {proteina_promedio:.1f}g vs objetivo {proteina_objetivo:.1f}g. Aumenta contenido de proteína."
                        
                        if dias_registrados > 0:
                            contexto_progreso += f"\n- Análisis basado en últimos {dias_registrados} días de consumo."
                except Exception as e:
                    logger.warning(f"Error construyendo contexto de progreso inteligente: {e}")
                    contexto_progreso = ""  # Continuar sin contexto específico
            
            # Recipe variation descriptions
            variaciones_desc = {
                "basica": "Standard recipe, balanced",
                "rapida": "Quick prep, less than 15 minutes",
                "tradicional": "Typical dish from the country",
                "economica": "Budget-friendly, basic ingredients"
            }
            desc_variacion = variaciones_desc.get(variacion, "Receta estándar")
            
            # Construir prompt base (reutilizable en reintentos)
            def construir_prompt(intento: int = 1) -> str:
                sufijo = ""
                if intento > 1:
                    sufijo = (
                        f"\n\nIMPORTANTE: Esta es invocación #{intento}. "
                        f"Sugiere una receta DIFERENTE a las anteriores. "
                        f"Sé creativo e innovador."
                    )
                
                # Mejorar estructura del prompt con contexto_progreso inteligente
                instrucciones_basicas = (
                    f'Eres un nutricionista experto en dar recomendaciones de recetas.\n'
                    f'CONTEXTO DEL USUARIO:\n'
                    f'• Nombre: {nombre}\n'
                    f'• Resido en: {pais}\n'
                    f'• Estabilidad económica: {economia}\n'
                    f'• Tipo de dieta: {dieta}\n'
                    f'• Tipo de receta: {desc_variacion}'
                )
                
                # Si hay información detallada de déficits, el prompt es más específico
                if ">>>" in contexto_progreso:  # Indicador de nuevo contexto
                    instrucciones_basicas += contexto_progreso
                    instrucciones_basicas += (
                        f'\n\nCREA UNA RECETA QUE CUMPLA CON LOS REQUISITOS ANTERIORES.\n'
                        f'La receta debe ser para "{tipo_comida}" y optimizada según los macros faltantes indicados.\n'
                        f'Respeta las restricciones sobre NO aumentar los macros que ya están cerca del objetivo.'
                    )
                else:
                    # Fallback
                    instrucciones_basicas += (
                        contexto_progreso + 
                        f'\n\nPor favor, sugiere una receta saludable y económica '
                        f'para el {tipo_comida} basada en ingredientes típicos y disponibles en {pais}.'
                    )
                
                # Especificación del formato (igual para ambos casos)
                formato_especifico = (
                    f'\n\nTu respuesta debe seguir este formato EXACTO.\n'
                    f'IMPORTANTE: El nombre del plato DEBE estar entre corchetes en la PRIMERA LÍNEA.\n\n'
                    f'FORMATO REQUERIDO:\n'
                    f'Para un {tipo_comida} te recomiendo que te prepares [NOMBRE DEL PLATO], '
                    f'ya que es rico en [cualidades nutricionales relevantes].\n'
                    f'[Descripción breve: ingredientes principales y preparación en 3-5 líneas].\n'
                    f'Para [NOMBRE DEL PLATO] se calcula que:\n'
                    f'• Xg de proteína\n'
                    f'• Yg de grasa\n'
                    f'• Zg de carbohidratos\n'
                    f'• W calorías'
                )
                
                return instrucciones_basicas + formato_especifico + sufijo
            
            # Sistema de reintentos para evitar duplicados
            max_intentos = 3
            for intento in range(1, max_intentos + 1):
                try:
                    prompt = construir_prompt(intento)
                    
                    response = self.client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "Eres un nutricionista experto en la "
                                    "creación de recetas saludables y económicas, "
                                    "adaptadas a diferentes tipos de dieta, "
                                    "estabilidad económica, disponibilidad de "
                                    "ingredientes según el país, y basadas en "
                                    "el progreso real del usuario. "
                                    "Tu respuesta debe ser concisa y seguir el "
                                    "formato exacto especificado, incluyendo "
                                    "valores numéricos para los macronutrientes. "
                                    "Sugiere platos típicos o populares del "
                                    "país mencionado, con beneficios específicos "
                                    "para el objetivo del usuario."
                                )
                            },
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7 + (0.05 * (intento - 1)),  # Aumentar creatividad
                        max_tokens=500
                    )
                    
                    resultado = response.choices[0].message.content.strip()
                    
                    # Extraer nombre de la receta para verificar duplicados
                    nombre_receta = self._extraer_nombre_receta(resultado)
                    logger.debug(
                        f"Nombre extraído (intento {intento}): {nombre_receta}"
                    )
                    
                    # Verificar duplicados si firebase_service está disponible
                    if self.firebase_service and nombre_receta:
                        es_duplicada = self.firebase_service.existe_receta_duplicada(
                            user.chat_id,
                            tipo_comida,
                            nombre_receta
                        )
                        
                        if es_duplicada:
                            logger.info(
                                f"Receta duplicada detectada en intento {intento}: "
                                f"{nombre_receta}. Reintentando..."
                            )
                            if intento < max_intentos:
                                continue  # Reintentar
                            else:
                                # En el último intento, retornar de todas formas
                                logger.warning(
                                    f"Máximo de intentos alcanzado para {user.chat_id}. "
                                    f"Retornando receta duplicada."
                                )
                        else:
                            # Receta única encontrada
                            logger.info(
                                f"Receta única generada en intento {intento}: "
                                f"{nombre_receta}"
                            )
                    
                    # Intentar guardar la receta en Firebase
                    if self.firebase_service and nombre_receta:
                        try:
                            self.firebase_service.guardar_receta_generada(
                                user.chat_id,
                                tipo_comida,
                                nombre_receta,
                                resultado
                            )
                            logger.debug(
                                f"Receta guardada para {user.chat_id}: {nombre_receta}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"No se pudo guardar receta para {user.chat_id}: {e}"
                            )
                    
                    logger.info(
                        f"Recommendation generated for user {user.chat_id} in {pais}"
                    )
                    return resultado
                    
                except Exception as e:
                    logger.error(
                        f"Error en intento {intento} para {user.chat_id}: {e}"
                    )
                    if intento == max_intentos:
                        raise  # Re-lanzar en el último intento
                    continue
            
            return None
            
        except Exception as e:
            logger.error(
                f"Error generating recommendation for {user.chat_id}: {e}"
            )
            return None
    
    # ========== ASISTENTE GENERAL ==========
    
    def responder_pregunta(self, pregunta: str) -> Optional[str]:
        """
        Answer general nutrition questions.
        
        Acts as expert nutrition assistant.
        
        Args:
            pregunta: User's question
            
        Returns:
            Assistant's response or None on error
        """
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert nutrition assistant. "
                            "Provide personalized advice on "
                            "food, healthy recipes, "
                            "caloric deficit and general wellness. "
                            "Be clear and friendly."
                        )
                    },
                    {"role": "user", "content": pregunta}
                ],
                temperature=0.7
            )
            
            resultado = response.choices[0].message.content.strip()
            logger.info("Response generated successfully")
            return resultado
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return None
    
    # ========== UTILIDADES DE PARSING ==========
    
    @staticmethod
    def extraer_macronutrientes(
        texto_analisis: str
    ) -> tuple:
        """
        Extrae valores de macronutrientes del análisis.
        
        Searches flexible patterns like:
        - "25g de proteína" or "25g protein"
        - "15g de grasa" or "15g fat"
        - "45g de carbohidratos" or "45g carbs"
        - "350 calorías", "350 kcal", "350 kilocalorías", etc.
        
        Args:
            texto_analisis: String with meal analysis
            
        Returns:
            Tuple (protein, fat, carbs, calories)
            Returns 0 if not found
        """
        try:
            # PROTEIN - Search: "Xg de proteína", "Xg de protein", "Xg protein", etc.
            proteina_match = re.search(
                r'(\d+)\s*g\s*(?:de\s+)?prote[íi]na',  # "25g protein" or "25g de protein"
                texto_analisis, 
                re.IGNORECASE
            )
            
            # FAT - Search: "Xg de grasa", "Xg fat", etc.
            grasa_match = re.search(
                r'(\d+)\s*g\s*(?:de\s+)?grasa',  # "15g fat" or "15g de grasa"
                texto_analisis,
                re.IGNORECASE
            )
            
            # CARBOHYDRATES - Search: "Xg de carbohidratos", "Xg carbs", etc.
            carbs_match = re.search(
                r'(\d+)\s*g\s*(?:de\s+)?(?:carbohidratos|carbs)',  # "45g carbs" or "45g de carbs"
                texto_analisis,
                re.IGNORECASE
            )
            
            # CALORIES - Searches multiple formats:
            # "350 calorie", "350cal", "350 kcal", "350kcal", "350 kilocalorie", etc.
            calorias_match = re.search(
                r'(\d+)\s*(?:kcal|calorias?|caloría|calorías|kilocaloria|kilocalorías)',  
                texto_analisis,
                re.IGNORECASE
            )
            
            # Extract values (0 if not found)
            proteina = (
                int(proteina_match.group(1)) 
                if proteina_match else 0
            )
            grasa = (
                int(grasa_match.group(1)) 
                if grasa_match else 0
            )
            carbohidratos = (
                int(carbs_match.group(1)) 
                if carbs_match else 0
            )
            calorias = (
                int(calorias_match.group(1)) 
                if calorias_match else 0
            )
            
            logger.debug(
                f"Macros extracted: "
                f"protein={proteina}g, fat={grasa}g, "
                f"carbs={carbohidratos}g, calories={calorias}"
            )
            
            return (proteina, grasa, carbohidratos, calorias)
            
        except Exception as e:
            logger.error(f"Error extracting macronutrients: {e}")
            return (0, 0, 0, 0)
