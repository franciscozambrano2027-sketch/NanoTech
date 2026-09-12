"""Genera sitemap.xml a partir de las páginas HTML públicas de NúcleoTech."""
from pathlib import Path
from datetime import date
from xml.sax.saxutils import escape

BASE = Path(__file__).resolve().parents[2]
SITE = "https://nucleo-tech.org/"
EXCLUDE = {"pc-no-arranca0.html", "disco-externo-vs-ssd.html"}

def main():
    today = date.today().isoformat()
    pages = []
    for p in sorted(BASE.glob("*.html")):
        if p.name in EXCLUDE or p.name.endswith(".backup"):
            continue
        pages.append(p.name)
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    for name in pages:
        loc = SITE if name == "index.html" else SITE + name
        out.append(f'  <url><loc>{escape(loc)}</loc><lastmod>{today}</lastmod></url>')
    out.append('</urlset>')
    (BASE / "sitemap.xml").write_text("\n".join(out)+"\n", encoding="utf-8")
    print(f"Sitemap generado: {len(pages)} URL(s)")

if __name__ == "__main__":
    main()
