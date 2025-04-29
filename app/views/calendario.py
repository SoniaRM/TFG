from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, FileResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from datetime import datetime, timedelta, date
from itertools import combinations
import random
import io
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    ListFlowable
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from babel.dates import format_date

from ..models import Receta, TipoComida, Calendario, Calendario_Receta
from .lista_compra import generar_lista_compra
from django.contrib.auth.decorators import login_required

#CALENDARIO
@login_required
def calendario_semanal(request):
    """
    Muestra un calendario de 7 días (semana).
    Permite navegar entre semanas usando un parámetro GET 'start' en formato YYYY-MM-DD.
    """    
    familia = request.user.familias.first()  # Obtener la familia del usuario

    # 1) Leemos el parámetro GET 'start' que indicará el lunes (o día inicial) de la semana.
    start_date_str = request.GET.get('start', None)

    # 2) Si no hay parámetro o es inválido, tomamos el lunes de la semana actual.
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            # Si la cadena no es una fecha válida, fallback a la semana actual
            start_date = date.today() - timedelta(days=date.today().weekday())
    else:
        start_date = date.today() - timedelta(days=date.today().weekday())

    # 3) Generamos la lista de 7 días de la semana
    dias = [start_date + timedelta(days=i) for i in range(7)]
    dias_semana_es = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    dias_context = [(dia, dias_semana_es[dia.weekday()]) for dia in dias]

    # 4) Obtenemos todos los objetos Calendario que caigan en esos 7 días
    calendarios = Calendario.objects.filter(familia=familia, fecha__range=[dias[0], dias[-1]],) \
                                    .prefetch_related('calendario_recetas__receta',
                                                      'calendario_recetas__tipo_comida')

    # 5) Creamos un diccionario con la info de recetas para cada día
    dia_data = {d: [] for d in dias}
    for calendario in calendarios:
        for cr in calendario.calendario_recetas.all():
            dia_data[calendario.fecha].append(cr)

    # 6) Calculamos las fechas de la semana anterior y siguiente
    prev_week_date = start_date - timedelta(days=7)
    next_week_date = start_date + timedelta(days=7)

    # Lista de tipos de comida en orden
    meal_order = ["Desayuno", "Almuerzo", "Merienda", "Cena"]

    #Para los 4 cuadrados del calendario y que se puedan pinchar
    tipos_comida = TipoComida.objects.all()
    # Crea un diccionario {nombre: id} para facilitar la búsqueda en JS
    meal_mapping = {tc.nombre: tc.id for tc in tipos_comida}

    # 7) Pasamos al contexto la info necesaria
    context = {
        'dias': dias,
        'dia_data': dia_data,
        'prev_week_url': f'?start={prev_week_date}',  # Query string para ir a la semana anterior
        'next_week_url': f'?start={next_week_date}',  # Query string para ir a la semana siguiente
        'meal_order': meal_order,  # <-- Importante
        'meal_mapping': meal_mapping,  # Este diccionario se usará en JS
        'dias_context': dias_context,
    }
    print(context)

    return render(request, 'calendario/semanal.html', context)

#Añadir receta al calendario desde el calendario
#Filtrar las recetas por tipo Comida
PENALTY_BASE = 50   # Máxima penalización

def calcular_penalty(ingredientes, fecha_date, familia):
    """
    Penalización = PENALTY_BASE * (ingredientes_repetidos / total_ingredientes)
    """
    ings = list(ingredientes)
    total = len(ings)
    if total == 0:
        return 0

    # Contamos cuántos ingredientes están en su periodo de descanso
    repetidos = 0
    for ing in ings:
        inicio = fecha_date - timedelta(days=ing.frec)
        fin    = fecha_date + timedelta(days=ing.frec)
        if Calendario_Receta.objects.filter(
            calendario__fecha__gte=inicio,
            calendario__fecha__lt=fin,
            receta__ingredientes=ing,
            calendario__familia=familia
        ).exists():
            repetidos += 1

    return PENALTY_BASE * (repetidos / total)
    
