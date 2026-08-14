from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)

DATABASE = "drid.db"


# -----------------------------
# DATABASE
# -----------------------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS drugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            target TEXT,
            indication TEXT,
            phase TEXT,
            status TEXT
        )
    """)

    # Only add sample data if database is empty
    count = conn.execute(
        "SELECT COUNT(*) FROM drugs"
    ).fetchone()[0]

    if count == 0:

        sample_drugs = [
            (
                "Aspirin",
                "COX-1 / COX-2",
                "Pain, inflammation, cardiovascular prevention",
                "Approved",
                "Established"
            ),
            (
                "Metformin",
                "AMPK",
                "Type 2 diabetes",
                "Approved",
                "Established"
            ),
            (
                "Pembrolizumab",
                "PD-1",
                "Multiple cancers",
                "Approved",
                "Established"
            ),
            (
                "Semaglutide",
                "GLP-1 receptor",
                "Type 2 diabetes, obesity",
                "Approved",
                "Established"
            ),
            (
                "Tirzepatide",
                "GIP / GLP-1 receptors",
                "Type 2 diabetes, obesity",
                "Approved",
                "Established"
            )
        ]

        conn.executemany("""
            INSERT INTO drugs
            (name, target, indication, phase, status)
            VALUES (?, ?, ?, ?, ?)
        """, sample_drugs)

    conn.commit()
    conn.close()


# -----------------------------
# ROUTES
# -----------------------------

@app.route("/")
def home():

    conn = get_db()

    drugs = conn.execute("""
        SELECT *
        FROM drugs
        ORDER BY name
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        drugs=drugs
    )


@app.route("/search")
def search():

    query = request.args.get("q", "").strip()

    conn = get_db()

    if query:

        search_pattern = f"%{query}%"

        drugs = conn.execute("""
            SELECT *
            FROM drugs
            WHERE name LIKE ?
               OR target LIKE ?
               OR indication LIKE ?
               OR phase LIKE ?
               OR status LIKE ?
            ORDER BY name
        """, (
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern
        )).fetchall()

    else:

        drugs = conn.execute("""
            SELECT *
            FROM drugs
            ORDER BY name
        """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        drugs=drugs,
        search_query=query
    )


# -----------------------------
# START APPLICATION
# -----------------------------

if __name__ == "__main__":

    initialize_database()

    app.run(debug=True)