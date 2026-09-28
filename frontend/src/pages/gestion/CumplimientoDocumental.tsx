import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, CheckCircle2, Clock, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { mensajeDeError } from "@/lib/errores";
import { fecha as formatoFecha } from "@/lib/formato";
import type {
  DocumentoPendiente,
  TableroCumplimiento,
  TipoDocumento,
} from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Select } from "@/components/ui/Field";

const TIPOS: { valor: TipoDocumento | ""; etiqueta: string }[] = [
  { valor: "", etiqueta: "Todos los tipos" },
  { valor: "permiso", etiqueta: "Permiso" },
  { valor: "certificado", etiqueta: "Certificado" },
  { valor: "resolucion", etiqueta: "Resolucion" },
  { valor: "seguro", etiqueta: "Seguro" },
  { valor: "otro", etiqueta: "Otro" },
];

function dias(documento: DocumentoPendiente): string {
  if (documento.dias_restantes === null) return "—";
  if (documento.dias_restantes < 0) {
    return `${Math.abs(documento.dias_restantes)} d vencido`;
  }
  return `${documento.dias_restantes} d`;
}

// V_TableroCumplimiento (CU-91): cuantos documentos hay vigentes, por vencer y
// vencidos, y cuales urge renovar.
//
// El agrupamiento, el orden por proximidad y la separacion de los que no tienen
// vigencia los hace el servidor (/cumplimiento/tablero/): la vista solo los
// muestra. Es de solo lectura; la consulta no modifica ningun documento.
export function CumplimientoDocumental() {
  const [tablero, setTablero] = useState<TableroCumplimiento | null>(null);
  const [tipo, setTipo] = useState<TipoDocumento | "">("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setCargando(true);
    api
      .get<TableroCumplimiento>("/cumplimiento/tablero/", {
        params: { tipo: tipo || undefined },
      })
      .then((res) => setTablero(res.data))
      .catch((err) =>
        setError(mensajeDeError(err, "No se pudo cargar el tablero de cumplimiento.")),
      )
      .finally(() => setCargando(false));
  }, [tipo]);

  const resumen = tablero?.resumen;
  const tarjetas = [
    { clave: "vigente", etiqueta: "Vigentes", icono: CheckCircle2, color: "text-brand-700" },
    { clave: "por_vencer", etiqueta: "Por vencer", icono: Clock, color: "text-amber-700" },
    { clave: "vencido", etiqueta: "Vencidos", icono: AlertTriangle, color: "text-red-700" },
    { clave: "sin_vigencia", etiqueta: "Sin vigencia definida", icono: ShieldCheck, color: "text-slate-400" },
  ] as const;

  return (
    <div>
      <PageHeader
        titulo="Cumplimiento documental"
        descripcion="Estado de vigencia de los permisos, certificados y seguros de la empresa."
        accion={
          <Select
            aria-label="Tipo de documento"
            className="w-auto"
            value={tipo}
            onChange={(e) => setTipo(e.target.value as TipoDocumento | "")}
          >
            {TIPOS.map((t) => (
              <option key={t.valor} value={t.valor}>
                {t.etiqueta}
              </option>
            ))}
          </Select>
        }
      />

      {error && (
        <div
          className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
          data-testid="error-cumplimiento"
        >
          {error}
        </div>
      )}

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {tarjetas.map(({ clave, etiqueta, icono: Icono, color }) => (
          <Card key={clave}>
            <CardBody className="flex items-center gap-4">
              <Icono className={`h-8 w-8 ${color}`} />
              <div>
                <p
                  className="text-2xl font-semibold text-slate-900"
                  data-testid={`resumen-${clave}`}
                >
                  {resumen ? resumen[clave] : "—"}
                </p>
                <p className="text-sm text-slate-500">{etiqueta}</p>
              </div>
            </CardBody>
          </Card>
        ))}
      </div>

      <Card className="mb-6">
        <CardHeader
          titulo="Documentos por vencer y vencidos"
          descripcion={
            tablero
              ? `Ordenados por proximidad de vencimiento. Se avisa con ${tablero.umbral_dias} días de anticipación.`
              : "Ordenados por proximidad de vencimiento, para priorizar las renovaciones."
          }
        />
        <Table>
          <thead>
            <tr>
              <Th>Documento</Th>
              <Th>Tipo</Th>
              <Th>Entidad emisora</Th>
              <Th>Vencimiento</Th>
              <Th>Días</Th>
              <Th>Estado</Th>
            </tr>
          </thead>
          <TBody>
            {cargando ? (
              <EmptyRow colSpan={6} texto="Cargando tablero..." />
            ) : !tablero || tablero.pendientes.length === 0 ? (
              <EmptyRow
                colSpan={6}
                texto={
                  tablero && tablero.total === 0
                    ? "Todavía no hay documentos registrados."
                    : "Ningún documento está por vencer ni vencido."
                }
              />
            ) : (
              tablero.pendientes.map((documento) => (
                <tr key={documento.id} className="hover:bg-slate-50" data-testid="fila-pendiente">
                  <Td className="font-medium text-slate-800">
                    <Link
                      to={`/documentos/historial?documento=${documento.id}`}
                      className="text-brand-700 hover:underline"
                    >
                      {documento.nombre}
                    </Link>
                  </Td>
                  <Td>{documento.tipo_display}</Td>
                  <Td>{documento.entidad_emisora}</Td>
                  <Td>{formatoFecha(documento.fecha_vencimiento)}</Td>
                  <Td
                    className={
                      (documento.dias_restantes ?? 0) < 0
                        ? "font-medium text-red-700"
                        : "text-slate-700"
                    }
                  >
                    {dias(documento)}
                  </Td>
                  <Td>
                    <Badge tono={tonoEstado(documento.estado)}>
                      {documento.estado_display}
                    </Badge>
                  </Td>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      </Card>

      {tablero && tablero.sin_vigencia.length > 0 && (
        <Card>
          <CardHeader
            titulo="Sin vigencia definida"
            descripcion="Pendientes de completar: no entran en los conteos de vigente, por vencer ni vencido."
          />
          <Table>
            <thead>
              <tr>
                <Th>Documento</Th>
                <Th>Tipo</Th>
                <Th>Entidad emisora</Th>
              </tr>
            </thead>
            <TBody>
              {tablero.sin_vigencia.map((documento) => (
                <tr key={documento.id} className="hover:bg-slate-50" data-testid="fila-sin-vigencia">
                  <Td className="font-medium text-slate-800">{documento.nombre}</Td>
                  <Td>{documento.tipo_display}</Td>
                  <Td>{documento.entidad_emisora}</Td>
                </tr>
              ))}
            </TBody>
          </Table>
        </Card>
      )}
    </div>
  );
}
