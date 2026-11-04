import { expect, test, type Page } from "@playwright/test";
import { elegirOpcion, entrar, registrarLlamadas } from "./apoyo/sesion";

// Ciclo productivo por las Vistas: camion -> inspeccion -> triturado -> pila ->
// procesos -> ensacado (CU-25, CU-30, CU-31, CU-35 a CU-43).
const CLIENTE = "Vivero Los Aromos";
const MATERIAL = "Rama verde";

async function registrarRecepcion(page: Page, volumen: string, conductor: string) {
  await page.goto("/recepcion");
  await elegirOpcion(page, "Cliente", CLIENTE);
  await page.getByLabel("Conductor").fill(conductor);
  await elegirOpcion(page, "Material", MATERIAL);
  await page.getByLabel("Volumen (m3)").fill(volumen);
  await page.getByRole("button", { name: /registrar recepcion/i }).click();
  await expect(page.getByText(/registrada|recepcion #/i).first()).toBeVisible();
}

function filaConVolumen(page: Page, volumen: string) {
  return page
    .getByTestId("fila-recepcion")
    .filter({ hasText: `${MATERIAL}: ${volumen} m³` })
    .first();
}

test.describe("Inspeccion de cargas y ciclo de la pila", () => {
  test("CU-30 y CU-31: multa y rechazo con su motivo", async ({ page }) => {
    const llamadas = registrarLlamadas(page);
    await entrar(page, "operador");
    await registrarRecepcion(page, "37", "Conductor rechazo");

    await page.goto("/inspeccion");
    const fila = filaConVolumen(page, "37");
    await expect(fila).toBeVisible();

    // CU-30 Excepcion 2: el monto debe ser mayor a cero.
    await fila.getByRole("button", { name: "Aplicar multa" }).click();
    await page.getByLabel(/Motivo/).fill("Botellas mezcladas");
    await page.getByLabel(/Monto/).fill("0");
    await page.getByRole("button", { name: "Registrar multa" }).click();
    await expect(page.getByText("El monto debe ser mayor a cero.")).toBeVisible();

    // CU-30 flujo normal: la recepcion sigue en inspeccion.
    await page.getByLabel(/Monto/).fill("15000");
    await page.getByRole("button", { name: "Registrar multa" }).click();
    await expect(fila).toContainText("$15.000");
    await expect(fila).toContainText("pendiente de inspeccion");

    // CU-31: el rechazo la saca de los pendientes y de inventario.
    await fila.getByRole("button", { name: "Rechazar carga" }).click();
    await page.getByLabel(/Motivo del rechazo/).fill("Demasiada basura en la carga");
    await page.getByRole("button", { name: "Confirmar rechazo" }).click();
    await expect(page.getByText(/quedó|salió del inventario/).first()).toBeVisible();
    await expect(filaConVolumen(page, "37")).toHaveCount(0);

    await page.getByLabel("Mostrar").selectOption({ label: "Rechazadas" });
    const rechazada = filaConVolumen(page, "37");
    await expect(rechazada).toContainText("Demasiada basura");
    await expect(rechazada).toContainText("$15.000");
    await expect(rechazada.getByRole("button", { name: "Aceptar carga" })).toHaveCount(0);

    expect(llamadas.some((l) => /POST .*\/recepciones\/\d+\/multa\/$/.test(l))).toBe(true);
    expect(llamadas.some((l) => /POST .*\/recepciones\/\d+\/rechazar\/$/.test(l))).toBe(true);
  });

  test("CU-35 a CU-43: de la carga aceptada a la pila cerrada", async ({ page }) => {
    await entrar(page, "operador");

    // Carga aceptada: 50 m3 de rama, factor 5 = 10 m3 de chip.
    await registrarRecepcion(page, "50", "Conductor ciclo");
    await page.goto("/inspeccion");
    await filaConVolumen(page, "50").getByRole("button", { name: "Aceptar carga" }).click();
    await expect(page.getByText(/quedó recibida/)).toBeVisible();

    // CU-37: triturado desde la lista de pilas.
    await page.goto("/pilas");
    await page.getByRole("button", { name: "Registrar triturado" }).click();
    await elegirOpcion(page, "Material por triturar", MATERIAL);
    await page.getByLabel(/Volumen procesado/).fill("50");
    await page.getByRole("button", { name: "Confirmar triturado" }).click();
    await expect(page.getByText(/registrado correctamente/)).toBeVisible();

    // CU-35: nueva pila con el codigo propuesto.
    await page.getByRole("button", { name: "Nueva pila" }).click();
    await expect(page.getByLabel(/Código/)).not.toHaveValue("");
    await page.getByLabel(/Observaciones/).fill("Pila del ciclo e2e");
    await page.getByRole("button", { name: "Crear pila" }).click();
    await page.waitForURL(/\/pilas\/\d+$/);
    await expect(page.getByText("Sin procesos registrados todavía.")).toBeVisible();

    // CU-36 Excepcion 3: sin material no se confirma.
    await page.getByRole("button", { name: "Confirmar composición" }).click();
    await expect(page.getByText(/al menos un material/)).toBeVisible();

    // CU-36: material con su descarga de origen.
    await elegirOpcion(page, "Material", MATERIAL);
    await page.getByLabel(/Cantidad/).fill("10");
    await elegirOpcion(page, "Descarga de origen", "50.00 m³");
    await page.getByRole("button", { name: "Agregar material" }).click();
    await expect(page.getByTestId("fila-composicion")).toContainText("10 m³");
    await page.getByRole("button", { name: "Confirmar composición" }).click();
    await expect(page.getByText(/Composición confirmada/)).toBeVisible();

    // CU-38 con temperatura sobre el techo: se registra con advertencia.
    await page.getByRole("button", { name: "Registrar volteo" }).click();
    await page.getByLabel(/Temperatura/).fill("75");
    await page.getByRole("button", { name: "Confirmar volteo" }).click();
    await expect(page.getByTestId("fila-proceso").first()).toContainText("sobre el techo");

    // CU-39: humedad opcional.
    await page.getByRole("button", { name: "Registrar riego" }).click();
    await page.getByRole("button", { name: "Confirmar riego" }).click();
    await expect(page.getByTestId("fila-proceso")).toHaveCount(2);

    // CU-41 Excepcion 1: sin harneado no hay reposo.
    await page.getByRole("button", { name: "Iniciar reposo" }).click();
    await page.getByRole("button", { name: "Confirmar inicio de reposo" }).click();
    await expect(page.getByText(/debe harnearse antes/)).toBeVisible();
    await page.getByRole("button", { name: "Cancelar" }).click();

    // CU-40 y CU-41.
    await page.getByRole("button", { name: "Registrar harneado" }).click();
    await page.getByRole("button", { name: "Confirmar harneado" }).click();
    await expect(page.getByTestId("fila-proceso")).toHaveCount(3);
    await page.getByRole("button", { name: "Iniciar reposo" }).click();
    await page.getByRole("button", { name: "Confirmar inicio de reposo" }).click();
    await expect(page.getByRole("button", { name: "Registrar ensacado" })).toBeVisible();

    // CU-42 Excepcion 2 y ensacado total: la pila se cierra.
    await page.getByRole("button", { name: "Registrar ensacado" }).click();
    await page.getByLabel(/Cantidad ensacada/).fill("99");
    await page.getByRole("button", { name: "Confirmar ensacado" }).click();
    await expect(page.getByText(/curados disponibles/)).toBeVisible();
    await page.getByLabel(/Cantidad ensacada/).fill("10");
    await page.getByRole("button", { name: "Confirmar ensacado" }).click();
    await expect(page.getByText("cerrada", { exact: true })).toBeVisible();
    await expect(page.getByTestId("fila-proceso")).toHaveCount(5);
  });
});
