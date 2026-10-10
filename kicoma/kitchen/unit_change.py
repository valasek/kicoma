"""Managed unit change of an article or of a single recipe line.

Factor semantics: 1 old unit = factor new units. Receipt and issue unit prices
always refer to the current article unit, so an article change converts every
line of the article, approved documents included.
"""

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone
from django.utils.translation import gettext as _

from .functions import UNIT_PRICE_QUANTUM, convert_units, format_decimal
from .models import (
    NUTRITION_FIELDS,
    Article,
    RecipeArticle,
    StockIssueArticle,
    StockReceiptArticle,
    UnitChangeLog,
)
from .utils import get_currency

AMOUNT_QUANTUM = Decimal("0.01")
FACTOR_QUANTUM = Decimal("0.000001")
MAX_FACTOR = Decimal("1000000")
MIN_LINE_AMOUNT = Decimal("0.01")
TOLERANCE = Decimal("0.05")
PIECE_SIZE_RANGE = (Decimal("1"), Decimal("25000"))
DENSITY_RANGE = (Decimal("0.3"), Decimal("2.0"))
PRICE_PER_KG_RANGE = (Decimal("1"), Decimal("5000"))

# size of one unit in g or ml
BASE_SIZE = {"kg": Decimal(1000), "g": Decimal(1), "l": Decimal(1000), "ml": Decimal(1)}
DIMENSION = {
    "kg": "weight",
    "g": "weight",
    "l": "volume",
    "ml": "volume",
    "ks": "piece",
}
BASE_UNIT = {"weight": "g", "volume": "ml"}
LARGE_UNIT = {"weight": "kg", "volume": "l"}
SIZE_HINT = re.compile(
    r"(?:(\d+)\s*[x×]\s*)?(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l)\b", re.IGNORECASE
)

LINE_MODELS: dict[str, tuple[Any, str | None]] = {
    "recipe": (RecipeArticle, None),
    "receipt": (StockReceiptArticle, "price_without_vat"),
    "issue": (StockIssueArticle, "average_unit_price"),
}
ARTICLE_FIELDS = (
    "unit",
    "on_stock",
    "min_on_stock",
    "total_price",
    "piece_weight",
    "piece_weight_unit",
)
DECIMAL_KEYS = {
    "on_stock",
    "min_on_stock",
    "total_price",
    "piece_weight",
    "amount",
    "price",
}


class UnitChangeError(Exception):
    def __init__(self, messages):
        self.messages = [messages] if isinstance(messages, str) else list(messages)
        super().__init__("; ".join(str(message) for message in self.messages))


class StaleUnitChangeError(UnitChangeError):
    pass


def convertible(unit_in, unit_out):
    return unit_in == unit_out or (
        DIMENSION[unit_in] != "piece" and DIMENSION[unit_in] == DIMENSION[unit_out]
    )


def quantize_amount(value):
    return Decimal(value).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)


def quantize_price(value):
    return Decimal(value).quantize(UNIT_PRICE_QUANTUM, rounding=ROUND_HALF_UP)


def quantize_factor(value):
    return Decimal(value).quantize(FACTOR_QUANTUM, rounding=ROUND_HALF_UP)


def unit_factor(old_unit, new_unit, article=None):
    """Return `(factor, locked)`; locked factors are fixed (kg<->g, l<->ml)."""
    if old_unit == new_unit:
        return None, False
    if convertible(old_unit, new_unit):
        return convert_units(Decimal(1), old_unit, new_unit), True
    if article is not None and article.has_piece_weight:
        piece_dimension = DIMENSION[article.piece_weight_unit]
        if old_unit == "ks" and DIMENSION[new_unit] == piece_dimension:
            return quantize_factor(article.piece_weight / BASE_SIZE[new_unit]), False
        if new_unit == "ks" and DIMENSION[old_unit] == piece_dimension:
            return quantize_factor(BASE_SIZE[old_unit] / article.piece_weight), False
    return None, False


def latest_unit_change_id():
    return UnitChangeLog.objects.aggregate(latest=Max("id"))["latest"] or 0


