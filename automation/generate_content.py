#!/usr/bin/env python3
"""
Generador diario de contenido para NucleoTech.

FUNCIONES:
1. Lee las fuentes RSS configuradas en automation/config/feeds.json.
2. Detecta noticias que todavía no han sido publicadas.
3. Genera entre 2 y 3 noticias diarias mediante Ollama.
4. Genera 1 artículo-guía diario si GENERAR_GUIA=1.
5. Por defecto guarda las piezas como borradores para revisión humana.
6. Crea un HTML individual solo cuando una pieza es aprobada.
6. Genera un banner SVG original para cada artículo.
7. Actualiza noticias.html mostrando solamente las noticias recientes.
8. Actualiza resenas.html mostrando solamente las guías recientes.
9. Mantiene los artículos HTML antiguos para conservar valor SEO.
10. Guarda el estado en automation/estado/estado.json.
11. Evita repetir noticias ya publicadas.
12. Genera el resumen para GitHub Actions.

Este script NO hace commit ni push.
Eso lo realiza GitHub Actions.
"""

from __future__ import annotations

import html
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

from asset_paths import canonical_relative_path, canonicalize_existing_image


# ============================================================================
# RUTAS
# ============================================================================

BASE = Path(__file__).resolve().parent.parent
AUTO = Path(__file__).resolve().parent

CONFIG_FEEDS = AUTO / "config" / "feeds.json"
CONFIG_TEMAS = AUTO / "config" / "temas_guias.json"
ESTADO_PATH = AUTO / "estado" / "estado.json"
TEMPLATES_DIR = AUTO / "templates"
IMG_AUTO_DIR = BASE / "imagenes" / "auto"
IMG_NOTICIAS_DIR = BASE / "imagenes" / "noticias"


# ============================================================================
# CONFIGURACION
# ============================================================================

OLLAMA_HOST = os.environ.get(
    "OLLAMA_HOST",
    "http://localhost:11434"
)

OLLAMA_MODEL = os.environ.get(
    "OLLAMA_MODEL",
    "llama3.2:3b"
)

# Por defecto: SOLO 2 noticias diarias.
# Puede cambiarse desde GitHub Actions a 3 usando NUM_NOTICIAS.
try:
    NUM_NOTICIAS = max(
        1,
        min(
            int(os.environ.get("NUM_NOTICIAS", "2")),
            3
        )
    )
except ValueError:
    NUM_NOTICIAS = 2


GENERAR_GUIA = (
    os.environ.get("GENERAR_GUIA", "1") == "1"
)


# Cantidad de artículos que aparecerán en los listados públicos.
# Los HTML antiguos NO se eliminan.
MAX_NOTICIAS_EN_PORTADA = 12
MAX_GUIAS_EN_PORTADA = 8

# Cantidad máxima de historial que conservamos en estado.json.
MAX_ARTICULOS_ESTADO = 500
MAX_NOTICIAS_PUBLICADAS = 1000

# La automatización genera borradores por defecto. La publicación pasa por revisión humana.
MODO_BORRADOR = os.environ.get("MODO_BORRADOR", "1") == "1"
DRAFT_PENDING_DIR = AUTO / "drafts" / "pending"
DRAFT_APPROVED_DIR = AUTO / "drafts" / "approved"


# ============================================================================
# IMPORTAR GENERADOR SVG
# ============================================================================

sys.path.insert(0, str(AUTO))



# ============================================================================
# MESES
# ============================================================================

MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


# ============================================================================
# UTILIDADES
# ============================================================================

def cargar_json(path: Path, defecto):
    """
    Carga un archivo JSON en UTF-8.

    Si el archivo no existe, devuelve el valor por defecto.
    """
    if not path.exists():
        return defecto

    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)

    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"JSON invalido en {path}: {e}"
        ) from e


