from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
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

#CALENDARIO
def calendario_semanal(request):
    """
    Muestra un calendario de 7 días (semana).
    Permite navegar entre semanas usando un parámetro GET 'start' en formato YYYY-MM-DD.
    """
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
    calendarios = Calendario.objects.filter(fecha__range=[dias[0], dias[-1]]) \
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

@csrf_exempt
def recetas_por_tipo(request):
    """
    Devuelve las recetas disponibles (individuales y en pares) para agregar al calendario,
    excluyendo las que ya han sido añadidas en la fecha y tipo de comida seleccionados,
    y ordenándolas según un score que combina el ajuste proteico y la penalización por frecuencia.
    """
    tipo = request.GET.get("tipo")
    fecha = request.GET.get("fecha")

    if not tipo or not fecha:
        return JsonResponse({"error": "Faltan parámetros."}, status=400)

    # 1. Recetas del tipo seleccionado, excluyendo las ya asignadas en esa fecha y comida

    # Obtener todas las recetas del tipo de comida seleccionado
    recetas_disponibles = Receta.objects.filter(tipo_comida__nombre=tipo).distinct()

    # Obtener las recetas que ya están en el calendario en esa fecha y tipo de comida
    recetas_ya_agregadas = Receta.objects.filter(
        recetas_calendario__calendario__fecha=fecha,
        recetas_calendario__tipo_comida__nombre=tipo
    ).distinct()

    # Excluir las recetas ya añadidas
    recetas_filtradas = recetas_disponibles.exclude(id__in=recetas_ya_agregadas.values_list('id', flat=True))
    # 2. Calcular el saldo proteico para el día indicado

    calendario = Calendario.objects.filter(fecha=fecha).first()
    if calendario:
        objetivo_proteico = calendario.objetivo_proteico
        proteinas_consumidas = calendario.proteinas_consumidas
    else:
        # Si no existe un calendario para ese día, usamos valores por defecto (por ejemplo, 100g de proteína)
        objetivo_proteico = 100
        proteinas_consumidas = 0
    remaining_protein = objetivo_proteico - proteinas_consumidas

    # 3. Parámetros y preparación
    PENALTY_PER_INGREDIENT = 50

    recetas_con_score = []
    fecha_date = datetime.strptime(fecha, "%Y-%m-%d").date()
    recomendaciones = []  # Aquí almacenaremos tanto individuales como pares

    # 4. Evaluación individual (se calcula el score para cada receta)
    individual_scores = []  # lista de tuplas (total_score, receta)
    for receta in recetas_filtradas:
        protein_score = 100 - abs(remaining_protein - receta.proteinas)
        penalty = 0
        for ingrediente in receta.ingredientes.all():
            start_period = fecha_date - timedelta(days=ingrediente.frec)
            end_period = fecha_date + timedelta(days=ingrediente.frec)
            used_recently = Calendario_Receta.objects.filter(
                calendario__fecha__gte=start_period,
                calendario__fecha__lt=end_period,
                receta__ingredientes=ingrediente
            ).exists()
            if used_recently:
                penalty += PENALTY_PER_INGREDIENT
        total_score = protein_score - penalty
        individual_scores.append((total_score, receta))
        recomendaciones.append({
            "ids": [receta.id],
            "nombre": receta.nombre,
            "score": total_score,
            "tipo": "single"
        })

    # 5. Para la generación de pares: si hay demasiadas recetas candidatas,
    # se selecciona un pool aleatorio (para incluir también recetas con menor score individual)
    MAX_POOL = 20  # Ajusta este número según tus necesidades
    pool_for_pairs = list(recetas_filtradas)
    if len(pool_for_pairs) > MAX_POOL:
        pool_for_pairs = random.sample(pool_for_pairs, MAX_POOL)

    # 6. Evaluación de pares (se forman combinaciones del pool para pares)
    for rec1, rec2 in combinations(pool_for_pairs, 2):
        combined_protein = rec1.proteinas + rec2.proteinas
        protein_score_pair = 100 - abs(remaining_protein - combined_protein)
        # Unión de ingredientes para evitar contar dos veces
        ingredientes_pair = set(list(rec1.ingredientes.all()) + list(rec2.ingredientes.all()))
        penalty_pair = 0
        for ingrediente in ingredientes_pair:
            start_period = fecha_date - timedelta(days=ingrediente.frec)
            end_period = fecha_date + timedelta(days=ingrediente.frec)
            used_recently = Calendario_Receta.objects.filter(
                calendario__fecha__gte=start_period,
                calendario__fecha__lt=end_period,
                receta__ingredientes=ingrediente
            ).exists()
            if used_recently:
                penalty_pair += PENALTY_PER_INGREDIENT
        total_score_pair = protein_score_pair - penalty_pair
        recomendaciones.append({
            "ids": [rec1.id, rec2.id],
            "nombre": f"{rec1.nombre} + {rec2.nombre}",
            "score": total_score_pair,
            "tipo": "pair"
        })

    # 7. Ordenar todas las recomendaciones por score (de mayor a menor)
    recomendaciones.sort(key=lambda x: x["score"], reverse=True)

    return JsonResponse(recomendaciones, safe=False)

