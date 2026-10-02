import csv
import json
import os
from collections import Counter, defaultdict

import duckdb


# ============================================================
# REEP PLAYER DOB SOURCES AUDIT
# READ-ONLY
# ============================================================

BASE_DIR = r"C:\Users\ADMIN\OneDrive\Documents\important database files\reep-player-database-main"

DB_PATH = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_DIR = os.path.join(BASE_DIR, "output")

CSV_PATH = os.path.join(
    OUTPUT_DIR,
    "reep-player-dob-sources.csv"
)

JSON_PATH = os.path.join(
    OUTPUT_DIR,
    "reep-player-dob-sources.json"
)


# ============================================================
# HELPERS
# ============================================================

def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def pct(part, total):
    if not total:
        return 0.0
    return round((part / total) * 100, 2)


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# START
# ============================================================

print("=" * 70)
print("REEP PLAYER DOB SOURCES AUDIT")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()
print("Source database:")
print(DB_PATH)
print()

if not os.path.isfile(DB_PATH):
    raise FileNotFoundError(
        f"Database not found:\n{DB_PATH}"
    )

ensure_output_dir()

print("Opening REEP database READ-ONLY...")

con = duckdb.connect(
    database=DB_PATH,
    read_only=True
)

print("Connected successfully.")
print()


# ============================================================
# CHECK REQUIRED TABLES
# ============================================================

print("=" * 70)
print("CHECKING REQUIRED TABLES")
print("=" * 70)

tables = {
    row[0]
    for row in con.execute(
        "SHOW TABLES"
    ).fetchall()
}

required_tables = [
    "players",
    "overlay_links",
    "overlay_xids",
]

for table in required_tables:
    if table in tables:
        print(f"  {table:<20} FOUND")
    else:
        print(f"  {table:<20} MISSING")

missing = [
    table for table in required_tables
    if table not in tables
]

if missing:
    raise RuntimeError(
        "Required table(s) missing: "
        + ", ".join(missing)
    )

print()


# ============================================================
# PLAYER MASTER
# ============================================================

print("=" * 70)
print("LOADING PLAYER MASTER")
print("=" * 70)

player_rows = con.execute(
    """
    SELECT
        reep_id,
        label,
        status,
        gender
    FROM players
    """
).fetchall()

players = {}

for reep_id, label, status, gender in player_rows:
    players[str(reep_id)] = {
        "reep_id": str(reep_id),
        "label": clean(label),
        "status": clean(status),
        "gender": clean(gender),
    }

total_players = len(players)

print(f"Total REEP players: {total_players:,}")
print()


# ============================================================
# PLAYER-LEVEL DOB EVIDENCE STRUCTURE
# ============================================================

player_data = {}

for reep_id, info in players.items():
    player_data[reep_id] = {
        "reep_id": reep_id,
        "label": info["label"],
        "status": info["status"],
        "gender": info["gender"],

        "qid_rows": 0,
        "qid_dob_agrees": 0,
        "qid_dob_unverified": 0,
        "qid_other_dob_status": 0,

        "xid_rows": 0,
        "xid_dob_agrees": 0,
        "xid_dob_unverified": 0,
        "xid_other_dob_status": 0,

        "providers": set(),

        "provider_statuses": defaultdict(set),
    }


# ============================================================
# QID / OVERLAY LINK DOB EVIDENCE
# ============================================================

print("=" * 70)
print("ANALYSING QID / OVERLAY-LINK DOB EVIDENCE")
print("=" * 70)

qid_rows = con.execute(
    """
    SELECT
        CAST(reep_id AS VARCHAR) AS reep_id,
        dob_check
    FROM overlay_links
    WHERE reep_id IS NOT NULL
    """
).fetchall()

qid_player_rows = 0

qid_status_counter = Counter()

for reep_id, dob_check in qid_rows:

    reep_id = clean(reep_id)

    if reep_id not in player_data:
        continue

    qid_player_rows += 1

    status = clean(dob_check)

    row_data = player_data[reep_id]

    row_data["qid_rows"] += 1

    qid_status_counter[status or "NULL"] += 1

    if status == "dob-agrees":
        row_data["qid_dob_agrees"] += 1

    elif status == "dob-unverified":
        row_data["qid_dob_unverified"] += 1

    else:
        row_data["qid_other_dob_status"] += 1


