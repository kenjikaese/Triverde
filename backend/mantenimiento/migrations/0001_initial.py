import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("mantenedores", "0002_vehiculo_mantenimiento"),
    ]

    operations = [
        migrations.CreateModel(
            name="Maquinaria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=120)),
                ("tipo", models.CharField(max_length=80)),
                ("datos_tecnicos", models.JSONField(blank=True, default=dict)),
                ("horometro", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("estado_operativo", models.CharField(choices=[("operativa", "Operativa"), ("en mantencion", "En mantencion"), ("fuera de servicio", "Fuera de servicio")], default="operativa", max_length=17)),
                ("estado", models.CharField(choices=[("activo", "Activo"), ("inactivo", "Inactivo")], default="activo", max_length=8)),
            ],
            options={"verbose_name": "Maquinaria", "verbose_name_plural": "Maquinarias", "ordering": ["nombre"]},
        ),
        migrations.CreateModel(
            name="RegistroUso",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("horas", models.DecimalField(decimal_places=2, max_digits=10)),
                ("horas_transcurridas", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("fecha", models.DateTimeField()),
                ("maquinaria", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="%(class)ss", to="mantenimiento.maquinaria")),
                ("operador", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="registros_uso", to=settings.AUTH_USER_MODEL)),
                ("vehiculo", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="%(class)ss", to="mantenedores.vehiculo")),
            ],
            options={"ordering": ["-fecha", "-id"]},
        ),
        migrations.CreateModel(
            name="Mantencion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("preventiva", "Preventiva"), ("correctiva", "Correctiva")], max_length=10)),
                ("criterio", models.CharField(blank=True, choices=[("fecha", "Por fecha"), ("horas", "Por horas")], max_length=6, null=True)),
                ("umbral_horas", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("fecha_programada", models.DateField(blank=True, null=True)),
                ("fecha_realizada", models.DateField(blank=True, null=True)),
                ("costo", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("descripcion", models.TextField()),
                ("falla", models.TextField(blank=True, default="")),
                ("reparacion", models.TextField(blank=True, default="")),
                ("estado", models.CharField(choices=[("programada", "Programada"), ("realizada", "Realizada")], max_length=10)),
                ("maquinaria", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="%(class)ss", to="mantenimiento.maquinaria")),
                ("vehiculo", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="%(class)ss", to="mantenedores.vehiculo")),
            ],
            options={"ordering": ["-fecha_programada", "-fecha_realizada", "-id"]},
        ),
        migrations.AddConstraint(model_name="registrouso", constraint=models.CheckConstraint(check=models.Q(models.Q(("maquinaria__isnull", False), ("vehiculo__isnull", True)), models.Q(("maquinaria__isnull", True), ("vehiculo__isnull", False)), _connector="OR"), name="registro_uso_un_activo")),
        migrations.AddConstraint(model_name="mantencion", constraint=models.CheckConstraint(check=models.Q(models.Q(("maquinaria__isnull", False), ("vehiculo__isnull", True)), models.Q(("maquinaria__isnull", True), ("vehiculo__isnull", False)), _connector="OR"), name="mantencion_un_activo")),
    ]
