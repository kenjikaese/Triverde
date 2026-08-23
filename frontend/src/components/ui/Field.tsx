import type {
  InputHTMLAttributes,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
  ReactNode,
} from "react";
import { cn } from "@/lib/cn";

const baseControl =
  "block w-full rounded-lg border-0 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-brand-600 disabled:bg-slate-50 disabled:text-slate-500";

interface CampoBase {
  label: string;
  htmlFor?: string;
  error?: string;
  requerido?: boolean;
  ayuda?: string;
  children: ReactNode;
}

export function Campo({ label, htmlFor, error, requerido, ayuda, children }: CampoBase) {
  return (
    <div>
      <label
        htmlFor={htmlFor}
        className="mb-1 block text-sm font-medium text-slate-700"
      >
        {label}
        {requerido && <span className="ml-0.5 text-red-600">*</span>}
      </label>
      {children}
      {ayuda && !error && <p className="mt-1 text-xs text-slate-500">{ayuda}</p>}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}

export function Input({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(baseControl, className)} {...props} />;
}

export function Select({
  className,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={cn(baseControl, "pr-8", className)} {...props}>
      {children}
    </select>
  );
}

export function Textarea({
  className,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn(baseControl, "min-h-20", className)} {...props} />;
}
