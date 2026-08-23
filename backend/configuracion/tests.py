"""Tests del modulo de configuracion: historial al cambiar parametro y
permisos de lectura para el operador."""
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from acceso.models import BitacoraAuditoria, Rol, Usuario

from .models import HistorialCambioParametro, ParametroConversion


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
