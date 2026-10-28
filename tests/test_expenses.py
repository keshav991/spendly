import pytest

from database.db import get_db
from database.queries import insert_expense


def fetch_expense(expense_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
    finally:
        conn.close()


def count_expenses():
    conn = get_db()
    try:
        return conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    finally:
        conn.close()


def test_add_expense_success(logged_in_client, user):
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "42.50",
            "category": "Food",
            "date": "2026-02-10",
            "description": "Lunch",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Expense added successfully" in response.data
    assert count_expenses() == 1

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE user_id = ?", (user["id"],)
        ).fetchone()
    finally:
        conn.close()

    assert row["amount"] == 42.50
    assert row["category"] == "Food"
    assert row["date"] == "2026-02-10"
    assert row["description"] == "Lunch"


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("amount", "0", b"valid positive amount"),
        ("category", "Invalid", b"valid category"),
        ("date", "10-02-2026", b"valid date"),
    ],
)
def test_add_expense_validation(logged_in_client, field, value, message):
    data = {
        "amount": "10",
        "category": "Food",
        "date": "2026-02-10",
        "description": "x",
    }
    data[field] = value

    response = logged_in_client.post(
        "/expenses/add", data=data, follow_redirects=True
    )

    assert message in response.data
    assert count_expenses() == 0


def test_edit_expense_success(logged_in_client, user):
    expense_id = insert_expense(
        user["id"], 10.0, "Food", "2026-02-01", "Old description"
    )

    response = logged_in_client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "amount": "99.99",
            "category": "Bills",
            "date": "2026-02-20",
            "description": "Updated",
        },
        follow_redirects=True,
    )

    assert b"Expense updated successfully" in response.data
    row = fetch_expense(expense_id)
    assert row["amount"] == 99.99
    assert row["category"] == "Bills"
    assert row["date"] == "2026-02-20"
    assert row["description"] == "Updated"


def test_edit_expense_of_another_user_returns_404(logged_in_client, other_user):
    expense_id = insert_expense(
        other_user["id"], 10.0, "Food", "2026-02-01", "Not yours"
    )

    response = logged_in_client.get(f"/expenses/{expense_id}/edit")

    assert response.status_code == 404


def test_delete_expense_success(logged_in_client, user):
    expense_id = insert_expense(
        user["id"], 10.0, "Food", "2026-02-01", "Delete me"
    )

    response = logged_in_client.post(
        f"/expenses/{expense_id}/delete", follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Expense deleted successfully" in response.data
    assert fetch_expense(expense_id) is None


def test_delete_expense_of_another_user_returns_404(logged_in_client, other_user):
    expense_id = insert_expense(
        other_user["id"], 10.0, "Food", "2026-02-01", "Not yours"
    )

    response = logged_in_client.post(f"/expenses/{expense_id}/delete")

    assert response.status_code == 404
    assert fetch_expense(expense_id) is not None


def test_delete_requires_login(client, user):
    expense_id = insert_expense(
        user["id"], 10.0, "Food", "2026-02-01", "Protected"
    )

    response = client.post(f"/expenses/{expense_id}/delete")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert fetch_expense(expense_id) is not None


def test_delete_rejects_get_request(logged_in_client, user):
    expense_id = insert_expense(
        user["id"], 10.0, "Food", "2026-02-01", "No GET"
    )

    response = logged_in_client.get(f"/expenses/{expense_id}/delete")

    assert response.status_code == 405
