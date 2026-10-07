import duckdb

DB = r"C:\Users\ADMIN\OneDrive\Documents\important database files\fyucha-player-database-main\fyucha-player-database-main\data\reep-register-v1.duckdb"

print("=" * 70)
print("REEP DOB → QID COVERAGE CHECK")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()

con = duckdb.connect(DB, read_only=True)

q1 = """
SELECT
    COUNT(DISTINCT reep_id) AS players,
    COUNT(DISTINCT qid) AS qids
FROM overlay_links
WHERE entity_type = 'player'
  AND lower(trim(dob_check)) = 'dob-agrees'
  AND qid IS NOT NULL
  AND trim(qid) <> ''
"""

q2 = """
SELECT COUNT(DISTINCT reep_id)
FROM overlay_links
WHERE entity_type = 'player'
  AND lower(trim(dob_check)) = 'dob-agrees'
"""

q3 = """
SELECT
    reep_id,
    qid,
    confidence,
    dob_check
FROM overlay_links
WHERE entity_type = 'player'
  AND lower(trim(dob_check)) = 'dob-agrees'
  AND qid IS NOT NULL
  AND trim(qid) <> ''
ORDER BY reep_id
LIMIT 20
"""

confirmed_with_qid = con.execute(q1).fetchone()
all_confirmed = con.execute(q2).fetchone()[0]
sample_qids = con.execute(q3).fetchall()

print("CONFIRMED DOB PLAYERS WITH QID:")
print(f"  Players: {confirmed_with_qid[0]:,}")
print(f"  Unique QIDs: {confirmed_with_qid[1]:,}")
print()

print("ALL CONFIRMED DOB PLAYERS:")
print(f"  Players: {all_confirmed:,}")
print()

if all_confirmed > 0:
    coverage = confirmed_with_qid[0] / all_confirmed * 100
    print(f"QID COVERAGE OF CONFIRMED DOB PLAYERS: {coverage:.2f}%")
else:
    print("QID COVERAGE: 0.00%")

print()
print("SAMPLE QIDS:")
print("-" * 70)

for row in sample_qids:
    print(row)

print()
print("=" * 70)
print("CHECK COMPLETE")
print("=" * 70)

con.close()