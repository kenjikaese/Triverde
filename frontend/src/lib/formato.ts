// Formatos compartidos por las vistas. Los montos y las cantidades viajan
// como string desde DRF (DecimalField), asi que se normalizan aca en vez de
// repetir la conversion en cada pantalla.

export function clp(valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined || valor === "") return "—";
  return `$${Math.round(Number(valor)).toLocaleString("es-CL")}`;
}

export function cantidad(valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined || valor === "") return "—";
  return Number(valor).toLocaleString("es-CL", {
    maximumFractionDigits: 2,
  });
}

export function fecha(valor: string | null | undefined): string {
  if (!valor) return "—";
  const [anio, mes, dia] = valor.split("-");
  return `${dia}-${mes}-${anio}`;
}

// Primer dia del mes en curso y hoy, en formato ISO: el periodo por defecto
// del listado de ventas (CU-59).
export function periodoVigente(): { desde: string; hasta: string } {
  const hoy = new Date();
  const primero = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { desde: iso(primero), hasta: iso(hoy) };
}
