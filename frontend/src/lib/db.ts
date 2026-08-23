// Cola local sin conexion (CU-32). Envoltorio minimo de IndexedDB: una sola
// object store con las operaciones capturadas offline, indexadas por id_local
// (el mismo UUID que hace idempotente la sincronizacion en el servidor, CU-33).
// Sin dependencias externas para que el equipo pueda leer el mecanismo.

const DB_NAME = "triverde";
const STORE = "cola_operaciones";
const VERSION = 1;

export type EstadoLocal = "pendiente" | "en conflicto" | "rechazada";

export interface OperacionCola {
  id_local: string;
  tipo: "recepcion";
  capturado_en: string;
  datos: Record<string, unknown>;
  estado_local: EstadoLocal;
  motivo?: string;
}

function abrir(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "id_local" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function promesa<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function guardarOperacion(op: OperacionCola): Promise<void> {
  const db = await abrir();
  const store = db.transaction(STORE, "readwrite").objectStore(STORE);
  await promesa(store.put(op));
  db.close();
}

export async function listarOperaciones(): Promise<OperacionCola[]> {
  const db = await abrir();
  const store = db.transaction(STORE, "readonly").objectStore(STORE);
  const todas = await promesa(store.getAll() as IDBRequest<OperacionCola[]>);
  db.close();
  return todas;
}

export async function eliminarOperacion(id_local: string): Promise<void> {
  const db = await abrir();
  const store = db.transaction(STORE, "readwrite").objectStore(STORE);
  await promesa(store.delete(id_local));
  db.close();
}

export async function actualizarOperacion(
  id_local: string,
  cambios: Partial<OperacionCola>,
): Promise<void> {
  const db = await abrir();
  const store = db.transaction(STORE, "readwrite").objectStore(STORE);
  const actual = await promesa(store.get(id_local) as IDBRequest<OperacionCola>);
  if (actual) {
    await promesa(store.put({ ...actual, ...cambios }));
  }
  db.close();
}
