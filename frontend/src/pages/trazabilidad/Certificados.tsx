import { Download, FileCheck2 } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

// MOCK: datos de ejemplo, sin backend (modulo 10).
const certificados = [
  { folio: "CTR-2026-0418", tipo: "Descarga individual", referencia: "Recepción #418", cliente: "Forestal Calle Calle", fecha: "22-08-2026", estado: "Emitido" },
  { folio: "CTR-2026-0417", tipo: "Descarga individual", referencia: "Recepción #417", cliente: "Municipalidad de Valdivia", fecha: "21-08-2026", estado: "Emitido" },
  { folio: "CTR-2026-008", tipo: "Consolidado mensual", referencia: "Julio 2026", cliente: "Áreas Verdes del Sur", fecha: "02-08-2026", estado: "Firmado" },
  { folio: "CTR-2026-0416", tipo: "Descarga individual", referencia: "Recepción #416", cliente: "Podas Los Ríos", fecha: "19-08-2026", estado: "Borrador" },
];

export function Certificados() {
  return (
    <div>
      <PageHeader titulo="Certificados de trazabilidad" descripcion="Respaldo del ingreso y valorización de residuos vegetales." accion={<Button><FileCheck2 className="h-4 w-4" /> Generar consolidado</Button>} />
      <Card><Table><thead><tr><Th>Folio</Th><Th>Tipo</Th><Th>Referencia</Th><Th>Cliente</Th><Th>Fecha</Th><Th>Estado</Th><Th>Archivo</Th></tr></thead><TBody>{certificados.map((certificado) => <tr key={certificado.folio} className="hover:bg-slate-50"><Td className="font-medium text-slate-800">{certificado.folio}</Td><Td>{certificado.tipo}</Td><Td>{certificado.referencia}</Td><Td>{certificado.cliente}</Td><Td>{certificado.fecha}</Td><Td><Badge tono={tonoEstado(certificado.estado)}>{certificado.estado}</Badge></Td><Td><Button variante="fantasma" tamano="sm"><Download className="h-4 w-4" /> PDF</Button></Td></tr>)}</TBody></Table></Card>
    </div>
  );
}
