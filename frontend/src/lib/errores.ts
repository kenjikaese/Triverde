import { isAxiosError } from "axios";

// Traduce la respuesta de error de la API a un texto que se le pueda mostrar a
// una persona. Sin esto, un error de validacion de DRF termina en pantalla como
// JSON crudo ({"monto":["El monto debe ser mayor a cero."]}), que no le dice
// nada al operador.

const CAMPOS: Record<string, string> = {
  cliente: "Cliente",
  producto: "Producto",
  cantidad: "Cantidad",
  monto: "Monto",
  distancia_km: "Distancia",
  receptor: "Quien retira",
  tipo: "Tipo de documento",
  estado_pago: "Estado de pago",
  detalles: "Productos de la venta",
  fecha: "Fecha",
  recepcion: "Recepción",
  venta: "Venta",
};

function primerTexto(valor: unknown): string | null {
  if (typeof valor === "string") return valor;
  if (Array.isArray(valor) && typeof valor[0] === "string") return valor[0];
  return null;
}

export function mensajeDeError(err: unknown, porDefecto: string): string {
  if (!isAxiosError(err)) return porDefecto;

  // Sin respuesta: el servidor no esta arriba o se corto la red.
  if (!err.response) {
    return "No se pudo conectar con el servidor. Revisa tu conexión e intenta de nuevo.";
  }

  if (err.response.status === 403) {
    return "Tu rol no tiene permiso para realizar esta acción.";
  }
  if (err.response.status >= 500) {
    return "El servidor tuvo un problema procesando la solicitud. Intenta de nuevo.";
  }

  const datos = err.response.data;
  if (typeof datos === "string" && datos.trim()) return datos;
  if (!datos || typeof datos !== "object") return porDefecto;

  const cuerpo = datos as Record<string, unknown>;

  // Mensaje general del backend.
  const general =
    primerTexto(cuerpo.detalle) ??
    primerTexto(cuerpo.detail) ??
    primerTexto(cuerpo.non_field_errors);
  if (general) return general;

  // Primer error de campo, con la etiqueta que ve el usuario en el formulario.
  for (const [campo, valor] of Object.entries(cuerpo)) {
    const texto = primerTexto(valor);
    if (texto) {
      const etiqueta = CAMPOS[campo];
      return etiqueta ? `${etiqueta}: ${texto}` : texto;
    }
    // Errores anidados de las lineas de la venta.
    if (Array.isArray(valor)) {
      for (const item of valor) {
        if (item && typeof item === "object") {
          for (const [subCampo, subValor] of Object.entries(
            item as Record<string, unknown>,
          )) {
            const subTexto = primerTexto(subValor);
            if (subTexto) {
              const etiqueta = CAMPOS[subCampo] ?? subCampo;
              return `${etiqueta}: ${subTexto}`;
            }
          }
        }
      }
    }
  }

  return porDefecto;
}
