# Automatización editorial de NúcleoTech

El sistema ahora está dividido en **generar → revisar → publicar**. Esto evita que una pieza generada automáticamente llegue al sitio sin revisión ni imagen editorial.

## Flujo diario

```text
GitHub Actions
   ↓
generate_content.py
   ↓
drafts/pending/*.json
   ↓
revisión humana
   ├─ corregir texto
   ├─ elegir/añadir imagen
   └─ mover JSON a drafts/approved/
   ↓
Publicar contenido aprobado
   ↓
HTML + noticias.html/resenas.html/index.html + estado.json
```

### 1. Generación

El workflow `Generar borradores diarios` corre a las **08:00 de Ecuador (13:00 UTC)** y crea hasta 2 noticias y 1 guía por defecto.

Las noticias proceden de RSS tecnológicos configurados en `config/feeds.json`. El modelo debe aportar contexto y redacción propia; no debe copiar ni limitarse a sustituir palabras.

Los borradores quedan en:

`automation/drafts/pending/`

Nada de esa carpeta se publica.

### 2. Elegir la imagen

Abre el JSON del borrador. Encontrarás:

```json
"imagen": ""
```

Coloca tu imagen dentro del proyecto, por ejemplo:

`imagenes/noticias/mi-foto.jpg`

y cambia el campo:

```json
"imagen": "imagenes/noticias/mi-foto.jpg"
```

También puedes utilizar una imagen local de `imagenes/auto/`.

Si dejas el campo vacío, el publicador genera un SVG original como respaldo. Para AdSense y para la identidad editorial de NúcleoTech, es preferible revisar cada imagen antes de publicar.

### 3. Aprobar

Después de revisar título, texto, fuente y fotografía, mueve el JSON de:

`automation/drafts/pending/`

a:

`automation/drafts/approved/`

Puedes hacerlo desde Visual Studio Code.

### 4. Publicar

Ejecuta el workflow **Publicar contenido aprobado** desde GitHub Actions o, localmente:

```bash
python automation/publish_approved.py
```

El publicador comprueba que la imagen exista, genera el HTML y utiliza **la misma ruta de imagen** para el artículo, `noticias.html`/`resenas.html` y `index.html`.

## Por qué se cambió el sistema

El objetivo ya no es publicar mucho, sino publicar material que merezca permanecer en el sitio. Google indica que el contenido con poco valor, páginas con poco contenido original y contenido replicado sin aportación adicional puede afectar la monetización. Por eso la revisión humana y la selección de imagen forman ahora parte del flujo editorial.

## Variables

- `NUM_NOTICIAS`: 1 a 3, por defecto 2.
- `GENERAR_GUIA`: `1` para generar una guía; `0` para desactivarla.
- `OLLAMA_MODEL`: modelo de Ollama. Por defecto `llama3.2:3b`.
- `MODO_BORRADOR`: debe permanecer en `1` para el workflow diario.

## Regla editorial

Antes de aprobar una pieza, comprueba:

- ¿El artículo aporta información concreta?
- ¿Hay datos o afirmaciones que deban verificarse?
- ¿La noticia sigue siendo realmente tecnológica?
- ¿La redacción aporta contexto propio?
- ¿La imagen corresponde al tema?
- ¿La imagen es local y tenemos derecho a utilizarla?
- ¿El artículo sería útil aunque no tuviera anuncios?

Si la respuesta es no, el borrador debe corregirse o rechazarse.
