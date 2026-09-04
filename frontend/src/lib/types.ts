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

// --- Modulo 8: Comercial (CU-55 a CU-64) -----------------------------------

export interface Cotizacion {
  id: number;
  cliente: number;
  cliente_razon_social?: string;
  fecha: string;
  distancia_km: string;
  servicio: string;
  costo_estimado: string | null;
  estado: string;
  advertencia?: string;
}

export interface CotizacionExportada {
  cotizacion: number;
  fecha: string;
  cliente: {
    razon_social: string;
    rut: string | null;
    nombre_contacto: string | null;
    telefono: string | null;
    email: string | null;
    direccion: string | null;
  };
  servicio: string;
  distancia_km: string;
  costo_estimado: string | null;
}

export interface DetalleVenta {
  id?: number;
  producto: number;
  producto_nombre?: string;
  cantidad: string;
  unidad?: "saco" | "m3";
  precio_unitario?: string;
  subtotal?: string;
}

export type EstadoVenta = "pendiente" | "despachada";

export interface Venta {
  id: number;
  cliente: number;
  cliente_razon_social?: string;
  fecha: string;
  estado: EstadoVenta;
  total: string;
  detalles: DetalleVenta[];
  despachada: boolean;
}

export interface TotalesVentas {
  cantidad: number;
  total: string;
}

export interface Despacho {
  id: number;
  venta: number;
  fecha: string;
  direccion: string | null;
  receptor: string;
  estado: string;
}

export interface Cobro {
  id: number;
  venta: number | null;
  recepcion: number | null;
  cliente: number;
  monto: string;
  monto_sugerido: string | null;
  fecha: string;
  medio: string | null;
  estado: string;
}

export interface SugerenciaCobro {
  recepcion: number;
  cliente: number;
  monto_sugerido: string | null;
  cobrada: boolean;
}

export interface DocumentoTributario {
  id: number;
  venta: number | null;
  cobro: number | null;
  cliente: number;
  tipo: "boleta" | "factura";
  folio: string | null;
  monto: string;
  estado: "pendiente";
  fecha: string;
}

export interface MovimientoCuentaCorriente {
  tipo: "venta" | "cobro";
  id: number;
  fecha: string;
  detalle: string;
  monto: string;
}

export interface CuentaCorriente {
  cliente: number;
  razon_social: string;
  estado_pago: "al dia" | "con deuda";
  total_ventas: string;
  total_cobros: string;
  saldo: string;
  movimientos: MovimientoCuentaCorriente[];
}

export interface CostoKm {
  costo_por_km: string | null;
  configurado: boolean;
}
