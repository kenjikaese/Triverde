import { useEffect, useMemo, useState, type FormEvent } from "react";
import axios from "axios";
import { Plus, TrendingUp } from "lucide-react";
import { api } from "@/lib/api";
import type {
  ComparacionProyeccion,
  Material,
  Proyeccion,
  TipoProyeccion,
} from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";

// Etiqueta legible para las claves de supuestos y resultados que expone la API.
const ETIQUETAS: Record<string, string> = {
  volumen_entrada_m3: "Volumen de entrada (m³)",
  densidad_kg_m3: "Densidad (kg/m³)",
  factor_reduccion: "Factor de reducción",
  rendimiento_compost: "Rendimiento de compost (m³ compost / m³ entrada)",
  sacos_por_m3: "Sacos por m³",
  precio_saco: "Precio por saco ($)",
  toneladas_entrada: "Toneladas de entrada",
  m3_compost: "Compost (m³)",
  sacos: "Sacos",
  m3_procesado: "Procesado (m³)",
  toneladas: "Toneladas",
  chip_m3: "Chip (m³)",
  m3: "Volumen (m³)",
  ingreso_estimado: "Ingreso estimado ($)",
};

// Supuestos requeridos por tipo (volumen_entrada_m3 aplica a todos). En "semanal"
// densidad y factor se toman del material; el resto se ingresa aquí.
const SUPUESTOS_POR_TIPO: Record<TipoProyeccion, string[]> = {
  mensual: ["volumen_entrada_m3", "densidad_kg_m3", "rendimiento_compost", "sacos_por_m3"],
  semanal: ["volumen_entrada_m3"],
  comercial: ["volumen_entrada_m3", "sacos_por_m3", "precio_saco"],
};

const etiqueta = (clave: string) => ETIQUETAS[clave] ?? clave;

function formatoValor(clave: string, valor: number): string {
  const entero = clave === "sacos";
  const dinero = clave === "ingreso_estimado";
  const n = entero ? Math.round(valor) : valor;
  const texto = n.toLocaleString("es-CL", {
    maximumFractionDigits: entero ? 0 : 2,
  });
  return dinero ? `$${texto}` : texto;
}

function mensajeError(err: unknown): string {
  if (axios.isAxiosError(err) && err.response?.data) {
    const data = err.response.data as Record<string, unknown>;
    const primero = data.supuestos ?? data.material ?? data.detail ?? Object.values(data)[0];
    if (typeof primero === "string") return primero;
    if (Array.isArray(primero) && typeof primero[0] === "string") return primero[0];
  }
  return "No se pudo calcular la proyección.";
}

const FORM_VACIO = {
  tipo: "mensual" as TipoProyeccion,
  periodo_inicio: "",
  periodo_fin: "",
  material: "" as number | "",
  supuestos: {} as Record<string, string>,
};

