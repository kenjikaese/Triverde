import type { ReactNode } from "react";

export function PageHeader({
  titulo,
  descripcion,
  accion,
}: {
  titulo: string;
  descripcion?: string;
  accion?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">{titulo}</h1>
        {descripcion && (
          <p className="mt-1 text-sm text-slate-500">{descripcion}</p>
        )}
      </div>
      {accion}
    </div>
  );
}
