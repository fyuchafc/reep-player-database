from pathlib import Path
from datetime import date
import re
import unicodedata
import json
import csv
from urllib.request import Request, urlopen
from urllib.parse import quote, urlencode

import duckdb
from fastapi import FastAPI, HTTPException, Query, Request as FastAPIRequest
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from api.popularity import POPULAR_PLAYERS

ROOT = Path(__file__).resolve().parent.parent

# Keep accepted birthday lookups separate from broad player search.
BIRTHDAY_DB_PATH = ROOT / "output" / "reep-birthday-tool-v1.0.duckdb"
DOB_EVIDENCE_DB_PATH = ROOT / "output" / "reep-player-dob-evidence.duckdb"
ALIAS_LOOKUP_DB_PATH = ROOT / "output" / "reep-player-alias-lookup.duckdb"

app = FastAPI(
    title="Fyucha FC Birthday API",
    description=(
        "Football birthdays, player records, and DOB evidence "
        "powered by the REEP database."
    ),
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def normalize_text(value):
    """Normalize accents and case for more forgiving name searches."""
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )
    return value.casefold().strip()


def query_db(sql, params=None, db_path=None):
    """Run a read-only query against the requested REEP database."""
    if db_path is None:
        db_path = BIRTHDAY_DB_PATH

    if not db_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Database file was not found: {db_path.name}",
        )

    try:
        with duckdb.connect(str(db_path), read_only=True) as conn:
            cursor = conn.execute(sql, params or [])
            columns = [item[0] for item in cursor.description]
            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {exc}",
        )


def dob_date_fields():
    """SQL expressions for month/day extracted from an ISO DOB."""
    return """
        CASE
            WHEN dob IS NOT NULL AND length(dob) >= 10
            THEN try_cast(substr(dob, 6, 2) AS INTEGER)
            ELSE NULL
        END AS birth_month,
        CASE
            WHEN dob IS NOT NULL AND length(dob) >= 10
            THEN try_cast(substr(dob, 9, 2) AS INTEGER)
            ELSE NULL
        END AS birth_day
    """


