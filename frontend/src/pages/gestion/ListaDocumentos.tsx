import { Plus } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

// MOCK: datos de ejemplo, sin backend (modulo 12).
const documentos = [
  { codigo: "DOC-AMB-01", tipo: "Resolución sanitaria", nombre: "Autorización planta de valorización", version: "v3", emision: "20-09-2024", vencimiento: "20-09-2026", vigencia: "Por vencer" },
  { codigo: "DOC-MUN-04", tipo: "Patente municipal", nombre: "Patente comercial segundo semestre", version: "2026-2", emision: "01-07-2026", vencimiento: "31-12-2026", vigencia: "Vigente" },
  { codigo: "DOC-PRL-07", tipo: "Prevención de riesgos", nombre: "Procedimiento operación chipeadora", version: "v5", emision: "12-03-2026", vencimiento: "—", vigencia: "Vigente" },
  { codigo: "DOC-AMB-09", tipo: "Declaración", nombre: "Declaración SINADER anual", version: "2025", emision: "18-03-2026", vencimiento: "18-03-2026", vigencia: "Vencido" },
];

export function ListaDocumentos() {
  return (
    <div>
      <PageHeader titulo="Documentos legales" descripcion="Control de versiones y vigencia de permisos, declaraciones y procedimientos." accion={<Button><Plus className="h-4 w-4" /> Nuevo documento</Button>} />
      <Card><Table><thead><tr><Th>Código</Th><Th>Tipo</Th><Th>Documento</Th><Th>Versión</Th><Th>Emisión</Th><Th>Vencimiento</Th><Th>Vigencia</Th></tr></thead><TBody>{documentos.map((documento) => <tr key={documento.codigo} className="hover:bg-slate-50"><Td className="font-medium text-slate-800">{documento.codigo}</Td><Td>{documento.tipo}</Td><Td>{documento.nombre}</Td><Td>{documento.version}</Td><Td>{documento.emision}</Td><Td>{documento.vencimiento}</Td><Td><Badge tono={tonoEstado(documento.vigencia)}>{documento.vigencia}</Badge></Td></tr>)}</TBody></Table></Card>
    </div>
  );
}
