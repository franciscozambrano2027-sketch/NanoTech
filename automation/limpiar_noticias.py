#!/usr/bin/env python3
"""
Limpieza controlada de noticias antiguas de NucleoTech.

Elimina:
- Archivos HTML de noticias antiguas.
- Banners SVG asociados.
- Tarjetas correspondientes en noticias.html.
- Las URLs correspondientes de estado.json.
- Las entradas correspondientes de estado["articulos"].

NO modifica:
- Las guías.
- resenas.html.
- temas_guias.json.
- feeds.json.
- La configuración del automatizador.

Antes de borrar, crea un respaldo automático de estado.json y noticias.html.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
ESTADO_PATH = BASE / "automation" / "estado" / "estado.json"
NOTICIAS_PATH = BASE / "noticias.html"
IMG_AUTO_DIR = BASE / "imagenes" / "auto"


# ---------------------------------------------------------------------------
# Noticias que queremos retirar
# ---------------------------------------------------------------------------

SLUGS_ELIMINAR = {
    "como-nintendo-se-convirtio-en-una-empresa-de-diversion-global",
    "la-verdadera-magnitud-del-crecimiento-exponencial",
    "por-que-las-ballenas-no-pueden-volver-a-caminar-sobre-la-tierra",
    "un-arbol-de-utah-que-ha-vivido-durante-80-000-anos",
    "el-kailash-el-monte-magico-que-nadie-ha-escalado",
    "descubren-un-tesoro-de-mas-de-2-600-monedas-en-una-ciudad-rusa-medieva",
    "descubre-el-gimnasio-mas-inusual-de-espana-donde-el-chatarra-es-el-mat",
    "rafa-nadal-la-historia-detras-de-la-empresa-de-cristales-de-baleares-q",
    "la-saga-de-hobonichi-techo-por-que-las-agendas-japonesas-estan-conquis",
    "la-recuperacion-del-desierto-norteamericano-un-exito-de-conservacion",
    "amancio-ortega-vende-acciones-de-pontegadea-a-una-compania-estatal-por",
    "la-nasa-se-enfrenta-a-una-desorbitacion-inminente-para-su-telescopio-s",
    "ee-uu-amplia-su-presencia-militar-en-espana",
    "la-sequia-obliga-a-francia-a-reinventar-sus-quesos-mas-famosos",
}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def cargar_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_json(path: Path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def hacer_backup(path: Path):
    backup = path.with_suffix(path.suffix + ".backup")
    shutil.copy2(path, backup)
    return backup


def slug_desde_url(url: str) -> str | None:
    """
    Intenta obtener el slug de una URL del sitio.
    """
    if not url:
        return None

    nombre = url.rstrip("/").split("/")[-1]

    if nombre.endswith(".html"):
        nombre = nombre[:-5]

    if nombre:
        return nombre

    return None


# ---------------------------------------------------------------------------
# Eliminar archivos
# ---------------------------------------------------------------------------

def eliminar_archivos():
    eliminados = []

    for slug in sorted(SLUGS_ELIMINAR):
        html = BASE / f"{slug}.html"
        svg = IMG_AUTO_DIR / f"{slug}.svg"

        if html.exists():
            html.unlink()
            eliminados.append(str(html.relative_to(BASE)))

        if svg.exists():
            svg.unlink()
            eliminados.append(str(svg.relative_to(BASE)))

    return eliminados


# ---------------------------------------------------------------------------
# Limpiar estado.json
# ---------------------------------------------------------------------------

def limpiar_estado():
    estado = cargar_json(ESTADO_PATH)

    noticias_publicadas_original = estado.get("noticias_publicadas", [])
    articulos_original = estado.get("articulos", [])

    # Eliminar del historial de URLs aquellas noticias que estamos retirando.
    noticias_publicadas_nuevas = []

    for url in noticias_publicadas_original:
        slug = slug_desde_url(url)

        if slug in SLUGS_ELIMINAR:
            continue

        noticias_publicadas_nuevas.append(url)

    # Eliminar únicamente artículos tipo noticia que correspondan
    # a los slugs antiguos.
    articulos_nuevos = []

    for articulo in articulos_original:
        slug = articulo.get("slug", "")
        tipo = articulo.get("tipo", "")

        if tipo == "noticia" and slug in SLUGS_ELIMINAR:
            continue

        articulos_nuevos.append(articulo)

    estado["noticias_publicadas"] = noticias_publicadas_nuevas
    estado["articulos"] = articulos_nuevos

    guardar_json(ESTADO_PATH, estado)

    return (
        len(noticias_publicadas_original) - len(noticias_publicadas_nuevas),
        len(articulos_original) - len(articulos_nuevos),
    )


# ---------------------------------------------------------------------------
# Limpiar tarjetas de noticias.html
# ---------------------------------------------------------------------------

def limpiar_noticias_html():
    if not NOTICIAS_PATH.exists():
        print("[aviso] No existe noticias.html")
        return 0

    contenido = NOTICIAS_PATH.read_text(encoding="utf-8")

    eliminadas = 0

    # Busca cada <article class="review-card">...</article>
    patron = re.compile(
        r'<article\s+class="review-card">.*?</article>',
        re.IGNORECASE | re.DOTALL,
    )

    def reemplazar(match):
        nonlocal eliminadas

        tarjeta = match.group(0)

        for slug in SLUGS_ELIMINAR:
            if f'href="{slug}.html"' in tarjeta:
                eliminadas += 1
                return ""

        return tarjeta

    nuevo_contenido = patron.sub(reemplazar, contenido)

    NOTICIAS_PATH.write_text(
        nuevo_contenido,
        encoding="utf-8",
        newline="\n",
    )

    return eliminadas


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("LIMPIEZA DE NOTICIAS ANTIGUAS - NUCLEOTECH")
    print("=" * 70)
    print()

    print(f"Noticias marcadas para eliminar: {len(SLUGS_ELIMINAR)}")
    print()

    # Verificar archivos principales antes de modificar.
    if not ESTADO_PATH.exists():
        raise FileNotFoundError(f"No existe: {ESTADO_PATH}")

    if not NOTICIAS_PATH.exists():
        raise FileNotFoundError(f"No existe: {NOTICIAS_PATH}")

    # Backups.
    backup_estado = hacer_backup(ESTADO_PATH)
    backup_noticias = hacer_backup(NOTICIAS_PATH)

    print("[backup] estado.json")
    print(f"         -> {backup_estado.name}")

    print("[backup] noticias.html")
    print(f"         -> {backup_noticias.name}")
    print()

    # Archivos HTML y SVG.
    archivos = eliminar_archivos()

    print(f"[archivos] Eliminados: {len(archivos)}")

    for archivo in archivos:
        print(f"  - {archivo}")

    print()

    # Estado.
    urls_eliminadas, articulos_eliminados = limpiar_estado()

    print(f"[estado] URLs eliminadas: {urls_eliminadas}")
    print(f"[estado] Artículos eliminados: {articulos_eliminados}")
    print()

    # Página principal de noticias.
    tarjetas = limpiar_noticias_html()

    print(f"[pagina] Tarjetas eliminadas de noticias.html: {tarjetas}")
    print()

    print("=" * 70)
    print("LIMPIEZA TERMINADA")
    print("=" * 70)
    print()
    print("Los archivos .backup se conservaron como respaldo.")
    print()
    print("Ahora revisa los cambios con:")
    print()
    print("  git status")
    print("  git diff --check")
    print()
    print("IMPORTANTE: todavía NO hagas commit hasta revisar el diff.")


if __name__ == "__main__":
    main()