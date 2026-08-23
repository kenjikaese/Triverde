"""Tests del modulo de recepcion: derivacion de peso/chip, CRUD del agregado,
permisos del transportista y sincronizacion idempotente (CU-33).

El test de idempotencia (criterio 4 del brief) es el entregable estrella:
envia el mismo lote dos veces y verifica que se crea una sola Recepcion.
"""
import tempfile
import uuid
from decimal import Decimal

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from acceso.models import BitacoraAuditoria, Rol, Usuario
from mantenedores.models import Cliente, Material, Transportista, Vehiculo

from .models import DetalleRecepcion, Recepcion

# PNG de 1x1 (valido para Pillow), para probar la foto base64 del sync.
PNG_1PX_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNg"
    "aGAAAAEEAIFw9selAAAAAElFTkSuQmCC"
)


class RecepcionTestBase(APITestCase):
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

        cls.cliente = Cliente.objects.create(razon_social="Municipalidad de Colina")
        cls.cliente_b = Cliente.objects.create(razon_social="Otra Empresa")

        cls.transportista = Transportista.objects.create(
            nombre="Juan Perez", cliente=cls.cliente, usuario=cls.camionero
        )
        cls.transportista_b = Transportista.objects.create(
            nombre="Pedro Soto", cliente=cls.cliente_b
        )

        cls.vehiculo = Vehiculo.objects.create(
            patente="BBBB10", cliente=cls.cliente,
            capacidad_m3=Decimal("20.00"), tramo="20",
        )

        cls.material = Material.objects.create(
            nombre="Rama seca", categoria=Material.SECA,
            densidad_kg_m3=Decimal("250.00"),
            factor_reduccion_chip=Decimal("5.00"), admite_chip=True,
        )
        cls.material_sin_densidad = Material.objects.create(
            nombre="Pasto", categoria=Material.VERDE
        )

    def autenticar(self, usuario):
        self.client.force_authenticate(user=usuario)

    def _lote_valido(self, id_local=None):
        return {
            "operaciones": [
                {
                    "id_local": str(id_local or uuid.uuid4()),
                    "tipo": "recepcion",
                    "capturado_en": "2026-08-20T14:03:00-04:00",
                    "datos": {
                        "cliente": self.cliente.pk,
                        "transportista": self.transportista.pk,
                        "vehiculo": self.vehiculo.pk,
                        "conductor": "Juan Perez",
                        "fecha": "2026-08-20",
                        "hora": "14:03",
                        "estado": "pendiente de inspeccion",
                        "detalles": [
                            {
                                "id_local": str(uuid.uuid4()),
                                "material": self.material.pk,
                                "volumen_m3": "20.00",
                                "destino_sugerido": "a pila",
                            }
                        ],
                    },
                }
            ]
        }