def article_unit_changed_since(article, marker):
    return (
        UnitChangeLog.objects.filter(article=article, pk__gt=marker)
        .filter(
            Q(kind=UnitChangeLog.Kind.ARTICLE)
            | Q(kind=UnitChangeLog.Kind.UNDO, undo_of__kind=UnitChangeLog.Kind.ARTICLE)
        )
        .exists()
    )


@dataclass
class LineChange:
    kind: str
    line: Any
    before: dict
    after: dict
    broken: bool = False
    rounded: bool = False
    total_before: Decimal | None = None
    total_after: Decimal | None = None

    @property
    def document(self):
        if self.kind == "receipt":
            return self.line.stock_receipt
        if self.kind == "issue":
            return self.line.stock_issue
        return self.line.recipe

    @property
    def approved(self):
        return bool(getattr(self.document, "approved", False))

    @property
    def changed(self):
        return self.before != self.after

    @property
    def label(self):
        if self.kind == "receipt":
            return _("Příjemka #{id}").format(id=self.line.stock_receipt_id)
        if self.kind == "issue":
            return _("Výdejka #{id}").format(id=self.line.stock_issue_id)
        return _("Recept {recipe}").format(recipe=self.line.recipe)


@dataclass
class UnitChangePreview:
    kind: str
    article: Article
    old_unit: str
    new_unit: str
    factor: Decimal | None
    recipe_article: RecipeArticle | None = None
    article_before: dict = field(default_factory=dict)
    article_after: dict = field(default_factory=dict)
    lines: list[LineChange] = field(default_factory=list)
    examples: list[tuple[str, str, str]] = field(default_factory=list)
    document_differences: list[dict] = field(default_factory=list)
    recipe_comparison: list[tuple[str, str, str]] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    fingerprint: str = ""

    @property
    def reverse_factor(self):
        if not self.factor:
            return None
        return quantize_factor(1 / self.factor)

    @property
    def recipe_lines(self):
        return [line for line in self.lines if line.kind == "recipe"]

    @property
    def open_document_lines(self):
        return [
            line for line in self.lines if line.kind != "recipe" and not line.approved
        ]

    @property
    def approved_document_lines(self):
        return [line for line in self.lines if line.kind != "recipe" and line.approved]


def _hash(parts):
    return hashlib.sha256(json.dumps(parts, default=str).encode()).hexdigest()


# 2, Decimal("2") and Decimal("2.00") must give the same fingerprint
def _normalized(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int | Decimal):
        return format_decimal(value)
    return value


def _jsonable(state):
    return {
        key: str(value) if isinstance(value, Decimal) else value
        for key, value in state.items()
    }


def _from_json(state):
    return {
        key: Decimal(value) if key in DECIMAL_KEYS and value is not None else value
        for key, value in state.items()
    }


def _exceeds(model, field_name, value):
    model_field = model._meta.get_field(field_name)
    limit = Decimal(10) ** (model_field.max_digits - model_field.decimal_places)
    return abs(value) >= limit


def _related_lines(article):
    return {
        "recipe": list(
            RecipeArticle.objects.filter(article=article)
            .select_related("recipe")
            .order_by("recipe__recipe", "id")
        ),
        "receipt": list(
            StockReceiptArticle.objects.filter(article=article)
            .select_related("stock_receipt", "vat")
            .order_by("-id")
        ),
        "issue": list(
            StockIssueArticle.objects.filter(article=article)
            .select_related("stock_issue")
            .order_by("-id")
        ),
    }


# backups (dumpdata) keep only milliseconds, an undo must still work after a restore
def _timestamp(value):
    return value.isoformat(timespec="milliseconds")


def _record_state(instance):
    return [
        (
            model_field.attname,
            _timestamp(value) if isinstance(value, datetime) else _normalized(value),
        )
        for model_field in instance._meta.concrete_fields
        for value in [getattr(instance, model_field.attname)]
    ]


def _line_state(kind, line):
    state = [kind, line.pk, _record_state(line)]
    if kind == "receipt":
        state.extend([_record_state(line.stock_receipt), _record_state(line.vat)])
    elif kind == "issue":
        state.append(_record_state(line.stock_issue))
    else:
        state.append(_record_state(line.recipe))
    return state


