from django.conf import settings
from django.utils import translation

from kicoma.kitchen.management.commands.reset_demo import demo_users
from kicoma.kitchen.models import AppSettings


def settings_context(_request):
    return {"settings": settings}


def demo(_request):
    if not settings.KICOMA_DEMO_MODE:
        return {}
    return {
        "demo_users": demo_users(translation.get_language()),
        "demo_password": settings.KICOMA_DEMO_PASSWORD,
    }


def currency(request):
    settings_obj = AppSettings.objects.first()
    return {"CURRENCY": settings_obj.currency if settings_obj else "Kč"}
