import { expect, test } from "@playwright/test";
import { entrar, registrarLlamadas } from "./apoyo/sesion";
import { esperarTrazas, leerTrazasDesde, marcarInicioTrazas } from "./apoyo/trazas";

// Primer dia del mes en curso y hoy, en ISO: el periodo que abarca la descarga
// que siembra seed_e2e (fecha = hoy).
function periodoDelMes(): { desde: string; hasta: string } {
  const hoy = new Date();
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { desde: iso(new Date(hoy.getFullYear(), hoy.getMonth(), 1)), hasta: iso(hoy) };
}

// CU-73, CU-76 - Reportes por periodo y exportacion (Modulo 10, Parte C).
test.describe("Reportes por periodo", () => {
  test("CU-73 y CU-76: el reporte de recepciones lo agrega el servidor y se exporta sin recalcular", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    const llamadas = registrarLlamadas(page);
    const { desde, hasta } = periodoDelMes();
    await entrar(page, "admin");

    await page.goto("/reportes");
    await page.getByLabel("Tipo de reporte").selectOption("recepciones");
    await page.getByLabel("Desde").fill(desde);
    await page.getByLabel("Hasta").fill(hasta);
    // Acotado al cliente del seed: otros escenarios registran descargas de
    // otros clientes en el mismo periodo.
    await page.getByLabel("Cliente").selectOption({ label: "Vivero Los Aromos" });
    await page.getByRole("button", { name: "Generar reporte" }).click();

    // La agregacion la hace el servidor y queda guardada en el Reporte.
    await esperarTrazas(marca, ["CU-73 reporte.generado"]);
    await expect(page.getByText("Reporte generado.")).toBeVisible();
    const porMaterial = page.getByRole("row", { name: /Rama verde/ }).first();
    await expect(porMaterial).toContainText("20 m³");
    await expect(porMaterial).toContainText("5.000 kg");
    expect(llamadas).toContain("POST /api/v1/reportes/");

    await page.screenshot({ path: "e2e-evidencias/cu-73-reporte-recepciones.png", fullPage: true });

    // CU-76: exporta el reporte ya generado en otro formato, sin volver a
    // generarlo (no hay un segundo POST ni una segunda traza de generacion).
    const marcaExport = await marcarInicioTrazas();
    const [descarga] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "CSV" }).click(),
    ]);
    expect(descarga.suggestedFilename()).toMatch(/^reporte-\d+\.csv$/);
    const lineas = await esperarTrazas(marcaExport, ["CU-76 reporte.exportado", "formato=csv"]);
    expect(lineas.some((l) => l.includes("reporte.generado"))).toBe(false);
    expect(llamadas.filter((l) => l === "POST /api/v1/reportes/")).toHaveLength(1);
  });

  test("CU-73 excepcion 1: un rango con termino anterior al inicio se rechaza", async ({ page }) => {
    const marca = await marcarInicioTrazas();
    await entrar(page, "admin");

    await page.goto("/reportes");
    await page.getByLabel("Tipo de reporte").selectOption("recepciones");
    await page.getByLabel("Desde").fill("2026-09-20");
    await page.getByLabel("Hasta").fill("2026-09-10");
    await page.getByRole("button", { name: "Generar reporte" }).click();

    await expect(page.getByText(/no puede ser anterior a la fecha de inicio/)).toBeVisible();
    // No se genero nada: el servidor rechazo antes de crear el Reporte.
    const lineas = await leerTrazasDesde(marca);
    expect(lineas.some((l) => l.includes("reporte.generado"))).toBe(false);
  });
});

// CU-72, CU-77 - Panel de control y su personalizacion (Modulo 10, Parte D).
// El orden importa: el panel parte del conjunto por defecto (seed_e2e borra la
// preferencia) y el escenario de personalizacion lo modifica.
test.describe("Panel de control", () => {
  test("CU-72: sin personalizar muestra inventario, produccion y ventas, y marca las pilas en proceso", async ({
    page,
  }) => {
    const marca = await marcarInicioTrazas();
    const llamadas = registrarLlamadas(page);
    await entrar(page, "admin");

    await page.goto("/");
    await esperarTrazas(marca, [
      "CU-72 panel.armado",
      "indicadores=['inventario', 'produccion', 'ventas']",
    ]);
    await expect(page.getByText("Inventario por material y etapa")).toBeVisible();
    await expect(page.getByText("Pilas recientes")).toBeVisible();
    await expect(page.getByText("Ventas del mes en curso")).toBeVisible();
    // La pila del seed esta cerrada: aparece con su estado, sin la marca.
    await expect(page.getByRole("row", { name: /P-E2E-01/ })).toContainText("Cerrada");
    expect(llamadas).toContain("GET /api/v1/panel/");

    await page.screenshot({ path: "e2e-evidencias/cu-72-panel-control.png", fullPage: true });
  });

  test("CU-77: exige al menos un indicador, guarda la seleccion y no re-guarda sin cambios", async ({
    page,
  }) => {
    await entrar(page, "admin");
    await page.goto("/");

    await page.getByRole("button", { name: "Personalizar" }).click();
    const inventario = page.getByLabel("Inventario por material y etapa");
    const produccion = page.getByLabel("Produccion reciente (pilas y procesos)");
    const ventas = page.getByLabel("Ventas del mes en curso");
    await expect(inventario).toBeChecked();

    // Excepcion 1: sin ningun indicador el servidor rechaza el guardado.
    let marca = await marcarInicioTrazas();
    await inventario.uncheck();
    await produccion.uncheck();
    await ventas.uncheck();
    await page.getByRole("button", { name: "Guardar preferencias" }).click();
    await esperarTrazas(marca, ["CU-77 panel.preferencias_rechazadas"]);
    await expect(page.getByText("Debe seleccionar al menos un indicador.")).toBeVisible();

    // Con un indicador se crea el PanelControl y el panel se compone con el.
    marca = await marcarInicioTrazas();
    await ventas.check();
    await page.getByRole("button", { name: "Guardar preferencias" }).click();
    await esperarTrazas(marca, [
      "CU-77 panel.preferencias_guardadas",
      "indicadores=['ventas']",
      "CU-72 panel.armado",
      "indicadores=['ventas']",
    ]);
    await expect(page.getByText("Preferencias guardadas.")).toBeVisible();
    await expect(page.getByText("Ventas del mes en curso")).toBeVisible();
    await expect(page.getByText("Inventario por material y etapa")).toHaveCount(0);

    // Excepcion 2: guardar la misma seleccion no genera una actualizacion.
    marca = await marcarInicioTrazas();
    await page.getByRole("button", { name: "Personalizar" }).click();
    await expect(page.getByLabel("Ventas del mes en curso")).toBeChecked();
    await page.getByRole("button", { name: "Guardar preferencias" }).click();
    const lineas = await esperarTrazas(marca, ["CU-77 panel.preferencias_sin_cambios"]);
    expect(lineas.some((l) => l.includes("panel.preferencias_guardadas"))).toBe(false);
    await expect(page.getByText("No hubo cambios en la seleccion")).toBeVisible();

    await page.screenshot({ path: "e2e-evidencias/cu-77-personalizar-panel.png", fullPage: true });
  });

  test("Permisos: el operador ve el resumen operativo y no pide el panel del administrador", async ({
    page,
  }) => {
    const llamadas = registrarLlamadas(page);
    await entrar(page, "operador");

    await page.goto("/");
    await expect(page.getByText("Resumen de la operacion de hoy.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Personalizar" })).toHaveCount(0);
    expect(llamadas.some((l) => l.includes("/api/v1/panel/"))).toBe(false);
  });
});
