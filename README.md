# NutrIA - Asistente de Nutrición con IA

## Descripción

NutrIA es un asistente inteligente de nutrición que funciona como un bot de Telegram. Utiliza Groq para analizar comidas, generar recomendaciones de recetas personalizadas y realizar seguimiento nutricional basado en inteligencia artificial.

### Características principales:

- **Análisis de comidas**: Identifica macronutrientes (proteína, grasa, carbohidratos, calorías)
- **Recomendaciones personalizadas**: Sugiere recetas según tu economía y tipo de dieta
- **Seguimiento nutricional**: Registra y analiza tu consumo diario, semanal y mensual
- **Perfiles adaptables**: Se ajusta a cada usuario (peso, altura, nivel de actividad física, etc.)
- **Almacenamiento seguro**: Tus datos están guardados en Firebase en tiempo real

## Arquitectura

### Backend (Python)

Los módulos están organizados para que cada uno tenga una responsabilidad clara:

```
Módulos especializados:
├── user_model.py          Modelos de datos del usuario y nutrición
├── firebase_service.py    Integración y operaciones en Firebase
├── groq_service.py        Análisis de comidas y recomendaciones con IA
├── state_manager.py       Gestión del estado del usuario en el flujo
├── validators.py          Validaciones de todos los datos de entrada
├── formatters.py          Formatos y estilos de mensajes Telegram
├── api.py                 API REST para el dashboard
└── bot_main.py            Bot principal que orquesta todo
```

**Tecnologías utilizadas:**

- Python 3.10+
- pyTelegramBotAPI (integración con Telegram)
- firebase-admin (base de datos en tiempo real)
- groq (API de inteligencia artificial Llama)

### Frontend (React)

La parte web permite seguir el progreso nutricional desde un dashboard interactivo:

```
dashboard/NutrIA-Dashboard/
├── src/
│   ├── App.js             Componente raíz de la aplicación
│   ├── Login.js           Autenticación y login con Firebase
│   ├── Dashboard.js       Interfaz principal con estadísticas
│   └── firebase-config.js Configuración de Firebase
├── public/                Archivos estáticos HTML y favicon
└── package.json           Dependencias y scripts npm
```

## Instalación

### Antes de empezar necesitas:

- Python 3.10 o superior
- Node.js 16+ (para ejecutar el dashboard React)
- Una cuenta de Telegram (crear un bot es gratis con BotFather)
- Una cuenta en Groq (obtener API key gratuita en console.groq.com)
- Un proyecto Firebase configurado

### Paso 1: Descargar el proyecto

```bash
git clone <tu-repositorio>
cd PROYBOT
```

### Paso 2: Crear el archivo .env

NutrIA requiere un archivo `.env` con las variables de entorno. En la raíz del proyecto, crea `.env` y copia lo siguiente:

```bash
# Token del bot de Telegram
TELEGRAM_TOKEN=aqui_tu_token_de_telegram

# Clave API de Groq para análisis de comidas
GROQ_API_KEY=aqui_tu_clave_groq

# URL de tu base de datos Firebase
FIREBASE_DATABASE_URL=https://tu-proyecto-rtdb.firebaseio.com/

# Ruta al archivo de credenciales Firebase
FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json

# Nivel de logs
LOG_LEVEL=INFO
```


### Paso 3: Configurar Firebase

1. Ve a tu consola de Firebase
2. Ve a "Configuración del proyecto" → "Cuentas de servicio"
3. Descarga el archivo JSON y renómbralo a `serviceAccountKey.json`
4. Coloca este archivo en la raíz del proyecto (mismo nivel que `bot_main.py`)

### Paso 4: Instalar dependencias Python

## Cómo usar NutrIA

### Comandos disponibles en Telegram:

| Comando | Qué hace |
|---------|----------|
| `/start` | Inicia tu registro o te da la bienvenida si ya estás registrado |
| `/menu` | Muestra el menú principal con todas las opciones |
| `/help` | Te explica cómo usar cada función |
| `/reset` | Borra tu perfil y limpia todos tus datos |

### Las 4 opciones principales:

Cuando presionas `/menu`, verás estas opciones:

1. **Análisis de comida**: Escribe cualquier plato (ej. "pechuga de pollo a la parrilla") y NutrIA te dice cuántas calorías, proteína, grasa y carbohidratos tiene
2. **Recomendaciones**: NutrIA sugiere recetas que se adaptan a tu tipo de dieta y presupuesto
3. **Seguimiento**: Ves gráficamente cuánto has comido hoy, esta semana o este mes comparado con tus metas
4. **Editar perfil**: Cambias tu presupuesto, tu objetivo de dieta o tu nivel de actividad física

### Cómo se registra un usuario nuevo:

Al presionar `/start`, NutrIA te pide:

- Tu nombre completo
- Tu país de residencia
- Tu género (hombre o mujer)
- Tu peso actual en kilos
- Tu altura en centímetros
- Tu edad
- Tu nivel de actividad (desde sedentario hasta muy activo)
- Tu presupuesto para comer (bajo, medio, alto)
- Tu objetivo: bajar de peso, ganar masa, o mantener

Con esta información, NutrIA calcula cuántas calorías y macronutrientes necesitas cada día.
```

El bot estará listo en Telegram. Encuentra tu bot buscando su nombre y presiona /start.

### Paso 6: Ejecutar el dashboard (opcional)

Desde otra terminal, en la carpeta del dashboard:

```bash
cd dashboard/NutrIA-Dashboard
npm install
npm start
```

El dashboard se abrirá en http://localhost:3000

---


## Estructura del proyecto

```
PROYBOT/
├── bot_main.py              Punto de entrada, corre el bot de Telegram
├── api.py                   API REST para el dashboard
├── user_model.py            Clases que representan usuarios y datos
├── firebase_service.py      Todas las operaciones con Firebase
├── groq_service.py          Análisis de comidas e IA
├── state_manager.py         Controla el estado del user en el flujo
├── validators.py            Valida que todos los datos sean correctos
├── formatters.py            Formatos y textos de los mensajes
│
├── .env                     Variables de entorno (no subir a Git)
├── config.py                Configuración del proyecto
├── requirements.txt         Lista de paquetes a instalar
├── .gitignore               Archivos que Git ignora
├── README.md                Este archivo
│
└── dashboard/               Dashboard React (frontend)
    └── NutrIA-Dashboard/
```
## Tecnologías principales

**Backend:**
- Python 3.10, Firebase, Groq IA, Telegram Bot API, Flask

**Frontend:**
- React 18, Firebase, CSS personalizado

## Autores

- **Jaime García** 
- **Daniel Chavez** 
- **Jesúa Camuendo Diaz** 
- **Anthony Loja Suarez** 
