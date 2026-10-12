from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone, translation

from kicoma.kitchen.management.commands.reset_demo import (
    DEMO_USERS,
    demo_users,
)
from kicoma.kitchen.models import (
    AppSettings,
    Article,
    DailyMenu,
    DailyMenuRecipe,
    MealGroup,
    MealType,
    Menu,
    MenuRecipe,
    Recipe,
    StockIssue,
    StockIssueArticle,
    StockReceipt,
    StockReceiptArticle,
    UnitChangeLog,
)
from kicoma.kitchen.permissions import Roles, user_has_any_role
from kicoma.utils.demo_database import use_database

User = get_user_model()
DEMO_DATABASES = {"default", "demo_en"}
LIST_MODELS = (
    Article,
    Recipe,
    Menu,
    DailyMenu,
    MealGroup,
    MealType,
    StockReceipt,
    StockIssue,
    UnitChangeLog,
)


class ResetDemoCommandTest(TestCase):
    databases = DEMO_DATABASES

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
        for alias, language in (("default", "cs"), ("demo_en", "en")):
            users = User.objects.using(alias)
            self.assertEqual(users.count(), len(DEMO_USERS))
            with use_database(alias):
                for (username, _label), (_names, roles, _) in zip(
                    demo_users(language), DEMO_USERS, strict=True
                ):
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
        self.assertEqual(
            User.objects.using("demo_en").get(username="cook").name, "Cook"
        )
        self.assertEqual(User.objects.get(username="kuchar").name, "Kuchař")
        self.assertFalse(User.objects.filter(username="cook").exists())

    @override_settings(KICOMA_DEMO_MODE=True, KICOMA_DEMO_SUPERUSER_PASSWORD="")
    def test_every_language_gets_its_own_small_data_set(self):
        call_command("reset_demo", stdout=None)

        self.assertTrue(Article.objects.filter(article="Brambory").exists())
        self.assertFalse(Article.objects.filter(article="Potatoes").exists())
        self.assertTrue(
            Article.objects.using("demo_en").filter(article="Potatoes").exists()
        )
        self.assertEqual(AppSettings.objects.get().currency, "Kč")
        self.assertEqual(AppSettings.objects.using("demo_en").get().currency, "€")
        potatoes = Article.objects.using("demo_en").get(article="Potatoes")
        self.assertEqual(potatoes.average_price, Decimal("0.72"))
        for alias in DEMO_DATABASES:
            for model in LIST_MODELS:
                count = model.objects.using(alias).count()
                self.assertTrue(1 <= count <= 10, f"{alias} {model.__name__}: {count}")
            for model in (
                MenuRecipe,
                DailyMenuRecipe,
                StockReceiptArticle,
                StockIssueArticle,
            ):
                self.assertTrue(model.objects.using(alias).exists(), model.__name__)
            receipts = StockReceipt.objects.using(alias)
            self.assertTrue(receipts.filter(approved=True).exists())
            self.assertTrue(receipts.filter(approved=False).exists())
            issues = StockIssue.objects.using(alias)
            self.assertTrue(issues.filter(approved=True).exists())
            self.assertTrue(issues.filter(approved=False).exists())
            dates = set(DailyMenu.objects.using(alias).values_list("date", flat=True))
            self.assertIn(timezone.localdate(), dates)
            self.assertIn(timezone.localdate() + timedelta(days=1), dates)
            self.assertTrue(
                Article.objects.using(alias).filter(on_stock__lt=1).exists(),
                "an article should be missing on stock",
            )

    @override_settings(KICOMA_DEMO_MODE=True, KICOMA_DEMO_SUPERUSER_PASSWORD="")
    def test_can_run_repeatedly(self):
        call_command("reset_demo", stdout=None)
        menus = DailyMenu.objects.count()
        call_command("reset_demo", stdout=None)
        self.assertEqual(DailyMenu.objects.count(), menus)
        self.assertEqual(User.objects.count(), len(DEMO_USERS))


@override_settings(
    KICOMA_DEMO_MODE=True,
    KICOMA_DEMO_PASSWORD="demo-pass",
    KICOMA_DEMO_SUPERUSER_PASSWORD="",
)
class DemoLanguageDatabaseTest(TestCase):
    databases = DEMO_DATABASES

    def setUp(self):
        call_command("reset_demo", stdout=None)

    def login(self, language, username):
        with translation.override(language):
            url = reverse("account_login")
        response = self.client.post(url, {"login": username, "password": "demo-pass"})
        self.assertEqual(response.status_code, 302)

    def articles(self, language):
        with translation.override(language):
            return self.client.get(reverse("kitchen:showArticles"))

    def test_english_visitor_sees_english_data(self):
        self.login("en", "stockkeeper")
        response = self.articles("en")
        self.assertContains(response, "Potatoes")
        self.assertNotContains(response, "Brambory")

    def test_czech_visitor_sees_czech_data(self):
        self.login("cs", "skladnik")
        response = self.articles("cs")
        self.assertContains(response, "Brambory")
        self.assertNotContains(response, "Potatoes")

    def test_switching_language_requires_new_login(self):
        self.login("cs", "skladnik")
        response = self.articles("en")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/en/accounts/login/", response.url)


class DemoModeWebTest(TestCase):
    databases = DEMO_DATABASES

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