def _article_fingerprint(article, related):
    parts = ["article", _record_state(article)]
    for kind in sorted(related):
        parts.extend(
            _line_state(kind, line)
            for line in sorted(related[kind], key=lambda row: row.pk)
        )
    return _hash(parts)


def _recipe_line_fingerprint(recipe_article):
    return _hash(
        [
            "recipe_line",
            _record_state(recipe_article),
            _record_state(recipe_article.recipe),
            [
                [
                    _record_state(line),
                    _record_state(line.article),
                    _normalized(line.article.average_price),
                ]
                for line in RecipeArticle.objects.filter(
                    recipe_id=recipe_article.recipe_id
                )
                .select_related("article")
                .order_by("pk")
            ],
        ]
    )


# a preview confirmed for other data or another unit/factor must not be applied
def _request_fingerprint(data_fingerprint, new_unit, factor):
    return _hash([data_fingerprint, new_unit, str(factor)])


def _line_total(kind, state, article_unit, vat_percentage):
    if state["price"] is None or state["amount"] is None:
        return None
    try:
        amount = convert_units(state["amount"], state["unit"], article_unit)
    except ValidationError:
        return None
    price = state["price"]
    if kind == "receipt":
        price = price + price * vat_percentage / 100
    return round(price * amount, 0)


def _convert_line(kind, line, old_unit, new_unit, factor):
    _model, price_field = LINE_MODELS[kind]
    price = getattr(line, price_field) if price_field else None
    before = {"amount": line.amount, "unit": line.unit, "price": price}
    after = dict(before)
    change = LineChange(kind=kind, line=line, before=before, after=after)
    if convertible(line.unit, new_unit):
        pass
    elif convertible(line.unit, old_unit):
        exact = convert_units(line.amount, line.unit, old_unit) * factor
        after["amount"] = quantize_amount(exact)
        after["unit"] = new_unit
        change.rounded = after["amount"] != exact
    else:
        # its price is still per the line unit, dividing it would corrupt the total
        change.broken = True
        return change
    if price is not None:
        after["price"] = quantize_price(price / factor)
        vat = line.vat.percentage if kind == "receipt" else None
        change.total_before = _line_total(kind, before, old_unit, vat)
        change.total_after = _line_total(kind, after, new_unit, vat)
    return change


def _check_input(preview, source_note):
    """Add input blockers; return False when no conversion can be computed."""
    computable = True
    if preview.old_unit == preview.new_unit:
        preview.blockers.append(_("Nová jednotka je stejná jako původní."))
        computable = False
    if preview.factor is None or preview.factor <= 0:
        preview.blockers.append(_("Zadej převodní koeficient větší než 0."))
        computable = False
    elif preview.factor >= MAX_FACTOR:
        preview.blockers.append(_("Převodní koeficient je příliš velký."))
        computable = False
    if not (source_note or "").strip():
        preview.blockers.append(_("Zadej zdroj koeficientu, například „etiketa 42 g“."))
    return computable


def _close(value, expected):
    return expected > 0 and abs(value - expected) / expected <= TOLERANCE


def _name_size_hints(name, dimension):
    hints = []
    for match in SIZE_HINT.finditer(name):
        count, size, unit = match.groups()
        unit = unit.lower()
        if DIMENSION[unit] != dimension:
            continue
        value = Decimal(size.replace(",", ".")) * BASE_SIZE[unit]
        hints.append(value)
        if count:
            hints.append(value * int(count))
    return hints


