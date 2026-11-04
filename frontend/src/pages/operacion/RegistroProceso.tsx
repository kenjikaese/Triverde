import { useEffect, useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { mensajeDeError } from "@/lib/errores";
import type { Existencia, TipoProcesoPila } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";

const CONFIG: Record<TipoProcesoPila, { titulo: string; confirmar: string; fecha: string }> = {
  triturado: { titulo: "Registrar triturado", confirmar: "Confirmar triturado", fecha: "Fecha" },
  volteo: { titulo: "Registrar volteo", confirmar: "Confirmar volteo", fecha: "Fecha del volteo" },
  riego: { titulo: "Registrar riego", confirmar: "Confirmar riego", fecha: "Fecha del riego" },
  harneado: { titulo: "Registrar harneado", confirmar: "Confirmar harneado", fecha: "Fecha del harneado" },
  reposo: { titulo: "Iniciar reposo", confirmar: "Confirmar inicio de reposo", fecha: "Inicio del reposo" },
  ensacado: { titulo: "Registrar ensacado", confirmar: "Confirmar ensacado", fecha: "Fecha del ensacado" },
};

// El valor de un input datetime-local va en hora local, sin zona.
function ahoraLocal() {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}


// V_RegistroProceso (CU-37 a CU-42): un formulario que registra el proceso segun su tipo.
export function RegistroProceso({
  tipo,
  pilaId,
  pilaCodigo,
  disponibleEnsacar,
  onCerrar,
  onRegistrado,
}: {
  tipo: TipoProcesoPila | null;
  pilaId?: number;
  pilaCodigo?: string;
  disponibleEnsacar?: string;
  onCerrar: () => void;
  onRegistrado: (mensaje: string) => void;
}) {
  const [fecha, setFecha] = useState(ahoraLocal());
  const [temperatura, setTemperatura] = useState("");
  const [humedad, setHumedad] = useState("");
  const [volumen, setVolumen] = useState("");
  const [material, setMaterial] = useState("");
  const [porTriturar, setPorTriturar] = useState<Existencia[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (!tipo) return;
    setFecha(ahoraLocal());
    setTemperatura("");
    setHumedad("");
    setVolumen("");
    setMaterial("");
    setError(null);
    if (tipo === "triturado") {
      api
        .get<Existencia[]>("/inventario/")
        .then((r) => setPorTriturar(r.data.filter((e) => e.etapa === "por triturar" && Number(e.volumen_m3) > 0)))
        .catch((err) => setError(mensajeDeError(err, "No se pudo cargar el inventario.")));
    }
  }, [tipo]);

  if (!tipo) return null;
  const config = CONFIG[tipo];

  async function confirmar(e: FormEvent) {
    e.preventDefault();
    setGuardando(true);
    setError(null);
    try {
      const res = await api.post<{ advertencia: string | null }>("/procesos-pila/", {
        tipo,
        pila: pilaId ?? null,
        material: tipo === "triturado" ? Number(material) : null,
        fecha: new Date(fecha).toISOString(),
        temperatura: temperatura || null,
        humedad: humedad || null,
        volumen_m3: volumen || null,
      });
      onRegistrado(res.data.advertencia || `${config.titulo}: registrado correctamente.`);
    } catch (err) {
      setError(mensajeDeError(err, "No se pudo registrar el proceso."));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <Modal abierto titulo={pilaCodigo ? `${config.titulo} · ${pilaCodigo}` : config.titulo} onCerrar={onCerrar}>
      <form onSubmit={confirmar} className="space-y-4">
        {error && <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        {tipo === "triturado" && (
          <Campo label="Material por triturar" htmlFor="proceso_material" requerido>
            <Select id="proceso_material" value={material} onChange={(e) => setMaterial(e.target.value)} required>
              <option value="">Selecciona un material</option>
              {porTriturar.map((e) => <option key={e.material} value={e.material}>{e.material_nombre} ({Number(e.volumen_m3).toLocaleString("es-CL")} m³ disponibles)</option>)}
            </Select>
          </Campo>
        )}
        <Campo label={config.fecha} htmlFor="proceso_fecha" requerido><Input id="proceso_fecha" type="datetime-local" value={fecha} onChange={(e) => setFecha(e.target.value)} required /></Campo>
        {tipo === "volteo" && (
          <Campo label="Temperatura medida (°C)" htmlFor="proceso_temperatura" requerido><Input id="proceso_temperatura" type="number" step="0.1" value={temperatura} onChange={(e) => setTemperatura(e.target.value)} required /></Campo>
        )}
        {tipo === "riego" && (
          <Campo label="Humedad estimada (%)" htmlFor="proceso_humedad" ayuda="Opcional: es un dato informativo."><Input id="proceso_humedad" type="number" step="0.1" min="0" max="100" value={humedad} onChange={(e) => setHumedad(e.target.value)} /></Campo>
        )}
        {tipo === "triturado" && (
          <Campo label="Volumen procesado (m³)" htmlFor="proceso_volumen" requerido><Input id="proceso_volumen" type="number" step="0.01" value={volumen} onChange={(e) => setVolumen(e.target.value)} required /></Campo>
        )}
        {tipo === "ensacado" && (
          <Campo label="Cantidad ensacada (m³)" htmlFor="proceso_volumen" requerido ayuda={disponibleEnsacar ? `Curado disponible: ${Number(disponibleEnsacar).toLocaleString("es-CL")} m³` : undefined}><Input id="proceso_volumen" type="number" step="0.01" value={volumen} onChange={(e) => setVolumen(e.target.value)} required /></Campo>
        )}
        <div className="flex justify-end gap-2 pt-2"><Button type="button" variante="secundario" onClick={onCerrar}>Cancelar</Button><Button type="submit" disabled={guardando}>{guardando ? "Guardando..." : config.confirmar}</Button></div>
      </form>
    </Modal>
  );
}
