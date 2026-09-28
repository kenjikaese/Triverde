import { expect, test } from "@playwright/test";
import { CUENTAS, elegirOpcion, entrar, registrarLlamadas } from "./apoyo/sesion";
import { esperarTrazas, marcarInicioTrazas } from "./apoyo/trazas";

// Primer dia del mes en curso y hoy, en ISO: el periodo que abarca la descarga
// que siembra seed_e2e (fecha = hoy).
function periodoDelMes(): { desde: string; hasta: string } {
  const hoy = new Date();
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { desde: iso(new Date(hoy.getFullYear(), hoy.getMonth(), 1)), hasta: iso(hoy) };
}

// CU-65, CU-66 - Certificados de trazabilidad (Modulo 9, Parte A).
test.describe("Certificados de trazabilidad", () => {
  test("CU-65: el certificado por descarga lo compila y folia el servidor", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    const llamadas = registrarLlamadas(page);
    await entrar(page, "admin");

    await page.goto("/certificados");
    // Solo se ofrecen descargas recibidas; la del seed trae 20 m3 de rama
    // verde con su peso derivado (5.000 kg).
    await elegirOpcion(page, "Descarga recibida", "Vivero Los Aromos");
    await page.getByRole("button", { name: "Emitir certificado" }).click();

    // La traza prueba que el servidor compilo el contenido, asigno el folio y
    // sumo el peso: la vista no calcula nada.
    await esperarTrazas(marca, [
      "CU-65 certificado.emitido",
      "peso_kg=5000.00",
    ]);

    const emitido = page.getByTestId("certificado-emitido");
    await expect(emitido).toBeVisible();
    await expect(emitido).toContainText(/CTR-\d{4}-0001/);
    await expect(emitido).toContainText("5000.00 kg en 20.00 m³");
    await expect(page.getByTestId("fila-certificado")).toHaveCount(1);
    expect(llamadas).toContain("POST /api/v1/certificados/generar-descarga/");

    await page.screenshot({
      path: "e2e-evidencias/cu-65-certificado-descarga.png",
      fullPage: true,
    });
  });

  test("CU-65: la misma descarga no genera un segundo folio", async ({ page }) => {
    const marca = await marcarInicioTrazas();
    await entrar(page, "admin");

    await page.goto("/certificados");
    await elegirOpcion(page, "Descarga recibida", "Vivero Los Aromos");
    await page.getByRole("button", { name: "Emitir certificado" }).click();

    // El servidor devuelve el certificado existente en vez de duplicarlo.
    await esperarTrazas(marca, ["CU-65 certificado.existente"]);
    await expect(page.getByTestId("certificado-emitido")).toContainText(
      /CTR-\d{4}-0001/,
    );
    await expect(page.getByTestId("fila-certificado")).toHaveCount(1);
  });

  test("CU-66: el consolidado agrupa por material y exige confirmar la nueva version", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    const llamadas = registrarLlamadas(page);
    const { desde, hasta } = periodoDelMes();
    await entrar(page, "admin");

    await page.goto("/certificados");
    await page.getByLabel("Cliente").selectOption({ label: "Vivero Los Aromos" });
    await page.getByLabel("Desde").fill(desde);
    await page.getByLabel("Hasta").fill(hasta);
    await page.getByRole("button", { name: "Emitir consolidado" }).click();

    await esperarTrazas(marca, [
      "CU-66 consolidado.emitido",
      "version=1 descargas=1",
    ]);
    await expect(page.getByTestId("certificado-emitido")).toContainText("versión 1");
    expect(llamadas).toContain("POST /api/v1/certificados/generar-consolidado/");

    await page.screenshot({
      path: "e2e-evidencias/cu-66-consolidado.png",
      fullPage: true,
    });

    // Excepcion 2: ya existe uno para el cliente y el periodo. El servidor
    // responde 409 y la vista pide confirmar antes de emitir otra version.
    await page.getByRole("button", { name: "Emitir consolidado" }).click();
    await esperarTrazas(marca, ["CU-66 consolidado.previo"]);
    const previo = page.getByTestId("consolidado-previo");
    await expect(previo).toBeVisible();
    await expect(previo).toContainText("Confirme para emitir una nueva version");

    await page.screenshot({
      path: "e2e-evidencias/cu-66-consolidado-previo.png",
      fullPage: true,
    });

    await page.getByRole("button", { name: "Emitir nueva versión" }).click();
    await esperarTrazas(marca, ["CU-66 consolidado.emitido", "version=2"]);
    await expect(page.getByTestId("certificado-emitido")).toContainText("versión 2");

    // Las dos versiones quedan en el historial junto al certificado por
    // descarga: nada se borra.
    await expect(page.getByTestId("fila-certificado")).toHaveCount(3);
    await expect(page.getByTestId("fila-certificado").first()).toContainText("v2");
  });

  test("CU-66 excepcion 1: sin descargas en el periodo no se emite", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    await entrar(page, "admin");

    await page.goto("/certificados");
    await page.getByLabel("Cliente").selectOption({ label: "Vivero Los Aromos" });
    await page.getByLabel("Desde").fill("2025-01-01");
    await page.getByLabel("Hasta").fill("2025-01-31");
    await page.getByRole("button", { name: "Emitir consolidado" }).click();

    await esperarTrazas(marca, ["CU-66 consolidado.rechazado"]);
    await expect(page.getByTestId("error-certificados")).toContainText(
      "no tiene descargas recibidas",
    );
    await expect(page.getByTestId("fila-certificado")).toHaveCount(3);
  });

  test("Permisos: el operador no ve ni accede a los certificados", async ({
    page,
  }) => {
    await entrar(page, "operador");
    await expect(page.getByRole("link", { name: "Certificados" })).toHaveCount(0);

    const login = await page.request.post("/api/v1/auth/login/", {
      data: { username: CUENTAS.operador.usuario, password: CUENTAS.operador.clave },
    });
    const { token } = await login.json();
    const respuesta = await page.request.get("/api/v1/certificados/", {
      headers: { Authorization: `Token ${token}` },
    });
    expect(respuesta.status()).toBe(403);
  });
});
