from django.shortcuts import render, redirect, get_object_or_404
from ..models import Receta, Ingrediente
from ..forms import RecetaForm, IngredienteForm
from django.contrib.auth.decorators import login_required

#RECETAS
@login_required
def listado_recetas(request):
    familia = request.user.familias.first()
    recetas = Receta.objects.filter(familia=familia)
    ingredientes = Ingrediente.objects.filter(familia=familia)
    return render(request, 'recetas/listado_recetas.html', {'recetas': recetas, 'ingredientes': ingredientes})

@login_required
def detalle_receta(request, pk):
    familia = request.user.familias.first()
    receta = get_object_or_404(Receta, pk=pk, familia=familia)
    if request.method == 'POST' and 'delete' in request.POST:
        receta.delete()
        return redirect('listado_recetas')
    return render(request, 'recetas/detalle_receta.html', {'receta': receta})

@login_required
def crear_receta(request):
    familia = request.user.familias.first()
    ingrediente_form = IngredienteForm()    # <— NUEVO

    if request.method == 'POST':
        form = RecetaForm(request.POST)
        if form.is_valid():
            receta = form.save(commit=False)
            receta.familia = familia
            receta.save()
            form.save_m2m()
            return render(request, 'recetas/crear_receta.html', {
                'form': RecetaForm(),
                'ingrediente_form': IngredienteForm(),  # <— aseguramos que el modal siga teniendo el form
                'exito': True
            })
    else:
        form = RecetaForm()
    return render(request, 'recetas/crear_receta.html', {'form': form, 'ingrediente_form': ingrediente_form})

@login_required
def editar_receta(request, pk):
    familia = request.user.familias.first()
    receta = get_object_or_404(Receta, pk=pk, familia=familia)
    if request.method == 'POST':
        form = RecetaForm(request.POST, instance=receta)
        if form.is_valid():
            form.save()
            return render(request, 'recetas/editar_receta.html', {
                'form': form,
                'receta': receta,
                'exito': True
            })
    else:
        form = RecetaForm(instance=receta)
    return render(request, 'recetas/editar_receta.html', {'form': form, 'receta': receta})
