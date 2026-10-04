from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Count, F, Min, Sum, UniqueConstraint
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords
from simple_history.utils import bulk_update_with_history

from .functions import convert_units, quantize_unit_price
from .managers import CollatableManager

UNIT = (
    ("kg", _("kg")),
    ("g", _("g")),
    ("l", _("l")),
    ("ml", _("ml")),
    ("ks", _("ks")),
)

PIECE_WEIGHT_UNIT = (
    ("g", _("g")),
    ("ml", _("ml")),
)


def _apply_article_stock_changes(changes, prefix, comment):
    """Apply `(article, amount_delta, price_delta)` changes in a fixed number of queries.

    Deltas are summed per article first, because one document may list the same
    article on several rows. They are written as F() expressions so a concurrent
    approval adds to the stock instead of overwriting it.
    """
    totals = {}
    for article, amount_delta, price_delta in changes:
        total = totals.setdefault(article.pk, [article, Decimal("0"), Decimal("0")])
        total[1] += amount_delta
        total[2] += price_delta
    if not totals:
        return
    modified = timezone.now()
    articles = []
    for article, amount_delta, price_delta in totals.values():
        article.on_stock = F("on_stock") + amount_delta
        article.total_price = F("total_price") + price_delta
        article.modified = modified
        articles.append(article)
    Article.objects.bulk_update(articles, ["on_stock", "total_price", "modified"])
    reason_field = Article.history.model._meta.get_field("history_change_reason")
    bulk_update_with_history(
        # Re-read because the instances above still hold unresolved F() expressions.
        list(Article.objects.filter(pk__in=list(totals))),
        Article,
        # No fields: the rows are already written, only history rows are missing.
        [],
        default_change_reason=f"{prefix} - {comment or ''}"[: reason_field.max_length],
    )


class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True, verbose_name=_("Datum vytvoření"))
    modified = models.DateTimeField(auto_now=True, verbose_name=_("Datum aktualizace"))

    class Meta:
        abstract = True


class AppSettings(models.Model):
    class Meta:
        verbose_name_plural = _("Nastavení")
        verbose_name = _("Nastavení")

    currency = models.CharField(max_length=5, default="Kč", help_text=_("Mena"))

    def __str__(self):
        return f"App Settings ({self.currency})"


class VAT(models.Model):
    class Meta:
        verbose_name_plural = _("číselník - DPH")
        verbose_name = _("číselník - DPH")

    percentage = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(100)],
        unique=True,
        verbose_name=_("Výše"),
        help_text=_("DPH procenta"),
    )
    rate = models.CharField(
        max_length=100, unique=True, verbose_name=_("Sazba"), help_text=_("DPH sazba")
    )

    def __str__(self):
        return str(self.percentage) + "%"


class Allergen(models.Model):
    class Meta:
        verbose_name_plural = _("číselník - Alergeny")
        verbose_name = _("číselník - Alergen")

    code = models.CharField(
        max_length=10, unique=True, verbose_name=_("Kód"), help_text=_("Kód alergenu")
    )
    description = models.CharField(
        max_length=150,
        unique=True,
        verbose_name=_("Název"),
        help_text=_("Název alergenu"),
    )

    def __str__(self):
        return self.code + " - " + self.description


class MealGroup(models.Model):
    class Meta:
        verbose_name_plural = _("číselník - Skupiny strávníků")
        verbose_name = _("číselník - Skupina strávníků")

    meal_group = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Skupina strávníka"),
        help_text=_("Skupina pro kterou se připravuje jídlo"),
    )

    def __str__(self):
        return str(self.meal_group)


class MealType(models.Model):
    class Meta:
        verbose_name_plural = _("číselník - Druhy jídla")
        verbose_name = _("číselník - Druh jídla")

    meal_type = models.CharField(
        max_length=30,
        unique=True,
        verbose_name=_("Druh jídla"),
        help_text=_("Druh jídla v rámci dne"),
    )

    def __str__(self):
        return self.meal_type


