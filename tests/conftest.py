import os
import sys
import tempfile
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

TEST_DB = Path(tempfile.mkdtemp(prefix="spendly_test_")) / "spendly_test.db"
os.environ["SPENDLY_DATABASE"] = str(TEST_DB)
os.environ["SPENDLY_SECRET_KEY"] = "test-secret-key"

from app import app as flask_app  # noqa: E402
from database.db import create_user, get_db  # noqa: E402


@pytest.fixture()
def app():
    flask_app.config.update(TESTING=True)
    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db():
    conn = get_db()
    try:
        conn.execute("DELETE FROM expenses")
        conn.execute("DELETE FROM users")
        conn.commit()
    finally:
        conn.close()
    yield


def create_test_user(username="alice", email="alice@example.com", password="password123"):
    return create_user(username, email, generate_password_hash(password))


@pytest.fixture()
def user():
    return {
        "id": create_test_user(),
        "email": "alice@example.com",
        "password": "password123",
    }


@pytest.fixture()
def other_user():
    return {
        "id": create_test_user("bob", "bob@example.com", "password456"),
        "email": "bob@example.com",
        "password": "password456",
    }


@pytest.fixture()
def logged_in_client(client, user):
    client.post(
        "/login",
        data={"email": user["email"], "password": user["password"]},
    )
    return client
