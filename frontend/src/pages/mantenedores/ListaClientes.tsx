import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Pencil, Plus, Power, Search } from "lucide-react";
import { api } from "@/lib/api";
import type { Cliente } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Campo, Input } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";

const VACIO = { razon_social: "", rut: "", nombre_contacto: "", telefono: "", email: "" };

const NOMBRES_CAMPO: Record<string, string> = {
  razon_social: "Razón social",
  rut: "RUT",
  nombre_contacto: "Nombre de contacto",
  telefono: "Teléfono",
  email: "Email",
};

// Convierte la respuesta de error del servidor (formato DRF) en un texto legible.
function mensajeDeError(err: unknown, porDefecto: string): string {
  const data = (err as { response?: { data?: unknown } })?.response?.data;
  if (!data) return porDefecto;
  if (typeof data === "string") return data;
  if (typeof data === "object") {
    const partes: string[] = [];
    for (const [campo, valor] of Object.entries(data as Record<string, unknown>)) {
      const textos = Array.isArray(valor) ? valor.map(String) : typeof valor === "string" ? [valor] : [];
      const nombre = NOMBRES_CAMPO[campo];
      for (const t of textos) partes.push(nombre ? `${nombre}: ${t}` : t);
    }
    if (partes.length > 0) return partes.join(" ");
  }
  return porDefecto;
}

function estaInactivo(c: Cliente) {
  return String(c.estado).toLowerCase() === "inactivo";
}

