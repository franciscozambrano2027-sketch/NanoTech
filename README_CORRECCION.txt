NucleoTech - correccion de noticias e imagenes

Cambios incluidos:
1. Se recupero la estructura limpia de las dos noticias actuales y se eliminaron marcadores de conflicto Git.
2. Cada articulo tiene un unico campo "imagen" en automation/estado/estado.json.
3. La misma imagen se usa en:
   - la pagina individual de la noticia,
   - noticias.html,
   - index.html cuando la noticia aparece.
4. Las dos noticias actuales conservan sus fotografias editoriales:
   - imagenes/noticias/millennials-no-le-interesan-ascensos.jpg
   - imagenes/noticias/evolucion-del-internet.jpg
5. La automatizacion futura buscara una imagen editorial con el mismo slug en imagenes/noticias/
   (.jpg, .jpeg, .png, .webp o .svg). Si no existe, utilizara el SVG generado en imagenes/auto/.
6. Se actualizan noticias.html e index.html a partir del estado, evitando que vuelvan a quedar con
   imagenes diferentes para una misma noticia.

Como aplicarlo:
- Copia el contenido de este ZIP sobre tu carpeta Nanotech actual.
- No reemplaces otros archivos de tu proyecto que no aparecen aqui.
- Luego revisa git diff antes de hacer commit/push.
