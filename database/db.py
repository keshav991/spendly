import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

# Keep the database tied to this project instead of the process working directory.
DATABASE = Path(__file__).resolve().parent.parent / 'spendly.db'

def get_db():
    """Returns a SQLite connection with row_factory and foreign keys enabled."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Creates all tables using CREATE TABLE IF NOT EXISTS."""
    with get_db() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        ''')
        conn.commit()

def seed_db():
    """Inserts sample data for development."""
    with get_db() as conn:
        # Check if data already exists to avoid duplicates
        cursor = conn.execute("SELECT count(*) FROM users")
        if cursor.fetchone()[0] > 0:
            return

        # Seed users with hashed passwords
        users = [
            ('testuser', generate_password_hash('password123'), 'test@example.com'),
            ('admin', generate_password_hash('admin123'), 'admin@spendly.com')
        ]
        conn.executemany("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", users)

        # Get user IDs for expenses
        cursor = conn.execute("SELECT id FROM users")
        user_ids = [row['id'] for row in cursor.fetchall()]

        if not user_ids:
            return

        # Seed 8 sample expenses across categories
        expenses = [
            (user_ids[0], 12.50, 'Food', 'Lunch at cafe', '2026-10-20'),
            (user_ids[0], 45.00, 'Transport', 'Gas refill', '2026-10-21'),
            (user_ids[0], 120.00, 'Bills', 'Internet bill', '2026-10-22'),
            (user_ids[1], 15.00, 'Entertainment', 'Movie ticket', '2026-10-23'),
            (user_ids[1], 60.00, 'Shopping', 'New shirt', '2026-10-24'),
            (user_ids[0], 25.00, 'Health', 'Pharmacy visit', '2026-10-25'),
            (user_ids[1], 10.00, 'Food', 'Coffee and pastry', '2026-10-26'),
            (user_ids[1], 200.00, 'Bills', 'Monthly Rent', '2026-10-27'),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
            expenses
        )
        conn.commit()

def get_user_by_email(email):
    """Returns the user row for a given email, or None if not found."""
    with get_db() as conn:
        return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

def create_user(username, email, password_hash):
    """Inserts a new user and returns the new user's ID."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
            (username, password_hash, email)
        )
        conn.commit()
        return cursor.lastrowid
