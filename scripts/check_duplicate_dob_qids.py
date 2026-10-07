import duckdb

DB = r"C:\Users\ADMIN\OneDrive\Documents\important database files\fyucha-player-database-main\fyucha-player-database-main\data\reep-register-v1.duckdb"

print("=" * 70)
print("REEP DOB DUPLICATE QID CHECK")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()

con = duckdb.connect(DB, read_only=True)

q1 = """
SELECT
    qid,
    COUNT(DISTINCT reep_id) AS reep_players
FROM overlay_links
WHERE entity_type = 'player'
  AND lower(trim(dob_check)) = 'dob-agrees'
  AND qid IS NOT NULL
  AND trim(qid) <> ''
GROUP BY qid
HAVING COUNT(DISTINCT reep_id) > 1
ORDER BY reep_players DESC, qid
"""

duplicates = con.execute(q1).fetchall()

print("DUPLICATE QIDS")
print("-" * 70)
print("Number of duplicate QIDs:", len(duplicates))
print()

for row in duplicates:
    print(row)

print()
print("PLAYER DETAILS")
print("-" * 70)

if duplicates:
    duplicate_qids = [row[0] for row in duplicates]

    placeholders = ",".join(["?"] * len(duplicate_qids))

    q2 = f"""
    SELECT
        reep_id,
        qid,
        confidence,
        dob_check
    FROM overlay_links
    WHERE entity_type = 'player'
      AND lower(trim(dob_check)) = 'dob-agrees'
      AND qid IN ({placeholders})
    ORDER BY qid, reep_id
    """

    details = con.execute(q2, duplicate_qids).fetchall()

    for row in details:
        print(row)
else:
    print("No duplicate QIDs found.")

print()
print("=" * 70)
print("CHECK COMPLETE")
print("=" * 70)

con.close()