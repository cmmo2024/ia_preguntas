# core/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Permite acceder a un item en un diccionario o lista por clave o índice"""
    try:
        return dictionary[key]
    except (KeyError, IndexError, TypeError):
        return None