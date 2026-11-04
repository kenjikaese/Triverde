import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Ban, Pencil, Plus } from "lucide-react";
import { isAxiosError } from "axios";
import { api } from "@/lib/api";
import { mensajeDeError } from "@/lib/errores";
import type { RecetaMezcla } from "@/lib/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Campo, Input, Textarea } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyRow, Table, TBody, Td, Th } from "@/components/ui/Table";

const VACIO = { nombre: "", relacion_seca: "", relacion_verde: "", descripcion: "" };

// V_ListaRecetas y V_FormularioReceta (CU-10). La mezcla objetivo usa la receta
// vigente modificada mas recientemente (mezcla/services.py), por eso se senala.
export function ListaRecetas() {
  const [recetas, setRecetas] = useState<RecetaMezcla[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [abierto, setAbierto] = useState(false);
  const [editando, setEditando] = useState<RecetaMezcla | null>(null);
  const [form, setForm] = useState(VACIO);
  const [errorModal, setErrorModal] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(() => {
    setCargando(true);
    api
      .get<RecetaMezcla[]>("/recetas/")
      .then((r) => setRecetas(r.data))
      .catch((err) => setError(mensajeDeError(err, "No se pudieron cargar las recetas.")))
      .finally(() => setCargando(false));
  }, []);
  useEffect(cargar, [cargar]);

  const enUso = useMemo(() => {
    const vigentes = recetas.filter((r) => r.vigente);
    vigentes.sort((a, b) => b.actualizado_en.localeCompare(a.actualizado_en) || b.id - a.id);
    return vigentes[0]?.id ?? null;
  }, [recetas]);

  function abrir(receta: RecetaMezcla | null) {
    setEditando(receta);
    setForm(
      receta
        ? { nombre: receta.nombre, relacion_seca: receta.relacion_seca, relacion_verde: receta.relacion_verde, descripcion: receta.descripcion }
        : VACIO,
    );
    setErrorModal(null);
    setAbierto(true);
  }

  async function guardar(e: FormEvent) {
    e.preventDefault();
    setGuardando(true);
    setErrorModal(null);
    setAviso(null);
    try {
      if (editando) await api.patch(`/recetas/${editando.id}/`, form);
      else await api.post("/recetas/", form);
      setAbierto(false);
      setAviso(`Receta "${form.nombre}" guardada.`);
      cargar();
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 404) {
        // Excepcion 1: otro administrador la elimino mientras se editaba.
        setAbierto(false);
        setError("La receta ya no existe.");
        cargar();
      } else {
        setErrorModal(mensajeDeError(err, "No se pudo guardar la receta."));
      }
    } finally {
      setGuardando(false);
    }
  }

  async function darDeBaja(receta: RecetaMezcla) {
    if (!window.confirm(`¿Dar de baja la receta ${receta.nombre}?`)) return;
    setError(null);
    setAviso(null);
    try {
      await api.delete(`/recetas/${receta.id}/`);
      setAviso(`Receta "${receta.nombre}" dada de baja.`);
      cargar();
    } catch (err) {
      setError(mensajeDeError(err, "No se pudo dar de baja la receta."));
    }
  }

  return (
    <div>
      <PageHeader
        titulo="Recetas de mezcla"
        descripcion="Proporción entre material seco y verde que se usa para calcular la mezcla objetivo de las pilas."
        accion={<Button onClick={() => abrir(null)}><Plus className="h-4 w-4" /> Nueva receta</Button>}
      />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {aviso && <div className="mb-4 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800">{aviso}</div>}

      <Card>
        <Table>
          <thead><tr><Th>Nombre</Th><Th>Seco : verde</Th><Th>Descripción</Th><Th>Estado</Th><Th>Acciones</Th></tr></thead>
          <TBody>
            {cargando ? <EmptyRow colSpan={5} texto="Cargando..." /> : recetas.length === 0 ? <EmptyRow colSpan={5} texto="No hay recetas registradas." /> : recetas.map((receta) => (
              <tr key={receta.id} className="hover:bg-slate-50" data-testid="fila-receta">
                <Td className="font-medium text-slate-800">{receta.nombre}</Td>
                <Td>{receta.proporcion}</Td>
                <Td>{receta.descripcion || "—"}</Td>
                <Td>
                  {receta.id === enUso ? <Badge tono="verde">En uso</Badge> : receta.vigente ? <Badge tono="azul">Vigente</Badge> : <Badge tono="ambar">De baja</Badge>}
                </Td>
                <Td>
                  {receta.vigente ? (
                    <div className="flex flex-wrap gap-2">
                      <Button variante="secundario" tamano="sm" onClick={() => abrir(receta)}><Pencil className="h-4 w-4" /> Editar</Button>
                      <Button variante="peligro" tamano="sm" onClick={() => darDeBaja(receta)}><Ban className="h-4 w-4" /> Dar de baja</Button>
                    </div>
                  ) : "—"}
                </Td>
              </tr>
            ))}
          </TBody>
        </Table>
      </Card>

      <Modal abierto={abierto} titulo={editando ? "Editar receta" : "Nueva receta"} onCerrar={() => setAbierto(false)}>
        <form onSubmit={guardar} className="space-y-4">
          {errorModal && <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{errorModal}</div>}
          <Campo label="Nombre" htmlFor="receta_nombre" requerido>
            <Input id="receta_nombre" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} required />
          </Campo>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Campo label="Partes de seco" htmlFor="receta_seca" requerido>
              <Input id="receta_seca" type="number" step="0.01" value={form.relacion_seca} onChange={(e) => setForm({ ...form, relacion_seca: e.target.value })} required />
            </Campo>
            <Campo label="Partes de verde" htmlFor="receta_verde" requerido>
              <Input id="receta_verde" type="number" step="0.01" value={form.relacion_verde} onChange={(e) => setForm({ ...form, relacion_verde: e.target.value })} required />
            </Campo>
          </div>
          <Campo label="Descripción" htmlFor="receta_descripcion">
            <Textarea id="receta_descripcion" value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} />
          </Campo>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variante="secundario" onClick={() => setAbierto(false)}>Cancelar</Button>
            <Button type="submit" disabled={guardando}>{guardando ? "Guardando..." : "Guardar receta"}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
