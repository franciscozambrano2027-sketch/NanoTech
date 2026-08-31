#!/usr/bin/env python3
"""
Generador diario de contenido para NucleoTech.

Que hace, en orden:
 1. Lee automation/config/feeds.json y descarga esas fuentes RSS.
 2. Elige noticias que aun no se han publicado (segun automation/estado/estado.json).
 3. Le pide a un modelo open-source local (via Ollama) que escriba, en espanol y
    con voz propia, un resumen/comentario de cada noticia -- nunca copia el texto
    original, siempre enlaza y menciona la fuente.
 4. Toma el siguiente tema de automation/config/temas_guias.json y genera un
    articulo-guia practico con el mismo modelo.
 5. Renderiza cada pieza con las plantillas Jinja2 (mismo look and feel del sitio),
    genera un banner SVG original (sin fotos de terceros) y escribe el .html final
    en la raiz del repo.
 6. Inserta una tarjeta nueva en noticias.html (noticias) o resenas.html (guias).
 7. Actualiza el estado para no repetir noticias ni temas.

Este script NO hace commit ni push: eso lo hace el workflow de GitHub Actions.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests
from jinja2 import Environment, FileSystemLoader

BASE = Path(__file__).resolve().parent.parent  # raiz del repo
AUTO = Path(__file__).resolve().parent  # carpeta automation/

CONFIG_FEEDS = AUTO / "config" / "feeds.json"
CONFIG_TEMAS = AUTO / "config" / "temas_guias.json"
ESTADO_PATH = AUTO / "estado" / "estado.json"
TEMPLATES_DIR = AUTO / "templates"
IMG_AUTO_DIR = BASE / "imagenes" / "auto"

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
NUM_NOTICIAS = int(os.environ.get("NUM_NOTICIAS", "1"))
GENERAR_GUIA = os.environ.get("GENERAR_GUIA", "1") == "1"

sys.path.insert(0, str(AUTO))
from svg_banner import build_banner_svg  # noqa: E402

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #

def cargar_json(path: Path, defecto):
    if not path.exists():
        return defecto
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def guardar_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def slugify(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
    texto = re.sub(r"-{2,}", "-", texto)
    return texto[:70].rstrip("-")


def slug_unico(base_slug: str) -> str:
    slug = base_slug
    i = 2
    while (BASE / f"{slug}.html").exists():
        slug = f"{base_slug}-{i}"
        i += 1
    return slug


def fecha_legible() -> str:
    ahora = datetime.now(timezone.utc)
    return f"{ahora.day} de {MESES[ahora.month - 1]} de {ahora.year}"


def sanitizar_html_cuerpo(html: str) -> str:
    """Deja pasar solo un set reducido de etiquetas seguras."""
    permitidas = r"h2|h3|p|ul|ol|li|strong|em|div|blockquote"
    # Elimina scripts/estilos por completo si el modelo los agrega por error.
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", html)
    # Elimina etiquetas no permitidas mientras conserva su texto.
    html = re.sub(rf"(?is)<(?!/?({permitidas})\b)[^>]+>", "", html)
    return html.strip()


def extraer_json(texto: str) -> dict:
    """Extrae el primer objeto JSON valido de la respuesta del modelo."""
    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio == -1 or fin == -1:
        raise ValueError("El modelo no devolvio JSON reconocible")
    bruto = texto[inicio : fin + 1]
    return json.loads(bruto)


def llamar_modelo(prompt: str, intentos: int = 3) -> str:
    ultimo_error = None
    for _ in range(intentos):
        try:
            r = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.6},
                },
                timeout=600,
            )
            r.raise_for_status()
            return r.json()["response"]
        except Exception as e:  # noqa: BLE001
            ultimo_error = e
    raise RuntimeError(f"No se pudo contactar al modelo tras varios intentos: {ultimo_error}")


# --------------------------------------------------------------------------- #
# Generacion de una noticia
# --------------------------------------------------------------------------- #

def obtener_noticias_nuevas(estado: dict) -> list[dict]:
    config = cargar_json(CONFIG_FEEDS, {"fuentes": []})
    publicadas = set(estado.get("noticias_publicadas", []))
    candidatas = []

    for fuente in config.get("fuentes", []):
        try:
            feed = feedparser.parse(fuente["url"])
        except Exception as e:  # noqa: BLE001
            print(f"[aviso] no se pudo leer {fuente['nombre']}: {e}")
            continue
        for entrada in feed.entries[:15]:
            link = entrada.get("link")
            if not link or link in publicadas:
                continue
            candidatas.append(
                {
                    "titulo_original": entrada.get("title", "").strip(),
                    "resumen_original": re.sub(
                        "<[^<]+?>", "", entrada.get("summary", "")
                    ).strip(),
                    "link": link,
                    "fuente_nombre": fuente["nombre"],
                    "categoria": fuente.get("categoria", "Tecnología"),
                    "publicado": entrada.get("published", ""),
                }
            )
    return candidatas[:NUM_NOTICIAS]


def generar_noticia(cruda: dict) -> dict:
    prompt = f"""Eres redactor del sitio de tecnología NúcleoTech, en español neutro, tono claro y práctico
