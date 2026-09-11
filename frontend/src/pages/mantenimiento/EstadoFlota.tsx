import { useEffect, useMemo, useState } from "react";
import { CalendarClock, Gauge, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import type { EstadoFlotaItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Field";

export function EstadoFlota() {
  const [equipos, setEquipos] = useState<EstadoFlotaItem[]>([]);
  const [estado, setEstado] = useState("");
  const [tipo, setTipo] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function cargar() {
    setCargando(true); setError(null);
    api.get<EstadoFlotaItem[]>("/maquinaria/estado-flota/")
      .then((r) => setEquipos(r.data))
      .catch(() => setError("No se pudo cargar el estado de la flota."))
      .finally(() => setCargando(false));
  }
  useEffect(cargar, []);
  const visibles = useMemo(() => equipos.filter((e) => (!estado || e.estado_operativo === estado) && (!tipo || e.clase_activo === tipo)), [equipos, estado, tipo]);

  return <div>
    <PageHeader titulo="Estado de la flota" descripcion="Disponibilidad, horómetros y próximas mantenciones." accion={<Button variante="secundario" onClick={cargar}><RefreshCw className="h-4 w-4" /> Actualizar</Button>} />
    {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
    <div className="mb-4 flex max-w-xl gap-3"><Select aria-label="Filtrar por estado" value={estado} onChange={(e) => setEstado(e.target.value)}><option value="">Todos los estados</option><option value="operativa">Operativa</option><option value="en mantencion">En mantención</option><option value="fuera de servicio">Fuera de servicio</option></Select><Select aria-label="Filtrar por tipo" value={tipo} onChange={(e) => setTipo(e.target.value)}><option value="">Todos los activos</option><option value="maquinaria">Maquinaria</option><option value="vehiculo">Vehículos</option></Select></div>
    {cargando ? <p className="py-10 text-center text-slate-500">Cargando...</p> : visibles.length === 0 ? <Card><CardBody><p className="text-center text-sm text-slate-500">No hay activos para este filtro.</p></CardBody></Card> : <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">{visibles.map((equipo) => <Card key={`${equipo.clase_activo}-${equipo.id}`}><CardBody>
      <div className="flex items-start justify-between gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 text-slate-600"><Gauge className="h-5 w-5" /></div><Badge tono={tonoEstado(equipo.estado_operativo)}>{equipo.estado_operativo}</Badge></div>
      <p className="mt-4 text-xs font-medium uppercase tracking-wide text-slate-400">{equipo.codigo} · {equipo.tipo}</p><h3 className="mt-1 font-semibold text-slate-900">{equipo.nombre}</h3><p className="mt-3 text-sm text-slate-600">{Number(equipo.horometro).toLocaleString("es-CL")} horas acumuladas</p>
      <div className="mt-4 border-t border-slate-100 pt-3"><div className="flex items-center gap-2 text-xs text-slate-500"><CalendarClock className="h-4 w-4" /> Próxima mantención</div>{equipo.proxima_mantencion ? <><p className="mt-1 text-sm font-medium text-slate-800">{equipo.proxima_mantencion.descripcion}</p><p className="mt-1 text-xs text-slate-500">{equipo.proxima_mantencion.fecha_programada ?? `${equipo.proxima_mantencion.umbral_horas} h`}</p></> : <p className="mt-1 text-sm text-slate-500">Sin mantención programada</p>}{equipo.alerta && <p className={`mt-3 rounded-lg px-3 py-2 text-xs ${equipo.nivel_alerta === "critica" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700"}`}>{equipo.alerta}</p>}</div>
    </CardBody></Card>)}</div>}
  </div>;
}
