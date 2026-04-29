from datetime import datetime
import os
import sqlite3

from flask import Flask, flash, redirect, render_template, request, url_for


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "issues.db"))

app = Flask(
    __name__,
    template_folder=os.path.join(ROOT_DIR, "templates"),
    static_folder=os.path.join(ROOT_DIR, "static"),
)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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

    return render_template(
        "index.html",
        issues=issues,
        counts=counts,
        recent=recent,
        status_filter=status_filter,
        priority_filter=priority_filter,
        environment_filter=environment_filter,
        search=search,
    )


@app.route("/issues", methods=["POST"])
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

    timestamp = datetime.utcnow().isoformat(timespec="seconds")
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO issues
                (title, owner, priority, status, category, environment, description, due_date, updated_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, owner, priority, "Open", category, environment, description, due_date, timestamp, timestamp),
        )

    flash("Issue created successfully.", "success")
    return redirect(url_for("index"))


@app.route("/issues/<int:issue_id>/status", methods=["POST"])
def update_status(issue_id):
    status = request.form.get("status", "Open")
    if status not in {"Open", "In Progress", "Resolved"}:
        flash("Invalid status.", "error")
        return redirect(url_for("index"))

    with get_db() as conn:
        conn.execute(
            "UPDATE issues SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.utcnow().isoformat(timespec="seconds"), issue_id),
        )

    flash("Issue status updated.", "success")
    return redirect(url_for("index"))


@app.route("/issues/<int:issue_id>/delete", methods=["POST"])
def delete_issue(issue_id):
    with get_db() as conn:
        conn.execute("DELETE FROM issues WHERE id = ?", (issue_id,))

    flash("Issue deleted.", "success")
    return redirect(url_for("index"))


@app.route("/health")
def health():
    return {"status": "ok"}


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
