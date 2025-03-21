from django.shortcuts import render, redirect
from .models import Receta, Ingrediente, TipoComida, Calendario, Calendario_Receta
from .forms import RecetaForm, IngredienteForm

from django.shortcuts import get_object_or_404

from django.http import JsonResponse
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from datetime import date, timedelta
from django.views.decorators.http import require_GET
#Exportacion pdf de las recetas de la semana
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

#RECETAS
def listado_recetas(request):
    recetas = Receta.objects.all()
    return render(request, 'recetas/listado_recetas.html', {'recetas': recetas})

def detalle_receta(request, pk):
    receta = get_object_or_404(Receta, pk=pk)
    if request.method == 'POST' and 'delete' in request.POST:
        receta.delete()
        return redirect('listado_recetas')
    return render(request, 'recetas/detalle_receta.html', {'receta': receta})

def crear_receta(request):
    if request.method == 'POST':
        form = RecetaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listado_recetas')  # Redirige a la lista de recetas después de crear una nueva
    else:
        form = RecetaForm()
    return render(request, 'recetas/crear_receta.html', {'form': form})

def editar_receta(request, pk):
    receta = get_object_or_404(Receta, pk=pk)
    if request.method == 'POST':
        form = RecetaForm(request.POST, instance=receta)
        if form.is_valid():
            form.save()
            return redirect('listado_recetas')
    else:
        form = RecetaForm(instance=receta)
    return render(request, 'recetas/editar_receta.html', {'form': form, 'receta': receta})

#INGREDIENTES
def listado_ingredientes(request):
    ingredientes = Ingrediente.objects.all()
    return render(request, 'ingredientes/listado_ingredientes.html', {'ingredientes': ingredientes})

def detalle_ingrediente(request, pk):
    ingrediente = get_object_or_404(Ingrediente, pk=pk)
    if request.method == 'POST' and 'delete' in request.POST:
        ingrediente.delete()
        return redirect('listado_ingredientes')
    return render(request, 'ingredientes/detalle_ingrediente.html', {'ingrediente': ingrediente})

def crear_ingrediente(request):
    if request.method == 'POST':
        form = IngredienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listado_ingredientes')  
    else:
        form = IngredienteForm()
    return render(request, 'ingredientes/crear_ingrediente.html', {'form': form})

def editar_ingrediente(request, pk):
    ingrediente = get_object_or_404(Ingrediente, pk=pk)
    if request.method == 'POST':
        form = IngredienteForm(request.POST, instance=ingrediente)
        if form.is_valid():
            form.save()
            return redirect('listado_ingredientes')  
    else:
        form = IngredienteForm(instance=ingrediente)
    return render(request, 'ingredientes/editar_ingrediente.html', {'form': form, 'ingrediente': ingrediente})

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

    }
    print(context)

    return render(request, 'calendario/semanal.html', context)

#Añadir receta al calendario desde el calendario
#Filtrar las recetas por tipo Comida

@csrf_exempt
def recetas_por_tipo(request):
    """
    Devuelve las recetas disponibles para agregar al calendario,
    excluyendo las que ya han sido añadidas en la fecha y tipo de comida seleccionados.
    """
    tipo = request.GET.get("tipo")
    fecha = request.GET.get("fecha")

    if not tipo or not fecha:
        return JsonResponse({"error": "Faltan parámetros."}, status=400)

    # Obtener todas las recetas del tipo de comida seleccionado
    recetas_disponibles = Receta.objects.filter(tipo_comida__nombre=tipo).distinct()

    # Obtener las recetas que ya están en el calendario en esa fecha y tipo de comida
    recetas_ya_agregadas = Receta.objects.filter(
        recetas_calendario__calendario__fecha=fecha,
        recetas_calendario__tipo_comida__nombre=tipo
    ).distinct()

    # Excluir las recetas ya añadidas
    recetas_filtradas = recetas_disponibles.exclude(id__in=recetas_ya_agregadas.values_list('id', flat=True))

    # Devolver la lista en formato JSON
    data = [{"id": receta.id, "nombre": receta.nombre} for receta in recetas_filtradas]
    return JsonResponse(data, safe=False)


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
def exportar_semana(request):
    """
    Exporta un PDF con el formato:
      - Una tabla donde la primera columna muestra los tipos de comida (Desayuno, Almuerzo, Merienda, Cena)
        y las siguientes 7 columnas corresponden a los días de la semana (con fecha y nombre del día en español).
      - Debajo, una lista de recetas únicas de la semana, mostrando sus ingredientes.
      - Finalmente, una lista de la compra que agrupa los ingredientes y cuenta sus apariciones.
    
    Se espera un parámetro GET 'start' con la fecha de inicio de la semana (YYYY-MM-DD).
    """
    # 1. Obtener la fecha de inicio de la semana
    start_str = request.GET.get('start')
    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        start_date = datetime.today().date()

    # 2. Generar la lista de 7 días
    dias = [start_date + timedelta(days=i) for i in range(7)]
    
    # Orden de los tipos de comida
    meal_order = ["Desayuno", "Almuerzo", "Merienda", "Cena"]

    # 3. Obtener los objetos Calendario para esos días (se asume que cada día tiene un objeto Calendario)
    calendarios = {cal.fecha: cal for cal in Calendario.objects.filter(fecha__in=dias)}

    # 4. Construir los datos para la tabla con la primera columna de tipos de comida
    # Primera fila: la primera celda vacía y luego las fechas en formato dd/mm
    header_dates = [""] + [d.strftime("%d/%m") for d in dias]
    # Segunda fila: la primera celda vacía y luego los nombres de los días en español
    header_days = [""] + [format_date(d, format="EEEE", locale='es').capitalize() for d in dias]
    
    table_data = []
    table_data.append(header_dates)
    table_data.append(header_days)
    
    # Para cada tipo de comida, la primera celda es el nombre y luego las recetas (separadas por salto de línea) para cada día
    for meal in meal_order:
        row = [meal]  # Primera celda: el tipo de comida
        for d in dias:
            cal = calendarios.get(d)
            cell_text = ""
            if cal:
                recetas = [cr.receta.nombre for cr in cal.calendario_recetas.all()
                           if cr.tipo_comida.nombre.lower() == meal.lower()]
                cell_text = "\n".join(recetas)
            row.append(cell_text)
        table_data.append(row)
    
    # 5. Generar la lista única de recetas y la lista de la compra
    unique_recipes = {}  # clave: receta.nombre, valor: lista de ingredientes
    shopping_dict = {}   # clave: ingrediente.nombre, valor: cantidad (número de apariciones)
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

    styles = getSampleStyleSheet()
    bullet_style = ParagraphStyle('bullet', parent=styles['Normal'], leftIndent=10)
    
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
    
    # Definir algunos estilos personalizados
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
    
    # Calcular los anchos: ahora tenemos 8 columnas (1 para tipos y 7 para días)
    first_col_width = doc.width * 0.15  # 15% del ancho para la primera columna
    other_cols_width = (doc.width - first_col_width) / len(dias)
    col_widths = [first_col_width] + [other_cols_width] * len(dias)
    
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
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