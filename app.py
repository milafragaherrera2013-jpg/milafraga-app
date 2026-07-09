# app.py
# Aplicacion de gestion de pedidos - Mila Fraga / Artabria
import json
import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session

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
    conn.close()


# Crear la base de datos ya al importar el módulo (necesario para gunicorn en producción)
init_db()


def todos_los_productos():
    """Aplana el catálogo completo en una sola lista para el formulario."""
    items = []
    for p in CATALOGO["productos"]:
        items.append({**p, "grupo": "Productos individuales"})
    for p in CATALOGO["packs_duo"]:
        items.append({**p, "grupo": "Packs Duo (2 unidades)"})
    for p in CATALOGO["packs_trio"]:
        items.append({**p, "grupo": "Packs Trío (3 unidades)"})
    for p in CATALOGO["packs_5"]:
        items.append({**p, "grupo": "Packs de 5 unidades"})
    for p in CATALOGO["combos_permanentes"]:
        items.append({**p, "grupo": "Combos"})
    for p in CATALOGO["edicion_limitada"]:
        items.append({**p, "grupo": "Edición limitada"})
    return items


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
    for r in rows:
        pedido = dict(r)
        pedido["productos"] = json.loads(pedido.pop("items"))
        pedidos.append(pedido)
        total_ventas += pedido["total"]

    return render_template(
        "index.html",
        pedidos=pedidos,
        total_ventas=total_ventas,
        num_pedidos=len(pedidos),
        negocio=CONFIG["negocio"],
        filtro_estado=filtro_estado,
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
@app.route("/", methods=["GET"])
def formulario():
    items = todos_los_productos()
    grupos = []
    vistos = []
    for it in items:
        if it["grupo"] not in vistos:
            vistos.append(it["grupo"])
    for g in vistos:
        grupos.append({"nombre": g, "productos": [i for i in items if i["grupo"] == g]})

    return render_template(
        "formulario.html",
        grupos=grupos,
        negocio=CONFIG["negocio"],
        cobro=CONFIG["cobro"],
    )


@app.route("/", methods=["POST"])
def crear_pedido():
    items_catalogo = {i["id"]: i for i in todos_los_productos()}

    cliente = request.form.get("cliente", "").strip()
    telefono_cliente = request.form.get("telefono_cliente", "").strip()
    direccion_cliente = request.form.get("direccion_cliente", "").strip()
    notas = request.form.get("notas", "").strip()

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

    conn = get_db()
    conn.execute(
        """INSERT INTO pedidos (fecha, cliente, telefono_cliente, direccion_cliente,
                                 items, total, notas, estado)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            cliente,
            telefono_cliente,
            direccion_cliente,
            json.dumps(items_pedido, ensure_ascii=False),
            total,
            notas,
            "Nuevo",
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
