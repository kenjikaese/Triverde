import { useCallback, useEffect, useState, type FormEvent } from "react";
import { AlertTriangle, CheckCircle2, FileDown } from "lucide-react";
import { api } from "@/lib/api";
import type { DeclaracionSinader } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Campo, Input } from "@/components/ui/Field";
import { Button } from "@/components/ui/Button";
import { cantidad as formatoCantidad, fecha as formatoFecha, periodoVigente } from "@/lib/formato";
import { mensajeDeError } from "@/lib/errores";

// CU-67: genera la declaracion del periodo (C_Trazabilidad). El servidor agrupa
// por cliente, excluye a los que no tienen datos obligatorios y arma la
// planilla XLSX; esta vista pide el periodo, muestra el resumen y descarga el
// archivo para cargarlo a mano en la plataforma de la autoridad.
export function ExportacionSinader() {
  const periodo = periodoVigente();
  const [desde, setDesde] = useState(periodo.desde);
  const [hasta, setHasta] = useState(periodo.hasta);
  const [declaraciones, setDeclaraciones] = useState<DeclaracionSinader[]>([]);
  const [generada, setGenerada] = useState<DeclaracionSinader | null>(null);
  const [generando, setGenerando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cargarHistorial = useCallback(() => {
    api
      .get<DeclaracionSinader[]>("/declaraciones-sinader/")
      .then((res) => setDeclaraciones(res.data))
      .catch((err) =>
        setError(mensajeDeError(err, "No se pudo cargar el historial de declaraciones.")),
      );
  }, []);

  useEffect(() => {
    cargarHistorial();
  }, [cargarHistorial]);

  async function generar(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setGenerada(null);
    setGenerando(true);
    try {
      const res = await api.post<DeclaracionSinader>("/declaraciones-sinader/generar/", {
        periodo_inicio: desde,
        periodo_fin: hasta,
      });
      setGenerada(res.data);
      cargarHistorial();
    } catch (err: unknown) {
      const datos = (
        err as { response?: { data?: { detalle?: string; excluidos?: { cliente: string }[] } } }
      ).response?.data;
      setError(
        datos?.excluidos?.length
          ? `${datos.detalle} Clientes por completar: ${datos.excluidos
              .map((x) => x.cliente)
              .join(", ")}.`
          : mensajeDeError(err, "No se pudo generar la declaración."),
      );
    } finally {
      setGenerando(false);
    }
  }

  async function descargar(declaracion: DeclaracionSinader) {
    setError(null);
    try {
      const res = await api.get(`/declaraciones-sinader/${declaracion.id}/descargar/`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data as Blob);
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = declaracion.nombre_archivo ?? `sinader-${declaracion.id}.xlsx`;
      enlace.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setError(mensajeDeError(err, "No se pudo descargar la planilla."));
    }
  }

  const totales = generada?.contenido.totales;

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        titulo="Exportación SINADER"
        descripcion="Prepara la declaración de residuos del período para cargarla manualmente en la plataforma de la autoridad."
      />

      {error && (
        <div
          className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
          data-testid="error-sinader"
        >
          {error}
        </div>
      )}

      <Card>
        <CardHeader
          titulo="Datos de la declaración"
          descripcion="Consolida las descargas recibidas dentro del rango, agrupadas por cliente generador."
        />
        <CardBody>
          <form onSubmit={generar} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Campo label="Desde" htmlFor="sinader_desde" requerido>
                <Input
                  id="sinader_desde"
                  type="date"
                  value={desde}
                  onChange={(e) => setDesde(e.target.value)}
                  required
                />
              </Campo>
              <Campo label="Hasta" htmlFor="sinader_hasta" requerido>
                <Input
                  id="sinader_hasta"
                  type="date"
                  value={hasta}
                  onChange={(e) => setHasta(e.target.value)}
                  required
                />
              </Campo>
            </div>
            <div className="flex justify-end">
              <Button type="submit" disabled={generando}>
                <FileDown className="h-4 w-4" />
                {generando ? "Generando..." : "Generar declaración"}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>

      {generada && totales && (
        <div className="mt-5 space-y-4" data-testid="resultado-sinader">
          <div className="flex flex-wrap items-center gap-3 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800">
            <CheckCircle2 className="h-5 w-5 shrink-0" />
            <span>
              Planilla lista: {totales.clientes} clientes, {totales.descargas} descargas,{" "}
              {formatoCantidad(totales.volumen_m3)} m³ y {formatoCantidad(totales.peso_kg)} kg
              declarables.
            </span>
            <Button tamano="sm" onClick={() => descargar(generada)}>
              <FileDown className="h-4 w-4" /> Descargar XLSX
            </Button>
          </div>

          {generada.contenido.excluidos.length > 0 && (
            <div
              className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800"
              data-testid="excluidos-sinader"
            >
              <p className="flex items-center gap-2 font-medium">
                <AlertTriangle className="h-4 w-4" /> Clientes excluidos por datos incompletos
              </p>
              <ul className="mt-1 list-inside list-disc">
                {generada.contenido.excluidos.map((x) => (
                  <li key={x.cliente}>
                    {x.cliente}: falta {x.faltantes.join(" y ")} ({x.descargas}{" "}
                    {x.descargas === 1 ? "descarga" : "descargas"} sin declarar)
                  </li>
                ))}
              </ul>
            </div>
          )}

          <Card>
            <CardHeader titulo="Resumen por cliente generador" />
            <Table>
              <thead>
                <tr>
                  <Th>Cliente</Th>
                  <Th>RUT</Th>
                  <Th>Descargas</Th>
                  <Th>Volumen</Th>
                  <Th>Peso</Th>
                </tr>
              </thead>
              <TBody>
                {generada.contenido.clientes.map((c) => (
                  <tr key={c.cliente} data-testid="cliente-sinader">
                    <Td className="font-medium text-slate-800">{c.cliente}</Td>
                    <Td>{c.rut}</Td>
                    <Td>{c.descargas}</Td>
                    <Td>{formatoCantidad(c.volumen_m3)} m³</Td>
                    <Td>{formatoCantidad(c.peso_kg)} kg</Td>
                  </tr>
                ))}
              </TBody>
            </Table>
          </Card>
        </div>
      )}

      <div className="mt-6">
        <Card>
          <CardHeader
            titulo="Declaraciones generadas"
            descripcion="Cada generación conserva su planilla; el sistema no se conecta con SINADER."
          />
          <Table>
            <thead>
              <tr>
                <Th>Período</Th>
                <Th>Generada</Th>
                <Th>Por</Th>
                <Th>Clientes</Th>
                <Th>Peso declarado</Th>
                <Th>Archivo</Th>
              </tr>
            </thead>
            <TBody>
              {declaraciones.length === 0 ? (
                <EmptyRow colSpan={6} texto="Aún no se generan declaraciones." />
              ) : (
                declaraciones.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50" data-testid="fila-declaracion">
                    <Td className="font-medium text-slate-800">
                      {formatoFecha(d.periodo_inicio)} a {formatoFecha(d.periodo_fin)}
                    </Td>
                    <Td>{formatoFecha(d.fecha_generada.slice(0, 10))}</Td>
                    <Td>{d.usuario_nombre ?? "—"}</Td>
                    <Td>
                      {d.contenido.totales.clientes}
                      {d.contenido.excluidos.length > 0
                        ? ` (${d.contenido.excluidos.length} excl.)`
                        : ""}
                    </Td>
                    <Td>{formatoCantidad(d.contenido.totales.peso_kg)} kg</Td>
                    <Td>
                      <Button variante="fantasma" tamano="sm" onClick={() => descargar(d)}>
                        <FileDown className="h-4 w-4" /> XLSX
                      </Button>
                    </Td>
                  </tr>
                ))
              )}
            </TBody>
          </Table>
        </Card>
      </div>
    </div>
  );
}
