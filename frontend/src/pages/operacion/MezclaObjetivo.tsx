import { CheckCircle2, FlaskConical, Target } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

// MOCK: datos de ejemplo, sin backend (modulo 6).
const aportes = [
  { material: "Ramas trituradas", categoria: "Seca", disponible: 34.0, aporte: 18.0, proporcion: "45 %" },
  { material: "Hojas y césped", categoria: "Verde", disponible: 26.5, aporte: 14.0, proporcion: "35 %" },
  { material: "Restos de feria", categoria: "Verde", disponible: 12.8, aporte: 8.0, proporcion: "20 %" },
];

export function MezclaObjetivo() {
  return (
    <div>
      <PageHeader titulo="Mezcla objetivo" descripcion="Combinación sugerida para alcanzar una relación carbono/nitrógeno equilibrada." accion={<Button><FlaskConical className="h-4 w-4" /> Recalcular mezcla</Button>} />
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card><CardBody><p className="text-sm text-slate-500">Relación C/N estimada</p><p className="mt-1 text-3xl font-semibold text-slate-900">28:1</p><Badge tono="verde">Dentro del objetivo</Badge></CardBody></Card>
        <Card><CardBody><p className="text-sm text-slate-500">Volumen de mezcla</p><p className="mt-1 text-3xl font-semibold text-slate-900">40,0 m³</p><p className="text-xs text-slate-500">Rendimiento estimado: 21,6 m³</p></CardBody></Card>
        <Card><CardBody className="flex items-start gap-3"><Target className="mt-1 h-7 w-7 text-brand-700" /><div><p className="font-semibold text-slate-900">Destino sugerido</p><p className="text-sm text-slate-600">Nueva pila P-025 · Sector B</p></div></CardBody></Card>
      </div>
      <Card><CardHeader titulo="Aporte por material" descripcion="Propuesta basada en existencias disponibles." /><Table><thead><tr><Th>Material</Th><Th>Categoría</Th><Th>Disponible</Th><Th>Aporte sugerido</Th><Th>Proporción</Th></tr></thead><TBody>{aportes.map((aporte) => <tr key={aporte.material}><Td className="font-medium text-slate-800">{aporte.material}</Td><Td><Badge tono={aporte.categoria === "Verde" ? "verde" : "ambar"}>{aporte.categoria}</Badge></Td><Td>{aporte.disponible.toLocaleString("es-CL")} m³</Td><Td>{aporte.aporte.toLocaleString("es-CL")} m³</Td><Td>{aporte.proporcion}</Td></tr>)}</TBody></Table></Card>
      <div className="mt-4 flex items-start gap-3 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800"><CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" /><p>La mezcla cumple la relación objetivo. Humedecer durante la conformación y registrar temperatura a las 24 horas.</p></div>
    </div>
  );
}
