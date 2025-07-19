# core/templatetags/date_filters.py
from django import template
from datetime import date, datetime, timedelta

register = template.Library()

@register.filter(name='add_days')
def add_days(value, days):
    """Añade N días a una fecha"""
    if not isinstance(value, (date, datetime.date)):
        return value
    try:
        return value + timedelta(days=int(days))
    except (ValueError, TypeError):
        return value