"""Siembra los datos minimos para operar el Incremento 1 y el arranque del
Incremento 2 (M02: costo de transporte y costos operativos).

Idempotente: se puede correr varias veces sin duplicar. Crea los roles, un
usuario administrador inicial y algunos parametros/tarifas/costos de
referencia tomados de docs/02 (los valores pendientes de confirmar con
Javier quedan marcados en la descripcion).

Uso:  python manage.py seed_inicial
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from acceso.models import Rol
from configuracion.models import CostoOperativo, CostoTransporte, ParametroConversion, TarifaRecepcion

Usuario = get_user_model()


class Command(BaseCommand):
    help = "Crea roles, administrador inicial y parametros/tarifas/costos de referencia."

    @transaction.atomic
    def handle(self, *args, **options):
        # --- Roles (docs/11: Administrador / Operador / Transportista) ------
        roles = {}
        for nombre, desc in [
            (Rol.ADMINISTRADOR, "Acceso total: configuracion, mantenedores y reportes."),
            (Rol.OPERADOR, "Registra recepciones y opera en terreno."),
            (Rol.TRANSPORTISTA, "Cuenta propia del camionero/arborista (CU-28)."),
        ]:
            rol, _ = Rol.objects.get_or_create(nombre=nombre, defaults={"descripcion": desc})
            roles[nombre] = rol
        self.stdout.write(self.style.SUCCESS("Roles listos."))

        # --- Administrador inicial -----------------------------------------
        if not Usuario.objects.filter(username="admin").exists():
            Usuario.objects.create_superuser(
                username="admin",
                email="triverdechile@gmail.com",
                password="admin",
                nombre_completo="Administrador Triverde",
                rol=roles[Rol.ADMINISTRADOR],
            )
            self.stdout.write(self.style.SUCCESS("Usuario admin creado (admin / admin) - CAMBIAR."))
        else:
            self.stdout.write("Usuario admin ya existe.")

        # --- Parametros de conversion (docs/02; provisorios) ----------------
        # `costo_por_km` se retiro de aqui: ahora vive en CostoTransporte,
        # que mantiene el vigente + el historico versionado (M02 Incremento 2).
        parametros = [
            ("factor_reduccion_rama", "Factor de reduccion al triturar rama", Decimal("5.00"), ":1",
             "Volumen de rama que se reduce a 1 volumen de chip al triturar."),
            ("factor_reduccion_tronco", "Factor de reduccion al triturar tronco", Decimal("2.00"), ":1",
             "Volumen de tronco que se reduce a 1 volumen de chip al triturar."),
            ("factor_multa", "Factor de multa por material contaminado", Decimal("1.00"), ":1",
             "Multa proporcional al volumen de material contaminado."),
            ("alerta_mantenimiento_dias", "Anticipacion de mantenimiento por fecha", Decimal("7"), "dias",
             "Valor predeterminado acordado para M11; editable por el administrador."),
            ("alerta_mantenimiento_horas", "Anticipacion de mantenimiento por horometro", Decimal("50"), "horas",
             "Valor predeterminado acordado para M11; editable por el administrador."),
        ]
        for clave, nombre, valor, unidad, desc in parametros:
            ParametroConversion.objects.get_or_create(
                clave=clave,
                defaults={"nombre": nombre, "valor": valor, "unidad": unidad, "descripcion": desc},
            )
        self.stdout.write(self.style.SUCCESS("Parametros de conversion listos."))

        # --- Tarifas de recepcion por tramo (docs/02) ----------------------
        # 20 m3 -> $30.000 y 30 m3 -> $40.000 estan confirmados; 10 y 40 pendientes.
        tarifas = [
            (Decimal("0"), Decimal("10"), Decimal("20000")),   # provisorio
            (Decimal("10"), Decimal("20"), Decimal("30000")),  # confirmado (tramo 20)
            (Decimal("20"), Decimal("30"), Decimal("40000")),  # confirmado (tramo 30)
            (Decimal("30"), Decimal("40"), Decimal("50000")),  # provisorio
        ]
        for tmin, tmax, monto in tarifas:
            TarifaRecepcion.objects.get_or_create(
                tramo_min_m3=tmin, tramo_max_m3=tmax,
                defaults={"monto": monto, "vigente": True},
            )
        self.stdout.write(self.style.SUCCESS("Tarifas de recepcion listas."))

        # --- Costo de transporte por km (docs/02: $2.000/km ida-vuelta) -----
        if CostoTransporte.objects.vigente() is None:
            CostoTransporte.objects.create(costo_por_km=Decimal("2000.00"))
        self.stdout.write(self.style.SUCCESS("Costo de transporte listo."))

        # --- Costos operativos de referencia (M02 Incremento 2; provisorios) -
        costos_operativos = [
            ("Combustible", Decimal("1200"), CostoOperativo.LITRO),
            ("Ayudante", Decimal("45000"), CostoOperativo.HORA),
        ]
        for concepto, monto, unidad in costos_operativos:
            CostoOperativo.objects.get_or_create(
                concepto=concepto, vigente=True, defaults={"monto": monto, "unidad": unidad},
            )
        self.stdout.write(self.style.SUCCESS("Costos operativos listos."))

        self.stdout.write(self.style.SUCCESS("Seed inicial completado."))
