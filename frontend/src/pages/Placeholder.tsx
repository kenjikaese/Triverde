import { Hammer } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";

// Pagina generica para las Vistas aun no maquetadas. El handoff del bulk las
// reemplaza por el mockup real de cada modulo.
export function Placeholder({
  titulo,
  descripcion,
}: {
  titulo: string;
  descripcion?: string;
}) {
  return (
    <div>
      <PageHeader titulo={titulo} descripcion={descripcion} />
      <Card>
        <CardBody className="flex flex-col items-center gap-3 py-16 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-amber-100 text-amber-700">
            <Hammer className="h-6 w-6" />
          </div>
          <p className="text-sm font-medium text-slate-700">
            Vista en preparacion
          </p>
          <p className="max-w-md text-sm text-slate-500">
            El mockup de esta vista es parte del lote pendiente. Sigue el patron
            del sistema de diseno (componentes en <code>components/ui</code>) y
            las vistas de referencia ya construidas.
          </p>
        </CardBody>
      </Card>
    </div>
  );
}
