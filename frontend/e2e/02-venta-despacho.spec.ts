import { expect, test } from "@playwright/test";
import { elegirOpcion, entrar, registrarLlamadas } from "./apoyo/sesion";
import { esperarTrazas, marcarInicioTrazas } from "./apoyo/trazas";

// CU-58, CU-59, CU-60 - Venta, consulta del periodo y despacho.
test.describe("Ventas y despacho", () => {
  test("CU-58: el total lo calcula el servidor, no el navegador", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    const llamadas = registrarLlamadas(page);
    await entrar(page, "admin");

    await page.goto("/ventas/nueva");
    await page.getByLabel("Cliente").selectOption({ label: "Vivero Los Aromos" });

    // Dos lineas: 10 sacos de compost a $4.500 = $45.000, mas 2 m3 de mulch a
    // $45.000 = $90.000. Total esperado: $135.000.
    await elegirOpcion(page, "Producto", "Compost premium");
    await page.getByLabel("Cantidad").fill("10");
    await page.getByRole("button", { name: "Agregar" }).click();

    await elegirOpcion(page, "Producto", "Mulch de corteza");
    await page.getByLabel("Cantidad").fill("2");
    await page.getByRole("button", { name: "Agregar" }).click();

    await expect(page.getByTestId("linea-venta")).toHaveCount(2);
    await expect(page.getByTestId("total-previsualizado")).toHaveText("$135.000");

    await page.getByRole("button", { name: "Registrar venta" }).click();
    await page.waitForURL(/\/ventas\?registrada=/);

    // La traza confirma que el servidor derivo el total desde el catalogo y
    // que la venta nacio pendiente: la vista no fijo ninguno de los dos.
    await esperarTrazas(marca, [
      "CU-58 venta.creada",
      "lineas=2 total=135000.00 estado=pendiente",
    ]);

    await expect(page.getByTestId("aviso-venta-registrada")).toBeVisible();
    expect(llamadas).toContain("POST /api/v1/ventas/");

    await page.screenshot({
      path: "e2e-evidencias/cu-58-venta.png",
      fullPage: true,
    });
  });

  test("CU-59: el total del periodo lo entrega el servidor", async ({ page }) => {
    const llamadas = registrarLlamadas(page);
    await entrar(page, "admin");

    await page.goto("/ventas");
    await expect(page.getByTestId("fila-venta").first()).toBeVisible();

    // El total del periodo sale del endpoint /ventas/totales/, no de sumar las
    // filas en el navegador.
    expect(
      llamadas.some((llamada) => llamada.startsWith("GET /api/v1/ventas/totales/")),
    ).toBe(true);
    await expect(page.getByTestId("total-periodo")).toHaveText("$135.000");
    await expect(page.getByTestId("cantidad-ventas")).toContainText("1 venta");

    await page.screenshot({
      path: "e2e-evidencias/cu-59-ventas-periodo.png",
      fullPage: true,
    });
  });

  test("CU-60: el despacho cambia el estado y no se puede repetir", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    const llamadas = registrarLlamadas(page);
    await entrar(page, "operador");

    await page.goto("/ventas");
    const fila = page.getByTestId("fila-venta").first();
    await expect(fila).toContainText("pendiente");
    await fila.getByRole("button", { name: /Registrar despacho/i }).click();

    await page.getByLabel("Quien retira").fill("Juan Pérez");
    await page.getByLabel("Dirección de entrega").fill("Camino Colina 450");
    await page.getByRole("button", { name: "Confirmar despacho" }).click();

    // La transicion de estado la hace el servidor, en el orden esperado.
    await esperarTrazas(marca, [
      "CU-60 despacho.creado",
      "CU-60 venta.estado",
      "transicion=pendiente->despachada",
    ]);

    await expect(page.getByTestId("fila-venta").first()).toContainText(
      "despachada",
    );

    // El navegador llamo a la accion del modulo, no a un PATCH del estado.
    expect(
      llamadas.some((llamada) => /POST \/api\/v1\/ventas\/\d+\/despachar\//.test(llamada)),
    ).toBe(true);
    expect(
      llamadas.some((llamada) => /PATCH \/api\/v1\/ventas\//.test(llamada)),
    ).toBe(false);

    await page.screenshot({
      path: "e2e-evidencias/cu-60-despacho.png",
      fullPage: true,
    });
  });

  test("CU-60 excepcion 2: la venta despachada ya no ofrece despacho", async ({
    page,
  }) => {
    await entrar(page, "operador");
    await page.goto("/ventas");

    const fila = page.getByTestId("fila-venta").first();
    await expect(fila).toContainText("despachada");
    // La vista ya no ofrece el boton; el backend ademas lo rechaza (cubierto
    // en comercial/tests.py).
    await expect(
      fila.getByRole("button", { name: /Registrar despacho/i }),
    ).toHaveCount(0);
  });
});
