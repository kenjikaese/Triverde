from django.apps import AppConfig


class TrazabilidadConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "trazabilidad"
    verbose_name = "Modulo 9 - Trazabilidad y ambiental"

    def ready(self):
        from . import signals  # noqa: F401

