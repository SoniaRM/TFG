from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt

from datetime import datetime, timedelta
import json

from babel.dates import format_date

from ..models import ListaCompra, ListaCompraItem, Calendario
from ..models import Ingrediente  # si lo necesitas para crear nuevos items

#LISTA COMPRA
def vista_lista_compra(request):
    # 1) Determinamos la semana
    start_str = request.GET.get('start')
    if start_str:
        try:
            input_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        except ValueError:
            input_date = now().date()
    else:
        input_date = now().date()

    # Forzamos a lunes
    start_date = input_date - timedelta(days=input_date.weekday())
    dias = [start_date + timedelta(days=i) for i in range(7)]

    # 2) Obtenemos (o creamos) la ListaCompra para esa semana
    lista_compra_obj, _ = ListaCompra.objects.get_or_create(start_date=start_date)

    # 3) Obtenemos todos los items y separamos en:
    #    - ingredientes por comprar (compra>0)
    #    - ingredientes en despensa (despensa>0)
    items = lista_compra_obj.items.select_related('ingrediente')
    ingredientes_por_comprar = []
    ingredientes_en_despensa = []

    for item in items:
        if item.compra > 0:
            ingredientes_por_comprar.append(item)
        if item.despensa > 0:
            item.faltan = item.original - item.despensa
            # Si por alguna razón faltan es negativo, lo ajustamos a 0
            if item.faltan < 0:
                item.faltan = 0
            ingredientes_en_despensa.append(item)


    # 4) Formateamos la semana (ej: "17-23 de marzo 2025")
    from babel.dates import format_date
    semana_formateada = f"{dias[0].day}-{dias[-1].day} de {format_date(dias[0], format='MMMM yyyy', locale='es')}"

    # 5) Calculamos URLs para anterior y siguiente semana
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


def mover_compra_despensa(request):
    if request.method == 'POST':
        lista_id = request.POST.get('lista_id')
        item_id = request.POST.get('item_id')
        raciones = int(request.POST.get('raciones', 0))
        item = get_object_or_404(ListaCompraItem, id=item_id, lista_id=lista_id)
        # Recalcular: Aumentar despensa y ajustar compra según el valor original.
        nuevo_despensa = item.despensa + raciones
        # No puede superar el total original:
        if nuevo_despensa > item.original:
            nuevo_despensa = item.original
        item.despensa = nuevo_despensa
        item.compra = item.original - nuevo_despensa
        item.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def mover_despensa_compra(request):
    if request.method == 'POST':
        lista_id = request.POST.get('lista_id')
        item_id = request.POST.get('item_id')
        raciones = int(request.POST.get('raciones', 0))
        item = get_object_or_404(ListaCompraItem, id=item_id, lista_id=lista_id)
        # Recalcular: Disminuir despensa y ajustar compra.
        nuevo_despensa = item.despensa - raciones
        if nuevo_despensa < 0:
            nuevo_despensa = 0
        item.despensa = nuevo_despensa
        item.compra = item.original - nuevo_despensa
        item.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def lista_compra_datos(request):
    start_str = request.GET.get('start')
    if start_str:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
    else:
        start_date = now().date() - timedelta(days=now().date().weekday())

    lista_compra_obj = get_object_or_404(ListaCompra, start_date=start_date)
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


def generar_lista_compra(week_start):
    """
    Recalcula la lista de la compra para la semana que inicia en week_start.
    Cada asignación de receta suma 1 para cada ingrediente de la receta.
    Se actualizan los items existentes preservando la cantidad en despensa,
    de modo que:
      compra = (nuevo total) – despensa,
      y si la despensa supera el nuevo total se ajusta a éste.
    """
    end_date = week_start + timedelta(days=6)

    # Obtén (o crea) la ListaCompra para esa semana
    lista, created = ListaCompra.objects.get_or_create(start_date=week_start)

    # Calcula los nuevos totales a partir del calendario
    calendarios = Calendario.objects.filter(fecha__range=(week_start, end_date)) \
                                    .prefetch_related('calendario_recetas__receta__ingredientes')

    nuevos_totales = {}
    for cal in calendarios:
        for cr in cal.calendario_recetas.all():
            for ing in cr.receta.ingredientes.all():
                nuevos_totales[ing.id] = nuevos_totales.get(ing.id, 0) + 1

    # Obtenemos los items existentes usando el ID del ingrediente
    items_existentes = { item.ingrediente.id: item for item in lista.items.all() }

    # Actualizamos o eliminamos los items existentes
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

    # Para los ingredientes nuevos, usamos get_or_create por seguridad extra
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

        lista = ListaCompra.objects.get(start_date=start_date)

        for item_info in items:
            item_id = item_info.get('item_id')
            cantidad_str = item_info.get('cantidad', '0')
            cantidad = int(cantidad_str)
            # Buscamos el ListaCompraItem
            try:
                lci = ListaCompraItem.objects.get(id=item_id, lista=lista)
                # Aumentamos la despensa
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
def resetear_lista_compra(request):
    if request.method == "POST":
        # Obtener la fecha de inicio de la semana (parámetro 'start')
        start_str = request.GET.get('start')
        if start_str:
            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({"error": "Fecha inválida"}, status=400)
        else:
            # Si no se proporciona, tomar el lunes de la semana actual
            start_date = now().date() - timedelta(days=now().date().weekday())
        
        try:
            lista = ListaCompra.objects.get(start_date=start_date)
        except ListaCompra.DoesNotExist:
            return JsonResponse({"error": "Lista de compra no encontrada para la fecha especificada."}, status=404)
        
        # Reiniciar cada item: despensa a 0 y compra igual al valor original
        for item in lista.items.all():
            item.despensa = 0
            item.compra = item.original
            item.save()
        
        return JsonResponse({"mensaje": "Lista de compra reiniciada correctamente."})
    
    return JsonResponse({"error": "Método no permitido"}, status=405)
