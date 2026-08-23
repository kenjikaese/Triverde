import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Plus, Search, UserX } from "lucide-react";
import { api } from "@/lib/api";
import type { Cliente, Transportista } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";

const VACIO = { nombre: "", rut: "", telefono: "", cliente: "" };

export function ListaTransportistas() {
  const [transportistas, setTransportistas] = useState<Transportista[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [busqueda, setBusqueda] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState(VACIO);
  const [guardando, setGuardando] = useState(false);

  function cargar() {
    setCargando(true);
    setError(null);
    Promise.all([
      api.get<Transportista[]>("/transportistas/"),
      api.get<Cliente[]>("/clientes/"),
    ])
      .then(([t, c]) => {
        setTransportistas(t.data);
        setClientes(c.data);
      })
      .catch(() => setError("No se pudo cargar la lista de transportistas."))
      .finally(() => setCargando(false));
  }

  useEffect(cargar, []);

  const nombresClientes = useMemo(
    () => new Map(clientes.map((cliente) => [cliente.id, cliente.razon_social])),
    [clientes],
  );
  const filtrados = useMemo(() => {
    const termino = busqueda.toLowerCase();
    return transportistas.filter(
      (transportista) =>
        transportista.nombre.toLowerCase().includes(termino) ||
        (transportista.rut ?? "").toLowerCase().includes(termino),
    );
  }, [transportistas, busqueda]);

  async function crear(e: FormEvent) {
    e.preventDefault();
    setGuardando(true);
    setError(null);
    try {
      await api.post("/transportistas/", {
        nombre: form.nombre,
        rut: form.rut || null,
        telefono: form.telefono || null,
        cliente: Number(form.cliente),
        usuario: null,
      });
      setModal(false);
      setForm(VACIO);
      cargar();
    } catch {
      setError("No se pudo guardar el transportista. Revisa los datos ingresados.");
    } finally {
      setGuardando(false);
    }
  }

  async function desactivar(transportista: Transportista) {
    if (!window.confirm(`¿Desactivar a ${transportista.nombre}?`)) return;
    try {
      await api.delete(`/transportistas/${transportista.id}/`);
      cargar();
    } catch {
      setError("No se pudo desactivar el transportista.");
    }
  }

  return (
    <div>
      <PageHeader
        titulo="Transportistas"
        descripcion="Conductores y empresas asociados a los clientes de la planta."
        accion={
          <Button onClick={() => setModal(true)}>
            <Plus className="h-4 w-4" />
            Nuevo transportista
          </Button>
        }
      />

      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <div className="relative mb-4 max-w-xs">
        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <Input
          placeholder="Buscar por nombre o RUT"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          className="pl-9"
        />
      </div>

      <Card>
        <Table>
          <thead><tr><Th>Nombre</Th><Th>RUT</Th><Th>Teléfono</Th><Th>Cliente</Th><Th>Estado</Th><Th>Acciones</Th></tr></thead>
          <TBody>
            {cargando ? (
              <EmptyRow colSpan={6} texto="Cargando..." />
            ) : error && transportistas.length === 0 ? (
              <EmptyRow colSpan={6} texto={error} />
            ) : filtrados.length === 0 ? (
              <EmptyRow colSpan={6} texto="Sin transportistas que coincidan." />
            ) : (
              filtrados.map((transportista) => (
                <tr key={transportista.id} className="hover:bg-slate-50">
                  <Td className="font-medium text-slate-800">{transportista.nombre}</Td>
                  <Td>{transportista.rut ?? "—"}</Td>
                  <Td>{transportista.telefono ?? "—"}</Td>
                  <Td>{nombresClientes.get(transportista.cliente) ?? `#${transportista.cliente}`}</Td>
                  <Td><Badge tono={tonoEstado(transportista.estado)}>{transportista.estado}</Badge></Td>
                  <Td>
                    {transportista.estado === "activo" ? (
                      <Button variante="peligro" tamano="sm" onClick={() => desactivar(transportista)}>
                        <UserX className="h-4 w-4" /> Desactivar
                      </Button>
                    ) : "—"}
                  </Td>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      </Card>

      <Modal abierto={modal} titulo="Nuevo transportista" onCerrar={() => setModal(false)}>
        <form onSubmit={crear} className="space-y-4">
          <Campo label="Nombre" htmlFor="transportista_nombre" requerido>
            <Input id="transportista_nombre" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} required />
          </Campo>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Campo label="RUT" htmlFor="transportista_rut">
              <Input id="transportista_rut" value={form.rut} onChange={(e) => setForm({ ...form, rut: e.target.value })} />
            </Campo>
            <Campo label="Teléfono" htmlFor="transportista_telefono">
              <Input id="transportista_telefono" value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} />
            </Campo>
          </div>
          <Campo label="Cliente" htmlFor="transportista_cliente" requerido>
            <Select id="transportista_cliente" value={form.cliente} onChange={(e) => setForm({ ...form, cliente: e.target.value })} required>
              <option value="">Selecciona...</option>
              {clientes.filter((cliente) => cliente.estado === "activo").map((cliente) => (
                <option key={cliente.id} value={cliente.id}>{cliente.razon_social}</option>
              ))}
            </Select>
          </Campo>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variante="secundario" onClick={() => setModal(false)}>Cancelar</Button>
            <Button type="submit" disabled={guardando}>{guardando ? "Guardando..." : "Guardar transportista"}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
