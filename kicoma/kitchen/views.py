from django.shortcuts import render
from django_tables2 import SingleTableMixin
from django_filters.views import FilterView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

from .models import Item, Recipe, Allergen, MealType, TargetGroup, Unit
from .tables import RecipeTable, RecipeFilter
from .forms import RecipeSearchForm

# import logging
# Get an instance of a logger
# logger = logging.getLogger(__name__)


def index(request):
    stockItemCount = Item.objects.all().count()
    recipeCount = Recipe.objects.all().count()
    allergenCount = Allergen.objects.all().count()
    mealTypeCount = MealType.objects.all().count()
    targetGroupCount = TargetGroup.objects.all().count()
    unitCount = Unit.objects.all().count()
    stockMoveCount = -1
    menuCount = -1
    return render(request, 'kitchen/home.html', {'stockItemCount': stockItemCount, 'recipeCount': recipeCount, 'allergenCount': allergenCount, 'mealTypeCount': mealTypeCount, 'targetGroupCount': targetGroupCount, 'unitCount': unitCount, 'stockMoveCount': stockMoveCount, 'menuCount': menuCount})


class RecipeListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = Recipe
    table_class = RecipeTable
    template_name = 'kitchen/recipe/show.html'
    filterset_class = RecipeFilter
    form_class = RecipeSearchForm
    paginate_by = 12


class RecipeCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Recipe
    fields = "__all__"
    template_name = 'kitchen/recipe/create.html'
    success_message = "Recept %(name)s byl vytvořen"

    def get_success_url(self):
        return reverse_lazy('kitchen:showRecipies')


class RecipeUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = Recipe
    fields = "__all__"
    template_name = 'kitchen/recipe/edit.html'
    success_message = "Recept %(name)s byl aktualizován"

    def get_success_url(self):
        return reverse_lazy('kitchen:showRecipies')


class RecipeDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = Recipe
    fields = "__all__"
    form_class = RecipeSearchForm
    template_name = 'kitchen/recipe/delete.html'
    success_message = "Recept %(name)s byl odstraněn"

    def get_success_url(self):
        return reverse_lazy('kitchen:showRecipies')
