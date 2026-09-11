from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from acceso.models import BitacoraAuditoria, Rol, Usuario

from .models import Alerta
from .services import activar_alerta


class AlertasCompartidasTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        rol_admin = Rol.objects.create(nombre=Rol.ADMINISTRADOR)
        rol_operador = Rol.objects.create(nombre=Rol.OPERADOR)
        rol_transportista = Rol.objects.create(nombre=Rol.TRANSPORTISTA)
        cls.admin = Usuario.objects.create_user(
            username="admin-alertas", password="clave-segura",
            nombre_completo="Admin Alertas", rol=rol_admin,
        )
        cls.operador = Usuario.objects.create_user(
            username="operador-alertas", password="clave-segura",
            nombre_completo="Operador Alertas", rol=rol_operador,
        )
        cls.transportista = Usuario.objects.create_user(
            username="transportista-alertas", password="clave-segura",
            nombre_completo="Transportista Alertas", rol=rol_transportista,
        )

    def test_activar_misma_clave_actualiza_sin_duplicar(self):
        primera, creada = activar_alerta(
            origen=Alerta.MEZCLA, clave="mezcla:pila:8:seca",
            nivel=Alerta.ADVERTENCIA, mensaje="Faltan 3 m3 de material seco.",
        )
        self.assertTrue(creada)
        segunda, creada = activar_alerta(
            origen=Alerta.MEZCLA, clave="mezcla:pila:8:seca",
            nivel=Alerta.CRITICA, mensaje="Faltan 5 m3 de material seco.",
        )
        self.assertFalse(creada)
        self.assertEqual(primera.pk, segunda.pk)
        self.assertEqual(Alerta.objects.count(), 1)
        segunda.refresh_from_db()
        self.assertEqual(segunda.nivel, Alerta.CRITICA)
        self.assertIn("5 m3", segunda.mensaje)

    def test_operador_lista_y_resuelve_alerta(self):
        alerta, _ = activar_alerta(
            origen=Alerta.MEZCLA, clave="mezcla:pila:3:verde",
            nivel=Alerta.ADVERTENCIA, mensaje="Falta material verde.",
        )
        self.client.force_authenticate(self.operador)
        respuesta = self.client.get(
            reverse("alerta-list"), {"estado": "activa", "origen": "mezcla"}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data), 1)

        respuesta = self.client.post(reverse("alerta-resolver", args=[alerta.pk]))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado, Alerta.RESUELTA)
        self.assertEqual(alerta.resuelta_por, self.operador)
        self.assertTrue(
            BitacoraAuditoria.objects.filter(
                entidad_afectada="Alerta", accion="Resolucion de alerta"
            ).exists()
        )

    def test_transportista_no_accede_a_alertas(self):
        self.client.force_authenticate(self.transportista)
        respuesta = self.client.get(reverse("alerta-list"))
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
