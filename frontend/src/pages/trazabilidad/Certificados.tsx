import { useCallback, useEffect, useState, type FormEvent } from "react";
import { AlertTriangle, Download, FileCheck2, FileText } from "lucide-react";
import { api } from "@/lib/api";
import type { CertificadoTrazabilidad, Cliente, Recepcion } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";
import { fecha as formatoFecha, periodoVigente } from "@/lib/formato";
import { mensajeDeError } from "@/lib/errores";

interface ConsolidadoPrevio {
  detalle: string;
  previo: CertificadoTrazabilidad;
}

// CU-65 y CU-66: emision de certificados por descarga y consolidado mensual,
// mas el historial (C_Certificados). El contenido lo compila el servidor; la
// exportacion descarga ese contenido como archivo, igual que el CU-56.
export function Certificados() {
  const periodo = periodoVigente();
  const [certificados, setCertificados] = useState<CertificadoTrazabilidad[]>([]);
  const [recepciones, setRecepciones] = useState<Recepcion[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [recepcionSel, setRecepcionSel] = useState("");
  const [clienteSel, setClienteSel] = useState("");
  const [desde, setDesde] = useState(periodo.desde);
  const [hasta, setHasta] = useState(periodo.hasta);
  const [previo, setPrevio] = useState<ConsolidadoPrevio | null>(null);
  const [emitido, setEmitido] = useState<CertificadoTrazabilidad | null>(null);
  const [generando, setGenerando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // El listado de recepciones trae el id del cliente; el nombre se resuelve
  // con el catalogo de clientes ya cargado para el consolidado.
  const nombreCliente = (id: number) =>
    clientes.find((c) => c.id === id)?.razon_social ?? `Cliente #${id}`;

  const cargarHistorial = useCallback(() => {
    api
      .get<CertificadoTrazabilidad[]>("/certificados/")
      .then((res) => setCertificados(res.data))
      .catch((err) =>
        setError(mensajeDeError(err, "No se pudo cargar el historial de certificados.")),
      );
  }, []);

  useEffect(() => {
    cargarHistorial();
    api
      .get<Recepcion[]>("/recepciones/", { params: { estado: "recibida" } })
      .then((res) => setRecepciones(res.data))
      .catch((err) =>
        setError(mensajeDeError(err, "No se pudo cargar las descargas recibidas.")),
      );
    api
      .get<Cliente[]>("/clientes/", { params: { estado: "activo" } })
      .then((res) => setClientes(res.data))
      .catch((err) => setError(mensajeDeError(err, "No se pudo cargar los clientes.")));
  }, [cargarHistorial]);

  async function generarDescarga(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setEmitido(null);
    if (!recepcionSel) {
      setError("Selecciona la descarga a certificar.");
      return;
    }
    setGenerando(true);
    try {
      const res = await api.post<CertificadoTrazabilidad>("/certificados/generar-descarga/", {
        recepcion: Number(recepcionSel),
      });
      setEmitido(res.data);
      setRecepcionSel("");
      cargarHistorial();
    } catch (err: unknown) {
      const datos = (err as { response?: { data?: { detalle?: string; sin_peso?: string[] } } })
        .response?.data;
      setError(
        datos?.sin_peso?.length
          ? `${datos.detalle} Materiales sin peso: ${datos.sin_peso.join(", ")}.`
          : mensajeDeError(err, "No se pudo emitir el certificado."),
      );
    } finally {
      setGenerando(false);
    }
  }

  async function generarConsolidado(confirmar: boolean) {
    setError(null);
    setEmitido(null);
    if (!clienteSel) {
      setError("Selecciona el cliente del consolidado.");
      return;
    }
    setGenerando(true);
    try {
      const res = await api.post<CertificadoTrazabilidad>("/certificados/generar-consolidado/", {
        cliente: Number(clienteSel),
        periodo_inicio: desde,
        periodo_fin: hasta,
        confirmar,
      });
      setEmitido(res.data);
      setPrevio(null);
      cargarHistorial();
    } catch (err: unknown) {
      const respuesta = (err as { response?: { status?: number; data?: ConsolidadoPrevio } })
        .response;
      if (respuesta?.status === 409 && respuesta.data) {
        // CU-66, Excepcion 2: ya existe uno; se pide confirmar la nueva version.
        setPrevio(respuesta.data);
      } else {
        setError(mensajeDeError(err, "No se pudo emitir el consolidado."));
      }
    } finally {
      setGenerando(false);
    }
  }

  async function exportar(certificado: CertificadoTrazabilidad) {
    setError(null);
    try {
      const res = await api.get(`/certificados/${certificado.id}/exportar/`);
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = `certificado-${certificado.codigo}.json`;
      enlace.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setError(mensajeDeError(err, "No se pudo exportar el certificado."));
    }
  }

  return (
    <div>
      <PageHeader
        titulo="Certificados de trazabilidad"
        descripcion="Respaldo del ingreso y valorización de residuos vegetales: por descarga puntual o consolidado mensual por cliente."
      />

      {error && (
        <div
          className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
          data-testid="error-certificados"
        >
          {error}
        </div>
      )}

      {emitido && (
        <div
          className="mb-4 flex items-center gap-3 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800"
          data-testid="certificado-emitido"
        >
          <FileCheck2 className="h-5 w-5 shrink-0" />
          <span>
            Certificado <strong>{emitido.codigo}</strong> emitido para{" "}
            {emitido.cliente_razon_social}: {emitido.contenido.totales.peso_kg} kg en{" "}
            {emitido.contenido.totales.volumen_m3} m³
            {emitido.contenido.version ? ` (versión ${emitido.contenido.version})` : ""}.
          </span>
          <Button variante="secundario" tamano="sm" onClick={() => exportar(emitido)}>
            <Download className="h-4 w-4" /> Descargar
          </Button>
        </div>
      )}

      {previo && (
        <div
          className="mb-4 flex flex-wrap items-center gap-3 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800"
          data-testid="consolidado-previo"
        >
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <span>
            {previo.detalle} Existe el folio <strong>{previo.previo.codigo}</strong> del{" "}
            {formatoFecha(previo.previo.fecha_emision)}.
          </span>
          <Button tamano="sm" onClick={() => generarConsolidado(true)} disabled={generando}>
            Emitir nueva versión
          </Button>
          <Button variante="fantasma" tamano="sm" onClick={() => setPrevio(null)}>
            Cancelar
          </Button>
        </div>
      )}

      <div className="mb-6 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader
            titulo="Certificado por descarga"
            descripcion="Solo descargas recibidas con su peso calculado."
          />
          <CardBody>
            <form onSubmit={generarDescarga} className="space-y-4">
              <Campo label="Descarga recibida" htmlFor="cert_recepcion" requerido>
                <Select
                  id="cert_recepcion"
                  value={recepcionSel}
                  onChange={(e) => setRecepcionSel(e.target.value)}
                >
                  <option value="">Selecciona una descarga</option>
                  {recepciones.map((r) => (
                    <option key={r.id} value={r.id}>
                      Recepción #{r.id} · {nombreCliente(r.cliente)} · {formatoFecha(r.fecha)}
                    </option>
                  ))}
                </Select>
              </Campo>
              <div className="flex justify-end">
                <Button type="submit" disabled={generando || recepciones.length === 0}>
                  <FileCheck2 className="h-4 w-4" />
                  {generando ? "Emitiendo..." : "Emitir certificado"}
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            titulo="Consolidado mensual"
            descripcion="Agrupa las descargas recibidas del cliente en el período, por material."
          />
          <CardBody>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                generarConsolidado(false);
              }}
              className="space-y-4"
            >
              <Campo label="Cliente" htmlFor="cert_cliente" requerido>
                <Select
                  id="cert_cliente"
                  value={clienteSel}
                  onChange={(e) => setClienteSel(e.target.value)}
                >
                  <option value="">Selecciona un cliente</option>
                  {clientes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.razon_social}
                    </option>
                  ))}
                </Select>
              </Campo>
              <div className="grid grid-cols-2 gap-3">
                <Campo label="Desde" htmlFor="cert_desde" requerido>
                  <Input
                    id="cert_desde"
                    type="date"
                    value={desde}
                    onChange={(e) => setDesde(e.target.value)}
                    required
                  />
                </Campo>
                <Campo label="Hasta" htmlFor="cert_hasta" requerido>
                  <Input
                    id="cert_hasta"
                    type="date"
                    value={hasta}
                    onChange={(e) => setHasta(e.target.value)}
                    required
                  />
                </Campo>
              </div>
              <div className="flex justify-end">
                <Button type="submit" disabled={generando}>
                  <FileText className="h-4 w-4" />
                  {generando ? "Emitiendo..." : "Emitir consolidado"}
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader
          titulo="Historial de certificados"
          descripcion="Todos los certificados emitidos. Las versiones anteriores de un consolidado se conservan."
        />
        <Table>
          <thead>
            <tr>
              <Th>Folio</Th>
              <Th>Tipo</Th>
              <Th>Referencia</Th>
              <Th>Cliente</Th>
              <Th>Emitido</Th>
              <Th>Peso certificado</Th>
              <Th>Archivo</Th>
            </tr>
          </thead>
          <TBody>
            {certificados.length === 0 ? (
              <EmptyRow colSpan={7} texto="Aún no se emiten certificados." />
            ) : (
              certificados.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50" data-testid="fila-certificado">
                  <Td className="font-medium text-slate-800">{c.codigo}</Td>
                  <Td>
                    <Badge tono={c.tipo === "consolidado" ? "azul" : "verde"}>
                      {c.tipo_display}
                      {c.contenido.version ? ` v${c.contenido.version}` : ""}
                    </Badge>
                  </Td>
                  <Td>{c.referencia}</Td>
                  <Td>{c.cliente_razon_social}</Td>
                  <Td>{formatoFecha(c.fecha_emision)}</Td>
                  <Td>{c.contenido.totales.peso_kg} kg</Td>
                  <Td>
                    <Button variante="fantasma" tamano="sm" onClick={() => exportar(c)}>
                      <Download className="h-4 w-4" /> Descargar
                    </Button>
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