def guardar_json(path: Path, data) -> None:
    """
    Guarda JSON usando UTF-8 real y sin BOM.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

        f.write("\n")


def slugify(texto: str) -> str:
    """
    Convierte un título en un slug seguro para URL.
    """

    texto = str(texto or "").strip()

    texto = unicodedata.normalize(
        "NFKD",
        texto
    ).encode(
        "ascii",
        "ignore"
    ).decode()

    texto = texto.lower()

    texto = re.sub(
        r"[^a-z0-9]+",
        "-",
        texto
    )

    texto = texto.strip("-")

    texto = re.sub(
        r"-{2,}",
        "-",
        texto
    )

    return texto[:80].rstrip("-")

def ruta_imagen_relativa(slug: str, tipo: str = "noticia") -> str:
    """Busca una imagen editorial existente para el artículo.

    No crea imágenes automáticamente: una publicación nueva debe tener una
    imagen elegida por el editor antes de pasar a approved/.
    """
    slug = str(slug or "").strip()
    if not slug:
        return ""

    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"):
        candidata = IMG_NOTICIAS_DIR / f"{slug}{ext}"
        if candidata.is_file():
            return f"imagenes/noticias/{candidata.name}"
        candidata = IMG_AUTO_DIR / f"{slug}{ext}"
        if candidata.is_file():
            return f"imagenes/auto/{candidata.name}"

    return ""


def normalizar_imagen_estado(entrada: dict) -> dict:
    """Garantiza que los artículos antiguos también tengan un campo imagen."""
    if not isinstance(entrada, dict):
        return entrada

    slug = str(entrada.get("slug", "")).strip()
    tipo = str(entrada.get("tipo", "noticia")).strip() or "noticia"

    imagen = str(entrada.get("imagen", "")).strip()
    if not imagen and slug:
        imagen = ruta_imagen_relativa(slug, tipo)

    # Si el estado aún apunta al SVG y apareció una foto editorial con el
    # mismo slug, la foto pasa a ser la fuente única para todos los listados.
    if slug and tipo == "noticia" and (
        not imagen or imagen == f"imagenes/auto/{slug}.svg"
    ):
        candidata = ruta_imagen_relativa(slug, tipo)
        if candidata != f"imagenes/auto/{slug}.svg":
            imagen = candidata

    entrada["imagen"] = imagen
    return entrada



def slug_unico(base_slug: str) -> str:
    """
    Genera un slug único sin sobrescribir HTML existente.
    """

    if not base_slug:
        base_slug = "articulo"

    slug = base_slug
    i = 2

    while (BASE / f"{slug}.html").exists():
        slug = f"{base_slug}-{i}"
        i += 1

    return slug


def fecha_legible() -> str:
    """
    Fecha actual en español.
    """

    ahora = datetime.now(timezone.utc)

    return (
        f"{ahora.day} de "
        f"{MESES[ahora.month - 1]} de "
        f"{ahora.year}"
    )


def limpiar_texto(texto: str) -> str:
    """
    Limpia texto procedente de RSS.
    """

    if not texto:
        return ""

    texto = re.sub(
        r"(?is)<script.*?>.*?</script>",
        "",
        texto
    )

    texto = re.sub(
        r"(?is)<style.*?>.*?</style>",
        "",
        texto
    )

    texto = re.sub(
        r"<[^>]+>",
        " ",
        texto
    )

    texto = html.unescape(texto)

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


def sanitizar_html_cuerpo(html_texto: str) -> str:
    """
    Permite únicamente las etiquetas HTML necesarias para el artículo.
    """

    if not html_texto:
        return ""

    # Eliminar scripts y estilos completos.
    html_texto = re.sub(
        r"(?is)<(script|style)[^>]*>.*?</\1>",
        "",
        html_texto
    )

    # Eliminar atributos peligrosos.
    html_texto = re.sub(
        r"(?is)\s+on[a-z]+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)",
        "",
        html_texto
    )

    # Eliminar enlaces HTML.
    html_texto = re.sub(
        r"(?is)</?a\b[^>]*>",
        "",
        html_texto
    )

    # Etiquetas permitidas.
    permitidas = (
        r"h2|h3|p|ul|ol|li|strong|em|div|blockquote"
    )

    html_texto = re.sub(
        rf"(?is)<(?!/?({permitidas})\b)[^>]+>",
        "",
        html_texto
    )

    # Evitar bloques vacíos excesivos.
    html_texto = re.sub(
        r"(?is)<p>\s*</p>",
        "",
        html_texto
    )

    html_texto = re.sub(
        r"\n{3,}",
        "\n\n",
        html_texto
    )

    return html_texto.strip()


def extraer_json(texto: str) -> dict:
    """
    Extrae el objeto JSON de la respuesta de Ollama.

    Algunos modelos pueden devolver texto adicional.
    """

    if not texto:
        raise ValueError(
            "El modelo devolvio una respuesta vacia."
        )

    texto = texto.strip()

    # Intento directo.
    try:
        datos = json.loads(texto)

        if isinstance(datos, dict):
            return datos

    except json.JSONDecodeError:
        pass

    # Buscar objeto JSON.
    inicio = texto.find("{")
    fin = texto.rfind("}")

    if inicio == -1 or fin == -1 or fin <= inicio:
        raise ValueError(
            "El modelo no devolvio un objeto JSON reconocible."
        )

    bruto = texto[inicio:fin + 1]

    try:
        datos = json.loads(bruto)

    except json.JSONDecodeError as e:
        raise ValueError(
            f"JSON generado por Ollama invalido: {e}"
        ) from e

    if not isinstance(datos, dict):
        raise ValueError(
            "La respuesta del modelo no es un objeto JSON."
        )

    return datos


# ============================================================================
# OLLAMA
# ============================================================================

def comprobar_ollama() -> None:
    """
    Comprueba que Ollama esté disponible.
    """

    try:
        respuesta = requests.get(
            OLLAMA_HOST,
            timeout=10
        )

        respuesta.raise_for_status()

        print(
            f"[ok] Ollama disponible en {OLLAMA_HOST}"
        )

        print(
            f"[info] Modelo: {OLLAMA_MODEL}"
        )

    except Exception as e:
        raise RuntimeError(
            f"No se pudo conectar con Ollama en "
            f"{OLLAMA_HOST}: {e}"
        ) from e


def llamar_modelo(
    prompt: str,
    intentos: int = 3
) -> str:

    ultimo_error = None

    for intento in range(1, intentos + 1):

        try:

            respuesta = requests.post(
                f"{OLLAMA_HOST}/api/generate",

                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",

                    "options": {
                        "temperature": 0.55,
                    },
                },

                timeout=600,
            )

            respuesta.raise_for_status()

            datos = respuesta.json()

            contenido = datos.get(
                "response",
                ""
            )

            if not contenido:
                raise RuntimeError(
                    "Ollama devolvio una respuesta vacia."
                )

            return contenido

        except Exception as e:
            ultimo_error = e

            print(
                f"[aviso] intento {intento}/{intentos} "
                f"fallido con Ollama: {e}"
            )

    raise RuntimeError(
        "No se pudo generar contenido con Ollama: "
        f"{ultimo_error}"
    )


# ============================================================================
# FILTRO DE RELEVANCIA TECNOLÓGICA
# ============================================================================

TECH_TERMS = (
    "tecnolog", "hardware", "software", "internet", "wifi", "wi-fi",
    "router", "redes", "5g", "4g", "fibra", "ethernet", "bluetooth",
    "usb", "ssd", "nvme", "ram", "procesador", "cpu", "gpu", "nvidia",
    "amd", "intel", "windows", "linux", "android", "ios", "iphone",
    "ipad", "mac", "macbook", "samsung", "pixel", "xiaomi", "motorola",
    "playstation", "xbox", "nintendo", "consola", "smartphone", "celular",
    "laptop", "computadora", "pc", "monitor", "teclado", "mouse", "ia",
    "inteligencia artificial", "openai", "google", "microsoft", "apple",
    "meta", "amazon", "chip", "semiconductor", "app", "aplicación",
    "ciberseguridad", "seguridad informática", "routeros", "mikrotik",
)

def es_tecnologica(titulo: str, resumen: str, categoria: str) -> bool:
    texto = f"{titulo} {resumen} {categoria}".lower()
    return any(term in texto for term in TECH_TERMS)


# ============================================================================
# RSS
# ============================================================================

def obtener_noticias_nuevas(
    estado: dict
) -> list[dict]:

    config = cargar_json(
        CONFIG_FEEDS,
        {"fuentes": []}
    )

    publicadas = set(
        estado.get(
            "noticias_publicadas",
            []
        )
    ) | set(
        estado.get(
            "noticias_en_revision",
            []
        )
    )

    candidatas = []

    urls_vistas = set()

    fuentes = config.get(
        "fuentes",
        []
    )

    if not fuentes:
        print(
            "[aviso] No hay fuentes RSS configuradas."
        )

        return []

    print(
        f"[info] Revisando {len(fuentes)} fuente(s) RSS..."
    )

    for fuente in fuentes:

        nombre = str(
            fuente.get(
                "nombre",
                "Fuente RSS"
            )
        ).strip()

        url = str(
            fuente.get(
                "url",
                ""
            )
        ).strip()

        categoria = str(
            fuente.get(
                "categoria",
                "Tecnologia"
            )
        ).strip()

        # Fuente sin URL.
        if not url:

            print(
                f"[aviso] {nombre}: no tiene URL. Se omite."
            )

            continue

        try:

            respuesta = requests.get(
                url,
                timeout=20,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "NucleoTech-RSS/1.0"
                    )
                }
            )

            respuesta.raise_for_status()

            feed = feedparser.parse(
                respuesta.content
            )

        except Exception as e:

            print(
                f"[aviso] No se pudo leer "
                f"{nombre}: {e}"
            )

            continue

        if getattr(
            feed,
            "bozo",
            False
        ) and not getattr(
            feed,
            "entries",
            []
        ):

            print(
                f"[aviso] {nombre}: "
                "RSS invalido o sin entradas."
            )

            continue

        entradas = getattr(
            feed,
            "entries",
            []
        )

        print(
            f"[info] {nombre}: "
            f"{len(entradas)} entrada(s)"
        )

        for entrada in entradas[:20]:

            link = str(
                entrada.get(
                    "link",
                    ""
                )
            ).strip()

            if not link:
                continue

            # Evitar duplicados entre feeds.
            if link in urls_vistas:
                continue

            urls_vistas.add(link)

            # Ya publicada.
            if link in publicadas:
                continue

            titulo = limpiar_texto(
                entrada.get(
                    "title",
                    ""
                )
            )

            if not titulo:
                continue

            resumen = limpiar_texto(
                entrada.get(
                    "summary",
                    ""
                )
            )

            if not resumen:
                resumen = limpiar_texto(
                    entrada.get(
                        "description",
                        ""
                    )
                )

            publicado = str(
                entrada.get(
                    "published",
                    ""
                )
                or entrada.get("updated", "")
                or entrada.get("created", "")
            ).strip()

            if not es_tecnologica(titulo, resumen, categoria):
                print(f"[omitida] No parece tecnológica: {titulo}")
                continue

            candidatas.append(
                {
                    "titulo_original": titulo,
                    "resumen_original": resumen,
                    "link": link,
                    "fuente_nombre": nombre,
                    "categoria": categoria,
                    "publicado": publicado,
                }
            )

    # ----------------------------------------------------------------------
    # Ordenar para dar prioridad a entradas que tengan fecha RSS.
    # ----------------------------------------------------------------------

    def clave_orden(item):
        fecha = str(
            item.get(
                "publicado",
                ""
            )
        )

        return fecha

    candidatas.sort(
        key=clave_orden,
        reverse=True
    )

    # ----------------------------------------------------------------------
    # Mostrar candidatos.
    # ----------------------------------------------------------------------

    print(
        f"[info] Noticias nuevas encontradas: "
        f"{len(candidatas)}"
    )

    for noticia in candidatas[:10]:

        print(
            "  - "
            f"{noticia['titulo_original']} "
            f"[{noticia['fuente_nombre']}]"
        )

    return candidatas[:NUM_NOTICIAS]


# ============================================================================
# GENERAR NOTICIA
# ============================================================================

def generar_noticia(
    cruda: dict
) -> dict:

    prompt = f"""