NUTRITION_STRUCTURE = (
    ("energy", ()),  # Energie
    (
        "fat",  # Tuky
        (
            "saturated_fat",  # z toho nasycené mastné kyseliny
        ),
    ),
    (
        "carbohydrates",  # Sacharidy
        (
            "sugars",  # z toho cukry
        ),
    ),
    ("fiber", ()),  # Vláknina
    ("protein", ()),  # Bílkoviny
)

NUTRITION_FIELDS = tuple(
    field_name
    for parent_name, child_names in NUTRITION_STRUCTURE
    for field_name in (parent_name, *child_names)
)


def sum_nutrition(nutrition_values):
    totals = {field_name: Decimal("0") for field_name in NUTRITION_FIELDS}
    for values in nutrition_values:
        for field_name, value in values.items():
            totals[field_name] += value
    return totals


def divide_nutrition(values, portions):
    # a recipe without portions has no meaningful per-portion value
    if not portions:
        return sum_nutrition(())
    return {
        field_name: value / Decimal(portions) for field_name, value in values.items()
    }


def missing_piece_weight_articles(recipe_articles):
    return sorted(
        {ra.article.article for ra in recipe_articles if ra.nutrition_incomplete},
        key=str.lower,
    )


class Article(TimeStampedModel):
    objects = CollatableManager()

    class Meta:
        verbose_name_plural = _("Zboží")
        verbose_name = _("Zboží")
        ordering = ["article"]

    article = models.CharField(
        max_length=30,
        unique=True,
        verbose_name=_("Zboží"),
        help_text=_("Název zboží na skladu"),
    )
    unit = models.CharField(max_length=2, choices=UNIT, verbose_name=_("Jednotka"))
    on_stock = models.DecimalField(
        decimal_places=2,
        max_digits=8,
        validators=[MinValueValidator(Decimal("0"))],
        default=0,
        verbose_name=_("Na skladu"),
        help_text=_("Celkové množství zboží na skladu"),
    )
    min_on_stock = models.DecimalField(
        decimal_places=2,
        max_digits=8,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        default=0,
        verbose_name=_("Minimálně na skladu"),
        help_text=_("Minimální množství zboží na skladu"),
    )
    total_price = models.DecimalField(
        max_digits=8,
        blank=True,
        null=True,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=0,
        verbose_name=_("Celková cena s DPH"),
        help_text=_("Celková cena zboží na skladu"),
    )
    energy = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10000)],
        verbose_name=_("Energie"),
        help_text=_("kJ / 100 g (ml)"),
    )
    fat = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        blank=True,
        null=True,
        default=0,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name=_("Tuky"),
        help_text=_("g / 100 g (ml)"),
    )
    saturated_fat = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        blank=True,
        null=True,
        default=0,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name=_("z toho nasycené mastné kyseliny"),
        help_text=_("g / 100 g (ml)"),
    )
    carbohydrates = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        blank=True,
        null=True,
        default=0,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name=_("Sacharidy"),
        help_text=_("g / 100 g (ml)"),
    )
    sugars = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        blank=True,
        null=True,
        default=0,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name=_("z toho cukry"),
        help_text=_("g / 100 g (ml)"),
    )
    fiber = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        blank=True,
        null=True,
        default=0,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name=_("Vláknina"),
        help_text=_("g / 100 g (ml)"),
    )
    protein = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        blank=True,
        null=True,
        default=0,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name=_("Bílkoviny"),
        help_text=_("g / 100 g (ml)"),
    )
    allergen = models.ManyToManyField(Allergen, blank=True, verbose_name=_("Alergeny"))
    piece_weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Hmotnost kusu"),
        help_text=_("Pro zboží v ks: hmotnost nebo objem jednoho kusu"),
    )
    piece_weight_unit = models.CharField(  # noqa: DJ001 - nullable in migration 0031
        max_length=2,
        choices=PIECE_WEIGHT_UNIT,
        blank=True,
        null=True,
        verbose_name=_("Jednotka hmotnosti kusu"),
    )
    comment = models.CharField(
        max_length=200, blank=True, default="", verbose_name=_("Poznámka")
    )
    history = HistoricalRecords(cascade_delete_history=True)

    def __str__(self):
        return self.article

    @property
    def has_piece_weight(self):
        return bool(self.piece_weight and self.piece_weight_unit)

    @property
    def nutrition_needs_piece_weight(self):
        return (
            self.unit == "ks"
            and not self.has_piece_weight
            and any(getattr(self, name) for name in NUTRITION_FIELDS)
        )

    # average unit price with VAT or last unit price with vat from stockreceipt
    @property
    def average_price(self):
        # Prefer current stock-based average if available
        if self.on_stock:
            try:
                return quantize_unit_price(self.total_price / self.on_stock)
            except Exception:
                return 0
        # If queryset was prefetched to attr `latest_receipt`, use it to avoid an extra query
        latest = getattr(self, "latest_receipt", None)
        if latest is not None:
            return quantize_unit_price(latest[0].price_with_vat) if latest else 0
        # Fallback: hit DB once for the latest receipt article
        sra = (
            StockReceiptArticle.objects.filter(article_id=self.id)
            .select_related("vat")
            .order_by("-id")
            .first()
        )
        return 0 if sra is None else quantize_unit_price(sra.price_with_vat)

    @staticmethod
    def sum_total_price():
        sum_price = Article.objects.aggregate(total_price=Sum("total_price"))[
            "total_price"
        ]
        return 0 if sum_price is None else round(sum_price, 0)

    """Create a string for the Allergens. This is required to display allergen in Admin and user table view."""

    def display_allergens(self):
        return ", ".join(allergen.code for allergen in self.allergen.all())

    display_allergens.short_description = _("Alergeny")


