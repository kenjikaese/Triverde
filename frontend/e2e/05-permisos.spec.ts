import { expect, test } from "@playwright/test";
import { elegirOpcion, entrar } from "./apoyo/sesion";
import { esperarSinTraza, marcarInicioTrazas } from "./apoyo/trazas";

// Criterio de aceptacion 5 de la spec del Modulo 8: el operador registra
// ventas, despachos y cobros, pero no cotiza ni ve la cuenta corriente.
test.describe("Permisos por rol", () => {
  test("el operador no ve el cotizador ni la cuenta corriente en el menú", async ({
    page,
  }) => {
    await entrar(page, "operador");

    const menu = page.getByRole("navigation");
    await expect(menu.getByRole("link", { name: "Ventas" })).toBeVisible();
    await expect(menu.getByRole("link", { name: "Cobros" })).toBeVisible();
    await expect(menu.getByRole("link", { name: "Cotizador" })).toHaveCount(0);
    await expect(
      menu.getByRole("link", { name: "Cuenta corriente" }),
    ).toHaveCount(0);

    await page.screenshot({
      path: "e2e-evidencias/permisos-menu-operador.png",
      fullPage: true,
    });
  });

  test("el operador que entra a mano al cotizador recibe 403", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    await entrar(page, "operador");

    const respuestas: number[] = [];
    page.on("response", (respuesta) => {
      if (respuesta.url().includes("/api/v1/cotizaciones/")) {
        respuestas.push(respuesta.status());
      }
    });

    // La pantalla carga (el operador si puede leer clientes), pero el intento
    // de cotizar lo corta el servidor.
    await page.goto("/cotizador");
    await elegirOpcion(page, "Cliente", "Vivero Los Aromos");
    await page.getByLabel("Tipo de servicio").fill("Triturado in situ");
    await page.getByLabel(/Distancia estimada/).fill("10");
    await page
      .getByRole("button", { name: /Calcular y guardar cotización/i })
      .click();

    await expect(page.getByTestId("error-cotizador")).toBeVisible();
    await expect(page.getByTestId("resultado-cotizacion")).toHaveCount(0);
    expect(respuestas).toContain(403);

    // El servidor corto antes de calcular nada: no hay traza de calculo.
    await esperarSinTraza(marca, "CU-55 cotizacion.calculada");
  });

  test("el operador que entra a mano a la cuenta corriente recibe 403", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    await entrar(page, "operador");

    const respuestas: number[] = [];
    page.on("response", (respuesta) => {
      if (respuesta.url().includes("/api/v1/cuenta-corriente/")) {
        respuestas.push(respuesta.status());
      }
    });

    await page.goto("/cuenta-corriente");
    await page.getByLabel("Cliente").selectOption({ label: "Vivero Los Aromos" });
    await expect(page.getByTestId("error-cuenta")).toBeVisible();
    expect(respuestas).toContain(403);

    await esperarSinTraza(marca, "CU-64 cuenta_corriente.calculada");
  });

  test("el administrador sí ve las cinco pantallas del módulo", async ({
    page,
  }) => {
    await entrar(page, "admin");

    const menu = page.getByRole("navigation");
    for (const etiqueta of [
      "Cotizador",
      "Historial de cotizaciones",
      "Ventas",
      "Cobros",
      "Cuenta corriente",
    ]) {
      await expect(menu.getByRole("link", { name: etiqueta })).toBeVisible();
    }
  });
});
