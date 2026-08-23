import { useEffect, useState, type FormEvent } from "react";
import { Pencil } from "lucide-react";
import { api } from "@/lib/api";
import type { ParametroConversion } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Campo, Input } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";

export function PanelParametros() {
  const [parametros, setParametros] = useState<ParametroConversion[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editando, setEditando] = useState<ParametroConversion | null>(null);
  const [valor, setValor] = useState("");
  const [guardando, setGuardando] = useState(false);

  function cargar() {
    setCargando(true);
    setError(null);
    api.get<ParametroConversion[]>("/parametros/")
      .then((res) => setParametros(res.data))
      .catch(() => setError("No se pudieron cargar los parámetros de conversión."))
      .finally(() => setCargando(false));
  }

  useEffect(cargar, []);

  function abrirEdicion(parametro: ParametroConversion) {
    setEditando(parametro);
    setValor(parametro.valor);
  }

  async function guardar(e: FormEvent) {
    e.preventDefault();
    if (!editando) return;
    setGuardando(true);
    setError(null);
    try {
      await api.patch(`/parametros/${editando.id}/`, { valor });
      setEditando(null);
      cargar();
    } catch {
      setError("No se pudo actualizar el parámetro.");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div>
      <PageHeader titulo="Parámetros de conversión" descripcion="Valores globales usados en cálculos de peso, rendimiento e impacto." />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <Card>
        <Table>
          <thead><tr><Th>Parámetro</Th><Th>Clave</Th><Th>Valor</Th><Th>Unidad</Th><Th>Descripción</Th><Th>Acciones</Th></tr></thead>
          <TBody>
            {cargando ? <EmptyRow colSpan={6} texto="Cargando..." /> : error && parametros.length === 0 ? <EmptyRow colSpan={6} texto={error} /> : parametros.length === 0 ? <EmptyRow colSpan={6} texto="No hay parámetros configurados." /> : parametros.map((parametro) => (
              <tr key={parametro.id} className="hover:bg-slate-50">
                <Td className="font-medium text-slate-800">{parametro.nombre}</Td>
                <Td><code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{parametro.clave}</code></Td>
                <Td className="font-medium">{parametro.valor}</Td><Td>{parametro.unidad ?? "—"}</Td><Td>{parametro.descripcion ?? "—"}</Td>
                <Td><Button variante="secundario" tamano="sm" onClick={() => abrirEdicion(parametro)}><Pencil className="h-4 w-4" /> Editar</Button></Td>
              </tr>
            ))}
          </TBody>
        </Table>
      </Card>
      <Modal abierto={editando !== null} titulo="Editar parámetro" onCerrar={() => setEditando(null)}>
        <form onSubmit={guardar} className="space-y-4">
          <div className="rounded-lg bg-slate-50 p-3"><p className="text-sm font-medium text-slate-800">{editando?.nombre}</p><p className="text-xs text-slate-500">{editando?.descripcion ?? editando?.clave}</p></div>
          <Campo label={`Valor${editando?.unidad ? ` (${editando.unidad})` : ""}`} htmlFor="parametro_valor" requerido><Input id="parametro_valor" type="number" step="0.0001" value={valor} onChange={(e) => setValor(e.target.value)} required /></Campo>
          <div className="flex justify-end gap-2 pt-2"><Button type="button" variante="secundario" onClick={() => setEditando(null)}>Cancelar</Button><Button type="submit" disabled={guardando}>{guardando ? "Guardando..." : "Guardar cambio"}</Button></div>
        </form>
      </Modal>
    </div>
  );
}