class Recipe(TimeStampedModel):
    objects = CollatableManager()

    class Meta:
        verbose_name_plural = _("Recepty")
        verbose_name = _("Recept")
        ordering = ["recipe"]

    recipe = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Recept"),
        help_text=_("Název receptu"),
    )
    norm_amount = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(1000)],
        verbose_name=_("Porcí"),
    )
    procedure = models.TextField(
        max_length=1000, blank=True, default="", verbose_name=_("Postup receptu")
    )
    comment = models.CharField(
        max_length=200, blank=True, default="", verbose_name=_("Poznámka")
    )

    def __str__(self):
        return self.recipe

    # used due to django-tables2 linkify
    def get_absolute_url(self):
        return reverse_lazy("kitchen:showRecipeArticles", args=[str(self.id)])

    @property
    def nutrition_totals(self):
        recipe_articles = getattr(self, "prefetched_recipe_articles", None)
        if recipe_articles is None:
            recipe_articles = RecipeArticle.objects.select_related("article").filter(
                recipe=self.id
            )
        return sum_nutrition(
            recipe_article.nutrition_totals for recipe_article in recipe_articles
        )

    @property
    def nutrition_per_portion(self):
        return divide_nutrition(self.nutrition_totals, self.norm_amount)

    @property
    def nutrition_missing_articles(self):
        recipe_articles = getattr(self, "prefetched_recipe_articles", None)
        if recipe_articles is None:
            recipe_articles = RecipeArticle.objects.select_related("article").filter(
                recipe=self.id
            )
        return missing_piece_weight_articles(recipe_articles)

    @property
    def total_recipe_articles_price(self):
        # If recipe articles were prefetched to attr `prefetched_recipe_articles`, use them
        recipes = getattr(self, "prefetched_recipe_articles", None)
        if recipes is None:
            recipes = RecipeArticle.objects.select_related("article").filter(
                recipe=self.id
            )
        total = 0
        for recipe in recipes:
            total += recipe.total_average_price
        return total

    def allergens(self):
        # Prefer prefetched recipe articles to avoid N+1 queries
        recipe_articles = getattr(self, "prefetched_recipe_articles", None)
        if recipe_articles is None:
            recipe_articles = (
                RecipeArticle.objects.filter(recipe=self.id)
                .select_related("article")
                .prefetch_related("article__allergen")
                .order_by("id")
            )

        codes = []
        for ra in recipe_articles:
            # article__allergen may be prefetched; this avoids extra queries
            for al in ra.article.allergen.all():
                code = getattr(al, "code", None)
                if code:
                    codes.append(code)

        # preserve original order while deduplicating
        seen = set()
        unique_codes = []
        for c in codes:
            if c not in seen:
                seen.add(c)
                unique_codes.append(c)

        # sort lexicographically for display
        unique_codes = sorted(unique_codes, key=lambda s: s.lower())
        return ", ".join(unique_codes) if unique_codes else "-"


