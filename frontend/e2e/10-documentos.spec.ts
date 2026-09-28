import { expect, test, type Page } from "@playwright/test";
import { entrar, registrarLlamadas } from "./apoyo/sesion";
import { esperarTrazas, leerTrazasDesde, marcarInicioTrazas } from "./apoyo/trazas";

const DOCUMENTO = "Permiso sanitario de compostaje";
const ENTIDAD = "SEREMI de Salud RM";

// Fecha ISO a `dias` de hoy, en hora local: el servidor compara contra su
// fecha local y toISOString() (UTC) ya es "manana" en la noche de Chile.
function enDias(dias: number): string {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() + dias);
  const dosDigitos = (n: number) => String(n).padStart(2, "0");
  return `${fecha.getFullYear()}-${dosDigitos(fecha.getMonth() + 1)}-${dosDigitos(fecha.getDate())}`;
}

// Un PDF minimo: el servidor valida formato por extension y tamano maximo.
const ARCHIVO_PDF = {
  name: "permiso-sanitario.pdf",
  mimeType: "application/pdf",
  buffer: Buffer.from("%PDF-1.4\n% documento de prueba e2e\n%%EOF\n"),
};

function filaDelDocumento(page: Page) {
  return page.getByTestId("fila-documento").filter({ hasText: DOCUMENTO });
}

// CU-86, CU-87, CU-88, CU-91 - Gestion documental (Modulo 12). El orden
// importa: seed_e2e deja la tabla de documentos vacia y los escenarios
// siguientes trabajan sobre el documento que registra el primero.
test.describe("Gestion documental", () => {
  test("CU-86, CU-87 y CU-88: registra el documento, adjunta su archivo y el servidor deriva el estado desde la vigencia", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    const llamadas = registrarLlamadas(page);
    await entrar(page, "admin");
    await page.goto("/documentos");

    // CU-86: registro.
    await page.getByRole("button", { name: "Nuevo documento" }).click();
    await page.getByLabel("Nombre del documento").fill(DOCUMENTO);
    await page.getByLabel("Clasificación").selectOption("permiso");
    await page.getByLabel("Entidad emisora").fill(ENTIDAD);
    // El boton que envia es el del formulario del modal, no el de la cabecera.
    await page.locator("form").getByRole("button", { name: "Nuevo documento" }).click();
    await esperarTrazas(marca, ["CU-86 documento.registrado", "tipo=permiso"]);
    await expect(filaDelDocumento(page)).toContainText("Sin archivo");

    // CU-87: el archivo queda como version 1 vigente.
    await filaDelDocumento(page).getByRole("button", { name: "Archivo" }).click();
    await page.getByLabel("Archivo").setInputFiles(ARCHIVO_PDF);
    await page.locator("form").getByRole("button", { name: "Adjuntar archivo" }).click();
    await esperarTrazas(marca, ["CU-87 documento.archivo_adjuntado", "version=1"]);
    await expect(filaDelDocumento(page)).toContainText("v1 · permiso-sanitario.pdf");

    // CU-88: con vencimiento dentro del umbral de aviso queda "por vencer"; el
    // estado lo calcula el servidor, no la vista.
    await filaDelDocumento(page).getByRole("button", { name: "Vigencia" }).click();
    await page.getByLabel("Fecha de emisión").fill(enDias(-355));
    await page.getByLabel("Fecha de vencimiento").fill(enDias(10));
    await page.locator("form").getByRole("button", { name: "Registrar vigencia" }).click();
    await esperarTrazas(marca, ["CU-88 documento.vigencia_registrada", "estado=por_vencer"]);
    await expect(filaDelDocumento(page)).toContainText("Por vencer");

    expect(llamadas).toContain("POST /api/v1/documentos-legales/");
    expect(llamadas.some((l) => /POST \/api\/v1\/documentos-legales\/\d+\/versiones\//.test(l))).toBe(true);
    await page.screenshot({ path: "e2e-evidencias/cu-86-88-documento.png", fullPage: true });
  });

  test("CU-86 excepcion 3: el mismo nombre y entidad advierte el duplicado y no registra sin confirmar", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    await entrar(page, "admin");
    await page.goto("/documentos");
    await expect(filaDelDocumento(page)).toHaveCount(1);

    await page.getByRole("button", { name: "Nuevo documento" }).click();
    await page.getByLabel("Nombre del documento").fill(DOCUMENTO);
    await page.getByLabel("Entidad emisora").fill(ENTIDAD);
    await page.locator("form").getByRole("button", { name: "Nuevo documento" }).click();

    await esperarTrazas(marca, ["CU-86 documento.posible_duplicado"]);
    await expect(page.getByText(/Ya existe un documento con el mismo nombre/)).toBeVisible();
    await page.getByRole("button", { name: "Cancelar" }).first().click();

    const lineas = await leerTrazasDesde(marca);
    expect(lineas.some((l) => l.includes("documento.registrado"))).toBe(false);
    await expect(filaDelDocumento(page)).toHaveCount(1);
  });

  test("CU-88 excepcion 2: un vencimiento anterior a la emision se rechaza", async ({ page }) => {
    const marca = await marcarInicioTrazas();
    await entrar(page, "admin");
    await page.goto("/documentos");

    await filaDelDocumento(page).getByRole("button", { name: "Vigencia" }).click();
    await page.getByLabel("Fecha de emisión").fill(enDias(0));
    await page.getByLabel("Fecha de vencimiento").fill(enDias(-5));
    await page.locator("form").getByRole("button", { name: "Registrar vigencia" }).click();

    await expect(
      page.getByText("La fecha de vencimiento no puede ser anterior a la fecha de emision."),
    ).toBeVisible();
    const lineas = await leerTrazasDesde(marca);
    expect(lineas.some((l) => l.includes("vigencia_registrada"))).toBe(false);
    // El documento conserva la vigencia anterior.
    await page.getByRole("button", { name: "Cancelar" }).first().click();
    await expect(filaDelDocumento(page)).toContainText("Por vencer");
  });

  test("CU-91: el tablero cuenta el documento por vencer y lo prioriza, sin modificarlo", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    const llamadas = registrarLlamadas(page);
    await entrar(page, "admin");

    await page.goto("/cumplimiento");
    await esperarTrazas(marca, ["CU-91 tablero.consultado", "total=1"]);
    await expect(page.getByTestId("resumen-por_vencer")).toHaveText("1");
    await expect(page.getByTestId("resumen-vencido")).toHaveText("0");
    const pendiente = page.getByTestId("fila-pendiente").filter({ hasText: DOCUMENTO });
    await expect(pendiente).toContainText("10 d");
    await expect(pendiente).toContainText("Por vencer");
    expect(llamadas.some((l) => l.startsWith("GET /api/v1/cumplimiento/tablero/"))).toBe(true);

    await page.screenshot({ path: "e2e-evidencias/cu-91-tablero-cumplimiento.png", fullPage: true });
  });

  test("Permisos: el operador no accede al tablero de cumplimiento", async ({ page }) => {
    await entrar(page, "operador");
    await page.goto("/cumplimiento");
    await expect(page.getByTestId("error-cumplimiento")).toBeVisible();
    await expect(page.getByTestId("fila-pendiente")).toHaveCount(0);
  });
});
