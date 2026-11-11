import { expect, test, type Page } from "@playwright/test";
import { entrar } from "./apoyo/sesion";

// Baja logica y reactivacion en los cinco mantenedores (CU-16, CU-18, CU-20, CU-22 y
// vehiculos), mas la direccion del cliente (que usan cotizacion, certificados y SINADER)
// y la edicion de vehiculos. Cada registro lleva una marca de tiempo porque la base e2e
// persiste entre corridas.

function fila(page: Page, texto: string) {
  return page.getByRole("row").filter({ hasText: texto });
}

async function darDeBajaYReactivar(page: Page, texto: string) {
  const f = fila(page, texto);
  await expect(f).toContainText("activo");
  page.once("dialog", (dialogo) => dialogo.accept());
  await f.getByRole("button", { name: "Desactivar" }).click();
  await expect(f).toContainText("inactivo");
  await f.getByRole("button", { name: "Activar" }).click();
  await expect(f.getByRole("button", { name: "Desactivar" })).toBeVisible();
  await expect(f).not.toContainText("inactivo");
}

test.describe("Mantenedores: baja y reactivacion", () => {
  test.beforeEach(async ({ page }) => {
    await entrar(page, "admin");
  });

  test("CU-15/16: el cliente guarda su direccion, se desactiva y se vuelve a activar", async ({ page }) => {
    const nombre = `Cliente e2e ${Date.now()}`;
    await page.goto("/clientes");
    await page.getByRole("button", { name: "Nuevo cliente" }).click();
    await page.getByLabel(/^Razon social/).fill(nombre);
    await page.getByLabel("Dirección").fill("Camino Quilapilun 100, Colina");
    await page.getByRole("button", { name: "Guardar cliente" }).click();

    const f = fila(page, nombre);
    await f.getByRole("button", { name: "Editar" }).click();
    await expect(page.getByLabel("Dirección")).toHaveValue("Camino Quilapilun 100, Colina");
    await page.getByLabel("Dirección").fill("Camino Quilapilun 200, Colina");
    await page.getByRole("button", { name: "Guardar cambios" }).click();
    await f.getByRole("button", { name: "Editar" }).click();
    await expect(page.getByLabel("Dirección")).toHaveValue("Camino Quilapilun 200, Colina");
    await page.getByRole("button", { name: "Cancelar" }).click();

    // El cliente usa un modal propio de confirmacion en vez del dialogo del navegador.
    await f.getByRole("button", { name: "Desactivar" }).click();
    await page.getByRole("button", { name: "Desactivar cliente" }).click();
    await expect(f).toContainText("inactivo");
    await f.getByRole("button", { name: "Activar" }).click();
    await expect(f.getByRole("button", { name: "Desactivar" })).toBeVisible();
    await expect(f).not.toContainText("inactivo");
  });

  test("CU-18: el transportista se desactiva y se vuelve a activar", async ({ page }) => {
    const nombre = `Transportista e2e ${Date.now()}`;
    await page.goto("/transportistas");
    await page.getByRole("button", { name: "Nuevo transportista" }).click();
    await page.getByLabel(/^Nombre/).fill(nombre);
    const cliente = page.getByRole("combobox", { name: /Cliente/ });
    const valor = await cliente.locator("option").nth(1).getAttribute("value");
    await cliente.selectOption(valor!);
    await page.getByRole("button", { name: "Guardar transportista" }).click();
    await darDeBajaYReactivar(page, nombre);
  });

  test("CU-20: el material se desactiva y se vuelve a activar", async ({ page }) => {
    const nombre = `Material e2e ${Date.now()}`;
    await page.goto("/materiales");
    await page.getByRole("button", { name: "Nuevo material" }).click();
    await page.getByLabel(/^Nombre/).fill(nombre);
    await page.getByLabel(/^Densidad/).fill("350");
    await page.getByRole("button", { name: "Guardar material" }).click();
    await darDeBajaYReactivar(page, nombre);
  });

  test("CU-22: el producto se desactiva y se vuelve a activar", async ({ page }) => {
    const nombre = `Producto e2e ${Date.now()}`;
    await page.goto("/productos");
    await page.getByRole("button", { name: "Nuevo producto" }).click();
    await page.getByLabel(/^Nombre/).fill(nombre);
    await page.getByLabel(/^Precio/).fill("5000");
    await page.getByRole("button", { name: "Guardar producto" }).click();
    await darDeBajaYReactivar(page, nombre);
  });

  test("Vehiculos: se edita, se desactiva y se vuelve a activar", async ({ page }) => {
    const patente = `E2E${String(Date.now()).slice(-5)}`;
    await page.goto("/vehiculos");
    await page.getByRole("button", { name: "Nuevo vehículo" }).click();
    await page.getByLabel(/^Patente/).fill(patente);
    await page.getByRole("button", { name: "Guardar vehículo" }).click();

    const f = fila(page, patente);
    await f.getByRole("button", { name: "Editar" }).click();
    await page.getByLabel("Descripción").fill("Camion tolva e2e");
    await page.getByRole("button", { name: "Guardar cambios" }).click();
    await expect(f).toContainText(patente);
    await f.getByRole("button", { name: "Editar" }).click();
    await expect(page.getByLabel("Descripción")).toHaveValue("Camion tolva e2e");
    await page.getByRole("button", { name: "Cancelar" }).click();

    await darDeBajaYReactivar(page, patente);
  });
});
