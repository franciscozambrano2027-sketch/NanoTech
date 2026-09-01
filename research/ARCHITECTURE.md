# NúcleoTech — arquitectura editorial

Esta estructura introduce una separación progresiva entre contenido, plantillas,
scripts, configuración y sitio publicado.

## Regla principal

- `content/`: fuente de verdad del contenido editorial.
- `templates/`: presentación y estructura HTML reutilizable.
- `scripts/`: generación, validación y SEO.
- `data/`: configuración global del sitio.
- `research/`: investigación previa a los artículos.
- `drafts/`: contenido en proceso.
- `logs/`: registros de automatización.
- `.github/workflows/`: automatización futura con GitHub Actions.

## Compatibilidad

Durante esta primera fase **no se han movido ni eliminado los HTML existentes**,
ni se han cambiado las rutas públicas. La raíz continúa siendo la zona publicada
por GitHub Pages.

## Próximo paso

Migrar un único artículo existente a `content/articles/`, crear su plantilla y
hacer que el generador produzca el HTML equivalente antes de migrar el resto.

## Nota sobre la automatización de contenido diario (agregado posteriormente)

Se agregó `automation/` con un pipeline independiente que SÍ publica directamente en la
raíz (igual que los HTML existentes), usando un modelo open-source local vía Ollama en
GitHub Actions. Es intencionalmente más simple que el pipeline `content/ + templates/ +
scripts/build` de esta fase 1, que aún no llega a publicar en la raíz. Ver
`automation/README.md` para el detalle. Si en el futuro se retoma la migración a
`content/articles/`, lo natural sería que `automation/generate_content.py` escriba el JSON
del artículo ahí en vez de HTML directo, y delegue el render a `scripts/build/build.py`.
