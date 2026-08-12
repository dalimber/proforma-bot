# ============================================================
# main.py
# Servidor principal de la aplicación.
# Recibe los mensajes de WhatsApp, coordina todos los servicios
# y devuelve la proforma generada al usuario.
# ============================================================

from fastapi import FastAPI, Request               # Framework del servidor web
from fastapi.responses import PlainTextResponse    # Para respuestas de texto plano
import os                                          # Para leer variables de entorno
from dotenv import load_dotenv                     # Para leer el archivo .env

# Importar todos los servicios del proyecto
from gemini_service import (
    extraer_datos_imagen,    # Extrae datos de una imagen
    extraer_datos_audio,     # Transcribe y extrae datos de un audio
    calcular_proforma,       # Calcula todos los valores de la proforma
    modificar_proforma,      # Aplica cambios a una proforma existente
    generar_nombre_archivo   # Genera el nombre único del archivo
)
from excel_service import generar_excel            # Genera el archivo Excel
from pdf_service import generar_pdf                # Genera el archivo PDF
from whatsapp_service import (
    enviar_mensaje_texto,    # Envía mensajes de texto
    enviar_botones,          # Envía mensajes con botones interactivos
    enviar_documento,        # Envía archivos Excel y PDF
    descargar_media          # Descarga imágenes y audios de WhatsApp
)
from storage_service import (
    guardar_sesion,          # Guarda el estado de la conversación
    cargar_sesion,           # Carga el estado de la conversación
    eliminar_sesion          # Elimina la sesión del usuario
)

# Cargar variables del archivo .env
load_dotenv()

# Crear la aplicación FastAPI
app = FastAPI()
# Middleware para ignorar advertencia de ngrok
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Token de verificación del webhook (definido en .env)
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")


# ============================================================
# RUTA 1: VERIFICACIÓN DEL WEBHOOK (GET)
# Meta llama a esta ruta cuando configuras el webhook
# para verificar que el servidor es tuyo
# ============================================================
@app.get("/webhook")
async def verificar_webhook(request: Request):
    """
    Meta envía una petición GET para verificar que el webhook
    es tuyo. Debes responder con el challenge que te envían.
    """
    # Extrae los parámetros que envía Meta en la URL
    params = dict(request.query_params)
    mode      = params.get("hub.mode")          # Debe ser "subscribe"
    token     = params.get("hub.verify_token")  # Debe coincidir con tu VERIFY_TOKEN
    challenge = params.get("hub.challenge")     # Número que debes devolver

    # Verifica que el modo y token son correctos
    if mode == "subscribe" and token == VERIFY_TOKEN:
        # Responde con el challenge para confirmar que eres el dueño
        return PlainTextResponse(content=challenge)

    # Si el token no coincide, rechaza la verificación
    return PlainTextResponse(content="Token incorrecto", status_code=403)


# ============================================================
# RUTA 2: RECIBIR MENSAJES DE WHATSAPP (POST)
# Meta envía aquí todos los mensajes que llegan a tu número
# ============================================================
@app.post("/webhook")
async def manejar_webhook(request: Request):
    """
    Recibe todos los mensajes de WhatsApp y los distribuye
    según el tipo (imagen, audio, botón o texto)
    """
    # Leer el cuerpo del mensaje en formato JSON
    body = await request.json()

    try:
        # Navegar por la estructura del JSON que envía Meta
        entry   = body["entry"][0]
        changes = entry["changes"][0]
        value   = changes["value"]

        # Si no hay mensajes en el webhook, ignorar y responder OK
        if "messages" not in value:
            return {"status": "ok"}

        # Extraer datos del primer mensaje recibido
        message  = value["messages"][0]
        telefono = message["from"]  # Número de quien escribe
        tipo_msg = message["type"]  # Tipo: image, audio, text, interactive

        # Cargar la sesión activa de este usuario (si existe)
        sesion = cargar_sesion(telefono)

        # Distribuir el mensaje según su tipo
        if tipo_msg == "image":
            # El usuario envió una imagen con productos
            await procesar_imagen(telefono, message)

        elif tipo_msg == "audio":
            # El usuario envió un audio describiendo productos
            await procesar_audio(telefono, message)

        elif tipo_msg == "interactive":
            # El usuario tocó uno de los botones del cuestionario
            reply_id = message["interactive"]["button_reply"]["id"]
            await procesar_boton(telefono, reply_id, sesion)

        elif tipo_msg == "text":
            # El usuario escribió un texto (porcentaje, nota o modificación)
            texto = message["text"]["body"].strip()
            await procesar_texto(telefono, texto, sesion)

    except Exception as e:
        # Registrar el error sin detener el servidor
        print(f"❌ Error en webhook: {e}")

    # Siempre responder 200 OK a Meta para confirmar recepción
    return {"status": "ok"}


