# ============================================================
# whatsapp_service.py
# Servicio para enviar y recibir mensajes por WhatsApp
# usando la API oficial de Meta
# ============================================================

import requests   # Para hacer peticiones HTTP a la API de Meta
import os         # Para leer variables de entorno
from dotenv import load_dotenv  # Para leer el archivo .env

# Cargar variables del archivo .env
load_dotenv()

# Token de autenticación de la API de WhatsApp (del archivo .env)
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")

# ID del número de teléfono de WhatsApp Business (del archivo .env)
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")

# URL base de la API de Meta con el ID del teléfono
BASE_URL = f"https://graph.facebook.com/v19.0/{PHONE_ID}"


def enviar_mensaje_texto(telefono: str, texto: str):
    """
    Envía un mensaje de texto simple a un número de WhatsApp.

    Args:
        telefono: Número del destinatario (con código de país, sin +)
        texto: Contenido del mensaje a enviar
    """
    # URL del endpoint de mensajes de la API de Meta
    url = f"{BASE_URL}/messages"

    # Cabeceras de autenticación y tipo de contenido
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",  # Token de acceso
        "Content-Type": "application/json"             # Tipo de datos
    }

    # Cuerpo del mensaje en formato JSON
    data = {
        "messaging_product": "whatsapp",  # Siempre "whatsapp"
        "to": telefono,                    # Número destinatario
        "type": "text",                    # Tipo de mensaje: texto
        "text": {"body": texto}            # Contenido del mensaje
    }

    # Envía la petición POST a la API de Meta y retorna la respuesta
    respuesta = requests.post(url, json=data, headers=headers)
    return respuesta.json()


def enviar_botones(telefono: str, texto: str, botones: list):
    """
    Envía un mensaje con botones interactivos para que el usuario
    pueda responder con un solo toque. Máximo 3 botones.

    Args:
        telefono: Número del destinatario
        texto: Pregunta o mensaje que acompaña los botones
        botones: Lista de dicts con "id" y "title" de cada botón
    """
    url = f"{BASE_URL}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    # Construye la lista de botones en el formato que acepta Meta
    # Solo toma los primeros 3 (límite de WhatsApp)
    lista_botones = []
    for btn in botones[:3]:
        lista_botones.append({
            "type": "reply",          # Tipo de botón: respuesta rápida
            "reply": {
                "id": btn["id"],      # Identificador único del botón
                "title": btn["title"] # Texto visible del botón
            }
        })

    # Cuerpo del mensaje interactivo con botones
    data = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",         # Tipo: mensaje interactivo
        "interactive": {
            "type": "button",          # Subtipo: botones de respuesta
            "body": {"text": texto},   # Texto de la pregunta
            "action": {
                "buttons": lista_botones  # Lista de botones
            }
        }
    }

    respuesta = requests.post(url, json=data, headers=headers)
    return respuesta.json()


def subir_archivo(ruta_archivo: str, mime_type: str) -> str:
    """
    Sube un archivo local (Excel o PDF) a los servidores de Meta
    y retorna el media_id que se usa para enviarlo por WhatsApp.

    Args:
        ruta_archivo: Ruta local del archivo (ej: "proformas/PROFORMA.xlsx")
        mime_type: Tipo de archivo (ej: "application/pdf")

    Returns:
        ID del archivo en Meta para poder enviarlo
    """
    url = f"{BASE_URL}/media"  # Endpoint para subir archivos

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}"
        # No incluir Content-Type aquí porque es multipart/form-data
    }

    # Abre el archivo y lo envía como multipart form data
    with open(ruta_archivo, "rb") as f:
        files = {
            # "file" es el campo requerido por Meta
            # Tupla: (nombre_del_archivo, contenido, tipo_mime)
            "file": (os.path.basename(ruta_archivo), f, mime_type)
        }
        data = {"messaging_product": "whatsapp"}  # Siempre requerido

        # Sube el archivo a los servidores de Meta
        respuesta = requests.post(url, headers=headers,
                                  files=files, data=data)

    # Extrae y retorna el media_id de la respuesta
    resultado = respuesta.json()
    return resultado.get("id", "")


def enviar_documento(telefono: str, ruta_archivo: str,
                     nombre: str, mime_type: str):
    """
    Sube un archivo a Meta y lo envía como documento por WhatsApp.
    Se usa para enviar el Excel y el PDF de la proforma.

    Args:
        telefono: Número del destinatario
        ruta_archivo: Ruta local del archivo a enviar
        nombre: Nombre que verá el destinatario
        mime_type: Tipo MIME del archivo
    """
    # Primero sube el archivo y obtiene su ID en Meta
    media_id = subir_archivo(ruta_archivo, mime_type)

    # Si no se pudo subir, termina la función
    if not media_id:
        print(f"Error: No se pudo subir el archivo {nombre}")
        return None

    url = f"{BASE_URL}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    # Cuerpo del mensaje con el documento
    data = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "document",        # Tipo: documento
        "document": {
            "id": media_id,        # ID del archivo subido a Meta
            "filename": nombre     # Nombre visible para el destinatario
        }
    }

    respuesta = requests.post(url, json=data, headers=headers)
    return respuesta.json()


def descargar_media(media_id: str, extension: str = "jpg") -> str:
    """
    Descarga un archivo multimedia (imagen o audio) enviado por
    el usuario desde WhatsApp y lo guarda en la carpeta temp.

    Args:
        media_id: ID del archivo en los servidores de Meta
        extension: Extensión del archivo (jpg para imágenes, ogg para audio)

    Returns:
        Ruta local donde se guardó el archivo descargado
    """
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

    # Paso 1: Consultar la URL real del archivo usando su ID
    url_info = f"https://graph.facebook.com/v19.0/{media_id}"
    respuesta_info = requests.get(url_info, headers=headers)
    info = respuesta_info.json()

    # Extrae la URL del archivo de la respuesta
    media_url = info.get("url", "")
    if not media_url:
        print(f"Error: No se pudo obtener la URL del archivo {media_id}")
        return ""

    # Paso 2: Descargar el archivo desde la URL obtenida
    respuesta_archivo = requests.get(media_url, headers=headers)

    # Crear carpeta temp si no existe (para archivos temporales)
    if not os.path.exists("temp"):
        os.makedirs("temp")

    # Guardar el archivo descargado localmente
    ruta_local = f"temp/{media_id}.{extension}"
    with open(ruta_local, "wb") as f:
        f.write(respuesta_archivo.content)  # Escribe el contenido binario

    return ruta_local  # Retorna la ruta para que Gemini pueda procesarlo