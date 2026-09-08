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
  estado_operativo: "operativa" | "en mantencion" | "fuera de servicio";
  estado: EstadoActivo;
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

// Modulo 7 - Proyecciones (espejo de proyecciones/serializers.py)
export type TipoProyeccion = "mensual" | "semanal" | "comercial";

export interface Proyeccion {
  id: number;
  tipo: TipoProyeccion;
  tipo_display: string;
  periodo_inicio: string;
  periodo_fin: string;
  material: number | null;
  material_nombre: string | null;
  supuestos: Record<string, unknown>;
  valor_proyectado: Record<string, number>;
  fecha_generada: string;
  usuario: number | null;
}

export interface ComparacionProyeccion {
  parcial: boolean;
  proyectado_m3: number;
  real_m3: number | null;
  desviacion_m3: number | null;
  desviacion_pct: number | null;
  ingreso_real?: number | null;
}