class RecipeArticle(TimeStampedModel):
    objects = CollatableManager()

    class Meta:
        verbose_name_plural = _("Suroviny v receptu")
        verbose_name = _("Surovina v receptu")
        ordering = ["article"]

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name=_("Recept"),
        related_name="recipearticle_set",
    )
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        verbose_name=_("Zboží"),
        help_text="Použité zboží",
    )
    amount = models.DecimalField(
        decimal_places=2,
        max_digits=10,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Množství"),
        help_text=_("Množství suroviny"),
    )
    unit = models.CharField(max_length=2, choices=UNIT, verbose_name=_("Jednotka"))
    comment = models.CharField(
        max_length=200, blank=True, default="", verbose_name=_("Poznámka")
    )

    def __str__(self):
        return (
            self.recipe.recipe + "-  " + self.article.article + "-  " + str(self.amount)
        )

    @property
    def nutrition_factor(self):
        # nutrition is per 100 g / 100 ml, a piece needs its own weight
        if self.unit in ("kg", "l"):
            return self.amount * Decimal("10")
        if self.unit in ("g", "ml"):
            return self.amount / Decimal("100")
        if self.article.has_piece_weight:
            return self.amount * self.article.piece_weight / Decimal("100")
        return None

    @property
    def nutrition_incomplete(self):
        return self.nutrition_factor is None

    def nutrition_total(self, field_name):
        factor = self.nutrition_factor
        if factor is None:
            return Decimal("0")
        # nutrition values are nullable - a missing value counts as zero
        value = getattr(self.article, field_name) or 0
        return value * factor

    @property
    def nutrition_totals(self):
        return {
            field_name: self.nutrition_total(field_name)
            for field_name in NUTRITION_FIELDS
        }

    @property
    def nutrition_per_portion(self):
        return divide_nutrition(self.nutrition_totals, self.recipe.norm_amount)

    @property
    def total_average_price(self):
        try:
            converted = convert_units(self.amount, self.unit, self.article.unit)
        except Exception:
            converted = 0
        return round(converted * self.article.average_price, 2)


class Menu(TimeStampedModel):
    class Meta:
        verbose_name_plural = _("Menu")
        verbose_name = _("Menu")
        ordering = ["menu"]

    menu = models.CharField(
        max_length=100, unique=True, verbose_name=_("Menu"), help_text=_("Název menu")
    )
    meal_type = models.ForeignKey(
        MealType,
        on_delete=models.CASCADE,
        verbose_name=_("Druh jídla"),
        help_text=_("Druh jídla v rámci dne"),
    )
    comment = models.CharField(
        max_length=200, blank=True, default="", verbose_name=_("Poznámka")
    )

    def __str__(self):
        return self.menu

    @property
    def recipe_count(self):
        # If annotated by a queryset (e.g., in a view), reuse it to avoid extra queries
        annotated = self.__dict__.get("rc") or self.__dict__.get("recipe_count_annot")
        if annotated is not None:
            return annotated
        return MenuRecipe.objects.filter(menu=self.id).aggregate(
            recipe_count=Count("recipe")
        )["recipe_count"]


