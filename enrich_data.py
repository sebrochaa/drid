import sqlite3
import requests
import time


DATABASE = "drid.db"

PUBCHEM_URL = (
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
)


# =========================================
# DATABASE
# =========================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# =========================================
# PREPARE DATABASE
# =========================================

def prepare_database():

    conn = get_db()

    existing_columns = [
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(drugs)"
        ).fetchall()
    ]


    new_columns = {

        "pubchem_cid": "INTEGER",

        "molecular_formula": "TEXT",

        "molecular_weight": "TEXT",

        "canonical_smiles": "TEXT",

        "isomeric_smiles": "TEXT"

    }


    for column, data_type in new_columns.items():

        if column not in existing_columns:

            conn.execute(
                f"""
                ALTER TABLE drugs
                ADD COLUMN {column} {data_type}
                """
            )


    conn.commit()

    conn.close()


# =========================================
# PUBCHEM SEARCH
# =========================================

def search_pubchem(drug_name):

    url = (
        f"{PUBCHEM_URL}/compound/name/"
        f"{drug_name}/property/"
        "MolecularFormula,MolecularWeight,"
        "CanonicalSMILES,IsomericSMILES/"
        "JSON"
    )


    try:

        response = requests.get(
            url,
            timeout=30
        )


        if response.status_code == 404:

            return None


        response.raise_for_status()


        data = response.json()


        properties = (
            data
            .get("PropertyTable", {})
            .get("Properties", [])
        )


        if not properties:

            return None


        return properties[0]


    except requests.RequestException as error:

        print(
            f"Request error for {drug_name}: {error}"
        )

        return None


# =========================================
# ENRICH DATABASE
# =========================================

def enrich_drugs():

    conn = get_db()


    drugs = conn.execute("""
        SELECT
            id,
            name,
            generic_name,
            pubchem_cid

        FROM drugs

        WHERE pubchem_cid IS NULL

        ORDER BY id
    """).fetchall()


    print(
        f"Drugs requiring enrichment: {len(drugs)}"
    )

    print()


    enriched = 0

    not_found = 0


    for drug in drugs:

        drug_id = drug["id"]

        drug_name = drug["generic_name"]


        if not drug_name:

            drug_name = drug["name"]


        print(
            f"Searching PubChem: {drug_name}"
        )


        result = search_pubchem(
            drug_name
        )


        if result is None:

            print(
                "  No PubChem record found."
            )

            not_found += 1

            print()

            continue


        cid = result.get("CID")

        formula = result.get(
            "MolecularFormula"
        )

        molecular_weight = result.get(
            "MolecularWeight"
        )

        canonical_smiles = result.get(
            "ConnectivitySMILES"
        )

        isomeric_smiles = result.get(
            "SMILES"
        )


        conn.execute("""
            UPDATE drugs

            SET
                pubchem_cid = ?,
                molecular_formula = ?,
                molecular_weight = ?,
                canonical_smiles = ?,
                isomeric_smiles = ?

            WHERE id = ?
        """, (
            cid,
            formula,
            molecular_weight,
            canonical_smiles,
            isomeric_smiles,
            drug_id
        ))


        conn.commit()


        enriched += 1


        print(
            f"  PubChem CID: {cid}"
        )

        print(
            f"  Formula: {formula}"
        )

        print(
            f"  Molecular weight: {molecular_weight}"
        )

        print()


        # Be respectful of the public API.

        time.sleep(0.2)


    conn.close()


    return enriched, not_found


# =========================================
# MAIN
# =========================================

def main():

    print()

    print(
        "======================================"
    )

    print(
        "       DRID PUBCHEM ENRICHMENT"
    )

    print(
        "======================================"
    )

    print()


    prepare_database()


    enriched, not_found = enrich_drugs()


    print()

    print(
        "--------------------------------------"
    )

    print(
        f"Drugs enriched:      {enriched}"
    )

    print(
        f"Not found:           {not_found}"
    )

    print(
        "Source:              PubChem"
    )

    print(
        "--------------------------------------"
    )

    print()

    print(
        "Enrichment complete."
    )

    print()


# =========================================
# RUN
# =========================================

if __name__ == "__main__":

    main()