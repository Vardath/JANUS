# JANUS Phase 2 — Persistence and migration matrix

Phase 2 Step 3 establishes a single compatibility registry for durable server state. The purpose is not to centralize every table creator; each subsystem still owns and initializes its own schema. The registry records the minimum shape current code requires and performs a read-only preflight before normal application imports can write to already-existing state.

## Startup policy

1. `auth_db_normalizer.py` preserves and normalizes the oldest incompatible `accounts` layout without deleting the original table.
2. `auth_schema_guard.py` performs safe additive auth migrations and preserves incompatible legacy `sessions` / `auth_tokens` tables.
3. `persistence_matrix.preflight_existing()` then runs before `janus_dashboard` is imported. Missing tables are valid on a clean installation. Any registered table that already exists but lacks columns required by its current owner causes full startup to fail closed before ordinary application writes.
4. Current modules create missing tables and perform their documented additive migrations.
5. Late in application installation, `persistence_matrix.record_current_matrix()` records the observed matrix version and per-table compatibility snapshot in `janus_schema_meta`.

Extra columns are accepted. This means a newer additive schema can survive an older-compatible restart path without destructive rewriting, while missing required columns cannot be silently ignored by `CREATE TABLE IF NOT EXISTS`.

## Registered durable tables

| Table | Owning subsystem | Registry version | Startup significance |
| --- | --- | ---: | --- |
| `accounts` | `auth.py` | 2 | authentication identity; critical |
| `sessions` | `auth.py` | 1 | authenticated sessions; critical |
| `auth_tokens` | `auth.py` | 1 | verification/reset tokens; critical |
| `desktop_memory` | `dashboard_api.py` | 1 | conversation and retained memory; critical |
| `desktop_events` | `dashboard_api.py` | 1 | activity/outbox/event history; critical |
| `janus_continuity_items` | `continuity_ledger.py` | 1 | durable projects/questions/tasks |
| `janus_continuity_events` | `continuity_ledger.py` | 1 | lifecycle audit history |
| `janus_research_claims` | `research_workspace.py` | 1 | epistemically typed claims |
| `janus_research_evidence` | `research_workspace.py` | 1 | evidence attached to claims |
| `janus_research_relations` | `research_workspace.py` | 1 | claim graph relations |
| `janus_client_presence` | `core_sync.py` | 1 | authenticated local/global presence |
| `janus_core_observe` | `core_observer.py` | 2 | profile-aware externalizable core observations |
| `janus_deliberation_tasks` | `deliberation_tasks.py` | 1 | user-directed persistent deliberation |
| `janus_message_threads` | `proactive_threads.py` | 1 | proactive-message thread provenance |
| `janus_reliability_audits` | `reliability_audit.py` | 1 | reliability audit history |
| `janus_files` | `attachment_api.py` | 1 | account-bound file metadata |
| `janus_generated_images` | `image_generation.py` | 1 | generated-image provenance/cost records |
| `janus_schema_meta` | persistence/reliability layer | 2 | schema and matrix metadata |

This registry deliberately defines minimum compatibility, not exact SQL identity. Indexes, constraints and extra additive columns remain owned by the subsystem implementation.

## Test matrix

The CI regression suite now explicitly covers:

- **clean installation:** an empty database passes preflight and can be initialized by normal owners;
- **legacy/incompatible shape:** an existing registered table missing required columns is rejected before ordinary writes;
- **additive upgrade:** extra columns remain compatible;
- **repeated restart:** recording the matrix and then running preflight again is idempotent and retains the matrix version.

Auth-specific legacy normalization remains separately tested by the existing authentication suite. Later Phase 2 soak work will exercise the same contract over long-running server/local reconnect and restart sequences.

## Safety boundary

The persistence guard is intentionally non-destructive. Outside the already-established auth compatibility normalizer/guard, it does not rename, delete, compact, repair or rewrite user tables. An unknown incompatible shape is preserved in place and the server enters degraded startup instead of guessing how to migrate it.
