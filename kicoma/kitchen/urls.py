from django.urls import path

from .views import RecipesBookListView, RecipesBookCreateView, \
RecipesBookUpdateView, RecipesBookDeleteView, RecipesBookDetailView

from . import views

urlpatterns = [
    path('kitchen/', views.index, name='home'),
    path('recipe/list', RecipesBookListView.as_view(), name='showRecipies'),
    path('recipe/create', RecipesBookCreateView.as_view(), name='createRecipe'),
    path('recipe/detail/<int:pk>', RecipesBookDetailView.as_view(), name='detailRecipe'),
    path('recipe/update/<int:pk>', RecipesBookUpdateView.as_view(), name='updateRecipe'),
    path('recipe/delete/<int:pk>', RecipesBookDeleteView.as_view(), name='deleteRecipe'),
]
