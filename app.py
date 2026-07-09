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
