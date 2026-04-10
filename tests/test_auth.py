import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from utils.security import COOKIE_NAME, hash_password, create_access_token


class TestRegistrationPage:
    """Tests for GET /auth/register page."""

    @pytest.mark.asyncio
    async def test_register_page_returns_200(self, client: AsyncClient):
        response = await client.get("/auth/register")
        assert response.status_code == 200
        assert "Create your account" in response.text

    @pytest.mark.asyncio
    async def test_register_page_redirects_authenticated_user_to_dashboard(
        self, authenticated_client: AsyncClient
    ):
        response = await authenticated_client.get("/auth/register")
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard/"

    @pytest.mark.asyncio
    async def test_register_page_redirects_admin_to_admin_dashboard(
        self, admin_client: AsyncClient
    ):
        response = await admin_client.get("/auth/register")
        assert response.status_code == 302
        assert response.headers["location"] == "/admin/dashboard/"


class TestRegistrationSubmit:
    """Tests for POST /auth/register."""

    @pytest.mark.asyncio
    async def test_register_valid_user_redirects_to_login(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            data={
                "display_name": "New User",
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "SecurePass123",
                "confirm_password": "SecurePass123",
            },
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/auth/login"

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_400(
        self, client: AsyncClient, test_user: User
    ):
        response = await client.post(
            "/auth/register",
            data={
                "display_name": "Another User",
                "email": test_user.email,
                "username": "anotheruser",
                "password": "SecurePass123",
                "confirm_password": "SecurePass123",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.text

    @pytest.mark.asyncio
    async def test_register_duplicate_username_returns_400(
        self, client: AsyncClient, test_user: User
    ):
        response = await client.post(
            "/auth/register",
            data={
                "display_name": "Another User",
                "email": "unique@example.com",
                "username": test_user.username,
                "password": "SecurePass123",
                "confirm_password": "SecurePass123",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.text

    @pytest.mark.asyncio
    async def test_register_password_mismatch_returns_400(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            data={
                "display_name": "Mismatch User",
                "email": "mismatch@example.com",
                "username": "mismatchuser",
                "password": "SecurePass123",
                "confirm_password": "DifferentPass456",
            },
        )
        assert response.status_code == 400
        assert "Passwords do not match" in response.text

    @pytest.mark.asyncio
    async def test_register_short_password_returns_400(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            data={
                "display_name": "Short Pass",
                "email": "shortpass@example.com",
                "username": "shortpass",
                "password": "short",
                "confirm_password": "short",
            },
        )
        assert response.status_code == 400
        assert "at least 8 characters" in response.text

    @pytest.mark.asyncio
    async def test_register_empty_display_name_returns_400(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            data={
                "display_name": "",
                "email": "emptyname@example.com",
                "username": "emptyname",
                "password": "SecurePass123",
                "confirm_password": "SecurePass123",
            },
        )
        assert response.status_code == 400
        assert "Display name is required" in response.text

    @pytest.mark.asyncio
    async def test_register_short_username_returns_400(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            data={
                "display_name": "Short Username",
                "email": "shortun@example.com",
                "username": "ab",
                "password": "SecurePass123",
                "confirm_password": "SecurePass123",
            },
        )
        assert response.status_code == 400
        assert "at least 3 characters" in response.text

    @pytest.mark.asyncio
    async def test_register_invalid_username_chars_returns_400(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            data={
                "display_name": "Bad Chars",
                "email": "badchars@example.com",
                "username": "bad user!",
                "password": "SecurePass123",
                "confirm_password": "SecurePass123",
            },
        )
        assert response.status_code == 400
        assert "letters, numbers, hyphens, and underscores" in response.text

    @pytest.mark.asyncio
    async def test_register_empty_email_returns_400(self, client: AsyncClient):
        response = await client.post(
            "/auth/register",
            data={
                "display_name": "No Email",
                "email": "",
                "username": "noemail",
                "password": "SecurePass123",
                "confirm_password": "SecurePass123",
            },
        )
        assert response.status_code == 400
        assert "Email is required" in response.text


class TestLoginPage:
    """Tests for GET /auth/login page."""

    @pytest.mark.asyncio
    async def test_login_page_returns_200(self, client: AsyncClient):
        response = await client.get("/auth/login")
        assert response.status_code == 200
        assert "Sign in to FitLog" in response.text

    @pytest.mark.asyncio
    async def test_login_page_redirects_authenticated_user_to_dashboard(
        self, authenticated_client: AsyncClient
    ):
        response = await authenticated_client.get("/auth/login")
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard/"

    @pytest.mark.asyncio
    async def test_login_page_redirects_admin_to_admin_dashboard(
        self, admin_client: AsyncClient
    ):
        response = await admin_client.get("/auth/login")
        assert response.status_code == 302
        assert response.headers["location"] == "/admin/dashboard/"


class TestLoginSubmit:
    """Tests for POST /auth/login."""

    @pytest.mark.asyncio
    async def test_login_valid_user_sets_cookie_and_redirects(
        self, client: AsyncClient, test_user: User
    ):
        response = await client.post(
            "/auth/login",
            data={
                "username": "testuser",
                "password": "TestPass123",
            },
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard/"

        set_cookie_header = response.headers.get("set-cookie", "")
        assert COOKIE_NAME in set_cookie_header

    @pytest.mark.asyncio
    async def test_login_admin_redirects_to_admin_dashboard(
        self, client: AsyncClient, test_admin: User
    ):
        response = await client.post(
            "/auth/login",
            data={
                "username": "testadmin",
                "password": "AdminPass123",
            },
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/admin/dashboard/"

        set_cookie_header = response.headers.get("set-cookie", "")
        assert COOKIE_NAME in set_cookie_header

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_400(
        self, client: AsyncClient, test_user: User
    ):
        response = await client.post(
            "/auth/login",
            data={
                "username": "testuser",
                "password": "WrongPassword123",
            },
        )
        assert response.status_code == 400
        assert "Invalid username or password" in response.text

    @pytest.mark.asyncio
    async def test_login_nonexistent_user_returns_400(self, client: AsyncClient):
        response = await client.post(
            "/auth/login",
            data={
                "username": "nonexistentuser",
                "password": "SomePassword123",
            },
        )
        assert response.status_code == 400
        assert "Invalid username or password" in response.text

    @pytest.mark.asyncio
    async def test_login_inactive_user_returns_400(
        self, client: AsyncClient, inactive_user: User
    ):
        response = await client.post(
            "/auth/login",
            data={
                "username": "inactiveuser",
                "password": "InactivePass123",
            },
        )
        assert response.status_code == 400
        assert "Invalid username or password" in response.text

    @pytest.mark.asyncio
    async def test_login_case_insensitive_username(
        self, client: AsyncClient, test_user: User
    ):
        response = await client.post(
            "/auth/login",
            data={
                "username": "TestUser",
                "password": "TestPass123",
            },
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard/"


class TestLogout:
    """Tests for POST /auth/logout."""

    @pytest.mark.asyncio
    async def test_logout_clears_cookie_and_redirects_to_login(
        self, authenticated_client: AsyncClient
    ):
        response = await authenticated_client.post("/auth/logout")
        assert response.status_code == 302
        assert response.headers["location"] == "/auth/login"

        set_cookie_header = response.headers.get("set-cookie", "")
        assert COOKIE_NAME in set_cookie_header
        # Cookie should be deleted (max-age=0 or expires in the past)
        lower_header = set_cookie_header.lower()
        has_deletion_marker = (
            'max-age=0' in lower_header
            or "expires=" in lower_header
            or '""' in set_cookie_header
            or '="";' in set_cookie_header
        )
        assert has_deletion_marker

    @pytest.mark.asyncio
    async def test_logout_without_auth_still_redirects(self, client: AsyncClient):
        response = await client.post("/auth/logout")
        assert response.status_code == 302
        assert response.headers["location"] == "/auth/login"


class TestJWTCookieAuthentication:
    """Tests for JWT cookie-based authentication flow."""

    @pytest.mark.asyncio
    async def test_cookie_httponly_flag_is_set(
        self, client: AsyncClient, test_user: User
    ):
        response = await client.post(
            "/auth/login",
            data={
                "username": "testuser",
                "password": "TestPass123",
            },
        )
        set_cookie_header = response.headers.get("set-cookie", "")
        assert "httponly" in set_cookie_header.lower()

    @pytest.mark.asyncio
    async def test_valid_cookie_grants_access_to_dashboard(
        self, authenticated_client: AsyncClient
    ):
        response = await authenticated_client.get("/dashboard/")
        assert response.status_code == 200
        assert "Welcome back" in response.text

    @pytest.mark.asyncio
    async def test_invalid_cookie_redirects_to_login(self, client: AsyncClient):
        client.cookies.set(COOKIE_NAME, "invalid-jwt-token-value")
        response = await client.get("/dashboard/")
        # Should get 401 or redirect to login
        assert response.status_code in (302, 401)

    @pytest.mark.asyncio
    async def test_expired_token_is_rejected(self, client: AsyncClient, test_user: User):
        from datetime import timedelta

        expired_token = create_access_token(
            data={"sub": str(test_user.id)},
            expires_delta=timedelta(seconds=-10),
        )
        client.cookies.set(COOKIE_NAME, expired_token)
        response = await client.get("/dashboard/")
        assert response.status_code in (302, 401)

    @pytest.mark.asyncio
    async def test_no_cookie_redirects_protected_routes(self, client: AsyncClient):
        response = await client.get("/dashboard/")
        assert response.status_code in (302, 401)

    @pytest.mark.asyncio
    async def test_no_cookie_redirects_workouts(self, client: AsyncClient):
        response = await client.get("/workouts/")
        assert response.status_code in (302, 401)

    @pytest.mark.asyncio
    async def test_no_cookie_redirects_measurements(self, client: AsyncClient):
        response = await client.get("/measurements/")
        assert response.status_code in (302, 401)


class TestRoleBasedRedirect:
    """Tests for role-based redirects on root and login."""

    @pytest.mark.asyncio
    async def test_root_redirects_unauthenticated_to_login(self, client: AsyncClient):
        response = await client.get("/")
        assert response.status_code == 302
        assert response.headers["location"] == "/auth/login"

    @pytest.mark.asyncio
    async def test_root_redirects_user_to_dashboard(
        self, authenticated_client: AsyncClient
    ):
        response = await authenticated_client.get("/")
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard/"

    @pytest.mark.asyncio
    async def test_root_redirects_admin_to_admin_dashboard(
        self, admin_client: AsyncClient
    ):
        response = await admin_client.get("/")
        assert response.status_code == 302
        assert response.headers["location"] == "/admin/dashboard/"

    @pytest.mark.asyncio
    async def test_admin_dashboard_forbidden_for_regular_user(
        self, authenticated_client: AsyncClient
    ):
        response = await authenticated_client.get("/admin/dashboard/")
        assert response.status_code in (302, 403)

    @pytest.mark.asyncio
    async def test_admin_dashboard_accessible_for_admin(
        self, admin_client: AsyncClient
    ):
        response = await admin_client.get("/admin/dashboard/")
        assert response.status_code == 200
        assert "Admin Dashboard" in response.text


class TestRegistrationAndLoginFlow:
    """End-to-end tests for the registration → login flow."""

    @pytest.mark.asyncio
    async def test_register_then_login_succeeds(self, client: AsyncClient):
        # Register a new user
        reg_response = await client.post(
            "/auth/register",
            data={
                "display_name": "Flow Test User",
                "email": "flowtest@example.com",
                "username": "flowtestuser",
                "password": "FlowTestPass123",
                "confirm_password": "FlowTestPass123",
            },
        )
        assert reg_response.status_code == 302
        assert reg_response.headers["location"] == "/auth/login"

        # Login with the newly registered user
        login_response = await client.post(
            "/auth/login",
            data={
                "username": "flowtestuser",
                "password": "FlowTestPass123",
            },
        )
        assert login_response.status_code == 302
        assert login_response.headers["location"] == "/dashboard/"

        set_cookie_header = login_response.headers.get("set-cookie", "")
        assert COOKIE_NAME in set_cookie_header

    @pytest.mark.asyncio
    async def test_login_then_logout_then_access_denied(self, client: AsyncClient, test_user: User):
        # Login
        login_response = await client.post(
            "/auth/login",
            data={
                "username": "testuser",
                "password": "TestPass123",
            },
        )
        assert login_response.status_code == 302

        # Extract cookie from login response and set it
        set_cookie_header = login_response.headers.get("set-cookie", "")
        assert COOKIE_NAME in set_cookie_header

        # Access dashboard with cookie should work
        # Parse the token from set-cookie header
        for part in set_cookie_header.split(";"):
            part = part.strip()
            if part.startswith(f"{COOKIE_NAME}="):
                token_value = part.split("=", 1)[1]
                client.cookies.set(COOKIE_NAME, token_value)
                break

        dashboard_response = await client.get("/dashboard/")
        assert dashboard_response.status_code == 200

        # Logout
        logout_response = await client.post("/auth/logout")
        assert logout_response.status_code == 302

        # Clear the cookie on the client side to simulate browser behavior
        client.cookies.delete(COOKIE_NAME)

        # Access dashboard without cookie should fail
        no_auth_response = await client.get("/dashboard/")
        assert no_auth_response.status_code in (302, 401)