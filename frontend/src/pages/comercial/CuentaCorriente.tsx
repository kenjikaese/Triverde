import { useCallback, useEffect, useState } from "react";
import { Wallet } from "lucide-react";
import { api } from "@/lib/api";
import type { Cliente, CuentaCorriente as Cuenta } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";
import { clp, fecha as formatoFecha } from "@/lib/formato";

// CU-64: el saldo lo calcula el servidor (ventas - cobros); esta vista no
// suma nada. CU-62: el estado de pago es el indicador manual que el
// administrador concilia aparte.
export function CuentaCorriente() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [clienteSel, setClienteSel] = useState("");
  const [rango, setRango] = useState({ desde: "", hasta: "" });
  const [cuenta, setCuenta] = useState<Cuenta | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [estadoPago, setEstadoPago] = useState("");
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    api
      .get<Cliente[]>("/clientes/")
      .then((res) => setClientes(res.data))
      .catch(() => setError("No se pudo cargar la lista de clientes."));
  }, []);

  const cargar = useCallback(() => {
    if (!clienteSel) {
      setCuenta(null);
      return;
    }
    setCargando(true);
    setError(null);
    const params: Record<string, string> = {};
    if (rango.desde) params.desde = rango.desde;
    if (rango.hasta) params.hasta = rango.hasta;
    api
      .get<Cuenta>(`/cuenta-corriente/${clienteSel}/`, { params })
      .then((res) => {
        setCuenta(res.data);
        setEstadoPago(res.data.estado_pago);
      })
      .catch(() => setError("No se pudo cargar la cuenta corriente."))
      .finally(() => setCargando(false));
  }, [clienteSel, rango]);

  useEffect(cargar, [cargar]);

  async function guardarEstadoPago() {
    if (!cuenta) return;
    setGuardando(true);
    setError(null);
    setAviso(null);
    try {
      await api.patch(`/cuenta-corriente/${cuenta.cliente}/`, {
        estado_pago: estadoPago,
      });
      setAviso("Estado de pago actualizado.");
      cargar();
    } catch (err: unknown) {
      const datos = (
        err as {
          response?: { data?: { detalle?: string; estado_pago?: string } };
        }
      ).response?.data;
      setError(
        datos?.detalle ??
          datos?.estado_pago ??
          "No se pudo actualizar el estado de pago.",
      );
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div>
      <PageHeader
        titulo="Cuenta corriente"
        descripcion="Saldo del cliente calculado a partir de sus ventas y cobros."
      />

      {error && (
        <div
          className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
          data-testid="error-cuenta"
        >
          {error}
        </div>
      )}
      {aviso && (
        <div
          className="mb-4 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800"
          data-testid="aviso-cuenta"
        >
          {aviso}
        </div>
      )}

      <Card className="mb-5 p-4">
        <div className="grid gap-3 md:grid-cols-3">
          <Campo label="Cliente" htmlFor="cuenta_cliente" requerido>
            <Select
              id="cuenta_cliente"
              value={clienteSel}
              onChange={(e) => setClienteSel(e.target.value)}
            >
              <option value="">Selecciona un cliente</option>
              {clientes.map((cliente) => (
                <option key={cliente.id} value={cliente.id}>
                  {cliente.razon_social}
                </option>
              ))}
            </Select>
          </Campo>
          <Campo label="Desde" htmlFor="cuenta_desde">
            <Input
              id="cuenta_desde"
              type="date"
              value={rango.desde}
              onChange={(e) => setRango({ ...rango, desde: e.target.value })}
            />
          </Campo>
          <Campo label="Hasta" htmlFor="cuenta_hasta">
            <Input
              id="cuenta_hasta"
              type="date"
              value={rango.hasta}
              onChange={(e) => setRango({ ...rango, hasta: e.target.value })}
            />
          </Campo>
        </div>
      </Card>

      {!clienteSel ? (
        <Card>
          <CardBody>
            <p className="text-sm text-slate-400">
              Selecciona un cliente para ver su saldo y sus movimientos.
            </p>
          </CardBody>
        </Card>
      ) : cargando ? (
        <Card>
          <CardBody>
            <p className="text-sm text-slate-400">Cargando...</p>
          </CardBody>
        </Card>
      ) : (
        cuenta && (
          <>
            <div className="mb-5 grid gap-4 md:grid-cols-3">
              <Card>
                <CardBody>
                  <p className="text-xs uppercase tracking-wide text-slate-500">
                    Total vendido
                  </p>
                  <p
                    className="mt-1 text-xl font-semibold text-slate-800"
                    data-testid="total-ventas"
                  >
                    {clp(cuenta.total_ventas)}
                  </p>
                </CardBody>
              </Card>
              <Card>
                <CardBody>
                  <p className="text-xs uppercase tracking-wide text-slate-500">
                    Total cobrado
                  </p>
                  <p
                    className="mt-1 text-xl font-semibold text-slate-800"
                    data-testid="total-cobros"
                  >
                    {clp(cuenta.total_cobros)}
                  </p>
                </CardBody>
              </Card>
              <Card>
                <CardBody>
                  <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500">
                    <Wallet className="h-4 w-4" />
                    Saldo pendiente
                  </div>
                  <p
                    className="mt-1 text-xl font-semibold text-slate-900"
                    data-testid="saldo"
                  >
                    {clp(cuenta.saldo)}
                  </p>
                </CardBody>
              </Card>
            </div>

            <Card className="mb-5">
              <CardHeader
                titulo="Estado de pago"
                descripcion="Indicador manual para dejar constancia de acuerdos o pagos resueltos fuera del sistema."
              />
              <CardBody>
                <div className="flex flex-wrap items-end gap-3">
                  <Badge tono={tonoEstado(cuenta.estado_pago)}>
                    {cuenta.estado_pago}
                  </Badge>
                  <div className="w-52">
                    <Campo label="Nuevo estado" htmlFor="cuenta_estado_pago">
                      <Select
                        id="cuenta_estado_pago"
                        value={estadoPago}
                        onChange={(e) => setEstadoPago(e.target.value)}
                      >
                        <option value="al dia">Al día</option>
                        <option value="con deuda">Con deuda</option>
                      </Select>
                    </Campo>
                  </div>
                  <Button onClick={guardarEstadoPago} disabled={guardando}>
                    {guardando ? "Guardando..." : "Actualizar estado de pago"}
                  </Button>
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardHeader titulo="Movimientos" />
              <Table>
                <thead>
                  <tr>
                    <Th>Fecha</Th>
                    <Th>Tipo</Th>
                    <Th>Detalle</Th>
                    <Th>Monto</Th>
                  </tr>
                </thead>
                <TBody>
                  {cuenta.movimientos.length === 0 ? (
                    <EmptyRow
                      colSpan={4}
                      texto="No hay movimientos en el rango consultado."
                    />
                  ) : (
                    cuenta.movimientos.map((movimiento) => (
                      <tr
                        key={`${movimiento.tipo}-${movimiento.id}`}
                        data-testid="fila-movimiento"
                      >
                        <Td>{formatoFecha(movimiento.fecha)}</Td>
                        <Td>
                          <Badge
                            tono={movimiento.tipo === "venta" ? "azul" : "verde"}
                          >
                            {movimiento.tipo}
                          </Badge>
                        </Td>
                        <Td>{movimiento.detalle}</Td>
                        <Td className="font-medium">{clp(movimiento.monto)}</Td>
                      </tr>
                    ))
                  )}
                </TBody>
              </Table>
            </Card>
          </>
        )
      )}
    </div>
  );
}
