import contextlib
import io
import logging
import tempfile
from collections import defaultdict
from contextlib import redirect_stdout
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlencode, urlparse, urlunparse

from dateutil import relativedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.views import SuccessMessageMixin
from django.core import management
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, transaction
from django.db.models import Count, F, Max, Prefetch, ProtectedError, Sum
from django.db.models.functions import ExtractYear, Lower
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import formats, timezone, translation
from django.utils.decorators import method_decorator
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.views.generic.list import ListView
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin
from tablib import Dataset
from weasyprint import HTML

from kicoma.users.models import User

from .admin import ArticleResource
from .forms import (
    ArticleForm,
    ArticleSearchForm,
    DailyMenuCateringUnitForm,
    DailyMenuCreateForm,
    DailyMenuEditForm,
    DailyMenuPrintForm,
    DailyMenuRecipeForm,
    MenuForm,
    MenuRecipeForm,
    RecipeArticleForm,
    RecipeForm,
    RecipeSearchForm,
    StockArticlesExportForm,
    StockIssueArticleForm,
    StockIssueForm,
    StockIssueFromDailyMenuForm,
    StockIssueSearchForm,
    StockReceiptArticleForm,
    StockReceiptForm,
    StockReceiptSearchForm,
    UnitChangeForm,
)
from .functions import convert_units, format_decimal, format_unit_price
from .models import (
    UNIT,
    VAT,
    Allergen,
    AppSettings,
    Article,
    DailyMenu,
    DailyMenuRecipe,
    MealGroup,
    MealType,
    Menu,
    MenuRecipe,
    Recipe,
    RecipeArticle,
    StockIssue,
    StockIssueArticle,
    StockReceipt,
    StockReceiptArticle,
    UnitChangeLog,
    missing_piece_weight_articles,
    sum_nutrition,
)
from .permissions import (
    AnyRoleRequiredMixin,
    CookOrNutritionAdvisorRequiredMixin,
    CookOrStockkeeperRequiredMixin,
    Roles,
    StockkeeperOrNutritionAdvisorRequiredMixin,
    StockkeeperRequiredMixin,
    user_has_any_role,
)
from .tables import (
    ArticleFilter,
    ArticleTable,
    DailyMenuFilter,
    DailyMenuRecipeTable,
    DailyMenuTable,
    MenuRecipeTable,
    MenuTable,
    RecipeArticleTable,
    RecipeFilter,
    RecipeTable,
    StockIssueArticleTable,
    StockIssueFilter,
    StockIssueTable,
    StockReceiptArticleTable,
    StockReceiptFilter,
    StockReceiptTable,
)
from .unit_change import (
    StaleUnitChangeError,
    UnitChangeError,
    apply_article_change,
    apply_recipe_line_change,
    convertible,
    preview_article_change,
    preview_recipe_line_change,
    quantize_factor,
    undo_blocker,
    undo_change,
    unit_factor,
)
from .utils import get_currency, load_changelog

HistoricalArticle = Article.history.model

# Get an instance of a logger
logger = logging.getLogger(__name__)


def create_pdf(self, request, filename, **kwargs):
    context = self.get_context_data(**kwargs)
    html_string = render_to_string(self.template_name, context, request=request)
    pdf_file = HTML(
        string=html_string, base_url=request.build_absolute_uri()
    ).write_pdf()
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response


def about(request):
    latest_entries = load_changelog(latest=True)
    return render(request, "kitchen/about.html", {"latest_entries": latest_entries})


def changelog(request):
    changelog = load_changelog()
    return render(request, "kitchen/changelog.html", {"changelog": changelog})


def policy(request):
    return render(request, "kitchen/policy.html")


def docs(request):
    allergen_count = Allergen.objects.all().count()
    meal_type_count = MealType.objects.all().count()
    meal_group_count = MealGroup.objects.all().count()
    vat_count = VAT.objects.all().count()
    recipe_count = Recipe.objects.all().count()
    recipe_article_count = RecipeArticle.objects.all().count()
    article_count = Article.objects.all().count()
    article_allergen_count = Article.objects.all().aggregate(count=Count("allergen"))[
        "count"
    ]
    historical_article_count = HistoricalArticle.objects.all().count()
    stock_issue_count = StockIssue.objects.all().count()
    stock_receipt_count = StockReceipt.objects.all().count()
    stock_issue_article_count = StockIssueArticle.objects.all().count()
    stock_receipt_article_count = StockReceiptArticle.objects.all().count()
    daily_menu_count = DailyMenu.objects.all().count()
    daily_menu_recipe_count = DailyMenuRecipe.objects.all().count()
    menu_count = Menu.objects.all().count()
    menu_recipe_count = MenuRecipe.objects.all().count()
    unit_change_log_count = UnitChangeLog.objects.all().count()
    app_settings_count = AppSettings.objects.all().count()

    user_count = User.objects.all().count()
    group_count = Group.objects.all().count()

    # service tables content
    content_type_count = ContentType.objects.all().count()
    permission_count = Permission.objects.all().count()
    with connection.cursor() as cursor:
        cursor.execute("select count(*) from django_migrations")
        row = cursor.fetchone()
        migration_count = row[0]

    with connection.cursor() as cursor:
        cursor.execute("select count(*) from django_session")
        row = cursor.fetchone()
        session_count = row[0]

    with connection.cursor() as cursor:
        cursor.execute("select count(*) from django_site")
        row = cursor.fetchone()
        site_count = row[0]

    with connection.cursor() as cursor:
        cursor.execute("select count(*) from users_user_groups")
        row = cursor.fetchone()
        user_group_rel_count = row[0]

    total_records = (
        allergen_count
        + meal_type_count
        + meal_group_count
        + vat_count
        + recipe_count
        + recipe_article_count
        + article_count
        + article_allergen_count
        + historical_article_count
        + stock_issue_count
        + stock_receipt_count
        + stock_issue_article_count
        + stock_receipt_article_count
        + daily_menu_count
        + daily_menu_recipe_count
        + menu_count
        + menu_recipe_count
        + unit_change_log_count
        + app_settings_count
        + user_count
        + group_count
        + content_type_count
        + permission_count
        + migration_count
        + session_count
        + site_count
        + user_group_rel_count
    )

    role_users = {}
    if request.user.is_authenticated:
        role_users = {
            "admin_users": User.objects.filter(is_superuser=True).order_by("username"),
            "nutrition_advisor_users": User.objects.filter(
                groups__name="nutrition_advisor"
            ).order_by("username"),
            "cook_users": User.objects.filter(groups__name="cook").order_by("username"),
            "stockkeeper_users": User.objects.filter(
                groups__name="stockkeeper"
            ).order_by("username"),
        }

    return render(
        request,
        "kitchen/docs.html",
        {
            "allergenCount": allergen_count,
            "meal_typeCount": meal_type_count,
            "mealGroupCount": meal_group_count,
            "vatCount": vat_count,
            "recipeCount": recipe_count,
            "recipe_article_count": recipe_article_count,
            "article_count": article_count,
            "article_allergen_count": article_allergen_count,
            "historical_article_count": historical_article_count,
            "stockIssueCount": stock_issue_count,
            "stockReceiptCount": stock_receipt_count,
            "stock_issue_article_count": stock_issue_article_count,
            "stock_receipt_article_count": stock_receipt_article_count,
            "dailyMenuCount": daily_menu_count,
            "dailyMenuRecipeCount": daily_menu_recipe_count,
            "menu_count": menu_count,
            "menu_recipe_count": menu_recipe_count,
            "unit_change_log_count": unit_change_log_count,
            "app_settings_count": app_settings_count,
            "groupCount": group_count,
            "userCount": user_count,
            "content_type_count": content_type_count,
            "permission_count": permission_count,
            "migration_count": migration_count,
            "session_count": session_count,
            "site_count": site_count,
            "user_group_rel_count": user_group_rel_count,
            "total_records": total_records,
            **role_users,
        },
    )


@login_required
def export_data(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    output = io.StringIO()
    management.call_command(
        "dumpdata", "auth.group", "users.user", "kitchen", stdout=output
    )
    file_name = "data.json"
    response = HttpResponse(output.getvalue(), content_type="application/json")
    response["Content-Disposition"] = f"attachment; filename={file_name}"
    messages.success(request, _("Všechna data byla exportována"))
    return response


class SuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


@method_decorator(transaction.non_atomic_requests, name="dispatch")
class ImportDataView(SuperuserRequiredMixin, TemplateView):
    template_name = "kitchen/import.html"

    def post(self, request):
        context = {}
        if len(request.FILES) == 0:
            messages.error(
                self.request,
                _("Není vybrán vstupní soubor, použij tlačítko Browse a vyber soubor."),
            )
            return super().render_to_response(context)
        uploaded_file = request.FILES["myfile"]
        f = io.StringIO()
        with tempfile.NamedTemporaryFile(suffix=".json") as dump:
            for chunk in uploaded_file.chunks():
                dump.write(chunk)
            dump.flush()
            try:
                with transaction.atomic(), redirect_stdout(f):
                    management.call_command("flush", interactive=False, verbosity=1)
                    management.call_command("loaddata", dump.name, verbosity=1)
                    messages.success(
                        self.request, _("Data úspěšně nahrána: ") + f.getvalue()
                    )
            except Exception as e:
                messages.error(
                    self.request, _("Chyba při výmazu dat před importem: ") + str(e)
                )
        return super().render_to_response(context)


class DataCleanUpView(SuccessMessageMixin, SuperuserRequiredMixin, TemplateView):
    template_name = "kitchen/data_cleanup.html"

    @staticmethod
    def cutoff_year():
        # records from this year and older are deleted
        return timezone.localdate().year - 2

    @staticmethod
    def year_counts(queryset, date_field):
        return (
            queryset.annotate(year=ExtractYear(date_field))
            .values("year")
            .annotate(count=Count("id"))
            .order_by("year")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stockreceipts_year_counts"] = self.year_counts(
            StockReceipt.objects.all(), "date_approved"
        )
        context["stockreceiptarticles_year_counts"] = self.year_counts(
            StockReceiptArticle.objects.all(), "stock_receipt__date_approved"
        )
        context["stockissues_year_counts"] = self.year_counts(
            StockIssue.objects.all(), "date_approved"
        )
        context["stockissuearticles_year_counts"] = self.year_counts(
            StockIssueArticle.objects.all(), "stock_issue__date_approved"
        )
        context["dailymenu_year_counts"] = self.year_counts(
            DailyMenu.objects.all(), "date"
        )
        context["dailymenuarticles_year_counts"] = self.year_counts(
            DailyMenuRecipe.objects.all(), "daily_menu__date"
        )
        context["historicalarticles_year_counts"] = self.year_counts(
            HistoricalArticle.objects.all(), "history_date"
        )
        context["two_years_ago"] = self.cutoff_year()
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        cutoff_year = self.cutoff_year()
        try:
            deleted_historical_articles_count, _deleted = (
                HistoricalArticle.objects.filter(
                    history_date__year__lte=cutoff_year
                ).delete()
            )
            if deleted_historical_articles_count > 0:
                messages.success(
                    self.request,
                    _(
                        "Zboží - historie, úspěšne vymazáno: {deleted_historical_articles_count} záznamů"
                    ).format(
                        deleted_historical_articles_count=deleted_historical_articles_count
                    ),
                )
            # unapproved documents are kept, they may still be approved
            deleted_stock_issues_count, _deleted = StockIssue.objects.filter(
                approved=True, date_approved__year__lte=cutoff_year
            ).delete()
            if deleted_stock_issues_count > 0:
                messages.success(
                    self.request,
                    _(
                        "Výdejky, úspěšne vymazáno: {deleted_stock_issues_count} záznamů"
                    ).format(deleted_stock_issues_count=deleted_stock_issues_count),
                )
            deleted_stock_receipts_count, _deleted = StockReceipt.objects.filter(
                approved=True, date_approved__year__lte=cutoff_year
            ).delete()
            if deleted_stock_receipts_count > 0:
                messages.success(
                    self.request,
                    _(
                        "Příjemky, úspěšne vymazáno: {deleted_stock_receipts_count} záznamů"
                    ).format(deleted_stock_receipts_count=deleted_stock_receipts_count),
                )
            daily_menus_count, _deleted = DailyMenu.objects.filter(
                date__year__lte=cutoff_year
            ).delete()
            if daily_menus_count > 0:
                messages.success(
                    self.request,
                    _(
                        "Denné menu, úspěšne vymazáno: {daily_menus_count} záznamů"
                    ).format(daily_menus_count=daily_menus_count),
                )
        except Exception as e:
            messages.error(
                self.request, _("Chyba při mazání historických záznamů: ") + str(e)
            )
        messages.success(self.request, _("Výmaz dokončen"))
        return super().render_to_response(context)


def switch_language(request):
    if request.method == "POST":
        user_language = request.POST.get("language", translation.get_language())
        translation.activate(user_language)
        request.session[settings.LANGUAGE_COOKIE_NAME] = user_language
        request.session.save()
        referer = request.headers.get("referer", "/")
        parsed_url = urlparse(referer)
        relative_url = urlunparse(
            ("", "", parsed_url.path, parsed_url.params, parsed_url.query, "")
        )
        # Ensure the URL has the correct language prefix
        if user_language == "cs":
            response = redirect(f"{relative_url[3:]}")
        else:
            response = redirect(f"/{user_language}{relative_url}")
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, user_language)
        return response
    else:
        return HttpResponseBadRequest("Invalid request method.")


