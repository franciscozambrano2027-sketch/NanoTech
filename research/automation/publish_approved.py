#!/usr/bin/env python3
"""
Publica manualmente los borradores aprobados de NúcleoTech.

Flujo:
1. automation genera JSON en drafts/pending/.
2. Revisa el texto.
3. Coloca la imagen elegida dentro del proyecto y escribe su ruta en "imagen".
4. Mueve el JSON a drafts/approved/.
5. Ejecuta este script (o el workflow "Publicar aprobados").
6. Se genera el HTML, se actualizan noticias.html/resenas.html/index.html y se guarda estado.

No publica nada que permanezca en drafts/pending/.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from generate_content import (
    BASE,
    ESTADO_PATH,
    TEMPLATES_DIR,
    cargar_json,
    guardar_json,
    normalizar_estado,
    render_y_guardar,
    reconstruir_listados,
    reconstruir_home,
    ruta_imagen_relativa,
)

AUTO = Path(__file__).resolve().parent
APPROVED_DIR = AUTO / "drafts" / "approved"
PUBLISHED_DIR = AUTO / "drafts" / "published"


def validar_imagen(draft: dict) -> str:
    imagen = str(draft.get("imagen", "")).strip()

    if not imagen:
        return ""

    if imagen.startswith(("http://", "https://")):
        raise ValueError(
            "La imagen debe ser un archivo local del proyecto. "
            "Usa una ruta como imagenes/noticias/mi-imagen.jpg."
        )

    ruta = (BASE / imagen).resolve()

    if BASE.resolve() not in ruta.parents and ruta != BASE.resolve():
        raise ValueError("La ruta de imagen sale del directorio del sitio.")

    if not ruta.exists() or not ruta.is_file():
        raise FileNotFoundError(
            f"No existe la imagen indicada: {imagen}"
        )

    return imagen


def publicar_draft(path: Path, estado: dict, env: Environment) -> dict:
    draft = json.loads(path.read_text(encoding="utf-8"))

    if draft.get("estado") not in ("pendiente", "aprobado", None):
        raise ValueError(f"Estado no publicable en {path.name}: {draft.get('estado')}")

    imagen = validar_imagen(draft)

    datos = {
        "titulo": str(draft.get("titulo", "")).strip(),
        "resumen_meta": str(draft.get("resumen_meta", "")).strip(),
        "cuerpo_html": str(draft.get("cuerpo_html", "")).strip(),
        "categoria": str(draft.get("categoria", "Tecnologia")).strip(),
        "tipo": str(draft.get("tipo", "noticia")).strip(),
        "fuente_nombre": str(draft.get("fuente_nombre", "")).strip(),
        "fuente_url": str(draft.get("fuente_url", "")).strip(),
    }

    if not datos["titulo"] or not datos["cuerpo_html"]:
        raise ValueError(f"El borrador {path.name} no tiene título o contenido.")

    if imagen:
        datos["imagen"] = imagen

    entrada = render_y_guardar(datos, estado, env)

    # El origen RSS deja de estar "en revisión" y pasa al historial de publicadas.
    origen = draft.get("origen") or {}
    fuente_url = str(origen.get("fuente_url") or datos.get("fuente_url") or "").strip()

    if fuente_url:
        estado["noticias_en_revision"] = [
            u for u in estado.get("noticias_en_revision", [])
            if u != fuente_url
        ]
        if fuente_url not in estado["noticias_publicadas"]:
            estado["noticias_publicadas"].append(fuente_url)

    estado["articulos"].append(entrada)

    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
    destino = PUBLISHED_DIR / path.name
    path.rename(destino)

    print(f"[publicado] {entrada['slug']}.html")
    print(f"[borrador] archivado en {destino.relative_to(BASE)}")

    return entrada


def main() -> None:
    APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)

    estado = normalizar_estado(
        cargar_json(
            ESTADO_PATH,
            {
                "noticias_publicadas": [],
                "noticias_en_revision": [],
                "indice_guia_siguiente": 0,
                "articulos": [],
            },
        )
    )

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
    )

    drafts = sorted(APPROVED_DIR.glob("*.json"))

    if not drafts:
        print("[info] No hay borradores aprobados para publicar.")
        return

    publicados = []

    for draft in drafts:
        try:
            publicados.append(publicar_draft(draft, estado, env))
        except Exception as exc:
            print(f"[error] No se pudo publicar {draft.name}: {exc}")

    if not publicados:
        print("[info] No se publicó ningún borrador.")
        return

    estado["articulos"] = estado["articulos"][-500:]
    estado["noticias_publicadas"] = list(dict.fromkeys(estado["noticias_publicadas"]))[-1000:]
    estado["noticias_en_revision"] = list(dict.fromkeys(estado["noticias_en_revision"]))[-1000:]

    reconstruir_listados(estado)
    reconstruir_home(estado)
    guardar_json(ESTADO_PATH, estado)

    resumen = Path("/tmp/nucleotech_resumen.md")
    resumen.write_text(
        "Se publicaron manualmente las siguientes piezas:\n\n"
        + "\n".join(
            f"- {a['titulo']} — https://nucleo-tech.org/{a['slug']}.html"
            for a in publicados
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"[ok] {len(publicados)} borrador(es) publicado(s).")


if __name__ == "__main__":
    main()
