from django import template

register = template.Library()

@register.filter
def has_filters(request_get):
    """Checks if request.GET contains filters (except page)"""
    return any(key != 'page' and value for key, value in request_get.items())