Eres redactor profesional del sitio tecnológico NucleoTech.

Escribe en español neutro latinoamericano.

IMPORTANTE:

- NO copies frases textuales de la fuente.
- NO inventes datos.
- NO inventes cifras.
- NO inventes declaraciones.
- NO presentes opiniones como hechos.
- Utiliza únicamente la información proporcionada como referencia.
- Puedes aportar contexto general cuando sea razonable.
- El artículo debe ser original.
- No menciones que eres una IA.
- No utilices Markdown.
- No utilices HTML fuera de cuerpo_html.
- No utilices enlaces HTML.
- El texto debe ser claro y natural.
- Evita titulares sensacionalistas.
- No uses "revolucionario", "impactante" o similares salvo que sean necesarios.

FUENTE:
{cruda['fuente_nombre']}

TITULAR ORIGINAL:
{cruda['titulo_original']}

RESUMEN ORIGINAL:
{cruda['resumen_original'][:1800]}

URL DE LA FUENTE:
{cruda['link']}

Escribe una noticia propia de aproximadamente 650 a 900 palabras. La pieza debe aportar contexto y análisis suficiente para que tenga valor por sí misma.

La estructura debe:

1. Explicar con precisión qué ocurrió y qué se sabe realmente.
2. Separar hechos confirmados de interpretaciones o expectativas.
3. Dar contexto técnico que ayude a entender la noticia.
4. Explicar por qué puede importar a usuarios, empresas o consumidores.
5. Añadir una sección de "Qué significa en la práctica" con ejemplos concretos.
6. Cerrar con una conclusión útil, sin repetir el titular.

