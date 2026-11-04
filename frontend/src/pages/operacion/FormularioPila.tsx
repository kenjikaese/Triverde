import { useEffect, useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { mensajeDeError } from "@/lib/errores";
import type { PilaResumen } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Textarea } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";

function hoyLocal() {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
}

// V_FormularioPila (CU-35): alta de una pila con el codigo propuesto por el sistema.
export function FormularioPila({
  abierto,
  onCerrar,
  onCreada,
}: {
  abierto: boolean;
  onCerrar: () => void;
  onCreada: (pila: PilaResumen) => void;
}) {
  const [codigo, setCodigo] = useState("");
  const [fechaInicio, setFechaInicio] = useState(hoyLocal());
  const [observaciones, setObservaciones] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (!abierto) return;
    setFechaInicio(hoyLocal());
    setObservaciones("");
    setError(null);
    api
      .get<{ codigo: string }>("/pilas/codigo-sugerido/")
      .then((r) => setCodigo(r.data.codigo))
      .catch((err) => setError(mensajeDeError(err, "No se pudo proponer un código.")));
  }, [abierto]);

  async function crear(e: FormEvent) {
    e.preventDefault();
    setGuardando(true);
    setError(null);
    try {
      const res = await api.post<PilaResumen>("/pilas/", {
        codigo,
        fecha_inicio: fechaInicio,
        observaciones: observaciones || null,
      });
      onCreada(res.data);
    } catch (err) {
      setError(mensajeDeError(err, "No se pudo crear la pila."));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <Modal abierto={abierto} titulo="Nueva pila" onCerrar={onCerrar}>
      <form onSubmit={crear} className="space-y-4">
        {error && <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Campo label="Código" htmlFor="pila_codigo" requerido><Input id="pila_codigo" value={codigo} onChange={(e) => setCodigo(e.target.value)} required /></Campo>
          <Campo label="Fecha de inicio" htmlFor="pila_fecha" requerido><Input id="pila_fecha" type="date" value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)} required /></Campo>
        </div>
        <Campo label="Observaciones" htmlFor="pila_observaciones"><Textarea id="pila_observaciones" value={observaciones} onChange={(e) => setObservaciones(e.target.value)} /></Campo>
        <div className="flex justify-end gap-2 pt-2"><Button type="button" variante="secundario" onClick={onCerrar}>Cancelar</Button><Button type="submit" disabled={guardando}>{guardando ? "Guardando..." : "Crear pila"}</Button></div>
      </form>
    </Modal>
  );
}
