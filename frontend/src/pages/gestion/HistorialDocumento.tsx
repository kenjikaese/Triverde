import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeft, Download, FileStack, History } from "lucide-react";
import { api } from "@/lib/api";
import { mensajeDeError } from "@/lib/errores";
import { fecha as formatoFecha } from "@/lib/formato";
import type { HistorialVersiones } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

function fechaHora(iso: string): string {
  return new Date(iso).toLocaleString("es-CL", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

// V_VersionesDocumento (CU-92): todas las versiones de un documento, de la mas
// reciente a la mas antigua, con su descarga.
//
// El documento llega por la URL (`/documentos/historial?documento=<id>`), que es
// como enlaza la lista de documentos. Solo lectura: ni el documento ni sus
// versiones cambian al consultarlo.
export function HistorialDocumento() {
  const [params] = useSearchParams();
  const id = params.get("documento");
  const [historial, setHistorial] = useState<HistorialVersiones | null>(null);
  const [cargando, setCargando] = useState(Boolean(id));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setCargando(true);
    setError(null);
    api
      .get<HistorialVersiones>(`/documentos-legales/${id}/historial/`)
      .then((res) => setHistorial(res.data))
      .catch((err) =>
        // CU-92 Excepcion 1: el documento no existe o no esta disponible.
        setError(mensajeDeError(err, "El documento no está disponible.")),
      )
      .finally(() => setCargando(false));
  }, [id]);

  const volver = (
    <Link to="/documentos">
      <Button variante="fantasma" tamano="sm">
        <ArrowLeft className="h-4 w-4" />
        Volver a documentos
      </Button>
    </Link>
  );

  if (!id) {
    return (
      <div>
        <PageHeader titulo="Historial de versiones" accion={volver} />
        <Card>
          <CardBody className="py-10 text-center text-slate-500">
            Elige un documento desde la lista para ver su historial de versiones.
          </CardBody>
        </Card>
      </div>
    );
  }

  const documento = historial?.documento;

  return (
    <div>
      <PageHeader
        titulo="Historial de versiones"
        descripcion="Archivos cargados de un documento a lo largo del tiempo, de la versión más reciente a la más antigua."
        accion={volver}
      />

      {error && (
        <div
          className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
          data-testid="error-historial"
        >
          {error}
        </div>
      )}

      {documento && (
        <Card className="mb-6">
          <CardBody className="flex items-center gap-4">
            <FileStack className="h-8 w-8 text-brand-700" />
            <div>
              <p className="text-lg font-semibold text-slate-900" data-testid="nombre-documento">
                {documento.nombre}
              </p>
              <p className="text-sm text-slate-500">
                {documento.tipo_display} · {documento.entidad_emisora}
                {documento.fecha_vencimiento
                  ? ` · vence el ${formatoFecha(documento.fecha_vencimiento)}`
                  : " · sin vigencia registrada"}
              </p>
            </div>
            <Badge tono={documento.estado === "vencido" ? "rojo" : "verde"}>
              {documento.estado_display}
            </Badge>
          </CardBody>
        </Card>
      )}

      <Card>
        <CardHeader titulo="Versiones" accion={<History className="h-5 w-5 text-slate-400" />} />
        <Table>
          <thead>
            <tr>
              <Th>Versión</Th>
              <Th>Fecha de carga</Th>
              <Th>Cargada por</Th>
              <Th>Vigencia declarada</Th>
              <Th>Estado</Th>
              <Th>Archivo</Th>
            </tr>
          </thead>
          <TBody>
            {cargando ? (
              <EmptyRow colSpan={6} texto="Cargando historial..." />
            ) : !historial || historial.versiones.length === 0 ? (
              <EmptyRow colSpan={6} texto="El documento todavía no tiene archivos cargados." />
            ) : (
              historial.versiones.map((version) => (
                <tr key={version.id} className="hover:bg-slate-50" data-testid="fila-version">
                  <Td className="font-medium text-slate-800">v{version.version}</Td>
                  <Td>{fechaHora(version.fecha_carga)}</Td>
                  <Td>{version.usuario_nombre ?? "—"}</Td>
                  <Td>
                    {version.fecha_vencimiento
                      ? `hasta ${formatoFecha(version.fecha_vencimiento)}`
                      : "—"}
                  </Td>
                  <Td>
                    <Badge tono={version.vigente ? "verde" : "gris"}>
                      {version.vigente ? "Vigente" : "Anterior"}
                    </Badge>
                  </Td>
                  <Td>
                    <a
                      href={version.archivo}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-sm text-brand-700 hover:bg-brand-50"
                      title={version.nombre_archivo}
                    >
                      <Download className="h-4 w-4" />
                      Descargar
                    </a>
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
