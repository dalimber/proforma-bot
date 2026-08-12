# ============================================================
# pdf_service.py
# Servicio para generar el archivo PDF de la proforma
# ============================================================

from fpdf import FPDF  # Librería para crear documentos PDF
import os              # Para manejar rutas y verificar archivos

# Carpeta donde se guardarán los PDFs generados
OUTPUT_DIR = "proformas"


# ============================================================
# FUNCIONES DE FORMATO
# ============================================================

def formato_moneda(valor: float) -> str:
    """
    Convierte un número a texto con formato de dinero
    Ejemplo: 1250.5 → "$ 1,250.50"
    """
    return f"$ {valor:,.2f}"


def formato_porcentaje(valor: float) -> str:
    """
    Convierte un número a texto con formato de porcentaje
    Ejemplo: 15 → "15%"
    """
    return f"{valor:.0f}%"


# ============================================================
# CLASE PERSONALIZADA DEL PDF
# ============================================================

class ProformaPDF(FPDF):
    """
    Extiende la clase FPDF para personalizar el comportamiento
    del PDF. Se desactivan el encabezado y pie automáticos
    porque los manejamos manualmente en el código.
    """

    def header(self):
        """Sin encabezado automático en cada página"""
        pass

    def footer(self):
        """Sin pie de página automático en cada página"""
        pass


# ============================================================
# FUNCIÓN PRINCIPAL: Generar el PDF
# ============================================================

