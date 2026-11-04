import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Ban, CheckCircle2, ClipboardCheck, Layers, Paperclip, ReceiptText } from "lucide-react";
import { api } from "@/lib/api";
import { mensajeDeError } from "@/lib/errores";
import type { Material, Recepcion } from "@/lib/types";
import { CapturaFoto, MiniaturasFoto } from "@/components/CapturaFoto";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select, Textarea } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";

const FILTROS = [
  { valor: "pendiente de inspeccion", etiqueta: "Por inspeccionar" },
  { valor: "recibida", etiqueta: "Recibidas" },
  { valor: "rechazada", etiqueta: "Rechazadas" },
  { valor: "", etiqueta: "Todas" },
];

function fechaHora(recepcion: Recepcion) {
  const d = new Date(recepcion.fecha + "T00:00:00");
  const fecha = isNaN(d.getTime()) ? recepcion.fecha : d.toLocaleDateString("es-CL");
  return `${fecha} ${recepcion.hora.slice(0, 5)}`;
}

function enInspeccion(recepcion: Recepcion) {
  return recepcion.estado === "pendiente de inspeccion" || recepcion.estado === "en curso";
}

// V_RegistroRechazo (CU-30, CU-31): inspeccion visual de la carga descargada. Aqui
// tambien se ven sus fotos (CU-27) y se completa el material de lo que registro el
// transportista desde su cuenta (CU-28).
export function RegistroRechazo() {
  const [recepciones, setRecepciones] = useState<Recepcion[]>([]);
  const [filtro, setFiltro] = useState(FILTROS[0].valor);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const [multando, setMultando] = useState<Recepcion | null>(null);
  const [formMulta, setFormMulta] = useState({ motivo: "", monto: "" });
  const [rechazando, setRechazando] = useState<Recepcion | null>(null);
  const [motivoRechazo, setMotivoRechazo] = useState("");
  const [errorModal, setErrorModal] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [adjuntando, setAdjuntando] = useState<Recepcion | null>(null);
  const [materiales, setMateriales] = useState<Material[]>([]);
  const [completando, setCompletando] = useState<Recepcion | null>(null);
  const [formMaterial, setFormMaterial] = useState({ material: "", volumen_m3: "" });

  useEffect(() => {
    api
      .get<Material[]>("/materiales/")
      .then((r) => setMateriales(r.data.filter((m) => m.estado === "activo")))
      .catch((err) => setError(mensajeDeError(err, "No se pudieron cargar los materiales.")));
  }, []);

  const cargar = useCallback(() => {
    setCargando(true);
    api
      .get<Recepcion[]>("/recepciones/", { params: filtro ? { estado: filtro } : {} })
      .then((r) => setRecepciones(r.data))
      .catch((err) => setError(mensajeDeError(err, "No se pudieron cargar las recepciones.")))
      .finally(() => setCargando(false));
  }, [filtro]);
  useEffect(cargar, [cargar]);

  async function aceptar(recepcion: Recepcion) {
    setError(null);
    setAviso(null);
    try {
      await api.post(`/recepciones/${recepcion.id}/aceptar/`);
      setAviso(`Recepción #${recepcion.id} aceptada: la carga quedó recibida.`);
      cargar();
    } catch (err) {
      setError(mensajeDeError(err, "No se pudo aceptar la recepción."));
    }
  }

  async function guardarFoto(archivo: string) {
    if (!adjuntando) return;
    await api.post(`/recepciones/${adjuntando.id}/foto/`, { archivo });
    setAviso(`Foto asociada a la recepción #${adjuntando.id}.`);
    setAdjuntando(null);
    cargar();
  }

  function abrirMaterial(recepcion: Recepcion) {
    setFormMaterial({ material: "", volumen_m3: recepcion.volumen_aproximado_m3 ?? "" });
    setErrorModal(null);
    setCompletando(recepcion);
  }

  async function completarMaterial(e: FormEvent) {
    e.preventDefault();
    if (!completando) return;
    setGuardando(true);
    setErrorModal(null);
    try {
      await api.patch(`/recepciones/${completando.id}/`, {
        detalles: [{ material: Number(formMaterial.material), volumen_m3: formMaterial.volumen_m3 }],
      });
      setAviso(`Material registrado en la recepción #${completando.id}.`);
      setCompletando(null);
      cargar();
    } catch (err) {
      setErrorModal(mensajeDeError(err, "No se pudo registrar el material."));
    } finally {
      setGuardando(false);
    }
  }

  function abrirMulta(recepcion: Recepcion) {
    setFormMulta({ motivo: "", monto: "" });
    setErrorModal(null);
    setMultando(recepcion);
  }

  async function registrarMulta(e: FormEvent) {
    e.preventDefault();
    if (!multando) return;
    setGuardando(true);
    setErrorModal(null);
    try {
      await api.post(`/recepciones/${multando.id}/multa/`, formMulta);
      setAviso(`Multa registrada en la recepción #${multando.id}.`);
      setMultando(null);
      cargar();
    } catch (err) {
      setErrorModal(mensajeDeError(err, "No se pudo registrar la multa."));
    } finally {
      setGuardando(false);
    }
  }

  function abrirRechazo(recepcion: Recepcion) {
    setMotivoRechazo("");
    setErrorModal(null);
    setRechazando(recepcion);
  }

  async function confirmarRechazo(e: FormEvent) {
    e.preventDefault();
    if (!rechazando) return;
    setGuardando(true);
    setErrorModal(null);
    try {
      await api.post(`/recepciones/${rechazando.id}/rechazar/`, { motivo_rechazo: motivoRechazo });
      setAviso(`Recepción #${rechazando.id} rechazada: su material salió del inventario.`);
      setRechazando(null);
      cargar();
    } catch (err) {
      setErrorModal(mensajeDeError(err, "No se pudo registrar el rechazo."));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div>
      <PageHeader titulo="Inspección de cargas" descripcion="Resultado de la inspección visual de cada descarga: aceptar, aplicar una multa o rechazar." />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {aviso && <div className="mb-4 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800">{aviso}</div>}

      <div className="mb-4 max-w-xs">
        <Campo label="Mostrar" htmlFor="inspeccion_filtro">
          <Select id="inspeccion_filtro" value={filtro} onChange={(e) => setFiltro(e.target.value)}>
            {FILTROS.map((f) => <option key={f.valor} value={f.valor}>{f.etiqueta}</option>)}
          </Select>
        </Campo>
      </div>

      <Card>
        <Table>
          <thead><tr><Th>N°</Th><Th>Fecha</Th><Th>Cliente</Th><Th>Vehículo</Th><Th>Material y fotos</Th><Th>Multas</Th><Th>Estado</Th><Th>Acciones</Th></tr></thead>
          <TBody>
            {cargando ? <EmptyRow colSpan={8} texto="Cargando..." /> : recepciones.length === 0 ? <EmptyRow colSpan={8} texto="No hay recepciones en este estado." /> : recepciones.map((r) => (
              <tr key={r.id} className="hover:bg-slate-50" data-testid="fila-recepcion">
                <Td className="font-medium text-slate-800">#{r.id}</Td>
                <Td>{fechaHora(r)}</Td>
                <Td>{r.cliente_razon_social ?? `#${r.cliente}`}</Td>
                <Td>{r.vehiculo_patente ?? "—"}</Td>
                <Td>
                  {r.detalles.length > 0 ? r.detalles.map((d) => (
                    <div key={d.id}>{d.material_nombre}: {Number(d.volumen_m3).toLocaleString("es-CL")} m³</div>
                  )) : r.volumen_aproximado_m3 ? (
                    <span className="text-amber-700">Aprox. {Number(r.volumen_aproximado_m3).toLocaleString("es-CL")} m³, por completar</span>
                  ) : "—"}
                  {r.fotos.length > 0 && <div className="mt-2"><MiniaturasFoto fotos={r.fotos} /></div>}
                </Td>
                <Td>{r.multas?.length ? r.multas.map((m) => <div key={m.id} title={m.motivo}>${Number(m.monto).toLocaleString("es-CL")}</div>) : "—"}</Td>
                <Td>
                  <Badge tono={tonoEstado(r.estado)}>{r.estado}</Badge>
                  {r.motivo_rechazo && <p className="mt-1 text-xs text-slate-500">{r.motivo_rechazo}</p>}
                </Td>
                <Td>
                  {enInspeccion(r) ? (
                    <div className="flex flex-col gap-2 whitespace-nowrap xl:flex-row">
                      {r.detalles.length > 0 ? (
                        <Button tamano="sm" onClick={() => aceptar(r)}><CheckCircle2 className="h-4 w-4" /> Aceptar carga</Button>
                      ) : (
                        <Button tamano="sm" onClick={() => abrirMaterial(r)}><Layers className="h-4 w-4" /> Completar material</Button>
                      )}
                      <Button tamano="sm" variante="secundario" onClick={() => setAdjuntando(r)}><Paperclip className="h-4 w-4" /> Agregar foto</Button>
                      <Button tamano="sm" variante="secundario" onClick={() => abrirMulta(r)}><ReceiptText className="h-4 w-4" /> Aplicar multa</Button>
                      <Button tamano="sm" variante="peligro" onClick={() => abrirRechazo(r)}><Ban className="h-4 w-4" /> Rechazar carga</Button>
                    </div>
                  ) : <ClipboardCheck className="h-4 w-4 text-slate-300" aria-label="Inspección terminada" />}
                </Td>
              </tr>
            ))}
          </TBody>
        </Table>
      </Card>

      <Modal abierto={adjuntando !== null} titulo={`Foto de la recepción #${adjuntando?.id ?? ""}`} onCerrar={() => setAdjuntando(null)}>
        {adjuntando && <CapturaFoto alGuardar={guardarFoto} />}
      </Modal>

      <Modal abierto={completando !== null} titulo={`Material de la recepción #${completando?.id ?? ""}`} onCerrar={() => setCompletando(null)}>
        <form onSubmit={completarMaterial} className="space-y-4">
          {errorModal && <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{errorModal}</div>}
          <Campo label="Material" htmlFor="completar_material" requerido>
            <Select id="completar_material" value={formMaterial.material} onChange={(e) => setFormMaterial({ ...formMaterial, material: e.target.value })} required>
              <option value="">Selecciona...</option>
              {materiales.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}
            </Select>
          </Campo>
          <Campo label="Volumen (m³)" htmlFor="completar_volumen" requerido ayuda="Parte del volumen aproximado que informó el transportista; corrígelo si la inspección indica otro.">
            <Input id="completar_volumen" type="number" min="0" step="0.01" value={formMaterial.volumen_m3} onChange={(e) => setFormMaterial({ ...formMaterial, volumen_m3: e.target.value })} required />
          </Campo>
          <div className="flex justify-end gap-2 pt-2"><Button type="button" variante="secundario" onClick={() => setCompletando(null)}>Cancelar</Button><Button type="submit" disabled={guardando}>{guardando ? "Guardando..." : "Registrar material"}</Button></div>
        </form>
      </Modal>

      <Modal abierto={multando !== null} titulo={`Aplicar multa a la recepción #${multando?.id ?? ""}`} onCerrar={() => setMultando(null)}>
        <form onSubmit={registrarMulta} className="space-y-4">
          {errorModal && <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{errorModal}</div>}
          <Campo label="Motivo" htmlFor="multa_motivo" requerido><Input id="multa_motivo" value={formMulta.motivo} onChange={(e) => setFormMulta({ ...formMulta, motivo: e.target.value })} placeholder="Ej. botellas o latas mezcladas" required /></Campo>
          <Campo label="Monto ($)" htmlFor="multa_monto" requerido><Input id="multa_monto" type="number" step="1" value={formMulta.monto} onChange={(e) => setFormMulta({ ...formMulta, monto: e.target.value })} required /></Campo>
          <div className="flex justify-end gap-2 pt-2"><Button type="button" variante="secundario" onClick={() => setMultando(null)}>Cancelar</Button><Button type="submit" disabled={guardando}>{guardando ? "Guardando..." : "Registrar multa"}</Button></div>
        </form>
      </Modal>

      <Modal abierto={rechazando !== null} titulo={`Rechazar la recepción #${rechazando?.id ?? ""}`} onCerrar={() => setRechazando(null)}>
        <form onSubmit={confirmarRechazo} className="space-y-4">
          {errorModal && <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{errorModal}</div>}
          <p className="text-sm text-slate-600">La recepción queda cerrada como constancia y su material sale del inventario. Las multas ya registradas se conservan.</p>
          <Campo label="Motivo del rechazo" htmlFor="rechazo_motivo" requerido><Textarea id="rechazo_motivo" value={motivoRechazo} onChange={(e) => setMotivoRechazo(e.target.value)} required /></Campo>
          <div className="flex justify-end gap-2 pt-2"><Button type="button" variante="secundario" onClick={() => setRechazando(null)}>Cancelar</Button><Button type="submit" variante="peligro" disabled={guardando}>{guardando ? "Guardando..." : "Confirmar rechazo"}</Button></div>
        </form>
      </Modal>
    </div>
  );
}
