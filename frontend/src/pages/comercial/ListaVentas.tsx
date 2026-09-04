import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Plus, Truck } from "lucide-react";
import { api } from "@/lib/api";
import type { Cliente, Producto, TotalesVentas, Venta } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import {
  cantidad as formatoCantidad,
  clp,
  fecha as formatoFecha,
  periodoVigente,
} from "@/lib/formato";

// CU-59: listado y total de las ventas del periodo (por defecto, el mes en
// curso). CU-60: el despacho se registra desde la fila de una venta pendiente.
export function ListaVentas() {
  const [params] = useSearchParams();
  const [ventas, setVentas] = useState<Venta[]>([]);
  const [totales, setTotales] = useState<TotalesVentas | null>(null);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [filtros, setFiltros] = useState({
    ...periodoVigente(),
    cliente: "",
    producto: "",
  });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [despachando, setDespachando] = useState<Venta | null>(null);
  const [formDespacho, setFormDespacho] = useState({
    fecha: new Date().toISOString().slice(0, 10),
    receptor: "",
    direccion: "",
  });
  const [guardando, setGuardando] = useState(false);
  const [errorDespacho, setErrorDespacho] = useState<string | null>(null);

  const cargar = useCallback(() => {
    setCargando(true);
    setError(null);
    const consulta: Record<string, string> = {};
    if (filtros.desde) consulta.desde = filtros.desde;
    if (filtros.hasta) consulta.hasta = filtros.hasta;
    if (filtros.cliente) consulta.cliente = filtros.cliente;
    if (filtros.producto) consulta.producto = filtros.producto;
    Promise.all([
      api.get<Venta[]>("/ventas/", { params: consulta }),
      api.get<TotalesVentas>("/ventas/totales/", { params: consulta }),
    ])
      .then(([listado, total]) => {
        setVentas(listado.data);
        setTotales(total.data);
      })
      .catch(() => setError("No se pudieron cargar las ventas del período."))
      .finally(() => setCargando(false));
  }, [filtros]);

  useEffect(() => {
    api
      .get<Cliente[]>("/clientes/")
      .then((res) => setClientes(res.data))
      .catch(() => undefined);
    api
      .get<Producto[]>("/productos/")
      .then((res) => setProductos(res.data))
      .catch(() => undefined);
  }, []);

  useEffect(cargar, [cargar]);

  function abrirDespacho(venta: Venta) {
    setDespachando(venta);
    setErrorDespacho(null);
    setFormDespacho({
      fecha: new Date().toISOString().slice(0, 10),
      receptor: "",
      direccion: "",
    });
  }

  async function confirmarDespacho(e: FormEvent) {
    e.preventDefault();
    if (!despachando) return;
    setGuardando(true);
    setErrorDespacho(null);
    try {
      await api.post(`/ventas/${despachando.id}/despachar/`, formDespacho);
      setDespachando(null);
      cargar();
    } catch (err: unknown) {
      const datos = (
        err as { response?: { data?: { detalle?: string; receptor?: string[] } } }
      ).response?.data;
      setErrorDespacho(
        datos?.detalle ??
          datos?.receptor?.[0] ??
          "No se pudo registrar el despacho.",
      );
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div>
      <PageHeader
        titulo="Ventas del período"
        descripcion="Ventas registradas, su total y el estado de despacho de cada una."
        accion={
          <Link to="/ventas/nueva">
            <Button>
              <Plus className="h-4 w-4" />
              Nueva venta
            </Button>
          </Link>
        }
      />

      {params.get("registrada") && (
        <div
          className="mb-4 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800"
          data-testid="aviso-venta-registrada"
        >
          Venta {params.get("registrada")} registrada correctamente.
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <Card className="mb-4 p-4">
        <div className="grid gap-3 md:grid-cols-4">
          <Campo label="Desde" htmlFor="venta_desde">
            <Input
              id="venta_desde"
              type="date"
              value={filtros.desde}
              onChange={(e) => setFiltros({ ...filtros, desde: e.target.value })}
            />
          </Campo>
          <Campo label="Hasta" htmlFor="venta_hasta">
            <Input
              id="venta_hasta"
              type="date"
              value={filtros.hasta}
              onChange={(e) => setFiltros({ ...filtros, hasta: e.target.value })}
            />
          </Campo>
          <Campo label="Cliente" htmlFor="venta_filtro_cliente">
            <Select
              id="venta_filtro_cliente"
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
          <Campo label="Producto" htmlFor="venta_filtro_producto">
            <Select
              id="venta_filtro_producto"
              value={filtros.producto}
              onChange={(e) =>
                setFiltros({ ...filtros, producto: e.target.value })
              }
            >
              <option value="">Todos</option>
              {productos.map((producto) => (
                <option key={producto.id} value={producto.id}>
                  {producto.nombre}
                </option>
              ))}
            </Select>
          </Campo>
        </div>
      </Card>

      <div className="mb-4 flex items-center justify-between rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Total vendido en el período
          </p>
          <p
            className="text-2xl font-semibold text-slate-800"
            data-testid="total-periodo"
          >
            {clp(totales?.total ?? 0)}
          </p>
        </div>
        <p className="text-sm text-slate-500" data-testid="cantidad-ventas">
          {totales?.cantidad ?? 0} venta(s)
        </p>
      </div>

      <Card>
        <Table>
          <thead>
            <tr>
              <Th>N.°</Th>
              <Th>Fecha</Th>
              <Th>Cliente</Th>
              <Th>Productos</Th>
              <Th>Total</Th>
              <Th>Estado</Th>
              <Th>Acciones</Th>
            </tr>
          </thead>
          <TBody>
            {cargando ? (
              <EmptyRow colSpan={7} texto="Cargando..." />
            ) : ventas.length === 0 ? (
              <EmptyRow
                colSpan={7}
                texto="No hay ventas que coincidan con el filtro aplicado."
              />
            ) : (
              ventas.map((venta) => (
                <tr
                  key={venta.id}
                  className="hover:bg-slate-50"
                  data-testid="fila-venta"
                >
                  <Td className="font-medium text-slate-800">{venta.id}</Td>
                  <Td>{formatoFecha(venta.fecha)}</Td>
                  <Td>{venta.cliente_razon_social}</Td>
                  <Td className="text-slate-600">
                    {venta.detalles
                      .map(
                        (detalle) =>
                          `${detalle.producto_nombre} (${formatoCantidad(detalle.cantidad)} ${detalle.unidad})`,
                      )
                      .join(", ")}
                  </Td>
                  <Td className="font-medium">{clp(venta.total)}</Td>
                  <Td>
                    <Badge tono={tonoEstado(venta.estado)}>{venta.estado}</Badge>
                  </Td>
                  <Td>
                    {venta.despachada ? (
                      <span className="text-xs text-slate-400">Despachada</span>
                    ) : (
                      <Button
                        variante="secundario"
                        tamano="sm"
                        onClick={() => abrirDespacho(venta)}
                      >
                        <Truck className="h-4 w-4" />
                        Registrar despacho
                      </Button>
                    )}
                  </Td>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      </Card>

      <Modal
        abierto={despachando !== null}
        titulo={`Despachar la venta ${despachando?.id ?? ""}`}
        onCerrar={() => setDespachando(null)}
      >
        <form onSubmit={confirmarDespacho} className="space-y-4">
          {errorDespacho && (
            <div
              className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
              data-testid="error-despacho"
            >
              {errorDespacho}
            </div>
          )}
          <Campo label="Fecha del despacho" htmlFor="despacho_fecha" requerido>
            <Input
              id="despacho_fecha"
              type="date"
              value={formDespacho.fecha}
              onChange={(e) =>
                setFormDespacho({ ...formDespacho, fecha: e.target.value })
              }
              required
            />
          </Campo>
          <Campo label="Quien retira" htmlFor="despacho_receptor" requerido>
            <Input
              id="despacho_receptor"
              value={formDespacho.receptor}
              onChange={(e) =>
                setFormDespacho({ ...formDespacho, receptor: e.target.value })
              }
              placeholder="Nombre de quien retira el producto"
              required
            />
          </Campo>
          <Campo label="Dirección de entrega" htmlFor="despacho_direccion">
            <Input
              id="despacho_direccion"
              value={formDespacho.direccion}
              onChange={(e) =>
                setFormDespacho({ ...formDespacho, direccion: e.target.value })
              }
            />
          </Campo>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variante="secundario"
              onClick={() => setDespachando(null)}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={guardando}>
              {guardando ? "Registrando..." : "Confirmar despacho"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
