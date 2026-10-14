from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


class LandingPageTests(TestCase):
    @override_settings(KICOMA_DEMO_MODE=True)
    def test_demo_shows_landing_page(self):
        response = self.client.get(reverse("kicoma:home"))
        self.assertTemplateUsed(response, "common/home.html")

    @override_settings(KICOMA_DEMO_MODE=False)
    def test_tenant_redirects_to_about(self):
        response = self.client.get(reverse("kicoma:home"))
        self.assertRedirects(response, reverse("kitchen:about"))


@override_settings(
    DEBUG=False,
    ALLOWED_HOSTS=["demo.kicoma.eu"],
    MANAGERS=[("Manager", "manager@example.com")],
    KICOMA_DEMO_MODE=False,
)
class BrokenLinkEmailTests(TestCase):
    def test_missing_urls_with_internal_referrer_do_not_send_email(self):
        for path in ("/login/", "/wp-login.php"):
            with self.subTest(path=path):
                response = self.client.get(
                    path,
                    HTTP_HOST="demo.kicoma.eu",
                    HTTP_REFERER="https://demo.kicoma.eu/",
                    secure=True,
                )
                self.assertEqual(response.status_code, 404)
                self.assertEqual(len(mail.outbox), 0)
