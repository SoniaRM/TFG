from django import template
from app.models import Calendario

register = template.Library()

@register.simple_tag
def get_calendario_for_date(fecha):
    """
    Dado un objeto fecha, devuelve la instancia de Calendario correspondiente.
    Si no existe, la crea con el objetivo_proteico por defecto (100).
    """
    calendario, created = Calendario.objects.get_or_create(fecha=fecha, defaults={'objetivo_proteico': 100})
    print(calendario)
    return calendario
