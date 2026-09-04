import { useCallback, useEffect, useState } from "react";
import { Download, Search } from "lucide-react";
import { api } from "@/lib/api";
import type { Cliente, Cotizacion } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";
import { clp, fecha as formatoFecha } from "@/lib/formato";

// CU-57: historial de cotizaciones con busqueda y filtros por cliente y rango
// de fechas. El filtrado lo hace el servidor (query params), no el navegador.
export function ListaCotizaciones() {
  const [cotizaciones, setCotizaciones] = useState<Cotizacion[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [filtros, setFiltros] = useState({
    search: "",
    cliente: "",
    desde: "",
    hasta: "",
  });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(() => {
    setCargando(true);
    setError(null);
    const params: Record<string, string> = {};
    if (filtros.search) params.search = filtros.search;
    if (filtros.cliente) params.cliente = filtros.cliente;
    if (filtros.desde) params.desde = filtros.desde;
    if (filtros.hasta) params.hasta = filtros.hasta;
    api
      .get<Cotizacion[]>("/cotizaciones/", { params })
      .then((res) => setCotizaciones(res.data))
      .catch(() => setError("No se pudo cargar el historial de cotizaciones."))
      .finally(() => setCargando(false));
  }, [filtros]);

  useEffect(() => {
    api
      .get<Cliente[]>("/clientes/")
      .then((res) => setClientes(res.data))
      .catch(() => setError("No se pudieron cargar los filtros."));
  }, []);

  useEffect(cargar, [cargar]);

  async function exportar(cotizacion: Cotizacion) {
    setError(null);
    try {
      const res = await api.get(`/cotizaciones/${cotizacion.id}/exportar/`);
      const blob = new Blob([JSON.stringify(res.data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = `cotizacion-${cotizacion.id}.json`;
      enlace.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const datos = (
        err as { response?: { data?: { detalle?: string; faltantes?: string[] } } }
      ).response?.data;
      setError(
        datos?.faltantes?.length
          ? `${datos.detalle} Faltan: ${datos.faltantes.join(", ")}.`
          : (datos?.detalle ?? "No se pudo exportar la cotización."),
      );
    }
  }

  return (
    <div>
      <PageHeader
        titulo="Historial de cotizaciones"
        descripcion="Cotizaciones generadas, de la más reciente a la más antigua."
      />

      {error && (
        <div
          className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
          data-testid="error-cotizaciones"
        >
          {error}
        </div>
      )}

      <Card className="mb-4 p-4">
        <div className="grid gap-3 md:grid-cols-4">
          <Campo label="Buscar" htmlFor="cotizacion_busqueda">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                id="cotizacion_busqueda"
                className="pl-9"
                placeholder="Cliente o servicio"
                value={filtros.search}
                onChange={(e) =>
                  setFiltros({ ...filtros, search: e.target.value })
                }
              />
            </div>
          </Campo>
          <Campo label="Cliente" htmlFor="cotizacion_filtro_cliente">
            <Select
              id="cotizacion_filtro_cliente"
              value={filtros.cliente}
              onChange={(e) =>
                setFiltros({ ...filtros, cliente: e.target.value })
              }
            >
              <option value="">Todos</option>
              {clientes.map((cliente) => (
                <option key={cliente.id} value={cliente.id}>
                  {cliente.razon_social}
                </option>
              ))}
            </Select>
          </Campo>
          <Campo label="Desde" htmlFor="cotizacion_desde">
            <Input
              id="cotizacion_desde"
              type="date"
              value={filtros.desde}
              onChange={(e) => setFiltros({ ...filtros, desde: e.target.value })}
            />
          </Campo>
          <Campo label="Hasta" htmlFor="cotizacion_hasta">
            <Input
              id="cotizacion_hasta"
              type="date"
              value={filtros.hasta}
              onChange={(e) => setFiltros({ ...filtros, hasta: e.target.value })}
            />
          </Campo>
        </div>
      </Card>

      <Card>
        <Table>
          <thead>
            <tr>
              <Th>N.°</Th>
              <Th>Fecha</Th>
              <Th>Cliente</Th>
              <Th>Servicio</Th>
              <Th>Distancia</Th>
              <Th>Costo estimado</Th>
              <Th>Acciones</Th>
            </tr>
          </thead>
          <TBody>
            {cargando ? (
              <EmptyRow colSpan={7} texto="Cargando..." />
            ) : cotizaciones.length === 0 ? (
              <EmptyRow
                colSpan={7}
                texto="No hay cotizaciones que coincidan con el filtro aplicado."
              />
            ) : (
              cotizaciones.map((cotizacion) => (
                <tr
                  key={cotizacion.id}
                  className="hover:bg-slate-50"
                  data-testid="fila-cotizacion"
                >
                  <Td className="font-medium text-slate-800">{cotizacion.id}</Td>
                  <Td>{formatoFecha(cotizacion.fecha)}</Td>
                  <Td>{cotizacion.cliente_razon_social}</Td>
                  <Td>{cotizacion.servicio}</Td>
                  <Td>{cotizacion.distancia_km} km</Td>
                  <Td className="font-medium">{clp(cotizacion.costo_estimado)}</Td>
                  <Td>
                    <Button
                      variante="secundario"
                      tamano="sm"
                      onClick={() => exportar(cotizacion)}
                    >
                      <Download className="h-4 w-4" />
                      Exportar
                    </Button>
                  </Td>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      </Card>
    </div>
  );
}
