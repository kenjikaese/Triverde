import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, CalendarClock, FileUp, History, Plus, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import type { DocumentoLegal, TipoDocumento } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Campo, Input, Select } from "@/components/ui/Field";
import { fecha as formatoFecha } from "@/lib/formato";
import { mensajeDeError } from "@/lib/errores";

type Accion = "registrar" | "adjuntar" | "vigencia" | "renovar";

const TIPOS: { valor: TipoDocumento; etiqueta: string }[] = [
  { valor: "permiso", etiqueta: "Permiso" },
  { valor: "certificado", etiqueta: "Certificado" },
  { valor: "resolucion", etiqueta: "Resolución" },
  { valor: "seguro", etiqueta: "Seguro" },
  { valor: "otro", etiqueta: "Otro" },
];

const TITULOS: Record<Accion, string> = {
  registrar: "Nuevo documento",
  adjuntar: "Adjuntar archivo",
  vigencia: "Registrar vigencia",
  renovar: "Renovar documento",
};

const FORMATOS = ".pdf,.jpg,.jpeg,.png";
// El cliente `api` envia JSON por defecto; los adjuntos van como multipart.
const MULTIPART = { headers: { "Content-Type": "multipart/form-data" } };

interface Aviso {
  texto: string;
  // Reintento con confirmacion: duplicado (CU-86 Exc. 3) o renovacion
  // innecesaria de un documento vigente (CU-89 Exc. 1).
  confirmar: () => void;
}