# ============================================================
# PROCESADORES DE MENSAJES
# ============================================================

async def procesar_imagen(telefono: str, message: dict):
    """Descarga la imagen, extrae los datos y lanza el cuestionario"""

    enviar_mensaje_texto(telefono,
        "📷 Imagen recibida. Extrayendo datos de la proforma...")

    # Obtener el ID de la imagen en los servidores de Meta
    media_id = message["image"]["id"]

    # Descargar la imagen a la carpeta temp
    ruta_imagen = descargar_media(media_id, "jpg")

    if not ruta_imagen:
        enviar_mensaje_texto(telefono,
            "❌ No pude descargar la imagen. Intenta enviarla de nuevo.")
        return

    # Enviar la imagen a Gemini para extraer los datos
    datos = extraer_datos_imagen(ruta_imagen)

    # Crear una sesión nueva para este usuario con los datos extraídos
    sesion = {
        "estado": "ESPERANDO_IVA",        # Primer paso del cuestionario
        "datos_extraidos": datos,          # Datos extraídos por Gemini
        "incluye_iva": None,               # Se define en el cuestionario
        "tipo_descuento": "ninguno",       # Se define en el cuestionario
        "porcentaje_descuento": 0,         # Se define en el cuestionario
        "anticipos": {                     # Valores por defecto (60-20-20)
            "porcentaje_1": 60,
            "porcentaje_2": 20,
            "porcentaje_3": 20
        },
        "nota": "",                        # Se define en el cuestionario
        "proforma_actual": None,           # Se llena al generar la proforma
        "nombre_archivo": None             # Se llena al generar la proforma
    }
    guardar_sesion(telefono, sesion)

    # Mostrar resumen de datos extraídos al usuario
    cliente = datos.get("cliente", {})
    num_productos = len(datos.get("productos", []))

    resumen = (
        f"✅ *Datos extraídos correctamente:*\n\n"
        f"👤 Cliente: {cliente.get('nombre', '-')}\n"
        f"📍 Lugar: {cliente.get('lugar', '-')}\n"
        f"🏗️ Obra: {cliente.get('obra', '-')}\n"
        f"📦 Productos encontrados: *{num_productos}*\n\n"
        f"Responde el siguiente cuestionario para generar la proforma:"
    )
    enviar_mensaje_texto(telefono, resumen)

    # Lanzar el cuestionario — primera pregunta: IVA
    preguntar_iva(telefono)


