"""
Módulo de modelos de usuario para NutrIA.

Define las clases que representan los datos de un usuario:
- User: Perfil completo con datos personales y preferencias
- NutritionData: Información nutricional de alimentos o comidas

Estos modelos se usan para calcular recomendaciones personalizadas
y guardar/cargar datos desde Firebase.
"""

from datetime import date
from typing import Dict, Optional, List


class User:
    """
    Representa el perfil completo de un usuario en NutrIA.
    
    Almacena todos los datos personales necesarios para calcular
    recomendaciones nutricionales personalizadas. Todos estos datos
    se usan para determinar cuántas calorías y macronutrientes
    necesita diariamente el usuario.
    
    Atributos:
        chat_id: ID único en Telegram
        nombre: Nombre completo
        pais: País de residencia
        genero: Hombre o Mujer
        peso: Peso en kilogramos
        altura_cm: Altura en centímetros
        edad: Edad en años
        actividad_fisica: Nivel de actividad (de sedentario a muy intensa)
        economia: Nivel económico (Alta, Media, Baja)
        dieta: Objetivo de la dieta (déficit, recomposición, superávit)
    """
    
    # Valores permitidos para cada atributo
    GENEROS_VALIDOS = ["Hombre", "Mujer"]
    ACTIVIDADES_VALIDAS = [
        "Sedentario", "Ligera", "Moderada", "Intensa", "Muy intensa"
    ]
    ECONOMIA_VALIDA = ["Alta", "Media", "Baja"]
    DIETAS_VALIDAS = [
        "Déficit calórico", "Recomposición muscular", "Superávit calórico"
    ]
    
    def __init__(self, chat_id: int):
        """
        Crea un nuevo usuario con un ID de Telegram.
        
        Todos los campos comienzan como None porque se rellenan
        gradualmente durante el registro.
        
        Args:
            chat_id: ID único del usuario en Telegram
        """
        self.chat_id = chat_id
        self.nombre: Optional[str] = None
        self.pais: Optional[str] = None
        self.genero: Optional[str] = None
        self.peso: Optional[float] = None
        self.altura_cm: Optional[float] = None
        self.edad: Optional[int] = None
        self.actividad_fisica: Optional[str] = None
        self.economia: Optional[str] = None
        self.dieta: Optional[str] = None
    
    def esta_completo(self) -> bool:
        """
        Verifica si el usuario completó todos los pasos de registro.
        
        Retorna True solo si TODOS los campos están rellenos.
        
        Returns:
            True si el perfil está completo, False en caso contrario
        """
        return all([
            self.nombre,
            self.pais,
            self.genero,
            self.peso,
            self.altura_cm,
            self.edad,
            self.actividad_fisica,
            self.economia,
            self.dieta
        ])
    
    def calcular_macros_necesarios(self) -> 'NutritionData':
        """
        Calcula las metas diarias de macronutrientes para este usuario.
        
        Usa la fórmula Mifflin-St Jeor (más precisión que Harris-Benedict).
        Luego ajusta según el nivel de actividad y el objetivo de dieta.
        
        Proceso:
        1. Calcula el metabolismo basal (TMB) según género, peso, altura y edad
        2. Multiplica por factor de actividad física
        3. Ajusta calorías según objetivo (déficit/superávit/mantenimiento)
        4. Calcula proteína dinámicamente (aumentada en déficit, reducida en superávit)
        5. Distribuye el resto entre grasa y carbohidratos
        
        Basado en:
        - Fórmula Mifflin-St Jeor (NIH, 1990)
        - Factores de actividad Katch-McArdle
        - Lineamientos ISSN 2017 y Academy of Nutrition & Dietetics
        
        Returns:
            Objeto NutritionData con proteína, grasa, carbos y calorías diarias
        """
        if not self.peso or not self.altura_cm or not self.edad:
            return NutritionData()  # Retorna ceros si falta información
        
        # Paso 1: Calcular TMB (Tasa Metabólica Basal)
        if self.genero == "Hombre":
            tmb = (10 * self.peso) + (6.25 * self.altura_cm) - (5 * self.edad) + 5
        else:  # Mujer
            tmb = (10 * self.peso) + (6.25 * self.altura_cm) - (5 * self.edad) - 161
        
        # Paso 2: Aplicar factor de actividad física
        factores_actividad = {
            "Sedentario": 1.2,      # Poco o ningún ejercicio
            "Ligera": 1.375,        # 1-3 días por semana
            "Moderada": 1.55,       # 3-5 días por semana
            "Intensa": 1.725,       # 6-7 días por semana
            "Muy intensa": 1.9      # Entrenamiento diario intenso
        }
        factor = factores_actividad.get(self.actividad_fisica, 1.55)
        tdee = tmb * factor  # Gasto calórico diario total
        
        # Paso 3: Ajustar por objetivo de dieta
        if self.dieta == "Déficit calórico":
            # Déficit 15% = pérdida 0.5-0.75 kg/semana
            calorias_diarias = tdee * 0.85
            # Proteína aumentada a 2.3g/kg para preservar músculo en déficit
            proteina_g = round(self.peso * 2.3)
            
        elif self.dieta == "Superávit calórico":
            # Superávit 15% = ganancia 0.5-0.75 kg/semana
            calorias_diarias = tdee * 1.15
            # Proteína reducida a 1.8g/kg (suficiente en ganancia)
            proteina_g = round(self.peso * 1.8)
            
        else:  # Recomposición muscular
            # Mantenimiento calórico exacto
            calorias_diarias = tdee
            # Proteína estándar 2.0g/kg (óptimo para recomposición)
            proteina_g = round(self.peso * 2.0)
        
        # Paso 4: Distribuir macronutrientes
        # Grasa: 25% de calorías (rango validado 20-35%)
        grasa_g = round((calorias_diarias * 0.25) / 9)
        # Carbohidratos: lo que sobra después de proteína y grasa
        carbs_g = round(
            (calorias_diarias - (proteina_g * 4) - (grasa_g * 9)) / 4
        )
        
        return NutritionData(
            proteina=proteina_g,
            grasa=grasa_g,
            carbohidratos=carbs_g,
            calorias=round(calorias_diarias)
        )
    
    def a_dict(self) -> Dict:
        """
        Convierte el usuario a diccionario para guardar en Firebase.
        
        Incluye todas las metas de macronutrientes calculadas en base
        a los datos personales del usuario.
        
        Returns:
            Diccionario con datos del usuario y sus metas nutricionales
        """
        macros = self.calcular_macros_necesarios()
        return {
            'nombre': self.nombre,
            'pais': self.pais,
            'genero': self.genero,
            'peso': self.peso,
            'altura': self.altura_cm,
            'edad': self.edad,
            'actividad_fisica': self.actividad_fisica,
            'economia': self.economia,
            'dieta': self.dieta,
            'macros_necesarios': macros.a_dict(),
        }
    
    @classmethod
    def desde_dict(cls, chat_id: int, data: Dict) -> 'User':
        """
        Crea un usuario cargando datos desde Firebase.
        
        Se usa cuando recuperamos un usuario que ya estaba registrado
        en la base de datos.
        
        Args:
            chat_id: ID del usuario en Telegram
            data: Diccionario con los datos del usuario desde Firebase
            
        Returns:
            Instancia de User con todos los datos cargados
        """
        user = cls(chat_id)
        user.nombre = data.get('nombre')
        user.pais = data.get('pais')
        user.genero = data.get('genero')
        user.peso = data.get('peso')
        user.altura_cm = data.get('altura')
        user.edad = data.get('edad')
        user.actividad_fisica = data.get('actividad_fisica')
        user.economia = data.get('economia')
        user.dieta = data.get('dieta')
        return user


