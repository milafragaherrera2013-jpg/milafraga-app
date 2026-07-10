# app.py
# Aplicacion de gestion de pedidos - Mila Fraga / Artabria
import csv
import io
import json
import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session, Response

from invoice import generar_factura, generar_etiqueta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "pedidos.db")

with open(os.path.join(BASE_DIR, "config.json"), encoding="utf-8") as f:
    CONFIG = json.load(f)

with open(os.path.join(BASE_DIR, "catalog.json"), encoding="utf-8") as f:
    CATALOGO = json.load(f)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mila-fraga-clave-local-cambiar-si-se-publica")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            cliente TEXT NOT NULL,
            telefono_cliente TEXT,
            direccion_cliente TEXT,
            items TEXT NOT NULL,
            total REAL NOT NULL,
            notas TEXT,
            estado TEXT NOT NULL DEFAULT 'Nuevo'
        )
    """)
    conn.commit()
    # Migración: añadir columna de gastos de envío si no existe todavía
    try:
        conn.execute("ALTER TABLE pedidos ADD COLUMN gastos_envio REAL DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # la columna ya existía
    # Migración: añadir columna de método de pago si no existe todavía
    try:
        conn.execute("ALTER TABLE pedidos ADD COLUMN metodo_pago TEXT DEFAULT 'No especificado'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # la columna ya existía
    # Migración: añadir columna de email del cliente si no existe todavía
    try:
        conn.execute("ALTER TABLE pedidos ADD COLUMN email_cliente TEXT DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # la columna ya existía
    # Migración: añadir columna de código de descuento/referido si no existe todavía
    try:
        conn.execute("ALTER TABLE pedidos ADD COLUMN codigo_descuento TEXT DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # la columna ya existía
    conn.close()


UMBRAL_ENVIO_GRATIS = 50.0
COSTE_ENVIO = 3.0


# Crear la base de datos ya al importar el módulo (necesario para gunicorn en producción)
init_db()


def todos_los_productos():
    """Aplana el catálogo completo en una sola lista para el formulario.
    Orden: primero promociones/edición limitada, luego el resto."""
    items = []
    for p in CATALOGO["edicion_limitada"]:
        items.append({**p, "grupo": "🔥 Promociones y edición limitada"})
    for p in CATALOGO["combos_permanentes"]:
        items.append({**p, "grupo": "Combos"})
    for p in CATALOGO["productos"]:
        items.append({**p, "grupo": "Productos individuales"})
    for p in CATALOGO["packs_duo"]:
        items.append({**p, "grupo": "Packs Duo (2 unidades)"})
    for p in CATALOGO["packs_trio"]:
        items.append({**p, "grupo": "Packs Trío (3 unidades)"})
    for p in CATALOGO["packs_5"]:
        items.append({**p, "grupo": "Packs de 5 unidades"})
    return items


# ---------------------------------------------------------------------------
# AGRUPACIÓN POR INGREDIENTE (desplegables del catálogo público)
# ---------------------------------------------------------------------------
CATEGORIAS_INGREDIENTE = [
    ("Café 5.0", "cafe", "☕"),
    ("Bebida Inteligente", "id", "🍵"),
    ("ChocoSlender", "choco", "🍫"),
    ("Elixir de Juventud", "elixir", "✨"),
    ("Caña Zero", "cania", "🍯"),
]


def _pertenece(item_id, keyword):
    """Comprueba si el id del producto contiene ese ingrediente
    (ej. 'duo_cafe_id' pertenece a 'cafe' y a 'id')."""
    return any(seg == keyword or seg.startswith(keyword) for seg in item_id.split("_"))


def productos_por_ingrediente():
    """Agrupa cada individual + todos los packs que lo incluyen, bajo su ingrediente."""
    base = []
    for p in CATALOGO["productos"]:
        base.append(p)
    for p in CATALOGO["packs_duo"]:
        base.append(p)
    for p in CATALOGO["packs_trio"]:
        base.append(p)
    for p in CATALOGO["packs_5"]:
        base.append(p)

    categorias = []
    for nombre, keyword, icono in CATEGORIAS_INGREDIENTE:
        productos = [p for p in base if _pertenece(p["id"], keyword)]
        categorias.append({"nombre": nombre, "icono": icono, "productos": productos})
    return categorias


# ---------------------------------------------------------------------------
# PROTECCIÓN CON CONTRASEÑA (solo para el panel de Mila, no para el catálogo)
# ---------------------------------------------------------------------------
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "cambiaesto")


def login_requerido(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        if not session.get("autenticado"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorada


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["autenticado"] = True
            destino = request.args.get("next") or url_for("index")
            return redirect(destino)
        else:
            error = "Contraseña incorrecta, inténtalo de nuevo."
    return render_template("login.html", error=error, negocio=CONFIG["negocio"])


@app.route("/logout")
def logout():
    session.pop("autenticado", None)
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# PANEL DE PEDIDOS (para Mila) — ahora vive en /panel, no en la raíz
# ---------------------------------------------------------------------------
@app.route("/panel")
@login_requerido
def index():
    conn = get_db()
    filtro_estado = request.args.get("estado", "")
    if filtro_estado:
        rows = conn.execute(
            "SELECT * FROM pedidos WHERE estado = ? ORDER BY id DESC", (filtro_estado,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM pedidos ORDER BY id DESC").fetchall()
    conn.close()

    pedidos = []
    total_ventas = 0
    ventas_por_producto = {}
    for r in rows:
        pedido = dict(r)
        pedido["productos"] = json.loads(pedido.pop("items"))
        pedidos.append(pedido)
        total_ventas += pedido["total"]
        for item in pedido["productos"]:
            ventas_por_producto[item["nombre"]] = ventas_por_producto.get(item["nombre"], 0) + item["cantidad"]

    producto_mas_vendido = None
    unidades_mas_vendido = 0
    if ventas_por_producto:
        producto_mas_vendido = max(ventas_por_producto, key=ventas_por_producto.get)
        unidades_mas_vendido = ventas_por_producto[producto_mas_vendido]

    return render_template(
        "index.html",
        pedidos=pedidos,
        total_ventas=total_ventas,
        num_pedidos=len(pedidos),
        negocio=CONFIG["negocio"],
        filtro_estado=filtro_estado,
        producto_mas_vendido=producto_mas_vendido,
        unidades_mas_vendido=unidades_mas_vendido,
    )


@app.route("/panel/exportar")
@login_requerido
def exportar_pedidos():
    conn = get_db()
    rows = conn.execute("SELECT * FROM pedidos ORDER BY id ASC").fetchall()
    conn.close()

    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow([
        "Nº Pedido", "Fecha", "Cliente", "Teléfono", "Email", "Dirección",
        "Productos", "Total", "Gastos Envío", "Método Pago", "Código Descuento",
        "Notas", "Estado",
    ])
    for r in rows:
        pedido = dict(r)
        items = json.loads(pedido["items"])
        productos_texto = "; ".join(f"{i['cantidad']}x {i['nombre']}" for i in items)
        escritor.writerow([
            pedido["id"],
            pedido["fecha"],
            pedido["cliente"],
            pedido.get("telefono_cliente", ""),
            pedido.get("email_cliente", ""),
            pedido.get("direccion_cliente", ""),
            productos_texto,
            pedido["total"],
            pedido.get("gastos_envio", 0),
            pedido.get("metodo_pago", ""),
            pedido.get("codigo_descuento", ""),
            pedido.get("notas", ""),
            pedido["estado"],
        ])

    nombre_archivo = f"pedidos_milafraga_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        "\ufeff" + salida.getvalue(),  # BOM para que Excel muestre bien los acentos
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"},
    )


@app.route("/pedido/<int:pedido_id>/estado", methods=["POST"])
@login_requerido
def cambiar_estado(pedido_id):
    nuevo_estado = request.form.get("estado")
    conn = get_db()
    conn.execute("UPDATE pedidos SET estado = ? WHERE id = ?", (nuevo_estado, pedido_id))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.route("/pedido/<int:pedido_id>/eliminar", methods=["POST"])
@login_requerido
def eliminar_pedido(pedido_id):
    conn = get_db()
    conn.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.route("/pedido/<int:pedido_id>/factura")
@login_requerido
def descargar_factura(pedido_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    conn.close()
    if row is None:
        return "Pedido no encontrado", 404

    pedido = dict(row)
    pedido["items"] = json.loads(pedido["items"])

    carpeta = os.path.join(BASE_DIR, "static", "facturas")
    ruta_pdf = generar_factura(pedido, carpeta)
    return send_file(ruta_pdf, as_attachment=True)


@app.route("/pedido/<int:pedido_id>/etiqueta")
@login_requerido
def descargar_etiqueta(pedido_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    conn.close()
    if row is None:
        return "Pedido no encontrado", 404

    pedido = dict(row)
    pedido["items"] = json.loads(pedido["items"])

    carpeta = os.path.join(BASE_DIR, "static", "etiquetas")
    ruta_pdf = generar_etiqueta(pedido, carpeta)
    return send_file(ruta_pdf, as_attachment=True)


# ---------------------------------------------------------------------------
# CATALOGO / FORMULARIO (para clientas) — ahora vive en la raíz "/"
# ---------------------------------------------------------------------------
ANCLAS_GRUPOS = {
    "🔥 Promociones y edición limitada": "promos",
    "Productos individuales": "individuales",
    "Combos": "combos",
}


@app.route("/", methods=["GET"])
def formulario():
    promos = CATALOGO["edicion_limitada"]
    combos = CATALOGO["combos_permanentes"]
    categorias = productos_por_ingrediente()

    return render_template(
        "formulario.html",
        promos=promos,
        combos=combos,
        categorias=categorias,
        negocio=CONFIG["negocio"],
        cobro=CONFIG["cobro"],
    )


@app.route("/", methods=["POST"])
def crear_pedido():
    items_catalogo = {i["id"]: i for i in todos_los_productos()}

    cliente = request.form.get("cliente", "").strip()
    telefono_cliente = request.form.get("telefono_cliente", "").strip()
    email_cliente = request.form.get("email_cliente", "").strip()
    direccion_cliente = request.form.get("direccion_cliente", "").strip()
    notas = request.form.get("notas", "").strip()
    metodo_pago = request.form.get("metodo_pago", "No especificado").strip()
    codigo_descuento = request.form.get("codigo_descuento", "").strip().upper()

    items_pedido = []
    total = 0
    for key, value in request.form.items():
        if key.startswith("cantidad_") and value and int(value) > 0:
            prod_id = key.replace("cantidad_", "")
            if prod_id in items_catalogo:
                cantidad = int(value)
                producto = items_catalogo[prod_id]
                subtotal = cantidad * producto["precio"]
                total += subtotal
                items_pedido.append({
                    "nombre": producto["nombre"],
                    "cantidad": cantidad,
                    "precio_unitario": producto["precio"],
                })

    if not cliente or not items_pedido:
        flash("Falta el nombre de la clienta o no se ha seleccionado ningún producto.")
        return redirect(url_for("formulario"))

    envio_base = 0.0 if total >= UMBRAL_ENVIO_GRATIS else COSTE_ENVIO
    recargo_contrareembolso = COSTE_ENVIO if metodo_pago == "Contrareembolso" else 0.0
    gastos_envio = envio_base + recargo_contrareembolso
    total_con_envio = total + gastos_envio

    conn = get_db()
    conn.execute(
        """INSERT INTO pedidos (fecha, cliente, telefono_cliente, direccion_cliente,
                                 items, total, notas, estado, gastos_envio, metodo_pago,
                                 email_cliente, codigo_descuento)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            cliente,
            telefono_cliente,
            direccion_cliente,
            json.dumps(items_pedido, ensure_ascii=False),
            total_con_envio,
            notas,
            "Nuevo",
            gastos_envio,
            metodo_pago,
            email_cliente,
            codigo_descuento,
        ),
    )
    conn.commit()
    pedido_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    return redirect(url_for("confirmacion", pedido_id=pedido_id))


@app.route("/confirmacion/<int:pedido_id>")
def confirmacion(pedido_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    conn.close()
    if row is None:
        return "Pedido no encontrado", 404
    pedido = dict(row)
    pedido["productos"] = json.loads(pedido.pop("items"))
    return render_template(
        "confirmacion.html", pedido=pedido, negocio=CONFIG["negocio"], cobro=CONFIG["cobro"]
    )


if __name__ == "__main__":
    init_db()
    puerto = int(os.environ.get("PORT", 5000))
    modo_debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=modo_debug, host="0.0.0.0", port=puerto)
