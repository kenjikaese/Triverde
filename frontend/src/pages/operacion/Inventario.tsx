import { Boxes, PackageCheck, Scale } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";

// MOCK: datos de ejemplo, sin backend (modulo 5).
const existencias = [
  { material: "Ramas de poda", etapa: "Crudo", volumen_m3: 86.4, peso_kg: 19008, ubicacion: "Patio norte" },
  { material: "Hojas y césped", etapa: "En pila", volumen_m3: 54.2, peso_kg: 18970, ubicacion: "Pila P-024" },
  { material: "Compost maduro", etapa: "Compost", volumen_m3: 31.8, peso_kg: 17490, ubicacion: "Zona de curado" },
  { material: "Compost premium", etapa: "Ensacado", volumen_m3: 12.6, peso_kg: 6930, ubicacion: "Bodega 2" },
  { material: "Troncos y madera limpia", etapa: "Crudo", volumen_m3: 42.0, peso_kg: 16800, ubicacion: "Patio sur" },
];

export function Inventario() {
  const volumenTotal = existencias.reduce((total, item) => total + item.volumen_m3, 0);
  const pesoTotal = existencias.reduce((total, item) => total + item.peso_kg, 0);
  return (
    <div>
      <PageHeader titulo="Inventario" descripcion="Existencias estimadas por material, etapa de proceso y ubicación." />
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card><CardBody className="flex items-center gap-4"><Boxes className="h-8 w-8 text-brand-700" /><div><p className="text-2xl font-semibold text-slate-900">{volumenTotal.toLocaleString("es-CL")} m³</p><p className="text-sm text-slate-500">Volumen disponible</p></div></CardBody></Card>
        <Card><CardBody className="flex items-center gap-4"><Scale className="h-8 w-8 text-sky-700" /><div><p className="text-2xl font-semibold text-slate-900">{(pesoTotal / 1000).toLocaleString("es-CL")} t</p><p className="text-sm text-slate-500">Peso estimado</p></div></CardBody></Card>
        <Card><CardBody className="flex items-center gap-4"><PackageCheck className="h-8 w-8 text-amber-700" /><div><p className="text-2xl font-semibold text-slate-900">12,6 m³</p><p className="text-sm text-slate-500">Producto ensacado</p></div></CardBody></Card>
      </div>
      <Card><Table><thead><tr><Th>Material</Th><Th>Etapa</Th><Th>Volumen</Th><Th>Peso estimado</Th><Th>Ubicación</Th></tr></thead><TBody>{existencias.map((item) => <tr key={`${item.material}-${item.etapa}`} className="hover:bg-slate-50"><Td className="font-medium text-slate-800">{item.material}</Td><Td><Badge tono={tonoEstado(item.etapa)}>{item.etapa}</Badge></Td><Td>{item.volumen_m3.toLocaleString("es-CL")} m³</Td><Td>{item.peso_kg.toLocaleString("es-CL")} kg</Td><Td>{item.ubicacion}</Td></tr>)}</TBody></Table></Card>
    </div>
  );
}
