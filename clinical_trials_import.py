import sqlite3
import requests
import time


DATABASE = "drid.db"

CLINICAL_TRIALS_URL = (
    "https://clinicaltrials.gov/api/v2/studies"
)


# =========================================
# DATABASE
# =========================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# =========================================
# CREATE TRIALS TABLE
# =========================================

def prepare_database():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS clinical_trials (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            drug_id INTEGER,

            nct_id TEXT UNIQUE,

            title TEXT,

            status TEXT,

            phase TEXT,

            conditions TEXT,

            sponsor TEXT,

            study_type TEXT,

            start_date TEXT,

            completion_date TEXT,

            source TEXT,

            FOREIGN KEY (drug_id)
                REFERENCES drugs(id)

        )
    """)

    conn.commit()

    conn.close()


# =========================================
# SEARCH CLINICALTRIALS.GOV
# =========================================

def search_trials(drug_name, limit=10):

    params = {

        "query.term": drug_name,

        "pageSize": limit,

        "format": "json"

    }


    try:

        response = requests.get(
            CLINICAL_TRIALS_URL,
            params=params,
            timeout=30
        )


        response.raise_for_status()


        return response.json().get(
            "studies",
            []
        )


    except requests.RequestException as error:

        print(
            f"  API error: {error}"
        )

        return []


# =========================================
# EXTRACT TRIAL INFORMATION
# =========================================

def extract_trial(study):

    protocol = study.get(
        "protocolSection",
        {}
    )


    identification = protocol.get(
        "identificationModule",
        {}
    )


    status_module = protocol.get(
        "statusModule",
        {}
    )


    design = protocol.get(
        "designModule",
        {}
    )


    conditions_module = protocol.get(
        "conditionsModule",
        {}
    )


    sponsor_module = protocol.get(
        "sponsorCollaboratorsModule",
        {}
    )


    study_type = design.get(
        "studyType"
    )


    phases = design.get(
        "phases",
        []
    )


    conditions = conditions_module.get(
        "conditions",
        []
    )


    start_date = (
        status_module
        .get("startDateStruct", {})
        .get("date")
    )


    completion_date = (
        status_module
        .get("completionDateStruct", {})
        .get("date")
    )


    lead_sponsor = sponsor_module.get(
        "leadSponsor",
        {}
    )


    sponsor = lead_sponsor.get(
        "name"
    )


    return {

        "nct_id": identification.get(
            "nctId"
        ),

        "title": identification.get(
            "briefTitle"
        ),

        "status": status_module.get(
            "overallStatus"
        ),

        "phase": ", ".join(phases),

        "conditions": ", ".join(
            conditions
        ),

        "sponsor": sponsor,

        "study_type": study_type,

        "start_date": start_date,

        "completion_date": completion_date

    }


# =========================================
# IMPORT TRIALS
# =========================================

def import_trials():

    conn = get_db()


    drugs = conn.execute("""
        SELECT
            id,
            name,
            generic_name

        FROM drugs

        ORDER BY id
    """).fetchall()


    print(
        f"Drugs to process: {len(drugs)}"
    )

    print()


    imported = 0

    duplicates = 0

    errors = 0


    for drug in drugs:

        drug_id = drug["id"]


        drug_name = (
            drug["generic_name"]
            or drug["name"]
        )


        if not drug_name:

            continue


        print(
            f"Searching trials for: {drug_name}"
        )


        studies = search_trials(
            drug_name,
            limit=10
        )


        print(
            f"  Studies returned: {len(studies)}"
        )


        for study in studies:

            trial = extract_trial(
                study
            )


            nct_id = trial["nct_id"]


            if not nct_id:

                errors += 1

                continue


            existing = conn.execute(
                """
                SELECT id

                FROM clinical_trials

                WHERE nct_id = ?
                """,
                (nct_id,)
            ).fetchone()


            if existing:

                duplicates += 1

                continue


            conn.execute(
                """
                INSERT INTO clinical_trials (

                    drug_id,
                    nct_id,
                    title,
                    status,
                    phase,
                    conditions,
                    sponsor,
                    study_type,
                    start_date,
                    completion_date,
                    source

                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,

                (

                    drug_id,

                    trial["nct_id"],

                    trial["title"],

                    trial["status"],

                    trial["phase"],

                    trial["conditions"],

                    trial["sponsor"],

                    trial["study_type"],

                    trial["start_date"],

                    trial["completion_date"],

                    "ClinicalTrials.gov"

                )
            )


            imported += 1


        conn.commit()


        # Small delay between API searches

        time.sleep(0.2)


    conn.close()


    return (
        imported,
        duplicates,
        errors
    )


# =========================================
# MAIN
# =========================================

def main():

    print()

    print(
        "======================================"
    )

    print(
        "   DRID CLINICAL TRIAL IMPORT"
    )

    print(
        "======================================"
    )

    print()


    prepare_database()


    imported, duplicates, errors = (
        import_trials()
    )


    print()

    print(
        "--------------------------------------"
    )

    print(
        f"Trials imported:     {imported}"
    )

    print(
        f"Duplicates skipped:  {duplicates}"
    )

    print(
        f"Errors:              {errors}"
    )

    print(
        "Source:              ClinicalTrials.gov"
    )

    print(
        "--------------------------------------"
    )

    print()

    print(
        "Clinical trial import complete."
    )

    print()


if __name__ == "__main__":

    main()