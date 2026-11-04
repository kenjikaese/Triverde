import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Pencil, Plus } from "lucide-react";
import { api } from "@/lib/api";
import { mensajeDeError } from "@/lib/errores";
import type { CostoOperativo, UnidadCostoOperativo } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyRow, Table, TBody, Td, Th } from "@/components/ui/Table";

const UNIDADES: { valor: UnidadCostoOperativo; etiqueta: string }[] = [
  { valor: "litro", etiqueta: "Litro" },
  { valor: "hora", etiqueta: "Hora" },
  { valor: "dia", etiqueta: "Día" },
  { valor: "viaje", etiqueta: "Viaje" },
  { valor: "unidad", etiqueta: "Unidad" },
];
const VACIO = { concepto: "", monto: "", unidad: "hora" as UnidadCostoOperativo };

// V_CostosOperativos (CU-13): valores de referencia para las proyecciones.
export function CostosOperativos() {
  const [costos, setCostos] = useState<CostoOperativo[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [abierto, setAbierto] = useState(false);
  const [editando, setEditando] = useState<CostoOperativo | null>(null);
  const [form, setForm] = useState(VACIO);
  const [errorModal, setErrorModal] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(() => {
    setCargando(true);
    api
      .get<CostoOperativo[]>("/costos-operativos/", { params: { vigente: "true" } })
      .then((r) => setCostos(r.data))
      .catch((err) => setError(mensajeDeError(err, "No se pudieron cargar los costos.")))
      .finally(() => setCargando(false));
  }, []);
  useEffect(cargar, [cargar]);

  function abrir(costo: CostoOperativo | null) {
    setEditando(costo);
    setForm(costo ? { concepto: costo.concepto, monto: costo.monto, unidad: costo.unidad } : VACIO);
    setErrorModal(null);
    setAbierto(true);
  }

  async function guardar(e: FormEvent) {
    e.preventDefault();
    setGuardando(true);
    setErrorModal(null);
    setAviso(null);
    try {
      if (editando) await api.patch(`/costos-operativos/${editando.id}/`, form);
      else await api.post("/costos-operativos/", form);
      setAbierto(false);
      setAviso(`Costo "${form.concepto}" guardado.`);
      cargar();
    } catch (err) {
      setErrorModal(mensajeDeError(err, "No se pudo guardar el costo."));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div>
      <PageHeader
        titulo="Costos operativos"
        descripcion="Valores de referencia que se usan en las proyecciones de rentabilidad."
        accion={<Button onClick={() => abrir(null)}><Plus className="h-4 w-4" /> Agregar concepto</Button>}
      />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {aviso && <div className="mb-4 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800">{aviso}</div>}

      <Card>
        <Table>
          <thead><tr><Th>Concepto</Th><Th>Valor</Th><Th>Unidad</Th><Th>Actualizado</Th><Th>Acciones</Th></tr></thead>
          <TBody>
            {cargando ? <EmptyRow colSpan={5} texto="Cargando..." /> : costos.length === 0 ? <EmptyRow colSpan={5} texto="No hay costos registrados." /> : costos.map((costo) => (
              <tr key={costo.id} className="hover:bg-slate-50" data-testid="fila-costo">
                <Td className="font-medium text-slate-800">{costo.concepto}</Td>
                <Td>${Math.round(Number(costo.monto)).toLocaleString("es-CL")}</Td>
                <Td>{costo.unidad_display}</Td>
                <Td>{new Date(costo.actualizado_en).toLocaleDateString("es-CL")}</Td>
                <Td><Button variante="secundario" tamano="sm" onClick={() => abrir(costo)}><Pencil className="h-4 w-4" /> Editar</Button></Td>
              </tr>
            ))}
          </TBody>
        </Table>
      </Card>

      <Modal abierto={abierto} titulo={editando ? "Editar costo" : "Agregar concepto"} onCerrar={() => setAbierto(false)}>
        <form onSubmit={guardar} className="space-y-4">
          {errorModal && <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{errorModal}</div>}
          <Campo label="Concepto" htmlFor="costo_concepto" requerido>
            <Input id="costo_concepto" value={form.concepto} onChange={(e) => setForm({ ...form, concepto: e.target.value })} required />
          </Campo>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Campo label="Valor (CLP)" htmlFor="costo_monto" requerido>
              <Input id="costo_monto" type="number" step="1" value={form.monto} onChange={(e) => setForm({ ...form, monto: e.target.value })} required />
            </Campo>
            <Campo label="Unidad" htmlFor="costo_unidad" requerido>
              <Select id="costo_unidad" value={form.unidad} onChange={(e) => setForm({ ...form, unidad: e.target.value as UnidadCostoOperativo })}>
                {UNIDADES.map((u) => <option key={u.valor} value={u.valor}>{u.etiqueta}</option>)}
              </Select>
            </Campo>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variante="secundario" onClick={() => setAbierto(false)}>Cancelar</Button>
            <Button type="submit" disabled={guardando}>{guardando ? "Guardando..." : "Guardar costo"}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
