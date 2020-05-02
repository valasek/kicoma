from django.urls import path

from .views import RecipeListView, RecipeCreateView, RecipeUpdateView, RecipeDeleteView
from .views import StockReceiptListView, StockReceiptCreateView

from . import views

app_name = "kitchen"
urlpatterns = [
    path('overview', views.index, name='overview'),
    path('stockreceipt/list', StockReceiptListView.as_view(), name='showStockReceipts'),
    path('stockreceipt/create', StockReceiptCreateView.as_view(), name='createStockReceipt'),
    path('recipe/list', RecipeListView.as_view(), name='showRecipies'),
    path('recipe/create', RecipeCreateView.as_view(), name='createRecipe'),
    path('recipe/update/<int:pk>', RecipeUpdateView.as_view(), name='updateRecipe'),
    path('recipe/delete/<int:pk>', RecipeDeleteView.as_view(), name='deleteRecipe'),
]
