# Parte D — Panel de control y personalización (CU-72, CU-77)

Extracción de la Parte D del módulo `reportes` (M10), solo para que la revises
por separado. En el repo real esto NO va como app aparte: la spec dice "App
backend: nueva app reportes" (una sola app para Parte C y D). Esta carpeta
existe únicamente para que puedas leer/revisar tu parte sin el ruido de la
Parte C de Pablo.

Para integrarla al proyecto real:
1. Estos archivos van dentro de la app `reportes` ya existente (junto a los
   de Parte C), no como app `panel` separada.
2. `apps.py` aquí dice `name = "panel"` solo para que la carpeta sea
   importable de forma aislada al probarla; en el repo real no se usa este
   archivo, se respeta el `apps.py` de la app `reportes`.
3. Los imports a `catalogo`, `recepcion`, `produccion`, `inventario`,
   `comercial`, `common` son los mismos stubs que ya te pasé en el zip
   anterior — reemplázalos por los modelos reales del repo.

## Qué prueba `tests.py`

Los 4 criterios de aceptación de Parte D del spec:
1. Sin `PanelControl` previo, el panel usa el set por defecto.
2. Un bloque sin datos aparece en cero; una pila en proceso se marca como tal.
3. Guardar preferencias con ≥1 indicador crea/actualiza el `PanelControl` y
   el panel refleja la selección.
4. Guardar sin indicadores se rechaza; guardar sin cambios no genera una
   nueva actualización.

Corridos de forma aislada (montados como app temporal en el proyecto de
prueba): 6/6 tests OK.
