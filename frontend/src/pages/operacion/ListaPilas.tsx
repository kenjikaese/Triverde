import { CalendarDays, Layers, Plus } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

// MOCK: datos de ejemplo, sin backend (modulo 6).
const pilas = [
  { codigo: "P-024", inicio: "05-08-2026", etapa: "Termofílica", volumen: 54.2, dias: 17, temperatura: 61 },
  { codigo: "P-023", inicio: "18-07-2026", etapa: "En maduración", volumen: 47.8, dias: 35, temperatura: 43 },
  { codigo: "P-022", inicio: "02-06-2026", etapa: "Curado", volumen: 39.5, dias: 81, temperatura: 27 },
  { codigo: "P-021", inicio: "12-05-2026", etapa: "Lista para cosecha", volumen: 32.1, dias: 102, temperatura: 22 },
];

export function ListaPilas() {
  return (
    <div>
      <PageHeader titulo="Pilas de compostaje" descripcion="Seguimiento de ciclos activos, volumen y madurez del compost." accion={<Button><Plus className="h-4 w-4" /> Nueva pila</Button>} />
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card><CardBody className="flex items-center gap-4"><Layers className="h-8 w-8 text-brand-700" /><div><p className="text-2xl font-semibold text-slate-900">4</p><p className="text-sm text-slate-500">Pilas activas</p></div></CardBody></Card>
        <Card><CardBody><p className="text-2xl font-semibold text-slate-900">173,6 m³</p><p className="text-sm text-slate-500">Volumen en proceso</p></CardBody></Card>
        <Card><CardBody className="flex items-center gap-4"><CalendarDays className="h-8 w-8 text-amber-700" /><div><p className="text-2xl font-semibold text-slate-900">1</p><p className="text-sm text-slate-500">Lista para cosecha</p></div></CardBody></Card>
      </div>
      <Card><Table><thead><tr><Th>Código</Th><Th>Fecha inicio</Th><Th>Etapa</Th><Th>Volumen</Th><Th>Días</Th><Th>Temperatura</Th></tr></thead><TBody>{pilas.map((pila) => <tr key={pila.codigo} className="hover:bg-slate-50"><Td className="font-medium text-slate-800">{pila.codigo}</Td><Td>{pila.inicio}</Td><Td><Badge tono={tonoEstado(pila.etapa)}>{pila.etapa}</Badge></Td><Td>{pila.volumen.toLocaleString("es-CL")} m³</Td><Td>{pila.dias}</Td><Td>{pila.temperatura} °C</Td></tr>)}</TBody></Table></Card>
    </div>
  );
}