No rellenes el texto con generalidades. Si la fuente no aporta un dato, no lo inventes.
No conviertas una noticia de otra categoría en una noticia tecnológica solo para publicarla.

El artículo debe tener al menos dos encabezados <h2>.

Devuelve EXCLUSIVAMENTE un objeto JSON válido con esta estructura:

{{
  "titulo": "titular original y atractivo, pero propio",
  "resumen_meta": "una sola frase de máximo 25 palabras",
  "cuerpo_html": "<p>...</p><h2>...</h2><p>...</p>"
}}
"""

    respuesta = llamar_modelo(
        prompt
    )

    datos = extraer_json(
        respuesta
    )

    titulo = limpiar_texto(
        str(
            datos.get(
                "titulo",
                ""
            )
        )
    )

    resumen_meta = limpiar_texto(
        str(
            datos.get(
                "resumen_meta",
                ""
            )
        )
    )

    cuerpo = sanitizar_html_cuerpo(
        str(
            datos.get(
                "cuerpo_html",
                ""
            )
        )
    )

    if not titulo:
        raise ValueError(
            "La noticia generada no tiene titulo."
        )

    if not cuerpo:
        raise ValueError(
            "La noticia generada no tiene cuerpo."
        )

    if not resumen_meta:

        texto_plano = limpiar_texto(
            cuerpo
        )

        resumen_meta = (
            texto_plano[:160]
            + ("..." if len(texto_plano) > 160 else "")
        )

    return {
        "titulo": titulo,
        "resumen_meta": resumen_meta,
        "cuerpo_html": cuerpo,
        "categoria": cruda.get(
            "categoria",
            "Tecnologia"
        ),
        "fuente_nombre": cruda[
            "fuente_nombre"
        ],
        "fuente_url": cruda[
            "link"
        ],
        "tipo": "noticia",
    }


# ============================================================================
# GENERAR GUIA
# ============================================================================

def generar_guia(
    tema: dict
) -> dict:

    prompt = f"""
Eres redactor profesional del sitio NucleoTech.

Escribe en español neutro latinoamericano.

Tema:
{tema['titulo']}

Categoría:
{tema['categoria']}

Escribe una guía práctica de aproximadamente 800 a 1100 palabras.

La guía debe:

- Resolver una necesidad real y concreta.
- Ser original y específica, no una introducción genérica al tema.
- Explicar el razonamiento detrás de cada recomendación.
- Incluir pasos concretos y comprobaciones cuando corresponda.
- Explicar errores frecuentes y cómo reconocerlos.
- Incluir criterios para decidir cuándo una solución no conviene.
- Incorporar una sección de "qué comprobar después" para verificar el resultado.
- Evitar frases de relleno y consejos que podrían aplicarse a cualquier dispositivo.
- No inventar especificaciones.
- No mencionar que eres una IA.
- No utilizar Markdown.
- No utilizar enlaces HTML.
- Usar solamente HTML permitido.

Si el tema implica electricidad, herramientas, calor, baterías,
componentes electrónicos o cualquier riesgo físico, incluye una
advertencia breve de seguridad.

Debe tener al menos dos encabezados <h2>.

Devuelve EXCLUSIVAMENTE un objeto JSON válido:

