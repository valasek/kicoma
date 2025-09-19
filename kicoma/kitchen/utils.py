from .models import AppSettings


def get_currency(default="Kč"):
    settings_obj = AppSettings.objects.first()
    return settings_obj.currency if settings_obj else default
