import { expect, test } from "@playwright/test";
import { entrar } from "./apoyo/sesion";

// Perfil propio (CU-04) y configuracion (CU-10, CU-12, CU-13 y CU-14). Los nombres
// llevan una marca de tiempo y los valores se restauran: la base e2e persiste entre
// corridas y otros escenarios usan el costo por km y los parametros.
test.describe("Perfil y configuracion", () => {
  test("CU-04: el usuario corrige sus datos y el cambio se ve de inmediato", async ({ page }) => {
    await entrar(page, "operador");
    await page.getByRole("link", { name: "Mi perfil" }).click();
    await expect(page.getByText("Operador", { exact: true }).last()).toBeVisible();

    const nombre = `Operador ${Date.now()}`;
    await page.getByRole("button", { name: "Editar" }).click();

    // Excepcion 3: nombre vacio.
    await page.getByLabel(/^Nombre/).fill("");
    await page.getByLabel(/^Correo/).fill(`operador${Date.now()}@triverde.cl`);
    await page.getByRole("button", { name: "Guardar cambios" }).click();
    await expect(page.getByText(/Ingresa tu nombre/)).toBeVisible();

    // Excepcion 2: la contrasena no cumple el criterio y no se guarda nada.
    await page.getByLabel(/^Nombre/).fill(nombre);
    await page.getByLabel("Nueva contraseña").fill("123");
    await page.getByLabel("Repetir contraseña").fill("123");
    await page.getByRole("button", { name: "Guardar cambios" }).click();
    await expect(page.getByText(/^Contraseña:/)).toBeVisible();

    await page.getByLabel("Nueva contraseña").fill("");
    await page.getByLabel("Repetir contraseña").fill("");
    await page.getByRole("button", { name: "Guardar cambios" }).click();
    await expect(page.getByText("Perfil actualizado.")).toBeVisible();
    await expect(page.getByTestId("perfil-nombre")).toHaveText(nombre);
    await expect(page.getByRole("banner").getByRole("link", { name: nombre })).toBeVisible();
  });

  test("CU-10: crea y edita una receta de mezcla, y queda en uso", async ({ page }) => {
    await entrar(page, "admin");
    await page.goto("/recetas");
    const nombre = `Receta e2e ${Date.now()}`;

    await page.getByRole("button", { name: "Nueva receta" }).click();
    await page.getByLabel(/^Nombre/).fill(nombre);
    await page.getByLabel(/Partes de seco/).fill("0");
    await page.getByLabel(/Partes de verde/).fill("1");
    await page.getByRole("button", { name: "Guardar receta" }).click();
    await expect(page.getByText(/Debe ser mayor a cero/)).toBeVisible();

    await page.getByLabel(/Partes de seco/).fill("3");
    await page.getByRole("button", { name: "Guardar receta" }).click();
    const fila = page.getByTestId("fila-receta").filter({ hasText: nombre });
    await expect(fila).toContainText("3:1");
    await expect(fila).toContainText("En uso");

    await fila.getByRole("button", { name: "Editar" }).click();
    await page.getByLabel(/Partes de seco/).fill("2");
    await page.getByRole("button", { name: "Guardar receta" }).click();
    await expect(fila).toContainText("2:1");

    page.once("dialog", (dialogo) => dialogo.accept());
    await fila.getByRole("button", { name: "Dar de baja" }).click();
    await expect(fila).toContainText("De baja");
    await expect(fila.getByRole("button", { name: "Editar" })).toHaveCount(0);
  });

  test("CU-12: actualiza el costo por km y no registra un cambio sin diferencia", async ({ page }) => {
    await entrar(page, "admin");
    await page.goto("/tarifas");
    const campo = page.getByLabel(/Costo por km/);
    await expect(campo).not.toHaveValue("");
    const original = await campo.inputValue();

    await page.getByRole("button", { name: "Guardar costo" }).click();
    await expect(page.getByText(/no se registró un cambio/)).toBeVisible();

    await campo.fill("0");
    await page.getByRole("button", { name: "Guardar costo" }).click();
    await expect(page.getByText(/Debe ser mayor a cero/)).toBeVisible();

    await campo.fill(String(Number(original) + 100));
    await page.getByRole("button", { name: "Guardar costo" }).click();
    await expect(page.getByText("Costo por km actualizado.")).toBeVisible();

    await campo.fill(original);
    await page.getByRole("button", { name: "Guardar costo" }).click();
    await expect(campo).toHaveValue(original);
    await expect(page.getByText("Costo por km actualizado.")).toBeVisible();
  });

  test("CU-13: agrega y edita un concepto, y rechaza el nombre repetido", async ({ page }) => {
    await entrar(page, "admin");
    await page.goto("/costos-operativos");
    const concepto = `Concepto e2e ${Date.now()}`;

    await page.getByRole("button", { name: "Agregar concepto" }).click();
    await page.getByLabel(/Concepto/).fill(concepto);
    await page.getByLabel(/Valor/).fill("1500");
    await page.getByRole("button", { name: "Guardar costo" }).click();
    const fila = page.getByTestId("fila-costo").filter({ hasText: concepto });
    await expect(fila).toContainText("$1.500");

    // Excepcion 1: nombre repetido.
    await page.getByRole("button", { name: "Agregar concepto" }).click();
    await page.getByLabel(/Concepto/).fill(concepto);
    await page.getByLabel(/Valor/).fill("2000");
    await page.getByRole("button", { name: "Guardar costo" }).click();
    await expect(page.getByText(/Edita ese concepto en su lugar/)).toBeVisible();
    await page.getByRole("button", { name: "Cancelar" }).click();

    await fila.getByRole("button", { name: "Editar" }).click();
    await page.getByLabel(/Valor/).fill("1800");
    await page.getByRole("button", { name: "Guardar costo" }).click();
    await expect(fila).toContainText("$1.800");
  });

  test("CU-14: el cambio de un parametro queda en el historial, filtrable y de solo lectura", async ({ page }) => {
    await entrar(page, "admin");
    await page.goto("/parametros");
    const fila = page.getByRole("row").filter({ has: page.getByRole("button", { name: "Editar" }) }).first();
    const nombre = (await fila.getByRole("cell").first().innerText()).trim();
    await fila.getByRole("button", { name: "Editar" }).click();
    const campo = page.getByLabel(/^Valor/);
    const original = await campo.inputValue();
    await campo.fill(String(Number(original) + 1));
    await page.getByRole("button", { name: "Guardar cambio" }).click();
    await expect(page.getByText("Editar parámetro")).toHaveCount(0);

    await page.goto("/parametros/historial");
    await page.getByLabel("Parámetro").selectOption({ label: nombre });
    const cambio = page.getByTestId("fila-cambio").first();
    await expect(cambio).toContainText(nombre);
    await expect(cambio).toContainText("admin");

    await cambio.click();
    const detalle = page.getByText("Detalle del cambio");
    await expect(detalle).toBeVisible();
    await expect(page.getByRole("button", { name: /Guardar/ })).toHaveCount(0);
    await page.getByRole("button", { name: "Cerrar", exact: true }).click();

    // Excepcion 1: el filtro sin resultados lo informa.
    await page.getByLabel("Hasta").fill("2000-01-01");
    await expect(page.getByText(/No hay cambios registrados para el parámetro/)).toBeVisible();

    // Se restaura el valor para no afectar otros escenarios.
    await page.goto("/parametros");
    await page.getByRole("row").filter({ hasText: nombre }).getByRole("button", { name: "Editar" }).click();
    await page.getByLabel(/^Valor/).fill(original);
    await page.getByRole("button", { name: "Guardar cambio" }).click();
    await expect(page.getByText("Editar parámetro")).toHaveCount(0);
  });
});
