from flask import Flask, render_template, request, redirect, url_for
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


    # =====================================
    # PAGINATION
    # =====================================

    page = request.args.get(
        "page",
        1,
        type=int
    )

    per_page = 25


    search_query = request.args.get(
        "search",
        "",
        type=str
    ).strip()


    if page < 1:

        page = 1


    # =====================================
    # COMPOUND QUERY
    # =====================================

    if search_query:

        search_pattern = f"%{search_query}%"


        total_drugs = conn.execute("""
            SELECT COUNT(*)
            FROM drugs

            WHERE
                name LIKE ?

                OR EXISTS (
                    SELECT 1
                    FROM drug_targets
                    JOIN targets
                        ON targets.id = drug_targets.target_id

                    WHERE
                        drug_targets.drug_id = drugs.id
                        AND targets.name LIKE ?
                )

                OR EXISTS (
                    SELECT 1
                    FROM drug_indications
                    JOIN indications
                        ON indications.id = drug_indications.indication_id

                    WHERE
                        drug_indications.drug_id = drugs.id
                        AND indications.name LIKE ?
                )
        """, (
            search_pattern,
            search_pattern,
            search_pattern
        )).fetchone()[0]


        offset = (page - 1) * per_page


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

                OR EXISTS (
                    SELECT 1
                    FROM drug_targets dt

                    JOIN targets t
                        ON t.id = dt.target_id

                    WHERE
                        dt.drug_id = drugs.id
                        AND t.name LIKE ?
                )

                OR EXISTS (
                    SELECT 1
                    FROM drug_indications di

                    JOIN indications i
                        ON i.id = di.indication_id

                    WHERE
                        di.drug_id = drugs.id
                        AND i.name LIKE ?
                )

            GROUP BY drugs.id

            ORDER BY drugs.name

            LIMIT ?
            OFFSET ?
        """, (
            search_pattern,
            search_pattern,
            search_pattern,
            per_page,
            offset
        )).fetchall()


    else:

        total_drugs = conn.execute("""
            SELECT COUNT(*)
            FROM drugs
        """).fetchone()[0]


        offset = (page - 1) * per_page


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

            LIMIT ?
            OFFSET ?
        """, (
            per_page,
            offset
        )).fetchall()


    # =====================================
    # PAGE COUNT
    # =====================================

    total_pages = max(
        1,
        (total_drugs + per_page - 1)
        // per_page
    )


    if page > total_pages:

        page = total_pages


    # =====================================
    # DASHBOARD STATISTICS
    # =====================================

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


    # =====================================
    # PHASE DISTRIBUTION
    # =====================================

    phase_rows = conn.execute("""
        SELECT
            phase,
            COUNT(*) AS count

        FROM drugs

        WHERE
            phase IS NOT NULL
            AND TRIM(phase) != ''

        GROUP BY phase

        ORDER BY count DESC
    """).fetchall()


    phase_distribution = []


    if total_drugs > 0:

        for row in phase_rows:

            percentage = round(
                (row["count"] / total_drugs) * 100
            )


            phase_distribution.append({
                "phase": row["phase"],
                "count": row["count"],
                "percentage": percentage
            })


    # =====================================
    # CLINICAL TRIAL STATISTICS
    # =====================================

    try:

        trial_count = conn.execute("""
            SELECT COUNT(*)
            FROM clinical_trials
        """).fetchone()[0]


        active_trial_count = conn.execute("""
            SELECT COUNT(*)
            FROM clinical_trials

            WHERE status IN (
                'RECRUITING',
                'NOT_YET_RECRUITING',
                'ENROLLING_BY_INVITATION',
                'ACTIVE_NOT_RECRUITING'
            )
        """).fetchone()[0]


    except sqlite3.OperationalError:

        trial_count = 0

        active_trial_count = 0


    # =====================================
    # PUBCHEM STATISTICS
    # =====================================

    try:

        enriched_count = conn.execute("""
            SELECT COUNT(*)
            FROM drugs

            WHERE pubchem_cid IS NOT NULL
        """).fetchone()[0]


    except sqlite3.OperationalError:

        enriched_count = 0


    conn.close()


    # =====================================
    # RENDER DASHBOARD
    # =====================================

    return render_template(

        "index.html",

        drugs=drugs,

        total_drugs=total_drugs,

        approved_drugs=approved_drugs,

        target_count=target_count,

        indication_count=indication_count,

        trial_count=trial_count,

        active_trial_count=active_trial_count,

        enriched_count=enriched_count,

        phase_distribution=phase_distribution,

        page=page,

        total_pages=total_pages,

        per_page=per_page,

        search_query=search_query

    )


# =========================================
# SEARCH
# =========================================

@app.route("/search")
def search():

    query = request.args.get("q", "").strip()

    return redirect(
        url_for(
            "home",
            search=query
        )
    )

# =========================================
# DRUG PROFILE
# =========================================

@app.route("/drug/<int:drug_id>")
def drug_profile(drug_id):

    conn = get_db()


    # =====================================
    # DRUG
    # =====================================

    drug = conn.execute("""
        SELECT *
        FROM drugs
        WHERE id = ?
    """, (drug_id,)).fetchone()


    if drug is None:

        conn.close()

        return "Drug not found", 404


    # =====================================
    # TARGETS
    # =====================================

    targets = conn.execute("""
        SELECT targets.name

        FROM targets

        JOIN drug_targets
            ON targets.id = drug_targets.target_id

        WHERE drug_targets.drug_id = ?

        ORDER BY targets.name

    """, (drug_id,)).fetchall()


    # =====================================
    # INDICATIONS
    # =====================================

    indications = conn.execute("""
        SELECT indications.name

        FROM indications

        JOIN drug_indications
            ON indications.id = drug_indications.indication_id

        WHERE drug_indications.drug_id = ?

        ORDER BY indications.name

    """, (drug_id,)).fetchall()


    # =====================================
    # CLINICAL TRIALS
    # =====================================

    clinical_trials = conn.execute("""
        SELECT

            nct_id,
            title,
            status,
            phase,
            conditions,
            sponsor,
            study_type,
            start_date,
            completion_date

        FROM clinical_trials

        WHERE drug_id = ?

        ORDER BY start_date DESC

    """, (drug_id,)).fetchall()


    # =====================================
    # TRIAL STATISTICS
    # =====================================

    trial_count = len(clinical_trials)


    recruiting_count = conn.execute("""
        SELECT COUNT(*)

        FROM clinical_trials

        WHERE drug_id = ?

        AND status IN (

            'RECRUITING',
            'NOT_YET_RECRUITING',
            'ENROLLING_BY_INVITATION',
            'ACTIVE_NOT_RECRUITING'

        )

    """, (drug_id,)).fetchone()[0]


    conn.close()


    return render_template(

        "drug.html",

        drug=drug,

        targets=targets,

        indications=indications,

        clinical_trials=clinical_trials,

        trial_count=trial_count,

        recruiting_count=recruiting_count

    )


# =========================================
# START APPLICATION
# =========================================

if __name__ == "__main__":

    initialize_database()

    app.run(debug=True)