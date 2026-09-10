import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard,
  Truck,
  RefreshCw,
  Boxes,
  Layers,
  FlaskConical,
  Bell,
  Wrench,
  Gauge,
  Sliders,
  Users,
  UserCog,
  Package,
  Leaf,
  Car,
  FileText,
  TrendingUp,
  Calculator,
  ShoppingCart,
  Receipt,
  BadgeCheck,
  FileCheck2,
  FileStack,
  ClipboardList,
  ScrollText,
} from "lucide-react";
import type { RolNombre } from "@/lib/types";

export interface ItemNav {
  etiqueta: string;
  ruta: string;
  icono: LucideIcon;
  roles: RolNombre[];
  /** true = cableada a la API (Inc 1); false = mockup visual (modulos posteriores). */
  inc1?: boolean;
}

export interface SeccionNav {
  titulo: string;
  items: ItemNav[];
}

const TODOS: RolNombre[] = ["Administrador", "Operador", "Transportista"];
const INTERNO: RolNombre[] = ["Administrador", "Operador"];
const ADMIN: RolNombre[] = ["Administrador"];

// Arbol de navegacion (docs/13 SS13.4). El menu se filtra por rol.
export const navegacion: SeccionNav[] = [
  {
    titulo: "",
    items: [
      {
        etiqueta: "Panel de control",
        ruta: "/",
        icono: LayoutDashboard,
        roles: TODOS,
      },
    ],
  },
  {
    titulo: "Operacion",
    items: [
      { etiqueta: "Recepcion de camiones", ruta: "/recepcion", icono: Truck, roles: INTERNO, inc1: true },
      { etiqueta: "Cola de sincronizacion", ruta: "/sincronizacion", icono: RefreshCw, roles: INTERNO, inc1: true },
      { etiqueta: "Inventario", ruta: "/inventario", icono: Boxes, roles: INTERNO },
      { etiqueta: "Pilas de compostaje", ruta: "/pilas", icono: Layers, roles: INTERNO },
      { etiqueta: "Mezcla objetivo", ruta: "/mezcla", icono: FlaskConical, roles: INTERNO },
      { etiqueta: "Alertas", ruta: "/alertas", icono: Bell, roles: INTERNO, inc1: true },
    ],
  },
  {
    titulo: "Mantenimiento",
    items: [
      { etiqueta: "Maquinaria y flota", ruta: "/maquinaria", icono: Wrench, roles: INTERNO, inc1: true },
      { etiqueta: "Estado de la flota", ruta: "/flota", icono: Gauge, roles: ADMIN, inc1: true },
    ],
  },
  {
    titulo: "Mantenedores",
    items: [
      { etiqueta: "Clientes", ruta: "/clientes", icono: Users, roles: ADMIN, inc1: true },
      { etiqueta: "Transportistas", ruta: "/transportistas", icono: UserCog, roles: ADMIN, inc1: true },
      { etiqueta: "Materiales", ruta: "/materiales", icono: Leaf, roles: ADMIN, inc1: true },
      { etiqueta: "Productos", ruta: "/productos", icono: Package, roles: ADMIN, inc1: true },
      { etiqueta: "Vehiculos", ruta: "/vehiculos", icono: Car, roles: ADMIN, inc1: true },
    ],
  },
  {
    titulo: "Configuracion",
    items: [
      { etiqueta: "Parametros", ruta: "/parametros", icono: Sliders, roles: ADMIN, inc1: true },
      { etiqueta: "Tarifas de recepcion", ruta: "/tarifas", icono: Calculator, roles: ADMIN, inc1: true },
    ],
  },
  {
    titulo: "Comercial",
    items: [
      { etiqueta: "Cotizador", ruta: "/cotizador", icono: Calculator, roles: ADMIN },
      { etiqueta: "Ventas", ruta: "/ventas", icono: ShoppingCart, roles: ADMIN },
      { etiqueta: "Cobros", ruta: "/cobros", icono: Receipt, roles: ADMIN },
    ],
  },
  {
    titulo: "Trazabilidad",
    items: [
      { etiqueta: "Certificados", ruta: "/certificados", icono: BadgeCheck, roles: ADMIN },
      { etiqueta: "Exportacion SINADER", ruta: "/sinader", icono: FileCheck2, roles: ADMIN },
      { etiqueta: "Indicador ambiental", ruta: "/ambiental", icono: Leaf, roles: ADMIN },
    ],
  },
  {
    titulo: "Gestion",
    items: [
      { etiqueta: "Proyecciones", ruta: "/proyecciones", icono: TrendingUp, roles: ADMIN },
      { etiqueta: "Reportes", ruta: "/reportes", icono: FileText, roles: ADMIN },
      { etiqueta: "Documentos legales", ruta: "/documentos", icono: FileStack, roles: ADMIN },
      { etiqueta: "Usuarios", ruta: "/usuarios", icono: ClipboardList, roles: ADMIN, inc1: true },
      { etiqueta: "Bitacora de auditoria", ruta: "/auditoria", icono: ScrollText, roles: ADMIN, inc1: true },
    ],
  },
];

export function seccionesParaRol(rol: RolNombre): SeccionNav[] {
  return navegacion
    .map((seccion) => ({
      ...seccion,
      items: seccion.items.filter((item) => item.roles.includes(rol)),
    }))
    .filter((seccion) => seccion.items.length > 0);
}