def generar_pdf(proforma: dict, nombre_archivo: str,
                tipo_descuento: str = "ninguno",
                porcentaje_descuento: float = 0) -> str:
    """
    Genera el archivo PDF completo de la proforma.

    Args:
        proforma: Diccionario con todos los datos calculados
        nombre_archivo: Nombre del archivo sin extensión
        tipo_descuento: 'ninguno', 'individual' o 'global'
        porcentaje_descuento: Porcentaje de descuento (ej: 5)

    Returns:
        Ruta completa del PDF generado
    """

    # Crea una instancia del PDF en formato A4 vertical
    # P = Portrait (vertical), mm = milímetros, A4 = tamaño estándar
    pdf = ProformaPDF(orientation='P', unit='mm', format='A4')

    # Agrega la primera página al documento
    pdf.add_page()

    # Configura salto de página automático con margen inferior de 15mm
    pdf.set_auto_page_break(auto=True, margin=15)

    # =========================================================
    # SECCIÓN 1: BANNER DE LA EMPRESA
    # =========================================================

    # Ruta del banner de la empresa (debe estar en la carpeta AppProforma)
    banner_path = "banner.png"

    if os.path.exists(banner_path):
        # Si existe el banner lo agrega en la parte superior de la página
        # x=10 y=10 = posición desde el margen, w=190 = ancho completo
        pdf.image(banner_path, x=10, y=10, w=190)
        # Mueve el cursor debajo del banner para seguir escribiendo
        pdf.set_y(65)
    else:
        # Si no hay banner, empieza desde el margen superior
        pdf.set_y(15)

    # =========================================================
    # SECCIÓN 2: TÍTULO PROFORMA
    # =========================================================

    pdf.set_font("Helvetica", style="B", size=16)  # Fuente grande y negrita
    pdf.set_fill_color(30, 30, 30)                 # Fondo casi negro
    pdf.set_text_color(255, 255, 255)              # Texto blanco
    # Celda que ocupa todo el ancho (190mm) con el título centrado
    pdf.cell(190, 10, "PROFORMA", border=0, align="C", fill=True)
    pdf.ln(12)  # Espacio de 12mm después del título

    # =========================================================
    # SECCIÓN 3: DATOS DEL CLIENTE
    # =========================================================

    pdf.set_text_color(0, 0, 0)       # Vuelve al texto negro
    cliente = proforma["cliente"]      # Extrae datos del cliente del diccionario
    fecha   = proforma["fecha"]        # Extrae la fecha de la proforma

    # --- Fila: Cliente y Fecha ---
    pdf.set_font("Helvetica", style="B", size=9)   # Negrita para etiqueta
    pdf.cell(25, 7, "CLIENTE:", border=0)           # Etiqueta
    pdf.set_font("Helvetica", size=9)
    pdf.cell(95, 7, cliente["nombre"], border=0)    # Valor: nombre del cliente
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.cell(20, 7, "FECHA:", border=0)             # Etiqueta
    pdf.set_font("Helvetica", size=9)
    pdf.cell(50, 7, fecha, border=0)                # Valor: fecha
    pdf.ln()  # Salto de línea

    # --- Fila: Dirección / Lugar ---
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.cell(25, 7, "DIRECCIÓN:", border=0)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(165, 7, cliente["lugar"], border=0)    # Valor: lugar
    pdf.ln()

    # --- Fila: Nombre de la Obra ---
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.cell(25, 7, "OBRA:", border=0)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(165, 7, cliente["obra"], border=0)     # Valor: obra
    pdf.ln(10)  # Espacio antes de la tabla

    # =========================================================
    # SECCIÓN 4: TABLA DE PRODUCTOS
    # =========================================================

    productos = proforma["productos"]  # Lista de productos de la proforma

    # --- Definir anchos de columnas según tipo de descuento ---
    # El ancho total siempre suma 190mm (ancho útil del A4)

    if tipo_descuento == "individual":
        # Con columna de descuento individual visible
        col_num    = 10  # Columna: Número
        col_prod   = 28  # Columna: Producto
        col_desc   = 33  # Columna: Descripción
        col_desc2  = 22  # Columna: Descripción adicional
        col_cant   = 17  # Columna: Cantidad
        col_precio = 22  # Columna: Precio
        col_desc_i = 22  # Columna: Descuento individual
        col_total  = 36  # Columna: Total
    else:
        # Sin columna de descuento individual
        col_num    = 10  # Columna: Número
        col_prod   = 33  # Columna: Producto
        col_desc   = 40  # Columna: Descripción
        col_desc2  = 27  # Columna: Descripción adicional
        col_cant   = 20  # Columna: Cantidad
        col_precio = 25  # Columna: Precio
        col_desc_i = 0   # No se usa
        col_total  = 35  # Columna: Total

    # --- Encabezados de la tabla ---
    pdf.set_font("Helvetica", style="B", size=8)   # Negrita para encabezados
    pdf.set_fill_color(50, 50, 50)                 # Fondo gris oscuro
    pdf.set_text_color(255, 255, 255)              # Texto blanco

    pdf.cell(col_num,    7, "Nº",           border=1, align="C", fill=True)
    pdf.cell(col_prod,   7, "PRODUCTO",     border=1, align="C", fill=True)
    pdf.cell(col_desc,   7, "DESCRIPCIÓN",  border=1, align="C", fill=True)
    pdf.cell(col_desc2,  7, "DESC. ADIC.",  border=1, align="C", fill=True)
    pdf.cell(col_cant,   7, "CANTIDAD",     border=1, align="C", fill=True)
    pdf.cell(col_precio, 7, "PRECIO",       border=1, align="C", fill=True)

    if tipo_descuento == "individual":
        # Muestra el % en el encabezado de descuento
        label_desc = f"DESC. {porcentaje_descuento:.0f}%"
        pdf.cell(col_desc_i, 7, label_desc, border=1, align="C", fill=True)

    pdf.cell(col_total, 7, "TOTAL", border=1, align="C", fill=True)
    pdf.ln()  # Salto de línea después de los encabezados

    # --- Filas de cada producto ---
    pdf.set_text_color(0, 0, 0)  # Texto negro para los datos

    for i, prod in enumerate(productos):

        # Alternar color de fondo entre filas para facilitar la lectura
        if i % 2 == 0:
            pdf.set_fill_color(245, 245, 245)  # Gris muy claro (filas pares)
        else:
            pdf.set_fill_color(255, 255, 255)  # Blanco (filas impares)

        pdf.set_font("Helvetica", size=8)  # Fuente normal para los datos

        # Número consecutivo del producto
        pdf.cell(col_num, 7,
                 str(prod["numero"]),
                 border=1, align="C", fill=True)

        # Nombre del producto (máx. 25 caracteres para que no se desborde)
        pdf.cell(col_prod, 7,
                 str(prod["producto"])[:25],
                 border=1, align="L", fill=True)

        # Descripción principal (máx. 30 caracteres)
        pdf.cell(col_desc, 7,
                 str(prod["descripcion"])[:30],
                 border=1, align="L", fill=True)

        # Descripción adicional (máx. 20 caracteres)
        pdf.cell(col_desc2, 7,
                 str(prod.get("descripcion_adicional", "-"))[:20],
                 border=1, align="L", fill=True)

        # Cantidad del producto
        pdf.cell(col_cant, 7,
                 str(prod["cantidad"]),
                 border=1, align="C", fill=True)

        # Precio unitario en formato moneda
        pdf.cell(col_precio, 7,
                 formato_moneda(prod["precio_unitario"]),
                 border=1, align="R", fill=True)

        # Descuento individual en $ (solo si el tipo es "individual")
        if tipo_descuento == "individual":
            desc_valor = prod.get("descuento_valor", 0)
            pdf.cell(col_desc_i, 7,
                     formato_moneda(desc_valor),
                     border=1, align="R", fill=True)

        # Total del producto en formato moneda
        pdf.cell(col_total, 7,
                 formato_moneda(prod["total"]),
                 border=1, align="R", fill=True)

        pdf.ln()  # Salto de línea después de cada producto

    pdf.ln(4)  # Espacio entre la tabla y los totales

    # =========================================================
    # SECCIÓN 5: TOTALES (Subtotal, Descuento, IVA, Total)
    # =========================================================

    # Anchos de las celdas de totales
    ancho_etiqueta = 55  # Ancho de la columna de etiqueta
    ancho_valor    = 35  # Ancho de la columna de valor

    # Calcula la posición X para que los totales queden a la derecha
    # 10mm de margen + espacio disponible - ancho total de los totales
    x_totales = 10 + (190 - ancho_etiqueta - ancho_valor)

    # --- Fila SUBTOTAL ---
    pdf.set_x(x_totales)                          # Mueve el cursor a la derecha
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.set_fill_color(220, 220, 220)              # Fondo gris claro
    pdf.set_text_color(0, 0, 0)                    # Texto negro
    pdf.cell(ancho_etiqueta, 7, "SUBTOTAL:",
             border=1, align="R", fill=True)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(ancho_valor, 7,
             formato_moneda(proforma["subtotal"]),
             border=1, align="R", fill=True)
    pdf.ln()

    # --- Fila DESCUENTO GLOBAL (solo si aplica) ---
    if tipo_descuento == "global":
        pdf.set_x(x_totales)
        pdf.set_font("Helvetica", style="B", size=9)
        pdf.set_fill_color(220, 220, 220)
        # Etiqueta con el porcentaje de descuento global
        label_global = f"DESCUENTO GLOBAL ({porcentaje_descuento:.0f}%):"
        pdf.cell(ancho_etiqueta, 7, label_global,
                 border=1, align="R", fill=True)
        pdf.set_font("Helvetica", size=9)
        pdf.cell(ancho_valor, 7,
                 formato_moneda(proforma["descuento_global_valor"]),
                 border=1, align="R", fill=True)
        pdf.ln()

    # --- Fila IVA ---
    pdf.set_x(x_totales)
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.set_fill_color(220, 220, 220)
    # Etiqueta del IVA según si aplica o no
    iva_label = "I.V.A. 15%:" if proforma["incluye_iva"] else "I.V.A. 0%:"
    pdf.cell(ancho_etiqueta, 7, iva_label,
             border=1, align="R", fill=True)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(ancho_valor, 7,
             formato_moneda(proforma["iva"]),
             border=1, align="R", fill=True)
    pdf.ln()

    # --- Fila TOTAL FINAL ---
    pdf.set_x(x_totales)
    pdf.set_font("Helvetica", style="B", size=10) # Fuente más grande para el total
    pdf.set_fill_color(30, 30, 30)                # Fondo oscuro
    pdf.set_text_color(255, 255, 255)             # Texto blanco
    pdf.cell(ancho_etiqueta, 8, "TOTAL:",
             border=1, align="R", fill=True)
    pdf.cell(ancho_valor, 8,
             formato_moneda(proforma["total"]),
             border=1, align="R", fill=True)
    pdf.ln(10)  # Espacio después del total

    # =========================================================
    # SECCIÓN 6: NOTA O CONDICIÓN ESPECIAL
    # =========================================================

    pdf.set_text_color(0, 0, 0)  # Texto negro

    # Solo agrega la sección de nota si existe y no está vacía
    if proforma.get("nota") and proforma["nota"].strip():
        pdf.set_font("Helvetica", style="B", size=9)
        pdf.cell(25, 7, "NOTA:", border=0)         # Etiqueta de nota
        pdf.set_font("Helvetica", size=9)
        # multi_cell permite texto que ocupa varias líneas automáticamente
        pdf.multi_cell(165, 7, proforma["nota"], border=0)
        pdf.ln(3)  # Pequeño espacio después de la nota

    # =========================================================
    # SECCIÓN 7: TABLA DE ANTICIPOS / FORMA DE PAGO
    # =========================================================

    anticipos = proforma["anticipos"]  # Datos de los 3 anticipos

    # --- Encabezado principal de la tabla ---
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.set_fill_color(50, 50, 50)                 # Fondo gris oscuro
    pdf.set_text_color(255, 255, 255)              # Texto blanco
    # Encabezado que abarca todo el ancho
    pdf.cell(190, 7, "FORMA DE PAGO",
             border=1, align="C", fill=True)
    pdf.ln()

    # --- Sub-encabezados de columnas ---
    pdf.set_font("Helvetica", style="B", size=8)
    pdf.cell(100, 7, "ANTICIPO", border=1, align="C", fill=True)
    pdf.cell(45,  7, "VALOR",   border=1, align="C", fill=True)
    pdf.cell(45,  7, "PAGADO",  border=1, align="C", fill=True)
    pdf.ln()

    # --- Fila Anticipo 1 ---
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", size=8)
    pdf.set_fill_color(245, 245, 245)  # Gris muy claro
    pct1 = anticipos['anticipo_1']['porcentaje']  # Porcentaje del anticipo 1
    pdf.cell(100, 7,
             f"1. Anticipo al contratar ({pct1}%)",
             border=1, align="L", fill=True)
    pdf.cell(45, 7,
             formato_moneda(anticipos["anticipo_1"]["valor"]),
             border=1, align="R", fill=True)
    pdf.cell(45, 7, "$ 0.00",          # Espacio para registrar pagos realizados
             border=1, align="R", fill=True)
    pdf.ln()

    # --- Fila Anticipo 2 ---
    pdf.set_fill_color(255, 255, 255)  # Blanco
    pct2 = anticipos['anticipo_2']['porcentaje']  # Porcentaje del anticipo 2
    pdf.cell(100, 7,
             f"2. Segundo anticipo ({pct2}%)",
             border=1, align="L", fill=True)
    pdf.cell(45, 7,
             formato_moneda(anticipos["anticipo_2"]["valor"]),
             border=1, align="R", fill=True)
    pdf.cell(45, 7, "$ 0.00",
             border=1, align="R", fill=True)
    pdf.ln()

    # --- Fila Anticipo 3 ---
    pdf.set_fill_color(245, 245, 245)
    pct3 = anticipos['anticipo_3']['porcentaje']  # Porcentaje del anticipo 3
    pdf.cell(100, 7,
             f"3. Pago final ({pct3}%)",
             border=1, align="L", fill=True)
    pdf.cell(45, 7,
             formato_moneda(anticipos["anticipo_3"]["valor"]),
             border=1, align="R", fill=True)
    pdf.cell(45, 7, "$ 0.00",
             border=1, align="R", fill=True)
    pdf.ln()

    # --- Fila TOTAL PROYECTO y SALDO A PAGAR ---
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.set_fill_color(30, 30, 30)                 # Fondo oscuro
    pdf.set_text_color(255, 255, 255)              # Texto blanco
    pdf.cell(100, 8, "TOTAL PROYECTO",
             border=1, align="L", fill=True)
    # Valor del total del proyecto
    pdf.cell(45, 8,
             formato_moneda(proforma["total"]),
             border=1, align="R", fill=True)
    # Saldo a pagar (por defecto igual al total, se actualiza si hay pagos)
    pdf.cell(45, 8,
             f"SALDO: {formato_moneda(proforma['total'])}",
             border=1, align="R", fill=True)
    pdf.ln()

  # =========================================================
    # SECCIÓN 8: IMAGEN DEL PIE DE PÁGINA
    # =========================================================

    # Ruta de la imagen del pie de página de la empresa
    footer_path = "footer.png"

    if os.path.exists(footer_path):
        # Obtiene la altura de la imagen del footer para posicionarla
        # desde el fondo de la página
        # Una página A4 tiene 297mm de alto
        # Dejamos 15mm de margen inferior
        # Asumimos que el footer tiene ~25mm de alto
        alto_footer = 25
        pos_y_footer = 297 - 15 - alto_footer

        # Posiciona el cursor en la parte inferior de la página
        pdf.set_y(pos_y_footer)

        # Agrega la imagen del pie de página centrada en la parte inferior
        # x=10 = margen izquierdo, w=190 = ancho completo útil
        pdf.image(footer_path, x=10, y=pos_y_footer, w=190)

    # =========================================================
    # GUARDAR EL ARCHIVO PDF
    # =========================================================

    # Construye la ruta completa del archivo
    ruta_pdf = f"{OUTPUT_DIR}/{nombre_archivo}.pdf"

    # Guarda el PDF en la carpeta proformas
    pdf.output(ruta_pdf)

    # Retorna la ruta del archivo para que WhatsApp pueda enviarlo
    return ruta_pdf