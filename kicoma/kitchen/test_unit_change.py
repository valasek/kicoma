from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from tablib import Dataset

from kicoma.kitchen.forms import (
    ArticleForm,
    RecipeArticleForm,
    StockIssueArticleForm,
    StockReceiptArticleForm,
    UnitChangeForm,
)
from kicoma.kitchen.models import (
    VAT,
    Article,
    Recipe,
    RecipeArticle,
    StockIssue,
    StockIssueArticle,
    StockReceipt,
    StockReceiptArticle,
    UnitChangeLog,
)
from kicoma.kitchen.unit_change import (
    StaleUnitChangeError,
    UnitChangeError,
    apply_article_change,
    apply_recipe_line_change,
    preview_article_change,
    preview_recipe_line_change,
    undo_blocker,
    undo_change,
    unit_factor,
)
from kicoma.kitchen.views import IncorrectUnitsListView, stock_issues_receipts_data


def make_user(username, roles=(), superuser=False):
    user = get_user_model().objects.create_user(
        username, f"{username}@example.com", "password", is_superuser=superuser
    )
    for role in roles:
        group, _created = Group.objects.get_or_create(name=role)
        user.groups.add(group)
    return user


class UnitChangeFixtureMixin:
    def setUp(self):
        self.user = make_user("keeper", ("stockkeeper", "cook", "nutrition_advisor"))
        self.today = timezone.localdate()
        self.vat0 = VAT.objects.create(percentage=0, rate="zero")
        self.vat21 = VAT.objects.create(percentage=21, rate="standard")
        self.article = Article.objects.create(
            article="Taveny syr",
            unit="ks",
            on_stock=Decimal("10"),
            min_on_stock=Decimal("2"),
            total_price=Decimal("100"),
            piece_weight=Decimal("42"),
            piece_weight_unit="g",
        )
        self.recipe = Recipe.objects.create(recipe="Toast", norm_amount=4)
        self.recipe_pieces = RecipeArticle.objects.create(
            recipe=self.recipe, article=self.article, amount=2, unit="ks"
        )
        self.other_recipe = Recipe.objects.create(recipe="Omacka", norm_amount=2)
        self.recipe_grams = RecipeArticle.objects.create(
            recipe=self.other_recipe, article=self.article, amount=100, unit="g"
        )
        self.approved_receipt = StockReceipt.objects.create(
            user_created=self.user,
            approved=True,
            date_approved=self.today,
            user_approved=self.user,
        )
        self.approved_receipt_line = StockReceiptArticle.objects.create(
            stock_receipt=self.approved_receipt,
            article=self.article,
            amount=10,
            unit="ks",
            price_without_vat=Decimal("8.2645"),
            vat=self.vat21,
        )
        self.open_receipt = StockReceipt.objects.create(user_created=self.user)
        self.open_receipt_line = StockReceiptArticle.objects.create(
            stock_receipt=self.open_receipt,
            article=self.article,
            amount=5,
            unit="ks",
            price_without_vat=Decimal("10"),
            vat=self.vat0,
        )
        self.approved_issue = StockIssue.objects.create(
            user_created=self.user,
            approved=True,
            date_approved=self.today,
            user_approved=self.user,
        )
        self.approved_issue_line = StockIssueArticle.objects.create(
            stock_issue=self.approved_issue,
            article=self.article,
            amount=3,
            unit="ks",
            average_unit_price=Decimal("10"),
        )
        self.open_issue = StockIssue.objects.create(user_created=self.user)
        self.open_issue_line = StockIssueArticle.objects.create(
            stock_issue=self.open_issue,
            article=self.article,
            amount=1,
            unit="ks",
            average_unit_price=Decimal("10"),
        )

    def convert(self, new_unit="kg", factor="0.042", note="etiketa 42 g", **kwargs):
        article = Article.objects.get(pk=self.article.pk)
        preview = preview_article_change(article, new_unit, Decimal(factor), note)
        return apply_article_change(
            article.pk,
            new_unit,
            Decimal(factor),
            note,
            self.user,
            preview.fingerprint,
            kwargs.get("confirmed", True),
        )

    def line_state(self):
        return {
            "article": Article.objects.filter(pk=self.article.pk)
            .values(
                "unit",
                "on_stock",
                "min_on_stock",
                "total_price",
                "piece_weight",
                "piece_weight_unit",
            )
            .get(),
            "recipe": list(
                RecipeArticle.objects.order_by("pk").values_list("amount", "unit")
            ),
            "receipt": list(
                StockReceiptArticle.objects.order_by("pk").values_list(
                    "amount", "unit", "price_without_vat"
                )
            ),
            "issue": list(
                StockIssueArticle.objects.order_by("pk").values_list(
                    "amount", "unit", "average_unit_price"
                )
            ),
        }


