import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("mantenimiento", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Alerta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("origen", models.CharField(choices=[("mezcla", "Mezcla"), ("mantencion", "Mantencion"), ("documento", "Documento")], max_length=12)),
                ("clave", models.CharField(help_text="Identificador estable para no duplicar alertas. Ejemplos: mantencion:15 o mezcla:pila:8:seca.", max_length=160)),
                ("nivel", models.CharField(choices=[("informativa", "Informativa"), ("advertencia", "Advertencia"), ("critica", "Critica")], max_length=12)),
                ("estado", models.CharField(choices=[("activa", "Activa"), ("resuelta", "Resuelta")], default="activa", max_length=9)),
                ("mensaje", models.TextField()),
                ("fecha_generada", models.DateTimeField(auto_now_add=True)),
                ("fecha_resuelta", models.DateTimeField(blank=True, null=True)),
                ("mantencion", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="alertas", to="mantenimiento.mantencion")),
                ("resuelta_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="alertas_resueltas", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-fecha_generada"]},
        ),
        migrations.AddConstraint(
            model_name="alerta",
            constraint=models.UniqueConstraint(condition=models.Q(("estado", "activa")), fields=("origen", "clave"), name="alerta_activa_origen_clave_unica"),
        ),
        migrations.AddConstraint(
            model_name="alerta",
            constraint=models.UniqueConstraint(condition=models.Q(("estado", "activa"), ("origen", "mantencion")), fields=("mantencion",), name="alerta_mantencion_activa_unica"),
        ),
    ]
