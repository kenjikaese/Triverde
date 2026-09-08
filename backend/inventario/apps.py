from django.apps import AppConfig


class InventarioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventario"
    verbose_name = "Modulo 5 - Inventario, pilas y procesos"

    def ready(self):
        # Registra el disparador de CU-44 sobre las recepciones (ver signals.py).
        from . import signals  # noqa: F401
