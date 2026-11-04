import { useEffect, useState, type FormEvent } from "react";
import { Pencil } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { mensajeDeError } from "@/lib/errores";
import type { Usuario } from "@/lib/types";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Campo, Input } from "@/components/ui/Field";
import { PageHeader } from "@/components/ui/PageHeader";

const SIN_CLAVE = { password: "", confirmacion: "" };

// V_Perfil (CU-04): datos de la propia cuenta. El rol y el estado son de solo
// lectura porque los controla el administrador.
export function Perfil() {
  const { actualizarUsuario } = useAuth();
  const [perfil, setPerfil] = useState<Usuario | null>(null);
  const [editando, setEditando] = useState(false);
  const [form, setForm] = useState({ nombre_completo: "", email: "" });
  const [clave, setClave] = useState(SIN_CLAVE);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    api
      .get<Usuario>("/auth/perfil/")
      .then((r) => setPerfil(r.data))
      .catch((err) => setError(mensajeDeError(err, "No se pudo cargar tu perfil.")));
  }, []);

  function editar() {
    if (!perfil) return;
    setForm({ nombre_completo: perfil.nombre_completo, email: perfil.email ?? "" });
    setClave(SIN_CLAVE);
    setError(null);
    setAviso(null);
    setEditando(true);
  }

  async function guardar(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (clave.password !== clave.confirmacion) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setGuardando(true);
    try {
      const res = await api.patch<Usuario>("/auth/perfil/", {
        ...form,
        ...(clave.password ? { password: clave.password } : {}),
      });
      setPerfil(res.data);
      actualizarUsuario(res.data);
      setEditando(false);
      setClave(SIN_CLAVE);
      setAviso("Perfil actualizado.");
    } catch (err) {
      setError(mensajeDeError(err, "No se pudo actualizar el perfil."));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader titulo="Mi perfil" descripcion="Tus datos de acceso al sistema." />
      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {aviso && <div className="mb-4 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800">{aviso}</div>}

      {perfil && (
        <Card>
          <CardHeader
            titulo={perfil.username}
            accion={!editando && <Button variante="secundario" tamano="sm" onClick={editar}><Pencil className="h-4 w-4" /> Editar</Button>}
          />
          <CardBody>
            {editando ? (
              <form onSubmit={guardar} noValidate className="space-y-4">
                <Campo label="Nombre" htmlFor="perfil_nombre" requerido>
                  <Input id="perfil_nombre" value={form.nombre_completo} onChange={(e) => setForm({ ...form, nombre_completo: e.target.value })} />
                </Campo>
                <Campo label="Correo" htmlFor="perfil_email" requerido>
                  <Input id="perfil_email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </Campo>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <Campo label="Nueva contraseña" htmlFor="perfil_clave" ayuda="Déjala vacía si no quieres cambiarla.">
                    <Input id="perfil_clave" type="password" autoComplete="new-password" value={clave.password} onChange={(e) => setClave({ ...clave, password: e.target.value })} />
                  </Campo>
                  <Campo label="Repetir contraseña" htmlFor="perfil_clave2">
                    <Input id="perfil_clave2" type="password" autoComplete="new-password" value={clave.confirmacion} onChange={(e) => setClave({ ...clave, confirmacion: e.target.value })} />
                  </Campo>
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <Button type="button" variante="secundario" onClick={() => { setEditando(false); setError(null); }}>Cancelar</Button>
                  <Button type="submit" disabled={guardando}>{guardando ? "Guardando..." : "Guardar cambios"}</Button>
                </div>
              </form>
            ) : (
              <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
                <div><dt className="text-slate-500">Nombre</dt><dd className="font-medium text-slate-800" data-testid="perfil-nombre">{perfil.nombre_completo}</dd></div>
                <div><dt className="text-slate-500">Correo</dt><dd className="font-medium text-slate-800" data-testid="perfil-correo">{perfil.email || "Sin registrar"}</dd></div>
                <div><dt className="text-slate-500">Rol</dt><dd className="font-medium text-slate-800">{perfil.rol_nombre}</dd></div>
                <div><dt className="text-slate-500">Estado</dt><dd><Badge tono={tonoEstado(perfil.estado)}>{perfil.estado}</Badge></dd></div>
              </dl>
            )}
          </CardBody>
        </Card>
      )}
    </div>
  );
}
