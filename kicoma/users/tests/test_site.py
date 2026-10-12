import pytest
from allauth.account.adapter import get_adapter
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.test import RequestFactory, override_settings

from kicoma.users.models import User

pytestmark = pytest.mark.django_db


@override_settings(
    DJANGO_SITE_DOMAIN="hospic-cercany.kicoma.eu", DJANGO_SITE_NAME="KiCoMa"
)
def test_sync_site_corrects_verification_email():
    Site.objects.update_or_create(
        pk=1, defaults={"domain": "example.com", "name": "example.com"}
    )
    Site.objects.clear_cache()
    Site.objects.get_current()

    call_command("sync_site")

    site = Site.objects.get_current()
    assert site.domain == "hospic-cercany.kicoma.eu"
    assert site.name == "KiCoMa"
    request = RequestFactory().get("/", HTTP_HOST=site.domain)
    message = get_adapter(request).render_mail(
        "account/email/email_confirmation",
        "recipient@example.com",
        {
            "current_site": site,
            "user": User(username="test-user"),
            "activate_url": f"https://{site.domain}/accounts/confirm-email/test/",
        },
    )
    assert message.subject.startswith("[KiCoMa]")
    assert site.domain in message.body
    assert "example.com" not in message.body


@override_settings(
    KICOMA_DEMO_MODE=True,
    KICOMA_DEMO_SUPERUSER_PASSWORD="",
    DJANGO_SITE_DOMAIN="kicoma.eu",
    DJANGO_SITE_NAME="KiCoMa",
)
def test_demo_reset_preserves_configured_site():
    call_command("reset_demo")

    site = Site.objects.get_current()
    assert site.domain == "kicoma.eu"
    assert site.name == "KiCoMa"


@override_settings(DJANGO_SITE_DOMAIN="", DJANGO_SITE_NAME="KiCoMa")
def test_sync_site_without_domain_preserves_existing_site():
    site = Site.objects.get_current()
    original = (site.domain, site.name)

    call_command("sync_site")

    site.refresh_from_db()
    assert (site.domain, site.name) == original
