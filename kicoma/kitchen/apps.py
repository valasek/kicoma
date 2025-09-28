import locale
import logging

from django.apps import AppConfig
from django.db import connection
from django.db.backends.signals import connection_created
from django.utils.translation import gettext_lazy as _


def register_collations(conn):
    try:
        locale.setlocale(locale.LC_COLLATE, "cs_CZ.utf8")

        def collate_cs(x, y):
            return locale.strcoll(x or "", y or "")

        locale.setlocale(locale.LC_COLLATE, "en_US.utf8")

        def collate_en(x, y):
            return locale.strcoll(x or "", y or "")

        conn.create_collation("cs_collate", collate_cs)
        conn.create_collation("en_collate", collate_en)

        logging.info("SQLite collations registered successfully")

    except Exception as e:
        logging.warning("Could not register SQLite collations: %s", e)


class KitchenConfig(AppConfig):
    name = "kicoma.kitchen"
    verbose_name = _("Kitchen")

    def ready(self):
        # Ensure collations are registered immediately for the first connection
        try:
            register_collations(connection.connection)
        except Exception as e:
            logging.warning("Immediate collation registration failed: %s", e)

        connection_created.connect(
            lambda sender, connection, **kwargs: register_collations(connection.connection)
        )

        try:
            import kicoma.kitchen.signals
        except ImportError:
            pass