(nunca sensacionalista, nunca copias frases textuales de la fuente).

Fuente: {cruda['fuente_nombre']}
Titular original: {cruda['titulo_original']}
Resumen original (solo como referencia de los hechos, NO lo copies literalmente): {cruda['resumen_original'][:1200]}

Tarea: escribe una nota propia en español que explique esta noticia a una audiencia general,
con tus propias palabras, aportando contexto o por qué importa. 350 a 450 palabras.

Responde ÚNICAMENTE con un objeto JSON con estas claves exactas:
{{
  "titulo": "titular propio, no traducido ni copiado del original",
  "resumen_meta": "una sola frase de hasta 25 palabras que resuma la nota",
  "cuerpo_html": "el cuerpo del artículo en HTML usando solo <h2>, <p>, <ul>, <li>, <strong>. Incluye al menos un <h2> intermedio."
}}"""
    crudo = llamar_modelo(prompt)
    datos = extraer_json(crudo)
    datos["cuerpo_html"] = sanitizar_html_cuerpo(datos["cuerpo_html"])
    datos["categoria"] = cruda["categoria"]
    datos["fuente_nombre"] = cruda["fuente_nombre"]
    datos["fuente_url"] = cruda["link"]
    datos["tipo"] = "noticia"
    return datos


# --------------------------------------------------------------------------- #
# Generacion de un articulo-guia
# --------------------------------------------------------------------------- #

def generar_guia(tema: dict) -> dict:
    prompt = f"""Eres redactor del sitio de tecnología NúcleoTech, en español neutro, tono práctico y directo,
sin relleno, orientado a que el lector resuelva un problema real.

Tema asignado: {tema['titulo']}
Categoría: {tema['categoria']}

Tarea: escribe un artículo explicativo/práctico sobre ese tema, con pasos u orientaciones concretas.
500 a 650 palabras. Si el tema implica riesgo físico o eléctrico, incluye una advertencia de seguridad breve.

