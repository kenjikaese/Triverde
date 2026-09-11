from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from mantenedores.models import Vehiculo

from .models import Maquinaria, Mantencion, RegistroUso


def validar_activo(attrs, instance=None):
    maquinaria = attrs.get("maquinaria", getattr(instance, "maquinaria", None))
    vehiculo = attrs.get("vehiculo", getattr(instance, "vehiculo", None))
    if bool(maquinaria) == bool(vehiculo):
        raise serializers.ValidationError(
            "Debe indicar exactamente una maquinaria o un vehiculo."
        )
    activo = maquinaria or vehiculo
    if activo.estado != activo.ACTIVO:
        raise serializers.ValidationError("El activo esta dado de baja.")
    if isinstance(activo, Vehiculo) and not activo.es_mantenible:
        raise serializers.ValidationError("El vehiculo no esta habilitado como mantenible.")
    return activo


class MaquinariaSerializer(serializers.ModelSerializer):
    codigo = serializers.SerializerMethodField()
    clase_activo = serializers.SerializerMethodField()

    class Meta:
        model = Maquinaria
        fields = [
            "id", "codigo", "clase_activo", "nombre", "tipo", "datos_tecnicos",
            "horometro", "estado_operativo", "estado",
        ]

    def get_codigo(self, obj):
        return f"MQ-{obj.pk:02d}"

    def get_clase_activo(self, obj):
        return "maquinaria"

    def validate_horometro(self, value):
        if value < 0:
            raise serializers.ValidationError("El horometro no puede ser negativo.")
        if self.instance and value < self.instance.horometro:
            raise serializers.ValidationError("El horometro no puede retroceder.")
        return value


