import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Layers, CalendarDays, Plus, Scissors, Sprout } from "lucide-react";
import { api } from "@/lib/api";
import type { PilaResumen } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { FormularioPila } from "./FormularioPila";
import { RegistroProceso } from "./RegistroProceso";

const num = (valor: string | number) => Number(valor) || 0;

function fecha(iso: string) {
  const d = new Date(iso + "T00:00:00");
  return isNaN(d.getTime()) ? iso : d.toLocaleDateString("es-CL");
}

export function ListaPilas() {
  const [pilas, setPilas] = useState<PilaResumen[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [formulario, setFormulario] = useState(false);
  const [triturando, setTriturando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const navegar = useNavigate();

  const cargar = useCallback(() => {
    api
      .get<PilaResumen[]>("/pilas/")
      .then((r) => setPilas(r.data))
      .catch(() => setError("No se pudieron cargar las pilas."))
      .finally(() => setCargando(false));
  }, []);
  useEffect(cargar, [cargar]);

  const activas = pilas.filter((p) => p.estado !== "cerrada");
  const enFormacion = pilas.filter((p) => p.estado === "en formacion").length;
  const volumenProceso = activas.reduce((t, p) => t + num(p.volumen_total_m3), 0);

  return (
    <div>
      <PageHeader titulo="Pilas de compostaje" descripcion="Seguimiento de los lotes de compostaje: estado del ciclo y volumen incorporado." accion={<div className="flex gap-2"><Button variante="secundario" onClick={() => setTriturando(true)}><Scissors className="h-4 w-4" /> Registrar triturado</Button><Button onClick={() => setFormulario(true)}><Plus className="h-4 w-4" /> Nueva pila</Button></div>} />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {aviso && <div className="mb-4 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800">{aviso}</div>}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card><CardBody className="flex items-center gap-4"><Layers className="h-8 w-8 text-brand-700" /><div><p className="text-2xl font-semibold text-slate-900">{activas.length}</p><p className="text-sm text-slate-500">Pilas activas</p></div></CardBody></Card>
        <Card><CardBody className="flex items-center gap-4"><CalendarDays className="h-8 w-8 text-sky-700" /><div><p className="text-2xl font-semibold text-slate-900">{volumenProceso.toLocaleString("es-CL", { maximumFractionDigits: 2 })} m³</p><p className="text-sm text-slate-500">Volumen en proceso</p></div></CardBody></Card>
        <Card><CardBody className="flex items-center gap-4"><Sprout className="h-8 w-8 text-amber-700" /><div><p className="text-2xl font-semibold text-slate-900">{enFormacion}</p><p className="text-sm text-slate-500">En formación</p></div></CardBody></Card>
      </div>
      <Card>
        {cargando ? (
          <CardBody className="py-10 text-center text-slate-500">Cargando pilas...</CardBody>
        ) : pilas.length === 0 ? (
          <CardBody className="py-10 text-center text-slate-500">No hay pilas registradas. Crea la primera con "Nueva pila".</CardBody>
        ) : (
          <Table>
            <thead><tr><Th>Código</Th><Th>Fecha inicio</Th><Th>Estado</Th><Th>Volumen incorporado</Th></tr></thead>
            <TBody>
              {pilas.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50">
                  <Td className="font-medium"><Link to={`/pilas/${p.id}`} className="text-brand-700 hover:underline">{p.codigo}</Link></Td>
                  <Td>{fecha(p.fecha_inicio)}</Td>
                  <Td><Badge tono={tonoEstado(p.estado)}>{p.estado}</Badge></Td>
                  <Td>{num(p.volumen_total_m3).toLocaleString("es-CL", { maximumFractionDigits: 2 })} m³</Td>
                </tr>
              ))}
            </TBody>
          </Table>
        )}
      </Card>
      <FormularioPila abierto={formulario} onCerrar={() => setFormulario(false)} onCreada={(pila) => navegar(`/pilas/${pila.id}`)} />
      <RegistroProceso tipo={triturando ? "triturado" : null} onCerrar={() => setTriturando(false)} onRegistrado={(mensaje) => { setTriturando(false); setAviso(mensaje); cargar(); }} />
    </div>
  );
}
