from django import template
from django.utils.html import format_html

from ..permissions import user_has_any_role

register = template.Library()


@register.filter(name="has_any_group")
def has_any_group(user, group_names):
    return user_has_any_role(user, group_names)


@register.simple_tag(takes_context=True)
def role_link(context, href, label, roles):
    if user_has_any_role(context["request"].user, roles):
        return format_html('<a href="{}">{}</a>', href, label)
    return label


@register.simple_tag(takes_context=True)
def superuser_link(context, href, label):
    user = context["request"].user
    if user.is_authenticated and user.is_superuser:
        return format_html('<a href="{}">{}</a>', href, label)
    return label
