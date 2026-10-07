import duckdb

DB = r"C:\Users\ADMIN\OneDrive\Documents\important database files\fyucha-player-database-main\fyucha-player-database-main\data\reep-register-v1.duckdb"

print("=" * 70)
print("REEP DUPLICATE DOB QID IDENTITY INSPECTION")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()

con = duckdb.connect(DB, read_only=True)

q = """
SELECT
    e.reep_id,
    e.label,
    e.entity_type,
    e.status,
    e.gender,
    e.country,
    e.corroboration_grade,
    e.corroboration_count,
    ol.qid,
    ol.confidence,
    ol.dob_check
FROM entities e
JOIN overlay_links ol
    ON e.reep_id = ol.reep_id
WHERE ol.entity_type = 'player'
  AND lower(trim(ol.dob_check)) = 'dob-agrees'
  AND ol.qid IN ('Q30103478', 'Q56611021')
ORDER BY ol.qid, e.reep_id
"""

rows = con.execute(q).fetchall()

print("PLAYER IDENTITY DETAILS")
print("-" * 70)

for row in rows:
    print(row)

print()
print("ALIASES")
print("-" * 70)

q2 = """
SELECT
    a.reep_id,
    a.alias,
    a.kind,
    a.rank,
    a.language
FROM aliases a
WHERE a.reep_id IN (
    'rp9ecbbb4d0876c7',
    'rpb9bade1645adf9',
    'rp802f7e130c21a0',
    'rp9433019ee9f020'
)
ORDER BY a.reep_id, a.rank, a.alias
"""

for row in con.execute(q2).fetchall():
    print(row)

print()
print("=" * 70)
print("CHECK COMPLETE")
print("=" * 70)

con.close()