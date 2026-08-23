// Sincronizacion de la cola local (CU-33). Envia el lote acumulado offline al
// endpoint idempotente POST /sincronizacion/ y aplica el resultado por operacion.
import { api } from "@/lib/api";
import {
  actualizarOperacion,
  eliminarOperacion,
  guardarOperacion,
  listarOperaciones,
  type OperacionCola,
} from "@/lib/db";

interface ResultadoSync {
  id_local: string;
  estado: "sincronizada" | "en conflicto" | "rechazada";
  id_servidor?: number;
  motivo?: string;
}

// Encola una recepcion capturada sin conexion. Genera el id_local (UUID) que
// hace idempotente el envio: reintentar no duplica.
export async function encolarRecepcion(
  datos: Record<string, unknown>,
): Promise<OperacionCola> {
  const op: OperacionCola = {
    id_local: crypto.randomUUID(),
    tipo: "recepcion",
    capturado_en: new Date().toISOString(),
    datos: { ...datos },
    estado_local: "pendiente",
  };
  await guardarOperacion(op);
  return op;
}

export interface ResumenSync {
  sincronizadas: number;
  enConflicto: number;
  rechazadas: number;
  sinConexion?: boolean;
}

// Vacia la cola contra el servidor. Devuelve un resumen para la UI.
export async function sincronizar(): Promise<ResumenSync> {
  const cola = await listarOperaciones();
  if (cola.length === 0) {
    return { sincronizadas: 0, enConflicto: 0, rechazadas: 0 };
  }

  const operaciones = cola.map((op) => ({
    id_local: op.id_local,
    tipo: op.tipo,
    capturado_en: op.capturado_en,
    datos: op.datos,
  }));

  let resultados: ResultadoSync[];
  try {
    const res = await api.post<{ resultados: ResultadoSync[] }>(
      "/sincronizacion/",
      { operaciones },
    );
    resultados = res.data.resultados;
  } catch {
    return { sincronizadas: 0, enConflicto: 0, rechazadas: 0, sinConexion: true };
  }

  const resumen: ResumenSync = {
    sincronizadas: 0,
    enConflicto: 0,
    rechazadas: 0,
  };
  for (const r of resultados) {
    if (r.estado === "sincronizada") {
      await eliminarOperacion(r.id_local);
      resumen.sincronizadas++;
    } else if (r.estado === "en conflicto") {
      await actualizarOperacion(r.id_local, {
        estado_local: "en conflicto",
        motivo: r.motivo,
      });
      resumen.enConflicto++;
    } else {
      await actualizarOperacion(r.id_local, {
        estado_local: "rechazada",
        motivo: r.motivo,
      });
      resumen.rechazadas++;
    }
  }
  return resumen;
}
