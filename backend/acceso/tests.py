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


class PerfilPropioTests(APITestCase):
    """CU-04: cada usuario edita su nombre, correo y contrasena."""

    @classmethod
    def setUpTestData(cls):
        rol_operador, _ = Rol.objects.get_or_create(
            nombre=Rol.OPERADOR, defaults={"descripcion": "o"}
        )
        rol_admin, _ = Rol.objects.get_or_create(
            nombre=Rol.ADMINISTRADOR, defaults={"descripcion": "a"}
        )
        cls.rol_admin = rol_admin
        cls.usuario = Usuario.objects.create_user(
            username="perfil", password="clave-inicial-2026", email="perfil@triverde.cl",
            nombre_completo="Persona Perfil", rol=rol_operador,
        )
        cls.otro = Usuario.objects.create_user(
            username="otro", password="clave-inicial-2026", email="otro@triverde.cl",
            nombre_completo="Otra Persona", rol=rol_operador,
        )

    def setUp(self):
        self.client.force_authenticate(self.usuario)

    def _editar(self, **datos):
        return self.client.patch(reverse("auth-perfil"), datos, format="json")

    def test_actualiza_nombre_y_correo_y_audita(self):
        respuesta = self._editar(nombre_completo="Nombre Nuevo", email="nuevo@triverde.cl")
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertEqual(respuesta.data["nombre_completo"], "Nombre Nuevo")
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.email, "nuevo@triverde.cl")
        self.assertTrue(BitacoraAuditoria.objects.filter(accion="Edicion de perfil").exists())

    def test_rol_y_estado_no_cambian(self):
        respuesta = self._editar(rol=self.rol_admin.pk, estado="inactivo", username="hackeado")
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.rol.nombre, Rol.OPERADOR)
        self.assertEqual(self.usuario.estado, "activo")
        self.assertEqual(self.usuario.username, "perfil")

    def test_excepcion_1_correo_de_otro_usuario(self):
        respuesta = self._editar(email="OTRO@triverde.cl")
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.email, "perfil@triverde.cl")

    def test_excepcion_2_clave_debil_no_altera_la_vigente(self):
        respuesta = self._editar(password="123")
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("clave-inicial-2026"))

    def test_clave_valida_se_guarda_cifrada(self):
        respuesta = self._editar(password="otra-clave-segura-2026")
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertNotIn("password", respuesta.data)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("otra-clave-segura-2026"))

    def test_excepcion_3_nombre_o_correo_vacios(self):
        for datos in ({"nombre_completo": ""}, {"email": ""}):
            respuesta = self._editar(**datos)
            self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST, datos)
