import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Plus, Search, UserX } from "lucide-react";
import { api } from "@/lib/api";
import type { Rol, Usuario } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";

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
    try { await api.delete(`/usuarios/${usuario.id}/`); cargar(); }
    catch { setError("No se pudo desactivar el usuario."); }
  }

  return (
    <div>
      <PageHeader titulo="Usuarios" descripcion="Cuentas de acceso, roles y estado de habilitación." accion={<Button onClick={() => setModal(true)}><Plus className="h-4 w-4" /> Nuevo usuario</Button>} />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <div className="relative mb-4 max-w-xs"><Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><Input placeholder="Buscar usuario" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} className="pl-9" /></div>
      <Card><Table><thead><tr><Th>Usuario</Th><Th>Nombre</Th><Th>Email</Th><Th>Rol</Th><Th>Estado</Th><Th>Acciones</Th></tr></thead><TBody>
        {cargando ? <EmptyRow colSpan={6} texto="Cargando..." /> : error && usuarios.length === 0 ? <EmptyRow colSpan={6} texto={error} /> : filtrados.length === 0 ? <EmptyRow colSpan={6} texto="Sin usuarios que coincidan." /> : filtrados.map((usuario) => <tr key={usuario.id} className="hover:bg-slate-50"><Td className="font-medium text-slate-800">{usuario.username}</Td><Td>{usuario.nombre_completo}</Td><Td>{usuario.email || "—"}</Td><Td>{usuario.rol_nombre ?? roles.find((rol) => rol.id === usuario.rol)?.nombre ?? `#${usuario.rol}`}</Td><Td><Badge tono={tonoEstado(usuario.estado)}>{usuario.estado}</Badge></Td><Td>{usuario.estado === "activo" ? <Button variante="peligro" tamano="sm" onClick={() => desactivar(usuario)}><UserX className="h-4 w-4" /> Desactivar</Button> : "—"}</Td></tr>)}
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
    </div>
  );
}
