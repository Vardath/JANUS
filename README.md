# JANUS Global Core

Persistent server for the JANUS experimental functional-metacognition/agency architecture.

Canonical cognitive topology: **7 specialist evaluators → 3 middle integration cores → 1 Face**. The three middle cores are left hemisphere, right hemisphere, and intermediary. Guardian is deterministic server policy outside the cognitive cores.

User-facing core names are mutable display preferences. Persistent identity, user IDs, memory ownership, and protected identity state do not change when a user renames their core.

## Render deployment

This repository includes a `render.yaml` Blueprint. Deploy it with **Render → New → Blueprint**, connect this repository, and supply `OPENAI_API_KEY` when prompted. The Blueprint creates:

- one paid Starter web service so the process does not spin down;
- a 1 GB persistent disk mounted at `/data`;
- `JANUS_DB_PATH=/data/janus.sqlite3`;
- `/health` health checks;
- automatic deployment on commits to the linked branch;
- a generated random `JANUS_ACCESS_TOKEN` for administrative endpoints.

Do not commit API keys, SMTP credentials, OAuth secrets, or access tokens to this repository.

## Runtime

The FastAPI lifespan starts the bounded autonomy loop with the service. With the default configuration, the online core wakes on its configured cadence, retains its SQLite state on the persistent disk, and can queue background reflection/message events independently of the PC or Android clients.

This is a functional persistence architecture, not a claim of phenomenal consciousness.
