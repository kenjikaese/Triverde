import { useEffect, useState, type FormEvent } from "react";
import { Calculator, Download, MapPin } from "lucide-react";
import { api } from "@/lib/api";
import type { Cliente, CostoKm, Cotizacion } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Button } from "@/components/ui/Button";
import { clp } from "@/lib/formato";
import { mensajeDeError } from "@/lib/errores";

// CU-55: el costo lo calcula el servidor (distancia x 2 x costo por km). Esta
// vista solo envia el formulario y muestra lo que devuelve la API; no replica
// la formula en el navegador.
const VACIO = { cliente: "", servicio: "", distancia_km: "" };

export function Cotizador() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [costoKm, setCostoKm] = useState<CostoKm | null>(null);
  const [form, setForm] = useState(VACIO);
  const [resultado, setResultado] = useState<Cotizacion | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Cliente[]>("/clientes/", { params: { estado: "activo" } })
      .then((res) => setClientes(res.data))
      .catch((err) =>
        setError(mensajeDeError(err, "No se pudo cargar la lista de clientes.")),
      );
    api
      .get<CostoKm>("/cotizaciones/costo-km/")
      .then((res) => setCostoKm(res.data))
      // Si la consulta falla no se asume "sin costo configurado": eso seria
      // un aviso enganoso. Se deja el estado sin resolver y se informa.
      .catch((err) => {
        setCostoKm(null);
        setError(
          mensajeDeError(
            err,
            "No se pudo verificar el costo por kilómetro configurado.",
          ),
        );
      });
  }, []);

  async function cotizar(e: FormEvent) {
    e.preventDefault();
    setGuardando(true);
    setError(null);
    setResultado(null);
    try {
      const res = await api.post<Cotizacion>("/cotizaciones/", {
        cliente: Number(form.cliente),
        servicio: form.servicio,
        distancia_km: form.distancia_km,
      });
      setResultado(res.data);
    } catch (err: unknown) {
      setError(
        mensajeDeError(
          err,
          "No se pudo generar la cotización. Revisa los datos ingresados.",
        ),
      );
    } finally {
      setGuardando(false);
    }
  }

  async function exportar() {
    if (!resultado) return;
    setError(null);
    try {
      const res = await api.get(`/cotizaciones/${resultado.id}/exportar/`);
      // CU-56: el documento se descarga para hacerlo llegar al cliente fuera
      // del sistema.
      const blob = new Blob([JSON.stringify(res.data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = `cotizacion-${resultado.id}.json`;
      enlace.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const datos = (
        err as { response?: { data?: { detalle?: string; faltantes?: string[] } } }
      ).response?.data;
      setError(
        datos?.faltantes?.length
          ? `${datos.detalle} Faltan: ${datos.faltantes.join(", ")}.`
          : (datos?.detalle ?? "No se pudo exportar la cotización."),
      );
    }
  }

  return (
    <div>
      <PageHeader
        titulo="Cotizador de servicios"
        descripcion="Genera el valor de un servicio aplicando el costo por kilómetro sobre el recorrido de ida y vuelta."
      />

      {costoKm && !costoKm.configurado && (
        <div
          className="mb-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800"
          data-testid="aviso-costo-km"
        >
          No hay un costo por kilómetro configurado. Puedes registrar la
          cotización, pero el sistema no calculará el costo hasta que un
          administrador configure el parámetro.
        </div>
      )}

      {error && (
        <div
          className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
          data-testid="error-cotizador"
        >
          {error}
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader
            titulo="Nueva cotización"
            descripcion="Selecciona el cliente, el servicio y la distancia hasta el lugar."
          />
          <CardBody>
            <form onSubmit={cotizar} className="space-y-4">
              <Campo label="Cliente" htmlFor="cotizacion_cliente" requerido>
                <Select
                  id="cotizacion_cliente"
                  value={form.cliente}
                  onChange={(e) => setForm({ ...form, cliente: e.target.value })}
                  required
                >
                  <option value="">Selecciona un cliente</option>
                  {clientes.map((cliente) => (
                    <option key={cliente.id} value={cliente.id}>
                      {cliente.razon_social}
                    </option>
                  ))}
                </Select>
              </Campo>

              <Campo label="Tipo de servicio" htmlFor="cotizacion_servicio" requerido>
                <Input
                  id="cotizacion_servicio"
                  value={form.servicio}
                  onChange={(e) => setForm({ ...form, servicio: e.target.value })}
                  placeholder="Triturado in situ"
                  required
                />
              </Campo>

              <Campo
                label="Distancia estimada (km)"
                htmlFor="cotizacion_distancia"
                ayuda="El sistema duplica la distancia para reflejar la ida y la vuelta."
                requerido
              >
                <Input
                  id="cotizacion_distancia"
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={form.distancia_km}
                  onChange={(e) =>
                    setForm({ ...form, distancia_km: e.target.value })
                  }
                  required
                />
              </Campo>

              <Button type="submit" disabled={guardando}>
                <Calculator className="h-4 w-4" />
                {guardando ? "Calculando..." : "Calcular y guardar cotización"}
              </Button>
            </form>
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            titulo="Resultado"
            descripcion="Costo calculado por el sistema para la cotización generada."
          />
          <CardBody>
            {!resultado ? (
              <p className="text-sm text-slate-400">
                Completa el formulario para generar una cotización.
              </p>
            ) : (
              <div className="space-y-4" data-testid="resultado-cotizacion">
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <MapPin className="h-4 w-4 text-slate-400" />
                  {resultado.distancia_km} km de ida ·{" "}
                  {Number(resultado.distancia_km) * 2} km de recorrido total
                </div>
                <div className="rounded-lg bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-wide text-slate-500">
                    Costo estimado
                  </p>
                  <p
                    className="mt-1 text-2xl font-semibold text-slate-800"
                    data-testid="costo-estimado"
                  >
                    {resultado.costo_estimado
                      ? clp(resultado.costo_estimado)
                      : "Sin calcular"}
                  </p>
                  {resultado.advertencia && (
                    <p className="mt-2 text-xs text-amber-700">
                      {resultado.advertencia}
                    </p>
                  )}
                </div>
                <Button variante="secundario" onClick={exportar}>
                  <Download className="h-4 w-4" />
                  Exportar cotización
                </Button>
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