async def procesar_audio(telefono: str, message: dict):
    """Descarga el audio, lo transcribe y lanza el cuestionario"""

    enviar_mensaje_texto(telefono,
        "🎙️ Audio recibido. Transcribiendo y extrayendo datos...")

    # Obtener el ID del audio en los servidores de Meta
    media_id = message["audio"]["id"]

    # Descargar el audio a la carpeta temp (formato OGG de WhatsApp)
    ruta_audio = descargar_media(media_id, "ogg")

    if not ruta_audio:
        enviar_mensaje_texto(telefono,
            "❌ No pude descargar el audio. Intenta enviarlo de nuevo.")
        return

    # Enviar el audio a Gemini para transcribir y extraer datos
    datos = extraer_datos_audio(ruta_audio)

    # Crear sesión nueva con los datos extraídos del audio
    sesion = {
        "estado": "ESPERANDO_IVA",
        "datos_extraidos": datos,
        "incluye_iva": None,
        "tipo_descuento": "ninguno",
        "porcentaje_descuento": 0,
        "anticipos": {
            "porcentaje_1": 60,
            "porcentaje_2": 20,
            "porcentaje_3": 20
        },
        "nota": "",
        "proforma_actual": None,
        "nombre_archivo": None
    }
    guardar_sesion(telefono, sesion)

    # Mostrar resumen de datos extraídos
    cliente = datos.get("cliente", {})
    num_productos = len(datos.get("productos", []))

    resumen = (
        f"✅ *Audio transcrito correctamente:*\n\n"
        f"👤 Cliente: {cliente.get('nombre', '-')}\n"
        f"📍 Lugar: {cliente.get('lugar', '-')}\n"
        f"🏗️ Obra: {cliente.get('obra', '-')}\n"
        f"📦 Productos encontrados: *{num_productos}*\n\n"
        f"Responde el siguiente cuestionario para generar la proforma:"
    )
    enviar_mensaje_texto(telefono, resumen)

    # Lanzar primera pregunta del cuestionario
    preguntar_iva(telefono)


async def procesar_boton(telefono: str, reply_id: str, sesion: dict):
    """
    Procesa la respuesta cuando el usuario toca un botón.
    Avanza al siguiente paso del cuestionario según el estado actual.
    """
    estado = sesion.get("estado", "INICIO")

    # --- Respuesta a pregunta de IVA ---
    if estado == "ESPERANDO_IVA":
        sesion["incluye_iva"] = (reply_id == "con_iva")  # True o False
        sesion["estado"] = "ESPERANDO_DESCUENTO_TIPO"
        guardar_sesion(telefono, sesion)
        preguntar_descuento_tipo(telefono)  # Siguiente pregunta

    # --- Respuesta a pregunta de tipo de descuento ---
    elif estado == "ESPERANDO_DESCUENTO_TIPO":

        if reply_id == "sin_descuento":
            # Sin descuento: saltar directo a anticipos
            sesion["tipo_descuento"] = "ninguno"
            sesion["porcentaje_descuento"] = 0
            sesion["estado"] = "ESPERANDO_ANTICIPOS"
            guardar_sesion(telefono, sesion)
            preguntar_anticipos(telefono)

        elif reply_id == "desc_individual":
            # Descuento individual: pedir el porcentaje
            sesion["tipo_descuento"] = "individual"
            sesion["estado"] = "ESPERANDO_DESCUENTO_PCT"
            guardar_sesion(telefono, sesion)
            enviar_mensaje_texto(telefono,
                "¿Cuál es el porcentaje de descuento individual?\n"
                "Escribe solo el número. Ej: *5* para 5%"
            )

        elif reply_id == "desc_global":
            # Descuento global: pedir el porcentaje
            sesion["tipo_descuento"] = "global"
            sesion["estado"] = "ESPERANDO_DESCUENTO_PCT"
            guardar_sesion(telefono, sesion)
            enviar_mensaje_texto(telefono,
                "¿Cuál es el porcentaje de descuento global?\n"
                "Escribe solo el número. Ej: *10* para 10%"
            )

    # --- Respuesta a pregunta de anticipos ---
    elif estado == "ESPERANDO_ANTICIPOS":

        if reply_id == "anticipos_estandar":
            # Usar distribución estándar 60-20-20
            sesion["anticipos"] = {
                "porcentaje_1": 60,
                "porcentaje_2": 20,
                "porcentaje_3": 20
            }
            sesion["estado"] = "ESPERANDO_NOTA"
            guardar_sesion(telefono, sesion)
            preguntar_nota(telefono)

        elif reply_id == "anticipos_custom":
            # Pedir distribución personalizada
            sesion["estado"] = "ESPERANDO_ANTICIPOS_CUSTOM"
            guardar_sesion(telefono, sesion)
            enviar_mensaje_texto(telefono,
                "Escribe los 3 porcentajes separados por guión.\n"
                "Deben sumar exactamente 100.\n"
                "Ej: *50-30-20*"
            )

    # --- Respuesta a pregunta de nota ---
    elif estado == "ESPERANDO_NOTA":

        if reply_id == "sin_nota":
            # Sin nota: generar la proforma directamente
            sesion["nota"] = ""
            sesion["estado"] = "GENERANDO"
            guardar_sesion(telefono, sesion)
            await generar_y_enviar_proforma(telefono, sesion)

        elif reply_id == "con_nota":
            # Con nota: pedir el texto de la nota
            sesion["estado"] = "ESPERANDO_NOTA_TEXTO"
            guardar_sesion(telefono, sesion)
            enviar_mensaje_texto(telefono,
                "✍️ Escribe la nota o condición especial:"
            )


