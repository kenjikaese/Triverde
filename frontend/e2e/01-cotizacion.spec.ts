import { expect, test } from "@playwright/test";
import { entrar, registrarLlamadas } from "./apoyo/sesion";
import { esperarTrazas, marcarInicioTrazas } from "./apoyo/trazas";

// CU-55, CU-56, CU-57 - Cotizacion de servicio.
test.describe("Cotizaciones", () => {
  test("CU-55: el costo lo calcula el servidor sobre la ida y vuelta", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    const llamadas = registrarLlamadas(page);
    await entrar(page, "admin");

    await page.goto("/cotizador");
    await page.getByLabel("Cliente").selectOption({ label: "Vivero Los Aromos" });
    await page.getByLabel("Tipo de servicio").fill("Triturado in situ");
    await page.getByLabel(/Distancia estimada/).fill("10");
    await page
      .getByRole("button", { name: /Calcular y guardar cotización/i })
      .click();

    await expect(page.getByTestId("resultado-cotizacion")).toBeVisible();

    // El seed configura el costo por km en $2.000 (parametro de docs/02), asi
    // que 10 km de ida = 20 km de recorrido = $40.000. Si el Modulo 2 aun no
    // aporta CostoTransporte, el sistema informa que falta el parametro.
    const costo = await page.getByTestId("costo-estimado").innerText();
    const trazas = await esperarTrazas(marca, ["CU-55 cotizacion."]);
    const calculo = trazas.find((linea) => linea.includes("cotizacion.calculada"));

    if (calculo) {
      // La traza demuestra que la multiplicacion ocurrio en el servidor.
      expect(calculo).toContain("distancia=10");
      expect(calculo).toContain("recorrido=20");
      expect(costo).not.toBe("Sin calcular");
    } else {
      expect(costo).toBe("Sin calcular");
      await expect(page.getByTestId("aviso-costo-km")).toBeVisible();
    }

    // La vista pidio el endpoint del modulo, no calculo nada por su cuenta.
    expect(llamadas).toContain("POST /api/v1/cotizaciones/");

    await page.screenshot({
      path: "e2e-evidencias/cu-55-cotizacion.png",
      fullPage: true,
    });
  });

  test("CU-55 excepcion 2: rechaza una distancia en cero", async ({ page }) => {
    await entrar(page, "admin");
    await page.goto("/cotizador");
    await page.getByLabel("Cliente").selectOption({ label: "Vivero Los Aromos" });
    await page.getByLabel("Tipo de servicio").fill("Triturado in situ");

    // El input tiene min=0.01, asi que la validacion del navegador ya frena el
    // envio: el formulario no llega a crear la cotizacion.
    await page.getByLabel(/Distancia estimada/).fill("0");
    await page
      .getByRole("button", { name: /Calcular y guardar cotización/i })
      .click();

    await expect(page.getByTestId("resultado-cotizacion")).toHaveCount(0);
  });

  test("CU-57: el historial filtra en el servidor", async ({ page }) => {
    const llamadas = registrarLlamadas(page);
    await entrar(page, "admin");

    // Deja una cotizacion registrada para que el historial tenga contenido.
    await page.goto("/cotizador");
    await page.getByLabel("Cliente").selectOption({ label: "Vivero Los Aromos" });
    await page.getByLabel("Tipo de servicio").fill("Triturado in situ");
    await page.getByLabel(/Distancia estimada/).fill("15");
    await page
      .getByRole("button", { name: /Calcular y guardar cotización/i })
      .click();
    await expect(page.getByTestId("resultado-cotizacion")).toBeVisible();

    await page.goto("/cotizaciones");
    await expect(page.getByTestId("fila-cotizacion").first()).toBeVisible();

    // Filtrar por otro cliente vacia el listado: el filtro viaja al servidor.
    await page
      .getByLabel("Cliente")
      .selectOption({ label: "Constructora Sin Datos" });
    await expect(page.getByTestId("fila-cotizacion")).toHaveCount(0);
    await expect(
      page.getByText(/No hay cotizaciones que coincidan/i),
    ).toBeVisible();

    expect(
      llamadas.some((llamada) => llamada.startsWith("GET /api/v1/cotizaciones/")),
    ).toBe(true);

    await page.screenshot({
      path: "e2e-evidencias/cu-57-historial.png",
      fullPage: true,
    });
  });

  test("CU-56 excepcion 1: no exporta si al cliente le faltan datos", async ({
    page,
  }) => {
    await entrar(page, "admin");

    await page.goto("/cotizador");
    await page
      .getByLabel("Cliente")
      .selectOption({ label: "Constructora Sin Datos" });
    await page.getByLabel("Tipo de servicio").fill("Retiro de material");
    await page.getByLabel(/Distancia estimada/).fill("8");
    await page
      .getByRole("button", { name: /Calcular y guardar cotización/i })
      .click();
    await expect(page.getByTestId("resultado-cotizacion")).toBeVisible();

    await page.getByRole("button", { name: /Exportar cotización/i }).click();

    const error = page.getByTestId("error-cotizador");
    await expect(error).toBeVisible();
    await expect(error).toContainText(/datos de contacto/i);
    await expect(error).toContainText(/Faltan:/);
  });
});
