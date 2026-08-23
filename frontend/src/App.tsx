import { Routes, Route, Navigate } from "react-router-dom";
import { RutaProtegida } from "@/components/RutaProtegida";
import { AppShell } from "@/components/layout/AppShell";
import { Login } from "@/pages/Login";
import { PanelControl } from "@/pages/PanelControl";
import { RegistroRecepcion } from "@/pages/recepcion/RegistroRecepcion";
import { ListaClientes } from "@/pages/mantenedores/ListaClientes";
import { ListaTransportistas } from "@/pages/mantenedores/ListaTransportistas";
import { ListaMateriales } from "@/pages/mantenedores/ListaMateriales";
import { ListaProductos } from "@/pages/mantenedores/ListaProductos";
import { ListaVehiculos } from "@/pages/mantenedores/ListaVehiculos";
import { PanelParametros } from "@/pages/configuracion/PanelParametros";
import { TablaTarifas } from "@/pages/configuracion/TablaTarifas";
import { ListaUsuarios } from "@/pages/gestion/ListaUsuarios";
import { BitacoraAuditoria } from "@/pages/gestion/BitacoraAuditoria";
import { ColaSincronizacion } from "@/pages/operacion/ColaSincronizacion";
import { Inventario } from "@/pages/operacion/Inventario";
import { ListaPilas } from "@/pages/operacion/ListaPilas";
import { MezclaObjetivo } from "@/pages/operacion/MezclaObjetivo";
import { Alertas } from "@/pages/operacion/Alertas";
import { ListaMaquinaria } from "@/pages/mantenimiento/ListaMaquinaria";
import { EstadoFlota } from "@/pages/mantenimiento/EstadoFlota";
import { Cotizador } from "@/pages/comercial/Cotizador";
import { ListaVentas } from "@/pages/comercial/ListaVentas";
import { Cobros } from "@/pages/comercial/Cobros";
import { Certificados } from "@/pages/trazabilidad/Certificados";
import { ExportacionSinader } from "@/pages/trazabilidad/ExportacionSinader";
import { IndicadorAmbiental } from "@/pages/trazabilidad/IndicadorAmbiental";
import { Proyecciones } from "@/pages/gestion/Proyecciones";
import { Reportes } from "@/pages/gestion/Reportes";
import { ListaDocumentos } from "@/pages/gestion/ListaDocumentos";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        element={
          <RutaProtegida>
            <AppShell />
          </RutaProtegida>
        }
      >
        {/* Cableadas a la API (Inc 1) */}
        <Route path="/" element={<PanelControl />} />
        <Route path="/recepcion" element={<RegistroRecepcion />} />
        <Route path="/clientes" element={<ListaClientes />} />

        {/* Vistas Inc 1 con backend real */}
        <Route path="/sincronizacion" element={<ColaSincronizacion />} />
        <Route path="/transportistas" element={<ListaTransportistas />} />
        <Route path="/materiales" element={<ListaMateriales />} />
        <Route path="/productos" element={<ListaProductos />} />
        <Route path="/vehiculos" element={<ListaVehiculos />} />
        <Route path="/parametros" element={<PanelParametros />} />
        <Route path="/tarifas" element={<TablaTarifas />} />
        <Route path="/usuarios" element={<ListaUsuarios />} />
        <Route path="/auditoria" element={<BitacoraAuditoria />} />

        {/* Mockups visuales (modulos posteriores, sin backend) */}
        <Route path="/inventario" element={<Inventario />} />
        <Route path="/pilas" element={<ListaPilas />} />
        <Route path="/mezcla" element={<MezclaObjetivo />} />
        <Route path="/alertas" element={<Alertas />} />
        <Route path="/maquinaria" element={<ListaMaquinaria />} />
        <Route path="/flota" element={<EstadoFlota />} />
        <Route path="/cotizador" element={<Cotizador />} />
        <Route path="/ventas" element={<ListaVentas />} />
        <Route path="/cobros" element={<Cobros />} />
        <Route path="/certificados" element={<Certificados />} />
        <Route path="/sinader" element={<ExportacionSinader />} />
        <Route path="/ambiental" element={<IndicadorAmbiental />} />
        <Route path="/proyecciones" element={<Proyecciones />} />
        <Route path="/reportes" element={<Reportes />} />
        <Route path="/documentos" element={<ListaDocumentos />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
