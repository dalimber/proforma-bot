# ============================================================
# storage_service.py
# Servicio para guardar y recuperar el estado de cada
# conversación activa de WhatsApp
# ============================================================

import json   # Para convertir datos a texto y viceversa
import os     # Para manejar carpetas y archivos

# Carpeta donde se guardarán las sesiones de cada usuario
SESSIONS_DIR = "sessions"


def _ruta_sesion(telefono: str) -> str:
    """
    Genera la ruta del archivo de sesión para un número de teléfono.
    Ejemplo: "sessions/593987654321.json"
    """
    return f"{SESSIONS_DIR}/{telefono}.json"


def guardar_sesion(telefono: str, datos: dict):
    """
    Guarda el estado actual de la conversación de un usuario.
    Si la carpeta sessions no existe, la crea automáticamente.
    """
    # Crea la carpeta sessions si no existe
    if not os.path.exists(SESSIONS_DIR):
        os.makedirs(SESSIONS_DIR)

    # Abre el archivo del usuario y guarda los datos en formato JSON
    # ensure_ascii=False permite guardar tildes y caracteres especiales
    # indent=2 hace el JSON legible con sangría de 2 espacios
    with open(_ruta_sesion(telefono), "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def cargar_sesion(telefono: str) -> dict:
    """
    Carga el estado guardado de la conversación de un usuario.
    Si no existe sesión, retorna un diccionario vacío.
    """
    ruta = _ruta_sesion(telefono)

    # Si no existe el archivo de sesión, retorna vacío
    if not os.path.exists(ruta):
        return {}

    # Lee el archivo y convierte el JSON a diccionario Python
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def eliminar_sesion(telefono: str):
    """
    Elimina la sesión de un usuario.
    Se usa cuando ocurre un error grave o el usuario reinicia.
    """
    ruta = _ruta_sesion(telefono)

    # Solo elimina si el archivo existe
    if os.path.exists(ruta):
        os.remove(ruta)


def sesion_existe(telefono: str) -> bool:
    """
    Verifica si un usuario tiene una sesión activa.
    Retorna True si existe, False si no.
    """
    return os.path.exists(_ruta_sesion(telefono))