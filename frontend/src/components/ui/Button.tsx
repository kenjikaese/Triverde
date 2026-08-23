import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

type Variante = "primario" | "secundario" | "peligro" | "fantasma";
type Tamano = "sm" | "md";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante;
  tamano?: Tamano;
  children: ReactNode;
}

const estilosVariante: Record<Variante, string> = {
  primario:
    "bg-brand-700 text-white hover:bg-brand-800 focus-visible:outline-brand-700 disabled:bg-brand-300",
  secundario:
    "bg-white text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 focus-visible:outline-slate-400",
  peligro:
    "bg-red-600 text-white hover:bg-red-700 focus-visible:outline-red-600 disabled:bg-red-300",
  fantasma:
    "bg-transparent text-slate-600 hover:bg-slate-100 focus-visible:outline-slate-400",
};

const estilosTamano: Record<Tamano, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
};

export function Button({
  variante = "primario",
  tamano = "md",
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed",
        estilosVariante[variante],
        estilosTamano[tamano],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
