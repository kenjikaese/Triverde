import { Boxes, TrendingUp, Wheat } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";

// MOCK: datos de ejemplo, sin backend (modulo 11).
const meses = [
  { mes: "Septiembre 2026", ingreso: 438, procesado: 401, compost: 151, rendimiento: "37,7 %" },
  { mes: "Octubre 2026", ingreso: 472, procesado: 449, compost: 169, rendimiento: "37,6 %" },
  { mes: "Noviembre 2026", ingreso: 510, procesado: 481, compost: 183, rendimiento: "38,0 %" },
  { mes: "Diciembre 2026", ingreso: 556, procesado: 520, compost: 198, rendimiento: "38,1 %" },
];

export function Proyecciones() {
  return (
    <div>
      <PageHeader titulo="Proyecciones" descripcion="Estimación mensual de recepción, proceso y producción de compost." />
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3"><Card><CardBody className="flex items-center gap-4"><TrendingUp className="h-8 w-8 text-brand-700" /><div><p className="text-2xl font-semibold text-slate-900">1.976 m³</p><p className="text-sm text-slate-500">Ingreso proyectado</p></div></CardBody></Card><Card><CardBody className="flex items-center gap-4"><Boxes className="h-8 w-8 text-sky-700" /><div><p className="text-2xl font-semibold text-slate-900">1.851 m³</p><p className="text-sm text-slate-500">Volumen a procesar</p></div></CardBody></Card><Card><CardBody className="flex items-center gap-4"><Wheat className="h-8 w-8 text-amber-700" /><div><p className="text-2xl font-semibold text-slate-900">701 m³</p><p className="text-sm text-slate-500">Compost esperado</p></div></CardBody></Card></div>
      <Card><CardHeader titulo="Proyección de los próximos cuatro meses" descripcion="Escenario base según tendencia reciente y rendimiento promedio." /><Table><thead><tr><Th>Mes</Th><Th>Ingreso estimado</Th><Th>Volumen procesado</Th><Th>Compost producido</Th><Th>Rendimiento</Th></tr></thead><TBody>{meses.map((mes) => <tr key={mes.mes}><Td className="font-medium text-slate-800">{mes.mes}</Td><Td>{mes.ingreso} m³</Td><Td>{mes.procesado} m³</Td><Td>{mes.compost} m³</Td><Td className="font-medium text-brand-800">{mes.rendimiento}</Td></tr>)}</TBody></Table></Card>
    </div>
  );
}
