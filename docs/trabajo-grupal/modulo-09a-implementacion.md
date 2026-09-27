# Modulo 9 - Parte A: certificados, SINADER y trazabilidad de lote

## Alcance

La Parte A implementa CU-65, CU-66, CU-67 y CU-68. Comparte la app
`trazabilidad` con la Parte B: la migracion `0001_initial` de la Parte B crea
`IndicadorAmbiental`, y la migracion `0002` de esta parte agrega
`CertificadoTrazabilidad` y `DeclaracionSinader`. El enlace Venta -> Pila vive
en la app `comercial` (migracion `0002_detalleventa_pila`), porque es un campo
del detalle de venta.

## Punto de integracion 1: enlace Venta -> Pila

- `DetalleVenta.pila` es una FK opcional a `inventario.Pila`. Queda nula para
  servicios y productos sin lote de origen.
- `on_delete=PROTECT`: una pila con ventas asociadas es evidencia de
  trazabilidad y no se borra.
- El registro de venta (CU-58) muestra un selector de pila de origen por
  linea; excluye las pilas "en formacion" porque su composicion aun no esta
  confirmada.

## Reglas de negocio

- **CU-65, certificado por descarga:** solo sobre `Recepcion` en estado
  `recibida`, con al menos una linea de material y con peso calculado. El peso
  derivado no admite nulos en la base, asi que "sin peso calculado" equivale
  a peso cero. Una descarga se certifica una sola vez: repetir la accion
  devuelve el certificado existente en vez de duplicar el folio.
- **CU-66, consolidado mensual:** agrupa las descargas recibidas del cliente en
  el periodo, sumando volumen y peso por material. Sin descargas no se emite.
  Si ya existe un consolidado para cliente + periodo, la API responde `409` y
  exige `confirmar`; al confirmar se emite una nueva version y la anterior se
  conserva en el historial (el numero de version va en `contenido`).
- **Folio:** `CTR-AAAA-NNNN`, correlativo por anio, nunca reutilizado.
- **`contenido`:** JSON con los datos compilados al emitir. Es un hecho
  historico: si despues cambia el cliente o la recepcion, el certificado
  emitido no se altera.
- **CU-67, declaracion SINADER:** agrupa por cliente generador el material
  recibido en el periodo con su fecha. Excluye las descargas de clientes sin
  datos obligatorios y devuelve la lista de que completar. Si ninguna descarga
  es declarable, no genera y avisa. Produce una planilla XLSX (hoja de detalle
  por descarga y material, y hoja de resumen por cliente) que se persiste en
  `media/sinader/`. El sistema no se conecta con SINADER.
- **Supuesto documentado:** los datos obligatorios del generador son RUT y
  direccion (`sinader.CAMPOS_OBLIGATORIOS`). Si la autoridad exige otro
  campo, se agrega a esa tupla.
- **CU-68, trazabilidad de lote:** reconstruye Venta -> Pila -> composicion de
  la pila (material y volumen). Sin pila en ninguna linea responde
  `trazable=false` con la advertencia "sin trazabilidad"; con pila no cerrada
  advierte que la composicion no es definitiva.

## Limite conocido del modelo de datos (CU-68)

La spec pide listar las recepciones de origen de la pila con la cantidad
aportada por cada una. `ComposicionPila` registra material y volumen, pero no
que `DetalleRecepcion` aporto ese material, y el inventario se lleva como
saldo por material y etapa. Por eso la cadena llega con certeza hasta la
composicion de la pila y no lista recepciones. Reconstruirlas exige agregar en
el Modulo 5 una FK opcional de `ComposicionPila` a `DetalleRecepcion`; queda
como decision pendiente del grupo. La vista lo indica explicitamente.

## API

Todo bajo `/api/v1/`, solo Administrador, con auditoria en cada emision.

- `GET /certificados/` (filtros `cliente`, `tipo`), `GET /certificados/{id}/`.
- `POST /certificados/generar-descarga/` con `{recepcion}` -> `201` (o `200`
  si ya existia).
- `POST /certificados/generar-consolidado/` con
  `{cliente, periodo_inicio, periodo_fin, confirmar?}` -> `201`, `400` sin
  descargas, `409` con consolidado previo.
- `GET /certificados/{id}/exportar/` -> contenido descargable (mismo patron
  que la exportacion de cotizaciones, CU-56).
- `GET /declaraciones-sinader/`, `POST /declaraciones-sinader/generar/` con
  `{periodo_inicio, periodo_fin}` -> `201` con resumen y excluidos, `400` si
  no hay nada declarable.
- `GET /declaraciones-sinader/{id}/descargar/` -> planilla XLSX.
- `GET /ventas/{id}/trazabilidad/` -> cadena del lote (app `comercial`).

## Dependencia nueva

`openpyxl==3.1.5` (planilla SINADER). Esta en `requirements.txt`; el
contenedor se reconstruye con `docker compose up -d --build`.

## Vistas

`Certificados.tsx`, `ExportacionSinader.tsx` y `TrazabilidadLote.tsx` dejaron
de ser mockups y consumen la API. `RegistroVenta.tsx` incorpora la pila de
origen.

## Pruebas

- `trazabilidad/test_parte_a.py`: 20 pruebas (CU-65 a CU-67, planilla XLSX,
  permisos).
- `comercial/tests.py::TrazabilidadVentaTests`: 8 pruebas (enlace y CU-68).
