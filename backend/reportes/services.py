"""Agregaciones y exportacion de reportes (CU-73 a CU-76)."""

import csv
import io
from collections import defaultdict
from decimal import Decimal
from xml.sax.saxutils import escape

from django.db.models import Prefetch
from django.http import HttpResponse
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from comercial.models import Cobro, Venta
from inventario.models import Inventario, Pila, ProcesoPila
from mantenedores.models import Cliente, Material
from recepcion.models import DetalleRecepcion, Recepcion

from .models import Reporte


def _numero(valor):
    """Convierte decimales del ORM a numeros serializables por JSON."""
    return float(valor or Decimal("0"))


def _reporte_recepciones(inicio, fin, filtros):
    """CU-73: agrega volumen y peso por material y por cliente.

    Solo cuentan las descargas recibidas: una rechazada o aun en curso no
    ingreso material a la planta (mismo criterio que los certificados del M9).
    """
    detalles = DetalleRecepcion.objects.select_related(
        "recepcion__cliente", "material"
    ).filter(
        recepcion__fecha__range=(inicio, fin),
        recepcion__estado=Recepcion.RECIBIDA,
    )
    if filtros.get("cliente"):
        detalles = detalles.filter(recepcion__cliente_id=filtros["cliente"])
    if filtros.get("material"):
        detalles = detalles.filter(material_id=filtros["material"])

    por_material = defaultdict(lambda: {"volumen_m3": Decimal("0"), "peso_kg": Decimal("0")})
    por_cliente = defaultdict(lambda: {"volumen_m3": Decimal("0"), "peso_kg": Decimal("0")})
    for detalle in detalles:
        material = (detalle.material_id, detalle.material.nombre)
        cliente = (detalle.recepcion.cliente_id, detalle.recepcion.cliente.razon_social)
        for grupo, clave in ((por_material, material), (por_cliente, cliente)):
            grupo[clave]["volumen_m3"] += detalle.volumen_m3
            grupo[clave]["peso_kg"] += detalle.peso_derivado_kg

    def filas(grupo, id_clave, nombre_clave):
        return [
            {
                id_clave: clave[0],
                nombre_clave: clave[1],
                "volumen_m3": _numero(valores["volumen_m3"]),
                "peso_kg": _numero(valores["peso_kg"]),
            }
            for clave, valores in sorted(grupo.items(), key=lambda item: item[0][1])
        ]

    total_volumen = sum((v["volumen_m3"] for v in por_material.values()), Decimal("0"))
    total_peso = sum((v["peso_kg"] for v in por_material.values()), Decimal("0"))
    # Se guardan los filtros por nombre: al exportar, el documento debe decir
    # que el total corresponde a un cliente o material y no a toda la planta.
    aplicados = {}
    if filtros.get("cliente"):
        cliente = Cliente.objects.filter(pk=filtros["cliente"]).first()
        aplicados["cliente"] = cliente.razon_social if cliente else str(filtros["cliente"])
    if filtros.get("material"):
        material = Material.objects.filter(pk=filtros["material"]).first()
        aplicados["material"] = material.nombre if material else str(filtros["material"])
    return {
        "filtros": aplicados,
        "totales": {"volumen_m3": _numero(total_volumen), "peso_kg": _numero(total_peso)},
        "por_material": filas(por_material, "material", "material_nombre"),
        "por_cliente": filas(por_cliente, "cliente", "cliente_nombre"),
    }


def _reporte_produccion(inicio, fin):
    """CU-74: separa lo procesado, lo que sigue en curso y el inventario."""
    procesos = ProcesoPila.objects.select_related("material", "pila").prefetch_related(
        "pila__composiciones__material"
    ).filter(
        fecha__date__range=(inicio, fin)
    )
    procesado = defaultdict(Decimal)
    en_curso = defaultdict(Decimal)
    for proceso in procesos:
        volumen = proceso.volumen_m3 or Decimal("0")
        composiciones = list(proceso.pila.composiciones.all()) if proceso.pila_id and not proceso.material_id else []
        if composiciones:
            total_composicion = sum((composicion.volumen_m3 for composicion in composiciones), Decimal("0"))
            distribucion = [
                (composicion.material_id, composicion.material.nombre,
                 volumen * composicion.volumen_m3 / total_composicion)
                for composicion in composiciones
            ] if total_composicion else []
        else:
            distribucion = [(proceso.material_id, proceso.material.nombre if proceso.material_id else "Pila", volumen)]
        for material_id, nombre, volumen_material in distribucion:
            clave = (material_id, nombre)
            if proceso.pila_id and proceso.pila.estado == Pila.EN_PROCESO:
                en_curso[clave] += volumen_material
            else:
                procesado[clave] += volumen_material

    inventario = defaultdict(Decimal)
    for existencia in Inventario.objects.select_related("material"):
        inventario[(existencia.material_id, existencia.material.nombre)] += existencia.volumen_m3
    claves = set(procesado) | set(en_curso) | set(inventario)
    detalle = [
        {
            "material": clave[0],
            "material_nombre": clave[1],
            "procesado_m3": _numero(procesado[clave]),
            "en_curso_m3": _numero(en_curso[clave]),
            "inventario_resultante_m3": _numero(inventario[clave]),
        }
        for clave in sorted(claves, key=lambda item: item[1])
    ]
    return {
        "totales": {
            "procesado_m3": sum(fila["procesado_m3"] for fila in detalle),
            "en_curso_m3": sum(fila["en_curso_m3"] for fila in detalle),
        },
        "por_material": detalle,
    }


