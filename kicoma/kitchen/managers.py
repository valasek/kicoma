from django.db import models
from django.db.models import F
from django.db.models.functions.comparison import Collate
from django.utils import translation


def get_collation():
    lang = translation.get_language()
    return "cs_collate" if lang == "cs" else "en_collate"


class CollatableQuerySet(models.QuerySet):
    def _resolve_ordering_field(self, field_name):
        """
        Resolve a field name to the correct field path.
        - Handles related fields (FKs).
        - Picks the first CharField/TextField in related model if needed.
        """
        parts = field_name.split("__")
        model = self.model
        resolved_parts = []

        for part in parts:
            field = model._meta.get_field(part)
            if field.is_relation and field.related_model:
                # If it's a FK, try to find a "natural" CharField/TextField
                related_model = field.related_model
                # find best display field
                string_fields = [
                    f.name for f in related_model._meta.get_fields()
                    if isinstance(f, (models.CharField, models.TextField))
                ]
                if string_fields:
                    # pick the first CharField/TextField (often the "name" or "title")
                    resolved_parts.append(part)
                    resolved_parts.append(string_fields[0])
                else:
                    # fallback to PK
                    resolved_parts.append(part)
                    resolved_parts.append(related_model._meta.pk.name)
                model = related_model
            else:
                resolved_parts.append(part)

        return "__".join(resolved_parts)

    def with_language_ordering(self):
        collation = get_collation()
        ordering = self.model._meta.ordering or []
        if not ordering:
            return self

        exprs = []
        for field in ordering:
            desc = field.startswith("-")
            field_name = field[1:] if desc else field
            resolved_field = self._resolve_ordering_field(field_name)
            expr = Collate(F(resolved_field), collation)
            exprs.append(expr.desc() if desc else expr.asc())
        return self.order_by(*exprs)


class CollatableManager(models.Manager):
    def get_queryset(self):
        return CollatableQuerySet(self.model, using=self._db)

    def with_language_ordering(self):
        return self.get_queryset().with_language_ordering()