export function Proyecciones() {
  const [proyecciones, setProyecciones] = useState<Proyeccion[]>([]);
  const [materiales, setMateriales] = useState<Material[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [modal, setModal] = useState(false);
  const [form, setForm] = useState(FORM_VACIO);
  const [guardando, setGuardando] = useState(false);
  const [errorForm, setErrorForm] = useState<string | null>(null);

  const [comparacion, setComparacion] = useState<
    { proyeccion: Proyeccion; datos: ComparacionProyeccion } | null
  >(null);
  const [ajuste, setAjuste] = useState<Proyeccion | null>(null);
  const [ajusteSupuestos, setAjusteSupuestos] = useState<Record<string, string>>({});

  function cargar() {
    setCargando(true);
    api
      .get<Proyeccion[]>("/proyecciones/")
      .then((res) => setProyecciones(res.data))
      .catch(() => setError("No se pudo cargar el historial de proyecciones."))
      .finally(() => setCargando(false));
  }

  useEffect(() => {
    cargar();
    api
      .get<Material[]>("/materiales/")
      .then((res) => setMateriales(res.data))
      .catch(() => setMateriales([]));
  }, []);

  const camposSupuestos = useMemo(() => SUPUESTOS_POR_TIPO[form.tipo], [form.tipo]);

  function abrirNueva() {
    setForm(FORM_VACIO);
    setErrorForm(null);
    setModal(true);
  }

  async function crear(e: FormEvent) {
    e.preventDefault();
    setGuardando(true);
    setErrorForm(null);
    const supuestos: Record<string, string> = {};
    for (const clave of camposSupuestos) {
      if (form.supuestos[clave]) supuestos[clave] = form.supuestos[clave];
    }
    try {
      await api.post("/proyecciones/", {
        tipo: form.tipo,
        periodo_inicio: form.periodo_inicio,
        periodo_fin: form.periodo_fin,
        material: form.tipo === "semanal" ? form.material || null : null,
        supuestos,
      });
      setModal(false);
      cargar();
    } catch (err) {
      setErrorForm(mensajeError(err));
    } finally {
      setGuardando(false);
    }
  }

  async function comparar(proyeccion: Proyeccion) {
    try {
      const res = await api.get<ComparacionProyeccion>(
        `/proyecciones/${proyeccion.id}/comparar/`,
      );
      setComparacion({ proyeccion, datos: res.data });
    } catch {
      setError("No se pudo comparar la proyección con lo real.");
    }
  }

  function abrirAjuste(proyeccion: Proyeccion) {
    const supuestos: Record<string, string> = {};
    for (const [clave, valor] of Object.entries(proyeccion.supuestos)) {
      if (!clave.startsWith("_")) supuestos[clave] = String(valor);
    }
    setAjusteSupuestos(supuestos);
    setAjuste(proyeccion);
  }

  async function guardarAjuste(e: FormEvent) {
    e.preventDefault();
    if (!ajuste) return;
    setGuardando(true);
    try {
      await api.post(`/proyecciones/${ajuste.id}/ajustar/`, { supuestos: ajusteSupuestos });
      setAjuste(null);
      cargar();
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div>
      <PageHeader
        titulo="Proyecciones"
        descripcion="Estimación de producción e ingresos aplicando los parámetros vigentes, y comparación con lo real."
        accion={
          <Button onClick={abrirNueva}>
            <Plus className="h-4 w-4" />
            Nueva proyección
          </Button>
        }
      />

      <Card>
        <Table>
          <thead>
            <tr>
              <Th>Tipo</Th>
              <Th>Período</Th>
              <Th>Material</Th>
              <Th>Resultado</Th>
              <Th>Acciones</Th>
            </tr>
          </thead>
          <TBody>
            {cargando ? (
              <EmptyRow colSpan={5} texto="Cargando..." />
            ) : error ? (
              <EmptyRow colSpan={5} texto={error} />
            ) : proyecciones.length === 0 ? (
              <EmptyRow colSpan={5} texto="Aún no hay proyecciones. Crea la primera." />
            ) : (
              proyecciones.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50">
                  <Td>
                    <Badge tono="azul">{p.tipo_display}</Badge>
                  </Td>
                  <Td className="text-slate-600">
                    {p.periodo_inicio} → {p.periodo_fin}
                  </Td>
                  <Td>{p.material_nombre ?? "—"}</Td>
                  <Td className="text-slate-700">
                    {Object.entries(p.valor_proyectado)
                      .map(([k, v]) => `${etiqueta(k)}: ${formatoValor(k, v)}`)
                      .join(" · ") || "—"}
                  </Td>
                  <Td>
                    <div className="flex gap-2">
                      <Button variante="secundario" onClick={() => comparar(p)}>
                        Comparar
                      </Button>
                      <Button variante="secundario" onClick={() => abrirAjuste(p)}>
                        Ajustar
                      </Button>
                    </div>
                  </Td>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      </Card>

      {/* Nueva proyección */}
      <Modal abierto={modal} titulo="Nueva proyección" onCerrar={() => setModal(false)}>
        <form onSubmit={crear} className="space-y-4">
          <Campo label="Tipo de proyección" htmlFor="tipo" requerido>
            <Select
              id="tipo"
              value={form.tipo}
              onChange={(e) =>
                setForm({ ...form, tipo: e.target.value as TipoProyeccion, supuestos: {} })
              }
            >
              <option value="mensual">Mensual de compost</option>
              <option value="semanal">Semanal por material</option>
              <option value="comercial">Rendimiento comercial</option>
            </Select>
          </Campo>

          <div className="grid grid-cols-2 gap-4">
            <Campo label="Inicio del período" htmlFor="periodo_inicio" requerido>
              <Input
                id="periodo_inicio"
                type="date"
                value={form.periodo_inicio}
                onChange={(e) => setForm({ ...form, periodo_inicio: e.target.value })}
                required
              />
            </Campo>
            <Campo label="Fin del período" htmlFor="periodo_fin" requerido>
              <Input
                id="periodo_fin"
                type="date"
                value={form.periodo_fin}
                onChange={(e) => setForm({ ...form, periodo_fin: e.target.value })}
                required
              />
            </Campo>
          </div>

          {form.tipo === "semanal" && (
            <Campo
              label="Material"
              htmlFor="material"
              requerido
              ayuda="Se aplican su densidad y factor de reducción."
            >
              <Select
                id="material"
                value={form.material}
                onChange={(e) =>
                  setForm({ ...form, material: e.target.value ? Number(e.target.value) : "" })
                }
                required
              >
                <option value="">Selecciona un material…</option>
                {materiales.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.nombre}
                  </option>
                ))}
              </Select>
            </Campo>
          )}

          {camposSupuestos.map((clave) => (
            <Campo key={clave} label={etiqueta(clave)} htmlFor={clave} requerido>
              <Input
                id={clave}
                type="number"
                step="any"
                min="0"
                value={form.supuestos[clave] ?? ""}
                onChange={(e) =>
                  setForm({
                    ...form,
                    supuestos: { ...form.supuestos, [clave]: e.target.value },
                  })
                }
                required
              />
            </Campo>
          ))}

          {errorForm && <p className="text-sm text-red-600">{errorForm}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variante="secundario" onClick={() => setModal(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={guardando}>
              {guardando ? "Calculando..." : "Calcular y guardar"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Comparación con lo real (CU-53) */}
      <Modal
        abierto={comparacion !== null}
        titulo="Comparación con lo real"
        onCerrar={() => setComparacion(null)}
      >
        {comparacion && (
          <div className="space-y-3">
            <p className="text-sm text-slate-600">
              {comparacion.proyeccion.tipo_display} · {comparacion.proyeccion.periodo_inicio} →{" "}
              {comparacion.proyeccion.periodo_fin}
            </p>
            {comparacion.datos.parcial && (
              <div className="flex items-center gap-2 rounded-md bg-amber-50 p-2 text-sm text-amber-800">
                <TrendingUp className="h-4 w-4" />
                El período aún no termina: la comparación es parcial.
              </div>
            )}
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-md border border-slate-200 p-3">
                <p className="text-slate-500">Proyectado</p>
                <p className="text-lg font-semibold">{comparacion.datos.proyectado_m3} m³</p>
              </div>
              <div className="rounded-md border border-slate-200 p-3">
                <p className="text-slate-500">Real</p>
                <p className="text-lg font-semibold">
                  {comparacion.datos.real_m3 === null ? "Sin datos" : `${comparacion.datos.real_m3} m³`}
                </p>
              </div>
            </div>
            {comparacion.datos.desviacion_m3 !== null && (
              <p className="text-sm text-slate-700">
                Desviación: <span className="font-medium">{comparacion.datos.desviacion_m3} m³</span>
                {comparacion.datos.desviacion_pct !== null &&
                  ` (${comparacion.datos.desviacion_pct} %)`}
              </p>
            )}
            <div className="flex justify-end pt-2">
              <Button variante="secundario" onClick={() => setComparacion(null)}>
                Cerrar
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Ajustar supuestos (CU-54) */}
      <Modal
        abierto={ajuste !== null}
        titulo="Ajustar supuestos del escenario"
        onCerrar={() => setAjuste(null)}
      >
        {ajuste && (
          <form onSubmit={guardarAjuste} className="space-y-4">
            <p className="text-sm text-slate-600">
              Recalcula esta proyección con nuevos supuestos sin cambiar los parámetros del sistema.
            </p>
            {Object.keys(ajusteSupuestos).map((clave) => (
              <Campo key={clave} label={etiqueta(clave)} htmlFor={`aj-${clave}`}>
                <Input
                  id={`aj-${clave}`}
                  type="number"
                  step="any"
                  value={ajusteSupuestos[clave]}
                  onChange={(e) =>
                    setAjusteSupuestos({ ...ajusteSupuestos, [clave]: e.target.value })
                  }
                />
              </Campo>
            ))}
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variante="secundario" onClick={() => setAjuste(null)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={guardando}>
                {guardando ? "Recalculando..." : "Recalcular"}
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
