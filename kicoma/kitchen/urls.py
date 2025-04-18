from django.urls import path
from django.conf.urls import include
from django.views.generic import RedirectView

from .views import ArticleListView, ArticleRestrictedListView, ArticleHistoryDetailView, ArticleCreateView, \
    ArticleRestrictedUpdateView, ArticleUpdateView, ArticleDeleteView, \
    ArticlePDFView, ArticleLackListView, ArticleExportView, ArticleImportView
from .views import StockTakePDFView
from .views import StockReceiptListView, StockReceiptCreateView, StockReceiptUpdateView, \
    StockReceiptDeleteView, StockReceiptPDFView, StockReceiptApproveView
from .views import StockReceiptArticleListView, StockReceiptArticleCreateView, StockReceiptArticleUpdateView, \
    StockReceiptArticleDeleteView
from .views import StockIssueListView, StockIssueCreateView, StockIssueUpdateView, StockIssueRefreshView, \
    StockIssueDeleteView, StockIssuePDFView, StockIssueApproveView, StockIssueFromDailyMenuCreateView
from .views import StockIssueArticleListView, StockIssueArticleCreateView, StockIssueArticleUpdateView, \
    StockIssueArticleDeleteView
from .views import RecipeListView, RecipeCreateView, RecipeUpdateView, RecipeDeleteView, \
    RecipePDFView, RecipeListPDFView
from .views import RecipeArticleListView, RecipeArticleCreateView, RecipeArticleUpdateView, \
    RecipeArticleDeleteView
from .views import DailyMenuListView, DailyMenuCreateView, DailyMenuUpdateView, DailyMenuDeleteView, \
    DailyMenuPDFView, DailyMenuPrintView
from .views import MenuListView, MenuCreateView, MenuUpdateView, MenuDeleteView
from .views import MenuRecipeListView, MenuRecipeCreateView, MenuRecipeUpdateView, MenuRecipeDeleteView
from .views import DailyMenuRecipeListView, DailyMenuRecipeCreateView, DailyMenuRecipeUpdateView, \
    DailyMenuRecipeDeleteView
from .views import IncorrectUnitsListView, ArticlesNotInRecipesListView, ShowFoodConsumptionTotalPrice, \
    CateringUnitFilterView, CateringUnitShowView

from .views import about, changelog, docs, export_data, switch_language, ImportDataView, DataCleanUpView

