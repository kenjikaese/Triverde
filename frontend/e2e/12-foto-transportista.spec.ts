import { expect, test, type Page } from "@playwright/test";
import { elegirOpcion, entrar, registrarLlamadas } from "./apoyo/sesion";

// Foto del material (CU-27) y descarga desde la cuenta del transportista (CU-28).
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgaGAAAAEEAIFw9selAAAAAElFTkSuQmCC",
  "base64",
);

// Con un modal abierto hay dos capturas en la pagina: el modal es la ultima.
async function adjuntarFoto(page: Page) {
  await page.getByRole("button", { name: "Adjuntar foto" }).last().click();
  await page.getByLabel("Elegir imagen").last().setInputFiles({
    name: "carga.png",
    mimeType: "image/png",
    buffer: PNG,
  });
  await expect(page.getByAltText("Vista previa de la foto")).toBeVisible();
  await page.getByRole("button", { name: "Guardar foto" }).click();
}

test.describe("Foto y descarga del transportista", () => {
  test("CU-28 y CU-27: del transportista a la carga aceptada por el operador", async ({ page }) => {
    const llamadas = registrarLlamadas(page);
    await entrar(page, "transportista");
    await page.waitForURL(/\/mi-descarga$/);
    await expect(page.getByRole("link", { name: "Recepcion de camiones" })).toHaveCount(0);

    // CU-28 Excepcion 2: sin volumen no se crea la recepcion.
    await page.getByRole("button", { name: "Confirmar descarga" }).click();
    await expect(page.getByText("Ingresa el volumen aproximado.")).toBeVisible();

    // CU-27 Excepcion 2: cancelar en la vista previa no deja foto.
    await page.getByRole("button", { name: "Adjuntar foto" }).click();
    await page.getByLabel("Elegir imagen").setInputFiles({ name: "carga.png", mimeType: "image/png", buffer: PNG });
    await page.getByRole("button", { name: "Cancelar" }).click();
    await expect(page.getByTestId("miniatura-foto")).toHaveCount(0);

    // Flujo normal: la foto se adjunta y la descarga queda a nombre de su empresa.
    await adjuntarFoto(page);
    await expect(page.getByTestId("miniatura-foto")).toHaveCount(1);
    await page.getByLabel(/Volumen aproximado/).fill("12.5");
    await page.getByRole("button", { name: "Confirmar descarga" }).click();
    await expect(page.getByText(/registrada a nombre de Vivero Los Aromos/)).toBeVisible();
    const fila = page.getByTestId("fila-descarga").first();
    await expect(fila).toContainText("12,5 m³");
    await expect(fila.getByTestId("miniatura-foto")).toHaveCount(1);
    expect(llamadas.some((l) => l.endsWith("POST /api/v1/recepciones/mi-descarga/"))).toBe(true);

    // CU-27: se puede agregar otra foto a la recepcion abierta.
    await fila.getByRole("button", { name: "Agregar foto" }).click();
    await adjuntarFoto(page);
    await expect(page.getByText(/Foto asociada a la descarga/)).toBeVisible();
    await expect(fila.getByTestId("miniatura-foto")).toHaveCount(2);

    // El operador ve las fotos y completa el material antes de aceptar.
    await entrar(page, "operador");
    await page.goto("/inspeccion");
    const pendiente = page.getByTestId("fila-recepcion").filter({ hasText: "Aprox. 12,5 m³, por completar" }).first();
    await expect(pendiente).toBeVisible();
    await expect(pendiente.getByRole("button", { name: "Aceptar carga" })).toHaveCount(0);
    const imagen = pendiente.getByTestId("miniatura-foto").first();
    await expect(imagen).toBeVisible();
    await expect
      .poll(() => imagen.evaluate((img: HTMLImageElement) => img.naturalWidth))
      .toBeGreaterThan(0);

    await pendiente.getByRole("button", { name: "Completar material" }).click();
    await elegirOpcion(page, "Material", "Rama verde");
    await expect(page.getByLabel(/Volumen \(m³\)/)).toHaveValue("12.50");
    await page.getByRole("button", { name: "Registrar material" }).click();
    await expect(page.getByText(/Material registrado/)).toBeVisible();

    const completa = page.getByTestId("fila-recepcion").filter({ hasText: "Rama verde: 12,5 m³" }).first();
    await completa.getByRole("button", { name: "Aceptar carga" }).click();
    await expect(page.getByText(/quedó recibida/)).toBeVisible();
  });

  test("CU-27: el operador adjunta la foto dentro del registro de la recepcion", async ({ page }) => {
    await entrar(page, "operador");
    await page.goto("/recepcion");
    await elegirOpcion(page, "Cliente", "Vivero Los Aromos");
    await elegirOpcion(page, "Material", "Rama verde");
    await page.getByLabel("Volumen (m3)").fill("3");
    await adjuntarFoto(page);
    await expect(page.getByTestId("miniatura-foto")).toHaveCount(1);
    await page.getByRole("button", { name: /registrar recepcion/i }).click();
    await expect(page.getByText(/1 foto\/s/)).toBeVisible();
  });

  test("CU-27 Excepcion 3 y CU-32: sin senal la descarga con foto queda en el dispositivo", async ({ page, context }) => {
    await entrar(page, "transportista");
    await page.waitForURL(/\/mi-descarga$/);
    await expect(page.getByText("Cargando...")).toHaveCount(0);
    const antes = await page.getByTestId("fila-descarga").count();

    await context.setOffline(true);
    await expect(page.getByText("Sin conexión", { exact: true })).toBeVisible();
    await adjuntarFoto(page);
    await page.getByLabel(/Volumen aproximado/).fill("4");
    await page.getByRole("button", { name: "Confirmar descarga" }).click();
    await expect(page.getByText(/guardada en este dispositivo/)).toBeVisible();

    // Al volver la senal se envia sola, una sola vez y con su foto.
    await context.setOffline(false);
    const fila = page.getByTestId("fila-descarga").filter({ hasText: "4 m³" });
    await expect(async () => {
      await page.reload();
      await expect(page.getByTestId("fila-descarga")).toHaveCount(antes + 1, { timeout: 1_000 });
    }).toPass({ timeout: 15_000 });
    await expect(fila.getByTestId("miniatura-foto")).toHaveCount(1);
  });
});
