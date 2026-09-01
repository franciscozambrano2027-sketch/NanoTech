# Revisión de NúcleoTech — septiembre de 2026

## Cambios realizados

### Contenido
- Eliminadas 30 reseñas/artículos de compra que compartían una plantilla genérica y aportaban poca información específica.
- Eliminados dos artículos de actualidad que no cumplían el nuevo criterio editorial.
- Reescritas y ampliadas tres guías principales:
  - cómo saber si reparar o cambiar una laptop;
  - cuándo reiniciar un router y cuándo no hacer factory reset;
  - cómo limpiar una PC de forma segura.
- La sección `resenas.html` pasa a ser una biblioteca de **Guías prácticas y análisis**.
- Se conserva la biblioteca técnica de reparación y MikroTik, que es la parte más diferenciada del proyecto.

### Imágenes
- La portada y las tarjetas ahora utilizan una única ruta de imagen por artículo.
- Se eliminaron referencias a imágenes que pertenecían a artículos retirados.
- El sistema de publicación permite elegir una imagen local antes de publicar.
- Si no se proporciona una imagen, existe un SVG original como respaldo; la recomendación editorial es seleccionar una imagen antes de aprobar.

### Navegación
- Se normalizó la barra de navegación en las páginas existentes.
- Se corrigieron los estados activos de MikroTik y Comunidad.
- Se añadieron de forma consistente Noticias y Cotización donde faltaban.
- Se mejoró el menú móvil, cierre con Escape, cierre al seleccionar un enlace y cierre al hacer clic fuera.
- Se corrigieron las plantillas que generaban artículos con una barra incompleta.

### Sobre nosotros
- La imagen de NúcleoTech pasó de una columna lateral a una posición centrada entre bloques de texto.
- Se amplió visualmente la imagen y se añadió una leyenda.
- Se reorganizó el texto para explicar propósito, método, transparencia y tipo de contenido.

### Automatización
- El problema principal era que el proyecto tenía una automatización que publicaba directamente y una copia paralela dentro de `research`.
- La automatización productiva queda en `automation/`.
- El workflow diario ahora genera borradores, no publica directamente.
- El nuevo workflow `Publicar contenido aprobado` publica solo los JSON que se hayan movido a `automation/drafts/approved/`.
- Se corrigió el arranque de Ollama para no intentar levantar un segundo servidor cuando ya existe uno.
- El estado separa fuentes `noticias_en_revision` de `noticias_publicadas`.
- La publicación valida que la imagen indicada exista dentro del proyecto.

## Flujo de una publicación

1. GitHub Actions genera el borrador.
2. Revisar `automation/drafts/pending/`.
3. Colocar la imagen elegida en `imagenes/noticias/` o `imagenes/auto/`.
4. Escribir la ruta en el campo `imagen` del JSON.
5. Mover el JSON a `automation/drafts/approved/`.
6. Ejecutar **Publicar contenido aprobado**.
7. El publicador genera el HTML y actualiza portada/listados/estado.

## Criterio para AdSense

El objetivo no es garantizar una aprobación —Google decide la revisión— sino eliminar problemas claros de contenido delgado y replicado.

La nueva regla editorial es: **si una pieza no aporta una explicación concreta, contexto, procedimiento, análisis o criterio de decisión, no se publica.**

La revisión humana es obligatoria para las noticias automáticas.