Responde ÚNICAMENTE con un objeto JSON con estas claves exactas:
{{
  "titulo": "puede ser igual o muy similar al tema asignado",
  "resumen_meta": "una sola frase de hasta 25 palabras que resuma el artículo",
  "cuerpo_html": "el cuerpo en HTML usando solo <h2>, <p>, <ol>, <ul>, <li>, <strong>. Incluye al menos dos <h2>."
}}"""
    crudo = llamar_modelo(prompt)
    datos = extraer_json(crudo)
    datos["cuerpo_html"] = sanitizar_html_cuerpo(datos["cuerpo_html"])
    datos["categoria"] = tema["categoria"]
    datos["tipo"] = "guia"
    return datos


# --------------------------------------------------------------------------- #
# Render + insercion en el sitio
# --------------------------------------------------------------------------- #

def render_y_guardar(datos: dict, estado: dict, env: Environment) -> dict:
    slug = slug_unico(slugify(datos["titulo"]))
    palabras = len(re.sub("<[^<]+?>", " ", datos["cuerpo_html"]).split())
    minutos = max(2, round(palabras / 200))

    relacionados = [
        a for a in estado.get("articulos", [])
        if a["tipo"] == datos["tipo"]
    ][-2:]

    contexto = {
        **datos,
        "slug": slug,
        "fecha_legible": fecha_legible(),
        "minutos_lectura": minutos,
        "relacionados": relacionados,
    }

    plantilla = env.get_template("noticia.html.j2" if datos["tipo"] == "noticia" else "guia.html.j2")
    html_final = plantilla.render(**contexto)
    (BASE / f"{slug}.html").write_text(html_final, encoding="utf-8")

    IMG_AUTO_DIR.mkdir(parents=True, exist_ok=True)
    banner = build_banner_svg(datos["titulo"], datos["categoria"], seed=slug)
    (IMG_AUTO_DIR / f"{slug}.svg").write_text(banner, encoding="utf-8")

    print(f"[ok] generado {slug}.html ({datos['tipo']})")
    return {"slug": slug, "titulo": datos["titulo"], "tipo": datos["tipo"],
            "categoria": datos["categoria"], "resumen_meta": datos["resumen_meta"]}


TARJETA_TMPL = (
    '<article class="review-card"><img src="imagenes/auto/{slug}.svg" alt="{titulo}" loading="lazy">'
    '<div><span class="tag">{categoria}</span><h2><a href="{slug}.html">{titulo}</a></h2>'
    '<p>{resumen_meta}</p></div></article>'
)


def insertar_tarjeta(pagina: str, entrada: dict) -> None:
    ruta = BASE / pagina
    contenido = ruta.read_text(encoding="utf-8")
    marca = "<!-- ARTICULOS_AUTO_START -->" if pagina == "resenas.html" else "<!-- NOTICIAS_GRID_START -->"
    tarjeta = TARJETA_TMPL.format(**entrada)
    contenido = contenido.replace(marca, marca + tarjeta, 1)
    ruta.write_text(contenido, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> None:
    estado = cargar_json(ESTADO_PATH, {"noticias_publicadas": [], "indice_guia_siguiente": 0, "articulos": []})
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)

    generados: list[dict] = []

    # --- Noticias ---
    crudas = obtener_noticias_nuevas(estado)
    if not crudas:
        print("[info] no hay noticias nuevas en los feeds configurados.")
    for cruda in crudas:
        try:
            datos = generar_noticia(cruda)
            entrada = render_y_guardar(datos, estado, env)
            insertar_tarjeta("noticias.html", entrada)
            estado["noticias_publicadas"].append(cruda["link"])
            estado["articulos"].append(entrada)
            generados.append(entrada)
        except Exception as e:  # noqa: BLE001
            print(f"[error] fallo generando noticia '{cruda['titulo_original']}': {e}")

    # --- Guia del dia ---
    if GENERAR_GUIA:
        temas = cargar_json(CONFIG_TEMAS, {"temas": []}).get("temas", [])
        if temas:
            idx = estado.get("indice_guia_siguiente", 0) % len(temas)
            tema = temas[idx]
            try:
                datos = generar_guia(tema)
                entrada = render_y_guardar(datos, estado, env)
                insertar_tarjeta("resenas.html", entrada)
                estado["indice_guia_siguiente"] = (idx + 1) % len(temas)
                estado["articulos"].append(entrada)
                generados.append(entrada)
            except Exception as e:  # noqa: BLE001
                print(f"[error] fallo generando guia '{tema['titulo']}': {e}")

    # Mantener el historial de articulos acotado.
    estado["articulos"] = estado["articulos"][-200:]
    estado["noticias_publicadas"] = estado["noticias_publicadas"][-500:]
    guardar_json(ESTADO_PATH, estado)

    if generados:
        print(f"[resumen] {len(generados)} pieza(s) publicada(s) hoy:")
        for g in generados:
            print(f"  - ({g['tipo']}) {g['titulo']} -> {g['slug']}.html")
    else:
        print("[resumen] no se genero contenido nuevo hoy.")


if __name__ == "__main__":
    main()
