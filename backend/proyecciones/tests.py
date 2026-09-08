"""Tests del Modulo 7 - Proyecciones (CU-50 a CU-54).

Cubren los criterios de aceptacion del spec M07: calculo con parametros
vigentes, senalamiento de parametro faltante, ajuste de supuestos sin tocar la
configuracion global, comparacion con lo real (con aviso de periodo parcial) y
persistencia de cada proyeccion.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from acceso.models import BitacoraAuditoria, Rol, Usuario
from mantenedores.models import Cliente, Material
from recepcion.models import DetalleRecepcion, Recepcion

from .models import Proyeccion


class ProyeccionesTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rol_admin = Rol.objects.create(nombre=Rol.ADMINISTRADOR, descripcion="a")
        cls.rol_operador = Rol.objects.create(nombre=Rol.OPERADOR, descripcion="o")
        cls.admin = Usuario.objects.create_user(
            username="admin", password="admin12345",
            nombre_completo="Admin", rol=cls.rol_admin,
        )
        cls.operador = Usuario.objects.create_user(
            username="operador", password="operador12345",
            nombre_completo="Operador", rol=cls.rol_operador,
        )
        cls.material = Material.objects.create(
            nombre="Rama", categoria=Material.VERDE,
            densidad_kg_m3=Decimal("250.00"), factor_reduccion_chip=Decimal("5.00"),
            admite_chip=True,
        )
        cls.cliente = Cliente.objects.create(razon_social="Cliente Prueba")

    def supuestos_mensual(self):
        return {
            "volumen_entrada_m3": "100",
            "densidad_kg_m3": "250",
            "rendimiento_compost": "0.4",
            "sacos_por_m3": "20",
        }


class CalculoTests(ProyeccionesTestBase):
    def test_crear_mensual_devuelve_toneladas_m3_sacos(self):
        """Criterio 1: aplica los parametros y devuelve toneladas, m3 y sacos."""
        self.client.force_authenticate(self.admin)
        respuesta = self.client.post(
            reverse("proyeccion-list"),
            {
                "tipo": Proyeccion.MENSUAL,
                "periodo_inicio": "2026-09-01",
                "periodo_fin": "2026-09-30",
                "supuestos": self.supuestos_mensual(),
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        valor = respuesta.data["valor_proyectado"]
        # 100 m3 x 250 kg/m3 / 1000 = 25 t ; 100 x 0.4 = 40 m3 ; 40 x 20 = 800 sacos
        self.assertEqual(valor["toneladas_entrada"], 25.0)
        self.assertEqual(valor["m3_compost"], 40.0)
        self.assertEqual(valor["sacos"], 800)

    def test_semanal_aplica_parametros_del_material(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.post(
            reverse("proyeccion-list"),
            {
                "tipo": Proyeccion.SEMANAL,
                "periodo_inicio": "2026-09-01",
                "periodo_fin": "2026-09-07",
                "material": self.material.pk,
                "supuestos": {"volumen_entrada_m3": "50"},
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        valor = respuesta.data["valor_proyectado"]
        # densidad y factor se toman del material: 50/5 = 10 m3 chip ; 50x250/1000 = 12.5 t
        self.assertEqual(valor["chip_m3"], 10.0)
        self.assertEqual(valor["toneladas"], 12.5)

    def test_falta_parametro_indica_cual_y_no_calcula(self):
        """Criterio 2: falta un parametro requerido -> lo indica y no calcula."""
        self.client.force_authenticate(self.admin)
        supuestos = self.supuestos_mensual()
        del supuestos["sacos_por_m3"]
        respuesta = self.client.post(
            reverse("proyeccion-list"),
            {
                "tipo": Proyeccion.MENSUAL,
                "periodo_inicio": "2026-09-01",
                "periodo_fin": "2026-09-30",
                "supuestos": supuestos,
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sacos_por_m3", str(respuesta.data))
        self.assertEqual(Proyeccion.objects.count(), 0)

    def test_semanal_requiere_material(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.post(
            reverse("proyeccion-list"),
            {
                "tipo": Proyeccion.SEMANAL,
                "periodo_inicio": "2026-09-01",
                "periodo_fin": "2026-09-07",
                "supuestos": {"volumen_entrada_m3": "50"},
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("material", respuesta.data)

    def test_cada_proyeccion_queda_guardada(self):
        """Criterio 5: cada proyeccion calculada queda guardada para consultarse."""
        self.client.force_authenticate(self.admin)
        self.client.post(
            reverse("proyeccion-list"),
            {
                "tipo": Proyeccion.MENSUAL,
                "periodo_inicio": "2026-09-01",
                "periodo_fin": "2026-09-30",
                "supuestos": self.supuestos_mensual(),
            },
            format="json",
        )
        self.assertEqual(Proyeccion.objects.count(), 1)
        lista = self.client.get(reverse("proyeccion-list"))
        self.assertEqual(len(lista.data), 1)
        self.assertTrue(
            BitacoraAuditoria.objects.filter(entidad_afectada="Proyeccion").exists()
        )

    def test_operador_no_puede_crear(self):
        self.client.force_authenticate(self.operador)
        respuesta = self.client.post(
            reverse("proyeccion-list"),
            {
                "tipo": Proyeccion.MENSUAL,
                "periodo_inicio": "2026-09-01",
                "periodo_fin": "2026-09-30",
                "supuestos": self.supuestos_mensual(),
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)


class AjusteTests(ProyeccionesTestBase):
    def test_ajustar_recalcula_sin_tocar_parametro_del_sistema(self):
        """Criterio 3: ajustar un supuesto recalcula esa proyeccion sin cambiar
        el parametro vigente del sistema; conserva el escenario base."""
        self.client.force_authenticate(self.admin)
        creada = self.client.post(
            reverse("proyeccion-list"),
            {
                "tipo": Proyeccion.MENSUAL,
                "periodo_inicio": "2026-09-01",
                "periodo_fin": "2026-09-30",
                "supuestos": self.supuestos_mensual(),
            },
            format="json",
        )
        pk = creada.data["id"]
        densidad_antes = Material.objects.get(pk=self.material.pk).densidad_kg_m3

        respuesta = self.client.post(
            reverse("proyeccion-ajustar", args=[pk]),
            {"supuestos": {"rendimiento_compost": "0.6"}},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        # nuevo m3_compost = 100 x 0.6 = 60 (antes 40)
        self.assertEqual(respuesta.data["valor_proyectado"]["m3_compost"], 60.0)
        # el parametro del sistema (densidad del material) no se toco
        self.assertEqual(
            Material.objects.get(pk=self.material.pk).densidad_kg_m3, densidad_antes
        )
        # se conserva el escenario base como referencia
        base = respuesta.data["supuestos"]["_escenario_base"]
        self.assertEqual(base["valor_proyectado"]["m3_compost"], 40.0)


class ComparacionTests(ProyeccionesTestBase):
    def _crear_proyeccion(self, inicio, fin):
        proy = Proyeccion.objects.create(
            tipo=Proyeccion.MENSUAL, periodo_inicio=inicio, periodo_fin=fin,
            supuestos={"volumen_entrada_m3": "100"}, valor_proyectado={},
            usuario=self.admin,
        )
        return proy

    def _recepcion_con_volumen(self, fecha, volumen):
        recepcion = Recepcion.objects.create(
            cliente=self.cliente, fecha=fecha, hora="10:00",
            estado=Recepcion.RECIBIDA,
        )
        DetalleRecepcion.objects.create(
            recepcion=recepcion, material=self.material,
            volumen_m3=Decimal(volumen), peso_derivado_kg=Decimal(volumen) * Decimal("250"),
        )

    def test_comparar_muestra_proyectado_real_y_desviacion(self):
        """Criterio 4: comparar muestra proyectado, real y desviacion."""
        self.client.force_authenticate(self.admin)
        proy = self._crear_proyeccion(date(2026, 8, 1), date(2026, 8, 31))
        self._recepcion_con_volumen(date(2026, 8, 10), "40")
        self._recepcion_con_volumen(date(2026, 8, 20), "20")

        respuesta = self.client.get(reverse("proyeccion-comparar", args=[proy.pk]))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["proyectado_m3"], 100.0)
        self.assertEqual(respuesta.data["real_m3"], 60.0)
        self.assertEqual(respuesta.data["desviacion_m3"], -40.0)
        self.assertEqual(respuesta.data["desviacion_pct"], -40.0)
        self.assertFalse(respuesta.data["parcial"])

    def test_comparar_periodo_abierto_avisa_parcial(self):
        self.client.force_authenticate(self.admin)
        futuro = date.today() + timedelta(days=15)
        proy = self._crear_proyeccion(date.today() - timedelta(days=5), futuro)
        respuesta = self.client.get(reverse("proyeccion-comparar", args=[proy.pk]))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertTrue(respuesta.data["parcial"])
        # sin datos reales, no calcula desviacion
        self.assertIsNone(respuesta.data["real_m3"])
        self.assertIsNone(respuesta.data["desviacion_m3"])