// V_ListaDocumentos sobre C_Documentos (CU-86 a CU-89): registro, adjunto de archivo, vigencia y
// renovacion. El estado lo deriva el servidor desde la vigencia; el historial de
// versiones (CU-92) se consulta en su vista propia.
export function ListaDocumentos() {
  const [documentos, setDocumentos] = useState<DocumentoLegal[]>([]);
  const [accion, setAccion] = useState<Accion | null>(null);
  const [seleccionado, setSeleccionado] = useState<DocumentoLegal | null>(null);
  const [nombre, setNombre] = useState("");
  const [tipo, setTipo] = useState<TipoDocumento>("permiso");
  const [tipoDetalle, setTipoDetalle] = useState("");
  const [entidad, setEntidad] = useState("");
  const [emision, setEmision] = useState("");
  const [vencimiento, setVencimiento] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorModal, setErrorModal] = useState<string | null>(null);
  const [exito, setExito] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(() => {
    api
      .get<DocumentoLegal[]>("/documentos-legales/")
      .then((res) => setDocumentos(res.data))
      .catch((err) => setError(mensajeDeError(err, "No se pudo cargar los documentos.")));
  }, []);

  useEffect(() => {
    cargar();
  }, [cargar]);

  function abrir(nueva: Accion, documento: DocumentoLegal | null = null) {
    setAccion(nueva);
    setSeleccionado(documento);
    setNombre("");
    setTipo("permiso");
    setTipoDetalle("");
    setEntidad("");
    setEmision(documento?.fecha_emision ?? "");
    setVencimiento(nueva === "vigencia" ? documento?.fecha_vencimiento ?? "" : "");
    if (nueva === "renovar") setEmision("");
    setArchivo(null);
    setAviso(null);
    setErrorModal(null);
    setExito(null);
  }

  function cerrar() {
    setAccion(null);
    setSeleccionado(null);
    setAviso(null);
  }

  function terminar(mensaje: string) {
    cerrar();
    setExito(mensaje);
    cargar();
  }

  function manejarError(err: unknown, porDefecto: string, reintentar: () => void) {
    const respuesta = (err as { response?: { status?: number; data?: { detalle?: string } } })
      .response;
    if (respuesta?.status === 409 && respuesta.data?.detalle) {
      setAviso({ texto: respuesta.data.detalle, confirmar: reintentar });
    } else {
      setErrorModal(mensajeDeError(err, porDefecto));
    }
  }

  async function registrar(confirmar = false) {
    setErrorModal(null);
    setGuardando(true);
    try {
      await api.post("/documentos-legales/", {
        nombre,
        tipo,
        tipo_detalle: tipo === "otro" ? tipoDetalle : "",
        entidad_emisora: entidad,
        confirmar,
      });
      terminar(`Documento "${nombre}" registrado. Adjunte su archivo y registre su vigencia.`);
    } catch (err) {
      manejarError(err, "No se pudo registrar el documento.", () => registrar(true));
    } finally {
      setGuardando(false);
    }
  }

  async function adjuntar() {
    if (!seleccionado) return;
    if (!archivo) {
      setErrorModal("Seleccione el archivo a adjuntar.");
      return;
    }
    setErrorModal(null);
    setGuardando(true);
    const datos = new FormData();
    datos.append("archivo", archivo);
    try {
      await api.post(`/documentos-legales/${seleccionado.id}/versiones/`, datos, MULTIPART);
      terminar(`Archivo adjuntado a "${seleccionado.nombre}" como nueva versión vigente.`);
    } catch (err) {
      setErrorModal(mensajeDeError(err, "No se pudo adjuntar el archivo."));
    } finally {
      setGuardando(false);
    }
  }

  async function registrarVigencia() {
    if (!seleccionado) return;
    setErrorModal(null);
    setGuardando(true);
    try {
      const res = await api.post<DocumentoLegal>(
        `/documentos-legales/${seleccionado.id}/vigencia/`,
        { fecha_emision: emision, fecha_vencimiento: vencimiento },
      );
      terminar(`Vigencia registrada: "${res.data.nombre}" queda ${res.data.estado_display.toLowerCase()}.`);
    } catch (err) {
      setErrorModal(mensajeDeError(err, "No se pudo registrar la vigencia."));
    } finally {
      setGuardando(false);
    }
  }

  async function renovar(confirmar = false) {
    if (!seleccionado) return;
    if (!archivo) {
      setErrorModal("Adjunte el archivo del documento renovado.");
      return;
    }
    setErrorModal(null);
    setGuardando(true);
    const datos = new FormData();
    datos.append("archivo", archivo);
    datos.append("fecha_emision", emision);
    datos.append("fecha_vencimiento", vencimiento);
    if (confirmar) datos.append("confirmar", "true");
    try {
      await api.post(`/documentos-legales/${seleccionado.id}/renovar/`, datos, MULTIPART);
      terminar(`"${seleccionado.nombre}" renovado con nueva vigencia hasta ${formatoFecha(vencimiento)}.`);
    } catch (err) {
      manejarError(err, "No se pudo renovar el documento.", () => renovar(true));
    } finally {
      setGuardando(false);
    }
  }

  function enviar(e: FormEvent) {
    e.preventDefault();
    if (accion === "registrar") registrar();
    if (accion === "adjuntar") adjuntar();
    if (accion === "vigencia") registrarVigencia();
    if (accion === "renovar") renovar();
  }

  return (
    <div>
      <PageHeader
        titulo="Documentos legales"
        descripcion="Permisos, certificados, resoluciones y seguros de la empresa, con su archivo vigente y su vencimiento."
        accion={
          <Button onClick={() => abrir("registrar")}>
            <Plus className="h-4 w-4" /> Nuevo documento
          </Button>
        }
      />

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}
      {exito && (
        <div
          className="mb-4 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800"
          data-testid="documento-exito"
        >
          {exito}
        </div>
      )}

      <Card>
        <Table>
          <thead>
            <tr>
              <Th>Documento</Th>
              <Th>Tipo</Th>
              <Th>Entidad emisora</Th>
              <Th>Versión vigente</Th>
              <Th>Emisión</Th>
              <Th>Vencimiento</Th>
              <Th>Estado</Th>
              <Th>Acciones</Th>
            </tr>
          </thead>
          <TBody>
            {documentos.length === 0 ? (
              <EmptyRow colSpan={8} texto="Aún no hay documentos legales registrados." />
            ) : (
              documentos.map((d) => (
                <tr key={d.id} className="hover:bg-slate-50" data-testid="fila-documento">
                  <Td className="font-medium text-slate-800">{d.nombre}</Td>
                  <Td>
                    {d.tipo === "otro" && d.tipo_detalle
                      ? d.tipo_detalle
                      : TIPOS.find((t) => t.valor === d.tipo)?.etiqueta ?? d.tipo_display}
                  </Td>
                  <Td>{d.entidad_emisora}</Td>
                  <Td>
                    {d.version_vigente ? (
                      <a
                        href={d.version_vigente.archivo}
                        target="_blank"
                        rel="noreferrer"
                        className="text-brand-700 hover:underline"
                      >
                        v{d.version_vigente.version} · {d.version_vigente.nombre_archivo}
                      </a>
                    ) : (
                      <span className="text-slate-400">Sin archivo</span>
                    )}
                  </Td>
                  <Td>{formatoFecha(d.fecha_emision)}</Td>
                  <Td>{formatoFecha(d.fecha_vencimiento)}</Td>
                  <Td>
                    <Badge tono={tonoEstado(d.estado_display)}>{d.estado_display}</Badge>
                  </Td>
                  <Td>
                    <div className="flex flex-wrap gap-1">
                      <Button variante="fantasma" tamano="sm" onClick={() => abrir("adjuntar", d)}>
                        <FileUp className="h-4 w-4" /> Archivo
                      </Button>
                      <Button variante="fantasma" tamano="sm" onClick={() => abrir("vigencia", d)}>
                        <CalendarClock className="h-4 w-4" /> Vigencia
                      </Button>
                      <Button variante="fantasma" tamano="sm" onClick={() => abrir("renovar", d)}>
                        <RefreshCw className="h-4 w-4" /> Renovar
                      </Button>
                      <Link
                        to={`/documentos/historial?documento=${d.id}`}
                        className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-sm text-slate-600 hover:bg-slate-100"
                      >
                        <History className="h-4 w-4" /> Historial
                      </Link>
                    </div>
                  </Td>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      </Card>

      <Modal abierto={accion !== null} titulo={accion ? TITULOS[accion] : ""} onCerrar={cerrar}>
        <form onSubmit={enviar} className="space-y-4">
          {seleccionado && (
            <p className="text-sm text-slate-600">
              {seleccionado.nombre} · {seleccionado.entidad_emisora}
              {seleccionado.fecha_vencimiento &&
                ` · vence ${formatoFecha(seleccionado.fecha_vencimiento)}`}
            </p>
          )}

          {accion === "registrar" && (
            <>
              <Campo label="Nombre del documento" htmlFor="doc_nombre" requerido>
                <Input id="doc_nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} />
              </Campo>
              <Campo label="Clasificación" htmlFor="doc_tipo" requerido>
                <Select
                  id="doc_tipo"
                  value={tipo}
                  onChange={(e) => setTipo(e.target.value as TipoDocumento)}
                >
                  {TIPOS.map((t) => (
                    <option key={t.valor} value={t.valor}>
                      {t.etiqueta}
                    </option>
                  ))}
                </Select>
              </Campo>
              {tipo === "otro" && (
                <Campo label="Describa la clasificación" htmlFor="doc_tipo_detalle" requerido>
                  <Input
                    id="doc_tipo_detalle"
                    value={tipoDetalle}
                    onChange={(e) => setTipoDetalle(e.target.value)}
                  />
                </Campo>
              )}
              <Campo label="Entidad emisora" htmlFor="doc_entidad" requerido>
                <Input id="doc_entidad" value={entidad} onChange={(e) => setEntidad(e.target.value)} />
              </Campo>
            </>
          )}

          {(accion === "adjuntar" || accion === "renovar") && (
            <Campo
              label={accion === "renovar" ? "Archivo del documento renovado" : "Archivo"}
              htmlFor="doc_archivo"
              requerido
              ayuda="Formatos PDF, JPG o PNG."
            >
              <Input
                id="doc_archivo"
                type="file"
                accept={FORMATOS}
                onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
              />
            </Campo>
          )}

          {(accion === "vigencia" || accion === "renovar") && (
            <div className="grid grid-cols-2 gap-3">
              <Campo label="Fecha de emisión" htmlFor="doc_emision" requerido>
                <Input
                  id="doc_emision"
                  type="date"
                  value={emision}
                  onChange={(e) => setEmision(e.target.value)}
                />
              </Campo>
              <Campo label="Fecha de vencimiento" htmlFor="doc_vencimiento" requerido>
                <Input
                  id="doc_vencimiento"
                  type="date"
                  value={vencimiento}
                  onChange={(e) => setVencimiento(e.target.value)}
                />
              </Campo>
            </div>
          )}

          {errorModal && (
            <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{errorModal}</div>
          )}

          {aviso ? (
            <div className="space-y-3 rounded-lg bg-amber-50 px-3 py-3 text-sm text-amber-800">
              <p className="flex gap-2">
                <AlertTriangle className="h-5 w-5 shrink-0" />
                {aviso.texto}
              </p>
              <div className="flex justify-end gap-2">
                <Button variante="fantasma" tamano="sm" type="button" onClick={cerrar}>
                  Cancelar
                </Button>
                <Button tamano="sm" type="button" onClick={aviso.confirmar} disabled={guardando}>
                  Continuar de todos modos
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex justify-end gap-2">
              <Button variante="fantasma" type="button" onClick={cerrar}>
                Cancelar
              </Button>
              <Button type="submit" disabled={guardando}>
                {guardando ? "Guardando..." : accion ? TITULOS[accion] : ""}
              </Button>
            </div>
          )}
        </form>
      </Modal>
    </div>
  );
}
