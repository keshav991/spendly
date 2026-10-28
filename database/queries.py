import sqlite3
from datetime import datetime
from database.db import get_db

def get_user_by_id(user_id):
    """Returns user details: name, email, and formatted member_since date."""
    with get_db() as conn:
        user = conn.execute(
            "SELECT username, email, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

        if not user:
            return None

        # Format created_at (YYYY-MM-DD HH:MM:SS) to "Month YYYY"
        try:
            dt = datetime.strptime(user['created_at'], '%Y-%m-%d %H:%M:%S')
            member_since = dt.strftime('%B %Y')
        except (ValueError, TypeError):
            member_since = "Unknown"

        return {
            "name": user['username'],
            "email": user['email'],
            "member_since": member_since
        }

def get_summary_stats(user_id, date_from=None, date_to=None):
    """Returns total spent, transaction count, and top category for a user."""
    with get_db() as conn:
        query = "SELECT SUM(amount), COUNT(*) FROM expenses WHERE user_id = ?"
        params = [user_id]

        if date_from and date_to:
            query += " AND date BETWEEN ? AND ?"
            params.extend([date_from, date_to])

        stats = conn.execute(query, params).fetchone()

        total_spent = stats[0] if stats[0] else 0.0
        transaction_count = stats[1] if stats[1] else 0

        # Top Category
        cat_query = "SELECT category FROM expenses WHERE user_id = ? "
        cat_params = [user_id]
        if date_from and date_to:
            cat_query += " AND date BETWEEN ? AND ?"
            cat_params.extend([date_from, date_to])
        cat_query += " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1"

        top_cat = conn.execute(cat_query, cat_params).fetchone()
        top_category = top_cat['category'] if top_cat else "—"

        return {
            "total_spent": f"{total_spent:,.2f}",
            "transaction_count": transaction_count,
            "top_category": top_category
        }

def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    """Returns a list of recent transactions ordered newest-first."""
    with get_db() as conn:
        query = "SELECT id, date, description, category, amount FROM expenses WHERE user_id = ?"
        params = [user_id]

        if date_from and date_to:
            query += " AND date BETWEEN ? AND ?"
            params.extend([date_from, date_to])

        query += " ORDER BY date DESC, created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()

        return [
            {
                "id": row['id'],
                "date": row['date'],
                "description": row['description'],
                "category": row['category'],
                "amount": f"{row['amount']:,.2f}"
            }
            for row in rows
        ]

def get_category_breakdown(user_id, date_from=None, date_to=None):
    """Returns category totals and percentages summing to 100%."""
    with get_db() as conn:
        query = "SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ?"
        params = [user_id]

        if date_from and date_to:
            query += " AND date BETWEEN ? AND ?"
            params.extend([date_from, date_to])

        query += " GROUP BY category ORDER BY total DESC"
        rows = conn.execute(query, params).fetchall()

        if not rows:
            return []

        total_all = sum(row['total'] for row in rows)
        if total_all == 0:
            return []

        breakdown = []
        sum_pct = 0

        for i, row in enumerate(rows):
            # Calculate integer percentage
            pct = round((row['total'] / total_all) * 100)

            # For the last item, adjust pct to make total sum exactly 100
            if i == len(rows) - 1:
                pct = 100 - sum_pct

            sum_pct += pct
            breakdown.append({
                "name": row['category'],
                "amount": f"{row['total']:,.2f}",
                "percentage": pct
            })

        return breakdown

def insert_expense(user_id, amount, category, date, description):
    """Inserts a new expense for the given user and returns its ID."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description)
        )
        conn.commit()
        return cursor.lastrowid

def get_expense_by_id(expense_id, user_id):
    """Fetches a single expense row only if it belongs to the given user."""
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id)
        ).fetchone()

def update_expense(expense_id, user_id, amount, category, date, description):
    """Updates an existing expense, scoped to the user for ownership safety."""
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ? AND user_id = ?",
            (amount, category, date, description, expense_id, user_id)
        )
        conn.commit()
        return cursor.rowcount

def delete_expense(expense_id, user_id):
    """Deletes an expense, scoped to the user for ownership safety."""
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id)
        )
        conn.commit()
        return cursor.rowcount
