import sqlite3
import requests
import time


from config import DATABASE_PATH

DATABASE = str(DATABASE_PATH)

CHEMBL_API = "https://www.ebi.ac.uk/chembl/api/data"


# ============================================================
# DATABASE
# ============================================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


def prepare_database():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS indications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

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

    conn.commit()

    conn.close()


# ============================================================
# CHEMBL REQUEST
# ============================================================

def chembl_request(endpoint, params):

    url = f"{CHEMBL_API}/{endpoint}"

    try:

        response = requests.get(
            url,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as error:

        print(
            f"    ChEMBL API error: {error}"
        )

        return None


# ============================================================
# FIND CHEMBL MOLECULE
# ============================================================

def find_chembl_molecule(drug_name):

    data = chembl_request(
        "molecule.json",
        {
            "pref_name__iexact": drug_name,
            "limit": 5
        }
    )

    if not data:
        return None

    molecules = data.get(
        "molecules",
        []
    )

    if not molecules:
        return None

    # Prefer an exact preferred-name match

    normalized_name = drug_name.strip().upper()

    for molecule in molecules:

        pref_name = molecule.get(
            "pref_name"
        )

        if pref_name:

            if pref_name.strip().upper() == normalized_name:

                return molecule

    # Otherwise use the first result

    return molecules[0]


# ============================================================
# FIND MECHANISMS / TARGETS
# ============================================================

def get_mechanisms(chembl_id):

    data = chembl_request(
        "mechanism.json",
        {
            "molecule_chembl_id": chembl_id,
            "limit": 100
        }
    )

    if not data:

        return []

    return data.get(
        "mechanisms",
        []
    )


# ============================================================
# FIND INDICATIONS
# ============================================================

def get_indications(chembl_id):

    data = chembl_request(
        "drug_indication.json",
        {
            "molecule_chembl_id": chembl_id,
            "limit": 100
        }
    )

    if not data:

        return []

    return data.get(
        "drug_indications",
        []
    )


# ============================================================
# TARGET NAME
# ============================================================

def get_target_name(target_chembl_id):

    if not target_chembl_id:

        return None

    data = chembl_request(
        f"target/{target_chembl_id}.json",
        {}
    )

    if not data:

        return None

    target = data.get(
        "target",
        {}
    )

    return (
        target.get("pref_name")
        or target.get("target_type")
    )


# ============================================================
# ADD TARGET
# ============================================================

def add_target(
    conn,
    drug_id,
    target_name
):

    if not target_name:

        return False

    target = conn.execute("""
        SELECT id

        FROM targets

        WHERE name = ?
    """, (
        target_name,
    )).fetchone()

    if target:

        target_id = target["id"]

    else:

        cursor = conn.execute("""
            INSERT INTO targets
            (name)

            VALUES (?)
        """, (
            target_name,
        ))

        target_id = cursor.lastrowid

    existing = conn.execute("""
        SELECT 1

        FROM drug_targets

        WHERE drug_id = ?
        AND target_id = ?
    """, (
        drug_id,
        target_id
    )).fetchone()

    if existing:

        return False

    conn.execute("""
        INSERT INTO drug_targets
        (drug_id, target_id)

        VALUES (?, ?)
    """, (
        drug_id,
        target_id
    ))

    return True


# ============================================================
# ADD INDICATION
# ============================================================

def add_indication(
    conn,
    drug_id,
    indication_name
):

    if not indication_name:

        return False

    indication = conn.execute("""
        SELECT id

        FROM indications

        WHERE name = ?
    """, (
        indication_name,
    )).fetchone()

    if indication:

        indication_id = indication["id"]

    else:

        cursor = conn.execute("""
            INSERT INTO indications
            (name)

            VALUES (?)
        """, (
            indication_name,
        ))

        indication_id = cursor.lastrowid

    existing = conn.execute("""
        SELECT 1

        FROM drug_indications

        WHERE drug_id = ?
        AND indication_id = ?
    """, (
        drug_id,
        indication_id
    )).fetchone()

    if existing:

        return False

    conn.execute("""
        INSERT INTO drug_indications
        (drug_id, indication_id)

        VALUES (?, ?)
    """, (
        drug_id,
        indication_id
    ))

    return True


# ============================================================
# ENRICH DRUGS
# ============================================================

def enrich_drugs():

    conn = get_db()

    drugs = conn.execute("""
        SELECT
            id,
            name

        FROM drugs

        ORDER BY id
    """).fetchall()

    print()
    print("=" * 60)
    print("DRID CHEMBL ENRICHMENT")
    print("=" * 60)
    print()

    print(
        f"Drugs to process: {len(drugs)}"
    )

    print()

    molecule_matches = 0
    target_links = 0
    indication_links = 0
    no_match = 0

    for index, drug in enumerate(
        drugs,
        start=1
    ):

        drug_id = drug["id"]
        drug_name = drug["name"]

        print(
            f"[{index}/{len(drugs)}] "
            f"{drug_name}"
        )

        molecule = find_chembl_molecule(
            drug_name
        )

        if not molecule:

            print(
                "    No ChEMBL molecule match."
            )

            no_match += 1

            time.sleep(0.2)

            continue

        chembl_id = molecule.get(
            "molecule_chembl_id"
        )

        print(
            f"    ChEMBL: {chembl_id}"
        )

        molecule_matches += 1

        # ----------------------------------------------------
        # TARGETS
        # ----------------------------------------------------

        mechanisms = get_mechanisms(
            chembl_id
        )

        added_targets = 0

        for mechanism in mechanisms:

            target_id = mechanism.get(
                "target_chembl_id"
            )

            target_name = (
                mechanism.get(
                    "mechanism_of_action"
                )
            )

            # If mechanism text is missing,
            # retrieve actual target name.

            if not target_name:

                target_name = get_target_name(
                    target_id
                )

            if target_name:

                added = add_target(
                    conn,
                    drug_id,
                    target_name
                )

                if added:

                    added_targets += 1

                    target_links += 1

        # ----------------------------------------------------
        # INDICATIONS
        # ----------------------------------------------------

        indications = get_indications(
            chembl_id
        )

        added_indications = 0

        for indication in indications:

            indication_name = (
                indication.get(
                    "efo_term"
                )
                or indication.get(
                    "mesh_heading"
                )
                or indication.get(
                    "max_phase_for_ind"
                )
            )

            if indication_name:

                added = add_indication(
                    conn,
                    drug_id,
                    str(indication_name)
                )

                if added:

                    added_indications += 1

                    indication_links += 1

        conn.commit()

        print(
            f"    Targets added: {added_targets}"
        )

        print(
            f"    Indications added: "
            f"{added_indications}"
        )

        time.sleep(0.2)

    conn.close()

    print()
    print("=" * 60)
    print("CHEMBL ENRICHMENT COMPLETE")
    print("=" * 60)
    print()

    print(
        f"ChEMBL matches:       {molecule_matches}"
    )

    print(
        f"Target relationships: {target_links}"
    )

    print(
        f"Indication links:     {indication_links}"
    )

    print(
        f"No ChEMBL match:      {no_match}"
    )

    print()


# ============================================================
# MAIN
# ============================================================

def main():

    prepare_database()

    enrich_drugs()


if __name__ == "__main__":

    main()