# Flujo de imágenes para publicaciones

1. Abre el JSON de `automation/drafts/pending/`.
2. Elige o crea la imagen que corresponda realmente al artículo.
3. Copia la imagen a `imagenes/noticias/` (JPG, PNG o WebP).
4. Escribe la ruta en el campo `imagen`, por ejemplo:

```json
"imagen": "imagenes/noticias/routeros-diagnostico.jpg"
```

5. Revisa el texto y mueve el JSON a `automation/drafts/approved/`.
6. Ejecuta **Publicar contenido aprobado**.

Una publicación nueva **no se publica sin imagen**. No se generan banners automáticos de texto. La misma ruta de imagen se conserva en el artículo, las tarjetas de Noticias/Guías y la portada.
