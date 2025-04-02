from django.shortcuts import render, redirect, get_object_or_404
from ..models import Ingrediente
from ..forms import IngredienteForm

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