class MenuRecipe(TimeStampedModel):
    objects = CollatableManager()

    class Meta:
        verbose_name_plural = _("Recepty menu")
        verbose_name = _("Recepty menu")
        ordering = ["recipe"]
        constraints = [
            UniqueConstraint(fields=["menu", "recipe"], name="unique_menu_recipe_pair"),
        ]

    menu = models.ForeignKey(
        Menu,
        on_delete=models.CASCADE,
        verbose_name=_("Menu"),
        related_name="menurecipe",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name=_("Recept"),
        help_text=_("Vybraný recept"),
    )
    amount = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(1000)],
        verbose_name=_("Porcí"),
        help_text=_("Počet porcí"),
    )

    def __str__(self):
        return self.recipe.recipe + " - " + str(self.amount)


class DailyMenu(TimeStampedModel):
    objects = CollatableManager()

    class Meta:
        verbose_name_plural = _("Denní menu")
        verbose_name = _("Denní menu")
        ordering = ["-date", "meal_group"]
        constraints = [
            UniqueConstraint(
                fields=["date", "meal_group", "meal_type"],
                name="unique_dailymenu_per_date_group_type",
            ),
        ]

    date = models.DateField(verbose_name=_("Datum"), help_text=_("Datum denního menu"))
    menu = models.ForeignKey(
        Menu,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Menu"),
        help_text=_("Přeber recepty z připraveného menu"),
    )
    meal_group = models.ForeignKey(
        MealGroup,
        on_delete=models.CASCADE,
        verbose_name=_("Skupina strávníka"),
        help_text=_("Skupina pro kterou se připravuje jídlo"),
    )
    meal_type = models.ForeignKey(
        MealType,
        on_delete=models.CASCADE,
        verbose_name=_("Druh jídla"),
        help_text=_("Druh jídla v rámci dne"),
    )
    comment = models.CharField(
        max_length=200, blank=True, default="", verbose_name=_("Poznámka")
    )

    def __str__(self):
        return (
            str(self.date)
            + " - "
            + self.meal_type.meal_type
            + " - "
            + self.meal_group.meal_group
        )

    @property
    def nutrition_per_portion(self):
        daily_menu_recipes = getattr(self, "prefetched_daily_menu_recipes", None)
        if daily_menu_recipes is None:
            recipe_articles = models.Prefetch(
                "recipe__recipearticle_set",
                queryset=RecipeArticle.objects.select_related("article"),
                to_attr="prefetched_recipe_articles",
            )
            daily_menu_recipes = (
                DailyMenuRecipe.objects.filter(daily_menu=self.id)
                .select_related("recipe")
                .prefetch_related(recipe_articles)
            )
        return sum_nutrition(
            daily_menu_recipe.nutrition_per_portion
            for daily_menu_recipe in daily_menu_recipes
        )

    @property
    def nutrition_missing_articles(self):
        daily_menu_recipes = getattr(self, "prefetched_daily_menu_recipes", None)
        if daily_menu_recipes is None:
            daily_menu_recipes = DailyMenuRecipe.objects.filter(
                daily_menu=self.id
            ).select_related("recipe")
        names = set()
        for daily_menu_recipe in daily_menu_recipes:
            names.update(daily_menu_recipe.nutrition_missing_articles)
        return sorted(names, key=str.lower)


