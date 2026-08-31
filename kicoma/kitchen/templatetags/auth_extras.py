from django import template

register = template.Library()

@register.filter(name="has_any_group")
def has_any_group(user, group_names):
    if not user or not user.is_authenticated:
        return False
    names = [name.strip() for name in group_names.split(",") if name.strip()]
    return user.groups.filter(name__in=names).exists()
