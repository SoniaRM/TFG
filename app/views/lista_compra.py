from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, FileResponse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt

from datetime import datetime, timedelta
import json

from babel.dates import format_date

from ..models import ListaCompra, ListaCompraItem, Calendario
from ..models import Ingrediente 
#Exportacion
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
from django.utils import timezone
from django.contrib.auth.decorators import login_required

#LISTA COMPRA
@login_required
def vista_lista_compra(request):
    familia = request.user.familias.first()
    start_str = request.GET.get('start')
    if start_str:
        try:
            input_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        except ValueError:
            input_date = now().date()
    else:
        input_date = now().date()

    start_date = input_date - timedelta(days=input_date.weekday())
    dias = [start_date + timedelta(days=i) for i in range(7)]

    lista_compra_obj, _ = ListaCompra.objects.get_or_create(start_date=start_date, familia=familia)

    items = lista_compra_obj.items.select_related('ingrediente')
    ingredientes_por_comprar = []
    ingredientes_en_despensa = []

    for item in items:
        if item.compra > 0:
            ingredientes_por_comprar.append(item)
        if item.despensa > 0:
            item.faltan = item.original - item.despensa
            if item.faltan < 0:
                item.faltan = 0
            ingredientes_en_despensa.append(item)
    ingredientes_por_comprar.sort(key=lambda x: x.ingrediente.nombre.lower())
    ingredientes_en_despensa.sort(key=lambda x: x.ingrediente.nombre.lower())

    from babel.dates import format_date
    semana_formateada = f"{dias[0].day}-{dias[-1].day} de {format_date(dias[0], format='MMMM yyyy', locale='es')}"

    prev_week_date = start_date - timedelta(days=7)
    next_week_date = start_date + timedelta(days=7)

    context = {
        'start_date': start_date,
        'semana_formateada': semana_formateada,
        'prev_week_url': f'?start={prev_week_date.isoformat()}',
        'next_week_url': f'?start={next_week_date.isoformat()}',
        'ingredientes_por_comprar': ingredientes_por_comprar,
        'ingredientes_en_despensa': ingredientes_en_despensa,
    }
    return render(request, 'lista_compra.html', context)

@login_required
def mover_compra_despensa(request):
    if request.method == 'POST':
        lista_id = request.POST.get('lista_id')
        item_id = request.POST.get('item_id')
        raciones = int(request.POST.get('raciones', 0))
        item = get_object_or_404(ListaCompraItem, id=item_id, lista_id=lista_id)
        familia = request.user.familias.first()
        if item.lista.familia != familia:
            return JsonResponse({'error': 'No tienes permiso para modificar este elemento.'}, status=403)
        
        nuevo_despensa = item.despensa + raciones
        if nuevo_despensa > item.original:
            nuevo_despensa = item.original
        item.despensa = nuevo_despensa
        item.compra = item.original - nuevo_despensa
        item.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required
def mover_despensa_compra(request):
    if request.method == 'POST':
        lista_id = request.POST.get('lista_id')
        item_id = request.POST.get('item_id')
        raciones = int(request.POST.get('raciones', 0))
        item = get_object_or_404(ListaCompraItem, id=item_id, lista_id=lista_id)
        familia = request.user.familias.first()
        if item.lista.familia != familia:
            return JsonResponse({'error': 'No tienes permiso para modificar este elemento.'}, status=403)
        
        nuevo_despensa = item.despensa - raciones
        if nuevo_despensa < 0:
            nuevo_despensa = 0
        item.despensa = nuevo_despensa
        item.compra = item.original - nuevo_despensa
        item.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required
def lista_compra_datos(request):
    start_str = request.GET.get('start')
    if start_str:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
    else:
        start_date = now().date() - timedelta(days=now().date().weekday())
    
    familia = request.user.familias.first()
    lista_compra_obj = get_object_or_404(ListaCompra, start_date=start_date, familia=familia)
    items = lista_compra_obj.items.select_related('ingrediente')

    por_comprar = []
    en_despensa = []
    for it in items:
        if it.compra > 0:
            por_comprar.append({
                'item_id': it.id,
                'lista_id': it.lista.id,
                'ingrediente': it.ingrediente.nombre,
                'compra': it.compra,
                'original': it.original,
            })
        if it.despensa > 0:
            en_despensa.append({
                'item_id': it.id,
                'lista_id': it.lista.id,
                'ingrediente': it.ingrediente.nombre,
                'despensa': it.despensa,
                'original': it.original,
                'faltan': max(0, it.original - it.despensa)
            })

    return JsonResponse({
        'por_comprar': por_comprar,
        'en_despensa': en_despensa,
    })


