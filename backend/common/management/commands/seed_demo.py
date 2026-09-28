"""Siembra datos representativos en todos los modulos del Incremento 2.

Puebla el sistema con un conjunto de datos coherente (inventario, pilas,
mezcla y alertas, mantenimiento y comercial) para revisar la aplicacion
funcionando de extremo a extremo: pruebas manuales, recorrido de demo, etc.
Se apoya en seed_e2e (roles, admin, clientes, productos, vehiculo, recepcion).

Es una ayuda de datos, no parte del despliegue. Cada seccion esta aislada
para que un fallo no aborte el resto.

Uso:  python manage.py seed_demo
"""
from datetime import date, timedelta
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Puebla los modulos del Inc 2 con datos representativos para capturas."

    def _ok(self, msg):
        self.stdout.write(self.style.SUCCESS(msg))

    def _warn(self, msg):
        self.stdout.write(self.style.WARNING(msg))

    def handle(self, *args, **options):
        call_command("seed_e2e", verbosity=0)
        self._ok("Base e2e lista (clientes, productos, vehiculo, recepcion).")

        from mantenedores.models import Material, Producto, Cliente

        # --- Materiales seca + verde (mezcla necesita ambas categorias) ------
        seca, _ = Material.objects.update_or_create(
            nombre="Rama seca triturada",
            defaults={"categoria": Material.SECA, "densidad_kg_m3": Decimal("180.00"),
                      "admite_chip": True, "factor_reduccion_chip": Decimal("4.00")},
        )
        verde = Material.objects.filter(categoria=Material.VERDE).first()
        if verde is None:
            verde, _ = Material.objects.update_or_create(
                nombre="Rama verde", defaults={"categoria": Material.VERDE,
                    "densidad_kg_m3": Decimal("250.00"), "admite_chip": True,
                    "factor_reduccion_chip": Decimal("5.00")})
        self._ok("Materiales seca/verde listos.")

        # --- M2: receta de mezcla vigente ------------------------------------
        try:
            from configuracion.models import RecetaMezcla
            if RecetaMezcla.objects.filter(vigente=True).count() == 0:
                RecetaMezcla.objects.create(
                    nombre="Receta compost 3:1", relacion_seca=3, relacion_verde=1,
                    vigente=True)
            self._ok("Receta de mezcla vigente lista.")
        except Exception as e:  # noqa: BLE001
            self._warn(f"Receta: {e}")

        # --- M5: inventario por etapa ----------------------------------------
        try:
            from django.db import transaction
            from inventario import services as inv
            from inventario.models import Inventario
            if not Inventario.objects.exists():
                with transaction.atomic():
                    inv.ingresar(seca, Inventario.POR_TRITURAR, Decimal("60"))
                    inv.ingresar(verde, Inventario.POR_TRITURAR, Decimal("8"))
                    inv.ingresar(seca, Inventario.CHIP, Decimal("22"))
                    inv.ingresar(seca, Inventario.CURADO, Decimal("15"))
            self._ok("Inventario sembrado (por triturar / chip / curado).")
        except Exception as e:  # noqa: BLE001
            self._warn(f"Inventario: {e}")

        # --- M5: pilas con composicion ---------------------------------------
        try:
            from inventario.models import Pila, ComposicionPila
            if Pila.objects.count() < 2:
                p1 = Pila.objects.create(codigo=Pila.generar_codigo(),
                    fecha_inicio=date.today() - timedelta(days=20), estado=Pila.EN_FORMACION)
                ComposicionPila.objects.create(pila=p1, material=seca, volumen_m3=Decimal("18"))
                ComposicionPila.objects.create(pila=p1, material=verde, volumen_m3=Decimal("2"))
                p2 = Pila.objects.create(codigo=Pila.generar_codigo(),
                    fecha_inicio=date.today() - timedelta(days=55), estado=Pila.EN_PROCESO)
                ComposicionPila.objects.create(pila=p2, material=seca, volumen_m3=Decimal("24"))
                ComposicionPila.objects.create(pila=p2, material=verde, volumen_m3=Decimal("8"))
            self._ok("Pilas con composicion listas.")
        except Exception as e:  # noqa: BLE001
            self._warn(f"Pilas: {e}")

        # --- M6: calcular mezcla -> genera alerta de faltante ----------------
        try:
            from inventario.models import Pila
            from mezcla.services import calcular_mezcla
            for pila in Pila.objects.filter(estado=Pila.EN_FORMACION):
                calcular_mezcla(pila)
            self._ok("Mezcla calculada (alertas de faltante generadas).")
        except Exception as e:  # noqa: BLE001
            self._warn(f"Mezcla: {e}")

        # --- M11: maquinaria + mantencion vencida -> alerta ------------------
        try:
            from mantenimiento.models import Maquinaria, Mantencion
            from mantenimiento.services import revisar_alertas_mantenimiento
            m1, _ = Maquinaria.objects.get_or_create(nombre="Chipeadora Bandit 990",
                defaults={"tipo": "Chipeadora", "horometro": Decimal("1240")})
            Maquinaria.objects.get_or_create(nombre="Minicargador Bobcat S650",
                defaults={"tipo": "Minicargador", "horometro": Decimal("880")})
            if not Mantencion.objects.filter(maquinaria=m1).exists():
                Mantencion.objects.create(maquinaria=m1, tipo=Mantencion.PREVENTIVA,
                    criterio=Mantencion.POR_FECHA,
                    fecha_programada=date.today() - timedelta(days=3),
                    descripcion="Cambio de cuchillas y filtros", estado=Mantencion.PROGRAMADA)
                Mantencion.objects.create(maquinaria=m1, tipo=Mantencion.CORRECTIVA,
                    fecha_realizada=date.today() - timedelta(days=40), costo=Decimal("320000"),
                    descripcion="Reparacion de correa", falla="Correa cortada",
                    reparacion="Reemplazo de correa", estado=Mantencion.REALIZADA)
            revisar_alertas_mantenimiento()
            self._ok("Maquinaria + mantenciones listas (alerta de mantencion generada).")
        except Exception as e:  # noqa: BLE001
            self._warn(f"Mantenimiento: {e}")

        # --- M8: cotizacion, venta con detalle y cobro -----------------------
        try:
            from comercial.models import Cotizacion, Venta, DetalleVenta, Cobro
            from comercial.services import calcular_costo_cotizacion
            cliente = Cliente.objects.filter(razon_social="Vivero Los Aromos").first() \
                or Cliente.objects.first()
            if not Cotizacion.objects.exists():
                Cotizacion.objects.create(cliente=cliente, distancia_km=Decimal("35.5"),
                    servicio="Retiro y triturado de ramas en obra",
                    costo_estimado=calcular_costo_cotizacion(Decimal("35.5")))
            producto = Producto.objects.filter(precio__isnull=False).first()
            if producto and not Venta.objects.exists():
                precio = producto.precio
                cant = Decimal("120")
                venta = Venta.objects.create(cliente=cliente, estado=Venta.PENDIENTE,
                    total=precio * cant)
                DetalleVenta.objects.create(venta=venta, producto=producto, cantidad=cant,
                    unidad=producto.unidad_de_venta, precio_unitario=precio,
                    subtotal=precio * cant)
                Cobro.objects.create(venta=venta, cliente=cliente,
                    monto=(precio * cant) / 2, fecha=date.today(), medio="Transferencia")
            self._ok("Comercial listo (cotizacion, venta, cobro parcial).")
        except Exception as e:  # noqa: BLE001
            self._warn(f"Comercial: {e}")

        # --- M7: una proyeccion mensual guardada -----------------------------
        try:
            from proyecciones.models import Proyeccion
            if not Proyeccion.objects.exists():
                Proyeccion.objects.create(
                    tipo="mensual",
                    periodo_inicio=date.today().replace(day=1),
                    periodo_fin=date.today().replace(day=1) + timedelta(days=29),
                    supuestos={"volumen_m3": 800, "densidad_kg_m3": 250,
                               "factor_reduccion": 0.6, "sacos_por_m3": 25},
                    valor_proyectado={"compost_t": 480, "compost_m3": 320, "sacos": 8000},
                )
            self._ok("Proyeccion mensual guardada.")
        except Exception as e:  # noqa: BLE001
            self._warn(f"Proyeccion: {e}")

        # --- M12: documentos legales en los cuatro estados -------------------
        # Uno por estado para que el tablero de cumplimiento (CU-91) y la
        # bandeja de alertas muestren algo real en la demo. Las fechas se
        # calculan contra el umbral configurado, no fijas, para que el estado
        # derivado siga siendo el esperado aunque pase el tiempo.
        try:
            from django.core.files.base import ContentFile

            from documental.cumplimiento import revisar_vencimientos
            from documental.models import DocumentoLegal, VersionDocumento
            from documental.services import registrar_vigencia, umbral_dias

            if not DocumentoLegal.objects.exists():
                hoy = date.today()
                umbral = umbral_dias()
                documentos = [
                    ("Autorizacion sanitaria de la planta", DocumentoLegal.RESOLUCION,
                     "SEREMI de Salud", hoy + timedelta(days=umbral * 12)),
                    ("Seguro de responsabilidad civil", DocumentoLegal.SEGURO,
                     "Compania de Seguros", hoy + timedelta(days=max(umbral // 3, 1))),
                    ("Declaracion SINADER del periodo anterior", DocumentoLegal.CERTIFICADO,
                     "Ministerio del Medio Ambiente", hoy - timedelta(days=20)),
                    ("Patente comercial en tramite", DocumentoLegal.PERMISO,
                     "Municipalidad de Colina", None),
                ]
                for nombre, tipo, entidad, vencimiento in documentos:
                    documento = DocumentoLegal.objects.create(
                        nombre=nombre, tipo=tipo, entidad_emisora=entidad
                    )
                    VersionDocumento.objects.create(
                        documento=documento,
                        archivo=ContentFile(
                            b"%PDF-1.4 documento de demostracion",
                            name=f"{documento.pk}-v1.pdf",
                        ),
                        nombre_archivo=f"{nombre[:40]}.pdf",
                        version=1,
                        vigente=True,
                    )
                    if vencimiento:
                        registrar_vigencia(
                            documento, vencimiento - timedelta(days=365), vencimiento
                        )
            resumen = revisar_vencimientos()
            self._ok(
                "Documentos legales listos "
                f"(alertas de vencimiento: {resumen['alertas_creadas']})."
            )
        except Exception as e:  # noqa: BLE001
            self._warn(f"Documental: {e}")

        self._ok("seed_demo completado.")
