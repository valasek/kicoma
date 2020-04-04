from django.shortcuts import render

from django_tables2 import SingleTableMixin
from django_filters.views import FilterView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from .models import Item, RecipeBook, Allergen
from .tables import RecipeBookTable, RecipeBookFilter

import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

def index(request):
    itemCount = Item.objects.all().count()
    recipeCount = RecipeBook.objects.all().count()
    allergenCount = Allergen.objects.all().count()
    logger.error("stanislav")
    logger.info("stanislav")
    logger.debug("stanislav")
    print("stan")
    logger.error(itemCount, recipeCount, allergenCount)
    return render(request, 'kitchen/home.html', {'itemCount': itemCount, 'recipeCount': recipeCount, 'allergenCount': allergenCount})


class RecipesBookListView(SingleTableMixin, FilterView):
    model = RecipeBook
    table_class = RecipeBookTable
    template_name = 'kitchen/recipebook/show.html'
    filterset_class = RecipeBookFilter


class RecipesBookDetailView(DetailView):
    model = RecipeBook
    template_name = 'kitchen/recipebook/detail.html'


class RecipesBookCreateView(CreateView):
    model = RecipeBook
    fields = "__all__"


class RecipesBookUpdateView(UpdateView):
    model = RecipeBook


class RecipesBookDeleteView(DeleteView):
    model = RecipeBook
