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

@register.filter
def get_vertical_gradient_style(calendario):
    """
    Devuelve un estilo CSS que muestra un relleno vertical (de abajo hacia arriba)
    según el porcentaje de proteínas consumidas.
    
    Se crea un degradado vertical (to top) que va de un color sólido a transparente.
    Luego se usa background-size para "recortar" el degradado al porcentaje deseado.
    """
    try:
        objetivo = calendario.objetivo_proteico
        consumido = calendario.proteinas_consumidas
    except Exception:
        return ""
    
    if objetivo == 0:
        return ""
    
    # Calcula el porcentaje de avance (clamp entre 0 y 100)
    porcentaje = min(max((consumido / objetivo) * 100, 0), 100)
    
    # Ajusta estos colores a los de tu paleta
    color_solido = "#FFD9C2"  # Color de la parte "rellena" (abajo)
    color_transparente = "rgba(0, 0, 0, 0)"  # Mismo tono pero transparente

    # Generamos un gradiente vertical que va de color_solido en la parte inferior a transparente en la parte superior.
    if porcentaje >= 100:
        # Si se alcanza el objetivo, el fondo queda completamente coloreado.
        style = f"background: {color_solido};"
    else:
        # Si no se alcanza el objetivo, se usa un degradado vertical.
        style = (
            "background: linear-gradient("
            "to top, "
            f"{color_solido} 0%, "
            f"{color_solido} 90%, "
            f"{color_transparente} 100%"
            ");"
            "background-repeat: no-repeat;"
            f"background-size: 100% {porcentaje}%;"
            "background-position: bottom;"
        )
    return style