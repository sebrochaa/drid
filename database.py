import sqlite3

from config import DATABASE_PATH


DRUG_COLUMNS = {
    "application_number": "TEXT",
    "brand_name": "TEXT",
    "generic_name": "TEXT",
    "manufacturer": "TEXT",
    "dosage_form": "TEXT",
    "route": "TEXT",
    "source": "TEXT",
    "pubchem_cid": "INTEGER",
    "molecular_formula": "TEXT",
    "molecular_weight": "TEXT",
    "canonical_smiles": "TEXT",
    "isomeric_smiles": "TEXT",
}


def get_db():
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _add_missing_columns(conn, table_name, columns):
    existing_columns = {
        row["name"]
        for row in conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    }

    for column_name, column_type in columns.items():
        if column_name not in existing_columns:
            conn.execute(
                f"""
                ALTER TABLE {table_name}
                ADD COLUMN {column_name} {column_type}
                """
            )


def _seed_sample_data(conn):
    has_drugs = conn.execute(
        "SELECT 1 FROM drugs LIMIT 1"
    ).fetchone()

    if has_drugs:
        return

    drugs = [
        ("Aspirin", "Approved", "Established"),
        ("Metformin", "Approved", "Established"),
        ("Pembrolizumab", "Approved", "Established"),
        ("Semaglutide", "Approved", "Established"),
        ("Tirzepatide", "Approved", "Established"),
    ]

    conn.executemany(
        """
        INSERT INTO drugs (name, phase, status)
        VALUES (?, ?, ?)
        """,
        drugs,
    )

    targets = [
        "COX-1",
        "COX-2",
        "AMPK",
        "PD-1",
        "GLP-1 receptor",
        "GIP receptor",
    ]

    indications = [
        "Pain",
        "Inflammation",
        "Cardiovascular prevention",
        "Type 2 diabetes",
        "Obesity",
        "Cancer",
    ]

    for name in targets:
        conn.execute(
            "INSERT OR IGNORE INTO targets (name) VALUES (?)",
            (name,),
        )

    for name in indications:
        conn.execute(
            "INSERT OR IGNORE INTO indications (name) VALUES (?)",
            (name,),
        )

    target_links = [
        ("Aspirin", "COX-1"),
        ("Aspirin", "COX-2"),
        ("Metformin", "AMPK"),
        ("Pembrolizumab", "PD-1"),
        ("Semaglutide", "GLP-1 receptor"),
        ("Tirzepatide", "GLP-1 receptor"),
        ("Tirzepatide", "GIP receptor"),
    ]

    indication_links = [
        ("Aspirin", "Pain"),
        ("Aspirin", "Inflammation"),
        ("Aspirin", "Cardiovascular prevention"),
        ("Metformin", "Type 2 diabetes"),
        ("Pembrolizumab", "Cancer"),
        ("Semaglutide", "Type 2 diabetes"),
        ("Semaglutide", "Obesity"),
        ("Tirzepatide", "Type 2 diabetes"),
        ("Tirzepatide", "Obesity"),
    ]

    for drug_name, target_name in target_links:
        drug_id = conn.execute(
            "SELECT id FROM drugs WHERE name = ?",
            (drug_name,),
        ).fetchone()["id"]

        target_id = conn.execute(
            "SELECT id FROM targets WHERE name = ?",
            (target_name,),
        ).fetchone()["id"]

        conn.execute(
            """
            INSERT OR IGNORE INTO drug_targets (drug_id, target_id)
            VALUES (?, ?)
            """,
            (drug_id, target_id),
        )

    for drug_name, indication_name in indication_links:
        drug_id = conn.execute(
            "SELECT id FROM drugs WHERE name = ?",
            (drug_name,),
        ).fetchone()["id"]

        indication_id = conn.execute(
            "SELECT id FROM indications WHERE name = ?",
            (indication_name,),
        ).fetchone()["id"]

        conn.execute(
            """
            INSERT OR IGNORE INTO drug_indications (drug_id, indication_id)
            VALUES (?, ?)
            """,
            (drug_id, indication_id),
        )


def initialize_database():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS drugs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phase TEXT,
                status TEXT,
                application_number TEXT,
                brand_name TEXT,
                generic_name TEXT,
                manufacturer TEXT,
                dosage_form TEXT,
                route TEXT,
                source TEXT,
                pubchem_cid INTEGER,
                molecular_formula TEXT,
                molecular_weight TEXT,
                canonical_smiles TEXT,
                isomeric_smiles TEXT
            );

            CREATE TABLE IF NOT EXISTS targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE
            );

            CREATE TABLE IF NOT EXISTS indications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE
            );

            CREATE TABLE IF NOT EXISTS drug_targets (
                drug_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                PRIMARY KEY (drug_id, target_id),
                FOREIGN KEY (drug_id) REFERENCES drugs(id),
                FOREIGN KEY (target_id) REFERENCES targets(id)
            );

            CREATE TABLE IF NOT EXISTS drug_indications (
                drug_id INTEGER NOT NULL,
                indication_id INTEGER NOT NULL,
                PRIMARY KEY (drug_id, indication_id),
                FOREIGN KEY (drug_id) REFERENCES drugs(id),
                FOREIGN KEY (indication_id) REFERENCES indications(id)
            );

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
            );

            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_drugs_name
                ON drugs(name);

            CREATE INDEX IF NOT EXISTS idx_drug_targets_target
                ON drug_targets(target_id);

            CREATE INDEX IF NOT EXISTS idx_drug_indications_indication
                ON drug_indications(indication_id);

            CREATE INDEX IF NOT EXISTS idx_clinical_trials_drug_date
                ON clinical_trials(drug_id, start_date DESC);
            """
        )

        _add_missing_columns(conn, "drugs", DRUG_COLUMNS)
        _seed_sample_data(conn)

        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations (version)
            VALUES (1)
            """
        )