print(
    f"Overlay-link rows belonging to players: "
    f"{qid_player_rows:,}"
)

print("QID DOB statuses:")

for status, count in qid_status_counter.most_common():
    print(
        f"  {status:<25} {count:>10,}"
    )

print()


# ============================================================
# EXTERNAL-ID DOB EVIDENCE
# ============================================================

print("=" * 70)
print("ANALYSING EXTERNAL-ID DOB EVIDENCE")
print("=" * 70)

xid_rows = con.execute(
    """
    SELECT
        CAST(reep_id AS VARCHAR) AS reep_id,
        provider,
        dob_check
    FROM overlay_xids
    WHERE reep_id IS NOT NULL
    """
).fetchall()

xid_player_rows = 0

xid_status_counter = Counter()

provider_player_status = defaultdict(
    lambda: {
        "players": set(),
        "dob_agrees": set(),
        "dob_unverified": set(),
        "other": set(),
    }
)

for reep_id, provider, dob_check in xid_rows:

    reep_id = clean(reep_id)

    if reep_id not in player_data:
        continue

    xid_player_rows += 1

    provider = clean(provider)
    status = clean(dob_check)

    row_data = player_data[reep_id]

    row_data["xid_rows"] += 1

    xid_status_counter[status or "NULL"] += 1

    if provider:
        row_data["providers"].add(provider)

        if status:
            row_data["provider_statuses"][provider].add(status)

        provider_player_status[provider]["players"].add(reep_id)

    if status == "dob-agrees":

        row_data["xid_dob_agrees"] += 1

        if provider:
            provider_player_status[provider][
                "dob_agrees"
            ].add(reep_id)

    elif status == "dob-unverified":

        row_data["xid_dob_unverified"] += 1

        if provider:
            provider_player_status[provider][
                "dob_unverified"
            ].add(reep_id)

    else:

        row_data["xid_other_dob_status"] += 1

        if provider:
            provider_player_status[provider][
                "other"
            ].add(reep_id)


print(
    f"External-ID rows belonging to players: "
    f"{xid_player_rows:,}"
)

print("External-ID DOB statuses:")

for status, count in xid_status_counter.most_common():
    print(
        f"  {status:<25} {count:>10,}"
    )

print()


# ============================================================
# PLAYER-LEVEL CLASSIFICATION
# ============================================================

print("=" * 70)
print("CLASSIFYING PLAYER DOB SUPPORT")
print("=" * 70)

summary_counts = Counter()

provider_count_distribution = Counter()

provider_count_for_dob_players = Counter()

dob_players = []

for reep_id, row in player_data.items():

    qid_agrees = row["qid_dob_agrees"] > 0
    qid_unverified = row["qid_dob_unverified"] > 0

    xid_agrees = row["xid_dob_agrees"] > 0
    xid_unverified = row["xid_dob_unverified"] > 0

    has_qid_evidence = (
        qid_agrees or qid_unverified
    )

    has_xid_evidence = (
        xid_agrees or xid_unverified
    )

    has_dob_evidence = (
        has_qid_evidence or has_xid_evidence
    )

    row["has_qid_dob_evidence"] = has_qid_evidence
    row["has_xid_dob_evidence"] = has_xid_evidence
    row["has_dob_evidence"] = has_dob_evidence

    row["dob_agrees"] = (
        qid_agrees or xid_agrees
    )

    row["dob_unverified"] = (
        qid_unverified or xid_unverified
    )

    row["provider_count"] = len(row["providers"])

    row["mixed_dob_status"] = (
        row["dob_agrees"]
        and row["dob_unverified"]
    )

    if has_dob_evidence:
        dob_players.append(reep_id)

        provider_count_for_dob_players[
            row["provider_count"]
        ] += 1

    # --------------------------------------------------------
    # Overall DOB classification
    # --------------------------------------------------------

    if not has_dob_evidence:

        classification = "no_dob_evidence"

    elif row["mixed_dob_status"]:

        classification = "mixed_dob_status"

    elif row["dob_agrees"]:

        classification = "dob_agrees"

    elif row["dob_unverified"]:

        classification = "dob_unverified_only"

    else:

        classification = "other"

    row["dob_classification"] = classification

    summary_counts[classification] += 1

    # --------------------------------------------------------
    # Evidence pathway
    # --------------------------------------------------------

    if has_qid_evidence and has_xid_evidence:

        pathway = "qid_and_xid"

    elif has_qid_evidence:

        pathway = "qid_only"

    elif has_xid_evidence:

        pathway = "xid_only"

    else:

        pathway = "none"

    row["dob_evidence_pathway"] = pathway

    # --------------------------------------------------------
    # Provider count
    # --------------------------------------------------------

    if has_dob_evidence:

        if row["provider_count"] == 0:
            provider_class = "no_provider"

        elif row["provider_count"] == 1:
            provider_class = "single_provider"

        else:
            provider_class = "multiple_providers"

        row["provider_support_class"] = provider_class

        provider_count_distribution[
            provider_class
        ] += 1

    else:

        row["provider_support_class"] = "no_dob_evidence"


