"""Siembra los datos que necesitan las pruebas end-to-end del Modulo 8.

Se apoya en `seed_inicial` (roles, admin, parametros y tarifas por tramo) y
agrega lo propio del ciclo comercial: un operador, un cliente con datos de
contacto completos, otro sin ellos, productos con precio, un vehiculo con
capacidad y una recepcion recibida lista para cobrar.

Determinista: borra los objetos transaccionales del modulo comercial antes de
sembrar, para que cada corrida parta del mismo estado y las aserciones sobre
totales y saldos sean estables.

Uso:  python manage.py seed_e2e
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from acceso.models import Rol
from comercial.models import (
    Cobro,
    Cotizacion,
    Despacho,
    DetalleVenta,
    DocumentoTributario,
    Venta,
)
from inventario.models import AporteRecepcionPila, ComposicionPila, Pila
from mantenedores.models import Cliente, Material, Producto, Vehiculo
from recepcion.models import DetalleRecepcion, Recepcion
from trazabilidad.models import (
    CertificadoTrazabilidad,
    DeclaracionSinader,
    IndicadorAmbiental,
)

Usuario = get_user_model()

CLAVE_E2E = "triverde-e2e-2026"


class Command(BaseCommand):
    help = "Prepara los datos de las pruebas end-to-end del modulo comercial."

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_inicial", verbosity=0)

        # --- Estado limpio del ciclo comercial y de trazabilidad -----------
        # Los certificados y las declaraciones protegen (PROTECT) a las
        # recepciones y clientes que referencian: se borran primero.
        CertificadoTrazabilidad.objects.all().delete()
        DeclaracionSinader.objects.all().delete()
        DocumentoTributario.objects.all().delete()
        Cobro.objects.all().delete()
        Despacho.objects.all().delete()
        DetalleVenta.objects.all().delete()
        Venta.objects.all().delete()
        Cotizacion.objects.all().delete()

        # --- Usuarios con clave conocida -----------------------------------
        rol_admin = Rol.objects.get(nombre=Rol.ADMINISTRADOR)
        rol_operador = Rol.objects.get(nombre=Rol.OPERADOR)

        admin = Usuario.objects.filter(username="admin").first()
        if admin:
            admin.set_password(CLAVE_E2E)
            admin.save(update_fields=["password"])

        operador, _ = Usuario.objects.get_or_create(
            username="operador",
            defaults={"nombre_completo": "Operador de Planta", "rol": rol_operador},
        )
        operador.rol = rol_operador
        operador.set_password(CLAVE_E2E)
        operador.save()

        # --- Clientes ------------------------------------------------------
        # Con datos completos: permite exportar la cotizacion (CU-56).
        cliente, _ = Cliente.objects.update_or_create(
            razon_social="Vivero Los Aromos",
            defaults={
                "rut": "77.123.456-7",
                "nombre_contacto": "Javier Rojas",
                "telefono": "+56 9 8765 4321",
                "email": "contacto@losaromos.cl",
                "direccion": "Camino Quilapilun 1200, Colina",
                "estado_pago": Cliente.AL_DIA,
            },
        )
        # Sin datos de contacto: dispara la Excepcion 1 del CU-56.
        Cliente.objects.update_or_create(
            razon_social="Constructora Sin Datos",
            defaults={"rut": None, "nombre_contacto": None, "telefono": None,
                      "email": None, "direccion": None},
        )

        # --- Productos con precio configurado ------------------------------
        Producto.objects.update_or_create(
            nombre="Compost premium 40 L",
            defaults={
                "tipo": Producto.COMPOST,
                "precio": Decimal("4500.00"),
                "unidad_de_venta": Producto.SACO,
                "estado": Producto.ACTIVO,
            },
        )
        Producto.objects.update_or_create(
            nombre="Mulch de corteza",
            defaults={
                "tipo": Producto.MULCH,
                "precio": Decimal("45000.00"),
                "unidad_de_venta": Producto.M3,
                "estado": Producto.ACTIVO,
            },
        )

        # --- Vehiculo con capacidad dentro de un tramo tarifado ------------
        # 25 m3 cae en el tramo 20-30, que seed_inicial deja en $40.000.
        vehiculo, _ = Vehiculo.objects.update_or_create(
            patente="TRV125",
            defaults={
                "cliente": cliente,
                "capacidad_m3": Decimal("25.00"),
                "descripcion": "Camion tolva de pruebas",
            },
        )

        # --- Material y recepcion recibida lista para cobrar ---------------
        rama_verde, _ = Material.objects.update_or_create(
            nombre="Rama verde",
            defaults={
                "categoria": Material.VERDE,
                "densidad_kg_m3": Decimal("250.00"),
                "admite_chip": True,
                "factor_reduccion_chip": Decimal("5.00"),
            },
        )
        # Las recepciones del ciclo anterior se reemplazan. La del cliente sin
        # datos la crea el escenario e2e de SINADER (CU-67); se limpia aca para
        # que no quede como "por cobrar" en la corrida siguiente.
        recepciones_previas = Recepcion.objects.filter(
            cliente__razon_social__in=[cliente.razon_social, "Constructora Sin Datos"]
        )
        IndicadorAmbiental.objects.filter(recepcion__in=recepciones_previas).delete()
        AporteRecepcionPila.objects.filter(
            detalle_recepcion__recepcion__in=recepciones_previas
        ).delete()
        recepciones_previas.delete()
        recepcion = Recepcion.objects.create(
            cliente=cliente,
            vehiculo=vehiculo,
            fecha=date.today(),
            hora="09:30",
            estado=Recepcion.RECIBIDA,
            conductor="Pedro Soto",
        )
        # Una linea de material con su peso derivado: lo que exige el CU-65
        # para certificar la descarga (20 m3 x 250 kg/m3 = 5.000 kg).
        detalle = DetalleRecepcion.objects.create(
            recepcion=recepcion,
            material=rama_verde,
            volumen_m3=Decimal("20.00"),
            peso_derivado_kg=Decimal("5000.00"),
            chip_derivado_m3=Decimal("4.00"),
            destino_sugerido=DetalleRecepcion.A_PILA,
        )

        # --- Pila cerrada con composicion (Modulo 9, CU-68) ---------------
        # Lote de origen que el registro de venta puede enlazar y que la
        # trazabilidad del lote recorre hasta su composicion.
        pila, _ = Pila.objects.update_or_create(
            codigo="P-E2E-01",
            defaults={
                "fecha_inicio": date(2026, 6, 1),
                "estado": Pila.CERRADA,
                "observaciones": "Lote de pruebas end-to-end",
            },
        )
        ComposicionPila.objects.update_or_create(
            pila=pila, material=rama_verde, defaults={"volumen_m3": Decimal("20.00")}
        )
        # Origen de esa composicion: los 20 m3 salieron de la descarga de arriba.
        AporteRecepcionPila.objects.update_or_create(
            pila=pila, detalle_recepcion=detalle, defaults={"volumen_m3": Decimal("20.00")}
        )

        self.stdout.write(self.style.SUCCESS("Datos e2e listos."))