class DailyMenuRecipe(TimeStampedModel):
    objects = CollatableManager()

    class Meta:
        verbose_name_plural = _("Recepty denního menu")
        verbose_name = _("Recepty denního menu")
        ordering = ["recipe"]
        constraints = [
            UniqueConstraint(
                fields=["daily_menu", "recipe"], name="unique_dailymenu_recipe_pair"
            ),
        ]

    daily_menu = models.ForeignKey(
        DailyMenu,
        on_delete=models.CASCADE,
        verbose_name=_("Denní menu"),
        related_name="dailymenurecipe",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name=_("Recept"),
        help_text=_("Vybraný recept"),
    )
    amount = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(1000)],
        verbose_name=_("Porcí"),
        help_text=_("Počet porcí"),
    )
    comment = models.CharField(
        max_length=200, blank=True, default="", verbose_name=_("Poznámka")
    )

    def __str__(self):
        return self.recipe.recipe + " - " + str(self.amount)

    @property
    def nutrition_per_portion(self):
        # a recipe with 0 portions is not served, so it adds nothing to the menu
        if not self.amount:
            return sum_nutrition(())
        return self.recipe.nutrition_per_portion

    @property
    def nutrition_missing_articles(self):
        if not self.amount:
            return []
        return self.recipe.nutrition_missing_articles