print("DOB classification:")

classification_order = [
    "dob_agrees",
    "dob_unverified_only",
    "mixed_dob_status",
    "no_dob_evidence",
    "other",
]

for key in classification_order:

    count = summary_counts[key]

    print(
        f"  {key:<25} "
        f"{count:>10,} "
        f"({pct(count, total_players):>6.2f}%)"
    )

print()

print("DOB evidence pathways:")

pathway_counts = Counter(
    row["dob_evidence_pathway"]
    for row in player_data.values()
)

for pathway, count in pathway_counts.most_common():

    print(
        f"  {pathway:<25} "
        f"{count:>10,} "
        f"({pct(count, total_players):>6.2f}%)"
    )

print()

print("Provider support among DOB-evidence players:")

for key in [
    "single_provider",
    "multiple_providers",
    "no_provider",
]:

    count = provider_count_distribution[key]

    print(
        f"  {key:<25} "
        f"{count:>10,}"
    )

print()


# ============================================================
# PROVIDER COVERAGE
# ============================================================

print("=" * 70)
print("TOP DOB PROVIDERS")
print("=" * 70)

provider_summary = []

for provider, data in provider_player_status.items():

    players_count = len(data["players"])
    agrees_count = len(data["dob_agrees"])
    unverified_count = len(data["dob_unverified"])
    other_count = len(data["other"])

    provider_summary.append({
        "provider": provider,
        "players": players_count,
        "dob_agrees": agrees_count,
        "dob_unverified": unverified_count,
        "other": other_count,
    })

provider_summary.sort(
    key=lambda x: x["players"],
    reverse=True
)

for item in provider_summary[:25]:

    print(
        f"  {item['provider']:<30} "
        f"{item['players']:>9,} players | "
        f"agrees {item['dob_agrees']:>9,} | "
        f"unverified {item['dob_unverified']:>7,}"
    )

print()


# ============================================================
# PROVIDER COUNT DISTRIBUTION
# ============================================================

print("=" * 70)
print("DOB PROVIDER COUNT DISTRIBUTION")
print("=" * 70)

for provider_count in sorted(
    provider_count_for_dob_players
):

    count = provider_count_for_dob_players[
        provider_count
    ]

    print(
        f"  {provider_count:>3} provider(s): "
        f"{count:>10,} players"
    )

print()


# ============================================================
# MIXED STATUS DETAILS
# ============================================================

mixed_players = [
    row
    for row in player_data.values()
    if row["mixed_dob_status"]
]

print("=" * 70)
print("MIXED DOB VERIFICATION STATUS")
print("=" * 70)

print(
    "Players having both dob-agrees and "
    "dob-unverified evidence:"
)
print(f"  {len(mixed_players):,}")

print()

if mixed_players:

    print("Sample:")
    print()

    for row in mixed_players[:20]:

        print(
            f"  {row['reep_id']} | "
            f"{row['label']} | "
            f"providers={row['provider_count']} | "
            f"QID agrees={row['qid_dob_agrees']} | "
            f"QID unverified={row['qid_dob_unverified']} | "
            f"XID agrees={row['xid_dob_agrees']} | "
            f"XID unverified={row['xid_dob_unverified']}"
        )

print()


# ============================================================
# UNVERIFIED-ONLY DETAILS
# ============================================================

unverified_only_players = [
    row
    for row in player_data.values()
    if row["dob_classification"] == "dob_unverified_only"
]

