from django import template
from django.db.models import Avg

register = template.Library()

@register.filter
def get_field_value(obj, field_name):
    """Get a field value from an object"""
    return getattr(obj, field_name, None)

@register.filter
def sum_reviews(hotels):
    return sum(h.get_total_reviews() for h in hotels)

@register.filter
def avg_rating(hotels):
    if not hotels:
        return 0
    total = sum(h.get_average_rating() for h in hotels)
    return total / len(hotels) if hotels else 0