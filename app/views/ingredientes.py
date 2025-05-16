from django.shortcuts import render, redirect, get_object_or_404
from ..models import Ingrediente, Receta
from ..forms import IngredienteForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse 

#INGREDIENTES
@login_required
def listado_ingredientes(request):
    familia = request.user.familias.first()  
    ingredientes = Ingrediente.objects.filter(familia=familia)
    return render(request, 'ingredientes/listado_ingredientes.html', {'ingredientes': ingredientes})

@login_required
def detalle_ingrediente(request, pk):
    familia = request.user.familias.first()
    ingrediente = get_object_or_404(Ingrediente, pk=pk, familia=familia)
    recetas = Receta.objects.filter(familia=familia, ingredientes=ingrediente)
    if request.method == 'POST' and 'delete' in request.POST:
        ingrediente.delete()
        return redirect('listado_ingredientes')
    return render(request, 'ingredientes/detalle_ingrediente.html', {'ingrediente': ingrediente, 'recetas': recetas})

@login_required
def crear_ingrediente(request):
    familia = request.user.familias.first()
    if request.method == 'POST':
        form = IngredienteForm(request.POST, user=request.user) 
        if form.is_valid():
            ingrediente = form.save(commit=False)
            ingrediente.familia = familia
            ingrediente.save()            
            return render(request, 'ingredientes/crear_ingrediente.html', {
                'form': IngredienteForm(),
                'exito': True
            })    
    else:
        form = IngredienteForm()
    return render(request, 'ingredientes/crear_ingrediente.html', {'form': form})

@login_required
def editar_ingrediente(request, pk):
    familia = request.user.familias.first()
    ingrediente = get_object_or_404(Ingrediente, pk=pk, familia=familia)
    if request.method == 'POST':
        form = IngredienteForm(request.POST, instance=ingrediente)
        if form.is_valid():
            form.save()
            return render(request, 'ingredientes/editar_ingrediente.html', {
                'form': form,
                'ingrediente': ingrediente,
                'exito': True
            })    
    else:
        form = IngredienteForm(instance=ingrediente)
    return render(request, 'ingredientes/editar_ingrediente.html', {'form': form, 'ingrediente': ingrediente})

@require_POST
@login_required
def crear_ingrediente_ajax(request):
    form = IngredienteForm(request.POST, user=request.user)
    if form.is_valid():
        nombre = form.cleaned_data['nombre'].strip()
        familia = request.user.familias.first()
        if Ingrediente.objects.filter(
            nombre__iexact=nombre,
            familia=familia
        ).exists():
            return JsonResponse({
                'errors': {'nombre': ['Ya existe un ingrediente con este nombre.']}
            }, status=400)

        ing = form.save(commit=False)
        ing.nombre  = nombre
        ing.familia = familia
        ing.save()
        return JsonResponse({'id': ing.id, 'nombre': ing.nombre})

    return JsonResponse({'errors': form.errors}, status=400)