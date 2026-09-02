# Revisión de rutas de NúcleoTech — septiembre 2026

## Correcciones realizadas

- Se restauraron los nombres Unicode originales de las imágenes que habían quedado convertidos en nombres literales `#U00...`.
- Se corrigieron las referencias de las imágenes principales de PS4 y laptop para usar rutas relativas desde la raíz del sitio:
  - `imagenes/ps4/...`
  - `imagenes/Laptop/...`
- Se revisaron referencias locales de `src`, `srcset`, `href`, `poster` y `url(...)` en HTML, plantillas, CSS, JS, JSON y scripts.
- Se revisaron referencias de imágenes JPG, JPEG, PNG, GIF, WEBP, SVG e ICO.
- Se comprobó que no existan referencias a archivos inexistentes, rutas fuera del proyecto ni rutas no canónicas.
- Se añadió `.nojekyll` para que el sitio estático pueda servirse sin procesamiento innecesario de Jekyll.

## Resultado de la auditoría

- Referencias de imágenes locales revisadas: **717**
- Referencias de imágenes locales inexistentes: **0**
- Nombres de archivos con `#U00...`: **0**
- Duplicados de rutas por diferencia de mayúsculas/normalización Unicode: **0**

## Importante

La auditoría también detectó algunos enlaces `href` hacia artículos que actualmente no están publicados en la raíz del sitio. Esos enlaces son referencias editoriales antiguas, no rutas de imágenes. No se cambiaron automáticamente para evitar publicar o redirigir contenido que todavía puede formar parte del flujo de borradores/revisión.

## Después de reemplazar el proyecto

Desde la carpeta del repositorio existente en VS Code:

```powershell
git status
git add -A
git commit -m "Corregir rutas y referencias de imagenes"
git push origin main
```

Después del `push`, espera a que GitHub Pages termine el despliegue y prueba con una ventana de incógnito o una recarga fuerte (`Ctrl + F5`).
