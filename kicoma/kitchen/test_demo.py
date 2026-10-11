from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Max
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone, translation

from kicoma.kitchen.management.commands.reset_demo import (
    DAILY_MENU_LEAD_DAYS,
    DEMO_USERS,
    demo_users,
)
from kicoma.kitchen.models import Article, DailyMenu
from kicoma.kitchen.permissions import Roles, user_has_any_role

User = get_user_model()
DEMO_USER_COUNT = 2 * len(DEMO_USERS)


class ResetDemoCommandTest(TestCase):
    def test_refuses_to_run_without_demo_mode(self):
        User.objects.create_user(username="customer", password="secret")
        with self.assertRaises(CommandError):
            call_command("reset_demo")
        self.assertTrue(User.objects.filter(username="customer").exists())

    @override_settings(KICOMA_DEMO_MODE=True, KICOMA_DEMO_SUPERUSER_PASSWORD="s3cret")
    def test_creates_superuser_only_with_configured_password(self):
        call_command("reset_demo", stdout=None)

        user = authenticate(username="valasek", password="s3cret")
        self.assertIsNotNone(user)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.email, "valasek@gmail.com")
        self.assertEqual(user.name, "Stanislav Valasek")
        self.assertNotContains(self.client.get(reverse("account_login")), "valasek")

        with override_settings(KICOMA_DEMO_SUPERUSER_PASSWORD=""):
            call_command("reset_demo", stdout=None)
        self.assertFalse(User.objects.filter(is_superuser=True).exists())

    @override_settings(
        KICOMA_DEMO_MODE=True,
        KICOMA_DEMO_PASSWORD="demo-pass",
        KICOMA_DEMO_SUPERUSER_PASSWORD="",
    )
    def test_replaces_data_with_sample_data_and_demo_users(self):
        User.objects.create_user(username="customer", password="secret")

        call_command("reset_demo", stdout=None)

        self.assertFalse(User.objects.filter(username="customer").exists())
        self.assertEqual(User.objects.count(), DEMO_USER_COUNT)
        for names, roles, _label in DEMO_USERS:
            for username in names.values():
                user = authenticate(username=username, password="demo-pass")
                self.assertIsNotNone(user)
                self.assertFalse(user.is_superuser)
                self.assertFalse(user.is_staff)
                self.assertSetEqual(
                    set(user.groups.values_list("name", flat=True)),
                    {role.value for role in roles},
                )
        admin = User.objects.get(username="spravce")
        self.assertEqual(admin.name, "Správce")
        for role in Roles:
            self.assertTrue(user_has_any_role(admin, role.value))
        self.assertEqual(User.objects.get(username="cook").name, "Cook")
        self.assertEqual(User.objects.get(username="kuchar").name, "Kuchař")
        self.assertTrue(Article.objects.exists())
        latest = DailyMenu.objects.aggregate(latest=Max("date"))["latest"]
        self.assertEqual(
            latest, timezone.localdate() + timedelta(days=DAILY_MENU_LEAD_DAYS)
        )

    @override_settings(KICOMA_DEMO_MODE=True, KICOMA_DEMO_SUPERUSER_PASSWORD="")
    def test_can_run_repeatedly(self):
        call_command("reset_demo", stdout=None)
        menus = DailyMenu.objects.count()
        call_command("reset_demo", stdout=None)
        self.assertEqual(DailyMenu.objects.count(), menus)
        self.assertEqual(User.objects.count(), DEMO_USER_COUNT)


class DemoModeWebTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="kuchar", password="secret")
        self.client.force_login(self.user)

    @override_settings(KICOMA_DEMO_MODE=True)
    def test_account_changes_are_blocked(self):
        for url in (
            reverse("account_change_password"),
            reverse("account_email"),
            reverse("users:update"),
        ):
            response = self.client.post(url, {"oldpassword": "secret"})
            self.assertRedirects(
                response, reverse("kitchen:about"), fetch_redirect_response=False
            )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("secret"))

    def test_account_changes_allowed_outside_demo(self):
        response = self.client.get(reverse("account_change_password"))
        self.assertEqual(response.status_code, 200)

    @override_settings(KICOMA_DEMO_MODE=True, KICOMA_DEMO_PASSWORD="demo-pass")
    def test_login_page_shows_demo_credentials_and_banner(self):
        self.client.logout()
        response = self.client.get(reverse("account_login"))
        self.assertContains(response, "demo-pass")
        for username, _role in demo_users("cs"):
            self.assertContains(response, f"<strong>{username}</strong>")
        self.assertContains(response, 'role="status"')

    @override_settings(KICOMA_DEMO_MODE=True)
    def test_login_page_shows_english_demo_users_in_english(self):
        self.client.logout()
        # override restores the language that LocaleMiddleware would otherwise leak into later tests
        with translation.override("en"):
            response = self.client.get(reverse("account_login"))
        self.assertContains(response, "<strong>cook</strong> – Cook")
        self.assertContains(response, "<strong>admin</strong> – Admin")
        self.assertNotContains(response, "<strong>kuchar</strong>")

    def test_login_page_has_no_demo_credentials_outside_demo(self):
        self.client.logout()
        response = self.client.get(reverse("account_login"))
        self.assertNotContains(response, 'role="status"')
        self.assertNotIn("demo_users", response.context)


class SignupTest(TestCase):
    def test_signup_is_closed_by_default(self):
        response = self.client.post(
            reverse("account_signup"),
            {
                "username": "intruder",
                "email": "intruder@example.com",
                "password1": "x-Very-long-pass-123",
                "password2": "x-Very-long-pass-123",
            },
        )
        self.assertTemplateUsed(response, "account/signup_closed.html")
        self.assertFalse(User.objects.filter(username="intruder").exists())
