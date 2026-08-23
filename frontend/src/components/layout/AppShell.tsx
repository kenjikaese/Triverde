import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { LogOut, Menu, X, Leaf, Wifi, WifiOff } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useOnline } from "@/lib/useOnline";
import { sincronizar } from "@/lib/sync";
import { seccionesParaRol } from "@/lib/navegacion";
import { cn } from "@/lib/cn";
import { Badge } from "@/components/ui/Badge";

export function AppShell() {
  const { usuario, logout } = useAuth();
  const navigate = useNavigate();
  const [abierto, setAbierto] = useState(false);
  const online = useOnline();
  const estabaOnline = useRef(online);

  const rol = usuario?.rol_nombre ?? "Operador";
  const secciones = seccionesParaRol(rol);

  // Auto-sincronizacion: al recuperar la conexion, vaciar la cola local (CU-33).
  useEffect(() => {
    if (online && !estabaOnline.current) {
      sincronizar().catch(() => {});
    }
    estabaOnline.current = online;
  }, [online]);

  async function salir() {
    await logout();
    navigate("/login");
  }

  return (
    <div className="flex h-full bg-slate-100">
      {/* Overlay movil */}
      {abierto && (
        <div
          className="fixed inset-0 z-20 bg-slate-900/40 lg:hidden"
          onClick={() => setAbierto(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 flex w-64 flex-col bg-brand-900 text-brand-50 transition-transform lg:static lg:translate-x-0",
          abierto ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center gap-2 px-5 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-700">
            <Leaf className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold leading-tight">Triverde</p>
            <p className="text-xs text-brand-300">Gestion operativa</p>
          </div>
          <button
            className="ml-auto rounded p-1 hover:bg-brand-800 lg:hidden"
            onClick={() => setAbierto(false)}
            aria-label="Cerrar menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-2">
          {secciones.map((seccion, i) => (
            <div key={i}>
              {seccion.titulo && (
                <p className="px-2 pb-1 text-xs font-semibold uppercase tracking-wider text-brand-400">
                  {seccion.titulo}
                </p>
              )}
              <ul className="space-y-0.5">
                {seccion.items.map((item) => (
                  <li key={item.ruta}>
                    <NavLink
                      to={item.ruta}
                      end={item.ruta === "/"}
                      onClick={() => setAbierto(false)}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm transition-colors",
                          isActive
                            ? "bg-brand-700 font-medium text-white"
                            : "text-brand-100 hover:bg-brand-800",
                        )
                      }
                    >
                      <item.icono className="h-4 w-4 shrink-0" />
                      <span className="truncate">{item.etiqueta}</span>
                      {item.inc1 === false && (
                        <span className="ml-auto text-[10px] text-brand-400">
                          mockup
                        </span>
                      )}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
      </aside>

      {/* Contenido */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3">
          <button
            className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-100 lg:hidden"
            onClick={() => setAbierto(true)}
            aria-label="Abrir menu"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="ml-auto flex items-center gap-3">
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset",
                online
                  ? "bg-brand-100 text-brand-800 ring-brand-600/20"
                  : "bg-amber-100 text-amber-800 ring-amber-600/20",
              )}
              title={online ? "Conectado" : "Sin conexion: las capturas se guardan localmente"}
            >
              {online ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
              {online ? "En linea" : "Sin conexion"}
            </span>
            <div className="text-right">
              <p className="text-sm font-medium text-slate-800">
                {usuario?.nombre_completo}
              </p>
              <div className="flex justify-end">
                <Badge tono="verde">{rol}</Badge>
              </div>
            </div>
            <button
              onClick={salir}
              className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-red-600"
              title="Cerrar sesion"
              aria-label="Cerrar sesion"
            >
              <LogOut className="h-5 w-5" />
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
