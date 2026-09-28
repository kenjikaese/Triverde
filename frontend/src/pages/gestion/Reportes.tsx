import { useEffect, useState, type FormEvent } from "react";
import { Download, FileDown } from "lucide-react";
import { api } from "@/lib/api";
import type { FormatoReporte, Reporte, TipoReporte } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Button } from "@/components/ui/Button";
import { Table, TBody, Td, Th } from "@/components/ui/Table";

const tiposReporte: Array<{ valor: TipoReporte; etiqueta: string }> = [
  { valor: "recepciones", etiqueta: "Recepciones por período" },
  { valor: "produccion", etiqueta: "Producción" },
  { valor: "ventas_cobros", etiqueta: "Ventas y cobros" },
];

function numero(valor: unknown): string {
  return typeof valor === "number" ? valor.toLocaleString("es-CL") : "0";
}

function seccionesReporte(reporte: Reporte): Array<[string, Array<Record<string, unknown>>]> {
  const contenido = reporte.contenido;
  const nombres = reporte.tipo === "recepciones"
    ? ["por_material", "por_cliente"]
    : reporte.tipo === "produccion" ? ["por_material"] : ["por_cliente", "por_producto"];
  return nombres.map((nombre) => [
    nombre,
    Array.isArray(contenido[nombre]) ? contenido[nombre] as Array<Record<string, unknown>> : [],
  ]);
}

export function Reportes() {
  const [tipo, setTipo] = useState<TipoReporte>("recepciones");
  const [desde, setDesde] = useState("2026-09-01");
  const [hasta, setHasta] = useState("2026-09-30");
  const [formato, setFormato] = useState<FormatoReporte>("pdf");
  const [cliente, setCliente] = useState("");
  const [material, setMaterial] = useState("");
  const [reportes, setReportes] = useState<Reporte[]>([]);
  const [seleccionado, setSeleccionado] = useState<Reporte | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    api.get<Reporte[]>("/reportes/")
      .then((respuesta) => setReportes(respuesta.data))
      .catch(() => setError("No se pudieron cargar los reportes generados."));
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
      setMensaje("Reporte generado correctamente.");
    } catch (err: unknown) {
      const detalle = (err as { response?: { data?: { detail?: string; periodo_fin?: string[] } } }).response?.data;
      setError(detalle?.periodo_fin?.[0] ?? detalle?.detail ?? "No se pudo generar el reporte.");
    } finally {
      setCargando(false);
    }
  }

  async function exportar(reporte: Reporte) {
    setError(null);
    try {
      const respuesta = await api.get(`/reportes/${reporte.id}/exportar/`, { responseType: "blob" });
      const url = URL.createObjectURL(respuesta.data);
      const enlace = document.createElement("a");
      enlace.href = url;
      const extension = reporte.formato === "excel" ? "xlsx" : reporte.formato;
      enlace.download = `reporte-${reporte.id}.${extension}`;
      enlace.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("No se pudo exportar el reporte. Puedes reintentarlo sin generarlo de nuevo.");
    }
  }

  const secciones = seleccionado ? seccionesReporte(seleccionado) : [];

  return (
    <div>
      <PageHeader titulo="Reportes" descripcion="Genera informes operativos y comerciales por período." />
      {mensaje && <div className="mb-4 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800">{mensaje}</div>}
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <Card>
        <CardHeader titulo="Nuevo reporte" descripcion="Selecciona el contenido, rango de fechas y formato de salida." />
        <CardBody>
          <form onSubmit={generar} className="space-y-4">
            <Campo label="Tipo de reporte" htmlFor="reporte_tipo" requerido>
              <Select id="reporte_tipo" value={tipo} onChange={(evento) => setTipo(evento.target.value as TipoReporte)}>
                {tiposReporte.map((opcion) => <option key={opcion.valor} value={opcion.valor}>{opcion.etiqueta}</option>)}
              </Select>
            </Campo>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Campo label="Desde" htmlFor="reporte_desde" requerido><Input id="reporte_desde" type="date" value={desde} onChange={(evento) => setDesde(evento.target.value)} required /></Campo>
              <Campo label="Hasta" htmlFor="reporte_hasta" requerido><Input id="reporte_hasta" type="date" value={hasta} onChange={(evento) => setHasta(evento.target.value)} required /></Campo>
            </div>
            {tipo === "recepciones" && <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Campo label="Cliente (opcional)" htmlFor="reporte_cliente"><Input id="reporte_cliente" type="number" min="1" value={cliente} onChange={(evento) => setCliente(evento.target.value)} /></Campo>
              <Campo label="Material (opcional)" htmlFor="reporte_material"><Input id="reporte_material" type="number" min="1" value={material} onChange={(evento) => setMaterial(evento.target.value)} /></Campo>
            </div>}
            <Campo label="Formato" htmlFor="reporte_formato" requerido>
              <Select id="reporte_formato" value={formato} onChange={(evento) => setFormato(evento.target.value as FormatoReporte)}>
                <option value="pdf">PDF</option><option value="excel">Excel</option><option value="csv">CSV</option>
              </Select>
            </Campo>
            <div className="flex justify-end"><Button type="submit" disabled={cargando}><FileDown className="h-4 w-4" /> {cargando ? "Generando..." : "Generar reporte"}</Button></div>
          </form>
        </CardBody>
      </Card>
      {seleccionado && <Card className="mt-6">
        <CardHeader titulo={`Resultado: ${seleccionado.tipo_display}`} accion={<Button variante="secundario" onClick={() => exportar(seleccionado)}><Download className="h-4 w-4" /> Exportar</Button>} />
        <Table><thead><tr><Th>Agrupación</Th><Th>Detalle</Th><Th>Valores</Th></tr></thead><TBody>
          {secciones.every(([, filas]) => filas.length === 0) ? <tr><td colSpan={3} className="px-4 py-8 text-center text-sm text-slate-500">No hubo actividad en el período seleccionado.</td></tr> : secciones.flatMap(([seccion, filas]) => filas.map((fila, indice) => {
            const nombre = String(fila.material_nombre ?? fila.cliente_nombre ?? fila.producto_nombre ?? "-");
            const valores = Object.entries(fila).filter(([clave]) => !clave.endsWith("_nombre") && clave !== "material" && clave !== "cliente" && clave !== "producto").map(([clave, valor]) => `${clave}: ${numero(valor)}`).join(" · ");
            return <tr key={`${seccion}-${nombre}-${indice}`}><Td>{seccion.replace("por_", "")}</Td><Td>{nombre}</Td><Td>{valores}</Td></tr>;
          }))}
        </TBody></Table>
      </Card>}
      {reportes.length > 0 && <p className="mt-6 text-sm text-slate-500">{reportes.length} reporte(s) generado(s) en esta sesión.</p>}
    </div>
  );
}
