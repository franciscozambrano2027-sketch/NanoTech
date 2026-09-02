"""Utilidades para mantener rutas de imágenes de NúcleoTech consistentes.

Regla del sitio: las imágenes publicadas viven en ./imagenes/ y se referencian
siempre con rutas relativas POSIX, sin barra inicial, sin espacios ni caracteres
Unicode problemáticos. Ejemplo: imagenes/mikrotik/diagnostico-dns/1-probar-ip-publica.jpg
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote

BASE = Path(__file__).resolve().parent.parent
IMAGE_ROOT = BASE / "imagenes"


def _decode_u00(value: str) -> str:
    # Corrige nombres heredados que contienen literalmente #U00f3, #U00e1, etc.
    return re.sub(r"#U([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), value)


def _safe_part(value: str, *, filename: bool = False) -> str:
    value = _decode_u00(value)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    if filename:
        suffix = Path(value).suffix.lower()
        stem = Path(value).stem
        stem = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").lower() or "archivo"
        return stem + suffix
    return re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower() or "carpeta"


def canonical_relative_path(raw: str) -> str:
    """Devuelve la forma canónica de una ruta que pertenece a ./imagenes/."""
    value = unquote(str(raw or "")).strip().replace("\\", "/")
    value = value.lstrip("/")
    if not value.startswith("imagenes/"):
        raise ValueError("La imagen debe estar dentro de imagenes/.")
    parts = [p for p in value.split("/") if p not in ("", ".")]
    if len(parts) < 2 or parts[0] != "imagenes":
        raise ValueError("Ruta de imagen no válida.")
    out = ["imagenes"]
    for index, part in enumerate(parts[1:], start=1):
        out.append(_safe_part(part, filename=index == len(parts) - 1))
    return "/".join(out)


def canonicalize_existing_image(raw: str) -> str:
    """Valida una imagen local y, si hace falta, la renombra a la ruta canónica."""
    value = unquote(str(raw or "")).strip().replace("\\", "/")
    if value.startswith(("http://", "https://", "data:")):
        raise ValueError("Las imágenes editoriales deben ser archivos locales del proyecto.")

    value = value.lstrip("/")
    if not value.startswith("imagenes/"):
        raise ValueError("La imagen debe estar dentro de imagenes/, no en research/imagenes/ ni en otra carpeta.")

    source = (BASE / value).resolve()
    base = BASE.resolve()
    if base not in source.parents or not source.is_file():
        raise FileNotFoundError(f"No existe la imagen indicada: {raw}")

    canonical = canonical_relative_path(value)
    target = (BASE / canonical).resolve()
    if base not in target.parents:
        raise ValueError("La ruta canónica de la imagen sale del proyecto.")

    if source != target:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(
                f"No se puede normalizar {value}: ya existe {canonical}."
            )
        source.rename(target)

    return canonical
