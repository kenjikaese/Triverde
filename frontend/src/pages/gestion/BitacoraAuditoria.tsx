import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Field";

interface RegistroAuditoria {
  id: number;
  usuario: number | null;
  usuario_username: string | null;
  accion: string;
  entidad_afectada: string;
  id_objeto: string | null;
  fecha_hora: string;
  detalle: string | null;
}

const fechaHora = (valor: string) => new Intl.DateTimeFormat("es-CL", { dateStyle: "short", timeStyle: "short" }).format(new Date(valor));

export function BitacoraAuditoria() {
  const [registros, setRegistros] = useState<RegistroAuditoria[]>([]);
  const [busqueda, setBusqueda] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<RegistroAuditoria[]>("/auditoria/").then((res) => setRegistros(res.data)).catch(() => setError("No se pudo cargar la bitácora de auditoría.")).finally(() => setCargando(false));
  }, []);

  const filtrados = useMemo(() => {
    const termino = busqueda.toLowerCase();
    return registros.filter((registro) => [registro.usuario_username, registro.accion, registro.entidad_afectada, registro.detalle].some((valor) => (valor ?? "").toLowerCase().includes(termino)));
  }, [registros, busqueda]);

  return (
    <div>
      <PageHeader titulo="Bitácora de auditoría" descripcion="Registro de acciones sensibles realizadas en el sistema." />
      <div className="relative mb-4 max-w-xs"><Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><Input placeholder="Buscar en la bitácora" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} className="pl-9" /></div>
      <Card><Table><thead><tr><Th>Fecha y hora</Th><Th>Usuario</Th><Th>Acción</Th><Th>Entidad</Th><Th>Objeto</Th><Th>Detalle</Th></tr></thead><TBody>
        {cargando ? <EmptyRow colSpan={6} texto="Cargando..." /> : error ? <EmptyRow colSpan={6} texto={error} /> : filtrados.length === 0 ? <EmptyRow colSpan={6} texto="No hay registros que coincidan." /> : filtrados.map((registro) => <tr key={registro.id} className="hover:bg-slate-50"><Td className="whitespace-nowrap">{fechaHora(registro.fecha_hora)}</Td><Td>{registro.usuario_username ?? "Sistema"}</Td><Td><Badge tono="azul">{registro.accion}</Badge></Td><Td>{registro.entidad_afectada}</Td><Td>{registro.id_objeto ?? "—"}</Td><Td className="max-w-sm">{registro.detalle ?? "—"}</Td></tr>)}
      </TBody></Table></Card>
    </div>
  );
}
