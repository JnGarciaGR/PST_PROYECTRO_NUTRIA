"""
NutrIA Configuration - Environment Variables.

This module loads credentials from environment variables.
This keeps credentials secure, outside of code.

Variables are loaded from:
1. .env file in project root (local development)
2. System environment variables (production)

Credentials are NEVER committed to Git.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load variables from local .env file
# If .env exists, loads variables from there
load_dotenv()


# ========== CREDENTIAL VALIDATION ==========

def _validar_credencial(nombre: str, valor: str) -> str:
    """
    Validate that a credential is configured.
    
    Args:
        nombre: Credential name (for messages)
        valor: Value to validate
        
    Returns:
        Value if valid
        
    Raises:
        ValueError: If credential not configured
    """
    if not valor:
        mensaje = (
            f"Error: '{nombre}' not configured.\n"
            f"Please configure environment variables:\n"
            f"  1. Copy config.example.py to .env\n"
            f"  2. Fill in your real credentials\n"
            f"  3. Make sure .env is NOT in Git"
        )
        raise ValueError(mensaje)
    return valor


# ========== REQUIRED CREDENTIALS ==========

# Telegram Bot token
TELEGRAM_TOKEN = _validar_credencial(
    "TELEGRAM_TOKEN",
    os.getenv("TELEGRAM_TOKEN")
)

# Groq API key (AI)
GROQ_API_KEY = _validar_credencial(
    "GROQ_API_KEY",
    os.getenv("GROQ_API_KEY")
)

# ========== FIREBASE ==========

# Path to Firebase credentials file
FIREBASE_CREDENTIALS_PATH = os.getenv(
    "FIREBASE_CREDENTIALS_PATH",
    "serviceAccountKey.json"
)

# Firebase database URL
FIREBASE_DATABASE_URL = _validar_credencial(
    "FIREBASE_DATABASE_URL",
    os.getenv("FIREBASE_DATABASE_URL")
)