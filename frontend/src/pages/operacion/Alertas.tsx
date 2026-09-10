import { useEffect, useState } from "react";
import { Bell, Check } from "lucide-react";
import { api } from "@/lib/api";
import type { Alerta } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export function Alertas() {
  const [alertas, setAlertas] = useState<Alerta[]>([]);
  const [error, setError] = useState<string | null>(null);
  function cargar() { api.get<Alerta[]>("/alertas/", { params: { estado: "activa" } }).then((r) => setAlertas(r.data)).catch(() => setError("No se pudieron cargar las alertas.")); }
  useEffect(cargar, []);
  async function resolver(id: number) { try { await api.post(`/alertas/${id}/resolver/`); cargar(); } catch { setError("No se pudo resolver la alerta."); } }
  return <div><PageHeader titulo="Alertas" descripcion="Avisos activos de operación y mantenimiento." />{error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}{alertas.length === 0 ? <Card><CardBody><p className="text-center text-sm text-slate-500">No hay alertas activas.</p></CardBody></Card> : <div className="space-y-3">{alertas.map((alerta) => <Card key={alerta.id}><CardBody className="flex items-start justify-between gap-4"><div className="flex gap-3"><Bell className={`mt-0.5 h-5 w-5 ${alerta.nivel === "critica" ? "text-red-600" : "text-amber-600"}`} /><div><div className="flex items-center gap-2"><strong className="text-sm text-slate-900">{alerta.activo_nombre ?? "Alerta del sistema"}</strong><Badge tono={alerta.nivel === "critica" ? "rojo" : "ambar"}>{alerta.nivel}</Badge></div><p className="mt-1 text-sm text-slate-600">{alerta.mensaje}</p><p className="mt-1 text-xs text-slate-400">{new Date(alerta.fecha_generada).toLocaleString("es-CL")}</p></div></div><Button tamano="sm" variante="secundario" onClick={() => resolver(alerta.id)}><Check className="h-4 w-4" /> Resolver</Button></CardBody></Card>)}</div>}</div>;
}
