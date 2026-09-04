import { expect } from "@playwright/test";
import { readFile, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const aqui = dirname(fileURLToPath(import.meta.url));
const ARCHIVO_TRAZAS = join(
  aqui,
  "..",
  "..",
  "..",
  "backend",
  "logs",
  "trazas-cu.log",
);

/**
 * Tamano actual del archivo de trazas.
 *
 * Cada escenario lo captura al empezar y solo afirma sobre lo que se escribio
 * despues, para no arrastrar las trazas de los escenarios anteriores.
 */
export async function marcarInicioTrazas(): Promise<number> {
  try {
    const info = await stat(ARCHIVO_TRAZAS);
    return info.size;
  } catch {
    return 0;
  }
}

/** Lineas de traza escritas despues del marcador. */
export async function leerTrazasDesde(marca: number): Promise<string[]> {
  let contenido: Buffer;
  try {
    contenido = await readFile(ARCHIVO_TRAZAS);
  } catch {
    return [];
  }
  // Se corta sobre el buffer y no sobre el texto: `marca` viene de stat().size,
  // que cuenta bytes, y las trazas llevan tildes (un caracter, dos bytes). Con
  // slice() sobre el string el corte quedaria desplazado.
  return contenido
    .subarray(marca)
    .toString("utf-8")
    .split(/\r?\n/)
    .map((linea) => linea.trim())
    .filter(Boolean);
}

/**
 * Afirma que las trazas esperadas aparecieron, en ese orden.
 *
 * Cada elemento de `esperadas` se busca como subcadena de una linea; no hace
 * falta reproducir el timestamp ni todos los campos. Las lineas intermedias se
 * ignoran: lo que se verifica es la secuencia, no la exclusividad.
 *
 * Esto es lo que demuestra que la operacion paso por donde se espera. Un
 * assert sobre la pantalla no distingue si el calculo lo hizo el servidor o el
 * navegador; la traza si.
 */
export async function esperarTrazas(
  marca: number,
  esperadas: string[],
  mensaje?: string,
): Promise<string[]> {
  let lineas: string[] = [];
  await expect
    .poll(
      async () => {
        lineas = await leerTrazasDesde(marca);
        return contieneSecuencia(lineas, esperadas);
      },
      {
        timeout: 10_000,
        message:
          mensaje ??
          `No aparecieron las trazas esperadas:\n  ${esperadas.join("\n  ")}`,
      },
    )
    .toBe(true);
  return lineas;
}

/** Afirma que NINGUNA linea contiene el fragmento indicado. */
export async function esperarSinTraza(
  marca: number,
  fragmento: string,
): Promise<void> {
  const lineas = await leerTrazasDesde(marca);
  const encontrada = lineas.find((linea) => linea.includes(fragmento));
  expect(
    encontrada,
    `No se esperaba la traza "${fragmento}", pero apareció: ${encontrada}`,
  ).toBeUndefined();
}

/**
 * true si las esperadas aparecen como subsecuencia de las lineas.
 *
 * Varias esperadas pueden calzar en la misma linea: es comun afirmar sobre el
 * nombre del evento y sobre sus campos por separado
 * ("CU-58 venta.creada" y "total=135000.00"), y ambos viven en una sola traza.
 */
function contieneSecuencia(lineas: string[], esperadas: string[]): boolean {
  let indice = 0;
  for (const linea of lineas) {
    while (indice < esperadas.length && linea.includes(esperadas[indice])) {
      indice += 1;
    }
    if (indice === esperadas.length) return true;
  }
  return indice === esperadas.length;
}
