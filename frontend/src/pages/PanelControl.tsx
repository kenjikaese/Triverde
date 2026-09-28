import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Truck,
  Users,
  Boxes,
  AlertTriangle,
  ArrowRight,
  Layers,
  ShoppingCart,
  SlidersHorizontal,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type {
  Cliente,
  IndicadorPanel,
  Panel,
  PreferenciasPanel,
  Recepcion,
} from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { cantidad, clp, fecha } from "@/lib/formato";
import { mensajeDeError } from "@/lib/errores";

// V_PanelControl (CU-72, CU-77). El administrador ve los bloques que eligio
// (inventario, produccion, ventas) armados por el servidor y los personaliza
// desde un modal. El resto de los roles ve el resumen operativo de Inc 1.

function Tile({
  icono: Icono,
  etiqueta,
  valor,
  tono,
}: {
  icono: LucideIcon;
  etiqueta: string;
  valor: string | number;
  tono: string;
}) {
  return (
    <Card>
      <CardBody className="flex items-center gap-4">
        <div className={`flex h-11 w-11 items-center justify-center rounded-lg ${tono}`}>
          <Icono className="h-5 w-5" />
        </div>
        <div>
          <p className="text-2xl font-semibold text-slate-900">{valor}</p>
          <p className="text-sm text-slate-500">{etiqueta}</p>
        </div>
      </CardBody>
    </Card>
  );
}

// Una pila que no cierra su ciclo se marca "En proceso" (CU-72 Excepcion 3),
// indicando su estado real cuando es otro (en formacion, en reposo).
function etiquetaPila(pila: { estado: string; estado_nombre: string; en_proceso: boolean }) {
  if (!pila.en_proceso || pila.estado === "en proceso") return pila.estado_nombre;
  return `En proceso (${pila.estado_nombre.toLowerCase()})`;
}

function VerMas({ a }: { a: string }) {
  return (
    <Link
      to={a}
      className="inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:text-brand-800"
    >
      Ver detalle <ArrowRight className="h-4 w-4" />
    </Link>
  );
}

export function PanelControl() {
  const { usuario } = useAuth();
  const nombre = usuario?.nombre_completo?.split(" ")[0] ?? "";

  return usuario?.rol_nombre === "Administrador" ? (
    <PanelAdministrador nombre={nombre} />
  ) : (
    <ResumenOperacion nombre={nombre} />
  );
}