def _plausibility_warnings(preview, article, old_unit, new_unit, factor):
    piece = dimension = None
    if old_unit == "ks" and new_unit in BASE_SIZE:
        piece, dimension = factor * BASE_SIZE[new_unit], DIMENSION[new_unit]
    elif new_unit == "ks" and old_unit in BASE_SIZE:
        piece, dimension = BASE_SIZE[old_unit] / factor, DIMENSION[old_unit]
    if piece is not None and dimension is not None:
        base_unit = BASE_UNIT[dimension]
        shown_piece = format_decimal(quantize_amount(piece))
        hints = _name_size_hints(article.article, dimension)
        if hints and not any(_close(piece, hint) for hint in hints):
            preview.warnings.append(
                _(
                    "Název zboží „{name}“ uvádí jinou velikost kusu, "
                    "než vychází z koeficientu (1 ks = {piece} {unit})."
                ).format(name=article.article, piece=shown_piece, unit=base_unit)
            )
        if (
            article.has_piece_weight
            and DIMENSION[article.piece_weight_unit] == dimension
            and not _close(piece, article.piece_weight)
        ):
            preview.warnings.append(
                _(
                    "Koeficient neodpovídá uložené hmotnosti kusu {weight} {weight_unit} "
                    "(1 ks = {piece} {unit})."
                ).format(
                    weight=format_decimal(article.piece_weight),
                    weight_unit=article.piece_weight_unit,
                    piece=shown_piece,
                    unit=base_unit,
                )
            )
        if not PIECE_SIZE_RANGE[0] <= piece <= PIECE_SIZE_RANGE[1]:
            preview.warnings.append(
                _(
                    "1 ks = {piece} {unit} je mimo obvyklý rozsah 1 {unit} až 25 000 {unit}."
                ).format(piece=shown_piece, unit=base_unit)
            )
    if {DIMENSION[old_unit], DIMENSION[new_unit]} == {"weight", "volume"}:
        if DIMENSION[old_unit] == "weight":
            mass, volume = BASE_SIZE[old_unit], factor * BASE_SIZE[new_unit]
        else:
            mass, volume = factor * BASE_SIZE[new_unit], BASE_SIZE[old_unit]
        density = mass / volume
        if not DENSITY_RANGE[0] <= density <= DENSITY_RANGE[1]:
            preview.warnings.append(
                _(
                    "Hustota {density} kg/l je mimo obvyklý rozsah 0,3 až 2,0 kg/l."
                ).format(density=format_decimal(density.quantize(Decimal("0.001"))))
            )
        preview.info.append(
            _(
                "Převod mezi hmotností a objemem: zkontroluj, zda jsou výživové "
                "údaje zadány na 100 g nebo na 100 ml."
            )
        )


def _price_warning(preview, article, new_unit, factor):
    if new_unit not in BASE_SIZE:
        return
    average = Decimal(article.average_price or 0)
    if average <= 0:
        return
    per_large_unit = average / factor * (Decimal(1000) / BASE_SIZE[new_unit])
    if not PRICE_PER_KG_RANGE[0] <= per_large_unit <= PRICE_PER_KG_RANGE[1]:
        preview.warnings.append(
            _(
                "Výsledná průměrná cena {price} {currency}/{unit} je mimo obvyklý "
                "rozsah 1 až 5 000 {currency}/{unit}."
            ).format(
                price=format_decimal(per_large_unit.quantize(Decimal("0.01"))),
                currency=get_currency(),
                unit=LARGE_UNIT[DIMENSION[new_unit]],
            )
        )


def _line_blockers(preview):
    below_minimum, too_large, zero_price = [], [], []
    for change in preview.lines:
        model, price_field = LINE_MODELS[change.kind]
        if change.after["amount"] != change.before["amount"]:
            if change.after["amount"] < MIN_LINE_AMOUNT:
                below_minimum.append(change.label)
            elif _exceeds(model, "amount", change.after["amount"]):
                too_large.append(change.label)
        if price_field and change.before["price"]:
            if not change.after["price"]:
                zero_price.append(change.label)
            elif _exceeds(model, price_field, change.after["price"]):
                too_large.append(change.label)
    if below_minimum:
        preview.blockers.append(
            _(
                "Množství by se zaokrouhlilo pod 0.01 {unit}, zvol menší jednotku: {lines}"
            ).format(unit=preview.new_unit, lines=", ".join(below_minimum))
        )
    if zero_price:
        preview.blockers.append(
            _(
                "Jednotková cena by se zaokrouhlila na 0, zvol menší jednotku: {lines}"
            ).format(lines=", ".join(zero_price))
        )
    if too_large:
        preview.blockers.append(
            _("Hodnota by přesáhla povolený počet číslic: {lines}").format(
                lines=", ".join(too_large)
            )
        )


