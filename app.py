from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from database.db import init_db, seed_db, get_user_by_email, create_user
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown, get_expense_by_id, update_expense
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'dev-secret-key-for-spendly'
app.permanent_session_lifetime = timedelta(days=30)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Initialize database on startup
with app.app_context():
    init_db()
    seed_db()



# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # 1. Check for empty fields
        if not all([name, email, password, confirm_password]):
            flash("All fields are required.")
            return redirect(url_for('register'))

        # 2. Check password match
        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for('register'))

        # 3. Check email uniqueness
        if get_user_by_email(email):
            flash("Email already registered.")
            return redirect(url_for('register'))

        try:
            hashed_password = generate_password_hash(password)
            create_user(name, email, hashed_password)
            flash("Account created successfully! Please sign in.")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"An error occurred: {e}")
            return redirect(url_for('register'))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            return render_template("login.html", error="All fields are required.")

        user = get_user_by_email(email)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session.permanent = request.form.get('remember_me') == 'on'
            return redirect(url_for('landing'))

        return render_template(
            "login.html",
            error="Invalid email or password.",
            email=email
        )

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")




# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('landing'))


@app.route("/profile")
@login_required
def profile():
    user_id = session.get('user_id')

    # 1. Extract and Validate Date Filters
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    # Preset Logic
    preset = request.args.get('preset')
    today = datetime.now()

    if preset == 'this_month':
        date_to = today.strftime('%Y-%m-%d')
        date_from = today.replace(day=1).strftime('%Y-%m-%d')
    elif preset == 'last_3':
        date_to = today.strftime('%Y-%m-%d')
        date_from = (today - timedelta(days=90)).strftime('%Y-%m-%d')
    elif preset == 'last_6':
        date_to = today.strftime('%Y-%m-%d')
        date_from = (today - timedelta(days=180)).strftime('%Y-%m-%d')
    elif preset == 'all':
        date_from = date_to = None

    # Validate ISO format
    valid_from = None
    valid_to = None
    try:
        if date_from:
            datetime.strptime(date_from, '%Y-%m-%d')
            valid_from = date_from
        if date_to:
            datetime.strptime(date_to, '%Y-%m-%d')
            valid_to = date_to
    except ValueError:
        # Fallback to unfiltered if malformed
        valid_from = valid_to = None

    # Logic check: from must be <= to
    if valid_from and valid_to and valid_from > valid_to:
        flash("Start date must be before end date.")
        valid_from = valid_to = None

    # 2. Fetch Data using filtered bounds
    user = get_user_by_id(user_id)
    stats = get_summary_stats(user_id, valid_from, valid_to)
    transactions = get_recent_transactions(user_id, date_from=valid_from, date_to=valid_to)
    categories = get_category_breakdown(user_id, valid_from, valid_to)

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        date_from=valid_from,
        date_to=valid_to,
        active_preset=preset
    )


@app.route("/expenses/add", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "POST":
        amount_raw = request.form.get("amount")
        category = request.form.get("category")
        date_str = request.form.get("date")
        description = request.form.get("description", "").strip() or None

        # 1. Validate Amount
        try:
            amount = float(amount_raw)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except (TypeError, ValueError):
            flash("Please enter a valid positive amount.")
            return render_template("add_expense.html", error="Invalid amount")

        # 2. Validate Category
        valid_categories = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
        if category not in valid_categories:
            flash("Please select a valid category.")
            return render_template("add_expense.html", error="Invalid category")

        # 3. Validate Date
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except (TypeError, ValueError):
            flash("Please enter a valid date.")
            return render_template("add_expense.html", error="Invalid date")

        # 4. Save Expense
        try:
            user_id = session.get('user_id')
            insert_expense(user_id, amount, category, date_str, description)
            flash("Expense added successfully!")
            return redirect(url_for('profile'))
        except Exception as e:
            flash(f"An error occurred while saving: {e}")
            return render_template("add_expense.html", error="Database error")

    # GET: render form with today's date as default
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template("add_expense.html", today=today)


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(id):
    user_id = session.get('user_id')

    if request.method == "POST":
        amount_raw = request.form.get("amount")
        category = request.form.get("category")
        date_str = request.form.get("date")
        description = request.form.get("description", "").strip() or None

        # Validation
        try:
            amount = float(amount_raw)
            if amount <= 0:
                raise ValueError()
        except (TypeError, ValueError):
            flash("Please enter a valid positive amount.")
            return render_template("edit_expense.html", expense={"id": id}, error="Invalid amount")

        valid_categories = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
        if category not in valid_categories:
            flash("Please select a valid category.")
            return render_template("edit_expense.html", expense={"id": id}, error="Invalid category")

        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except (TypeError, ValueError):
            flash("Please enter a valid date.")
            return render_template("edit_expense.html", expense={"id": id}, error="Invalid date")

        # Update in DB
        try:
            update_expense(id, user_id, amount, category, date_str, description)
            flash("Expense updated successfully!")
            return redirect(url_for('profile'))
        except Exception as e:
            flash(f"An error occurred: {e}")
            return render_template("edit_expense.html", expense={"id": id}, error="Database error")

    # GET: Load existing expense
    expense = get_expense_by_id(id, user_id)
    if not expense:
        abort(404)

    return render_template("edit_expense.html", expense=expense)


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
