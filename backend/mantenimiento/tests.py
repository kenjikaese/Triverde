from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from acceso.models import BitacoraAuditoria, Rol, Usuario
from configuracion.models import ParametroConversion
from mantenedores.models import Cliente, Vehiculo
from mezcla.models import Alerta

from .models import Maquinaria, Mantencion, RegistroUso
from .services import revisar_alertas_mantenimiento


class MantenimientoTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rol_admin = Rol.objects.create(nombre=Rol.ADMINISTRADOR)
        cls.rol_operador = Rol.objects.create(nombre=Rol.OPERADOR)
        cls.rol_transportista = Rol.objects.create(nombre=Rol.TRANSPORTISTA)
        cls.admin = Usuario.objects.create_user(
            username="admin-m11", password="clave-segura", nombre_completo="Admin",
            rol=cls.rol_admin,
        )
        cls.operador = Usuario.objects.create_user(
            username="operador-m11", password="clave-segura", nombre_completo="Operador",
            rol=cls.rol_operador,
        )
        cls.transportista = Usuario.objects.create_user(
            username="transportista-m11", password="clave-segura",
            nombre_completo="Transportista", rol=cls.rol_transportista,
        )
        cls.maquina = Maquinaria.objects.create(
            nombre="Chipeadora", tipo="Chipeadora", horometro=Decimal("100.00")
        )
        cls.cliente = Cliente.objects.create(razon_social="Cliente M11")
        cls.vehiculo = Vehiculo.objects.create(
            patente="MANT11", cliente=cls.cliente, es_mantenible=True,
            horometro=Decimal("50.00"),
        )

    def autenticar(self, usuario):
        self.client.force_authenticate(user=usuario)


