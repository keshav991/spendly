from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    insert_expense,
)


def seed_expenses(user_id):
    insert_expense(user_id, 50.0, "Food", "2026-01-05", "January expense")
    insert_expense(user_id, 100.0, "Bills", "2026-02-10", "February expense")
    insert_expense(user_id, 25.0, "Food", "2026-03-15", "March expense")


def test_summary_stats_respects_date_range(user):
    seed_expenses(user["id"])

    stats = get_summary_stats(user["id"], "2026-02-01", "2026-02-28")

    assert stats["total_spent"] == "100.00"
    assert stats["transaction_count"] == 1
    assert stats["top_category"] == "Bills"


def test_recent_transactions_respects_date_range(user):
    seed_expenses(user["id"])

    transactions = get_recent_transactions(
        user["id"], date_from="2026-01-01", date_to="2026-02-28"
    )

    assert len(transactions) == 2
    assert [tx["description"] for tx in transactions] == [
        "February expense",
        "January expense",
    ]


def test_category_breakdown_respects_date_range(user):
    seed_expenses(user["id"])

    breakdown = get_category_breakdown(
        user["id"], "2026-01-01", "2026-02-28"
    )

    assert {item["name"] for item in breakdown} == {"Food", "Bills"}
    assert sum(item["percentage"] for item in breakdown) == 100


def test_profile_filters_transactions_by_date(logged_in_client, user):
    seed_expenses(user["id"])

    response = logged_in_client.get(
        "/profile?date_from=2026-02-01&date_to=2026-02-28"
    )

    assert response.status_code == 200
    assert b"February expense" in response.data
    assert b"January expense" not in response.data
    assert b"March expense" not in response.data
    assert b"100.00" in response.data


def test_profile_rejects_inverted_date_range(logged_in_client, user):
    seed_expenses(user["id"])

    response = logged_in_client.get(
        "/profile?date_from=2026-03-01&date_to=2026-02-01"
    )

    assert b"Start date must be before end date" in response.data
