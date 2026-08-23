import { useState, type FormEvent } from "react";
import { FileDown } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Button } from "@/components/ui/Button";

// MOCK: datos de ejemplo, sin backend (modulo 12).
const tiposReporte = ["Recepciones y materiales", "Inventario y producción", "Ventas y cobros", "Indicadores ambientales", "Mantenciones de equipos"];

export function Reportes() {
  const [tipo, setTipo] = useState(tiposReporte[0]);
  const [desde, setDesde] = useState("2026-08-01");
  const [hasta, setHasta] = useState("2026-08-22");
  const [formato, setFormato] = useState("PDF");
  const [mensaje, setMensaje] = useState<string | null>(null);

  function generar(e: FormEvent) { e.preventDefault(); setMensaje(`Reporte “${tipo}” preparado para el período ${desde} a ${hasta}.`); }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader titulo="Reportes" descripcion="Genera informes operativos, comerciales y ambientales por período." />
      {mensaje && <div className="mb-4 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800">{mensaje}</div>}
      <Card><CardHeader titulo="Nuevo reporte" descripcion="Selecciona el contenido, rango de fechas y formato de salida." /><CardBody><form onSubmit={generar} className="space-y-4"><Campo label="Tipo de reporte" htmlFor="reporte_tipo" requerido><Select id="reporte_tipo" value={tipo} onChange={(e) => setTipo(e.target.value)}>{tiposReporte.map((opcion) => <option key={opcion}>{opcion}</option>)}</Select></Campo><div className="grid grid-cols-1 gap-4 sm:grid-cols-2"><Campo label="Desde" htmlFor="reporte_desde" requerido><Input id="reporte_desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} required /></Campo><Campo label="Hasta" htmlFor="reporte_hasta" requerido><Input id="reporte_hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} required /></Campo></div><Campo label="Formato" htmlFor="reporte_formato" requerido><Select id="reporte_formato" value={formato} onChange={(e) => setFormato(e.target.value)}><option>PDF</option><option>Excel</option><option>CSV</option></Select></Campo><div className="flex justify-end"><Button type="submit"><FileDown className="h-4 w-4" /> Generar reporte {formato}</Button></div></form></CardBody></Card>
    </div>
  );
}
