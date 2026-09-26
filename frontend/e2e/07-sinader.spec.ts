import { expect, test, type Page } from "@playwright/test";
import { CUENTAS, entrar, registrarLlamadas } from "./apoyo/sesion";
import { esperarTrazas, marcarInicioTrazas } from "./apoyo/trazas";

function periodoDelMes(): { desde: string; hasta: string } {
  const hoy = new Date();
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { desde: iso(new Date(hoy.getFullYear(), hoy.getMonth(), 1)), hasta: iso(hoy) };
}

/**
 * Crea por la API una descarga recibida del cliente sin RUT ni direccion.
 *
 * Se crea aqui y no en seed_e2e a proposito: si existiera desde el inicio
 * apareceria como "por cobrar" y alteraria los escenarios de cobro del Modulo
 * 8, que corren antes. seed_e2e la limpia en la corrida siguiente.
 */
async function crearDescargaDelClienteSinDatos(page: Page): Promise<void> {
  const login = await page.request.post("/api/v1/auth/login/", {
    data: { username: CUENTAS.admin.usuario, password: CUENTAS.admin.clave },
  });
  const { token } = await login.json();
  const cabeceras = { Authorization: `Token ${token}` };

  const clientes = await page.request.get("/api/v1/clientes/", { headers: cabeceras });
  const sinDatos = (await clientes.json()).find(
    (c: { razon_social: string }) => c.razon_social === "Constructora Sin Datos",
  );
  const materiales = await page.request.get("/api/v1/materiales/", { headers: cabeceras });
  const ramaVerde = (await materiales.json()).find(
    (m: { nombre: string }) => m.nombre === "Rama verde",
  );

  const creada = await page.request.post("/api/v1/recepciones/", {
    headers: cabeceras,
    data: {
      cliente: sinDatos.id,
      conductor: "Sin Datos",
      fecha: new Date().toISOString().slice(0, 10),
      hora: "11:00",
      estado: "recibida",
      detalles: [{ material: ramaVerde.id, volumen_m3: "4.00", destino_sugerido: "a pila" }],
    },
  });
  expect(creada.status(), await creada.text()).toBe(201);
}

// CU-67 - Declaracion para SINADER (Modulo 9, Parte A).
test.describe("Exportacion SINADER", () => {
  test("CU-67: agrupa por cliente, excluye al que no tiene datos y entrega la planilla", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    const llamadas = registrarLlamadas(page);
    const { desde, hasta } = periodoDelMes();
    await entrar(page, "admin");
    await crearDescargaDelClienteSinDatos(page);

    await page.goto("/sinader");
    await page.getByLabel("Desde").fill(desde);
    await page.getByLabel("Hasta").fill(hasta);
    await page.getByRole("button", { name: "Generar declaración" }).click();

    // El servidor agrupo, excluyo al cliente incompleto y armo el archivo: la
    // traza lo registra con los totales.
    await esperarTrazas(marca, [
      "CU-67 declaracion.generada",
      "clientes=1 excluidos=1 peso_kg=5000.00",
    ]);

    const resultado = page.getByTestId("resultado-sinader");
    await expect(resultado).toContainText("1 clientes, 1 descargas");
    await expect(resultado).toContainText("5.000 kg declarables");
    await expect(page.getByTestId("cliente-sinader")).toHaveCount(1);
    await expect(page.getByTestId("cliente-sinader")).toContainText("Vivero Los Aromos");
    const excluidos = page.getByTestId("excluidos-sinader");
    await expect(excluidos).toContainText("Constructora Sin Datos");
    await expect(excluidos).toContainText("falta RUT y direccion");
    expect(llamadas).toContain("POST /api/v1/declaraciones-sinader/generar/");

    await page.screenshot({
      path: "e2e-evidencias/cu-67-sinader.png",
      fullPage: true,
    });

    // La planilla se descarga desde el endpoint del modulo, como XLSX.
    const [descarga] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Descargar XLSX" }).click(),
    ]);
    expect(descarga.suggestedFilename()).toMatch(/^sinader-.*\.xlsx$/);
    await esperarTrazas(marca, ["CU-67 declaracion.descargada"]);
    expect(
      llamadas.some((llamada) =>
        /GET \/api\/v1\/declaraciones-sinader\/\d+\/descargar\//.test(llamada),
      ),
    ).toBe(true);

    await expect(page.getByTestId("fila-declaracion")).toHaveCount(1);
    await expect(page.getByTestId("fila-declaracion").first()).toContainText("1 (1 excl.)");
  });

  test("CU-67 excepcion 1: un periodo sin descargas no genera declaracion", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    await entrar(page, "admin");

    await page.goto("/sinader");
    await page.getByLabel("Desde").fill("2025-01-01");
    await page.getByLabel("Hasta").fill("2025-01-31");
    await page.getByRole("button", { name: "Generar declaración" }).click();

    await esperarTrazas(marca, ["CU-67 declaracion.rechazada"]);
    await expect(page.getByTestId("error-sinader")).toContainText(
      "No hay descargas recibidas en el periodo",
    );
    await expect(page.getByTestId("resultado-sinader")).toHaveCount(0);
    // El historial sigue con la unica declaracion valida.
    await expect(page.getByTestId("fila-declaracion")).toHaveCount(1);

    await page.screenshot({
      path: "e2e-evidencias/cu-67-sinader-periodo-vacio.png",
      fullPage: true,
    });
  });
});
