# Modulo 9 Parte A - Secuencias de diseno

Se incluyen los flujos normal y de excepcion de los cuatro casos de uso, en
`docs/trabajo-grupal/diagramas/secuencias/`. Cada diagrama se versiona en
tres formatos: `.puml` como fuente editable, `.png` para documentos y
presentaciones, y `.svg` para conservar calidad al ampliarlo.

- CU-65: `cu65-certificado-descarga-normal.puml` y
  `cu65-certificado-descarga-excepcion.puml`.
- CU-66: `cu66-certificado-consolidado-normal.puml` y
  `cu66-certificado-consolidado-excepcion.puml`.
- CU-67: `cu67-declaracion-sinader-normal.puml` y
  `cu67-declaracion-sinader-excepcion.puml`.
- CU-68: `cu68-trazabilidad-lote-normal.puml` y
  `cu68-trazabilidad-lote-excepcion.puml`.

Los diagramas siguen la nomenclatura de la especificacion: vista `V_`,
controlador `C_` y objetos de dominio con prefijo `:`. Atendiendo la
observacion 4 de la revision del Incremento 2, los objetos se nombran como
las tablas reales de la base (`:comercial_venta`, `:inventario_pila`,
`:trazabilidad_certificadotrazabilidad`), y los diez diagramas del Modulo 8
(CU-55 a CU-64) se corrigieron con el mismo criterio.
