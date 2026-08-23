import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type Tono = "verde" | "ambar" | "rojo" | "gris" | "azul";

const estilos: Record<Tono, string> = {
  verde: "bg-brand-100 text-brand-800 ring-brand-600/20",
  ambar: "bg-amber-100 text-amber-800 ring-amber-600/20",
  rojo: "bg-red-100 text-red-700 ring-red-600/20",
  gris: "bg-slate-100 text-slate-600 ring-slate-500/20",
  azul: "bg-sky-100 text-sky-800 ring-sky-600/20",
};

export function Badge({
  tono = "gris",
  children,
}: {
  tono?: Tono;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        estilos[tono],
      )}
    >
      {children}
    </span>
  );
}

// Mapea los estados del dominio a un tono coherente en toda la app.
export function tonoEstado(estado: string): Tono {
  switch (estado) {
    case "activo":
    case "recibida":
    case "sincronizada":
    case "operativa":
    case "al dia":
    case "Vigente":
    case "Pagada":
    case "Pagado":
    case "Firmado":
    case "Valorizado":
    case "Ensacado":
    case "Lista para cosecha":
      return "verde";
    case "pendiente de inspeccion":
    case "en curso":
    case "pendiente":
    case "en mantencion":
    case "En pila":
    case "Termofílica":
    case "En maduración":
    case "Próxima":
    case "Pendiente":
    case "Por vencer":
      return "ambar";
    case "rechazada":
    case "en conflicto":
    case "fuera de servicio":
    case "con deuda":
    case "inactivo":
    case "Vencida":
    case "Vencido":
      return "rojo";
    case "Emitido":
    case "Pago parcial":
    case "En proceso":
      return "azul";
    default:
      return "gris";
  }
}
