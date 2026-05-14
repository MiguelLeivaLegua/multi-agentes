"""
deepseek_client.py - Cliente de conexión con DeepSeek API (V2 - Con Historial)
Autor: @Programador (Lead Developer)
Propósito: Centraliza todas las llamadas a DeepSeek. Ahora soporta
           conversaciones con historial (memoria por agente).

Seguridad: La API key se lee SIEMPRE desde variables de entorno (.env).
           Nunca se escribe directamente en el código.
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# Cargamos las variables de entorno desde .env (en la raíz del proyecto)
load_dotenv()

# ─── Configuración del cliente ──────────────────────────────────────────────

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
# Timeout en segundos: evita que la llamada se quede colgada si DeepSeek no responde
DEEPSEEK_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT", "120"))

if not DEEPSEEK_API_KEY:
    raise EnvironmentError(
        "[ERROR] La variable de entorno 'DEEPSEEK_API_KEY' no está definida. "
        "Revisa el archivo .env en la raíz del proyecto."
    )

# Instancia compartida del cliente (reutilizable en todo el proyecto)
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    timeout=DEEPSEEK_TIMEOUT,  # Timeout para no quedarse colgado
)


# ─── Consulta simple (sin historial, una sola vez) ─────────────────────────

def consultar_agente(system_prompt: str, mensaje_usuario: str, temperatura: float = 0.7) -> str:
    """
    Envía un mensaje único al modelo DeepSeek (sin historial).
    Útil para consultas rápidas o verificación de conexión.
    """
    try:
        respuesta = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": mensaje_usuario},
            ],
            temperature=temperatura,
            stream=False,
        )
        return respuesta.choices[0].message.content

    except Exception as e:
        raise RuntimeError(f"[ERROR] Fallo al consultar DeepSeek: {e}") from e


# ─── Consulta con historial (memoria de conversación) ──────────────────────

def consultar_con_historial(mensajes: list, temperatura: float = 0.7) -> str:
    """
    Envía una conversación completa (con historial) al modelo DeepSeek.
    
    Parámetros:
        mensajes    : Lista de dicts [{"role": "system"|"user"|"assistant", "content": "..."}]
        temperatura : Controla la creatividad (0.0 = determinista, 1.0 = creativo).
    
    Retorna:
        str: Texto de la respuesta del modelo.
    """
    try:
        respuesta = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=mensajes,
            temperature=temperatura,
            stream=False,
        )
        return respuesta.choices[0].message.content

    except Exception as e:
        raise RuntimeError(f"[ERROR] Fallo al consultar DeepSeek con historial: {e}") from e


# ─── Prueba de conexión ─────────────────────────────────────────────────────

def verificar_conexion() -> bool:
    """Verifica que la API key y la conexión a DeepSeek sean válidas."""
    try:
        respuesta = consultar_agente(
            system_prompt="Eres un asistente de prueba.",
            mensaje_usuario="Responde solo 'OK' si me estás recibiendo.",
            temperatura=0.0,
        )
        print(f"[✅ CONEXIÓN OK] Respuesta: {respuesta.strip()}")
        return True
    except Exception as e:
        print(f"[❌ ERROR DE CONEXIÓN] {e}")
        return False


if __name__ == "__main__":
    print("Verificando conexión con DeepSeek API...")
    verificar_conexion()
