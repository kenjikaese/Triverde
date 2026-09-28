import datetime as dt

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from catalogo.models import Cliente, Material, Producto
from comercial.models import DetalleVenta, Venta
from common.models import PerfilUsuario, Rol
from inventario.models import Inventario
from produccion.models import Pila

from .models import PanelControl

User = get_user_model()


def crear_admin():
    rol_admin, _ = Rol.objects.get_or_create(nombre=Rol.ADMINISTRADOR)
    user = User.objects.create_user(username="rocio", password="x")
    PerfilUsuario.objects.create(usuario=user, rol=rol_admin)
    return user


class PanelControlTests(TestCase):
    def setUp(self):
        self.admin = crear_admin()
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

        cliente = Cliente.objects.create(nombre="Vivero Sur")
        material = Material.objects.create(nombre="Poda")
        producto = Producto.objects.create(nombre="Compost premium", material=material)

        Pila.objects.create(
            material=material,
            producto=producto,
            fecha_inicio=dt.date(2026, 9, 6),
            fecha_fin=dt.date(2026, 9, 20),
            peso_kg=450,
            estado=Pila.PROCESADA,
        )
        Pila.objects.create(
            material=material, fecha_inicio=dt.date(2026, 9, 12), peso_kg=180, estado=Pila.EN_PROCESO
        )

        venta = Venta.objects.create(cliente=cliente, fecha=dt.date(2026, 9, 15))
        DetalleVenta.objects.create(venta=venta, producto=producto, cantidad_kg=100, monto=50000)

        Inventario.objects.create(material=material, estado="disponible", cantidad_kg=1200)

    def test_sin_panelcontrol_previo_usa_set_por_defecto(self):
        resp = self.client.get("/api/v1/panel/")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(sorted(resp.data["indicadores_visibles"]), ["inventario", "produccion", "ventas"])
        self.assertIn("inventario", resp.data["bloques"])
        self.assertIn("produccion", resp.data["bloques"])
        self.assertIn("ventas", resp.data["bloques"])

    def test_bloque_sin_datos_aparece_en_cero_y_pila_en_proceso_marcada(self):
        Inventario.objects.all().delete()
        resp = self.client.get("/api/v1/panel/")
        self.assertEqual(resp.data["bloques"]["inventario"], [])
        estados = {b["estado"] for b in resp.data["bloques"]["produccion"]}
        self.assertIn("en_proceso", estados)

    def test_guardar_preferencias_crea_o_actualiza_panelcontrol_y_panel_refleja_seleccion(self):
        resp = self.client.post(
            "/api/v1/panel/preferencias/", {"indicadores_visibles": ["ventas"]}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["indicadores_visibles"], ["ventas"])

        panel = self.client.get("/api/v1/panel/")
        self.assertEqual(panel.data["indicadores_visibles"], ["ventas"])
        self.assertEqual(set(panel.data["bloques"].keys()), {"ventas"})

    def test_guardar_sin_indicadores_se_rechaza(self):
        resp = self.client.post("/api/v1/panel/preferencias/", {"indicadores_visibles": []}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_guardar_con_indicador_invalido_se_rechaza(self):
        resp = self.client.post(
            "/api/v1/panel/preferencias/", {"indicadores_visibles": ["hackerman"]}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_guardar_sin_cambios_no_genera_nueva_actualizacion(self):
        self.client.post("/api/v1/panel/preferencias/", {"indicadores_visibles": ["ventas"]}, format="json")
        panel_antes = PanelControl.objects.get(usuario=self.admin)
        actualizado_antes = panel_antes.actualizado

        self.client.post("/api/v1/panel/preferencias/", {"indicadores_visibles": ["ventas"]}, format="json")
        panel_despues = PanelControl.objects.get(usuario=self.admin)
        self.assertEqual(actualizado_antes, panel_despues.actualizado)

    def test_sin_rol_administrador_no_accede(self):
        rol_operador, _ = Rol.objects.get_or_create(nombre=Rol.OPERADOR)
        operador = User.objects.create_user(username="op", password="x")
        PerfilUsuario.objects.create(usuario=operador, rol=rol_operador)
        client = APIClient()
        client.force_authenticate(operador)
        resp = client.get("/api/v1/panel/")
        self.assertEqual(resp.status_code, 403)
