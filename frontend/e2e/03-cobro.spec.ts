import { expect, test } from "@playwright/test";
import { entrar, registrarLlamadas } from "./apoyo/sesion";
import { esperarTrazas, marcarInicioTrazas } from "./apoyo/trazas";

// CU-61, CU-63 - Cobro de una recepcion y documento tributario.
test.describe("Cobros", () => {
  test("CU-61: el monto sugerido sale de la tarifa del tramo", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    const llamadas = registrarLlamadas(page);
    await entrar(page, "operador");

    await page.goto("/cobros");
    const fila = page.getByTestId("fila-por-cobrar").first();
    await expect(fila).toBeVisible();
    await fila.getByRole("button", { name: /Registrar cobro/i }).click();

    // El vehiculo del seed tiene 25 m3, que cae en el tramo 20-30 ($40.000).
    // La traza demuestra que la busqueda del tramo la hizo el servidor.
    await esperarTrazas(marca, [
      "CU-61 cobro.tarifa_sugerida",
      "capacidad=25.00 tramo=20.00-30.00 monto=40000.00",
    ]);

    // El input numerico normaliza "40000.00" a "40000": se compara el valor.
    expect(Number(await page.getByLabel("Monto").inputValue())).toBe(40000);
    await expect(page.getByText(/Monto sugerido por la tarifa del tramo/)).toBeVisible();
    expect(
      llamadas.some((llamada) =>
        llamada.startsWith("GET /api/v1/cobros/sugerencia/"),
      ),
    ).toBe(true);

    await page.screenshot({
      path: "e2e-evidencias/cu-61-sugerencia.png",
      fullPage: true,
    });

    // El operador puede ajustar el monto antes de registrar.
    await page.getByLabel("Monto").fill("38000");
    await page.getByLabel("Forma de pago").selectOption("transferencia");
    await page
      .locator("form")
      .getByRole("button", { name: "Registrar cobro" })
      .click();

    await esperarTrazas(marca, ["CU-61 cobro.creado", "monto=38000.00"]);
    await expect(page.getByTestId("fila-cobro").first()).toContainText("$38.000");

    await page.screenshot({
      path: "e2e-evidencias/cu-61-cobro.png",
      fullPage: true,
    });
  });

  test("CU-61 excepcion 3: la recepcion cobrada sale de la lista", async ({
    page,
  }) => {
    await entrar(page, "operador");
    await page.goto("/cobros");

    // Ya fue cobrada en el escenario anterior: no vuelve a aparecer entre las
    // pendientes, asi que no hay forma de duplicar el cobro desde la vista.
    await expect(page.getByTestId("fila-por-cobrar")).toHaveCount(0);
    await expect(
      page.getByText(/No hay recepciones pendientes de cobro/i),
    ).toBeVisible();
    await expect(page.getByTestId("fila-cobro")).toHaveCount(1);
  });

  test("CU-63: el documento tributario nace pendiente", async ({ page }) => {
    const marca = await marcarInicioTrazas();
    await entrar(page, "admin");

    await page.goto("/cobros");
    await page
      .getByTestId("fila-cobro")
      .first()
      .getByRole("button", { name: "Documento" })
      .click();

    // El monto llega precargado desde el cobro de origen.
    expect(Number(await page.getByLabel("Monto").inputValue())).toBe(38000);
    await page.getByLabel("Tipo de documento").selectOption("factura");
    await page.getByLabel("Folio").fill("F-00123");
    await page.getByRole("button", { name: "Registrar documento" }).click();

    await esperarTrazas(marca, [
      "CU-63 documento.registrado",
      "tipo=factura origen=cobro estado=pendiente",
    ]);

    await page.screenshot({
      path: "e2e-evidencias/cu-63-documento.png",
      fullPage: true,
    });
  });
});
