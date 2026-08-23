import { useState, type FormEvent } from "react";
import { CheckCircle2, FileDown } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Button } from "@/components/ui/Button";

// MOCK: datos de ejemplo, sin backend (modulo 10).
const formatos = ["Planilla SINADER (.xlsx)", "Resumen de declaración (.pdf)", "Archivo de respaldo (.csv)"];

export function ExportacionSinader() {
  const [desde, setDesde] = useState("2026-07-01");
  const [hasta, setHasta] = useState("2026-07-31");
  const [formato, setFormato] = useState(formatos[0]);
  const [generado, setGenerado] = useState(false);

  function exportar(e: FormEvent) { e.preventDefault(); setGenerado(true); }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader titulo="Exportación SINADER" descripcion="Prepara la declaración de residuos no peligrosos para el período seleccionado." />
      {generado && <div className="mb-4 flex items-center gap-3 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800"><CheckCircle2 className="h-5 w-5" /> Archivo preparado con 86 recepciones y 1.284,6 m³ declarables.</div>}
      <Card><CardHeader titulo="Datos de la declaración" descripcion="La exportación consolida recepciones aprobadas dentro del rango." /><CardBody><form onSubmit={exportar} className="space-y-4"><div className="grid grid-cols-1 gap-4 sm:grid-cols-2"><Campo label="Desde" htmlFor="sinader_desde" requerido><Input id="sinader_desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} required /></Campo><Campo label="Hasta" htmlFor="sinader_hasta" requerido><Input id="sinader_hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} required /></Campo></div><Campo label="Formato" htmlFor="sinader_formato" requerido><Select id="sinader_formato" value={formato} onChange={(e) => setFormato(e.target.value)}>{formatos.map((opcion) => <option key={opcion}>{opcion}</option>)}</Select></Campo><div className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600"><p className="font-medium text-slate-800">Vista previa del período</p><div className="mt-2 grid grid-cols-2 gap-3"><span>86 recepciones</span><span>1.284,6 m³</span><span>398.220 kg estimados</span><span>7 clientes generadores</span></div></div><div className="flex justify-end"><Button type="submit"><FileDown className="h-4 w-4" /> Generar exportación</Button></div></form></CardBody></Card>
    </div>
  );
}
