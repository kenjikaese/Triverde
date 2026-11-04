import { useRef, useState, type ChangeEvent } from "react";
import { Camera, ImagePlus, Paperclip, Save, X } from "lucide-react";
import { mensajeDeError } from "@/lib/errores";
import { reducirImagen } from "@/lib/imagen";
import { Button } from "@/components/ui/Button";

interface CapturaFotoProps {
  /** Recibe la imagen ya reducida, como data URI en base64. */
  alGuardar: (archivo: string) => Promise<void> | void;
}

// V_CapturaFoto (CU-27): tomar o elegir la foto, confirmarla en una vista previa
// y guardarla. Quien la usa decide si va al registro en curso o a una recepcion
// ya creada. Todos los botones son type="button": suele ir dentro de un formulario.
export function CapturaFoto({ alGuardar }: CapturaFotoProps) {
  const camara = useRef<HTMLInputElement>(null);
  const galeria = useRef<HTMLInputElement>(null);
  const [opciones, setOpciones] = useState(false);
  const [vistaPrevia, setVistaPrevia] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  async function alElegir(e: ChangeEvent<HTMLInputElement>) {
    const archivo = e.target.files?.[0];
    e.target.value = "";
    // Excepcion 2: si se cancela la seleccion no hay archivo y nada cambia.
    if (!archivo) return;
    setError(null);
    try {
      setVistaPrevia(await reducirImagen(archivo));
    } catch {
      // Excepcion 1: el adjunto falla sin bloquear el resto del registro.
      setError("No se pudo leer la imagen. Puedes adjuntarla más tarde sin perder el registro.");
    }
  }

  function cancelar() {
    setVistaPrevia(null);
    setOpciones(false);
    setError(null);
  }

  async function guardar() {
    if (!vistaPrevia) return;
    setGuardando(true);
    setError(null);
    try {
      await alGuardar(vistaPrevia);
      setVistaPrevia(null);
      setOpciones(false);
    } catch (err) {
      setError(mensajeDeError(err, "No se pudo guardar la foto."));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="space-y-3">
      <input ref={camara} type="file" accept="image/*" capture="environment" className="hidden" aria-label="Tomar foto" onChange={alElegir} />
      <input ref={galeria} type="file" accept="image/*" className="hidden" aria-label="Elegir imagen" onChange={alElegir} />

      {error && <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

      {vistaPrevia ? (
        <div className="space-y-3">
          <img src={vistaPrevia} alt="Vista previa de la foto" className="max-h-64 rounded-lg ring-1 ring-slate-200" />
          <div className="flex flex-wrap gap-2">
            <Button type="button" tamano="sm" disabled={guardando} onClick={guardar}>
              <Save className="h-4 w-4" /> {guardando ? "Guardando..." : "Guardar foto"}
            </Button>
            <Button type="button" tamano="sm" variante="secundario" disabled={guardando} onClick={cancelar}>
              <X className="h-4 w-4" /> Cancelar
            </Button>
          </div>
        </div>
      ) : opciones ? (
        <div className="flex flex-wrap gap-2">
          <Button type="button" tamano="sm" onClick={() => camara.current?.click()}>
            <Camera className="h-4 w-4" /> Tomar foto
          </Button>
          <Button type="button" tamano="sm" variante="secundario" onClick={() => galeria.current?.click()}>
            <ImagePlus className="h-4 w-4" /> Elegir imagen
          </Button>
          <Button type="button" tamano="sm" variante="fantasma" onClick={cancelar}>
            Cancelar
          </Button>
        </div>
      ) : (
        <Button type="button" tamano="sm" variante="secundario" onClick={() => setOpciones(true)}>
          <Paperclip className="h-4 w-4" /> Adjuntar foto
        </Button>
      )}
    </div>
  );
}

// Miniaturas de las fotos ya guardadas; cada una abre la imagen completa.
export function MiniaturasFoto({ fotos }: { fotos: { id?: number; archivo: string }[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {fotos.map((foto, indice) => (
        <a key={foto.id ?? indice} href={foto.archivo} target="_blank" rel="noreferrer">
          <img src={foto.archivo} alt="Foto de la carga" className="h-12 w-12 rounded object-cover ring-1 ring-slate-200" data-testid="miniatura-foto" />
        </a>
      ))}
    </div>
  );
}
