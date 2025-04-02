from django.shortcuts import render, redirect, get_object_or_404
from ..models import Receta
from ..forms import RecetaForm

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
