import locale
import logging

from django.apps import AppConfig
from django.db.backends.signals import connection_created
from django.utils.translation import gettext_lazy as _


def register_collations(conn):
    try:
        def collate_cs(x, y):
            locale.setlocale(locale.LC_COLLATE, "cs_CZ.UTF-8")
            return locale.strcoll(x or "", y or "")

        def collate_en(x, y):
            locale.setlocale(locale.LC_COLLATE, "en_US.UTF-8")
            return locale.strcoll(x or "", y or "")

        conn.create_collation("cs_collate", collate_cs)
        conn.create_collation("en_collate", collate_en)

    except Exception as e:
        logging.warning("Could not register SQLite collations: %s", e)


class KitchenConfig(AppConfig):
    name = "kicoma.kitchen"
    verbose_name = _("Kitchen")

    def ready(self):
        connection_created.connect(
            lambda sender, connection, **kwargs: register_collations(connection.connection)
        )

        try:
            import kicoma.kitchen.signals
        except ImportError:
            pass
