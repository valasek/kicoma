import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from crispy_forms.utils import render_crispy_form
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.models import ProtectedError
from django.test import RequestFactory, SimpleTestCase, TestCase, TransactionTestCase
from django.test.client import Client
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse
from django.utils import timezone, translation
from tablib import Dataset

from kicoma.kitchen.admin import (
    ArticleAdmin,
    ArticleResource,
    StockIssueAdmin,
    StockIssueArticleAdmin,
    StockIssueArticleResource,
    VATAdmin,
    VATResource,
)
from kicoma.kitchen.forms import (
    ArticleForm,
    RecipeArticleForm,
    RecipeForm,
    StockArticlesExportForm,
    StockIssueArticleForm,
    StockReceiptArticleForm,
)
from kicoma.kitchen.functions import format_unit_price
from kicoma.kitchen.models import (
    NUTRITION_FIELDS,
    UNIT,
    VAT,
    Article,
    DailyMenu,
    DailyMenuRecipe,
    MealGroup,
    MealType,
    Menu,
    MenuRecipe,
    Recipe,
    RecipeArticle,
    StockIssue,
    StockIssueArticle,
    StockReceipt,
    StockReceiptArticle,
)
from kicoma.kitchen.permissions import user_has_any_role
from kicoma.kitchen.views import ArticleCreateView, stock_issues_receipts_data


class ArticleFormRoleTests(TestCase):
    common_fields = {"article", "unit", "comment", "allergen"}
    stock_fields = {"on_stock", "min_on_stock", "total_price"}
    nutrition_fields = set(NUTRITION_FIELDS)

    def create_user(self, group_name):
        user = get_user_model().objects.create_user(
            username=group_name,
            password="password",
        )
        user.groups.add(Group.objects.create(name=group_name))
        return user

    def test_nutrition_fields_are_the_supported_set(self):
        self.assertEqual(
            NUTRITION_FIELDS,
            (
                "energy",
                "fat",
                "saturated_fat",
                "carbohydrates",
                "sugars",
                "fiber",
                "protein",
            ),
        )

    def test_stockkeeper_can_edit_only_stock_and_common_fields(self):
        form = ArticleForm(user=self.create_user("stockkeeper"))

        self.assertEqual(set(form.fields), self.common_fields | self.stock_fields)
        for field_name in self.stock_fields:
            self.assertNotIn("readonly", form.fields[field_name].widget.attrs)

    def test_nutrition_advisor_can_edit_only_nutrition_and_common_fields(self):
        article = Article.objects.create(
            article="Nutrition article",
            unit=UNIT[0][0],
            on_stock=10,
            min_on_stock=2,
            total_price=100,
        )
        form = ArticleForm(
            data={
                "article": article.article,
                "unit": article.unit,
                "on_stock": 999,
                "min_on_stock": 999,
                "total_price": 999,
                "energy": 1234,
                "fat": "4.5",
                "saturated_fat": "1.1",
                "carbohydrates": "67.8",
                "sugars": "9.1",
                "fiber": "2.3",
                "protein": "12.3",
                "comment": "Nutrition updated",
            },
            instance=article,
            user=self.create_user("nutrition_advisor"),
        )

        self.assertEqual(set(form.fields), self.common_fields | self.nutrition_fields)
        self.assertEqual(
            tuple(
                field_name
                for field_name in form.fields
                if field_name in NUTRITION_FIELDS
            ),
            NUTRITION_FIELDS,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        article.refresh_from_db()
        self.assertEqual(article.on_stock, Decimal("10"))
        self.assertEqual(article.min_on_stock, Decimal("2"))
        self.assertEqual(article.total_price, Decimal("100"))
        self.assertEqual(article.energy, 1234)

    def test_superuser_can_edit_stock_and_nutrition_with_or_without_groups(self):
        user = get_user_model().objects.create_superuser(
            "admin", "admin@example.com", "password"
        )
        article = Article.objects.create(article="Eggs", unit="ks")
        for grouped in (False, True):
            with self.subTest(grouped=grouped):
                if grouped:
                    user.groups.add(Group.objects.create(name="cook"))
                form = ArticleForm(
                    data={
                        "article": article.article,
                        "unit": "g",
                        "on_stock": "2",
                        "min_on_stock": "1",
                        "total_price": "20",
                        "energy": "100",
                        "piece_weight": "50",
                        "piece_weight_unit": "g",
                    },
                    instance=article,
                    user=user,
                )
                expected = (
                    self.common_fields
                    | self.stock_fields
                    | self.nutrition_fields
                    | set(ArticleForm.piece_fields)
                )
                self.assertEqual(set(form.fields), expected)
                rendered = render_crispy_form(form)
                for field_name in expected:
                    self.assertIn(f'name="{field_name}"', rendered)
                self.assertTrue(form.fields["unit"].disabled)
                self.assertTrue(form.is_valid(), form.errors)
                form.save()
                article.refresh_from_db()
                self.assertEqual(article.unit, "ks")
                self.assertEqual(article.on_stock, Decimal("2"))
                self.assertEqual(article.total_price, Decimal("20"))
                self.assertEqual(article.energy, 100)
                self.assertEqual(article.piece_weight, Decimal("50"))

    def test_user_without_roles_cannot_edit_stock_or_nutrition(self):
        user = get_user_model().objects.create_user("unprivileged")
        self.assertEqual(set(ArticleForm(user=user).fields), self.common_fields)

    def test_unit_is_editable_only_for_new_article(self):
        user = self.create_user("stockkeeper")
        self.assertFalse(ArticleForm(user=user).fields["unit"].disabled)

        article = Article.objects.create(
            article="Locked unit",
            unit="kg",
            on_stock=1,
            min_on_stock=0,
            total_price=10,
        )
        form = ArticleForm(
            data={
                "article": article.article,
                "unit": "g",
                "on_stock": 1,
                "min_on_stock": 0,
                "total_price": 10,
            },
            instance=article,
            user=user,
        )

        self.assertTrue(form.fields["unit"].disabled)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        article.refresh_from_db()
        self.assertEqual(article.unit, "kg")


class ArticleUnitLockTests(TestCase):
    def setUp(self):
        self.article = Article.objects.create(
            article="Mouka", unit="kg", on_stock=1, min_on_stock=0, total_price=10
        )

    def import_article(self, unit, name="Mouka", pk=None):
        dataset = Dataset(headers=["id", "article", "unit"])
        dataset.append([pk or "", name, unit])
        return ArticleResource().import_data(dataset, dry_run=False)

    def test_import_with_changed_unit_is_rejected(self):
        result = self.import_article("g", pk=self.article.pk)

        self.assertTrue(result.has_validation_errors())
        self.article.refresh_from_db()
        self.assertEqual(self.article.unit, "kg")

    def test_import_with_same_unit_and_new_article_is_allowed(self):
        same_unit = self.import_article("kg", name="Mouka 2", pk=self.article.pk)
        self.assertFalse(same_unit.has_validation_errors())
        result = self.import_article("ks", name="Vejce")

        self.assertFalse(result.has_errors() or result.has_validation_errors())
        self.assertEqual(Article.objects.get(article="Vejce").unit, "ks")

    def test_admin_unit_is_readonly_on_change(self):
        model_admin = ArticleAdmin(Article, AdminSite())

        self.assertNotIn("unit", model_admin.get_readonly_fields(None))
        self.assertIn("unit", model_admin.get_readonly_fields(None, self.article))


class TestUrl(SimpleTestCase):
    def test_article_create_view_is_resolved(self):
        url = reverse("kitchen:createArticle")
        self.assertEqual(resolve(url).func.view_class, ArticleCreateView)


class StockUpdateTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="stockkeeper",
            password="password",
        )

    def create_article(self, name):
        return Article.objects.create(
            article=name,
            unit="kg",
            on_stock=10,
            min_on_stock=0,
            total_price=100,
        )

    def create_stock_issue(self, article_count):
        stock_issue = StockIssue.objects.create(user_created=self.user)
        articles = []
        for index in range(article_count):
            article = self.create_article(f"Article {stock_issue.pk}-{index}")
            StockIssueArticle.objects.create(
                stock_issue=stock_issue,
                article=article,
                amount=1,
                unit="kg",
                average_unit_price=10,
            )
            articles.append(article)
        return stock_issue, articles

    def create_stock_receipt(self, article_count):
        vat = VAT.objects.create(percentage=article_count, rate=f"rate {article_count}")
        stock_receipt = StockReceipt.objects.create(user_created=self.user)
        for index in range(article_count):
            StockReceiptArticle.objects.create(
                stock_receipt=stock_receipt,
                article=self.create_article(f"Receipt {stock_receipt.pk}-{index}"),
                amount=1,
                unit="kg",
                price_without_vat=10,
                vat=vat,
            )
        return stock_receipt

    def test_stock_update_query_count_does_not_scale_with_articles(self):
        single_issue, _ = self.create_stock_issue(1)
        double_issue, articles = self.create_stock_issue(2)

        with CaptureQueriesContext(connection) as single_queries:
            StockIssue.update_article_on_stock(single_issue.pk, "Lunch", False)
        with CaptureQueriesContext(connection) as double_queries:
            StockIssue.update_article_on_stock(double_issue.pk, "Lunch", False)

        self.assertEqual(len(double_queries), len(single_queries))
        for article in articles:
            article.refresh_from_db()
            self.assertEqual(article.on_stock, Decimal("9"))
            self.assertEqual(article.total_price, Decimal("90"))
            self.assertEqual(article.history.count(), 2)
            self.assertTrue(
                article.history.first().history_change_reason.endswith("Lunch")
            )

    def test_stock_update_sums_repeated_rows_for_the_same_article(self):
        stock_issue, articles = self.create_stock_issue(1)
        article = articles[0]
        StockIssueArticle.objects.create(
            stock_issue=stock_issue,
            article=article,
            amount=3,
            unit="kg",
            average_unit_price=10,
        )

        StockIssue.update_article_on_stock(stock_issue.pk, "Lunch", False)

        article.refresh_from_db()
        self.assertEqual(article.on_stock, Decimal("6"))
        self.assertEqual(article.total_price, Decimal("60"))
        self.assertEqual(article.history.count(), 2)

    def test_receipt_in_other_unit_adds_line_value_once(self):
        article = self.create_article("Mouka")
        stock_receipt = StockReceipt.objects.create(user_created=self.user)
        StockReceiptArticle.objects.create(
            stock_receipt=stock_receipt,
            article=article,
            amount=500,
            unit="g",
            price_without_vat=100,
            vat=VAT.objects.create(percentage=0, rate="zero"),
        )

        StockReceipt.update_article_on_stock(stock_receipt.pk, "Delivery")

        article.refresh_from_db()
        self.assertEqual(article.on_stock, Decimal("10.5"))
        self.assertEqual(article.total_price, Decimal("150"))

    def test_issue_in_other_unit_removes_line_value_once(self):
        stock_issue, articles = self.create_stock_issue(1)
        line = stock_issue.stockissuearticle_set.get()
        line.amount = 2000
        line.unit = "g"
        line.save()

        StockIssue.update_article_on_stock(stock_issue.pk, "Lunch", False)

        article = articles[0]
        article.refresh_from_db()
        self.assertEqual(article.on_stock, Decimal("8"))
        self.assertEqual(article.total_price, Decimal("80"))
        stock_issue, articles = self.create_stock_issue(1)

        StockIssue.update_article_on_stock(stock_issue.pk, "x" * 200, False)

        reason = articles[0].history.first().history_change_reason
        self.assertEqual(len(reason), 100)

    def test_receipt_stock_update_query_count_does_not_scale_with_articles(self):
        single_receipt = self.create_stock_receipt(1)
        double_receipt = self.create_stock_receipt(2)

        with CaptureQueriesContext(connection) as single_queries:
            StockReceipt.update_article_on_stock(single_receipt.pk, "Delivery")
        with CaptureQueriesContext(connection) as double_queries:
            StockReceipt.update_article_on_stock(double_receipt.pk, "Delivery")

        self.assertEqual(len(double_queries), len(single_queries))
        for article in Article.objects.filter(
            stockreceiptarticle_set__stock_receipt=double_receipt
        ):
            self.assertEqual(article.on_stock, Decimal("11"))
            self.assertEqual(article.total_price, Decimal("110"))

    def test_average_price_update_query_count_does_not_scale_with_articles(self):
        single_issue, _ = self.create_stock_issue(1)
        double_issue, _ = self.create_stock_issue(2)

        with CaptureQueriesContext(connection) as single_queries:
            StockIssue.update_stock_issue_article_average_unit_price(single_issue.pk)
        with CaptureQueriesContext(connection) as double_queries:
            StockIssue.update_stock_issue_article_average_unit_price(double_issue.pk)

        self.assertEqual(len(double_queries), len(single_queries))
        self.assertEqual(
            list(
                double_issue.stockissuearticle_set.values_list(
                    "average_unit_price", flat=True
                )
            ),
            [Decimal("10"), Decimal("10")],
        )

    def test_average_price_uses_latest_receipt_for_empty_stock(self):
        stock_issue, articles = self.create_stock_issue(1)
        article = articles[0]
        article.on_stock = 0
        article.total_price = 0
        article.save()
        vat = VAT.objects.create(percentage=20, rate="basic")
        stock_receipt = StockReceipt.objects.create(user_created=self.user)
        StockReceiptArticle.objects.create(
            stock_receipt=stock_receipt,
            article=article,
            amount=1,
            unit="kg",
            price_without_vat=10,
            vat=vat,
        )

        StockIssue.update_stock_issue_article_average_unit_price(stock_issue.pk)

        stock_issue_article = stock_issue.stockissuearticle_set.get()
        self.assertEqual(stock_issue_article.average_unit_price, Decimal("12"))


