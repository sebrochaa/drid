import requests
import sqlite3


DATABASE = "drid.db"

FDA_URL = "https://api.fda.gov/drug/drugsfda.json"


# =========================================
# DATABASE
# =========================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# =========================================
# DATABASE UPGRADE
# =========================================

def prepare_database():

    conn = get_db()

    # Add useful FDA fields to the existing drugs table
    existing_columns = [
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(drugs)"
        ).fetchall()
    ]

    new_columns = {
        "application_number": "TEXT",
        "brand_name": "TEXT",
        "generic_name": "TEXT",
        "manufacturer": "TEXT",
        "dosage_form": "TEXT",
        "route": "TEXT",
        "source": "TEXT"
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
# FETCH FDA DATA
# =========================================

def get_fda_records(limit=100):

    print("Connecting to openFDA...")

    response = requests.get(
        FDA_URL,
        params={"limit": limit},
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return data.get("results", [])


# =========================================
# EXTRACT PRODUCT INFORMATION
# =========================================

def extract_products(record):

    application_number = record.get(
        "application_number"
    )

    products = record.get(
        "products",
        []
    )

    manufacturer = record.get(
        "sponsor_name",
        "Unknown"
    )

    extracted = []

    for product in products:

        brand_name = product.get(
            "brand_name"
        )

        dosage_form = product.get(
            "dosage_form"
        )

        route = product.get(
            "route"
        )

        ingredients = product.get(
            "active_ingredients",
            []
        )

        generic_names = []

        for ingredient in ingredients:

            name = ingredient.get("name")

            if name:
                generic_names.append(name)

        generic_name = ", ".join(
            generic_names
        )

        extracted.append({
            "application_number": application_number,
            "brand_name": brand_name,
            "generic_name": generic_name,
            "manufacturer": manufacturer,
            "dosage_form": dosage_form,
            "route": route
        })

    return extracted


# =========================================
# INSERT INTO DRID
# =========================================

def import_records(records):

    conn = get_db()

    imported = 0

    duplicates = 0

    for record in records:

        products = extract_products(record)

        for product in products:

            application_number = product[
                "application_number"
            ]

            brand_name = product[
                "brand_name"
            ]

            generic_name = product[
                "generic_name"
            ]

            manufacturer = product[
                "manufacturer"
            ]

            dosage_form = product[
                "dosage_form"
            ]

            route = product[
                "route"
            ]


            # ---------------------------------
            # CHECK FOR EXISTING RECORD
            # ---------------------------------

            existing = conn.execute(
                """
                SELECT id
                FROM drugs
                WHERE application_number = ?
                AND brand_name = ?
                """,
                (
                    application_number,
                    brand_name
                )
            ).fetchone()


            if existing:

                duplicates += 1

                continue


            # ---------------------------------
            # INSERT
            # ---------------------------------

            conn.execute(
                """
                INSERT INTO drugs (
                    name,
                    phase,
                    status,
                    application_number,
                    brand_name,
                    generic_name,
                    manufacturer,
                    dosage_form,
                    route,
                    source
                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    brand_name or generic_name,

                    "Approved",

                    "FDA Record",

                    application_number,

                    brand_name,

                    generic_name,

                    manufacturer,

                    dosage_form,

                    route,

                    "openFDA"
                )
            )


            imported += 1


    conn.commit()

    conn.close()


    return imported, duplicates


# =========================================
# MAIN
# =========================================

def main():

    print()
    print("======================================")
    print("       DRID DATA IMPORT")
    print("======================================")
    print()


    # Prepare database

    prepare_database()


    # Fetch FDA records

    records = get_fda_records(
        limit=100
    )


    print(
        f"FDA records fetched: {len(records)}"
    )

    print()


    # Import records

    imported, duplicates = import_records(
        records
    )


    print()
    print("--------------------------------------")

    print(
        f"Drugs imported:      {imported}"
    )

    print(
        f"Duplicates skipped:  {duplicates}"
    )

    print(
        "Source:              openFDA"
    )

    print("--------------------------------------")

    print()
    print("Import complete.")
    print()


# =========================================
# RUN
# =========================================

if __name__ == "__main__":

    main()