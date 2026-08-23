import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Truck, Users, Boxes, AlertTriangle, ArrowRight } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Cliente, Recepcion } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";

function Tile({
  icono: Icono,
  etiqueta,
  valor,
  tono,
}: {
  icono: LucideIcon;
  etiqueta: string;
  valor: string | number;
  tono: string;
}) {
  return (
    <Card>
      <CardBody className="flex items-center gap-4">
        <div className={`flex h-11 w-11 items-center justify-center rounded-lg ${tono}`}>
          <Icono className="h-5 w-5" />
        </div>
        <div>
          <p className="text-2xl font-semibold text-slate-900">{valor}</p>
          <p className="text-sm text-slate-500">{etiqueta}</p>
        </div>
      </CardBody>
    </Card>
  );
}

export function PanelControl() {
  const { usuario } = useAuth();
  const [recepciones, setRecepciones] = useState<Recepcion[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [sinDatos, setSinDatos] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get<Recepcion[]>("/recepciones/"),
      api.get<Cliente[]>("/clientes/"),
    ])
      .then(([r, c]) => {
        setRecepciones(r.data);
        setClientes(c.data);
      })
      .catch(() => setSinDatos(true));
  }, []);

  const pendientes = recepciones.filter(
    (r) => r.estado === "pendiente de inspeccion",
  ).length;

  return (
    <div>
      <PageHeader
        titulo={`Hola, ${usuario?.nombre_completo?.split(" ")[0] ?? ""}`}
        descripcion="Resumen de la operacion de hoy."
      />

      {sinDatos && (
        <div className="mb-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
          No se pudo cargar la informacion en vivo. Verifica que el backend este
          corriendo en <code>localhost:8000</code>.
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Tile icono={Truck} etiqueta="Recepciones" valor={recepciones.length} tono="bg-brand-100 text-brand-700" />
        <Tile icono={AlertTriangle} etiqueta="Por inspeccionar" valor={pendientes} tono="bg-amber-100 text-amber-700" />
        <Tile icono={Users} etiqueta="Clientes activos" valor={clientes.filter((c) => c.estado === "activo").length} tono="bg-sky-100 text-sky-700" />
        <Tile icono={Boxes} etiqueta="Materiales" valor="—" tono="bg-earth-100 text-earth-700" />
      </div>

      <Card className="mt-6">
        <CardHeader
          titulo="Ultimas recepciones"
          accion={
            <Link
              to="/recepcion"
              className="inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:text-brand-800"
            >
              Ver todas <ArrowRight className="h-4 w-4" />
            </Link>
          }
        />
        <Table>
          <thead>
            <tr>
              <Th>Fecha</Th>
              <Th>Cliente</Th>
              <Th>Estado</Th>
              <Th>Sincronizacion</Th>
            </tr>
          </thead>
          <TBody>
            {recepciones.length === 0 ? (
              <EmptyRow colSpan={4} texto="Aun no hay recepciones registradas." />
            ) : (
              recepciones.slice(0, 6).map((r) => (
                <tr key={r.id}>
                  <Td>{r.fecha}</Td>
                  <Td>#{r.cliente}</Td>
                  <Td>
                    <Badge tono={tonoEstado(r.estado)}>{r.estado}</Badge>
                  </Td>
                  <Td>
                    <Badge tono={tonoEstado(r.estado_sincronizacion)}>
                      {r.estado_sincronizacion}
                    </Badge>
                  </Td>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      </Card>
    </div>
  );
}
