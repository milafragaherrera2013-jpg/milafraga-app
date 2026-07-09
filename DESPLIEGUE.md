# Cómo poner tu app en internet con milafraga.es (gratis)

Esta guía usa **Render** (hosting gratuito) + un dominio `.es` que compres tú.
Vas a hacer todo desde el navegador, sin líneas de comandos. Tardarás
entre 30 y 60 minutos la primera vez.

⚠️ **Importante sobre el plan gratuito de Render:**
- Si nadie visita tu app durante un rato, "se duerme" y tarda unos 30-50
  segundos en despertar la primera vez que alguien entra después. Es normal,
  no es que esté rota.
- Los pedidos guardados pueden borrarse si Render reinicia el servidor
  (por ejemplo, al actualizar el código). Como hablamos, esto es aceptable
  por ahora. Si más adelante quieres que nunca se borren, hay que pasar a
  un plan de pago (~7€/mes) — dímelo cuando llegue ese momento.

---

## PARTE 1 — Subir tu código a GitHub (donde Render lo va a leer)

GitHub es como un "Google Drive" para código. Es gratis.

1. Ve a https://github.com y crea una cuenta (si no tienes) con tu email.
2. Una vez dentro, haz clic en el botón verde **"New"** (o el símbolo **+** de
   arriba a la derecha → "New repository").
3. Ponle de nombre `milafraga-app`. Déjalo en "Public". No marques ninguna
   casilla adicional. Dale a **"Create repository"**.
4. En la pantalla siguiente, busca el enlace que dice **"uploading an existing
   file"** (subir un archivo existente) y haz clic.
5. Ahora arrastra **todos los archivos y carpetas** de tu carpeta `milafraga_app`
   (los que ves en el Explorador de Windows: `app.py`, `catalog.json`, `static`,
   `templates`, `Procfile`, `requirements.txt`, etc.) a la zona de arrastre de GitHub.
6. Espera a que termine de subir todo (puede tardar un par de minutos por las fotos).
7. Abajo del todo, dale a **"Commit changes"** (el botón verde).

Ya tienes tu código en GitHub. ✅

---

## PARTE 2 — Crear tu app en Render

1. Ve a https://render.com y haz clic en **"Get Started"**.
2. Elige **"Sign up with GitHub"** — así conecta directamente con lo que acabas
   de subir.
3. Autoriza el acceso cuando te lo pida.
4. En el panel de Render, haz clic en **"New +"** → **"Web Service"**.
5. Busca y selecciona el repositorio `milafraga-app` que acabas de crear →
   **"Connect"**.
6. Rellena así:
   - **Name:** `mila-fraga` (o el que quieras, saldrá en una URL provisional)
   - **Region:** Frankfurt (la más cercana a España)
   - **Branch:** main
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Instance Type:** Free
7. Dale a **"Create Web Service"**.
8. Espera unos minutos mientras Render instala todo (verás un registro de texto
   pasando, como en tu ordenador). Cuando termine, arriba te dará una URL tipo:
   `https://mila-fraga.onrender.com`
9. Entra en esa URL y comprueba que tu panel y tu catálogo cargan — igual que
   en tu ordenador, pero ahora accesible desde cualquier móvil del mundo. 🎉

---

## PARTE 3 — Comprar el dominio milafraga.es

1. Ve a un registrador que venda dominios `.es`, por ejemplo:
   - https://www.namecheap.com
   - https://www.ovh.es
   - https://www.nic.es (el registro oficial español)
2. Busca `milafraga.es` y comprueba que está libre.
3. Añádelo al carrito y completa la compra (~10-15€/año). Aquí sí necesitas
   meter tus datos y tarjeta — eso lo haces tú directamente en su web, yo no
   puedo ni debo hacerlo por ti.

---

## PARTE 4 — Conectar milafraga.es con tu app de Render

1. En Render, entra en tu servicio (`mila-fraga`) → pestaña **"Settings"** →
   busca la sección **"Custom Domains"**.
2. Haz clic en **"Add Custom Domain"** y escribe `milafraga.es` (y también
   `www.milafraga.es` si quieres que funcionen los dos).
3. Render te va a mostrar unos datos tipo:
   ```
   Tipo: CNAME
   Nombre: www
   Valor: mila-fraga.onrender.com
   ```
   (o un registro tipo "A" con una IP, dependiendo del caso — Render te lo
   deja escrito clarito).
4. Ve a la web donde compraste el dominio → busca **"Gestión DNS"** o
   **"DNS Management"** → añade exactamente ese registro que te dio Render.
5. Espera entre 15 minutos y unas horas (a veces hasta 24h) — es el tiempo
   que tarda internet en "aprender" la nueva dirección. Esto se llama
   propagación DNS y es normal que no sea instantáneo.
6. Cuando esté listo, entra en `https://milafraga.es` y deberías ver tu app.

---

## Resumen del camino completo

```
Tu ordenador (código)
        ↓
   GitHub (guarda el código)
        ↓
   Render (lo ejecuta 24/7, gratis)
        ↓
milafraga.es (tu dominio, apuntando a Render)
```

---

## Si algo falla

Copia el mensaje de error exacto que veas (una captura de pantalla vale) y
mándamelo — lo revisamos juntas paso a paso, igual que hemos hecho hasta ahora.

## Cuando quieras actualizar la app en el futuro (nuevos productos, fotos, precios)

1. Cambia el archivo que corresponda en tu ordenador (por ejemplo `catalog.json`).
2. Sube ese archivo actualizado a GitHub (en la página de tu repositorio,
   entra en el archivo → lápiz de "editar" arriba a la derecha, o vuelve a
   arrastrarlo en "Add file → Upload files").
3. Render detecta el cambio solo y vuelve a desplegar automáticamente en
   1-2 minutos. No tienes que tocar nada en Render.
