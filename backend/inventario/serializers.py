"""Serializers del modulo de inventario, pilas y procesos (CU-34 a CU-44).

Igual que en la recepcion, las reglas de negocio viven en el servidor: el
cliente declara que hizo (que material, que volumen, sobre que pila) y el
serializer valida el estado de la pila, deriva lo que haya que derivar y mueve
el inventario a traves de `services.py`. Nunca se confia en cantidades
calculadas por el dispositivo.
"""
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from configuracion.models import ParametroConversion
from mantenedores.models import Material
from recepcion.models import DetalleRecepcion, Recepcion

from . import services
from .models import ComposicionPila, Inventario, Pila, ProcesoPila

CERO = Decimal("0.00")
CENTESIMA = Decimal("0.01")

# Techo de temperatura para la maduracion (CU-38 Excepcion 2). Es un valor de
# referencia: si el administrador configura el parametro, manda el configurado.
CLAVE_TEMPERATURA_MAXIMA = "temperatura_maxima_pila"
TEMPERATURA_MAXIMA_POR_DEFECTO = Decimal("70.00")


def temperatura_maxima():
    """Techo de temperatura recomendado, configurable desde el Modulo 2."""
    parametro = ParametroConversion.objects.filter(
        clave=CLAVE_TEMPERATURA_MAXIMA
    ).first()
    return parametro.valor if parametro else TEMPERATURA_MAXIMA_POR_DEFECTO


def validar_no_futura(fecha, campo="fecha"):
    """Rechaza fechas posteriores al momento actual.

    Regla comun a CU-35, CU-39 y CU-40: el operador registra lo que ya paso,
    nunca lo que va a pasar.
    """
    if fecha is None:
        return fecha
    if not isinstance(fecha, datetime):
        # Es un date (CU-35): se compara contra el dia de hoy.
        if fecha > timezone.localdate():
            raise serializers.ValidationError(
                {campo: "La fecha no puede ser posterior al dia de hoy."}
            )
        return fecha
    if fecha > timezone.now():
        raise serializers.ValidationError(
            {campo: "La fecha no puede ser posterior al momento actual."}
        )
    return fecha


# --- Inventario (CU-34) -----------------------------------------------------


class InventarioSerializer(serializers.ModelSerializer):
    """Saldo por material y etapa. Solo lectura: lo mueven los procesos."""

    material_nombre = serializers.CharField(source="material.nombre", read_only=True)
    material_categoria = serializers.CharField(
        source="material.categoria", read_only=True
    )

    class Meta:
        model = Inventario
        fields = [
            "id",
            "material",
            "material_nombre",
            "material_categoria",
            "etapa",
            "volumen_m3",
            "actualizado",
        ]
        read_only_fields = fields


# --- Pilas (CU-35, CU-43) ---------------------------------------------------


class ComposicionPilaSerializer(serializers.ModelSerializer):
    """Material incorporado a una pila (lectura)."""

    material_nombre = serializers.CharField(source="material.nombre", read_only=True)

    class Meta:
        model = ComposicionPila
        fields = ["id", "material", "material_nombre", "volumen_m3"]
        read_only_fields = fields


