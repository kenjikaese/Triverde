"""CU-90: revisa la vigencia de los documentos legales y genera sus alertas.

Actor Sistema. Corre a demanda durante la demo y queda programado en el
despliegue del Incremento 4. Es idempotente: pasarlo dos veces no duplica
alertas, porque la revision mantiene la activa que ya existe.

Uso:  python manage.py revisar_vencimientos_documentales
"""
from django.core.management.base import BaseCommand

from documental.cumplimiento import revisar_vencimientos


class Command(BaseCommand):
    help = "Revisa los vencimientos documentales y genera o actualiza sus alertas (CU-90)."

    def handle(self, *args, **options):
        resumen = revisar_vencimientos()
        self.stdout.write(
            f"Documentos revisados: {resumen['revisados']} "
            f"(por vencer: {resumen['por_vencer']}, vencidos: {resumen['vencidos']})"
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Alertas creadas: {resumen['alertas_creadas']} · "
                f"mantenidas: {resumen['alertas_mantenidas']}"
            )
        )
