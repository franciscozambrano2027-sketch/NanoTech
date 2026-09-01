CORRECCIÓN NUCLEOTECH - NOTICIAS E INICIO
================================================

Cambios realizados:
1. Se eliminó la estructura HTML dañada por el conflicto de Git en index.html.
2. Se restauró la estructura coherente de la portada, conservando:
   - guía destacada
   - últimas publicaciones
   - noticias nuevas
   - guías
   - bloque "Recién publicado"
3. Las dos noticias actuales usan una única imagen editorial en:
   - index.html
   - noticias.html
   - la página individual de cada noticia
4. Las páginas individuales de las noticias quedaron con una sola imagen de portada.
5. La automatización ya conserva el campo "imagen" en estado.json y lo utiliza para
   generar los tres lugares, evitando que se mezclen imágenes.
6. Se verificaron los archivos de imagen locales referenciados por estas páginas.

Imágenes actuales:
- por-que-los-millennials-rechazan-ascensos-en-la-empresa.html
  -> imagenes/noticias/millennials-no-le-interesan-ascensos.jpg
- como-internet-ha-evolucionado-en-las-ultimas-dos-decadas.html
  -> imagenes/noticias/evolucion-del-internet.jpg

Antes de publicar:
1. Reemplaza los archivos del proyecto por esta versión.
2. Ejecuta:
   git diff --check
   git status
3. Revisa index.html y noticias.html localmente.
4. Luego haz commit y push.

No se deben volver a resolver manualmente los bloques de contenido de index.html
eligiendo un lado del conflicto: las marcas HTML permiten que generate_content.py
los reconstruya automáticamente.
