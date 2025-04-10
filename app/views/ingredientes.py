from django.shortcuts import render, redirect, get_object_or_404
from ..models import Ingrediente
from ..forms import IngredienteForm
from django.contrib.auth.decorators import login_required

#INGREDIENTES
@login_required
def listado_ingredientes(request):
    familia = request.user.familias.first()  # Obtén la familia del usuario
    ingredientes = Ingrediente.objects.filter(familia=familia)
    return render(request, 'ingredientes/listado_ingredientes.html', {'ingredientes': ingredientes})

@login_required
def detalle_ingrediente(request, pk):
    familia = request.user.familias.first()
    ingrediente = get_object_or_404(Ingrediente, pk=pk, familia=familia)
    if request.method == 'POST' and 'delete' in request.POST:
        ingrediente.delete()
        return redirect('listado_ingredientes')
    return render(request, 'ingredientes/detalle_ingrediente.html', {'ingrediente': ingrediente})

@login_required
def crear_ingrediente(request):
    familia = request.user.familias.first()
    if request.method == 'POST':
        form = IngredienteForm(request.POST)
        if form.is_valid():
            ingrediente = form.save(commit=False)
            # Asigna la familia actual al nuevo ingrediente
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