class NutritionData:
    """
    Representa información nutricional de un alimento o comida.
    
    Almacena los cuatro macronutrientes principales: proteína, grasa,
    carbohidratos y calorías. Se usa tanto para guardar metas diarias
    como para registrar lo que el usuario comió.
    
    Atributos:
        proteina: Gramos de proteína
        grasa: Gramos de grasa
        carbohidratos: Gramos de carbohidratos
        calorias: Total de calorías
    """
    
    def __init__(
        self,
        proteina: int = 0,
        grasa: int = 0,
        carbohidratos: int = 0,
        calorias: int = 0
    ):
        """
        Crea un objeto con datos nutricionales.
        
        Todos los valores son opcionales y por defecto son 0.
        
        Args:
            proteina: Gramos de proteína
            grasa: Gramos de grasa
            carbohidratos: Gramos de carbohidratos
            calorias: Total de calorías
        """
        self.proteina = proteina
        self.grasa = grasa
        self.carbohidratos = carbohidratos
        self.calorias = calorias
    
    def __add__(self, otro: 'NutritionData') -> 'NutritionData':
        """
        Suma dos objetos de nutrición (útil para sumar comidas del día).
        
        Permite hacer cosas como: desayuno + almuerzo + cena = total_diario
        
        Args:
            otro: Otro objeto NutritionData a sumar
            
        Returns:
            Nuevo objeto NutritionData con la suma de ambos
        """
        return NutritionData(
            proteina=self.proteina + otro.proteina,
            grasa=self.grasa + otro.grasa,
            carbohidratos=self.carbohidratos + otro.carbohidratos,
            calorias=self.calorias + otro.calorias
        )
    
    def a_dict(self) -> Dict:
        """
        Convierte a diccionario para guardar en Firebase.
        
        Returns:
            Diccionario con los nutrientes
        """
        return {
            'proteina': self.proteina,
            'grasa': self.grasa,
            'carbohidratos': self.carbohidratos,
            'calorias': self.calorias
        }
    
    @classmethod
    def desde_dict(cls, data: Dict) -> 'NutritionData':
        """
        Crea un objeto desde un diccionario (cargado desde Firebase).
        
        Es flexible con los nombres de campos porque Firebase podría tener
        nombres como "total_proteina" en datos antiguos.
        
        Args:
            data: Diccionario con los datos nutricionales
            
        Returns:
            Nuevo objeto NutritionData con los valores cargados
        """
        return cls(
            proteina=data.get('proteina', data.get('total_proteina', 0)),
            grasa=data.get('grasa', data.get('total_grasa', 0)),
            carbohidratos=data.get(
                'carbohidratos',
                data.get('total_carbohidratos', 0)
            ),
            calorias=data.get('calorias', data.get('total_calorias', 0))
        )
    
    def __repr__(self) -> str:
        """
        Devuelve una representación legible del objeto (útil para debugging).
        
        Returns:
            String con los datos nutricionales formateados
        """
        return (
            f"NutritionData(proteina={self.proteina}g, "
            f"grasa={self.grasa}g, "
            f"carbohidratos={self.carbohidratos}g, "
            f"calorias={self.calorias})"
        )
