"""Serializers del modulo de acceso (Rol, Usuario, login, auditoria)."""
from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

from .models import BitacoraAuditoria, Rol

Usuario = get_user_model()


class RolSerializer(serializers.ModelSerializer):
    """Rol de un usuario (catalogo cerrado: solo lectura via API)."""

    class Meta:
        model = Rol
        fields = ["id", "nombre", "descripcion"]


class UsuarioSerializer(serializers.ModelSerializer):
    """Cuenta de acceso. `password` es write-only: nunca se serializa."""

    password = serializers.CharField(
        write_only=True, required=False, style={"input_type": "password"}
    )
    rol_nombre = serializers.CharField(source="rol.nombre", read_only=True)

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "email",
            "nombre_completo",
            "rol",
            "rol_nombre",
            "estado",
            "is_active",
            "date_joined",
            "password",
        ]
        read_only_fields = ["date_joined"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError(
                {"password": "La contrasena es obligatoria al crear un usuario."}
            )
        usuario = Usuario.objects.create_user(password=password, **validated_data)
        return usuario

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for atributo, valor in validated_data.items():
            setattr(instance, atributo, valor)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    """Credenciales de ingreso. Devuelve el usuario autenticado si es valido."""

    username = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"})

    def validate(self, attrs):
        usuario = authenticate(
            request=self.context.get("request"),
            username=attrs["username"],
            password=attrs["password"],
        )
        if usuario is None:
            raise serializers.ValidationError("Credenciales invalidas.")
        if usuario.estado == Usuario.INACTIVO:
            raise serializers.ValidationError(
                "La cuenta esta inactiva; contacte al administrador."
            )
        attrs["usuario"] = usuario
        return attrs


class BitacoraAuditoriaSerializer(serializers.ModelSerializer):
    """Registro de auditoria (solo lectura via API)."""

    usuario_username = serializers.CharField(source="usuario.username", read_only=True)

    class Meta:
        model = BitacoraAuditoria
        fields = [
            "id",
            "usuario",
            "usuario_username",
            "accion",
            "entidad_afectada",
            "id_objeto",
            "fecha_hora",
            "detalle",
        ]
        read_only_fields = fields