class ArticleUnitChangeServiceTests(UnitChangeFixtureMixin, TestCase):
    def test_piece_to_kilogram_converts_stock_recipes_and_all_documents(self):
        history_before = list(
            self.article.history.order_by("history_id").values_list(
                "history_id", "unit", "on_stock"
            )
        )

        log = self.convert()

        article = Article.objects.get(pk=self.article.pk)
        self.assertEqual(article.unit, "kg")
        self.assertEqual(article.on_stock, Decimal("0.42"))
        self.assertEqual(article.min_on_stock, Decimal("0.08"))
        self.assertEqual(article.total_price, Decimal("100"))
        self.recipe_pieces.refresh_from_db()
        self.assertEqual(
            (self.recipe_pieces.amount, self.recipe_pieces.unit),
            (Decimal("0.08"), "kg"),
        )
        # 100 g could not be converted to ks before; now it fits the stock unit as is
        self.recipe_grams.refresh_from_db()
        self.assertEqual(
            (self.recipe_grams.amount, self.recipe_grams.unit), (Decimal("100"), "g")
        )
        line = StockReceiptArticle.objects.get(pk=self.approved_receipt_line.pk)
        self.assertEqual((line.amount, line.unit), (Decimal("0.42"), "kg"))
        self.assertEqual(line.price_without_vat, Decimal("196.7738"))
        issue_line = StockIssueArticle.objects.get(pk=self.approved_issue_line.pk)
        self.assertEqual((issue_line.amount, issue_line.unit), (Decimal("0.13"), "kg"))
        self.assertEqual(issue_line.average_unit_price, Decimal("238.0952"))
        open_line = StockReceiptArticle.objects.get(pk=self.open_receipt_line.pk)
        self.assertEqual(open_line.price_without_vat, Decimal("238.0952"))

        receipt = StockReceipt.objects.get(pk=self.approved_receipt.pk)
        self.assertTrue(receipt.approved)
        self.assertEqual(receipt.date_approved, self.today)
        self.assertEqual(receipt.user_approved, self.user)
        self.assertFalse(StockIssue.objects.get(pk=self.open_issue.pk).approved)

        self.assertEqual(log.kind, UnitChangeLog.Kind.ARTICLE)
        self.assertEqual((log.old_unit, log.new_unit), ("ks", "kg"))
        self.assertEqual(log.factor, Decimal("0.042"))
        self.assertEqual(log.source_note, "etiketa 42 g")
        self.assertEqual(log.user, self.user)
        self.assertEqual(len(log.details["rows"]), 5)
        self.assertEqual(log.details["article"]["before"]["on_stock"], "10.00")

        history = list(
            article.history.order_by("history_id").values_list(
                "history_id", "unit", "on_stock"
            )
        )
        self.assertEqual(history[: len(history_before)], history_before)
        latest = article.history.latest("history_id")
        self.assertIn("ks -> kg", latest.history_change_reason)
        self.assertEqual(latest.history_user, self.user)

    def test_totals_reports_and_incorrect_units_stay_consistent(self):
        before = stock_issues_receipts_data(0)
        preview = preview_article_change(
            self.article, "kg", Decimal("0.042"), "etiketa"
        )
        approved_difference = sum(
            entry["difference"]
            for entry in preview.document_differences
            if entry["approved"]
        )

        self.convert()

        after = stock_issues_receipts_data(0)
        self.assertEqual(after["stock_receipts_price"], before["stock_receipts_price"])
        # 3 ks -> 0.126 kg is rounded to 0.13 kg; the preview lists the difference
        self.assertEqual(approved_difference, Decimal("1"))
        self.assertEqual(
            after["stock_issues_price"] - before["stock_issues_price"],
            approved_difference,
        )
        self.assertEqual(
            IncorrectUnitsListView.get_incorrect_articles(
                StockIssueArticle.objects.all()
            ),
            [],
        )
        self.assertEqual(
            IncorrectUnitsListView.get_incorrect_articles(
                StockReceiptArticle.objects.all()
            ),
            [],
        )

    def test_preview_does_not_write_and_reports_information(self):
        state = self.line_state()

        preview = preview_article_change(
            self.article, "kg", Decimal("0.042"), "etiketa"
        )

        self.assertEqual(self.line_state(), state)
        self.assertEqual(preview.blockers, [])
        self.assertEqual(preview.warnings, [])
        self.assertEqual(len(preview.approved_document_lines), 2)
        self.assertEqual(len(preview.open_document_lines), 2)
        self.assertEqual(preview.reverse_factor, Decimal("23.809524"))
        self.assertTrue(any("1 naskladněné" in message for message in preview.info))

    def test_kilogram_to_gram_keeps_lines_and_divides_prices(self):
        self.convert()
        log = self.convert(new_unit="g", factor="1000", note="kg -> g")

        self.assertEqual(log.factor, Decimal("1000"))
        line = StockReceiptArticle.objects.get(pk=self.approved_receipt_line.pk)
        self.assertEqual((line.amount, line.unit), (Decimal("0.42"), "kg"))
        self.assertEqual(line.price_without_vat, Decimal("0.1968"))
        self.assertEqual(Article.objects.get(pk=self.article.pk).on_stock, 420)
        self.assertEqual(unit_factor("kg", "g"), (Decimal(1000), True))

    def test_weight_to_pieces_sets_piece_weight(self):
        article = Article.objects.create(
            article="Mouka", unit="kg", on_stock=Decimal("2"), total_price=40
        )

        log = apply_article_change(
            article.pk,
            "ks",
            Decimal("4"),
            "balení 250 g",
            self.user,
            preview_article_change(article, "ks", Decimal("4"), "x").fingerprint,
        )

        article.refresh_from_db()
        self.assertEqual(article.unit, "ks")
        self.assertEqual(article.on_stock, Decimal("8"))
        self.assertEqual(
            (article.piece_weight, article.piece_weight_unit), (Decimal("250"), "g")
        )
        self.assertEqual(log.new_unit, "ks")

    def test_piece_weight_overflow_is_a_blocker(self):
        article = Article.objects.create(article="Mouka", unit="kg")

        preview = preview_article_change(article, "ks", Decimal("0.000001"), "x")

        self.assertTrue(any("číslic" in blocker for blocker in preview.blockers))

    def test_piece_weight_suggests_factor(self):
        self.assertEqual(
            unit_factor("ks", "g", self.article), (Decimal("42.000000"), False)
        )
        self.assertEqual(
            unit_factor("ks", "kg", self.article), (Decimal("0.042000"), False)
        )
        self.assertEqual(unit_factor("ks", "ml", self.article), (None, False))

    def test_warnings(self):
        cases = (
            ("name hint", "Jogurt 150g", None, "kg", "0.2", "Název zboží"),
            ("multipack", "Jogurt 4x125g", None, "g", "300", "Název zboží"),
            ("piece weight", "Syr", Decimal("42"), "g", "50", "hmotnosti kusu"),
            ("piece range", "Hrozinky", None, "g", "0.5", "mimo obvyklý rozsah"),
            ("density", "Olej", None, "l", "5", "Hustota"),
            ("price", "Koreni", None, "g", "1", "průměrná cena"),
        )
        for name, article_name, piece_weight, new_unit, factor, expected in cases:
            with self.subTest(name):
                unit = "kg" if name == "density" else "ks"
                article = Article.objects.create(
                    article=article_name,
                    unit=unit,
                    on_stock=1,
                    total_price=10,
                    piece_weight=piece_weight,
                    piece_weight_unit="g" if piece_weight else None,
                )
                preview = preview_article_change(
                    article, new_unit, Decimal(factor), "note"
                )
                self.assertTrue(
                    any(expected in warning for warning in preview.warnings),
                    preview.warnings,
                )
                article.delete()

    def test_multipack_name_hint_accepts_single_piece_or_pack(self):
        article = Article.objects.create(article="Jogurt 4x125g", unit="ks")

        for factor in ("125", "500"):
            preview = preview_article_change(article, "g", Decimal(factor), "x")
            self.assertEqual(preview.warnings, [])

    def test_broken_lines_are_left_unchanged_with_warning(self):
        self.recipe_grams.unit = "ml"
        self.recipe_grams.save()

        preview = preview_article_change(self.article, "kg", Decimal("0.042"), "x")

        self.assertTrue(any("nelze převést" in w for w in preview.warnings))
        broken = [line for line in preview.lines if line.broken]
        self.assertEqual([line.line.pk for line in broken], [self.recipe_grams.pk])

    def test_broken_document_line_keeps_its_price(self):
        self.approved_issue_line.unit = "l"
        self.approved_issue_line.save()

        preview = preview_article_change(self.article, "kg", Decimal("0.042"), "x")

        broken = next(line for line in preview.lines if line.broken)
        self.assertEqual(broken.line.pk, self.approved_issue_line.pk)
        self.assertEqual(broken.after, broken.before)

    def test_warnings_require_confirmation(self):
        with self.assertRaises(UnitChangeError):
            self.convert(factor="0.05", confirmed=False)
        self.assertEqual(Article.objects.get(pk=self.article.pk).unit, "ks")

        self.convert(factor="0.05", confirmed=True)
        self.assertEqual(Article.objects.get(pk=self.article.pk).unit, "kg")

    def test_blockers(self):
        cases = (
            ("same unit", "ks", "1", "note", "stejná"),
            ("missing factor", "kg", None, "note", "větší než 0"),
            ("negative factor", "kg", "-1", "note", "větší než 0"),
            ("empty note", "kg", "0.042", "  ", "zdroj koeficientu"),
            ("below minimum", "kg", "0.001", "note", "pod 0.01"),
            ("overflow", "g", "999999", "note", "počet číslic"),
        )
        for name, new_unit, factor, note, expected in cases:
            with self.subTest(name):
                preview = preview_article_change(
                    self.article,
                    new_unit,
                    Decimal(factor) if factor is not None else None,
                    note,
                )
                self.assertTrue(
                    any(expected in blocker.lower() for blocker in preview.blockers),
                    preview.blockers,
                )
                with self.assertRaises(UnitChangeError):
                    apply_article_change(
                        self.article.pk,
                        new_unit,
                        Decimal(factor) if factor is not None else None,
                        note,
                        self.user,
                        preview.fingerprint,
                        True,
                    )

    def test_zero_price_is_a_blocker(self):
        self.open_issue_line.average_unit_price = Decimal("0.0002")
        self.open_issue_line.save()

        preview = preview_article_change(self.article, "kg", Decimal("1000"), "x")

        self.assertTrue(any("na 0" in blocker for blocker in preview.blockers))

    def test_stale_fingerprint_is_rejected(self):
        preview = preview_article_change(self.article, "kg", Decimal("0.042"), "x")
        self.open_receipt_line.amount = 6
        self.open_receipt_line.save()

        with self.assertRaises(StaleUnitChangeError):
            apply_article_change(
                self.article.pk,
                "kg",
                Decimal("0.042"),
                "x",
                self.user,
                preview.fingerprint,
                True,
            )
        self.assertEqual(Article.objects.get(pk=self.article.pk).unit, "ks")

    def test_changed_factor_after_preview_is_rejected(self):
        preview = preview_article_change(self.article, "kg", Decimal("0.042"), "x")

        with self.assertRaises(StaleUnitChangeError):
            apply_article_change(
                self.article.pk,
                "kg",
                Decimal("0.05"),
                "x",
                self.user,
                preview.fingerprint,
                True,
            )

    def test_preview_rejects_changed_approval_without_timestamp(self):
        preview = preview_article_change(self.article, "kg", Decimal("0.042"), "x")
        StockReceipt.objects.filter(pk=self.open_receipt.pk).update(
            approved=True, date_approved=self.today, user_approved=self.user
        )
        with self.assertRaises(StaleUnitChangeError):
            apply_article_change(
                self.article.pk,
                "kg",
                Decimal("0.042"),
                "x",
                self.user,
                preview.fingerprint,
                True,
            )
        self.assertFalse(UnitChangeLog.objects.exists())

    def test_error_rolls_back_everything(self):
        state = self.line_state()

        with (
            patch(
                "kicoma.kitchen.unit_change._write_article",
                side_effect=RuntimeError("boom"),
            ),
            self.assertRaises(RuntimeError),
        ):
            self.convert()

        self.assertEqual(self.line_state(), state)
        self.assertFalse(UnitChangeLog.objects.exists())

    def test_undo_restores_exact_values(self):
        state = self.line_state()
        log = self.convert()

        undo = undo_change(log.pk, self.user)

        self.assertEqual(self.line_state(), state)
        self.assertEqual(undo.kind, UnitChangeLog.Kind.UNDO)
        self.assertEqual(undo.undo_of, log)
        self.assertEqual((undo.old_unit, undo.new_unit), ("kg", "ks"))
        self.assertTrue(StockReceipt.objects.get(pk=self.approved_receipt.pk).approved)
        self.assertIsNotNone(undo_blocker(log))
        self.assertIsNotNone(undo_blocker(undo))

    def test_undo_is_refused_after_price_update_without_timestamp(self):
        log = self.convert()
        StockReceiptArticle.objects.filter(pk=self.open_receipt_line.pk).update(
            price_without_vat=Decimal("999")
        )

        with self.assertRaises(UnitChangeError):
            undo_change(log.pk, self.user)

        self.assertEqual(
            StockReceiptArticle.objects.get(
                pk=self.open_receipt_line.pk
            ).price_without_vat,
            Decimal("999"),
        )

    def test_undo_is_refused_after_data_change(self):
        log = self.convert()
        line = StockReceiptArticle.objects.get(pk=self.open_receipt_line.pk)
        line.comment = "edited"
        line.save()

        self.assertIsNotNone(undo_blocker(log))
        with self.assertRaises(UnitChangeError):
            undo_change(log.pk, self.user)

    def test_undo_is_refused_after_later_conversion(self):
        first = self.convert()
        self.convert(new_unit="g", factor="1000", note="g")

        self.assertIn("další změna", undo_blocker(first))

    def test_undo_is_refused_when_new_lines_exist(self):
        log = self.convert()
        StockReceiptArticle.objects.create(
            stock_receipt=self.open_receipt,
            article=self.article,
            amount=1,
            unit="kg",
            price_without_vat=200,
            vat=self.vat0,
        )

        self.assertIsNotNone(undo_blocker(log))


