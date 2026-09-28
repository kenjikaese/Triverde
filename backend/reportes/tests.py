from datetime import date
from decimal import Decimal
from io import BytesIO

from django.urls import reverse
from openpyxl import load_workbook
from rest_framework import status
from rest_framework.test import APITestCase

from acceso.models import BitacoraAuditoria, Rol, Usuario
from comercial.models import Cobro, DetalleVenta, Venta
from inventario.models import ComposicionPila, Inventario, Pila, ProcesoPila
from mantenedores.models import Cliente, Material, Producto
from recepcion.models import DetalleRecepcion, Recepcion

from .models import PanelControl, Reporte


class ReportesTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rol = Rol.objects.create(nombre=Rol.ADMINISTRADOR, descripcion="a")
        cls.admin = Usuario.objects.create_user(
            username="admin", password="admin12345", nombre_completo="Admin", rol=cls.rol
        )
        cls.cliente = Cliente.objects.create(razon_social="Cliente Prueba")
        cls.material = Material.objects.create(
            nombre="Rama", categoria=Material.VERDE,
            densidad_kg_m3=Decimal("250"), factor_reduccion_chip=Decimal("5"),
            admite_chip=True,
        )
        cls.producto = Producto.objects.create(
            nombre="Compost", tipo=Producto.COMPOST, unidad_de_venta=Producto.M3,
            precio=Decimal("100")
        )

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def generar(self, tipo, formato="pdf", **filtros):
        datos = {
            "tipo": tipo, "periodo_inicio": "2026-09-01", "periodo_fin": "2026-09-30",
            "formato": formato, **filtros,
        }
        return self.client.post(reverse("reporte-list"), datos, format="json")

    def test_recepciones_agrega_por_material_y_cliente(self):
        recepcion = Recepcion.objects.create(
            cliente=self.cliente, fecha=date(2026, 9, 10), hora="10:00", estado=Recepcion.RECIBIDA
        )
        DetalleRecepcion.objects.create(
            recepcion=recepcion, material=self.material, volumen_m3=Decimal("12"),
            peso_derivado_kg=Decimal("3000"),
        )
        respuesta = self.generar(Reporte.RECEPCIONES, cliente=self.cliente.pk)
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        self.assertEqual(respuesta.data["contenido"]["totales"]["volumen_m3"], 12.0)
        self.assertEqual(len(respuesta.data["contenido"]["por_material"]), 1)

    def test_produccion_distingue_en_curso_y_guarda_inventario(self):
        pila = Pila.objects.create(codigo="P-0001", fecha_inicio=date(2026, 9, 1), estado=Pila.EN_PROCESO)
        ComposicionPila.objects.create(pila=pila, material=self.material, volumen_m3=Decimal("10"))
        ProcesoPila.objects.create(
            pila=pila, tipo=ProcesoPila.ENSACADO, fecha="2026-09-10T10:00:00Z", volumen_m3=Decimal("8")
        )
        Inventario.objects.create(material=self.material, etapa=Inventario.CURADO, volumen_m3=Decimal("20"))
        respuesta = self.generar(Reporte.PRODUCCION)
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        fila = respuesta.data["contenido"]["por_material"][0]
        self.assertEqual(fila["en_curso_m3"], 8.0)
        self.assertEqual(fila["inventario_resultante_m3"], 20.0)

    def test_ventas_cobros_calcula_pendiente(self):
        venta = Venta.objects.create(cliente=self.cliente, fecha=date(2026, 9, 10), total=Decimal("100"))
        DetalleVenta.objects.create(
            venta=venta, producto=self.producto, cantidad=Decimal("1"), unidad="m3",
            precio_unitario=Decimal("100"), subtotal=Decimal("100"),
        )
        Cobro.objects.create(venta=venta, cliente=self.cliente, monto=Decimal("40"), fecha=date(2026, 9, 11))
        respuesta = self.generar(Reporte.VENTAS_COBROS)
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        self.assertEqual(respuesta.data["contenido"]["totales"]["pendiente"], 60.0)

    def test_rango_invalido_no_crea_reporte(self):
        respuesta = self.client.post(
            reverse("reporte-list"),
            {"tipo": Reporte.RECEPCIONES, "periodo_inicio": "2026-09-30", "periodo_fin": "2026-09-01"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Reporte.objects.count(), 0)

    def test_periodo_sin_datos_se_puede_exportar(self):
        for formato in (Reporte.PDF, Reporte.EXCEL, Reporte.CSV):
            respuesta = self.generar(Reporte.RECEPCIONES, formato=formato)
            self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
            exportacion = self.client.get(
                reverse("reporte-exportar", args=[respuesta.data["id"]])
            )
            self.assertEqual(exportacion.status_code, status.HTTP_200_OK)
            self.assertIn("attachment", exportacion["Content-Disposition"])
            if formato == Reporte.PDF:
                self.assertTrue(exportacion.content.startswith(b"%PDF"))
            elif formato == Reporte.EXCEL:
                libro = load_workbook(BytesIO(exportacion.content))
                self.assertEqual(libro.active["A1"].value, "Reporte")
            else:
                self.assertIn("por_material", exportacion.content.decode())
        self.assertTrue(BitacoraAuditoria.objects.filter(entidad_afectada="Reporte").exists())

    def test_recepciones_solo_cuenta_descargas_recibidas(self):
        for estado, volumen in ((Recepcion.RECIBIDA, "12"), (Recepcion.RECHAZADA, "30"), (Recepcion.EN_CURSO, "7")):
            recepcion = Recepcion.objects.create(
                cliente=self.cliente, fecha=date(2026, 9, 10), hora="10:00", estado=estado
            )
            DetalleRecepcion.objects.create(
                recepcion=recepcion, material=self.material, volumen_m3=Decimal(volumen),
                peso_derivado_kg=Decimal(volumen) * 250,
            )
        respuesta = self.generar(Reporte.RECEPCIONES)
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        self.assertEqual(respuesta.data["contenido"]["totales"]["volumen_m3"], 12.0)

    def test_filtros_quedan_en_el_reporte_y_en_la_exportacion(self):
        respuesta = self.generar(Reporte.RECEPCIONES, formato=Reporte.CSV, cliente=self.cliente.pk)
        self.assertEqual(respuesta.data["contenido"]["filtros"], {"cliente": "Cliente Prueba"})
        exportacion = self.client.get(reverse("reporte-exportar", args=[respuesta.data["id"]]))
        self.assertIn("cliente: Cliente Prueba", exportacion.content.decode("utf-8-sig"))

    def test_exportar_en_otro_formato_sin_regenerar(self):
        respuesta = self.generar(Reporte.VENTAS_COBROS, formato=Reporte.PDF)
        url = reverse("reporte-exportar", args=[respuesta.data["id"]])
        exportacion = self.client.get(url, {"formato": Reporte.EXCEL})
        self.assertEqual(exportacion.status_code, status.HTTP_200_OK)
        self.assertIn(".xlsx", exportacion["Content-Disposition"])
        self.assertEqual(self.client.get(url, {"formato": "docx"}).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Reporte.objects.count(), 1)

    def test_solo_administrador_genera_reportes(self):
        operador = Usuario.objects.create_user(
            username="operador", password="operador12345", nombre_completo="Operador",
            rol=Rol.objects.create(nombre=Rol.OPERADOR, descripcion="o"),
        )
        self.client.force_authenticate(operador)
        self.assertEqual(self.generar(Reporte.RECEPCIONES).status_code, status.HTTP_403_FORBIDDEN)


class PanelControlTests(APITestCase):
    """Criterios de aceptacion de Parte D (CU-72, CU-77)."""

    @classmethod
    def setUpTestData(cls):
        cls.rol = Rol.objects.create(nombre=Rol.ADMINISTRADOR, descripcion="a")
        cls.admin = Usuario.objects.create_user(
            username="admin-panel", password="admin12345", nombre_completo="Admin", rol=cls.rol
        )
        cls.cliente = Cliente.objects.create(razon_social="Vivero Sur")
        cls.material = Material.objects.create(nombre="Poda", categoria=Material.VERDE)
        cls.producto = Producto.objects.create(
            nombre="Compost premium", tipo=Producto.COMPOST, unidad_de_venta=Producto.SACO,
            precio=Decimal("50000"),
        )

        pila_procesada = Pila.objects.create(
            codigo="P-0001", fecha_inicio=date(2026, 9, 6), estado=Pila.CERRADA
        )
        ComposicionPila.objects.create(pila=pila_procesada, material=cls.material, volumen_m3=Decimal("4.5"))

        pila_en_proceso = Pila.objects.create(
            codigo="P-0002", fecha_inicio=date(2026, 9, 12), estado=Pila.EN_PROCESO
        )
        ComposicionPila.objects.create(pila=pila_en_proceso, material=cls.material, volumen_m3=Decimal("1.8"))

        venta = Venta.objects.create(cliente=cls.cliente, fecha=date(2026, 9, 15), total=Decimal("50000"))
        DetalleVenta.objects.create(
            venta=venta, producto=cls.producto, cantidad=Decimal("1"), unidad="saco",
            precio_unitario=Decimal("50000"), subtotal=Decimal("50000"),
        )

        Inventario.objects.create(material=cls.material, etapa=Inventario.CURADO, volumen_m3=Decimal("12"))

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_sin_panelcontrol_previo_usa_set_por_defecto(self):
        respuesta = self.client.get(reverse("panel-list"))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertEqual(
            sorted(respuesta.data["indicadores_visibles"]), ["inventario", "produccion", "ventas"]
        )
        self.assertIn("inventario", respuesta.data["bloques"])
        self.assertIn("produccion", respuesta.data["bloques"])
        self.assertIn("ventas", respuesta.data["bloques"])

    def test_bloque_sin_datos_aparece_en_cero_y_pila_en_proceso_marcada(self):
        Inventario.objects.all().delete()
        respuesta = self.client.get(reverse("panel-list"))
        self.assertEqual(respuesta.data["bloques"]["inventario"], [])
        estados = {fila["estado"] for fila in respuesta.data["bloques"]["produccion"]}
        self.assertIn("en_proceso", estados)

    def test_guardar_preferencias_crea_o_actualiza_panelcontrol_y_panel_refleja_seleccion(self):
        respuesta = self.client.post(
            reverse("panel-preferencias"), {"indicadores_visibles": ["ventas"]}, format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertEqual(respuesta.data["indicadores_visibles"], ["ventas"])

        panel = self.client.get(reverse("panel-list"))
        self.assertEqual(panel.data["indicadores_visibles"], ["ventas"])
        self.assertEqual(set(panel.data["bloques"].keys()), {"ventas"})
        self.assertTrue(BitacoraAuditoria.objects.filter(entidad_afectada="PanelControl").exists())

    def test_guardar_sin_indicadores_se_rechaza(self):
        respuesta = self.client.post(reverse("panel-preferencias"), {"indicadores_visibles": []}, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_guardar_con_indicador_invalido_se_rechaza(self):
        respuesta = self.client.post(
            reverse("panel-preferencias"), {"indicadores_visibles": ["hackerman"]}, format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_guardar_sin_cambios_no_genera_nueva_actualizacion(self):
        self.client.post(reverse("panel-preferencias"), {"indicadores_visibles": ["ventas"]}, format="json")
        actualizado_antes = PanelControl.objects.get(usuario=self.admin).actualizado

        self.client.post(reverse("panel-preferencias"), {"indicadores_visibles": ["ventas"]}, format="json")
        actualizado_despues = PanelControl.objects.get(usuario=self.admin).actualizado
        self.assertEqual(actualizado_antes, actualizado_despues)

    def test_sin_rol_administrador_no_accede(self):
        operador = Usuario.objects.create_user(
            username="operador-panel", password="operador12345", nombre_completo="Operador",
            rol=Rol.objects.create(nombre=Rol.OPERADOR, descripcion="o"),
        )
        self.client.force_authenticate(operador)
        self.assertEqual(self.client.get(reverse("panel-list")).status_code, status.HTTP_403_FORBIDDEN)