class DerivacionTests(RecepcionTestBase):
    def test_derivacion_al_crear_recepcion(self):
        self.autenticar(self.operador)
        datos = {
            "cliente": self.cliente.pk,
            "transportista": self.transportista.pk,
            "vehiculo": self.vehiculo.pk,
            "conductor": "Juan Perez",
            "fecha": "2026-08-20",
            "hora": "14:03",
            "estado": "pendiente de inspeccion",
            "detalles": [
                {
                    "material": self.material.pk,
                    "volumen_m3": "20.00",
                    "destino_sugerido": "a pila",
                }
            ],
        }
        respuesta = self.client.post(
            reverse("recepcion-list"), datos, format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(respuesta.data["id_local"])
        detalle = DetalleRecepcion.objects.get(recepcion_id=respuesta.data["id"])
        self.assertEqual(detalle.peso_derivado_kg, Decimal("5000.00"))
        self.assertEqual(detalle.chip_derivado_m3, Decimal("4.00"))

    def test_material_sin_densidad_rechazado(self):
        self.autenticar(self.operador)
        datos = {
            "cliente": self.cliente.pk,
            "fecha": "2026-08-20",
            "hora": "14:03",
            "detalles": [
                {
                    "material": self.material_sin_densidad.pk,
                    "volumen_m3": "10.00",
                }
            ],
        }
        respuesta = self.client.post(
            reverse("recepcion-list"), datos, format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("densidad", str(respuesta.data))
        self.assertEqual(Recepcion.objects.count(), 0)

    def test_delete_recepcion_no_permitido(self):
        recepcion = Recepcion.objects.create(
            cliente=self.cliente, fecha="2026-08-20", hora="10:00"
        )
        self.autenticar(self.operador)
        respuesta = self.client.delete(
            reverse("recepcion-detail", args=[recepcion.pk])
        )
        self.assertEqual(respuesta.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Recepcion.objects.filter(pk=recepcion.pk).exists())


class SincronizacionTests(RecepcionTestBase):
    def test_sincronizacion_idempotente(self):
        """Enviar el mismo lote dos veces crea una sola Recepcion."""
        self.autenticar(self.operador)
        lote = self._lote_valido()

        primera = self.client.post(reverse("sincronizacion"), lote, format="json")
        self.assertEqual(primera.status_code, status.HTTP_200_OK)
        self.assertEqual(Recepcion.objects.count(), 1)
        self.assertEqual(DetalleRecepcion.objects.count(), 1)
        recepcion = Recepcion.objects.get()
        self.assertEqual(recepcion.estado_sincronizacion, Recepcion.SINCRONIZADA)
        self.assertEqual(recepcion.fecha.isoformat(), "2026-08-20")
        self.assertEqual(recepcion.hora.isoformat(), "14:03:00")
        self.assertEqual(
            recepcion.detalles.get().peso_derivado_kg, Decimal("5000.00")
        )
        resultado = primera.data["resultados"][0]
        self.assertEqual(resultado["estado"], "sincronizada")
        self.assertEqual(resultado["id_servidor"], recepcion.pk)

        segunda = self.client.post(reverse("sincronizacion"), lote, format="json")
        self.assertEqual(segunda.status_code, status.HTTP_200_OK)
        self.assertEqual(Recepcion.objects.count(), 1)
        self.assertEqual(DetalleRecepcion.objects.count(), 1)
        resultado = segunda.data["resultados"][0]
        self.assertEqual(resultado["estado"], "sincronizada")
        self.assertEqual(resultado["id_servidor"], recepcion.pk)
        self.assertEqual(resultado["id_local"], str(recepcion.id_local))

    def test_sincronizacion_rechaza_y_continua(self):
        """Una operacion invalida no bloquea a las demas (CU-33 Excepcion 3)."""
        self.autenticar(self.operador)
        lote = self._lote_valido()
        operacion_invalida = {
            "id_local": str(uuid.uuid4()),
            "tipo": "recepcion",
            "capturado_en": "2026-08-20T10:00:00-04:00",
            "datos": {
                "cliente": self.cliente.pk,
                "fecha": "2026-08-20",
                "hora": "10:00",
                "detalles": [
                    {
                        "id_local": str(uuid.uuid4()),
                        "material": self.material_sin_densidad.pk,
                        "volumen_m3": "5.00",
                    }
                ],
            },
        }
        lote["operaciones"] = [operacion_invalida, lote["operaciones"][0]]

        respuesta = self.client.post(reverse("sincronizacion"), lote, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        resultados = respuesta.data["resultados"]
        self.assertEqual(resultados[0]["estado"], "rechazada")
        self.assertIn("densidad", resultados[0]["motivo"])
        self.assertEqual(resultados[1]["estado"], "sincronizada")
        self.assertEqual(Recepcion.objects.count(), 1)

    def test_sincronizacion_conflicto(self):
        """Objeto ya existente en estado incompatible: queda en conflicto."""
        self.autenticar(self.operador)
        id_local = uuid.uuid4()
        recepcion = Recepcion.objects.create(
            cliente=self.cliente, fecha="2026-08-19", hora="10:00", id_local=id_local
        )
        lote = self._lote_valido(id_local=id_local)

        respuesta = self.client.post(reverse("sincronizacion"), lote, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        resultado = respuesta.data["resultados"][0]
        self.assertEqual(resultado["estado"], "en conflicto")
        recepcion.refresh_from_db()
        self.assertEqual(recepcion.estado_sincronizacion, Recepcion.EN_CONFLICTO)
        self.assertEqual(Recepcion.objects.count(), 1)

    def test_sincronizacion_ordena_por_capturado_en(self):
        self.autenticar(self.operador)
        id_temprano = str(uuid.uuid4())
        id_tarde = str(uuid.uuid4())
        operacion_temprana = {
            "id_local": id_temprano,
            "tipo": "recepcion",
            "capturado_en": "2026-08-20T10:00:00-04:00",
            "datos": {
                "cliente": self.cliente.pk,
                "fecha": "2026-08-20",
                "hora": "10:00",
                "detalles": [
                    {
                        "id_local": str(uuid.uuid4()),
                        "material": self.material.pk,
                        "volumen_m3": "5.00",
                    }
                ],
            },
        }
        operacion_tardia = dict(operacion_temprana)
        operacion_tardia["id_local"] = id_tarde
        operacion_tardia["capturado_en"] = "2026-08-20T15:00:00-04:00"
        operacion_tardia["datos"] = dict(operacion_temprana["datos"])
        operacion_tardia["datos"]["detalles"] = [
            {
                "id_local": str(uuid.uuid4()),
                "material": self.material.pk,
                "volumen_m3": "8.00",
            }
        ]

        lote = {"operaciones": [operacion_tardia, operacion_temprana]}
        respuesta = self.client.post(reverse("sincronizacion"), lote, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        resultados = respuesta.data["resultados"]
        self.assertEqual(resultados[0]["id_local"], id_temprano)
        self.assertEqual(resultados[1]["id_local"], id_tarde)

    def test_sincronizacion_sin_autenticacion_da_401(self):
        respuesta = self.client.post(
            reverse("sincronizacion"), self._lote_valido(), format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_sincronizacion_con_foto_base64(self):
        """La foto viaja embebida en base64 y la recepcion sincroniza (CU-33)."""
        self.autenticar(self.operador)
        lote = self._lote_valido()
        lote["operaciones"][0]["datos"]["fotos"] = [
            {
                "id_local": str(uuid.uuid4()),
                "archivo": f"data:image/png;base64,{PNG_1PX_BASE64}",
            }
        ]
        respuesta = self.client.post(reverse("sincronizacion"), lote, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["resultados"][0]["estado"], "sincronizada")
        recepcion = Recepcion.objects.get()
        self.assertEqual(recepcion.fotos.count(), 1)
        foto = recepcion.fotos.get()
        self.assertEqual(foto.estado_sincronizacion, Recepcion.SINCRONIZADA)
        self.assertTrue(foto.archivo.name.endswith(".png"))

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_sincronizacion_foto_base64_invalida_rechaza(self):
        """Una foto base64 corrupta rechaza la operacion completa (Excepcion 3)."""
        self.autenticar(self.operador)
        lote = self._lote_valido()
        lote["operaciones"][0]["datos"]["fotos"] = [
            {"id_local": str(uuid.uuid4()), "archivo": "esto-no-es-base64!!!"}
        ]
        respuesta = self.client.post(reverse("sincronizacion"), lote, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["resultados"][0]["estado"], "rechazada")
        self.assertEqual(Recepcion.objects.count(), 0)


class MultaYRechazoTests(RecepcionTestBase):
    """CU-30 (aplicacion de multa) y CU-31 (rechazo de carga)."""

    def _crear_recepcion(self):
        return Recepcion.objects.create(
            cliente=self.cliente, operador=self.operador,
            fecha="2026-08-20", hora="10:00",
            estado="pendiente de inspeccion",
        )

    def test_aplicar_multa_a_recepcion(self):
        """CU-30: el operador aplica una multa por material contaminado y queda auditada."""
        recepcion = self._crear_recepcion()
        self.autenticar(self.operador)
        respuesta = self.client.patch(
            reverse("recepcion-detail", args=[recepcion.pk]),
            {
                "multas": [
                    {
                        "cliente": self.cliente.pk,
                        "motivo": "Material contaminado con plastico",
                        "monto": "20.00",
                        "fecha": "2026-08-20",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(recepcion.multas.count(), 1)
        self.assertEqual(recepcion.multas.get().monto, Decimal("20.00"))
        self.assertTrue(
            BitacoraAuditoria.objects.filter(
                accion="Aplicacion de multa", entidad_afectada="Recepcion"
            ).exists()
        )

    def test_rechazo_de_recepcion(self):
        """CU-31: el operador rechaza una carga registrando el motivo, y queda auditado."""
        recepcion = self._crear_recepcion()
        self.autenticar(self.operador)
        respuesta = self.client.patch(
            reverse("recepcion-detail", args=[recepcion.pk]),
            {
                "estado": "rechazada",
                "motivo_rechazo": "Carga con residuos no organicos",
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        recepcion.refresh_from_db()
        self.assertEqual(recepcion.estado, Recepcion.RECHAZADA)
        self.assertEqual(
            recepcion.motivo_rechazo, "Carga con residuos no organicos"
        )
        self.assertTrue(
            BitacoraAuditoria.objects.filter(
                accion="Rechazo de recepcion", entidad_afectada="Recepcion"
            ).exists()
        )


class PermisosTransportistaTests(RecepcionTestBase):
    def test_transportista_solo_ve_sus_recepciones(self):
        Recepcion.objects.create(
            cliente=self.cliente, transportista=self.transportista,
            fecha="2026-08-20", hora="10:00",
        )
        Recepcion.objects.create(
            cliente=self.cliente_b, transportista=self.transportista_b,
            fecha="2026-08-20", hora="11:00",
        )
        self.autenticar(self.camionero)
        respuesta = self.client.get(reverse("recepcion-list"))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data), 1)
        self.assertEqual(respuesta.data[0]["transportista"], self.transportista.pk)

    def test_transportista_crea_con_su_propio_transportista(self):
        self.autenticar(self.camionero)
        datos = {
            "cliente": self.cliente.pk,
            "transportista": self.transportista_b.pk,
            "fecha": "2026-08-20",
            "hora": "14:03",
            "detalles": [
                {"material": self.material.pk, "volumen_m3": "10.00"}
            ],
        }
        respuesta = self.client.post(
            reverse("recepcion-list"), datos, format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        recepcion = Recepcion.objects.get(pk=respuesta.data["id"])
        self.assertEqual(recepcion.transportista, self.transportista)

    def test_transportista_no_puede_editar(self):
        recepcion = Recepcion.objects.create(
            cliente=self.cliente, transportista=self.transportista,
            fecha="2026-08-20", hora="10:00",
        )
        self.autenticar(self.camionero)
        respuesta = self.client.patch(
            reverse("recepcion-detail", args=[recepcion.pk]),
            {"observaciones": "edicion prohibida"}, format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_transportista_no_puede_sincronizar(self):
        self.autenticar(self.camionero)
        respuesta = self.client.post(
            reverse("sincronizacion"), self._lote_valido(), format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
