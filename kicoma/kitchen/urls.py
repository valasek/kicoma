from django.urls import path

from .views import RecipeBookListView, RecipeBookCreateView, RecipeBookUpdateView, RecipeBookDeleteView

from . import views

app_name = "kitchen"
urlpatterns = [
    path('overview', views.index, name='overview'),
    path('recipe/list', RecipeBookListView.as_view(), name='showRecipies'),
    path('recipe/create', RecipeBookCreateView.as_view(), name='createRecipe'),
    path('recipe/update/<int:pk>', RecipeBookUpdateView.as_view(), name='updateRecipe'),
    path('recipe/delete/<int:pk>', RecipeBookDeleteView.as_view(), name='deleteRecipe'),
]