def _reporte_ventas_cobros(inicio, fin):
    """CU-75: reparte cobros de cada venta entre sus lineas proporcionalmente."""
    cobros_periodo = Cobro.objects.filter(fecha__range=(inicio, fin))
    ventas = Venta.objects.select_related("cliente").prefetch_related(
        "detalles", Prefetch("cobros", queryset=cobros_periodo)
    ).filter(
        fecha__range=(inicio, fin)
    )
    por_cliente = defaultdict(lambda: {"vendido": Decimal("0"), "cobrado": Decimal("0")})
    por_producto = defaultdict(lambda: {"vendido": Decimal("0"), "cobrado": Decimal("0")})
    for venta in ventas:
        cobrado = sum((cobro.monto for cobro in venta.cobros.all()), Decimal("0"))
        total = venta.total or sum((detalle.subtotal for detalle in venta.detalles.all()), Decimal("0"))
        detalles = list(venta.detalles.all())
        for detalle in detalles:
            proporcion = detalle.subtotal / total if total else Decimal("0")
            monto_cobrado = cobrado * proporcion
            cliente = (venta.cliente_id, venta.cliente.razon_social)
            producto = (detalle.producto_id, detalle.producto.nombre)
            por_cliente[cliente]["vendido"] += detalle.subtotal
            por_cliente[cliente]["cobrado"] += monto_cobrado
            por_producto[producto]["vendido"] += detalle.subtotal
            por_producto[producto]["cobrado"] += monto_cobrado

    def filas(grupo, id_clave, nombre_clave):
        return [
            {
                id_clave: clave[0],
                nombre_clave: clave[1],
                "vendido": _numero(valores["vendido"]),
                "cobrado": _numero(valores["cobrado"]),
                "pendiente": _numero(valores["vendido"] - valores["cobrado"]),
            }
            for clave, valores in sorted(grupo.items(), key=lambda item: item[0][1])
        ]

    clientes = filas(por_cliente, "cliente", "cliente_nombre")
    productos = filas(por_producto, "producto", "producto_nombre")
    return {
        "totales": {
            "vendido": sum(fila["vendido"] for fila in clientes),
            "cobrado": sum(fila["cobrado"] for fila in clientes),
            "pendiente": sum(fila["pendiente"] for fila in clientes),
        },
        "por_cliente": clientes,
        "por_producto": productos,
    }


def generar_reporte(tipo, inicio, fin, usuario, formato=Reporte.PDF, filtros=None):
    """Genera y guarda el resultado agregado correspondiente al tipo solicitado."""
    filtros = filtros or {}
    generadores = {
        Reporte.RECEPCIONES: _reporte_recepciones,
        Reporte.PRODUCCION: _reporte_produccion,
        Reporte.VENTAS_COBROS: _reporte_ventas_cobros,
    }
    if tipo == Reporte.RECEPCIONES:
        contenido = generadores[tipo](inicio, fin, filtros)
    else:
        contenido = generadores[tipo](inicio, fin)
    return Reporte.objects.create(
        tipo=tipo,
        periodo_inicio=inicio,
        periodo_fin=fin,
        formato=formato,
        usuario=usuario,
        contenido=contenido,
    )


