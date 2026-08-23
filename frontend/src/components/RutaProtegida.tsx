import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth";

export function RutaProtegida({ children }: { children: ReactNode }) {
  const { usuario, cargando } = useAuth();

  if (cargando) {
    return (
      <div className="flex h-full items-center justify-center text-slate-400">
        Cargando...
      </div>
    );
  }

  if (!usuario) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
