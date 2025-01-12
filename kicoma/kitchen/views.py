import logging
import io
from datetime import datetime
from contextlib import redirect_stdout
from dateutil import relativedelta
from urllib.parse import urlparse, urlunparse

from django.core import management
from django.core.files.storage import FileSystemStorage

from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import translation

from django.db import transaction, connection
from django.db.models import F, Count, Sum

from django.views.generic import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.views.generic.base import TemplateView, View

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.models import Group, ContentType, Permission

from django_tables2 import SingleTableMixin
from django_filters.views import FilterView

from tablib import Dataset

from kicoma.users.models import User

from .models import StockIssueArticle, StockReceiptArticle, Recipe, Allergen, MealType, MealGroup, \
    VAT, Article, RecipeArticle, StockIssue, StockReceipt, DailyMenu, Menu, MenuRecipe, DailyMenuRecipe
from .models import HistoricalArticle

from .tables import StockReceiptTable, StockReceiptArticleTable, StockReceiptFilter
from .tables import StockIssueTable, StockIssueArticleTable, StockIssueFilter
from .tables import ArticleTable, ArticleRestrictedTable, ArticleFilter
from .tables import DailyMenuTable, MenuTable, DailyMenuFilter
from .tables import DailyMenuRecipeTable, MenuRecipeTable
from .tables import RecipeTable, RecipeFilter, RecipeArticleTable

from .forms import RecipeForm, RecipeArticleForm, RecipeSearchForm
from .forms import StockReceiptForm, StockReceiptSearchForm, StockReceiptArticleForm
from .forms import StockIssueForm, StockIssueSearchForm, StockIssueArticleForm, StockIssueFromDailyMenuForm
from .forms import ArticleForm, ArticleRestrictedForm, ArticleSearchForm
from .forms import DailyMenuSearchForm, DailyMenuPrintForm, MenuForm, MenuRecipeForm, DailyMenuCreateForm, \
                   DailyMenuEditForm, DailyMenuRecipeForm
from .forms import DailyMenuCateringUnitForm

from .functions import convert_units

from .admin import ArticleResource

# Get an instance of a logger
logger = logging.getLogger(__name__)


def about(request):
    return render(request, 'kitchen/about.html')


def changelog(request):
    return render(request, 'kitchen/changelog.html')


def docs(request):
    allergen_count = Allergen.objects.all().count()
    meal_type_count = MealType.objects.all().count()
    meal_group_count = MealGroup.objects.all().count()
    vat_count = VAT.objects.all().count()
    recipe_count = Recipe.objects.all().count()
    recipe_article_count = RecipeArticle.objects.all().count()
    article_count = Article.objects.all().count()
    article_allergen_count = Article.objects.all().aggregate(count=Count('allergen'))['count']
    historical_article_count = HistoricalArticle.objects.all().count()
    stock_issue_count = StockIssue.objects.all().count()
    stock_receipt_count = StockReceipt.objects.all().count()
    stock_issue_article_count = StockIssueArticle.objects.all().count()
    stock_receipt_article_count = StockReceiptArticle.objects.all().count()
    daily_menu_count = DailyMenu.objects.all().count()
    daily_menu_recipe_count = DailyMenuRecipe.objects.all().count()

    user_count = User.objects.all().count()
    group_count = Group.objects.all().count()

    # service tables content
    content_type_count = ContentType.objects.all().count()
    permission_count = Permission.objects.all().count()
    with connection.cursor() as cursor:
        cursor.execute('select count(*) from django_migrations')
        row = cursor.fetchone()
        migration_count = row[0]

    with connection.cursor() as cursor:
        cursor.execute('select count(*) from django_session')
        row = cursor.fetchone()
        session_count = row[0]

    with connection.cursor() as cursor:
        cursor.execute('select count(*) from django_site')
        row = cursor.fetchone()
        site_count = row[0]

    with connection.cursor() as cursor:
        cursor.execute('select count(*) from users_user_groups')
        row = cursor.fetchone()
        user_group_rel_count = row[0]

    total_records = allergen_count + meal_type_count + meal_group_count + \
        vat_count + recipe_count + recipe_article_count + article_count + article_allergen_count + \
        historical_article_count + stock_issue_count + stock_receipt_count + stock_issue_article_count + \
        stock_receipt_article_count + daily_menu_count + daily_menu_recipe_count + user_count + group_count + \
        content_type_count + permission_count + migration_count + session_count + site_count + user_group_rel_count

    return render(request, 'kitchen/docs.html', {
        'allergenCount': allergen_count,
        'meal_typeCount': meal_type_count,
        'mealGroupCount': meal_group_count,
        'vatCount': vat_count,

        'recipeCount': recipe_count,
        'recipe_article_count': recipe_article_count,
        'article_count': article_count,
        'article_allergen_count': article_allergen_count,
        'historical_article_count': historical_article_count,
        'stockIssueCount': stock_issue_count,
        'stockReceiptCount': stock_receipt_count,
        'stock_issue_article_count': stock_issue_article_count,
        'stock_receipt_article_count': stock_receipt_article_count,
        'dailyMenuCount': daily_menu_count,
        'dailyMenuRecipeCount': daily_menu_recipe_count,

        "groupCount": group_count,
        "userCount": user_count,

        "content_type_count": content_type_count,
        'permission_count': permission_count,
        "migration_count": migration_count,
        "session_count": session_count,
        'site_count': site_count,
        'user_group_rel_count': user_group_rel_count,

        'total_records': total_records
    })


@login_required
def export_data(request):
    file_name = 'data.json'
    with open(file_name, "w") as f:
        management.call_command('dumpdata', 'kitchen', exclude=['contenttypes', 'auth'], stdout=f)
        f.close()
        response = HttpResponse(open(file_name, "rb"), content_type="application/json")
        response['Content-Disposition'] = 'attachment; filename='+file_name
        messages.success(request, "Všechna data byla exportována")
        return response


class ImportDataView(LoginRequiredMixin, TemplateView):
    template_name = 'kitchen/import.html'

    def post(self, request):
        context = {}
        if len(request.FILES) == 0:
            messages.error(
                self.request,
                "Není vybrán vstupní soubor, použij tlačítko Browse a vyber soubor.")
            return super(ImportDataView, self).render_to_response(context)
        uploaded_file = request.FILES['myfile']
        fs = FileSystemStorage()
        filename = fs.save(uploaded_file.name, uploaded_file)
        f = io.StringIO()
        try:
            with redirect_stdout(f):
                management.call_command('flush', interactive=False, verbosity=1)
                management.call_command('loaddata', "./kicoma/kitchen/fixtures/skupiny.json", verbosity=1)
                management.call_command('loaddata', "./kicoma/kitchen/fixtures/uzivatele.json", verbosity=1)
                management.call_command('loaddata', fs.path(filename), verbosity=1)
                messages.success(self.request, "Data úspěšně nahrána: "+f.getvalue())
        except Exception as e:
            messages.success(self.request, "Chyba při výmazu dat před importem: "+str(e))
        return super(ImportDataView, self).render_to_response(context)


