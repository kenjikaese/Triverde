import { AlertTriangle, CheckCircle2, Clock, ShieldCheck } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";

// MOCK: datos de ejemplo, sin backend (modulo 12, CU-91). El cableado real
// toma el resumen y el detalle desde /api/v1/cumplimiento/tablero/.
const resumen = { vigentes: 9, porVencer: 3, vencidos: 1, sinVigencia: 2 };

const pendientes = [
  { codigo: "DOC-AMB-09", nombre: "Declaración SINADER anual", tipo: "Declaración", vencimiento: "18-03-2026", dias: -182, estado: "Vencido" },
  { codigo: "DOC-AMB-01", nombre: "Autorización planta de valorización", tipo: "Resolución sanitaria", vencimiento: "20-09-2026", dias: 4, estado: "Por vencer" },
  { codigo: "DOC-SEG-02", nombre: "Seguro de responsabilidad civil", tipo: "Seguro", vencimiento: "05-10-2026", dias: 19, estado: "Por vencer" },
  { codigo: "DOC-MUN-04", nombre: "Patente comercial segundo semestre", tipo: "Patente municipal", vencimiento: "31-10-2026", dias: 45, estado: "Por vencer" },
];

export function CumplimientoDocumental() {
  return (
    <div>
      <PageHeader
        titulo="Cumplimiento documental"
        descripcion="Estado de vigencia de los permisos, certificados y seguros de la empresa."
      />

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card>
          <CardBody className="flex items-center gap-4">
            <CheckCircle2 className="h-8 w-8 text-brand-700" />
            <div>
              <p className="text-2xl font-semibold text-slate-900">{resumen.vigentes}</p>
              <p className="text-sm text-slate-500">Vigentes</p>
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="flex items-center gap-4">
            <Clock className="h-8 w-8 text-amber-700" />
            <div>
              <p className="text-2xl font-semibold text-slate-900">{resumen.porVencer}</p>
              <p className="text-sm text-slate-500">Por vencer</p>
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="flex items-center gap-4">
            <AlertTriangle className="h-8 w-8 text-red-700" />
            <div>
              <p className="text-2xl font-semibold text-slate-900">{resumen.vencidos}</p>
              <p className="text-sm text-slate-500">Vencidos</p>
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="flex items-center gap-4">
            <ShieldCheck className="h-8 w-8 text-slate-400" />
            <div>
              <p className="text-2xl font-semibold text-slate-900">{resumen.sinVigencia}</p>
              <p className="text-sm text-slate-500">Sin vigencia definida</p>
            </div>
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader
          titulo="Documentos por vencer y vencidos"
          descripcion="Ordenados por proximidad de vencimiento, para priorizar las renovaciones."
        />
        <Table>
          <thead>
            <tr>
              <Th>Código</Th>
              <Th>Documento</Th>
              <Th>Tipo</Th>
              <Th>Vencimiento</Th>
              <Th>Días</Th>
              <Th>Estado</Th>
            </tr>
          </thead>
          <TBody>
            {pendientes.map((documento) => (
              <tr key={documento.codigo} className="hover:bg-slate-50">
                <Td className="font-medium text-slate-800">{documento.codigo}</Td>
                <Td>{documento.nombre}</Td>
                <Td>{documento.tipo}</Td>
                <Td>{documento.vencimiento}</Td>
                <Td className={documento.dias < 0 ? "font-medium text-red-700" : "text-slate-700"}>
                  {documento.dias < 0
                    ? `${Math.abs(documento.dias)} d vencido`
                    : `${documento.dias} d`}
                </Td>
                <Td><Badge tono={tonoEstado(documento.estado)}>{documento.estado}</Badge></Td>
              </tr>
            ))}
          </TBody>
        </Table>
      </Card>
    </div>
  );
}
