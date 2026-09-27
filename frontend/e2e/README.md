# Pruebas end-to-end — Módulo 8 (Comercial) y Módulo 9 Parte A (Trazabilidad)

Verifican los CU-55 a CU-64 y los CU-65 a CU-68 sobre el sistema andando:
navegador real, frontend real y backend real.

## Cómo correrlas

```bash
cd frontend
npm install
npx playwright install chromium   # solo la primera vez
npm run e2e
```

No hay que levantar nada a mano: Playwright arranca el backend y el frontend,
y los apaga al terminar.

- `npm run e2e:ui` abre el modo interactivo, útil para depurar un escenario.
- `npm run e2e:reporte` abre el reporte HTML de la última corrida.

## Qué verifica cada escenario

| Archivo | Casos de uso |
|---|---|
| `01-cotizacion.spec.ts` | CU-55, CU-56, CU-57 |
| `02-venta-despacho.spec.ts` | CU-58, CU-59, CU-60 |
| `03-cobro.spec.ts` | CU-61, CU-63 |
| `04-cuenta-corriente.spec.ts` | CU-62, CU-64 |
| `05-permisos.spec.ts` | Criterio de aceptación 5 |
| `06-certificados.spec.ts` | CU-65, CU-66 y permisos del Módulo 9 |
| `07-sinader.spec.ts` | CU-67 |
| `08-trazabilidad-lote.spec.ts` | CU-68 (sobre el enlace Venta → Pila del CU-58) |

## Las tres capas de evidencia

Cada escenario afirma sobre tres cosas distintas, y las tres importan:

1. **La traza del servidor.** El backend registra el paso por cada punto de
   negocio (`backend/common/trazas.py`) en `backend/logs/trazas-cu.log`, y el
   test verifica que la secuencia esperada apareció, en orden:

   ```
   CU-55 cotizacion.calculada distancia=10.00 recorrido=20.00 costo=40000.00
   CU-60 venta.estado venta=1 transicion=pendiente->despachada
   ```

2. **La llamada de red.** `registrarLlamadas()` captura lo que pidió el
   navegador, para comprobar que la vista usó el endpoint correcto — por
   ejemplo `POST /ventas/12/despachar/` y no un `PATCH` directo al estado.

3. **La interfaz.** Lo que ve la persona en pantalla.

### Por qué hacen falta las trazas

Una prueba de interfaz puede quedar verde pasando por el camino equivocado. Si
el cotizador calculara `km × 2 × costo` en JavaScript, la pantalla mostraría el
número correcto y el test pasaría, pero se estaría violando el patrón por capas
que exige la spec ("las derivaciones se calculan en el servidor, nunca en el
navegador"). El assert sobre la pantalla no distingue esos dos casos; la traza
sí.

Está comprobado: al desactivar la traza del cálculo dejando la vista intacta,
`01-cotizacion.spec.ts` falla aunque la pantalla siga mostrando $40.000.

## Datos y aislamiento

- Base propia: `backend/db.e2e.sqlite3`, nunca la de desarrollo.
- `manage.py seed_e2e` corre antes de cada sesión y deja el mismo estado
  inicial: usuarios `admin` y `operador` (clave `triverde-e2e-2026`), un
  cliente con datos completos y otro sin ellos, dos productos con precio, un
  vehículo de 25 m³, una recepción recibida lista para cobrar (con 20 m³ de
  rama verde y su peso derivado, certificable por el CU-65) y una pila cerrada
  `P-E2E-01` con composición, que el CU-68 recorre.
- La descarga del cliente sin datos que necesita el CU-67 la crea el propio
  escenario por la API, para no alterar la lista de cobros pendientes de los
  escenarios del Módulo 8; `seed_e2e` la limpia en la corrida siguiente.
- Un solo worker y orden fijo: los escenarios comparten la base y el saldo de
  la cuenta corriente depende de la venta y el cobro de los anteriores.

## Evidencias para el entregable

Los escenarios dejan capturas en `frontend/e2e-evidencias/`, con el mismo
formato que las del Incremento 1 en
`docs/entregables/evidencias-casos-de-prueba/`. Para adjuntarlas a la entrega,
se copian desde ahí junto con la salida de `npm run e2e`.
