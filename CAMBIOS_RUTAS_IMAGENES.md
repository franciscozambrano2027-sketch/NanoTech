# Corrección de rutas de imágenes — NúcleoTech

## Qué se corrigió

- Se normalizaron los nombres de archivos y carpetas dentro de `imagenes/`.
- Se eliminaron espacios, tildes, caracteres especiales y nombres heredados con secuencias `#U00...`.
- Las referencias de las páginas HTML se actualizaron para apuntar a las nuevas rutas.
- Las imágenes publicadas usan rutas relativas desde la raíz del sitio, por ejemplo:
  `imagenes/telefono/celular-no-carga/celular-no-carga.jpg`
- Se corrigieron las rutas de PS4, Laptop, Celulares y MikroTik.
- La automatización ahora normaliza una imagen editorial al publicar un borrador, siempre que el archivo exista dentro de `imagenes/`.
- Se agregó `scripts/validate/validate_assets.py` para detectar referencias inexistentes o no canónicas.
- GitHub Actions ejecuta esta validación antes de hacer commit/push.

## Regla para futuras imágenes

Guardar las imágenes nuevas dentro de `imagenes/` y preferiblemente con nombres ASCII, minúsculas y guiones:

```text
imagenes/noticias/mi-noticia-2026.png
imagenes/mikrotik/mikrotik-dns/1-probar-ip-publica.jpg
```

No usar:

```text
/imagenes/...
imagenes/Mi Carpeta/Foto con título y tildes.jpg
research/imagenes/...
```

## Comprobación realizada

La auditoría local del proyecto devuelve:

- Referencias de imágenes en HTML: **279**
- Archivos inexistentes: **0**
- Rutas no canónicas: **0**
- Archivos problemáticos dentro de `imagenes/`: **0**

## Sobre la guía `celular-no-carga.html`

La página publicada en la raíz conserva la fotografía editorial en la introducción y en los primeros pasos, mientras que los pasos posteriores utilizan los diagramas SVG. El navegador puede mostrar una ruta como `imagenes/guias/...` porque esa es precisamente la URL pública correspondiente a una ruta relativa desde una página HTML situada en la raíz.