export function ListaClientes() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [busqueda, setBusqueda] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);

  const [modal, setModal] = useState(false);
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [form, setForm] = useState(VACIO);
  const [errorForm, setErrorForm] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const [porDesactivar, setPorDesactivar] = useState<Cliente | null>(null);
  const [desactivando, setDesactivando] = useState(false);
  const [errorDesactivar, setErrorDesactivar] = useState<string | null>(null);

  const editando = editandoId !== null;

  function cargar() {
    setCargando(true);
    api
      .get<Cliente[]>("/clientes/")
      .then((res) => setClientes(res.data))
      .catch(() => setError("No se pudo cargar la lista de clientes."))
      .finally(() => setCargando(false));
  }

  useEffect(cargar, []);

  const filtrados = useMemo(
    () =>
      clientes.filter((c) =>
        c.razon_social.toLowerCase().includes(busqueda.toLowerCase()),
      ),
    [clientes, busqueda],
  );

  function abrirNuevo() {
    setEditandoId(null);
    setForm(VACIO);
    setErrorForm(null);
    setModal(true);
  }

  function abrirEditar(c: Cliente) {
    const datos = c as Cliente & Partial<typeof VACIO>;
    setEditandoId(c.id);
    setForm({
      razon_social: datos.razon_social ?? "",
      rut: datos.rut ?? "",
      nombre_contacto: datos.nombre_contacto ?? "",
      telefono: datos.telefono ?? "",
      email: datos.email ?? "",
    });
    setErrorForm(null);
    setModal(true);
  }

  function cerrar() {
    setModal(false);
    setEditandoId(null);
    setForm(VACIO);
    setErrorForm(null);
  }

  async function guardar(e: FormEvent) {
    e.preventDefault();
    setErrorForm(null);

    // Excepción 1: dato obligatorio vacío. Se señala el campo y no se guarda.
    if (form.razon_social.trim() === "") {
      setErrorForm("Falta un dato obligatorio: Razón social.");
      return;
    }

    setGuardando(true);
    try {
      if (editando) await api.patch(`/clientes/${editandoId}/`, form);
      else await api.post("/clientes/", form);
      cerrar();
      cargar();
    } catch (err) {
      // Excepción 2: RUT repetido. El servidor rechaza el cambio; el modal sigue abierto
      // y la lista no se recarga, por lo que los datos previos se mantienen.
      setErrorForm(
        mensajeDeError(err, "No se pudo guardar el cliente. Revisa los datos e inténtalo de nuevo."),
      );
    } finally {
      setGuardando(false);
    }
  }

  function pedirDesactivar(c: Cliente) {
    setErrorDesactivar(null);
    setPorDesactivar(c);
  }

  async function desactivar() {
    if (!porDesactivar) return;
    setDesactivando(true);
    setErrorDesactivar(null);
    try {
      // El servidor no borra el cliente, lo deja inactivo. Sus transportistas no se tocan.
      await api.delete(`/clientes/${porDesactivar.id}/`);
      setPorDesactivar(null);
      setErrorAccion(null);
      cargar();
    } catch (err) {
      setErrorDesactivar(mensajeDeError(err, "No se pudo desactivar el cliente."));
    } finally {
      setDesactivando(false);
    }
  }

  return (
    <div>
      <PageHeader
        titulo="Clientes"
        descripcion="Generadores que descargan material en la planta."
        accion={
          <Button onClick={abrirNuevo}>
            <Plus className="h-4 w-4" />
            Nuevo cliente
          </Button>
        }
      />

      {errorAccion && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{errorAccion}</div>
      )}

      <div className="mb-4 relative max-w-xs">
        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <Input
          placeholder="Buscar por razon social"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          className="pl-9"
        />
      </div>

      <Card>
        <Table>
          <thead>
            <tr>
              <Th>Razon social</Th>
              <Th>RUT</Th>
              <Th>Contacto</Th>
              <Th>Pago</Th>
              <Th>Estado</Th>
              <Th>Acciones</Th>
            </tr>
          </thead>
          <TBody>
            {cargando ? (
              <EmptyRow colSpan={6} texto="Cargando..." />
            ) : error ? (
              <EmptyRow colSpan={6} texto={error} />
            ) : filtrados.length === 0 ? (
              <EmptyRow colSpan={6} texto="Sin clientes que coincidan." />
            ) : (
              filtrados.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50">
                  <Td className="font-medium text-slate-800">{c.razon_social}</Td>
                  <Td>{c.rut ?? "—"}</Td>
                  <Td>{c.nombre_contacto ?? "—"}</Td>
                  <Td>
                    <Badge tono={tonoEstado(c.estado_pago)}>{c.estado_pago}</Badge>
                  </Td>
                  <Td>
                    <Badge tono={tonoEstado(c.estado)}>{c.estado}</Badge>
                  </Td>
                  <Td>
                    <div className="flex gap-2">
                      <Button type="button" variante="secundario" onClick={() => abrirEditar(c)}>
                        <Pencil className="h-4 w-4" />
                        Editar
                      </Button>
                      <Button
                        type="button"
                        variante="secundario"
                        disabled={estaInactivo(c)}
                        onClick={() => pedirDesactivar(c)}
                      >
                        <Power className="h-4 w-4" />
                        Desactivar
                      </Button>
                    </div>
                  </Td>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      </Card>

      <Modal abierto={modal} titulo={editando ? "Editar cliente" : "Nuevo cliente"} onCerrar={cerrar}>
        <form onSubmit={guardar} className="space-y-4">
          {errorForm && (
            <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{errorForm}</div>
          )}
          <Campo label="Razon social" htmlFor="razon_social" requerido>
            <Input
              id="razon_social"
              value={form.razon_social}
              onChange={(e) => setForm({ ...form, razon_social: e.target.value })}
              required
            />
          </Campo>
          <div className="grid grid-cols-2 gap-4">
            <Campo label="RUT" htmlFor="rut">
              <Input
                id="rut"
                value={form.rut}
                onChange={(e) => setForm({ ...form, rut: e.target.value })}
              />
            </Campo>
            <Campo label="Telefono" htmlFor="telefono">
              <Input
                id="telefono"
                value={form.telefono}
                onChange={(e) => setForm({ ...form, telefono: e.target.value })}
              />
            </Campo>
          </div>
          <Campo label="Nombre de contacto" htmlFor="nombre_contacto">
            <Input
              id="nombre_contacto"
              value={form.nombre_contacto}
              onChange={(e) => setForm({ ...form, nombre_contacto: e.target.value })}
            />
          </Campo>
          <Campo label="Email" htmlFor="email">
            <Input
              id="email"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </Campo>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variante="secundario" onClick={cerrar}>
              Cancelar
            </Button>
            <Button type="submit" disabled={guardando}>
              {guardando ? "Guardando..." : editando ? "Guardar cambios" : "Guardar cliente"}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        abierto={porDesactivar !== null}
        titulo="Desactivar cliente"
        onCerrar={() => setPorDesactivar(null)}
      >
        <div className="space-y-4">
          {errorDesactivar && (
            <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{errorDesactivar}</div>
          )}
          <p className="text-sm text-slate-700">
            ¿Desactivar a <span className="font-medium">{porDesactivar?.razon_social}</span>? El cliente
            no se borra, queda inactivo. Si tiene transportistas asociados, no se desasocian ni se
            afectan, y quedan disponibles para asociarse a otro cliente.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variante="secundario" onClick={() => setPorDesactivar(null)}>
              Cancelar
            </Button>
            <Button type="button" onClick={desactivar} disabled={desactivando}>
              {desactivando ? "Desactivando..." : "Desactivar cliente"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