class StockIssue(TimeStampedModel):
    class Meta:
        verbose_name_plural = _("Výdejky")
        verbose_name = _("Výdejka")
        ordering = ["-created"]

    user_created = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="user_is_created",
        verbose_name=_("Vytvořil"),
    )
    approved = models.BooleanField(
        default=False, blank=True, null=True, verbose_name=_("Vyskladněno")
    )
    date_approved = models.DateField(
        blank=True, null=True, verbose_name=_("Datum vyskladnění")
    )
    user_approved = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="user_is_approved",
        verbose_name=_("Vyskladnil"),
    )
    comment = models.CharField(
        max_length=200, blank=True, default="", verbose_name=_("Poznámka")
    )
    menu_date = models.DateField(
        blank=True, null=True, verbose_name=_("Datum denního menu")
    )

    def __str__(self):
        return str(self.created)

    @property
    def total_price(self):
        stock_issue_articles = StockIssueArticle.objects.select_related(
            "article"
        ).filter(stock_issue=self.id)
        # sum of rounded lines, same as the stock value change on approval
        return sum(line.total_average_price_with_vat for line in stock_issue_articles)

    def consolidate_by_article(self):
        # select all articles where count > 1
        # group by article_id and sum amount and average_unit_price
        articles_to_consolidate = (
            StockIssueArticle.objects.filter(stock_issue_id=self.pk)
            .values("article_id")
            .annotate(
                average_unit_price=Min("average_unit_price"),
                total=Count("article_id"),
                sumAmount=Sum("amount"),
            )
            .filter(total__gt=1)
        )
        article_ids = []
        for article in articles_to_consolidate:
            article_ids.append(article["article_id"])
        # remove all articles where count > 1
        StockIssueArticle.objects.filter(
            stock_issue_id=self.pk, article_id__in=article_ids
        ).delete()
        # insert consolidated articles
        for article in articles_to_consolidate:
            x = StockIssueArticle(
                stock_issue=self,
                article=Article.objects.filter(pk=article["article_id"]).get(),
                amount=article["sumAmount"],
                unit=Article.objects.filter(pk=article["article_id"]).get().unit,
                average_unit_price=article["average_unit_price"],
                comment="ca",
            )
            x.save()
        return len(StockIssueArticle.objects.filter(stock_issue_id=self.pk))

    @staticmethod
    def create_from_daily_menu(daily_menus, date, user, menu_date=None):
        with transaction.atomic():
            # save the StockIssue
            stock_issue = StockIssue(
                comment=_("Pro ") + date, user_created=user, menu_date=menu_date
            )
            stock_issue.save()
            # save all StockIssue Articles
            daily_menu_recipes = DailyMenuRecipe.objects.select_related(
                "recipe"
            ).filter(daily_menu__in=daily_menus)
            article_totals = {}
            for daily_menu_recipe in daily_menu_recipes:
                recipe_articles = RecipeArticle.objects.select_related(
                    "article"
                ).filter(recipe_id=daily_menu_recipe.recipe_id)
                norm_amount = daily_menu_recipe.recipe.norm_amount
                if not norm_amount:
                    raise ValidationError(
                        _("Recept {recipe} má nulový počet porcí").format(
                            recipe=daily_menu_recipe.recipe
                        )
                    )
                for recipe_article in recipe_articles:
                    # get the coefficient between daily menu amount and recipe amount
                    recipe_article_coefficient = Decimal(
                        daily_menu_recipe.amount
                    ) / Decimal(norm_amount)
                    recipe_article_amount = (
                        convert_units(
                            recipe_article.amount,
                            recipe_article.unit,
                            recipe_article.article.unit,
                        )
                        * recipe_article_coefficient
                    )
                    total = article_totals.setdefault(
                        recipe_article.article_id,
                        [recipe_article.article, Decimal("0")],
                    )
                    total[1] += recipe_article_amount
            count = 0
            for article, amount in article_totals.values():
                amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if not amount:
                    continue
                StockIssueArticle.objects.create(
                    stock_issue=stock_issue,
                    article=article,
                    amount=amount,
                    unit=article.unit,
                    average_unit_price=article.average_price,
                    comment="",
                )
                count += 1
        return count

    @staticmethod
    def update_stock_issue_article_average_unit_price(stock_issue_id):
        latest_receipt = models.Prefetch(
            "article__stockreceiptarticle_set",
            queryset=StockReceiptArticle.objects.select_related("vat").order_by("-id")[
                :1
            ],
            to_attr="latest_receipt",
        )
        stock_issue_articles = list(
            StockIssueArticle.objects.filter(stock_issue_id=stock_issue_id)
            .select_related("article")
            .prefetch_related(latest_receipt)
        )
        modified = timezone.now()
        for stock_issue_article in stock_issue_articles:
            stock_issue_article.average_unit_price = (
                stock_issue_article.article.average_price
            )
            stock_issue_article.modified = modified
        StockIssueArticle.objects.bulk_update(
            stock_issue_articles,
            ["average_unit_price", "modified"],
        )

    @staticmethod
    def update_article_on_stock(stock_id, comment, fake):
        stock_articles = StockIssueArticle.objects.select_related("article").filter(
            stock_issue=stock_id
        )
        messages = []
        changes = []
        issued = {}
        for stock_article in stock_articles:
            article = stock_article.article
            converted_amount = convert_units(
                stock_article.amount, stock_article.unit, article.unit
            )
            delta_amount = Decimal(round(converted_amount, 2))
            total = issued.setdefault(article.pk, [article, Decimal("0")])
            total[1] += delta_amount
            if not fake:
                delta_price = Decimal(
                    round(stock_article.total_average_price_with_vat, 0)
                )
                changes.append((article, -delta_amount, -delta_price))
        for article, converted_amount in issued.values():
            if article.on_stock < 0 or article.on_stock - converted_amount < 0:
                messages.append(
                    _(
                        "{article} - na výdejce {converted_amount}, na skladu {on_stock}"
                    ).format(
                        article=article,
                        converted_amount=converted_amount,
                        on_stock=article.on_stock,
                    )
                )
        _apply_article_stock_changes(changes, _("Výdej"), comment)
        return messages


