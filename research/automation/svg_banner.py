"""
Genera un banner SVG original para cada articulo/noticia automatico.
No usa fotos ni imagenes de terceros: solo formas geometricas y texto,
en la paleta de color propia de NucleoTech (ver styles.css :root).
"""
import hashlib
import textwrap

PALETTE = ["#f0ad45", "#45c7b1", "#263443", "#172331"]
BG = "#0a0f16"
TEXT = "#f5f7fa"


def _color_for(seed: str) -> str:
    h = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16)
    return PALETTE[h % len(PALETTE)]


def _wrap_title(title: str, width: int = 26) -> list[str]:
    return textwrap.wrap(title, width=width)[:3]


def build_banner_svg(title: str, tag: str, seed: str) -> str:
    """Devuelve el XML de un SVG 1400x700 con figuras geometricas + titulo."""
    accent = _color_for(seed)
    accent2 = _color_for(seed + "2")
    lines = _wrap_title(title)
    line_h = 64
    start_y = 700 // 2 - (len(lines) - 1) * line_h // 2

    text_svg = "".join(
        f'<text x="80" y="{start_y + i * line_h}" font-family="Space Grotesk, system-ui, sans-serif" '
        f'font-size="46" font-weight="700" fill="{TEXT}">{_escape(l)}</text>'
        for i, l in enumerate(lines)
    )

    shapes = f"""
    <circle cx="1180" cy="140" r="180" fill="{accent}" opacity="0.18"/>
    <circle cx="1260" cy="520" r="120" fill="{accent2}" opacity="0.22"/>
    <rect x="0" y="0" width="10" height="700" fill="{accent}"/>
    """

    return f"""<svg viewBox="0 0 1400 700" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{_escape(title)}">
<rect width="1400" height="700" fill="{BG}"/>
{shapes}
<text x="80" y="{start_y - line_h}" font-family="DM Sans, system-ui, sans-serif" font-size="26" font-weight="700"
 letter-spacing="2" fill="{accent}">{_escape(tag.upper())}</text>
{text_svg}
<text x="80" y="640" font-family="DM Sans, system-ui, sans-serif" font-size="22" fill="#9eabb8">NucleoTech</text>
</svg>"""


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
