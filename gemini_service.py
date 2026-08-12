# ============================================================
# gemini_service.py
# Servicio de IA para procesar imágenes y audios con Gemini
# ============================================================

from google import genai          # Nueva librería oficial de Google
from google.genai import types    # Para configurar tipos de contenido
import os                         # Para manejar rutas y archivos
from dotenv import load_dotenv    # Para leer el archivo .env
from datetime import datetime     # Para obtener la fecha actual
import json                       # Para convertir texto JSON a datos Python

# Cargar variables del archivo .env
load_dotenv()

# Crear el cliente de Gemini con la API Key
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Modelo a utilizar
MODELO = "gemini-3.5-flash"


# ============================================================
# FUNCIÓN 1: Extraer datos desde una IMAGEN
# ============================================================
def extraer_datos_imagen(ruta_imagen: str) -> dict:
    """Lee una imagen y extrae los datos de la proforma"""

    # Leer el archivo de imagen en modo binario
    with open(ruta_imagen, "rb") as f:
        imagen_bytes = f.read()

    # Instrucciones para que Gemini analice la imagen
    prompt = """
    Analiza esta imagen y extrae la información para una proforma.

    REGLAS IMPORTANTES:
    - Si encuentras el símbolo " o "" en la descripción de un producto,
      significa que la descripción es IGUAL a la del producto anterior,
      copia exactamente esa descripción en ese campo
    - Si cantidad o precio_unitario no están especificados en la imagen,
      coloca el valor 0
    - Si no encuentras el nombre, lugar u obra del cliente,
      coloca el símbolo "-" en ese campo
    - El campo descripcion_adicional es información extra del producto
      (por ejemplo: color, material, medida especial).
      Si no existe esa información, coloca "-"
    - NO extraigas descuentos, esos los preguntará el sistema aparte

    Devuelve ÚNICAMENTE este JSON sin ningún texto adicional,
    sin comillas de bloque, sin explicaciones:
    {
        "cliente": {
            "nombre": "nombre del cliente o -",
            "lugar": "lugar o ciudad o -",
            "obra": "nombre de la obra o proyecto o -"
        },
        "productos": [
            {
                "producto": "nombre del producto",
                "descripcion": "descripción principal del producto",
                "descripcion_adicional": "descripción extra o -",
                "cantidad": 0,
                "precio_unitario": 0.00
            }
        ]
    }
    """

    # Enviar imagen e instrucciones a Gemini usando la nueva API
    respuesta = client.models.generate_content(
        model=MODELO,
        contents=[
            types.Part.from_bytes(
                data=imagen_bytes,
                mime_type="image/jpeg"
            ),
            prompt
        ]
    )

    # Limpiar la respuesta de caracteres innecesarios
    texto = respuesta.text.strip()
    texto = texto.replace("```json", "").replace("```", "").strip()

    # Convertir texto JSON a diccionario Python
    return json.loads(texto)


# ============================================================
# FUNCIÓN 2: Extraer datos desde un AUDIO
# ============================================================
def extraer_datos_audio(ruta_audio: str) -> dict:
    """Transcribe un audio y extrae los datos de la proforma"""

    # Leer el archivo de audio en modo binario
    with open(ruta_audio, "rb") as f:
        audio_bytes = f.read()

    # Instrucciones para que Gemini transcriba el audio
    prompt = """
    Transcribe este audio y extrae la información para una proforma.

    REGLAS IMPORTANTES:
    - Si cantidad o precio_unitario no se mencionan en el audio,
      coloca el valor 0
    - Si no se menciona el nombre, lugar u obra del cliente,
      coloca el símbolo "-" en ese campo
    - El campo descripcion_adicional es información extra del producto
      (por ejemplo: color, material, medida especial).
      Si no se menciona, coloca "-"
    - NO extraigas descuentos, esos los preguntará el sistema aparte

    Devuelve ÚNICAMENTE este JSON sin ningún texto adicional,
    sin comillas de bloque, sin explicaciones:
    {
        "cliente": {
            "nombre": "nombre del cliente o -",
            "lugar": "lugar o ciudad o -",
            "obra": "nombre de la obra o proyecto o -"
        },
        "productos": [
            {
                "producto": "nombre del producto",
                "descripcion": "descripción principal del producto",
                "descripcion_adicional": "descripción extra o -",
                "cantidad": 0,
                "precio_unitario": 0.00
            }
        ]
    }
    """

    # Enviar audio e instrucciones a Gemini usando la nueva API
    respuesta = client.models.generate_content(
        model=MODELO,
        contents=[
            types.Part.from_bytes(
                data=audio_bytes,
                mime_type="audio/ogg"
            ),
            prompt
        ]
    )

    # Limpiar la respuesta
    texto = respuesta.text.strip()
    texto = texto.replace("```json", "").replace("```", "").strip()

    return json.loads(texto)


