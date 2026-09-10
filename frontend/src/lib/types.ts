// Tipos del dominio, espejo de los serializers del backend (docs/11 SS11.6).
// Se mantienen sincronizados con backend/*/serializers.py.

export type RolNombre = "Administrador" | "Operador" | "Transportista";

export interface Rol {
  id: number;
  nombre: RolNombre;
  descripcion: string | null;
}

export interface Usuario {
  id: number;
  username: string;
  nombre_completo: string;
  rol: number;
  rol_nombre?: RolNombre;
  estado: "activo" | "inactivo";
}

export interface LoginResponse {
  token: string;
  usuario: Usuario;
}

export type EstadoActivo = "activo" | "inactivo";

export interface Cliente {
  id: number;
  razon_social: string;
  rut: string | null;
  nombre_contacto: string | null;
  telefono: string | null;
  email: string | null;
  direccion: string | null;
  estado_pago: "al dia" | "con deuda";
  estado: EstadoActivo;
}

export interface Transportista {
  id: number;
  nombre: string;
  rut: string | null;
  telefono: string | null;
  cliente: number;
  usuario: number | null;
  estado: EstadoActivo;
}

export interface Vehiculo {
  id: number;
  patente: string;
  cliente: number | null;
  capacidad_m3: string | null;
  tramo: string | null;
  descripcion: string | null;
  es_mantenible: boolean;
  datos_tecnicos: Record<string, string>;
  horometro: string;
  estado_operativo: "operativa" | "en mantencion" | "fuera de servicio";
  estado: EstadoActivo;
}

export type EstadoOperativo = "operativa" | "en mantencion" | "fuera de servicio";
export type ClaseActivo = "maquinaria" | "vehiculo";

export interface Maquinaria {
  id: number;
  codigo: string;
  clase_activo: "maquinaria";
  nombre: string;
  tipo: string;
  datos_tecnicos: Record<string, string>;
  horometro: string;
  estado_operativo: EstadoOperativo;
  estado: EstadoActivo;
}

export interface RegistroUso {
  id: number;
  maquinaria: number | null;
  vehiculo: number | null;
  activo_nombre: string;
  horas: string;
  fecha: string;
  operador: number;
  operador_nombre: string;
  horas_transcurridas: string;
}

export interface Mantencion {
  id: number;
  maquinaria: number | null;
  vehiculo: number | null;
  activo_nombre: string;
  tipo: "preventiva" | "correctiva";
  criterio: "fecha" | "horas" | null;
  umbral_horas: string | null;
  fecha_programada: string | null;
  fecha_realizada: string | null;
  costo: string | null;
  descripcion: string;
  falla: string;
  reparacion: string;
  estado: "programada" | "realizada";
}

export interface EstadoFlotaItem {
  id: number;
  clase_activo: ClaseActivo;
  codigo: string;
  nombre: string;
  tipo: string;
  horometro: string;
  estado_operativo: EstadoOperativo;
  proxima_mantencion: Mantencion | null;
  alerta: string | null;
  nivel_alerta: "informativa" | "advertencia" | "critica" | null;
}

export interface Alerta {
  id: number;
  origen: "mezcla" | "mantencion" | "documento";
  nivel: "informativa" | "advertencia" | "critica";
  estado: "activa" | "resuelta";
  mensaje: string;
  fecha_generada: string;
  fecha_resuelta: string | null;
  mantencion: number | null;
  activo_nombre: string | null;
}

export interface Material {
  id: number;
  nombre: string;
  categoria: "seca" | "verde" | null;
  densidad_kg_m3: string | null;
  factor_reduccion_chip: string | null;
  admite_chip: boolean;
  estado: EstadoActivo;
}

export interface Producto {
  id: number;
  nombre: string;
  tipo: "chip" | "mulch" | "compost" | "lena";
  precio: string | null;
  unidad_de_venta: "saco" | "m3";
  estado: EstadoActivo;
}

export interface ParametroConversion {
  id: number;
  clave: string;
  nombre: string;
  valor: string;
  unidad: string | null;
  descripcion: string | null;
}

export interface TarifaRecepcion {
  id: number;
  tramo_min_m3: string;
  tramo_max_m3: string;
  monto: string;
  vigente: boolean;
}

export type EstadoRecepcion =
  | "en curso"
  | "pendiente de inspeccion"
  | "recibida"
  | "rechazada";

export type EstadoSincronizacion =
  | "pendiente"
  | "sincronizada"
  | "en conflicto";

export interface DetalleRecepcion {
  id?: number;
  id_local?: string;
  material: number;
  volumen_m3: string;
  peso_derivado_kg?: string;
  chip_derivado_m3?: string | null;
  destino_sugerido: "a pila" | "a chip" | "a venta directa" | null;
}

export interface Recepcion {
  id: number;
  id_local: string;
  estado_sincronizacion: EstadoSincronizacion;
  cliente: number;
  transportista: number | null;
  vehiculo: number | null;
  operador: number | null;
  conductor: string | null;
  fecha: string;
  hora: string;
  estado: EstadoRecepcion;
  motivo_rechazo: string | null;
  observaciones: string | null;
  detalles: DetalleRecepcion[];
}