app_name = "kitchen"
urlpatterns = [
    path('about', about, name='about'),
    path('changelog', changelog, name='changelog'),
    path('docs', docs, name='docs'),
    path('export', export_data, name='export'),
    path('import', ImportDataView.as_view(), name='import'),
    path('data_cleanup', DataCleanUpView.as_view(), name='data_cleanup'),
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicons/favicon.ico')),
    path('switchlang', switch_language, name='switchlang'),
    path('i18n', include('django.conf.urls.i18n'), name='i18n'),

    path('article/list', ArticleListView.as_view(), name='showArticles'),
    path('article/restrictedlist', ArticleRestrictedListView.as_view(), name='showRestrictedArticles'),
    path('article/listlack', ArticleLackListView.as_view(), name='showLackArticles'),
    path('article/create', ArticleCreateView.as_view(), name='createArticle'),
    path('article/update/<int:pk>', ArticleUpdateView.as_view(), name='updateArticle'),
    path('article/restrictedupdate/<int:pk>', ArticleRestrictedUpdateView.as_view(), name='restrictedupdateArticle'),
    path('article/delete/<int:pk>', ArticleDeleteView.as_view(), name='deleteArticle'),
    path('article/print', ArticlePDFView.as_view(), name='printArticles'),
    path('article/export', ArticleExportView.as_view(), name='exportArticles'),
    path('article/import', ArticleImportView.as_view(), name='importArticles'),
    path('article/history/<int:pk>', ArticleHistoryDetailView.as_view(), name='showArticleHistory'),

    path('article/stockprint', StockTakePDFView.as_view(), name='printStockArticles'),

    path('stockissue/list', StockIssueListView.as_view(), name='showStockIssues'),
    path('stockissue/articlelist/<int:pk>', StockIssueArticleListView.as_view(), name='showStockIssueArticles'),
    path('stockissue/create', StockIssueCreateView.as_view(), name='createStockIssue'),
    path('stockissue/createfrommenu', StockIssueFromDailyMenuCreateView.as_view(),
         name='createStockIssueFromDailyMenu'),
    path('stockissue/createarticle/<int:pk>', StockIssueArticleCreateView.as_view(), name='createStockIssueArticle'),
    path('stockissue/update/<int:pk>', StockIssueUpdateView.as_view(), name='updateStockIssue'),
    path('stockissue/refresh/<int:pk>', StockIssueRefreshView.as_view(), name='refreshStockIssue'),
    path('stockissue/updatearticle/<int:pk>', StockIssueArticleUpdateView.as_view(), name='updateStockIssueArticle'),
    path('stockissue/delete/<int:pk>', StockIssueDeleteView.as_view(), name='deleteStockIssue'),
    path('stockissue/deletearticle/<int:pk>', StockIssueArticleDeleteView.as_view(), name='deleteStockIssueArticle'),
    path('stockissue/print/<int:pk>', StockIssuePDFView.as_view(), name='printStockIssue'),
    path('stockissue/approve/<int:pk>', StockIssueApproveView.as_view(), name='approveStockIssue'),

    path('stockreceipt/list', StockReceiptListView.as_view(), name='showStockReceipts'),
    path('stockreceipt/articlelist/<int:pk>', StockReceiptArticleListView.as_view(), name='showStockReceiptArticles'),
    path('stockreceipt/create', StockReceiptCreateView.as_view(), name='createStockReceipt'),
    path('stockreceipt/createarticle/<int:pk>', StockReceiptArticleCreateView.as_view(),
         name='createStockReceiptArticle'),
    path('stockreceipt/update/<int:pk>', StockReceiptUpdateView.as_view(), name='updateStockReceipt'),
    path('stockreceipt/updatearticle/<int:pk>', StockReceiptArticleUpdateView.as_view(),
         name='updateStockReceiptArticle'),
    path('stockreceipt/delete/<int:pk>', StockReceiptDeleteView.as_view(), name='deleteStockReceipt'),
    path('stockreceipt/deletearticle/<int:pk>', StockReceiptArticleDeleteView.as_view(),
         name='deleteStockReceiptArticle'),
    path('stockreceipt/print/<int:pk>', StockReceiptPDFView.as_view(), name='printStockReceipt'),
    path('stockreceipt/approve/<int:pk>', StockReceiptApproveView.as_view(), name='approveStockReceipt'),

    path('recipe/list', RecipeListView.as_view(), name='showRecipes'),
    path('recipe/articlelist/<int:pk>', RecipeArticleListView.as_view(), name='showRecipeArticles'),
    path('recipe/create', RecipeCreateView.as_view(), name='createRecipe'),
    path('recipe/createarticle/<int:pk>', RecipeArticleCreateView.as_view(), name='createRecipeArticle'),
    path('recipe/update/<int:pk>', RecipeUpdateView.as_view(), name='updateRecipe'),
    path('recipe/updatearticle/<int:pk>', RecipeArticleUpdateView.as_view(), name='updateRecipeArticle'),
    path('recipe/delete/<int:pk>', RecipeDeleteView.as_view(), name='deleteRecipe'),
    path('recipe/deletearticle/<int:pk>', RecipeArticleDeleteView.as_view(), name='deleteRecipeArticle'),
    path('recipe/print/<int:pk>', RecipePDFView.as_view(), name='printRecipe'),
    path('recipe/print', RecipeListPDFView.as_view(), name='printRecipes'),

    path('dailymenu/list', DailyMenuListView.as_view(), name='showDailyMenus'),
    path('dailymenu/recipelist/<int:pk>', DailyMenuRecipeListView.as_view(), name='showDailyMenuRecipes'),
    path('dailymenu/create', DailyMenuCreateView.as_view(), name='createDailyMenu'),
    path('dailymenu/createrecipe/<int:pk>', DailyMenuRecipeCreateView.as_view(), name='createDailyMenuRecipe'),
    path('dailymenu/update/<int:pk>', DailyMenuUpdateView.as_view(), name='updateDailyMenu'),
    path('dailymenu/updaterecipe/<int:pk>', DailyMenuRecipeUpdateView.as_view(), name='updateDailyMenuRecipe'),
    path('dailymenu/delete/<int:pk>', DailyMenuDeleteView.as_view(), name='deleteDailyMenu'),
    path('dailymenu/deleterecipe/<int:pk>', DailyMenuRecipeDeleteView.as_view(), name='deleteDailyMenuRecipe'),
    path('dailymenu/filterprint', DailyMenuPrintView.as_view(), name='filterPrintDailyMenu'),
    path('dailymenu/print', DailyMenuPDFView.as_view(), name='printDailyMenu'),

    path('menu/list', MenuListView.as_view(), name='showMenus'),
    path('menu/recipelist/<int:pk>', MenuRecipeListView.as_view(), name='showMenuRecipes'),
    path('menu/create', MenuCreateView.as_view(), name='createMenu'),
    path('menu/createrecipe/<int:pk>', MenuRecipeCreateView.as_view(), name='createMenuRecipe'),
    path('menu/update/<int:pk>', MenuUpdateView.as_view(), name='updateMenu'),
    path('menu/updaterecipe/<int:pk>', MenuRecipeUpdateView.as_view(), name='updateMenuRecipe'),
    path('menu/delete/<int:pk>', MenuDeleteView.as_view(), name='deleteMenu'),
    path('menu/deleterecipe/<int:pk>', MenuRecipeDeleteView.as_view(), name='deleteMenuRecipe'),

    path('report/showFoodConsumptionTotalPrice',
         ShowFoodConsumptionTotalPrice.as_view(), name='showFoodConsumptionTotalPrice'),
    path('report/filtercateringunit', CateringUnitFilterView.as_view(), name='filterCateringUnit'),
    path('report/print/cateringunit', CateringUnitShowView.as_view(), name='showCateringUnit'),
    path('report/incorrectunits', IncorrectUnitsListView.as_view(), name='showIncorrectUnits'),
    path('report/articlesnotinrecipes', ArticlesNotInRecipesListView.as_view(), name='showArticlesNotInRecipes'),
]
