"""Campos de serializer reutilizables.

`Base64ImageField` permite que una imagen viaje embebida como base64 dentro del
JSON (decision de contrato del sync offline CU-33: la cola local en IndexedDB
guarda la foto en base64 y la envia en el mismo lote de sincronizacion). Tambien
acepta un archivo subido normal (multipart) en el CRUD online, asi que sirve
para ambos caminos.

Sin dependencias externas: se decodifica a mano y se detecta el tipo por los
magic bytes (imghdr fue removido en Python 3.13). Pillow (ya instalado) valida
que el contenido sea realmente una imagen al llamar al ImageField base.
"""
import base64
import binascii
import uuid

from django.core.files.base import ContentFile
from rest_framework import serializers


def _extension_por_firma(datos):
    """Deduce la extension del archivo a partir de sus primeros bytes."""
    if datos[:3] == b"\xff\xd8\xff":
        return "jpg"
    if datos[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if datos[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return "webp"
    return "jpg"


class Base64ImageField(serializers.ImageField):
    """ImageField que ademas acepta una cadena base64 (con o sin data URI)."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            contenido = data
            extension = None
            if contenido.startswith("data:") and ";base64," in contenido:
                cabecera, contenido = contenido.split(";base64,", 1)
                # cabecera tipo "data:image/png" -> "png"
                if "/" in cabecera:
                    extension = cabecera.split("/", 1)[1].lower() or None
            try:
                decodificado = base64.b64decode(contenido, validate=True)
            except (binascii.Error, ValueError):
                raise serializers.ValidationError(
                    "La imagen base64 no es valida."
                )
            if not decodificado:
                raise serializers.ValidationError("La imagen base64 esta vacia.")
            extension = extension or _extension_por_firma(decodificado)
            if extension == "jpeg":
                extension = "jpg"
            data = ContentFile(decodificado, name=f"{uuid.uuid4()}.{extension}")
        return super().to_internal_value(data)
