import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError } from "@/lib/errores";
import type { CambioParametro, ParametroConversion } from "@/lib/types";
import { Card } from "@/components/ui/Card";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyRow, Table, TBody, Td, Th } from "@/components/ui/Table";

const fechaHora = (valor: string) => new Date(valor).toLocaleString("es-CL");

// V_HistorialParametros (CU-14): consulta de solo lectura, del cambio mas reciente
// al mas antiguo. El orden y los filtros los aplica el servidor.
export function HistorialParametros() {
  const [parametros, setParametros] = useState<ParametroConversion[]>([]);
  const [cambios, setCambios] = useState<CambioParametro[]>([]);
  const [filtros, setFiltros] = useState({ parametro: "", desde: "", hasta: "" });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detalle, setDetalle] = useState<CambioParametro | null>(null);

  useEffect(() => {
    api
      .get<ParametroConversion[]>("/parametros/")
      .then((r) => setParametros(r.data))
      .catch((err) => setError(mensajeDeError(err, "No se pudieron cargar los parámetros.")));
  }, []);

  useEffect(() => {
    setCargando(true);
    setError(null);
    const params = Object.fromEntries(Object.entries(filtros).filter(([, valor]) => valor));
    api
      .get<CambioParametro[]>("/historial-parametros/", { params })
      .then((r) => setCambios(r.data))
      .catch((err) => setError(mensajeDeError(err, "No se pudo cargar el historial.")))
      .finally(() => setCargando(false));
  }, [filtros]);

  const hayFiltros = Boolean(filtros.parametro || filtros.desde || filtros.hasta);

  return (
    <div>
      <PageHeader titulo="Historial de parámetros" descripcion="Quién cambió cada valor, cuándo y desde qué valor anterior. Selecciona un registro para ver su detalle." />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <div className="mb-4 grid max-w-3xl grid-cols-1 gap-4 sm:grid-cols-3">
        <Campo label="Parámetro" htmlFor="historial_parametro">
          <Select id="historial_parametro" value={filtros.parametro} onChange={(e) => setFiltros({ ...filtros, parametro: e.target.value })}>
            <option value="">Todos</option>
            {parametros.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
          </Select>
        </Campo>
        <Campo label="Desde" htmlFor="historial_desde">
          <Input id="historial_desde" type="date" value={filtros.desde} onChange={(e) => setFiltros({ ...filtros, desde: e.target.value })} />
        </Campo>
        <Campo label="Hasta" htmlFor="historial_hasta">
          <Input id="historial_hasta" type="date" value={filtros.hasta} onChange={(e) => setFiltros({ ...filtros, hasta: e.target.value })} />
        </Campo>
      </div>

      <Card>
        <Table>
          <thead><tr><Th>Fecha</Th><Th>Parámetro</Th><Th>Valor anterior</Th><Th>Valor nuevo</Th><Th>Usuario</Th></tr></thead>
          <TBody>
            {cargando ? <EmptyRow colSpan={5} texto="Cargando..." /> : cambios.length === 0 ? (
              <EmptyRow colSpan={5} texto={hayFiltros ? "No hay cambios registrados para el parámetro o el rango de fechas elegido." : "Todavía no hay cambios registrados."} />
            ) : cambios.map((cambio) => (
              <tr key={cambio.id} className="cursor-pointer hover:bg-slate-50" data-testid="fila-cambio" onClick={() => setDetalle(cambio)}>
                <Td>{fechaHora(cambio.fecha_hora)}</Td>
                <Td className="font-medium text-slate-800">{cambio.parametro_nombre}</Td>
                <Td>{cambio.valor_anterior ?? "—"}</Td>
                <Td>{cambio.valor_nuevo}</Td>
                <Td>{cambio.usuario_username ?? "—"}</Td>
              </tr>
            ))}
          </TBody>
        </Table>
      </Card>

      <Modal abierto={detalle !== null} titulo="Detalle del cambio" onCerrar={() => setDetalle(null)}>
        {detalle && (
          <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
            <div><dt className="text-slate-500">Parámetro</dt><dd className="font-medium text-slate-800">{detalle.parametro_nombre}</dd></div>
            <div><dt className="text-slate-500">Clave</dt><dd><code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{detalle.parametro_clave}</code></dd></div>
            <div><dt className="text-slate-500">Valor anterior</dt><dd className="font-medium text-slate-800">{detalle.valor_anterior ?? "—"}</dd></div>
            <div><dt className="text-slate-500">Valor nuevo</dt><dd className="font-medium text-slate-800">{detalle.valor_nuevo}</dd></div>
            <div><dt className="text-slate-500">Fecha</dt><dd className="font-medium text-slate-800">{fechaHora(detalle.fecha_hora)}</dd></div>
            <div><dt className="text-slate-500">Usuario</dt><dd className="font-medium text-slate-800">{detalle.usuario_username ?? "—"}</dd></div>
          </dl>
        )}
      </Modal>
    </div>
  );
}