class MaquinariaTests(MantenimientoTestBase):
    def test_administrador_registra_maquinaria_y_audita(self):
        self.autenticar(self.admin)
        respuesta = self.client.post(
            reverse("maquinaria-list"),
            {"nombre": "Harnero", "tipo": "Cribadora", "horometro": "12.50"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data["estado_operativo"], Maquinaria.OPERATIVA)
        self.assertTrue(BitacoraAuditoria.objects.filter(entidad_afectada="Maquinaria").exists())

    def test_operador_no_puede_crear_maquinaria(self):
        self.autenticar(self.operador)
        respuesta = self.client.post(
            reverse("maquinaria-list"), {"nombre": "Retro", "tipo": "Retro"}, format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_baja_logica_conserva_historial_y_exige_confirmacion(self):
        Mantencion.objects.create(
            maquinaria=self.maquina, tipo=Mantencion.PREVENTIVA,
            criterio=Mantencion.POR_FECHA,
            fecha_programada=timezone.localdate() + timedelta(days=30),
            descripcion="Cambio aceite", estado=Mantencion.PROGRAMADA,
        )
        self.autenticar(self.admin)
        url = reverse("maquinaria-detail", args=[self.maquina.pk])
        respuesta = self.client.delete(url, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        respuesta = self.client.delete(url, {"confirmar_baja": True}, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_204_NO_CONTENT)
        self.maquina.refresh_from_db()
        self.assertEqual(self.maquina.estado, Maquinaria.INACTIVO)
        self.assertEqual(self.maquina.mantencions.count(), 1)


class RegistroUsoTests(MantenimientoTestBase):
    def test_lectura_actualiza_horometro_y_calcula_diferencia(self):
        self.autenticar(self.operador)
        respuesta = self.client.post(
            reverse("registro-uso-list"),
            {"maquinaria": self.maquina.pk, "horas": "125.00", "fecha": timezone.now()},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.maquina.refresh_from_db()
        self.assertEqual(self.maquina.horometro, Decimal("125.00"))
        registro = RegistroUso.objects.get()
        self.assertEqual(registro.operador, self.operador)
        self.assertEqual(registro.horas_transcurridas, Decimal("25.00"))

    def test_horometro_no_retrocede(self):
        self.autenticar(self.operador)
        respuesta = self.client.post(
            reverse("registro-uso-list"),
            {"maquinaria": self.maquina.pk, "horas": "99.00", "fecha": timezone.now()},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("no puede ser menor", str(respuesta.data))

    def test_no_registra_fuera_de_servicio(self):
        self.maquina.estado_operativo = Maquinaria.FUERA_DE_SERVICIO
        self.maquina.save()
        self.autenticar(self.operador)
        respuesta = self.client.post(
            reverse("registro-uso-list"),
            {"maquinaria": self.maquina.pk, "horas": "110", "fecha": timezone.now()},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)


class MantencionTests(MantenimientoTestBase):
    def test_preventiva_por_horas_debe_superar_horometro(self):
        self.autenticar(self.admin)
        respuesta = self.client.post(
            reverse("mantencion-list"),
            {"maquinaria": self.maquina.pk, "tipo": "preventiva", "criterio": "horas",
             "umbral_horas": "100", "descripcion": "Cambio cuchillas"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_operador_no_programa_preventiva(self):
        self.autenticar(self.operador)
        respuesta = self.client.post(
            reverse("mantencion-list"),
            {"maquinaria": self.maquina.pk, "tipo": "preventiva", "criterio": "horas",
             "umbral_horas": "200", "descripcion": "Cambio cuchillas"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_correctiva_registra_costo_y_estado_final(self):
        self.autenticar(self.operador)
        respuesta = self.client.post(
            reverse("mantencion-list"),
            {"vehiculo": self.vehiculo.pk, "tipo": "correctiva",
             "descripcion": "Reparacion hidraulica", "falla": "Fuga",
             "reparacion": "Cambio de sello", "costo": "85000",
             "reparacion_habilita": False},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.vehiculo.estado_operativo, Vehiculo.FUERA_DE_SERVICIO)
        self.assertEqual(Mantencion.objects.get().costo, Decimal("85000.00"))

    def test_alerta_proxima_no_se_duplica_y_flota_la_refleja(self):
        mantencion = Mantencion.objects.create(
            maquinaria=self.maquina, tipo=Mantencion.PREVENTIVA,
            criterio=Mantencion.POR_HORAS, umbral_horas=Decimal("140"),
            descripcion="Cambio cuchillas", estado=Mantencion.PROGRAMADA,
        )
        revisar_alertas_mantenimiento()
        revisar_alertas_mantenimiento()
        self.assertEqual(
            Alerta.objects.filter(mantencion=mantencion, estado=Alerta.ACTIVA).count(), 1
        )
        self.autenticar(self.admin)
        respuesta = self.client.get(reverse("maquinaria-estado-flota"))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        maquina = next(x for x in respuesta.data if x["clase_activo"] == "maquinaria")
        self.assertIsNotNone(maquina["alerta"])

    def test_reprogramar_resuelve_alerta_anterior(self):
        mantencion = Mantencion.objects.create(
            maquinaria=self.maquina, tipo=Mantencion.PREVENTIVA,
            criterio=Mantencion.POR_HORAS, umbral_horas=Decimal("140"),
            descripcion="Cambio cuchillas", estado=Mantencion.PROGRAMADA,
        )
        revisar_alertas_mantenimiento()
        alerta = Alerta.objects.get(mantencion=mantencion)
        self.autenticar(self.admin)
        respuesta = self.client.patch(
            reverse("mantencion-detail", args=[mantencion.pk]),
            {"umbral_horas": "300"}, format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado, Alerta.RESUELTA)

    def test_umbral_de_horas_es_editable(self):
        mantencion = Mantencion.objects.create(
            maquinaria=self.maquina, tipo=Mantencion.PREVENTIVA,
            criterio=Mantencion.POR_HORAS, umbral_horas=Decimal("170"),
            descripcion="Servicio de motor", estado=Mantencion.PROGRAMADA,
        )
        revisar_alertas_mantenimiento()
        self.assertFalse(Alerta.objects.filter(mantencion=mantencion).exists())

        parametro = ParametroConversion.objects.get(
            clave="alerta_mantenimiento_horas"
        )
        parametro.valor = Decimal("80")
        parametro.save(update_fields=["valor"])
        revisar_alertas_mantenimiento()
        self.assertTrue(
            Alerta.objects.filter(mantencion=mantencion, estado=Alerta.ACTIVA).exists()
        )

    def test_umbral_no_acepta_valor_cero(self):
        parametro = ParametroConversion.objects.get(
            clave="alerta_mantenimiento_dias"
        )
        self.autenticar(self.admin)
        respuesta = self.client.patch(
            reverse("parametro-detail", args=[parametro.pk]),
            {"valor": "0"}, format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_historial_filtra_por_activo_y_tipo(self):
        Mantencion.objects.create(
            maquinaria=self.maquina, tipo=Mantencion.CORRECTIVA,
            fecha_realizada=timezone.localdate(), costo=10, descripcion="Reparacion",
            falla="Falla", reparacion="Lista", estado=Mantencion.REALIZADA,
        )
        self.autenticar(self.operador)
        respuesta = self.client.get(
            reverse("mantencion-list"), {"maquinaria": self.maquina.pk, "tipo": "correctiva"}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data), 1)

    def test_transportista_no_tiene_acceso(self):
        self.autenticar(self.transportista)
        respuesta = self.client.get(reverse("mantencion-list"))
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
