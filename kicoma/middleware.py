from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import gettext as _

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


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/health-check/":
            response = HttpResponse("OK")
        else:
            response = self.get_response(request)

        return response
