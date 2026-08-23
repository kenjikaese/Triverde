import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Leaf, Plus, Search } from "lucide-react";
import { api } from "@/lib/api";
import type { Material } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";

const VACIO = { nombre: "", categoria: "", densidad_kg_m3: "", factor_reduccion_chip: "", admite_chip: false };

export function ListaMateriales() {
  const [materiales, setMateriales] = useState<Material[]>([]);
  const [busqueda, setBusqueda] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState(VACIO);
  const [guardando, setGuardando] = useState(false);

  function cargar() {
    setCargando(true);
    setError(null);
    api.get<Material[]>("/materiales/")
      .then((res) => setMateriales(res.data))
      .catch(() => setError("No se pudo cargar la lista de materiales."))
      .finally(() => setCargando(false));
  }

  useEffect(cargar, []);

  const filtrados = useMemo(() => materiales.filter((material) =>
    material.nombre.toLowerCase().includes(busqueda.toLowerCase()),
  ), [materiales, busqueda]);

  async function crear(e: FormEvent) {
    e.preventDefault();
    setGuardando(true);
    setError(null);
    try {
      await api.post("/materiales/", {
        nombre: form.nombre,
        categoria: form.categoria || null,
        densidad_kg_m3: form.densidad_kg_m3 || null,
        factor_reduccion_chip: form.factor_reduccion_chip || null,
        admite_chip: form.admite_chip,
      });
      setModal(false);
      setForm(VACIO);
      cargar();
    } catch {
      setError("No se pudo guardar el material. Revisa los datos ingresados.");
    } finally {
      setGuardando(false);
    }
  }

  async function desactivar(material: Material) {
    if (!window.confirm(`¿Desactivar ${material.nombre}?`)) return;
    try {
      await api.delete(`/materiales/${material.id}/`);
      cargar();
    } catch {
      setError("No se pudo desactivar el material.");
    }
  }

  return (
    <div>
      <PageHeader titulo="Materiales" descripcion="Catálogo de residuos recibidos y sus factores de conversión." accion={
        <Button onClick={() => setModal(true)}><Plus className="h-4 w-4" /> Nuevo material</Button>
      } />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <div className="relative mb-4 max-w-xs">
        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <Input placeholder="Buscar material" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} className="pl-9" />
      </div>
      <Card>
        <Table>
          <thead><tr><Th>Material</Th><Th>Categoría</Th><Th>Densidad</Th><Th>Factor chip</Th><Th>Admite chip</Th><Th>Estado</Th><Th>Acciones</Th></tr></thead>
          <TBody>
            {cargando ? <EmptyRow colSpan={7} texto="Cargando..." /> : error && materiales.length === 0 ? <EmptyRow colSpan={7} texto={error} /> : filtrados.length === 0 ? <EmptyRow colSpan={7} texto="Sin materiales que coincidan." /> : filtrados.map((material) => (
              <tr key={material.id} className="hover:bg-slate-50">
                <Td className="font-medium text-slate-800">{material.nombre}</Td>
                <Td>{material.categoria ?? "—"}</Td>
                <Td>{material.densidad_kg_m3 ? `${material.densidad_kg_m3} kg/m³` : "—"}</Td>
                <Td>{material.factor_reduccion_chip ?? "—"}</Td>
                <Td><Badge tono={material.admite_chip ? "verde" : "gris"}>{material.admite_chip ? "Sí" : "No"}</Badge></Td>
                <Td><Badge tono={tonoEstado(material.estado)}>{material.estado}</Badge></Td>
                <Td>{material.estado === "activo" ? <Button variante="peligro" tamano="sm" onClick={() => desactivar(material)}><Leaf className="h-4 w-4" /> Desactivar</Button> : "—"}</Td>
              </tr>
            ))}
          </TBody>
        </Table>
      </Card>
      <Modal abierto={modal} titulo="Nuevo material" onCerrar={() => setModal(false)}>
        <form onSubmit={crear} className="space-y-4">
          <Campo label="Nombre" htmlFor="material_nombre" requerido><Input id="material_nombre" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} required /></Campo>
          <Campo label="Categoría" htmlFor="material_categoria"><Select id="material_categoria" value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })}><option value="">Sin categoría</option><option value="seca">Seca</option><option value="verde">Verde</option></Select></Campo>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Campo label="Densidad (kg/m³)" htmlFor="material_densidad"><Input id="material_densidad" type="number" min="0" step="0.01" value={form.densidad_kg_m3} onChange={(e) => setForm({ ...form, densidad_kg_m3: e.target.value })} /></Campo>
            <Campo label="Factor reducción chip" htmlFor="material_factor"><Input id="material_factor" type="number" min="0" step="0.01" value={form.factor_reduccion_chip} onChange={(e) => setForm({ ...form, factor_reduccion_chip: e.target.value })} /></Campo>
          </div>
          <Campo label="Procesamiento a chip" htmlFor="material_admite_chip" requerido><Select id="material_admite_chip" value={form.admite_chip ? "si" : "no"} onChange={(e) => setForm({ ...form, admite_chip: e.target.value === "si" })}><option value="si">Sí, admite chip</option><option value="no">No admite chip</option></Select></Campo>
          <div className="flex justify-end gap-2 pt-2"><Button type="button" variante="secundario" onClick={() => setModal(false)}>Cancelar</Button><Button type="submit" disabled={guardando}>{guardando ? "Guardando..." : "Guardar material"}</Button></div>
        </form>
      </Modal>
    </div>
  );
}
