import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.test.client import Client
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse
from django.utils import translation

from kicoma.kitchen.forms import ArticleForm
from kicoma.kitchen.models import (
    NUTRITION_FIELDS,
    UNIT,
    VAT,
    Article,
    DailyMenu,
    DailyMenuRecipe,
    MealGroup,
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
from kicoma.kitchen.views import ArticleCreateView


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

    def test_change_reason_is_truncated_to_the_history_column(self):
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
                totals[f"total_{field_name}"], Decimal(value) * Decimal("3.5")
            )
        self.assertContains(response, "Výživové údaje celkem")
        self.assertContains(response, "z toho nasycené mastné kyseliny")
        self.assertContains(response, "Celkem")
        self.assertContains(response, "nutrition-facts--total")
        self.assertContains(response, "350,0")
        self.assertContains(response, "38,5")
        self.assertNotContains(response, "<details")
        self.assertContains(response, "<span>kJ</span>", html=True)
        self.assertContains(response, "310 Kč")
        self.assertNotContains(response, "celková cena:")
        self.assertNotContains(response, "Hidden")

    def test_daily_menu_views_show_scaled_nutrition_totals(self):
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
        self.assertContains(list_response, "2\xa0500,0")
        list_table = list_response.context["table"]
        self.assertIn("nutrition", list_table.columns)
        list_record = next(iter(list_table.data))
        with CaptureQueriesContext(connection) as list_nutrition_queries:
            list_totals = list_record.nutrition_totals
        self.assertEqual(len(list_nutrition_queries), 0)
        for field_name, value in nutrition.items():
            self.assertEqual(
                list_totals[field_name],
                Decimal(value) * Decimal("2.5"),
            )

        detail_response = self.client.get(
            reverse("kitchen:showDailyMenuRecipes", args=[daily_menu.pk])
        )
        detail_table = detail_response.context["table"]
        self.assertIn("nutrition", detail_table.columns)
        detail_records = {record.recipe: record for record in detail_table.data}
        with CaptureQueriesContext(connection) as detail_nutrition_queries:
            detail_totals = {
                recipe: record.nutrition_totals
                for recipe, record in detail_records.items()
            }
        self.assertEqual(len(detail_nutrition_queries), 0)
        for field_name, value in nutrition.items():
            self.assertEqual(
                detail_totals[first_recipe][field_name],
                Decimal(value) * Decimal("1.5"),
            )
            self.assertEqual(
                detail_totals[second_recipe][field_name],
                Decimal(value),
            )
            self.assertEqual(
                detail_table.pinned_data["bottom"][0]["nutrition_totals"][field_name],
                Decimal(value) * Decimal("2.5"),
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

    def tearDown(self):
        self.user.delete()

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
        # price_with_vat for newer = 20 * 1.21 = 24.2 -> rounded 24
        self.assertEqual(a.average_price, 24)

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
            "ks": Decimal("1"),
        }

        for unit, expected_factor in expected_factors.items():
            article = Article.objects.create(
                article=f"Nutrition {unit}",
                unit=unit,
                energy=100,
                saturated_fat=Decimal("2.0"),
            )
            recipe_article = RecipeArticle(
                recipe=recipe, article=article, amount=1, unit=unit
            )
            self.assertEqual(recipe_article.nutrition_factor, expected_factor)
            self.assertEqual(
                recipe_article.total_energy, Decimal("100") * expected_factor
            )
            self.assertEqual(
                recipe_article.total_saturated_fat,
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