class ArticleListView(
    SingleTableMixin, StockkeeperOrNutritionAdvisorRequiredMixin, FilterView
):
    model = Article
    table_class = ArticleTable
    template_name = "kitchen/article/list.html"
    filterset_class = ArticleFilter
    form_class = ArticleSearchForm
    paginate_by = settings.PAGINATE_BY

    def get_queryset(self):
        # Prefetch allergens and last receipt price for average_price property
        from .models import StockReceiptArticle

        latest_receipt = Prefetch(
            "stockreceiptarticle_set",
            queryset=StockReceiptArticle.objects.select_related("vat").order_by("-id")[
                :1
            ],
            to_attr="latest_receipt",
        )
        return super().get_queryset().prefetch_related("allergen", latest_receipt)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_stock_price"] = Article.sum_total_price()
        return context


class ArticleLackListView(SingleTableMixin, StockkeeperRequiredMixin, FilterView):
    model = Article
    table_class = ArticleTable
    template_name = "kitchen/article/listlack.html"
    filterset_class = ArticleFilter
    form_class = ArticleSearchForm
    paginate_by = settings.PAGINATE_BY

    def get_queryset(self):
        # show only articles where
        from .models import StockReceiptArticle

        latest_receipt = Prefetch(
            "stockreceiptarticle_set",
            queryset=StockReceiptArticle.objects.select_related("vat").order_by("-id")[
                :1
            ],
            to_attr="latest_receipt",
        )
        return (
            super()
            .get_queryset()
            .prefetch_related("allergen", latest_receipt)
            .filter(on_stock__lt=F("min_on_stock"))
        )


class ArticleCreateView(SuccessMessageMixin, StockkeeperRequiredMixin, CreateView):
    model = Article
    form_class = ArticleForm
    template_name = "kitchen/article/create.html"
    success_message = _(
        "Skladová karta %(article)s byla založeno, je možné zadávat příjemky a recepty"
    )
    success_url = reverse_lazy("kitchen:showArticles")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ArticleUpdateView(
    SuccessMessageMixin, StockkeeperOrNutritionAdvisorRequiredMixin, UpdateView
):
    model = Article
    form_class = ArticleForm
    template_name = "kitchen/article/update.html"
    success_message = _("Skladová karta %(article)s byla aktualizována")
    success_url = reverse_lazy("kitchen:showArticles")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ArticleDeleteView(SuccessMessageMixin, StockkeeperRequiredMixin, DeleteView):
    model = Article
    template_name = "kitchen/article/delete.html"
    success_message = _("Skladová karta byla odstraněna")
    success_url = reverse_lazy("kitchen:showArticles")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        recipe_articles = RecipeArticle.objects.filter(article=obj)
        context["recipe_articles"] = recipe_articles
        context["delete_blockers"] = self.delete_blockers(obj)
        return context

    @staticmethod
    def delete_blockers(article):
        blockers = []
        if article.on_stock or article.total_price:
            blockers.append(
                _(
                    "Zboží je na skladu nebo má nenulovou cenu. "
                    "Nejdříve ho vyskladněte nebo opravte stav skladu."
                )
            )
        receipt_count = (
            StockReceiptArticle.objects.filter(article=article)
            .values("stock_receipt")
            .distinct()
            .count()
        )
        issue_count = (
            StockIssueArticle.objects.filter(article=article)
            .values("stock_issue")
            .distinct()
            .count()
        )
        if receipt_count or issue_count:
            blockers.append(
                _(
                    "Zboží je použité na {receipts} příjemkách a {issues} výdejkách, "
                    "jejich historie by se změnila."
                ).format(receipts=receipt_count, issues=issue_count)
            )
        return blockers

    def form_valid(self, form):
        blockers = self.delete_blockers(self.object)
        if RecipeArticle.objects.filter(article=self.object).exists():
            blockers.append(_("Zboží je použité v receptech."))
        if not blockers:
            try:
                return super().form_valid(form)
            except ProtectedError:
                blockers = self.delete_blockers(self.object)
        for blocker in blockers:
            messages.warning(self.request, blocker)
        return HttpResponseRedirect(
            reverse("kitchen:deleteArticle", args=[self.object.pk])
        )


class ArticlePDFView(StockkeeperOrNutritionAdvisorRequiredMixin, TemplateView):
    template_name = "kitchen/article/pdf.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["articles"] = Article.objects.all().prefetch_related("allergen")
        context["title"] = _("Seznam zboží na skladu")
        context["total_stock_price"] = Article.sum_total_price()
        return context

    def get(self, request, *args, **kwargs):
        response = create_pdf(self, request, _("Seznam_zbozi.pdf"), **kwargs)
        return response


