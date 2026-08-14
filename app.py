from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)

DATABASE = "drid.db"


# =========================================
# DATABASE CONNECTION
# =========================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================
# DATABASE SETUP
# =========================================

def initialize_database():

    conn = get_db()

    # -----------------------------
    # DRUGS
    # -----------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS drugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phase TEXT,
            status TEXT
        )
    """)


    # -----------------------------
    # TARGETS
    # -----------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)


    # -----------------------------
    # INDICATIONS
    # -----------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS indications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)


    # -----------------------------
    # DRUG ↔ TARGET
    # -----------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS drug_targets (
            drug_id INTEGER,
            target_id INTEGER,

            PRIMARY KEY (drug_id, target_id),

            FOREIGN KEY (drug_id)
                REFERENCES drugs(id),

            FOREIGN KEY (target_id)
                REFERENCES targets(id)
        )
    """)


    # -----------------------------
    # DRUG ↔ INDICATION
    # -----------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS drug_indications (
            drug_id INTEGER,
            indication_id INTEGER,

            PRIMARY KEY (drug_id, indication_id),

            FOREIGN KEY (drug_id)
                REFERENCES drugs(id),

            FOREIGN KEY (indication_id)
                REFERENCES indications(id)
        )
    """)


    # =====================================
    # SAMPLE DATA
    # =====================================

    drug_count = conn.execute(
        "SELECT COUNT(*) FROM drugs"
    ).fetchone()[0]


    if drug_count == 0:

        # -----------------------------
        # DRUGS
        # -----------------------------

        drugs = [
            ("Aspirin", "Approved", "Established"),
            ("Metformin", "Approved", "Established"),
            ("Pembrolizumab", "Approved", "Established"),
            ("Semaglutide", "Approved", "Established"),
            ("Tirzepatide", "Approved", "Established")
        ]


        conn.executemany("""
            INSERT INTO drugs
            (name, phase, status)
            VALUES (?, ?, ?)
        """, drugs)


        # -----------------------------
        # TARGETS
        # -----------------------------

        targets = [
            ("COX-1",),
            ("COX-2",),
            ("AMPK",),
            ("PD-1",),
            ("GLP-1 receptor",),
            ("GIP receptor",)
        ]


        conn.executemany("""
            INSERT OR IGNORE INTO targets
            (name)
            VALUES (?)
        """, targets)


        # -----------------------------
        # INDICATIONS
        # -----------------------------

        indications = [
            ("Pain",),
            ("Inflammation",),
            ("Cardiovascular prevention",),
            ("Type 2 diabetes",),
            ("Obesity",),
            ("Cancer",)
        ]


        conn.executemany("""
            INSERT OR IGNORE INTO indications
            (name)
            VALUES (?)
        """, indications)


        # -----------------------------
        # DRUG TARGET RELATIONSHIPS
        # -----------------------------

        relationships = [

            (1, "COX-1"),
            (1, "COX-2"),

            (2, "AMPK"),

            (3, "PD-1"),

            (4, "GLP-1 receptor"),

            (5, "GLP-1 receptor"),
            (5, "GIP receptor")
        ]


        for drug_id, target_name in relationships:

            target = conn.execute("""
                SELECT id
                FROM targets
                WHERE name = ?
            """, (target_name,)).fetchone()


            conn.execute("""
                INSERT OR IGNORE INTO drug_targets
                (drug_id, target_id)
                VALUES (?, ?)
            """, (
                drug_id,
                target["id"]
            ))


        # -----------------------------
        # DRUG INDICATION RELATIONSHIPS
        # -----------------------------

        indications_relationships = [

            (1, "Pain"),
            (1, "Inflammation"),
            (1, "Cardiovascular prevention"),

            (2, "Type 2 diabetes"),

            (3, "Cancer"),

            (4, "Type 2 diabetes"),
            (4, "Obesity"),

            (5, "Type 2 diabetes"),
            (5, "Obesity")
        ]


        for drug_id, indication_name in indications_relationships:

            indication = conn.execute("""
                SELECT id
                FROM indications
                WHERE name = ?
            """, (indication_name,)).fetchone()


            conn.execute("""
                INSERT OR IGNORE INTO drug_indications
                (drug_id, indication_id)
                VALUES (?, ?)
            """, (
                drug_id,
                indication["id"]
            ))


    conn.commit()

    conn.close()


# =========================================
# DASHBOARD
# =========================================

@app.route("/")
def home():

    conn = get_db()


    drugs = conn.execute("""
        SELECT
            drugs.id,
            drugs.name,
            drugs.phase,
            drugs.status,

            GROUP_CONCAT(
                DISTINCT targets.name
            ) AS targets,

            GROUP_CONCAT(
                DISTINCT indications.name
            ) AS indications

        FROM drugs

        LEFT JOIN drug_targets
            ON drugs.id = drug_targets.drug_id

        LEFT JOIN targets
            ON drug_targets.target_id = targets.id

        LEFT JOIN drug_indications
            ON drugs.id = drug_indications.drug_id

        LEFT JOIN indications
            ON drug_indications.indication_id = indications.id

        GROUP BY drugs.id

        ORDER BY drugs.name
    """).fetchall()


    total_drugs = conn.execute("""
        SELECT COUNT(*)
        FROM drugs
    """).fetchone()[0]


    approved_drugs = conn.execute("""
        SELECT COUNT(*)
        FROM drugs
        WHERE phase = 'Approved'
    """).fetchone()[0]


    target_count = conn.execute("""
        SELECT COUNT(*)
        FROM targets
    """).fetchone()[0]


    indication_count = conn.execute("""
        SELECT COUNT(*)
        FROM indications
    """).fetchone()[0]


    conn.close()


    return render_template(
        "index.html",
        drugs=drugs,
        total_drugs=total_drugs,
        approved_drugs=approved_drugs,
        target_count=target_count,
        indication_count=indication_count
    )


# =========================================
# SEARCH
# =========================================

@app.route("/search")
def search():

    query = request.args.get("q", "").strip()

    conn = get_db()


    if query:

        search_pattern = f"%{query}%"


        drugs = conn.execute("""
            SELECT
                drugs.id,
                drugs.name,
                drugs.phase,
                drugs.status,

                GROUP_CONCAT(
                    DISTINCT targets.name
                ) AS targets,

                GROUP_CONCAT(
                    DISTINCT indications.name
                ) AS indications

            FROM drugs

            LEFT JOIN drug_targets
                ON drugs.id = drug_targets.drug_id

            LEFT JOIN targets
                ON drug_targets.target_id = targets.id

            LEFT JOIN drug_indications
                ON drugs.id = drug_indications.drug_id

            LEFT JOIN indications
                ON drug_indications.indication_id = indications.id

            WHERE
                drugs.name LIKE ?
                OR targets.name LIKE ?
                OR indications.name LIKE ?
                OR drugs.phase LIKE ?
                OR drugs.status LIKE ?

            GROUP BY drugs.id

            ORDER BY drugs.name
        """, (
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern
        )).fetchall()


    else:

        drugs = conn.execute("""
            SELECT
                drugs.id,
                drugs.name,
                drugs.phase,
                drugs.status,

                GROUP_CONCAT(
                    DISTINCT targets.name
                ) AS targets,

                GROUP_CONCAT(
                    DISTINCT indications.name
                ) AS indications

            FROM drugs

            LEFT JOIN drug_targets
                ON drugs.id = drug_targets.drug_id

            LEFT JOIN targets
                ON drug_targets.target_id = targets.id

            LEFT JOIN drug_indications
                ON drugs.id = drug_indications.drug_id

            LEFT JOIN indications
                ON drug_indications.indication_id = indications.id

            GROUP BY drugs.id

            ORDER BY drugs.name
        """).fetchall()


    total_drugs = conn.execute(
        "SELECT COUNT(*) FROM drugs"
    ).fetchone()[0]


    approved_drugs = conn.execute("""
        SELECT COUNT(*)
        FROM drugs
        WHERE phase = 'Approved'
    """).fetchone()[0]


    target_count = conn.execute(
        "SELECT COUNT(*) FROM targets"
    ).fetchone()[0]


    indication_count = conn.execute(
        "SELECT COUNT(*) FROM indications"
    ).fetchone()[0]


    conn.close()


    return render_template(
        "index.html",
        drugs=drugs,
        search_query=query,
        total_drugs=total_drugs,
        approved_drugs=approved_drugs,
        target_count=target_count,
        indication_count=indication_count
    )


# =========================================
# DRUG PROFILE
# =========================================

@app.route("/drug/<int:drug_id>")
def drug_profile(drug_id):

    conn = get_db()


    drug = conn.execute("""
        SELECT *
        FROM drugs
        WHERE id = ?
    """, (drug_id,)).fetchone()


    if drug is None:

        conn.close()

        return "Drug not found", 404


    targets = conn.execute("""
        SELECT targets.name

        FROM targets

        JOIN drug_targets
            ON targets.id = drug_targets.target_id

        WHERE drug_targets.drug_id = ?

        ORDER BY targets.name
    """, (drug_id,)).fetchall()


    indications = conn.execute("""
        SELECT indications.name

        FROM indications

        JOIN drug_indications
            ON indications.id = drug_indications.indication_id

        WHERE drug_indications.drug_id = ?

        ORDER BY indications.name
    """, (drug_id,)).fetchall()


    conn.close()


    return render_template(
        "drug.html",
        drug=drug,
        targets=targets,
        indications=indications
    )


# =========================================
# START APPLICATION
# =========================================

if __name__ == "__main__":

    initialize_database()

    app.run(debug=True)