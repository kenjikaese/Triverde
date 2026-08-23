import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        {children}
      </table>
    </div>
  );
}

export function Th({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <th
      className={cn(
        "bg-slate-50 px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500",
        className,
      )}
    >
      {children}
    </th>
  );
}

export function Td({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <td className={cn("px-4 py-3 text-slate-700", className)}>{children}</td>
  );
}

export function TBody({ children }: { children: ReactNode }) {
  return <tbody className="divide-y divide-slate-100">{children}</tbody>;
}

export function EmptyRow({ colSpan, texto }: { colSpan: number; texto: string }) {
  return (
    <tr>
      <td colSpan={colSpan} className="px-4 py-10 text-center text-slate-400">
        {texto}
      </td>
    </tr>
  );
}
