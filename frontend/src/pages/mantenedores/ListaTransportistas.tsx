import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Pencil, Plus, Power, Search, UserX } from "lucide-react";
import { api } from "@/lib/api";
import { mensajeDeError } from "@/lib/errores";
import type { Cliente, Transportista, Usuario } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";

const VACIO = { nombre: "", rut: "", telefono: "", cliente: "", usuario: "" };

export function ListaTransportistas() {
  const [transportistas, setTransportistas] = useState<Transportista[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [busqueda, setBusqueda] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState(false);
  const [editando, setEditando] = useState<Transportista | null>(null);
  const [form, setForm] = useState(VACIO);
  const [errorCliente, setErrorCliente] = useState<string | null>(null);
  const [errorModal, setErrorModal] = useState<string | null>(null);
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
  // Aparte de la carga principal: sin estas cuentas la lista igual debe mostrarse.
  useEffect(() => {
    api.get<Usuario[]>("/usuarios/").then((r) => setUsuarios(r.data)).catch(() => setUsuarios([]));
  }, []);

  // CU-28: solo cuentas de rol Transportista que no esten ya vinculadas.
  const cuentasLibres = useMemo(
    () =>
      usuarios.filter(
        (usuario) =>
          usuario.rol_nombre === "Transportista" &&
          usuario.estado === "activo" &&
          !transportistas.some((transportista) => transportista.usuario === usuario.id && transportista.id !== editando?.id),
      ),
    [usuarios, transportistas, editando],
  );

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

  function abrir(transportista: Transportista | null) {
    setEditando(transportista);
    setForm(transportista ? {
      nombre: transportista.nombre,
      rut: transportista.rut ?? "",
      telefono: transportista.telefono ?? "",
      cliente: String(transportista.cliente),
      usuario: transportista.usuario === null ? "" : String(transportista.usuario),
    } : VACIO);
    setErrorCliente(null);
    setErrorModal(null);
    setModal(true);
  }

  async function guardar(e: FormEvent) {
    e.preventDefault();
    if (editando) {
      const cliente = clientes.find((item) => String(item.id) === form.cliente);
      if (!cliente) {
        setErrorCliente("Selecciona un cliente.");
        return;
      }
      if (cliente.estado !== "activo") {
        setErrorCliente("El cliente seleccionado no está activo.");
        return;
      }
    }
    setErrorCliente(null);
    setGuardando(true);
    setErrorModal(null);
    try {
      const asociacion = {
        cliente: Number(form.cliente),
        usuario: form.usuario ? Number(form.usuario) : null,
      };
      if (editando) {
        await api.patch(`/transportistas/${editando.id}/`, asociacion);
      } else {
        await api.post("/transportistas/", {
          nombre: form.nombre,
          rut: form.rut || null,
          telefono: form.telefono || null,
          ...asociacion,
        });
      }
      setModal(false);
      setForm(VACIO);
      cargar();
    } catch (err) {
      setErrorModal(mensajeDeError(err, "No se pudo guardar el transportista. Revisa los datos ingresados."));
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

  // Reactiva un transportista dado de baja. Si su cliente sigue inactivo, primero hay que activar el cliente.
  async function activar(transportista: Transportista) {
    const cliente = clientes.find((item) => item.id === transportista.cliente);
    if (cliente && cliente.estado !== "activo") {
      setError(`Para activar a ${transportista.nombre}, primero activa su cliente (${cliente.razon_social}).`);
      return;
    }
    setError(null);
    try {
      await api.patch(`/transportistas/${transportista.id}/`, { estado: "activo" });
      cargar();
    } catch (err) {
      setError(mensajeDeError(err, "No se pudo activar el transportista."));
    }
  }

  return (
    <div>
      <PageHeader
        titulo="Transportistas"
        descripcion="Conductores y empresas asociados a los clientes de la planta."
        accion={
          <Button onClick={() => abrir(null)}>
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
                    <Button variante="secundario" tamano="sm" onClick={() => abrir(transportista)}>
                      <Pencil className="h-4 w-4" /> Editar
                    </Button>{" "}
                    {transportista.estado === "activo" ? (
                      <Button variante="peligro" tamano="sm" onClick={() => desactivar(transportista)}>
                        <UserX className="h-4 w-4" /> Desactivar
                      </Button>
                    ) : (
                      <Button variante="secundario" tamano="sm" onClick={() => activar(transportista)}>
                        <Power className="h-4 w-4" /> Activar
                      </Button>
                    )}
                  </Td>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      </Card>

      <Modal abierto={modal} titulo={editando ? "Editar transportista" : "Nuevo transportista"} onCerrar={() => setModal(false)}>
        <form onSubmit={guardar} noValidate={!!editando} className="space-y-4">
          {errorModal && <div role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{errorModal}</div>}
          {!editando && <>
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
          </>}
          <Campo label="Cliente" htmlFor="transportista_cliente" requerido error={errorCliente ?? undefined}>
            <Select id="transportista_cliente" value={form.cliente} onChange={(e) => { setForm({ ...form, cliente: e.target.value }); setErrorCliente(null); }} required aria-invalid={!!errorCliente}>
              <option value="">Selecciona...</option>
              {clientes.filter((cliente) => editando || cliente.estado === "activo").map((cliente) => (
                <option key={cliente.id} value={cliente.id}>{cliente.razon_social}{cliente.estado === "inactivo" ? " (inactivo)" : ""}</option>
              ))}
            </Select>
          </Campo>
          <Campo label="Cuenta de acceso" htmlFor="transportista_usuario" ayuda="Permite que registre sus descargas desde su propia cuenta. La cuenta se crea antes en Usuarios, con rol Transportista.">
            <Select id="transportista_usuario" value={form.usuario} onChange={(e) => setForm({ ...form, usuario: e.target.value })}>
              <option value="">Sin cuenta</option>
              {editando?.usuario && !cuentasLibres.some((usuario) => usuario.id === editando.usuario) && (
                <option value={editando.usuario}>{usuarios.find((usuario) => usuario.id === editando.usuario)?.username ?? `Cuenta #${editando.usuario}`}</option>
              )}
              {cuentasLibres.map((usuario) => (
                <option key={usuario.id} value={usuario.id}>{usuario.username} ({usuario.nombre_completo})</option>
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