class AgregarComposicionSerializer(serializers.Serializer):
    """Entrada de CU-36: un material y su volumen incorporado a la pila.

    `detalle_recepcion` es opcional (propuesta Inc 3, CU-68): indica de que
    descarga sale el material, para que la pila conserve su origen.
    """

    material = serializers.PrimaryKeyRelatedField(queryset=Material.objects.all())
    volumen_m3 = serializers.DecimalField(max_digits=8, decimal_places=2)
    detalle_recepcion = serializers.PrimaryKeyRelatedField(
        queryset=DetalleRecepcion.objects.select_related("recepcion", "material"),
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        material = attrs["material"]
        volumen = attrs["volumen_m3"]
        if volumen <= CERO:
            raise serializers.ValidationError(
                {"volumen_m3": "El volumen debe ser mayor a cero."}
            )
        detalle = attrs.get("detalle_recepcion")
        if detalle is not None:
            self._validar_origen(detalle, material, volumen)
        # CU-36 Excepcion 1: no se puede incorporar mas de lo disponible.
        etapa = services.etapa_origen_para_pila(material)
        disponible = services.disponible(material, etapa)
        ya_declarado = CERO
        pila = self.context.get("pila")
        if pila is not None:
            existente = pila.composiciones.filter(material=material).first()
            if existente is not None:
                ya_declarado = existente.volumen_m3
        if volumen + ya_declarado > disponible:
            raise serializers.ValidationError(
                {
                    "volumen_m3": (
                        f"Solo hay {disponible} m3 de '{material.nombre}' en la "
                        f"etapa '{etapa}'; ya declarados {ya_declarado} m3 en "
                        "esta pila."
                    )
                }
            )
        attrs["etapa_origen"] = etapa
        return attrs

    def _validar_origen(self, detalle, material, volumen):
        """La descarga de origen debe estar recibida, ser del mismo material y
        tener volumen suficiente sin contar lo ya aportado a otras pilas."""
        if detalle.recepcion.estado != Recepcion.RECIBIDA:
            raise serializers.ValidationError(
                {"detalle_recepcion": "Solo una descarga recibida puede ser origen de una pila."}
            )
        if detalle.material_id != material.pk:
            raise serializers.ValidationError(
                {
                    "detalle_recepcion": (
                        f"La descarga es de '{detalle.material.nombre}', no de "
                        f"'{material.nombre}'."
                    )
                }
            )
        ya_aportado = detalle.aportes_pila.aggregate(total=Sum("volumen_m3"))["total"] or CERO
        pila = self.context.get("pila")
        if pila is not None:
            # Lo aportado por esta misma descarga a esta pila se va a sumar, no
            # a duplicar: se descuenta del acumulado para no contarlo dos veces.
            propio = detalle.aportes_pila.filter(pila=pila).aggregate(
                total=Sum("volumen_m3")
            )["total"] or CERO
            ya_aportado -= propio
            volumen = volumen + propio
        if ya_aportado + volumen > detalle.volumen_m3:
            raise serializers.ValidationError(
                {
                    "detalle_recepcion": (
                        f"La descarga trajo {detalle.volumen_m3} m3 y ya aporto "
                        f"{ya_aportado} m3 a otras pilas; no alcanza para {volumen} m3."
                    )
                }
            )


class PilaSerializer(serializers.ModelSerializer):
    """Pila de compostaje (CU-35).

    `codigo` es opcional al crear: si no viene, el sistema propone el
    correlativo siguiente. `estado` lo gobiernan los procesos (CU-36, CU-41,
    CU-42), no el cliente.
    """

    codigo = serializers.CharField(max_length=30, required=False)
    fecha_inicio = serializers.DateField(required=False)
    estado = serializers.CharField(read_only=True)
    volumen_total_m3 = serializers.SerializerMethodField()

    class Meta:
        model = Pila
        fields = [
            "id",
            "codigo",
            "fecha_inicio",
            "estado",
            "observaciones",
            "volumen_total_m3",
        ]

    def get_volumen_total_m3(self, pila):
        return pila.volumen_composicion()

    def validate_fecha_inicio(self, valor):
        # CU-35 Excepcion 2: no se abre una pila con fecha futura.
        return validar_no_futura(valor, "fecha_inicio")

    def create(self, validated_data):
        validated_data.setdefault("fecha_inicio", timezone.localdate())
        if not validated_data.get("codigo"):
            validated_data["codigo"] = Pila.generar_codigo()
        return super().create(validated_data)


class PilaTrazabilidadSerializer(serializers.ModelSerializer):
    """Ficha completa de una pila (CU-43): composicion + linea de tiempo.

    Los procesos van en orden cronologico ascendente, que es como se lee un
    historial; el listado general los muestra al reves (lo mas reciente arriba).
    """

    composiciones = ComposicionPilaSerializer(many=True, read_only=True)
    procesos = serializers.SerializerMethodField()
    volumen_total_m3 = serializers.SerializerMethodField()
    volumen_ensacado_m3 = serializers.SerializerMethodField()
    volumen_curado_disponible_m3 = serializers.SerializerMethodField()

    class Meta:
        model = Pila
        fields = [
            "id",
            "codigo",
            "fecha_inicio",
            "estado",
            "observaciones",
            "volumen_total_m3",
            "volumen_ensacado_m3",
            "volumen_curado_disponible_m3",
            "composiciones",
            "procesos",
        ]
        read_only_fields = fields

    def get_procesos(self, pila):
        procesos = pila.procesos.select_related("material", "operador").order_by(
            "fecha", "id"
        )
        return ProcesoPilaSerializer(procesos, many=True).data

    def get_volumen_total_m3(self, pila):
        return pila.volumen_composicion()

    def get_volumen_ensacado_m3(self, pila):
        return pila.volumen_ensacado()

    def get_volumen_curado_disponible_m3(self, pila):
        return pila.volumen_curado_disponible()


# --- Procesos (CU-37 a CU-42) -----------------------------------------------


def _repartir_por_composicion(pila, volumen):
    """Reparte `volumen` entre los materiales de la pila, a prorrata.

    El Inventario lleva el saldo por material; una pila puede tener varios.
    Al ensacar se declara un volumen unico, asi que se distribuye segun el peso
    relativo de cada material en la composicion. El ultimo tramo absorbe el
    resto del redondeo para que la suma cuadre exactamente con lo declarado.
    """
    composiciones = list(pila.composiciones.select_related("material"))
    total = pila.volumen_composicion()
    if not composiciones or total <= CERO:
        raise serializers.ValidationError(
            "La pila no tiene composicion registrada; no se puede repartir el "
            "volumen entre sus materiales."
        )
    cantidad = Decimal(str(volumen))
    repartos = []
    acumulado = CERO
    for composicion in composiciones[:-1]:
        parte = (cantidad * composicion.volumen_m3 / total).quantize(CENTESIMA)
        acumulado += parte
        repartos.append((composicion.material, parte))
    repartos.append((composiciones[-1].material, cantidad - acumulado))
    return [(material, parte) for material, parte in repartos if parte > CERO]


class ProcesoPilaSerializer(serializers.ModelSerializer):
    """Registro de un proceso (CU-37 a CU-42).

    Un unico serializer para los seis tipos, como define C_ProcesosPila. El
    `tipo` decide que campos son obligatorios, que estado debe tener la pila y
    que movimiento de inventario corresponde.
    """

    id_local = serializers.UUIDField(required=False)
    estado_sincronizacion = serializers.CharField(read_only=True)
    fecha = serializers.DateTimeField(required=False)
    pila_codigo = serializers.CharField(source="pila.codigo", read_only=True)
    material_nombre = serializers.CharField(source="material.nombre", read_only=True)
    chip_pendiente = serializers.BooleanField(read_only=True)
    advertencia = serializers.CharField(read_only=True)

    class Meta:
        model = ProcesoPila
        fields = [
            "id",
            "id_local",
            "estado_sincronizacion",
            "pila",
            "pila_codigo",
            "material",
            "material_nombre",
            "operador",
            "tipo",
            "fecha",
            "temperatura",
            "humedad",
            "volumen_m3",
            "chip_pendiente",
            "advertencia",
        ]
        read_only_fields = ["operador"]

    # -- validacion por tipo -------------------------------------------------

    def validate(self, attrs):
        tipo = attrs.get("tipo")
        attrs.setdefault("fecha", timezone.now())
        validar_no_futura(attrs["fecha"])

        if tipo == ProcesoPila.TRITURADO:
            self._validar_triturado(attrs)
        elif tipo in (ProcesoPila.VOLTEO, ProcesoPila.RIEGO, ProcesoPila.HARNEADO):
            self._validar_sobre_pila_en_proceso(attrs, tipo)
        elif tipo == ProcesoPila.REPOSO:
            self._validar_reposo(attrs)
        elif tipo == ProcesoPila.ENSACADO:
            self._validar_ensacado(attrs)
        return attrs

    def _validar_triturado(self, attrs):
        """CU-37: material obligatorio, sin pila, volumen mayor a cero."""
        material = attrs.get("material")
        if material is None:
            raise serializers.ValidationError(
                {"material": "El triturado debe indicar el material procesado."}
            )
        if attrs.get("pila") is not None:
            raise serializers.ValidationError(
                {"pila": "El triturado ocurre antes de armar una pila; no lleva pila."}
            )
        volumen = attrs.get("volumen_m3")
        if volumen is None or volumen <= CERO:
            # CU-37 Excepcion 1.
            raise serializers.ValidationError(
                {"volumen_m3": "Indique el volumen triturado (mayor a cero)."}
            )
        # CU-37 Excepcion 2: no se puede triturar mas de lo que hay.
        disponible = services.disponible(material, Inventario.POR_TRITURAR)
        if volumen > disponible:
            raise serializers.ValidationError(
                {
                    "volumen_m3": (
                        f"Solo hay {disponible} m3 de '{material.nombre}' por "
                        "triturar."
                    )
                }
            )

    def _validar_sobre_pila_en_proceso(self, attrs, tipo):
        """CU-38, CU-39, CU-40: la pila debe existir y estar en proceso."""
        pila = attrs.get("pila")
        if pila is None:
            raise serializers.ValidationError(
                {"pila": f"El {tipo} debe registrarse sobre una pila."}
            )
        if pila.estado != Pila.EN_PROCESO:
            # CU-40 Excepcion 2 (y equivalente para volteo y riego).
            raise serializers.ValidationError(
                {
                    "pila": (
                        f"La pila {pila.codigo} esta '{pila.estado}'; el {tipo} "
                        "solo corresponde a una pila en proceso."
                    )
                }
            )
        if tipo == ProcesoPila.VOLTEO and attrs.get("temperatura") is None:
            # CU-38 Excepcion 1: la temperatura medida es obligatoria.
            raise serializers.ValidationError(
                {"temperatura": "Registre la temperatura medida al voltear la pila."}
            )

    def _validar_reposo(self, attrs):
        """CU-41: pila en proceso y con harneado previo."""
        pila = attrs.get("pila")
        if pila is None:
            raise serializers.ValidationError(
                {"pila": "El reposo debe registrarse sobre una pila."}
            )
        if pila.estado in (Pila.EN_REPOSO, Pila.CERRADA):
            # CU-41 Excepcion 2.
            raise serializers.ValidationError(
                {"pila": f"La pila {pila.codigo} ya esta '{pila.estado}'."}
            )
        if pila.estado != Pila.EN_PROCESO:
            raise serializers.ValidationError(
                {"pila": f"La pila {pila.codigo} esta '{pila.estado}'; debe estar en proceso."}
            )
        if not pila.procesos.filter(tipo=ProcesoPila.HARNEADO).exists():
            # CU-41 Excepcion 1.
            raise serializers.ValidationError(
                {"pila": "La pila debe harnearse antes de iniciar el reposo."}
            )

    def _validar_ensacado(self, attrs):
        """CU-42: pila en reposo y cantidad dentro del curado disponible."""
        pila = attrs.get("pila")
        if pila is None:
            raise serializers.ValidationError(
                {"pila": "El ensacado debe registrarse sobre una pila."}
            )
        if pila.estado != Pila.EN_REPOSO:
            raise serializers.ValidationError(
                {
                    "pila": (
                        f"La pila {pila.codigo} esta '{pila.estado}'; solo se "
                        "ensaca una pila en reposo."
                    )
                }
            )
        volumen = attrs.get("volumen_m3")
        if volumen is None or volumen <= CERO:
            # CU-42 Excepcion 1.
            raise serializers.ValidationError(
                {"volumen_m3": "Indique la cantidad ensacada (mayor a cero)."}
            )
        disponible = pila.volumen_curado_disponible()
        if volumen > disponible:
            # CU-42 Excepcion 2.
            raise serializers.ValidationError(
                {
                    "volumen_m3": (
                        f"La pila {pila.codigo} solo tiene {disponible} m3 "
                        "curados disponibles para ensacar."
                    )
                }
            )

    # -- aplicacion ----------------------------------------------------------

    def create(self, validated_data):
        """Crea el proceso y aplica su efecto sobre la pila y el inventario.

        Todo ocurre en una transaccion: si el movimiento de inventario falla,
        tampoco queda el proceso registrado.

        Es idempotente por `id_local`: como el proceso viaja por la cola
        offline, reenviar el mismo lote no vuelve a mover el inventario. Se
        devuelve el proceso ya registrado sin aplicar nada.
        """
        id_local = validated_data.get("id_local")
        if id_local is not None:
            existente = ProcesoPila.objects.filter(id_local=id_local).first()
            if existente is not None:
                return existente
        tipo = validated_data["tipo"]
        with transaction.atomic():
            if tipo == ProcesoPila.TRITURADO:
                return self._aplicar_triturado(validated_data)
            if tipo == ProcesoPila.VOLTEO:
                return self._aplicar_volteo(validated_data)
            if tipo == ProcesoPila.REPOSO:
                return self._aplicar_reposo(validated_data)
            if tipo == ProcesoPila.ENSACADO:
                return self._aplicar_ensacado(validated_data)
            # Riego y harneado solo dejan constancia; no mueven inventario.
            return ProcesoPila.objects.create(**validated_data)

    def _aplicar_triturado(self, validated_data):
        """CU-37: descuenta 'por triturar' e incorpora el chip derivado."""
        material = validated_data["material"]
        volumen = validated_data["volumen_m3"]
        chip = material.derivar_chip(volumen)
        if chip is None:
            # CU-37 Excepcion 3: se registra y descuenta, el chip queda pendiente.
            services.descontar(material, Inventario.POR_TRITURAR, volumen)
            validated_data["chip_pendiente"] = True
            validated_data["advertencia"] = (
                f"'{material.nombre}' no tiene factor de reduccion a chip "
                "configurado; la cantidad de chip queda pendiente de conversion."
            )
        else:
            services.aplicar_movimiento(
                material,
                Inventario.POR_TRITURAR,
                Inventario.CHIP,
                volumen,
                volumen_destino=chip,
            )
        return ProcesoPila.objects.create(**validated_data)

    def _aplicar_volteo(self, validated_data):
        """CU-38: registra el volteo; marca advertencia si la temperatura excede."""
        temperatura = validated_data.get("temperatura")
        techo = temperatura_maxima()
        if temperatura is not None and temperatura > techo:
            # CU-38 Excepcion 2: se registra igual, marcado con advertencia.
            validated_data["advertencia"] = (
                f"Temperatura {temperatura} C sobre el techo recomendado "
                f"({techo} C); un exceso sostenido afecta la calidad del compost."
            )
        return ProcesoPila.objects.create(**validated_data)

    def _aplicar_reposo(self, validated_data):
        """CU-41: traslada la pila de 'pila en proceso' a 'curado' y la cierra a reposo."""
        pila = validated_data["pila"]
        for composicion in pila.composiciones.select_related("material"):
            services.aplicar_movimiento(
                composicion.material,
                Inventario.PILA_EN_PROCESO,
                Inventario.CURADO,
                composicion.volumen_m3,
            )
        proceso = ProcesoPila.objects.create(**validated_data)
        pila.estado = Pila.EN_REPOSO
        pila.save(update_fields=["estado"])
        return proceso

    def _aplicar_ensacado(self, validated_data):
        """CU-42: traslada de 'curado' a 'ensacado' y cierra la pila si se agota."""
        pila = validated_data["pila"]
        volumen = validated_data["volumen_m3"]
        disponible_antes = pila.volumen_curado_disponible()
        for material, parte in _repartir_por_composicion(pila, volumen):
            services.aplicar_movimiento(
                material, Inventario.CURADO, Inventario.ENSACADO, parte
            )
        proceso = ProcesoPila.objects.create(**validated_data)
        if volumen >= disponible_antes:
            pila.estado = Pila.CERRADA
            pila.save(update_fields=["estado"])
        return proceso
