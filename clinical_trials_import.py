import sqlite3
import requests
import time


from config import DATABASE_PATH

DATABASE = str(DATABASE_PATH)

CLINICAL_TRIALS_URL = "https://clinicaltrials.gov/api/v2/studies"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


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
            FOREIGN KEY (drug_id) REFERENCES drugs(id)
        )
    """)

    conn.commit()
    conn.close()


def search_trials(drug_name, limit=100):
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

        return response.json().get("studies", [])

    except requests.RequestException as error:
        print(f"  API error: {error}")
        return []


def extract_trial(study, drug_name):

    protocol = study.get("protocolSection", {})

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

    interventions_module = protocol.get(
        "armsInterventionsModule",
        {}
    )

    interventions = interventions_module.get(
        "interventions",
        []
    )

    normalized_drug = drug_name.lower().strip()

    drug_found = False

    # =====================================
    # CHECK INTERVENTIONS
    # =====================================

    for intervention in interventions:

        intervention_name = intervention.get(
            "name",
            ""
        ).lower().strip()

        # Exact match
        if normalized_drug == intervention_name:
            drug_found = True
            break

        # Partial match
        if normalized_drug in intervention_name:
            drug_found = True
            break

        if intervention_name in normalized_drug:
            drug_found = True
            break


    # =====================================
    # CHECK STUDY TITLE
    # =====================================

    title = identification.get(
        "briefTitle",
        ""
    )

    if title:

        title_lower = title.lower()

        if normalized_drug in title_lower:
            drug_found = True


    # =====================================
    # CHECK CONDITIONS
    # =====================================

    conditions = conditions_module.get(
        "conditions",
        []
    )

    for condition in conditions:

        condition_lower = condition.lower()

        if normalized_drug in condition_lower:
            drug_found = True
            break


    if not drug_found:
        return None


    # =====================================
    # TRIAL INFORMATION
    # =====================================

    phases = design.get(
        "phases",
        []
    )


    lead_sponsor = sponsor_module.get(
        "leadSponsor",
        {}
    )


    start_date = status_module.get(
        "startDateStruct",
        {}
    ).get(
        "date"
    )


    completion_date = status_module.get(
        "completionDateStruct",
        {}
    ).get(
        "date"
    )


    return {

        "nct_id": identification.get(
            "nctId"
        ),

        "title": title,

        "status": status_module.get(
            "overallStatus"
        ),

        "phase": ", ".join(phases),

        "conditions": ", ".join(conditions),

        "sponsor": lead_sponsor.get(
            "name"
        ),

        "study_type": design.get(
            "studyType"
        ),

        "start_date": start_date,

        "completion_date": completion_date

    }


def import_trials():

    conn = get_db()

    drugs = conn.execute("""
        SELECT id, name
        FROM drugs
        ORDER BY id
    """).fetchall()

    print(f"Drugs to process: {len(drugs)}")
    print()

    imported = 0
    rejected = 0
    duplicates = 0

    for drug in drugs:

        drug_id = drug["id"]
        drug_name = drug["name"]

        if not drug_name:
            continue

        print(
            f"Searching trials for: {drug_name}"
        )

        studies = search_trials(
            drug_name,
            limit=100
        )

        print(
            f"  Candidate studies: {len(studies)}"
        )

        for study in studies:

            trial = extract_trial(
                study,
                drug_name
            )

            if trial is None:
                rejected += 1
                continue

            nct_id = trial["nct_id"]

            if not nct_id:
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

        time.sleep(0.2)

    conn.close()

    return imported, rejected, duplicates


def main():

    print()
    print("======================================")
    print("   DRID CLINICAL TRIAL IMPORT")
    print("======================================")
    print()

    prepare_database()

    imported, rejected, duplicates = import_trials()

    print()
    print("--------------------------------------")
    print(f"Trials imported:     {imported}")
    print(f"Studies rejected:    {rejected}")
    print(f"Duplicates skipped:  {duplicates}")
    print("--------------------------------------")
    print()
    print("Clinical trial import complete.")


if __name__ == "__main__":
    main()