from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone, translation

from kicoma.kitchen.models import DailyMenu
from kicoma.kitchen.permissions import Roles

DEMO_FIXTURES = (
    "dph",
    "alergeny",
    "druhy-jidla",
    "skupiny-stravniku",
    "article",
    "recipe",
    "recipe_article",
    "daily_menu",
)

DEMO_USERS = (
    ({"cs": "kuchar", "en": "cook"}, (Roles.COOK,), Roles.COOK.label),
    (
        {"cs": "skladnik", "en": "stockkeeper"},
        (Roles.STOCKKEEPER,),
        Roles.STOCKKEEPER.label,
    ),
    (
        {"cs": "nutricni-poradce", "en": "nutrition-advisor"},
        (Roles.NUTRITION_ADVISOR,),
        Roles.NUTRITION_ADVISOR.label,
    ),
    # Not a superuser: the demo must not expose Django admin or data import.
    ({"cs": "spravce", "en": "admin"}, (Roles.ADMIN,), Roles.ADMIN.label),
)


def demo_users(language):
    """(username, label) pairs for the given language, Czech as fallback."""
    language = (language or "cs").split("-")[0]
    return tuple(
        (names.get(language, names["cs"]), label) for names, _roles, label in DEMO_USERS
    )


# Latest sample daily menu is moved this many days ahead of today.
DAILY_MENU_LEAD_DAYS = 7

# Not listed on the login page; password from KICOMA_DEMO_SUPERUSER_PASSWORD.
DEMO_SUPERUSER = {
    "username": "valasek",
    "email": "valasek@gmail.com",
    "name": "Stanislav Valasek",
}


class Command(BaseCommand):
    help = "Public demo only: wipe ALL data, load sample data and demo users."

    def handle(self, *args, **options):
        if not settings.KICOMA_DEMO_MODE:
            raise CommandError(
                "Refusing to run: KICOMA_DEMO_MODE is not enabled on this instance."
            )
        with transaction.atomic():
            call_command("flush", interactive=False, verbosity=0)
            call_command("loaddata", *DEMO_FIXTURES, verbosity=0)
            call_command("sync_site", verbosity=0)
            self.create_users()
            self.shift_daily_menus()
        self.stdout.write(self.style.SUCCESS("Demo data has been reset."))

    def create_users(self):
        User = get_user_model()
        for names, roles, label in DEMO_USERS:
            groups = [Group.objects.get_or_create(name=role.value)[0] for role in roles]
            for language, username in names.items():
                with translation.override(language):
                    name = str(label)
                user = User.objects.create_user(
                    username=username,
                    password=settings.KICOMA_DEMO_PASSWORD,
                    name=name,
                )
                user.groups.add(*groups)
        if settings.KICOMA_DEMO_SUPERUSER_PASSWORD:
            User.objects.create_superuser(
                password=settings.KICOMA_DEMO_SUPERUSER_PASSWORD, **DEMO_SUPERUSER
            )

    def shift_daily_menus(self):
        latest = DailyMenu.objects.aggregate(latest=Max("date"))["latest"]
        if latest is None:
            return
        delta = timezone.localdate() + timedelta(days=DAILY_MENU_LEAD_DAYS) - latest
        if not delta:
            return
        # Move the farthest dates first so the (date, group, type) constraint never collides.
        ordering = "-date" if delta > timedelta(0) else "date"
        for pk, date in DailyMenu.objects.order_by(ordering).values_list("pk", "date"):
            DailyMenu.objects.filter(pk=pk).update(date=date + delta)
