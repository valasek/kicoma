from django.urls import path

from .views import ArticleListView, ArticleCreateView, ArticleUpdateView, ArticlePDFView
from .views import StockReceiptListView, StockReceiptCreateView, StockReceiptUpdateView, \
    StockReceiptDeleteView, StockReceiptPDFView
from .views import StockReceiptItemListView, StockReceiptItemCreateView, StockReceiptItemUpdateView, \
    StockReceiptItemDeleteView
from .views import RecipeListView, RecipeCreateView, RecipeUpdateView, RecipeDeleteView, RecipePDFView
from .views import RecipeIngredientListView, RecipeIngredientCreateView, RecipeIngredientUpdateView, \
    RecipeIngredientDeleteView
from .views import StockIssueListView, StockIssueCreateView
from .views import DailyMenuListView, DailyMenuCreateView, DailyMenuUpdateView, DailyMenuDeleteView
from .views import DailyMenuRecipeListView, DailyMenuRecipeCreateView, DailyMenuRecipeUpdateView, \
    DailyMenuRecipeDeleteView

from .views import index, notImplemented

app_name = "kitchen"
urlpatterns = [
    path('overview', index, name='overview'),

    path('article/list', ArticleListView.as_view(), name='showArticles'),
    path('article/create', ArticleCreateView.as_view(), name='createArticle'),
    path('article/update/<int:pk>', ArticleUpdateView.as_view(), name='updateArticle'),
    path('article/print', ArticlePDFView.as_view(), name='printArticles'),

    path('stockissue/list', StockIssueListView.as_view(), name='showStockIssues'),
    path('stockissue/create', StockIssueCreateView.as_view(), name='createStockIssue'),
    path('stockreceipt/create', StockReceiptCreateView.as_view(), name='createStockReceipt'),

    path('stockreceipt/list', StockReceiptListView.as_view(), name='showStockReceipts'),
    path('stockreceipt/itemlist/<int:pk>', StockReceiptItemListView.as_view(), name='showStockReceiptItems'),
    path('stockreceipt/create', StockReceiptCreateView.as_view(), name='createStockReceipt'),
    path('stockreceipt/createitem/<int:pk>', StockReceiptItemCreateView.as_view(), name='createStockReceiptItem'),
    path('stockreceipt/update/<int:pk>', StockReceiptUpdateView.as_view(), name='updateStockReceipt'),
    path('stockreceipt/updateitem/<int:pk>', StockReceiptItemUpdateView.as_view(), name='updateStockReceiptItem'),
    path('stockreceipt/delete/<int:pk>', StockReceiptDeleteView.as_view(), name='deleteStockReceipt'),
    path('stockreceipt/deleteitem/<int:pk>', StockReceiptItemDeleteView.as_view(), name='deleteStockReceiptItem'),
    path('stockreceipt/print/<int:pk>', StockReceiptPDFView.as_view(), name='printStockReceipt'),

    path('recipe/list', RecipeListView.as_view(), name='showRecipes'),
    path('recipe/ingredientlist/<int:pk>', RecipeIngredientListView.as_view(), name='showRecipeIngredients'),
    path('recipe/create', RecipeCreateView.as_view(), name='createRecipe'),
    path('recipe/createingredient/<int:pk>', RecipeIngredientCreateView.as_view(), name='createRecipeIngredient'),
    path('recipe/update/<int:pk>', RecipeUpdateView.as_view(), name='updateRecipe'),
    path('recipe/updateingredient/<int:pk>', RecipeIngredientUpdateView.as_view(), name='updateRecipeIngredient'),
    path('recipe/delete/<int:pk>', RecipeDeleteView.as_view(), name='deleteRecipe'),
    path('recipe/deleteingredient/<int:pk>', RecipeIngredientDeleteView.as_view(), name='deleteRecipeIngredient'),
    path('recipe/print', RecipePDFView.as_view(), name='printRecipes'),


    path('dailymenu/list', DailyMenuListView.as_view(), name='showDailyMenus'),
    path('dailymenu/recipelist/<int:pk>', DailyMenuRecipeListView.as_view(), name='showDailyMenuRecipes'),
    path('dailymenu/create', DailyMenuCreateView.as_view(), name='createDailyMenu'),
    path('dailymenu/createrecipe/<int:pk>', DailyMenuRecipeCreateView.as_view(), name='createDailyMenuRecipe'),
    path('dailymenu/update/<int:pk>', DailyMenuUpdateView.as_view(), name='updateDailyMenu'),
    path('dailymenu/updaterecipe/<int:pk>', DailyMenuRecipeUpdateView.as_view(), name='updateDailyMenuRecipe'),
    path('dailymenu/delete/<int:pk>', DailyMenuDeleteView.as_view(), name='deleteDailyMenu'),
    path('dailymenu/deleterecipe/<int:pk>', DailyMenuRecipeDeleteView.as_view(), name='deleteDailyMenuRecipe'),
    path('dailymenu/print', notImplemented, name='printDailyMenu'),
]
