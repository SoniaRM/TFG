from django.shortcuts import render, redirect
from django.utils import timezone
from ..models import Calendario
from ..forms import ObjetivoDiarioForm

#Configuración objetivo diario
def vista_configurar_objetivo(request):
    hoy = timezone.now().date()
    calendario, _ = Calendario.objects.get_or_create(fecha=hoy)

    if request.method == 'POST':
        form = ObjetivoDiarioForm(request.POST, instance=calendario)
        if form.is_valid():
            nuevo_objetivo = form.cleaned_data['objetivo_proteico']
            # Actualizamos todos los días desde hoy en adelante
            Calendario.objects.filter(fecha__gte=hoy).update(objetivo_proteico=nuevo_objetivo)
            return redirect('calendario_semanal')  # O donde quieras redirigir
    else:
        form = ObjetivoDiarioForm(instance=calendario)

    return render(request, 'configurar_objetivo.html', {'form': form})
