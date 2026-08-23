import { useState } from "react";
import { Bell, Check } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

// MOCK: datos de ejemplo, sin backend (modulo 7).
const alertasIniciales = [
  { id: 1, origen: "Mantención", nivel: "Vencida", titulo: "Cambio de aceite minicargador", detalle: "Superó en 12 h el intervalo programado.", fecha: "22-08-2026" },
  { id: 2, origen: "Mezcla", nivel: "Próxima", titulo: "Control de temperatura P-024", detalle: "Medición requerida antes de las 16:00.", fecha: "22-08-2026" },
  { id: 3, origen: "Documento", nivel: "Próxima", titulo: "Renovación resolución sanitaria", detalle: "La vigencia vence en 28 días.", fecha: "20-09-2026" },
  { id: 4, origen: "Mantención", nivel: "Próxima", titulo: "Engrase de chipeadora", detalle: "Faltan 6 horas de uso para el servicio.", fecha: "24-08-2026" },
];

export function Alertas() {
  const [resueltas, setResueltas] = useState<number[]>([]);
  const activas = alertasIniciales.filter((alerta) => !resueltas.includes(alerta.id));
  return (
    <div>
      <PageHeader titulo="Alertas" descripcion="Pendientes operativos, documentales y de mantención que requieren atención." />
      <div className="space-y-3">
        {activas.length === 0 ? <Card><CardBody className="py-10 text-center text-slate-500">No hay alertas activas.</CardBody></Card> : activas.map((alerta) => (
          <Card key={alerta.id}><CardBody className="flex flex-col gap-4 sm:flex-row sm:items-center"><div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${alerta.nivel === "Vencida" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}><Bell className="h-5 w-5" /></div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><p className="font-semibold text-slate-900">{alerta.titulo}</p><Badge tono={tonoEstado(alerta.nivel)}>{alerta.nivel}</Badge><Badge tono="gris">{alerta.origen}</Badge></div><p className="mt-1 text-sm text-slate-600">{alerta.detalle}</p><p className="mt-1 text-xs text-slate-400">Fecha objetivo: {alerta.fecha}</p></div><Button variante="secundario" tamano="sm" onClick={() => setResueltas((actuales) => [...actuales, alerta.id])}><Check className="h-4 w-4" /> Resolver</Button></CardBody></Card>
        ))}
      </div>
    </div>
  );
}
