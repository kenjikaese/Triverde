import { useCallback, useEffect, useState, type FormEvent } from "react";
import { CheckCircle2, Paperclip, Truck } from "lucide-react";
import { isAxiosError } from "axios";
import { api } from "@/lib/api";
import { mensajeDeError } from "@/lib/errores";
import { encolarRecepcion } from "@/lib/sync";
import { useOnline } from "@/lib/useOnline";
import type { Recepcion } from "@/lib/types";
import { CapturaFoto, MiniaturasFoto } from "@/components/CapturaFoto";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Campo, Input } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyRow, Table, TBody, Td, Th } from "@/components/ui/Table";

function fechaLocal() {
  const ahora = new Date();
  const mes = String(ahora.getMonth() + 1).padStart(2, "0");
  const dia = String(ahora.getDate()).padStart(2, "0");
  return `${ahora.getFullYear()}-${mes}-${dia}`;
}

// V_RecepcionTransportista (CU-28): formulario reducido de la descarga. El cliente,
// el transportista y el vehiculo los determina el servidor a partir de la cuenta.
export function RecepcionTransportista() {
  const online = useOnline();
  const [fecha, setFecha] = useState(fechaLocal);
  const [hora, setHora] = useState(() => new Date().toTimeString().slice(0, 5));
  const [volumen, setVolumen] = useState("");
  const [fotos, setFotos] = useState<string[]>([]);
  const [errorVolumen, setErrorVolumen] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const [descargas, setDescargas] = useState<Recepcion[]>([]);
  const [cargando, setCargando] = useState(true);
  const [adjuntando, setAdjuntando] = useState<Recepcion | null>(null);

  const cargar = useCallback(() => {
    setCargando(true);
    api
      .get<Recepcion[]>("/recepciones/")
      .then((r) => setDescargas(r.data))
      .catch((err) => setError(mensajeDeError(err, "No se pudieron cargar tus descargas.")))
      .finally(() => setCargando(false));
  }, []);
  useEffect(() => {
    if (online) cargar();
    else setCargando(false);
  }, [cargar, online]);

  function limpiar() {
    setVolumen("");
    setFotos([]);
    setFecha(fechaLocal());
    setHora(new Date().toTimeString().slice(0, 5));
  }

  async function confirmar(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setAviso(null);
    setErrorVolumen(null);
    // Excepcion 2: sin volumen no se crea la recepcion.
    if (!volumen.trim()) {
      setErrorVolumen("Ingresa el volumen aproximado.");
      return;
    }
    const datos = {
      fecha,
      hora,
      volumen_aproximado_m3: volumen,
      fotos: fotos.map((archivo) => ({ archivo })),
    };
    const avisoCola = "Descarga guardada en este dispositivo. Se enviará sola al recuperar la señal.";
    setEnviando(true);
    try {
      if (!online) {
        await encolarRecepcion(datos);
        setAviso(avisoCola);
        limpiar();
        return;
      }
      const res = await api.post<Recepcion>("/recepciones/mi-descarga/", datos);
      setAviso(`Descarga #${res.data.id} registrada a nombre de ${res.data.cliente_razon_social}. El operador la revisará en planta.`);
      limpiar();
      cargar();
    } catch (err) {
      if (isAxiosError(err) && !err.response) {
        // Fallo de red pese a figurar en linea: se respalda en la cola local.
        await encolarRecepcion(datos);
        setAviso(avisoCola);
        limpiar();
      } else {
        setError(mensajeDeError(err, "No se pudo registrar la descarga."));
      }
    } finally {
      setEnviando(false);
    }
  }

  async function guardarFoto(archivo: string) {
    if (!adjuntando) return;
    await api.post(`/recepciones/${adjuntando.id}/foto/`, { archivo });
    setAviso(`Foto asociada a la descarga #${adjuntando.id}.`);
    setAdjuntando(null);
    cargar();
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        titulo="Registrar mi descarga"
        descripcion="Indica cuándo descargaste y cuánto material traías. El operador completa el resto en planta."
        accion={online ? <Badge tono="verde">En línea</Badge> : <Badge tono="ambar">Sin conexión</Badge>}
      />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {aviso && (
        <div className="mb-4 flex items-start gap-3 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800">
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" /> {aviso}
        </div>
      )}

      <form onSubmit={confirmar} noValidate className="mb-6">
        <Card>
          <CardHeader titulo="Datos de la descarga" />
          <CardBody className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Campo label="Fecha" htmlFor="descarga_fecha" requerido>
                <Input id="descarga_fecha" type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />
              </Campo>
              <Campo label="Hora" htmlFor="descarga_hora" requerido>
                <Input id="descarga_hora" type="time" value={hora} onChange={(e) => setHora(e.target.value)} />
              </Campo>
              <Campo label="Volumen aproximado (m³)" htmlFor="descarga_volumen" requerido error={errorVolumen ?? undefined}>
                <Input id="descarga_volumen" type="number" min="0" step="0.01" value={volumen} onChange={(e) => setVolumen(e.target.value)} />
              </Campo>
            </div>
            <div>
              <p className="mb-2 text-sm font-medium text-slate-700">Foto del material</p>
              {fotos.length > 0 && <div className="mb-3"><MiniaturasFoto fotos={fotos.map((archivo) => ({ archivo }))} /></div>}
              <CapturaFoto alGuardar={(archivo) => setFotos((previas) => [...previas, archivo])} />
            </div>
            <div className="flex justify-end">
              <Button type="submit" disabled={enviando}>
                <Truck className="h-4 w-4" /> {enviando ? "Guardando..." : "Confirmar descarga"}
              </Button>
            </div>
          </CardBody>
        </Card>
      </form>

      <Card>
        <CardHeader titulo="Mis descargas" />
        <Table>
          <thead><tr><Th>N°</Th><Th>Fecha</Th><Th>Volumen aprox.</Th><Th>Fotos</Th><Th>Estado</Th><Th>Acciones</Th></tr></thead>
          <TBody>
            {cargando ? (
              <EmptyRow colSpan={6} texto="Cargando..." />
            ) : descargas.length === 0 ? (
              <EmptyRow colSpan={6} texto={online ? "Todavía no registras descargas." : "Sin conexión: tus descargas se muestran al recuperar la señal."} />
            ) : (
              descargas.map((d) => (
                <tr key={d.id} className="hover:bg-slate-50" data-testid="fila-descarga">
                  <Td className="font-medium text-slate-800">#{d.id}</Td>
                  <Td>{d.fecha} {d.hora.slice(0, 5)}</Td>
                  <Td>{d.volumen_aproximado_m3 ? `${Number(d.volumen_aproximado_m3).toLocaleString("es-CL")} m³` : "—"}</Td>
                  <Td>{d.fotos.length > 0 ? <MiniaturasFoto fotos={d.fotos} /> : "—"}</Td>
                  <Td><Badge tono={tonoEstado(d.estado)}>{d.estado}</Badge></Td>
                  <Td>
                    {d.estado === "pendiente de inspeccion" ? (
                      <Button type="button" tamano="sm" variante="secundario" onClick={() => setAdjuntando(d)}>
                        <Paperclip className="h-4 w-4" /> Agregar foto
                      </Button>
                    ) : "—"}
                  </Td>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      </Card>

      <Modal abierto={adjuntando !== null} titulo={`Foto de la descarga #${adjuntando?.id ?? ""}`} onCerrar={() => setAdjuntando(null)}>
        {adjuntando && <CapturaFoto alGuardar={guardarFoto} />}
      </Modal>
    </div>
  );
}
