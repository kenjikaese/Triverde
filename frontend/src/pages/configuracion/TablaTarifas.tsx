import { useEffect, useState, type FormEvent } from "react";
import { Plus } from "lucide-react";
import { api } from "@/lib/api";
import type { TarifaRecepcion } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";

const VACIO = { tramo_min_m3: "", tramo_max_m3: "", monto: "", vigente: true };
const clp = (valor: string) => `$${Math.round(Number(valor)).toLocaleString("es-CL")}`;

export function TablaTarifas() {
  const [tarifas, setTarifas] = useState<TarifaRecepcion[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState(VACIO);
  const [guardando, setGuardando] = useState(false);

  function cargar() {
    setCargando(true); setError(null);
    api.get<TarifaRecepcion[]>("/tarifas/").then((res) => setTarifas(res.data)).catch(() => setError("No se pudieron cargar las tarifas.")).finally(() => setCargando(false));
  }
  useEffect(cargar, []);

  async function crear(e: FormEvent) {
    e.preventDefault(); setGuardando(true); setError(null);
    try { await api.post("/tarifas/", form); setModal(false); setForm(VACIO); cargar(); }
    catch { setError("No se pudo guardar la tarifa. Revisa que el tramo sea válido."); }
    finally { setGuardando(false); }
  }

  return (
    <div>
      <PageHeader titulo="Tarifas de recepción" descripcion="Montos aplicados según el volumen del camión recibido." accion={<Button onClick={() => setModal(true)}><Plus className="h-4 w-4" /> Nueva tarifa</Button>} />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <Card>
        <Table><thead><tr><Th>Desde</Th><Th>Hasta</Th><Th>Monto</Th><Th>Vigencia</Th></tr></thead><TBody>
          {cargando ? <EmptyRow colSpan={4} texto="Cargando..." /> : error && tarifas.length === 0 ? <EmptyRow colSpan={4} texto={error} /> : tarifas.length === 0 ? <EmptyRow colSpan={4} texto="No hay tarifas configuradas." /> : tarifas.map((tarifa) => <tr key={tarifa.id} className="hover:bg-slate-50"><Td>{tarifa.tramo_min_m3} m³</Td><Td>{tarifa.tramo_max_m3} m³</Td><Td className="font-medium text-slate-800">{clp(tarifa.monto)}</Td><Td><Badge tono={tarifa.vigente ? "verde" : "gris"}>{tarifa.vigente ? "Vigente" : "No vigente"}</Badge></Td></tr>)}
        </TBody></Table>
      </Card>
      <Modal abierto={modal} titulo="Nueva tarifa" onCerrar={() => setModal(false)}>
        <form onSubmit={crear} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2"><Campo label="Volumen mínimo (m³)" htmlFor="tarifa_min" requerido><Input id="tarifa_min" type="number" min="0" step="0.01" value={form.tramo_min_m3} onChange={(e) => setForm({ ...form, tramo_min_m3: e.target.value })} required /></Campo><Campo label="Volumen máximo (m³)" htmlFor="tarifa_max" requerido><Input id="tarifa_max" type="number" min="0" step="0.01" value={form.tramo_max_m3} onChange={(e) => setForm({ ...form, tramo_max_m3: e.target.value })} required /></Campo></div>
          <Campo label="Monto (CLP)" htmlFor="tarifa_monto" requerido><Input id="tarifa_monto" type="number" min="0" step="1" value={form.monto} onChange={(e) => setForm({ ...form, monto: e.target.value })} required /></Campo>
          <Campo label="Vigencia" htmlFor="tarifa_vigente" requerido><Select id="tarifa_vigente" value={form.vigente ? "si" : "no"} onChange={(e) => setForm({ ...form, vigente: e.target.value === "si" })}><option value="si">Vigente</option><option value="no">No vigente</option></Select></Campo>
          <div className="flex justify-end gap-2 pt-2"><Button type="button" variante="secundario" onClick={() => setModal(false)}>Cancelar</Button><Button type="submit" disabled={guardando}>{guardando ? "Guardando..." : "Guardar tarifa"}</Button></div>
        </form>
      </Modal>
    </div>
  );
}