def popularity_case_sql():
    """Rank curated players even when their full label contains middle names."""
    clauses = []
    for name, score in sorted(
        POPULAR_PLAYERS.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        conditions = []
        for token in name.split():
            pattern = (
                r"(^|[^a-z0-9])"
                + re.escape(token)
                + r"([^a-z0-9]|$)"
            )
            pattern = pattern.replace("'", "''")
            conditions.append(
                "regexp_matches(lower(strip_accents(label)), "
                f"'{pattern}')"
            )

        clauses.append(
            f"WHEN {' AND '.join(conditions)} THEN {int(score)}"
        )

    return "CASE " + " ".join(clauses) + " ELSE 0 END"


@app.get("/")
def home():
    return {
        "name": "Fyucha FC Birthday API",
        "version": "1.2.0",
        "status": "online",
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    birthday_rows = query_db(
        "SELECT COUNT(*) AS total FROM birthday_players",
        db_path=BIRTHDAY_DB_PATH,
    )
    evidence_rows = query_db(
        "SELECT COUNT(*) AS total FROM player_dob",
        db_path=DOB_EVIDENCE_DB_PATH,
    )

    return {
        "status": "ok",
        "version": "1.2.0",
        "birthday_database": BIRTHDAY_DB_PATH.name,
        "birthday_players": birthday_rows[0]["total"],
        "dob_evidence_database": DOB_EVIDENCE_DB_PATH.name,
        "dob_evidence_players": evidence_rows[0]["total"],
    }


@app.get("/api/birthdays")
def birthdays(
    date_value: str = Query(
        default=None,
        alias="date",
        description="Birthday in MM-DD format, e.g. 10-09",
    ),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
):
    if date_value is None:
        today = date.today()
        month, day = today.month, today.day
    else:
        try:
            month_text, day_text = date_value.split("-")
            month, day = int(month_text), int(day_text)
            date(2000, month, day)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail="Use a valid MM-DD date, such as 10-09 or 02-29.",
            )

    count = query_db(
        """
        SELECT COUNT(*) AS total
        FROM birthday_players
        WHERE birth_month = ? AND birth_day = ?
        """,
        [month, day],
        db_path=BIRTHDAY_DB_PATH,
    )[0]["total"]

    offset = (page - 1) * limit

    players = query_db(
        f"""
        SELECT
            reep_id, label, gender, dob, birth_month, birth_day
        FROM birthday_players
        WHERE birth_month = ? AND birth_day = ?
        ORDER BY {popularity_case_sql()} DESC, lower(strip_accents(label)), label
        LIMIT ? OFFSET ?
        """,
        [month, day, limit, offset],
        db_path=BIRTHDAY_DB_PATH,
    )

    return {
        "date": f"{month:02d}-{day:02d}",
        "total": count,
        "page": page,
        "limit": limit,
        "results": players,
    }


@app.get("/api/search")
def search_players(
    q: str = Query(min_length=2, max_length=100),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
):
    term = q.strip()
    normalized_term = normalize_text(term)
    tokens = re.findall(r"[^\W_]+", normalized_term, flags=re.UNICODE)

    if not tokens:
        raise HTTPException(
            status_code=400,
            detail="Enter a valid player name or search term.",
        )

    label_conditions = []
    alias_conditions = []
    token_params = []

    for token in tokens:
        pattern = r"(?i)(^|[^a-z0-9])" + re.escape(token)
        label_conditions.append("regexp_matches(strip_accents(p.label), ?)")
        alias_conditions.append("regexp_matches(strip_accents(a.alias), ?)")
        token_params.append(pattern)

    label_match = " AND ".join(label_conditions)
    alias_match = " AND ".join(alias_conditions)
    where_clause = f"""
        (
            ({label_match})
            OR EXISTS (
                SELECT 1
                FROM aliasdb.main.aliases a
                WHERE a.reep_id = p.reep_id
                  AND ({alias_match})
            )
        )
    """

    exact_name = normalize_text(term)
    prefix_pattern = (
        exact_name.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_") + "%"
    )

    def run_search(sql, params):
        if not DOB_EVIDENCE_DB_PATH.is_file() or not ALIAS_LOOKUP_DB_PATH.is_file():
            raise HTTPException(status_code=500, detail="Required database file not found.")
        con = duckdb.connect(str(DOB_EVIDENCE_DB_PATH), read_only=True)
        try:
            ap = str(ALIAS_LOOKUP_DB_PATH).replace("\\", "/").replace("'", "''")
            con.execute(f"ATTACH '{ap}' AS aliasdb (READ_ONLY)")
            cursor = con.execute(sql, params)
            columns = [item[0] for item in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            con.close()

    known_alias_first = """
        CASE WHEN EXISTS (
            SELECT 1
            FROM aliasdb.main.aliases a
            WHERE a.reep_id = p.reep_id
              AND lower(strip_accents(a.alias)) = ?
              AND lower(a.kind) = 'known_name'
        ) THEN 0 ELSE 1 END
    """

    count_rows = run_search(
        f"""
        SELECT COUNT(*) AS total
        FROM main.player_dob p
        WHERE {where_clause}
        """,
        token_params + token_params,
    )
    total = count_rows[0]["total"]

    popularity_sql = popularity_case_sql().replace("label", "p.label")

    players = run_search(
        f"""
        SELECT
            p.reep_id,
            p.label,
            p.gender,
            p.dob,
            {dob_date_fields()},
            p.dob_status,
            p.dob_precision,
            p.evidence_reason,
            p.source,
            p.source_qid,
            p.resolved_qid,
            p.corroboration_grade,
            p.corroboration_count,
            p.claim_count
        FROM main.player_dob p
        WHERE {where_clause}
        ORDER BY
            {known_alias_first},
            CASE WHEN lower(strip_accents(p.label)) = ? THEN 0 ELSE 1 END,
            {popularity_sql} DESC,
            CASE WHEN lower(strip_accents(p.label)) LIKE ? THEN 0 ELSE 1 END,
            lower(strip_accents(p.label)),
            p.label
        LIMIT ? OFFSET ?
        """,
        token_params + token_params + [
            exact_name,
            exact_name,
            prefix_pattern,
            limit,
            (page - 1) * limit,
        ],
    )

    return {
        "query": term,
        "total": total,
        "page": page,
        "limit": limit,
        "database": DOB_EVIDENCE_DB_PATH.name,
        "results": players,
    }


# Local portraits are kept outside both DuckDB databases.
PORTRAIT_CATALOGUE_PATH = ROOT / "data" / "portrait_review" / "portrait_catalogue.csv"
PORTRAIT_IMAGE_DIR = ROOT / "data" / "portrait_review" / "images"


def approved_local_portrait_path(reep_id: str):
    """Find a downloaded local image only if its catalogue entry is approved."""
    if not re.fullmatch(r"rp[a-zA-Z0-9]+", reep_id):
        return None
    if not PORTRAIT_CATALOGUE_PATH.is_file():
        return None

    try:
        with PORTRAIT_CATALOGUE_PATH.open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            for row in csv.DictReader(handle):
                if row.get("reep_id") != reep_id:
                    continue
                if (row.get("review_status") or "").strip().lower() != "approved":
                    continue
                if (row.get("download_status") or "").strip().lower() != "downloaded":
                    continue

                filename = (row.get("local_filename") or "").strip()
                if not filename or Path(filename).name != filename:
                    continue

                image_path = PORTRAIT_IMAGE_DIR / filename
                allowed = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
                if image_path.is_file() and image_path.suffix.lower() in allowed:
                    return image_path
    except (OSError, csv.Error):
        return None

    return None


@app.get("/api/local-player-image/{reep_id}")
def local_player_image(reep_id: str):
    """Serve an approved local portrait file."""
    image_path = approved_local_portrait_path(reep_id)
    if image_path is None:
        raise HTTPException(status_code=404, detail="Approved local portrait not found.")

    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return FileResponse(
        path=image_path,
        media_type=media_types[image_path.suffix.lower()],
        headers={"Cache-Control": "public, max-age=3600"},
    )


# In-memory cache: player REEP ID -> image URL, or None if unavailable.
PLAYER_IMAGE_CACHE = {}


@app.get("/api/player-image/{reep_id}")
def player_image(reep_id: str, request: FastAPIRequest):
    """Prefer approved local portraits, then use online image sources."""
    local_path = approved_local_portrait_path(reep_id)
    if local_path is not None:
        image_url = (
            str(request.base_url).rstrip("/")
            + "/api/local-player-image/"
            + quote(reep_id, safe="")
        )
        PLAYER_IMAGE_CACHE[reep_id] = image_url
        return {"reep_id": reep_id, "image_url": image_url}

    if reep_id in PLAYER_IMAGE_CACHE:
        return {"reep_id": reep_id, "image_url": PLAYER_IMAGE_CACHE[reep_id]}

    rows = query_db(
        """
        SELECT source_qid, resolved_qid
        FROM player_dob
        WHERE reep_id = ?
        LIMIT 1
        """,
        [reep_id],
        db_path=DOB_EVIDENCE_DB_PATH,
    )

    if not rows:
        PLAYER_IMAGE_CACHE[reep_id] = None
        return {"reep_id": reep_id, "image_url": None}

    row = rows[0]
    candidates = [row.get("resolved_qid"), row.get("source_qid")]
    qid = next(
        (
            str(value).strip()
            for value in candidates
            if value and re.fullmatch(r"Q[1-9][0-9]*", str(value).strip())
        ),
        None,
    )

    if not qid:
        PLAYER_IMAGE_CACHE[reep_id] = None
        return {"reep_id": reep_id, "image_url": None}

    image_url = None
    entity = {}
    temporary_error = False
    headers = {
        "User-Agent": "FyuchaFCBirthdayTool/1.1 (football birthday lookup)"
    }

    # First choice: a portrait directly listed in Wikidata (P18).
    request = Request(
        f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json",
        headers=headers,
    )

    try:
        with urlopen(request, timeout=8) as response:
            entity_data = json.load(response)

        entity = entity_data.get("entities", {}).get(qid, {})
        claims = entity.get("claims", {}).get("P18", [])

        for claim in claims:
            value = (
                claim.get("mainsnak", {})
                .get("datavalue", {})
                .get("value")
            )
            if isinstance(value, str) and value.strip():
                image_url = (
                    "https://commons.wikimedia.org/wiki/Special:FilePath/"
                    + quote(value.strip(), safe="")
                    + "?width=320"
                )
                break
    except Exception:
        # Continue to Wikipedia if the Wikidata request fails.
        temporary_error = True

    # Fallback: use thumbnails from the player's linked Wikipedia pages.
    if not image_url:
        sitelinks = entity.get("sitelinks", {})

        for site in ("enwiki", "itwiki"):
            link = sitelinks.get(site)
            if not link or not link.get("title"):
                continue

            language = site[:-4]
            params = {
                "action": "query",
                "titles": link["title"],
                "prop": "pageimages",
                "format": "json",
                "pithumbsize": 320,
            }
            from urllib.parse import urlencode

            api_url = (
                f"https://{language}.wikipedia.org/w/api.php?"
                + urlencode(params)
            )
            request = Request(api_url, headers=headers)

            try:
                with urlopen(request, timeout=8) as response:
                    page_data = json.load(response)

                pages = page_data.get("query", {}).get("pages", {})
                for page in pages.values():
                    thumbnail = page.get("thumbnail", {}).get("source")
                    if isinstance(thumbnail, str) and thumbnail.startswith("https://"):
                        image_url = thumbnail
                        break
            except Exception:
                temporary_error = True

            if image_url:
                break

    # Don't permanently cache a missing image if a source request failed.
    if image_url or not temporary_error:
        PLAYER_IMAGE_CACHE[reep_id] = image_url

    return {"reep_id": reep_id, "image_url": image_url}


@app.get("/api/players/{reep_id}")
def player_profile(reep_id: str):
    rows = query_db(
        f"""
        SELECT
            reep_id,
            label,
            status,
            gender,
            dob,
            {dob_date_fields()},
            dob_status,
            dob_precision,
            evidence_reason,
            source,
            source_qid,
            resolved_qid,
            redirected,
            corroboration_grade,
            corroboration_count,
            claim_count,
            preferred_claim_count,
            normal_claim_count,
            deprecated_claim_count
        FROM player_dob
        WHERE reep_id = ?
        LIMIT 1
        """,
        [reep_id],
        db_path=DOB_EVIDENCE_DB_PATH,
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Player not found in the REEP DOB evidence database.",
        )

    return rows[0]