class ArticleExportView(StockkeeperRequiredMixin, View):
    def get(self, *args, **kwargs):
        data = ArticleResource().export()
        filename = _("seznam-zbozi.xlsx")
        response = HttpResponse(
            data.xlsx,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f"attachment; filename={filename}"
        messages.success(self.request, _("Seznam zboží byl exportován"))
        return response


class ArticleImportView(StockkeeperRequiredMixin, TemplateView):
    template_name = "kitchen/article/import.html"

    def post(self, request, **kwargs):
        article_resource = ArticleResource()
        dataset = Dataset()
        context = {}  # set your context
        if len(request.FILES) == 0:
            messages.error(
                self.request,
                _(
                    "Není vybrán vstupní soubor, použij tlačítko Browse a vyber exportovaný a upravený MS Excel soubor."
                ),
            )
            return super().render_to_response(context)
        new_articles = request.FILES["myfile"]
        imported_data = dataset.load(new_articles.read())
        result = article_resource.import_data(
            imported_data, dry_run=True, collect_failed_rows=True
        )  # Test the data import
        if result.has_errors() or result.has_validation_errors():
            messages.error(
                self.request,
                _("Chyba v průběhu importu. Chybná data: {error}").format(
                    error=result.failed_dataset
                ),
            )
        else:
            article_resource.import_data(
                imported_data, dry_run=False
            )  # Actually import now
            messages.success(
                self.request,
                _(
                    "Seznam zboží byl importován. Importováno {} řádků, z toho {} vloženo, \
                {} aktualizováno, {} vymazáno, {} přeskočeno, {} s chybou a {} neplatných řádků"
                ).format(
                    result.total_rows,
                    result.totals["new"],
                    result.totals["update"],
                    result.totals["delete"],
                    result.totals["skip"],
                    result.totals["error"],
                    result.totals["invalid"],
                ),
            )
        return super().render_to_response(context)


class ArticleHistoryDetailView(StockkeeperOrNutritionAdvisorRequiredMixin, DetailView):
    model = Article
    template_name = "kitchen/article/listhistory.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["article_name"] = kwargs["object"].article
        context["table"] = kwargs["object"].history.all()
        context["unit_changes"] = kwargs["object"].unit_changes.select_related(
            "user", "recipe"
        )
        return context


class StockTakePDFView(CookOrStockkeeperRequiredMixin, TemplateView):
    template_name = "kitchen/stocktake/pdf.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["articles"] = Article.objects.all().prefetch_related("allergen")
        context["title"] = _("Seznam zboží na skladu ke kontrole")
        return context

    def get(self, request, *args, **kwargs):
        response = create_pdf(self, request, _("Seznam_zbozi_na_skladu.pdf"), **kwargs)
        return response


class ArticleExportInSelectedDaysFilter(CookOrStockkeeperRequiredMixin, FormView):
    template_name = "kitchen/stocktake/selecteddayfilter.html"
    form_class = StockArticlesExportForm

    # context['total_stock_price'] = Article.sum_total_price()

    def form_valid(self, form):
        selected_date = form.cleaned_data["date"]

        # Build adjustments for stock/issues after the selected date (to roll back to that date)
        issues_after = StockIssueArticle.objects.select_related(
            "article", "stock_issue"
        ).filter(
            stock_issue__approved=True,
            stock_issue__date_approved__gt=selected_date,
        )
        receipts_after = StockReceiptArticle.objects.select_related(
            "article", "stock_receipt"
        ).filter(
            stock_receipt__approved=True,
            stock_receipt__date_approved__gt=selected_date,
        )

        issue_amount_by_article = defaultdict(lambda: Decimal("0"))
        issue_value_by_article = defaultdict(lambda: Decimal("0"))
        skipped_lines = []
        for row in issues_after:
            try:
                converted_amount = convert_units(row.amount, row.unit, row.article.unit)
            except ValidationError:
                skipped_lines.append(row)
                continue
            issue_amount_by_article[row.article_id] += Decimal(converted_amount)
            issue_value_by_article[row.article_id] += Decimal(
                row.total_average_price_with_vat or 0
            )

        receipt_amount_by_article = defaultdict(lambda: Decimal("0"))
        receipt_value_by_article = defaultdict(lambda: Decimal("0"))
        for row in receipts_after:
            try:
                converted_amount = convert_units(row.amount, row.unit, row.article.unit)
            except ValidationError:
                skipped_lines.append(row)
                continue
            receipt_amount_by_article[row.article_id] += Decimal(converted_amount)
            receipt_value_by_article[row.article_id] += Decimal(
                row.total_price_with_vat or 0
            )

        incomplete_articles = defaultdict(list)
        for line in skipped_lines:
            document = (
                line.stock_issue
                if isinstance(line, StockIssueArticle)
                else line.stock_receipt
            )
            incomplete_articles[line.article_id].append(
                f"{type(document).__name__} #{document.pk}, "
                f"{type(line).__name__} #{line.pk}: {line.amount} {line.unit}"
            )

        # Prepare in-memory Article objects with historical values as of selected_date
        articles = list(Article.objects.all())
        for a in articles:
            if a.pk in incomplete_articles:
                a.on_stock = None
                a.total_price = None
                continue
            current_stock = a.on_stock or Decimal("0")
            current_value = a.total_price or Decimal("0")
            a.on_stock = (
                current_stock
                + issue_amount_by_article[a.id]
                - receipt_amount_by_article[a.id]
            )
            a.total_price = (
                current_value
                + issue_value_by_article[a.id]
                - receipt_value_by_article[a.id]
            )

        data = ArticleResource().export(articles)
        if incomplete_articles:
            data.append_col(
                [
                    str(_("Stav nelze určit: "))
                    + "; ".join(incomplete_articles[article.pk])
                    if article.pk in incomplete_articles
                    else ""
                    for article in articles
                ],
                header="export_warning",
            )
        response = HttpResponse(
            data.xlsx,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        filename = _("seznam-zbozi-{selected_date}.xlsx").format(
            selected_date=selected_date
        )
        response["Content-Disposition"] = f"attachment; filename={filename}"
        messages.success(
            self.request,
            _("Seznam zboží na skladu ke dni {selected_date} byl exportován").format(
                selected_date=selected_date
            ),
        )
        if skipped_lines:
            messages.warning(
                self.request,
                format_html(
                    "{}<br/>{}",
                    _(
                        "Následující řádky mají jednotku, kterou nelze převést na "
                        "jednotku skladu, a v exportu nejsou započteny. Opravte je "
                        "(report nesprávných jednotek):"
                    ),
                    format_html_join(
                        mark_safe("<br/>"),
                        "{} - {} {}",
                        (
                            (line.article, line.amount, line.unit)
                            for line in skipped_lines
                        ),
                    ),
                ),
            )
        return response


class RecipeListView(SingleTableMixin, CookOrNutritionAdvisorRequiredMixin, FilterView):
    model = Recipe
    table_class = RecipeTable
    template_name = "kitchen/recipe/list.html"
    filterset_class = RecipeFilter
    form_class = RecipeSearchForm
    paginate_by = settings.PAGINATE_BY

    def get_queryset(self):
        # Prefetch recipe articles with related article, allergens and article's latest receipt
        article_latest_receipt = Prefetch(
            "article__stockreceiptarticle_set",
            queryset=StockReceiptArticle.objects.select_related("vat").order_by("-id")[
                :1
            ],
            to_attr="latest_receipt",
        )
        recipe_articles_prefetch = Prefetch(
            "recipearticle_set",
            queryset=(
                RecipeArticle.objects.select_related("article")
                .prefetch_related("article__allergen", article_latest_receipt)
                .order_by("id")
            ),
            to_attr="prefetched_recipe_articles",
        )
        return super().get_queryset().prefetch_related(recipe_articles_prefetch)


class RecipeCreateView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, CreateView
):
    model = Recipe
    form_class = RecipeForm
    template_name = "kitchen/recipe/create.html"
    success_message = _("Recept %(recipe)s byl vytvořen, přidej ingredience")

    def get_success_url(self):
        return reverse_lazy("kitchen:showRecipeArticles", kwargs={"pk": self.object.id})


class RecipeUpdateView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, UpdateView
):
    model = Recipe
    form_class = RecipeForm
    template_name = "kitchen/recipe/update.html"
    success_message = _("Recept %(recipe)s byl aktualizován")
    success_url = reverse_lazy("kitchen:showRecipes")


class RecipeDeleteView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, DeleteView
):
    model = Recipe
    template_name = "kitchen/recipe/delete.html"
    success_message = _("Recept byl odstraněn")
    success_url = reverse_lazy("kitchen:showRecipes")

    def form_valid(self, form):
        return super().form_valid(form)


class RecipeListPDFView(CookOrNutritionAdvisorRequiredMixin, TemplateView):
    template_name = "kitchen/recipe/pdf_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recipes"] = Recipe.objects.all()
        context["recipes_total"] = Recipe.objects.all().count()
        context["title"] = _("Seznam receptů")
        return context

    def get(self, request, *args, **kwargs):
        response = create_pdf(self, request, _("Seznam_receptu.pdf"), **kwargs)
        return response


class RecipePDFView(CookOrNutritionAdvisorRequiredMixin, TemplateView):
    template_name = "kitchen/recipe/pdf.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recipe = Recipe.objects.filter(pk=self.kwargs["pk"]).get()
        context["recipe"] = recipe
        context["recipe_articles"] = RecipeArticle.objects.select_related(
            "article"
        ).filter(recipe=recipe)
        context["title"] = recipe.recipe
        return context

    def get(self, request, *args, **kwargs):
        response = create_pdf(self, request, "Recept.pdf", **kwargs)
        return response


class RecipeArticleListView(
    SingleTableMixin, CookOrNutritionAdvisorRequiredMixin, FilterView
):
    model = RecipeArticle
    table_class = RecipeArticleTable
    template_name = "kitchen/recipe/listarticles.html"
    paginate_by = settings.PAGINATE_BY

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recipe"] = Recipe.objects.filter(pk=self.kwargs["pk"])[0]
        return context

    def get_table_kwargs(self):
        return {
            "nutrition_per_portion": sum_nutrition(
                recipe_article.nutrition_per_portion
                for recipe_article in self.object_list
            ),
            "total_average_price": sum(
                recipe_article.total_average_price
                for recipe_article in self.object_list
            ),
            "nutrition_missing": missing_piece_weight_articles(self.object_list),
        }

    def get_queryset(self):
        # show only recipe ingredients
        from .models import StockReceiptArticle

        latest_receipt = Prefetch(
            "article__stockreceiptarticle_set",
            queryset=StockReceiptArticle.objects.select_related("vat").order_by("-id")[
                :1
            ],
            to_attr="latest_receipt",
        )
        return (
            super()
            .get_queryset()
            .filter(recipe=self.kwargs["pk"])
            .select_related("article", "recipe")
            .prefetch_related(latest_receipt)
        )


class RecipeArticleCreateView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, CreateView
):
    model = RecipeArticle
    form_class = RecipeArticleForm
    template_name = "kitchen/recipe/createarticle.html"
    success_message = _("Zboží %(article)s bylo přidáno do receptu")

    def get_success_url(self):
        # return reverse_lazy('kitchen:showRecipeCreateArticle', kwargs={'pk': self.kwargs['pk']})
        return reverse_lazy(
            "kitchen:createRecipeArticle", kwargs={"pk": self.kwargs["pk"]}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recipe"] = Recipe.objects.filter(pk=self.kwargs["pk"]).get()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        recipe = context["recipe"]
        recipe_article = form.save(commit=False)
        try:
            convert_units(
                recipe_article.amount, recipe_article.unit, recipe_article.article.unit
            )
        except ValidationError as err:
            messages.warning(self.request, err.message)
            return super().form_invalid(form)
        recipe_article.recipe = Recipe.objects.filter(pk=recipe.id).get()
        recipe_article.save()
        return super().form_valid(form)


class RecipeArticleUpdateView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, UpdateView
):
    model = RecipeArticle
    form_class = RecipeArticleForm
    template_name = "kitchen/recipe/updatearticle.html"
    success_message = _("Zboží %(article)s bylo aktualizováno")

    def get_success_url(self):
        return reverse_lazy(
            "kitchen:showRecipeArticles", kwargs={"pk": self.kwargs["pk"]}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recipe_article_before"] = RecipeArticle.objects.filter(
            pk=self.kwargs["pk"]
        ).get()
        return context

    def form_valid(self, form):
        recipe_article = form.save(commit=False)
        try:
            convert_units(
                recipe_article.amount, recipe_article.unit, recipe_article.article.unit
            )
        except ValidationError as err:
            messages.warning(self.request, err.message)
            return super().form_invalid(form)
        recipe_article.recipe = RecipeArticle.objects.filter(pk=recipe_article.id)[
            0
        ].recipe
        recipe_article.save()
        self.kwargs = {"pk": recipe_article.recipe.id}
        return super().form_valid(form)


