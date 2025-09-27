from itertools import islice
from pathlib import Path

import yaml
from django.utils.translation import get_language

from .models import AppSettings


def get_currency(default="Kč"):
    settings_obj = AppSettings.objects.first()
    return settings_obj.currency if settings_obj else default

def load_changelog(latest=False):
    lang = (get_language() or "cs").split("-")[0]
    filename = f"changelog-{lang}.yaml"
    path = Path(__file__).resolve().parent / filename
    with open(path, encoding="UTF-8") as f:
        data = yaml.safe_load(f)
    if latest:
        merged = (
            {"year":year, **e}
            for year, entries in sorted(data.items(), reverse=True)
            for e in entries
        )
        return list(islice(merged,4))
    else:
        return data
