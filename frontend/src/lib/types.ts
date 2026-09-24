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
  clave: string;
  nivel: string;
  estado: "activa" | "resuelta";
  mensaje: string;
  categoria: "seca" | "verde" | null;
  categoria_display: string | null;
  faltante_m3: string;
  disponible_m3: string;
  pila: number | null;
  pila_codigo: string | null;
  mantencion: number | null;
  activo_nombre: string | null;
  fecha_generada: string;
  fecha_resuelta: string | null;
  resuelta_por_username?: string | null;
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

// Modulo 9 - Indicador ambiental (CU-69 a CU-71)
export type OrigenIndicadorAmbiental = "recepcion" | "pila";

export interface IndicadorAmbientalDetalle {
  id: number;
  origen: OrigenIndicadorAmbiental;
  origen_display: string;
  recepcion: number | null;
  pila: number | null;
  referencia: string;
  descripcion: string;
  co2_evitado_kg: string;
  metodo: string;
  fecha: string;
}

export interface CalculoAmbientalPendiente {
  origen: OrigenIndicadorAmbiental;
  objeto_id: number;
  referencia: string;
  motivo: string;
}

export interface ResumenIndicadorAmbiental {
  periodo: { desde: string | null; hasta: string | null };
  total_co2_evitado_kg: string;
  recepciones_co2_evitado_kg: string;
  pilas_co2_evitado_kg: string;
  cantidad_recepciones: number;
  cantidad_pilas: number;
  resultados: IndicadorAmbientalDetalle[];
  pendientes: CalculoAmbientalPendiente[];
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

export interface PilaResumen {
  id: number;
  codigo: string;
  fecha_inicio: string;
  estado: string;
  volumen_total_m3: string;
}

export interface Existencia {
  id: number;
  material: number;
  material_nombre: string;
  material_categoria: "seca" | "verde" | null;
  etapa: string;
  volumen_m3: string;
  actualizado: string;
}

export interface MezclaCategoria {
  categoria: "seca" | "verde";
  volumen_m3: string;
}

export interface MezclaObjetivo {
  pila: number;
  pila_codigo: string;
  estado: string;
  receta: {
    id: number;
    nombre: string;
    relacion_seca: string;
    relacion_verde: string;
    proporcion: string;
  } | null;
  mensaje: string | null;
  actual: MezclaCategoria[];
  faltantes: MezclaCategoria[];
  disponibles: MezclaCategoria[];
}