class RecipeArticleDeleteView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, DeleteView
):
    model = RecipeArticle
    template_name = "kitchen/recipe/deletearticle.html"
    success_message = _("Zboží bylo odstraněno")
    recipe_id = 0

    def get_success_url(self):
        return reverse_lazy("kitchen:showRecipeArticles", kwargs={"pk": self.recipe_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recipe_article_before"] = RecipeArticle.objects.filter(
            pk=self.kwargs["pk"]
        ).get()
        return context

    def form_valid(self, form):
        recipe_article = get_object_or_404(RecipeArticle, pk=self.kwargs["pk"])
        self.recipe_id = recipe_article.recipe.id
        return super().form_valid(form)


class DailyMenuListView(
    SingleTableMixin, CookOrNutritionAdvisorRequiredMixin, FilterView
):
    model = DailyMenu
    table_class = DailyMenuTable
    template_name = "kitchen/dailymenu/list.html"
    filterset_class = DailyMenuFilter
    paginate_by = settings.PAGINATE_BY

    def get_table_kwargs(self):
        if user_has_any_role(self.request.user, (Roles.NUTRITION_ADVISOR,)):
            return {}
        return {"exclude": ("nutrition",)}

    def get_queryset(self):
        recipe_articles = Prefetch(
            "recipe__recipearticle_set",
            queryset=RecipeArticle.objects.select_related("article").order_by("id"),
            to_attr="prefetched_recipe_articles",
        )
        daily_menu_recipes = Prefetch(
            "dailymenurecipe",
            queryset=(
                DailyMenuRecipe.objects.select_related("recipe")
                .prefetch_related(recipe_articles)
                .order_by("id")
            ),
            to_attr="prefetched_daily_menu_recipes",
        )
        return (
            super()
            .get_queryset()
            .select_related("meal_group", "meal_type")
            .prefetch_related(daily_menu_recipes)
            .annotate(recipe_count=Max("dailymenurecipe__amount"))
        )


class DailyMenuCreateView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, CreateView
):
    model = DailyMenu
    form_class = DailyMenuCreateForm
    template_name = "kitchen/dailymenu/create.html"
    success_message = _(
        "Denní menu pro den %(formatted_date)s bylo vytvořeno, přidej recepty"
    )
    success_message_from_menu = _(
        "Denní menu pro den %(formatted_date)s bylo vytvořeno, "
        "recepty byly převzaty z menu %(menu)s"
    )

    def get_success_message(self, cleaned_data):
        date_obj = self.object.date
        formatted_date = formats.date_format(date_obj, "SHORT_DATE_FORMAT")

        menu = cleaned_data.get("menu")
        if menu:
            return self.success_message_from_menu % {
                "formatted_date": formatted_date,
                "menu": menu,
            }
        return self.success_message % {"formatted_date": formatted_date}

    def get_success_url(self):
        return reverse_lazy("kitchen:createDailyMenuRecipe", args=[self.object.pk])

    def form_valid(self, form):
        response = super().form_valid(form)
        menu = form.cleaned_data.get("menu")
        if menu:
            # name the source menu so a wrongly picked menu is visible in the recipe list
            comment = _("Recept byl převzatý z menu %(menu)s") % {"menu": menu}
            for menu_recipe in MenuRecipe.objects.filter(menu=menu):
                DailyMenuRecipe.objects.create(
                    daily_menu=self.object,
                    recipe=menu_recipe.recipe,
                    amount=menu_recipe.amount,
                    comment=comment[:200],
                )
        return response


class DailyMenuUpdateView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, UpdateView
):
    model = DailyMenu
    form_class = DailyMenuEditForm
    template_name = "kitchen/dailymenu/update.html"
    success_message = _(
        "Denní menu pro den %(formatted_date)s bylo aktualizováno včetně výdejky ke schválení"
    )
    success_url = reverse_lazy("kitchen:showDailyMenus")

    def get_success_message(self, cleaned_data):
        date_obj = self.object.date
        formatted_date = formats.date_format(date_obj, "SHORT_DATE_FORMAT")

        return self.success_message % {"formatted_date": formatted_date}


class DailyMenuDeleteView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, DeleteView
):
    model = DailyMenu
    template_name = "kitchen/dailymenu/delete.html"
    success_message = "Denní menu bylo odstraněno"
    success_url = reverse_lazy("kitchen:showDailyMenus")

    def form_valid(self, form):
        return super().form_valid(form)


class DailyMenuPDFView(CookOrNutritionAdvisorRequiredMixin, TemplateView):
    template_name = "kitchen/dailymenu/pdf.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        date = self.request.GET["date"]
        meal_group = self.request.GET["meal_group"]
        if len(meal_group) == 0:
            daily_menu_recipes = DailyMenuRecipe.objects.filter(
                daily_menu__date=datetime.strptime(date, "%Y-%m-%d")
            )
        else:
            daily_menu_recipes = DailyMenuRecipe.objects.filter(
                daily_menu__date=datetime.strptime(date, "%Y-%m-%d"),
                daily_menu__meal_group=meal_group,
            )
            context["meal_group_filter"] = (
                _("Filtrováno pro skupinu strávníků: ")
                + MealGroup.objects.filter(pk=meal_group).get().meal_group
            )
        context["title"] = _("Denní menu pro ") + date
        context["daily_menu_recipes"] = daily_menu_recipes
        return context

    def get(self, request, *args, **kwargs):
        try:
            date = request.GET["date"]
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError as e:
            messages.warning(
                self.request,
                _(
                    "Chybně zadané datum. Požadovaný formát je rrrr-mm-dd. Chyba: {error}"
                ).format(error=e),
            )
            return HttpResponseRedirect(reverse_lazy("kitchen:filterPrintDailyMenu"))
        response = create_pdf(self, request, _("Denni_menu.pdf"), **kwargs)
        return response


class DailyMenuPrintView(CookOrNutritionAdvisorRequiredMixin, CreateView):
    model = DailyMenu
    form_class = DailyMenuPrintForm
    template_name = "kitchen/dailymenu/print.html"


class MenuListView(SingleTableMixin, CookOrNutritionAdvisorRequiredMixin, FilterView):
    model = Menu
    table_class = MenuTable
    template_name = "kitchen/menu/list.html"
    paginate_by = settings.PAGINATE_BY

    def get_queryset(self):
        # Annotate recipe_count to avoid per-row COUNT queries in property access
        return (
            super()
            .get_queryset()
            .annotate(rc=Count("menurecipe"))
            .order_by("menu", "id")  # ensure deterministic ordering for pagination
        )


class MenuCreateView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, CreateView
):
    model = Menu
    form_class = MenuForm
    template_name = "kitchen/menu/create.html"
    success_message = _("Menu bylo vytvořeno, přidej recepty")

    def get_initial(self):
        initial = super().get_initial()
        latest_menu = (
            Menu.objects.order_by("-created", "-pk")
            .values_list("menu", flat=True)
            .first()
        )
        if latest_menu is not None:
            initial["menu"] = latest_menu
        return initial

    def get_success_url(self):
        return reverse_lazy("kitchen:showMenuRecipes", kwargs={"pk": self.object.id})


class MenuUpdateView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, UpdateView
):
    model = Menu
    form_class = MenuForm
    template_name = "kitchen/menu/update.html"
    success_message = _("Menu bylo aktualizováno")
    success_url = reverse_lazy("kitchen:showMenus")


class MenuDeleteView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, DeleteView
):
    model = Menu
    template_name = "kitchen/menu/delete.html"
    success_message = _("Menu bylo odstraněno")
    success_url = reverse_lazy("kitchen:showMenus")

    def form_valid(self, form):
        return super().form_valid(form)


class MenuRecipeListView(
    SingleTableMixin, CookOrNutritionAdvisorRequiredMixin, FilterView
):
    model = MenuRecipe
    table_class = MenuRecipeTable
    template_name = "kitchen/menu/listrecipe.html"
    paginate_by = settings.PAGINATE_BY

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["menu"] = Menu.objects.filter(pk=self.kwargs["pk"])[0]
        return context

    def get_queryset(self):
        # show only DailyMeny recipes
        return super().get_queryset().filter(menu=self.kwargs["pk"])


class MenuRecipeCreateView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, CreateView
):
    model = MenuRecipe
    form_class = MenuRecipeForm
    template_name = "kitchen/menu/createrecipe.html"
    success_message = _("Recept %(recipe)s byl přidán")

    def get_success_url(self):
        return reverse_lazy(
            "kitchen:showMenuRecipes", kwargs={"pk": self.object.menu.id}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["menu"] = Menu.objects.filter(pk=self.kwargs["pk"]).get()
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = MenuRecipe(menu_id=self.kwargs["pk"])
        return kwargs


class MenuRecipeUpdateView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, UpdateView
):
    model = MenuRecipe
    form_class = MenuRecipeForm
    template_name = "kitchen/menu/updaterecipe.html"
    success_message = _("Recept %(recipe)s byl aktualizován")

    def get_success_url(self):
        return reverse_lazy("kitchen:showMenuRecipes", kwargs={"pk": self.kwargs["pk"]})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["menurecipe_before"] = MenuRecipe.objects.filter(pk=self.kwargs["pk"])[
            0
        ]
        return context

    def form_valid(self, form):
        menu_recipe = form.save(commit=False)
        menu_recipe.menu = MenuRecipe.objects.filter(pk=menu_recipe.id)[0].menu
        menu_recipe.save()
        self.kwargs = {"pk": menu_recipe.menu.id}
        return super().form_valid(form)


