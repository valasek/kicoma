from django.conf import settings

from kicoma.kitchen.models import AppSettings


def settings_context(_request):
    return {"settings": settings}

def currency(request):
    settings_obj = AppSettings.objects.first()
    return {
        "CURRENCY": settings_obj.currency if settings_obj else "Kč"
    }
