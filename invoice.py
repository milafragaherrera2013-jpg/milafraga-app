# invoice.py
# Genera facturas en PDF para los pedidos, usando los datos de config.json
import json
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas

with open(os.path.join(os.path.dirname(__file__), "config.json"), encoding="utf-8") as f:
    CONFIG = json.load(f)

AQUA = colors.HexColor(CONFIG["marca_visual"]["color_aqua"])
LILA = colors.HexColor(CONFIG["marca_visual"]["color_lila"])
TEXTO = colors.HexColor(CONFIG["marca_visual"]["color_texto"])


def generar_factura(pedido, carpeta_destino):
    """
    pedido: dict con keys: id, fecha, cliente, telefono, direccion, items (lista de dicts
            con nombre, cantidad, precio_unitario), total, notas
    carpeta_destino: ruta local donde guardar el PDF
    Devuelve la ruta del PDF generado.
    """
    os.makedirs(carpeta_destino, exist_ok=True)
    numero_factura = f"MF-{pedido['id']:05d}"
    nombre_archivo = f"Factura_{numero_factura}.pdf"
    ruta_pdf = os.path.join(carpeta_destino, nombre_archivo)

    c = canvas.Canvas(ruta_pdf, pagesize=A4)
    ancho, alto = A4

    # Logo
    logo_path = os.path.join(os.path.dirname(__file__), CONFIG["rutas"]["logo_factura"])
    if os.path.exists(logo_path):
        try:
            c.drawImage(logo_path, ancho - 60 * mm, alto - 45 * mm, width=45 * mm, height=35 * mm,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # Cabecera negocio
    negocio = CONFIG["negocio"]
    cobro = CONFIG["cobro"]

    y = alto - 25 * mm
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(TEXTO)
    c.drawString(20 * mm, y, negocio["marca"])
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, y, negocio["nombre_completo"])
    y -= 4.5 * mm
    c.drawString(20 * mm, y, f"NIF: {negocio['nif']}")
    y -= 4.5 * mm
    c.drawString(20 * mm, y, negocio["direccion_calle"])
    y -= 4.5 * mm
    c.drawString(20 * mm, y, negocio["direccion_cp_ciudad"])
    y -= 4.5 * mm
    c.drawString(20 * mm, y, f"Tel/WhatsApp: {negocio['telefono']}")

    # Datos factura
    y -= 12 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, f"Factura Nº {numero_factura}")
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    fecha = pedido.get("fecha", datetime.now().strftime("%d/%m/%Y"))
    c.drawString(20 * mm, y, f"Fecha: {fecha}")

    # Datos cliente
    y -= 10 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, "Cliente")
    y -= 5 * mm
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, y, pedido.get("cliente", ""))
    if pedido.get("telefono_cliente"):
        y -= 4.5 * mm
        c.drawString(20 * mm, y, f"Tel: {pedido['telefono_cliente']}")
    if pedido.get("direccion_cliente"):
        y -= 4.5 * mm
        c.drawString(20 * mm, y, pedido["direccion_cliente"])

    # Tabla de productos
    y -= 12 * mm
    c.setFillColor(AQUA)
    c.rect(20 * mm, y - 2 * mm, ancho - 40 * mm, 7 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(22 * mm, y, "Producto")
    c.drawString(120 * mm, y, "Cant.")
    c.drawString(140 * mm, y, "Precio")
    c.drawString(165 * mm, y, "Subtotal")

    y -= 9 * mm
    c.setFillColor(TEXTO)
    c.setFont("Helvetica", 9)
    total = 0
    for item in pedido.get("items", []):
        subtotal = item["cantidad"] * item["precio_unitario"]
        total += subtotal
        c.drawString(22 * mm, y, item["nombre"][:45])
        c.drawString(120 * mm, y, str(item["cantidad"]))
        c.drawString(140 * mm, y, f"{item['precio_unitario']:.2f} EUR")
        c.drawString(165 * mm, y, f"{subtotal:.2f} EUR")
        y -= 6 * mm
        if y < 60 * mm:
            c.showPage()
            y = alto - 25 * mm

    # Total
    y -= 4 * mm
    c.setFillColor(LILA)
    c.rect(120 * mm, y - 2 * mm, ancho - 140 * mm, 8 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(125 * mm, y, f"TOTAL: {total:.2f} EUR")

    # Forma de pago
    y -= 18 * mm
    c.setFillColor(TEXTO)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, "Forma de pago")
    y -= 5 * mm
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, y, f"Bizum: {cobro['bizum']}")
    y -= 4.5 * mm
    c.drawString(20 * mm, y, f"WhatsApp: {cobro['whatsapp']}")
    y -= 4.5 * mm
    c.drawString(20 * mm, y, f"Transferencia - IBAN: {cobro['iban_mostrar']}")
    y -= 4.5 * mm
    c.drawString(20 * mm, y, f"Titular: {cobro['titular_cuenta']}")

    if pedido.get("notas"):
        y -= 10 * mm
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(20 * mm, y, f"Notas: {pedido['notas']}")

    c.save()
    return ruta_pdf


def generar_etiqueta(pedido, carpeta_destino):
    """
    Genera una etiqueta de envío sencilla (tamaño mitad de A4) con los datos
    del cliente y el número de pedido.
    """
    os.makedirs(carpeta_destino, exist_ok=True)
    numero = f"MF-{pedido['id']:05d}"
    ruta_pdf = os.path.join(carpeta_destino, f"Etiqueta_{numero}.pdf")

    ancho, alto = 148 * mm, 105 * mm  # tamaño A6 aprox
    c = canvas.Canvas(ruta_pdf, pagesize=(ancho, alto))

    c.setFillColor(AQUA)
    c.rect(0, alto - 18 * mm, ancho, 18 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(8 * mm, alto - 12 * mm, CONFIG["negocio"]["marca"])

    c.setFillColor(TEXTO)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(8 * mm, alto - 28 * mm, "Enviar a:")
    c.setFont("Helvetica", 11)
    c.drawString(8 * mm, alto - 36 * mm, pedido.get("cliente", ""))
    if pedido.get("direccion_cliente"):
        c.drawString(8 * mm, alto - 43 * mm, pedido["direccion_cliente"])
    if pedido.get("telefono_cliente"):
        c.drawString(8 * mm, alto - 50 * mm, f"Tel: {pedido['telefono_cliente']}")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(8 * mm, 10 * mm, f"Pedido: {numero}")

    c.save()
    return ruta_pdf