def _document_differences(preview):
    differences = {}
    for change in preview.lines:
        if change.kind == "recipe" or change.total_before is None:
            continue
        if change.total_after is None or change.total_after == change.total_before:
            continue
        document = change.document
        entry = differences.setdefault(
            (change.kind, document.pk),
            {
                "label": change.label,
                "approved": change.approved,
                "month": document.date_approved.strftime("%Y-%m")
                if document.date_approved
                else "",
                "difference": Decimal(0),
            },
        )
        entry["difference"] += change.total_after - change.total_before
    preview.document_differences = [
        entry for entry in differences.values() if entry["difference"]
    ]


def _price_text(price, unit):
    return f"{format_decimal(price)} {get_currency()} / {unit}"


def _article_examples(preview):
    before, after = preview.article_before, preview.article_after
    preview.examples.append(
        (
            _("Stav skladu"),
            f"{before['on_stock']} {preview.old_unit}",
            f"{after['on_stock']} {preview.new_unit}",
        )
    )
    receipt = next((line for line in preview.lines if line.kind == "receipt"), None)
    if receipt is not None:
        preview.examples.append(
            (
                _("Poslední příjemka") + f" ({receipt.label})",
                f"{receipt.before['amount']} {receipt.before['unit']}, "
                + _price_text(receipt.before["price"], preview.old_unit),
                f"{receipt.after['amount']} {receipt.after['unit']}, "
                + _price_text(receipt.after["price"], preview.new_unit),
            )
        )
    recipe = next((line for line in preview.recipe_lines if line.changed), None)
    if recipe is not None:
        preview.examples.append(
            (
                recipe.label,
                f"{recipe.before['amount']} {recipe.before['unit']}",
                f"{recipe.after['amount']} {recipe.after['unit']}",
            )
        )


def _article_info(preview, article_rounded):
    documents = defaultdict(set)
    for change in preview.lines:
        if change.kind != "recipe":
            documents[(change.kind, change.approved)].add(change.document.pk)
    preview.info.append(
        _(
            "Přepočtou se řádky dokladů: příjemky {open_receipts} nenaskladněné a "
            "{approved_receipts} naskladněné, výdejky {open_issues} nevyskladněné a "
            "{approved_issues} vyskladněné. Údaje o schválení zůstanou beze změny."
        ).format(
            open_receipts=len(documents[("receipt", False)]),
            approved_receipts=len(documents[("receipt", True)]),
            open_issues=len(documents[("issue", False)]),
            approved_issues=len(documents[("issue", True)]),
        )
    )
    recipes = sorted(
        {str(line.line.recipe) for line in preview.recipe_lines if line.changed},
        key=str.lower,
    )
    if recipes:
        preview.info.append(
            _(
                "Přepočtou se suroviny v receptech ({count}): {recipes}. "
                "Cena a výživové údaje se mohou zaokrouhlením mírně změnit."
            ).format(count=len(recipes), recipes=", ".join(recipes))
        )
    rounded = article_rounded + sum(1 for line in preview.lines if line.rounded)
    if rounded:
        preview.info.append(
            _("Množství {count} položek se zaokrouhlí na 2 desetinná místa.").format(
                count=rounded
            )
        )
    if preview.document_differences:
        preview.info.append(
            _(
                "Celková cena {count} dokladů se zaokrouhlením změní, viz seznam níže. "
                "U schválených dokladů se změní i měsíční přehled."
            ).format(count=len(preview.document_differences))
        )
    preview.info.append(
        _("Již vytištěná nebo exportovaná PDF a tabulky zůstávají v původní jednotce.")
    )


