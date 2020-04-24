from django.urls import path

from .views import RecipeListView, RecipeCreateView, RecipeUpdateView, RecipeDeleteView

from . import views

app_name = "kitchen"
urlpatterns = [
    path('overview', views.index, name='overview'),
    path('recipe/list', RecipeListView.as_view(), name='showRecipies'),
    path('recipe/create', RecipeCreateView.as_view(), name='createRecipe'),
    path('recipe/update/<int:pk>', RecipeUpdateView.as_view(), name='updateRecipe'),
    path('recipe/delete/<int:pk>', RecipeDeleteView.as_view(), name='deleteRecipe'),
]
