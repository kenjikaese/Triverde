import { useEffect, useState, type FormEvent } from "react";
import { Plus, Trash2, Truck, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";
import { isAxiosError } from "axios";
import type { Cliente, Material, Recepcion, Transportista, Vehiculo } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Campo, Input, Select, Textarea } from "@/components/ui/Field";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { useOnline } from "@/lib/useOnline";
import { encolarRecepcion } from "@/lib/sync";

interface LineaForm {
  material: string;
  volumen_m3: string;
  destino_sugerido: string;
}

const hoy = new Date().toISOString().slice(0, 10);
const ahora = new Date().toTimeString().slice(0, 5);
const lineaVacia: LineaForm = { material: "", volumen_m3: "", destino_sugerido: "" };

export function RegistroRecepcion() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [materiales, setMateriales] = useState<Material[]>([]);
  const [vehiculos, setVehiculos] = useState<Vehiculo[]>([]);
  const [transportistas, setTransportistas] = useState<Transportista[]>([]);

  const [cliente, setCliente] = useState("");
  const [transportista, setTransportista] = useState("");
  const [vehiculo, setVehiculo] = useState("");
  const [conductor, setConductor] = useState("");
  const [fecha, setFecha] = useState(hoy);
  const [hora, setHora] = useState(ahora);
  const [observaciones, setObservaciones] = useState("");
  const [lineas, setLineas] = useState<LineaForm[]>([{ ...lineaVacia }]);

  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState<Recepcion | null>(null);
  const [encolada, setEncolada] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const online = useOnline();

  useEffect(() => {
    Promise.all([
      api.get<Cliente[]>("/clientes/"),
      api.get<Material[]>("/materiales/"),
      api.get<Vehiculo[]>("/vehiculos/"),
      api.get<Transportista[]>("/transportistas/"),
    ])
      .then(([c, m, v, t]) => {
        setClientes(c.data);
        setMateriales(m.data);
        setVehiculos(v.data);
        setTransportistas(t.data);
      })
      .catch(() => setError("No se pudieron cargar los catalogos (backend caido?)."));
  }, []);

  function actualizarLinea(i: number, campo: keyof LineaForm, valor: string) {
    setLineas((prev) =>
      prev.map((l, idx) => (idx === i ? { ...l, [campo]: valor } : l)),
    );
  }

  function limpiarFormulario() {
    setCliente("");
    setTransportista("");
    setVehiculo("");
    setConductor("");
    setObservaciones("");
    setLineas([{ ...lineaVacia }]);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setExito(null);
    setEncolada(false);
    setEnviando(true);
    const payload = {
      cliente: Number(cliente),
      transportista: transportista ? Number(transportista) : null,
      vehiculo: vehiculo ? Number(vehiculo) : null,
      conductor: conductor || null,
      fecha,
      hora,
      estado: "pendiente de inspeccion",
      observaciones: observaciones || null,
      detalles: lineas
        .filter((l) => l.material && l.volumen_m3)
        .map((l) => ({
          material: Number(l.material),
          volumen_m3: l.volumen_m3,
          destino_sugerido: l.destino_sugerido || null,
        })),
    };

    // Sin senal: se guarda en la cola local y se enviara al reconectar (CU-32).
    if (!online) {
      await encolarRecepcion(payload);
      setEncolada(true);
      limpiarFormulario();
      setEnviando(false);
      return;
    }

    try {
      const res = await api.post<Recepcion>("/recepciones/", payload);
      setExito(res.data);
      limpiarFormulario();
    } catch (err) {
      if (isAxiosError(err) && err.response?.data) {
        // Error de validacion del servidor: mostrarlo, no encolar.
        setError(JSON.stringify(err.response.data));
      } else {
        // Fallo de red pese a estar "online": respaldar en la cola local.
        await encolarRecepcion(payload);
        setEncolada(true);
        limpiarFormulario();
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        titulo="Registrar recepcion"
        descripcion="Descarga de un camion. El peso se calcula solo a partir del volumen."
        accion={
          online ? (
            <Badge tono="verde">En linea</Badge>
          ) : (
            <Badge tono="ambar">Sin conexion</Badge>
          )
        }
      />

      {encolada && (
        <div className="mb-4 flex items-start gap-3 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
          <div>
            <p className="font-medium">Recepcion guardada en la cola local.</p>
            <p className="text-amber-700">
              Se enviara automaticamente al recuperar la conexion. Puedes verla
              en "Cola de sincronizacion".
            </p>
          </div>
        </div>
      )}

      {exito && (
        <div className="mb-4 flex items-start gap-3 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800">
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" />
          <div>
            <p className="font-medium">
              Recepcion #{exito.id} registrada ({exito.detalles.length} linea/s).
            </p>
            {exito.detalles.map((d, i) => (
              <p key={i} className="text-brand-700">
                Linea {i + 1}: {d.volumen_m3} m3 → {d.peso_derivado_kg} kg
                {d.chip_derivado_m3 ? ` · ${d.chip_derivado_m3} m3 de chip` : ""}
              </p>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <form onSubmit={onSubmit} className="space-y-4">
        <Card>
          <CardHeader titulo="Datos del camion" />
          <CardBody className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Campo label="Cliente" htmlFor="cliente" requerido>
              <Select
                id="cliente"
                value={cliente}
                onChange={(e) => setCliente(e.target.value)}
                required
              >
                <option value="">Selecciona...</option>
                {clientes.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.razon_social}
                  </option>
                ))}
              </Select>
            </Campo>
            <Campo label="Transportista" htmlFor="transportista">
              <Select
                id="transportista"
                value={transportista}
                onChange={(e) => setTransportista(e.target.value)}
              >
                <option value="">Sin transportista</option>
                {transportistas.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.nombre}
                  </option>
                ))}
              </Select>
            </Campo>
            <Campo label="Vehiculo" htmlFor="vehiculo">
              <Select
                id="vehiculo"
                value={vehiculo}
                onChange={(e) => setVehiculo(e.target.value)}
              >
                <option value="">Sin vehiculo</option>
                {vehiculos.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.patente}
                  </option>
                ))}
              </Select>
            </Campo>
            <Campo label="Conductor" htmlFor="conductor">
              <Input
                id="conductor"
                value={conductor}
                onChange={(e) => setConductor(e.target.value)}
                placeholder="Nombre del conductor"
              />
            </Campo>
            <Campo label="Fecha" htmlFor="fecha" requerido>
              <Input id="fecha" type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} required />
            </Campo>
            <Campo label="Hora" htmlFor="hora" requerido>
              <Input id="hora" type="time" value={hora} onChange={(e) => setHora(e.target.value)} required />
            </Campo>
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            titulo="Material descargado"
            descripcion="Una linea por material. Solo se teclea el volumen."
            accion={
              <Button
                type="button"
                variante="secundario"
                tamano="sm"
                onClick={() => setLineas((p) => [...p, { ...lineaVacia }])}
              >
                <Plus className="h-4 w-4" />
                Agregar linea
              </Button>
            }
          />
          <CardBody className="space-y-3">
            {lineas.map((linea, i) => (
              <div key={i} className="grid grid-cols-12 items-end gap-2">
                <div className="col-span-5">
                  <Campo label={i === 0 ? "Material" : ""} htmlFor={`mat-${i}`} requerido={i === 0}>
                    <Select
                      id={`mat-${i}`}
                      value={linea.material}
                      onChange={(e) => actualizarLinea(i, "material", e.target.value)}
                    >
                      <option value="">Material...</option>
                      {materiales.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.nombre}
                        </option>
                      ))}
                    </Select>
                  </Campo>
                </div>
                <div className="col-span-3">
                  <Campo label={i === 0 ? "Volumen (m3)" : ""} htmlFor={`vol-${i}`}>
                    <Input
                      id={`vol-${i}`}
                      type="number"
                      step="0.01"
                      min="0"
                      value={linea.volumen_m3}
                      onChange={(e) => actualizarLinea(i, "volumen_m3", e.target.value)}
                      placeholder="0.00"
                    />
                  </Campo>
                </div>
                <div className="col-span-3">
                  <Campo label={i === 0 ? "Destino" : ""} htmlFor={`dest-${i}`}>
                    <Select
                      id={`dest-${i}`}
                      value={linea.destino_sugerido}
                      onChange={(e) => actualizarLinea(i, "destino_sugerido", e.target.value)}
                    >
                      <option value="">—</option>
                      <option value="a pila">A pila</option>
                      <option value="a chip">A chip</option>
                      <option value="a venta directa">A venta directa</option>
                    </Select>
                  </Campo>
                </div>
                <div className="col-span-1 pb-1">
                  {lineas.length > 1 && (
                    <button
                      type="button"
                      onClick={() => setLineas((p) => p.filter((_, idx) => idx !== i))}
                      className="rounded p-2 text-slate-400 hover:bg-red-50 hover:text-red-600"
                      aria-label="Quitar linea"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
            <p className="text-xs text-slate-500">
              <Badge tono="azul">Automatico</Badge>{" "}
              El peso en kilos lo calcula el servidor con la densidad de cada
              material; no hay balanza en terreno.
            </p>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Campo label="Observaciones" htmlFor="observaciones">
              <Textarea
                id="observaciones"
                value={observaciones}
                onChange={(e) => setObservaciones(e.target.value)}
                placeholder="Notas de la descarga (opcional)"
              />
            </Campo>
          </CardBody>
        </Card>

        <div className="flex justify-end gap-2">
          <Button type="submit" disabled={enviando}>
            <Truck className="h-4 w-4" />
            {enviando
              ? "Guardando..."
              : online
                ? "Registrar recepcion"
                : "Guardar en cola"}
          </Button>
        </div>
      </form>
    </div>
  );
}
