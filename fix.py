#!/usr/bin/env python3
"""
fix_mojibake.py
----------------
Repara texto con problemas de doble codificacion (mojibake) - las tildes,
enies y signos que aparecen como caracteres raros tipo "Ã©", "Ã±", "â€”" -
en TODOS los archivos de texto de un proyecto, recursivamente.

USO:
    python fix_mojibake.py "C:\\ruta\\a\\tu\\proyecto"
    python fix_mojibake.py /ruta/a/tu/proyecto
    python fix_mojibake.py            (usa la carpeta actual si no pasas ruta)

REQUISITO (una sola vez):
    pip install ftfy

RECOMENDACION:
    Corre esto sobre un proyecto que ya este en Git (o con un backup hecho).
    Asi, si algo no te convence, revisas el diff con "git diff" y puedes
    revertir con "git checkout -- ." si hace falta.
"""
import sys
import os

try:
    import ftfy
except ImportError:
    sys.exit("Falta la libreria ftfy. Instalala con:\n    pip install ftfy")

# Extensiones de archivo que se revisaran (agrega mas si te faltan)
EXTENSIONES = {
    ".html", ".htm", ".css", ".js", ".json", ".txt", ".md",
    ".xml", ".svg", ".j2", ".jinja", ".jinja2", ".yml", ".yaml", ".csv",
}

# Carpetas que se ignoran por completo
IGNORAR_CARPETAS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}


def procesar_archivo(ruta):
    """Devuelve True si el archivo fue corregido, False si no tenia problemas,
    None si no se pudo leer como texto (se salta sin tocar)."""
    try:
        with open(ruta, "r", encoding="utf-8-sig", newline="") as f:
            texto = f.read()
    except (UnicodeDecodeError, PermissionError, OSError):
        return None

    # uncurl_quotes=False para no tocar comillas tipograficas que hayas puesto a proposito
    corregido = ftfy.fix_text(texto, uncurl_quotes=False)

    if corregido != texto:
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            f.write(corregido)
        return True
    return False


def main():
    raiz = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.isdir(raiz):
        sys.exit(f"No encuentro la carpeta: {raiz}")

    modificados = []
    revisados = 0

    for carpeta_actual, subcarpetas, archivos in os.walk(raiz):
        subcarpetas[:] = [d for d in subcarpetas if d not in IGNORAR_CARPETAS]
        for nombre in archivos:
            _, ext = os.path.splitext(nombre)
            if ext.lower() in EXTENSIONES:
                ruta = os.path.join(carpeta_actual, nombre)
                revisados += 1
                if procesar_archivo(ruta):
                    modificados.append(ruta)

    print(f"\nArchivos revisados: {revisados}")
    print(f"Archivos corregidos: {len(modificados)}")
    for r in modificados:
        print("  -", r)
    if not modificados:
        print("No se encontro texto mal codificado en los archivos revisados.")
    else:
        print("\nListo. Revisa los cambios con 'git diff' antes de hacer commit.")


if __name__ == "__main__":
    main()