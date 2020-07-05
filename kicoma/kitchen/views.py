import logging
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy

from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.db.models import Sum

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.models import Group

from wkhtmltopdf.views import PDFTemplateView
from django_tables2 import SingleTableMixin
from django_filters.views import FilterView

from kicoma.users.models import User

from .models import Item, Recipe, Allergen, MealType, MealGroup, VAT, \
    Article, Ingredient, StockIssue, StockReceipt, DailyMenu, DailyMenuRecipe

from .tables import StockReceiptTable, StockReceiptItemTable, StockReceiptFilter, StockReceiptItemFilter
from .tables import ArticleTable, ArticleFilter
from .tables import DailyMenuTable, DailyMenuFilter
from .tables import DailyMenuRecipeTable, DailyMenuRecipeFilter
from .tables import StockIssueTable, StockIssueFilter
from .tables import RecipeTable, RecipeFilter, RecipeIngredientTable, RecipeIngredientFilter

from .forms import RecipeForm, RecipeIngredientForm, RecipeSearchForm, RecipeIngredientSearchForm
from .forms import StockReceiptForm, StockReceiptSearchForm, StockReceiptItemForm, StockReceiptItemSearchForm
from .forms import StockIssueForm, StockIssueSearchForm
from .forms import ArticleForm, ArticleSearchForm
from .forms import DailyMenuSearchForm, DailyMenuForm, DailyMenuRecipeForm, DailyMenuRecipeSearchForm

from .signals import updateOnStock, updateTotalPrice

# Get an instance of a logger
logger = logging.getLogger(__name__)


def notImplemented(request):
    return render(request, 'notImplemented.html')


def index(request):
    allergenCount = Allergen.objects.all().count()
    mealTypeCount = MealType.objects.all().count()
    mealGroupCount = MealGroup.objects.all().count()
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
        'mealGroupCount': mealGroupCount,
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


class ArticleCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Article
    form_class = ArticleForm
    template_name = 'kitchen/article/create.html'
    success_message = "Zboží %(article)s bylo založeno, je možné zadávat příjemky"
    success_url = reverse_lazy('kitchen:showArticles')


class ArticleUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = Article
    form_class = ArticleForm
    template_name = 'kitchen/article/update.html'
    success_message = "Zboží %(article)s bylo aktualizováno"
    success_url = reverse_lazy('kitchen:showArticles')


class ArticlePDFView(LoginRequiredMixin, PDFTemplateView):
    template_name = 'kitchen/article/pdf.html'
    filename = 'Seznam-zbozi.pdf'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['articles'] = Article.objects.all()
        context['title'] = "Seznam zboží na skladu"
        return context


class RecipeListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = Recipe
    table_class = RecipeTable
    template_name = 'kitchen/recipe/list.html'
    filterset_class = RecipeFilter
    form_class = RecipeSearchForm
    paginate_by = 12


class RecipeCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Recipe
    form_class = RecipeForm
    template_name = 'kitchen/recipe/create.html'
    success_message = "Recept %(recipe)s byl vytvořen, přidej do receptu suroviny a jejich počet"
    success_url = reverse_lazy('kitchen:showRecipes')


class RecipeUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = Recipe
    form_class = RecipeForm
    template_name = 'kitchen/recipe/update.html'
    success_message = "Recept %(recipe)s byl aktualizován"
    success_url = reverse_lazy('kitchen:showRecipes')


class RecipeDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = Recipe
    fields = "__all__"
    # form_class = RecipeSearchForm
    template_name = 'kitchen/recipe/delete.html'
    success_message = "Recept %(recipe)s byl odstraněn"
    success_url = reverse_lazy('kitchen:showRecipes')


class RecipePDFView(LoginRequiredMixin, PDFTemplateView):
    template_name = 'kitchen/recipe/pdf.html'
    filename = 'Recepty.pdf'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recipes'] = Recipe.objects.all()
        context['recipes_total'] = Recipe.objects.all().count()
        context['title'] = "Seznam receptů"
        return context


class RecipeIngredientListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = Ingredient
    table_class = RecipeIngredientTable
    template_name = 'kitchen/recipe/listingredients.html'
    filterset_class = RecipeIngredientFilter
    form_class = RecipeIngredientSearchForm
    paginate_by = 12

    def get_context_data(self, **kwargs):
        context = super(RecipeIngredientListView, self).get_context_data(**kwargs)
        context['recipe'] = Recipe.objects.filter(pk=self.kwargs['pk'])[0]
        return context

    def get_queryset(self):
        # show only recipe ingedients
        return super().get_queryset().filter(recipe=self.kwargs["pk"])


class RecipeIngredientCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Ingredient
    form_class = RecipeIngredientForm
    template_name = 'kitchen/recipe/createingredient.html'
    success_message = "Ingedence %(article)s byla přidána do receptu"

    def get_success_url(self):
        return reverse_lazy('kitchen:showRecipeIngredients', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super(RecipeIngredientCreateView, self).get_context_data(**kwargs)
        context['recipe'] = Recipe.objects.filter(pk=self.kwargs['pk'])[0]
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        recipe = context['recipe']
        ingredient = form.save(commit=False)
        ingredient.recipe = Recipe.objects.filter(pk=recipe.id)[0]
        ingredient.save()
        return super(RecipeIngredientCreateView, self).form_valid(form)


class RecipeIngredientUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = Ingredient
    form_class = RecipeIngredientForm
    template_name = 'kitchen/recipe/updateingredient.html'
    success_message = "Ingedience %(article)s byla aktualizována"

    def get_success_url(self):
        return reverse_lazy('kitchen:showRecipeIngredients', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super(RecipeIngredientUpdateView, self).get_context_data(**kwargs)
        context['ingredient_before'] = Ingredient.objects.filter(pk=self.kwargs['pk'])[0]
        return context

    def form_valid(self, form):
        ingredient = form.save(commit=False)
        ingredient.recipe = Ingredient.objects.filter(pk=ingredient.id)[0].recipe
        ingredient.save()
        self.kwargs = {'pk': ingredient.recipe.id }
        return super(RecipeIngredientUpdateView, self).form_valid(form)


class RecipeIngredientDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = Ingredient
    template_name = 'kitchen/recipe/deleteingredient.html'
    success_message = "Ingredience byla odstraněna"
    # success_url = reverse_lazy('kitchen:showStockReceipts')
    recipe_id = 0

    def get_success_url(self):
        return reverse_lazy('kitchen:showRecipeIngredients', kwargs={'pk': self.recipe_id})

    def delete(self, request, *args, **kwargs):
        ingredient = get_object_or_404(Ingredient, pk=self.kwargs['pk'])
        self.recipe_id = ingredient.recipe.id
        return super(RecipeIngredientDeleteView, self).delete(request, *args, **kwargs)


class DailyMenuListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = DailyMenu
    table_class = DailyMenuTable
    template_name = 'kitchen/dailymenu/list.html'
    filterset_class = DailyMenuFilter
    form_class = DailyMenuSearchForm
    paginate_by = 12


class DailyMenuCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = DailyMenu
    form_class = DailyMenuForm
    template_name = 'kitchen/dailymenu/create.html'
    success_message = "Denní menu pro den %(date)s bylo vytvořeno včetně výdejky ke schválení"
    success_url = reverse_lazy('kitchen:showDailyMenus')


class DailyMenuUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = DailyMenu
    form_class = DailyMenuForm
    template_name = 'kitchen/dailymenu/update.html'
    success_message = "Denní menu pro den %(date)s bylo aktualizováno včetně výdejky ke schválení"
    success_url = reverse_lazy('kitchen:showDailyMenus')


class DailyMenuDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = DailyMenu
    fields = "__all__"
    template_name = 'kitchen/dailymenu/delete.html'
    success_message = "Denní menu pro den %(date)s bylo odstraněno"
    success_url = reverse_lazy('kitchen:showDailyMenus')


class DailyMenuRecipeListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = DailyMenuRecipe
    table_class = DailyMenuRecipeTable
    template_name = 'kitchen/dailymenu/listrecipe.html'
    filterset_class = DailyMenuRecipeFilter
    form_class = DailyMenuRecipeSearchForm
    paginate_by = 12

    def get_context_data(self, **kwargs):
        context = super(DailyMenuRecipeListView, self).get_context_data(**kwargs)
        context['dailymenu'] = DailyMenu.objects.filter(pk=self.kwargs['pk'])[0]
        return context

    def get_queryset(self):
        # show only DailyMeny recipes
        return super().get_queryset().filter(daily_menu=self.kwargs["pk"])


class DailyMenuRecipeCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = DailyMenuRecipe
    form_class = DailyMenuRecipeForm
    template_name = 'kitchen/dailymenu/createrecipe.html'
    success_message = 'Recept %(recipe)s byl vytvořen'

    def get_success_url(self):
        return reverse_lazy('kitchen:showDailyMenuRecipes', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super(DailyMenuRecipeCreateView, self).get_context_data(**kwargs)
        context['dailymenu'] = DailyMenu.objects.filter(pk=self.kwargs['pk'])[0]
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        dailu_menu = context['dailymenu']
        dailu_menu_recipe = form.save(commit=False)
        dailu_menu_recipe.daily_menu = DailyMenu.objects.filter(pk=dailu_menu.id)[0]
        dailu_menu_recipe.save()
        return super(DailyMenuRecipeCreateView, self).form_valid(form)


class DailyMenuRecipeUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = DailyMenuRecipe
    form_class = DailyMenuRecipeForm
    template_name = 'kitchen/dailymenu/updaterecipe.html'
    success_message = "Recept %(recipe)s byl aktualizován"

    def get_success_url(self):
        return reverse_lazy('kitchen:showDailyMenuRecipes', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super(DailyMenuRecipeUpdateView, self).get_context_data(**kwargs)
        context['dailymenurecipe_before'] = DailyMenuRecipe.objects.filter(pk=self.kwargs['pk'])[0]
        return context

    def form_valid(self, form):
        dailu_menu_recipe = form.save(commit=False)
        dailu_menu_recipe.daily_menu = DailyMenuRecipe.objects.filter(pk=dailu_menu_recipe.id)[0].daily_menu
        dailu_menu_recipe.save()
        self.kwargs = {'pk': dailu_menu_recipe.daily_menu.id}
        return super(DailyMenuRecipeUpdateView, self).form_valid(form)


class DailyMenuRecipeDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = DailyMenuRecipe
    template_name = 'kitchen/dailymenu/deleterecipe.html'
    success_message = "Recept byl odstraněn"
    success_url = reverse_lazy('kitchen:showDailyMenuRecipes')
    daily_menu_id = 0

    def get_success_url(self):
        return reverse_lazy('kitchen:showDailyMenuRecipes', kwargs={'pk': self.daily_menu_id})

    def delete(self, request, *args, **kwargs):
        recipe = get_object_or_404(DailyMenuRecipe, pk=self.kwargs['pk'])
        self.daily_menu_id = recipe.daily_menu.id
        return super(DailyMenuRecipeDeleteView, self).delete(request, *args, **kwargs)


class StockIssueListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = StockIssue
    table_class = StockIssueTable
    template_name = 'kitchen/stockissue/list.html'
    filterset_class = StockIssueFilter
    form_class = StockIssueSearchForm
    paginate_by = 12


class StockIssueCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = StockIssue
    form_class = StockIssueForm
    template_name = 'kitchen/stockissue/create.html'
    success_message = "Vydejka byla vytvořena a je možné přidávat položky"
    success_url = reverse_lazy('kitchen:showStockIssues')

    def form_valid(self, form):
        print("form_valid", self, form)
        form.instance.userCreated = self.request.user
        self.object = form.save()
        return super(StockIssueCreateView, self).form_valid(form)


class StockReceiptListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = StockReceipt
    table_class = StockReceiptTable
    template_name = 'kitchen/stockreceipt/list.html'
    filterset_class = StockReceiptFilter
    form_class = StockReceiptSearchForm
    paginate_by = 12


class StockReceiptCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = StockReceipt
    form_class = StockReceiptForm
    template_name = 'kitchen/stockreceipt/create.html'
    success_message = "Příjemka byla vytvořena a je možné přidávat položky"
    success_url = reverse_lazy('kitchen:showStockReceipts')

    def form_valid(self, form):
        form.instance.userCreated = self.request.user
        self.object = form.save()
        return super(StockReceiptCreateView, self).form_valid(form)


class StockReceiptUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = StockReceipt
    form_class = StockReceiptForm
    template_name = 'kitchen/stockreceipt/update.html'
    success_message = "Hlavička příjemky byla aktualizována"
    success_url = reverse_lazy('kitchen:showStockReceipts')


class StockReceiptDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = StockReceipt
    template_name = 'kitchen/stockreceipt/delete.html'
    success_message = "Příjemka ze dne %(created)s byla odstraněna"
    success_url = reverse_lazy('kitchen:showStockReceipts')


class StockReceiptPDFView(LoginRequiredMixin, PDFTemplateView):
    template_name = 'kitchen/stockreceipt/pdf.html'
    filename = 'Prijemka.pdf'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stock_receipt = StockReceipt.objects.filter(pk=kwargs['pk'])[0]
        items = Item.objects.filter(stockReceipt_id=kwargs['pk'])
        total_price = Item.objects.filter(stockReceipt_id=kwargs['pk']).aggregate(
            Sum('priceWithoutVat'))['priceWithoutVat__sum']
        context['stock_receipt'] = stock_receipt
        context['items'] = items
        context['title'] = "Příjemka"
        context['total_price'] = total_price
        return context


class StockReceiptItemListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = Item
    table_class = StockReceiptItemTable
    template_name = 'kitchen/stockreceipt/listitems.html'
    filterset_class = StockReceiptItemFilter
    form_class = StockReceiptItemSearchForm
    paginate_by = 12

    def get_context_data(self, **kwargs):
        context = super(StockReceiptItemListView, self).get_context_data(**kwargs)
        context['stockreceipt'] = StockReceipt.objects.filter(pk=self.kwargs['pk'])[0]
        return context

    def get_queryset(self):
        # show only StockReceipt Items
        return super().get_queryset().filter(stockReceipt=self.kwargs["pk"])


class StockReceiptItemCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Item
    form_class = StockReceiptItemForm
    template_name = 'kitchen/stockreceipt/createitem.html'
    success_message = 'Polozka %(article)s byla vytvořena a výše zásob zboží na skladu aktualizována'

    def get_success_url(self):
        return reverse_lazy('kitchen:showStockReceiptItems', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super(StockReceiptItemCreateView, self).get_context_data(**kwargs)
        context['stockreceipt'] = StockReceipt.objects.filter(pk=self.kwargs['pk'])[0]
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        stock_receipt = context['stockreceipt']
        item = form.save(commit=False)
        item.stockReceipt = StockReceipt.objects.filter(pk=stock_receipt.id)[0]
        item.save()
        updateOnStock(item.article.id, 'receipt', item.amount, 0, item.unit)
        updateTotalPrice(item.article.id, 'receipt', item.price_with_vat)
        return super(StockReceiptItemCreateView, self).form_valid(form)


class StockReceiptItemUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = Item
    form_class = StockReceiptItemForm
    template_name = 'kitchen/stockreceipt/updateitem.html'
    success_message = "Zboží %(article)s bylo aktualizováno a výše zásob zboží na skladu aktualizována"

    def get_success_url(self):
        return reverse_lazy('kitchen:showStockReceiptItems', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super(StockReceiptItemUpdateView, self).get_context_data(**kwargs)
        context['item_before'] = Item.objects.filter(pk=self.kwargs['pk'])[0]
        return context

    def form_valid(self, form):
        item = form.save(commit=False)
        item.stockReceipt = Item.objects.filter(pk=item.id)[0].stockReceipt
        old_amount = Item.objects.filter(pk=item.id).values('amount')[0]['amount']
        # todo put into transaction
        item.save()
        updateOnStock(item.article.id, 'receipt', item.amount, old_amount, item.unit)
        updateTotalPrice(item.article.id, 'receipt', item.price_with_vat)
        return super(StockReceiptItemUpdateView, self).form_valid(form)


class StockReceiptItemDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = Item
    template_name = 'kitchen/stockreceipt/deleteitem.html'
    success_message = "Zboží bylo odstraněno"
    success_url = reverse_lazy('kitchen:showStockReceipts')
    stock_receipt_id = 0

    def get_success_url(self):
        return reverse_lazy('kitchen:showStockReceiptItems', kwargs={'pk': self.stock_receipt_id})

    def delete(self, request, *args, **kwargs):
        item = get_object_or_404(Item, pk=self.kwargs['pk'])
        self.stock_receipt_id = item.stockReceipt.id
        return super(StockReceiptItemDeleteView, self).delete(request, *args, **kwargs)