@csrf_exempt
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

            # Obtener objetos desde la base de datos
            receta = get_object_or_404(Receta, id=receta_id)
            tipo_comida = get_object_or_404(TipoComida, id=tipo_comida_id)

            # Obtener o crear la instancia de calendario para esa fecha
            calendario, created = Calendario.objects.get_or_create(fecha=fecha)

            # Verificar si la receta ya está asignada para evitar duplicados
            if Calendario_Receta.objects.filter(calendario=calendario, receta=receta, tipo_comida=tipo_comida).exists():
                return JsonResponse({"error": "Esta receta ya está agregada en este día y tipo de comida."}, status=400)

            # Crear la relación en la tabla intermedia
            Calendario_Receta.objects.create(calendario=calendario, receta=receta, tipo_comida=tipo_comida)

            # 1) Obtener el lunes de la semana en la que se ha añadido la receta
            from datetime import datetime, timedelta
            fecha_date = datetime.strptime(fecha, "%Y-%m-%d").date()
            week_start = fecha_date - timedelta(days=fecha_date.weekday())

            # 2) Llamar a generar_lista_compra(week_start)
            generar_lista_compra(week_start)

            return JsonResponse({"mensaje": "Receta agregada exitosamente."}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Método no permitido"}, status=405)

@csrf_exempt
def recetas_en_calendario(request):
    """Devuelve las recetas ya añadidas al calendario para un día y tipo de comida."""
    fecha = request.GET.get("fecha")
    tipo = request.GET.get("tipo")

    calendario = Calendario.objects.filter(fecha=fecha).first()
    if not calendario:
        return JsonResponse([], safe=False)

    recetas = Calendario_Receta.objects.filter(calendario=calendario, tipo_comida__nombre=tipo)
    data = [{"id": cr.receta.id, "nombre": cr.receta.nombre} for cr in recetas]
    return JsonResponse(data, safe=False)

@csrf_exempt
def eliminar_receta_calendario(request):
    """Elimina una receta del calendario."""
    if request.method == "POST":
        fecha = request.POST.get("fecha")
        receta_id = request.POST.get("receta_id")
        tipo_comida = request.POST.get("tipo_comida")  # Se espera que se envíe el nombre del tipo de comida

        if not fecha or not receta_id:
            return JsonResponse({"error": "Faltan parámetros."}, status=400)

        # Eliminar la receta de la fecha y tipo de comida correspondiente
        eliminados, _ = Calendario_Receta.objects.filter(
            calendario__fecha=fecha, receta__id=receta_id, tipo_comida__nombre=tipo_comida
        ).delete()

        # 1) Obtener el lunes de la semana
        from datetime import datetime, timedelta
        fecha_date = datetime.strptime(fecha, "%Y-%m-%d").date()
        week_start = fecha_date - timedelta(days=fecha_date.weekday())

        # 2) Llamar a generar_lista_compra(week_start)
        generar_lista_compra(week_start)

        if eliminados:
            return JsonResponse({"mensaje": "Receta eliminada correctamente."}, status=200)
        else:
            return JsonResponse({"error": "No se encontró la receta en el calendario."}, status=404)

    return JsonResponse({"error": "Método no permitido"}, status=405)



def actualizar_calendario_dia(request):
    """
    Devuelve las recetas actualizadas de un día específico en formato JSON.
    """
    fecha = request.GET.get("fecha")
    if not fecha:
        return JsonResponse({"error": "Fecha no proporcionada."}, status=400)

    calendario = Calendario.objects.filter(fecha=fecha).first()
    if not calendario:
        return JsonResponse({"recetas": {}}, status=200)

    recetas_por_tipo = {}
    for cr in Calendario_Receta.objects.filter(calendario=calendario):
        if cr.tipo_comida.nombre not in recetas_por_tipo:
            recetas_por_tipo[cr.tipo_comida.nombre] = []
        recetas_por_tipo[cr.tipo_comida.nombre].append(cr.receta.nombre)

    proteinas_consumidas = sum(cr.receta.proteinas for cr in Calendario_Receta.objects.filter(calendario=calendario))

    return JsonResponse({"recetas": recetas_por_tipo,  
        "objetivo_proteico": calendario.objetivo_proteico,
        "proteinas_consumidas": proteinas_consumidas})

#Para que el degradado de los dias del calendario se actualice solo
@require_GET
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

    calendario, _ = Calendario.objects.get_or_create(fecha=fecha_obj, defaults={'objetivo_proteico': 100})
    data = {
        'proteinas_consumidas': calendario.proteinas_consumidas,
        'objetivo_proteico': calendario.objetivo_proteico
    }
    return JsonResponse(data)

#Exportacion pdf de las recetas de la semana
#EXPORTACION
def exportar_semana(request):
    """
    Exporta un PDF con el formato:
      - Una tabla donde la primera columna muestra los tipos de comida (Desayuno, Almuerzo, Merienda, Cena)
        y las siguientes 7 columnas corresponden a cada día de la semana (lunes a domingo).
      - Debajo, una lista de recetas únicas de la semana, mostrando sus ingredientes.
      - Finalmente, una lista de la compra que agrupa los ingredientes y cuenta sus apariciones.
    
    Se espera un parámetro GET 'start' con la fecha de inicio de la semana (YYYY-MM-DD).
    Si no se pasa o es inválido, se toma el lunes de la semana actual.
    """
    # 1. Obtener la fecha base
    start_str = request.GET.get('start')
    if start_str:
        try:
            input_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            input_date = datetime.today().date()
    else:
        input_date = datetime.today().date()

    # 2. Forzar que sea lunes
    start_date = input_date - timedelta(days=input_date.weekday())

    # Generar 7 días desde el lunes (lunes a domingo)
    dias = [start_date + timedelta(days=i) for i in range(7)]
    
    # Orden de los tipos de comida
    meal_order = ["Desayuno", "Almuerzo", "Merienda", "Cena"]

    # 3. Obtener los objetos Calendario para esos días
    calendarios = {cal.fecha: cal for cal in Calendario.objects.filter(fecha__in=dias)}

    # 4. Construir los datos para la tabla
    # 4.1. Dos filas de cabecera: la primera con las fechas (dd/mm) y la segunda con el nombre del día
    #     Dejamos la primera celda vacía (para la columna de tipos de comida)
    header_dates = [""] + [d.strftime("%d/%m") for d in dias]
    header_days = [""] + [format_date(d, format="EEEE", locale='es').capitalize() for d in dias]
    
    table_data = []
    table_data.append(header_dates)
    table_data.append(header_days)
    
    # 4.2. Para cada tipo de comida, la primera celda es el tipo,
    #      y el resto son Paragraph con posibles saltos de línea <br/>
    styles = getSampleStyleSheet()  # Para usarlo en los Paragraph
    normal_style = styles['Normal']

    for meal in meal_order:
        # Primera columna: el tipo de comida
        row = [Paragraph(meal, normal_style)]
        for d in dias:
            cal = calendarios.get(d)
            # Por defecto, la celda estará vacía
            cell_paragraph = Paragraph("", normal_style)
            if cal:
                # Recopilar recetas de este día que coincidan con el tipo de comida
                recetas = [cr.receta.nombre for cr in cal.calendario_recetas.all()
                           if cr.tipo_comida.nombre.lower() == meal.lower()]
                if recetas:
                    # Usamos <br/> para separar las recetas en líneas distintas
                    combined_text = "<br/>".join(recetas)
                    cell_paragraph = Paragraph(combined_text, normal_style)
            row.append(cell_paragraph)
        table_data.append(row)
    
    # 5. Generar la lista única de recetas y la lista de la compra
    unique_recipes = {}
    shopping_dict = {}
    for d in dias:
        cal = calendarios.get(d)
        if cal:
            for cr in cal.calendario_recetas.all():
                receta = cr.receta
                if receta.nombre not in unique_recipes:
                    ingredientes = list(receta.ingredientes.values_list('nombre', flat=True))
                    unique_recipes[receta.nombre] = ingredientes
                for ing in receta.ingredientes.all():
                    shopping_dict[ing.nombre] = shopping_dict.get(ing.nombre, 0) + 1

    bullet_style = ParagraphStyle('bullet', parent=normal_style, leftIndent=10)
    
    recetas_flowables = []
    for rec_name, ingredientes in unique_recipes.items():
        ing_str = ", ".join(ingredientes)
        recetas_flowables.append(Paragraph(f"{rec_name}: {ing_str}", bullet_style))
    
    compra_flowables = []
    for ing_name in sorted(shopping_dict.keys()):
        count = shopping_dict[ing_name]
        compra_flowables.append(Paragraph(f"{ing_name}: {count} raciones", bullet_style))
    
    # 6. Crear el PDF usando Platypus
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=40
    )
    
    custom_title = ParagraphStyle('customTitle', parent=styles['Title'], alignment=1)
    custom_heading = ParagraphStyle('customHeading', parent=styles['Heading2'], alignment=1)
    
    elements = []
    # Título principal en dos líneas
    start_formatted = format_date(dias[0], format="d 'de' MMMM 'de' y", locale='es')
    end_formatted = format_date(dias[-1], format="d 'de' MMMM 'de' y", locale='es')
    elements.append(Paragraph("Recetas de la semana", custom_title))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(f"{start_formatted} al {end_formatted}", custom_heading))
    elements.append(Spacer(1, 20))
    
    # Cálculo de anchos de columnas (1 para tipos y 7 para días)
    first_col_width = doc.width * 0.15
    other_cols_width = (doc.width - first_col_width) / len(dias)
    col_widths = [first_col_width] + [other_cols_width] * len(dias)
    
    # Ajustamos el estilo de la tabla para permitir WORDWRAP y alineación vertical arriba
    table_style = TableStyle([
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
    week_table = Table(table_data, colWidths=col_widths)
    week_table.setStyle(table_style)
    elements.append(week_table)
    elements.append(Spacer(1, 20))
    
    elements.append(Paragraph("Recetas:", custom_heading))
    elements.append(Spacer(1, 10))
    if recetas_flowables:
        from reportlab.platypus import ListFlowable
        elements.append(ListFlowable(recetas_flowables, bulletType='bullet'))
    else:
        elements.append(Paragraph("No hay recetas asignadas.", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    elements.append(Paragraph("Lista de la compra:", custom_heading))
    elements.append(Spacer(1, 10))
    if compra_flowables:
        elements.append(ListFlowable(compra_flowables, bulletType='bullet'))
    else:
        elements.append(Paragraph("No hay ingredientes en la lista de la compra.", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    doc.build(elements)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="recetas_semana.pdf")