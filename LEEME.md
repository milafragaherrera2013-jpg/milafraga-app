# Cómo instalar tu app "Mila Fraga" en tu ordenador

Esta guía está pensada para alguien que **no es programadora**. Ve paso a paso, sin saltarte ninguno.

---

## 1. Descomprime la carpeta

Descarga el archivo `.zip` que te ha dado Claude y descomprímelo donde prefieras
(por ejemplo, en tu escritorio o en `Documentos`). Al descomprimir verás una carpeta
llamada `milafraga_app` con varios archivos dentro (`app.py`, `config.json`, etc.).
No cambies el nombre de los archivos ni los muevas de sitio.

---

## 2. Instala Python (si no lo tienes)

Python es el "motor" que hace funcionar la aplicación.

- **Windows:** ve a https://www.python.org/downloads/ , descarga la última versión
  y al instalar, **marca la casilla que dice "Add Python to PATH"** antes de darle a Instalar.
  Es el paso que más gente olvida y luego da error, así que fíjate bien.
- **Mac:** los Mac suelen traer Python instalado. Para comprobarlo, abre la aplicación
  "Terminal" (búscala con Spotlight, la lupa de arriba a la derecha) y escribe:
  ```
  python3 --version
  ```
  Si te devuelve un número (ej. `Python 3.12.3`), ya lo tienes.

---

## 3. Abre la Terminal (o Símbolo del sistema) en la carpeta del proyecto

- **Windows:** abre la carpeta `milafraga_app` en el Explorador de archivos, haz clic
  en la barra de direcciones de arriba, escribe `cmd` y pulsa Enter. Se abrirá una
  ventana negra ya situada en esa carpeta.
- **Mac:** abre "Terminal", escribe `cd ` (con un espacio al final) y luego arrastra
  la carpeta `milafraga_app` dentro de la ventana de Terminal — se autocompletará la
  ruta. Pulsa Enter.

---

## 4. Instala lo necesario (solo la primera vez)

En esa ventana negra, escribe esto y pulsa Enter:

```
pip install -r requirements.txt
```

(En Mac, si da error, prueba con `pip3 install -r requirements.txt`)

Vas a ver un montón de texto pasando — es normal, está descargando e instalando
las piezas que la app necesita (Flask, generador de PDF, etc.). Espera a que termine
y te devuelva el cursor.

---

## 5. Arranca la aplicación

Escribe:

```
python app.py
```

(En Mac: `python3 app.py`)

Si todo va bien, verás un mensaje parecido a este:

```
* Running on http://127.0.0.1:5000
```

**Deja esa ventana abierta** — si la cierras, la aplicación se apaga.

---

## 6. Ábrela en el navegador

Abre Chrome, Firefox o el navegador que uses, y visita:

- **Panel de pedidos (para ti):** http://127.0.0.1:5000
- **Catálogo (para tus clientas):** http://127.0.0.1:5000/formulario

---

## 7. Para apagarla o volver a arrancarla

- **Apagar:** vuelve a la ventana negra y pulsa `Ctrl + C`.
- **Volver a arrancar otro día:** repite solo el paso 3 y el paso 5
  (el paso 4 de instalar solo hace falta la primera vez).

---

## Preguntas frecuentes

**¿Dónde se guardan mis pedidos?**
En un archivito llamado `pedidos.db` dentro de la misma carpeta. No lo borres ni lo muevas.

**¿Puedo compartir esto con otra persona para que lo use desde su casa?**
Tal y como está ahora, no — solo funciona en el ordenador donde la tengas arrancada
(por eso en la dirección pone "127.0.0.1", que significa "este mismo ordenador").
Para que sea accesible desde cualquier sitio con tu propio dominio, hay que hacer un
despliegue en internet (hosting) — dímelo cuando quieras dar ese paso y te ayudo.

**Se me ha cerrado la ventana negra sin querer, ¿pasa algo?**
No, no pierdes ningún pedido. Solo tienes que repetir los pasos 3 y 5 para volver a
arrancarla.

**He cambiado algo en `catalog.json` (precios, productos) y no se ve reflejado.**
Tienes que apagar la app (`Ctrl+C`) y volver a arrancarla (`python app.py`) para que
recoja los cambios.