async def procesar_texto(telefono: str, texto: str, sesion: dict):
    """
    Procesa los mensajes de texto del usuario.
    Puede ser: porcentaje de descuento, distribución de anticipos,
    texto de nota o instrucción de modificación de la proforma.
    """
    estado = sesion.get("estado", "INICIO")

    # --- El usuario escribe el porcentaje de descuento ---
    if estado == "ESPERANDO_DESCUENTO_PCT":
        try:
            # Convertir el texto a número (elimina % si lo escribió)
            porcentaje = float(texto.replace("%", "").strip())
            sesion["porcentaje_descuento"] = porcentaje
            sesion["estado"] = "ESPERANDO_ANTICIPOS"
            guardar_sesion(telefono, sesion)

            tipo = sesion.get("tipo_descuento", "ninguno")
            enviar_mensaje_texto(telefono,
                f"✅ Descuento {tipo} del {porcentaje}% registrado."
            )
            preguntar_anticipos(telefono)

        except ValueError:
            # Si no es un número válido, pedir que lo intente de nuevo
            enviar_mensaje_texto(telefono,
                "⚠️ Por favor escribe solo el número. Ej: *5*"
            )

    # --- El usuario escribe los anticipos personalizados ---
    elif estado == "ESPERANDO_ANTICIPOS_CUSTOM":
        try:
            # Separar los 3 porcentajes por el guión
            partes = texto.strip().split("-")
            p1 = float(partes[0])
            p2 = float(partes[1])
            p3 = float(partes[2])

            # Verificar que sumen exactamente 100
            if abs((p1 + p2 + p3) - 100) > 0.01:
                enviar_mensaje_texto(telefono,
                    f"⚠️ Los porcentajes suman {p1+p2+p3}, "
                    f"deben sumar exactamente 100.\n"
                    f"Intenta de nuevo. Ej: *50-30-20*"
                )
                return

            # Guardar los porcentajes personalizados
            sesion["anticipos"] = {
                "porcentaje_1": p1,
                "porcentaje_2": p2,
                "porcentaje_3": p3
            }
            sesion["estado"] = "ESPERANDO_NOTA"
            guardar_sesion(telefono, sesion)

            enviar_mensaje_texto(telefono,
                f"✅ Anticipos registrados: {p1:.0f}% - {p2:.0f}% - {p3:.0f}%"
            )
            preguntar_nota(telefono)

        except (ValueError, IndexError):
            # Si el formato es incorrecto, pedir que lo intente de nuevo
            enviar_mensaje_texto(telefono,
                "⚠️ Formato incorrecto. Escribe 3 números separados por guión.\n"
                "Ej: *50-30-20*"
            )

    # --- El usuario escribe el texto de la nota especial ---
    elif estado == "ESPERANDO_NOTA_TEXTO":
        sesion["nota"] = texto           # Guardar el texto de la nota
        sesion["estado"] = "GENERANDO"
        guardar_sesion(telefono, sesion)
        await generar_y_enviar_proforma(telefono, sesion)

    # --- El usuario quiere modificar una proforma ya generada ---
    elif estado == "PROFORMA_LISTA":
        enviar_mensaje_texto(telefono, "🔄 Aplicando modificaciones...")

        # Cargar la proforma actual guardada en sesión
        proforma_actual = sesion.get("proforma_actual")

        if not proforma_actual:
            enviar_mensaje_texto(telefono,
                "❌ No encontré una proforma activa para modificar.\n"
                "Envía una imagen o audio para crear una nueva."
            )
            return

        try:
            # Enviar a Gemini la proforma actual y la instrucción de cambio
            proforma_modificada = modificar_proforma(proforma_actual, texto)

            nombre_archivo    = sesion.get("nombre_archivo")
            tipo_descuento    = sesion.get("tipo_descuento", "ninguno")
            porcentaje_desc   = sesion.get("porcentaje_descuento", 0)

            # Regenerar el Excel con los cambios aplicados
            ruta_excel = generar_excel(
                proforma_modificada, nombre_archivo,
                tipo_descuento, porcentaje_desc
            )

            # Regenerar el PDF con los cambios aplicados
            ruta_pdf = generar_pdf(
                proforma_modificada, nombre_archivo,
                tipo_descuento, porcentaje_desc
            )

            # Actualizar la proforma en la sesión con los nuevos datos
            sesion["proforma_actual"] = proforma_modificada
            guardar_sesion(telefono, sesion)

            # Enviar los archivos actualizados al usuario
            enviar_mensaje_texto(telefono,
                "✅ *Proforma modificada exitosamente.*\n"
                "Aquí están los archivos actualizados:"
            )

            # Enviar Excel actualizado
            enviar_documento(
                telefono, ruta_excel,
                f"{nombre_archivo}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # Enviar PDF actualizado
            enviar_documento(
                telefono, ruta_pdf,
                f"{nombre_archivo}.pdf",
                "application/pdf"
            )

        except Exception as e:
            enviar_mensaje_texto(telefono,
                f"❌ Error al modificar: {str(e)}\n"
                "Intenta describir el cambio de otra manera."
            )

    # --- El usuario escribe sin tener una sesión activa ---
    else:
        enviar_mensaje_texto(telefono,
            "👋 ¡Hola! Para generar una proforma envíame:\n\n"
            "📷 Una *imagen* con los productos\n"
            "🎙️ Un *audio* describiendo los productos\n\n"
            "Yo me encargo del resto 😊"
        )


# ============================================================
# GENERAR Y ENVIAR LA PROFORMA COMPLETA
# ============================================================
async def generar_y_enviar_proforma(telefono: str, sesion: dict):
    """
    Toma todos los datos recopilados en el cuestionario,
    genera la proforma, crea el Excel y PDF y los envía por WhatsApp.
    """
    enviar_mensaje_texto(telefono,
        "⚙️ Generando tu proforma, un momento..."
    )

    try:
        # Extraer todos los valores del cuestionario guardados en sesión
        datos              = sesion["datos_extraidos"]
        incluye_iva        = sesion["incluye_iva"]
        tipo_descuento     = sesion["tipo_descuento"]
        porcentaje_desc    = sesion["porcentaje_descuento"]
        anticipos          = sesion["anticipos"]
        nota               = sesion.get("nota", "")

        # Calcular todos los valores de la proforma con Gemini
        proforma = calcular_proforma(
            datos=datos,
            incluye_iva=incluye_iva,
            anticipos=anticipos,
            nota=nota,
            tipo_descuento=tipo_descuento,
            porcentaje_descuento=porcentaje_desc
        )

        # Generar el nombre único del archivo (ej: PROFORMA20260613_CLIENTE)
        nombre_cliente = datos["cliente"]["nombre"]
        if nombre_cliente == "-":
            nombre_cliente = "CLIENTE"  # Nombre por defecto si no se detectó
        nombre_archivo = generar_nombre_archivo(nombre_cliente)

        # Generar el archivo Excel basado en la plantilla
        ruta_excel = generar_excel(
            proforma, nombre_archivo,
            tipo_descuento, porcentaje_desc
        )

        # Generar el archivo PDF
        ruta_pdf = generar_pdf(
            proforma, nombre_archivo,
            tipo_descuento, porcentaje_desc
        )

        # Guardar la proforma generada en la sesión para modificaciones futuras
        sesion["estado"]          = "PROFORMA_LISTA"
        sesion["proforma_actual"] = proforma
        sesion["nombre_archivo"]  = nombre_archivo
        guardar_sesion(telefono, sesion)

        # Enviar resumen de la proforma al usuario
        resumen = (
            f"✅ *Proforma generada exitosamente*\n\n"
            f"👤 Cliente: {proforma['cliente']['nombre']}\n"
            f"📅 Fecha: {proforma['fecha']}\n"
            f"💰 Subtotal: *${proforma['subtotal']:,.2f}*\n"
            f"🧾 IVA: *${proforma['iva']:,.2f}*\n"
            f"💵 Total: *${proforma['total']:,.2f}*\n\n"
            f"📎 Aquí están tus archivos:"
        )
        enviar_mensaje_texto(telefono, resumen)

        # Enviar archivo Excel
        enviar_documento(
            telefono, ruta_excel,
            f"{nombre_archivo}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Enviar archivo PDF
        enviar_documento(
            telefono, ruta_pdf,
            f"{nombre_archivo}.pdf",
            "application/pdf"
        )

        # Informar al usuario que puede pedir modificaciones
        enviar_mensaje_texto(telefono,
            "💬 Si necesitas hacer algún cambio, escríbelo aquí.\n"
            "_Ejemplos:_\n"
            "• _Elimina el producto 2_\n"
            "• _Cambia el precio del cemento a $9.00_\n"
            "• _Agrega 5% de descuento al producto 3_"
        )

    except Exception as e:
        # Si algo falla, informar al usuario y limpiar la sesión
        print(f"❌ Error generando proforma: {e}")
        enviar_mensaje_texto(telefono,
            "❌ Ocurrió un error al generar la proforma.\n"
            "Por favor envía la imagen o audio de nuevo."
        )
        eliminar_sesion(telefono)


# ============================================================
# PREGUNTAS DEL CUESTIONARIO (funciones de ayuda)
# ============================================================

def preguntar_iva(telefono: str):
    """Envía la primera pregunta del cuestionario: ¿Con o sin IVA?"""
    enviar_botones(
        telefono,
        "1️⃣ ¿La proforma incluye IVA?",
        [
            {"id": "con_iva",  "title": "✅ Con IVA (15%)"},
            {"id": "sin_iva",  "title": "❌ Sin IVA"}
        ]
    )


def preguntar_descuento_tipo(telefono: str):
    """Envía la segunda pregunta: ¿Qué tipo de descuento aplica?"""
    enviar_botones(
        telefono,
        "2️⃣ ¿Qué tipo de descuento aplica?",
        [
            {"id": "sin_descuento",   "title": "Sin descuento"},
            {"id": "desc_individual", "title": "Individual"},
            {"id": "desc_global",     "title": "Global"}
        ]
    )


def preguntar_anticipos(telefono: str):
    """Envía la tercera pregunta: ¿Distribución de anticipos?"""
    enviar_botones(
        telefono,
        "3️⃣ ¿Distribución de anticipos?",
        [
            {"id": "anticipos_estandar", "title": "60-20-20 estándar"},
            {"id": "anticipos_custom",   "title": "Personalizado"}
        ]
    )


def preguntar_nota(telefono: str):
    """Envía la cuarta y última pregunta: ¿Agregar nota especial?"""
    enviar_botones(
        telefono,
        "4️⃣ ¿Deseas agregar una nota o condición especial?",
        [
            {"id": "con_nota", "title": "✍️ Sí, agregar nota"},
            {"id": "sin_nota", "title": "❌ No, generar ya"}
        ]
    )