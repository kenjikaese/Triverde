import { useEffect, useState } from "react";
import { Boxes, Layers, PackageCheck } from "lucide-react";
import { api } from "@/lib/api";
import type { Existencia } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";

const num = (valor: string | number) => Number(valor) || 0;
const m3 = (valor: number) =>
  `${valor.toLocaleString("es-CL", { maximumFractionDigits: 2 })} m³`;

export function Inventario() {
  const [existencias, setExistencias] = useState<Existencia[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Existencia[]>("/inventario/")
      .then((r) => setExistencias(r.data))
      .catch(() => setError("No se pudo cargar el inventario."))
      .finally(() => setCargando(false));
  }, []);

  const conStock = existencias.filter((e) => num(e.volumen_m3) > 0);
  const volumenTotal = existencias.reduce((t, e) => t + num(e.volumen_m3), 0);
  const porTriturar = existencias
    .filter((e) => e.etapa === "por triturar")
    .reduce((t, e) => t + num(e.volumen_m3), 0);
  const curado = existencias
    .filter((e) => e.etapa === "curado" || e.etapa === "ensacado")
    .reduce((t, e) => t + num(e.volumen_m3), 0);

  return (
    <div>
      <PageHeader titulo="Inventario" descripcion="Existencias por material y etapa de proceso." />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card><CardBody className="flex items-center gap-4"><Boxes className="h-8 w-8 text-brand-700" /><div><p className="text-2xl font-semibold text-slate-900">{m3(volumenTotal)}</p><p className="text-sm text-slate-500">Volumen disponible</p></div></CardBody></Card>
        <Card><CardBody className="flex items-center gap-4"><Layers className="h-8 w-8 text-sky-700" /><div><p className="text-2xl font-semibold text-slate-900">{m3(porTriturar)}</p><p className="text-sm text-slate-500">Por triturar</p></div></CardBody></Card>
        <Card><CardBody className="flex items-center gap-4"><PackageCheck className="h-8 w-8 text-amber-700" /><div><p className="text-2xl font-semibold text-slate-900">{m3(curado)}</p><p className="text-sm text-slate-500">Curado y ensacado</p></div></CardBody></Card>
      </div>
      <Card>
        {cargando ? (
          <CardBody className="py-10 text-center text-slate-500">Cargando inventario...</CardBody>
        ) : conStock.length === 0 ? (
          <CardBody className="py-10 text-center text-slate-500">Sin existencias registradas.</CardBody>
        ) : (
          <Table>
            <thead><tr><Th>Material</Th><Th>Categoría</Th><Th>Etapa</Th><Th>Volumen</Th></tr></thead>
            <TBody>
              {conStock.map((e) => (
                <tr key={e.id} className="hover:bg-slate-50">
                  <Td className="font-medium text-slate-800">{e.material_nombre}</Td>
                  <Td>{e.material_categoria ? <Badge tono={e.material_categoria === "verde" ? "verde" : "ambar"}>{e.material_categoria}</Badge> : "—"}</Td>
                  <Td><Badge tono={tonoEstado(e.etapa)}>{e.etapa}</Badge></Td>
                  <Td>{m3(num(e.volumen_m3))}</Td>
                </tr>
              ))}
            </TBody>
          </Table>
        )}
      </Card>
    </div>
  );
}
