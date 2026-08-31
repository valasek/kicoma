from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.test.client import Client
from django.urls import resolve, reverse

from kicoma.kitchen.forms import ArticleForm
from kicoma.kitchen.models import (
    UNIT,
    VAT,
    Article,
    Menu,
    MenuRecipe,
    Recipe,
    RecipeArticle,
    StockReceipt,
    StockReceiptArticle,
)
from kicoma.kitchen.views import ArticleCreateView


class ArticleFormRoleTests(TestCase):
    common_fields = {"article", "unit", "comment", "allergen"}
    stock_fields = {"on_stock", "min_on_stock", "total_price"}
    nutrition_fields = {
        "energy",
        "protein",
        "fat",
        "carbohydrates",
        "sugars",
        "fiber",
    }

    def create_user(self, group_name):
        user = get_user_model().objects.create_user(
            username=group_name,
            password="password",
        )
        user.groups.add(Group.objects.create(name=group_name))
        return user

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
                "protein": "12.3",
                "fat": "4.5",
                "carbohydrates": "67.8",
                "sugars": "9.1",
                "fiber": "2.3",
                "comment": "Nutrition updated",
            },
            instance=article,
            user=self.create_user("nutrition_advisor"),
        )

        self.assertEqual(
            set(form.fields), self.common_fields | self.nutrition_fields
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
    ]

    def test_access_private_urls_with_login(self):
        self.client.login(username="john", password="password")
        for url in self.private_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_docs_lists_users_in_each_role(self):
        self.user.is_superuser = True
        self.user.save()

        response = self.client.get(reverse("kitchen:docs"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode().count("john<br />"), 4)

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

                for url_name in all_links:
                    link = f'href="{reverse(f"kitchen:{url_name}")}"'
                    expected_count = 2 if url_name in allowed_links else 0
                    self.assertEqual(content.count(link), expected_count)

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
        for field_name in (
            "energy",
            "protein",
            "fat",
            "carbohydrates",
            "sugars",
            "fiber",
        ):
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
                "protein": "12.3",
                "fat": "4.5",
                "carbohydrates": "67.8",
                "sugars": "9.1",
                "fiber": "2.3",
                "comment": article.comment,
            },
        )
        self.assertRedirects(response, reverse("kitchen:showArticles"))
        article.refresh_from_db()
        self.assertEqual(article.energy, 1234)
        self.assertEqual(article.protein, Decimal("12.3"))
        self.assertEqual(article.fat, Decimal("4.5"))
        self.assertEqual(article.carbohydrates, Decimal("67.8"))
        self.assertEqual(article.sugars, Decimal("9.1"))
        self.assertEqual(article.fiber, Decimal("2.3"))

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
        for field_name in (
            "energy",
            "protein",
            "fat",
            "carbohydrates",
            "sugars",
            "fiber",
        ):
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
            "protein": Decimal("2.0"),
            "fat": Decimal("3.0"),
            "carbohydrates": Decimal("4.0"),
            "sugars": Decimal("5.0"),
            "fiber": Decimal("6.0"),
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
        self.assertEqual(totals["total_energy"], Decimal("350.0"))
        self.assertEqual(totals["total_protein"], Decimal("7.00"))
        self.assertEqual(totals["total_fat"], Decimal("10.50"))
        self.assertEqual(totals["total_carbohydrates"], Decimal("14.00"))
        self.assertEqual(totals["total_sugars"], Decimal("17.50"))
        self.assertEqual(totals["total_fiber"], Decimal("21.00"))
        self.assertContains(response, "Energie (kJ)")
        self.assertContains(response, "Celkem")
        self.assertContains(response, "350.0 kJ")
        self.assertContains(response, "7.0 g")
        self.assertContains(response, "310 Kč")
        self.assertNotContains(response, "celková cena:")
        self.assertNotContains(response, "Hidden")

    def test_article_nutrition_defaults_and_validators(self):
        article = Article(article="Nutrition", unit=UNIT[0][0])
        nutrition_fields = (
            "energy",
            "protein",
            "fat",
            "carbohydrates",
            "sugars",
            "fiber",
        )
        for field_name in nutrition_fields:
            self.assertEqual(getattr(article, field_name), 0)

        article.energy = -1
        article.protein = Decimal("-0.1")
        article.fat = Decimal("-0.1")
        article.carbohydrates = Decimal("-0.1")
        article.sugars = Decimal("-0.1")
        article.fiber = Decimal("-0.1")
        with self.assertRaises(ValidationError) as validation_error:
            article.full_clean()
        self.assertEqual(
            set(validation_error.exception.message_dict), set(nutrition_fields)
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
                protein=Decimal("2.0"),
            )
            recipe_article = RecipeArticle(
                recipe=recipe, article=article, amount=1, unit=unit
            )
            self.assertEqual(recipe_article.nutrition_factor, expected_factor)
            self.assertEqual(
                recipe_article.total_energy, Decimal("100") * expected_factor
            )
            self.assertEqual(
                recipe_article.total_protein, Decimal("2.0") * expected_factor
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
