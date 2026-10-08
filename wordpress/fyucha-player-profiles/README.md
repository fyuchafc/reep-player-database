# Fyucha FC Player Profiles

This is the first WordPress foundation for the REEP-powered Fyucha FC player-profile system.

## Architecture

REEP V1.2 DuckDB
→ Player Profile Feed
→ WordPress Player CPT
→ Fyucha FC player profile pages

## Permanent identity

Every player is identified by:

`reep_id`

Names, aliases, clubs, positions and external IDs are attributes. They are not the permanent identity.

## Current plugin foundation

The plugin registers:

- Custom post type: `fyucha_player`
- Public URL structure: `/player/<slug>/`
- WordPress REST lookup:
  `/wp-json/fyucha/v1/player/<reep_id>`

The importer is intentionally not included yet. The next implementation stage is a batch importer that can safely create/update profiles from the JSONL feed without loading all 432,124 players into memory.

## Data source

The exporter reads the audited:

`output/reep-player-master-v1.2.duckdb`

and creates:

`output/reep-player-profile-feed-v1.0.jsonl`

The feed contains one canonical record per REEP player and is designed to be regenerated whenever a new REEP database version is released.
