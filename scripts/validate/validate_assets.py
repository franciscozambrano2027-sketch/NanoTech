#!/usr/bin/env python3
"""Comprueba que las referencias de imágenes publicables existan y sean canónicas."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

BASE = Path(__file__).resolve().parents[2]
ATTR_RE = re.compile(r'''\b(?:src|poster)\s*=\s*["']([^"']+)["']''', re.I)
CSS_RE = re.compile(r'''url\(\s*["']?([^"')]+)["']?\s*\)''', re.I)

SKIP_PARTS = {".git", "__pycache__", ".backup-analytics"}
SKIP_FILES = {"noticias.html.backup"}


def iter_publishable_files():
    for p in BASE.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_PARTS for part in p.parts):
            continue
        if p.name in SKIP_FILES:
            continue
        if p.suffix.lower() in {".html", ".htm", ".css", ".js", ".py", ".j2", ".json", ".md"}:
            yield p


def main() -> int:
    missing = []
    noncanonical = []
    checked = 0

    for p in iter_publishable_files():
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        values = ATTR_RE.findall(text) + CSS_RE.findall(text)
        for raw in values:
            value = unquote(raw.strip()).replace("\\", "/")
            if value.startswith("/"):
                value = value[1:]
            if not value.startswith("imagenes/"):
                continue
            # Ignore template variables; the rendered page will be validated separately.
            if "{{" in value or "}}" in value:
                continue
            checked += 1
            target = BASE / value
            if not target.is_file():
                missing.append((p.relative_to(BASE).as_posix(), value))
                continue
            parts = value.split("/")
            canonical = []
            import unicodedata
            import re as _re
            for i, part in enumerate(parts):
                if i == 0:
                    canonical.append("imagenes")
                    continue
                v = unicodedata.normalize("NFKD", part).encode("ascii", "ignore").decode("ascii")
                if i == len(parts)-1:
                    stem = Path(v).stem
                    ext = Path(v).suffix.lower()
                    stem = _re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").lower() or "archivo"
                    canonical.append(stem + ext)
                else:
                    canonical.append(_re.sub(r"[^A-Za-z0-9]+", "-", v).strip("-").lower() or "carpeta")
            canonical_value = "/".join(canonical)
            if value != canonical_value:
                noncanonical.append((p.relative_to(BASE).as_posix(), value, canonical_value))

    print(f"[assets] referencias comprobadas: {checked}")
    print(f"[assets] archivos inexistentes: {len(missing)}")
    print(f"[assets] rutas no canónicas: {len(noncanonical)}")

    for item in missing:
        print(f"[MISSING] {item[0]} -> {item[1]}")
    for item in noncanonical:
        print(f"[NONCANONICAL] {item[0]} -> {item[1]} (usar {item[2]})")

    return 1 if missing or noncanonical else 0


if __name__ == "__main__":
    raise SystemExit(main())
