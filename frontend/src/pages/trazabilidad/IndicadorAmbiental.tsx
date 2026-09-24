import { useEffect, useState } from "react";
import { AlertTriangle, Leaf, Recycle, RefreshCw, Truck } from "lucide-react";
import { api } from "@/lib/api";
import type { ResumenIndicadorAmbiental } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";

const VACIO: ResumenIndicadorAmbiental = {
  periodo: { desde: null, hasta: null },
  total_co2_evitado_kg: "0.00",
  recepciones_co2_evitado_kg: "0.00",
  pilas_co2_evitado_kg: "0.00",
  cantidad_recepciones: 0,
  cantidad_pilas: 0,
  resultados: [],
  pendientes: [],
};

function toneladas(kilos: string): string {
  return (Number(kilos) / 1000).toLocaleString("es-CL", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 3,
  });
}

function kilos(valor: string): string {
  return Number(valor).toLocaleString("es-CL", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function IndicadorAmbiental() {
  const [datos, setDatos] = useState<ResumenIndicadorAmbiental>(VACIO);
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function cargar(filtros = { desde, hasta }) {
    setCargando(true);
    setError(null);
    try {
      const respuesta = await api.get<ResumenIndicadorAmbiental>(
        "/indicador-ambiental/",
        {
          params: {
            ...(filtros.desde ? { desde: filtros.desde } : {}),
            ...(filtros.hasta ? { hasta: filtros.hasta } : {}),
          },
        },
      );
      setDatos(respuesta.data);
    } catch {
      setError("No se pudo cargar el indicador ambiental.");
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    void cargar({ desde: "", hasta: "" });
  }, []);

  function limpiarFiltros() {
    setDesde("");
    setHasta("");
    void cargar({ desde: "", hasta: "" });
  }

  return (
    <div>
      <PageHeader
        titulo="Indicador ambiental"
        descripcion="CO₂ evitado por las recepciones de material y los lotes compostados."
        accion={
          <Button onClick={() => void cargar()} disabled={cargando}>
            <RefreshCw className={`h-4 w-4 ${cargando ? "animate-spin" : ""}`} />
            {cargando ? "Actualizando..." : "Actualizar"}
          </Button>
        }
      />

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <Card className="mb-6">
        <CardBody className="flex flex-wrap items-end gap-4">
          <label className="text-sm font-medium text-slate-700">
            Desde
            <input
              type="date"
              value={desde}
              onChange={(evento) => setDesde(evento.target.value)}
              className="mt-1 block rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            />
          </label>
          <label className="text-sm font-medium text-slate-700">
            Hasta
            <input
              type="date"
              value={hasta}
              min={desde || undefined}
              onChange={(evento) => setHasta(evento.target.value)}
              className="mt-1 block rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            />
          </label>
          <Button
            variante="secundario"
            onClick={() => void cargar()}
            disabled={cargando || Boolean(desde && hasta && hasta < desde)}
          >
            Aplicar período
          </Button>
          <Button variante="fantasma" onClick={limpiarFiltros} disabled={cargando}>
            Ver histórico
          </Button>
        </CardBody>
      </Card>

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardBody className="flex items-center gap-4">
            <Leaf className="h-8 w-8 text-brand-700" />
            <div>
              <p className="text-2xl font-semibold text-slate-900">
                {toneladas(datos.total_co2_evitado_kg)} t
              </p>
              <p className="text-sm text-slate-500">CO₂e evitado total</p>
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="flex items-center gap-4">
            <Truck className="h-8 w-8 text-sky-700" />
            <div>
              <p className="text-2xl font-semibold text-slate-900">
                {toneladas(datos.recepciones_co2_evitado_kg)} t
              </p>
              <p className="text-sm text-slate-500">
                {datos.cantidad_recepciones} {datos.cantidad_recepciones === 1 ? "recepción" : "recepciones"}
              </p>
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="flex items-center gap-4">
            <Recycle className="h-8 w-8 text-amber-700" />
            <div>
              <p className="text-2xl font-semibold text-slate-900">
                {toneladas(datos.pilas_co2_evitado_kg)} t
              </p>
              <p className="text-sm text-slate-500">
                {datos.cantidad_pilas} {datos.cantidad_pilas === 1 ? "lote" : "lotes"}
              </p>
            </div>
          </CardBody>
        </Card>
      </div>

      {datos.pendientes.length > 0 && (
        <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-amber-900">
          <div className="flex items-center gap-2 font-semibold">
            <AlertTriangle className="h-5 w-5" />
            Cálculos pendientes ({datos.pendientes.length})
          </div>
          <ul className="mt-2 space-y-1 text-sm">
            {datos.pendientes.map((pendiente) => (
              <li key={`${pendiente.origen}-${pendiente.objeto_id}`}>
                <strong>{pendiente.referencia}:</strong> {pendiente.motivo}
              </li>
            ))}
          </ul>
        </div>
      )}

      <Card>
        <CardHeader
          titulo="Desglose del impacto"
          descripcion="Resultados calculados en el servidor con los factores ambientales configurados."
        />
        <Table>
          <thead>
            <tr>
              <Th>Fecha</Th>
              <Th>Origen</Th>
              <Th>Referencia</Th>
              <Th>Descripción</Th>
              <Th>CO₂e evitado</Th>
            </tr>
          </thead>
          <TBody>
            {cargando ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-500">Cargando indicador...</td></tr>
            ) : datos.resultados.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-500">No hay cálculos para el período seleccionado.</td></tr>
            ) : (
              datos.resultados.map((indicador) => (
                <tr key={indicador.id}>
                  <Td>{new Date(`${indicador.fecha}T00:00:00`).toLocaleDateString("es-CL")}</Td>
                  <Td><Badge tono={indicador.origen === "recepcion" ? "azul" : "verde"}>{indicador.origen_display}</Badge></Td>
                  <Td className="font-medium text-slate-800">{indicador.referencia}</Td>
                  <Td>{indicador.descripcion}</Td>
                  <Td className="font-semibold text-brand-800">{kilos(indicador.co2_evitado_kg)} kg</Td>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      </Card>
    </div>
  );
}
