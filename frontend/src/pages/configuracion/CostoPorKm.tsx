import { useCallback, useEffect, useState, type FormEvent } from "react";
import { isAxiosError } from "axios";
import { api } from "@/lib/api";
import { mensajeDeError } from "@/lib/errores";
import type { CostoTransporte } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Campo, Input } from "@/components/ui/Field";

// CU-12: costo por kilometro vigente, dentro de V_FormularioTarifa (docs/13). Cada
// cambio crea un valor nuevo: lo ya cotizado conserva el costo que se uso entonces.
export function CostoPorKm() {
  const [vigente, setVigente] = useState<CostoTransporte | null>(null);
  const [valor, setValor] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(() => {
    api
      .get<CostoTransporte>("/costo-transporte/")
      .then((r) => {
        setVigente(r.data);
        setValor(r.data.costo_por_km);
      })
      .catch((err) => {
        // Sin valor todavia: el administrador lo define por primera vez.
        if (isAxiosError(err) && err.response?.status === 404) setVigente(null);
        else setError(mensajeDeError(err, "No se pudo cargar el costo por km."));
      });
  }, []);
  useEffect(cargar, [cargar]);

  async function guardar(e: FormEvent) {
    e.preventDefault();
    setGuardando(true);
    setError(null);
    setAviso(null);
    try {
      const res = await api.post<CostoTransporte>("/costo-transporte/", { costo_por_km: valor });
      // Excepcion 2: el mismo valor responde 200 y no registra un cambio.
      setAviso(res.status === 201 ? "Costo por km actualizado." : "El valor no cambió: no se registró un cambio.");
      setVigente(res.data);
      setValor(res.data.costo_por_km);
    } catch (err) {
      setError(mensajeDeError(err, "No se pudo guardar el costo por km."));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="mt-6">
      <Card>
        <CardHeader
          titulo="Costo de transporte por km"
          descripcion={
            vigente
              ? `Última actualización: ${new Date(vigente.fecha).toLocaleDateString("es-CL")}. Se usa en las cotizaciones desde ese momento.`
              : "Todavía no se define un valor."
          }
        />
        <CardBody>
          {error && <div className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
          {aviso && <div className="mb-4 rounded-lg bg-brand-50 px-3 py-2 text-sm text-brand-800">{aviso}</div>}
          <form onSubmit={guardar} className="flex flex-wrap items-end gap-3">
            <div className="w-56">
              <Campo label="Costo por km (CLP)" htmlFor="costo_km" requerido>
                <Input id="costo_km" type="number" step="1" value={valor} onChange={(e) => setValor(e.target.value)} required />
              </Campo>
            </div>
            <Button type="submit" disabled={guardando}>{guardando ? "Guardando..." : "Guardar costo"}</Button>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
