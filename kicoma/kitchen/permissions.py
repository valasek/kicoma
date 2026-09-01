from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils.translation import gettext_lazy as _


class Roles(models.TextChoices):
    COOK = "cook", _("Kuchař")
    STOCKKEEPER = "stockkeeper", _("Skladník")
    NUTRITION_ADVISOR = "nutrition_advisor", _("Nutriční poradce")


def split_roles(roles):
    if isinstance(roles, str):
        roles = roles.split(",")
    return tuple(role.strip() for role in roles if role and role.strip())


def validate_roles(roles):
    unknown = sorted(set(roles) - set(Roles.values))
    if unknown:
        raise ValueError(
            f"Unknown role(s): {', '.join(unknown)}. Known roles: {', '.join(Roles.values)}"
        )
    return roles


def user_role_names(user):
    """Cached on the user instance - role checks run ~20x per rendered page."""
    if not user or not user.is_authenticated:
        return frozenset()
    if not hasattr(user, "_cached_role_names"):
        user._cached_role_names = frozenset(user.groups.values_list("name", flat=True))
    return user._cached_role_names


def user_has_any_role(user, roles):
    roles = validate_roles(split_roles(roles))
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return bool(user_role_names(user).intersection(roles))


class RoleRequiredMixin(AccessMixin):
    """Anonymous users are redirected to login, signed-in users without a role get 403."""

    allowed_roles: tuple[str, ...] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        validate_roles(split_roles(cls.allowed_roles))

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not user_has_any_role(request.user, self.allowed_roles):
            raise PermissionDenied(_("Nemáte oprávnění zobrazit tuto stránku."))
        return super().dispatch(request, *args, **kwargs)


class StockkeeperRequiredMixin(RoleRequiredMixin):
    allowed_roles = (Roles.STOCKKEEPER,)


class CookOrStockkeeperRequiredMixin(RoleRequiredMixin):
    allowed_roles = (Roles.COOK, Roles.STOCKKEEPER)


class CookOrNutritionAdvisorRequiredMixin(RoleRequiredMixin):
    allowed_roles = (Roles.COOK, Roles.NUTRITION_ADVISOR)


class StockkeeperOrNutritionAdvisorRequiredMixin(RoleRequiredMixin):
    allowed_roles = (Roles.STOCKKEEPER, Roles.NUTRITION_ADVISOR)


class AnyRoleRequiredMixin(RoleRequiredMixin):
    allowed_roles = tuple(Roles.values)