class StockReceipt(TimeStampedModel):
    class Meta:
        verbose_name_plural = _("Příjemky")
        verbose_name = _("Příjemka")
        ordering = ["-created"]

    date_created = models.DateField(
        default=timezone.localdate, verbose_name=_("Datum založení")
    )
    user_created = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="user_created",
        verbose_name=_("Vytvořil"),
    )
    approved = models.BooleanField(
        default=False, blank=True, null=True, verbose_name=_("Naskladněno")
    )
    date_approved = models.DateField(
        blank=True, null=True, verbose_name=_("Datum naskladnění")
    )
    user_approved = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="user_approved",
        verbose_name=_("Naskladnil"),
    )
    comment = models.CharField(
        max_length=200, blank=True, default="", verbose_name=_("Poznámka")
    )

    def __str__(self):
        return str(self.created)

    @property
    def total_price(self):
        stock_receipt_articles = StockReceiptArticle.objects.filter(
            stock_receipt=self.id
        )
        total_price = 0
        for stock_receipt_article in stock_receipt_articles:
            total_price += stock_receipt_article.total_price_with_vat
        return round(total_price, 0)

    @staticmethod
    def update_article_on_stock(stock_id, comment):
        stock_articles = StockReceiptArticle.objects.select_related(
            "article", "vat"
        ).filter(stock_receipt=stock_id)
        changes = []
        for stock_article in stock_articles:
            article = stock_article.article
            converted_amount = convert_units(
                stock_article.amount, stock_article.unit, article.unit
            )
            delta_amount = Decimal(round(converted_amount, 2))
            delta_price = Decimal(round(stock_article.total_price_with_vat, 0))
            changes.append((article, delta_amount, delta_price))
        _apply_article_stock_changes(changes, "Příjem", comment)


class StockIssueArticle(TimeStampedModel):
    objects = CollatableManager()

    class Meta:
        verbose_name_plural = _("Zboží na výdejce")
        verbose_name = _("Zboží na výdejce")
        ordering = ["article"]

    stock_issue = models.ForeignKey(
        StockIssue, on_delete=models.CASCADE, verbose_name=_("Výdejka")
    )
    article = models.ForeignKey(
        Article, on_delete=models.PROTECT, verbose_name=_("Zboží")
    )
    amount = models.DecimalField(
        decimal_places=2,
        max_digits=8,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Množství"),
    )
    unit = models.CharField(max_length=2, choices=UNIT, verbose_name=_("Jednotka"))
    average_unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0"))],
        blank=True,
        null=True,
        verbose_name=_("Průměrná jednotková cena s DPH"),
    )
    comment = models.CharField(
        max_length=200, blank=True, default="", verbose_name=_("Poznámka")
    )

    @property
    def total_average_price_with_vat(self):
        if self.amount is not None and self.average_unit_price is not None:
            return round(
                self.average_unit_price
                * convert_units(self.amount, self.unit, self.article.unit),
                0,
            )
        return 0

    def __str__(self):
        return self.article.article + " - " + str(self.amount) + self.unit


class StockReceiptArticle(TimeStampedModel):
    objects = CollatableManager()

    class Meta:
        verbose_name_plural = _("Zboží na příjemce")
        verbose_name = _("Zboží na příjemce")
        ordering = ["article"]

    stock_receipt = models.ForeignKey(
        StockReceipt, on_delete=models.CASCADE, verbose_name=_("Příjemka")
    )
    article = models.ForeignKey(
        Article,
        on_delete=models.PROTECT,
        verbose_name=_("Zboží"),
        related_name="stockreceiptarticle_set",
    )
    amount = models.DecimalField(
        decimal_places=2,
        max_digits=8,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Množství"),
    )
    unit = models.CharField(max_length=2, choices=UNIT, verbose_name=_("Jednotka"))
    price_without_vat = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
        verbose_name=_("Jednotková cena bez DPH"),
    )
    vat = models.ForeignKey(
        VAT, default=4, on_delete=models.PROTECT, verbose_name=_("DPH")
    )
    comment = models.CharField(
        max_length=200, blank=True, default="", verbose_name=_("Poznámka")
    )

    @property
    def price_with_vat(self):
        if self.price_without_vat is not None and self.vat.percentage is not None:
            return (
                self.price_without_vat
                + self.price_without_vat * self.vat.percentage / 100
            )
        return 0

    @property
    def total_price_with_vat(self):
        if self.price_with_vat is not None and self.amount is not None:
            return round(
                self.price_with_vat
                * convert_units(self.amount, self.unit, self.article.unit),
                0,
            )
        return 0

    def __str__(self):
        return self.article.article + " - " + str(self.amount) + self.unit