function PanelAdministrador({ nombre }: { nombre: string }) {
  const [panel, setPanel] = useState<Panel | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [personalizando, setPersonalizando] = useState(false);

  const cargar = useCallback(() => {
    api
      .get<Panel>("/panel/")
      .then((r) => {
        setPanel(r.data);
        setError(null);
      })
      .catch((err) => setError(mensajeDeError(err, "No se pudo cargar el panel de control.")));
  }, []);

  useEffect(cargar, [cargar]);

  const { inventario, produccion, ventas } = panel?.bloques ?? {};

  return (
    <div>
      <PageHeader
        titulo={`Hola, ${nombre}`}
        descripcion="Panel de control: inventario, produccion y ventas de un vistazo."
        accion={
          <Button variante="secundario" onClick={() => setPersonalizando(true)}>
            <SlidersHorizontal className="h-4 w-4" /> Personalizar
          </Button>
        }
      />

      {error && (
        <div className="mb-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">{error}</div>
      )}
      {aviso && (
        <div className="mb-4 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800">{aviso}</div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {inventario && (
          <Tile
            icono={Boxes}
            etiqueta="m³ en inventario"
            valor={cantidad(inventario.total_m3)}
            tono="bg-earth-100 text-earth-700"
          />
        )}
        {produccion && (
          <Tile
            icono={Layers}
            etiqueta="Pilas en proceso"
            valor={produccion.pilas_en_proceso}
            tono="bg-amber-100 text-amber-700"
          />
        )}
        {ventas && (
          <Tile
            icono={ShoppingCart}
            etiqueta={`Vendido en el mes (${ventas.cantidad} ${ventas.cantidad === 1 ? "venta" : "ventas"})`}
            valor={clp(ventas.total_vendido)}
            tono="bg-brand-100 text-brand-700"
          />
        )}
      </div>

      {inventario && (
        <Card className="mt-6">
          <CardHeader titulo="Inventario por material y etapa" accion={<VerMas a="/inventario" />} />
          <Table>
            <thead>
              <tr>
                <Th>Material</Th>
                <Th>Etapa</Th>
                <Th className="text-right">Volumen</Th>
              </tr>
            </thead>
            <TBody>
              {inventario.filas.length === 0 ? (
                <EmptyRow colSpan={3} texto="Sin existencias: el inventario esta en cero." />
              ) : (
                inventario.filas.map((fila) => (
                  <tr key={`${fila.material}-${fila.etapa}`}>
                    <Td className="font-medium text-slate-800">{fila.material}</Td>
                    <Td>{fila.etapa_nombre}</Td>
                    <Td className="text-right">{cantidad(fila.volumen_m3)} m³</Td>
                  </tr>
                ))
              )}
            </TBody>
          </Table>
        </Card>
      )}

      {produccion && (
        <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
          <Card>
            <CardHeader titulo="Pilas recientes" accion={<VerMas a="/pilas" />} />
            <Table>
              <thead>
                <tr>
                  <Th>Pila</Th>
                  <Th>Inicio</Th>
                  <Th>Estado</Th>
                  <Th className="text-right">Volumen</Th>
                </tr>
              </thead>
              <TBody>
                {produccion.pilas.length === 0 ? (
                  <EmptyRow colSpan={4} texto="Aun no hay pilas registradas." />
                ) : (
                  produccion.pilas.map((pila) => (
                    <tr key={pila.pila_id}>
                      <Td className="whitespace-nowrap font-medium text-slate-800">{pila.codigo}</Td>
                      <Td className="whitespace-nowrap">{fecha(pila.fecha_inicio)}</Td>
                      <Td>
                        <Badge tono={pila.en_proceso ? "ambar" : "gris"}>
                          {etiquetaPila(pila)}
                        </Badge>
                      </Td>
                      <Td className="text-right">{cantidad(pila.volumen_m3)} m³</Td>
                    </tr>
                  ))
                )}
              </TBody>
            </Table>
          </Card>

          <Card>
            <CardHeader titulo="Procesos recientes" accion={<VerMas a="/pilas" />} />
            <Table>
              <thead>
                <tr>
                  <Th>Fecha</Th>
                  <Th>Proceso</Th>
                  <Th>Pila o material</Th>
                  <Th className="text-right">Volumen</Th>
                </tr>
              </thead>
              <TBody>
                {produccion.procesos.length === 0 ? (
                  <EmptyRow colSpan={4} texto="Aun no hay procesos registrados." />
                ) : (
                  produccion.procesos.map((proceso) => (
                    <tr key={proceso.proceso_id}>
                      <Td className="whitespace-nowrap">{fecha(proceso.fecha.slice(0, 10))}</Td>
                      <Td>{proceso.tipo_nombre}</Td>
                      <Td>{proceso.pila ?? proceso.material ?? "Planta"}</Td>
                      <Td className="text-right">
                        {proceso.volumen_m3 === null ? "—" : `${cantidad(proceso.volumen_m3)} m³`}
                      </Td>
                    </tr>
                  ))
                )}
              </TBody>
            </Table>
          </Card>
        </div>
      )}

      {ventas && (
        <Card className="mt-6">
          <CardHeader
            titulo="Ventas del mes en curso"
            descripcion={`Del ${fecha(ventas.desde)} al ${fecha(ventas.hasta)}`}
            accion={<VerMas a="/ventas" />}
          />
          <CardBody>
            {ventas.cantidad === 0 ? (
              <p className="text-sm text-slate-500">Aun no hay ventas este mes: total $0.</p>
            ) : (
              <p className="text-sm text-slate-600">
                {ventas.cantidad} {ventas.cantidad === 1 ? "venta" : "ventas"} por un total de{" "}
                <span className="font-semibold text-slate-900">{clp(ventas.total_vendido)}</span>.
              </p>
            )}
          </CardBody>
        </Card>
      )}

      <PersonalizarPanel
        abierto={personalizando}
        onCerrar={() => setPersonalizando(false)}
        onGuardado={(mensaje) => {
          setPersonalizando(false);
          setAviso(mensaje);
          cargar();
        }}
      />
    </div>
  );
}

// CU-77: listado completo de indicadores con los activos marcados. El servidor
// rechaza guardar sin ninguno y avisa si la seleccion no cambio.
function PersonalizarPanel({
  abierto,
  onCerrar,
  onGuardado,
}: {
  abierto: boolean;
  onCerrar: () => void;
  onGuardado: (mensaje: string) => void;
}) {
  const [disponibles, setDisponibles] = useState<IndicadorPanel[]>([]);
  const [seleccion, setSeleccion] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (!abierto) return;
    setError(null);
    setAviso(null);
    api
      .get<PreferenciasPanel>("/panel/preferencias/")
      .then((r) => {
        setDisponibles(r.data.disponibles);
        setSeleccion(r.data.indicadores_visibles);
      })
      .catch((err) => setError(mensajeDeError(err, "No se pudieron cargar las preferencias.")));
  }, [abierto]);

  const alternar = (clave: string) =>
    setSeleccion((actual) =>
      actual.includes(clave) ? actual.filter((c) => c !== clave) : [...actual, clave],
    );

  const guardar = async () => {
    setGuardando(true);
    setError(null);
    setAviso(null);
    try {
      const r = await api.post<PreferenciasPanel>("/panel/preferencias/", {
        indicadores_visibles: seleccion,
      });
      if (r.data.cambio) {
        onGuardado("Preferencias guardadas. El panel muestra los indicadores elegidos.");
      } else {
        setAviso("No hubo cambios en la seleccion; el panel se mantiene igual.");
      }
    } catch (err) {
      setError(mensajeDeError(err, "No se pudieron guardar las preferencias."));
    } finally {
      setGuardando(false);
    }
  };

  return (
    <Modal abierto={abierto} titulo="Personalizar panel de control" onCerrar={onCerrar}>
      <p className="mb-4 text-sm text-slate-500">
        Elige los indicadores que quieres ver en el panel. Debe quedar al menos uno activo.
      </p>
      <div className="space-y-2">
        {disponibles.map((indicador) => (
          <label
            key={indicador.clave}
            className="flex cursor-pointer items-center gap-3 rounded-lg border border-slate-200 px-4 py-3 hover:bg-slate-50"
          >
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300 text-brand-700 focus:ring-brand-600"
              checked={seleccion.includes(indicador.clave)}
              onChange={() => alternar(indicador.clave)}
            />
            <span className="text-sm text-slate-700">{indicador.nombre}</span>
          </label>
        ))}
      </div>

      {error && <p className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      {aviso && <p className="mt-4 rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-600">{aviso}</p>}

      <div className="mt-5 flex justify-end gap-2">
        <Button variante="secundario" onClick={onCerrar}>
          Cancelar
        </Button>
        <Button onClick={guardar} disabled={guardando}>
          {guardando ? "Guardando..." : "Guardar preferencias"}
        </Button>
      </div>
    </Modal>
  );
}

// Resumen operativo de Inc 1 para Operador y Transportista (el panel de
// control CU-72 es solo del administrador).
function ResumenOperacion({ nombre }: { nombre: string }) {
  const [recepciones, setRecepciones] = useState<Recepcion[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [sinDatos, setSinDatos] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get<Recepcion[]>("/recepciones/"),
      api.get<Cliente[]>("/clientes/"),
    ])
      .then(([r, c]) => {
        setRecepciones(r.data);
        setClientes(c.data);
      })
      .catch(() => setSinDatos(true));
  }, []);

  const pendientes = recepciones.filter(
    (r) => r.estado === "pendiente de inspeccion",
  ).length;

  return (
    <div>
      <PageHeader titulo={`Hola, ${nombre}`} descripcion="Resumen de la operacion de hoy." />

      {sinDatos && (
        <div className="mb-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
          No se pudo cargar la informacion en vivo. Verifica que el backend este
          corriendo en <code>localhost:8000</code>.
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Tile icono={Truck} etiqueta="Recepciones" valor={recepciones.length} tono="bg-brand-100 text-brand-700" />
        <Tile icono={AlertTriangle} etiqueta="Por inspeccionar" valor={pendientes} tono="bg-amber-100 text-amber-700" />
        <Tile icono={Users} etiqueta="Clientes activos" valor={clientes.filter((c) => c.estado === "activo").length} tono="bg-sky-100 text-sky-700" />
        <Tile icono={Boxes} etiqueta="Materiales" valor="—" tono="bg-earth-100 text-earth-700" />
      </div>

      <Card className="mt-6">
        <CardHeader titulo="Ultimas recepciones" accion={<VerMas a="/recepcion" />} />
        <Table>
          <thead>
            <tr>
              <Th>Fecha</Th>
              <Th>Cliente</Th>
              <Th>Estado</Th>
              <Th>Sincronizacion</Th>
            </tr>
          </thead>
          <TBody>
            {recepciones.length === 0 ? (
              <EmptyRow colSpan={4} texto="Aun no hay recepciones registradas." />
            ) : (
              recepciones.slice(0, 6).map((r) => (
                <tr key={r.id}>
                  <Td>{r.fecha}</Td>
                  <Td>#{r.cliente}</Td>
                  <Td>
                    <Badge tono={tonoEstado(r.estado)}>{r.estado}</Badge>
                  </Td>
                  <Td>
                    <Badge tono={tonoEstado(r.estado_sincronizacion)}>
                      {r.estado_sincronizacion}
                    </Badge>
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
