from django.urls import path

from .views import RecipeListView, RecipeCreateView, RecipeUpdateView, RecipeDeleteView
from .views import ArticleListView, ArticleCreateView, ArticleUpdateView
from .views import StockReceiptListView, StockReceiptCreateView, StockReceiptUpdateView, IngredientCreateView

from . import views

app_name = "kitchen"
urlpatterns = [
    path('overview', views.index, name='overview'),
    path('article/list', ArticleListView.as_view(), name='showArticles'),
    path('article/create', ArticleCreateView.as_view(), name='createArticle'),
    path('article/update/<int:pk>', ArticleUpdateView.as_view(), name='updateArticle'),
    path('stockreceipt/list', StockReceiptListView.as_view(), name='showStockReceipts'),
    path('stockreceipt/create', StockReceiptCreateView.as_view(), name='createStockReceipt'),
    path('stockreceipt/update/<int:pk>', StockReceiptUpdateView.as_view(), name='updateStockReceipt'),
    path('recipe/list', RecipeListView.as_view(), name='showRecipies'),
    path('recipe/create', RecipeCreateView.as_view(), name='createRecipe'),
    path('recipe/update/<int:pk>', RecipeUpdateView.as_view(), name='updateRecipe'),
    path('recipe/delete/<int:pk>', RecipeDeleteView.as_view(), name='deleteRecipe'),
    path('ingredient/create/<int:pk>', IngredientCreateView.as_view(), name='createIngredient'),
]