class MenuRecipeDeleteView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, DeleteView
):
    model = MenuRecipe
    template_name = "kitchen/menu/deleterecipe.html"
    success_message = _("Recept byl z menu odstraněn")
    daily_menu_id = 0

    def get_success_url(self):
        return reverse_lazy("kitchen:showMenuRecipes", kwargs={"pk": self.menu_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["menurecipe_before"] = MenuRecipe.objects.filter(
            pk=self.kwargs["pk"]
        ).get()
        return context

    def form_valid(self, form):
        recipe = get_object_or_404(MenuRecipe, pk=self.kwargs["pk"])
        self.menu_id = recipe.menu.id
        return super().form_valid(form)


class DailyMenuRecipeListView(
    SingleTableMixin, CookOrNutritionAdvisorRequiredMixin, FilterView
):
    model = DailyMenuRecipe
    table_class = DailyMenuRecipeTable
    template_name = "kitchen/dailymenu/listrecipe.html"
    paginate_by = settings.PAGINATE_BY

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dailymenu"] = DailyMenu.objects.filter(pk=self.kwargs["pk"])[0]
        return context

    def get_table_kwargs(self):
        if not user_has_any_role(self.request.user, (Roles.NUTRITION_ADVISOR,)):
            return {"exclude": ("nutrition",)}
        return {
            "nutrition_per_portion": sum_nutrition(
                record.nutrition_per_portion for record in self.object_list
            ),
            "nutrition_missing": sorted(
                {
                    name
                    for record in self.object_list
                    for name in record.nutrition_missing_articles
                },
                key=str.lower,
            ),
        }

    def get_queryset(self):
        recipe_articles = Prefetch(
            "recipe__recipearticle_set",
            queryset=RecipeArticle.objects.select_related("article").order_by("id"),
            to_attr="prefetched_recipe_articles",
        )
        return (
            super()
            .get_queryset()
            .filter(daily_menu=self.kwargs["pk"])
            .select_related("recipe")
            .prefetch_related(recipe_articles)
        )


class DailyMenuRecipeCreateView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, CreateView
):
    model = DailyMenuRecipe
    form_class = DailyMenuRecipeForm
    template_name = "kitchen/dailymenu/createrecipe.html"
    success_message = _("Recept %(recipe)s byl vytvořen")

    def get_success_url(self):
        return reverse_lazy(
            "kitchen:showDailyMenuRecipes", kwargs={"pk": self.kwargs["pk"]}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["daily_menu"] = DailyMenu.objects.filter(pk=self.kwargs["pk"]).get()
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = DailyMenuRecipe(daily_menu_id=self.kwargs["pk"])
        return kwargs


class DailyMenuRecipeUpdateView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, UpdateView
):
    model = DailyMenuRecipe
    form_class = DailyMenuRecipeForm
    template_name = "kitchen/dailymenu/updaterecipe.html"
    success_message = _("Recept %(recipe)s byl aktualizován")

    def get_success_url(self):
        return reverse_lazy(
            "kitchen:showDailyMenuRecipes", kwargs={"pk": self.kwargs["pk"]}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dailymenurecipe_before"] = DailyMenuRecipe.objects.filter(
            pk=self.kwargs["pk"]
        )[0]
        return context

    def form_valid(self, form):
        daily_menu_recipe = form.save(commit=False)
        daily_menu_recipe.daily_menu = DailyMenuRecipe.objects.filter(
            pk=daily_menu_recipe.id
        )[0].daily_menu
        daily_menu_recipe.save()
        self.kwargs = {"pk": daily_menu_recipe.daily_menu.id}
        return super().form_valid(form)


class DailyMenuRecipeDeleteView(
    SuccessMessageMixin, CookOrNutritionAdvisorRequiredMixin, DeleteView
):
    model = DailyMenuRecipe
    template_name = "kitchen/dailymenu/deleterecipe.html"
    success_message = _("Recept byl odstraněn")
    daily_menu_id = 0

    def get_success_url(self):
        return reverse_lazy(
            "kitchen:showDailyMenuRecipes", kwargs={"pk": self.daily_menu_id}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dailymenurecipe_before"] = DailyMenuRecipe.objects.filter(
            pk=self.kwargs["pk"]
        ).get()
        return context

    def form_valid(self, form):
        recipe = get_object_or_404(DailyMenuRecipe, pk=self.kwargs["pk"])
        self.daily_menu_id = recipe.daily_menu.id
        return super().form_valid(form)


class StockIssueListView(SingleTableMixin, CookOrStockkeeperRequiredMixin, FilterView):
    model = StockIssue
    table_class = StockIssueTable
    template_name = "kitchen/stockissue/list.html"
    filterset_class = StockIssueFilter
    form_class = StockIssueSearchForm
    paginate_by = settings.PAGINATE_BY

    def get_queryset(self):
        return super().get_queryset().select_related("user_created", "user_approved")


class StockIssueCreateView(
    SuccessMessageMixin, CookOrStockkeeperRequiredMixin, CreateView
):
    model = StockIssue
    form_class = StockIssueForm
    template_name = "kitchen/stockissue/create.html"
    success_message = _("Výdejka byla vytvořena a je možné přidávat zboží")

    def form_valid(self, form):
        form.instance.user_created = self.request.user
        self.object = form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "kitchen:createStockIssueArticle", kwargs={"pk": self.object.id}
        )


class StockIssueFromDailyMenuCreateView(
    SuccessMessageMixin, CookOrStockkeeperRequiredMixin, CreateView
):
    model = StockIssue
    form_class = StockIssueFromDailyMenuForm
    template_name = "kitchen/stockissue/create_from_daily_menu.html"
    success_url = reverse_lazy("kitchen:showStockIssues")

    # do not save form which contains DailyMenu but save StockIssue on that date
    def form_valid(self, form):
        date_str = self.request.POST["date"]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        formatted_date = formats.date_format(date_obj, "SHORT_DATE_FORMAT")
        daily_menus = DailyMenu.objects.filter(date=date_obj)
        if len(daily_menus) < 1:
            form.add_error("date", _("Pro zadané datum není vytvořeno denní menu"))
            return super().form_invalid(form)
        try:
            count = StockIssue.create_from_daily_menu(
                daily_menus, formatted_date, self.request.user, menu_date=date_obj
            )
        except ValidationError as error:
            messages.error(
                self.request,
                format_html(
                    _(
                        "Výdejku nelze vytvořit: {error}. Zkontrolujte "
                        '<a href="{report_url}">report nesprávných jednotek</a> a '
                        "kontaktujte uživatele ve skupině Skladník nebo Výživový "
                        "poradce, aby opravil jednotky na skladu nebo v receptu."
                    ),
                    error="; ".join(error.messages),
                    report_url=reverse("kitchen:showIncorrectUnits"),
                ),
            )
            return super().form_invalid(form)
        messages.success(
            self.request,
            _(
                "Výdejka pro den {formatted_date} vytvořena a vyskladňuje {count} druhů zboží"
            ).format(formatted_date=formatted_date, count=count),
        )
        return HttpResponseRedirect(self.success_url)


class StockIssueUpdateView(
    SuccessMessageMixin, CookOrStockkeeperRequiredMixin, UpdateView
):
    model = StockIssue
    form_class = StockIssueForm
    template_name = "kitchen/stockissue/update.html"
    success_message = _("Poznámka výdejky byla aktualizována")
    success_url = reverse_lazy("kitchen:showStockIssues")


class StockIssueRefreshView(CookOrStockkeeperRequiredMixin, View):
    model = StockIssue
    http_method_names = ["post"]
    # "Pro <date>" comments written before menu_date existed, in cs and en
    comment_prefixes = ("Pro ", "For ")
    comment_date_formats = ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y")

    @classmethod
    def menu_date_from_comment(cls, comment):
        for prefix in cls.comment_prefixes:
            if comment.startswith(prefix):
                value = comment[len(prefix) :].strip()
                for date_format in cls.comment_date_formats:
                    try:
                        return datetime.strptime(value, date_format).date()
                    except ValueError:
                        continue
        return None

    def post(self, *args, **kwargs):
        redirect_url = reverse_lazy("kitchen:showStockIssues")
        stock_issue = get_object_or_404(StockIssue, pk=kwargs["pk"])
        if stock_issue.approved:
            messages.warning(
                self.request, _("Aktualizace neprovedena - výdejka je již vyskladněna")
            )
            return HttpResponseRedirect(redirect_url)
        menu_date = stock_issue.menu_date or self.menu_date_from_comment(
            stock_issue.comment
        )
        if menu_date is None:
            messages.warning(
                self.request,
                _(
                    "Aktualizace zboží je možná jenom pro výdejku vytvořenou z denního menu"
                ),
            )
            return HttpResponseRedirect(redirect_url)
        daily_menus = DailyMenu.objects.filter(date=menu_date)
        if not daily_menus.exists():
            messages.error(
                self.request, _("Pro zadané datum není vytvořeno denní menu")
            )
            return HttpResponseRedirect(redirect_url)
        formatted_date = formats.date_format(menu_date, "SHORT_DATE_FORMAT")
        try:
            with transaction.atomic():
                user_created = stock_issue.user_created
                stock_issue.delete()
                count = StockIssue.create_from_daily_menu(
                    daily_menus, formatted_date, user_created, menu_date=menu_date
                )
        except ValidationError as error:
            messages.error(
                self.request,
                format_html(
                    _(
                        "Výdejku nelze vytvořit: {error}. Zkontrolujte "
                        '<a href="{report_url}">report nesprávných jednotek</a> a '
                        "kontaktujte uživatele ve skupině Skladník nebo Výživový "
                        "poradce, aby opravil jednotky na skladu nebo v receptu."
                    ),
                    error="; ".join(error.messages),
                    report_url=reverse("kitchen:showIncorrectUnits"),
                ),
            )
            return HttpResponseRedirect(redirect_url)
        messages.success(
            self.request,
            _(
                "Seznam zboží na výdejce byl aktualizován dle aktuálních receptů na denním menu a vyskladňuje {count} druhů zboží"  # noqa: E501
            ).format(count=count),
        )
        return HttpResponseRedirect(redirect_url)


class StockIssueDeleteView(
    SuccessMessageMixin, CookOrStockkeeperRequiredMixin, DeleteView
):
    model = StockIssue
    template_name = "kitchen/stockissue/delete.html"
    success_message = _("Výdejka byla odstraněna")
    success_url = reverse_lazy("kitchen:showStockIssues")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stock_issue = StockIssue.objects.filter(pk=self.kwargs["pk"]).get()
        stock_issue_articles = StockIssueArticle.objects.filter(
            stock_issue_id=self.kwargs["pk"]
        )
        context["stock_issue"] = stock_issue
        context["stock_issue_articles"] = stock_issue_articles
        context["total_price"] = stock_issue.total_price
        return context

    def post(self, request, *args, **kwargs):
        stock_issue = StockIssue.objects.filter(pk=self.kwargs["pk"]).get()
        if stock_issue.approved:
            messages.warning(
                self.request, _("Výmaz neproveden - výdejka je již vyskladněna")
            )
            return HttpResponseRedirect(
                reverse_lazy(
                    "kitchen:showStockIssues",
                )
            )
        return super().post(request, *args, **kwargs)


class StockIssuePDFView(CookOrStockkeeperRequiredMixin, TemplateView):
    template_name = "kitchen/stockissue/pdf.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stock_issue = StockIssue.objects.filter(pk=self.kwargs["pk"]).get()
        stock_issue_articles = (
            StockIssueArticle.objects.filter(stock_issue_id=self.kwargs["pk"])
            .select_related("article")
            .order_by(Lower("article__article"))
        )
        context["stock_issue"] = stock_issue
        context["stock_issue_articles"] = stock_issue_articles
        context["title"] = "Výdejka"
        context["total_price"] = stock_issue.total_price
        return context

    def get(self, request, *args, **kwargs):
        response = create_pdf(self, request, _("Výdejka.pdf"), **kwargs)
        return response


