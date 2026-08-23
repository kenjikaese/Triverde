"""Modelos base reutilizables.

`SincronizableModel` implementa la capa offline descrita en docs/11 (Decision 2):
los objetos que pueden crearse sin senal en el dispositivo nacen con un
`id_local` (UUID, clave alterna unica) que hace idempotente la sincronizacion
(CU-33), y un `estado_sincronizacion`. El `id` autoincremental sigue siendo la
PK del servidor.
"""
import uuid

from django.db import models


class SincronizableModel(models.Model):
    PENDIENTE = "pendiente"
    SINCRONIZADA = "sincronizada"
    EN_CONFLICTO = "en conflicto"
    ESTADO_SINCRONIZACION_CHOICES = [
        (PENDIENTE, "Pendiente"),
        (SINCRONIZADA, "Sincronizada"),
        (EN_CONFLICTO, "En conflicto"),
    ]

    id_local = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="Clave alterna generada en el dispositivo; idempotencia de sync (CU-33).",
    )
    estado_sincronizacion = models.CharField(
        max_length=12,
        choices=ESTADO_SINCRONIZACION_CHOICES,
        default=PENDIENTE,
    )

    class Meta:
        abstract = True