print("=" * 70)
print("UNVERIFIED-ONLY DOB PLAYERS")
print("=" * 70)

print(
    f"Players with only unverified DOB evidence: "
    f"{len(unverified_only_players):,}"
)

print()


# ============================================================
# CSV OUTPUT
# ============================================================

print("=" * 70)
print("WRITING PLAYER-LEVEL CSV")
print("=" * 70)

fieldnames = [
    "reep_id",
    "label",
    "status",
    "gender",

    "has_dob_evidence",

    "dob_classification",
    "dob_evidence_pathway",

    "has_qid_dob_evidence",
    "qid_rows",
    "qid_dob_agrees",
    "qid_dob_unverified",
    "qid_other_dob_status",

    "has_xid_dob_evidence",
    "xid_rows",
    "xid_dob_agrees",
    "xid_dob_unverified",
    "xid_other_dob_status",

    "dob_agrees",
    "dob_unverified",
    "mixed_dob_status",

    "provider_count",
    "provider_support_class",
    "providers",
]

with open(
    CSV_PATH,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()

    for reep_id in sorted(
        player_data,
        key=lambda x: (
            player_data[x]["label"].lower(),
            x
        )
    ):

        row = player_data[reep_id]

        writer.writerow({
            "reep_id": row["reep_id"],
            "label": row["label"],
            "status": row["status"],
            "gender": row["gender"],

            "has_dob_evidence": row[
                "has_dob_evidence"
            ],

            "dob_classification": row[
                "dob_classification"
            ],

            "dob_evidence_pathway": row[
                "dob_evidence_pathway"
            ],

            "has_qid_dob_evidence": row[
                "has_qid_dob_evidence"
            ],

            "qid_rows": row["qid_rows"],
            "qid_dob_agrees": row[
                "qid_dob_agrees"
            ],
            "qid_dob_unverified": row[
                "qid_dob_unverified"
            ],
            "qid_other_dob_status": row[
                "qid_other_dob_status"
            ],

            "has_xid_dob_evidence": row[
                "has_xid_dob_evidence"
            ],

            "xid_rows": row["xid_rows"],
            "xid_dob_agrees": row[
                "xid_dob_agrees"
            ],
            "xid_dob_unverified": row[
                "xid_dob_unverified"
            ],
            "xid_other_dob_status": row[
                "xid_other_dob_status"
            ],

            "dob_agrees": row["dob_agrees"],
            "dob_unverified": row[
                "dob_unverified"
            ],

            "mixed_dob_status": row[
                "mixed_dob_status"
            ],

            "provider_count": row[
                "provider_count"
            ],

            "provider_support_class": row[
                "provider_support_class"
            ],

            "providers": ";".join(
                sorted(row["providers"])
            ),
        })


# ============================================================
# JSON SUMMARY
# ============================================================

json_summary = {
    "audit": "REEP PLAYER DOB SOURCES AUDIT",
    "read_only": True,
    "source_database": DB_PATH,

    "total_players": total_players,

    "qid_player_rows": qid_player_rows,
    "xid_player_rows": xid_player_rows,

    "players_with_dob_evidence": len(
        dob_players
    ),

    "dob_classification": {
        key: summary_counts[key]
        for key in classification_order
    },

    "dob_evidence_pathways": dict(
        pathway_counts
    ),

    "provider_support": {
        key: provider_count_distribution[key]
        for key in [
            "single_provider",
            "multiple_providers",
            "no_provider",
        ]
    },

    "provider_count_distribution": {
        str(key): value
        for key, value
        in sorted(
            provider_count_for_dob_players.items()
        )
    },

    "top_providers": provider_summary[:50],

    "mixed_dob_status_players": len(
        mixed_players
    ),

    "unverified_only_players": len(
        unverified_only_players
    ),

    "outputs": {
        "csv": CSV_PATH,
        "json": JSON_PATH,
    },

    "source_database_modified": False,
}


with open(
    JSON_PATH,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        json_summary,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# FINAL
# ============================================================

print("=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)

print()
print("Output files:")
print(CSV_PATH)
print(JSON_PATH)

print()
print("SOURCE DATABASE UNMODIFIED")
print("AUDIT MODE READ-ONLY")
print()

con.close()