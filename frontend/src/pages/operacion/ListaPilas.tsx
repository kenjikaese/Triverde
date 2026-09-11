import { useEffect, useState } from "react";
import { Layers, CalendarDays, Sprout } from "lucide-react";
import { api } from "@/lib/api";
import type { PilaResumen } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";

const num = (valor: string | number) => Number(valor) || 0;

function fecha(iso: string) {
  const d = new Date(iso + "T00:00:00");
  return isNaN(d.getTime()) ? iso : d.toLocaleDateString("es-CL");
}

export function ListaPilas() {
  const [pilas, setPilas] = useState<PilaResumen[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<PilaResumen[]>("/pilas/")
      .then((r) => setPilas(r.data))
      .catch(() => setError("No se pudieron cargar las pilas."))
      .finally(() => setCargando(false));
  }, []);

  const activas = pilas.filter((p) => p.estado !== "cerrada");
  const enFormacion = pilas.filter((p) => p.estado === "en formacion").length;
  const volumenProceso = activas.reduce((t, p) => t + num(p.volumen_total_m3), 0);

  return (
    <div>
      <PageHeader titulo="Pilas de compostaje" descripcion="Seguimiento de los lotes de compostaje: estado del ciclo y volumen incorporado." />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card><CardBody className="flex items-center gap-4"><Layers className="h-8 w-8 text-brand-700" /><div><p className="text-2xl font-semibold text-slate-900">{activas.length}</p><p className="text-sm text-slate-500">Pilas activas</p></div></CardBody></Card>
        <Card><CardBody className="flex items-center gap-4"><CalendarDays className="h-8 w-8 text-sky-700" /><div><p className="text-2xl font-semibold text-slate-900">{volumenProceso.toLocaleString("es-CL", { maximumFractionDigits: 2 })} m³</p><p className="text-sm text-slate-500">Volumen en proceso</p></div></CardBody></Card>
        <Card><CardBody className="flex items-center gap-4"><Sprout className="h-8 w-8 text-amber-700" /><div><p className="text-2xl font-semibold text-slate-900">{enFormacion}</p><p className="text-sm text-slate-500">En formación</p></div></CardBody></Card>
      </div>
      <Card>
        {cargando ? (
          <CardBody className="py-10 text-center text-slate-500">Cargando pilas...</CardBody>
        ) : pilas.length === 0 ? (
          <CardBody className="py-10 text-center text-slate-500">No hay pilas registradas.</CardBody>
        ) : (
          <Table>
            <thead><tr><Th>Código</Th><Th>Fecha inicio</Th><Th>Estado</Th><Th>Volumen incorporado</Th></tr></thead>
            <TBody>
              {pilas.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50">
                  <Td className="font-medium text-slate-800">{p.codigo}</Td>
                  <Td>{fecha(p.fecha_inicio)}</Td>
                  <Td><Badge tono={tonoEstado(p.estado)}>{p.estado}</Badge></Td>
                  <Td>{num(p.volumen_total_m3).toLocaleString("es-CL", { maximumFractionDigits: 2 })} m³</Td>
                </tr>
              ))}
            </TBody>
          </Table>
        )}
      </Card>
    </div>
  );
}
