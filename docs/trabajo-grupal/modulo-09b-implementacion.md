# Modulo 9 - Parte B: huella de carbono

## Alcance

La Parte B implementa CU-69, CU-70 y CU-71 en la app compartida
`trazabilidad`. Los calculos se ejecutan en el servidor y la vista solo
consulta los resultados.

## Contrato para la Parte A

- La app `trazabilidad` y su migracion `0001_initial` ya existen.
- `0001_initial` crea exclusivamente `IndicadorAmbiental`.
- Los modelos de la Parte A deben agregarse mediante una migracion posterior.
- El router comun ya esta incorporado en `config/urls.py`.
- La Parte A puede registrar sus ViewSets adicionales en `trazabilidad/urls.py`.

## Parametros requeridos

Los factores no se inventan ni se cargan con valores arbitrarios. El
administrador debe crear valores positivos en `ParametroConversion`:

- `co2_evitado_camion`: kg de CO2e evitado por kg de material recibido.
- `co2_evitado_compostaje`: kg de CO2e evitado por kg de material compostado.

Al crear o editar estos parametros se reintentan automaticamente los calculos
que estaban pendientes.

## Calculos

- CU-69: suma `DetalleRecepcion.peso_derivado_kg` y multiplica el total por
  `co2_evitado_camion` cuando la recepcion queda en estado `recibida`.
- CU-70: deriva el peso de cada composicion como
  `volumen_m3 * Material.densidad_kg_m3` y multiplica la suma por
  `co2_evitado_compostaje` cuando la pila queda `cerrada`.
- Las correcciones actualizan el mismo indicador; nunca generan duplicados.
- Rechazar una recepcion retira su indicador y ajusta el acumulado.
- La ausencia de peso, densidad o factor deja el calculo pendiente y visible
  en la respuesta de CU-71.

## API

`GET /api/v1/indicador-ambiental/`

Solo el Administrador puede consultar. Acepta los filtros opcionales `desde`
y `hasta` en formato `AAAA-MM-DD`. Devuelve:

- total acumulado de CO2e evitado;
- desglose entre recepciones y pilas;
- cantidad de fuentes de cada origen;
- detalles individuales;
- calculos pendientes y su motivo.

## Pruebas

Las pruebas de `trazabilidad/tests.py` cubren calculos, parametros faltantes,
reintentos, correcciones, rechazo, deduplicacion, permisos y filtro por
periodo.

