import { useEffect, useState, type FormEvent } from "react";
import { Download, Eye, FileDown } from "lucide-react";
import { api } from "@/lib/api";
import type { Cliente, FormatoReporte, Material, Reporte, TipoReporte } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Button } from "@/components/ui/Button";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { cantidad, clp, fecha as formatoFecha, periodoVigente } from "@/lib/formato";
import { mensajeDeError } from "@/lib/errores";

// V_Reportes (CU-73 a CU-76). El servidor agrega los datos del periodo y guarda
// el resultado; la vista solo lo presenta y pide la exportacion del reporte ya
// generado, en el formato que se elija, sin volver a calcularlo.

const tiposReporte: Array<{ valor: TipoReporte; etiqueta: string }> = [
  { valor: "recepciones", etiqueta: "Recepciones por período" },
  { valor: "produccion", etiqueta: "Producción" },
  { valor: "ventas_cobros", etiqueta: "Ventas y cobros" },
];

const formatos: Array<{ valor: FormatoReporte; etiqueta: string; extension: string }> = [
  { valor: "pdf", etiqueta: "PDF", extension: "pdf" },
  { valor: "excel", etiqueta: "Excel", extension: "xlsx" },
  { valor: "csv", etiqueta: "CSV", extension: "csv" },
];

type Fila = Record<string, unknown>;

interface Columna {
  clave: string;
  titulo: string;
  formato: (valor: unknown) => string;
}

interface Seccion {
  clave: string;
  titulo: string;
  columnas: Columna[];
}

const nombre = (valor: unknown) => String(valor ?? "—");
const m3 = (valor: unknown) => `${cantidad(valor as number)} m³`;
const kg = (valor: unknown) => `${cantidad(valor as number)} kg`;
const pesos = (valor: unknown) => clp(valor as number);

// Columnas de cada seccion segun el tipo; las claves son las del `contenido`
// que arma el servidor.
const seccionesPorTipo: Record<TipoReporte, Seccion[]> = {
  recepciones: [
    { clave: "por_material", titulo: "Por material", columnas: [
      { clave: "material_nombre", titulo: "Material", formato: nombre },
      { clave: "volumen_m3", titulo: "Volumen", formato: m3 },
      { clave: "peso_kg", titulo: "Peso", formato: kg },
    ] },
    { clave: "por_cliente", titulo: "Por cliente", columnas: [
      { clave: "cliente_nombre", titulo: "Cliente", formato: nombre },
      { clave: "volumen_m3", titulo: "Volumen", formato: m3 },
      { clave: "peso_kg", titulo: "Peso", formato: kg },
    ] },
  ],
  produccion: [
    { clave: "por_material", titulo: "Por material", columnas: [
      { clave: "material_nombre", titulo: "Material", formato: nombre },
      { clave: "procesado_m3", titulo: "Procesado", formato: m3 },
      { clave: "en_curso_m3", titulo: "En curso", formato: m3 },
      { clave: "inventario_resultante_m3", titulo: "Inventario actual", formato: m3 },
    ] },
  ],
  ventas_cobros: [
    { clave: "por_cliente", titulo: "Por cliente", columnas: [
      { clave: "cliente_nombre", titulo: "Cliente", formato: nombre },
      { clave: "vendido", titulo: "Vendido", formato: pesos },
      { clave: "cobrado", titulo: "Cobrado", formato: pesos },
      { clave: "pendiente", titulo: "Pendiente", formato: pesos },
    ] },
    { clave: "por_producto", titulo: "Por producto", columnas: [
      { clave: "producto_nombre", titulo: "Producto", formato: nombre },
      { clave: "vendido", titulo: "Vendido", formato: pesos },
      { clave: "cobrado", titulo: "Cobrado", formato: pesos },
      { clave: "pendiente", titulo: "Pendiente", formato: pesos },
    ] },
  ],
};

const totalesPorTipo: Record<TipoReporte, Columna[]> = {
  recepciones: [
    { clave: "volumen_m3", titulo: "Volumen recibido", formato: m3 },
    { clave: "peso_kg", titulo: "Peso recibido", formato: kg },
  ],
  produccion: [
    { clave: "procesado_m3", titulo: "Procesado", formato: m3 },
    { clave: "en_curso_m3", titulo: "En curso", formato: m3 },
  ],
  ventas_cobros: [
    { clave: "vendido", titulo: "Vendido", formato: pesos },
    { clave: "cobrado", titulo: "Cobrado", formato: pesos },
    { clave: "pendiente", titulo: "Pendiente", formato: pesos },
  ],
};

function filasDe(reporte: Reporte, seccion: string): Fila[] {
  const filas = reporte.contenido[seccion];
  return Array.isArray(filas) ? (filas as Fila[]) : [];
}

