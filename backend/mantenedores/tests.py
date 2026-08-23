"""Tests del modulo de mantenedores: CRUD, baja logica y permisos por rol."""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from acceso.models import Rol, Usuario

from .models import Cliente


class MantenedoresTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rol_admin = Rol.objects.create(nombre=Rol.ADMINISTRADOR, descripcion="a")
        cls.rol_operador = Rol.objects.create(nombre=Rol.OPERADOR, descripcion="o")
        cls.rol_transportista = Rol.objects.create(
            nombre=Rol.TRANSPORTISTA, descripcion="t"
        )
        cls.admin = Usuario.objects.create_user(
            username="admin", password="admin12345",
            nombre_completo="Admin", rol=cls.rol_admin,
        )
        cls.operador = Usuario.objects.create_user(
            username="operador", password="operador12345",
            nombre_completo="Operador", rol=cls.rol_operador,
        )
        cls.camionero = Usuario.objects.create_user(
            username="camionero", password="camionero12345",
            nombre_completo="Camionero", rol=cls.rol_transportista,
        )

    def autenticar(self, usuario):
        self.client.force_authenticate(user=usuario)


class ClienteTests(MantenedoresTestBase):
    def test_crud_y_baja_logica_cliente(self):
        self.autenticar(self.admin)
        respuesta = self.client.post(
            reverse("cliente-list"),
            {"razon_social": "Empresa de Prueba", "rut": "77.123.456-7"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        pk = respuesta.data["id"]

        respuesta = self.client.delete(reverse("cliente-detail", args=[pk]))
        self.assertEqual(respuesta.status_code, status.HTTP_204_NO_CONTENT)
        cliente = Cliente.objects.get(pk=pk)
        self.assertEqual(cliente.estado, Cliente.INACTIVO)
        self.assertTrue(Cliente.objects.filter(pk=pk).exists())

        respuesta = self.client.get(reverse("cliente-list"), {"estado": "activo"})
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertNotIn(pk, [item["id"] for item in respuesta.data])

    def test_operador_lee_pero_no_escribe(self):
        self.autenticar(self.operador)
        respuesta = self.client.get(reverse("cliente-list"))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        respuesta = self.client.post(
            reverse("cliente-list"), {"razon_social": "No debe crear"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_transportista_sin_acceso_a_mantenedores(self):
        self.autenticar(self.camionero)
        respuesta = self.client.get(reverse("cliente-list"))
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
