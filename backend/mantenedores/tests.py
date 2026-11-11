"""Tests del modulo de mantenedores: CRUD, baja logica y permisos por rol."""
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from acceso.models import Rol, Usuario

from .models import Cliente, Material, Producto, Transportista


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

        # CU-16: el cliente inactivo se reactiva desde la misma ficha.
        respuesta = self.client.patch(
            reverse("cliente-detail", args=[pk]), {"estado": "activo"}, format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        cliente.refresh_from_db()
        self.assertEqual(cliente.estado, Cliente.ACTIVO)

    def test_varios_clientes_sin_rut(self):
        """El RUT es unico, pero un RUT vacio se guarda como nulo y no choca con otro vacio."""
        self.autenticar(self.admin)
        for nombre in ("Sin RUT uno", "Sin RUT dos"):
            respuesta = self.client.post(
                reverse("cliente-list"),
                {"razon_social": nombre, "rut": "", "direccion": "Colina"},
                format="json",
            )
            self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Cliente.objects.filter(rut__isnull=True, razon_social__startswith="Sin RUT").count(), 2)

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


class ValidacionesEdicionTests(APITestCase):
    """Excepciones de CU-18 y CU-20 que revisa el servidor."""

    @classmethod
    def setUpTestData(cls):
        rol, _ = Rol.objects.get_or_create(nombre=Rol.ADMINISTRADOR, defaults={"descripcion": "a"})
        cls.admin = Usuario.objects.create_user(
            username="admin-edicion", password="clave-12345", nombre_completo="Admin", rol=rol
        )
        cls.activo = Cliente.objects.create(razon_social="Cliente activo")
        cls.inactivo = Cliente.objects.create(razon_social="Cliente inactivo", estado=Cliente.INACTIVO)
        cls.transportista = Transportista.objects.create(nombre="Transportista", cliente=cls.activo)
        cls.material = Material.objects.create(
            nombre="Material", categoria=Material.SECA, densidad_kg_m3=Decimal("200.00")
        )

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_no_asocia_transportista_a_cliente_inactivo(self):
        respuesta = self.client.patch(
            f"/api/v1/transportistas/{self.transportista.pk}/", {"cliente": self.inactivo.pk}, format="json"
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("no está activo", str(respuesta.data))

    def test_conserva_cliente_ya_inactivo_si_no_cambia(self):
        Cliente.objects.filter(pk=self.activo.pk).update(estado=Cliente.INACTIVO)
        respuesta = self.client.patch(
            f"/api/v1/transportistas/{self.transportista.pk}/",
            {"cliente": self.activo.pk, "telefono": "123"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.data)

    def test_densidad_vacia_o_cero_se_rechaza_al_editar(self):
        for valor in (None, "0"):
            respuesta = self.client.patch(
                f"/api/v1/materiales/{self.material.pk}/", {"densidad_kg_m3": valor}, format="json"
            )
            self.assertEqual(respuesta.status_code, 400, valor)

    def test_nombre_de_producto_repetido_se_rechaza(self):
        Producto.objects.create(nombre="Compost", tipo=Producto.COMPOST, precio=Decimal("100"))
        otro = Producto.objects.create(nombre="Mulch", tipo=Producto.COMPOST, precio=Decimal("100"))
        respuesta = self.client.patch(f"/api/v1/productos/{otro.pk}/", {"nombre": "compost"}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Ya existe", str(respuesta.data))
        otro.refresh_from_db()
        self.assertEqual(otro.nombre, "Mulch")

    def test_editar_producto_sin_cambiar_el_nombre_es_valido(self):
        producto = Producto.objects.create(nombre="Sacos", tipo=Producto.COMPOST, precio=Decimal("100"))
        respuesta = self.client.patch(
            f"/api/v1/productos/{producto.pk}/", {"nombre": "Sacos", "precio": "150"}, format="json"
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.data)

