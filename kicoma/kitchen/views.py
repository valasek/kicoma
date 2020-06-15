import logging
from django.shortcuts import render
from django_tables2 import SingleTableMixin
from django_filters.views import FilterView

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.models import Group

from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db import transaction

from kicoma.users.models import User

from .models import Item, Recipe, Allergen, MealType, TargetGroup, VAT, \
    Article, Ingredient, StockIssue, StockReceipt, DailyMenu
from .tables import RecipeTable, RecipeFilter, StockReceiptTable, StockReceiptFilter, ArticleTable, ArticleFilter
from .forms import RecipeSearchForm, StockReceiptForm, StockReceiptSearchForm, IngredientFormSet, StockReceiptFormSet, ArticleSearchForm

# Get an instance of a logger
logger = logging.getLogger(__name__)


# TODO: doplnit validaci formu a save
# https://dev.to/zxenia/django-inline-formsets-with-class-based-views-and-crispy-forms-14o6
# https://medium.com/@adandan01/django-inline-formsets-example-mybook-420cc4b6225d
# https://www.youtube.com/watch?v=JIvJL1HizP4
# https://www.mattlayman.com/understand-django/user-interaction-forms/?utm_campaign=Django%2BNewsletter&utm_medium=email&utm_source=Django_Newsletter_22


def index(request):
    allergenCount = Allergen.objects.all().count()
    mealTypeCount = MealType.objects.all().count()
    targetGroupCount = TargetGroup.objects.all().count()
    vatCount = VAT.objects.all().count()

    recipeCount = Recipe.objects.all().count()
    ingredientCount = Ingredient.objects.all().count()
    articleCount = Article.objects.all().count()
    stockIssueCount = StockIssue.objects.all().count()
    stockReceiptCount = StockReceipt.objects.all().count()
    itemCount = Item.objects.all().count()
    dailyMenuCount = DailyMenu.objects.all().count()

    userCount = User.objects.all().count()
    groupCount = Group.objects.all().count()

    logger.info("processing index")

    return render(request, 'kitchen/home.html', {
        'allergenCount': allergenCount,
        'mealTypeCount': mealTypeCount,
        'targetGroupCount': targetGroupCount,
        'vatCount': vatCount,

        'recipeCount': recipeCount,
        'ingredientCount': ingredientCount,
        'articleCount': articleCount,
        'stockIssueCount': stockIssueCount,
        'stockReceiptCount': stockReceiptCount,
        'itemCount': itemCount,
        'dailyMenuCount': dailyMenuCount,

        "groupCount": groupCount,
        "userCount": userCount
    })


def about(request):
    return render(request, 'kitchen/about.html')


class ArticleListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = Article
    table_class = ArticleTable
    template_name = 'kitchen/article/list.html'
    filterset_class = ArticleFilter
    form_class = ArticleSearchForm
    paginate_by = 12

class RecipeListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = Recipe
    table_class = RecipeTable
    template_name = 'kitchen/recipe/list.html'
    filterset_class = RecipeFilter
    form_class = RecipeSearchForm
    paginate_by = 12


class RecipeCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Recipe
    fields = "__all__"
    template_name = 'kitchen/recipe/create.html'
    success_message = "Recept %(name)s byl vytvořen, přidej suroviny receptu"

    def get_success_url(self):
        return reverse_lazy('kitchen:createIngredient', kwargs={'pk': self.object.pk})


class IngredientCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Ingredient
    fields = "__all__"
    # form_class = IngredientForm
    template_name = 'kitchen/ingredient/create.html'
    success_message = "Suroviny přidány do receptu"

    def get_context_data(self, **kwargs):
        data = super(IngredientCreateView, self).get_context_data(**kwargs)
        if self.request.POST:
            data['ingredients'] = IngredientFormSet(self.request.POST, instance=self.object)
        else:
            data['ingredients'] = IngredientFormSet(instance=self.object)
        return data

    # TODO add for valid

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


# StockReceipt

class StockReceiptListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = StockReceipt
    table_class = StockReceiptTable
    template_name = 'kitchen/stockreceipt/list.html'
    filterset_class = StockReceiptFilter
    form_class = StockReceiptSearchForm
    paginate_by = 12


# class StockReceiptCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
#     model = Item
#     fields = ["amount", "unit", "priceWithoutVat", "vat", "comment"]
#     template_name = 'kitchen/stockreceipt/create.html'
#     success_message = "Příjemka %(name)s byla vytvořena a zásoby zboží na skladu aktualizovány"

#     def get_success_url(self):
#         return reverse_lazy('kitchen:showStockReceipts')

# Source: https: // dev.to/zxenia/django-inline-formsets-with-class-based-views-and-crispy-forms-14o6
class StockReceiptCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = StockReceipt
    form_class = StockReceiptForm
    template_name = 'kitchen/stockreceipt/create.html'
    success_message = "Příjemka ze dne %(createdAt)s byla vytvořena a zásoby zboží na skladu aktualizovány"
    success_url = None

    def get_context_data(self, **kwargs):
        data = super(StockReceiptCreateView, self).get_context_data(**kwargs)
        if self.request.POST:
            data['items'] = StockReceiptFormSet(self.request.POST)
        else:
            data['items'] = StockReceiptFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        items = context['items']
        with transaction.atomic():
            form.instance.userCreated = self.request.user
            self.object = form.save()
            if items.is_valid():
                items.instance = self.object
                items.save()
        return super(StockReceiptCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('kitchen:showStockReceipts')  # , kwargs={'pk': self.object.pk})


class StockReceiptUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = StockReceipt
    form_class = StockReceiptForm
    template_name = 'kitchen/stockreceipt/edit.html'
    success_message = "Příjemka ze dne %(createdAt)s byla aktualizována a zásoby zboží na skladu taky"
    success_url = None

    def get_context_data(self, **kwargs):
        context = super(StockReceiptUpdateView, self).get_context_data(**kwargs)
        if self.request.POST:
            context['items'] = StockReceiptFormSet(self.request.POST, instance=self.object)
        else:
            context['items'] = StockReceiptFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items = context['items']
        with transaction.atomic():
            form.instance.userCreated = self.request.user
            self.object = form.save()
            # print(self.object, self.object.id)
            if items.is_valid():
                items.instance = self.object
                # items.stockReceipt = self.object.id
                items.save()
        return super(StockReceiptUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('kitchen:updateStockReceipt', kwargs={'pk': self.object.pk})
