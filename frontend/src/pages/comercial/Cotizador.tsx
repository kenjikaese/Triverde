import { useState, type FormEvent } from "react";
import { Calculator, MapPin, Truck } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Button } from "@/components/ui/Button";

// MOCK: datos de ejemplo, sin backend (modulo 9).
const tarifasBase = [
  { tramo: "Hasta 20 m³", base: 165000 },
  { tramo: "20 a 40 m³", base: 245000 },
  { tramo: "Más de 40 m³", base: 335000 },
];

const clp = (valor: number) => `$${Math.round(valor).toLocaleString("es-CL")}`;

export function Cotizador() {
  const [km, setKm] = useState("35");
  const [tramo, setTramo] = useState("1");
  const [viajes, setViajes] = useState("1");
  const [resultado, setResultado] = useState<number | null>(null);

  function cotizar(e: FormEvent) {
    e.preventDefault();
    const tarifa = tarifasBase[Number(tramo)];
    setResultado((tarifa.base + Number(km) * 1450) * Number(viajes));
  }

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader titulo="Cotizador de triturado" descripcion="Estimación referencial para servicios de triturado en terreno." />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-3"><CardHeader titulo="Datos del servicio" descripcion="Completa recorrido, volumen y cantidad de viajes." /><CardBody><form onSubmit={cotizar} className="space-y-4"><Campo label="Distancia desde la planta (km)" htmlFor="cotizador_km" requerido><Input id="cotizador_km" type="number" min="0" value={km} onChange={(e) => setKm(e.target.value)} required /></Campo><div className="grid grid-cols-1 gap-4 sm:grid-cols-2"><Campo label="Tramo de volumen" htmlFor="cotizador_tramo" requerido><Select id="cotizador_tramo" value={tramo} onChange={(e) => setTramo(e.target.value)}>{tarifasBase.map((tarifa, indice) => <option key={tarifa.tramo} value={indice}>{tarifa.tramo}</option>)}</Select></Campo><Campo label="Viajes estimados" htmlFor="cotizador_viajes" requerido><Input id="cotizador_viajes" type="number" min="1" value={viajes} onChange={(e) => setViajes(e.target.value)} required /></Campo></div><Button type="submit"><Calculator className="h-4 w-4" /> Calcular estimación</Button></form></CardBody></Card>
        <Card className="lg:col-span-2"><CardHeader titulo="Costo estimado" /><CardBody>{resultado === null ? <div className="py-8 text-center text-sm text-slate-400"><Truck className="mx-auto mb-3 h-10 w-10" />Ingresa los datos para obtener una estimación.</div> : <div><p className="text-3xl font-semibold text-slate-900">{clp(resultado)}</p><p className="mt-1 text-sm text-slate-500">Neto estimado</p><div className="mt-5 space-y-2 border-t border-slate-100 pt-4 text-sm"><div className="flex justify-between"><span className="text-slate-500">Tarifa base</span><span>{clp(tarifasBase[Number(tramo)].base * Number(viajes))}</span></div><div className="flex justify-between"><span className="flex items-center gap-1 text-slate-500"><MapPin className="h-3.5 w-3.5" /> Traslado</span><span>{clp(Number(km) * 1450 * Number(viajes))}</span></div><div className="flex justify-between"><span className="text-slate-500">IVA</span><span>{clp(resultado * 0.19)}</span></div></div><p className="mt-4 text-xs text-slate-400">Valor referencial sujeto a inspección del material y condiciones de acceso.</p></div>}</CardBody></Card>
      </div>
    </div>
  );
}