@login_required
def recetas_por_tipo(request):
    """
    Devuelve las recetas disponibles (individuales y en pares) para agregar al calendario,
    excluyendo las que ya han sido añadidas en la fecha y tipo de comida seleccionados,
    y ordenándolas según un score que combina el ajuste proteico y la penalización por frecuencia.
    """
    familia = request.user.familias.first()
    tipo = request.GET.get("tipo")
    fecha = request.GET.get("fecha")
    limit  = int(request.GET.get("limit", 10))
    offset = int(request.GET.get("offset", 0))

    if not tipo or not fecha:
        return JsonResponse({"error": "Faltan parámetros."}, status=400)

    # 1. Recetas del tipo seleccionado, excluyendo las ya asignadas en esa fecha y comida

    # Obtener todas las recetas del tipo de comida seleccionado
    recetas_disponibles = Receta.objects.filter(familia=familia, tipo_comida__nombre=tipo).distinct()

    # Obtener las recetas que ya están en el calendario en esa fecha y tipo de comida
    recetas_ya_agregadas = Receta.objects.filter(
        recetas_calendario__calendario__fecha=fecha,
        recetas_calendario__tipo_comida__nombre=tipo,
        familia=familia  # Aseguramos que pertenezcan a la familia
    ).distinct()

    # Excluir las recetas ya añadidas
    recetas_filtradas = recetas_disponibles.exclude(id__in=recetas_ya_agregadas.values_list('id', flat=True))
    # 2. Calcular el saldo proteico para el día indicado

    calendario = Calendario.objects.filter(fecha=fecha, familia=familia).first()
    if calendario:
        objetivo_proteico = calendario.objetivo_proteico
        proteinas_consumidas = calendario.proteinas_consumidas
        objetivo_carbohidratos  = calendario.objetivo_carbohidratos
        carbohidratos_consumidos = calendario.carbohidratos_consumidos
    else:
        # Si no existe un calendario para ese día, usamos valores por defecto (por ejemplo, 100g de proteína)
        objetivo_proteico = 100
        proteinas_consumidas = 0
        objetivo_carbohidratos   = 250   # valor por defecto
        carbohidratos_consumidos = 0

    remaining_protein = objetivo_proteico - proteinas_consumidas
    remaining_carbs   = objetivo_carbohidratos - carbohidratos_consumidos

    # —— Reparto equitativo entre huecos libres ——
    meal_order = ["Desayuno", "Almuerzo", "Merienda", "Cena"]
    ocupados = set()
    if calendario:
        ocupados = { cr.tipo_comida.nombre for cr in calendario.calendario_recetas.all() }
    slots_libres = sum(1 for m in meal_order if m not in ocupados)
    if slots_libres > 0:
        target_protein = remaining_protein / slots_libres
        target_carbs   = remaining_carbs   / slots_libres
    else:
        target_protein = remaining_protein
        target_carbs   = remaining_carbs

    # 3. Parámetros y preparación
    PENALTY_PER_INGREDIENT = 50
    ##################################################
    
    recetas_con_score = []
    fecha_date = datetime.strptime(fecha, "%Y-%m-%d").date()
    recomendaciones = []  # Aquí almacenaremos tanto individuales como pares

    # 4. Evaluación individual (se calcula el score para cada receta)
    individual_scores = []  # lista de tuplas (total_score, receta)
    PESO_PROTEINA = 0.7
    PESO_CARBOHIDRATO = 0.3
    for receta in recetas_filtradas:
        protein_score = 100 - abs(target_protein - receta.proteinas)
        carb_score    = 100 - abs(target_carbs   - receta.carbohidratos)
        base_score    = (protein_score * PESO_PROTEINA) + (carb_score * PESO_CARBOHIDRATO)
        penalty     = calcular_penalty(receta.ingredientes.all(), fecha_date, familia)
        total_score   = base_score - penalty
        recomendaciones.append({
            "ids": [receta.id],
            "nombre": receta.nombre,
            "score": round(total_score, 2),
            "tipo": "single"
        })

    # 🔧 Filtrar solo las recetas combinables
    recetas_combinables = recetas_filtradas.filter(combinable=True)

    # 5. Para la generación de pares: si hay demasiadas recetas candidatas,
    # se selecciona un pool aleatorio (para incluir también recetas con menor score individual)
    MAX_POOL = 20  # Ajusta este número según tus necesidades
    pool_for_pairs = list(recetas_combinables)
    if len(pool_for_pairs) > MAX_POOL:
        pool_for_pairs = random.sample(pool_for_pairs, MAX_POOL)

    # 6. Evaluación de pares (se forman combinaciones del pool para pares)
    for rec1, rec2 in combinations(pool_for_pairs, 2):
        combined_protein = rec1.proteinas + rec2.proteinas
        combined_carbs    = rec1.carbohidratos + rec2.carbohidratos

        protein_score_pair = 100 - abs(target_protein - combined_protein)
        carb_score_pair    = 100 - abs(target_carbs           - combined_carbs)
        base_score_pair    = (protein_score_pair * PESO_PROTEINA) + (carb_score_pair * PESO_CARBOHIDRATO)
       
        # Unión de ingredientes en un set
        ings_pair = set(rec1.ingredientes.all()) | set(rec2.ingredientes.all())
        # pásalo directamente a la función
        penalty_pair     = calcular_penalty(ings_pair, fecha_date, familia)
        total_score_pair = base_score_pair - penalty_pair


        recomendaciones.append({
            "ids": [rec1.id, rec2.id],
            "nombre": f"{rec1.nombre} + {rec2.nombre}",
            "score": round(total_score_pair, 2),
            "tipo": "pair"
        })
    # 7. Una vez has llenado `recomendaciones` con todos los scores absolutos:
    # ------------------------------------------------------------
    # Si no hay ninguna recomendación, devolvemos lista vacía
    if not recomendaciones:
        return JsonResponse([], safe=False)

    # Extraemos todos los raw scores
    raw_scores = [item["score"] for item in recomendaciones]
    min_sc, max_sc = min(raw_scores), max(raw_scores)

    # Si solo hay una recomendación
    if len(recomendaciones) == 1:
        recomendaciones[0]["score"] = 100
    else:
        if max_sc == min_sc:
            # Todos iguales => damos 100% a todas
            for item in recomendaciones:
                item["score"] = 100
        else:
            # Normalización min-max
            for item in recomendaciones:
                raw = item["score"]
                item["score"] = round((raw - min_sc) / (max_sc - min_sc) * 100, 2)

    # Ordenamos y devolvemos
    recomendaciones.sort(key=lambda x: x["score"], reverse=True)
    paged = recomendaciones[offset:offset+limit]
    return JsonResponse(paged, safe=False)

