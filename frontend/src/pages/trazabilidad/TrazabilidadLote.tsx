import { Layers, Package, Truck, Waypoints } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";

// MOCK: datos de ejemplo, sin backend (modulo 9, CU-68). La vista reconstruye
// la cadena Venta -> Pila -> Recepciones de origen; el cableado real toma el
// lote desde /api/v1/ventas/{id}/trazabilidad/.
const lote = {
  venta: "Venta #312",
  cliente: "Áreas Verdes del Sur",
  producto: "Compost premium",
  cantidad: "180 sacos",
  fecha: "24-08-2026",
  pila: "Lote C-118",
  estadoPila: "Valorizado",
};

const recepciones = [
  { referencia: "Recepción #401", cliente: "Forestal Calle Calle", fecha: "02-07-2026", material: "Poda verde", volumen: 42.5 },
  { referencia: "Recepción #404", cliente: "Municipalidad de Valdivia", fecha: "05-07-2026", material: "Ramas secas", volumen: 31.0 },
  { referencia: "Recepción #409", cliente: "Podas Los Ríos", fecha: "09-07-2026", material: "Poda verde", volumen: 28.4 },
  { referencia: "Recepción #415", cliente: "Forestal Calle Calle", fecha: "14-07-2026", material: "Ramas secas", volumen: 19.7 },
];

export function TrazabilidadLote() {
  return (
    <div>
      <PageHeader
        titulo="Trazabilidad de lote entregado"
        descripcion="Cadena de origen de un producto vendido: la pila de la que salió y las recepciones que la compusieron."
      />

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardBody className="flex items-center gap-4">
            <Package className="h-8 w-8 text-brand-700" />
            <div>
              <p className="text-lg font-semibold text-slate-900">{lote.producto}</p>
              <p className="text-sm text-slate-500">{lote.venta} · {lote.cantidad}</p>
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="flex items-center gap-4">
            <Layers className="h-8 w-8 text-amber-700" />
            <div>
              <p className="text-lg font-semibold text-slate-900">{lote.pila}</p>
              <p className="mt-0.5 text-sm text-slate-500">
                Pila de origen · <Badge tono={tonoEstado(lote.estadoPila)}>{lote.estadoPila}</Badge>
              </p>
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="flex items-center gap-4">
            <Truck className="h-8 w-8 text-sky-700" />
            <div>
              <p className="text-lg font-semibold text-slate-900">{recepciones.length} recepciones</p>
              <p className="text-sm text-slate-500">Aportaron material a la pila</p>
            </div>
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader
          titulo="Recepciones que compusieron la pila"
          descripcion={`${lote.pila} · entregado a ${lote.cliente} el ${lote.fecha}`}
          accion={<Waypoints className="h-5 w-5 text-slate-400" />}
        />
        <Table>
          <thead>
            <tr>
              <Th>Recepción</Th>
              <Th>Cliente de origen</Th>
              <Th>Fecha de descarga</Th>
              <Th>Material</Th>
              <Th>Volumen aportado</Th>
            </tr>
          </thead>
          <TBody>
            {recepciones.map((recepcion) => (
              <tr key={recepcion.referencia} className="hover:bg-slate-50">
                <Td className="font-medium text-slate-800">{recepcion.referencia}</Td>
                <Td>{recepcion.cliente}</Td>
                <Td>{recepcion.fecha}</Td>
                <Td>{recepcion.material}</Td>
                <Td className="font-medium text-brand-800">
                  {recepcion.volumen.toLocaleString("es-CL")} m³
                </Td>
              </tr>
            ))}
          </TBody>
        </Table>
      </Card>
    </div>
  );
}
