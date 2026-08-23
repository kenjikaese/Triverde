import { Plus } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

// MOCK: datos de ejemplo, sin backend (modulo 9).
const ventas = [
  { folio: "V-1084", fecha: "22-08-2026", cliente: "Vivero Los Aromos", producto: "Compost premium 40 L", cantidad: "120 sacos", monto: 540000, pago: "Pagada" },
  { folio: "V-1083", fecha: "21-08-2026", cliente: "Constructora Arrayán", producto: "Mulch de corteza", cantidad: "18 m³", monto: 810000, pago: "Pendiente" },
  { folio: "V-1082", fecha: "19-08-2026", cliente: "Paisajismo Sur Ltda.", producto: "Chip decorativo", cantidad: "12 m³", monto: 624000, pago: "Pago parcial" },
  { folio: "V-1081", fecha: "16-08-2026", cliente: "Municipalidad de Paillaco", producto: "Compost a granel", cantidad: "30 m³", monto: 990000, pago: "Pagada" },
];
const clp = (valor: number) => `$${valor.toLocaleString("es-CL")}`;

export function ListaVentas() {
  return (
    <div>
      <PageHeader titulo="Ventas" descripcion="Ventas de productos terminados y seguimiento de pago." accion={<Button><Plus className="h-4 w-4" /> Nueva venta</Button>} />
      <Card><Table><thead><tr><Th>Folio</Th><Th>Fecha</Th><Th>Cliente</Th><Th>Producto</Th><Th>Cantidad</Th><Th>Monto</Th><Th>Pago</Th></tr></thead><TBody>{ventas.map((venta) => <tr key={venta.folio} className="hover:bg-slate-50"><Td className="font-medium text-slate-800">{venta.folio}</Td><Td>{venta.fecha}</Td><Td>{venta.cliente}</Td><Td>{venta.producto}</Td><Td>{venta.cantidad}</Td><Td className="font-medium">{clp(venta.monto)}</Td><Td><Badge tono={tonoEstado(venta.pago)}>{venta.pago}</Badge></Td></tr>)}</TBody></Table></Card>
    </div>
  );
}