class RegistroUsoSerializer(serializers.ModelSerializer):
    operador_nombre = serializers.CharField(source="operador.nombre_completo", read_only=True)
    activo_nombre = serializers.SerializerMethodField()

    class Meta:
        model = RegistroUso
        fields = [
            "id", "maquinaria", "vehiculo", "activo_nombre", "horas", "fecha",
            "operador", "operador_nombre", "horas_transcurridas",
        ]
        read_only_fields = ["operador", "horas_transcurridas"]

    def get_activo_nombre(self, obj):
        return obj.activo.nombre if obj.maquinaria_id else obj.activo.patente

    def validate(self, attrs):
        activo = validar_activo(attrs, self.instance)
        if activo.estado_operativo == activo.FUERA_DE_SERVICIO:
            raise serializers.ValidationError(
                "No se pueden registrar horas de un activo fuera de servicio."
            )
        if attrs["horas"] < activo.horometro:
            raise serializers.ValidationError(
                {"horas": "La lectura no puede ser menor al horometro actual."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data["operador"] = self.context["request"].user
        activo_original = validated_data.get("maquinaria") or validated_data.get("vehiculo")
        activo = activo_original.__class__.objects.select_for_update().get(pk=activo_original.pk)
        if validated_data["horas"] < activo.horometro:
            raise serializers.ValidationError(
                {"horas": "La lectura no puede ser menor al horometro actual."}
            )
        validated_data["horas_transcurridas"] = validated_data["horas"] - activo.horometro
        registro = super().create(validated_data)
        activo.horometro = registro.horas
        activo.save(update_fields=["horometro"])
        from .services import revisar_alertas_mantenimiento
        revisar_alertas_mantenimiento()
        return registro


class MantencionSerializer(serializers.ModelSerializer):
    activo_nombre = serializers.SerializerMethodField()
    confirmar_duplicada = serializers.BooleanField(write_only=True, required=False, default=False)
    reparacion_habilita = serializers.BooleanField(write_only=True, required=False, default=True)

    class Meta:
        model = Mantencion
        fields = [
            "id", "maquinaria", "vehiculo", "activo_nombre", "tipo", "criterio",
            "umbral_horas", "fecha_programada", "fecha_realizada", "costo",
            "descripcion", "falla", "reparacion", "estado", "confirmar_duplicada",
            "reparacion_habilita",
        ]
        read_only_fields = ["estado", "fecha_realizada"]

    def get_activo_nombre(self, obj):
        return obj.activo.nombre if obj.maquinaria_id else obj.activo.patente

    def validate(self, attrs):
        activo = validar_activo(attrs, self.instance)
        tipo = attrs.get("tipo", getattr(self.instance, "tipo", None))
        if tipo == Mantencion.PREVENTIVA:
            if activo.estado_operativo == activo.FUERA_DE_SERVICIO:
                raise serializers.ValidationError(
                    "No se puede programar un activo fuera de servicio."
                )
            criterio = attrs.get("criterio", getattr(self.instance, "criterio", None))
            if criterio == Mantencion.POR_FECHA:
                fecha = attrs.get("fecha_programada", getattr(self.instance, "fecha_programada", None))
                if not fecha or fecha <= timezone.localdate():
                    raise serializers.ValidationError(
                        {"fecha_programada": "La fecha debe ser futura."}
                    )
                attrs["umbral_horas"] = None
            elif criterio == Mantencion.POR_HORAS:
                umbral = attrs.get("umbral_horas", getattr(self.instance, "umbral_horas", None))
                if umbral is None or umbral <= activo.horometro:
                    raise serializers.ValidationError(
                        {"umbral_horas": "El umbral debe superar el horometro actual."}
                    )
                attrs["fecha_programada"] = None
            else:
                raise serializers.ValidationError({"criterio": "Seleccione fecha u horas."})

            filtro = {
                "maquinaria": attrs.get("maquinaria", getattr(self.instance, "maquinaria", None)),
                "vehiculo": attrs.get("vehiculo", getattr(self.instance, "vehiculo", None)),
                "tipo": Mantencion.PREVENTIVA,
                "estado": Mantencion.PROGRAMADA,
                "criterio": criterio,
            }
            duplicadas = Mantencion.objects.filter(**filtro)
            if self.instance:
                duplicadas = duplicadas.exclude(pk=self.instance.pk)
            if duplicadas.exists() and not attrs.get("confirmar_duplicada"):
                raise serializers.ValidationError(
                    {"confirmar_duplicada": "Ya existe una mantencion programada con este criterio."}
                )
        else:
            if not attrs.get("falla", "").strip():
                raise serializers.ValidationError({"falla": "Describa la falla detectada."})
            if not attrs.get("reparacion", "").strip():
                raise serializers.ValidationError({"reparacion": "Describa la reparacion realizada."})
            if attrs.get("costo") is None or attrs["costo"] < 0:
                raise serializers.ValidationError({"costo": "El costo debe ser cero o positivo."})
            attrs.update(
                criterio=None, umbral_horas=None, fecha_programada=None,
                fecha_realizada=timezone.localdate(), estado=Mantencion.REALIZADA,
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        habilita = validated_data.pop("reparacion_habilita", True)
        validated_data.pop("confirmar_duplicada", None)
        if validated_data["tipo"] == Mantencion.PREVENTIVA:
            validated_data["estado"] = Mantencion.PROGRAMADA
        mantencion = super().create(validated_data)
        if mantencion.tipo == Mantencion.CORRECTIVA:
            activo = mantencion.activo
            activo.estado_operativo = (
                activo.OPERATIVA if habilita else activo.FUERA_DE_SERVICIO
            )
            activo.save(update_fields=["estado_operativo"])
        return mantencion

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("confirmar_duplicada", None)
        validated_data.pop("reparacion_habilita", None)
        mantencion = super().update(instance, validated_data)
        mantencion.alertas.filter(estado="activa").update(
            estado="resuelta", fecha_resuelta=timezone.now()
        )
        from .services import revisar_alertas_mantenimiento
        revisar_alertas_mantenimiento()
        return mantencion
