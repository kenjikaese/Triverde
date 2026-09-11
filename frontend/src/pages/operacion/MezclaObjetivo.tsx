import { useEffect, useState } from "react";
import { CheckCircle2, FlaskConical, Layers } from "lucide-react";
import { api } from "@/lib/api";
import type { MezclaObjetivo as MezclaObjetivoData, PilaResumen } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export function MezclaObjetivo() {
  const [pilas, setPilas] = useState<PilaResumen[]>([]);
  const [pilaId, setPilaId] = useState("");
  const [mezcla, setMezcla] = useState<MezclaObjetivoData | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function cargarMezcla(id: string) {
    if (!id) return;
    setCargando(true);
    setError(null);
    try {
      const respuesta = await api.get<MezclaObjetivoData>(`/mezcla-objetivo/${id}/`);
      setMezcla(respuesta.data);
    } catch {
      setError("No se pudo calcular la mezcla de la pila seleccionada.");
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    api.get<PilaResumen[]>("/pilas/", { params: { estado: "en formacion" } })
      .then((respuesta) => {
        setPilas(respuesta.data);
        const primera = respuesta.data[0];
        if (primera) {
          setPilaId(String(primera.id));
          void cargarMezcla(String(primera.id));
        } else {
          setCargando(false);
        }
      })
      .catch(() => {
        setError("No se pudieron cargar las pilas.");
        setCargando(false);
      });
  }, []);

  const total = mezcla?.actual.reduce((suma, item) => suma + Number(item.volumen_m3), 0) ?? 0;
  const faltante = mezcla?.faltantes.reduce((suma, item) => suma + Number(item.volumen_m3), 0) ?? 0;
  const hayFaltanteSinCobertura = mezcla?.faltantes.some((item) => {
    const disponible = mezcla.disponibles.find((fila) => fila.categoria === item.categoria);
    return Number(item.volumen_m3) > Number(disponible?.volumen_m3 ?? 0);
  }) ?? false;

  return (
    <div>
      <PageHeader titulo="Mezcla objetivo" descripcion="Cálculo de faltantes según la receta vigente y el inventario disponible." accion={<Button onClick={() => void cargarMezcla(pilaId)} disabled={!pilaId || cargando}><FlaskConical className="h-4 w-4" /> {cargando ? "Calculando..." : "Recalcular mezcla"}</Button>} />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <Card className="mb-6"><CardBody className="flex flex-wrap items-center gap-3"><label htmlFor="pila-mezcla" className="inline-flex items-center gap-2 text-sm font-medium text-slate-700"><Layers className="h-4 w-4 text-brand-700" /> Pila</label><select id="pila-mezcla" value={pilaId} onChange={(event) => { setPilaId(event.target.value); void cargarMezcla(event.target.value); }} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"><option value="">Selecciona una pila</option>{pilas.map((pila) => <option key={pila.id} value={pila.id}>{pila.codigo} · {pila.estado}</option>)}</select></CardBody></Card>
      {!mezcla && !cargando ? <Card><CardBody className="py-10 text-center text-slate-500">No hay pilas disponibles para calcular.</CardBody></Card> : mezcla && <>
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card><CardBody><p className="text-sm text-slate-500">Receta vigente</p><p className="mt-1 text-3xl font-semibold text-slate-900">{mezcla.receta?.proporcion ?? "—"}</p><Badge tono={mezcla.receta ? "verde" : "ambar"}>{mezcla.receta?.nombre ?? "Sin receta vigente"}</Badge></CardBody></Card>
        <Card><CardBody><p className="text-sm text-slate-500">Volumen incorporado</p><p className="mt-1 text-3xl font-semibold text-slate-900">{total.toLocaleString("es-CL", { maximumFractionDigits: 2 })} m³</p><p className="text-xs text-slate-500">Pila {mezcla.pila_codigo}</p></CardBody></Card>
        <Card><CardBody><p className="text-sm text-slate-500">Faltante calculado</p><p className="mt-1 text-3xl font-semibold text-slate-900">{faltante.toLocaleString("es-CL", { maximumFractionDigits: 2 })} m³</p><p className="text-xs text-slate-500">Volumen que falta para la receta</p></CardBody></Card>
      </div>
      <Card><CardHeader titulo="Aporte por categoría" descripcion="Comparación entre lo incorporado, el faltante y el inventario disponible." /><Table><thead><tr><Th>Categoría</Th><Th>Incorporado</Th><Th>Faltante</Th><Th>Disponible</Th><Th>Estado</Th></tr></thead><TBody>{mezcla.actual.map((item) => { const faltanteItem = mezcla.faltantes.find((fila) => fila.categoria === item.categoria); const disponibleItem = mezcla.disponibles.find((fila) => fila.categoria === item.categoria); const falta = Number(faltanteItem?.volumen_m3 ?? 0); const disponible = Number(disponibleItem?.volumen_m3 ?? 0); return <tr key={item.categoria}><Td className="font-medium text-slate-800">{item.categoria === "seca" ? "Seca" : "Verde"}</Td><Td>{Number(item.volumen_m3).toLocaleString("es-CL")} m³</Td><Td>{falta.toLocaleString("es-CL")} m³</Td><Td>{disponible.toLocaleString("es-CL")} m³</Td><Td><Badge tono={falta > disponible ? "rojo" : "verde"}>{falta > disponible ? "Faltante" : "Cubierto"}</Badge></Td></tr>; })}</TBody></Table></Card>
      <div className={`mt-4 flex items-start gap-3 rounded-lg px-4 py-3 text-sm ${mezcla.mensaje || hayFaltanteSinCobertura ? "bg-amber-50 text-amber-800" : "bg-brand-50 text-brand-800"}`}><CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" /><p>{mezcla.mensaje ?? (hayFaltanteSinCobertura ? "El inventario no cubre todo el faltante; revise la bandeja de alertas." : faltante > 0 ? "El faltante esta cubierto por el inventario disponible." : "La composición actual cumple la proporción de la receta.")}</p></div>
      </>}
    </div>
  );
}