@login_required
def agregar_receta_calendario(request):
    """Vista para agregar una receta a una fecha específica en el calendario."""
    if request.method == "POST":
        try:
            data = request.POST
            fecha = data.get("fecha")
            receta_id = data.get("receta_id")
            tipo_comida_id = data.get("tipo_comida_id")

            # Verifica que los datos sean válidos
            if not fecha or not receta_id or not tipo_comida_id:
                return JsonResponse({"error": "Faltan datos en la solicitud"}, status=400)

            familia = request.user.familias.first()

            # Obtener objetos desde la base de datos
            receta = get_object_or_404(Receta, id=receta_id, familia=familia)
            tipo_comida = get_object_or_404(TipoComida, id=tipo_comida_id)

            # Obtener o crear la instancia de calendario para esa fecha
            calendario, created = Calendario.objects.get_or_create(fecha=fecha, familia=familia)

            # Verificar si la receta ya está asignada para evitar duplicados
            if Calendario_Receta.objects.filter(calendario=calendario, receta=receta, tipo_comida=tipo_comida).exists():
                return JsonResponse({"error": "Esta receta ya está agregada en este día y tipo de comida."}, status=400)

            # Crear la relación en la tabla intermedia
            Calendario_Receta.objects.create(calendario=calendario, receta=receta, tipo_comida=tipo_comida)

            # 1) Obtener el lunes de la semana en la que se ha añadido la receta
            from datetime import datetime, timedelta
            fecha_date = datetime.strptime(fecha, "%Y-%m-%d").date()
            week_start = fecha_date - timedelta(days=fecha_date.weekday())
            try:
                # 2) Llamar a generar_lista_compra(week_start)
                generar_lista_compra(week_start, familia)
            except Exception as e:
                # opcional: loggea el error, pero no lo devuelvas al cliente
                print("⚠️ Error generando lista de compra:", e)
            return JsonResponse({"mensaje": "Receta agregada exitosamente."}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Método no permitido"}, status=405)

@login_required
def recetas_en_calendario(request):
    """Devuelve las recetas ya añadidas al calendario para un día y tipo de comida."""
    fecha = request.GET.get("fecha")
    tipo = request.GET.get("tipo")
    familia = request.user.familias.first()

    calendario = Calendario.objects.filter(fecha=fecha, familia=familia).first()
    if not calendario:
        return JsonResponse([], safe=False)

    recetas = Calendario_Receta.objects.filter(calendario=calendario, tipo_comida__nombre=tipo)
    data = [{"id": cr.receta.id, "nombre": cr.receta.nombre} for cr in recetas]
    return JsonResponse(data, safe=False)

@login_required
def eliminar_receta_calendario(request):
    """Elimina una receta del calendario."""
    if request.method == "POST":
        fecha = request.POST.get("fecha")
        receta_id = request.POST.get("receta_id")
        tipo_comida = request.POST.get("tipo_comida")  # Se espera que se envíe el nombre del tipo de comida

        if not fecha or not receta_id:
            return JsonResponse({"error": "Faltan parámetros."}, status=400)
        
        familia = request.user.familias.first()
        # Eliminar la receta de la fecha y tipo de comida correspondiente
        eliminados, _ = Calendario_Receta.objects.filter(
            calendario__fecha=fecha, calendario__familia=familia, receta__id=receta_id, tipo_comida__nombre=tipo_comida
        ).delete()

        # 1) Obtener el lunes de la semana
        from datetime import datetime, timedelta
        fecha_date = datetime.strptime(fecha, "%Y-%m-%d").date()
        week_start = fecha_date - timedelta(days=fecha_date.weekday())

        # 2) Llamar a generar_lista_compra(week_start)
        generar_lista_compra(week_start, familia)

        if eliminados:
            return JsonResponse({"mensaje": "Receta eliminada correctamente."}, status=200)
        else:
            return JsonResponse({"error": "No se encontró la receta en el calendario."}, status=404)

    return JsonResponse({"error": "Método no permitido"}, status=405)


@login_required
def actualizar_calendario_dia(request):
    """
    Devuelve las recetas actualizadas de un día específico en formato JSON.
    """
    fecha = request.GET.get("fecha")
    if not fecha:
        return JsonResponse({"error": "Fecha no proporcionada."}, status=400)
    
    familia = request.user.familias.first()
    calendario = Calendario.objects.filter(fecha=fecha, familia=familia).first()
    if not calendario:
        return JsonResponse({"recetas": {}}, status=200)

    recetas_por_tipo = {}
    for cr in Calendario_Receta.objects.filter(calendario=calendario):
        if cr.tipo_comida.nombre not in recetas_por_tipo:
            recetas_por_tipo[cr.tipo_comida.nombre] = []
        recetas_por_tipo[cr.tipo_comida.nombre].append(cr.receta.nombre)

    proteinas_consumidas = sum(cr.receta.proteinas for cr in Calendario_Receta.objects.filter(calendario=calendario))
    carbohidratos_consumidos  = sum(cr.receta.carbohidratos for cr in Calendario_Receta.objects.filter(calendario=calendario))

    return JsonResponse({"recetas": recetas_por_tipo,  
        "objetivo_proteico": calendario.objetivo_proteico,
        "proteinas_consumidas": proteinas_consumidas,
        "objetivo_carbohidratos":  calendario.objetivo_carbohidratos,
        "carbohidratos_consumidos": carbohidratos_consumidos
    })

#Para que el degradado de los dias del calendario se actualice solo
@require_GET
@login_required
def datos_dia(request, fecha):
    """
    Retorna en JSON los datos del día: proteínas consumidas y objetivo.
    La fecha se espera en formato YYYY-MM-DD.
    """
    from datetime import datetime
    try:
        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({'error': 'Fecha inválida'}, status=400)
    
    familia = request.user.familias.first()
    calendario, _ = Calendario.objects.get_or_create(fecha=fecha_obj, familia=familia, defaults={'objetivo_proteico': 100, 'objetivo_carbohidratos': 250})
    data = {
        'proteinas_consumidas': calendario.proteinas_consumidas,
        'objetivo_proteico': calendario.objetivo_proteico,
        'carbohidratos_consumidos': calendario.carbohidratos_consumidos,
        'objetivo_carbohidratos':   calendario.objetivo_carbohidratos,
    }
    return JsonResponse(data)

#Exportacion pdf de las recetas de la semana
#EXPORTACION
@login_required
def exportar_semana(request):
    import io
    from math import ceil
    from datetime import datetime, timedelta
    from babel.dates import format_date

    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    )
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    # 1) Obtener la fecha base
    start_str = request.GET.get('start')
    if start_str:
        try:
            input_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            input_date = datetime.today().date()
    else:
        input_date = datetime.today().date()

    # 2) Forzar que sea lunes
    start_date = input_date - timedelta(days=input_date.weekday())

    # Generar 7 días (lunes a domingo)
    dias = [start_date + timedelta(days=i) for i in range(7)]
    
    # Tipos de comida
    meal_order = ["Desayuno", "Almuerzo", "Merienda", "Cena"]

    familia = request.user.familias.first()
    # 3) Obtener los calendarios de la semana
    calendarios = {cal.fecha: cal for cal in Calendario.objects.filter(fecha__in=dias, familia=familia)}

    # 4) Construir la tabla principal (cabeceras de fechas y días)
    header_dates = [""] + [d.strftime("%d/%m") for d in dias]
    header_days = [""] + [format_date(d, format="EEEE", locale='es').capitalize() for d in dias]
    table_data = [header_dates, header_days]

    styles = getSampleStyleSheet()
    normal_style = styles['Normal']

    for meal in meal_order:
        row = [Paragraph(meal, normal_style)]
        for d in dias:
            cal = calendarios.get(d)
            cell_paragraph = Paragraph("", normal_style)
            if cal:
                recetas = [
                    cr.receta.nombre for cr in cal.calendario_recetas.all()
                    if cr.tipo_comida.nombre.lower() == meal.lower()
                ]
                if recetas:
                    combined_text = "<br/>".join(recetas)
                    cell_paragraph = Paragraph(combined_text, normal_style)
            row.append(cell_paragraph)
        table_data.append(row)

    # 5) Extraer recetas únicas e ingredientes para la lista de la compra
    unique_recipes = {}
    shopping_dict = {}
    for d in dias:
        cal = calendarios.get(d)
        if cal:
            for cr in cal.calendario_recetas.all():
                receta = cr.receta
                if receta.nombre not in unique_recipes:
                    ings = list(receta.ingredientes.values_list('nombre', flat=True))
                    unique_recipes[receta.nombre] = ings
                for ing in receta.ingredientes.all():
                    shopping_dict[ing.nombre] = shopping_dict.get(ing.nombre, 0) + 1

    # 5.1) Tabla de recetas (2 columnas: Receta / Ingrediente)
    recipes_table_data = [["Receta", "Ingrediente"]]
    for rec_name, ing_list in unique_recipes.items():
        ing_str = ", ".join(ing_list)
        recipes_table_data.append([rec_name, ing_str])

    # 6) Crear PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=40
    )

    # === Tabla de Recetas ===
    first_col_width = doc.width * 0.4
    second_col_width = doc.width * 0.55
    recipes_table_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),  # Alinear en la parte superior
    ])
    recipes_table = Table(recipes_table_data, colWidths=[first_col_width, second_col_width])
    recipes_table.setStyle(recipes_table_style)

    # === Dividir lista de la compra en 2 subtablas para colocar lado a lado ===
    shopping_data = [["Ingrediente", "Raciones"]]
    for ing_name in sorted(shopping_dict.keys()):
        shopping_data.append([ing_name, str(shopping_dict[ing_name])])

    total_items = len(shopping_data) - 1  # sin contar el header
    mitad = ceil(total_items / 2)
    left_table_data = [shopping_data[0]] + shopping_data[1 : 1 + mitad]
    right_table_data = [shopping_data[0]] + shopping_data[1 + mitad :]

    # Estilo para las subtablas
    shopping_table_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),  # Alinear parte superior
    ])

    # Ajustar anchos de columna para que quepan en medio doc.width cada una
    half_width = doc.width / 2
    left_subtable = Table(left_table_data, colWidths=[half_width * 0.6, half_width * 0.4])
    left_subtable.setStyle(shopping_table_style)
    right_subtable = Table(right_table_data, colWidths=[half_width * 0.6, half_width * 0.4])
    right_subtable.setStyle(shopping_table_style)

    # Contenedor con 2 columnas, cada una una subtabla
    container_table = Table(
        [[left_subtable, right_subtable]],
        colWidths=[half_width, half_width]
    )
    # Alineación vertical TOP en la tabla contenedora
    container_table_style = TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ])
    container_table.setStyle(container_table_style)

    # === Estilos para títulos y headings ===
    custom_title = ParagraphStyle('customTitle', parent=styles['Title'], alignment=1)
    custom_heading = ParagraphStyle('customHeading', parent=styles['Heading2'], alignment=1)

    # === Construir el contenido (elements) ===
    elements = []

    start_formatted = format_date(dias[0], format="d 'de' MMMM 'de' y", locale='es')
    end_formatted = format_date(dias[-1], format="d 'de' MMMM 'de' y", locale='es')
    elements.append(Paragraph("Recetas de la semana", custom_title))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(f"{start_formatted} al {end_formatted}", custom_heading))
    elements.append(Spacer(1, 20))

    # === Tabla principal (comidas por día) ===
    first_col_width = doc.width * 0.15
    other_cols_width = (doc.width - first_col_width) / len(dias)
    main_table_col_widths = [first_col_width] + [other_cols_width] * len(dias)

    main_table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('WORDWRAP', (0, 0), (-1, -1), True),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ])
    main_table = Table(table_data, colWidths=main_table_col_widths)
    main_table.setStyle(main_table_style)
    elements.append(main_table)
    elements.append(Spacer(1, 20))

    # === Tabla de recetas
    elements.append(Paragraph("Recetas:", custom_heading))
    elements.append(Spacer(1, 10))
    elements.append(recipes_table)
    elements.append(Spacer(1, 20))

    # === Lista de la compra (dos subtablas lado a lado)
    elements.append(Paragraph("Lista de la compra:", custom_heading))
    elements.append(Spacer(1, 10))
    elements.append(container_table)
    elements.append(Spacer(1, 20))

    # === Generar PDF
    doc.build(elements)
    buffer.seek(0)
    start_day = dias[0].day
    end_day = dias[-1].day
    month_text = format_date(dias[0], format="MMMM", locale='es').lower()
    file_name = f"recetas_semana_{start_day}-{end_day}_{month_text}.pdf"

    return FileResponse(buffer, as_attachment=True, filename=file_name)