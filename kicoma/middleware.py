from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import translation
from django.utils.translation import gettext as _

from kicoma.utils.demo_database import demo_database_alias, use_database

# Views that would let one demo visitor lock out or affect the others.
DEMO_BLOCKED_VIEWS = frozenset(
    {
        "account_signup",
        "account_change_password",
        "account_set_password",
        "account_reset_password",
        "account_reset_password_from_key",
        "account_email",
        "users:update",
    }
)


class DemoModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not settings.KICOMA_DEMO_MODE:
            return None
        match = request.resolver_match
        if match is None or match.view_name not in DEMO_BLOCKED_VIEWS:
            return None
        messages.warning(request, _("V ukázkové verzi není tato akce dostupná."))
        return redirect("kitchen:about")


class DemoDatabaseMiddleware:
    """Demo only: each language (URL prefix) has its own sample data.

    Must run before SessionMiddleware so sessions are stored per language too.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = translation.get_language_from_path(request.path_info)
        alias = demo_database_alias(language)
        if alias is None:
            return self.get_response(request)
        with use_database(alias):
            return self.get_response(request)


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/health-check/":
            response = HttpResponse("OK")
        else:
            response = self.get_response(request)

        return response