class RolePermissionTests(TestCase):
    role_urls = {
        "/kitchen/stockreceipt/list": ("stockkeeper",),
        "/kitchen/stockissue/list": ("cook", "stockkeeper"),
        "/kitchen/article/list": ("stockkeeper", "nutrition_advisor"),
        "/kitchen/recipe/list": ("cook", "nutrition_advisor"),
        "/kitchen/dailymenu/list": ("cook", "nutrition_advisor"),
        "/kitchen/report/stockbyunit": (
            "cook",
            "stockkeeper",
            "nutrition_advisor",
        ),
    }

    def make_user(self, username, roles=()):
        user = get_user_model().objects.create_user(
            username, f"{username}@example.com", "password"
        )
        for role in roles:
            group, _ = Group.objects.get_or_create(name=role)
            user.groups.add(group)
        return user

    def test_signed_in_user_without_any_role_is_denied(self):
        self.client.force_login(self.make_user("norole"))

        for url in self.role_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_each_role_reaches_only_its_own_urls(self):
        for role in ("cook", "stockkeeper", "nutrition_advisor"):
            self.client.force_login(self.make_user(f"user_{role}", (role,)))
            for url, allowed_roles in self.role_urls.items():
                with self.subTest(role=role, url=url):
                    expected = 200 if role in allowed_roles else 403
                    self.assertEqual(self.client.get(url).status_code, expected)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get("/kitchen/article/list")

        self.assertEqual(response.status_code, 302)

    def test_superuser_without_roles_has_access(self):
        user = self.make_user("root")
        user.is_superuser = True
        user.save()
        self.client.force_login(user)

        for url in self.role_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_unknown_role_name_raises_instead_of_hiding_silently(self):
        with self.assertRaises(ValueError):
            user_has_any_role(self.make_user("typo"), "stockkeper")

    def test_role_lookup_is_cached_per_user_instance(self):
        user = self.make_user("cached", ("cook",))

        with CaptureQueriesContext(connection) as ctx:
            for _unused in range(5):
                user_has_any_role(user, "cook,stockkeeper")

        self.assertEqual(len(ctx.captured_queries), 1)


