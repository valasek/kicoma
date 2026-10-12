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
