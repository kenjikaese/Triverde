import { useCallback, useEffect, useState, type FormEvent } from "react";
import { FileText, Receipt } from "lucide-react";
import { api } from "@/lib/api";
import type {
  Cliente,
  Cobro,
  DocumentoTributario,
  Recepcion,
  SugerenciaCobro,
} from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { clp, fecha as formatoFecha } from "@/lib/formato";

// CU-61: el cobro de una recepcion se apoya en la tarifa configurada para el
// tramo del camion. El monto sugerido lo calcula el servidor
// (/cobros/sugerencia/); el operador lo confirma o lo ajusta.
export function Cobros() {
  const [cobros, setCobros] = useState<Cobro[]>([]);
  const [recepciones, setRecepciones] = useState<Recepcion[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [cobrando, setCobrando] = useState<Recepcion | null>(null);
  const [sugerencia, setSugerencia] = useState<SugerenciaCobro | null>(null);
  const [formCobro, setFormCobro] = useState({
    monto: "",
    medio: "efectivo",
    fecha: new Date().toISOString().slice(0, 10),
  });
  const [guardando, setGuardando] = useState(false);
  const [errorCobro, setErrorCobro] = useState<string | null>(null);

  const [documentando, setDocumentando] = useState<Cobro | null>(null);
  const [formDocumento, setFormDocumento] = useState({
    tipo: "boleta",
    folio: "",
    monto: "",
  });
  const [errorDocumento, setErrorDocumento] = useState<string | null>(null);

  const nombreCliente = useCallback(
    (id: number) =>
      clientes.find((cliente) => cliente.id === id)?.razon_social ?? `#${id}`,
    [clientes],
  );

  const cargar = useCallback(() => {
    setCargando(true);
    setError(null);
    Promise.all([
      api.get<Cobro[]>("/cobros/"),
      api.get<Recepcion[]>("/recepciones/", { params: { estado: "recibida" } }),
    ])
      .then(([listaCobros, listaRecepciones]) => {
        setCobros(listaCobros.data);
        setRecepciones(listaRecepciones.data);
      })
      .catch(() => setError("No se pudieron cargar los cobros."))
      .finally(() => setCargando(false));
  }, []);

  useEffect(() => {
    api
      .get<Cliente[]>("/clientes/")
      .then((res) => setClientes(res.data))
      .catch(() => undefined);
  }, []);

  useEffect(cargar, [cargar]);

  async function abrirCobro(recepcion: Recepcion) {
    setCobrando(recepcion);
    setErrorCobro(null);
    setSugerencia(null);
    setFormCobro({
      monto: "",
      medio: "efectivo",
      fecha: new Date().toISOString().slice(0, 10),
    });
    try {
      const res = await api.get<SugerenciaCobro>("/cobros/sugerencia/", {
        params: { recepcion: recepcion.id },
      });
      setSugerencia(res.data);
      if (res.data.monto_sugerido) {
        setFormCobro((actual) => ({
          ...actual,
          monto: res.data.monto_sugerido as string,
        }));
      }
    } catch {
      setErrorCobro("No se pudo obtener el monto sugerido.");
    }
  }

  async function registrarCobro(e: FormEvent) {
    e.preventDefault();
    if (!cobrando) return;
    setGuardando(true);
    setErrorCobro(null);
    try {
      await api.post("/cobros/", {
        recepcion: cobrando.id,
        cliente: cobrando.cliente,
        monto: formCobro.monto,
        medio: formCobro.medio,
        fecha: formCobro.fecha,
      });
      setCobrando(null);
      cargar();
    } catch (err: unknown) {
      const datos = (
        err as { response?: { data?: { detalle?: string; monto?: string[] } } }
      ).response?.data;
      setErrorCobro(
        datos?.detalle ?? datos?.monto?.[0] ?? "No se pudo registrar el cobro.",
      );
    } finally {
      setGuardando(false);
    }
  }

  async function registrarDocumento(e: FormEvent) {
    e.preventDefault();
    if (!documentando) return;
    setGuardando(true);
    setErrorDocumento(null);
    try {
      await api.post<DocumentoTributario>("/documentos-tributarios/", {
        cobro: documentando.id,
        cliente: documentando.cliente,
        tipo: formDocumento.tipo,
        folio: formDocumento.folio || null,
        monto: formDocumento.monto,
        fecha: new Date().toISOString().slice(0, 10),
      });
      setDocumentando(null);
    } catch (err: unknown) {
      const datos = (err as { response?: { data?: unknown } }).response?.data;
      setErrorDocumento(
        typeof datos === "object" && datos !== null
          ? JSON.stringify(datos)
          : "No se pudo registrar el documento tributario.",
      );
    } finally {
      setGuardando(false);
    }
  }

  const cobradas = new Set(
    cobros.filter((cobro) => cobro.recepcion).map((cobro) => cobro.recepcion),
  );
  const porCobrar = recepciones.filter(
    (recepcion) => !cobradas.has(recepcion.id),
  );

  return (
    <div>
      <PageHeader
        titulo="Cobros"
        descripcion="Cobro de las recepciones recibidas, según la tarifa del tramo del camión."
      />

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <Card className="mb-5">
        <CardHeader
          titulo="Recepciones por cobrar"
          descripcion="Recepciones recibidas que aún no tienen un cobro registrado."
        />
        <Table>
          <thead>
            <tr>
              <Th>Recepción</Th>
              <Th>Fecha</Th>
              <Th>Cliente</Th>
              <Th>Acciones</Th>
            </tr>
          </thead>
          <TBody>
            {cargando ? (
              <EmptyRow colSpan={4} texto="Cargando..." />
            ) : porCobrar.length === 0 ? (
              <EmptyRow colSpan={4} texto="No hay recepciones pendientes de cobro." />
            ) : (
              porCobrar.map((recepcion) => (
                <tr
                  key={recepcion.id}
                  className="hover:bg-slate-50"
                  data-testid="fila-por-cobrar"
                >
                  <Td className="font-medium text-slate-800">{recepcion.id}</Td>
                  <Td>{formatoFecha(recepcion.fecha)}</Td>
                  <Td>{nombreCliente(recepcion.cliente)}</Td>
                  <Td>
                    <Button
                      variante="secundario"
                      tamano="sm"
                      onClick={() => abrirCobro(recepcion)}
                    >
                      <Receipt className="h-4 w-4" />
                      Registrar cobro
                    </Button>
                  </Td>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      </Card>

      <Card>
        <CardHeader titulo="Cobros registrados" />
        <Table>
          <thead>
            <tr>
              <Th>N.°</Th>
              <Th>Fecha</Th>
              <Th>Cliente</Th>
              <Th>Origen</Th>
              <Th>Medio</Th>
              <Th>Monto</Th>
              <Th>Acciones</Th>
            </tr>
          </thead>
          <TBody>
            {cargando ? (
              <EmptyRow colSpan={7} texto="Cargando..." />
            ) : cobros.length === 0 ? (
              <EmptyRow colSpan={7} texto="Todavía no hay cobros registrados." />
            ) : (
              cobros.map((cobro) => (
                <tr
                  key={cobro.id}
                  className="hover:bg-slate-50"
                  data-testid="fila-cobro"
                >
                  <Td className="font-medium text-slate-800">{cobro.id}</Td>
                  <Td>{formatoFecha(cobro.fecha)}</Td>
                  <Td>{nombreCliente(cobro.cliente)}</Td>
                  <Td className="text-slate-600">
                    {cobro.recepcion
                      ? `Recepción ${cobro.recepcion}`
                      : `Venta ${cobro.venta}`}
                  </Td>
                  <Td>{cobro.medio ?? "—"}</Td>
                  <Td className="font-medium">{clp(cobro.monto)}</Td>
                  <Td>
                    <Button
                      variante="fantasma"
                      tamano="sm"
                      onClick={() => {
                        setDocumentando(cobro);
                        setErrorDocumento(null);
                        setFormDocumento({
                          tipo: "boleta",
                          folio: "",
                          monto: cobro.monto,
                        });
                      }}
                    >
                      <FileText className="h-4 w-4" />
                      Documento
                    </Button>
                  </Td>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      </Card>

      <Modal
        abierto={cobrando !== null}
        titulo={`Cobrar la recepción ${cobrando?.id ?? ""}`}
        onCerrar={() => setCobrando(null)}
      >
        <form onSubmit={registrarCobro} className="space-y-4">
          {errorCobro && (
            <div
              className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
              data-testid="error-cobro"
            >
              {errorCobro}
            </div>
          )}
          {sugerencia && sugerencia.monto_sugerido === null && (
            <div
              className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800"
              data-testid="aviso-sin-tarifa"
            >
              No hay una tarifa configurada para el tramo de este vehículo.
              Ingresa el monto manualmente.
            </div>
          )}
          <Campo
            label="Monto"
            htmlFor="cobro_monto"
            ayuda={
              sugerencia?.monto_sugerido
                ? `Monto sugerido por la tarifa del tramo: ${clp(sugerencia.monto_sugerido)}`
                : undefined
            }
            requerido
          >
            <Input
              id="cobro_monto"
              type="number"
              step="0.01"
              min="0.01"
              value={formCobro.monto}
              onChange={(e) =>
                setFormCobro({ ...formCobro, monto: e.target.value })
              }
              required
            />
          </Campo>
          <Campo label="Forma de pago" htmlFor="cobro_medio">
            <Select
              id="cobro_medio"
              value={formCobro.medio}
              onChange={(e) =>
                setFormCobro({ ...formCobro, medio: e.target.value })
              }
            >
              <option value="efectivo">Efectivo</option>
              <option value="transferencia">Transferencia</option>
              <option value="cheque">Cheque</option>
            </Select>
          </Campo>
          <Campo label="Fecha" htmlFor="cobro_fecha" requerido>
            <Input
              id="cobro_fecha"
              type="date"
              value={formCobro.fecha}
              onChange={(e) =>
                setFormCobro({ ...formCobro, fecha: e.target.value })
              }
              required
            />
          </Campo>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variante="secundario"
              onClick={() => setCobrando(null)}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={guardando}>
              {guardando ? "Registrando..." : "Registrar cobro"}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        abierto={documentando !== null}
        titulo="Registrar documento tributario"
        onCerrar={() => setDocumentando(null)}
      >
        <form onSubmit={registrarDocumento} className="space-y-4">
          {errorDocumento && (
            <div
              className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
              data-testid="error-documento"
            >
              {errorDocumento}
            </div>
          )}
          <p className="text-sm text-slate-500">
            Deja constancia de la obligación pendiente. No emite el documento.
          </p>
          <Campo label="Tipo de documento" htmlFor="documento_tipo" requerido>
            <Select
              id="documento_tipo"
              value={formDocumento.tipo}
              onChange={(e) =>
                setFormDocumento({ ...formDocumento, tipo: e.target.value })
              }
              required
            >
              <option value="boleta">Boleta</option>
              <option value="factura">Factura</option>
            </Select>
          </Campo>
          <Campo label="Folio" htmlFor="documento_folio">
            <Input
              id="documento_folio"
              value={formDocumento.folio}
              onChange={(e) =>
                setFormDocumento({ ...formDocumento, folio: e.target.value })
              }
            />
          </Campo>
          <Campo label="Monto" htmlFor="documento_monto" requerido>
            <Input
              id="documento_monto"
              type="number"
              step="0.01"
              min="0.01"
              value={formDocumento.monto}
              onChange={(e) =>
                setFormDocumento({ ...formDocumento, monto: e.target.value })
              }
              required
            />
          </Campo>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variante="secundario"
              onClick={() => setDocumentando(null)}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={guardando}>
              {guardando ? "Registrando..." : "Registrar documento"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
