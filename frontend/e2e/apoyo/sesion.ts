import type { Page } from "@playwright/test";

/** Credenciales que siembra `manage.py seed_e2e`. */
export const CUENTAS = {
  admin: { usuario: "admin", clave: "triverde-e2e-2026" },
  operador: { usuario: "operador", clave: "triverde-e2e-2026" },
};

/** Entra por la pantalla de login y espera a llegar al panel de control. */
export async function entrar(
  page: Page,
  cuenta: keyof typeof CUENTAS = "admin",
): Promise<void> {
  const { usuario, clave } = CUENTAS[cuenta];
  await page.goto("/login");
  await page.getByLabel("Usuario").fill(usuario);
  await page.getByLabel("Clave").fill(clave);
  await page.getByRole("button", { name: /ingresar|entrar/i }).click();
  await page.waitForURL((url) => !url.pathname.startsWith("/login"));
}

/**
 * Registra las llamadas a la API que hace el navegador.
 *
 * Complementa las trazas del servidor: verifica que la vista pidio el endpoint
 * correcto (por ejemplo `POST /ventas/12/despachar/` y no un PATCH directo al
 * estado de la venta).
 */
export function registrarLlamadas(page: Page): string[] {
  const llamadas: string[] = [];
  page.on("request", (peticion) => {
    const url = new URL(peticion.url());
    if (url.pathname.startsWith("/api/")) {
      llamadas.push(`${peticion.method()} ${url.pathname}`);
    }
  });
  return llamadas;
}

/**
 * Selecciona la opcion de un `<select>` cuyo texto contiene el fragmento dado.
 *
 * `selectOption({ label })` exige el texto exacto, y varias opciones de la app
 * componen la etiqueta con el precio y la unidad ("Compost premium 40 L ·
 * $4.500 / saco"). Esto resuelve el value real a partir de un fragmento.
 */
export async function elegirOpcion(
  page: Page,
  etiqueta: string | RegExp,
  fragmento: string,
): Promise<void> {
  // Por rol y no por getByLabel: los campos obligatorios llevan un asterisco
  // en la etiqueta, y hay botones cuyo aria-label contiene la misma palabra
  // que el campo ("Producto" / "Quitar producto").
  const select = page.getByRole("combobox", {
    name: typeof etiqueta === "string" ? new RegExp(etiqueta) : etiqueta,
  });
  const valor = await select
    .locator("option", { hasText: fragmento })
    .first()
    .getAttribute("value");
  if (!valor) {
    throw new Error(`No hay una opción que contenga "${fragmento}".`);
  }
  await select.selectOption(valor);
}
