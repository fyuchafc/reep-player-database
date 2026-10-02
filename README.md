# REEP Player Database

A standalone football-player database project built from the REEP Register as the sole source dataset.

## Source

The primary source is the local REEP DuckDB database: `reep-register-v1.duckdb`.

The source database is intentionally **not committed to normal Git history** because the current file is approximately 663 MB.

## Principles

- REEP is the sole source of player records.
- The original REEP database is read-only.
- No FYUCHA-to-REEP identity matching is part of this project.
- No existing FYUCHA player database is used as a source.
- Processing is staged: audit → extract → normalize → deduplicate → validate → build.
- Every transformation should be reproducible.

## Current phase

**Phase 1: REEP schema and data audit**

The first script is read-only and reports the structure and basic statistics of a REEP DuckDB file.

## Planned structure

```
scripts/
  audit_reep.py
  extract_players.py
  normalize_players.py
  deduplicate_players.py
  build_master.py

config/
output/
```

Generated data and large source files should not be committed until the storage strategy is explicitly decided.
