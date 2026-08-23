import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Plus } from "lucide-react";

// MOCK: datos de ejemplo, sin backend (modulo 8).
const maquinaria = [
  { codigo: "MQ-01", nombre: "Chipeadora Vermeer BC1000", tipo: "Chipeadora", horas: 1842, estado: "operativa", ultimo_servicio: "02-08-2026" },
  { codigo: "MQ-02", nombre: "Minicargador Bobcat S590", tipo: "Cargador", horas: 3267, estado: "en mantencion", ultimo_servicio: "18-06-2026" },
  { codigo: "MQ-03", nombre: "Cribadora Komptech Multistar", tipo: "Cribadora", horas: 911, estado: "operativa", ultimo_servicio: "27-07-2026" },
  { codigo: "VH-07", nombre: "Camión tolva Volvo VM", tipo: "Vehículo", horas: 5420, estado: "fuera de servicio", ultimo_servicio: "09-05-2026" },
];

export function ListaMaquinaria() {
  return (
    <div>
      <PageHeader titulo="Maquinaria y flota" descripcion="Activos mantenibles, horas acumuladas y condición actual." accion={<Button><Plus className="h-4 w-4" /> Nuevo equipo</Button>} />
      <Card><Table><thead><tr><Th>Código</Th><Th>Equipo</Th><Th>Tipo</Th><Th>Horas de uso</Th><Th>Último servicio</Th><Th>Estado</Th></tr></thead><TBody>{maquinaria.map((equipo) => <tr key={equipo.codigo} className="hover:bg-slate-50"><Td className="font-medium text-slate-800">{equipo.codigo}</Td><Td>{equipo.nombre}</Td><Td>{equipo.tipo}</Td><Td>{equipo.horas.toLocaleString("es-CL")} h</Td><Td>{equipo.ultimo_servicio}</Td><Td><Badge tono={tonoEstado(equipo.estado)}>{equipo.estado}</Badge></Td></tr>)}</TBody></Table></Card>
    </div>
  );
}
