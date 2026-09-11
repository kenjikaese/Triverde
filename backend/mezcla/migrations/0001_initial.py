from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inventario", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="Alerta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("origen", models.CharField(choices=[("mezcla", "Mezcla"), ("mantencion", "Mantencion"), ("documento", "Documento")], max_length=12)),
                ("nivel", models.CharField(default="faltante", max_length=20)),
                ("estado", models.CharField(choices=[("activa", "Activa"), ("resuelta", "Resuelta")], default="activa", max_length=10)),
                ("mensaje", models.CharField(max_length=240)),
                ("categoria", models.CharField(blank=True, choices=[("seca", "Seca"), ("verde", "Verde")], max_length=6, null=True)),
                ("faltante_m3", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("disponible_m3", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("fecha_generada", models.DateTimeField(auto_now_add=True)),
                ("fecha_resuelta", models.DateTimeField(blank=True, null=True)),
                ("mantencion", models.IntegerField(blank=True, null=True)),
                ("pila", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="alertas", to="inventario.pila")),
                ("resuelta_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="alertas_resueltas", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-fecha_generada", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="alerta",
            constraint=models.UniqueConstraint(condition=models.Q(estado="activa", origen="mezcla"), fields=("pila", "categoria"), name="alerta_mezcla_activa_pila_categoria_unica"),
        ),
    ]
