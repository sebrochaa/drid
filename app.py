from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

from flask import Flask, render_template, request, redirect, url_for
import sqlite3

from config import DEBUG
from database import get_db, initialize_database


app = Flask(__name__)

# Safe to run on every startup; it only creates or upgrades what is missing.
initialize_database()


# =========================================
# DASHBOARD
# =========================================



@app.route("/")
def home():
    conn = get_db()

    page = max(1, request.args.get("page", 1, type=int))
    per_page = 25

    search_query = request.args.get("search", "", type=str).strip()
    selected_phase = request.args.get("phase", "", type=str).strip()
    selected_source = request.args.get("source", "", type=str).strip()
    target_query = request.args.get("target", "", type=str).strip()
    indication_query = request.args.get(
        "indication",
        "",
        type=str,
    ).strip()

    selected_trials = request.args.get(
        "trials",
        "all",
        type=str,
    ).strip()

    selected_molecular = request.args.get(
        "molecular",
        "all",
        type=str,
    ).strip()

    sort_order = request.args.get(
        "sort",
        "name_asc",
        type=str,
    ).strip()

    allowed_sorts = {
        "name_asc": "d.name COLLATE NOCASE ASC, d.id ASC",
        "name_desc": "d.name COLLATE NOCASE DESC, d.id DESC",
        "most_trials": "trial_count DESC, d.name COLLATE NOCASE ASC",
        "fewest_trials": "trial_count ASC, d.name COLLATE NOCASE ASC",
    }

    if sort_order not in allowed_sorts:
        sort_order = "name_asc"

    if selected_trials not in {"all", "with", "without"}:
        selected_trials = "all"

    if selected_molecular not in {"all", "enriched", "missing"}:
        selected_molecular = "all"

    filters = []
    parameters = []

    if search_query:
        pattern = f"%{search_query}%"

        filters.append(
            """
            (
                d.name LIKE ?
                OR COALESCE(d.generic_name, '') LIKE ?
                OR EXISTS (
                    SELECT 1
                    FROM drug_targets dt
                    JOIN targets t ON t.id = dt.target_id
                    WHERE dt.drug_id = d.id
                    AND t.name LIKE ?
                )
                OR EXISTS (
                    SELECT 1
                    FROM drug_indications di
                    JOIN indications i ON i.id = di.indication_id
                    WHERE di.drug_id = d.id
                    AND i.name LIKE ?
                )
            )
            """
        )

        parameters.extend([pattern, pattern, pattern, pattern])

    if selected_phase:
        filters.append("d.phase = ?")
        parameters.append(selected_phase)

    if selected_source:
        filters.append("d.source = ?")
        parameters.append(selected_source)

    if target_query:
        filters.append(
            """
            EXISTS (
                SELECT 1
                FROM drug_targets dt
                JOIN targets t ON t.id = dt.target_id
                WHERE dt.drug_id = d.id
                AND t.name LIKE ?
            )
            """
        )
        parameters.append(f"%{target_query}%")

    if indication_query:
        filters.append(
            """
            EXISTS (
                SELECT 1
                FROM drug_indications di
                JOIN indications i ON i.id = di.indication_id
                WHERE di.drug_id = d.id
                AND i.name LIKE ?
            )
            """
        )
        parameters.append(f"%{indication_query}%")

    if selected_trials == "with":
        filters.append(
            """
            EXISTS (
                SELECT 1
                FROM clinical_trials ct
                WHERE ct.drug_id = d.id
            )
            """
        )

    elif selected_trials == "without":
        filters.append(
            """
            NOT EXISTS (
                SELECT 1
                FROM clinical_trials ct
                WHERE ct.drug_id = d.id
            )
            """
        )

    if selected_molecular == "enriched":
        filters.append("d.pubchem_cid IS NOT NULL")

    elif selected_molecular == "missing":
        filters.append("d.pubchem_cid IS NULL")

    where_sql = ""

    if filters:
        where_sql = "WHERE " + " AND ".join(filters)

    total_drugs = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM drugs d
        {where_sql}
        """,
        parameters,
    ).fetchone()[0]

    total_pages = max(1, (total_drugs + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page

    drugs = conn.execute(
        f"""
        SELECT
            d.id,
            d.name,
            d.phase,
            d.status,

            (
                SELECT GROUP_CONCAT(t.name, ', ')
                FROM drug_targets dt
                JOIN targets t ON t.id = dt.target_id
                WHERE dt.drug_id = d.id
            ) AS targets,

            (
                SELECT GROUP_CONCAT(i.name, ', ')
                FROM drug_indications di
                JOIN indications i ON i.id = di.indication_id
                WHERE di.drug_id = d.id
            ) AS indications,

            (
                SELECT COUNT(*)
                FROM clinical_trials ct
                WHERE ct.drug_id = d.id
            ) AS trial_count

        FROM drugs d
        {where_sql}

        ORDER BY {allowed_sorts[sort_order]}

        LIMIT ?
        OFFSET ?
        """,
        [*parameters, per_page, offset],
    ).fetchall()

    def build_preview(value):
        if not value:
            return "—"

        items = [
            item.strip()
            for item in value.split(",")
            if item.strip()
        ]

        if len(items) > 2:
            return f"{', '.join(items[:2])} + {len(items) - 2} more"

        return ", ".join(items)

    drug_list = []

    for drug in drugs:
        drug_data = dict(drug)
        drug_data["targets_preview"] = build_preview(
            drug_data["targets"]
        )
        drug_data["indications_preview"] = build_preview(
            drug_data["indications"]
        )
        drug_list.append(drug_data)

    approved_drugs = conn.execute(
        """
        SELECT COUNT(*)
        FROM drugs
        WHERE phase = 'Approved'
        """
    ).fetchone()[0]

    target_count = conn.execute(
        "SELECT COUNT(*) FROM targets"
    ).fetchone()[0]

    indication_count = conn.execute(
        "SELECT COUNT(*) FROM indications"
    ).fetchone()[0]

    trial_count = conn.execute(
        "SELECT COUNT(*) FROM clinical_trials"
    ).fetchone()[0]

    active_trial_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM clinical_trials
        WHERE status IN (
            'RECRUITING',
            'NOT_YET_RECRUITING',
            'ENROLLING_BY_INVITATION',
            'ACTIVE_NOT_RECRUITING'
        )
        """
    ).fetchone()[0]

    enriched_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM drugs
        WHERE pubchem_cid IS NOT NULL
        """
    ).fetchone()[0]

    phase_rows = conn.execute(
        """
        SELECT phase, COUNT(*) AS count
        FROM drugs
        WHERE phase IS NOT NULL
        AND TRIM(phase) != ''
        GROUP BY phase
        ORDER BY count DESC
        """
    ).fetchall()

    phase_distribution = []

    for row in phase_rows:
        percentage = round(
            (row["count"] / max(1, approved_drugs)) * 100
        )

        phase_distribution.append(
            {
                "phase": row["phase"],
                "count": row["count"],
                "percentage": percentage,
            }
        )

    phase_options = [
        row["phase"]
        for row in conn.execute(
            """
            SELECT DISTINCT phase
            FROM drugs
            WHERE phase IS NOT NULL
            AND TRIM(phase) != ''
            ORDER BY phase
            """
        ).fetchall()
    ]

    source_options = [
        row["source"]
        for row in conn.execute(
            """
            SELECT DISTINCT source
            FROM drugs
            WHERE source IS NOT NULL
            AND TRIM(source) != ''
            ORDER BY source
            """
        ).fetchall()
    ]

    conn.close()

    return render_template(
        "index.html",
        drugs=drug_list,
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
        search_query=search_query,
        selected_phase=selected_phase,
        selected_source=selected_source,
        target_query=target_query,
        indication_query=indication_query,
        selected_trials=selected_trials,
        selected_molecular=selected_molecular,
        sort_order=sort_order,
        phase_options=phase_options,
        source_options=source_options,
    )

# =========================================
# SEARCH
# =========================================

@app.route("/search")
def search():

    query = request.args.get(
        "q",
        ""
    ).strip()


    return redirect(
        url_for(
            "home",
            search=query
        )
    )

# =========================================
# CLINICAL TRIAL EXPLORER
# =========================================

@app.route("/trials")
def clinical_trials():

    conn = get_db()

    page = max(
        1,
        request.args.get("page", 1, type=int)
    )

    per_page = 25

    trial_query = request.args.get(
        "q",
        "",
        type=str
    ).strip()

    selected_status = request.args.get(
        "status",
        "",
        type=str
    ).strip()

    selected_phase = request.args.get(
        "phase",
        "",
        type=str
    ).strip()

    sort_order = request.args.get(
        "sort",
        "newest",
        type=str
    ).strip()

    allowed_sorts = {
        "newest": (
            "ct.start_date IS NULL ASC, "
            "ct.start_date DESC, "
            "ct.id DESC"
        ),
        "oldest": (
            "ct.start_date IS NULL ASC, "
            "ct.start_date ASC, "
            "ct.id ASC"
        ),
        "drug": (
            "d.name COLLATE NOCASE ASC, "
            "ct.start_date DESC"
        ),
        "status": (
            "ct.status COLLATE NOCASE ASC, "
            "ct.start_date DESC"
        ),
    }

    if sort_order not in allowed_sorts:
        sort_order = "newest"

    filters = []
    parameters = []

    if trial_query:

        pattern = f"%{trial_query}%"

        filters.append(
            """
            (
                ct.nct_id LIKE ?
                OR ct.title LIKE ?
                OR ct.conditions LIKE ?
                OR ct.sponsor LIKE ?
                OR d.name LIKE ?
            )
            """
        )

        parameters.extend(
            [pattern, pattern, pattern, pattern, pattern]
        )

    if selected_status:

        filters.append("ct.status = ?")
        parameters.append(selected_status)

    if selected_phase:

        filters.append("ct.phase LIKE ?")
        parameters.append(f"%{selected_phase}%")

    where_sql = ""

    if filters:
        where_sql = "WHERE " + " AND ".join(filters)

    total_trials = conn.execute(
        f"""
        SELECT COUNT(*)

        FROM clinical_trials ct

        LEFT JOIN drugs d
            ON d.id = ct.drug_id

        {where_sql}
        """,
        parameters,
    ).fetchone()[0]

    total_pages = max(
        1,
        (total_trials + per_page - 1) // per_page
    )

    page = min(page, total_pages)
    offset = (page - 1) * per_page

    trials = conn.execute(
        f"""
        SELECT
            ct.id,
            ct.drug_id,
            ct.nct_id,
            ct.title,
            ct.status,
            ct.phase,
            ct.conditions,
            ct.sponsor,
            ct.study_type,
            ct.start_date,
            ct.completion_date,
            d.name AS drug_name

        FROM clinical_trials ct

        LEFT JOIN drugs d
            ON d.id = ct.drug_id

        {where_sql}

        ORDER BY {allowed_sorts[sort_order]}

        LIMIT ?
        OFFSET ?
        """,
        [*parameters, per_page, offset],
    ).fetchall()

    total_trial_count = conn.execute(
        "SELECT COUNT(*) FROM clinical_trials"
    ).fetchone()[0]

    recruiting_count = conn.execute(
        """
        SELECT COUNT(*)

        FROM clinical_trials

        WHERE status = 'RECRUITING'
        """
    ).fetchone()[0]

    active_trial_count = conn.execute(
        """
        SELECT COUNT(*)

        FROM clinical_trials

        WHERE status IN (
            'RECRUITING',
            'NOT_YET_RECRUITING',
            'ENROLLING_BY_INVITATION',
            'ACTIVE_NOT_RECRUITING'
        )
        """
    ).fetchone()[0]

    compounds_with_trials = conn.execute(
        """
        SELECT COUNT(DISTINCT drug_id)

        FROM clinical_trials

        WHERE drug_id IS NOT NULL
        """
    ).fetchone()[0]

    status_options = [
        row["status"]
        for row in conn.execute(
            """
            SELECT DISTINCT status

            FROM clinical_trials

            WHERE status IS NOT NULL
            AND TRIM(status) != ''

            ORDER BY status
            """
        ).fetchall()
    ]

    conn.close()

    return render_template(
        "trials.html",
        trials=trials,
        total_trials=total_trials,
        total_trial_count=total_trial_count,
        recruiting_count=recruiting_count,
        active_trial_count=active_trial_count,
        compounds_with_trials=compounds_with_trials,
        status_options=status_options,
        page=page,
        total_pages=total_pages,
        per_page=per_page,
        trial_query=trial_query,
        selected_status=selected_status,
        selected_phase=selected_phase,
        sort_order=sort_order,
    )

# =========================================
# THERAPEUTIC AREAS
# =========================================

@app.route("/therapeutic-areas")
def therapeutic_areas():

    conn = get_db()

    page = max(
        1,
        request.args.get("page", 1, type=int)
    )

    per_page = 25

    area_query = request.args.get(
        "q",
        "",
        type=str
    ).strip()

    study_filter = request.args.get(
        "studies",
        "all",
        type=str
    ).strip()

    sort_order = request.args.get(
        "sort",
        "most_compounds",
        type=str
    ).strip()

    allowed_sorts = {
        "most_compounds": (
            "compound_count DESC, "
            "i.name COLLATE NOCASE ASC"
        ),
        "most_trials": (
            "trial_count DESC, "
            "i.name COLLATE NOCASE ASC"
        ),
        "most_active": (
            "active_trial_count DESC, "
            "i.name COLLATE NOCASE ASC"
        ),
        "name_asc": (
            "i.name COLLATE NOCASE ASC"
        ),
    }

    if sort_order not in allowed_sorts:
        sort_order = "most_compounds"

    if study_filter not in {"all", "with", "without"}:
        study_filter = "all"

    filters = []
    parameters = []

    if area_query:

        filters.append("i.name LIKE ?")
        parameters.append(f"%{area_query}%")

    if study_filter == "with":

        filters.append(
            """
            EXISTS (
                SELECT 1

                FROM drug_indications di_check

                JOIN clinical_trials ct_check
                    ON ct_check.drug_id = di_check.drug_id

                WHERE di_check.indication_id = i.id
            )
            """
        )

    elif study_filter == "without":

        filters.append(
            """
            NOT EXISTS (
                SELECT 1

                FROM drug_indications di_check

                JOIN clinical_trials ct_check
                    ON ct_check.drug_id = di_check.drug_id

                WHERE di_check.indication_id = i.id
            )
            """
        )

    where_sql = ""

    if filters:
        where_sql = "WHERE " + " AND ".join(filters)

    total_areas = conn.execute(
        f"""
        SELECT COUNT(*)

        FROM indications i

        {where_sql}
        """,
        parameters,
    ).fetchone()[0]

    total_pages = max(
        1,
        (total_areas + per_page - 1) // per_page
    )

    page = min(page, total_pages)
    offset = (page - 1) * per_page

    areas = conn.execute(
        f"""
        SELECT
            i.id,
            i.name,

            COUNT(DISTINCT di.drug_id) AS compound_count,

            COUNT(DISTINCT ct.id) AS trial_count,

            COUNT(
                DISTINCT CASE
                    WHEN ct.status IN (
                        'RECRUITING',
                        'NOT_YET_RECRUITING',
                        'ENROLLING_BY_INVITATION',
                        'ACTIVE_NOT_RECRUITING'
                    )
                    THEN ct.id
                END
            ) AS active_trial_count

        FROM indications i

        LEFT JOIN drug_indications di
            ON di.indication_id = i.id

        LEFT JOIN clinical_trials ct
            ON ct.drug_id = di.drug_id

        {where_sql}

        GROUP BY i.id, i.name

        ORDER BY {allowed_sorts[sort_order]}

        LIMIT ?
        OFFSET ?
        """,
        [*parameters, per_page, offset],
    ).fetchall()

    total_area_count = conn.execute(
        "SELECT COUNT(*) FROM indications"
    ).fetchone()[0]

    areas_with_compounds = conn.execute(
        """
        SELECT COUNT(DISTINCT indication_id)

        FROM drug_indications
        """
    ).fetchone()[0]

    areas_with_trials = conn.execute(
        """
        SELECT COUNT(DISTINCT di.indication_id)

        FROM drug_indications di

        JOIN clinical_trials ct
            ON ct.drug_id = di.drug_id
        """
    ).fetchone()[0]

    top_area = conn.execute(
        """
        SELECT
            i.name,
            COUNT(DISTINCT di.drug_id) AS compound_count

        FROM indications i

        LEFT JOIN drug_indications di
            ON di.indication_id = i.id

        GROUP BY i.id, i.name

        ORDER BY compound_count DESC, i.name ASC

        LIMIT 1
        """
    ).fetchone()

    conn.close()

    return render_template(
        "therapeutic_areas.html",
        areas=areas,
        total_areas=total_areas,
        total_area_count=total_area_count,
        areas_with_compounds=areas_with_compounds,
        areas_with_trials=areas_with_trials,
        top_area=top_area,
        page=page,
        total_pages=total_pages,
        per_page=per_page,
        area_query=area_query,
        study_filter=study_filter,
        sort_order=sort_order,
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
        SELECT

            targets.name

        FROM targets

        JOIN drug_targets
            ON targets.id = drug_targets.target_id

        WHERE
            drug_targets.drug_id = ?

        ORDER BY targets.name

    """, (drug_id,)).fetchall()


    # =====================================
    # INDICATIONS
    # =====================================

    indications = conn.execute("""
        SELECT

            indications.name

        FROM indications

        JOIN drug_indications
            ON indications.id = drug_indications.indication_id

        WHERE
            drug_indications.drug_id = ?

        ORDER BY indications.name

    """, (drug_id,)).fetchall()


    # =====================================
    # CLINICAL TRIALS
    # =====================================

    try:

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

    except sqlite3.OperationalError:

        clinical_trials = []


    # =====================================
    # TRIAL STATISTICS
    # =====================================

    trial_count = len(clinical_trials)


    try:

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

    except sqlite3.OperationalError:

        recruiting_count = 0


    conn.close()


    # =====================================
    # RENDER DRUG PROFILE
    # =====================================

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
    app.run(debug=DEBUG)