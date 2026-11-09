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

    def test_login_y_logout_quedan_en_la_bitacora(self):
        respuesta = self.client.post(
            reverse("auth-login"),
            {"username": "operador", "password": "operador12345"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertTrue(
            BitacoraAuditoria.objects.filter(usuario=self.operador, accion="Inicio de sesion", entidad_afectada="Usuario").exists()
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {respuesta.data['token']}")
        self.client.post(reverse("auth-logout"))
        self.assertTrue(
            BitacoraAuditoria.objects.filter(usuario=self.operador, accion="Cierre de sesion", entidad_afectada="Usuario").exists()
        )

    def test_login_fallido_no_queda_en_la_bitacora(self):
        self.client.post(
            reverse("auth-login"),
            {"username": "operador", "password": "clave-equivocada"},
            format="json",
        )
        self.assertFalse(BitacoraAuditoria.objects.filter(accion="Inicio de sesion").exists())

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


class CuentaPropiaTests(AccesoTestBase):
    """CU-05 y CU-06: lo que el administrador no puede hacer sobre si mismo.

    La razon es la misma en los dos casos: el sistema no puede quedar sin
    ningun usuario con rol Administrador activo.
    """

    def setUp(self):
        self.autenticar(self.admin)

    def test_excepcion_el_admin_no_puede_desactivarse(self):
        """CU-05 Excepcion 1, por el boton Desactivar."""
        respuesta = self.client.delete(reverse("usuario-detail", args=[self.admin.pk]))

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.estado, Usuario.ACTIVO)

    def test_excepcion_el_admin_tampoco_se_desactiva_por_patch(self):
        """CU-05 Excepcion 1: la regla no se esquiva editando el estado."""
        respuesta = self.client.patch(
            reverse("usuario-detail", args=[self.admin.pk]),
            {"estado": Usuario.INACTIVO},
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.estado, Usuario.ACTIVO)

    def test_excepcion_el_admin_no_puede_quitarse_su_rol(self):
        """CU-06 Excepcion 2."""
        respuesta = self.client.patch(
            reverse("usuario-detail", args=[self.admin.pk]),
            {"rol": self.rol_operador.pk},
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.rol.nombre, Rol.ADMINISTRADOR)

    def test_el_admin_si_puede_editar_otros_datos_suyos(self):
        """La regla acota lo justo: el resto de su cuenta sigue editable."""
        respuesta = self.client.patch(
            reverse("usuario-detail", args=[self.admin.pk]),
            {"nombre_completo": "Administrador Triverde"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.nombre_completo, "Administrador Triverde")


class DesactivacionYRolTests(AccesoTestBase):
    """CU-05 y CU-06 sobre otras cuentas: el camino normal."""

    def setUp(self):
        self.autenticar(self.admin)

    def test_al_desactivar_se_cierra_la_sesion_abierta(self):
        """CU-05 Excepcion 2: la desactivacion tiene efecto de inmediato."""
        token = Token.objects.create(user=self.operador)

        respuesta = self.client.delete(
            reverse("usuario-detail", args=[self.operador.pk])
        )

        self.assertEqual(respuesta.status_code, status.HTTP_204_NO_CONTENT)
        self.operador.refresh_from_db()
        self.assertEqual(self.operador.estado, Usuario.INACTIVO)
        self.assertFalse(Token.objects.filter(pk=token.pk).exists())

    def test_desactivar_por_patch_tambien_cierra_la_sesion(self):
        token = Token.objects.create(user=self.operador)

        respuesta = self.client.patch(
            reverse("usuario-detail", args=[self.operador.pk]),
            {"estado": Usuario.INACTIVO},
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertFalse(Token.objects.filter(pk=token.pk).exists())

    def test_reactivar_devuelve_el_acceso(self):
        """CU-05: una cuenta desactivada se vuelve a activar y puede entrar."""
        self.operador.estado = Usuario.INACTIVO
        self.operador.save(update_fields=["estado"])

        respuesta = self.client.patch(
            reverse("usuario-detail", args=[self.operador.pk]),
            {"estado": Usuario.ACTIVO},
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.operador.refresh_from_db()
        self.assertEqual(self.operador.estado, Usuario.ACTIVO)

        self.client.force_authenticate(user=None)
        login = self.client.post(
            reverse("auth-login"),
            {"username": "operador", "password": "operador12345"},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)

    def test_cambiar_el_rol_de_otro_usuario_y_auditarlo(self):
        """CU-06 flujo normal."""
        respuesta = self.client.patch(
            reverse("usuario-detail", args=[self.operador.pk]),
            {"rol": self.rol_transportista.pk},
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.operador.refresh_from_db()
        self.assertEqual(self.operador.rol.nombre, Rol.TRANSPORTISTA)
        self.assertTrue(
            BitacoraAuditoria.objects.filter(
                accion="Edicion de usuario", id_objeto=str(self.operador.pk)
            ).exists()
        )

    def test_excepcion_el_mismo_rol_no_deja_registro_en_la_bitacora(self):
        """CU-06 Excepcion 1: sin cambio que aplicar, no se audita."""
        respuesta = self.client.patch(
            reverse("usuario-detail", args=[self.operador.pk]),
            {"rol": self.operador.rol_id},
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertFalse(
            BitacoraAuditoria.objects.filter(accion="Edicion de usuario").exists()
        )
