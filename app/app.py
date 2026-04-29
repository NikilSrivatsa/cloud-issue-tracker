from datetime import datetime
from functools import wraps
import os
import sqlite3

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "issues.db"))

app = Flask(
    __name__,
    template_folder=os.path.join(ROOT_DIR, "templates"),
    static_folder=os.path.join(ROOT_DIR, "static"),
)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

DEMO_USERS = {
    "admin": {"password": "admin123", "name": "Admin User", "role": "Cloud Admin"},
    "devops": {"password": "devops123", "name": "DevOps Engineer", "role": "Pipeline Owner"},
    "viewer": {"password": "viewer123", "name": "Project Reviewer", "role": "Read Only"},
}


def current_time():
    return datetime.utcnow().isoformat(timespec="seconds")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "username" not in session:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def editor_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("username") == "viewer":
            flash("Viewer account is read-only. Use admin or devops to make changes.", "error")
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped_view


def record_activity(conn, action, issue_id=None, detail=""):
    conn.execute(
        """
        INSERT INTO activity (action, issue_id, actor, detail, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (action, issue_id, session.get("username", "system"), detail, current_time()),
    )


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                owner TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                category TEXT NOT NULL DEFAULT 'Infrastructure',
                environment TEXT NOT NULL DEFAULT 'Production',
                description TEXT NOT NULL DEFAULT '',
                due_date TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id INTEGER NOT NULL,
                author TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(issue_id) REFERENCES issues(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                issue_id INTEGER,
                actor TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(issues)").fetchall()}
        migrations = {
            "category": "ALTER TABLE issues ADD COLUMN category TEXT NOT NULL DEFAULT 'Infrastructure'",
            "environment": "ALTER TABLE issues ADD COLUMN environment TEXT NOT NULL DEFAULT 'Production'",
            "description": "ALTER TABLE issues ADD COLUMN description TEXT NOT NULL DEFAULT ''",
            "due_date": "ALTER TABLE issues ADD COLUMN due_date TEXT NOT NULL DEFAULT ''",
            "updated_at": "ALTER TABLE issues ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
        }
        for column, statement in migrations.items():
            if column not in columns:
                conn.execute(statement)


@app.route("/")
@login_required
def index():
    status_filter = request.args.get("status", "All")
    priority_filter = request.args.get("priority", "All")
    environment_filter = request.args.get("environment", "All")
    search = request.args.get("q", "").strip()
    where = []
    params = []

    if status_filter != "All":
        where.append("status = ?")
        params.append(status_filter)
    if priority_filter != "All":
        where.append("priority = ?")
        params.append(priority_filter)
    if environment_filter != "All":
        where.append("environment = ?")
        params.append(environment_filter)
    if search:
        where.append("(title LIKE ? OR owner LIKE ? OR description LIKE ? OR category LIKE ?)")
        params.extend([f"%{search}%"] * 4)

    query = "SELECT * FROM issues"
    if where:
        query += " WHERE " + " AND ".join(where)
    query += """
        ORDER BY
            CASE priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END,
            id DESC
    """

    with get_db() as conn:
        issues = conn.execute(query, params).fetchall()
        counts = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) AS open,
                SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS progress,
                SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) AS resolved,
                SUM(CASE WHEN priority = 'Critical' THEN 1 ELSE 0 END) AS critical
            FROM issues
            """
        ).fetchone()
        recent = conn.execute(
            "SELECT * FROM issues ORDER BY COALESCE(NULLIF(updated_at, ''), created_at) DESC LIMIT 5"
        ).fetchall()
        activity = conn.execute("SELECT * FROM activity ORDER BY id DESC LIMIT 8").fetchall()
        environment_counts = conn.execute(
            """
            SELECT environment, COUNT(*) AS total
            FROM issues
            GROUP BY environment
            ORDER BY total DESC
            """
        ).fetchall()

    return render_template(
        "index.html",
        issues=issues,
        counts=counts,
        recent=recent,
        activity=activity,
        environment_counts=environment_counts,
        status_filter=status_filter,
        priority_filter=priority_filter,
        environment_filter=environment_filter,
        search=search,
        user=DEMO_USERS[session["username"]],
        username=session["username"],
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = DEMO_USERS.get(username)

        if user and user["password"] == password:
            session["username"] = username
            flash(f"Welcome back, {user['name']}.", "success")
            return redirect(url_for("index"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


@app.route("/issues", methods=["POST"])
@login_required
@editor_required
def create_issue():
    title = request.form.get("title", "").strip()
    owner = request.form.get("owner", "").strip()
    priority = request.form.get("priority", "Medium").strip()
    category = request.form.get("category", "Infrastructure").strip()
    environment = request.form.get("environment", "Production").strip()
    description = request.form.get("description", "").strip()
    due_date = request.form.get("due_date", "").strip()

    if not title or not owner:
        flash("Title and owner are required.", "error")
        return redirect(url_for("index"))

    if priority not in {"Critical", "High", "Medium", "Low"}:
        priority = "Medium"
    if environment not in {"Production", "Staging", "Development"}:
        environment = "Production"

    timestamp = current_time()
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO issues
                (title, owner, priority, status, category, environment, description, due_date, updated_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, owner, priority, "Open", category, environment, description, due_date, timestamp, timestamp),
        )
        record_activity(conn, "Created ticket", cursor.lastrowid, title)

    flash("Issue created successfully.", "success")
    return redirect(url_for("index"))


@app.route("/issues/<int:issue_id>/status", methods=["POST"])
@login_required
@editor_required
def update_status(issue_id):
    status = request.form.get("status", "Open")
    if status not in {"Open", "In Progress", "Resolved"}:
        flash("Invalid status.", "error")
        return redirect(url_for("index"))

    with get_db() as conn:
        conn.execute(
            "UPDATE issues SET status = ?, updated_at = ? WHERE id = ?",
            (status, current_time(), issue_id),
        )
        record_activity(conn, "Updated status", issue_id, status)

    flash("Issue status updated.", "success")
    return redirect(url_for("index"))


@app.route("/issues/<int:issue_id>/edit", methods=["GET", "POST"])
@login_required
def edit_issue(issue_id):
    with get_db() as conn:
        issue = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
        if issue is None:
            flash("Ticket not found.", "error")
            return redirect(url_for("index"))

        if request.method == "POST":
            if session.get("username") == "viewer":
                flash("Viewer account is read-only. Use admin or devops to make changes.", "error")
                return redirect(url_for("edit_issue", issue_id=issue_id))

            title = request.form.get("title", "").strip()
            owner = request.form.get("owner", "").strip()
            priority = request.form.get("priority", "Medium").strip()
            status = request.form.get("status", "Open").strip()
            category = request.form.get("category", "Infrastructure").strip()
            environment = request.form.get("environment", "Production").strip()
            description = request.form.get("description", "").strip()
            due_date = request.form.get("due_date", "").strip()

            if not title or not owner:
                flash("Title and owner are required.", "error")
                return redirect(url_for("edit_issue", issue_id=issue_id))

            conn.execute(
                """
                UPDATE issues
                SET title = ?, owner = ?, priority = ?, status = ?, category = ?,
                    environment = ?, description = ?, due_date = ?, updated_at = ?
                WHERE id = ?
                """,
                (title, owner, priority, status, category, environment, description, due_date, current_time(), issue_id),
            )
            record_activity(conn, "Edited ticket", issue_id, title)
            flash("Ticket updated.", "success")
            return redirect(url_for("index"))

        comments = conn.execute(
            "SELECT * FROM comments WHERE issue_id = ? ORDER BY id DESC",
            (issue_id,),
        ).fetchall()

    return render_template("edit_issue.html", issue=issue, comments=comments)


@app.route("/issues/<int:issue_id>/comments", methods=["POST"])
@login_required
@editor_required
def add_comment(issue_id):
    note = request.form.get("note", "").strip()
    if not note:
        flash("Comment cannot be empty.", "error")
        return redirect(url_for("edit_issue", issue_id=issue_id))

    with get_db() as conn:
        issue = conn.execute("SELECT title FROM issues WHERE id = ?", (issue_id,)).fetchone()
        if issue is None:
            flash("Ticket not found.", "error")
            return redirect(url_for("index"))
        conn.execute(
            """
            INSERT INTO comments (issue_id, author, note, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (issue_id, session["username"], note, current_time()),
        )
        conn.execute("UPDATE issues SET updated_at = ? WHERE id = ?", (current_time(), issue_id))
        record_activity(conn, "Added comment", issue_id, issue["title"])

    flash("Comment added.", "success")
    return redirect(url_for("edit_issue", issue_id=issue_id))


@app.route("/issues/<int:issue_id>/delete", methods=["POST"])
@login_required
@editor_required
def delete_issue(issue_id):
    with get_db() as conn:
        issue = conn.execute("SELECT title FROM issues WHERE id = ?", (issue_id,)).fetchone()
        conn.execute("DELETE FROM comments WHERE issue_id = ?", (issue_id,))
        conn.execute("DELETE FROM issues WHERE id = ?", (issue_id,))
        record_activity(conn, "Deleted ticket", issue_id, issue["title"] if issue else "")

    flash("Issue deleted.", "success")
    return redirect(url_for("index"))


@app.route("/api/issues")
@login_required
def issues_api():
    with get_db() as conn:
        issues = [dict(row) for row in conn.execute("SELECT * FROM issues ORDER BY id DESC").fetchall()]
    return jsonify({"issues": issues, "total": len(issues)})


@app.route("/health")
def health():
    return {"status": "ok"}


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
