"""Helper de auditoria (RNF-01).

Las acciones sensibles (crear/editar usuario, cambiar parametro, rechazar
recepcion, aplicar multa) registran una entrada en `BitacoraAuditoria`.
"""
from acceso.models import BitacoraAuditoria


def registrar_auditoria(usuario, accion, entidad_afectada, id_objeto=None, detalle=None):
    """Crea un registro de auditoria. Devuelve la instancia creada."""
    return BitacoraAuditoria.objects.create(
        usuario=usuario if usuario and usuario.is_authenticated else None,
        accion=accion,
        entidad_afectada=entidad_afectada,
        id_objeto=str(id_objeto) if id_objeto is not None else None,
        detalle=detalle,
    )
