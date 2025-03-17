from django import template

register = template.Library()

#Creado para la vista del calendario
@register.filter
def dictkey(dictionary, key):
    return dictionary.get(key, [])