def preview_article_change(article, new_unit, factor, source_note=""):
    related = _related_lines(article)
    preview = UnitChangePreview(
        kind=UnitChangeLog.Kind.ARTICLE,
        article=article,
        old_unit=article.unit,
        new_unit=new_unit,
        factor=quantize_factor(factor) if factor is not None else None,
    )
    preview.fingerprint = _request_fingerprint(
        _article_fingerprint(article, related), new_unit, preview.factor
    )
    preview.article_before = {name: getattr(article, name) for name in ARTICLE_FIELDS}
    if not _check_input(preview, source_note):
        return preview
    old_unit, factor = preview.old_unit, preview.factor
    after = dict(preview.article_before, unit=new_unit)
    article_rounded = 0
    for name in ("on_stock", "min_on_stock"):
        exact = preview.article_before[name] * factor
        after[name] = quantize_amount(exact)
        article_rounded += after[name] != exact
        if _exceeds(Article, name, after[name]):
            preview.blockers.append(
                _("Hodnota by přesáhla povolený počet číslic: {field}").format(
                    field=Article._meta.get_field(name).verbose_name
                )
            )
    if article.on_stock and not after["on_stock"]:
        preview.blockers.append(
            _("Stav skladu by se zaokrouhlil na 0, zvol menší jednotku.")
        )
    if new_unit == "ks" and old_unit != "ks":
        piece_weight = quantize_amount(BASE_SIZE[old_unit] / factor)
        if piece_weight < MIN_LINE_AMOUNT:
            preview.blockers.append(_("Hmotnost kusu by byla menší než 0.01."))
        elif _exceeds(Article, "piece_weight", piece_weight):
            preview.blockers.append(
                _("Hodnota by přesáhla povolený počet číslic: {field}").format(
                    field=Article._meta.get_field("piece_weight").verbose_name
                )
            )
        else:
            after["piece_weight"] = piece_weight
            after["piece_weight_unit"] = BASE_UNIT[DIMENSION[old_unit]]
    preview.article_after = after

    for kind, lines in related.items():
        for line in lines:
            change = _convert_line(kind, line, old_unit, new_unit, factor)
            if change.changed or change.broken:
                preview.lines.append(change)
    _line_blockers(preview)
    _document_differences(preview)
    _plausibility_warnings(preview, article, old_unit, new_unit, factor)
    _price_warning(preview, article, new_unit, factor)
    broken = sum(1 for line in preview.lines if line.broken)
    if broken:
        preview.warnings.append(
            _(
                "{count} řádků má jednotku, kterou nelze převést na {old} ani na {new}; "
                "jejich množství zůstane beze změny (viz report nesprávných jednotek)."
            ).format(count=broken, old=old_unit, new=new_unit)
        )
    _article_info(preview, article_rounded)
    _article_examples(preview)
    return preview


def preview_recipe_line_change(recipe_article, new_unit, factor, source_note=""):
    article = recipe_article.article
    preview = UnitChangePreview(
        kind=UnitChangeLog.Kind.RECIPE_LINE,
        article=article,
        old_unit=recipe_article.unit,
        new_unit=new_unit,
        factor=quantize_factor(factor) if factor is not None else None,
        recipe_article=recipe_article,
    )
    preview.fingerprint = _request_fingerprint(
        _recipe_line_fingerprint(recipe_article), new_unit, preview.factor
    )
    if not _check_input(preview, source_note):
        return preview
    if not convertible(new_unit, article.unit):
        preview.blockers.append(
            _(
                "Jednotku {unit} nelze převést na skladovou jednotku zboží {article_unit}."
            ).format(unit=new_unit, article_unit=article.unit)
        )
        return preview
    factor = preview.factor
    before = {
        "amount": recipe_article.amount,
        "unit": recipe_article.unit,
        "price": None,
    }
    exact = recipe_article.amount * factor
    after = dict(before, amount=quantize_amount(exact), unit=new_unit)
    change = LineChange(
        kind="recipe",
        line=recipe_article,
        before=before,
        after=after,
        rounded=after["amount"] != exact,
    )
    preview.lines.append(change)
    _line_blockers(preview)
    _plausibility_warnings(preview, article, preview.old_unit, new_unit, factor)
    if change.rounded:
        preview.info.append(_("Množství se zaokrouhlí na 2 desetinná místa."))
    preview.examples.append(
        (
            change.label,
            f"{before['amount']} {before['unit']}",
            f"{after['amount']} {after['unit']}",
        )
    )
    _recipe_comparison(preview, recipe_article, after)
    return preview


