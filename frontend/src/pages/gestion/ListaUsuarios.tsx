import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Plus, Search, UserCheck, UserCog, UserX } from "lucide-react";
import { api } from "@/lib/api";
import type { Rol, Usuario } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { mensajeDeError } from "@/lib/errores";

interface UsuarioApi extends Usuario { email?: string; date_joined?: string; }
const VACIO = { username: "", email: "", nombre_completo: "", rol: "", password: "" };

export function ListaUsuarios() {
  const [usuarios, setUsuarios] = useState<UsuarioApi[]>([]);
  const [roles, setRoles] = useState<Rol[]>([]);
  const [busqueda, setBusqueda] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState(VACIO);
  const [guardando, setGuardando] = useState(false);
  // CU-06: usuario al que se le está cambiando el rol, y el rol elegido.
  const [cambioRol, setCambioRol] = useState<UsuarioApi | null>(null);
  const [rolElegido, setRolElegido] = useState("");

  function cargar() {
    setCargando(true); setError(null);
    Promise.all([api.get<UsuarioApi[]>("/usuarios/"), api.get<Rol[]>("/roles/")])
      .then(([u, r]) => { setUsuarios(u.data); setRoles(r.data); })
      .catch(() => setError("No se pudo cargar la administración de usuarios."))
      .finally(() => setCargando(false));
  }
  useEffect(cargar, []);

  const filtrados = useMemo(() => {
    const termino = busqueda.toLowerCase();
    return usuarios.filter((usuario) => usuario.username.toLowerCase().includes(termino) || usuario.nombre_completo.toLowerCase().includes(termino));
  }, [usuarios, busqueda]);

  async function crear(e: FormEvent) {
    e.preventDefault(); setGuardando(true); setError(null);
    try {
      await api.post("/usuarios/", { username: form.username, email: form.email, nombre_completo: form.nombre_completo, rol: Number(form.rol), password: form.password, estado: "activo", is_active: true });
      setModal(false); setForm(VACIO); cargar();
    } catch { setError("No se pudo crear el usuario. Revisa el nombre de usuario y la contraseña."); }
    finally { setGuardando(false); }
  }

  async function desactivar(usuario: UsuarioApi) {
    if (!window.confirm(`¿Desactivar la cuenta ${usuario.username}?`)) return;
    setError(null);
    try { await api.delete(`/usuarios/${usuario.id}/`); cargar(); }
    // El servidor impide desactivar la cuenta propia (CU-05 Excepción 1) y
    // explica por qué; se muestra su mensaje, no uno genérico.
    catch (err) { setError(mensajeDeError(err, "No se pudo desactivar el usuario.")); }
  }

  // CU-05: reactivar una cuenta desactivada.
  async function activar(usuario: UsuarioApi) {
    setError(null);
    try { await api.patch(`/usuarios/${usuario.id}/`, { estado: "activo" }); cargar(); }
    catch (err) { setError(mensajeDeError(err, "No se pudo activar el usuario.")); }
  }

  function abrirCambioRol(usuario: UsuarioApi) {
    setError(null);
    setCambioRol(usuario);
    setRolElegido(String(usuario.rol));
  }

  // CU-06: cambiar el rol. El servidor impide que el administrador se quite el
  // suyo (Excepción 2); acá solo se evita enviar un cambio que no cambia nada.
  async function confirmarCambioRol() {
    if (!cambioRol) return;
    setGuardando(true); setError(null);
    try {
      await api.patch(`/usuarios/${cambioRol.id}/`, { rol: Number(rolElegido) });
      setCambioRol(null); cargar();
    } catch (err) { setError(mensajeDeError(err, "No se pudo cambiar el rol.")); setCambioRol(null); }
    finally { setGuardando(false); }
  }

  return (
    <div>
      <PageHeader titulo="Usuarios" descripcion="Cuentas de acceso, roles y estado de habilitación." accion={<Button onClick={() => setModal(true)}><Plus className="h-4 w-4" /> Nuevo usuario</Button>} />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <div className="relative mb-4 max-w-xs"><Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><Input placeholder="Buscar usuario" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} className="pl-9" /></div>
      <Card><Table><thead><tr><Th>Usuario</Th><Th>Nombre</Th><Th>Email</Th><Th>Rol</Th><Th>Estado</Th><Th>Acciones</Th></tr></thead><TBody>
        {cargando ? <EmptyRow colSpan={6} texto="Cargando..." /> : error && usuarios.length === 0 ? <EmptyRow colSpan={6} texto={error} /> : filtrados.length === 0 ? <EmptyRow colSpan={6} texto="Sin usuarios que coincidan." /> : filtrados.map((usuario) => <tr key={usuario.id} className="hover:bg-slate-50"><Td className="font-medium text-slate-800">{usuario.username}</Td><Td>{usuario.nombre_completo}</Td><Td>{usuario.email || "—"}</Td><Td>{usuario.rol_nombre ?? roles.find((rol) => rol.id === usuario.rol)?.nombre ?? `#${usuario.rol}`}</Td><Td><Badge tono={tonoEstado(usuario.estado)}>{usuario.estado}</Badge></Td><Td><div className="flex flex-col items-stretch gap-2 whitespace-nowrap xl:flex-row"><Button variante="secundario" tamano="sm" onClick={() => abrirCambioRol(usuario)}><UserCog className="h-4 w-4" /> Cambiar rol</Button>{usuario.estado === "activo" ? <Button variante="peligro" tamano="sm" onClick={() => desactivar(usuario)}><UserX className="h-4 w-4" /> Desactivar</Button> : <Button tamano="sm" onClick={() => activar(usuario)}><UserCheck className="h-4 w-4" /> Activar</Button>}</div></Td></tr>)}
      </TBody></Table></Card>
      <Modal abierto={modal} titulo="Nuevo usuario" onCerrar={() => setModal(false)}>
        <form onSubmit={crear} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2"><Campo label="Usuario" htmlFor="usuario_username" requerido><Input id="usuario_username" autoComplete="off" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required /></Campo><Campo label="Rol" htmlFor="usuario_rol" requerido><Select id="usuario_rol" value={form.rol} onChange={(e) => setForm({ ...form, rol: e.target.value })} required><option value="">Selecciona...</option>{roles.map((rol) => <option key={rol.id} value={rol.id}>{rol.nombre}</option>)}</Select></Campo></div>
          <Campo label="Nombre completo" htmlFor="usuario_nombre" requerido><Input id="usuario_nombre" value={form.nombre_completo} onChange={(e) => setForm({ ...form, nombre_completo: e.target.value })} required /></Campo>
          <Campo label="Email" htmlFor="usuario_email"><Input id="usuario_email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Campo>
          <Campo label="Contraseña inicial" htmlFor="usuario_password" requerido ayuda="La contraseña solo se envía al crear la cuenta."><Input id="usuario_password" type="password" autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required /></Campo>
          <div className="flex justify-end gap-2 pt-2"><Button type="button" variante="secundario" onClick={() => setModal(false)}>Cancelar</Button><Button type="submit" disabled={guardando}>{guardando ? "Creando..." : "Crear usuario"}</Button></div>
        </form>
      </Modal>
      <Modal abierto={cambioRol !== null} titulo={`Cambiar rol de ${cambioRol?.username ?? ""}`} onCerrar={() => setCambioRol(null)}>
        <div className="space-y-4">
          <Campo label="Rol" htmlFor="usuario_rol_nuevo" requerido ayuda={`Rol actual: ${cambioRol?.rol_nombre ?? roles.find((rol) => rol.id === cambioRol?.rol)?.nombre ?? "—"}`}>
            <Select id="usuario_rol_nuevo" value={rolElegido} onChange={(e) => setRolElegido(e.target.value)}>
              {roles.map((rol) => <option key={rol.id} value={rol.id}>{rol.nombre}</option>)}
            </Select>
          </Campo>
          {/* CU-06 Excepción 1: elegir el mismo rol no es un cambio, así que no
              se envía nada y no se genera un registro en la bitácora. */}
          {Number(rolElegido) === cambioRol?.rol && <p className="text-sm text-slate-500">Ese es el rol que la cuenta ya tiene. No hay cambio que aplicar.</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variante="secundario" onClick={() => setCambioRol(null)}>Cancelar</Button>
            <Button type="button" onClick={confirmarCambioRol} disabled={guardando || !rolElegido || Number(rolElegido) === cambioRol?.rol}>{guardando ? "Cambiando..." : "Confirmar cambio"}</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