def switch_language(request):
    if request.method == 'POST':
        user_language = request.POST.get('language', translation.get_language())
        translation.activate(user_language)
        request.session[settings.LANGUAGE_COOKIE_NAME] = user_language
        request.session.save()
        referer = request.META.get('HTTP_REFERER', '/')
        parsed_url = urlparse(referer)
        relative_url = urlunparse(('', '', parsed_url.path, parsed_url.params, parsed_url.query, ''))
        # Ensure the URL has the correct language prefix
        if user_language == "cs":
            response = redirect(f'{relative_url[3:]}')
        else:
            response = redirect(f'/{user_language}{relative_url}')
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, user_language)
        return response
    else:
        return HttpResponseBadRequest('Invalid request method.')


class ArticleListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = Article
    table_class = ArticleTable
    template_name = 'kitchen/article/list.html'
    filterset_class = ArticleFilter
    form_class = ArticleSearchForm
    paginate_by = settings.PAGINATE_BY

    def get_context_data(self, **kwargs):
        context = super(ArticleListView, self).get_context_data(**kwargs)
        context['total_stock_price'] = Article.sum_total_price()
        return context


class ArticleRestrictedListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = Article
    table_class = ArticleRestrictedTable
    template_name = 'kitchen/article/restricted_list.html'
    filterset_class = ArticleFilter
    form_class = ArticleSearchForm
    paginate_by = settings.PAGINATE_BY


class ArticleLackListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = Article
    table_class = ArticleTable
    template_name = 'kitchen/article/listlack.html'
    filterset_class = ArticleFilter
    form_class = ArticleSearchForm
    paginate_by = settings.PAGINATE_BY

    def get_queryset(self):
        # show only articles where
        return super().get_queryset().filter(on_stock__lt=F('min_on_stock'))


class ArticleCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Article
    form_class = ArticleForm
    template_name = 'kitchen/article/create.html'
    success_message = "Skladová karta %(article)s byla založeno, je možné zadávat příjemky a recepty"
    success_url = reverse_lazy('kitchen:showArticles')


class ArticleUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = Article
    form_class = ArticleForm
    template_name = 'kitchen/article/update.html'
    success_message = "Skladová karta %(article)s byla aktualizována"
    success_url = reverse_lazy('kitchen:showArticles')


class ArticleRestrictedUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = Article
    form_class = ArticleRestrictedForm
    template_name = 'kitchen/article/restricted_update.html'
    success_message = "Skladová karta %(article)s byla aktualizována"
    success_url = reverse_lazy('kitchen:showRestrictedArticles')


class ArticleDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = Article
    template_name = 'kitchen/article/delete.html'
    success_message = "Skladová karta byla odstraněna"
    success_url = reverse_lazy('kitchen:showArticles')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        recipe_articles = RecipeArticle.objects.filter(article=obj)
        context['recipe_articles'] = recipe_articles
        return context

    def form_valid(self, form):
        return super(ArticleDeleteView, self).form_valid(form)


class ArticlePDFView(LoginRequiredMixin, TemplateView):
    template_name = 'kitchen/article/pdf.html'
    file_name = 'Seznam_zbozi.pdf'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['articles'] = Article.objects.all()
        context['title'] = "Seznam zboží na skladu"
        context['total_stock_price'] = Article.sum_total_price()
        return context
    
    # def render_to_response(self, context, **kwargs):
    #    return html_to_pdf(self.file_name, self.template_name, context)


