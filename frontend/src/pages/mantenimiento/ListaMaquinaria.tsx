import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Clock3, History, Plus, Search, Wrench } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Maquinaria, Mantencion, RegistroUso, Vehiculo } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Table, TBody, Td, Th, EmptyRow } from "@/components/ui/Table";
import { Badge, tonoEstado } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Campo, Input, Select, Textarea } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";

type Activo = {
  id: number; clase: "maquinaria" | "vehiculo"; codigo: string; nombre: string;
  tipo: string; horometro: string; estado_operativo: string; estado: string;
};

const FORM_ACTIVO = { clase: "maquinaria", nombre: "", tipo: "", vehiculo: "", marca: "", modelo: "", serie: "", horometro: "0" };
const FORM_USO = { horas: "", fecha: new Date().toISOString().slice(0, 16) };
const FORM_MANTENCION = { tipo: "correctiva", criterio: "horas", umbral_horas: "", fecha_programada: "", descripcion: "", falla: "", reparacion: "", costo: "0", reparacion_habilita: true };
const FORM_REPROGRAMACION = { criterio: "horas", umbral_horas: "", fecha_programada: "", descripcion: "" };
const FILTROS_HISTORIAL = { tipo: "", desde: "", hasta: "" };

export function ListaMaquinaria() {
  const { usuario } = useAuth();
  const admin = usuario?.rol_nombre === "Administrador";
  const [maquinarias, setMaquinarias] = useState<Maquinaria[]>([]);
  const [vehiculos, setVehiculos] = useState<Vehiculo[]>([]);
  const [busqueda, setBusqueda] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalActivo, setModalActivo] = useState(false);
  const [modalUso, setModalUso] = useState(false);
  const [modalMantencion, setModalMantencion] = useState(false);
  const [modalHistorial, setModalHistorial] = useState(false);
  const [reprogramando, setReprogramando] = useState<Mantencion | null>(null);
  const [seleccionado, setSeleccionado] = useState<Activo | null>(null);
  const [editando, setEditando] = useState<Activo | null>(null);
  const [formActivo, setFormActivo] = useState(FORM_ACTIVO);
  const [formUso, setFormUso] = useState(FORM_USO);
  const [formMantencion, setFormMantencion] = useState(FORM_MANTENCION);
  const [formReprogramacion, setFormReprogramacion] = useState(FORM_REPROGRAMACION);
  const [filtrosHistorial, setFiltrosHistorial] = useState(FILTROS_HISTORIAL);
  const [mantenciones, setMantenciones] = useState<Mantencion[]>([]);
  const [usos, setUsos] = useState<RegistroUso[]>([]);
  const [guardando, setGuardando] = useState(false);

  function cargar() {
    setCargando(true); setError(null);
    Promise.all([api.get<Maquinaria[]>("/maquinaria/"), api.get<Vehiculo[]>("/vehiculos/")])
      .then(([m, v]) => { setMaquinarias(m.data); setVehiculos(v.data); })
      .catch(() => setError("No se pudieron cargar los activos mantenibles."))
      .finally(() => setCargando(false));
  }
  useEffect(cargar, []);

  const activos = useMemo<Activo[]>(() => [
    ...maquinarias.map((m) => ({ id: m.id, clase: "maquinaria" as const, codigo: m.codigo, nombre: m.nombre, tipo: m.tipo, horometro: m.horometro, estado_operativo: m.estado_operativo, estado: m.estado })),
    ...vehiculos.filter((v) => v.es_mantenible).map((v) => ({ id: v.id, clase: "vehiculo" as const, codigo: `VH-${String(v.id).padStart(2, "0")}`, nombre: v.patente, tipo: "Vehículo", horometro: v.horometro, estado_operativo: v.estado_operativo, estado: v.estado })),
  ], [maquinarias, vehiculos]);
  const filtrados = activos.filter((a) => `${a.codigo} ${a.nombre} ${a.tipo}`.toLowerCase().includes(busqueda.toLowerCase()));
  const referencia = (activo: Activo) => activo.clase === "maquinaria" ? { maquinaria: activo.id, vehiculo: null } : { maquinaria: null, vehiculo: activo.id };

  async function guardarActivo(e: FormEvent) {
    e.preventDefault(); setGuardando(true); setError(null);
    const datos_tecnicos = { marca: formActivo.marca, modelo: formActivo.modelo, numero_serie: formActivo.serie };
    try {
      if (editando?.clase === "maquinaria") {
        await api.patch(`/maquinaria/${editando.id}/`, { nombre: formActivo.nombre, tipo: formActivo.tipo, horometro: formActivo.horometro, datos_tecnicos });
      } else if (editando?.clase === "vehiculo") {
        await api.patch(`/vehiculos/${editando.id}/`, { horometro: formActivo.horometro, datos_tecnicos });
      } else if (formActivo.clase === "maquinaria") {
        await api.post("/maquinaria/", { nombre: formActivo.nombre, tipo: formActivo.tipo, horometro: formActivo.horometro, datos_tecnicos });
      } else {
        await api.patch(`/vehiculos/${formActivo.vehiculo}/`, { es_mantenible: true, horometro: formActivo.horometro, datos_tecnicos, estado_operativo: "operativa", estado: "activo" });
      }
      setModalActivo(false); setEditando(null); setFormActivo(FORM_ACTIVO); cargar();
    } catch { setError("No se pudo registrar el activo. Revisa los datos ingresados."); }
    finally { setGuardando(false); }
  }

  function editarActivo(activo: Activo) {
    const original = activo.clase === "maquinaria"
      ? maquinarias.find((m) => m.id === activo.id)
      : vehiculos.find((v) => v.id === activo.id);
    const datos = original?.datos_tecnicos ?? {};
    setEditando(activo);
    setFormActivo({
      clase: activo.clase, nombre: activo.clase === "maquinaria" ? activo.nombre : "",
      tipo: activo.clase === "maquinaria" ? activo.tipo : "", vehiculo: String(activo.id),
      marca: datos.marca ?? "", modelo: datos.modelo ?? "", serie: datos.numero_serie ?? "",
      horometro: activo.horometro,
    });
    setModalActivo(true);
  }

  async function registrarUso(e: FormEvent) {
    e.preventDefault(); if (!seleccionado) return; setGuardando(true); setError(null);
    try {
      await api.post("/registros-uso/", { ...referencia(seleccionado), horas: formUso.horas, fecha: new Date(formUso.fecha).toISOString() });
      setModalUso(false); setFormUso(FORM_USO); cargar();
    } catch { setError("No se pudo registrar la lectura. El horómetro no puede retroceder ni actualizarse fuera de servicio."); }
    finally { setGuardando(false); }
  }

  async function registrarMantencion(e: FormEvent, confirmar_duplicada = false) {
    e.preventDefault(); if (!seleccionado) return; setGuardando(true); setError(null);
    const payload = { ...referencia(seleccionado), ...formMantencion, confirmar_duplicada,
      umbral_horas: formMantencion.criterio === "horas" ? formMantencion.umbral_horas : null,
      fecha_programada: formMantencion.criterio === "fecha" ? formMantencion.fecha_programada : null,
    };
    try {
      await api.post("/mantenciones/", payload); setModalMantencion(false); setFormMantencion(FORM_MANTENCION); cargar();
    } catch (err: unknown) {
      const duplicada = typeof err === "object" && err !== null && "response" in err && JSON.stringify((err as { response?: { data?: unknown } }).response?.data).includes("confirmar_duplicada");
      if (duplicada && window.confirm("Ya existe una mantención programada con ese criterio. ¿Crear otra igualmente?")) return registrarMantencion(e, true);
      setError("No se pudo guardar la mantención. Revisa el criterio, fechas, horas y campos obligatorios.");
    } finally { setGuardando(false); }
  }

  async function cargarHistorial(activo: Activo, filtros = filtrosHistorial) {
    const params: Record<string, string | number> = activo.clase === "maquinaria"
      ? { maquinaria: activo.id }
      : { vehiculo: activo.id };
    if (filtros.tipo) params.tipo = filtros.tipo;
    if (filtros.desde) params.desde = filtros.desde;
    if (filtros.hasta) params.hasta = filtros.hasta;
    try {
      const [m, u] = await Promise.all([api.get<Mantencion[]>("/mantenciones/", { params }), api.get<RegistroUso[]>("/registros-uso/", { params })]);
      setMantenciones(m.data); setUsos(u.data);
    } catch { setError("No se pudo cargar el historial del activo."); }
  }

  async function verHistorial(activo: Activo) {
    setSeleccionado(activo); setModalHistorial(true); setFiltrosHistorial(FILTROS_HISTORIAL);
    await cargarHistorial(activo, FILTROS_HISTORIAL);
  }

  async function aplicarFiltrosHistorial(e: FormEvent) {
    e.preventDefault();
    if (seleccionado) await cargarHistorial(seleccionado);
  }

  function abrirReprogramacion(mantencion: Mantencion) {
    setFormReprogramacion({
      criterio: mantencion.criterio ?? "horas",
      umbral_horas: mantencion.umbral_horas ?? "",
      fecha_programada: mantencion.fecha_programada ?? "",
      descripcion: mantencion.descripcion,
    });
    setModalHistorial(false);
    setReprogramando(mantencion);
  }

  async function guardarReprogramacion(e: FormEvent) {
    e.preventDefault();
    if (!reprogramando || !seleccionado) return;
    setGuardando(true); setError(null);
    try {
      await api.patch(`/mantenciones/${reprogramando.id}/`, {
        criterio: formReprogramacion.criterio,
        umbral_horas: formReprogramacion.criterio === "horas" ? formReprogramacion.umbral_horas : null,
        fecha_programada: formReprogramacion.criterio === "fecha" ? formReprogramacion.fecha_programada : null,
        descripcion: formReprogramacion.descripcion,
      });
      setReprogramando(null);
      await cargarHistorial(seleccionado);
      setModalHistorial(true);
      cargar();
    } catch {
      setError("No se pudo reprogramar. La fecha debe ser futura y las horas deben superar el horómetro actual.");
    } finally { setGuardando(false); }
  }

  async function realizarPreventiva(mantencion: Mantencion) {
    if (!seleccionado) return;
    const costo = window.prompt("Costo de la mantención", "0");
    if (costo === null) return;
    const reparacion = window.prompt("Trabajo realizado", mantencion.descripcion);
    if (reparacion === null) return;
    try {
      await api.post(`/mantenciones/${mantencion.id}/realizar/`, {
        costo, reparacion, reparacion_habilita: true,
      });
      await verHistorial(seleccionado); cargar();
    } catch { setError("No se pudo marcar la mantención como realizada."); }
  }

  async function darDeBaja(activo: Activo) {
    if (!window.confirm(`¿Dar de baja ${activo.nombre}? Su historial se conservará.`)) return;
    const url = activo.clase === "maquinaria" ? `/maquinaria/${activo.id}/` : `/vehiculos/${activo.id}/`;
    try {
      try { await api.delete(url); }
      catch (err: unknown) {
        const conflicto = typeof err === "object" && err !== null && "response" in err && (err as { response?: { status?: number } }).response?.status === 409;
        if (!conflicto || !window.confirm("Tiene una mantención pendiente o está en mantención. ¿Confirmas la baja?")) throw err;
        await api.delete(url, { data: { confirmar_baja: true } });
      }
      cargar();
    } catch { setError("No se pudo dar de baja el activo."); }
  }

  return <div>
    <PageHeader titulo="Maquinaria y flota" descripcion="Activos mantenibles, horas de uso y mantenciones." accion={admin ? <Button onClick={() => { setEditando(null); setFormActivo(FORM_ACTIVO); setModalActivo(true); }}><Plus className="h-4 w-4" /> Nuevo activo</Button> : undefined} />
    {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
    <div className="relative mb-4 max-w-sm"><Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><Input className="pl-9" placeholder="Buscar equipo, código o tipo" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} /></div>
    <Card><Table><thead><tr><Th>Código</Th><Th>Equipo</Th><Th>Tipo</Th><Th>Horómetro</Th><Th>Estado</Th><Th>Acciones</Th></tr></thead><TBody>
      {cargando ? <EmptyRow colSpan={6} texto="Cargando..." /> : filtrados.length === 0 ? <EmptyRow colSpan={6} texto="No hay activos mantenibles." /> : filtrados.map((activo) => <tr key={`${activo.clase}-${activo.id}`} className="hover:bg-slate-50">
        <Td className="font-medium text-slate-800">{activo.codigo}</Td><Td>{activo.nombre}</Td><Td>{activo.tipo}</Td><Td>{Number(activo.horometro).toLocaleString("es-CL")} h</Td><Td><Badge tono={tonoEstado(activo.estado_operativo)}>{activo.estado_operativo}</Badge></Td>
        <Td><div className="flex flex-wrap gap-1"><Button variante="fantasma" tamano="sm" onClick={() => verHistorial(activo)}><History className="h-4 w-4" /> Historial</Button><Button variante="secundario" tamano="sm" onClick={() => { setSeleccionado(activo); setFormUso({ ...FORM_USO, horas: activo.horometro }); setModalUso(true); }}><Clock3 className="h-4 w-4" /> Horas</Button><Button variante="secundario" tamano="sm" onClick={() => { setSeleccionado(activo); setModalMantencion(true); }}><Wrench className="h-4 w-4" /> Mantención</Button>{admin && <Button variante="fantasma" tamano="sm" onClick={() => editarActivo(activo)}>Editar</Button>}{admin && activo.estado === "activo" && <Button variante="peligro" tamano="sm" onClick={() => darDeBaja(activo)}>Baja</Button>}</div></Td>
      </tr>)}
    </TBody></Table></Card>

    <Modal abierto={modalActivo} titulo={editando ? "Editar activo mantenible" : "Registrar activo mantenible"} onCerrar={() => { setModalActivo(false); setEditando(null); }}><form onSubmit={guardarActivo} className="space-y-4">
      <Campo label="Tipo de activo" requerido><Select disabled={Boolean(editando)} value={formActivo.clase} onChange={(e) => setFormActivo({ ...formActivo, clase: e.target.value })}><option value="maquinaria">Máquina o equipo nuevo</option><option value="vehiculo">Vehículo existente</option></Select></Campo>
      {formActivo.clase === "maquinaria" ? <div className="grid grid-cols-1 gap-4 sm:grid-cols-2"><Campo label="Nombre" requerido><Input required value={formActivo.nombre} onChange={(e) => setFormActivo({ ...formActivo, nombre: e.target.value })} /></Campo><Campo label="Tipo" requerido><Input required value={formActivo.tipo} onChange={(e) => setFormActivo({ ...formActivo, tipo: e.target.value })} /></Campo></div> : editando ? <Campo label="Vehículo"><Input disabled value={editando.nombre} /></Campo> : <Campo label="Vehículo" requerido><Select required value={formActivo.vehiculo} onChange={(e) => setFormActivo({ ...formActivo, vehiculo: e.target.value })}><option value="">Seleccionar...</option>{vehiculos.filter((v) => !v.es_mantenible && v.estado === "activo").map((v) => <option key={v.id} value={v.id}>{v.patente} · {v.descripcion ?? "Sin descripción"}</option>)}</Select></Campo>}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3"><Campo label="Marca"><Input value={formActivo.marca} onChange={(e) => setFormActivo({ ...formActivo, marca: e.target.value })} /></Campo><Campo label="Modelo"><Input value={formActivo.modelo} onChange={(e) => setFormActivo({ ...formActivo, modelo: e.target.value })} /></Campo><Campo label="N.º de serie"><Input value={formActivo.serie} onChange={(e) => setFormActivo({ ...formActivo, serie: e.target.value })} /></Campo></div>
      <Campo label="Lectura inicial del horómetro" requerido><Input required type="number" min="0" step="0.01" value={formActivo.horometro} onChange={(e) => setFormActivo({ ...formActivo, horometro: e.target.value })} /></Campo>
      <div className="flex justify-end gap-2"><Button type="button" variante="secundario" onClick={() => { setModalActivo(false); setEditando(null); }}>Cancelar</Button><Button type="submit" disabled={guardando}>{guardando ? "Guardando..." : editando ? "Guardar cambios" : "Registrar"}</Button></div>
    </form></Modal>

    <Modal abierto={modalUso} titulo={`Registrar horas · ${seleccionado?.nombre ?? ""}`} onCerrar={() => setModalUso(false)}><form onSubmit={registrarUso} className="space-y-4"><Campo label="Lectura actual" ayuda={`Última lectura: ${seleccionado?.horometro ?? 0} h`} requerido><Input required type="number" min={seleccionado?.horometro} step="0.01" value={formUso.horas} onChange={(e) => setFormUso({ ...formUso, horas: e.target.value })} /></Campo><Campo label="Fecha y hora" requerido><Input required type="datetime-local" value={formUso.fecha} onChange={(e) => setFormUso({ ...formUso, fecha: e.target.value })} /></Campo><div className="flex justify-end gap-2"><Button type="button" variante="secundario" onClick={() => setModalUso(false)}>Cancelar</Button><Button type="submit" disabled={guardando}>Registrar horas</Button></div></form></Modal>

    <Modal abierto={modalMantencion} titulo={`Mantención · ${seleccionado?.nombre ?? ""}`} onCerrar={() => setModalMantencion(false)}><form onSubmit={registrarMantencion} className="space-y-4"><Campo label="Tipo" requerido><Select value={formMantencion.tipo} onChange={(e) => setFormMantencion({ ...formMantencion, tipo: e.target.value })}>{admin && <option value="preventiva">Preventiva</option>}<option value="correctiva">Correctiva</option></Select></Campo>
      {formMantencion.tipo === "preventiva" ? <><Campo label="Criterio" requerido><Select value={formMantencion.criterio} onChange={(e) => setFormMantencion({ ...formMantencion, criterio: e.target.value })}><option value="horas">Por horas</option><option value="fecha">Por fecha</option></Select></Campo>{formMantencion.criterio === "horas" ? <Campo label="Ejecutar al alcanzar" ayuda={`Debe superar ${seleccionado?.horometro ?? 0} h`} requerido><Input required type="number" min={Number(seleccionado?.horometro ?? 0) + 0.01} step="0.01" value={formMantencion.umbral_horas} onChange={(e) => setFormMantencion({ ...formMantencion, umbral_horas: e.target.value })} /></Campo> : <Campo label="Fecha programada" requerido><Input required type="date" min={new Date(Date.now() + 86400000).toISOString().slice(0, 10)} value={formMantencion.fecha_programada} onChange={(e) => setFormMantencion({ ...formMantencion, fecha_programada: e.target.value })} /></Campo>}<Campo label="Tarea a realizar" requerido><Textarea required value={formMantencion.descripcion} onChange={(e) => setFormMantencion({ ...formMantencion, descripcion: e.target.value })} /></Campo></> : <><Campo label="Falla detectada" requerido><Textarea required value={formMantencion.falla} onChange={(e) => setFormMantencion({ ...formMantencion, falla: e.target.value })} /></Campo><Campo label="Reparación realizada" requerido><Textarea required value={formMantencion.reparacion} onChange={(e) => setFormMantencion({ ...formMantencion, reparacion: e.target.value, descripcion: e.target.value })} /></Campo><Campo label="Costo" requerido><Input required type="number" min="0" step="0.01" value={formMantencion.costo} onChange={(e) => setFormMantencion({ ...formMantencion, costo: e.target.value })} /></Campo><label className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={formMantencion.reparacion_habilita} onChange={(e) => setFormMantencion({ ...formMantencion, reparacion_habilita: e.target.checked })} />La reparación deja el activo operativo</label></>}
      <div className="flex justify-end gap-2"><Button type="button" variante="secundario" onClick={() => setModalMantencion(false)}>Cancelar</Button><Button type="submit" disabled={guardando}>Guardar mantención</Button></div></form></Modal>

    <Modal abierto={reprogramando !== null} titulo="Reprogramar mantención" onCerrar={() => setReprogramando(null)}>
      <form onSubmit={guardarReprogramacion} className="space-y-4">
        <Campo label="Criterio" requerido><Select value={formReprogramacion.criterio} onChange={(e) => setFormReprogramacion({ ...formReprogramacion, criterio: e.target.value })}><option value="horas">Por horas</option><option value="fecha">Por fecha</option></Select></Campo>
        {formReprogramacion.criterio === "horas" ? <Campo label="Nuevo umbral de horas" ayuda={`Debe superar ${seleccionado?.horometro ?? 0} h`} requerido><Input required type="number" min={Number(seleccionado?.horometro ?? 0) + 0.01} step="0.01" value={formReprogramacion.umbral_horas} onChange={(e) => setFormReprogramacion({ ...formReprogramacion, umbral_horas: e.target.value })} /></Campo> : <Campo label="Nueva fecha" requerido><Input required type="date" min={new Date(Date.now() + 86400000).toISOString().slice(0, 10)} value={formReprogramacion.fecha_programada} onChange={(e) => setFormReprogramacion({ ...formReprogramacion, fecha_programada: e.target.value })} /></Campo>}
        <Campo label="Tarea a realizar" requerido><Textarea required value={formReprogramacion.descripcion} onChange={(e) => setFormReprogramacion({ ...formReprogramacion, descripcion: e.target.value })} /></Campo>
        <div className="flex justify-end gap-2"><Button type="button" variante="secundario" onClick={() => setReprogramando(null)}>Cancelar</Button><Button type="submit" disabled={guardando}>{guardando ? "Guardando..." : "Reprogramar"}</Button></div>
      </form>
    </Modal>

    <Modal abierto={modalHistorial} titulo={`Historial · ${seleccionado?.nombre ?? ""}`} onCerrar={() => setModalHistorial(false)}>
      <div className="space-y-5">
        <form onSubmit={aplicarFiltrosHistorial} className="rounded-lg bg-slate-50 p-3">
          <p className="mb-3 text-sm font-semibold text-slate-700">Filtrar mantenciones</p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Campo label="Tipo"><Select value={filtrosHistorial.tipo} onChange={(e) => setFiltrosHistorial({ ...filtrosHistorial, tipo: e.target.value })}><option value="">Todas</option><option value="preventiva">Preventivas</option><option value="correctiva">Correctivas</option></Select></Campo>
            <Campo label="Desde"><Input type="date" value={filtrosHistorial.desde} onChange={(e) => setFiltrosHistorial({ ...filtrosHistorial, desde: e.target.value })} /></Campo>
            <Campo label="Hasta"><Input type="date" min={filtrosHistorial.desde || undefined} value={filtrosHistorial.hasta} onChange={(e) => setFiltrosHistorial({ ...filtrosHistorial, hasta: e.target.value })} /></Campo>
          </div>
          <div className="mt-3 flex justify-end gap-2"><Button type="button" variante="fantasma" tamano="sm" onClick={() => { setFiltrosHistorial(FILTROS_HISTORIAL); if (seleccionado) cargarHistorial(seleccionado, FILTROS_HISTORIAL); }}>Limpiar</Button><Button type="submit" tamano="sm">Aplicar filtros</Button></div>
        </form>
        <div>
          <h4 className="mb-2 font-semibold text-slate-800">Mantenciones</h4>
          {mantenciones.length === 0 ? <p className="text-sm text-slate-500">Sin mantenciones para los filtros seleccionados.</p> : <div className="space-y-2">{mantenciones.map((m) => <div key={m.id} className="rounded-lg border border-slate-200 p-3 text-sm"><div className="flex justify-between"><strong className="capitalize">{m.tipo}</strong><Badge tono={tonoEstado(m.estado)}>{m.estado}</Badge></div><p className="mt-1 text-slate-600">{m.descripcion}</p><p className="mt-1 text-xs text-slate-500">{m.fecha_realizada ?? m.fecha_programada ?? `${m.umbral_horas} h`} {m.costo ? `· $${Number(m.costo).toLocaleString("es-CL")}` : ""}</p>{admin && m.tipo === "preventiva" && m.estado === "programada" && <div className="mt-2 flex gap-2"><Button tamano="sm" onClick={() => realizarPreventiva(m)}>Marcar realizada</Button><Button variante="secundario" tamano="sm" onClick={() => abrirReprogramacion(m)}>Reprogramar</Button></div>}</div>)}</div>}
        </div>
        <div><h4 className="mb-2 font-semibold text-slate-800">Lecturas de horómetro</h4>{usos.length === 0 ? <p className="text-sm text-slate-500">Sin lecturas registradas.</p> : <div className="space-y-1 text-sm">{usos.map((u) => <div key={u.id} className="flex justify-between border-b border-slate-100 py-2"><span>{new Date(u.fecha).toLocaleString("es-CL")}</span><strong>{Number(u.horas).toLocaleString("es-CL")} h</strong></div>)}</div>}</div>
      </div>
    </Modal>
  </div>;
}
