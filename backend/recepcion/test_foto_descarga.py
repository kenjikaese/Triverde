"""Foto del material (CU-27) y descarga desde la cuenta del transportista (CU-28)."""
import shutil
import tempfile
import uuid
from decimal import Decimal

from django.test import override_settings

from acceso.models import BitacoraAuditoria
from inventario.models import Inventario
from mantenedores.models import Transportista, Vehiculo

from .models import FotoRecepcion, Recepcion
from .tests import PNG_1PX_BASE64, RecepcionTestBase

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="triverde-test-media-")
FOTO = f"data:image/png;base64,{PNG_1PX_BASE64}"


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class BaseFotos(RecepcionTestBase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def _descarga(self, **cambios):
        datos = {"fecha": "2026-11-04", "hora": "09:30", "volumen_aproximado_m3": "12.50"}
        datos.update(cambios)
        return self.client.post("/api/v1/recepciones/mi-descarga/", datos, format="json")


class FotoRecepcionTests(BaseFotos):
    def _recepcion(self, **cambios):
        datos = {
            "cliente": self.cliente,
            "transportista": self.transportista,
            "fecha": "2026-11-04",
            "hora": "10:00",
            "estado": Recepcion.PENDIENTE_INSPECCION,
        }
        datos.update(cambios)
        return Recepcion.objects.create(**datos)

    def test_guardar_foto_registra_autor_y_auditoria(self):
        recepcion = self._recepcion()
        self.autenticar(self.operador)
        respuesta = self.client.post(
            f"/api/v1/recepciones/{recepcion.pk}/foto/", {"archivo": FOTO}, format="json"
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        foto = recepcion.fotos.get()
        self.assertEqual(foto.autor, self.operador)
        self.assertTrue(
            BitacoraAuditoria.objects.filter(accion="Adjuntar foto").exists()
        )

    def test_se_pueden_adjuntar_varias_fotos(self):
        recepcion = self._recepcion()
        self.autenticar(self.operador)
        for _ in range(2):
            self.client.post(
                f"/api/v1/recepciones/{recepcion.pk}/foto/", {"archivo": FOTO}, format="json"
            )
        self.assertEqual(recepcion.fotos.count(), 2)

    def test_imagen_invalida_no_crea_la_foto(self):
        recepcion = self._recepcion()
        self.autenticar(self.operador)
        respuesta = self.client.post(
            f"/api/v1/recepciones/{recepcion.pk}/foto/", {"archivo": "no-es-imagen"}, format="json"
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(recepcion.fotos.count(), 0)

    def test_no_se_adjunta_a_una_recepcion_cerrada(self):
        recepcion = self._recepcion(estado=Recepcion.RECIBIDA)
        self.autenticar(self.operador)
        respuesta = self.client.post(
            f"/api/v1/recepciones/{recepcion.pk}/foto/", {"archivo": FOTO}, format="json"
        )
        self.assertEqual(respuesta.status_code, 400)

    def test_transportista_adjunta_solo_a_las_suyas(self):
        propia = self._recepcion()
        ajena = self._recepcion(cliente=self.cliente_b, transportista=self.transportista_b)
        self.autenticar(self.camionero)
        respuesta = self.client.post(
            f"/api/v1/recepciones/{propia.pk}/foto/", {"archivo": FOTO}, format="json"
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        respuesta = self.client.post(
            f"/api/v1/recepciones/{ajena.pk}/foto/", {"archivo": FOTO}, format="json"
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_foto_dentro_del_registro_guarda_autor(self):
        self.autenticar(self.operador)
        respuesta = self.client.post(
            "/api/v1/recepciones/",
            {
                "cliente": self.cliente.pk,
                "fecha": "2026-11-04",
                "hora": "10:00",
                "fotos": [{"archivo": FOTO}],
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertEqual(FotoRecepcion.objects.get().autor, self.operador)


class DescargaTransportistaTests(BaseFotos):
    def test_crea_la_recepcion_a_nombre_de_su_empresa(self):
        self.autenticar(self.camionero)
        respuesta = self._descarga(fotos=[{"archivo": FOTO}])
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        recepcion = Recepcion.objects.get(pk=respuesta.data["id"])
        self.assertEqual(recepcion.estado, Recepcion.PENDIENTE_INSPECCION)
        self.assertEqual(recepcion.transportista, self.transportista)
        self.assertEqual(recepcion.cliente, self.cliente)
        self.assertEqual(recepcion.vehiculo, self.vehiculo)
        self.assertEqual(recepcion.volumen_aproximado_m3, Decimal("12.50"))
        self.assertEqual(recepcion.detalles.count(), 0)
        self.assertEqual(recepcion.fotos.get().autor, self.camionero)

    def test_no_acepta_otra_empresa_en_los_datos(self):
        self.autenticar(self.camionero)
        respuesta = self._descarga(
            cliente=self.cliente_b.pk, transportista=self.transportista_b.pk
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        recepcion = Recepcion.objects.get(pk=respuesta.data["id"])
        self.assertEqual(recepcion.cliente, self.cliente)
        self.assertEqual(recepcion.transportista, self.transportista)

    def test_excepcion_1_varios_vehiculos_queda_sin_asignar(self):
        Vehiculo.objects.create(
            patente="CCCC20", cliente=self.cliente,
            capacidad_m3=Decimal("10.00"), tramo="10",
        )
        self.autenticar(self.camionero)
        respuesta = self._descarga()
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertIsNone(Recepcion.objects.get(pk=respuesta.data["id"]).vehiculo)

    def test_excepcion_2_sin_volumen_no_crea_la_recepcion(self):
        self.autenticar(self.camionero)
        respuesta = self.client.post(
            "/api/v1/recepciones/mi-descarga/",
            {"fecha": "2026-11-04", "hora": "09:30"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Ingresa el volumen aproximado.", str(respuesta.data))
        self.assertEqual(Recepcion.objects.count(), 0)

    def test_volumen_cero_no_crea_la_recepcion(self):
        self.autenticar(self.camionero)
        respuesta = self._descarga(volumen_aproximado_m3="0")
        self.assertEqual(respuesta.status_code, 400)

    def test_cuenta_sin_transportista_recibe_un_mensaje(self):
        Transportista.objects.filter(usuario=self.camionero).update(usuario=None)
        self.camionero.refresh_from_db()
        self.autenticar(self.camionero)
        respuesta = self._descarga()
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("no tiene un transportista asociado", str(respuesta.data))

    def test_operador_no_usa_esta_accion(self):
        self.autenticar(self.operador)
        self.assertEqual(self._descarga().status_code, 403)

    def test_operador_completa_el_material_y_entra_al_inventario(self):
        self.autenticar(self.camionero)
        pk = self._descarga().data["id"]

        self.autenticar(self.operador)
        respuesta = self.client.post(f"/api/v1/recepciones/{pk}/aceptar/")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Completa el material", str(respuesta.data))

        respuesta = self.client.patch(
            f"/api/v1/recepciones/{pk}/",
            {"detalles": [{"material": self.material.pk, "volumen_m3": "12.50"}]},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        fila = Inventario.objects.get(material=self.material, etapa=Inventario.POR_TRITURAR)
        self.assertEqual(fila.volumen_m3, Decimal("12.50"))

        respuesta = self.client.post(f"/api/v1/recepciones/{pk}/aceptar/")
        self.assertEqual(respuesta.status_code, 200, respuesta.data)


class SincronizacionTransportistaTests(BaseFotos):
    def _lote(self, tipo="recepcion", **datos):
        id_local = str(uuid.uuid4())
        base = {"fecha": "2026-11-04", "hora": "09:30", "volumen_aproximado_m3": "8.00"}
        base.update(datos)
        return id_local, {
            "operaciones": [
                {
                    "id_local": id_local,
                    "tipo": tipo,
                    "capturado_en": "2026-11-04T12:30:00Z",
                    "datos": base,
                }
            ]
        }

    def test_descarga_sin_senal_sincroniza_una_sola_vez(self):
        self.autenticar(self.camionero)
        id_local, lote = self._lote(cliente=self.cliente_b.pk, fotos=[{"archivo": FOTO}])
        for _ in range(2):
            respuesta = self.client.post("/api/v1/sincronizacion/", lote, format="json")
            self.assertEqual(respuesta.status_code, 200, respuesta.data)
            self.assertEqual(respuesta.data["resultados"][0]["estado"], "sincronizada")
        recepcion = Recepcion.objects.get(id_local=id_local)
        self.assertEqual(Recepcion.objects.count(), 1)
        self.assertEqual(recepcion.cliente, self.cliente)
        self.assertEqual(recepcion.transportista, self.transportista)
        self.assertEqual(recepcion.fotos.get().autor, self.camionero)

    def test_transportista_no_sincroniza_procesos_de_pila(self):
        self.autenticar(self.camionero)
        _, lote = self._lote(tipo="proceso_pila")
        respuesta = self.client.post("/api/v1/sincronizacion/", lote, format="json")
        self.assertEqual(respuesta.data["resultados"][0]["estado"], "rechazada")