class ArticleExportView(LoginRequiredMixin, View):

    def get(self, *args, **kwargs):
        data = ArticleResource().export()
        response = HttpResponse(
            data.xlsx, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response['Content-Disposition'] = 'attachment; filename=seznam-zbozi.xlsx'
        messages.success(self.request, "Seznam zboží byl exportován")
        return response


class ArticleImportView(LoginRequiredMixin, TemplateView):
    template_name = 'kitchen/article/import.html'

    def post(self, request, **kwargs):
        article_resource = ArticleResource()
        dataset = Dataset()
        context = {}  # set your context
        if len(request.FILES) == 0:
            messages.error(
                self.request,
                "Není vybrán vstupní soubor, použij tlačítko Browse a vyber exportovaný a upravený MS Excel soubor.")
            return super(ArticleImportView, self).render_to_response(context)
        new_articles = request.FILES['myfile']
        imported_data = dataset.load(new_articles.read())
        result = article_resource.import_data(imported_data, dry_run=True,
                                              collect_failed_rows=True)  # Test the data import
        if result.has_errors() or result.has_validation_errors():
            messages.error(self.request, "Chyba v průběhu importu. Chybná data: {}".format(result.failed_dataset))
        else:
            article_resource.import_data(imported_data, dry_run=False)  # Actually import now
            messages.success(self.request, "Seznam zboží byl importován. Importováno {} řádků, z toho {} vloženo, \
                {} aktualizováno, {} vymazáno, {} přeskočeno, {} s chybou a {} neplatných řádků"
                             .format(result.total_rows, result.totals['new'], result.totals['update'],
                                     result.totals['delete'], result.totals['skip'], result.totals['error'],
                                     result.totals['invalid']))
        return super(ArticleImportView, self).render_to_response(context)


class ArticleHistoryDetailView(LoginRequiredMixin, DetailView):
    model = Article
    template_name = 'kitchen/article/listhistory.html'

    def get_context_data(self, **kwargs):
        context = super(ArticleHistoryDetailView, self).get_context_data(**kwargs)
        context['article_name'] = kwargs['object'].article
        context['table'] = kwargs['object'].history.all()
        return context


class StockTakePDFView(LoginRequiredMixin, TemplateView):
    template_name = 'kitchen/stocktake/pdf.html'
    filename = 'Seznam_zbozi_na_skladu.pdf'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['articles'] = Article.objects.all()
        context['title'] = "Seznam zboží na skladu ke kontrole"
        return context


class RecipeListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = Recipe
    table_class = RecipeTable
    template_name = 'kitchen/recipe/list.html'
    filterset_class = RecipeFilter
    form_class = RecipeSearchForm
    paginate_by = settings.PAGINATE_BY


class RecipeCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Recipe
    form_class = RecipeForm
    template_name = 'kitchen/recipe/create.html'
    success_message = "Recept %(recipe)s byl vytvořen, přidej ingredience"

    def get_success_url(self):
        return reverse_lazy('kitchen:showRecipeArticles', kwargs={'pk': self.object.id})


class RecipeUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = Recipe
    form_class = RecipeForm
    template_name = 'kitchen/recipe/update.html'
    success_message = "Recept %(recipe)s byl aktualizován"
    success_url = reverse_lazy('kitchen:showRecipes')


class RecipeDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = Recipe
    template_name = 'kitchen/recipe/delete.html'
    success_message = "Recept byl odstraněn"
    success_url = reverse_lazy('kitchen:showRecipes')

    def form_valid(self, form):
        return super(RecipeDeleteView, self).form_valid(form)


class RecipeListPDFView(LoginRequiredMixin, TemplateView):
    template_name = 'kitchen/recipe/pdf_list.html'
    filename = 'Seznam_receptu.pdf'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recipes'] = Recipe.objects.all()
        context['recipes_total'] = Recipe.objects.all().count()
        context['title'] = "Seznam receptů"
        return context


class RecipePDFView(LoginRequiredMixin, TemplateView):
    template_name = 'kitchen/recipe/pdf.html'
    filename = 'Recept.pdf'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recipe = Recipe.objects.filter(pk=self.kwargs['pk']).get()
        context['recipe'] = recipe
        context['recipe_articles'] = RecipeArticle.objects.filter(recipe=recipe)
        context['title'] = recipe.recipe
        return context


class RecipeArticleListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = RecipeArticle
    table_class = RecipeArticleTable
    template_name = 'kitchen/recipe/listarticles.html'
    paginate_by = settings.PAGINATE_BY

    def get_context_data(self, **kwargs):
        context = super(RecipeArticleListView, self).get_context_data(**kwargs)
        context['recipe'] = Recipe.objects.filter(pk=self.kwargs['pk'])[0]
        return context

    def get_queryset(self):
        # show only recipe ingredients
        return super().get_queryset().filter(recipe=self.kwargs["pk"])


class RecipeArticleCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = RecipeArticle
    form_class = RecipeArticleForm
    template_name = 'kitchen/recipe/createarticle.html'
    success_message = "Zboží %(article)s bylo přidáno do receptu"

    def get_success_url(self):
        # return reverse_lazy('kitchen:showRecipeCreateArticle', kwargs={'pk': self.kwargs['pk']})
        return reverse_lazy('kitchen:createRecipeArticle', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super(RecipeArticleCreateView, self).get_context_data(**kwargs)
        context['recipe'] = Recipe.objects.filter(pk=self.kwargs['pk']).get()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        recipe = context['recipe']
        recipe_article = form.save(commit=False)
        try:
            convert_units(recipe_article.amount,
                          recipe_article.unit, recipe_article.article.unit)
        except ValidationError as err:
            messages.warning(self.request, err.message)
            return super(RecipeArticleCreateView, self).form_invalid(form)
        recipe_article.recipe = Recipe.objects.filter(pk=recipe.id).get()
        recipe_article.save()
        return super(RecipeArticleCreateView, self).form_valid(form)


class RecipeArticleUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = RecipeArticle
    form_class = RecipeArticleForm
    template_name = 'kitchen/recipe/updatearticle.html'
    success_message = "Zboží %(article)s bylo aktualizováno"

    def get_success_url(self):
        return reverse_lazy('kitchen:showRecipeArticles', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super(RecipeArticleUpdateView, self).get_context_data(**kwargs)
        context['recipe_article_before'] = RecipeArticle.objects.filter(pk=self.kwargs['pk']).get()
        return context

    def form_valid(self, form):
        recipe_article = form.save(commit=False)
        try:
            convert_units(recipe_article.amount,
                          recipe_article.unit, recipe_article.article.unit)
        except ValidationError as err:
            messages.warning(self.request, err.message)
            return super(RecipeArticleUpdateView, self).form_invalid(form)
        recipe_article.recipe = RecipeArticle.objects.filter(pk=recipe_article.id)[0].recipe
        recipe_article.save()
        self.kwargs = {'pk': recipe_article.recipe.id}
        return super(RecipeArticleUpdateView, self).form_valid(form)


class RecipeArticleDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = RecipeArticle
    template_name = 'kitchen/recipe/deletearticle.html'
    success_message = "Zboží bylo odstraněno"
    recipe_id = 0

    def get_success_url(self):
        return reverse_lazy('kitchen:showRecipeArticles', kwargs={'pk': self.recipe_id})

    def get_context_data(self, **kwargs):
        context = super(RecipeArticleDeleteView, self).get_context_data(**kwargs)
        context['recipe_article_before'] = RecipeArticle.objects.filter(pk=self.kwargs['pk']).get()
        return context

    def form_valid(self, form):
        recipe_article = get_object_or_404(RecipeArticle, pk=self.kwargs['pk'])
        self.recipe_id = recipe_article.recipe.id
        return super(RecipeArticleDeleteView, self).form_valid(form)


class DailyMenuListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = DailyMenu
    table_class = DailyMenuTable
    template_name = 'kitchen/dailymenu/list.html'
    filterset_class = DailyMenuFilter
    form_class = DailyMenuSearchForm
    paginate_by = settings.PAGINATE_BY


class DailyMenuCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = DailyMenu
    form_class = DailyMenuCreateForm
    template_name = 'kitchen/dailymenu/create.html'
    success_message = "Denní menu pro den %(date)s bylo vytvořeno, přidej recepty"

    def get_success_url(self):
        return reverse_lazy('kitchen:showDailyMenus')

    def form_valid(self, form):
        daily_menu = form.save()
        if form.data['menu']:
            menu_recipes = MenuRecipe.objects.filter(menu=daily_menu.menu)
            for menu_recipe in menu_recipes:
                DailyMenuRecipe.objects.create(
                    daily_menu=daily_menu,
                    recipe=menu_recipe.recipe,
                    amount=menu_recipe.amount,
                    comment="Recept byl převzatý z menu"
                )
        return HttpResponseRedirect(self.get_success_url())


class DailyMenuUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = DailyMenu
    form_class = DailyMenuEditForm
    template_name = 'kitchen/dailymenu/update.html'
    success_message = "Denní menu pro den %(date)s bylo aktualizováno včetně výdejky ke schválení"
    success_url = reverse_lazy('kitchen:showDailyMenus')


class DailyMenuDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = DailyMenu
    template_name = 'kitchen/dailymenu/delete.html'
    success_message = "Denní menu bylo odstraněno"
    success_url = reverse_lazy('kitchen:showDailyMenus')

    def form_valid(self, form):
        return super(DailyMenuDeleteView, self).form_valid(form)


class DailyMenuPDFView(LoginRequiredMixin, TemplateView):
    template_name = 'kitchen/dailymenu/pdf.html'
    filename = 'Denni_menu.pdf'

    def get(self, request, *args, **kwargs):
        try:
            date = request.GET['date']
            datetime.strptime(date, "%d.%m.%Y")
        except ValueError as e:
            messages.warning(self.request, "Chybně zadané datum. Požadovaný formát je dd.mm.rr. Chyba: {}".format(e))
            return HttpResponseRedirect(reverse_lazy('kitchen:filterPrintDailyMenu'))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        date = self.request.GET['date']
        meal_group = self.request.GET['meal_group']
        if len(meal_group) == 0:
            daily_menu_recipes = DailyMenuRecipe.objects.filter(daily_menu__date=datetime.strptime(date, "%d.%m.%Y"))
        else:
            daily_menu_recipes = DailyMenuRecipe.objects.filter(
                daily_menu__date=datetime.strptime(date, "%d.%m.%Y"), daily_menu__meal_group=meal_group)
            context['meal_group_filter'] = "Filtrováno pro skupinu strávníků: " + \
                MealGroup.objects.filter(pk=meal_group).get().meal_group
        context['title'] = "Denní menu pro " + date
        context['daily_menu_recipes'] = daily_menu_recipes
        return context


class DailyMenuPrintView(LoginRequiredMixin, CreateView):
    model = DailyMenu
    form_class = DailyMenuPrintForm
    template_name = 'kitchen/dailymenu/print.html'


class MenuListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = Menu
    table_class = MenuTable
    template_name = 'kitchen/menu/list.html'
    paginate_by = settings.PAGINATE_BY


class MenuCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Menu
    form_class = MenuForm
    template_name = 'kitchen/menu/create.html'
    success_message = "Menu bylo vytvořeno, přidej recepty"

    def get_success_url(self):
        return reverse_lazy('kitchen:showMenuRecipes', kwargs={'pk': self.object.id})


class MenuUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = Menu
    form_class = MenuForm
    template_name = 'kitchen/menu/update.html'
    success_message = "Menu bylo aktualizováno"
    success_url = reverse_lazy('kitchen:showMenus')


class MenuDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = Menu
    template_name = 'kitchen/menu/delete.html'
    success_message = "Menu bylo odstraněno"
    success_url = reverse_lazy('kitchen:showMenus')

    def form_valid(self, form):
        return super(MenuDeleteView, self).form_valid(form)


class MenuRecipeListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = MenuRecipe
    table_class = MenuRecipeTable
    template_name = 'kitchen/menu/listrecipe.html'
    paginate_by = settings.PAGINATE_BY

    def get_context_data(self, **kwargs):
        context = super(MenuRecipeListView, self).get_context_data(**kwargs)
        context['menu'] = Menu.objects.filter(pk=self.kwargs['pk'])[0]
        return context

    def get_queryset(self):
        # show only DailyMeny recipes
        return super().get_queryset().filter(menu=self.kwargs["pk"])


class MenuRecipeCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = MenuRecipe
    form_class = MenuRecipeForm
    template_name = 'kitchen/menu/createrecipe.html'
    success_message = "Recept %(recipe)s byl přidán"

    def get_success_url(self):
        return reverse_lazy('kitchen:showMenuRecipes', kwargs={'pk': self.object.menu.id})

    def get_context_data(self, **kwargs):
        context = super(MenuRecipeCreateView, self).get_context_data(**kwargs)
        context['menu'] = Menu.objects.filter(pk=self.kwargs['pk']).get()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        menu = context['menu']
        menu_recipe = form.save(commit=False)
        menu_recipe.menu = Menu.objects.filter(pk=menu.id)[0]
        menu_recipe.save()
        return super(MenuRecipeCreateView, self).form_valid(form)


class MenuRecipeUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = MenuRecipe
    form_class = MenuRecipeForm
    template_name = 'kitchen/menu/updaterecipe.html'
    success_message = "Recept %(recipe)s byl aktualizován"

    def get_success_url(self):
        return reverse_lazy('kitchen:showMenuRecipes', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super(MenuRecipeUpdateView, self).get_context_data(**kwargs)
        context['menurecipe_before'] = MenuRecipe.objects.filter(pk=self.kwargs['pk'])[0]
        return context

    def form_valid(self, form):
        menu_recipe = form.save(commit=False)
        menu_recipe.menu = MenuRecipe.objects.filter(pk=menu_recipe.id)[0].menu
        menu_recipe.save()
        self.kwargs = {'pk': menu_recipe.menu.id}
        return super(MenuRecipeUpdateView, self).form_valid(form)


class MenuRecipeDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = MenuRecipe
    template_name = 'kitchen/menu/deleterecipe.html'
    success_message = "Recept byl z menu odstraněn"
    daily_menu_id = 0

    def get_success_url(self):
        return reverse_lazy('kitchen:showMenuRecipes', kwargs={'pk': self.menu_id})

    def get_context_data(self, **kwargs):
        context = super(MenuRecipeDeleteView, self).get_context_data(**kwargs)
        context['menurecipe_before'] = MenuRecipe.objects.filter(pk=self.kwargs['pk']).get()
        return context

    def form_valid(self, form):
        recipe = get_object_or_404(MenuRecipe, pk=self.kwargs['pk'])
        self.menu_id = recipe.menu.id
        return super(MenuRecipeDeleteView, self).form_valid(form)


class DailyMenuRecipeListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = DailyMenuRecipe
    table_class = DailyMenuRecipeTable
    template_name = 'kitchen/dailymenu/listrecipe.html'
    paginate_by = settings.PAGINATE_BY

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
        context['daily_menu'] = DailyMenu.objects.filter(pk=self.kwargs['pk']).get()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        daily_menu = context['daily_menu']
        daily_menu_recipe = form.save(commit=False)
        daily_menu_recipe.daily_menu = DailyMenu.objects.filter(pk=daily_menu.id)[0]
        daily_menu_recipe.save()
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
        daily_menu_recipe = form.save(commit=False)
        daily_menu_recipe.daily_menu = DailyMenuRecipe.objects.filter(pk=daily_menu_recipe.id)[0].daily_menu
        daily_menu_recipe.save()
        self.kwargs = {'pk': daily_menu_recipe.daily_menu.id}
        return super(DailyMenuRecipeUpdateView, self).form_valid(form)


class DailyMenuRecipeDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = DailyMenuRecipe
    template_name = 'kitchen/dailymenu/deleterecipe.html'
    success_message = "Recept byl odstraněn"
    daily_menu_id = 0

    def get_success_url(self):
        return reverse_lazy('kitchen:showDailyMenuRecipes', kwargs={'pk': self.daily_menu_id})

    def get_context_data(self, **kwargs):
        context = super(DailyMenuRecipeDeleteView, self).get_context_data(**kwargs)
        context['dailymenurecipe_before'] = DailyMenuRecipe.objects.filter(pk=self.kwargs['pk']).get()
        return context

    def form_valid(self, form):
        recipe = get_object_or_404(DailyMenuRecipe, pk=self.kwargs['pk'])
        self.daily_menu_id = recipe.daily_menu.id
        return super(DailyMenuRecipeDeleteView, self).form_valid(form)


class StockIssueListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = StockIssue
    table_class = StockIssueTable
    template_name = 'kitchen/stockissue/list.html'
    filterset_class = StockIssueFilter
    form_class = StockIssueSearchForm
    paginate_by = settings.PAGINATE_BY


class StockIssueCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = StockIssue
    form_class = StockIssueForm
    template_name = 'kitchen/stockissue/create.html'
    success_message = "Výdejka byla vytvořena a je možné přidávat zboží"

    def form_valid(self, form):
        form.instance.user_created = self.request.user
        self.object = form.save()
        return super(StockIssueCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('kitchen:createStockIssueArticle', kwargs={'pk': self.object.id})


class StockIssueFromDailyMenuCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = StockIssue
    form_class = StockIssueFromDailyMenuForm
    template_name = 'kitchen/stockissue/create_from_daily_menu.html'
    success_url = reverse_lazy('kitchen:showStockIssues')

    # do not save form which contains DailyMenu but save StockIssue on that date
    def form_valid(self, form):
        date = self.request.POST['date']
        daily_menus = DailyMenu.objects.filter(date=datetime.strptime(date, "%d.%m.%Y"))
        if len(daily_menus) < 1:
            form.add_error('date', "Pro zadané datum není vytvořeno denní menu")
            return super(StockIssueFromDailyMenuCreateView, self).form_invalid(form)
        count = StockIssue.create_from_daily_menu(daily_menus, date, self.request.user)
        messages.success(
            self.request, 'Výdejka pro den {} vytvořena a vyskladňuje {} druhů zboží'.format(date, count))
        return HttpResponseRedirect(self.success_url)


class StockIssueUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = StockIssue
    form_class = StockIssueForm
    template_name = 'kitchen/stockissue/update.html'
    success_message = "Poznámka výdejky byla aktualizována"
    success_url = reverse_lazy('kitchen:showStockIssues')


class StockIssueRefreshView(LoginRequiredMixin, View):
    model = StockIssue

    def get(self, *args, **kwargs):
        stock_issue = StockIssue.objects.filter(pk=kwargs['pk']).get()
        if stock_issue.approved:
            messages.warning(self.request, "Aktualizace neprovedena - výdejka je již vyskladněna")
            return HttpResponseRedirect(reverse_lazy('kitchen:showStockIssues',))
        comment = stock_issue.comment
        if "Pro " not in comment:
            messages.warning(self.request, "Aktualizace zboží je možná jenom pro výdejku vytvořenou z denního menu")
        else:
            date = comment[4:]
            with transaction.atomic():
                stock_issue.delete()
                daily_menus = DailyMenu.objects.filter(date=datetime.strptime(date, "%d.%m.%Y"))
                if len(daily_menus) < 1:
                    messages.error('date', "Pro zadané datum není vytvořeno denní menu")
                    return HttpResponseRedirect(reverse_lazy('kitchen:showStockIssues'))
                count = StockIssue.create_from_daily_menu(daily_menus, date, self.request.user)
                messages.success(
                    self.request, "Seznam zboží na výdejce byl aktualizován dle aktuálních receptů na denním menu a vyskladňuje {} druhů zboží".format(count))
        return HttpResponseRedirect(reverse_lazy('kitchen:showStockIssues'))


class StockIssueDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = StockIssue
    template_name = 'kitchen/stockissue/delete.html'
    success_message = "Výdejka byla odstraněna"
    success_url = reverse_lazy('kitchen:showStockIssues')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stock_issue = StockIssue.objects.filter(pk=self.kwargs['pk']).get()
        stock_issue_articles = StockIssueArticle.objects.filter(stock_issue_id=self.kwargs['pk'])
        context['stock_issue'] = stock_issue
        context['stock_issue_articles'] = stock_issue_articles
        context['total_price'] = stock_issue.total_price
        return context

    def post(self, request, *args, **kwargs):
        stock_issue = StockIssue.objects.filter(pk=self.kwargs['pk']).get()
        if stock_issue.approved:
            messages.warning(self.request, "Výmaz neproveden - výdejka je již vyskladněna")
            return HttpResponseRedirect(reverse_lazy('kitchen:showStockIssues',))
        return super(StockIssueDeleteView, self).post(request, *args, **kwargs)


class StockIssuePDFView(SuccessMessageMixin, LoginRequiredMixin, TemplateView):
    template_name = 'kitchen/stockissue/pdf.html'
    filename = 'Výdejka-' + datetime.now().strftime("%Y.%m.%d_%H-%M-%S-%f") + '.pdf'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stock_issue = StockIssue.objects.filter(pk=self.kwargs['pk']).get()
        stock_issue_articles = StockIssueArticle.objects.filter(
            stock_issue_id=self.kwargs['pk']).order_by('article__article')
        context['stock_issue'] = stock_issue
        context['stock_issue_articles'] = stock_issue_articles
        context['title'] = "Výdejka"
        context['total_price'] = stock_issue.total_price
        return context


class StockIssueApproveView(LoginRequiredMixin, TemplateView):
    model = StockIssue
    template_name = 'kitchen/stockissue/approve.html'
    fields = "__all__"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stock_issue = StockIssue.objects.filter(pk=self.kwargs['pk']).get()
        stock_issue_articles = StockIssueArticle.objects.filter(stock_issue_id=self.kwargs['pk'])
        context['stock_issue'] = stock_issue
        context['stock_issue_articles'] = stock_issue_articles
        context['total_price'] = stock_issue.total_price
        return context

    def post(self, *args, **kwargs):
        stock_issue = StockIssue.objects.filter(pk=self.kwargs['pk']).get()
        if stock_issue.approved:
            messages.warning(self.request, 'Vyskladnění neprovedeno - již bylo vyskladněno')
            return HttpResponseRedirect(reverse_lazy('kitchen:showStockIssues',))
        if stock_issue.total_price <= 0:
            messages.warning(
                self.request, 'Vyskladnění neprovedeno - nulová cena zboží, je zboží naskladněno?')
            return HttpResponseRedirect(reverse_lazy('kitchen:showStockIssues',))
        with transaction.atomic():
            stock_issue.approved = True
            stock_issue.date_approved = datetime.now()
            stock_issue.user_approved = self.request.user
            StockIssue.update_stock_issue_article_average_unit_price(stock_issue.id)
            errors = StockIssue.update_article_on_stock(stock_issue.id, stock_issue.comment, True)
            if errors:
                errors = "Níže uvedené zboží není možné vyskladnit:<br/>" + errors
                messages.error(self.request, mark_safe(errors))
                return HttpResponseRedirect(reverse_lazy('kitchen:approveStockIssue', kwargs={'pk': self.kwargs['pk']}))
            _ = StockIssue.update_article_on_stock(stock_issue.id, stock_issue.comment, False)
            stock_issue.save(update_fields=('approved', 'date_approved', 'user_approved',))
            messages.success(self.request, "Výdejka byla vyskladněna")
            return HttpResponseRedirect(reverse_lazy('kitchen:showStockIssues',))


class StockIssueArticleListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = StockIssueArticle
    table_class = StockIssueArticleTable
    template_name = 'kitchen/stockissue/listarticles.html'
    table_pagination = False
    paginate_by = settings.PAGINATE_BY

    def get_context_data(self, **kwargs):
        context = super(StockIssueArticleListView, self).get_context_data(**kwargs)
        context['stockissue'] = StockIssue.objects.filter(pk=self.kwargs['pk']).get()
        return context

    def get_queryset(self):
        # show only StockIssueArticles
        return super().get_queryset().filter(stock_issue=self.kwargs["pk"]).order_by('article__article')


class StockIssueArticleCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = StockIssueArticle
    form_class = StockIssueArticleForm
    template_name = 'kitchen/stockissue/createarticle.html'
    success_message = 'Zboží %(article)s bylo přidáno'

    def get_success_url(self):
        return reverse_lazy('kitchen:showStockIssueArticles', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super(StockIssueArticleCreateView, self).get_context_data(**kwargs)
        context['stockissue'] = StockIssue.objects.filter(pk=self.kwargs['pk']).get()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        stock_issue = context['stockissue']
        stock_issue_article = form.save(commit=False)
        try:
            convert_units(stock_issue_article.amount,
                          stock_issue_article.unit, stock_issue_article.article.unit)
        except ValidationError as err:
            messages.warning(self.request, err.message)
            return super(StockIssueArticleCreateView, self).form_invalid(form)
        stock_issue_article.stock_issue = StockIssue.objects.filter(pk=stock_issue.id).get()
        if stock_issue_article.stock_issue.approved:
            messages.warning(self.request, 'Přidání zboží neprovedeno, výdejka je již vyskladněna')
            return HttpResponseRedirect(
                reverse_lazy('kitchen:showStockIssueArticles', kwargs={'pk': stock_issue.id}))
        stock_issue_article.average_unit_price = stock_issue_article.article.average_price
        stock_issue_article.save()
        return super(StockIssueArticleCreateView, self).form_valid(form)


class StockIssueArticleUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = StockIssueArticle
    form_class = StockIssueArticleForm
    template_name = 'kitchen/stockissue/updatearticle.html'
    success_message = "Zboží %(article)s bylo aktualizováno"

    def get_success_url(self):
        return reverse_lazy('kitchen:showStockIssueArticles', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super(StockIssueArticleUpdateView, self).get_context_data(**kwargs)
        context['stock_issue_article_before'] = StockIssueArticle.objects.filter(pk=self.kwargs['pk']).get()
        return context

    def form_valid(self, form):
        stock_issue_article = form.save(commit=False)
        try:
            convert_units(stock_issue_article.amount,
                          stock_issue_article.unit, stock_issue_article.article.unit)
        except ValidationError as err:
            messages.warning(self.request, err.message)
            return super(StockIssueArticleUpdateView, self).form_invalid(form)
        stock_issue_article.stock_issue = StockIssueArticle.objects.filter(pk=stock_issue_article.id).get().stock_issue
        if stock_issue_article.stock_issue.approved:
            messages.warning(self.request, 'Aktualizace zboží neprovedena, výdejka je již vyskladněna')
            return HttpResponseRedirect(
                reverse_lazy('kitchen:showStockIssueArticles', kwargs={'pk': stock_issue_article.stock_issue.id}))
        stock_issue_article.average_unit_price = stock_issue_article.article.average_price
        stock_issue_article.save()
        self.kwargs = {'pk': stock_issue_article.stock_issue.id}
        return super(StockIssueArticleUpdateView, self).form_valid(form)


class StockIssueArticleDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = StockIssueArticle
    template_name = 'kitchen/stockissue/deletearticle.html'
    success_message = "Zboží bylo odstraněno"
    success_url = reverse_lazy('kitchen:showStockIssues')
    stock_issue_id = 0

    def get_success_url(self):
        return reverse_lazy('kitchen:showStockIssueArticles', kwargs={'pk': self.stock_issue_id})

    def form_valid(self, form):
        stock_issue_article = get_object_or_404(StockIssueArticle, pk=self.kwargs['pk'])
        if stock_issue_article.stock_issue.approved:
            messages.warning(self.request, 'Odstranění zboží neprovedeno, výdejka je již vyskladněna')
            return HttpResponseRedirect(
                reverse_lazy('kitchen:showStockIssueArticles', kwargs={'pk': stock_issue_article.stock_issue.id}))
        self.stock_issue_id = stock_issue_article.stock_issue.id
        return super(StockIssueArticleDeleteView, self).form_valid(form)


class StockReceiptListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = StockReceipt
    table_class = StockReceiptTable
    template_name = 'kitchen/stockreceipt/list.html'
    filterset_class = StockReceiptFilter
    form_class = StockReceiptSearchForm
    paginate_by = settings.PAGINATE_BY


class StockReceiptCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = StockReceipt
    form_class = StockReceiptForm
    template_name = 'kitchen/stockreceipt/create.html'
    success_message = "Příjemka byla vytvořena a je možné přidávat zboží"

    def form_valid(self, form):
        form.instance.user_created = self.request.user
        self.object = form.save()
        return super(StockReceiptCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('kitchen:createStockReceiptArticle', kwargs={'pk': self.object.id})


class StockReceiptUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = StockReceipt
    form_class = StockReceiptForm
    template_name = 'kitchen/stockreceipt/update.html'
    success_message = "Poznámka příjemky byla aktualizována"
    success_url = reverse_lazy('kitchen:showStockReceipts')


class StockReceiptDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = StockReceipt
    template_name = 'kitchen/stockreceipt/delete.html'
    success_message = "Příjemka byla odstraněna"
    success_url = reverse_lazy('kitchen:showStockReceipts')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stock_receipt = StockReceipt.objects.filter(pk=self.kwargs['pk']).get()
        stock_receipt_articles = StockReceiptArticle.objects.filter(stock_receipt_id=self.kwargs['pk'])
        context['stock_receipt'] = stock_receipt
        context['stock_receipt_articles'] = stock_receipt_articles
        context['total_price'] = stock_receipt.total_price
        return context

    def post(self, request, *args, **kwargs):
        stock_receipt = StockReceipt.objects.filter(pk=self.kwargs['pk']).get()
        if stock_receipt.approved:
            messages.warning(self.request, "Výmaz neproveden - příjemka je již naskladněna")
            return HttpResponseRedirect(reverse_lazy('kitchen:showStockReceipts',))
        return super(StockReceiptDeleteView, self).post(request, *args, **kwargs)


class StockReceiptPDFView(LoginRequiredMixin, TemplateView):
    template_name = 'kitchen/stockreceipt/pdf.html'
    filename = 'Příjemka.pdf'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stock_receipt = StockReceipt.objects.filter(pk=self.kwargs['pk']).get()
        stock_receipt_articles = StockReceiptArticle.objects.filter(stock_receipt_id=self.kwargs['pk'])
        context['stock_receipt'] = stock_receipt
        context['stock_receipt_articles'] = stock_receipt_articles
        context['title'] = "Příjemka"
        context['total_price'] = stock_receipt.total_price
        return context


class StockReceiptApproveView(LoginRequiredMixin, TemplateView):
    model = StockReceipt
    template_name = 'kitchen/stockreceipt/approve.html'
    fields = "__all__"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stock_receipt = StockReceipt.objects.filter(pk=self.kwargs['pk']).get()
        stock_receipt_articles = StockReceiptArticle.objects.filter(stock_receipt_id=self.kwargs['pk'])
        context['stock_receipt'] = stock_receipt
        context['stock_receipt_articles'] = stock_receipt_articles
        context['total_price'] = stock_receipt.total_price
        return context

    def post(self, *args, **kwargs):
        stock_receipt = StockReceipt.objects.filter(pk=self.kwargs['pk']).get()
        if stock_receipt.approved:
            messages.warning(self.request, 'Naskladnění neprovedeno - již bylo naskladněno')
            return HttpResponseRedirect(reverse_lazy('kitchen:showStockReceipts',))
        if stock_receipt.total_price <= 0:
            messages.warning(
                self.request, 'Naskladnění neprovedeno - nulová cena zboží, přidejte alespoň jedno zboží na příjemku')
            return HttpResponseRedirect(reverse_lazy('kitchen:showStockReceipts',))
        with transaction.atomic():
            stock_receipt.approved = True
            stock_receipt.date_approved = datetime.now()
            stock_receipt.user_approved = self.request.user
            StockReceipt.update_article_on_stock(stock_receipt.id, stock_receipt.comment)
            stock_receipt.save(update_fields=('approved', 'date_approved', 'user_approved',))
            messages.success(self.request, "Příjemka byla naskladněna")
        return HttpResponseRedirect(reverse_lazy('kitchen:showStockReceipts',))


class StockReceiptArticleListView(SingleTableMixin, LoginRequiredMixin, FilterView):
    model = StockReceiptArticle
    table_class = StockReceiptArticleTable
    template_name = 'kitchen/stockreceipt/listarticles.html'
    table_pagination = False

    def get_context_data(self, **kwargs):
        context = super(StockReceiptArticleListView, self).get_context_data(**kwargs)
        context['stockreceipt'] = StockReceipt.objects.filter(pk=self.kwargs['pk']).get()
        return context

    def get_queryset(self):
        # show only StockReceiptArticles
        return super().get_queryset().filter(stock_receipt=self.kwargs["pk"])


class StockReceiptArticleCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = StockReceiptArticle
    form_class = StockReceiptArticleForm
    template_name = 'kitchen/stockreceipt/createarticle.html'
    success_message = 'Zboží %(article)s bylo přidáno: %(amount)s %(unit)s * %(unit_price)s Kč = %(total_price)s Kč'

    def get_success_url(self):
        return reverse_lazy('kitchen:createStockReceiptArticle', kwargs={'pk': self.kwargs['pk']})

    def get_success_message(self, cleaned_data):
        return self.success_message % dict(
            cleaned_data,
            unit_price=self.object.price_with_vat,
            total_price=self.object.total_price_with_vat
        )

    def get_context_data(self, **kwargs):
        context = super(StockReceiptArticleCreateView, self).get_context_data(**kwargs)
        context['stockreceipt'] = StockReceipt.objects.filter(pk=self.kwargs['pk'])[0]
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        stock_receipt = context['stockreceipt']
        stock_receipt_article = form.save(commit=False)
        try:
            convert_units(stock_receipt_article.amount,
                          stock_receipt_article.unit, stock_receipt_article.article.unit)
        except ValidationError as err:
            messages.warning(self.request, err.message)
            return super(StockReceiptArticleCreateView, self).form_invalid(form)
        stock_receipt_article.stock_receipt = StockReceipt.objects.filter(pk=stock_receipt.id).get()
        if stock_receipt_article.stock_receipt.approved:
            messages.warning(self.request, 'Přidání zboží neprovedeno, příjemka je již naskladněna')
            return HttpResponseRedirect(
                reverse_lazy('kitchen:showStockReceiptArticles', kwargs={'pk': stock_receipt.id}))
        stock_receipt_article.save()
        return super(StockReceiptArticleCreateView, self).form_valid(form)


class StockReceiptArticleUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = StockReceiptArticle
    form_class = StockReceiptArticleForm
    template_name = 'kitchen/stockreceipt/updatearticle.html'
    success_message = "Zboží %(article)s bylo aktualizováno"

    def get_success_url(self):
        return reverse_lazy('kitchen:showStockReceiptArticles', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super(StockReceiptArticleUpdateView, self).get_context_data(**kwargs)
        context['stock_receipt_article_before'] = StockReceiptArticle.objects.filter(pk=self.kwargs['pk']).get()
        return context

    def form_valid(self, form):
        stock_receipt_article = form.save(commit=False)
        try:
            convert_units(stock_receipt_article.amount,
                          stock_receipt_article.unit, stock_receipt_article.article.unit)
        except ValidationError as err:
            messages.warning(self.request, err.message)
            return super(StockReceiptArticleUpdateView, self).form_invalid(form)
        stock_receipt_article.stock_receipt = StockReceiptArticle.objects.filter(
            pk=stock_receipt_article.id).get().stock_receipt
        if stock_receipt_article.stock_receipt.approved:
            messages.warning(self.request, 'Aktualizace zboží neprovedena, příjemka je již naskladněna')
            return HttpResponseRedirect(
                reverse_lazy('kitchen:showStockReceiptArticles', kwargs={'pk': stock_receipt_article.stock_receipt.id}))
        stock_receipt_article.save()
        self.kwargs = {'pk': stock_receipt_article.stock_receipt.id}
        return super(StockReceiptArticleUpdateView, self).form_valid(form)


class StockReceiptArticleDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = StockReceiptArticle
    template_name = 'kitchen/stockreceipt/deletearticle.html'
    success_message = "Zboží bylo odstraněno"
    success_url = reverse_lazy('kitchen:showStockReceipts')
    stock_receipt_id = 0

    def get_success_url(self):
        return reverse_lazy('kitchen:showStockReceiptArticles', kwargs={'pk': self.stock_receipt_id})

    def form_valid(self, form):
        stock_receipt_article = get_object_or_404(StockReceiptArticle, pk=self.kwargs['pk'])
        if stock_receipt_article.stock_receipt.approved:
            messages.warning(self.request, 'Odstranění zboží neprovedeno, příjemka je již naskladněna')
            return HttpResponseRedirect(
                reverse_lazy('kitchen:showStockReceiptArticles', kwargs={'pk': self.kwargs['pk']}))
        self.stock_receipt_id = stock_receipt_article.stock_receipt.id
        return super(StockReceiptArticleDeleteView, self).form_valid(form)


def stock_issues_receipts_data(month):
    month = datetime.now() + relativedelta.relativedelta(months=-month)
    month_year = month.year
    month_month = month.month
    stock_issues = StockIssue.objects.filter(
        date_approved__year=month_year, date_approved__month=month_month)
    stock_receipts = StockReceipt.objects.filter(
        date_approved__year=month_year, date_approved__month=month_month)
    stock_issues_price = -1
    for si in stock_issues:
        stock_issues_price += si.total_price
    stock_receipts_price = -1
    for sr in stock_receipts:
        stock_receipts_price += sr.total_price
    return {
        'year': month_year,
        'month': month_month,
        'stock_issues_count': stock_issues.count(),
        'stock_issues_price': stock_issues_price,
        'stock_receipts_count': stock_receipts.count(),
        'stock_receipts_price': stock_receipts_price
    }


class ShowFoodConsumptionTotalPrice(LoginRequiredMixin, TemplateView):
    template_name = 'kitchen/report/show_stock_issues_receipts_total_price.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['all_data'] = [
            stock_issues_receipts_data(0),
            stock_issues_receipts_data(1),
            stock_issues_receipts_data(2),
            stock_issues_receipts_data(3),
            stock_issues_receipts_data(4),
            stock_issues_receipts_data(5),
            #stock_issues_receipts_data(6),
            #stock_issues_receipts_data(7),
            #stock_issues_receipts_data(8),
            #stock_issues_receipts_data(9),
            #stock_issues_receipts_data(10),
            #stock_issues_receipts_data(11),
            #stock_issues_receipts_data(12),
            #stock_issues_receipts_data(13),
        ]

        return context


class IncorrectUnitsListView(SingleTableMixin, LoginRequiredMixin, ListView):
    model = Recipe
    template_name = 'kitchen/report/incorrect-units.html'

    def get_queryset(self):
        # show only recipes where article unit cannot be converted to stock article unit
        recipes = super().get_queryset()
        incorrect_recipes = set()
        for recipe in recipes:
            recipe_articles = RecipeArticle.objects.filter(recipe=recipe)
            for recipe_article in recipe_articles:
                try:
                    convert_units(recipe_article.amount,
                                  recipe_article.unit, recipe_article.article.unit)
                except ValidationError:
                    incorrect_recipes.add(recipe.pk)
        return Recipe.objects.filter(pk__in=incorrect_recipes)


class ArticlesNotInRecipesListView(SingleTableMixin, LoginRequiredMixin, ListView):
    model = Article
    template_name = 'kitchen/report/articles_not_in_recipe.html'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        articles_on_recipes = RecipeArticle.objects.values_list('article__id')
        articles = Article.objects.exclude(pk__in=articles_on_recipes)
        context['articles'] = articles
        return context


class CateringUnitShowView(LoginRequiredMixin, TemplateView):
    template_name = 'kitchen/report/catering_unit_show.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        date = self.request.GET['date']
        daily_menu_ids = DailyMenu.objects.filter(date=datetime.strptime(date, "%d.%m.%Y")).values('id')
        daily_menu_recipes = DailyMenuRecipe.objects.filter(daily_menu__in=daily_menu_ids)
        recipes = Recipe.objects.filter(id__in=daily_menu_recipes.values('recipe'))

        output = []
        total_price = 0
        for recipe in recipes:
            daily_menu_recipes = DailyMenuRecipe.objects.filter(
                daily_menu__in=daily_menu_ids
            ).filter(recipe=recipe).values('recipe').annotate(amount=Sum('amount'))[0]
            unit_price = recipe.total_recipe_articles_price / recipe.norm_amount
            output_new = {
                "recipe": recipe.recipe,
                "unit_price": unit_price,
                "amount": daily_menu_recipes['amount'],
                "total_price": unit_price * daily_menu_recipes['amount']
            }
            output.append(output_new)
            total_price += unit_price * daily_menu_recipes['amount']

        context['date'] = date
        context['daily_menu_recipes'] = output
        context['daily_menu_recipes_total'] = len(output)
        context['daily_menu_recipes_total_price'] = total_price
        return context


class CateringUnitFilterView(LoginRequiredMixin, CreateView):
    model = DailyMenu
    form_class = DailyMenuCateringUnitForm
    template_name = 'kitchen/report/catering_unit_filter.html'
