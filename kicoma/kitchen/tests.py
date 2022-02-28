from django.test import TestCase
import urllib.parse


class ViewTests(TestCase):

    private_urls = [
        "/kitchen/article/list",
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
        "/kitchen/dailymenu/print",

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
        "/kitchen/report/print/cateringunit",
        "/kitchen/report/incorrectunits",
        "/kitchen/report/articlesnotinrecipes"
    ]

    def test_public_urls(self):
        public_urls = [
            "/",
            "/kitchen/about",
            "/kitchen/changelog",
            "/kitchen/docs",
        ]
        for url in public_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_private_urls_redirect_to_login(self):
        for url in self.private_urls:
            response = self.client.get(url)
            self.assertRedirects(response, "/accounts/login/?next="+urllib.parse.quote(url), status_code=302,
                                 target_status_code=200, msg_prefix='', fetch_redirect_response=True)
            # self.assertEqual(response.status_code, 302, msg=url)
