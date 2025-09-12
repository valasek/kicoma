from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import SimpleTestCase, TestCase
from django.test.client import Client
from django.urls import resolve, reverse

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


class TestUrl(SimpleTestCase):

    def test_article_create_view_is_resolved(self):
        url = reverse('kitchen:createArticle')
        self.assertEqual(resolve(url).func.view_class, ArticleCreateView)


class ViewTests(TestCase):

    def addGroup(self, user_name, group_name):
        self.group = Group(name=group_name)
        self.group.save()
        user_name.groups.add(self.group)
        user_name.save()

    def setUp(self):
        user = get_user_model()
        self.client = Client()
        self.user = user.objects.create_user('john', 'lennon@thebeatles.com', 'password')
        self.addGroup(self.user, "cook")
        self.addGroup(self.user, "chef")
        self.addGroup(self.user, "stockkeeper")

    def tearDown(self):
        self.user.delete()
        self.group.delete()

    private_urls = [
        "/kitchen/article/list",
        "/kitchen/article/restrictedlist",
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
        "/kitchen/report/articlesnotinrecipes"
    ]

    def test_access_private_urls_with_login(self):
        self.client.login(username='john', password='password')
        for url in self.private_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def article_test(self, test_url):
        self.client.login(username='john', password='password')
        article = Article.objects.create(
            article = "Test article",
            unit = UNIT[0][0],
            on_stock = 0,
            min_on_stock = 0,
            total_price = 10,
            comment = "Comment"
        )
        response = self.client.get(reverse(test_url))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, article.article)
        article.delete()

    def test_article_read_views(self):
        self.article_test("kitchen:showArticles")
        self.article_test("kitchen:showRestrictedArticles")
        self.article_test("kitchen:showRestrictedArticles")
        # self.article_test("kitchen:printArticles")

    def test_update_article(self):
        self.client.login(username='john', password='password')
        article = Article.objects.create(
            article = "Test article",
            unit = UNIT[0][0],
            on_stock = 0,
            min_on_stock = 0,
            total_price = 10,
            comment = "Comment"
        )
        response = self.client.get(reverse('kitchen:updateArticle', args=(article.id,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, article.article)


class ModelBehaviorTests(TestCase):

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user('john', 'john@example.com', 'password')
        # Ensure a VAT record exists for receipt price calculations
        self.vat21 = VAT.objects.create(percentage=21, rate='high')

    def tearDown(self):
        self.user.delete()

    def test_article_average_price_from_stock(self):
        a = Article.objects.create(
            article="Flour",
            unit='kg',
            on_stock=10,
            total_price=200,  # avg = 20
        )
        self.assertEqual(a.average_price, 20)

    def test_article_average_price_from_latest_receipt_when_no_stock(self):
        a = Article.objects.create(article="Milk", unit='l', on_stock=0, total_price=0)
        sr = StockReceipt.objects.create(user_created=self.user)
        # older receipt
        StockReceiptArticle.objects.create(
            stock_receipt=sr,
            article=a,
            amount=1,
            unit='l',
            price_without_vat=10,
            vat=self.vat21,
        )
        # newer receipt (higher id) with different price
        StockReceiptArticle.objects.create(
            stock_receipt=sr,
            article=a,
            amount=1,
            unit='l',
            price_without_vat=20,
            vat=self.vat21,
        )
        # price_with_vat for newer = 20 * 1.21 = 24.2 -> rounded 24
        self.assertEqual(a.average_price, 24)

    def test_recipe_total_price_same_with_and_without_prefetch(self):
        # Article with stock-based average: average = total_price/on_stock = 100/5 = 20
        a = Article.objects.create(article="Sugar", unit='kg', on_stock=5, total_price=100)
        r = Recipe.objects.create(recipe="Cake", norm_amount=10)
        RecipeArticle.objects.create(recipe=r, article=a, amount=2, unit='kg')

        # Without prefetch
        direct_total = r.total_recipe_articles_price

        # With prefetch via queryset to set to_attr 'prefetched_recipe_articles'
        r2 = (
            Recipe.objects
            .filter(pk=r.pk)
            .prefetch_related(
                'recipearticle_set__article',
            )
            .first()
        )
        prefetched_total = r2.total_recipe_articles_price
        self.assertEqual(direct_total, prefetched_total)

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
        m_annot = Menu.objects.annotate(rc=Count('menurecipe')).get(pk=m.pk)
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
