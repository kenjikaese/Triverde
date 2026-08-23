import { useCallback, useEffect, useState } from "react";
import { RefreshCw, CloudOff, CheckCircle2 } from "lucide-react";
import { listarOperaciones, type OperacionCola } from "@/lib/db";
import { sincronizar, type ResumenSync } from "@/lib/sync";
import { useOnline } from "@/lib/useOnline";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

function cantidadDetalles(op: OperacionCola): number {
  const d = op.datos["detalles"];
  return Array.isArray(d) ? d.length : 0;
}

export function ColaSincronizacion() {
  const online = useOnline();
  const [cola, setCola] = useState<OperacionCola[]>([]);
  const [cargando, setCargando] = useState(true);
  const [sincronizando, setSincronizando] = useState(false);
  const [resumen, setResumen] = useState<ResumenSync | null>(null);

  const cargar = useCallback(() => {
    setCargando(true);
    listarOperaciones()
      .then(setCola)
      .finally(() => setCargando(false));
  }, []);

  useEffect(cargar, [cargar]);

  async function sincronizarAhora() {
    setSincronizando(true);
    setResumen(null);
    try {
      const r = await sincronizar();
      setResumen(r);
      cargar();
    } finally {
      setSincronizando(false);
    }
  }

  return (
    <div>
      <PageHeader
        titulo="Cola de sincronizacion"
        descripcion="Recepciones capturadas sin senal, pendientes de enviar al servidor."
        accion={
          <Button
            onClick={sincronizarAhora}
            disabled={sincronizando || cola.length === 0 || !online}
          >
            <RefreshCw className="h-4 w-4" />
            {sincronizando ? "Sincronizando..." : "Sincronizar ahora"}
          </Button>
        }
      />

      {!online && (
        <div className="mb-4 flex items-center gap-2 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <CloudOff className="h-4 w-4" />
          Sin conexion. La cola se enviara automaticamente al reconectar.
        </div>
      )}

      {resumen && (
        <div className="mb-4 flex items-center gap-2 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800">
          <CheckCircle2 className="h-4 w-4 text-brand-600" />
          {resumen.sinConexion
            ? "No se pudo conectar; se reintentara luego."
            : `Sincronizadas: ${resumen.sincronizadas} · En conflicto: ${resumen.enConflicto} · Rechazadas: ${resumen.rechazadas}.`}
        </div>
      )}

      <Card>
        <Table>
          <thead>
            <tr>
              <Th>ID local</Th>
              <Th>Capturada</Th>
              <Th>Cliente</Th>
              <Th>Lineas</Th>
              <Th>Estado</Th>
              <Th>Motivo</Th>
            </tr>
          </thead>
          <TBody>
            {cargando ? (
              <EmptyRow colSpan={6} texto="Cargando..." />
            ) : cola.length === 0 ? (
              <EmptyRow colSpan={6} texto="No hay operaciones en la cola local." />
            ) : (
              cola.map((op) => (
                <tr key={op.id_local}>
                  <Td className="font-mono text-xs text-slate-500">
                    {op.id_local.slice(0, 8)}…
                  </Td>
                  <Td>{new Date(op.capturado_en).toLocaleString("es-CL")}</Td>
                  <Td>#{String(op.datos["cliente"] ?? "—")}</Td>
                  <Td>{cantidadDetalles(op)}</Td>
                  <Td>
                    <Badge tono={tonoEstado(op.estado_local)}>
                      {op.estado_local}
                    </Badge>
                  </Td>
                  <Td className="text-xs text-slate-500">{op.motivo ?? "—"}</Td>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      </Card>
    </div>
  );
}
