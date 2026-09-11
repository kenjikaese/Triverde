"""Pruebas del modulo 6: mezcla objetivo (CU-45 a CU-49) y alertas compartidas."""
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from acceso.models import BitacoraAuditoria, Rol, Usuario
from configuracion.models import RecetaMezcla
from inventario import services as inventario_services
from inventario.models import ComposicionPila, Inventario, Pila
from mantenedores.models import Cliente, Material
from recepcion.models import Recepcion

from .models import Alerta
from .services import activar_alerta, calcular_mezcla


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


class MezclaYAlertasTests(APITestCase):
    """Valida calculo, alertas, sugerencia de destino y resolucion."""

    @classmethod
    def setUpTestData(cls):
        rol = Rol.objects.create(nombre=Rol.OPERADOR, descripcion="o")
        cls.operador = Usuario.objects.create_user(
            username="operador-m6", password="operador12345", rol=rol,
            nombre_completo="Operador M6",
        )
        cls.seca = Material.objects.create(
            nombre="Ramas M6", categoria=Material.SECA,
            densidad_kg_m3=Decimal("200.00"), admite_chip=True,
            factor_reduccion_chip=Decimal("3.00"),
        )
        cls.verde = Material.objects.create(
            nombre="Verde M6", categoria=Material.VERDE,
            densidad_kg_m3=Decimal("300.00"), admite_chip=False,
        )
        cls.cliente = Cliente.objects.create(razon_social="Cliente M6")

    def setUp(self):
        self.client.force_authenticate(self.operador)

    def crear_pila(self, estado=Pila.EN_FORMACION):
        return Pila.objects.create(
            codigo=Pila.generar_codigo(), fecha_inicio=timezone.localdate(), estado=estado
        )

    def test_calcula_faltante_y_deduplica_alerta(self):
        """Una receta 3:1 calcula el faltante y no duplica la alerta."""
        RecetaMezcla.objects.create(
            nombre="Receta 3 a 1", relacion_seca=3, relacion_verde=1
        )
        pila = self.crear_pila()
        ComposicionPila.objects.create(pila=pila, material=self.seca, volumen_m3=9)
        ComposicionPila.objects.create(pila=pila, material=self.verde, volumen_m3=1)
        inventario_services.ingresar(self.verde, Inventario.POR_TRITURAR, 1)

        calculo = calcular_mezcla(pila)
        self.assertEqual(calculo["faltantes"][Material.VERDE], Decimal("2.00"))
        alerta = Alerta.objects.get(pila=pila, categoria=Material.VERDE)
        self.assertEqual(alerta.estado, Alerta.ACTIVA)
        self.assertEqual(Alerta.objects.filter(pila=pila, categoria=Material.VERDE).count(), 1)
        calcular_mezcla(pila)
        self.assertEqual(Alerta.objects.filter(pila=pila, categoria=Material.VERDE).count(), 1)

    def test_endpoint_mezcla_sin_receta_no_bloquea(self):
        """Sin receta vigente, consultar la mezcla sigue siendo valido."""
        pila = self.crear_pila()
        respuesta = self.client.get(reverse("mezcla-objetivo-detail", args=[pila.pk]))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertIsNone(respuesta.data["receta"])
        self.assertIn("no queda bloqueada", respuesta.data["mensaje"])

    def test_pila_fuera_de_formacion_no_genera_alerta_de_mezcla(self):
        """CU-45: la mezcla objetivo solo aplica mientras se arma la pila."""
        RecetaMezcla.objects.create(
            nombre="Receta fuera de formacion", relacion_seca=3, relacion_verde=1
        )
        pila = self.crear_pila(estado=Pila.CERRADA)
        Alerta.objects.create(
            origen=Alerta.MEZCLA, nivel="faltante", estado=Alerta.ACTIVA,
            mensaje="Alerta antigua", categoria=Material.VERDE,
            faltante_m3=2, disponible_m3=0, pila=pila,
        )
        respuesta = self.client.get(reverse("mezcla-objetivo-detail", args=[pila.pk]))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertIn("solo aplica", respuesta.data["mensaje"])
        self.assertFalse(Alerta.objects.filter(pila=pila, estado=Alerta.ACTIVA).exists())

    def test_recepcion_sugiere_pila_si_hay_alerta_activa(self):
        """Una alerta activa hace que una recepcion sugiera destino a pila."""
        pila = self.crear_pila()
        Alerta.objects.create(
            origen=Alerta.MEZCLA, nivel="faltante", estado=Alerta.ACTIVA,
            mensaje="Falta seca", categoria=Material.SECA, faltante_m3=4,
            disponible_m3=0, pila=pila,
        )
        recepcion = Recepcion.objects.create(
            cliente=self.cliente, fecha=timezone.localdate(),
            hora=timezone.now().time(), estado=Recepcion.RECIBIDA,
        )
        respuesta = self.client.post(
            reverse("recepcion-list"),
            {
                "cliente": self.cliente.pk,
                "fecha": timezone.localdate().isoformat(),
                "hora": "10:00:00",
                "estado": Recepcion.RECIBIDA,
                "detalles": [{"material": self.seca.pk, "volumen_m3": "2.00"}],
            }, format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data["detalles"][0]["destino_sugerido"], "a pila")
        recepcion.delete()

    def test_resolver_alerta_la_saca_de_activas_y_audita(self):
        """Resolver quita la alerta de activas y registra al operador."""
        alerta = Alerta.objects.create(
            origen=Alerta.MEZCLA, nivel="faltante", estado=Alerta.ACTIVA,
            mensaje="Falta verde", categoria=Material.VERDE, faltante_m3=2,
            disponible_m3=0, pila=self.crear_pila(),
        )
        respuesta = self.client.post(reverse("alerta-resolver", args=[alerta.pk]))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado, Alerta.RESUELTA)
        self.assertEqual(self.client.get(reverse("alerta-list")).data, [])
        self.assertIsNotNone(alerta.fecha_resuelta)
        self.assertEqual(alerta.resuelta_por, self.operador)
