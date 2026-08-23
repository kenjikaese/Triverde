import { useState, type FormEvent } from "react";
import { Plus } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";

// MOCK: datos de ejemplo, sin backend (modulo 9).
const cobrosIniciales = [
  { id: 1, cliente: "Constructora Arrayán", documento: "V-1083", vencimiento: "05-09-2026", monto: 810000, abonado: 0, estado: "Pendiente" },
  { id: 2, cliente: "Paisajismo Sur Ltda.", documento: "V-1082", vencimiento: "02-09-2026", monto: 624000, abonado: 300000, estado: "Pago parcial" },
  { id: 3, cliente: "Vivero Los Aromos", documento: "V-1084", vencimiento: "22-08-2026", monto: 540000, abonado: 540000, estado: "Pagado" },
];
const clp = (valor: number) => `$${valor.toLocaleString("es-CL")}`;

export function Cobros() {
  const [cobros, setCobros] = useState(cobrosIniciales);
  const [cliente, setCliente] = useState("Constructora Arrayán");
  const [monto, setMonto] = useState("");

  function registrar(e: FormEvent) {
    e.preventDefault();
    const valor = Number(monto);
    if (!valor) return;
    setCobros((actuales) => [{ id: Date.now(), cliente, documento: "Cobro manual", vencimiento: "22-08-2026", monto: valor, abonado: valor, estado: "Pagado" }, ...actuales]);
    setMonto("");
  }

  return (
    <div>
      <PageHeader titulo="Cobros" descripcion="Registro de pagos y saldos pendientes por cliente." />
      <Card className="mb-6"><CardHeader titulo="Registrar cobro" /><CardBody><form onSubmit={registrar} className="grid grid-cols-1 items-end gap-4 sm:grid-cols-3"><Campo label="Cliente" htmlFor="cobro_cliente" requerido><Select id="cobro_cliente" value={cliente} onChange={(e) => setCliente(e.target.value)}><option>Constructora Arrayán</option><option>Paisajismo Sur Ltda.</option><option>Vivero Los Aromos</option></Select></Campo><Campo label="Monto recibido (CLP)" htmlFor="cobro_monto" requerido><Input id="cobro_monto" type="number" min="1" value={monto} onChange={(e) => setMonto(e.target.value)} required /></Campo><Button type="submit"><Plus className="h-4 w-4" /> Registrar pago</Button></form></CardBody></Card>
      <Card><Table><thead><tr><Th>Cliente</Th><Th>Documento</Th><Th>Vencimiento</Th><Th>Monto</Th><Th>Abonado</Th><Th>Saldo</Th><Th>Estado</Th></tr></thead><TBody>{cobros.map((cobro) => <tr key={cobro.id} className="hover:bg-slate-50"><Td className="font-medium text-slate-800">{cobro.cliente}</Td><Td>{cobro.documento}</Td><Td>{cobro.vencimiento}</Td><Td>{clp(cobro.monto)}</Td><Td>{clp(cobro.abonado)}</Td><Td>{clp(cobro.monto - cobro.abonado)}</Td><Td><Badge tono={tonoEstado(cobro.estado)}>{cobro.estado}</Badge></Td></tr>)}</TBody></Table></Card>
    </div>
  );
}
