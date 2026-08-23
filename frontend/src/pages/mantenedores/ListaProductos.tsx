import { useEffect, useMemo, useState, type FormEvent } from "react";
import { PackageMinus, Plus, Search } from "lucide-react";
import { api } from "@/lib/api";
import type { Producto } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";

const VACIO = { nombre: "", tipo: "chip", precio: "", unidad_de_venta: "saco" };
const clp = (valor: string | number) => `$${Math.round(Number(valor)).toLocaleString("es-CL")}`;

export function ListaProductos() {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [busqueda, setBusqueda] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState(VACIO);
  const [guardando, setGuardando] = useState(false);

  function cargar() {
    setCargando(true);
    setError(null);
    api.get<Producto[]>("/productos/")
      .then((res) => setProductos(res.data))
      .catch(() => setError("No se pudo cargar la lista de productos."))
      .finally(() => setCargando(false));
  }
  useEffect(cargar, []);

  const filtrados = useMemo(() => productos.filter((producto) =>
    producto.nombre.toLowerCase().includes(busqueda.toLowerCase()),
  ), [productos, busqueda]);

  async function crear(e: FormEvent) {
    e.preventDefault();
    setGuardando(true);
    setError(null);
    try {
      await api.post("/productos/", { ...form, precio: form.precio || null });
      setModal(false);
      setForm(VACIO);
      cargar();
    } catch {
      setError("No se pudo guardar el producto. Revisa los datos ingresados.");
    } finally {
      setGuardando(false);
    }
  }

  async function desactivar(producto: Producto) {
    if (!window.confirm(`¿Desactivar ${producto.nombre}?`)) return;
    try {
      await api.delete(`/productos/${producto.id}/`);
      cargar();
    } catch {
      setError("No se pudo desactivar el producto.");
    }
  }

  return (
    <div>
      <PageHeader titulo="Productos" descripcion="Productos terminados disponibles para venta." accion={<Button onClick={() => setModal(true)}><Plus className="h-4 w-4" /> Nuevo producto</Button>} />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <div className="relative mb-4 max-w-xs"><Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><Input placeholder="Buscar producto" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} className="pl-9" /></div>
      <Card>
        <Table>
          <thead><tr><Th>Producto</Th><Th>Tipo</Th><Th>Precio</Th><Th>Unidad de venta</Th><Th>Estado</Th><Th>Acciones</Th></tr></thead>
          <TBody>
            {cargando ? <EmptyRow colSpan={6} texto="Cargando..." /> : error && productos.length === 0 ? <EmptyRow colSpan={6} texto={error} /> : filtrados.length === 0 ? <EmptyRow colSpan={6} texto="Sin productos que coincidan." /> : filtrados.map((producto) => (
              <tr key={producto.id} className="hover:bg-slate-50">
                <Td className="font-medium text-slate-800">{producto.nombre}</Td><Td className="capitalize">{producto.tipo}</Td><Td>{producto.precio ? clp(producto.precio) : "—"}</Td><Td>{producto.unidad_de_venta === "m3" ? "m³" : "saco"}</Td><Td><Badge tono={tonoEstado(producto.estado)}>{producto.estado}</Badge></Td>
                <Td>{producto.estado === "activo" ? <Button variante="peligro" tamano="sm" onClick={() => desactivar(producto)}><PackageMinus className="h-4 w-4" /> Desactivar</Button> : "—"}</Td>
              </tr>
            ))}
          </TBody>
        </Table>
      </Card>
      <Modal abierto={modal} titulo="Nuevo producto" onCerrar={() => setModal(false)}>
        <form onSubmit={crear} className="space-y-4">
          <Campo label="Nombre" htmlFor="producto_nombre" requerido><Input id="producto_nombre" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} required /></Campo>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Campo label="Tipo" htmlFor="producto_tipo" requerido><Select id="producto_tipo" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })} required><option value="chip">Chip</option><option value="mulch">Mulch</option><option value="compost">Compost</option><option value="lena">Leña</option></Select></Campo>
            <Campo label="Unidad de venta" htmlFor="producto_unidad" requerido><Select id="producto_unidad" value={form.unidad_de_venta} onChange={(e) => setForm({ ...form, unidad_de_venta: e.target.value })} required><option value="saco">Saco</option><option value="m3">Metro cúbico</option></Select></Campo>
          </div>
          <Campo label="Precio (CLP)" htmlFor="producto_precio"><Input id="producto_precio" type="number" min="0" step="1" value={form.precio} onChange={(e) => setForm({ ...form, precio: e.target.value })} /></Campo>
          <div className="flex justify-end gap-2 pt-2"><Button type="button" variante="secundario" onClick={() => setModal(false)}>Cancelar</Button><Button type="submit" disabled={guardando}>{guardando ? "Guardando..." : "Guardar producto"}</Button></div>
        </form>
      </Modal>
    </div>
  );
}
