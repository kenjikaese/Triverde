from decimal import Decimal

from django.db import migrations


def crear_parametros_alerta(apps, schema_editor):
    ParametroConversion = apps.get_model("configuracion", "ParametroConversion")
    parametros = [
        (
            "alerta_mantenimiento_dias",
            "Anticipacion de mantenimiento por fecha",
            Decimal("7"),
            "dias",
            "Dias de anticipacion para generar una alerta de mantenimiento proxima.",
        ),
        (
            "alerta_mantenimiento_horas",
            "Anticipacion de mantenimiento por horometro",
            Decimal("50"),
            "horas",
            "Horas de anticipacion para generar una alerta de mantenimiento proxima.",
        ),
    ]
    for clave, nombre, valor, unidad, descripcion in parametros:
        ParametroConversion.objects.get_or_create(
            clave=clave,
            defaults={
                "nombre": nombre,
                "valor": valor,
                "unidad": unidad,
                "descripcion": descripcion,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("configuracion", "0001_initial")]

    operations = [
        migrations.RunPython(crear_parametros_alerta, migrations.RunPython.noop),
    ]
