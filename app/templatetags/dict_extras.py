from django import template

register = template.Library()

@register.filter
def dictkey(dictionary, key):
    return dictionary.get(key, [])
