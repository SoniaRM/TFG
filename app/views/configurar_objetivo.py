from django.shortcuts import render, redirect
from django.utils import timezone
from ..models import Calendario
from ..forms import ObjetivoDiarioForm
from django.contrib.auth.decorators import login_required

#Configuración objetivo diario
@login_required
def vista_configurar_objetivo(request):
    familia = request.user.familias.first()  # Se obtiene la familia del usuario
    hoy = timezone.now().date()
    calendario, _ = Calendario.objects.get_or_create(fecha=hoy, familia=familia)

    if request.method == 'POST':
        form = ObjetivoDiarioForm(request.POST, instance=calendario)
        if form.is_valid():
            nuevo_objetivo = form.cleaned_data['objetivo_proteico']
            # Actualizamos todos los días desde hoy en adelante
            Calendario.objects.filter(fecha__gte=hoy, familia=familia).update(objetivo_proteico=nuevo_objetivo)
            return render(request, 'configurar_objetivo.html', {'form': form, 'exito': True})  # Mostrar modal
    else:
        form = ObjetivoDiarioForm(instance=calendario)

    return render(request, 'configurar_objetivo.html', {'form': form})
