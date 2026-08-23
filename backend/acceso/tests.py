"""Tests del modulo de acceso: login/logout/perfil por token, permisos por
rol, auditoria y baja logica de usuarios."""
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import BitacoraAuditoria, Rol, Usuario


class AccesoTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rol_admin = Rol.objects.create(nombre=Rol.ADMINISTRADOR, descripcion="a")
        cls.rol_operador = Rol.objects.create(nombre=Rol.OPERADOR, descripcion="o")
        cls.rol_transportista = Rol.objects.create(
            nombre=Rol.TRANSPORTISTA, descripcion="t"
        )
        cls.admin = Usuario.objects.create_user(
            username="admin", password="admin12345",
            nombre_completo="Admin Triverde", rol=cls.rol_admin,
        )
        cls.operador = Usuario.objects.create_user(
            username="operador", password="operador12345",
            nombre_completo="Operador Triverde", rol=cls.rol_operador,
        )
        cls.camionero = Usuario.objects.create_user(
            username="camionero", password="camionero12345",
            nombre_completo="Camionero", rol=cls.rol_transportista,
        )

    def autenticar(self, usuario):
        self.client.force_authenticate(user=usuario)


class AutenticacionTests(AccesoTestBase):
    def test_login_devuelve_token_y_perfil_responde(self):
        respuesta = self.client.post(
            reverse("auth-login"),
            {"username": "operador", "password": "operador12345"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertIn("token", respuesta.data)
        self.assertEqual(respuesta.data["usuario"]["username"], "operador")
        self.assertEqual(respuesta.data["usuario"]["rol_nombre"], "Operador")

        token = respuesta.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        perfil = self.client.get(reverse("auth-perfil"))
        self.assertEqual(perfil.status_code, status.HTTP_200_OK)
        self.assertEqual(perfil.data["username"], "operador")

    def test_login_rechaza_usuario_inactivo(self):
        self.operador.estado = Usuario.INACTIVO
        self.operador.save(update_fields=["estado"])
        respuesta = self.client.post(
            reverse("auth-login"),
            {"username": "operador", "password": "operador12345"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("token", respuesta.data)

    def test_logout_invalida_token(self):
        token = Token.objects.create(user=self.operador)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        respuesta = self.client.post(reverse("auth-logout"))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertFalse(Token.objects.filter(pk=token.pk).exists())

    def test_sin_token_da_401(self):
        respuesta = self.client.get(reverse("usuario-list"))
        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)


class PermisosTests(AccesoTestBase):
    def test_operador_no_puede_crear_usuario(self):
        self.autenticar(self.operador)
        respuesta = self.client.post(
            reverse("usuario-list"),
            {
                "username": "intruso",
                "password": "clave12345",
                "nombre_completo": "Intruso",
                "rol": self.rol_operador.pk,
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Usuario.objects.filter(username="intruso").exists())

    def test_transportista_sin_acceso_a_usuarios(self):
        self.autenticar(self.camionero)
        respuesta = self.client.get(reverse("usuario-list"))
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_transportista_sin_acceso_a_auditoria(self):
        self.autenticar(self.camionero)
        respuesta = self.client.get(reverse("auditoria-list"))
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_crea_usuario_y_audita(self):
        self.autenticar(self.admin)
        respuesta = self.client.post(
            reverse("usuario-list"),
            {
                "username": "nuevo",
                "password": "clave12345",
                "nombre_completo": "Usuario Nuevo",
                "rol": self.rol_operador.pk,
                "email": "nuevo@triverde.cl",
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", respuesta.data)
        usuario = Usuario.objects.get(username="nuevo")
        self.assertTrue(usuario.check_password("clave12345"))
        self.assertTrue(
            BitacoraAuditoria.objects.filter(
                accion="Creacion de usuario", entidad_afectada="Usuario"
            ).exists()
        )

    def test_baja_logica_de_usuario(self):
        self.autenticar(self.admin)
        respuesta = self.client.delete(
            reverse("usuario-detail", args=[self.operador.pk])
        )
        self.assertEqual(respuesta.status_code, status.HTTP_204_NO_CONTENT)
        self.operador.refresh_from_db()
        self.assertEqual(self.operador.estado, Usuario.INACTIVO)
        self.assertTrue(Usuario.objects.filter(pk=self.operador.pk).exists())
