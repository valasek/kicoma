from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class KitchenConfig(AppConfig):
    name = "kicoma.kitchen"
    verbose_name = _("Kitchen")

    def ready(self):
        try:
            import kicoma.kitchen.signals  # noqa F401
        except ImportError:
            pass
