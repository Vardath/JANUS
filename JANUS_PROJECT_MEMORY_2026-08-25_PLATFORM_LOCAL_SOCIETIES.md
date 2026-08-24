# JANUS Project Continuity — 2026-08-25 Platform Local Societies

This checkpoint follows the merged canonical 1|3|7 sensory architecture and records the platform-local parity work for Windows and iOS.

## Canonical rule retained

A connected JANUS installation may comprise two distinct 11-core societies:

- **Local JANUS** — device-specific persistent deterministic state.
- **Global JANUS** — persistent online/account-specific state.

Together they are 22 cores, but they are never one merged 22-core hive. Each 11-core society keeps the canonical 1|3|7 structure: seven Fano subconscious projections -> Left and Right hemispheres -> Front/Bridge -> Interface. Peer state is sensed through all seven receiving subconscious cores and does not overwrite the receiving society's Front, Interface or protected identity.

The canonical seven meanings remain Evidence=1/E, Safety=2/V, Counterpoint=3/E+V, Context=4/P, Logic=5/E+P, Novelty=6/V+P and Memory=7/E+V+P. Direction 0 remains neutral/uncommitted reference.

## Windows local society

`client/janus_local_society.py` implements a persistent deterministic Windows-local 11-core society.

- Exactly eleven canonical cores.
- Persistent state under the user's local JANUS profile directory.
- Text, file, runtime and peer sensory events currently wired from the Windows client; the shared modality vocabulary also includes image, audio, web, memory and action-result for later capability acquisition.
- Every sense passes through all seven specialists, then both hemispheres, Front appraisal and Interface.
- Front/Interface use the same bounded appraisal dimensions as the global architecture.
- Deterministic local processing performs zero external model/API calls.
- The authenticated heartbeat sends bounded local cycle counts, core summaries and Front/Interface state to global JANUS.
- Global Front/Interface state returns as a peer sense through all seven local cores.
- Windows v0.25 now presents Local and Global societies separately instead of pretending to be global-only.

Windows CI compiles the module, executes a local-society smoke test proving exactly 11 cores and peer-sense progression, then packages the actual `JANUS.exe`. The Stage 2 Windows build passed.

## iOS local society

`ios/JANUS/LocalJanusSociety.swift` implements the corresponding persistent deterministic iOS-local 11-core society.

- Exactly eleven canonical cores.
- App-private persistence through UserDefaults.
- Chat text, attached files, generated-image availability, runtime/session events, global peer state and Chat action-results are currently wired as local senses.
- Every sensory event passes through all seven specialists, both hemispheres, Front and Interface.
- Heartbeat sends the local cycle/summaries and Front/Interface appraisals to global JANUS.
- Global state is re-sensed locally through all seven.
- Local and global Front postures are kept distinct in client status.
- Deterministic local processing itself makes zero external model/API calls.

The iOS simulator workflow now statically protects the local 1|3|7 contract before generating/building the Xcode project. The Stage 2 iOS simulator build passed.

## Platform caveats

Android remains the strongest background-capable local implementation because mobile/desktop operating systems differ in background execution policy. Windows local cycling currently advances through authenticated foreground heartbeat/activity; iOS advances through authenticated interaction/heartbeat and is subject to iOS background-execution constraints. Do not falsely describe either as continuously executing when the operating system has suspended the app.

The architectural invariant is persistent local state + deterministic local sensory passes when execution is available, not a claim of uninterrupted subjective experience.

## Regression boundaries

Retain all boundaries from `JANUS_PROJECT_MEMORY_2026-08-25_137_SENSORY.md`, especially:

- exact 11 canonical cores per society;
- both hemispheres receive all seven;
- Front is canonical, `consensus` is transport compatibility only;
- no Interface -> Front recursive self-chat;
- peer state re-enters through all seven;
- local/global no-overwrite federation;
- zero external model/API calls for deterministic local cycles;
- account/auth/file/memory isolation;
- no phenomenal-consciousness or biological-feeling claim.

## Verification

Stage 2 branch `janus-platform-local-societies` was current with main before final review. Its diff was limited to Windows/iOS client local-society code and their build workflows. Windows EXE and iOS simulator builds both passed on the implementation head before promotion for merge.