# ============================================================
# FUNCIÓN 3: Calcular todos los valores de la proforma
# ============================================================
def calcular_proforma(datos: dict, incluye_iva: bool,
                      anticipos: dict, nota: str = "",
                      tipo_descuento: str = "ninguno",
                      porcentaje_descuento: float = 0) -> dict:
    """Calcula totales, IVA y anticipos de la proforma"""

    productos = datos["productos"]

    # Recorrer productos: agregar número consecutivo y calcular total
    for i, p in enumerate(productos, 1):
        p["numero"] = i  # Número consecutivo automático

        subtotal_item = p["cantidad"] * p["precio_unitario"]

        # Descuento individual por producto
        if tipo_descuento == "individual":
            p["descuento_valor"] = round(
                subtotal_item * (porcentaje_descuento / 100), 2
            )
        else:
            p["descuento_valor"] = 0

        p["total"] = round(subtotal_item - p["descuento_valor"], 2)

    # Subtotal general
    subtotal = round(sum(p["total"] for p in productos), 2)

    # Descuento global
    if tipo_descuento == "global":
        descuento_global_valor = round(
            subtotal * (porcentaje_descuento / 100), 2
        )
    else:
        descuento_global_valor = 0

    # Base para IVA
    base_iva = round(subtotal - descuento_global_valor, 2)

    # IVA del 15%
    iva = round(base_iva * 0.15, 2) if incluye_iva else 0.00

    # Total final
    total = round(base_iva + iva, 2)

    # Anticipos
    anticipo_1 = round(total * (anticipos["porcentaje_1"] / 100), 2)
    anticipo_2 = round(total * (anticipos["porcentaje_2"] / 100), 2)
    anticipo_3 = round(total - anticipo_1 - anticipo_2, 2)

    return {
        "cliente": datos["cliente"],
        "fecha": datetime.now().strftime("%d/%m/%Y"),
        "incluye_iva": incluye_iva,
        "tipo_descuento": tipo_descuento,
        "porcentaje_descuento": porcentaje_descuento,
        "descuento_global_valor": descuento_global_valor,
        "nota": nota,
        "productos": productos,
        "subtotal": subtotal,
        "iva": iva,
        "total": total,
        "anticipos": {
            "anticipo_1": {
                "porcentaje": anticipos["porcentaje_1"],
                "valor": anticipo_1
            },
            "anticipo_2": {
                "porcentaje": anticipos["porcentaje_2"],
                "valor": anticipo_2
            },
            "anticipo_3": {
                "porcentaje": anticipos["porcentaje_3"],
                "valor": anticipo_3
            }
        }
    }


# ============================================================
# FUNCIÓN 4: Modificar una proforma ya generada
# ============================================================
def modificar_proforma(proforma_actual: dict,
                       instruccion: str) -> dict:
    """Aplica modificaciones a una proforma existente"""

    prompt = f"""
    Tienes esta proforma en formato JSON:
    {json.dumps(proforma_actual, ensure_ascii=False)}

    Aplica exactamente esta modificación: "{instruccion}"

    REGLAS OBLIGATORIAS:
    - Recalcula el total de cada producto modificado
    - Recalcula subtotal, descuento global, IVA y total general
    - Recalcula los 3 anticipos usando los mismos porcentajes
    - Si se elimina un producto, renumera los restantes desde 1
    - Mantén todos los demás campos exactamente igual

    Devuelve ÚNICAMENTE el JSON completo con los cambios aplicados,
    sin texto adicional, sin comillas de bloque.
    """

    # Enviar instrucción a Gemini
    respuesta = client.models.generate_content(
        model=MODELO,
        contents=prompt
    )

    texto = respuesta.text.strip()
    texto = texto.replace("```json", "").replace("```", "").strip()

    return json.loads(texto)


# ============================================================
# FUNCIÓN 5: Generar nombre único del archivo
# ============================================================
def generar_nombre_archivo(nombre_cliente: str) -> str:
    """Genera el nombre del archivo en formato PROFORMAFECHA_CLIENTE"""

    # Fecha actual en formato YYYYMMDD
    fecha = datetime.now().strftime("%Y%m%d")

    # Nombre en mayúsculas sin espacios
    nombre = nombre_cliente.upper().replace(" ", "")

    # Nombre base
    nombre_base = f"PROFORMA{fecha}_{nombre}"

    # Verificar si ya existe y agregar _2, _3...
    contador = 1
    nombre_final = nombre_base

    while (os.path.exists(f"proformas/{nombre_final}.xlsx") or
           os.path.exists(f"proformas/{nombre_final}.pdf")):
        contador += 1
        nombre_final = f"{nombre_base}_{contador}"

    return nombre_final