class StockIssueApproveView(StockkeeperRequiredMixin, TemplateView):
    model = StockIssue
    template_name = "kitchen/stockissue/approve.html"
    fields = "__all__"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stock_issue = StockIssue.objects.filter(pk=self.kwargs["pk"]).get()
        stock_issue_articles = StockIssueArticle.objects.filter(
            stock_issue_id=self.kwargs["pk"]
        )
        context["stock_issue"] = stock_issue
        context["stock_issue_articles"] = stock_issue_articles
        context["total_price"] = stock_issue.total_price
        return context

    def post(self, *args, **kwargs):
        stock_issue = StockIssue.objects.filter(pk=self.kwargs["pk"]).get()
        if stock_issue.approved:
            messages.warning(
                self.request, _("Vyskladnění neprovedeno - již bylo vyskladněno")
            )
            return HttpResponseRedirect(
                reverse_lazy(
                    "kitchen:showStockIssues",
                )
            )
        with transaction.atomic():
            StockIssue.update_stock_issue_article_average_unit_price(stock_issue.id)
            total_price = stock_issue.total_price
            if total_price is None:
                messages.error(
                    self.request,
                    _(
                        "Vyskladnění neprovedeno - jednotku některého zboží nelze převést "
                        "na jednotku skladu, viz report nesprávných jednotek"
                    ),
                )
                transaction.set_rollback(True)
                return HttpResponseRedirect(reverse_lazy("kitchen:showStockIssues"))
            if total_price <= 0:
                messages.warning(
                    self.request,
                    _(
                        "Vyskladnění neprovedeno - nulová cena zboží, je zboží naskladněno?"
                    ),
                )
                transaction.set_rollback(True)
                return HttpResponseRedirect(reverse_lazy("kitchen:showStockIssues"))
            errors = StockIssue.update_article_on_stock(
                stock_issue.id, stock_issue.comment, True
            )
            if errors:
                messages.error(
                    self.request,
                    format_html(
                        "{}<br/>{}",
                        _("Níže uvedené zboží není možné vyskladnit:"),
                        format_html_join(
                            mark_safe("<br/>"), "{}", ((e,) for e in errors)
                        ),
                    ),
                )
                transaction.set_rollback(True)
                return HttpResponseRedirect(
                    reverse_lazy(
                        "kitchen:approveStockIssue", kwargs={"pk": self.kwargs["pk"]}
                    )
                )
            StockIssue.update_article_on_stock(
                stock_issue.id, stock_issue.comment, False
            )
            stock_issue.approved = True
            stock_issue.date_approved = timezone.localdate()
            stock_issue.user_approved = self.request.user
            stock_issue.save(
                update_fields=(
                    "approved",
                    "date_approved",
                    "user_approved",
                )
            )
            messages.success(self.request, _("Výdejka byla vyskladněna"))
            return HttpResponseRedirect(
                reverse_lazy(
                    "kitchen:showStockIssues",
                )
            )


class StockIssueArticleListView(
    SingleTableMixin, CookOrStockkeeperRequiredMixin, FilterView
):
    model = StockIssueArticle
    table_class = StockIssueArticleTable
    template_name = "kitchen/stockissue/listarticles.html"
    table_pagination = False
    paginate_by = settings.PAGINATE_BY

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stockissue"] = StockIssue.objects.filter(pk=self.kwargs["pk"]).get()
        return context

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(stock_issue=self.kwargs["pk"])
            .select_related("article")
        )


class StockIssueArticleCreateView(
    SuccessMessageMixin, CookOrStockkeeperRequiredMixin, CreateView
):
    model = StockIssueArticle
    form_class = StockIssueArticleForm
    template_name = "kitchen/stockissue/createarticle.html"
    success_message = _("Zboží %(article)s bylo přidáno")

    def get_success_url(self):
        return reverse_lazy(
            "kitchen:showStockIssueArticles", kwargs={"pk": self.kwargs["pk"]}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stockissue"] = StockIssue.objects.filter(pk=self.kwargs["pk"]).get()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        stock_issue = context["stockissue"]
        stock_issue_article = form.save(commit=False)
        try:
            convert_units(
                stock_issue_article.amount,
                stock_issue_article.unit,
                stock_issue_article.article.unit,
            )
        except ValidationError as err:
            messages.warning(self.request, err.message)
            return super().form_invalid(form)
        stock_issue_article.stock_issue = StockIssue.objects.filter(
            pk=stock_issue.id
        ).get()
        if stock_issue_article.stock_issue.approved:
            messages.warning(
                self.request, _("Přidání zboží neprovedeno, výdejka je již vyskladněna")
            )
            return HttpResponseRedirect(
                reverse_lazy(
                    "kitchen:showStockIssueArticles", kwargs={"pk": stock_issue.id}
                )
            )
        stock_issue_article.average_unit_price = (
            stock_issue_article.article.average_price
        )
        stock_issue_article.save()
        return super().form_valid(form)


class StockIssueArticleUpdateView(
    SuccessMessageMixin, CookOrStockkeeperRequiredMixin, UpdateView
):
    model = StockIssueArticle
    form_class = StockIssueArticleForm
    template_name = "kitchen/stockissue/updatearticle.html"
    success_message = _("Zboží %(article)s bylo aktualizováno")

    def get_success_url(self):
        return reverse_lazy(
            "kitchen:showStockIssueArticles", kwargs={"pk": self.kwargs["pk"]}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stock_issue_article_before"] = StockIssueArticle.objects.filter(
            pk=self.kwargs["pk"]
        ).get()
        return context

    def form_valid(self, form):
        stock_issue_article = form.save(commit=False)
        try:
            convert_units(
                stock_issue_article.amount,
                stock_issue_article.unit,
                stock_issue_article.article.unit,
            )
        except ValidationError as err:
            messages.warning(self.request, err.message)
            return super().form_invalid(form)
        stock_issue_article.stock_issue = (
            StockIssueArticle.objects.filter(pk=stock_issue_article.id)
            .get()
            .stock_issue
        )
        if stock_issue_article.stock_issue.approved:
            messages.warning(
                self.request,
                _("Aktualizace zboží neprovedena, výdejka je již vyskladněna"),
            )
            return HttpResponseRedirect(
                reverse_lazy(
                    "kitchen:showStockIssueArticles",
                    kwargs={"pk": stock_issue_article.stock_issue.id},
                )
            )
        stock_issue_article.average_unit_price = (
            stock_issue_article.article.average_price
        )
        stock_issue_article.save()
        self.kwargs = {"pk": stock_issue_article.stock_issue.id}
        return super().form_valid(form)


class StockIssueArticleDeleteView(
    SuccessMessageMixin, CookOrStockkeeperRequiredMixin, DeleteView
):
    model = StockIssueArticle
    template_name = "kitchen/stockissue/deletearticle.html"
    success_message = _("Zboží bylo odstraněno")
    success_url = reverse_lazy("kitchen:showStockIssues")
    stock_issue_id = 0

    def get_success_url(self):
        return reverse_lazy(
            "kitchen:showStockIssueArticles", kwargs={"pk": self.stock_issue_id}
        )

    def form_valid(self, form):
        stock_issue_article = get_object_or_404(StockIssueArticle, pk=self.kwargs["pk"])
        if stock_issue_article.stock_issue.approved:
            messages.warning(
                self.request,
                _("Odstranění zboží neprovedeno, výdejka je již vyskladněna"),
            )
            return HttpResponseRedirect(
                reverse_lazy(
                    "kitchen:showStockIssueArticles",
                    kwargs={"pk": stock_issue_article.stock_issue.id},
                )
            )
        self.stock_issue_id = stock_issue_article.stock_issue.id
        return super().form_valid(form)


class StockReceiptListView(SingleTableMixin, StockkeeperRequiredMixin, FilterView):
    model = StockReceipt
    table_class = StockReceiptTable
    template_name = "kitchen/stockreceipt/list.html"
    filterset_class = StockReceiptFilter
    form_class = StockReceiptSearchForm
    paginate_by = settings.PAGINATE_BY

    def get_queryset(self):
        return super().get_queryset().select_related("user_created", "user_approved")


class StockReceiptCreateView(SuccessMessageMixin, StockkeeperRequiredMixin, CreateView):
    model = StockReceipt
    form_class = StockReceiptForm
    template_name = "kitchen/stockreceipt/create.html"
    success_message = _("Příjemka byla vytvořena a je možné přidávat zboží")

    def form_valid(self, form):
        form.instance.user_created = self.request.user
        self.object = form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "kitchen:createStockReceiptArticle", kwargs={"pk": self.object.id}
        )


class StockReceiptUpdateView(SuccessMessageMixin, StockkeeperRequiredMixin, UpdateView):
    model = StockReceipt
    form_class = StockReceiptForm
    template_name = "kitchen/stockreceipt/update.html"
    success_message = _("Poznámka příjemky byla aktualizována")
    success_url = reverse_lazy("kitchen:showStockReceipts")


class StockReceiptDeleteView(SuccessMessageMixin, StockkeeperRequiredMixin, DeleteView):
    model = StockReceipt
    template_name = "kitchen/stockreceipt/delete.html"
    success_message = _("Příjemka byla odstraněna")
    success_url = reverse_lazy("kitchen:showStockReceipts")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stock_receipt = StockReceipt.objects.filter(pk=self.kwargs["pk"]).get()
        stock_receipt_articles = StockReceiptArticle.objects.filter(
            stock_receipt_id=self.kwargs["pk"]
        )
        context["stock_receipt"] = stock_receipt
        context["stock_receipt_articles"] = stock_receipt_articles
        context["total_price"] = stock_receipt.total_price
        return context

    def post(self, request, *args, **kwargs):
        stock_receipt = StockReceipt.objects.filter(pk=self.kwargs["pk"]).get()
        if stock_receipt.approved:
            messages.warning(
                self.request, _("Výmaz neproveden - příjemka je již naskladněna")
            )
            return HttpResponseRedirect(
                reverse_lazy(
                    "kitchen:showStockReceipts",
                )
            )
        return super().post(request, *args, **kwargs)


class StockReceiptPDFView(StockkeeperRequiredMixin, TemplateView):
    template_name = "kitchen/stockreceipt/pdf.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stock_receipt = StockReceipt.objects.filter(pk=self.kwargs["pk"]).get()
        stock_receipt_articles = StockReceiptArticle.objects.filter(
            stock_receipt_id=self.kwargs["pk"]
        )
        context["stock_receipt"] = stock_receipt
        context["stock_receipt_articles"] = stock_receipt_articles
        context["title"] = "Příjemka"
        context["total_price"] = stock_receipt.total_price
        return context

    def get(self, request, *args, **kwargs):
        response = create_pdf(self, request, _("Prijemka.pdf"), **kwargs)
        return response


class StockReceiptApproveView(StockkeeperRequiredMixin, TemplateView):
    model = StockReceipt
    template_name = "kitchen/stockreceipt/approve.html"
    fields = "__all__"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stock_receipt = StockReceipt.objects.filter(pk=self.kwargs["pk"]).get()
        stock_receipt_articles = StockReceiptArticle.objects.filter(
            stock_receipt_id=self.kwargs["pk"]
        )
        context["stock_receipt"] = stock_receipt
        context["stock_receipt_articles"] = stock_receipt_articles
        context["total_price"] = stock_receipt.total_price
        return context

    def post(self, *args, **kwargs):
        stock_receipt = StockReceipt.objects.filter(pk=self.kwargs["pk"]).get()
        if stock_receipt.approved:
            messages.warning(
                self.request, _("Naskladnění neprovedeno - již bylo naskladněno")
            )
            return HttpResponseRedirect(
                reverse_lazy(
                    "kitchen:showStockReceipts",
                )
            )
        total_price = stock_receipt.total_price
        if total_price is None:
            messages.error(
                self.request,
                _(
                    "Naskladnění neprovedeno - jednotku některého zboží nelze převést "
                    "na jednotku skladu, viz report nesprávných jednotek"
                ),
            )
            return HttpResponseRedirect(reverse_lazy("kitchen:showStockReceipts"))
        if total_price <= 0:
            messages.warning(
                self.request,
                _(
                    "Naskladnění neprovedeno - nulová cena zboží, přidejte alespoň jedno zboží na příjemku"
                ),
            )
            return HttpResponseRedirect(
                reverse_lazy(
                    "kitchen:showStockReceipts",
                )
            )
        with transaction.atomic():
            stock_receipt.approved = True
            stock_receipt.date_approved = timezone.localdate()
            stock_receipt.user_approved = self.request.user
            StockReceipt.update_article_on_stock(
                stock_receipt.id, stock_receipt.comment
            )
            stock_receipt.save(
                update_fields=(
                    "approved",
                    "date_approved",
                    "user_approved",
                )
            )
            messages.success(self.request, _("Příjemka byla naskladněna"))
        return HttpResponseRedirect(
            reverse_lazy(
                "kitchen:showStockReceipts",
            )
        )


