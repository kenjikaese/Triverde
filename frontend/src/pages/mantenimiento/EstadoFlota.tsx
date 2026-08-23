import { CalendarClock, Gauge, Wrench } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

// MOCK: datos de ejemplo, sin backend (modulo 8).
const equipos = [
  { codigo: "MQ-01", nombre: "Chipeadora Vermeer", estado: "operativa", horas: 1842, proxima: "En 34 h", tarea: "Cambio de cuchillas" },
  { codigo: "MQ-02", nombre: "Minicargador Bobcat", estado: "en mantencion", horas: 3267, proxima: "En ejecución", tarea: "Cambio de aceite" },
  { codigo: "MQ-03", nombre: "Cribadora Komptech", estado: "operativa", horas: 911, proxima: "En 89 h", tarea: "Inspección general" },
  { codigo: "VH-07", nombre: "Camión tolva Volvo", estado: "fuera de servicio", horas: 5420, proxima: "Vencida", tarea: "Reparación hidráulica" },
];

export function EstadoFlota() {
  return (
    <div>
      <PageHeader titulo="Estado de la flota" descripcion="Disponibilidad de equipos y próximos hitos de mantención." accion={<Button variante="secundario"><Wrench className="h-4 w-4" /> Planificar mantención</Button>} />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">{equipos.map((equipo) => <Card key={equipo.codigo}><CardBody><div className="flex items-start justify-between gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 text-slate-600"><Gauge className="h-5 w-5" /></div><Badge tono={tonoEstado(equipo.estado)}>{equipo.estado}</Badge></div><p className="mt-4 text-xs font-medium uppercase tracking-wide text-slate-400">{equipo.codigo}</p><h3 className="mt-1 font-semibold text-slate-900">{equipo.nombre}</h3><p className="mt-3 text-sm text-slate-600">{equipo.horas.toLocaleString("es-CL")} horas acumuladas</p><div className="mt-4 border-t border-slate-100 pt-3"><div className="flex items-center gap-2 text-xs text-slate-500"><CalendarClock className="h-4 w-4" /> Próxima mantención</div><p className={`mt-1 text-sm font-medium ${equipo.proxima === "Vencida" ? "text-red-700" : "text-slate-800"}`}>{equipo.proxima} · {equipo.tarea}</p></div></CardBody></Card>)}</div>
    </div>
  );
}
