from contextlib import contextmanager

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, connections


def demo_database_alias(language):
    """Database holding the demo data for `language`; None means "default"."""
    if not settings.KICOMA_DEMO_MODE:
        return None
    alias = settings.KICOMA_DEMO_DATABASES.get(language)
    return alias if alias in settings.DATABASES else None


def demo_databases():
    """(alias, language) of every demo database, the default one first."""
    languages = dict(settings.LANGUAGES)
    result = [(DEFAULT_DB_ALIAS, settings.LANGUAGE_CODE)]
    for language, alias in settings.KICOMA_DEMO_DATABASES.items():
        if language in languages and alias in settings.DATABASES:
            result.append((alias, language))
    return result


@contextmanager
def use_database(alias):
    """Serve every "default" database access in this thread from `alias`.

    Swapping the connection (instead of a router) also covers raw cursors,
    transaction.atomic() without `using` and the session store.
    """
    if alias == DEFAULT_DB_ALIAS:
        yield
        return
    default = connections[DEFAULT_DB_ALIAS]
    connections[DEFAULT_DB_ALIAS] = connections[alias]
    try:
        yield
    finally:
        connections[DEFAULT_DB_ALIAS] = default
