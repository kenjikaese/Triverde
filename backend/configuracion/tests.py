"""Tests del modulo de configuracion: historial al cambiar parametro,
permisos de lectura para el operador, recetas de mezcla y costos (M02
Incremento 2)."""
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from acceso.models import BitacoraAuditoria, Rol, Usuario

from .models import (
    CostoOperativo,
    CostoTransporte,
    HistorialCambioParametro,
    ParametroConversion,
    RecetaMezcla,
)


class ConfiguracionTestBase(APITestCase):
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

    def autenticar(self, usuario):
        self.client.force_authenticate(user=usuario)


class ParametroTests(ConfiguracionTestBase):
    def test_cambio_parametro_genera_historial_y_auditoria(self):
        self.autenticar(self.admin)
        parametro = ParametroConversion.objects.create(
            clave="factor_prueba", nombre="Factor de prueba",
            valor=Decimal("1.0000"), unidad=":1",
        )
        respuesta = self.client.patch(
            reverse("parametro-detail", args=[parametro.pk]),
            {"valor": "2.5000"}, format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        historial = HistorialCambioParametro.objects.filter(parametro=parametro)
        self.assertEqual(historial.count(), 1)
        self.assertEqual(historial.get().valor_anterior, Decimal("1.0000"))
        self.assertEqual(historial.get().valor_nuevo, Decimal("2.5000"))
        self.assertTrue(
            BitacoraAuditoria.objects.filter(
                accion="Cambio de parametro", entidad_afectada="ParametroConversion"
            ).exists()
        )

    def test_operador_lee_pero_no_escribe_parametros(self):
        self.autenticar(self.operador)
        parametro = ParametroConversion.objects.create(
            clave="factor_lectura", nombre="Factor de lectura",
            valor=Decimal("1.0000"),
        )
        respuesta = self.client.get(reverse("parametro-list"))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        respuesta = self.client.patch(
            reverse("parametro-detail", args=[parametro.pk]),
            {"valor": "9.0000"}, format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)


class HistorialFiltroTests(ConfiguracionTestBase):
    def setUp(self):
        self.param = ParametroConversion.objects.create(clave="sacos_m3", nombre="Sacos por m3", valor=10)
        otro = ParametroConversion.objects.create(clave="co2", nombre="Factor CO2", valor=1)
        for i in range(3):
            HistorialCambioParametro.objects.create(
                parametro=self.param, usuario=self.admin, valor_anterior=i, valor_nuevo=i + 1
            )
        HistorialCambioParametro.objects.create(parametro=otro, usuario=self.admin, valor_nuevo=2)

    def test_orden_y_filtro_por_clave(self):
        self.autenticar(self.admin)
        respuesta = self.client.get(reverse("historial-parametro-list"), {"parametro": "sacos_m3"})
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        fechas = [x["fecha_hora"] for x in respuesta.data]
        self.assertEqual(len(fechas), 3)
        self.assertEqual(fechas, sorted(fechas, reverse=True))
        self.assertEqual(respuesta.data[0]["parametro_clave"], "sacos_m3")

    def test_filtro_fechas_sin_resultados(self):
        self.autenticar(self.admin)
        respuesta = self.client.get(
            reverse("historial-parametro-list"), {"desde": "2000-01-01", "hasta": "2000-01-31"}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data, [])


class RecetaMezclaTests(ConfiguracionTestBase):
    def test_crear_receta_3_a_1_queda_vigente(self):
        self.autenticar(self.admin)
        respuesta = self.client.post(reverse("receta-list"), {
            "nombre": "Compost estandar",
            "relacion_seca": "3",
            "relacion_verde": "1",
        })
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        receta = RecetaMezcla.objects.get(pk=respuesta.data["id"])
        self.assertTrue(receta.vigente)
        self.assertEqual(receta.proporcion, "3:1")
        self.assertEqual(receta.fraccion_seca, Decimal("0.75"))
        self.assertTrue(
            BitacoraAuditoria.objects.filter(accion="crear_receta", id_objeto=str(receta.pk)).exists()
        )

    def test_proporcion_cero_rechazada(self):
        self.autenticar(self.admin)
        respuesta = self.client.post(
            reverse("receta-list"), {"nombre": "Mala", "relacion_seca": "0", "relacion_verde": "1"}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("relacion_seca", respuesta.data)

    def test_delete_es_baja_logica(self):
        self.autenticar(self.admin)
        receta = RecetaMezcla.objects.create(nombre="X", relacion_seca=2, relacion_verde=1)
        respuesta = self.client.delete(reverse("receta-detail", args=[receta.pk]))
        self.assertEqual(respuesta.status_code, status.HTTP_204_NO_CONTENT)
        receta.refresh_from_db()
        self.assertFalse(receta.vigente)
        self.assertEqual(self.client.get(reverse("receta-list"), {"vigente": "true"}).data, [])


class CostoTransporteTests(ConfiguracionTestBase):
    def test_cambio_deja_anterior_no_vigente(self):
        self.autenticar(self.admin)
        self.client.post(reverse("costo-transporte-list"), {"costo_por_km": "850"})
        respuesta = self.client.post(reverse("costo-transporte-list"), {"costo_por_km": "920"})
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CostoTransporte.objects.filter(vigente=True).count(), 1)
        self.assertEqual(CostoTransporte.objects.vigente().costo_por_km, Decimal("920"))
        self.assertEqual(CostoTransporte.objects.filter(vigente=False).count(), 1)
        self.assertEqual(BitacoraAuditoria.objects.filter(accion="cambiar_costo_km").count(), 2)

    def test_mismo_valor_no_crea_registro(self):
        self.autenticar(self.admin)
        self.client.post(reverse("costo-transporte-list"), {"costo_por_km": "850"})
        respuesta = self.client.post(reverse("costo-transporte-list"), {"costo_por_km": "850.00"})
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(CostoTransporte.objects.count(), 1)
        self.assertEqual(BitacoraAuditoria.objects.filter(accion="cambiar_costo_km").count(), 1)


class CostoOperativoTests(ConfiguracionTestBase):
    def test_concepto_vigente_no_se_duplica(self):
        self.autenticar(self.admin)
        self.client.post(
            reverse("costo-operativo-list"), {"concepto": "Combustible", "monto": "1200", "unidad": "litro"}
        )
        respuesta = self.client.post(
            reverse("costo-operativo-list"), {"concepto": "combustible", "monto": "1300", "unidad": "litro"}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("concepto", respuesta.data)

    def test_concepto_dado_de_baja_se_puede_recrear(self):
        self.autenticar(self.admin)
        viejo = CostoOperativo.objects.create(concepto="Ayudante", monto=25000, unidad="dia", vigente=False)
        respuesta = self.client.post(
            reverse("costo-operativo-list"), {"concepto": "Ayudante", "monto": "28000", "unidad": "dia"}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(respuesta.data["id"], viejo.pk)


class PermisosM2Tests(ConfiguracionTestBase):
    def test_operador_no_escribe_recetas_ni_costos(self):
        self.autenticar(self.operador)
        casos = [
            (reverse("receta-list"), {"nombre": "R", "relacion_seca": "3", "relacion_verde": "1"}),
            (reverse("costo-transporte-list"), {"costo_por_km": "900"}),
            (reverse("costo-operativo-list"), {"concepto": "Retro", "monto": "45000", "unidad": "hora"}),
        ]
        for url, data in casos:
            respuesta = self.client.post(url, data)
            self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN, url)

    def test_operador_lee_recetas_e_historial_pero_no_costos(self):
        self.autenticar(self.operador)
        self.assertEqual(self.client.get(reverse("receta-list")).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(reverse("historial-parametro-list")).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(reverse("costo-operativo-list")).status_code, status.HTTP_403_FORBIDDEN)

    def test_sin_token_es_401(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse("receta-list")).status_code, status.HTTP_401_UNAUTHORIZED)
