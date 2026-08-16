import sqlite3
from config import DATABASE_PATH

conn = sqlite3.connect(DATABASE_PATH)
conn.row_factory = sqlite3.Row

drugs = ["Aspirin", "Metformin", "Pembrolizumab", "Semaglutide", "Tirzepatide"]

for drug_name in drugs:

    print()
    print("=" * 60)
    print(f"{drug_name.upper()} TRIALS")
    print("=" * 60)

    drug = conn.execute(
        "SELECT id FROM drugs WHERE name = ?",
        (drug_name,)
    ).fetchone()

    if not drug:
        print("Drug not found")
        continue

    trials = conn.execute("""
        SELECT
            nct_id,
            title,
            status,
            phase
        FROM clinical_trials
        WHERE drug_id = ?
        ORDER BY start_date DESC
        LIMIT 5
    """, (drug["id"],)).fetchall()

    if not trials:
        print("NO TRIALS FOUND")
        continue

    print(f"Trials found: {len(trials)}")
    print()

    for trial in trials:
        print(f"{trial['nct_id']} | {trial['status']} | {trial['phase']}")
        print(f"  {trial['title']}")
        print()

conn.close()