def _recipe_comparison(preview, recipe_article, after):
    recipe = recipe_article.recipe
    lines = list(
        RecipeArticle.objects.select_related("article").filter(recipe=recipe.pk)
    )
    target = next(line for line in lines if line.pk == recipe_article.pk)
    recipe.prefetched_recipe_articles = lines

    def snapshot():
        return recipe.total_recipe_articles_price, recipe.nutrition_per_portion

    cost_before, nutrition_before = snapshot()
    target.amount, target.unit = after["amount"], after["unit"]
    cost_after, nutrition_after = snapshot()
    del recipe.prefetched_recipe_articles
    currency = get_currency()
    preview.recipe_comparison.append(
        (
            _("Cena receptu s DPH"),
            f"{format_decimal(round(cost_before, 2))} {currency}",
            f"{format_decimal(round(cost_after, 2))} {currency}",
        )
    )
    for name in NUTRITION_FIELDS:
        unit = "kJ" if name == "energy" else "g"
        preview.recipe_comparison.append(
            (
                str(Article._meta.get_field(name).verbose_name),
                f"{nutrition_before[name]:.1f} {unit}",
                f"{nutrition_after[name]:.1f} {unit}",
            )
        )


def _check_apply(preview, fingerprint, confirmed):
    if preview.fingerprint != fingerprint:
        raise StaleUnitChangeError(
            _("Data nebo zadání se mezitím změnila, zkontroluj náhled znovu.")
        )
    if preview.blockers:
        raise UnitChangeError(preview.blockers)
    if preview.warnings and not confirmed:
        raise UnitChangeError(_("Potvrď, že jsi zkontroloval varování."))


def _write_lines(rows):
    """Write `(kind, line_id, state)` rows; only amount, unit and price change."""
    modified = timezone.now()
    states = defaultdict(dict)
    for kind, line_id, state in rows:
        states[kind][line_id] = state
    for kind, kind_states in states.items():
        model, price_field = LINE_MODELS[kind]
        lines = list(model.objects.filter(pk__in=list(kind_states)))
        for line in lines:
            state = kind_states[line.pk]
            line.amount = state["amount"]
            line.unit = state["unit"]
            if price_field:
                setattr(line, price_field, state["price"])
            line.modified = modified
        fields = ["amount", "unit", "modified"]
        if price_field:
            fields.append(price_field)
        model.objects.bulk_update(lines, fields)


def _write_article(article, state, reason, user):
    for name, value in state.items():
        setattr(article, name, value)
    reason_field = Article.history.model._meta.get_field("history_change_reason")
    article._change_reason = reason[: reason_field.max_length]
    article._history_user = user
    article.save()


def _change_reason(prefix, old_unit, new_unit, factor):
    return f"{prefix} {old_unit} -> {new_unit} (1 {old_unit} = {format_decimal(factor)} {new_unit})"


def _create_log(preview, source_note, user, details, recipe=None):
    return UnitChangeLog.objects.create(
        kind=preview.kind,
        article=preview.article,
        recipe=recipe,
        article_name=preview.article.article,
        old_unit=preview.old_unit,
        new_unit=preview.new_unit,
        factor=preview.factor,
        source_note=source_note.strip(),
        user=user,
        details=details,
    )


def _line_details(preview):
    return [
        {
            "model": change.kind,
            "id": change.line.pk,
            "before": _jsonable(change.before),
            "after": _jsonable(change.after),
        }
        for change in preview.lines
    ]


@transaction.atomic
def apply_article_change(
    article_id, new_unit, factor, source_note, user, fingerprint, confirmed=False
):
    article = Article.objects.get(pk=article_id)
    preview = preview_article_change(article, new_unit, factor, source_note)
    _check_apply(preview, fingerprint, confirmed)
    _write_lines(
        (change.kind, change.line.pk, change.after) for change in preview.lines
    )
    _write_article(
        article,
        preview.article_after,
        _change_reason(_("Změna jednotky"), article.unit, new_unit, preview.factor),
        user,
    )
    article = Article.objects.get(pk=article_id)
    details = {
        "article": {
            "before": _jsonable(preview.article_before),
            "after": _jsonable(preview.article_after),
        },
        "rows": _line_details(preview),
        "info": [str(message) for message in preview.info],
        "warnings": [str(message) for message in preview.warnings],
        "document_differences": [
            dict(entry, label=str(entry["label"]), difference=str(entry["difference"]))
            for entry in preview.document_differences
        ],
        "after_fingerprint": _article_fingerprint(article, _related_lines(article)),
    }
    return _create_log(preview, source_note, user, details)


