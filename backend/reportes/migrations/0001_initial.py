from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [("acceso", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="Reporte",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("recepciones", "Recepciones"), ("produccion", "Produccion"), ("ventas_cobros", "Ventas y cobros")], max_length=20)),
                ("periodo_inicio", models.DateField()),
                ("periodo_fin", models.DateField()),
                ("formato", models.CharField(choices=[("pdf", "PDF"), ("excel", "Excel"), ("csv", "CSV")], default="pdf", max_length=10)),
                ("fecha_generado", models.DateTimeField(auto_now_add=True)),
                ("contenido", models.JSONField(default=dict)),
                ("usuario", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reportes", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-fecha_generado", "-id"]},
        ),
    ]