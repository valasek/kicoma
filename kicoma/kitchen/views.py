from django.shortcuts import render
from django_tables2 import SingleTableMixin
from django_filters.views import FilterView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

from .models import StockItem, RecipeBook, Allergen, MealType, TargetGroup, StockUnit
from .tables import RecipeBookTable, RecipeBookFilter
from .forms import RecipeBookSearchForm

# import logging
# Get an instance of a logger
# logger = logging.getLogger(__name__)


def index(request):
    stockItemCount = StockItem.objects.all().count()
    recipeCount = RecipeBook.objects.all().count()
    allergenCount = Allergen.objects.all().count()
    mealTypeCount = MealType.objects.all().count()
    targetGroupCount = TargetGroup.objects.all().count()
    stockUnitCount = StockUnit.objects.all().count()
    stockMoveCount = -1
    menuCount = -1
    return render(request, 'kitchen/home.html', {'stockItemCount': stockItemCount, 'recipeCount': recipeCount, 'allergenCount': allergenCount, 'mealTypeCount': mealTypeCount, 'targetGroupCount': targetGroupCount, 'stockUnitCount': stockUnitCount, 'stockMoveCount': stockMoveCount, 'menuCount': menuCount})


class RecipeBookListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = RecipeBook
    table_class = RecipeBookTable
    template_name = 'kitchen/recipebook/show.html'
    filterset_class = RecipeBookFilter
    form_class = RecipeBookSearchForm
    paginate_by = 12


class RecipeBookCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = RecipeBook
    fields = "__all__"
    template_name = 'kitchen/recipebook/create.html'
    success_message = "Recept %(name)s byl vytvořen"

    def get_success_url(self):
        return reverse_lazy('kitchen:showRecipies')


class RecipeBookUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = RecipeBook
    fields = "__all__"
    template_name = 'kitchen/recipebook/edit.html'
    success_message = "Recept %(name)s byl aktualizován"

    def get_success_url(self):
        return reverse_lazy('kitchen:showRecipies')


class RecipeBookDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = RecipeBook
    fields = "__all__"
    form_class = RecipeBookSearchForm
    template_name = 'kitchen/recipebook/delete.html'
    success_message = "Recept %(name)s byl odstraněn"

    def get_success_url(self):
        return reverse_lazy('kitchen:showRecipies')
