from django import template

from kicoma.kitchen.functions import format_decimal, format_unit_price

register = template.Library()


@register.filter
def plain_decimal(value):
    return format_decimal(value)


@register.filter
def unit_price(value):
    return format_unit_price(value)


@register.filter
def has_filters(request_get):
    """Checks if request.GET contains filters (except page)"""
    return any(key != "page" and value for key, value in request_get.items())
