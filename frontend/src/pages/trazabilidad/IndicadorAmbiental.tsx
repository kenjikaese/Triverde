import { Leaf, Recycle, Truck } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";

// MOCK: datos de ejemplo, sin backend (modulo 10).
const impactos = [
  { referencia: "P-024", origen: "Forestal Calle Calle", volumen: 54.2, camiones: 3, co2: 8.13, estado: "En proceso" },
  { referencia: "P-023", origen: "Municipalidad de Valdivia", volumen: 47.8, camiones: 4, co2: 7.17, estado: "En proceso" },
  { referencia: "Lote C-118", origen: "Consolidado julio", volumen: 121.6, camiones: 9, co2: 18.24, estado: "Valorizado" },
  { referencia: "Lote C-117", origen: "Consolidado junio", volumen: 104.3, camiones: 8, co2: 15.65, estado: "Valorizado" },
];

export function IndicadorAmbiental() {
  return (
    <div>
      <PageHeader titulo="Indicador ambiental" descripcion="Impacto estimado por desvío de residuos vegetales desde disposición final." />
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3"><Card><CardBody className="flex items-center gap-4"><Leaf className="h-8 w-8 text-brand-700" /><div><p className="text-2xl font-semibold text-slate-900">49,19 t</p><p className="text-sm text-slate-500">CO₂e evitado</p></div></CardBody></Card><Card><CardBody className="flex items-center gap-4"><Truck className="h-8 w-8 text-sky-700" /><div><p className="text-2xl font-semibold text-slate-900">24</p><p className="text-sm text-slate-500">Camiones valorizados</p></div></CardBody></Card><Card><CardBody className="flex items-center gap-4"><Recycle className="h-8 w-8 text-amber-700" /><div><p className="text-2xl font-semibold text-slate-900">327,9 m³</p><p className="text-sm text-slate-500">Material recuperado</p></div></CardBody></Card></div>
      <Card><CardHeader titulo="Impacto por lote o pila" descripcion="Cálculo referencial según factor de conversión configurado." /><Table><thead><tr><Th>Referencia</Th><Th>Origen</Th><Th>Volumen</Th><Th>Camiones</Th><Th>CO₂e evitado</Th><Th>Estado</Th></tr></thead><TBody>{impactos.map((impacto) => <tr key={impacto.referencia}><Td className="font-medium text-slate-800">{impacto.referencia}</Td><Td>{impacto.origen}</Td><Td>{impacto.volumen.toLocaleString("es-CL")} m³</Td><Td>{impacto.camiones}</Td><Td className="font-medium text-brand-800">{impacto.co2.toLocaleString("es-CL")} t</Td><Td><Badge tono={tonoEstado(impacto.estado)}>{impacto.estado}</Badge></Td></tr>)}</TBody></Table></Card>
    </div>
  );
}
