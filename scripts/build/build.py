"""Build mínimo de contenido editorial de NúcleoTech.

Fase 1: genera una copia de los artículos migrados en _build/.
No modifica los HTML publicados de la raíz.
"""
from pathlib import Path
import json, html, re, shutil

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "_build"
SITE = json.loads((ROOT/"data/site.json").read_text(encoding="utf-8"))
AUTHORS = {a["id"]: a["name"] for a in json.loads((ROOT/"data/authors.json").read_text(encoding="utf-8"))["authors"]}

def esc(v):
    return html.escape(str(v), quote=True)

def render(template, values):
    for key, value in values.items():
        template = template.replace("{{"+key+"}}", str(value))
    return template

def related_html(items):
    out=[]
    for i,item in enumerate(items,1):
        out.append(f'<li><span class="num">{i:02d}</span><a href="{esc(item["url"])}">{esc(item["title"])}</a></li>')
    return "\n".join(out)

def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    template=(ROOT/"templates/articles/review.html").read_text(encoding="utf-8")
    count=0
    for path in sorted((ROOT/"content/articles").rglob("*.json")):
        article=json.loads(path.read_text(encoding="utf-8"))
        if article.get("status") != "published":
            continue
        if article.get("type") != "review":
            continue
        updated=article.get("updated_at","")
        updated_label=" ".join(updated.split("-")[:2]) if updated else "sin fecha"
        values={
            "site.language":esc(SITE["site"]["language"]),
            "site.name":esc(SITE["site"]["name"]),
            "adsense":'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5675726602507111" crossorigin="anonymous"></script>',
            "title":esc(article["title"]),
            "description":esc(article["description"]),
            "canonical":esc(article["seo"]["canonical"]),
            "subcategory":esc(article.get("subcategory","")),
            "author":esc(AUTHORS.get(article.get("author_id"),article.get("author_id",""))),
            "updated_label":esc(updated_label),
            "reading_time":esc(article.get("reading_time","")),
            "hero_image":esc(article["hero"]["image"]),
            "hero_alt":esc(article["hero"]["alt"]),
            "content_html":article["content_html"],
            "related":related_html(article.get("sidebar",{}).get("related",[])),
        }
        rendered=render(template,values)
        (OUT/f"{article['slug']}.html").write_text(rendered,encoding="utf-8")
        count+=1
    print(f"Build completado: {count} artículo(s) en {OUT}")

if __name__=="__main__":
    main()
