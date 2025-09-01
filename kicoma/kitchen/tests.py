from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import SimpleTestCase, TestCase
from django.test.client import Client
from django.urls import resolve, reverse

from kicoma.kitchen.models import UNIT, Article
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
        self.article_test("kitchen:printArticles")

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
