import { useEffect, useState } from "react";
import { AlertTriangle, Info, Layers, Package, Waypoints } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import type { TrazabilidadVenta, Venta } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Campo, Select } from "@/components/ui/Field";
import { cantidad as formatoCantidad, fecha as formatoFecha } from "@/lib/formato";
import { mensajeDeError } from "@/lib/errores";

// CU-68: reconstruye la cadena de un lote entregado a partir de la venta.
// La cadena la arma el servidor en /ventas/{id}/trazabilidad/; esta vista solo
// la presenta. Llega con certeza hasta la composicion de la pila: el modelo de
// datos no registra que recepcion aporto el material a cada pila.
export function TrazabilidadLote() {
  const [params, setParams] = useSearchParams();
  const ventaSel = params.get("venta") ?? "";
  const [ventas, setVentas] = useState<Venta[]>([]);
  const [traza, setTraza] = useState<TrazabilidadVenta | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Venta[]>("/ventas/")
      .then((res) => setVentas(res.data))
      .catch((err) =>
        setError(mensajeDeError(err, "No se pudo cargar la lista de ventas.")),
      );
  }, []);

  useEffect(() => {
    if (!ventaSel) {
      setTraza(null);
      return;
    }
    setCargando(true);
    setError(null);
    api
      .get<TrazabilidadVenta>(`/ventas/${ventaSel}/trazabilidad/`)
      .then((res) => setTraza(res.data))
      .catch((err) => {
        setTraza(null);
        setError(mensajeDeError(err, "No se pudo reconstruir la trazabilidad del lote."));
      })
      .finally(() => setCargando(false));
  }, [ventaSel]);

  const lineasConPila = traza?.lineas.filter((linea) => linea.pila) ?? [];

  return (
    <div>
      <PageHeader
        titulo="Trazabilidad de lote entregado"
        descripcion="Cadena de origen de un producto vendido: la venta, la pila de la que salió y el material que la compuso."
      />

      <Card>
        <CardBody>
          <div className="max-w-md">
            <Campo label="Venta a trazar" htmlFor="traza_venta">
              <Select
                id="traza_venta"
                value={ventaSel}
                onChange={(e) =>
                  setParams(e.target.value ? { venta: e.target.value } : {})
                }
              >
                <option value="">Selecciona una venta</option>
                {ventas.map((venta) => (
                  <option key={venta.id} value={venta.id}>
                    Venta #{venta.id} · {venta.cliente_razon_social} ·{" "}
                    {formatoFecha(venta.fecha)}
                  </option>
                ))}
              </Select>
            </Campo>
          </div>
        </CardBody>
      </Card>

      {error && (
        <div
          className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
          data-testid="error-trazabilidad"
        >
          {error}
        </div>
      )}

      {cargando && <p className="mt-4 text-sm text-slate-500">Reconstruyendo la cadena...</p>}

      {traza && !cargando && (
        <div className="mt-6 space-y-5">
          {traza.advertencias.map((advertencia) => (
            <div
              key={advertencia}
              className="flex items-start gap-2 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800"
              data-testid="advertencia-trazabilidad"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              {advertencia}
            </div>
          ))}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Card>
              <CardBody className="flex items-center gap-4">
                <Package className="h-8 w-8 text-brand-700" />
                <div>
                  <p className="text-lg font-semibold text-slate-900">
                    Venta #{traza.venta}
                  </p>
                  <p className="text-sm text-slate-500">
                    {traza.cliente} · {formatoFecha(traza.fecha)} ·{" "}
                    <Badge tono={tonoEstado(traza.estado)}>{traza.estado}</Badge>
                  </p>
                </div>
              </CardBody>
            </Card>
            <Card>
              <CardBody className="flex items-center gap-4">
                <Layers className="h-8 w-8 text-amber-700" />
                <div>
                  <p className="text-lg font-semibold text-slate-900">
                    {lineasConPila.length} de {traza.lineas.length} líneas trazables
                  </p>
                  <p className="text-sm text-slate-500">Con pila de origen registrada</p>
                </div>
              </CardBody>
            </Card>
          </div>

          {traza.lineas.map((linea) => (
            <Card key={linea.detalle}>
              <CardHeader
                titulo={`${linea.producto} · ${formatoCantidad(linea.cantidad)} ${linea.unidad}`}
                descripcion={
                  linea.pila
                    ? `Pila de origen ${linea.pila.codigo}, iniciada el ${formatoFecha(linea.pila.fecha_inicio)}`
                    : "Sin pila de origen registrada"
                }
                accion={
                  linea.pila ? (
                    <Badge tono={tonoEstado(linea.pila.estado)}>{linea.pila.estado}</Badge>
                  ) : (
                    <Waypoints className="h-5 w-5 text-slate-400" />
                  )
                }
              />
              {linea.pila && (
                <>
                  <Table>
                    <thead>
                      <tr>
                        <Th>Descarga de origen</Th>
                        <Th>Cliente generador</Th>
                        <Th>Fecha</Th>
                        <Th>Material</Th>
                        <Th>Volumen aportado</Th>
                      </tr>
                    </thead>
                    <TBody>
                      {linea.pila.recepciones_origen.length === 0 ? (
                        <EmptyRow
                          colSpan={5}
                          texto="Sin descargas de origen registradas: la cadena llega hasta la composición de la pila."
                        />
                      ) : (
                        linea.pila.recepciones_origen.map((origen, indice) => (
                          <tr
                            key={`${origen.recepcion}-${indice}`}
                            data-testid="recepcion-origen"
                          >
                            <Td className="font-medium text-slate-800">
                              Recepción #{origen.recepcion}
                            </Td>
                            <Td>{origen.cliente}</Td>
                            <Td>{formatoFecha(origen.fecha)}</Td>
                            <Td>{origen.material}</Td>
                            <Td className="font-medium text-brand-800">
                              {formatoCantidad(origen.volumen_m3)} m³
                            </Td>
                          </tr>
                        ))
                      )}
                    </TBody>
                  </Table>
                  <div className="border-t border-slate-100 px-5 py-3 text-xs font-medium uppercase tracking-wide text-slate-400">
                    Composición total de la pila
                  </div>
                  <Table>
                    <thead>
                      <tr>
                        <Th>Material incorporado a la pila</Th>
                        <Th>Volumen</Th>
                      </tr>
                    </thead>
                    <TBody>
                      {linea.pila.composicion.length === 0 ? (
                        <EmptyRow colSpan={2} texto="La pila aún no tiene composición registrada." />
                      ) : (
                        linea.pila.composicion.map((item) => (
                          <tr key={item.material} data-testid="composicion-pila">
                            <Td className="font-medium text-slate-800">{item.material}</Td>
                            <Td className="font-medium text-brand-800">
                              {formatoCantidad(item.volumen_m3)} m³
                            </Td>
                          </tr>
                        ))
                      )}
                    </TBody>
                  </Table>
                </>
              )}
            </Card>
          ))}

          {lineasConPila.length > 0 && (
            <div className="flex items-start gap-2 rounded-lg bg-slate-50 px-4 py-3 text-xs text-slate-600">
              <Info className="mt-0.5 h-4 w-4 shrink-0" />
              Las descargas de origen se registran al componer la pila indicando
              de qué recepción sale el material. Una pila compuesta sin ese dato
              solo muestra su composición total.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
