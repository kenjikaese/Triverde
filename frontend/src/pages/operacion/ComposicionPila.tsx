import { useEffect, useMemo, useState, type FormEvent } from "react";
import { CheckCircle2, Plus } from "lucide-react";
import { api } from "@/lib/api";
import { mensajeDeError } from "@/lib/errores";
import type { Existencia, Material, Recepcion } from "@/lib/types";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";

// V_ComposicionPila (CU-36): material del inventario disponible que entra a la pila.
export function ComposicionPila({
  pilaId,
  onCambio,
  onConfirmada,
}: {
  pilaId: number;
  onCambio: () => void;
  onConfirmada: () => void;
}) {
  const [materiales, setMateriales] = useState<Material[]>([]);
  const [existencias, setExistencias] = useState<Existencia[]>([]);
  const [recibidas, setRecibidas] = useState<Recepcion[]>([]);
  const [material, setMaterial] = useState("");
  const [volumen, setVolumen] = useState("");
  const [origen, setOrigen] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  function cargarInventario() {
    return api.get<Existencia[]>("/inventario/").then((r) => setExistencias(r.data));
  }

  useEffect(() => {
    Promise.all([
      api.get<Material[]>("/materiales/", { params: { estado: "activo" } }),
      api.get<Recepcion[]>("/recepciones/", { params: { estado: "recibida" } }),
      cargarInventario(),
    ])
      .then(([m, r]) => {
        setMateriales(m.data);
        setRecibidas(r.data);
      })
      .catch((err) => setError(mensajeDeError(err, "No se pudo cargar el inventario disponible.")));
  }, []);

  // Regla del servidor: lo que se tritura entra como chip; el resto, como se recibio.
  const disponibles = useMemo(
    () =>
      materiales
        .map((m) => {
          const etapa = m.admite_chip ? "chip" : "por triturar";
          const fila = existencias.find((e) => e.material === m.id && e.etapa === etapa);
          return { material: m, etapa, volumen: Number(fila?.volumen_m3 ?? 0) };
        })
        .filter((d) => d.volumen > 0),
    [materiales, existencias],
  );

  const descargas = useMemo(
    () =>
      recibidas.flatMap((r) =>
        r.detalles
          .filter((d) => String(d.material) === material)
          .map((d) => ({ id: d.id, etiqueta: `Recepción #${r.id} · ${r.cliente_razon_social ?? ""} · ${d.volumen_m3} m³` })),
      ),
    [recibidas, material],
  );

  async function agregar(e: FormEvent) {
    e.preventDefault();
    setGuardando(true);
    setError(null);
    try {
      await api.post(`/pilas/${pilaId}/composicion/`, {
        material: Number(material),
        volumen_m3: volumen,
        detalle_recepcion: origen ? Number(origen) : null,
      });
      setMaterial("");
      setVolumen("");
      setOrigen("");
      await cargarInventario();
      onCambio();
    } catch (err) {
      setError(mensajeDeError(err, "No se pudo agregar el material."));
    } finally {
      setGuardando(false);
    }
  }

  async function confirmar() {
    setGuardando(true);
    setError(null);
    try {
      await api.post(`/pilas/${pilaId}/confirmar-composicion/`);
      onConfirmada();
    } catch (err) {
      setError(mensajeDeError(err, "No se pudo confirmar la composición."));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <Card className="mb-6">
      <CardHeader titulo="Agregar material a la pila" />
      <CardBody>
        {error && <div className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        <form onSubmit={agregar} className="grid grid-cols-1 gap-4 md:grid-cols-4 md:items-end">
          <Campo label="Material" htmlFor="composicion_material" requerido>
            <Select id="composicion_material" value={material} onChange={(e) => { setMaterial(e.target.value); setOrigen(""); }} required>
              <option value="">Selecciona un material</option>
              {disponibles.map((d) => <option key={d.material.id} value={d.material.id}>{d.material.nombre} ({d.volumen.toLocaleString("es-CL")} m³ en {d.etapa})</option>)}
            </Select>
          </Campo>
          <Campo label="Cantidad (m³)" htmlFor="composicion_volumen" requerido><Input id="composicion_volumen" type="number" step="0.01" value={volumen} onChange={(e) => setVolumen(e.target.value)} required /></Campo>
          <Campo label="Descarga de origen" htmlFor="composicion_origen">
            <Select id="composicion_origen" value={origen} onChange={(e) => setOrigen(e.target.value)} disabled={descargas.length === 0}>
              <option value="">Sin indicar</option>
              {descargas.map((d) => <option key={d.id} value={d.id}>{d.etiqueta}</option>)}
            </Select>
          </Campo>
          <Button type="submit" variante="secundario" disabled={guardando}><Plus className="h-4 w-4" /> Agregar material</Button>
        </form>
        {disponibles.length === 0 && <p className="mt-3 text-sm text-slate-500">No hay material disponible en el inventario. El material que admite chip entra a la pila ya triturado: regístrale un triturado primero.</p>}
        <div className="mt-4 flex justify-end"><Button onClick={confirmar} disabled={guardando}><CheckCircle2 className="h-4 w-4" /> Confirmar composición</Button></div>
      </CardBody>
    </Card>
  );
}