def exportar_reporte(reporte, formato=None):
    """CU-76: transforma el contenido guardado en un archivo descargable.

    `formato` permite exportar un reporte ya generado en otro formato sin
    recalcularlo; por defecto usa el que se eligio al generarlo.
    """
    contenido = reporte.contenido
    formato = formato or reporte.formato
    filtros = [f"{clave}: {valor}" for clave, valor in contenido.get("filtros", {}).items()]
    if formato == Reporte.CSV:
        salida = io.StringIO()
        writer = csv.writer(salida)
        writer.writerow(["reporte", reporte.get_tipo_display()])
        writer.writerow(["periodo_inicio", reporte.periodo_inicio])
        writer.writerow(["periodo_fin", reporte.periodo_fin])
        if filtros:
            writer.writerow(["filtros", "; ".join(filtros)])
        writer.writerow([])
        for seccion, filas in contenido.items():
            if not isinstance(filas, list):
                continue
            writer.writerow([seccion])
            if filas:
                writer.writerow(list(filas[0].keys()))
                writer.writerows([fila.values() for fila in filas])
        # Con BOM para que Excel abra bien las tildes y la enie de los nombres.
        response = HttpResponse(
            salida.getvalue().encode("utf-8-sig"), content_type="text/csv; charset=utf-8"
        )
        extension = "csv"
    elif formato == Reporte.EXCEL:
        libro = Workbook()
        hoja = libro.active
        hoja.title = "Reporte"
        hoja.append(["Reporte", reporte.get_tipo_display()])
        hoja.append(["Periodo inicio", str(reporte.periodo_inicio)])
        hoja.append(["Periodo fin", str(reporte.periodo_fin)])
        if filtros:
            hoja.append(["Filtros", "; ".join(filtros)])
        hoja.append([])
        for seccion, filas in contenido.items():
            if not isinstance(filas, list):
                continue
            hoja.append([seccion])
            if filas:
                hoja.append(list(filas[0].keys()))
                for fila in filas:
                    hoja.append(list(fila.values()))
            hoja.append([])
        salida = io.BytesIO()
        libro.save(salida)
        response = HttpResponse(
            salida.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        extension = "xlsx"
    else:
        salida = io.BytesIO()
        documento = SimpleDocTemplate(
            salida, pagesize=letter, rightMargin=0.5 * inch,
            leftMargin=0.5 * inch, topMargin=0.5 * inch, bottomMargin=0.5 * inch,
        )
        estilos = getSampleStyleSheet()
        estilos.add(ParagraphStyle(
            name="ReporteTitulo", parent=estilos["Title"], fontName="Helvetica-Bold",
            fontSize=20, leading=24, textColor=colors.HexColor("#2E5E2A"),
            spaceAfter=6,
        ))
        estilos.add(ParagraphStyle(
            name="ReporteSeccion", parent=estilos["Heading2"], fontName="Helvetica-Bold",
            fontSize=12, leading=15, textColor=colors.HexColor("#2E5E2A"),
            spaceBefore=10, spaceAfter=6,
        ))
        estilos.add(ParagraphStyle(
            name="ReporteMeta", parent=estilos["Normal"], fontSize=9,
            textColor=colors.HexColor("#5D6B63"),
        ))
        elementos = [
            Paragraph(f"Triverde · {reporte.get_tipo_display()}", estilos["ReporteTitulo"]),
            Paragraph(
                f"Periodo: {reporte.periodo_inicio} a {reporte.periodo_fin}",
                estilos["ReporteMeta"],
            ),
        ]
        if filtros:
            # Paragraph interpreta marcado: se escapa por si un nombre trae "&".
            elementos.append(Paragraph(escape("Filtros: " + "; ".join(filtros)), estilos["ReporteMeta"]))
        elementos.append(Spacer(1, 0.2 * inch))
        totales = contenido.get("totales", {})
        if totales:
            resumen = [[clave.replace("_", " ").title(), str(valor)] for clave, valor in totales.items()]
            tabla_resumen = Table([["Resumen", "Valor"]] + resumen, colWidths=[2.8 * inch, 1.4 * inch])
            tabla_resumen.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E5E2A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F4F8F2"), colors.white]),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#9CC49A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D7E5D4")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            elementos.extend([tabla_resumen, Spacer(1, 0.15 * inch)])
        for seccion, filas in contenido.items():
            if isinstance(filas, list):
                elementos.append(Paragraph(seccion.replace("_", " ").title(), estilos["ReporteSeccion"]))
                if filas:
                    encabezados = list(filas[0].keys())
                    datos = [encabezados] + [[str(fila.get(clave, "")) for clave in encabezados] for fila in filas]
                    tabla = Table(datos, repeatRows=1)
                    tabla.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E5E2A")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F4F8F2"), colors.white]),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#9CC49A")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D7E5D4")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ]))
                    elementos.append(tabla)
                else:
                    elementos.append(Paragraph("Sin actividad en el periodo.", estilos["Normal"]))
                elementos.append(Spacer(1, 0.15 * inch))
        def pie_pagina(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#718078"))
            canvas.drawString(0.5 * inch, 0.3 * inch, "Triverde · Reporte generado por el sistema")
            canvas.drawRightString(7.9 * inch, 0.3 * inch, f"Pagina {doc.page}")
            canvas.restoreState()

        documento.build(elementos, onFirstPage=pie_pagina, onLaterPages=pie_pagina)
        response = HttpResponse(salida.getvalue(), content_type="application/pdf")
        extension = "pdf"
    response["Content-Disposition"] = f'attachment; filename="reporte-{reporte.pk}.{extension}"'
    return response
