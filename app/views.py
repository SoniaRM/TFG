from django.shortcuts import render, redirect
from .models import Receta, Ingrediente 
from .components import TipoComida
from .forms import IngredienteForm

from django.shortcuts import get_object_or_404



#RECETAS
def listado_recetas(request):
    recetas = Receta.objects.all()
    return render(request, 'listado_recetas.html', {'recetas': recetas})

#INGREDIENTES
def listado_ingredientes(request):
    ingredientes = Ingrediente.objects.all()
    return render(request, 'listado_ingredientes.html', {'ingredientes': ingredientes})

def crear_ingrediente(request):
    if request.method == 'POST':
        form = IngredienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listado_ingredientes')  
    else:
        form = IngredienteForm()
    return render(request, 'crear_ingrediente.html', {'form': form})

def editar_ingrediente(request, pk):
    ingrediente = get_object_or_404(Ingrediente, pk=pk)
    if request.method == 'POST':
        form = IngredienteForm(request.POST, instance=ingrediente)
        if form.is_valid():
            form.save()
            return redirect('listado_ingredientes')  
    else:
        form = IngredienteForm(instance=ingrediente)
    return render(request, 'editar_ingrediente.html', {'form': form})

def detalle_ingrediente(request, pk):
    ingrediente = get_object_or_404(Ingrediente, pk=pk)
    if request.method == 'POST' and 'delete' in request.POST:
        ingrediente.delete()
        return redirect('listado_ingredientes')
    return render(request, 'detalle_ingrediente.html', {'ingrediente': ingrediente})