@transaction.atomic
def apply_recipe_line_change(
    recipe_article_id, new_unit, factor, source_note, user, fingerprint, confirmed=False
):
    recipe_article = RecipeArticle.objects.select_related("article", "recipe").get(
        pk=recipe_article_id
    )
    preview = preview_recipe_line_change(recipe_article, new_unit, factor, source_note)
    _check_apply(preview, fingerprint, confirmed)
    _write_lines(
        (change.kind, change.line.pk, change.after) for change in preview.lines
    )
    recipe_article.refresh_from_db()
    details = {
        "rows": _line_details(preview),
        "info": [str(message) for message in preview.info],
        "warnings": [str(message) for message in preview.warnings],
        "after_fingerprint": _recipe_line_fingerprint(recipe_article),
    }
    return _create_log(
        preview, source_note, user, details, recipe=recipe_article.recipe
    )


def _current_fingerprint(log):
    if log.kind == UnitChangeLog.Kind.ARTICLE:
        article = Article.objects.filter(pk=log.article_id).first()
        if article is None:
            return None
        return _article_fingerprint(article, _related_lines(article))
    rows = log.details.get("rows") or [{}]
    recipe_article = (
        RecipeArticle.objects.select_related("article")
        .filter(pk=rows[0].get("id"))
        .first()
    )
    return None if recipe_article is None else _recipe_line_fingerprint(recipe_article)


def undo_blocker(log):
    """Return why the change cannot be undone exactly, or None."""
    if log.kind == UnitChangeLog.Kind.UNDO:
        return _("Vrácení změny nelze vrátit, proveď nový převod.")
    if UnitChangeLog.objects.filter(undo_of=log).exists():
        return _("Změna již byla vrácena.")
    if log.article_id is None:
        return _("Zboží již neexistuje.")
    if (
        log.kind == UnitChangeLog.Kind.ARTICLE
        and UnitChangeLog.objects.filter(
            article_id=log.article_id, pk__gt=log.pk
        ).exists()
    ):
        return _("Po této změně následovala další změna jednotky.")
    if _current_fingerprint(log) != log.details.get("after_fingerprint"):
        return _(
            "Data se od změny upravila (pohyby na skladu, doklady nebo recepty). "
            "Použij zpětný převod."
        )
    return None


def recipe_unit_changed_since(recipe_article, marker):
    if not recipe_article.pk:
        return False
    return (
        UnitChangeLog.objects.filter(
            recipe_id=recipe_article.recipe_id,
            pk__gt=marker,
            details__rows__0__id=recipe_article.pk,
        )
        .filter(
            Q(kind=UnitChangeLog.Kind.RECIPE_LINE)
            | Q(
                kind=UnitChangeLog.Kind.UNDO,
                undo_of__kind=UnitChangeLog.Kind.RECIPE_LINE,
            )
        )
        .exists()
    )


@transaction.atomic
def undo_change(log_id, user):
    log = UnitChangeLog.objects.select_related("article", "recipe").get(pk=log_id)
    blocker = undo_blocker(log)
    if blocker:
        raise UnitChangeError(blocker)
    rows = log.details.get("rows", [])
    _write_lines((row["model"], row["id"], _from_json(row["before"])) for row in rows)
    details = {
        "rows": [dict(row, before=row["after"], after=row["before"]) for row in rows]
    }
    if log.kind == UnitChangeLog.Kind.ARTICLE:
        states = log.details["article"]
        _write_article(
            log.article,
            _from_json(states["before"]),
            _change_reason(
                _("Vrácení změny jednotky"),
                log.new_unit,
                log.old_unit,
                quantize_factor(1 / log.factor),
            ),
            user,
        )
        details["article"] = {"before": states["after"], "after": states["before"]}
    return UnitChangeLog.objects.create(
        kind=UnitChangeLog.Kind.UNDO,
        article=log.article,
        recipe=log.recipe,
        article_name=log.article_name,
        old_unit=log.new_unit,
        new_unit=log.old_unit,
        factor=quantize_factor(1 / log.factor),
        source_note=_("Vrácení změny #{id}").format(id=log.pk),
        user=user,
        details=details,
        undo_of=log,
    )
