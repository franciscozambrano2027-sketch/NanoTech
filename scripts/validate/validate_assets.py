#!/usr/bin/env python3
"""Valida todas las referencias locales a imágenes de NúcleoTech."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote

BASE = Path(__file__).resolve().parents[2]
IMAGE_ROOT = (BASE / "imagenes").resolve()
TEXT_EXTENSIONS = {".html", ".htm", ".css", ".js", ".xml", ".json", ".md", ".j2", ".py", ".yml", ".yaml"}
SKIP_PARTS = {".git", "__pycache__"}
ATTR_RE = re.compile(r'''\b(?:src|href|poster|content|srcset)\s*=\s*(["'])([^"']+)\1''', re.I)
URL_RE = re.compile(r'''url\(\s*["']?([^)"']+)["']?\s*\)''', re.I)
IMAGE_PATH_RE = re.compile(r'''((?:/|(?:\.\.?/)*)imagenes/[^"'`\s<>)},;]+)''', re.I)
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif", ".ico"}


def iter_files():
    for p in BASE.rglob("*"):
        if p.is_file() and not any(part in SKIP_PARTS for part in p.parts) and p.suffix.lower() in TEXT_EXTENSIONS:
            yield p


def is_template(value: str) -> bool:
    return any(x in value for x in ("{{", "}}", "{%", "%}"))


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower() or "archivo"


def canonical_image_path(path: Path) -> str:
    rel = path.resolve().relative_to(BASE.resolve()).as_posix()
    parts = rel.split("/")
    out = ["imagenes"]
    out.extend(normalize(x) for x in parts[1:-1])
    out.append(normalize(Path(parts[-1]).stem) + Path(parts[-1]).suffix.lower())
    return "/".join(out)


def iter_image_refs(value: str):
    for m in IMAGE_PATH_RE.finditer(value):
        raw = unquote(m.group(1)).replace("\\", "/")
        if Path(raw.split("?", 1)[0].split("#", 1)[0]).suffix.lower() in IMAGE_EXTENSIONS:
            yield raw


def resolve_reference(source: Path, raw: str) -> Path:
    clean = raw.split("?", 1)[0].split("#", 1)[0]
    return (BASE / clean.lstrip("/")).resolve() if clean.startswith("/") else (source.parent / clean).resolve()


def main() -> int:
    missing, noncanonical, outside = [], [], []
    checked = 0

    for source in iter_files():
        try:
            text = source.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        values = [m.group(2) for m in ATTR_RE.finditer(text)] + [m.group(1) for m in URL_RE.finditer(text)]
        for value in values:
            if is_template(value):
                continue
            for raw in iter_image_refs(value):
                target = resolve_reference(source, raw)
                try:
                    target.relative_to(BASE.resolve())
                except ValueError:
                    outside.append((source.relative_to(BASE).as_posix(), raw))
                    continue
                try:
                    target.relative_to(IMAGE_ROOT)
                except ValueError:
                    continue

                checked += 1
                if not target.is_file():
                    missing.append((source.relative_to(BASE).as_posix(), raw))
                    continue
                actual = target.relative_to(BASE).as_posix()
                canonical = canonical_image_path(target)
                if actual != canonical:
                    noncanonical.append((source.relative_to(BASE).as_posix(), raw, canonical))

    print(f"[assets] referencias de imagen comprobadas: {checked}")
    print(f"[assets] archivos inexistentes: {len(missing)}")
    print(f"[assets] rutas no canónicas: {len(noncanonical)}")
    print(f"[assets] referencias fuera del proyecto: {len(outside)}")
    for source, raw in missing:
        print(f"[MISSING] {source} -> {raw}")
    for source, raw, canonical in noncanonical:
        print(f"[NONCANONICAL] {source} -> {raw} (usar {canonical})")
    for source, raw in outside:
        print(f"[OUTSIDE] {source} -> {raw}")
    return 1 if missing or noncanonical or outside else 0


if __name__ == "__main__":
    raise SystemExit(main())
