import { Download, FileStack, History } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

// MOCK: datos de ejemplo, sin backend (modulo 12, CU-92). El cableado real
// toma las versiones desde /api/v1/documentos-legales/{id}/historial/.
const documento = {
  codigo: "DOC-AMB-01",
  nombre: "Autorización planta de valorización",
  tipo: "Resolución sanitaria",
  entidad: "SEREMI de Salud",
};

const versiones = [
  { version: "v3", fecha: "20-09-2024", usuario: "Kenji Kimura", estado: "Vigente" },
  { version: "v2", fecha: "12-08-2022", usuario: "Kenji Kimura", estado: "Anterior" },
  { version: "v1", fecha: "03-06-2020", usuario: "José Contreras", estado: "Anterior" },
];

export function HistorialDocumento() {
  return (
    <div>
      <PageHeader
        titulo="Historial de versiones"
        descripcion="Archivos cargados de un documento a lo largo del tiempo, de la versión más reciente a la más antigua."
      />

      <Card className="mb-6">
        <CardBody className="flex items-center gap-4">
          <FileStack className="h-8 w-8 text-brand-700" />
          <div>
            <p className="text-lg font-semibold text-slate-900">{documento.nombre}</p>
            <p className="text-sm text-slate-500">
              {documento.codigo} · {documento.tipo} · {documento.entidad}
            </p>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          titulo="Versiones"
          accion={<History className="h-5 w-5 text-slate-400" />}
        />
        <Table>
          <thead>
            <tr>
              <Th>Versión</Th>
              <Th>Fecha de carga</Th>
              <Th>Cargada por</Th>
              <Th>Estado</Th>
              <Th>Archivo</Th>
            </tr>
          </thead>
          <TBody>
            {versiones.map((version) => (
              <tr key={version.version} className="hover:bg-slate-50">
                <Td className="font-medium text-slate-800">{version.version}</Td>
                <Td>{version.fecha}</Td>
                <Td>{version.usuario}</Td>
                <Td><Badge tono={tonoEstado(version.estado)}>{version.estado}</Badge></Td>
                <Td>
                  <Button variante="fantasma" tamano="sm">
                    <Download className="h-4 w-4" /> PDF
                  </Button>
                </Td>
              </tr>
            ))}
          </TBody>
        </Table>
      </Card>
    </div>
  );
}