class ViewTests(TestCase):
    def addGroup(self, user_name, group_name):
        group, _ = Group.objects.get_or_create(name=group_name)
        user_name.groups.add(group)

    def setUp(self):
        user = get_user_model()
        self.client = Client()
        self.user = user.objects.create_user(
            "john", "lennon@thebeatles.com", "password"
        )
        self.addGroup(self.user, "cook")
        self.addGroup(self.user, "nutrition_advisor")
        self.addGroup(self.user, "stockkeeper")

    def test_create_menu_prefills_latest_saved_name(self):
        self.client.force_login(self.user)
        url = reverse("kitchen:createMenu")
        self.assertIsNone(self.client.get(url).context["form"]["menu"].value())

        meal_type = MealType.objects.create(meal_type="Lunch")
        Menu.objects.create(menu="Earlier menu", meal_type=meal_type)
        Menu.objects.create(menu="Latest menu", meal_type=meal_type)

        response = self.client.get(url)
        self.assertEqual(response.context["form"]["menu"].value(), "Latest menu")

        response = self.client.post(url, {"menu": "New menu"})
        self.assertEqual(response.context["form"]["menu"].value(), "New menu")

    private_urls = [
        "/kitchen/article/list",
        "/kitchen/article/listlack",
        "/kitchen/article/create",
        # "/kitchen/article/update/<int:pk>",
        # "/kitchen/article/restrictedupdate/<int:pk>",
        # "/kitchen/article/delete/<int:pk>",
        "/kitchen/article/print",
        "/kitchen/article/export",
        "/kitchen/article/import",
        # "/kitchen/article/history/<int:pk>",
        "/kitchen/article/stockprint",
        "/kitchen/stockissue/list",
        # "/kitchen/stockissue/articlelist/<int:pk>",
        "/kitchen/stockissue/create",
        "/kitchen/stockissue/createfrommenu",
        # "/kitchen/stockissue/createarticle/<int:pk>",
        # "/kitchen/stockissue/update/<int:pk>",
        # "/kitchen/stockissue/refresh/<int:pk>",
        # "/kitchen/stockissue/updatearticle/<int:pk>",
        # "/kitchen/stockissue/delete/<int:pk>",
        # "/kitchen/stockissue/deletearticle/<int:pk>",
        # "/kitchen/stockissue/print/<int:pk>",
        # "/kitchen/stockissue/approve/<int:pk>",
        "/kitchen/stockreceipt/list",
        # "/kitchen/stockreceipt/articlelist/<int:pk>",
        "/kitchen/stockreceipt/create",
        # "/kitchen/stockreceipt/createarticle/<int:pk>",
        # "/kitchen/stockreceipt/update/<int:pk>",
        # "/kitchen/stockreceipt/updatearticle/<int:pk>",
        # "/kitchen/stockreceipt/delete/<int:pk>",
        # "/kitchen/stockreceipt/deletearticle/<int:pk>",
        # "/kitchen/stockreceipt/print/<int:pk>",
        # "/kitchen/stockreceipt/approve/<int:pk>",
        "/kitchen/recipe/list",
        # "/kitchen/recipe/articlelist/<int:pk>",
        "/kitchen/recipe/create",
        # "/kitchen/recipe/createarticle/<int:pk>",
        # "/kitchen/recipe/update/<int:pk>",
        # "/kitchen/recipe/updatearticle/<int:pk>",
        # "/kitchen/recipe/delete/<int:pk>",
        # "/kitchen/recipe/deletearticle/<int:pk>",
        # "/kitchen/recipe/print/<int:pk>",
        "/kitchen/recipe/print",
        "/kitchen/dailymenu/list",
        # "/kitchen/dailymenu/recipelist/<int:pk>",
        "/kitchen/dailymenu/create",
        # "/kitchen/dailymenu/createrecipe/<int:pk>",
        # "/kitchen/dailymenu/update/<int:pk>",
        # "/kitchen/dailymenu/updaterecipe/<int:pk>",
        # "/kitchen/dailymenu/delete/<int:pk>",
        # "/kitchen/dailymenu/deleterecipe/<int:pk>",
        "/kitchen/dailymenu/filterprint",
        # "/kitchen/dailymenu/print", - doplnit date argument
        "/kitchen/menu/list",
        # "/kitchen/menu/recipelist/<int:pk>",
        "/kitchen/menu/create",
        # "/kitchen/menu/createrecipe/<int:pk>",
        # "/kitchen/menu/update/<int:pk>",
        # "/kitchen/menu/updaterecipe/<int:pk>",
        # "/kitchen/menu/delete/<int:pk>",
        # "/kitchen/menu/deleterecipe/<int:pk>",
        "/kitchen/report/showFoodConsumptionTotalPrice",
        "/kitchen/report/filtercateringunit",
        # "/kitchen/report/print/cateringunit", - doplnit date argument
        "/kitchen/report/incorrectunits",
        "/kitchen/report/articlesnotinrecipes",
        "/kitchen/report/stockbyunit",
    ]

    def test_access_private_urls_with_login(self):
        self.client.login(username="john", password="password")
        for url in self.private_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_create_stock_issue_from_menu_displays_unit_conversion_error(self):
        self.client.login(username="john", password="password")
        conversion_error = ValidationError("Není možné provést konverzi 125.00 g na ks")

        with (
            patch(
                "kicoma.kitchen.views.DailyMenu.objects.filter", return_value=[object()]
            ),
            patch(
                "kicoma.kitchen.views.StockIssue.create_from_daily_menu",
                side_effect=conversion_error,
            ),
        ):
            response = self.client.post(
                reverse("kitchen:createStockIssueFromDailyMenu"),
                {"date": "2026-09-08"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Není možné provést konverzi 125.00 g na ks")
        self.assertContains(
            response,
            'href="/kitchen/report/incorrectunits"',
        )
        self.assertContains(
            response,
            "kontaktujte uživatele ve skupině Skladník nebo Výživový poradce",
        )

        with (
            patch(
                "kicoma.kitchen.views.DailyMenu.objects.filter", return_value=[object()]
            ),
            patch(
                "kicoma.kitchen.views.StockIssue.create_from_daily_menu",
                side_effect=conversion_error,
            ),
            translation.override("en"),
        ):
            response = self.client.post(
                reverse("kitchen:createStockIssueFromDailyMenu"),
                {"date": "2026-09-08"},
            )

        self.assertContains(response, "Stock issue cannot be created")
        self.assertContains(response, "incorrect units report")
        self.assertContains(response, 'href="/en/kitchen/report/incorrectunits"')
        self.assertContains(
            response,
            "contact a user in the Stockkeeper or Nutrition advisor group",
        )

    def test_incorrect_units_report_includes_stock_document_articles(self):
        self.client.login(username="john", password="password")
        article = Article.objects.create(
            article="Incorrect historical unit",
            unit="kg",
            on_stock=0,
            total_price=0,
        )
        stock_issue = StockIssue.objects.create(user_created=self.user)
        StockIssueArticle.objects.create(
            stock_issue=stock_issue,
            article=article,
            amount=1,
            unit="ks",
            average_unit_price=10,
        )
        vat = VAT.objects.create(percentage=21, rate="standard")
        stock_receipt = StockReceipt.objects.create(user_created=self.user)
        StockReceiptArticle.objects.create(
            stock_receipt=stock_receipt,
            article=article,
            amount=1,
            unit="ks",
            price_without_vat=10,
            vat=vat,
        )

        response = self.client.get(reverse("kitchen:showIncorrectUnits"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Incorrect historical unit")
        self.assertContains(
            response,
            reverse("kitchen:showStockIssueArticles", args=[stock_issue.pk]),
        )
        self.assertContains(
            response,
            reverse("kitchen:showStockReceiptArticles", args=[stock_receipt.pk]),
        )
        self.assertNotContains(response, "Všechny jednotky jsou zadány správně")

    def test_stock_by_unit_report_shows_overview_and_selected_goods(self):
        self.client.login(username="john", password="password")
        flour = Article.objects.create(
            article="Flour",
            unit="kg",
            on_stock=Decimal("2.5"),
            total_price=0,
        )
        Article.objects.create(
            article="Salt",
            unit="kg",
            on_stock=Decimal("1.5"),
            total_price=0,
        )
        Article.objects.create(
            article="Empty bottle",
            unit="ks",
            on_stock=0,
            total_price=0,
        )

        overview = self.client.get(reverse("kitchen:showStockByUnit"))

        self.assertEqual(overview.status_code, 200)
        self.assertEqual(overview.context["total_articles"], 3)
        self.assertEqual(
            overview.context["units"],
            [
                {
                    "value": "kg",
                    "label": "kg",
                    "unit": "kg",
                    "article_count": 2,
                    "total_on_stock": Decimal("4"),
                },
                {
                    "value": "ks",
                    "label": "ks",
                    "unit": "ks",
                    "article_count": 1,
                    "total_on_stock": Decimal("0"),
                },
            ],
        )
        self.assertNotContains(overview, "Flour")

        detail = self.client.get(reverse("kitchen:showStockByUnit"), {"unit": "kg"})

        self.assertContains(detail, "Flour")
        self.assertContains(detail, "Salt")
        self.assertNotContains(detail, "Empty bottle")
        self.assertContains(detail, reverse("kitchen:updateArticle", args=[flour.pk]))

    def test_total_price_report_redirects_on_incorrect_historical_unit(self):
        self.client.login(username="john", password="password")
        article = Article.objects.create(
            article="Incorrect historical unit",
            unit="kg",
            on_stock=0,
            total_price=0,
        )
        stock_issue = StockIssue.objects.create(
            user_created=self.user,
            approved=True,
            date_approved=date.today(),
        )
        StockIssueArticle.objects.create(
            stock_issue=stock_issue,
            article=article,
            amount=1,
            unit="ks",
            average_unit_price=10,
        )

        response = self.client.get(reverse("kitchen:showFoodConsumptionTotalPrice"))

        self.assertRedirects(
            response,
            reverse("kitchen:showIncorrectUnits"),
            fetch_redirect_response=False,
        )
        message = next(iter(response.wsgi_request._messages))
        self.assertIn("Není možné provést konverzi 1.00 ks na kg", str(message))

    def test_docs_lists_users_in_each_role(self):
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)

        response = self.client.get(reverse("kitchen:docs"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode().count("john<br />"), 4)

    def test_docs_does_not_list_users_for_anonymous_visitors(self):
        response = self.client.get(reverse("kitchen:docs"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "john")
        self.assertNotContains(response, "Uživatelé")

    def test_docs_links_follow_menu_role_visibility(self):
        role_links = {
            "stockkeeper": {
                "showArticles",
                "showStockReceipts",
                "createStockIssueFromDailyMenu",
                "showStockIssues",
            },
            "cook": {
                "createStockIssueFromDailyMenu",
                "showStockIssues",
                "showRecipes",
                "showDailyMenus",
            },
            "nutrition_advisor": {
                "showArticles",
                "showRecipes",
                "showDailyMenus",
            },
        }
        all_links = set().union(*role_links.values())
        self.client.force_login(self.user)

        for role, allowed_links in role_links.items():
            with self.subTest(role=role):
                self.user.groups.clear()
                self.addGroup(self.user, role)
                response = self.client.get(reverse("kitchen:docs"))
                content = response.content.decode()

                handbook = content.split('<div class="container-fluid">', 1)[1]
                for url_name in all_links:
                    link = f'href="{reverse(f"kitchen:{url_name}")}"'
                    if url_name in allowed_links:
                        self.assertIn(link, handbook)
                    else:
                        self.assertNotIn(link, handbook)

                self.assertNotContains(
                    response,
                    f'href="{reverse("admin:index")}kitchen/article"',
                    html=True,
                )

    def test_superuser_sees_admin_menu_items(self):
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        self.client.login(username="john", password="password")

        response = self.client.get(reverse("kitchen:about"))

        self.assertContains(response, reverse("admin:index"))
        self.assertContains(response, reverse("kitchen:export"))
        self.assertContains(response, reverse("kitchen:import"))
        self.assertContains(response, reverse("kitchen:data_cleanup"))

    def test_non_superuser_cannot_access_admin_data_views(self):
        self.client.login(username="john", password="password")

        for url_name in ("export", "import", "data_cleanup"):
            response = self.client.get(reverse(f"kitchen:{url_name}"))
            self.assertEqual(response.status_code, 403)

    def article_test(self, test_url):
        self.client.login(username="john", password="password")
        article = Article.objects.create(
            article="Test article",
            unit=UNIT[0][0],
            on_stock=0,
            min_on_stock=0,
            total_price=10,
            comment="Comment",
        )
        response = self.client.get(reverse(test_url))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, article.article)
        article.delete()

    def test_article_read_views(self):
        self.article_test("kitchen:showArticles")
        # self.article_test("kitchen:printArticles")

    def test_update_article(self):
        self.client.login(username="john", password="password")
        article = Article.objects.create(
            article="Test article",
            unit=UNIT[0][0],
            on_stock=0,
            min_on_stock=0,
            total_price=10,
            comment="Comment",
        )
        response = self.client.get(reverse("kitchen:updateArticle", args=(article.id,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, article.article)
        self.assertContains(response, "Výživové údaje")
        for field_name in NUTRITION_FIELDS:
            self.assertContains(response, f'name="{field_name}"')

        response = self.client.post(
            reverse("kitchen:updateArticle", args=(article.id,)),
            {
                "article": article.article,
                "unit": article.unit,
                "on_stock": article.on_stock,
                "min_on_stock": article.min_on_stock,
                "total_price": article.total_price,
                "energy": 1234,
                "fat": "4.5",
                "saturated_fat": "1.1",
                "carbohydrates": "67.8",
                "sugars": "9.1",
                "fiber": "2.3",
                "protein": "12.3",
                "comment": article.comment,
            },
        )
        self.assertRedirects(response, reverse("kitchen:showArticles"))
        article.refresh_from_db()
        self.assertEqual(article.energy, 1234)
        self.assertEqual(article.fat, Decimal("4.5"))
        self.assertEqual(article.saturated_fat, Decimal("1.1"))
        self.assertEqual(article.carbohydrates, Decimal("67.8"))
        self.assertEqual(article.sugars, Decimal("9.1"))
        self.assertEqual(article.fiber, Decimal("2.3"))
        self.assertEqual(article.protein, Decimal("12.3"))

    def test_update_article_with_blank_nutrition(self):
        self.client.login(username="john", password="password")
        article = Article.objects.create(
            article="Blank nutrition article",
            unit=UNIT[0][0],
            carbohydrates=Decimal("5.0"),
        )
        response = self.client.post(
            reverse("kitchen:updateArticle", args=(article.id,)),
            {
                "article": article.article,
                "unit": article.unit,
                "on_stock": article.on_stock,
                "min_on_stock": "",
                "total_price": article.total_price,
                "energy": "737",
                "protein": "20.7",
                "fat": "9.8",
                "carbohydrates": "",
                "sugars": "0.0",
                "fiber": "0.0",
                "comment": "",
            },
        )
        self.assertRedirects(response, reverse("kitchen:showArticles"))
        article.refresh_from_db()
        self.assertIsNone(article.carbohydrates)
        self.assertEqual(article.min_on_stock, Decimal("0"))

    def test_non_nutrition_advisor_cannot_view_or_update_article_nutrition(self):
        self.user.groups.remove(Group.objects.get(name="nutrition_advisor"))
        self.client.login(username="john", password="password")
        article = Article.objects.create(
            article="Restricted nutrition",
            unit=UNIT[0][0],
            energy=100,
            protein=Decimal("1.0"),
            fat=Decimal("2.0"),
            carbohydrates=Decimal("3.0"),
            sugars=Decimal("4.0"),
            fiber=Decimal("5.0"),
        )
        update_url = reverse("kitchen:updateArticle", args=(article.id,))

        response = self.client.get(update_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Výživové údaje")
        for field_name in NUTRITION_FIELDS:
            self.assertNotContains(response, f'name="{field_name}"')

        response = self.client.post(
            update_url,
            {
                "article": article.article,
                "unit": article.unit,
                "on_stock": article.on_stock,
                "min_on_stock": article.min_on_stock,
                "total_price": article.total_price,
                "energy": 999,
                "protein": "9.9",
                "fat": "9.9",
                "carbohydrates": "9.9",
                "sugars": "9.9",
                "fiber": "9.9",
                "comment": "Allowed change",
            },
        )
        self.assertRedirects(response, reverse("kitchen:showArticles"))
        article.refresh_from_db()
        self.assertEqual(article.comment, "Allowed change")
        self.assertEqual(article.energy, 100)
        self.assertEqual(article.protein, Decimal("1.0"))
        self.assertEqual(article.fat, Decimal("2.0"))
        self.assertEqual(article.carbohydrates, Decimal("3.0"))
        self.assertEqual(article.sugars, Decimal("4.0"))
        self.assertEqual(article.fiber, Decimal("5.0"))

    def test_recipe_article_list_shows_nutrition_and_totals(self):
        self.client.login(username="john", password="password")
        recipe = Recipe.objects.create(recipe="Nutrition recipe", norm_amount=4)
        nutrition = {
            "energy": 100,
            "fat": Decimal("2.0"),
            "saturated_fat": Decimal("3.0"),
            "carbohydrates": Decimal("6.0"),
            "sugars": Decimal("7.0"),
            "fiber": Decimal("10.0"),
            "protein": Decimal("11.0"),
        }
        grams = Article.objects.create(
            article="Grams nutrition",
            unit="g",
            on_stock=100,
            total_price=200,
            **nutrition,
        )
        pieces = Article.objects.create(
            article="Pieces nutrition",
            unit="ks",
            on_stock=10,
            total_price=50,
            piece_weight=100,
            piece_weight_unit="g",
            **nutrition,
        )
        RecipeArticle.objects.create(
            recipe=recipe, article=grams, amount=150, unit="g", comment="Hidden"
        )
        RecipeArticle.objects.create(
            recipe=recipe, article=pieces, amount=2, unit="ks", comment="Hidden"
        )

        url = reverse("kitchen:showRecipeArticles", args=(recipe.id,))
        response = self.client.get(f"{url}?per_page=1")

        self.assertEqual(response.status_code, 200)
        table = response.context["table"]
        self.assertEqual(table.paginator.per_page, 1)
        self.assertNotIn("comment", table.columns)
        totals = table.pinned_data["bottom"][0]
        self.assertEqual(totals["total_average_price"], 310)
        for field_name, value in nutrition.items():
            self.assertEqual(
                totals["nutrition_per_portion"][field_name],
                Decimal(value) * Decimal("3.5") / 4,
            )
        with CaptureQueriesContext(connection) as ingredient_queries:
            for recipe_article in table.data:
                for field_name, value in nutrition.items():
                    self.assertEqual(
                        recipe_article.nutrition_per_portion[field_name],
                        Decimal(value) * recipe_article.nutrition_factor / 4,
                    )
        self.assertEqual(len(ingredient_queries), 0)
        with CaptureQueriesContext(connection) as price_queries:
            view_totals = response.context["view"].get_table_kwargs()
        self.assertEqual(len(price_queries), 0)
        self.assertEqual(view_totals["total_average_price"], 310)
        self.assertContains(response, "Výživové údaje na 1 porci")
        self.assertContains(response, "z toho nasycené mastné kyseliny")
        self.assertContains(response, "Celkem")
        self.assertContains(response, "nutrition-facts--total")
        self.assertContains(response, "87,5")
        self.assertContains(response, "9,6")
        self.assertNotContains(response, "<details")
        self.assertContains(response, "<span>kJ</span>", html=True)
        self.assertContains(response, "310 Kč")
        self.assertNotContains(response, "celková cena:")
        self.assertNotContains(response, "Hidden")

    def test_zero_serving_recipe_nutrition_does_not_divide_by_zero(self):
        self.client.login(username="john", password="password")
        article = Article.objects.create(article="No servings", unit="g", energy=100)
        recipe = Recipe.objects.create(recipe="Zero servings", norm_amount=0)
        RecipeArticle.objects.create(
            recipe=recipe, article=article, amount=100, unit="g"
        )
        recipe_response = self.client.get(
            reverse("kitchen:showRecipeArticles", args=[recipe.pk])
        )
        self.assertEqual(recipe_response.status_code, 200)
        with CaptureQueriesContext(connection) as no_receipt_queries:
            recipe_response.context["view"].get_table_kwargs()
        self.assertEqual(len(no_receipt_queries), 0)
        self.assertEqual(
            recipe_response.context["table"].pinned_data["bottom"][0][
                "nutrition_per_portion"
            ]["energy"],
            0,
        )

        daily_menu = DailyMenu.objects.create(
            date=date.today(),
            meal_group=MealGroup.objects.create(meal_group="No servings"),
            meal_type_id=MealTypeFactory.ensure(),
        )
        DailyMenuRecipe.objects.create(daily_menu=daily_menu, recipe=recipe, amount=1)
        list_response = self.client.get(reverse("kitchen:showDailyMenus"))
        self.assertEqual(list_response.status_code, 200)
        list_record = next(iter(list_response.context["table"].data))
        self.assertEqual(list_record.nutrition_per_portion["energy"], 0)
        detail_response = self.client.get(
            reverse("kitchen:showDailyMenuRecipes", args=[daily_menu.pk])
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(
            detail_response.context["table"].pinned_data["bottom"][0][
                "nutrition_per_portion"
            ]["energy"],
            0,
        )

    def test_daily_menu_list_shows_nutrition_only_to_advisors(self):
        article = Article.objects.create(
            article="Role-specific nutrition", unit="g", energy=1000
        )
        recipe = Recipe.objects.create(recipe="Role-specific recipe", norm_amount=1)
        RecipeArticle.objects.create(
            recipe=recipe, article=article, amount=100, unit="g"
        )
        daily_menu = DailyMenu.objects.create(
            date=date.today(),
            meal_group=MealGroup.objects.create(meal_group="Residents"),
            meal_type_id=MealTypeFactory.ensure(),
        )
        DailyMenuRecipe.objects.create(daily_menu=daily_menu, recipe=recipe, amount=1)
        url = reverse("kitchen:showDailyMenus")
        self.user.groups.remove(Group.objects.get(name="nutrition_advisor"))
        self.client.force_login(self.user)

        cook_response = self.client.get(url)
        self.assertNotIn("nutrition", cook_response.context["table"].columns)
        self.assertNotContains(cook_response, "Výživové údaje na 1 porci")
        self.assertNotContains(cook_response, "nutrition-facts--total")

        self.user.groups.remove(Group.objects.get(name="cook"))
        self.addGroup(self.user, "nutrition_advisor")
        advisor_response = self.client.get(url)
        self.assertIn("nutrition", advisor_response.context["table"].columns)
        self.assertContains(advisor_response, "Výživové údaje na 1 porci")
        self.assertContains(advisor_response, "1\xa0000,0")

    def test_daily_menu_recipe_list_shows_nutrition_only_to_advisors(self):
        article = Article.objects.create(
            article="Role-specific nutrition", unit="g", energy=1000
        )
        recipe = Recipe.objects.create(recipe="Role-specific recipe", norm_amount=1)
        RecipeArticle.objects.create(
            recipe=recipe, article=article, amount=100, unit="g"
        )
        daily_menu = DailyMenu.objects.create(
            date=date.today(),
            meal_group=MealGroup.objects.create(meal_group="Residents"),
            meal_type_id=MealTypeFactory.ensure(),
        )
        DailyMenuRecipe.objects.create(daily_menu=daily_menu, recipe=recipe, amount=1)
        url = reverse("kitchen:showDailyMenuRecipes", args=[daily_menu.pk])
        self.user.groups.remove(Group.objects.get(name="nutrition_advisor"))
        self.client.force_login(self.user)

        cook_response = self.client.get(url)
        cook_table = cook_response.context["table"]
        self.assertNotIn("nutrition", cook_table.columns)
        self.assertIsNone(cook_table.get_bottom_pinned_data())
        self.assertNotContains(cook_response, "Výživové údaje na 1 porci")
        self.assertNotContains(cook_response, "nutrition-facts")

        self.user.groups.remove(Group.objects.get(name="cook"))
        self.addGroup(self.user, "nutrition_advisor")
        advisor_response = self.client.get(url)
        advisor_table = advisor_response.context["table"]
        self.assertIn("nutrition", advisor_table.columns)
        self.assertIsNotNone(advisor_table.get_bottom_pinned_data())
        self.assertContains(advisor_response, "Výživové údaje na 1 porci")
        self.assertContains(advisor_response, "nutrition-facts--total")
        self.assertContains(advisor_response, "1\xa0000,0")

    def test_daily_menu_views_show_nutrition_per_portion(self):
        self.client.login(username="john", password="password")
        nutrition = {
            "energy": 1000,
            "fat": Decimal("2.0"),
            "saturated_fat": Decimal("1.0"),
            "carbohydrates": Decimal("4.0"),
            "sugars": Decimal("3.0"),
            "fiber": Decimal("5.0"),
            "protein": Decimal("6.0"),
        }
        article = Article.objects.create(
            article="Daily menu nutrition",
            unit="g",
            **nutrition,
        )
        first_recipe = Recipe.objects.create(recipe="First course", norm_amount=4)
        second_recipe = Recipe.objects.create(recipe="Second course", norm_amount=2)
        RecipeArticle.objects.create(
            recipe=first_recipe,
            article=article,
            amount=100,
            unit="g",
        )
        RecipeArticle.objects.create(
            recipe=second_recipe,
            article=article,
            amount=200,
            unit="g",
        )
        daily_menu = DailyMenu.objects.create(
            date=date.today(),
            meal_group=MealGroup.objects.create(meal_group="Residents"),
            meal_type_id=MealTypeFactory.ensure(),
        )
        DailyMenuRecipe.objects.create(
            daily_menu=daily_menu,
            recipe=first_recipe,
            amount=6,
        )
        DailyMenuRecipe.objects.create(
            daily_menu=daily_menu,
            recipe=second_recipe,
            amount=1,
        )

        list_response = self.client.get(reverse("kitchen:showDailyMenus"))
        self.assertContains(list_response, "1\xa0250,0")
        self.assertNotContains(list_response, "2\xa0500,0")
        list_table = list_response.context["table"]
        self.assertIn("nutrition", list_table.columns)
        list_record = next(iter(list_table.data))
        with CaptureQueriesContext(connection) as list_nutrition_queries:
            list_totals = list_record.nutrition_per_portion
        self.assertEqual(len(list_nutrition_queries), 0)
        for field_name, value in nutrition.items():
            self.assertEqual(
                list_totals[field_name],
                Decimal(value) * Decimal("1.25"),
            )

        detail_response = self.client.get(
            reverse("kitchen:showDailyMenuRecipes", args=[daily_menu.pk])
        )
        detail_table = detail_response.context["table"]
        self.assertIn("nutrition", detail_table.columns)
        self.assertContains(detail_response, "Výživové údaje na 1 porci")
        detail_records = {record.recipe: record for record in detail_table.data}
        with CaptureQueriesContext(connection) as detail_nutrition_queries:
            detail_totals = {
                recipe: record.nutrition_per_portion
                for recipe, record in detail_records.items()
            }
        self.assertEqual(len(detail_nutrition_queries), 0)
        for field_name, value in nutrition.items():
            self.assertEqual(
                detail_totals[first_recipe][field_name],
                Decimal(value) / 4,
            )
            self.assertEqual(
                detail_totals[second_recipe][field_name],
                Decimal(value),
            )
            self.assertEqual(
                detail_table.pinned_data["bottom"][0]["nutrition_per_portion"][
                    field_name
                ],
                Decimal(value) * Decimal("1.25"),
            )

        unserved_recipe = Recipe.objects.create(recipe="Unserved course", norm_amount=1)
        RecipeArticle.objects.create(
            recipe=unserved_recipe, article=article, amount=100, unit="g"
        )
        DailyMenuRecipe.objects.create(
            daily_menu=daily_menu, recipe=unserved_recipe, amount=0
        )
        zero_list_response = self.client.get(reverse("kitchen:showDailyMenus"))
        self.assertContains(zero_list_response, "1\xa0250,0")
        zero_response = self.client.get(
            reverse("kitchen:showDailyMenuRecipes", args=[daily_menu.pk])
        )
        unserved_record = next(
            record
            for record in zero_response.context["table"].data
            if record.recipe == unserved_recipe
        )
        for field_name, value in nutrition.items():
            self.assertEqual(unserved_record.nutrition_per_portion[field_name], 0)
            self.assertEqual(
                zero_response.context["table"].pinned_data["bottom"][0][
                    "nutrition_per_portion"
                ][field_name],
                Decimal(value) * Decimal("1.25"),
            )

    def test_article_nutrition_defaults_and_validators(self):
        article = Article(article="Nutrition", unit=UNIT[0][0])
        for field_name in NUTRITION_FIELDS:
            self.assertEqual(getattr(article, field_name), 0)

        for field_name in NUTRITION_FIELDS:
            value = -1 if field_name == "energy" else Decimal("-0.1")
            setattr(article, field_name, value)
        with self.assertRaises(ValidationError) as validation_error:
            article.full_clean()
        self.assertEqual(
            set(validation_error.exception.message_dict), set(NUTRITION_FIELDS)
        )


class ModelBehaviorTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            "john", "john@example.com", "password"
        )
        # Ensure a VAT record exists for receipt price calculations
        self.vat21 = VAT.objects.create(percentage=21, rate="high")

    def test_article_average_price_from_stock(self):
        a = Article.objects.create(
            article="Flour",
            unit="kg",
            on_stock=10,
            total_price=200,  # avg = 20
        )
        self.assertEqual(a.average_price, 20)

    def test_article_average_price_from_latest_receipt_when_no_stock(self):
        a = Article.objects.create(article="Milk", unit="l", on_stock=0, total_price=0)
        sr = StockReceipt.objects.create(user_created=self.user)
        # older receipt
        StockReceiptArticle.objects.create(
            stock_receipt=sr,
            article=a,
            amount=1,
            unit="l",
            price_without_vat=10,
            vat=self.vat21,
        )
        # newer receipt (higher id) with different price
        StockReceiptArticle.objects.create(
            stock_receipt=sr,
            article=a,
            amount=1,
            unit="l",
            price_without_vat=20,
            vat=self.vat21,
        )
        # price_with_vat for newer = 20 * 1.21 = 24.2, kept to 4 decimal places
        self.assertEqual(a.average_price, Decimal("24.2"))

    def test_recipe_total_price_same_with_and_without_prefetch(self):
        # Article with stock-based average: average = total_price/on_stock = 100/5 = 20
        a = Article.objects.create(
            article="Sugar", unit="kg", on_stock=5, total_price=100
        )
        r = Recipe.objects.create(recipe="Cake", norm_amount=10)
        RecipeArticle.objects.create(recipe=r, article=a, amount=2, unit="kg")

        # Without prefetch
        direct_total = r.total_recipe_articles_price

        # With prefetch via queryset to set to_attr 'prefetched_recipe_articles'
        r2 = (
            Recipe.objects.filter(pk=r.pk)
            .prefetch_related(
                "recipearticle_set__article",
            )
            .first()
        )
        prefetched_total = r2.total_recipe_articles_price
        self.assertEqual(direct_total, prefetched_total)

    def test_recipe_article_nutrition_uses_amount_and_unit(self):
        recipe = Recipe.objects.create(recipe="Mixed units", norm_amount=1)
        expected_factors = {
            "kg": Decimal("10"),
            "g": Decimal("0.01"),
            "l": Decimal("10"),
            "ml": Decimal("0.01"),
            "ks": Decimal("0.5"),
        }

        for unit, expected_factor in expected_factors.items():
            article = Article.objects.create(
                article=f"Nutrition {unit}",
                unit=unit,
                energy=100,
                saturated_fat=Decimal("2.0"),
                piece_weight=Decimal("50") if unit == "ks" else None,
                piece_weight_unit="g" if unit == "ks" else None,
            )
            recipe_article = RecipeArticle(
                recipe=recipe, article=article, amount=1, unit=unit
            )
            self.assertEqual(recipe_article.nutrition_factor, expected_factor)
            self.assertEqual(
                recipe_article.nutrition_totals["energy"],
                Decimal("100") * expected_factor,
            )
            self.assertEqual(
                recipe_article.nutrition_totals["saturated_fat"],
                Decimal("2.0") * expected_factor,
            )

    def test_menu_recipe_count_property_with_and_without_annotation(self):
        m = Menu.objects.create(menu="Lunch", meal_type_id=MealTypeFactory.ensure())
        r1 = Recipe.objects.create(recipe="Soup", norm_amount=10)
        r2 = Recipe.objects.create(recipe="Stew", norm_amount=10)
        MenuRecipe.objects.create(menu=m, recipe=r1, amount=10)
        MenuRecipe.objects.create(menu=m, recipe=r2, amount=10)

        # Plain instance (no annotation)
        m_plain = Menu.objects.get(pk=m.pk)
        self.assertEqual(m_plain.recipe_count, 2)

        # Annotated instance uses annotated field (rc)
        from django.db.models import Count

        m_annot = Menu.objects.annotate(rc=Count("menurecipe")).get(pk=m.pk)
        self.assertEqual(m_annot.recipe_count, 2)


class HighPriorityFixTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("jane", password="password")
        for name in ("cook", "stockkeeper", "nutrition_advisor"):
            self.user.groups.add(Group.objects.get_or_create(name=name)[0])
        self.client.force_login(self.user)
        self.vat = VAT.objects.create(percentage=0, rate="zero")

    # H1
    def test_gram_article_average_price_is_not_rounded_to_zero(self):
        article = Article.objects.create(
            article="Sul", unit="g", on_stock=1000, total_price=50
        )

        self.assertEqual(article.average_price, Decimal("0.05"))

    def test_receipt_keeps_four_decimal_unit_price(self):
        article = Article.objects.create(article="Koreni", unit="g")
        line = StockReceiptArticle.objects.create(
            stock_receipt=StockReceipt.objects.create(user_created=self.user),
            article=article,
            amount=200,
            unit="g",
            price_without_vat=Decimal("0.0125"),
            vat=self.vat,
        )
        line.refresh_from_db()

        self.assertEqual(line.price_without_vat, Decimal("0.0125"))
        self.assertEqual(line.total_price_with_vat, Decimal("2"))

    def test_unit_price_is_shown_with_two_decimals(self):
        with translation.override("en"):
            self.assertEqual(format_unit_price(Decimal("0.0500")), "0.05")
            self.assertEqual(format_unit_price(Decimal("0.0125")), "0.01")
            self.assertEqual(format_unit_price(Decimal("0.005")), "0.01")
            self.assertEqual(format_unit_price(Decimal("1234.5")), "1,234.50")
            self.assertEqual(format_unit_price(Decimal("12")), "12.00")

    def test_stock_issue_article_list_shows_two_decimal_unit_price(self):
        article = Article.objects.create(article="Maso", unit="kg")
        stock_issue = StockIssue.objects.create(user_created=self.user)
        StockIssueArticle.objects.create(
            stock_issue=stock_issue,
            article=article,
            amount=1,
            unit="kg",
            average_unit_price=Decimal("12.3456"),
        )

        response = self.client.get(
            reverse("kitchen:showStockIssueArticles", args=[stock_issue.pk])
        )

        self.assertContains(response, "12,35 Kč / kg")
        self.assertNotContains(response, "12,3456")

    # H2
    def test_article_name_is_escaped_in_messages(self):
        response = self.client.post(
            reverse("kitchen:createArticle"),
            {
                "article": "<b>x</b>",
                "unit": "kg",
                "on_stock": 0,
                "min_on_stock": 0,
                "total_price": 0,
            },
            follow=True,
        )

        self.assertContains(response, "&lt;b&gt;x&lt;/b&gt;")
        self.assertNotContains(response, "<b>x</b>")

    def test_issue_approval_errors_are_escaped(self):
        article = Article.objects.create(
            article="<i>y</i>", unit="kg", on_stock=1, total_price=10
        )
        stock_issue = StockIssue.objects.create(user_created=self.user)
        StockIssueArticle.objects.create(
            stock_issue=stock_issue,
            article=article,
            amount=5,
            unit="kg",
            average_unit_price=10,
        )

        response = self.client.post(
            reverse("kitchen:approveStockIssue", args=[stock_issue.pk]), follow=True
        )

        self.assertContains(response, "&lt;i&gt;y&lt;/i&gt; - na výdejce 5")
        self.assertNotContains(response, "<i>y</i>")
        stock_issue.refresh_from_db()
        self.assertFalse(stock_issue.approved)

    # H3
    def test_article_with_documents_cannot_be_deleted(self):
        article = Article.objects.create(article="Mouka", unit="kg")
        StockReceiptArticle.objects.create(
            stock_receipt=StockReceipt.objects.create(user_created=self.user),
            article=article,
            amount=1,
            unit="kg",
            price_without_vat=10,
            vat=self.vat,
        )

        response = self.client.post(reverse("kitchen:deleteArticle", args=[article.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Article.objects.filter(pk=article.pk).exists())
        with self.assertRaises(ProtectedError):
            article.delete()

    def test_article_on_stock_cannot_be_deleted(self):
        article = Article.objects.create(
            article="Cukr", unit="kg", on_stock=1, total_price=20
        )

        self.client.post(reverse("kitchen:deleteArticle", args=[article.pk]))

        self.assertTrue(Article.objects.filter(pk=article.pk).exists())

    def test_unused_empty_article_can_be_deleted(self):
        article = Article.objects.create(article="Prazdne", unit="kg")

        self.client.post(reverse("kitchen:deleteArticle", args=[article.pk]))

        self.assertFalse(Article.objects.filter(pk=article.pk).exists())

    # H4
    def create_daily_menu(self, menu_date):
        article = Article.objects.create(
            article="Brambory", unit="kg", on_stock=10, total_price=100
        )
        recipe = Recipe.objects.create(recipe="Pure", norm_amount=10)
        RecipeArticle.objects.create(
            recipe=recipe, article=article, amount=1, unit="kg"
        )
        daily_menu = DailyMenu.objects.create(
            date=menu_date,
            meal_group=MealGroup.objects.create(meal_group="Deti"),
            meal_type_id=MealTypeFactory.ensure(),
        )
        DailyMenuRecipe.objects.create(daily_menu=daily_menu, recipe=recipe, amount=20)

    def test_refresh_parses_legacy_cs_and_en_comments(self):
        menu_date = date(2026, 10, 4)
        self.create_daily_menu(menu_date)
        creator = get_user_model().objects.create_user("creator")
        for comment in ("Pro 04.10.2026", "For 10/04/2026", "Pro 2026-10-04"):
            with self.subTest(comment=comment):
                stock_issue = StockIssue.objects.create(
                    user_created=creator, comment=comment
                )

                response = self.client.post(
                    reverse("kitchen:refreshStockIssue", args=[stock_issue.pk])
                )

                self.assertEqual(response.status_code, 302)
                self.assertFalse(StockIssue.objects.filter(pk=stock_issue.pk).exists())
                refreshed = StockIssue.objects.get()
                self.assertEqual(refreshed.menu_date, menu_date)
                self.assertEqual(refreshed.user_created, creator)
                self.assertEqual(
                    refreshed.stockissuearticle_set.get().amount, Decimal("2")
                )
                refreshed.delete()

    def test_refresh_is_post_only(self):
        stock_issue = StockIssue.objects.create(
            user_created=self.user, menu_date=date(2026, 10, 4)
        )

        response = self.client.get(
            reverse("kitchen:refreshStockIssue", args=[stock_issue.pk])
        )

        self.assertEqual(response.status_code, 405)
        self.assertTrue(StockIssue.objects.filter(pk=stock_issue.pk).exists())

    def test_refresh_without_daily_menu_keeps_issue(self):
        stock_issue = StockIssue.objects.create(
            user_created=self.user, menu_date=date(2026, 10, 4)
        )

        self.client.post(reverse("kitchen:refreshStockIssue", args=[stock_issue.pk]))

        self.assertTrue(StockIssue.objects.filter(pk=stock_issue.pk).exists())

    # H5
    def create_piece_recipe(self, piece_weight=None):
        article = Article.objects.create(
            article="Vejce",
            unit="ks",
            energy=600,
            protein=Decimal("12.0"),
            piece_weight=piece_weight,
            piece_weight_unit="g" if piece_weight else None,
        )
        recipe = Recipe.objects.create(recipe="Omeleta", norm_amount=2)
        RecipeArticle.objects.create(
            recipe=recipe, article=article, amount=4, unit="ks"
        )
        return recipe

    def test_piece_line_uses_piece_weight(self):
        recipe = self.create_piece_recipe(piece_weight=Decimal("50"))

        # 4 pieces x 50 g = 200 g = 2 x 100 g, 2 portions
        self.assertEqual(recipe.nutrition_per_portion["energy"], Decimal("600"))
        self.assertEqual(recipe.nutrition_per_portion["protein"], Decimal("12"))
        self.assertEqual(recipe.nutrition_missing_articles, [])

    def test_piece_line_without_piece_weight_is_incomplete(self):
        recipe = self.create_piece_recipe()
        recipe_article = recipe.recipearticle_set.get()

        self.assertIsNone(recipe_article.nutrition_factor)
        self.assertTrue(recipe_article.nutrition_incomplete)
        self.assertEqual(recipe.nutrition_per_portion["energy"], Decimal("0"))
        self.assertEqual(recipe.nutrition_missing_articles, ["Vejce"])
        self.assertTrue(recipe_article.article.nutrition_needs_piece_weight)

        response = self.client.get(
            reverse("kitchen:showRecipeArticles", args=[recipe.pk])
        )
        self.assertContains(response, "chybí hmotnost kusu: Vejce")

    def test_daily_menu_nutrition_with_piece_article(self):
        recipe = self.create_piece_recipe(piece_weight=Decimal("50"))
        daily_menu = DailyMenu.objects.create(
            date=date(2026, 10, 4),
            meal_group=MealGroup.objects.create(meal_group="Deti"),
            meal_type_id=MealTypeFactory.ensure(),
        )
        DailyMenuRecipe.objects.create(daily_menu=daily_menu, recipe=recipe, amount=30)

        self.assertEqual(daily_menu.nutrition_per_portion["energy"], Decimal("600"))
        self.assertEqual(daily_menu.nutrition_missing_articles, [])

    def test_piece_article_with_nutrition_requires_piece_weight(self):
        data = {"article": "Rohlik", "unit": "ks", "on_stock": 0, "energy": 1200}
        form = ArticleForm(data=data, user=self.user)

        self.assertFalse(form.is_valid())
        self.assertIn("piece_weight", form.errors)
        self.assertIn("piece_weight_unit", form.errors)

        form = ArticleForm(
            data={**data, "piece_weight": 43, "piece_weight_unit": "g"}, user=self.user
        )
        self.assertTrue(form.is_valid(), form.errors)


class MediumPriorityFixTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("max", password="password")
        for name in ("cook", "stockkeeper", "nutrition_advisor"):
            self.user.groups.add(Group.objects.get_or_create(name=name)[0])
        self.client.force_login(self.user)

    def test_data_cleanup_deletes_old_records(self):
        superuser = get_user_model().objects.create_superuser(
            "root", "root@example.com", "password"
        )
        old_date = timezone.localdate().replace(year=timezone.localdate().year - 3)
        old_issue = StockIssue.objects.create(
            user_created=self.user, approved=True, date_approved=old_date
        )
        self.client.force_login(superuser)

        response = self.client.post(reverse("kitchen:data_cleanup"), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(StockIssue.objects.filter(pk=old_issue.pk).exists())
        self.assertContains(response, "Výdejky, úspěšne vymazáno: 1 záznamů")
        self.assertNotContains(response, "Chyba při mazání")

    def test_issue_approval_checks_stock_per_article(self):
        article = Article.objects.create(
            article="Mouka", unit="kg", on_stock=5, total_price=50
        )
        stock_issue = StockIssue.objects.create(user_created=self.user)
        for _index in range(2):
            StockIssueArticle.objects.create(
                stock_issue=stock_issue,
                article=article,
                amount=3,
                unit="kg",
                average_unit_price=10,
            )

        errors = StockIssue.update_article_on_stock(stock_issue.pk, "", True)

        self.assertEqual(len(errors), 1)
        self.assertIn("na výdejce 6", str(errors[0]))
        article.refresh_from_db()
        self.assertEqual(article.on_stock, Decimal("5"))

    def test_recipe_line_price_keeps_two_decimals(self):
        article = Article.objects.create(
            article="Sul", unit="g", on_stock=1000, total_price=50
        )
        recipe = Recipe.objects.create(recipe="Polevka", norm_amount=10)
        RecipeArticle.objects.create(recipe=recipe, article=article, amount=7, unit="g")
        RecipeArticle.objects.create(recipe=recipe, article=article, amount=3, unit="g")

        self.assertEqual(
            recipe.recipearticle_set.get(amount=7).total_average_price,
            Decimal("0.35"),
        )
        self.assertEqual(recipe.total_recipe_articles_price, Decimal("0.50"))

    def test_recipe_norm_amount_must_be_positive(self):
        form = RecipeForm(data={"recipe": "Nula", "norm_amount": 0})

        self.assertFalse(form.is_valid())
        self.assertIn("norm_amount", form.errors)

    def test_issue_from_daily_menu_with_zero_portions_recipe(self):
        article = Article.objects.create(article="Ryze", unit="kg")
        recipe = Recipe.objects.create(recipe="Rizoto", norm_amount=0)
        RecipeArticle.objects.create(
            recipe=recipe, article=article, amount=1, unit="kg"
        )
        daily_menu = DailyMenu.objects.create(
            date=date(2026, 10, 4),
            meal_group=MealGroup.objects.create(meal_group="Deti"),
            meal_type_id=MealTypeFactory.ensure(),
        )
        DailyMenuRecipe.objects.create(daily_menu=daily_menu, recipe=recipe, amount=5)

        with self.assertRaises(ValidationError):
            StockIssue.create_from_daily_menu(
                DailyMenu.objects.all(), "04.10.2026", self.user
            )
        self.assertFalse(StockIssue.objects.exists())

    def test_user_with_documents_cannot_be_deleted(self):
        StockIssue.objects.create(user_created=self.user)
        StockReceipt.objects.create(user_created=self.user, user_approved=self.user)

        with self.assertRaises(ProtectedError):
            self.user.delete()


class LowPriorityFixTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("eva", password="password")
        for name in ("cook", "stockkeeper", "nutrition_advisor"):
            self.user.groups.add(Group.objects.get_or_create(name=name)[0])
        self.client.force_login(self.user)
        self.vat = VAT.objects.create(percentage=0, rate="zero")
        self.superuser = get_user_model().objects.create_superuser(
            "root", "root@example.com", "password"
        )

    def approved_issue(self, article, amount, unit, date_approved=None, price=10):
        stock_issue = StockIssue.objects.create(
            user_created=self.user,
            approved=True,
            date_approved=date_approved or timezone.localdate(),
        )
        StockIssueArticle.objects.create(
            stock_issue=stock_issue,
            article=article,
            amount=amount,
            unit=unit,
            average_unit_price=price,
        )
        return stock_issue

    def test_line_amount_minimum_is_one_hundredth(self):
        article = Article.objects.create(article="Small quantity", unit="kg")
        for form_class in (
            RecipeArticleForm,
            StockReceiptArticleForm,
            StockIssueArticleForm,
        ):
            for amount in ("0.01", "0", "-0.01", "0.001"):
                with self.subTest(form=form_class.__name__, amount=amount):
                    form = form_class(
                        data={
                            "article": article.pk,
                            "amount": amount,
                            "unit": "kg",
                            "price_without_vat": "10",
                            "vat": self.vat.pk,
                        }
                    )
                    field = form._meta.model._meta.get_field("amount")
                    if amount == "0.01":
                        self.assertTrue(form.is_valid(), form.errors)
                        self.assertEqual(
                            field.clean(Decimal(amount), None), Decimal(amount)
                        )
                    else:
                        self.assertFalse(form.is_valid())
                        self.assertIn("amount", form.errors)
                        with self.assertRaises(ValidationError):
                            field.clean(Decimal(amount), None)

    def test_export_date_uses_the_current_timezone(self):
        cases = (
            (
                "Europe/Prague",
                datetime(2026, 10, 4, 23, 30, tzinfo=UTC),
                date(2026, 10, 5),
            ),
            (
                "America/Los_Angeles",
                datetime(2026, 10, 5, 0, 30, tzinfo=UTC),
                date(2026, 10, 4),
            ),
        )
        for zone, instant, local_day in cases:
            with (
                self.subTest(zone=zone),
                timezone.override(zone),
                patch("django.utils.timezone.datetime", wraps=datetime) as clock,
            ):
                clock.now.return_value = instant
                for day, valid in (
                    (local_day - timedelta(days=1), True),
                    (local_day, True),
                    (local_day + timedelta(days=1), False),
                ):
                    form = StockArticlesExportForm(data={"date": day.isoformat()})
                    self.assertEqual(form.is_valid(), valid, form.errors.as_data())
                    if not valid:
                        self.assertIn("date", form.errors)

    def test_monthly_report_starts_at_zero(self):
        data = stock_issues_receipts_data(0)

        self.assertEqual(data["stock_issues_price"], 0)
        self.assertEqual(data["stock_receipts_price"], 0)

    def test_generated_issue_skips_lines_rounding_to_zero(self):
        salt = Article.objects.create(article="Sul", unit="kg")
        rice = Article.objects.create(article="Ryze", unit="kg")
        recipe = Recipe.objects.create(recipe="Rizoto", norm_amount=100)
        RecipeArticle.objects.create(recipe=recipe, article=salt, amount=1, unit="g")
        RecipeArticle.objects.create(recipe=recipe, article=rice, amount=1000, unit="g")
        daily_menu = DailyMenu.objects.create(
            date=date(2026, 10, 4),
            meal_group=MealGroup.objects.create(meal_group="Deti"),
            meal_type_id=MealTypeFactory.ensure(),
        )
        DailyMenuRecipe.objects.create(daily_menu=daily_menu, recipe=recipe, amount=1)

        count = StockIssue.create_from_daily_menu(
            DailyMenu.objects.all(), "04.10.2026", self.user
        )

        self.assertEqual(count, 1)
        line = StockIssueArticle.objects.get()
        self.assertEqual(line.article, rice)
        self.assertEqual(line.amount, Decimal("0.01"))

    def test_issue_total_is_sum_of_rounded_lines(self):
        stock_issue = StockIssue.objects.create(user_created=self.user)
        for name in ("A", "B", "C"):
            StockIssueArticle.objects.create(
                stock_issue=stock_issue,
                article=Article.objects.create(
                    article=name, unit="kg", on_stock=10, total_price=100
                ),
                amount=Decimal("0.6"),
                unit="kg",
                average_unit_price=1,
            )

        # each line 0.6 Kc rounds to 1 Kc, the stock change is 3 Kc
        self.assertEqual(stock_issue.total_price, 3)

    def test_approval_checks_the_rounded_stock_deduction(self):
        article = Article.objects.create(
            article="Rounded stock",
            unit="kg",
            on_stock=Decimal("0.03"),
            total_price=30,
        )
        stock_issue = StockIssue.objects.create(user_created=self.user)
        for _index in range(4):
            StockIssueArticle.objects.create(
                stock_issue=stock_issue,
                article=article,
                amount=6,
                unit="g",
                average_unit_price=1000,
            )

        self.client.post(reverse("kitchen:approveStockIssue", args=[stock_issue.pk]))

        stock_issue.refresh_from_db()
        article.refresh_from_db()
        self.assertFalse(stock_issue.approved)
        self.assertEqual(article.on_stock, Decimal("0.03"))

    def test_approval_refreshes_prices_and_rolls_back_rejections(self):
        cases = (
            ("stale zero price", 10, 100, 0, 1, True),
            ("insufficient stock", 1, 100, 1, 2, False),
            ("refreshed zero price", 10, 0, 10, 1, False),
        )
        for name, stock, value, old_price, amount, approved in cases:
            with self.subTest(name=name):
                article = Article.objects.create(
                    article=name, unit="kg", on_stock=stock, total_price=value
                )
                stock_issue = StockIssue.objects.create(user_created=self.user)
                line = StockIssueArticle.objects.create(
                    stock_issue=stock_issue,
                    article=article,
                    amount=amount,
                    unit="kg",
                    average_unit_price=old_price,
                )
                history_count = article.history.count()

                response = self.client.post(
                    reverse("kitchen:approveStockIssue", args=[stock_issue.pk])
                )

                self.assertEqual(response.status_code, 302)
                stock_issue.refresh_from_db()
                article.refresh_from_db()
                line.refresh_from_db()
                self.assertEqual(stock_issue.approved, approved)
                if approved:
                    self.assertEqual(line.average_unit_price, Decimal("10"))
                    self.assertEqual(article.on_stock, Decimal("9"))
                    self.assertEqual(article.total_price, Decimal("90"))
                    self.assertEqual(stock_issue.user_approved, self.user)
                    self.assertEqual(stock_issue.date_approved, timezone.localdate())
                else:
                    self.assertEqual(line.average_unit_price, old_price)
                    self.assertEqual(article.on_stock, stock)
                    self.assertEqual(article.total_price, value)
                    self.assertEqual(article.history.count(), history_count)
                    self.assertIsNone(stock_issue.user_approved)
                    self.assertIsNone(stock_issue.date_approved)

    def test_generated_issue_rounds_after_summing_the_article(self):
        article = Article.objects.create(article="Small portions", unit="kg")
        recipe = Recipe.objects.create(recipe="Small portions", norm_amount=1)
        for _index in range(3):
            RecipeArticle.objects.create(
                recipe=recipe, article=article, amount=4, unit="g"
            )
        daily_menu = DailyMenu.objects.create(
            date=date(2026, 10, 4),
            meal_group=MealGroup.objects.create(meal_group="Small portions"),
            meal_type_id=MealTypeFactory.ensure(),
        )
        DailyMenuRecipe.objects.create(daily_menu=daily_menu, recipe=recipe, amount=1)

        count = StockIssue.create_from_daily_menu(
            DailyMenu.objects.all(), "04.10.2026", self.user
        )

        self.assertEqual(count, 1)
        self.assertEqual(StockIssueArticle.objects.get().amount, Decimal("0.01"))

    def test_receipt_approval_uses_local_date(self):
        article = Article.objects.create(article="Mouka", unit="kg")
        stock_receipt = StockReceipt.objects.create(user_created=self.user)
        StockReceiptArticle.objects.create(
            stock_receipt=stock_receipt,
            article=article,
            amount=1,
            unit="kg",
            price_without_vat=10,
            vat=self.vat,
        )
        local_day = date(2026, 10, 5)

        with patch("django.utils.timezone.localdate", return_value=local_day):
            self.client.post(
                reverse("kitchen:approveStockReceipt", args=[stock_receipt.pk])
            )

        stock_receipt.refresh_from_db()
        self.assertTrue(stock_receipt.approved)
        self.assertEqual(stock_receipt.date_approved, local_day)

    def test_user_profile_is_visible_only_to_owner_and_superuser(self):
        other = get_user_model().objects.create_user("other", password="password")
        other_url = reverse("users:detail", kwargs={"username": other.username})

        self.assertEqual(self.client.get(other_url).status_code, 404)
        own_url = reverse("users:detail", kwargs={"username": self.user.username})
        self.assertEqual(self.client.get(own_url).status_code, 200)
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get(other_url).status_code, 200)

    def test_admin_cannot_change_or_delete_approved_document_lines(self):
        article = Article.objects.create(article="Maso", unit="kg")
        approved = self.approved_issue(article, 1, "kg")
        open_issue = StockIssue.objects.create(user_created=self.user)
        open_line = StockIssueArticle.objects.create(
            stock_issue=open_issue, article=article, amount=1, unit="kg"
        )
        approved_line = StockIssueArticle.objects.get(stock_issue=approved)
        request = RequestFactory().get("/")
        request.user = self.superuser
        line_admin = StockIssueArticleAdmin(StockIssueArticle, AdminSite())
        issue_admin = StockIssueAdmin(StockIssue, AdminSite())

        self.assertFalse(line_admin.has_change_permission(request, approved_line))
        self.assertFalse(line_admin.has_delete_permission(request, approved_line))
        self.assertTrue(line_admin.has_change_permission(request, open_line))
        self.assertFalse(issue_admin.has_delete_permission(request, approved))
        self.assertIn("approved", issue_admin.get_readonly_fields(request, open_issue))

        with patch.object(line_admin, "message_user"):
            line_admin.delete_queryset(request, StockIssueArticle.objects.all())
        self.assertEqual(list(StockIssueArticle.objects.all()), [approved_line])

    def test_admin_import_cannot_change_approved_document_lines(self):
        article = Article.objects.create(article="Maso", unit="kg")
        line = StockIssueArticle.objects.get(
            stock_issue=self.approved_issue(article, 1, "kg")
        )
        dataset = StockIssueArticleResource().export(
            StockIssueArticle.objects.filter(pk=line.pk)
        )
        dataset.dict = [{**row, "amount": "5"} for row in dataset.dict]

        result = StockIssueArticleResource().import_data(dataset, dry_run=False)

        self.assertTrue(result.has_validation_errors() or result.has_errors())
        line.refresh_from_db()
        self.assertEqual(line.amount, Decimal("1"))

    def test_data_cleanup_keeps_unapproved_and_recent_documents(self):
        article = Article.objects.create(article="Mouka", unit="kg")
        old_date = timezone.localdate().replace(year=timezone.localdate().year - 2)
        old_approved = self.approved_issue(article, 1, "kg", date_approved=old_date)
        recent = self.approved_issue(
            article,
            1,
            "kg",
            date_approved=old_date.replace(year=old_date.year + 1),
        )
        old_open = StockIssue.objects.create(user_created=self.user)
        StockIssue.objects.filter(pk=old_open.pk).update(
            modified=timezone.now().replace(year=old_date.year - 1)
        )
        self.client.force_login(self.superuser)

        self.client.post(reverse("kitchen:data_cleanup"))

        self.assertFalse(StockIssue.objects.filter(pk=old_approved.pk).exists())
        self.assertTrue(StockIssue.objects.filter(pk=recent.pk).exists())
        self.assertTrue(StockIssue.objects.filter(pk=old_open.pk).exists())

    def test_vat_deletion_cannot_cascade_into_approved_receipts(self):
        receipt = StockReceipt.objects.create(user_created=self.user, approved=True)
        line = StockReceiptArticle.objects.create(
            stock_receipt=receipt,
            article=Article.objects.create(article="Protected VAT", unit="kg"),
            amount=1,
            unit="kg",
            price_without_vat=100,
            vat=self.vat,
        )

        with self.assertRaises(ProtectedError):
            self.vat.delete()

        self.assertTrue(StockReceiptArticle.objects.filter(pk=line.pk).exists())

    def test_vat_percentage_on_approved_receipts_is_locked_in_admin_and_import(self):
        receipt = StockReceipt.objects.create(user_created=self.user, approved=True)
        StockReceiptArticle.objects.create(
            stock_receipt=receipt,
            article=Article.objects.create(article="VAT history", unit="kg"),
            amount=1,
            unit="kg",
            price_without_vat=100,
            vat=self.vat,
        )
        request = RequestFactory().get("/")
        request.user = self.superuser
        vat_admin = VATAdmin(VAT, AdminSite())
        self.assertIn("percentage", vat_admin.get_readonly_fields(request, self.vat))
        dataset = VATResource().export(VAT.objects.filter(pk=self.vat.pk))
        dataset.dict = [{**row, "percentage": 21} for row in dataset.dict]

        result = VATResource().import_data(dataset, dry_run=False)

        self.assertTrue(result.has_validation_errors() or result.has_errors())
        self.vat.refresh_from_db()
        self.assertEqual(self.vat.percentage, 0)
        self.assertEqual(receipt.total_price, 100)

    def test_stock_export_skips_unconvertible_lines(self):
        article = Article.objects.create(
            article="Vejce", unit="kg", on_stock=5, total_price=50
        )
        self.approved_issue(article, 2, "kg")
        broken_issue = self.approved_issue(article, 3, "ks")
        valid_article = Article.objects.create(
            article="Valid stock", unit="kg", on_stock=5, total_price=50
        )
        self.approved_issue(valid_article, 2, "kg")
        receipt = StockReceipt.objects.create(
            user_created=self.user, approved=True, date_approved=timezone.localdate()
        )
        StockReceiptArticle.objects.create(
            stock_receipt=receipt,
            article=article,
            amount=1,
            unit="l",
            price_without_vat=10,
            vat=self.vat,
        )
        yesterday = timezone.localdate() - timedelta(days=1)

        response = self.client.post(
            reverse("kitchen:exportStockArticlesSelectedDay"),
            {"date": yesterday.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        exported = {
            row["article"]: row
            for row in Dataset().load(response.content, format="xlsx").dict
        }
        self.assertIsNone(exported[article.article]["on_stock"])
        self.assertIsNone(exported[article.article]["total_price"])
        self.assertIn(
            f"StockIssue #{broken_issue.pk}",
            exported[article.article]["export_warning"],
        )
        self.assertIn(
            f"StockReceipt #{receipt.pk}", exported[article.article]["export_warning"]
        )
        self.assertEqual(exported[valid_article.article]["on_stock"], 7)
        self.assertEqual(exported[valid_article.article]["total_price"], 70)
        warnings = [str(m) for m in response.wsgi_request._messages]
        self.assertTrue(any("Vejce - 3.00 ks" in m for m in warnings), warnings)


class DataImportExportTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            id=12,
            username="backup-admin",
            email="admin@example.com",
            password="password",
        )
        self.user.groups.add(Group.objects.create(name="backup-admins"))
        self.client.force_login(self.user)
        article = Article(
            article="Imported article",
            unit=UNIT[0][0],
            on_stock=0,
            min_on_stock=0,
            total_price=0,
        )
        article._history_user = self.user
        article.save()

    def test_full_export_import_preserves_users_and_history(self):
        article = Article.objects.get()
        vat = VAT.objects.create(percentage=12, rate="Protected VAT")
        receipt = StockReceipt.objects.create(
            user_created=self.user,
            user_approved=self.user,
            approved=True,
            date_approved=date(2026, 10, 4),
        )
        StockReceiptArticle.objects.create(
            stock_receipt=receipt,
            article=article,
            vat=vat,
            amount=1,
            unit=article.unit,
            price_without_vat=Decimal("12.3456"),
        )
        issue = StockIssue.objects.create(
            user_created=self.user,
            user_approved=self.user,
            approved=True,
            date_approved=date(2026, 10, 4),
        )
        StockIssueArticle.objects.create(
            stock_issue=issue,
            article=article,
            amount=1,
            unit=article.unit,
            average_unit_price=Decimal("13.8271"),
        )
        export_response = self.client.get(reverse("kitchen:export"))
        exported_objects = json.loads(export_response.content)
        exported_models = {item["model"] for item in exported_objects}

        self.assertIn("auth.group", exported_models)
        self.assertIn("users.user", exported_models)
        self.assertIn("kitchen.historicalarticle", exported_models)

        upload = SimpleUploadedFile(
            "data.json", export_response.content, content_type="application/json"
        )
        response = self.client.post(reverse("kitchen:import"), {"myfile": upload})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_model().objects.get(pk=12).username, "backup-admin")
        self.assertEqual(Article.objects.get().history.get().history_user_id, 12)
        self.assertTrue(StockReceipt.objects.get(pk=receipt.pk).approved)
        self.assertTrue(StockIssue.objects.get(pk=issue.pk).approved)
        self.assertEqual(StockReceiptArticle.objects.get().vat_id, vat.pk)
        self.assertEqual(
            StockReceiptArticle.objects.get().price_without_vat, Decimal("12.3456")
        )
        self.assertEqual(
            StockIssueArticle.objects.get().average_unit_price, Decimal("13.8271")
        )

    def test_failed_import_does_not_erase_existing_data(self):
        export_response = self.client.get(reverse("kitchen:export"))
        fixture_objects = json.loads(export_response.content)
        article_object = next(
            item for item in fixture_objects if item["model"] == "kitchen.article"
        )
        article_object["fields"]["allergen"] = [999]
        upload = SimpleUploadedFile(
            "invalid.json",
            json.dumps(fixture_objects).encode(),
            content_type="application/json",
        )

        response = self.client.post(reverse("kitchen:import"), {"myfile": upload})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_model().objects.get(pk=12).username, "backup-admin")
        self.assertTrue(Article.objects.filter(article="Imported article").exists())

    def test_full_import_loads_changed_unit_from_dump(self):
        export_response = self.client.get(reverse("kitchen:export"))
        fixture_objects = json.loads(export_response.content)
        for item in fixture_objects:
            if item["model"] == "kitchen.article":
                item["fields"]["unit"] = "ks"
        upload = SimpleUploadedFile(
            "data.json",
            json.dumps(fixture_objects).encode(),
            content_type="application/json",
        )

        response = self.client.post(reverse("kitchen:import"), {"myfile": upload})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Article.objects.get().unit, "ks")

    def test_full_import_does_not_store_dump_in_media_root(self):
        export_response = self.client.get(reverse("kitchen:export"))
        upload = SimpleUploadedFile(
            "data.json", export_response.content, content_type="application/json"
        )

        with patch("django.core.files.storage.FileSystemStorage.save") as save:
            response = self.client.post(reverse("kitchen:import"), {"myfile": upload})

        self.assertEqual(response.status_code, 200)
        save.assert_not_called()
        self.assertEqual(Article.objects.get().article, "Imported article")


# Helper factory for MealType to satisfy FK without importing fixtures
class MealTypeFactory:
    @staticmethod
    def ensure():
        from kicoma.kitchen.models import MealType

        obj = MealType.objects.first()
        if obj:
            return obj.id
        return MealType.objects.create(meal_type="Oběd").id


# HistoricalArticle
# StockIssueArticle
# StockReceiptArticle
# Recipe
# Article
# RecipeArticle, StockIssue, StockReceipt
# DailyMenu, Menu, MenuRecipe, DailyMenuRecipe

# seed
# Allergen
# MealType
# MealGroup
# VAT
