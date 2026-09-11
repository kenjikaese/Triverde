import { useEffect, useState } from "react";
import { Bell, Check } from "lucide-react";
import { api } from "@/lib/api";
import type { Alerta } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

function tituloAlerta(alerta: Alerta): string {
  if (alerta.origen === "mantencion") return alerta.activo_nombre ?? "Mantención pendiente";
  if (alerta.origen === "mezcla") return "Faltante de material";
  return "Alerta del sistema";
}

function detalleAlerta(alerta: Alerta): string | null {
  if (alerta.origen === "mezcla") return `Pila: ${alerta.pila_codigo ?? "Sin pila"}`;
  return null;
}

export function Alertas() {
  const [alertas, setAlertas] = useState<Alerta[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function cargar() {
    setCargando(true);
    api
      .get<Alerta[]>("/alertas/", { params: { estado: "activa" } })
      .then((respuesta) => setAlertas(respuesta.data))
      .catch(() => setError("No se pudieron cargar las alertas activas."))
      .finally(() => setCargando(false));
  }

  useEffect(cargar, []);

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
      <PageHeader titulo="Alertas" descripcion="Avisos activos de operación y mantenimiento." />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <div className="space-y-3">
        {cargando ? (
          <Card><CardBody className="py-10 text-center text-slate-500">Cargando alertas...</CardBody></Card>
        ) : alertas.length === 0 ? (
          <Card><CardBody className="py-10 text-center text-slate-500">No hay alertas activas.</CardBody></Card>
        ) : (
          alertas.map((alerta) => {
            const critica = alerta.nivel === "critica";
            const detalle = detalleAlerta(alerta);
            return (
              <Card key={alerta.id}>
                <CardBody className="flex flex-col gap-4 sm:flex-row sm:items-center">
                  <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${critica ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>
                    <Bell className="h-5 w-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-slate-900">{tituloAlerta(alerta)}</p>
                      <Badge tono={critica ? "rojo" : "ambar"}>{alerta.nivel}</Badge>
                      <Badge tono="gris">{alerta.origen}</Badge>
                    </div>
                    <p className="mt-1 text-sm text-slate-600">{alerta.mensaje}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {detalle ? `${detalle} · ` : ""}Generada: {new Date(alerta.fecha_generada).toLocaleString("es-CL")}
                    </p>
                  </div>
                  <Button variante="secundario" tamano="sm" onClick={() => void resolver(alerta.id)}>
                    <Check className="h-4 w-4" /> Resolver
                  </Button>
                </CardBody>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
