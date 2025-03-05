from django.shortcuts import render, redirect
from .models import Receta, Ingrediente, TipoComida, Calendario, Calendario_Receta
from .forms import RecetaForm, IngredienteForm

from django.shortcuts import get_object_or_404

from django.http import JsonResponse
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from datetime import date, timedelta



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
'''
def calendario_eventos(request):
    """Devuelve las recetas planificadas en formato JSON para FullCalendar."""
    eventos = []
    
    for cr in Calendario_Receta.objects.select_related("calendario", "receta", "tipo_comida").all():
        eventos.append({
            "title": f"{cr.receta.nombre} ({cr.tipo_comida.nombre})",
            "start": cr.calendario.fecha.strftime("%Y-%m-%d"),
            "color": get_color_tipo_comida(cr.tipo_comida.nombre),  # Color basado en tipo de comida
        })
    
    return JsonResponse(eventos, safe=False)

def get_color_tipo_comida(tipo):
    """Asigna un color según el tipo de comida."""
    colores = {
        "Desayuno": "#FFD700",  # Amarillo
        "Almuerzo": "#FF4500",  # Naranja
        "Merienda": "#32CD32",  # Verde
        "Cena": "#4682B4",  # Azul
    }
    return colores.get(tipo, "#808080")  # Gris por defecto

def vista_calendario(request):
    """Renderiza la página del calendario."""
    recetas = Receta.objects.all()
    tipos_comida = TipoComida.objects.all()
    
    return render(request, "calendario/calendario.html", {
        "recetas": recetas,
        "tipos_comida": tipos_comida
    })

@csrf_exempt
def agregar_receta_calendario(request):
    """Agrega una receta al calendario desde el formulario AJAX."""
    if request.method == "POST":
        fecha = request.POST.get("fecha")
        receta_id = request.POST.get("receta_id")
        tipo_comida_id = request.POST.get("tipo_comida_id")

        calendario, _ = Calendario.objects.get_or_create(fecha=fecha)
        receta = Receta.objects.get(id=receta_id)
        tipo_comida = TipoComida.objects.get(id=tipo_comida_id)

        Calendario_Receta.objects.create(calendario=calendario, receta=receta, tipo_comida=tipo_comida)

        return JsonResponse({"mensaje": "Receta agregada al calendario"}, status=200)

    return JsonResponse({"error": "Método no permitido"}, status=400)
'''
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

    # 7) Pasamos al contexto la info necesaria
    context = {
        'dias': dias,
        'dia_data': dia_data,
        'prev_week_url': f'?start={prev_week_date}',  # Query string para ir a la semana anterior
        'next_week_url': f'?start={next_week_date}',  # Query string para ir a la semana siguiente
    }
    return render(request, 'calendario/semanal.html', context)