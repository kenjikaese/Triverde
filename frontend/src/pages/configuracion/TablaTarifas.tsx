import { useEffect, useState, type FormEvent } from "react";
import { Pencil, Plus } from "lucide-react";
import { api } from "@/lib/api";
import type { TarifaRecepcion } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { CostoPorKm } from "./CostoPorKm";

const VACIO = { tramo_min_m3: "", tramo_max_m3: "", monto: "", vigente: true };
const clp = (valor: string) => `$${Math.round(Number(valor)).toLocaleString("es-CL")}`;

// Convierte la respuesta de error del servidor (formato DRF) en un texto legible.
function mensajeDeError(err: unknown, porDefecto: string): string {
  const data = (err as { response?: { data?: unknown } })?.response?.data;
  if (!data) return porDefecto;
  if (typeof data === "string") return data;
  if (typeof data === "object") {
    const partes: string[] = [];
    for (const valor of Object.values(data as Record<string, unknown>)) {
      if (Array.isArray(valor)) partes.push(...valor.map(String));
      else if (typeof valor === "string") partes.push(valor);
    }
    if (partes.length > 0) return partes.join(" ");
  }
  return porDefecto;
}

export function TablaTarifas() {
  const [tarifas, setTarifas] = useState<TarifaRecepcion[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState(false);
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [form, setForm] = useState(VACIO);
  const [errorForm, setErrorForm] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const editando = editandoId !== null;

  function cargar() {
    setCargando(true); setError(null);
    api.get<TarifaRecepcion[]>("/tarifas/").then((res) => setTarifas(res.data)).catch(() => setError("No se pudieron cargar las tarifas.")).finally(() => setCargando(false));
  }
  useEffect(cargar, []);

  function abrirNueva() {
    setEditandoId(null); setForm(VACIO); setErrorForm(null); setModal(true);
  }

  function abrirEditar(tarifa: TarifaRecepcion) {
    setEditandoId(tarifa.id);
    setForm({
      tramo_min_m3: String(tarifa.tramo_min_m3),
      tramo_max_m3: String(tarifa.tramo_max_m3),
      monto: String(Math.round(Number(tarifa.monto))),
      vigente: tarifa.vigente,
    });
    setErrorForm(null); setModal(true);
  }

  function cerrar() {
    setModal(false); setEditandoId(null); setForm(VACIO); setErrorForm(null);
  }

  async function guardar(e: FormEvent) {
    e.preventDefault(); setErrorForm(null);

    // Excepción 3: precio vacío, en cero o negativo.
    if (form.monto === "" || !(Number(form.monto) > 0)) {
      setErrorForm("El precio debe ser mayor a cero.");
      return;
    }
    if (Number(form.tramo_min_m3) >= Number(form.tramo_max_m3)) {
      setErrorForm("El volumen máximo debe ser mayor al volumen mínimo.");
      return;
    }

    setGuardando(true);
    try {
      if (editando) await api.patch(`/tarifas/${editandoId}/`, form);
      else await api.post("/tarifas/", form);
      cerrar(); cargar();
    } catch (err) {
      // Excepción 2: el servidor rechaza rangos que se superponen y el mensaje se muestra en el formulario.
      setErrorForm(mensajeDeError(err, "No se pudo guardar la tarifa. Revisa que el tramo sea válido."));
    } finally { setGuardando(false); }
  }

  return (
    <div>
      <PageHeader titulo="Tarifas de recepción" descripcion="Montos aplicados según el volumen del camión recibido." accion={<Button onClick={abrirNueva}><Plus className="h-4 w-4" /> Nueva tarifa</Button>} />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <Card>
        <Table><thead><tr><Th>Desde</Th><Th>Hasta</Th><Th>Monto</Th><Th>Vigencia</Th><Th>Acciones</Th></tr></thead><TBody>
          {cargando ? <EmptyRow colSpan={5} texto="Cargando..." /> : error && tarifas.length === 0 ? <EmptyRow colSpan={5} texto={error} /> : tarifas.length === 0 ? <EmptyRow colSpan={5} texto="No hay tarifas configuradas." /> : tarifas.map((tarifa) => (
            <tr key={tarifa.id} className="hover:bg-slate-50">
              <Td>{tarifa.tramo_min_m3} m³</Td>
              <Td>{tarifa.tramo_max_m3} m³</Td>
              <Td className="font-medium text-slate-800">{clp(tarifa.monto)}</Td>
              <Td><Badge tono={tarifa.vigente ? "verde" : "gris"}>{tarifa.vigente ? "Vigente" : "No vigente"}</Badge></Td>
              <Td><Button type="button" variante="secundario" onClick={() => abrirEditar(tarifa)}><Pencil className="h-4 w-4" /> Editar</Button></Td>
            </tr>
          ))}
        </TBody></Table>
      </Card>
      <CostoPorKm />
      <Modal abierto={modal} titulo={editando ? "Editar tarifa" : "Nueva tarifa"} onCerrar={cerrar}>
        <form onSubmit={guardar} className="space-y-4">
          {errorForm && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{errorForm}</div>}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2"><Campo label="Volumen mínimo (m³)" htmlFor="tarifa_min" requerido><Input id="tarifa_min" type="number" min="0" step="0.01" value={form.tramo_min_m3} onChange={(e) => setForm({ ...form, tramo_min_m3: e.target.value })} required /></Campo><Campo label="Volumen máximo (m³)" htmlFor="tarifa_max" requerido><Input id="tarifa_max" type="number" min="0" step="0.01" value={form.tramo_max_m3} onChange={(e) => setForm({ ...form, tramo_max_m3: e.target.value })} required /></Campo></div>
          <Campo label="Monto (CLP)" htmlFor="tarifa_monto" requerido><Input id="tarifa_monto" type="number" step="1" value={form.monto} onChange={(e) => setForm({ ...form, monto: e.target.value })} required /></Campo>
          <Campo label="Vigencia" htmlFor="tarifa_vigente" requerido><Select id="tarifa_vigente" value={form.vigente ? "si" : "no"} onChange={(e) => setForm({ ...form, vigente: e.target.value === "si" })}><option value="si">Vigente</option><option value="no">No vigente</option></Select></Campo>
          <div className="flex justify-end gap-2 pt-2"><Button type="button" variante="secundario" onClick={cerrar}>Cancelar</Button><Button type="submit" disabled={guardando}>{guardando ? "Guardando..." : editando ? "Guardar cambios" : "Guardar tarifa"}</Button></div>
        </form>
      </Modal>
    </div>
  );
}
