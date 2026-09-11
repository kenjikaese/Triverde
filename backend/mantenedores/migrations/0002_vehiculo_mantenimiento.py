from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("mantenedores", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="vehiculo",
            name="es_mantenible",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="vehiculo",
            name="datos_tecnicos",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="vehiculo",
            name="horometro",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
