from django.urls import path

from .views import RecipeListView, RecipeCreateView, RecipeUpdateView, RecipeDeleteView
from .views import ArticleListView, ArticleCreateView, ArticleUpdateView
from .views import StockReceiptListView, StockReceiptCreateView, StockReceiptUpdateView, IngredientCreateView
from .views import StockIssues
from .views import DailyMenuListView, DailyMenuCreateView, DailyMenuUpdateView, DailyMenuDeleteView

from . import views

app_name = "kitchen"
urlpatterns = [
    path('overview', views.index, name='overview'),
    path('article/list', ArticleListView.as_view(), name='showArticles'),
    path('article/print', views.notImplemented, name='printArticles'),
    path('article/create', ArticleCreateView.as_view(), name='createArticle'),
    path('article/edit/<int:pk>', ArticleUpdateView.as_view(), name='updateArticle'),
    path('stockprint', views.notImplemented, name='stockPrint'),
    path('stockissue/list', StockIssues.as_view(), name='showStockIssues'),
    path('stockreceipt/list', StockReceiptListView.as_view(), name='showStockReceipts'),
    path('stockreceipt/create', StockReceiptCreateView.as_view(), name='createStockReceipt'),
    path('stockreceipt/update/<int:pk>', StockReceiptUpdateView.as_view(), name='updateStockReceipt'),
    path('recipe/print', views.notImplemented, name='printRecipies'),
    path('recipe/list', RecipeListView.as_view(), name='showRecipies'),
    path('recipe/create', RecipeCreateView.as_view(), name='createRecipe'),
    path('recipe/update/<int:pk>', RecipeUpdateView.as_view(), name='updateRecipe'),
    path('recipe/delete/<int:pk>', RecipeDeleteView.as_view(), name='deleteRecipe'),
    path('ingredient/create/<int:pk>', IngredientCreateView.as_view(), name='createIngredient'),
    path('dailymenu/list', DailyMenuListView.as_view(), name='showDailyMenus'),
    path('dailymenu/create', DailyMenuCreateView.as_view(), name='createDailyMenu'),
    path('dailymenu/edit/<int:pk>', DailyMenuUpdateView.as_view(), name='updateDailyMenu'),
    path('dailymenu/delete/<int:pk>', DailyMenuDeleteView.as_view(), name='deleteDailyMenu'),
    path('dailymenu/print', views.notImplemented, name='printDailyMenu'),
]
