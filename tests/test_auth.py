from werkzeug.security import check_password_hash

from database.db import get_user_by_email


def test_register_creates_user(client):
    response = client.post(
        "/register",
        data={
            "name": "New User",
            "email": "new@example.com",
            "password": "secret123",
            "confirm_password": "secret123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Account created successfully" in response.data

    user = get_user_by_email("new@example.com")
    assert user is not None
    assert user["username"] == "New User"
    assert check_password_hash(user["password"], "secret123")


def test_register_rejects_mismatched_passwords(client):
    response = client.post(
        "/register",
        data={
            "name": "Mismatch",
            "email": "mismatch@example.com",
            "password": "secret123",
            "confirm_password": "different",
        },
        follow_redirects=True,
    )

    assert b"Passwords do not match" in response.data
    assert get_user_by_email("mismatch@example.com") is None


def test_register_rejects_duplicate_email(client, user):
    response = client.post(
        "/register",
        data={
            "name": "Alice Two",
            "email": user["email"],
            "password": "secret123",
            "confirm_password": "secret123",
        },
        follow_redirects=True,
    )

    assert b"Email already registered" in response.data


def test_login_success_sets_session(client, user):
    response = client.post(
        "/login",
        data={"email": user["email"], "password": user["password"]},
    )

    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert sess["user_id"] == user["id"]


def test_login_rejects_invalid_password(client, user):
    response = client.post(
        "/login",
        data={"email": user["email"], "password": "wrong-password"},
    )

    assert response.status_code == 200
    assert b"Invalid email or password" in response.data


def test_logout_clears_session_and_flashes(logged_in_client):
    response = logged_in_client.get("/logout", follow_redirects=True)

    assert b"You have been logged out" in response.data
    with logged_in_client.session_transaction() as sess:
        assert "user_id" not in sess


def test_profile_requires_login(client):
    response = client.get("/profile")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_add_expense_requires_login(client):
    response = client.get("/expenses/add")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_secret_key_comes_from_environment(app):
    assert app.secret_key == "test-secret-key"
