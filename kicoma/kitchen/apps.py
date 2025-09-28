import locale
import logging

from django.apps import AppConfig
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
        from django.db import connections
        from django.db.backends.signals import connection_created

        # register for all *future* connections
        connection_created.connect(
            lambda sender, connection, **kwargs: register_collations(connection.connection),
            weak=False,
        )

        # also loop over all *existing* connections and register immediately
        for conn in connections.all():
            try:
                register_collations(conn.connection)
            except Exception as e:
                import logging
                logging.warning("Could not register collations immediately: %s", e)

        try:
            import kicoma.kitchen.signals
        except ImportError:
            pass
