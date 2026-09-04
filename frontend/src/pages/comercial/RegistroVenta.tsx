import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Plus, ShoppingCart, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import type { Cliente, Producto, Venta } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Button } from "@/components/ui/Button";
import { cantidad as formatoCantidad, clp } from "@/lib/formato";

interface Linea {
  producto: Producto;
  cantidad: string;
}

// CU-58: registra una venta con una o mas lineas producto+cantidad. El monto
// definitivo lo calcula el servidor; el total que se muestra antes de guardar
// es solo una previsualizacion para que el usuario confirme.
export function RegistroVenta() {
  const navegar = useNavigate();
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [cliente, setCliente] = useState("");
  const [lineas, setLineas] = useState<Linea[]>([]);
  const [productoSel, setProductoSel] = useState("");
  const [cantidadSel, setCantidadSel] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Cliente[]>("/clientes/", { params: { estado: "activo" } })
      .then((res) => setClientes(res.data))
      .catch(() => setError("No se pudo cargar la lista de clientes."));
    api
      .get<Producto[]>("/productos/", { params: { estado: "activo" } })
      .then((res) => setProductos(res.data))
      .catch(() => setError("No se pudo cargar el catálogo de productos."));
  }, []);

  const total = useMemo(
    () =>
      lineas.reduce(
        (suma, linea) =>
          suma + Number(linea.producto.precio ?? 0) * Number(linea.cantidad),
        0,
      ),
    [lineas],
  );

  function agregarLinea() {
    setError(null);
    const producto = productos.find((p) => p.id === Number(productoSel));
    if (!producto) {
      setError("Selecciona un producto del catálogo.");
      return;
    }
    if (!cantidadSel || Number(cantidadSel) <= 0) {
      setError("La cantidad debe ser mayor a cero.");
      return;
    }
    if (producto.precio === null) {
      setError(
        `El producto ${producto.nombre} no tiene precio configurado; no se puede vender.`,
      );
      return;
    }
    setLineas([...lineas, { producto, cantidad: cantidadSel }]);
    setProductoSel("");
    setCantidadSel("");
  }

  async function registrar(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!cliente) {
      setError("Selecciona el cliente comprador.");
      return;
    }
    if (lineas.length === 0) {
      setError("Agrega al menos un producto a la venta.");
      return;
    }
    setGuardando(true);
    try {
      const res = await api.post<Venta>("/ventas/", {
        cliente: Number(cliente),
        detalles: lineas.map((linea) => ({
          producto: linea.producto.id,
          cantidad: linea.cantidad,
        })),
      });
      navegar(`/ventas?registrada=${res.data.id}`);
    } catch (err: unknown) {
      const datos = (err as { response?: { data?: unknown } }).response?.data;
      setError(
        typeof datos === "object" && datos !== null
          ? JSON.stringify(datos)
          : "No se pudo registrar la venta.",
      );
    } finally {
      setGuardando(false);
    }
  }

  const sinProductos = productos.length === 0;

  return (
    <div>
      <PageHeader
        titulo="Nueva venta"
        descripcion="Registra la venta de productos del catálogo a un cliente."
      />

      {sinProductos && (
        <div
          className="mb-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800"
          data-testid="aviso-sin-productos"
        >
          No hay productos activos disponibles para vender.
        </div>
      )}

      {error && (
        <div
          className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
          data-testid="error-venta"
        >
          {error}
        </div>
      )}

      <form onSubmit={registrar} className="space-y-5">
        <Card>
          <CardHeader titulo="Cliente comprador" />
          <CardBody>
            <div className="max-w-md">
              <Campo label="Cliente" htmlFor="venta_cliente" requerido>
                <Select
                  id="venta_cliente"
                  value={cliente}
                  onChange={(e) => setCliente(e.target.value)}
                  required
                >
                  <option value="">Selecciona un cliente</option>
                  {clientes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.razon_social}
                    </option>
                  ))}
                </Select>
              </Campo>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            titulo="Productos vendidos"
            descripcion="La cantidad va en sacos o metros cúbicos según la unidad configurada del producto."
          />
          <CardBody>
            <div className="mb-4 grid gap-3 md:grid-cols-[2fr_1fr_auto] md:items-end">
              <Campo label="Producto" htmlFor="venta_producto">
                <Select
                  id="venta_producto"
                  value={productoSel}
                  onChange={(e) => setProductoSel(e.target.value)}
                  disabled={sinProductos}
                >
                  <option value="">Selecciona un producto</option>
                  {productos.map((producto) => (
                    <option key={producto.id} value={producto.id}>
                      {producto.nombre} · {clp(producto.precio)} /{" "}
                      {producto.unidad_de_venta}
                    </option>
                  ))}
                </Select>
              </Campo>
              <Campo label="Cantidad" htmlFor="venta_cantidad">
                <Input
                  id="venta_cantidad"
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={cantidadSel}
                  onChange={(e) => setCantidadSel(e.target.value)}
                  disabled={sinProductos}
                />
              </Campo>
              <Button
                type="button"
                variante="secundario"
                onClick={agregarLinea}
                disabled={sinProductos}
              >
                <Plus className="h-4 w-4" />
                Agregar
              </Button>
            </div>

            <Table>
              <thead>
                <tr>
                  <Th>Producto</Th>
                  <Th>Cantidad</Th>
                  <Th>Precio unitario</Th>
                  <Th>Subtotal</Th>
                  <Th>Quitar</Th>
                </tr>
              </thead>
              <TBody>
                {lineas.length === 0 ? (
                  <EmptyRow colSpan={5} texto="Aún no agregas productos." />
                ) : (
                  lineas.map((linea, indice) => (
                    <tr key={indice} data-testid="linea-venta">
                      <Td className="font-medium text-slate-800">
                        {linea.producto.nombre}
                      </Td>
                      <Td>
                        {formatoCantidad(linea.cantidad)}{" "}
                        {linea.producto.unidad_de_venta}
                      </Td>
                      <Td>{clp(linea.producto.precio)}</Td>
                      <Td className="font-medium">
                        {clp(
                          Number(linea.producto.precio ?? 0) *
                            Number(linea.cantidad),
                        )}
                      </Td>
                      <Td>
                        <Button
                          type="button"
                          variante="fantasma"
                          tamano="sm"
                          onClick={() =>
                            setLineas(lineas.filter((_, i) => i !== indice))
                          }
                          aria-label="Quitar producto"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </Td>
                    </tr>
                  ))
                )}
              </TBody>
            </Table>
          </CardBody>
        </Card>

        <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">
              Total de la venta
            </p>
            <p
              className="text-2xl font-semibold text-slate-800"
              data-testid="total-previsualizado"
            >
              {clp(total)}
            </p>
          </div>
          <Button type="submit" disabled={guardando || lineas.length === 0}>
            <ShoppingCart className="h-4 w-4" />
            {guardando ? "Registrando..." : "Registrar venta"}
          </Button>
        </div>
      </form>
    </div>
  );
}