{{
  "titulo": "titulo de la guia",
  "resumen_meta": "una sola frase de máximo 25 palabras",
  "cuerpo_html": "<p>...</p><h2>...</h2><p>...</p>"
}}
"""

    respuesta = llamar_modelo(
        prompt
    )

    datos = extraer_json(
        respuesta
    )

    titulo = limpiar_texto(
        str(
            datos.get(
                "titulo",
                ""
            )
        )
    )

    resumen_meta = limpiar_texto(
        str(
            datos.get(
                "resumen_meta",
                ""
            )
        )
    )

    cuerpo = sanitizar_html_cuerpo(
        str(
            datos.get(
                "cuerpo_html",
                ""
            )
        )
    )

    if not titulo:
        raise ValueError(
            "La guia generada no tiene titulo."
        )

    if not cuerpo:
        raise ValueError(
            "La guia generada no tiene cuerpo."
        )

    if not resumen_meta:

        texto_plano = limpiar_texto(
            cuerpo
        )

        resumen_meta = (
            texto_plano[:160]
            + ("..." if len(texto_plano) > 160 else "")
        )

    return {
        "titulo": titulo,
        "resumen_meta": resumen_meta,
        "cuerpo_html": cuerpo,
        "categoria": tema[
            "categoria"
        ],
        "tipo": "guia",
    }


# ============================================================================
# BORRADORES
# ============================================================================

def guardar_borrador(datos: dict, origen: dict | None = None) -> dict:
    """Guarda una pieza en revisión sin crear HTML público ni tocar los listados."""
    DRAFT_PENDING_DIR.mkdir(parents=True, exist_ok=True)

    slug_base = slugify(datos.get("titulo", "")) or "borrador"
    fecha = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = f"{slug_base}-{fecha}"

    borrador = {
        "estado": "pendiente",
        "creado": datetime.now(timezone.utc).isoformat(),
        "slug_sugerido": slug,
        "titulo": datos.get("titulo", ""),
        "resumen_meta": datos.get("resumen_meta", ""),
        "cuerpo_html": datos.get("cuerpo_html", ""),
        "categoria": datos.get("categoria", "Tecnologia"),
        "tipo": datos.get("tipo", "noticia"),
        "fuente_nombre": datos.get("fuente_nombre", ""),
        "fuente_url": datos.get("fuente_url", ""),
        "imagen": "",
        "imagen_instrucciones": (
            "OBLIGATORIO: coloca primero la imagen elegida dentro del repositorio y escribe aqui su ruta relativa, "
            "por ejemplo imagenes/noticias/nombre.jpg. Este borrador no se puede publicar sin imagen."
        ),
    }

    if origen:
        borrador["origen"] = {
            "fuente_nombre": origen.get("fuente_nombre", ""),
            "fuente_url": origen.get("link", ""),
            "titulo_original": origen.get("titulo_original", ""),
        }

    ruta = DRAFT_PENDING_DIR / f"{slug}.json"
    ruta.write_text(
        json.dumps(borrador, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(f"[borrador] {ruta.relative_to(BASE)}")
    return borrador


# ============================================================================
# RENDERIZADO
# ============================================================================

def render_y_guardar(
    datos: dict,
    estado: dict,
    env: Environment
) -> dict:

    slug = slug_unico(
        slugify(
            datos["titulo"]
        )
    )

    texto_plano = limpiar_texto(
        datos["cuerpo_html"]
    )

    palabras = len(
        texto_plano.split()
    )

    minutos = max(
        2,
        round(
            palabras / 200
        )
    )

    relacionados = [
        a
        for a in estado.get(
            "articulos",
            []
        )
        if a.get("tipo") == datos["tipo"]
    ][-3:]

    # Una sola fuente de imagen: la misma ruta se usa en la noticia,
    # noticias.html e index.html.
    imagen = str(datos.get("imagen", "")).strip()
    if imagen:
        imagen = canonicalize_existing_image(imagen)
    else:
        imagen = ruta_imagen_relativa(slug, datos["tipo"])
        if not imagen:
            raise ValueError(
                "No hay imagen editorial. La publicación requiere una imagen local antes de aprobarse."
            )
        imagen = canonical_relative_path(imagen)

    contexto = {
        **datos,

        "slug": slug,

        "imagen": imagen,

        "fecha_legible": fecha_legible(),

        "minutos_lectura": minutos,

        "relacionados": relacionados,
    }

    if datos["tipo"] == "noticia":

        plantilla_nombre = (
            "noticia.html.j2"
        )

    else:

        plantilla_nombre = (
            "guia.html.j2"
        )

    plantilla = env.get_template(
        plantilla_nombre
    )

    html_final = plantilla.render(
        **contexto
    )

    ruta_html = BASE / f"{slug}.html"

    ruta_html.write_text(
        html_final,
        encoding="utf-8",
        newline="\n"
    )

    print(
        f"[ok] generado "
        f"{slug}.html "
        f"({datos['tipo']})"
    )

    return {
        "slug": slug,

        "titulo": datos[
            "titulo"
        ],

        "tipo": datos[
            "tipo"
        ],

        "categoria": datos[
            "categoria"
        ],

        "resumen_meta": datos[
            "resumen_meta"
        ],

        "imagen": imagen,

        "fuente_nombre": datos.get(
            "fuente_nombre",
            ""
        ),

        "fuente_url": datos.get(
            "fuente_url",
            ""
        ),
    }


# ============================================================================
# TARJETAS
# ============================================================================

TARJETA_TMPL = """
<article class="review-card">
<img src="{imagen}"
     alt="{titulo}"
     loading="lazy">