class StockReceiptArticleListView(
    SingleTableMixin, StockkeeperRequiredMixin, FilterView
):
    model = StockReceiptArticle
    table_class = StockReceiptArticleTable
    template_name = "kitchen/stockreceipt/listarticles.html"
    table_pagination = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stockreceipt"] = StockReceipt.objects.filter(
            pk=self.kwargs["pk"]
        ).get()
        return context

    def get_queryset(self):
        # show only StockReceiptArticles
        return (
            super()
            .get_queryset()
            .filter(stock_receipt=self.kwargs["pk"])
            .select_related("article", "vat")
        )


class StockReceiptArticleCreateView(
    SuccessMessageMixin, StockkeeperRequiredMixin, CreateView
):
    model = StockReceiptArticle
    form_class = StockReceiptArticleForm
    template_name = "kitchen/stockreceipt/createarticle.html"
    success_message = _(
        "Zboží %(article)s bylo přidáno: %(amount)s %(unit)s * %(unit_price)s %(currency)s = %(total_price)s %(currency)s"  # noqa: E501
    )

    def get_success_url(self):
        return reverse_lazy(
            "kitchen:createStockReceiptArticle", kwargs={"pk": self.kwargs["pk"]}
        )

    def get_success_message(self, cleaned_data):
        return self.success_message % dict(
            cleaned_data,
            unit_price=format_unit_price(self.object.price_with_vat),
            total_price=self.object.total_price_with_vat,
            currency=get_currency(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stockreceipt"] = StockReceipt.objects.filter(pk=self.kwargs["pk"])[0]
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        stock_receipt = context["stockreceipt"]
        stock_receipt_article = form.save(commit=False)
        try:
            convert_units(
                stock_receipt_article.amount,
                stock_receipt_article.unit,
                stock_receipt_article.article.unit,
            )
        except ValidationError as err:
            messages.warning(self.request, err.message)
            return super().form_invalid(form)
        stock_receipt_article.stock_receipt = StockReceipt.objects.filter(
            pk=stock_receipt.id
        ).get()
        if stock_receipt_article.stock_receipt.approved:
            messages.warning(
                self.request,
                _("Přidání zboží neprovedeno, příjemka je již naskladněna"),
            )
            return HttpResponseRedirect(
                reverse_lazy(
                    "kitchen:showStockReceiptArticles", kwargs={"pk": stock_receipt.id}
                )
            )
        stock_receipt_article.save()
        return super().form_valid(form)


class StockReceiptArticleUpdateView(
    SuccessMessageMixin, StockkeeperRequiredMixin, UpdateView
):
    model = StockReceiptArticle
    form_class = StockReceiptArticleForm
    template_name = "kitchen/stockreceipt/updatearticle.html"
    success_message = _("Zboží %(article)s bylo aktualizováno")

    def get_success_url(self):
        return reverse_lazy(
            "kitchen:showStockReceiptArticles", kwargs={"pk": self.kwargs["pk"]}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stock_receipt_article_before"] = StockReceiptArticle.objects.filter(
            pk=self.kwargs["pk"]
        ).get()
        return context

    def form_valid(self, form):
        stock_receipt_article = form.save(commit=False)
        try:
            convert_units(
                stock_receipt_article.amount,
                stock_receipt_article.unit,
                stock_receipt_article.article.unit,
            )
        except ValidationError as err:
            messages.warning(self.request, err.message)
            return super().form_invalid(form)
        stock_receipt_article.stock_receipt = (
            StockReceiptArticle.objects.filter(pk=stock_receipt_article.id)
            .get()
            .stock_receipt
        )
        if stock_receipt_article.stock_receipt.approved:
            messages.warning(
                self.request,
                _("Aktualizace zboží neprovedena, příjemka je již naskladněna"),
            )
            return HttpResponseRedirect(
                reverse_lazy(
                    "kitchen:showStockReceiptArticles",
                    kwargs={"pk": stock_receipt_article.stock_receipt.id},
                )
            )
        stock_receipt_article.save()
        self.kwargs = {"pk": stock_receipt_article.stock_receipt.id}
        return super().form_valid(form)


class StockReceiptArticleDeleteView(
    SuccessMessageMixin, StockkeeperRequiredMixin, DeleteView
):
    model = StockReceiptArticle
    template_name = "kitchen/stockreceipt/deletearticle.html"
    success_message = _("Zboží bylo odstraněno")
    success_url = reverse_lazy("kitchen:showStockReceipts")
    stock_receipt_id = 0

    def get_success_url(self):
        return reverse_lazy(
            "kitchen:showStockReceiptArticles", kwargs={"pk": self.stock_receipt_id}
        )

    def form_valid(self, form):
        stock_receipt_article = get_object_or_404(
            StockReceiptArticle, pk=self.kwargs["pk"]
        )
        if stock_receipt_article.stock_receipt.approved:
            messages.warning(
                self.request,
                _("Odstranění zboží neprovedeno, příjemka je již naskladněna"),
            )
            return HttpResponseRedirect(
                reverse_lazy(
                    "kitchen:showStockReceiptArticles", kwargs={"pk": self.kwargs["pk"]}
                )
            )
        self.stock_receipt_id = stock_receipt_article.stock_receipt.id
        return super().form_valid(form)


def stock_issues_receipts_data(month):
    month = datetime.now() + relativedelta.relativedelta(months=-month)
    month_year = month.year
    month_month = month.month
    stock_issues = StockIssue.objects.filter(
        date_approved__year=month_year, date_approved__month=month_month
    )
    stock_receipts = StockReceipt.objects.filter(
        date_approved__year=month_year, date_approved__month=month_month
    )
    stock_issues_price = 0
    for si in stock_issues:
        total = si.total_price
        if total is None:
            # re-raise the conversion error so the report can name the line
            for line in si.stockissuearticle_set.select_related("article"):
                convert_units(line.amount, line.unit, line.article.unit)
        stock_issues_price += total
    stock_receipts_price = 0
    for sr in stock_receipts:
        total = sr.total_price
        if total is None:
            for line in sr.stockreceiptarticle_set.select_related("article"):
                convert_units(line.amount, line.unit, line.article.unit)
        stock_receipts_price += total
    return {
        "year": month_year,
        "month": month_month,
        "stock_issues_count": stock_issues.count(),
        "stock_issues_price": stock_issues_price,
        "stock_receipts_count": stock_receipts.count(),
        "stock_receipts_price": stock_receipts_price,
    }


class ShowFoodConsumptionTotalPrice(AnyRoleRequiredMixin, TemplateView):
    template_name = "kitchen/report/show_stock_issues_receipts_total_price.html"

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except ValidationError as error:
            messages.error(
                request,
                format_html(
                    _(
                        "Celkovou cenu nelze spočítat: {error}. "
                        'Podrobnosti najdete v <a href="{report_url}">reportu '
                        "nesprávných jednotek</a>."
                    ),
                    error="; ".join(error.messages),
                    report_url=reverse("kitchen:showIncorrectUnits"),
                ),
            )
            return HttpResponseRedirect(reverse("kitchen:showIncorrectUnits"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["all_data"] = [
            stock_issues_receipts_data(0),
            stock_issues_receipts_data(1),
            stock_issues_receipts_data(2),
            # stock_issues_receipts_data(3),
            # stock_issues_receipts_data(4),
            # stock_issues_receipts_data(5),
            # stock_issues_receipts_data(6),
            # stock_issues_receipts_data(7),
            # stock_issues_receipts_data(8),
            # stock_issues_receipts_data(9),
            # stock_issues_receipts_data(10),
            # stock_issues_receipts_data(11),
            # stock_issues_receipts_data(12),
            # stock_issues_receipts_data(13),
        ]

        return context


class IncorrectUnitsListView(SingleTableMixin, AnyRoleRequiredMixin, ListView):
    model = Recipe
    template_name = "kitchen/report/incorrect-units.html"

    @staticmethod
    def get_incorrect_articles(queryset):
        items_to_fix = []
        for item in queryset.select_related("article"):
            try:
                convert_units(item.amount, item.unit, item.article.unit)
            except ValidationError:
                items_to_fix.append(item)
        return items_to_fix

    def get_queryset(self):
        # show only recipes where article unit cannot be converted to stock article unit
        recipes = super().get_queryset()
        items_to_fix = []
        for recipe in recipes:
            articles_to_fix = []
            for recipe_article in RecipeArticle.objects.filter(recipe=recipe):
                try:
                    convert_units(
                        recipe_article.amount,
                        recipe_article.unit,
                        recipe_article.article.unit,
                    )
                except ValidationError:
                    articles_to_fix.append(recipe_article)
            if articles_to_fix:
                items_to_fix.append(
                    {
                        "recipe": recipe,
                        "articles": articles_to_fix,
                    }
                )
        return items_to_fix

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stock_issue_articles"] = self.get_incorrect_articles(
            StockIssueArticle.objects.all()
        )
        context["stock_receipt_articles"] = self.get_incorrect_articles(
            StockReceiptArticle.objects.all()
        )
        return context


class ArticlesNotInRecipesListView(SingleTableMixin, AnyRoleRequiredMixin, ListView):
    model = Article
    template_name = "kitchen/report/articles_not_in_recipe.html"

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        articles_on_recipes = RecipeArticle.objects.values_list("article__id")
        articles = Article.objects.exclude(pk__in=articles_on_recipes)
        context["articles"] = articles
        return context


class StockByUnitReportView(AnyRoleRequiredMixin, TemplateView):
    template_name = "kitchen/report/stock_by_unit.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        totals_by_unit = {
            item["unit"]: item
            for item in Article.objects.order_by()
            .values("unit")
            .annotate(
                article_count=Count("id"),
                total_on_stock=Sum("on_stock"),
            )
        }
        context["units"] = [
            {
                "value": value,
                "label": label,
                **totals_by_unit[value],
            }
            for value, label in UNIT
            if value in totals_by_unit
        ]
        context["total_articles"] = sum(
            unit["article_count"] for unit in context["units"]
        )

        selected_unit = self.request.GET.get("unit")
        unit_labels = dict(UNIT)
        if selected_unit in totals_by_unit:
            context["selected_unit"] = {
                "value": selected_unit,
                "label": unit_labels[selected_unit],
                **totals_by_unit[selected_unit],
            }
            context["articles"] = Article.objects.filter(unit=selected_unit)
            context["can_change_articles"] = user_has_any_role(
                self.request.user, UNIT_CHANGE_ROLES[UnitChangeLog.Kind.ARTICLE]
            )

        return context


class CateringUnitShowView(AnyRoleRequiredMixin, TemplateView):
    template_name = "kitchen/report/catering_unit_show.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        date_str = self.request.GET["date"]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        daily_menu_ids = DailyMenu.objects.filter(date=date_obj).values("id")
        daily_menu_recipes = DailyMenuRecipe.objects.filter(
            daily_menu__in=daily_menu_ids
        )
        recipes = Recipe.objects.filter(id__in=daily_menu_recipes.values("recipe"))

        output = []
        total_price = 0
        for recipe in recipes:
            daily_menu_recipes = (
                DailyMenuRecipe.objects.filter(daily_menu__in=daily_menu_ids)
                .filter(recipe=recipe)
                .values("recipe")
                .annotate(amount=Sum("amount"))[0]
            )
            unit_price = recipe.total_recipe_articles_price / recipe.norm_amount
            output_new = {
                "recipe": recipe.recipe,
                "unit_price": unit_price,
                "amount": daily_menu_recipes["amount"],
                "total_price": unit_price * daily_menu_recipes["amount"],
            }
            output.append(output_new)
            total_price += unit_price * daily_menu_recipes["amount"]

        context["date"] = date_obj
        context["daily_menu_recipes"] = output
        context["daily_menu_recipes_total"] = len(output)
        context["daily_menu_recipes_total_price"] = total_price
        return context


class CateringUnitFilterView(AnyRoleRequiredMixin, CreateView):
    model = DailyMenu
    form_class = DailyMenuCateringUnitForm
    template_name = "kitchen/report/catering_unit_filter.html"


UNIT_CHANGE_ROLES = {
    UnitChangeLog.Kind.ARTICLE: (Roles.STOCKKEEPER, Roles.NUTRITION_ADVISOR),
    UnitChangeLog.Kind.RECIPE_LINE: (Roles.COOK, Roles.NUTRITION_ADVISOR),
}


class UnitManagementView(AnyRoleRequiredMixin, TemplateView):
    template_name = "kitchen/units/manage.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        can_change_articles = user_has_any_role(
            user, UNIT_CHANGE_ROLES[UnitChangeLog.Kind.ARTICLE]
        )
        can_change_recipes = user_has_any_role(
            user, UNIT_CHANGE_ROLES[UnitChangeLog.Kind.RECIPE_LINE]
        )
        context["can_change_articles"] = can_change_articles
        context["can_change_recipes"] = can_change_recipes
        if can_change_articles:
            context["articles"] = Article.objects.all()
        if can_change_recipes:
            context["incorrect_recipe_articles"] = [
                recipe_article
                for recipe_article in RecipeArticle.objects.select_related(
                    "article", "recipe"
                ).order_by("recipe__recipe", "id")
                if not convertible(recipe_article.unit, recipe_article.article.unit)
            ]
        context["logs"] = [
            (
                log,
                log.kind in UNIT_CHANGE_ROLES
                and user_has_any_role(user, UNIT_CHANGE_ROLES[log.kind])
                and undo_blocker(log) is None,
            )
            for log in UnitChangeLog.objects.select_related("user", "recipe")[:50]
        ]
        return context


class UnitChangeBaseView(View):
    template_name = "kitchen/units/change.html"
    old_unit = ""
    unit_choices: list[str] = []

    def load_subject(self):
        raise NotImplementedError

    def subject_article(self):
        raise NotImplementedError

    def subject_context(self):
        raise NotImplementedError

    def preview(self, data):
        raise NotImplementedError

    def apply(self, data):
        raise NotImplementedError

    def success_url(self):
        raise NotImplementedError

    def dispatch(self, request, *args, **kwargs):
        # role mixins come first in the MRO, so the user is already checked here
        self.load_subject()
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, data=None, initial=None):
        return UnitChangeForm(
            data,
            initial=initial,
            old_unit=self.old_unit,
            unit_choices=self.unit_choices,
        )

    def suggestions(self):
        result = []
        for unit in self.unit_choices:
            factor, locked = unit_factor(self.old_unit, unit, self.subject_article())
            if factor is not None:
                result.append((unit, format_decimal(factor), locked))
        return result

    def render(self, form, preview=None):
        context = {
            "form": form,
            "preview": preview,
            "suggestions": self.suggestions(),
            "suggested_factors": {
                unit: {"factor": factor, "locked": locked}
                for unit, factor, locked in self.suggestions()
            },
            **self.subject_context(),
        }
        return render(self.request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        initial = {}
        new_unit = request.GET.get("new_unit")
        if new_unit in self.unit_choices:
            initial["new_unit"] = new_unit
            factor, _locked = unit_factor(
                self.old_unit, new_unit, self.subject_article()
            )
            with contextlib.suppress(KeyError, ArithmeticError):
                factor = Decimal(request.GET["factor"])
            if factor is not None:
                initial["factor"] = factor
        return self.render(self.get_form(initial=initial))

    def post(self, request, *args, **kwargs):
        form = self.get_form(request.POST)
        if not form.is_valid():
            return self.render(form)
        if request.POST.get("action") == "apply":
            try:
                log = self.apply(form.cleaned_data)
            except StaleUnitChangeError as error:
                for message in error.messages:
                    messages.warning(request, message)
            except UnitChangeError as error:
                for message in error.messages:
                    messages.error(request, message)
            else:
                messages.success(
                    request,
                    format_html(
                        _(
                            "Jednotka {name} byla změněna z {old} na {new}. "
                            'Změnu lze vrátit na stránce <a href="{url}">Správa jednotek</a>.'
                        ),
                        name=log.article_name,
                        old=log.old_unit,
                        new=log.new_unit,
                        url=reverse("kitchen:showUnitManagement"),
                    ),
                )
                return redirect(self.success_url())
        preview = self.preview(form.cleaned_data)
        data = request.POST.copy()
        data["fingerprint"] = preview.fingerprint
        # every preview has to be confirmed again, its warnings may differ
        data.pop("confirmed", None)
        form = self.get_form(data)
        form.is_valid()
        return self.render(form, preview)


class ArticleUnitChangeView(
    StockkeeperOrNutritionAdvisorRequiredMixin, UnitChangeBaseView
):
    def load_subject(self):
        self.article = get_object_or_404(Article, pk=self.kwargs["pk"])
        self.old_unit = self.article.unit
        self.unit_choices = [unit for unit, _label in UNIT]

    def subject_article(self):
        return self.article

    def subject_context(self):
        return {
            "title": _("Změna jednotky zboží {article}").format(article=self.article),
            "back_url": reverse("kitchen:updateArticle", args=[self.article.pk]),
            "is_article": True,
        }

    def preview(self, data):
        return preview_article_change(
            self.article, data["new_unit"], data["factor"], data["source_note"]
        )

    def apply(self, data):
        return apply_article_change(
            self.article.pk,
            data["new_unit"],
            data["factor"],
            data["source_note"],
            self.request.user,
            data["fingerprint"],
            data["confirmed"],
        )

    def success_url(self):
        return reverse("kitchen:showArticles")


class RecipeArticleUnitChangeView(
    CookOrNutritionAdvisorRequiredMixin, UnitChangeBaseView
):
    def load_subject(self):
        self.recipe_article = get_object_or_404(
            RecipeArticle.objects.select_related("article", "recipe"),
            pk=self.kwargs["pk"],
        )
        self.old_unit = self.recipe_article.unit
        self.unit_choices = [
            unit
            for unit, _label in UNIT
            if convertible(unit, self.recipe_article.article.unit)
        ]

    def subject_article(self):
        return self.recipe_article.article

    def subject_context(self):
        return {
            "title": _("Změna jednotky suroviny {article} v receptu {recipe}").format(
                article=self.recipe_article.article,
                recipe=self.recipe_article.recipe,
            ),
            "back_url": reverse(
                "kitchen:showRecipeArticles", args=[self.recipe_article.recipe_id]
            ),
            "recipe_article": self.recipe_article,
            "can_change_article": user_has_any_role(
                self.request.user, UNIT_CHANGE_ROLES[UnitChangeLog.Kind.ARTICLE]
            ),
        }

    def preview(self, data):
        return preview_recipe_line_change(
            self.recipe_article, data["new_unit"], data["factor"], data["source_note"]
        )

    def apply(self, data):
        return apply_recipe_line_change(
            self.recipe_article.pk,
            data["new_unit"],
            data["factor"],
            data["source_note"],
            self.request.user,
            data["fingerprint"],
            data["confirmed"],
        )

    def success_url(self):
        return reverse(
            "kitchen:showRecipeArticles", args=[self.recipe_article.recipe_id]
        )


class UnitChangeUndoView(AnyRoleRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        log = get_object_or_404(UnitChangeLog, pk=self.kwargs["pk"])
        roles = UNIT_CHANGE_ROLES.get(log.kind)
        if roles is not None and not user_has_any_role(request.user, roles):
            raise PermissionDenied(_("Nemáte oprávnění vrátit tuto změnu."))
        try:
            undo_change(log.pk, request.user)
        except UnitChangeError as error:
            for message in error.messages:
                messages.warning(request, message)
            reverse_url = self.reverse_conversion_url(log)
            if reverse_url:
                messages.info(
                    request,
                    _("Je předvyplněn zpětný převod, zkontroluj ho v náhledu."),
                )
                return redirect(reverse_url)
        else:
            messages.success(
                request,
                _("Změna jednotky {name} byla vrácena.").format(name=log.article_name),
            )
        return redirect("kitchen:showUnitManagement")

    @staticmethod
    def reverse_conversion_url(log):
        if log.kind == UnitChangeLog.Kind.UNDO or log.article_id is None:
            return None
        query = urlencode(
            {"new_unit": log.old_unit, "factor": quantize_factor(1 / log.factor)}
        )
        if log.kind == UnitChangeLog.Kind.ARTICLE:
            if not Article.objects.filter(
                pk=log.article_id, unit=log.new_unit
            ).exists():
                return None
            return (
                f"{reverse('kitchen:changeArticleUnit', args=[log.article_id])}?{query}"
            )
        rows = log.details.get("rows") or [{}]
        if not RecipeArticle.objects.filter(
            pk=rows[0].get("id"),
            article_id=log.article_id,
            recipe_id=log.recipe_id,
            unit=log.new_unit,
        ).exists():
            return None
        return f"{reverse('kitchen:changeRecipeArticleUnit', args=[rows[0]['id']])}?{query}"
