# Automatización de contenido diario — NúcleoTech

Publica automáticamente, todos los días, 1 noticia resumida (de RSS reales) + 1 artículo-guía
(sobre un tema rotativo de reparación/mantenimiento), usando un **modelo de IA open-source
gratuito** (Ollama) que corre dentro del propio runner de GitHub Actions — **sin API keys de
pago y sin costo**, mientras el repositorio sea público.

## Cómo funciona (resumen)

```
GitHub Actions (cron diario)
  └─ instala Ollama y descarga el modelo (llama3.2:3b por defecto)
  └─ python automation/generate_content.py
       ├─ lee automation/config/feeds.json → descarga RSS → elige noticias no publicadas
       ├─ le pide al modelo que las reescriba en español, con voz propia (nunca copia texto)
       ├─ toma el siguiente tema de automation/config/temas_guias.json
       ├─ le pide al modelo un artículo práctico sobre ese tema
       ├─ genera un banner SVG original para cada pieza (sin fotos de terceros)
       ├─ escribe {slug}.html usando las plantillas de automation/templates/
       ├─ inserta una tarjeta en noticias.html (noticias) o resenas.html (guías)
       └─ actualiza automation/estado/estado.json para no repetir contenido
  └─ si hay archivos nuevos: git commit + git push automático
```

## Puesta en marcha (una sola vez)

1. **Sube estos archivos a tu repositorio** (incluye la carpeta `.github/workflows/`,
   `automation/` y las páginas modificadas: `noticias.html`, `resenas.html`, y la barra de
   navegación con el nuevo enlace "Noticias" en todas las páginas).
2. En GitHub → **Settings → Actions → General → Workflow permissions**, marca
   **"Read and write permissions"** (para que el workflow pueda hacer `git push`).
3. Ve a la pestaña **Actions** de tu repo y ejecuta manualmente el workflow
   **"Publicar contenido diario"** (botón *Run workflow*) para probarlo antes de esperar al cron.
4. Revisa el resultado: debería aparecer un commit nuevo con 1-2 archivos `.html`, sus SVG en
   `imagenes/auto/`, y las tarjetas nuevas en `noticias.html`/`resenas.html`.

El cron ya viene configurado para correr todos los días a las **08:00 hora Ecuador**
(13:00 UTC). Puedes cambiarlo editando la línea `cron` en
`.github/workflows/publicar-diario.yml` ([ayuda con sintaxis cron](https://crontab.guru)).

## Cómo personalizar

- **Fuentes de noticias**: edita `automation/config/feeds.json`. Verifica cada URL de RSS en tu
  navegador antes de agregarla (debe cargar un XML, no una página web normal).
- **Temas de las guías**: edita `automation/config/temas_guias.json`. El script los usa en orden
  y vuelve a empezar cuando llega al final — puedes agregar tantos como quieras.
- **Cuántas noticias por día**: variable de repositorio `NUM_NOTICIAS` (Settings → Secrets and
  variables → Actions → Variables). Por defecto: 1.
- **Desactivar la guía diaria**: variable `GENERAR_GUIA=0`.
- **Cambiar de modelo**: variable `OLLAMA_MODEL` (por defecto `llama3.2:3b`, rápido y liviano).
  Si quieres más calidad de redacción a cambio de más tiempo de ejecución, prueba
  `qwen2.5:7b-instruct`. Cualquier modelo de la [librería de Ollama](https://ollama.com/library)
  funciona sin cambiar código.

## Cosas importantes a tener en cuenta

- **Revisión editorial**: el modelo es gratuito y liviano, así que ocasionalmente puede cometer
  errores de hecho o redactar de forma torpe. Te recomendamos revisar los primeros días de
  publicaciones antes de confiar el proceso al 100%. Nada se publica sin pasar por tu propio
  repositorio: siempre puedes revisar el commit antes de que se refleje en GitHub Pages, o
  simplemente borrar/editar un artículo después de publicado.
- **AdSense y contenido generado por IA**: Google permite contenido creado con ayuda de IA,
  pero penaliza el contenido "delgado" o creado en masa sin valor añadido para el lector
  (política de "contenido escalado con fines de manipulación de buscadores"). Por eso el script
  limita la producción a 1-2 piezas diarias, cuida el resumen/atribución de fuentes y evita
  copiar texto ajeno. Aun así, es tu responsabilidad revisar que el contenido cumpla las
  políticas de AdSense a medida que el sitio crece.
- **Derechos de las noticias**: el script nunca copia el texto de la fuente; genera un resumen
  con palabras propias y siempre enlaza al artículo original con crédito visible.
- **Sin API keys ni tarjetas de crédito**: todo corre en el runner gratuito de GitHub Actions
  (ilimitado en repos públicos) con un modelo open-source local. Si en el futuro quieres mejor
  calidad de texto, puedes cambiar `llamar_modelo()` en `generate_content.py` para usar la API
  de Claude u otro proveedor — pero eso ya implicaría una API key y costo por uso.

## Probar en tu propia computadora (opcional)

```bash
pip install -r automation/requirements.txt
ollama serve &                # requiere tener Ollama instalado: https://ollama.com/download
ollama pull llama3.2:3b
python automation/generate_content.py
```
