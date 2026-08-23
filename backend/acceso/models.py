"""Modulo 1 - Acceso y auditoria (docs/11 SS11.6)."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Rol(models.Model):
    """Rol/permisos de un usuario."""

    ADMINISTRADOR = "Administrador"
    OPERADOR = "Operador"
    TRANSPORTISTA = "Transportista"
    NOMBRE_CHOICES = [
        (ADMINISTRADOR, "Administrador"),
        (OPERADOR, "Operador"),
        (TRANSPORTISTA, "Transportista"),
    ]

    nombre = models.CharField(max_length=20, unique=True, choices=NOMBRE_CHOICES)
    descripcion = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.nombre


class Usuario(AbstractUser):
    """Cuenta de acceso. Extiende AbstractUser (username, email, password,
    is_active, date_joined). Agrega nombre_completo, rol y estado (baja logica).
    """

    ACTIVO = "activo"
    INACTIVO = "inactivo"
    ESTADO_CHOICES = [(ACTIVO, "Activo"), (INACTIVO, "Inactivo")]

    nombre_completo = models.CharField(max_length=150)
    rol = models.ForeignKey(
        Rol, on_delete=models.PROTECT, related_name="usuarios"
    )
    estado = models.CharField(max_length=8, choices=ESTADO_CHOICES, default=ACTIVO)

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return self.nombre_completo or self.username


class BitacoraAuditoria(models.Model):
    """Registro de acciones sensibles (RNF-01)."""

    usuario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="acciones",
    )
    accion = models.CharField(max_length=50)
    entidad_afectada = models.CharField(max_length=50)
    id_objeto = models.CharField(max_length=64, null=True, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    detalle = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Registro de auditoria"
        verbose_name_plural = "Bitacora de auditoria"
        ordering = ["-fecha_hora"]

    def __str__(self):
        return f"{self.accion} sobre {self.entidad_afectada} ({self.fecha_hora:%Y-%m-%d %H:%M})"
