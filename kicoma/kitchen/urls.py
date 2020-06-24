from django.urls import path

from .views import RecipeListView, RecipeCreateView, RecipeUpdateView, RecipeDeleteView
from .views import ArticleListView, ArticleCreateView, ArticleUpdateView

from .views import StockReceiptListView, StockReceiptItemListView, StockReceiptCreateView, StockReceiptItemCreateView, \
    StockReceiptUpdateView, StockReceiptItemUpdateView, StockReceiptDeleteView, StockReceiptItemDeleteView, \
    StockReceiptPDFView

from .views import IngredientCreateView
from .views import StockIssueListView
from .views import DailyMenuListView, DailyMenuCreateView, DailyMenuUpdateView, DailyMenuDeleteView

from .views import index, notImplemented

app_name = "kitchen"
urlpatterns = [
    path('overview', index, name='overview'),
    path('article/list', ArticleListView.as_view(), name='showArticles'),
    path('article/print', notImplemented, name='printArticles'),
    path('article/create', ArticleCreateView.as_view(), name='createArticle'),
    path('article/update/<int:pk>', ArticleUpdateView.as_view(), name='updateArticle'),
    path('stockprint', notImplemented, name='stockPrint'),

    path('stockissue/list', StockIssueListView.as_view(), name='showStockIssues'),

    path('stockreceipt/list', StockReceiptListView.as_view(), name='showStockReceipts'),
    path('stockreceipt/itemlist/<int:pk>', StockReceiptItemListView.as_view(), name='showStockReceiptItems'),
    path('stockreceipt/create', StockReceiptCreateView.as_view(), name='createStockReceipt'),
    path('stockreceipt/createitem/<int:pk>', StockReceiptItemCreateView.as_view(), name='createStockReceiptItem'),
    path('stockreceipt/update/<int:pk>', StockReceiptUpdateView.as_view(), name='updateStockReceipt'),
    path('stockreceipt/updateitem/<int:pk>', StockReceiptItemUpdateView.as_view(), name='updateStockReceiptItem'),
    path('stockreceipt/delete/<int:pk>', StockReceiptDeleteView.as_view(), name='deleteStockReceipt'),
    path('stockreceipt/deleteitem/<int:pk>', StockReceiptItemDeleteView.as_view(), name='deleteStockReceiptItem'),
    path('stockreceipt/print/<int:pk>', StockReceiptPDFView.as_view(), name='printStockReceipt'),

    path('recipe/print', notImplemented, name='printRecipies'),
    path('recipe/list', RecipeListView.as_view(), name='showRecipies'),
    path('recipe/create', RecipeCreateView.as_view(), name='createRecipe'),
    path('recipe/update/<int:pk>', RecipeUpdateView.as_view(), name='updateRecipe'),
    path('recipe/delete/<int:pk>', RecipeDeleteView.as_view(), name='deleteRecipe'),
    path('ingredient/create/<int:pk>', IngredientCreateView.as_view(), name='createIngredient'),
    path('dailymenu/list', DailyMenuListView.as_view(), name='showDailyMenus'),
    path('dailymenu/create', DailyMenuCreateView.as_view(), name='createDailyMenu'),
    path('dailymenu/update/<int:pk>', DailyMenuUpdateView.as_view(), name='updateDailyMenu'),
    path('dailymenu/delete/<int:pk>', DailyMenuDeleteView.as_view(), name='deleteDailyMenu'),
    path('dailymenu/print', notImplemented, name='printDailyMenu'),
]
