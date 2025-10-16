import datetime

from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.urls import reverse

from .functions import convert_units

CACHE_KEY_MESSAGE_DATE = "daily_job_date"
CACHE_KEY_MESSAGE = "daily_job_messages"

def run_daily_job():
    """Run the recipe unit validation and store results in cache."""
    from kicoma.kitchen.models import Recipe, RecipeArticle
    message_text = ""
    errors = 0

    for recipe in Recipe.objects.all():
        for ra in RecipeArticle.objects.filter(recipe=recipe):
            try:
                convert_units(ra.amount, ra.unit, ra.article.unit)
            except ValidationError:
                errors += 1

    if errors > 0:
        report_url = reverse("kitchen:showIncorrectUnits")
        message_text = {
            "level": messages.ERROR,
            "text": (
                f"{errors} receptů obsahuje zboží, které má nastavené jednotky jinak než na skladu. "
                f"Otevřete <a href='{report_url}'>report</a> a opravte jednotky zboží."
            ),
            "tag": "error",
        }

        cache.set(CACHE_KEY_MESSAGE_DATE, str(datetime.date.today()), None)
        cache.set(CACHE_KEY_MESSAGE, message_text, None)
    else:
        clear_messages()


def should_run_today():
    """Return True if we haven’t run the job today."""
    last_date = cache.get(CACHE_KEY_MESSAGE_DATE)
    return last_date != str(datetime.date.today())


def get_message():
    """Return current list of job messages."""
    return cache.get(CACHE_KEY_MESSAGE, [])


def clear_messages():
    """Manually clear messages (resolve them)."""
    cache.delete_many([CACHE_KEY_MESSAGE_DATE, CACHE_KEY_MESSAGE])
