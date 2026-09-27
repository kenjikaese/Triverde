import { expect, test } from "@playwright/test";
import { elegirOpcion, entrar, registrarLlamadas } from "./apoyo/sesion";
import { esperarTrazas, marcarInicioTrazas } from "./apoyo/trazas";

// CU-68 - Trazabilidad del lote entregado (Modulo 9, Parte A), sobre el enlace
// Venta -> Pila que agrega el registro de venta (CU-58).
test.describe("Trazabilidad de lote", () => {
  test("CU-68: la venta con pila de origen reconstruye la cadena hasta la composicion", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    const llamadas = registrarLlamadas(page);
    await entrar(page, "admin");

    // 1. Se registra una venta enlazada a la pila cerrada del seed (P-E2E-01,
    //    20 m3 de rama verde). El enlace es opcional y lo guarda el servidor
    //    en la linea de venta.
    await page.goto("/ventas/nueva");
    await page.getByLabel("Cliente").selectOption({ label: "Vivero Los Aromos" });
    await elegirOpcion(page, "Producto", "Compost premium");
    await page.getByLabel("Cantidad").fill("5");
    await elegirOpcion(page, "Pila de origen", "P-E2E-01");
    await page.getByRole("button", { name: "Agregar" }).click();
    await expect(page.getByTestId("linea-venta")).toContainText("P-E2E-01");
    await page.getByRole("button", { name: "Registrar venta" }).click();
    await page.waitForURL(/\/ventas\?registrada=/);
    const ventaId = new URL(page.url()).searchParams.get("registrada");
    expect(ventaId).toBeTruthy();

    // 2. La trazabilidad del lote la arma el servidor a partir de la venta.
    await page.goto(`/trazabilidad-lote?venta=${ventaId}`);
    await esperarTrazas(marca, [
      "CU-68 venta.trazabilidad",
      `venta=${ventaId} lineas=1 con_pila=1 recepciones=1`,
    ]);

    await expect(page.getByText("1 de 1 líneas trazables")).toBeVisible();
    await expect(page.getByText("Pila de origen P-E2E-01")).toBeVisible();
    const composicion = page.getByTestId("composicion-pila");
    await expect(composicion).toHaveCount(1);
    await expect(composicion.first()).toContainText("Rama verde");
    await expect(composicion.first()).toContainText("20 m³");
    // Y hasta la descarga de origen: el seed registra que los 20 m3 de la
    // pila salieron de la recepcion recibida de Vivero Los Aromos.
    const origen = page.getByTestId("recepcion-origen");
    await expect(origen).toHaveCount(1);
    await expect(origen.first()).toContainText("Vivero Los Aromos");
    await expect(origen.first()).toContainText("Rama verde");
    await expect(origen.first()).toContainText("20 m³");
    // La pila esta cerrada: no hay advertencia de composicion provisoria.
    await expect(page.getByTestId("advertencia-trazabilidad")).toHaveCount(0);
    expect(
      llamadas.some((llamada) =>
        new RegExp(`GET /api/v1/ventas/${ventaId}/trazabilidad/`).test(llamada),
      ),
    ).toBe(true);

    await page.screenshot({
      path: "e2e-evidencias/cu-68-trazabilidad-lote.png",
      fullPage: true,
    });
  });

  test("CU-68 excepcion 1: la venta sin pila de origen informa que no es trazable", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    await entrar(page, "admin");

    await page.goto("/trazabilidad-lote");
    // La venta del escenario de ventas (02) se registro sin pila de origen.
    // Se elige la primera opcion cuyo texto no sea la venta enlazada recien
    // creada: el select ordena las ventas de la mas reciente a la mas antigua.
    const select = page.getByRole("combobox", { name: /Venta a trazar/ });
    // Las ventas llegan por la API: se espera a que el select tenga al menos
    // el marcador y las dos ventas antes de leer sus opciones.
    await expect.poll(() => select.locator("option").count()).toBeGreaterThanOrEqual(3);
    const valores = await select.locator("option").evaluateAll((opciones) =>
      opciones.map((o) => (o as HTMLOptionElement).value).filter(Boolean),
    );
    expect(valores.length).toBeGreaterThanOrEqual(2);
    await select.selectOption(valores[valores.length - 1]);

    await esperarTrazas(marca, ["CU-68 venta.trazabilidad", "con_pila=0"]);
    await expect(page.getByTestId("advertencia-trazabilidad")).toContainText(
      "no cuenta con trazabilidad de compostaje",
    );
    // La venta del escenario 02 tiene dos lineas, ninguna con pila.
    await expect(page.getByText("0 de 2 líneas trazables")).toBeVisible();
    await expect(page.getByTestId("composicion-pila")).toHaveCount(0);

    await page.screenshot({
      path: "e2e-evidencias/cu-68-sin-pila.png",
      fullPage: true,
    });
  });
});
