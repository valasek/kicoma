from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import translation

from kicoma.kitchen import demo_data
from kicoma.kitchen.permissions import Roles
from kicoma.utils.demo_database import demo_databases, use_database

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


# Not listed on the login page; password from KICOMA_DEMO_SUPERUSER_PASSWORD.
DEMO_SUPERUSER = {
    "username": "valasek",
    "email": "valasek@gmail.com",
    "name": "Stanislav Valasek",
}


class Command(BaseCommand):
    help = (
        "Public demo only: wipe ALL data, load sample data and demo users "
        "into the database of every language."
    )

    def handle(self, *args, **options):
        if not settings.KICOMA_DEMO_MODE:
            raise CommandError(
                "Refusing to run: KICOMA_DEMO_MODE is not enabled on this instance."
            )
        for alias, language in demo_databases():
            with use_database(alias), translation.override(language):
                call_command("migrate", interactive=False, verbosity=0)
                with transaction.atomic():
                    call_command("flush", interactive=False, verbosity=0)
                    call_command("sync_site", verbosity=0)
                    users = self.create_users(language)
                    demo_data.load(language, users)
            self.stdout.write(
                self.style.SUCCESS(f"Demo data ({language}) has been reset.")
            )

    def create_users(self, language):
        """Create the demo users for `language`; return {role: user}."""
        User = get_user_model()
        users = {}
        for (username, label), (_names, roles, _label) in zip(
            demo_users(language), DEMO_USERS, strict=True
        ):
            groups = [Group.objects.get_or_create(name=role.value)[0] for role in roles]
            user = User.objects.create_user(
                username=username,
                password=settings.KICOMA_DEMO_PASSWORD,
                name=str(label),
            )
            user.groups.add(*groups)
            users.update(dict.fromkeys(roles, user))
        if settings.KICOMA_DEMO_SUPERUSER_PASSWORD:
            User.objects.create_superuser(
                password=settings.KICOMA_DEMO_SUPERUSER_PASSWORD, **DEMO_SUPERUSER
            )
        return users
