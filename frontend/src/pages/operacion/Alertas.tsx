import { useEffect, useState } from "react";
import { Bell, Check } from "lucide-react";
import { api } from "@/lib/api";
import type { Alerta as AlertaData } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export function Alertas() {
  const [alertas, setAlertas] = useState<AlertaData[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.get<AlertaData[]>("/alertas/").then((respuesta) => setAlertas(respuesta.data)).catch(() => setError("No se pudieron cargar las alertas activas.")).finally(() => setCargando(false)); }, []);

  async function resolver(id: number) {
    try {
      await api.post(`/alertas/${id}/resolver/`);
      setAlertas((actuales) => actuales.filter((alerta) => alerta.id !== id));
    } catch {
      setError("No se pudo resolver la alerta.");
    }
  }

  return (
    <div>
      <PageHeader titulo="Alertas" descripcion="Pendientes operativos que requieren atención." />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <div className="space-y-3">
        {cargando ? <Card><CardBody className="py-10 text-center text-slate-500">Cargando alertas...</CardBody></Card> : alertas.length === 0 ? <Card><CardBody className="py-10 text-center text-slate-500">No hay alertas activas.</CardBody></Card> : alertas.map((alerta) => (
          <Card key={alerta.id}><CardBody className="flex flex-col gap-4 sm:flex-row sm:items-center"><div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-700"><Bell className="h-5 w-5" /></div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><p className="font-semibold text-slate-900">Faltante de material</p><Badge tono="ambar">{alerta.nivel}</Badge><Badge tono="gris">{alerta.origen}</Badge></div><p className="mt-1 text-sm text-slate-600">{alerta.mensaje}</p><p className="mt-1 text-xs text-slate-400">Pila: {alerta.pila_codigo ?? "Sin pila"} · Generada: {new Date(alerta.fecha_generada).toLocaleString("es-CL")}</p></div><Button variante="secundario" tamano="sm" onClick={() => void resolver(alerta.id)}><Check className="h-4 w-4" /> Resolver</Button></CardBody></Card>
        ))}
      </div>
    </div>
  );
}