class RecipeLineUnitChangeServiceTests(UnitChangeFixtureMixin, TestCase):
    def test_preview_rejects_changed_recipe_pricing(self):
        preview = preview_recipe_line_change(self.line, "g", Decimal("150"), "x")
        Article.objects.filter(pk=self.kg_article.pk).update(total_price=60)
        with self.assertRaises(StaleUnitChangeError):
            apply_recipe_line_change(
                self.line.pk,
                "g",
                Decimal("150"),
                "x",
                self.user,
                preview.fingerprint,
                True,
            )
        self.assertFalse(UnitChangeLog.objects.exists())

    def test_smallest_factor_undo_log_can_be_read(self):
        self.recipe_grams.amount = Decimal("10000")
        self.recipe_grams.save()
        factor = Decimal("0.000001")
        preview = preview_recipe_line_change(self.recipe_grams, "ks", factor, "pack")
        self.assertFalse(preview.blockers)
        log = apply_recipe_line_change(
            self.recipe_grams.pk,
            "ks",
            factor,
            "pack",
            self.user,
            preview.fingerprint,
            True,
        )
        undone = undo_change(log.pk, self.user)
        undone.refresh_from_db()
        self.assertEqual(undone.factor, Decimal("1000000"))
        self.recipe_grams.refresh_from_db()
        self.assertEqual(self.recipe_grams.amount, Decimal("10000"))

    def setUp(self):
        super().setUp()
        self.kg_article = Article.objects.create(
            article="Cibule", unit="kg", on_stock=1, total_price=30
        )
        self.line = RecipeArticle.objects.create(
            recipe=self.recipe, article=self.kg_article, amount=2, unit="ks"
        )

    def test_converts_one_line_and_logs_it(self):
        preview = preview_recipe_line_change(self.line, "g", Decimal("150"), "1 ks")
        self.assertEqual(preview.blockers, [])
        self.assertEqual(preview.recipe_comparison[0][1:], ("20 Kč", "29 Kč"))

        log = apply_recipe_line_change(
            self.line.pk, "g", Decimal("150"), "1 ks", self.user, preview.fingerprint
        )

        self.line.refresh_from_db()
        self.assertEqual((self.line.amount, self.line.unit), (Decimal("300"), "g"))
        self.assertEqual(log.kind, UnitChangeLog.Kind.RECIPE_LINE)
        self.assertEqual(log.recipe, self.recipe)
        self.recipe_pieces.refresh_from_db()
        self.assertEqual(self.recipe_pieces.unit, "ks")

        undo_change(log.pk, self.user)
        self.line.refresh_from_db()
        self.assertEqual((self.line.amount, self.line.unit), (Decimal("2"), "ks"))

    def test_target_unit_must_fit_the_article(self):
        preview = preview_recipe_line_change(self.line, "ml", Decimal("150"), "x")

        self.assertTrue(any("nelze převést" in b for b in preview.blockers))


