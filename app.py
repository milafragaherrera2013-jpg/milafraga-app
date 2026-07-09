# app.py
# Aplicacion de gestion de pedidos - Mila Fraga / Artabria
import json
import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session

from invoice import generar_factura, generar_etiqueta

BASE_DIR =
