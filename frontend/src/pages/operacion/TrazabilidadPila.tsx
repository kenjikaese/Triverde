import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Droplets, Filter, Hourglass, PackageCheck, Shuffle } from "lucide-react";
import { api } from "@/lib/api";
import { mensajeDeError } from "@/lib/errores";
import type { PilaFicha, TipoProcesoPila } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ComposicionPila } from "./ComposicionPila";
import { RegistroProceso } from "./RegistroProceso";

const m3 = (valor: string | null | undefined) => `${Number(valor ?? 0).toLocaleString("es-CL", { maximumFractionDigits: 2 })} m³`;

function fechaLarga(iso: string) {
  const d = new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleString("es-CL", { dateStyle: "short", timeStyle: "short" });
}

// V_TrazabilidadPila (CU-43): ficha de la pila, composicion y linea de tiempo.
// Desde aqui se abren V_ComposicionPila (CU-36) y V_RegistroProceso (CU-38 a CU-42).
export function TrazabilidadPila() {
  const { id } = useParams();
  const [pila, setPila] = useState<PilaFicha | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [proceso, setProceso] = useState<TipoProcesoPila | null>(null);

  const cargar = useCallback(() => {
    api
      .get<PilaFicha>(`/pilas/${id}/trazabilidad/`)
      .then((r) => setPila(r.data))
      .catch((err) => setError(mensajeDeError(err, "No se pudo cargar la ficha de la pila.")));
  }, [id]);
  useEffect(cargar, [cargar]);

  if (!pila) {
    return (
      <div>
        <PageHeader titulo="Ficha de la pila" descripcion="Composición y procesos registrados." />
        {error ? <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : <p className="text-slate-500">Cargando...</p>}
      </div>
    );
  }

  const enProceso = pila.estado === "en proceso";
  const enReposo = pila.estado === "en reposo";

  return (
    <div>
      <Link to="/pilas" className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"><ArrowLeft className="h-4 w-4" /> Volver a las pilas</Link>
      <PageHeader titulo={`Pila ${pila.codigo}`} descripcion={`Iniciada el ${new Date(pila.fecha_inicio + "T00:00:00").toLocaleDateString("es-CL")}${pila.observaciones ? ` · ${pila.observaciones}` : ""}`} />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {aviso && <div className="mb-4 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800">{aviso}</div>}

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card><CardBody><p className="text-sm text-slate-500">Estado</p><div className="mt-1"><Badge tono={tonoEstado(pila.estado)}>{pila.estado}</Badge></div></CardBody></Card>
        <Card><CardBody><p className="text-sm text-slate-500">Volumen incorporado</p><p className="text-xl font-semibold text-slate-900">{m3(pila.volumen_total_m3)}</p></CardBody></Card>
        <Card><CardBody><p className="text-sm text-slate-500">Ensacado / curado disponible</p><p className="text-xl font-semibold text-slate-900">{m3(pila.volumen_ensacado_m3)} / {m3(pila.volumen_curado_disponible_m3)}</p></CardBody></Card>
      </div>

      {pila.estado === "en formacion" && (
        <ComposicionPila
          pilaId={pila.id}
          onCambio={cargar}
          onConfirmada={() => { setAviso("Composición confirmada: la pila quedó en proceso y el inventario se trasladó a 'pila en proceso'."); cargar(); }}
        />
      )}

      {(enProceso || enReposo) && (
        <div className="mb-6 flex flex-wrap gap-2">
          {enProceso && (
            <>
              <Button variante="secundario" onClick={() => setProceso("volteo")}><Shuffle className="h-4 w-4" /> Registrar volteo</Button>
              <Button variante="secundario" onClick={() => setProceso("riego")}><Droplets className="h-4 w-4" /> Registrar riego</Button>
              <Button variante="secundario" onClick={() => setProceso("harneado")}><Filter className="h-4 w-4" /> Registrar harneado</Button>
              <Button onClick={() => setProceso("reposo")}><Hourglass className="h-4 w-4" /> Iniciar reposo</Button>
            </>
          )}
          {enReposo && <Button onClick={() => setProceso("ensacado")}><PackageCheck className="h-4 w-4" /> Registrar ensacado</Button>}
        </div>
      )}

      <Card className="mb-6">
        <CardHeader titulo="Composición" />
        <Table>
          <thead><tr><Th>Material</Th><Th>Volumen</Th></tr></thead>
          <TBody>
            {pila.composiciones.length === 0 ? <EmptyRow colSpan={2} texto="La pila todavía no tiene materiales." /> : pila.composiciones.map((c) => (
              <tr key={c.id} data-testid="fila-composicion"><Td className="font-medium text-slate-800">{c.material_nombre}</Td><Td>{m3(c.volumen_m3)}</Td></tr>
            ))}
          </TBody>
        </Table>
      </Card>

      <Card>
        <CardHeader titulo="Línea de tiempo de procesos" />
        <Table>
          <thead><tr><Th>Fecha</Th><Th>Proceso</Th><Th>Temperatura</Th><Th>Humedad</Th><Th>Volumen</Th><Th>Observación</Th></tr></thead>
          <TBody>
            {pila.procesos.length === 0 ? <EmptyRow colSpan={6} texto="Sin procesos registrados todavía." /> : pila.procesos.map((p) => (
              <tr key={p.id} data-testid="fila-proceso">
                <Td>{fechaLarga(p.fecha)}</Td>
                <Td className="font-medium capitalize text-slate-800">{p.tipo}</Td>
                <Td>{p.temperatura ? `${p.temperatura} °C` : "—"}</Td>
                <Td>{p.humedad ? `${p.humedad} %` : "—"}</Td>
                <Td>{p.volumen_m3 ? m3(p.volumen_m3) : "—"}</Td>
                <Td className="text-amber-700">{p.advertencia ?? ""}</Td>
              </tr>
            ))}
          </TBody>
        </Table>
      </Card>

      <RegistroProceso
        tipo={proceso}
        pilaId={pila.id}
        pilaCodigo={pila.codigo}
        disponibleEnsacar={pila.volumen_curado_disponible_m3}
        onCerrar={() => setProceso(null)}
        onRegistrado={(mensaje) => { setProceso(null); setAviso(mensaje); cargar(); }}
      />
    </div>
  );
}
