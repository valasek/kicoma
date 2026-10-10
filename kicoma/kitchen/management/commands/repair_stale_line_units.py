"""Convert lines left in an old unit by an unmanaged article unit change.

The amount and unit price of such a line still refer to the line unit, so both are
converted with `1 line_unit = factor article units`; line totals stay the same up
to rounding. Without --apply only a dry run is printed.
"""

from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from kicoma.kitchen.models import UNIT, Article
from kicoma.kitchen.unit_change import (
    LINE_MODELS,
    MAX_FACTOR,
    MIN_LINE_AMOUNT,
    _write_lines,
    convertible,
    quantize_amount,
    quantize_price,
)

DOCUMENT = {
    "recipe": ("recipe", "recipe_id"),
    "receipt": ("stock_receipt", "stock_receipt_id"),
    "issue": ("stock_issue", "stock_issue_id"),
}


class Command(BaseCommand):
    help = "Convert recipe, receipt and issue lines whose unit no longer fits the article unit."

    def add_arguments(self, parser):
        parser.add_argument("article_id", type=int)
        parser.add_argument("line_unit", choices=[code for code, _label in UNIT])
        parser.add_argument("factor", help="1 line_unit = factor article units")
        parser.add_argument(
            "--apply", action="store_true", help="write the changes (default: dry run)"
        )

    def handle(self, *args, **options):
        line_unit = options["line_unit"]
        try:
            factor = Decimal(options["factor"])
        except InvalidOperation as err:
            raise CommandError(f"Invalid factor {options['factor']!r}") from err
        if not 0 < factor < MAX_FACTOR:
            raise CommandError(f"Factor must be between 0 and {MAX_FACTOR}")
        article = Article.objects.filter(pk=options["article_id"]).first()
        if article is None:
            raise CommandError(f"Article {options['article_id']} does not exist")
        if convertible(line_unit, article.unit):
            raise CommandError(
                f"{line_unit} lines of {article} are not stale, article unit is {article.unit}"
            )

        rows = []
        for kind, (model, price_field) in LINE_MODELS.items():
            document, document_id = DOCUMENT[kind]
            lines = (
                model.objects.select_related(
                    document, *(("vat",) if kind == "receipt" else ())
                )
                .filter(article=article, unit=line_unit)
                .order_by(document_id, "pk")
            )
            for line in lines:
                amount = quantize_amount(line.amount * factor)
                if amount < MIN_LINE_AMOUNT:
                    raise CommandError(
                        f"{kind} line {line.pk}: amount would be {amount}"
                    )
                state = {"amount": amount, "unit": article.unit, "price": None}
                approved = getattr(getattr(line, document), "approved", None)
                text = (
                    f"{kind} #{getattr(line, document_id)}"
                    f"{' (approved)' if approved else ''} line {line.pk}: "
                    f"{line.amount} {line_unit} -> {amount} {article.unit}"
                )
                price = getattr(line, price_field) if price_field else None
                if price is not None:
                    state["price"] = quantize_price(price / factor)
                    vat = (
                        1 + line.vat.percentage / Decimal(100)
                        if kind == "receipt"
                        else 1
                    )
                    before = round(price * vat * line.amount, 0)
                    after = round(state["price"] * vat * amount, 0)
                    text += f", price {price} -> {state['price']}, total {before} -> {after}"
                rows.append((kind, line.pk, state))
                self.stdout.write(text)

        if not rows:
            self.stdout.write(f"No {line_unit} lines of {article}")
            return
        if not options["apply"]:
            self.stdout.write(f"Dry run: {len(rows)} lines, use --apply to write")
            return
        with transaction.atomic():
            _write_lines(rows)
        self.stdout.write(
            self.style.SUCCESS(f"Converted {len(rows)} lines of {article}")
        )