def generar_lista_compra(week_start, familia):
    """
    Recalcula la lista de la compra para la semana que inicia en week_start.
    Cada asignación de receta suma 1 para cada ingrediente de la receta.
    Se actualizan los items existentes preservando la cantidad en despensa,
    de modo que:
      compra = (nuevo total) – despensa,
      y si la despensa supera el nuevo total se ajusta a éste.
    """
    if familia is None:
        raise PermissionDenied("Debes iniciar sesión para generar la lista de compra.")
        
    end_date = week_start + timedelta(days=6)

    lista, created = ListaCompra.objects.get_or_create(start_date=week_start, familia=familia)

    calendarios = Calendario.objects.filter(fecha__range=(week_start, end_date), familia=familia) \
                                    .prefetch_related('calendario_recetas__receta__ingredientes')

    nuevos_totales = {}
    for cal in calendarios:
        for cr in cal.calendario_recetas.all():
            for ing in cr.receta.ingredientes.all():
                nuevos_totales[ing.id] = nuevos_totales.get(ing.id, 0) + 1

    items_existentes = { item.ingrediente.id: item for item in lista.items.all() }

    for ing_id, item in items_existentes.items():
        if ing_id in nuevos_totales:
            nuevo_total = nuevos_totales[ing_id]
            if item.despensa > nuevo_total:
                item.despensa = nuevo_total
            item.original = nuevo_total
            item.compra = nuevo_total - item.despensa
            item.save()
            del nuevos_totales[ing_id]
        else:
            item.delete()

    for ing_id, total in nuevos_totales.items():
        try:
            ing_obj = Ingrediente.objects.get(pk=ing_id)
        except Ingrediente.DoesNotExist:
            continue

        item, created = ListaCompraItem.objects.get_or_create(
            lista=lista,
            ingrediente=ing_obj,
            defaults={
                'original': total,
                'compra': total,
                'despensa': 0
            }
        )
        if not created:
            item.original = total
            item.compra = item.original - item.despensa
            item.save()

    return lista

@csrf_exempt
@login_required
def finalizar_compra(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        items = data.get('items', [])
        start_str = data.get('start')

        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        except:
            return JsonResponse({"error": "Fecha inválida"}, status=400)

        familia = request.user.familias.first()
        lista = ListaCompra.objects.get(start_date=start_date, familia=familia)

        for item_info in items:
            item_id = item_info.get('item_id')
            cantidad_str = item_info.get('cantidad', '0')
            cantidad = int(cantidad_str)
            try:
                lci = ListaCompraItem.objects.get(id=item_id, lista=lista)
                nuevo_despensa = lci.despensa + cantidad
                if nuevo_despensa > lci.original:
                    nuevo_despensa = lci.original
                lci.despensa = nuevo_despensa
                lci.compra = lci.original - nuevo_despensa
                lci.save()
            except ListaCompraItem.DoesNotExist:
                continue
        
        return JsonResponse({"mensaje": "Compra realizada correctamente."})
    return JsonResponse({"error": "Método no permitido"}, status=405)


@csrf_exempt
@login_required
def resetear_lista_compra(request):
    if request.method == "POST":
        start_str = request.GET.get('start')
        if start_str:
            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({"error": "Fecha inválida"}, status=400)
        else:
            start_date = now().date() - timedelta(days=now().date().weekday())
        
        familia = request.user.familias.first()
        try:
            lista = ListaCompra.objects.get(start_date=start_date, familia=familia)
        except ListaCompra.DoesNotExist:
            return JsonResponse({"error": "Lista de compra no encontrada para la fecha especificada."}, status=404)
        
        for item in lista.items.all():
            item.despensa = 0
            item.compra = item.original
            item.save()
        
        return JsonResponse({"mensaje": "Lista de compra reiniciada correctamente."})
    
    return JsonResponse({"error": "Método no permitido"}, status=405)

@login_required
def exportar_lista_compra(request):
    """
    Exporta un PDF con la lista de la compra.
    Se espera un parámetro GET 'start' con la fecha de inicio de la semana (YYYY-MM-DD).
    El PDF incluirá una tabla con los ingredientes a comprar (donde compra > 0) y las raciones correspondientes.
    """
    start_str = request.GET.get('start')
    if start_str:
        try:
            input_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            input_date = timezone.now().date()
    else:
        input_date = timezone.now().date()

    start_date = input_date - timedelta(days=input_date.weekday())
    end_date = start_date + timedelta(days=6)
    familia = request.user.familias.first()
    lista_compra, created = ListaCompra.objects.get_or_create(start_date=start_date, familia=familia)

    items_por_comprar = lista_compra.items.filter(compra__gt=0)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=40, leftMargin=40, topMargin=60, bottomMargin=40)

    styles = getSampleStyleSheet()
    custom_title = ParagraphStyle('customTitle', parent=styles['Title'], alignment=1)
    custom_heading = ParagraphStyle('customHeading', parent=styles['Heading2'], alignment=1)

    elements = []
    week_start_text = format_date(start_date, format="d 'de' MMMM 'de' y", locale='es')
    week_end_text = format_date(end_date, format="d 'de' MMMM 'de' y", locale='es')
    week_text = f"Semana del {week_start_text} al {week_end_text}"

    elements.append(Paragraph("Lista de la compra", custom_title))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(week_text, custom_heading))
    elements.append(Spacer(1, 20))

    shopping_data = [["Ingrediente", "Raciones"]]
    if items_por_comprar.exists():
        for item in items_por_comprar:
            shopping_data.append([item.ingrediente.nombre, str(item.compra)])
    else:
        shopping_data.append(["No hay ingredientes pendientes", ""])
    
    col_widths = [doc.width * 0.3, doc.width * 0.2]
    table_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ])

    shopping_table = Table(shopping_data, colWidths=col_widths)
    shopping_table.setStyle(table_style)
    elements.append(shopping_table)
    elements.append(Spacer(1, 20))

    doc.build(elements)
    buffer.seek(0)
    start_day = start_date.day
    end_day = end_date.day
    month_text = format_date(start_date, format="MMMM", locale='es').lower()
    file_name = f"lista_compra_{start_day}-{end_day}_{month_text}.pdf"
    
    return FileResponse(buffer, as_attachment=True, filename=file_name)