import logging
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy

from django.views.generic.edit import CreateView, UpdateView, DeleteView

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.models import Group

from wkhtmltopdf.views import PDFTemplateView
from django_tables2 import SingleTableMixin
from django_filters.views import FilterView

from kicoma.users.models import User
from .models import Item, Recipe, Allergen, MealType, MealGroup, VAT, \
    Article, Ingredient, StockIssue, StockReceipt, DailyMenu
from .tables import StockReceiptTable, StockReceiptFilter, StockReceiptItemFilter, ArticleTable, ArticleFilter, \
    DailyMenuTable, DailyMenuFilter, RecipeTable, RecipeFilter, StockReceiptItemTable, StockIssueTable
from .forms import RecipeSearchForm, StockReceiptForm, StockReceiptSearchForm, \
    ArticleSearchForm, DailyMenuSearchForm, StockReceiptItemForm, StockReceiptItemSearchForm

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
    fields = ["article", "unit", "comment", "allergen", ]
    template_name = 'kitchen/article/create.html'
    success_message = "Zboží %(article)s bylo založeno, je možné zadávat příjemky."

    def get_success_url(self):
        return reverse_lazy('kitchen:showArticles')


class ArticleUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = Article
    fields = ["article", "unit", "comment", "allergen", ]
    template_name = 'kitchen/article/update.html'
    success_message = "Zboží %(article)s bylo aktualizováno, je možné zadávat příjemky."

    def get_success_url(self):
        return reverse_lazy('kitchen:showArticles')


class IngredientCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Ingredient
    fields = "__all__"
    template_name = 'kitchen/ingredient/create.html'
    success_message = "Suroviny přidány do receptu"

    def get_success_url(self):
        return reverse_lazy('kitchen:showRecipies')


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
    success_message = "Recept %(recipe)s byl vytvořen, přidej suroviny receptu"

    def get_success_url(self):
        return reverse_lazy('kitchen:createIngredient', kwargs={'pk': self.object.pk})


class RecipeUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = Recipe
    fields = "__all__"
    template_name = 'kitchen/recipe/update.html'
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


class StockReceiptListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = StockReceipt
    table_class = StockReceiptTable
    template_name = 'kitchen/stockreceipt/list.html'
    filterset_class = StockReceiptFilter
    form_class = StockReceiptSearchForm
    paginate_by = 12


class StockReceiptItemListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = Item
    table_class = StockReceiptItemTable
    template_name = 'kitchen/stockreceipt/listitems.html'
    filterset_class = StockReceiptItemFilter
    form_class = StockReceiptItemSearchForm
    paginate_by = 12

    def get_context_data(self, **kwargs):
        context = super(StockReceiptItemListView, self).get_context_data(**kwargs)
        context['stockreceipt'] = StockReceipt.objects.filter(pk=self.kwargs['pk'])
        return context


class StockReceiptCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = StockReceipt
    form_class = StockReceiptForm
    template_name = 'kitchen/stockreceipt/create.html'
    success_message = "Příjemka ze dne %(dateCreated)s byla vytvořena a je možné přidávat položky"
    success_url = reverse_lazy('kitchen:showStockReceipts')

    def form_valid(self, form):
        form.instance.userCreated = self.request.user
        self.object = form.save()
        return super(StockReceiptCreateView, self).form_valid(form)


class StockReceiptItemCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Item
    form_class = StockReceiptItemForm
    template_name = 'kitchen/stockreceipt/createitem.html'
    success_message = "Polozka příjemky byla vytvořena a zboží na skladu aktualizováno"

    def get_success_url(self):
        return reverse_lazy('kitchen:showStockReceiptItems', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super(StockReceiptItemCreateView, self).get_context_data(**kwargs)
        context['stockreceipt'] = StockReceipt.objects.filter(pk=self.kwargs['pk'])
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        stock_receipt = context['stockreceipt']
        print("stock_receipt ID:", stock_receipt[0].id)
        item = form.save(commit=False)
        item.stockReceipt = StockReceipt.objects.filter(pk=stock_receipt[0].id)[0]
        item.save()
        return super(StockReceiptItemCreateView, self).form_valid(form)


class StockReceiptUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = StockReceipt
    form_class = StockReceiptForm
    template_name = 'kitchen/stockreceipt/update.html'
    success_message = "Hlavička příjemky ze dne %(dateCreated)s byla aktualizována."
    success_url = reverse_lazy('kitchen:showStockReceipts')


class StockReceiptItemUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = Item
    form_class = StockReceiptItemForm
    template_name = 'kitchen/stockreceipt/updateitem.html'
    success_message = "Položka příjemky byla aktualizována."

    def get_success_url(self):
        return reverse_lazy('kitchen:showStockReceiptItems', kwargs={'pk': self.kwargs['pk']})


class StockReceiptDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = StockReceipt
    template_name = 'kitchen/stockreceipt/delete.html'
    success_message = "Příjemka ze dne %(dateCreated)s byla odstraněna"
    success_url = reverse_lazy('kitchen:showStockReceipts')


class StockReceiptItemDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = Item
    template_name = 'kitchen/stockreceipt/deleteitem.html'
    success_message = "Položka byla odstraněna"
    stock_receipt_id = 0

    def get_success_url(self):
        return reverse_lazy('kitchen:showStockReceiptItems', kwargs={'pk': self.stock_receipt_id})

    def delete(self, request, *args, **kwargs):
        item = get_object_or_404(Item, pk=self.kwargs['pk'])
        self.stock_receipt_id = item.stockReceipt.id
        return super(StockReceiptItemDeleteView, self).delete(request, *args, **kwargs)


class StockReceiptPDFView(LoginRequiredMixin, PDFTemplateView):
    template_name = 'kitchen/stockreceipt/pdf.html'
    filename = 'Prijemka.pdf'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stock_receipt = StockReceipt.objects.filter(pk=kwargs['pk'])
        items = Item.objects.filter(stockReceipt_id=kwargs['pk'])
        context['stock_receipt'] = stock_receipt
        context['items'] = items
        return context

    def get_success_url(self):
        return reverse_lazy('kitchen:showStockReceipts')


class DailyMenuListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = DailyMenu
    table_class = DailyMenuTable
    template_name = 'kitchen/dailymenu/list.html'
    filterset_class = DailyMenuFilter
    form_class = DailyMenuSearchForm
    paginate_by = 12


class DailyMenuCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = DailyMenu
    fields = "__all__"
    template_name = 'kitchen/dailymenu/create.html'
    success_message = "Denní menu pro den %(date)s bylo vytvořeno včetně výdejky ke schválení."

    def get_success_url(self):
        return reverse_lazy('kitchen:showDailyMenus')


class DailyMenuUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = DailyMenu
    fields = "__all__"
    template_name = 'kitchen/dailymenu/update.html'
    success_message = "Denní menu pro den %(date)s bylo aktualizováno včetně výdejky ke schválení."

    def get_success_url(self):
        return reverse_lazy('kitchen:showDailyMenus')


class DailyMenuDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = DailyMenu
    fields = "__all__"
    template_name = 'kitchen/dailymenu/delete.html'
    success_message = "Denní menu pro den %(date)s bylo odstraněno"

    def get_success_url(self):
        return reverse_lazy('kitchen:showDailyMenus')


class StockIssueListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = StockIssue
    table_class = StockIssueTable
    template_name = 'kitchen/stockissue/list.html'
    paginate_by = 12
