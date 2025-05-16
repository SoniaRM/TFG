from django import template
from app.models import Calendario

register = template.Library()

@register.simple_tag(takes_context=True)
def get_calendario_for_date(context, fecha):
    """
    Dado un objeto fecha y el contexto (para obtener el request y la familia),
    devuelve la instancia de Calendario correspondiente para esa familia.
    Si no existe, la crea con objetivo_proteico por defecto (100).
    """
    request = context.get('request')
    familia = context.get('familia')
    if not familia and request and hasattr(request, 'user'):
        familia = request.user.familias.first()
    
    if not familia:
        return None  
    
    calendario, created = Calendario.objects.get_or_create(
        fecha=fecha,
        familia=familia,
        defaults={'objetivo_proteico': 100}
    )

    print(calendario)
    return calendario

@register.filter
def get_vertical_gradient_style(calendario):
    """
    Devuelve un estilo inline CSS con DOS degradados superpuestos:
     - azul (proteínas) en la mitad izquierda, hasta su %.
     - rojo (carbohidratos) en la mitad derecha, hasta su %.
    """
    try:
        obj_p = calendario.objetivo_proteico or 0
        con_p = calendario.proteinas_consumidas or 0
        obj_c = calendario.objetivo_carbohidratos or 0
        con_c = calendario.carbohidratos_consumidos or 0
    except:
        return ""

    def pct(cons, obj):
        return min(max((cons / obj) * 100, 0), 100) if obj > 0 else 0

    p_p = pct(con_p, obj_p)
    p_c = pct(con_c, obj_c)

    grad_p = "linear-gradient(to top, var(--blue-dark) 90%, rgba(0,0,0,0) 100%)"
    grad_c = "linear-gradient(to top, var(--blue-light) 90%, rgba(0,0,0,0) 100%)"

    style = (
        f"background-color: var(--gray-light);"
        f"background-image: {grad_p}, {grad_c};"
        f"background-repeat: no-repeat, no-repeat;"
        f"background-position: left bottom, right bottom;"
        f"background-size: 50% {p_p}%, 50% {p_c}%;"
    )
    return style