function filtrosDe(reporte: Reporte): string | null {
  const filtros = reporte.contenido.filtros as Record<string, string> | undefined;
  if (!filtros || Object.keys(filtros).length === 0) return null;
  return Object.entries(filtros).map(([clave, valor]) => `${clave}: ${valor}`).join(" · ");
}

export function Reportes() {
  const periodo = periodoVigente();
  const [tipo, setTipo] = useState<TipoReporte>("recepciones");
  const [desde, setDesde] = useState(periodo.desde);
  const [hasta, setHasta] = useState(periodo.hasta);
  const [formato, setFormato] = useState<FormatoReporte>("pdf");
  const [cliente, setCliente] = useState("");
  const [material, setMaterial] = useState("");
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [materiales, setMateriales] = useState<Material[]>([]);
  const [reportes, setReportes] = useState<Reporte[]>([]);
  const [seleccionado, setSeleccionado] = useState<Reporte | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    api.get<Reporte[]>("/reportes/")
      .then((res) => setReportes(res.data))
      .catch((err) => setError(mensajeDeError(err, "No se pudieron cargar los reportes generados.")));
    api.get<Cliente[]>("/clientes/")
      .then((res) => setClientes(res.data))
      .catch((err) => setError(mensajeDeError(err, "No se pudo cargar los clientes.")));
    api.get<Material[]>("/materiales/")
      .then((res) => setMateriales(res.data))
      .catch((err) => setError(mensajeDeError(err, "No se pudo cargar los materiales.")));
  }, []);

  async function generar(evento: FormEvent) {
    evento.preventDefault();
    setCargando(true);
    setMensaje(null);
    setError(null);
    try {
      const respuesta = await api.post<Reporte>("/reportes/", {
        tipo,
        periodo_inicio: desde,
        periodo_fin: hasta,
        formato,
        ...(tipo === "recepciones" && cliente ? { cliente: Number(cliente) } : {}),
        ...(tipo === "recepciones" && material ? { material: Number(material) } : {}),
      });
      setSeleccionado(respuesta.data);
      setReportes((anteriores) => [respuesta.data, ...anteriores]);
      setMensaje("Reporte generado. Puedes exportarlo en el formato que necesites.");
    } catch (err: unknown) {
      setError(mensajeDeError(err, "No se pudo generar el reporte."));
    } finally {
      setCargando(false);
    }
  }

  async function exportar(reporte: Reporte, formatoSalida: FormatoReporte = reporte.formato) {
    setError(null);
    try {
      const respuesta = await api.get(`/reportes/${reporte.id}/exportar/`, {
        params: { formato: formatoSalida },
        responseType: "blob",
      });
      const url = URL.createObjectURL(respuesta.data);
      const enlace = document.createElement("a");
      enlace.href = url;
      const extension = formatos.find((f) => f.valor === formatoSalida)?.extension ?? formatoSalida;
      enlace.download = `reporte-${reporte.id}.${extension}`;
      enlace.click();
      URL.revokeObjectURL(url);
    } catch {
      // El reporte queda guardado: se puede reintentar sin generarlo de nuevo.
      setError("No se pudo exportar el reporte. Puedes reintentarlo sin generarlo de nuevo.");
    }
  }

  const totales = (seleccionado?.contenido.totales ?? {}) as Fila;
  const filtros = seleccionado ? filtrosDe(seleccionado) : null;

  return (
    <div>
      <PageHeader titulo="Reportes" descripcion="Genera informes operativos y comerciales por período." />
      {mensaje && <div className="mb-4 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800">{mensaje}</div>}
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <Card>
        <CardHeader titulo="Nuevo reporte" descripcion="Selecciona el contenido, el rango de fechas y el formato de salida." />
        <CardBody>
          <form onSubmit={generar} className="space-y-4">
            <Campo label="Tipo de reporte" htmlFor="reporte_tipo" requerido>
              <Select id="reporte_tipo" value={tipo} onChange={(e) => setTipo(e.target.value as TipoReporte)}>
                {tiposReporte.map((opcion) => <option key={opcion.valor} value={opcion.valor}>{opcion.etiqueta}</option>)}
              </Select>
            </Campo>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Campo label="Desde" htmlFor="reporte_desde" requerido>
                <Input id="reporte_desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} required />
              </Campo>
              <Campo label="Hasta" htmlFor="reporte_hasta" requerido>
                <Input id="reporte_hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} required />
              </Campo>
            </div>
            {tipo === "recepciones" && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Campo label="Cliente" htmlFor="reporte_cliente">
                  <Select id="reporte_cliente" value={cliente} onChange={(e) => setCliente(e.target.value)}>
                    <option value="">Todos los clientes</option>
                    {clientes.map((c) => <option key={c.id} value={c.id}>{c.razon_social}</option>)}
                  </Select>
                </Campo>
                <Campo label="Material" htmlFor="reporte_material">
                  <Select id="reporte_material" value={material} onChange={(e) => setMaterial(e.target.value)}>
                    <option value="">Todos los materiales</option>
                    {materiales.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}
                  </Select>
                </Campo>
              </div>
            )}
            <Campo label="Formato" htmlFor="reporte_formato" requerido>
              <Select id="reporte_formato" value={formato} onChange={(e) => setFormato(e.target.value as FormatoReporte)}>
                {formatos.map((f) => <option key={f.valor} value={f.valor}>{f.etiqueta}</option>)}
              </Select>
            </Campo>
            <div className="flex justify-end">
              <Button type="submit" disabled={cargando}>
                <FileDown className="h-4 w-4" /> {cargando ? "Generando..." : "Generar reporte"}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>

      {seleccionado && (
        <Card className="mt-6">
          <CardHeader
            titulo={seleccionado.tipo_display}
            descripcion={`Período ${formatoFecha(seleccionado.periodo_inicio)} a ${formatoFecha(seleccionado.periodo_fin)}${filtros ? ` · ${filtros}` : ""}`}
            accion={
              <div className="flex flex-wrap gap-2">
                {formatos.map((f) => (
                  <Button key={f.valor} variante="secundario" tamano="sm" onClick={() => exportar(seleccionado, f.valor)}>
                    <Download className="h-4 w-4" /> {f.etiqueta}
                  </Button>
                ))}
              </div>
            }
          />
          <CardBody>
            <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
              {totalesPorTipo[seleccionado.tipo].map((t) => (
                <div key={t.clave} className="rounded-lg bg-slate-50 px-4 py-3">
                  <p className="text-sm text-slate-500">{t.titulo}</p>
                  <p className="text-xl font-semibold text-slate-900">{t.formato(totales[t.clave] ?? 0)}</p>
                </div>
              ))}
            </div>
            {seccionesPorTipo[seleccionado.tipo].map((seccion) => {
              const filas = filasDe(seleccionado, seccion.clave);
              return (
                <div key={seccion.clave} className="mb-6 last:mb-0">
                  <h4 className="mb-2 text-sm font-semibold text-slate-700">{seccion.titulo}</h4>
                  <Table>
                    <thead>
                      <tr>{seccion.columnas.map((c) => <Th key={c.clave}>{c.titulo}</Th>)}</tr>
                    </thead>
                    <TBody>
                      {filas.length === 0 ? (
                        <EmptyRow colSpan={seccion.columnas.length} texto="Sin actividad en el período." />
                      ) : (
                        filas.map((fila, indice) => (
                          <tr key={indice}>
                            {seccion.columnas.map((c) => <Td key={c.clave}>{c.formato(fila[c.clave])}</Td>)}
                          </tr>
                        ))
                      )}
                    </TBody>
                  </Table>
                </div>
              );
            })}
          </CardBody>
        </Card>
      )}

      <Card className="mt-6">
        <CardHeader titulo="Reportes generados" descripcion="Cada reporte guarda su resultado: se puede volver a ver o exportar sin recalcularlo." />
        <Table>
          <thead>
            <tr><Th>Generado</Th><Th>Tipo</Th><Th>Período</Th><Th>Formato</Th><Th>Acciones</Th></tr>
          </thead>
          <TBody>
            {reportes.length === 0 ? (
              <EmptyRow colSpan={5} texto="Todavía no se ha generado ningún reporte." />
            ) : (
              reportes.map((reporte) => (
                <tr key={reporte.id} className="hover:bg-slate-50">
                  <Td>{formatoFecha(reporte.fecha_generado.slice(0, 10))}</Td>
                  <Td>{reporte.tipo_display}</Td>
                  <Td>{formatoFecha(reporte.periodo_inicio)} a {formatoFecha(reporte.periodo_fin)}</Td>
                  <Td>{formatos.find((f) => f.valor === reporte.formato)?.etiqueta ?? reporte.formato}</Td>
                  <Td>
                    <div className="flex gap-2">
                      <Button variante="fantasma" tamano="sm" onClick={() => setSeleccionado(reporte)}>
                        <Eye className="h-4 w-4" /> Ver
                      </Button>
                      <Button variante="fantasma" tamano="sm" onClick={() => exportar(reporte)}>
                        <Download className="h-4 w-4" /> Exportar
                      </Button>
                    </div>
                  </Td>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      </Card>
    </div>
  );
}
