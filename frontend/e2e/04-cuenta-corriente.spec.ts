import { expect, test } from "@playwright/test";
import { entrar, registrarLlamadas } from "./apoyo/sesion";
import { esperarTrazas, marcarInicioTrazas } from "./apoyo/trazas";

// CU-62, CU-64 - Cuenta corriente calculada y estado de pago.
test.describe("Cuenta corriente", () => {
  test("CU-64: el saldo es ventas menos cobros, calculado en el servidor", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    const llamadas = registrarLlamadas(page);
    await entrar(page, "admin");

    await page.goto("/cuenta-corriente");
    await page.getByLabel("Cliente").selectOption({ label: "Vivero Los Aromos" });

    // Acumulado de los escenarios anteriores: una venta de $135.000 y un
    // cobro de $38.000, asi que el saldo es $97.000.
    await esperarTrazas(marca, [
      "CU-64 cuenta_corriente.calculada",
      "ventas=135000.00 cobros=38000.00 saldo=97000.00",
    ]);

    await expect(page.getByTestId("total-ventas")).toHaveText("$135.000");
    await expect(page.getByTestId("total-cobros")).toHaveText("$38.000");
    await expect(page.getByTestId("saldo")).toHaveText("$97.000");
    await expect(page.getByTestId("fila-movimiento")).toHaveCount(2);

    // El saldo lo entrega el endpoint; la vista no suma nada.
    expect(
      llamadas.some((llamada) =>
        /GET \/api\/v1\/cuenta-corriente\/\d+\//.test(llamada),
      ),
    ).toBe(true);

    await page.screenshot({
      path: "e2e-evidencias/cu-64-cuenta-corriente.png",
      fullPage: true,
    });
  });

  test("CU-62: el estado de pago se registra sobre el cliente", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    await entrar(page, "admin");

    await page.goto("/cuenta-corriente");
    await page.getByLabel("Cliente").selectOption({ label: "Vivero Los Aromos" });
    await expect(page.getByTestId("saldo")).toBeVisible();

    await page.getByLabel("Nuevo estado").selectOption("con deuda");
    await page
      .getByRole("button", { name: /Actualizar estado de pago/i })
      .click();

    await esperarTrazas(marca, [
      "CU-62 estado_pago.actualizado",
      "transicion=al dia->con deuda",
    ]);

    await expect(page.getByTestId("aviso-cuenta")).toBeVisible();

    await page.screenshot({
      path: "e2e-evidencias/cu-62-estado-pago.png",
      fullPage: true,
    });
  });

  test("CU-64 excepcion 1: cliente sin movimientos da saldo cero", async ({
    page,
  }) => {
    await entrar(page, "admin");

    await page.goto("/cuenta-corriente");
    await page
      .getByLabel("Cliente")
      .selectOption({ label: "Constructora Sin Datos" });

    await expect(page.getByTestId("saldo")).toHaveText("$0");
    await expect(page.getByTestId("fila-movimiento")).toHaveCount(0);
    await expect(
      page.getByText(/No hay movimientos en el rango consultado/i),
    ).toBeVisible();
  });

  test("CU-62 excepcion 1: sin movimientos no hay nada que conciliar", async ({
    page,
  }) => {
    await entrar(page, "admin");

    await page.goto("/cuenta-corriente");
    await page
      .getByLabel("Cliente")
      .selectOption({ label: "Constructora Sin Datos" });
    await expect(page.getByTestId("saldo")).toBeVisible();

    await page.getByLabel("Nuevo estado").selectOption("con deuda");
    await page
      .getByRole("button", { name: /Actualizar estado de pago/i })
      .click();

    const error = page.getByTestId("error-cuenta");
    await expect(error).toBeVisible();
    await expect(error).toContainText(/no tiene ventas ni cobros/i);
  });
});