class UnitChangeFormTests(UnitChangeFixtureMixin, TestCase):
    def test_recipe_form_renders_conversion_marker(self):
        from crispy_forms.utils import render_crispy_form

        form = RecipeArticleForm(instance=self.recipe_pieces)
        self.assertIn('name="unit_change_marker"', render_crispy_form(form))

    def test_stale_recipe_form_is_rejected_after_conversion(self):
        for kind in ("article", "recipe_line"):
            with self.subTest(kind=kind):
                line = RecipeArticle.objects.get(pk=self.recipe_pieces.pk)
                data = dict(RecipeArticleForm(instance=line).initial)
                data["unit_change_marker"] = (
                    UnitChangeLog.objects.order_by("-pk")
                    .values_list("pk", flat=True)
                    .first()
                    or 0
                )
                if kind == "article":
                    self.convert()
                else:
                    preview = preview_recipe_line_change(
                        line, "g", Decimal(1000), "fixed"
                    )
                    apply_recipe_line_change(
                        line.pk,
                        "g",
                        Decimal(1000),
                        "fixed",
                        self.user,
                        preview.fingerprint,
                        True,
                    )
                form = RecipeArticleForm(
                    data, instance=RecipeArticle.objects.get(pk=line.pk)
                )
                self.assertFalse(form.is_valid())
                self.assertTrue(form.non_field_errors())

    def test_stale_article_form_cannot_overwrite_converted_stock(self):
        original = ArticleForm(instance=self.article, user=self.user)
        data = dict(original.initial, unit_change_marker=0)
        self.convert()
        form = ArticleForm(
            data,
            instance=Article.objects.get(pk=self.article.pk),
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_fixed_pair_locks_the_factor(self):
        form = UnitChangeForm(
            {"new_unit": "g", "factor": "5", "source_note": "x"},
            old_unit="kg",
            unit_choices=["kg", "g", "ks"],
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["factor"], Decimal(1000))

    def test_other_pairs_need_a_factor(self):
        form = UnitChangeForm(
            {"new_unit": "kg", "source_note": "x"},
            old_unit="ks",
            unit_choices=["kg", "ks"],
        )

        self.assertFalse(form.is_valid())
        self.assertIn("factor", form.errors)

    def test_stale_receipt_line_form_is_rejected(self):
        form = StockReceiptArticleForm()
        marker = form.fields["unit_change_marker"].initial
        self.convert()
        data = {
            "article": self.article.pk,
            "amount": "1",
            "unit": "kg",
            "price_without_vat": "100",
            "vat": self.vat0.pk,
            "unit_change_marker": marker,
        }

        form = StockReceiptArticleForm(data)

        self.assertFalse(form.is_valid())
        self.assertIn("zadej řádek znovu", str(form.non_field_errors()))
        form = StockReceiptArticleForm(form.data)
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)
        self.assertIn("price_without_vat", form.errors)
        data = form.data.copy()
        data.update(amount="1", unit="kg", price_without_vat="100")
        form = StockReceiptArticleForm(data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_marker_cannot_bypass_conversion_guard(self):
        self.convert()
        for form_class in (StockReceiptArticleForm, StockIssueArticleForm):
            with self.subTest(form=form_class.__name__):
                form = form_class(
                    {
                        "article": self.article.pk,
                        "amount": "1",
                        "unit": "kg",
                        "price_without_vat": "10",
                        "vat": self.vat0.pk,
                    }
                )
                self.assertFalse(form.is_valid())
                self.assertTrue(form.non_field_errors())

    def test_stale_issue_line_form_is_rejected(self):
        marker = StockIssueArticleForm().fields["unit_change_marker"].initial
        self.convert()

        form = StockIssueArticleForm(
            {
                "article": self.article.pk,
                "amount": "1",
                "unit": "kg",
                "unit_change_marker": marker,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("zadej řádek znovu", str(form.non_field_errors()))

    def test_article_choices_show_stock_unit(self):
        form = StockReceiptArticleForm()

        labels = [label for _value, label in form.fields["article"].choices]
        self.assertIn("Taveny syr [ks]", labels)


class UnitChangeViewTests(UnitChangeFixtureMixin, TestCase):
    def test_incorrect_units_report_links_respect_roles(self):
        StockReceiptArticle.objects.filter(pk=self.open_receipt_line.pk).update(
            unit="g"
        )
        StockIssueArticle.objects.filter(pk=self.approved_issue_line.pk).update(
            unit="g"
        )
        article_url = reverse("kitchen:changeArticleUnit", args=[self.article.pk])
        recipe_url = reverse(
            "kitchen:changeRecipeArticleUnit", args=[self.recipe_grams.pk]
        )
        cases = (
            ("cook", False, True, False),
            ("stockkeeper", False, False, True),
            ("nutrition_advisor", False, True, True),
            ("root", True, True, True),
        )
        for role, superuser, recipe_allowed, article_allowed in cases:
            with self.subTest(role=role):
                user = make_user(
                    role, () if superuser else (role,), superuser=superuser
                )
                self.client.force_login(user)
                response = self.client.get(reverse("kitchen:showIncorrectUnits"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response, f'href="{recipe_url}"', count=int(recipe_allowed)
                )
                self.assertContains(
                    response, f'href="{article_url}"', count=3 if article_allowed else 0
                )
                if recipe_allowed:
                    self.assertContains(response, "Změnit jednotku suroviny")

    def post_change(self, action, **extra):
        data = {
            "new_unit": "kg",
            "factor": "0.042",
            "source_note": "etiketa 42 g",
            "action": action,
            **extra,
        }
        return self.client.post(
            reverse("kitchen:changeArticleUnit", args=[self.article.pk]), data
        )

    def test_roles(self):
        article_url = reverse("kitchen:changeArticleUnit", args=[self.article.pk])
        recipe_url = reverse(
            "kitchen:changeRecipeArticleUnit", args=[self.recipe_pieces.pk]
        )
        cases = (
            (("cook",), 403, 200),
            (("stockkeeper",), 200, 403),
            (("nutrition_advisor",), 200, 200),
        )
        for roles, article_status, recipe_status in cases:
            with self.subTest(roles=roles):
                self.client.force_login(make_user("_".join(roles), roles))
                self.assertEqual(
                    self.client.get(article_url).status_code, article_status
                )
                self.assertEqual(self.client.get(recipe_url).status_code, recipe_status)
        self.client.force_login(make_user("root", superuser=True))
        self.assertEqual(self.client.get(article_url).status_code, 200)
        self.assertEqual(self.client.get(recipe_url).status_code, 200)
        self.client.force_login(make_user("norole"))
        self.assertEqual(
            self.client.get(reverse("kitchen:showUnitManagement")).status_code, 403
        )

    def test_preview_then_apply(self):
        self.client.force_login(self.user)

        response = self.post_change("preview")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Article.objects.get(pk=self.article.pk).unit, "ks")
        preview = response.context["preview"]
        self.assertEqual(preview.blockers, [])

        response = self.post_change("apply", fingerprint=preview.fingerprint)

        self.assertRedirects(response, reverse("kitchen:showArticles"))
        self.assertEqual(Article.objects.get(pk=self.article.pk).unit, "kg")
        response = self.client.get(reverse("kitchen:showUnitManagement"))
        self.assertTrue(response.context["logs"][0][1])
        self.assertContains(response, "etiketa 42 g")

    def test_apply_without_preview_only_renders_preview(self):
        self.client.force_login(self.user)

        response = self.post_change("apply")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Article.objects.get(pk=self.article.pk).unit, "ks")
        self.assertIsNotNone(response.context["preview"])

    def test_recipe_line_without_other_unit_points_to_article_change(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("kitchen:changeRecipeArticleUnit", args=[self.recipe_pieces.pk])
        )

        self.assertNotContains(response, 'name="action"')
        self.assertContains(
            response, reverse("kitchen:changeArticleUnit", args=[self.article.pk])
        )

    def test_recipe_line_preview_then_apply(self):
        self.client.force_login(self.user)
        article = Article.objects.create(article="Cibule", unit="kg")
        line = RecipeArticle.objects.create(
            recipe=self.recipe, article=article, amount=2, unit="ks"
        )
        url = reverse("kitchen:changeRecipeArticleUnit", args=[line.pk])
        data = {"new_unit": "g", "factor": "30000", "source_note": "x"}

        response = self.client.post(url, {**data, "action": "preview"})

        preview = response.context["preview"]
        self.assertIn("Varování", response.content.decode())
        self.assertIn("confirmed", response.content.decode())
        response = self.client.post(
            url,
            {
                **data,
                "action": "apply",
                "fingerprint": preview.fingerprint,
                "confirmed": "on",
            },
        )

        self.assertRedirects(
            response, reverse("kitchen:showRecipeArticles", args=[self.recipe.pk])
        )
        line.refresh_from_db()
        self.assertEqual((line.amount, line.unit), (Decimal("60000"), "g"))

    def test_undo_is_post_only_and_falls_back_to_reverse_conversion(self):
        self.client.force_login(self.user)
        log = self.convert()
        url = reverse("kitchen:undoUnitChange", args=[log.pk])

        self.assertEqual(self.client.get(url).status_code, 405)

        line = StockReceiptArticle.objects.get(pk=self.open_receipt_line.pk)
        line.comment = "edited"
        line.save()
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("new_unit=ks", response["Location"])
        self.assertIn("factor=23.809524", response["Location"])
        response = self.client.get(response["Location"])
        self.assertEqual(
            response.context["form"]["factor"].value(), Decimal("23.809524")
        )

    def test_undo_view(self):
        self.client.force_login(self.user)
        log = self.convert()

        response = self.client.post(reverse("kitchen:undoUnitChange", args=[log.pk]))

        self.assertRedirects(response, reverse("kitchen:showUnitManagement"))
        self.assertEqual(Article.objects.get(pk=self.article.pk).unit, "ks")

    def test_stale_undo_does_not_suggest_factor_for_different_unit(self):
        self.client.force_login(self.user)
        log = self.convert()
        self.convert(new_unit="l", factor="1.2", note="density")

        response = self.client.post(reverse("kitchen:undoUnitChange", args=[log.pk]))

        self.assertRedirects(response, reverse("kitchen:showUnitManagement"))
        self.assertEqual(Article.objects.get(pk=self.article.pk).unit, "l")

    def test_undo_view_checks_role_of_change_kind(self):
        log = self.convert()
        self.client.force_login(make_user("cook_only", ("cook",)))

        response = self.client.post(reverse("kitchen:undoUnitChange", args=[log.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Article.objects.get(pk=self.article.pk).unit, "kg")

    def test_recipe_reverse_factor_requires_original_line_identity_and_unit(self):
        self.client.force_login(self.user)
        factor = Decimal("0.02381")
        preview = preview_recipe_line_change(self.recipe_grams, "ks", factor, "piece")
        log = apply_recipe_line_change(
            self.recipe_grams.pk,
            "ks",
            factor,
            "piece",
            self.user,
            preview.fingerprint,
            True,
        )
        replacement = Article.objects.create(article="Other", unit="ks")
        changes = (
            {"unit": "g"},
            {"article_id": replacement.pk},
            {"recipe_id": self.recipe.pk},
        )
        for change in changes:
            with self.subTest(change=change):
                state = {
                    "unit": "ks",
                    "article_id": self.article.pk,
                    "recipe_id": self.other_recipe.pk,
                }
                RecipeArticle.objects.filter(pk=self.recipe_grams.pk).update(
                    **(state | change)
                )
                response = self.client.post(
                    reverse("kitchen:undoUnitChange", args=[log.pk])
                )
                self.assertRedirects(response, reverse("kitchen:showUnitManagement"))

    def test_profile_link_visibility(self):
        self.client.force_login(self.user)
        url = reverse("users:detail", args=[self.user.username])
        self.assertContains(self.client.get(url), reverse("kitchen:showUnitManagement"))

        user = make_user("plain")
        self.client.force_login(user)
        url = reverse("users:detail", args=[user.username])
        self.assertNotContains(
            self.client.get(url), reverse("kitchen:showUnitManagement")
        )

    def test_history_page_lists_unit_changes(self):
        self.client.force_login(self.user)
        self.convert()

        response = self.client.get(
            reverse("kitchen:showArticleHistory", args=[self.article.pk])
        )

        self.assertContains(response, "etiketa 42 g")


class UnitChangeBackupTests(UnitChangeFixtureMixin, TransactionTestCase):
    def test_full_backup_round_trip_restores_converted_data_and_log(self):
        superuser = make_user("root", superuser=True)
        self.client.force_login(superuser)
        log = self.convert()
        undo_change(log.pk, self.user)
        self.convert(factor="0.042", note="again")
        state = self.line_state()
        logs = list(UnitChangeLog.objects.order_by("pk").values())
        approvals = list(
            StockReceipt.objects.order_by("pk").values_list(
                "approved", "date_approved", "user_approved"
            )
        )
        export = self.client.get(reverse("kitchen:export"))
        self.assertIn(b'"kitchen.unitchangelog"', export.content)

        response = self.client.post(
            reverse("kitchen:import"),
            {
                "myfile": SimpleUploadedFile(
                    "data.json", export.content, content_type="application/json"
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.line_state(), state)
        restored_logs = list(UnitChangeLog.objects.order_by("pk").values())
        for entry in logs:
            # dumpdata keeps only milliseconds
            entry["created"] = entry["created"].replace(
                microsecond=entry["created"].microsecond // 1000 * 1000
            )
        self.assertEqual(restored_logs, logs)
        self.assertIsNone(undo_blocker(UnitChangeLog.objects.latest("pk")))
        self.assertEqual(
            list(
                StockReceipt.objects.order_by("pk").values_list(
                    "approved", "date_approved", "user_approved"
                )
            ),
            approvals,
        )


class StockExportAfterUnitChangeTests(UnitChangeFixtureMixin, TestCase):
    def export(self, selected_date):
        response = self.client.post(
            reverse("kitchen:exportStockArticlesSelectedDay"),
            {"date": selected_date.isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        rows = Dataset().load(response.content, format="xlsx").dict
        return next(row for row in rows if row["article"] == self.article.article)

    def test_export_for_date_before_conversion_matches_converted_old_export(self):
        self.client.force_login(self.user)
        yesterday = self.today - timedelta(days=1)
        before = self.export(yesterday)

        self.convert()

        after = self.export(yesterday)
        self.assertEqual(after["unit"], "kg")
        self.assertNotIn("export_warning", after)
        # 3 ks * 0.042 = 0.126 kg; the issue line is stored rounded to 0.13 kg
        self.assertAlmostEqual(
            Decimal(str(after["on_stock"])),
            Decimal(str(before["on_stock"])) * Decimal("0.042"),
            delta=Decimal("0.01"),
        )
        # differs only by the rounding difference listed in the preview
        self.assertAlmostEqual(
            Decimal(str(after["total_price"])),
            Decimal(str(before["total_price"])),
            delta=Decimal("1"),
        )
