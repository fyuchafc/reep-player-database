import duckdb

DB = r"C:\Users\ADMIN\OneDrive\Documents\important database files\fyucha-player-database-main\fyucha-player-database-main\data\reep-register-v1.duckdb"

print("=" * 70)
print("REEP DUPLICATE DOB QID EXTERNAL-ID INSPECTION")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()

con = duckdb.connect(DB, read_only=True)

player_ids = [
    'rp9ecbbb4d0876c7',
    'rpb9bade1645adf9',
    'rp802f7e130c21a0',
    'rp9433019ee9f020'
]

placeholders = ",".join(["?"] * len(player_ids))

q = f"""
SELECT
    reep_id,
    provider,
    property,
    external_id,
    rank,
    confidence,
    dob_check,
    qid
FROM overlay_xids
WHERE reep_id IN ({placeholders})
ORDER BY reep_id, provider, property, external_id
"""

rows = con.execute(q, player_ids).fetchall()

print("EXTERNAL ID RECORDS")
print("-" * 70)

current = None

for row in rows:
    if row[0] != current:
        current = row[0]
        print()
        print("REEP ID:", current)

    print(
        "  Provider:", row[1],
        "| Property:", row[2],
        "| External ID:", row[3],
        "| Rank:", row[4],
        "| Confidence:", row[5],
        "| DOB:", row[6],
        "| QID:", row[7]
    )

print()
print("=" * 70)
print("CHECK COMPLETE")
print("=" * 70)

con.close()