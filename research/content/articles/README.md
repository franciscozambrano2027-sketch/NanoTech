# Contenido editorial

Cada artículo migrado se guarda como un archivo de datos independiente.

Durante la transición, los HTML existentes de la raíz siguen siendo la versión
publicada. Los artículos migrados se prueban mediante `scripts/build/build.py`
y se generan en `_build/`.

No editar manualmente un artículo migrado en la raíz: la fuente futura será su
archivo dentro de `content/articles/`.
