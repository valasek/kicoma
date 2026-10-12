import pytest
from django.test import RequestFactory, override_settings
from django.urls import reverse

from kicoma.users.models import User
from kicoma.users.views import UserRedirectView, UserUpdateView

pytestmark = pytest.mark.django_db


class TestUserUpdateView:
    """
    TODO:
        extracting view initialization code as class-scoped fixture
        would be great if only pytest-django supported non-function-scoped
        fixture db access -- this is a work-in-progress for now:
        https://github.com/pytest-dev/pytest-django/pull/258
    """

    def test_get_success_url(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user

        view.request = request

        assert view.get_success_url() == f"/users/{user.username}/"

    def test_get_object(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user

        view.request = request

        assert view.get_object() == user


class TestUserRedirectView:
    def test_get_redirect_url(self, user: User, rf: RequestFactory):
        view = UserRedirectView()
        request = rf.get("/fake-url")
        request.user = user

        view.request = request

        assert view.get_redirect_url() == f"/users/{user.username}/"


class TestChangePassword:
    def test_profile_links_to_change_password(self, user: User, client):
        client.force_login(user)
        response = client.get(reverse("users:detail", args=[user.username]))
        assert reverse("account_change_password").encode() in response.content

    @override_settings(KICOMA_DEMO_MODE=True)
    def test_link_hidden_in_demo(self, user: User, client):
        client.force_login(user)
        response = client.get(reverse("users:detail", args=[user.username]))
        assert reverse("account_change_password").encode() not in response.content

    def test_change_password(self, user: User, client):
        user.set_password("old-Pass-123")
        user.save()
        client.force_login(user)
        response = client.post(
            reverse("account_change_password"),
            {
                "oldpassword": "old-Pass-123",
                "password1": "new-Pass-456",
                "password2": "new-Pass-456",
            },
        )
        assert response.status_code == 302
        user.refresh_from_db()
        assert user.check_password("new-Pass-456")
