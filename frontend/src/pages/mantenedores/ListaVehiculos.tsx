import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Car, Pencil, Plus, Power, Search } from "lucide-react";
import { isAxiosError } from "axios";
import { api } from "@/lib/api";
import { mensajeDeError } from "@/lib/errores";
import type { Cliente, Vehiculo } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";

const VACIO = { patente: "", cliente: "", capacidad_m3: "", tramo: "", descripcion: "", estado_operativo: "operativa" };

export function ListaVehiculos() {
  const [vehiculos, setVehiculos] = useState<Vehiculo[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [busqueda, setBusqueda] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState(false);
  const [editando, setEditando] = useState<Vehiculo | null>(null);
  const [form, setForm] = useState(VACIO);
  const [errorModal, setErrorModal] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  function cargar() {
    setCargando(true);
    setError(null);
    Promise.all([api.get<Vehiculo[]>("/vehiculos/"), api.get<Cliente[]>("/clientes/")])
      .then(([v, c]) => { setVehiculos(v.data); setClientes(c.data); })
      .catch(() => setError("No se pudo cargar la lista de vehículos."))
      .finally(() => setCargando(false));
  }
  useEffect(cargar, []);

  const nombresClientes = useMemo(() => new Map(clientes.map((cliente) => [cliente.id, cliente.razon_social])), [clientes]);
  const filtrados = useMemo(() => {
    const termino = busqueda.toLowerCase();
    return vehiculos.filter((vehiculo) => vehiculo.patente.toLowerCase().includes(termino) || (vehiculo.descripcion ?? "").toLowerCase().includes(termino));
  }, [vehiculos, busqueda]);

  function abrir(vehiculo: Vehiculo | null) {
    setEditando(vehiculo);
    setForm(vehiculo ? {
      patente: vehiculo.patente,
      cliente: vehiculo.cliente === null ? "" : String(vehiculo.cliente),
      capacidad_m3: vehiculo.capacidad_m3 ?? "",
      tramo: vehiculo.tramo ?? "",
      descripcion: vehiculo.descripcion ?? "",
      estado_operativo: vehiculo.estado_operativo,
    } : VACIO);
    setErrorModal(null);
    setModal(true);
  }

  function cerrar() {
    setModal(false);
    setEditando(null);
    setForm(VACIO);
    setErrorModal(null);
  }

  async function guardar(e: FormEvent) {
    e.preventDefault();
    setGuardando(true);
    setErrorModal(null);
    const datos = {
      patente: form.patente.toUpperCase(), cliente: form.cliente ? Number(form.cliente) : null,
      capacidad_m3: form.capacidad_m3 || null, tramo: form.tramo || null,
      descripcion: form.descripcion || null, estado_operativo: form.estado_operativo,
    };
    try {
      if (editando) await api.patch(`/vehiculos/${editando.id}/`, datos);
      else await api.post("/vehiculos/", datos);
      cerrar();
      cargar();
    } catch (err) {
      setErrorModal(mensajeDeError(err, "No se pudo guardar el vehículo. Revisa los datos ingresados."));
    } finally { setGuardando(false); }
  }

  async function desactivar(vehiculo: Vehiculo) {
    if (!window.confirm(`¿Desactivar el vehículo ${vehiculo.patente}?`)) return;
    try {
      await api.delete(`/vehiculos/${vehiculo.id}/`);
      cargar();
    } catch (err) {
      // Si está en mantención o tiene una mantención pendiente, el servidor pide una segunda confirmación.
      if (isAxiosError(err) && err.response?.status === 409) {
        if (!window.confirm(`El vehículo ${vehiculo.patente} está en mantención o tiene una mantención pendiente. ¿Desactivarlo de todas formas?`)) return;
        try {
          await api.delete(`/vehiculos/${vehiculo.id}/`, { data: { confirmar_baja: true } });
          cargar();
          return;
        } catch { /* cae al mensaje general */ }
      }
      setError("No se pudo desactivar el vehículo.");
    }
  }

  // Reactiva un vehículo dado de baja: vuelve a estar disponible para las recepciones.
  async function activar(vehiculo: Vehiculo) {
    setError(null);
    try {
      await api.patch(`/vehiculos/${vehiculo.id}/`, { estado: "activo" });
      cargar();
    } catch (err) {
      setError(mensajeDeError(err, "No se pudo activar el vehículo."));
    }
  }

  // Al editar se muestra también el cliente actual aunque esté inactivo, para no perder la asociación.
  const clientesSeleccionables = clientes.filter(
    (cliente) => cliente.estado === "activo" || (editando !== null && cliente.id === editando.cliente),
  );

  return (
    <div>
      <PageHeader titulo="Vehículos" descripcion="Camiones asociados a clientes y su condición operativa." accion={<Button onClick={() => abrir(null)}><Plus className="h-4 w-4" /> Nuevo vehículo</Button>} />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <div className="relative mb-4 max-w-xs"><Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><Input placeholder="Buscar por patente" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} className="pl-9" /></div>
      <Card>
        <Table>
          <thead><tr><Th>Patente</Th><Th>Cliente</Th><Th>Capacidad</Th><Th>Tramo</Th><Th>Estado operativo</Th><Th>Estado</Th><Th>Acciones</Th></tr></thead>
          <TBody>
            {cargando ? <EmptyRow colSpan={7} texto="Cargando..." /> : error && vehiculos.length === 0 ? <EmptyRow colSpan={7} texto={error} /> : filtrados.length === 0 ? <EmptyRow colSpan={7} texto="Sin vehículos que coincidan." /> : filtrados.map((vehiculo) => (
              <tr key={vehiculo.id} className="hover:bg-slate-50">
                <Td className="font-medium text-slate-800">{vehiculo.patente}</Td><Td>{vehiculo.cliente ? nombresClientes.get(vehiculo.cliente) ?? `#${vehiculo.cliente}` : "Sin cliente"}</Td><Td>{vehiculo.capacidad_m3 ? `${vehiculo.capacidad_m3} m³` : "—"}</Td><Td>{vehiculo.tramo ?? "—"}</Td><Td><Badge tono={tonoEstado(vehiculo.estado_operativo)}>{vehiculo.estado_operativo}</Badge></Td><Td><Badge tono={tonoEstado(vehiculo.estado)}>{vehiculo.estado}</Badge></Td>
                <Td>
                  <div className="flex gap-2">
                    <Button variante="secundario" tamano="sm" onClick={() => abrir(vehiculo)}><Pencil className="h-4 w-4" /> Editar</Button>
                    {vehiculo.estado === "activo"
                      ? <Button variante="peligro" tamano="sm" onClick={() => desactivar(vehiculo)}><Car className="h-4 w-4" /> Desactivar</Button>
                      : <Button variante="secundario" tamano="sm" onClick={() => activar(vehiculo)}><Power className="h-4 w-4" /> Activar</Button>}
                  </div>
                </Td>
              </tr>
            ))}
          </TBody>
        </Table>
      </Card>
      <Modal abierto={modal} titulo={editando ? "Editar vehículo" : "Nuevo vehículo"} onCerrar={cerrar}>
        <form onSubmit={guardar} className="space-y-4">
          {errorModal && <div role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{errorModal}</div>}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2"><Campo label="Patente" htmlFor="vehiculo_patente" requerido><Input id="vehiculo_patente" value={form.patente} onChange={(e) => setForm({ ...form, patente: e.target.value })} required /></Campo><Campo label="Capacidad (m³)" htmlFor="vehiculo_capacidad"><Input id="vehiculo_capacidad" type="number" min="0" step="0.01" value={form.capacidad_m3} onChange={(e) => setForm({ ...form, capacidad_m3: e.target.value })} /></Campo></div>
          <Campo label="Cliente" htmlFor="vehiculo_cliente"><Select id="vehiculo_cliente" value={form.cliente} onChange={(e) => setForm({ ...form, cliente: e.target.value })}><option value="">Sin cliente</option>{clientesSeleccionables.map((cliente) => <option key={cliente.id} value={cliente.id}>{cliente.razon_social}{cliente.estado === "inactivo" ? " (inactivo)" : ""}</option>)}</Select></Campo>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2"><Campo label="Tramo" htmlFor="vehiculo_tramo"><Input id="vehiculo_tramo" value={form.tramo} onChange={(e) => setForm({ ...form, tramo: e.target.value })} placeholder="Ej. 20–40 m³" /></Campo><Campo label="Estado operativo" htmlFor="vehiculo_estado" requerido><Select id="vehiculo_estado" value={form.estado_operativo} onChange={(e) => setForm({ ...form, estado_operativo: e.target.value })}><option value="operativa">Operativa</option><option value="en mantencion">En mantención</option><option value="fuera de servicio">Fuera de servicio</option></Select></Campo></div>
          <Campo label="Descripción" htmlFor="vehiculo_descripcion"><Input id="vehiculo_descripcion" value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} /></Campo>
          <div className="flex justify-end gap-2 pt-2"><Button type="button" variante="secundario" onClick={cerrar}>Cancelar</Button><Button type="submit" disabled={guardando}>{guardando ? "Guardando..." : editando ? "Guardar cambios" : "Guardar vehículo"}</Button></div>
        </form>
      </Modal>
    </div>
  );
}