<div>
<span class="tag">{categoria}</span>
<h2>
<a href="{slug}.html">{titulo}</a>
</h2>
<p>{resumen_meta}</p>
</div>
</article>
"""


def crear_tarjeta(
    entrada: dict
) -> str:

    titulo = html.escape(
        str(
            entrada.get(
                "titulo",
                ""
            )
        ),
        quote=True
    )

    categoria = html.escape(
        str(
            entrada.get(
                "categoria",
                "Tecnologia"
            )
        ),
        quote=True
    )

    resumen = html.escape(
        str(
            entrada.get(
                "resumen_meta",
                ""
            )
        ),
        quote=True
    )

    slug = entrada[
        "slug"
    ]

    imagen = html.escape(
        str(
            entrada.get(
                "imagen",
                ruta_imagen_relativa(slug, entrada.get("tipo", "noticia"))
            )
        ),
        quote=True
    )

    return TARJETA_TMPL.format(
        slug=slug,
        titulo=titulo,
        categoria=categoria,
        resumen_meta=resumen,
        imagen=imagen,
    ).strip()


# ============================================================================
# RECONSTRUIR LISTADOS
# ============================================================================

def reconstruir_listado(
    pagina: str,
    articulos: list[dict],
    maximo: int,
    marca_inicio: str,
    marca_fin: str,
) -> None:

    ruta = BASE / pagina

    if not ruta.exists():

        print(
            f"[aviso] No existe {pagina}; "
            "no se puede actualizar."
        )

        return

    contenido = ruta.read_text(
        encoding="utf-8"
    )

    inicio = contenido.find(
        marca_inicio
    )

    fin = contenido.find(
        marca_fin
    )

    if inicio == -1 or fin == -1:

        print(
            f"[aviso] No se encontraron "
            f"las marcas de {pagina}."
        )

        return

    fin += len(
        marca_fin
    )

    recientes = [
        a
        for a in articulos
        if isinstance(a, dict)
    ][-maximo:]

    tarjetas = "\n"

    if not recientes:
        tarjetas = '<div class="repair-empty">Aún no hay publicaciones en esta sección.</div>\n'

    # Más reciente primero.
    for entrada in reversed(
        recientes
    ):

        tarjetas += (
            crear_tarjeta(
                entrada
            )
            + "\n"
        )

    bloque = (
        marca_inicio
        + tarjetas
        + marca_fin
    )

    nuevo_contenido = (
        contenido[:inicio]
        + bloque
        + contenido[fin:]
    )

    ruta.write_text(
        nuevo_contenido,
        encoding="utf-8",
        newline="\n"
    )

    print(
        f"[ok] actualizado {pagina}: "
        f"{len(recientes)} tarjeta(s)"
    )


def reconstruir_listados(
    estado: dict
) -> None:

    articulos = estado.get(
        "articulos",
        []
    )

    noticias = [
        a
        for a in articulos
        if a.get("tipo") == "noticia"
    ]

    guias = [
        a
        for a in articulos
        if a.get("tipo") == "guia"
    ]

    reconstruir_listado(
        pagina="noticias.html",

        articulos=noticias,

        maximo=MAX_NOTICIAS_EN_PORTADA,

        marca_inicio=(
            "<!-- NOTICIAS_GRID_START -->"
        ),

        marca_fin=(
            "<!-- NOTICIAS_GRID_END -->"
        ),
    )

    reconstruir_listado(
        pagina="resenas.html",

        articulos=guias,

        maximo=MAX_GUIAS_EN_PORTADA,

        marca_inicio=(
            "<!-- ARTICULOS_AUTO_START -->"
        ),

        marca_fin=(
            "<!-- ARTICULOS_AUTO_END -->"
        ),
    )


# ============================================================================
# PORTADA (index.html) - CONTENIDO ROTATIVO
# ============================================================================

def _reemplazar_entre_marcas(
    contenido: str,
    marca_inicio: str,
    marca_fin: str,
    nuevo_bloque: str,
) -> str | None:
    inicio = contenido.find(marca_inicio)
    fin = contenido.find(marca_fin)
    if inicio == -1 or fin == -1:
        return None
    fin += len(marca_fin)
    return contenido[:inicio] + marca_inicio + nuevo_bloque + marca_fin + contenido[fin:]


def reconstruir_home(estado: dict, maximo_lista: int = 6) -> None:
    """Actualiza index.html con el contenido publicado más reciente
    (noticias + guías mezcladas), para que la portada deje de ser estática."""

    ruta = BASE / "index.html"
    if not ruta.exists():
        print("[aviso] No existe index.html; no se puede actualizar la portada.")
        return

    articulos = [a for a in estado.get("articulos", []) if isinstance(a, dict)]
    if not articulos:
        print("[info] Sin artículos todavía; la portada queda sin cambios.")
        return

    recientes = list(reversed(articulos))  # más nuevo primero
    destacado = recientes[0]
    lista = recientes[1 : 1 + maximo_lista]
    sidebar = recientes[: max(5, 1)][:5]

    def esc(v):
        return html.escape(str(v or ""), quote=True)

    # --- Hero destacado ---
    tipo = destacado.get("tipo")
    eyebrow = "NOTICIA DESTACADA" if tipo == "noticia" else "GUÍA DESTACADA"
    accion = "la noticia" if tipo == "noticia" else "la guía"
    hero_html = (
        f'<div><p class="eyebrow-plain">{eyebrow}</p>'
        f'<h1>{esc(destacado.get("titulo"))}</h1>'
        f'<p class="dek">{esc(destacado.get("resumen_meta"))}</p>'
        f'<p class="hero-meta">Por el equipo de NúcleoTech · {esc(destacado.get("categoria"))}</p>'
        f'<a class="btn" href="{destacado.get("slug")}.html">Leer {accion}</a></div>'
        f'<img class="hero-image" src="{esc(destacado.get("imagen") or ruta_imagen_relativa(destacado.get("slug"), destacado.get("tipo", "noticia")))}" '
        f'alt="{esc(destacado.get("titulo"))}" loading="eager">'
    )

    # --- Últimas publicaciones ---
    filas = []
    for a in lista:
        tipo_legible = "Noticia" if a.get("tipo") == "noticia" else "Guía"
        filas.append(
            '<article class="article-row">'
            f'<img class="article-thumb" src="{esc(a.get("imagen") or ruta_imagen_relativa(a.get("slug"), a.get("tipo", "noticia")))}" '
            f'alt="{esc(a.get("titulo"))}" loading="lazy">'
            f'<div><p class="category">{esc(a.get("categoria"))}</p>'
            f'<h3><a href="{a.get("slug")}.html">{esc(a.get("titulo"))}</a></h3>'
            f'<p>{esc(a.get("resumen_meta"))}</p>'
            f'<p class="meta">{tipo_legible}</p></div></article>'
        )
    lista_html = "\n".join(filas)

    # --- Sidebar "recién publicado" ---
    items = []
    for i, a in enumerate(sidebar, start=1):
        items.append(
            f'<li><span class="num">{i:03d}</span>'
            f'<a href="{a.get("slug")}.html">{esc(a.get("titulo"))}</a></li>'
        )
    sidebar_html = "\n".join(items)

    contenido = ruta.read_text(encoding="utf-8")

    for marca_i, marca_f, bloque in [
        ("<!-- HERO_DESTACADO_START -->", "<!-- HERO_DESTACADO_END -->", hero_html),
        ("<!-- ULTIMAS_PUBLICACIONES_START -->", "<!-- ULTIMAS_PUBLICACIONES_END -->", lista_html),
        ("<!-- RECIENTES_SIDEBAR_START -->", "<!-- RECIENTES_SIDEBAR_END -->", sidebar_html),
    ]:
        nuevo = _reemplazar_entre_marcas(contenido, marca_i, marca_f, "\n" + bloque + "\n")
        if nuevo is None:
            print(f"[aviso] No se encontraron las marcas {marca_i} en index.html")
            continue
        contenido = nuevo

    ruta.write_text(contenido, encoding="utf-8", newline="\n")
    print(f"[ok] portada (index.html) actualizada con lo más reciente: {destacado.get('titulo')}")


# ============================================================================
# ESTADO
# ============================================================================

def normalizar_estado(
    estado: dict
) -> dict:

    if not isinstance(
        estado,
        dict
    ):
        estado = {}

    if not isinstance(
        estado.get(
            "noticias_publicadas"
        ),
        list
    ):

        estado[
            "noticias_publicadas"
        ] = []

    if not isinstance(
        estado.get(
            "articulos"
        ),
        list
    ):

        estado[
            "articulos"
        ] = []

    if not isinstance(
        estado.get(
            "noticias_en_revision"
        ),
        list
    ):
        estado[
            "noticias_en_revision"
        ] = []

    try:

        estado[
            "indice_guia_siguiente"
        ] = int(
            estado.get(
                "indice_guia_siguiente",
                0
            )
        )

    except (
        TypeError,
        ValueError
    ):

        estado[
            "indice_guia_siguiente"
        ] = 0

    return estado


# ============================================================================
# RESUMEN PARA GITHUB
# ============================================================================

def escribir_resumen_notificacion(
    generados: list[dict]
) -> None:

    sitio = (
        "https://nucleo-tech.org"
    )

    accion = "generaron para revisión" if MODO_BORRADOR else "publicaron"
    lineas = [
        (
            f"Se {accion} **"
            f"{len(generados)}"
            f" pieza(s) nuevas hoy:"
        ),
        "",
    ]

    for generado in generados:

        etiqueta = (
            "Noticia"
            if generado["tipo"] == "noticia"
            else "Guia"
        )

        if MODO_BORRADOR:
            lineas.append(
                f"- **[{etiqueta}]** {generado['titulo']} "
                f"— revisar en `automation/drafts/pending/`."
            )
        else:
            url = (
                f"{sitio}/"
                f"{generado['slug']}.html"
            )
            lineas.append(
                f"- **[{etiqueta}]** "
                f"[{generado['titulo']}]"
                f"({url})"
            )

    resumen = (
        "\n".join(lineas)
        + "\n"
    )

    resumen_path = Path(
        "/tmp/nucleotech_resumen.md"
    )

    resumen_path.write_text(
        resumen,
        encoding="utf-8",
        newline="\n"
    )

    # GitHub Actions Step Summary.
    resumen_paso = os.environ.get(
        "GITHUB_STEP_SUMMARY"
    )

    if resumen_paso:

        with open(
            resumen_paso,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                "\n"
                + resumen
            )


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:

    print("=" * 70)

    print(
        "NUCLEOTECH - GENERADOR DIARIO"
    )

    print("=" * 70)

    print(
        f"[config] Noticias diarias: "
        f"{NUM_NOTICIAS}"
    )

    print(
        f"[config] Generar guia: "
        f"{GENERAR_GUIA}"
    )

    print(
        f"[config] Modelo Ollama: "
        f"{OLLAMA_MODEL}"
    )
    print(
        f"[config] Modo borrador: "
        f"{MODO_BORRADOR}"
    )

    print("=" * 70)

    # ----------------------------------------------------------------------
    # Estado
    # ----------------------------------------------------------------------

    estado = cargar_json(
        ESTADO_PATH,

        {
            "noticias_publicadas": [],
            "noticias_en_revision": [],
            "indice_guia_siguiente": 0,
            "articulos": [],
        }
    )

    estado = normalizar_estado(
        estado
    )

    # Migración de artículos existentes: todos reciben una ruta de imagen
    # única para que noticia, listado y portada siempre coincidan.
    estado["articulos"] = [
        normalizar_imagen_estado(a)
        for a in estado.get("articulos", [])
        if isinstance(a, dict)
    ]

    # ----------------------------------------------------------------------
    # Entorno Jinja
    # ----------------------------------------------------------------------

    env = Environment(
        loader=FileSystemLoader(
            str(TEMPLATES_DIR)
        ),

        autoescape=False,
    )

    # ----------------------------------------------------------------------
    # Comprobar Ollama
    # ----------------------------------------------------------------------

    comprobar_ollama()

    generados = []

    # ======================================================================
    # NOTICIAS
    # ======================================================================

    print("")
    print(
        ">>> BUSCANDO NOTICIAS NUEVAS"
    )

    crudas = obtener_noticias_nuevas(
        estado
    )

    if not crudas:

        print(
            "[info] No hay noticias nuevas "
            "en los feeds configurados."
        )

    for cruda in crudas:

        try:

            print("")
            print(
                f"[generando] "
                f"{cruda['titulo_original']}"
            )

            datos = generar_noticia(
                cruda
            )

            if MODO_BORRADOR:
                guardar_borrador(datos, cruda)
                if cruda["link"] not in estado["noticias_en_revision"]:
                    estado["noticias_en_revision"].append(cruda["link"])
                generados.append({
                    "titulo": datos["titulo"],
                    "tipo": "noticia",
                    "slug": slugify(datos["titulo"]),
                })
            else:
                entrada = render_y_guardar(
                    datos,
                    estado,
                    env
                )
                if cruda["link"] not in estado["noticias_publicadas"]:
                    estado["noticias_publicadas"].append(cruda["link"])
                estado["articulos"].append(entrada)
                generados.append(entrada)

        except Exception as e:

            print(
                "[error] fallo generando "
                f"noticia "
                f"'{cruda['titulo_original']}': "
                f"{e}"
            )

    # ======================================================================
    # GUIA
    # ======================================================================

    if GENERAR_GUIA:

        print("")
        print(
            ">>> GENERANDO GUIA"
        )

        config_temas = cargar_json(
            CONFIG_TEMAS,
            {"temas": []}
        )

        temas = config_temas.get(
            "temas",
            []
        )

        if not temas:

            print(
                "[aviso] No hay temas "
                "de guia configurados."
            )

        else:

            idx = (
                estado[
                    "indice_guia_siguiente"
                ]
                % len(temas)
            )

            tema = temas[idx]

            try:

                print(
                    f"[guia] Tema "
                    f"{idx + 1}/{len(temas)}: "
                    f"{tema['titulo']}"
                )

                datos = generar_guia(
                    tema
                )

                if MODO_BORRADOR:
                    guardar_borrador(datos)
                    estado["indice_guia_siguiente"] = (idx + 1) % len(temas)
                    generados.append({
                        "titulo": datos["titulo"],
                        "tipo": "guia",
                        "slug": slugify(datos["titulo"]),
                    })
                else:
                    entrada = render_y_guardar(
                        datos,
                        estado,
                        env
                    )
                    estado["indice_guia_siguiente"] = (idx + 1) % len(temas)
                    estado["articulos"].append(entrada)
                    generados.append(entrada)

            except Exception as e:

                print(
                    "[error] fallo generando "
                    f"guia "
                    f"'{tema['titulo']}': "
                    f"{e}"
                )

    # ======================================================================
    # LIMPIEZA Y NORMALIZACION DEL ESTADO
    # ======================================================================

    estado[
        "articulos"
    ] = estado[
        "articulos"
    ][-MAX_ARTICULOS_ESTADO:]

    estado[
        "noticias_publicadas"
    ] = list(
        dict.fromkeys(
            estado[
                "noticias_publicadas"
            ]
        )
    )[-MAX_NOTICIAS_PUBLICADAS:]

    # ======================================================================
    # ACTUALIZAR NOTICIAS.HTML Y RESENAS.HTML
    # ======================================================================

    if not MODO_BORRADOR:
        print("")
        print(">>> ACTUALIZANDO LISTADOS")
        reconstruir_listados(estado)
        reconstruir_home(estado)
    else:
        print("")
        print("[revision] Los borradores NO se publican automaticamente.")
        print('[revision] Añade la imagen al repositorio, completa el campo "imagen" y mueve el JSON a drafts/approved/.')

    # ======================================================================
    # GUARDAR ESTADO
    # ======================================================================

    guardar_json(
        ESTADO_PATH,
        estado
    )

    print(
        f"[ok] Estado guardado en "
        f"{ESTADO_PATH}"
    )

    # ======================================================================
    # RESUMEN
    # ======================================================================

    print("")
    print("=" * 70)

    if generados:

        print(
            f"[resumen] "
            f"{len(generados)} pieza(s) "
            f"publicada(s) hoy:"
        )

        for generado in generados:

            print(
                f"  - "
                f"({generado['tipo']}) "
                f"{generado['titulo']} "
                f"-> "
                f"{generado['slug']}.html"
            )

        escribir_resumen_notificacion(
            generados
        )

    else:

        print(
            "[resumen] "
            "No se genero contenido nuevo hoy."
        )

        # Crear igualmente el archivo para que
        # el workflow no encuentre un resumen
        # antiguo de otra ejecución.
        Path(
            "/tmp/nucleotech_resumen.md"
        ).write_text(
            "",
            encoding="utf-8"
        )

    print("=" * 70)


# ============================================================================
# EJECUCION
# ============================================================================

if __name__ == "__main__":
    main()