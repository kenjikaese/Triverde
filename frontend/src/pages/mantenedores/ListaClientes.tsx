import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Plus, Search } from "lucide-react";
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

export function ListaClientes() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [busqueda, setBusqueda] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [modal, setModal] = useState(false);
  const [form, setForm] = useState(VACIO);
  const [guardando, setGuardando] = useState(false);

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

  async function crear(e: FormEvent) {
    e.preventDefault();
    setGuardando(true);
    try {
      await api.post("/clientes/", form);
      setModal(false);
      setForm(VACIO);
      cargar();
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div>
      <PageHeader
        titulo="Clientes"
        descripcion="Generadores que descargan material en la planta."
        accion={
          <Button onClick={() => setModal(true)}>
            <Plus className="h-4 w-4" />
            Nuevo cliente
          </Button>
        }
      />

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
            </tr>
          </thead>
          <TBody>
            {cargando ? (
              <EmptyRow colSpan={5} texto="Cargando..." />
            ) : error ? (
              <EmptyRow colSpan={5} texto={error} />
            ) : filtrados.length === 0 ? (
              <EmptyRow colSpan={5} texto="Sin clientes que coincidan." />
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
                </tr>
              ))
            )}
          </TBody>
        </Table>
      </Card>

      <Modal abierto={modal} titulo="Nuevo cliente" onCerrar={() => setModal(false)}>
        <form onSubmit={crear} className="space-y-4">
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
            <Button type="button" variante="secundario" onClick={() => setModal(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={guardando}>
              {guardando ? "Guardando..." : "Guardar cliente"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
