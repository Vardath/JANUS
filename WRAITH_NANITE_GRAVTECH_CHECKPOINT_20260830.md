# Wraith & Nanite Gravtech checkpoint — 2026-08-30

This file is an external-project continuity note only. It does **not** define or modify JANUS runtime behavior, architecture, Android code, server code, deployment, budgets, identity, or release state.

Repository: `Vardath/Wraith-Nanite-Gravtech`
Active development branch: `develop`

## Current verified build state

A real RimWorld 1.6 compile/package pipeline now exists in GitHub Actions rather than relying on source-only ZIPs or local PowerShell builds.

The user's local PowerShell compile exposed two initial errors:

- `CS0246` in `CompProperties_AbilityHostSeedGestation.cs`: `HediffDef` namespace/import issue.
- `CS0534` in `GeneGizmo_Resource_LifeForce.cs`: missing required `GetTooltip()` implementation.

Those were fixed. GitHub CI was then extended to perform an actual C# compile and package a playable mod artifact. That CI compile exposed a second layer of seven real compiler errors, including C# 8 string/TaggedString typing, missing `PathEndMode` namespace, sound playback API namespace/reference issues, and an obsolete/missing enemy entry-cell constant. Those were fixed as one coherent compile-repair pass.

Latest verified playable-build commit:

`3f2af8a124133d46b039b4b1225c21105be98d3f`

GitHub Actions run:

- workflow: `Static Def Audit`
- run ID: `33301376568`
- run number: `206`
- result: **success**
- static Def audit: success
- .NET compile: success
- DLL verification: success
- playable folder assembly: success
- artifact upload: success

Generated GitHub artifact:

- artifact name: `Wraith-Nanite-Gravtech-playable`
- artifact ID: `9729046436`
- artifact SHA-256 digest: `2f9fc7d711fbf8f93253a526af274c7afb72d0f29fd32c2936186731f7eb5e4f`
- compiled DLL: `Assemblies/WraithNaniteGravtech.dll`
- observed DLL size in packaged artifact: 36,352 bytes

A user-facing ZIP was repacked with a single correct top-level mod folder:

`Wraith-Nanite-Gravtech-RimWorld-Mod.zip`

Expected install shape:

```text
RimWorld/Mods/Wraith-Nanite-Gravtech/
    About/
    Assemblies/
    Defs/
    Languages/
    Sounds/
    Textures/
```

The user installed this packaged build and began the first real RimWorld startup/load test. At this checkpoint, runtime success is **not yet proven**; the next evidence is whether RimWorld reaches the main menu with WNG still enabled after a clean relaunch.

## Important runtime-validation rule

Do not call WNG playable/runtime-ready merely because CI is green. CI now proves XML/static consistency plus successful C# compilation and packaging. RimWorld runtime loading, Def resolution against the real game/DLC set, scenarios, factions, abilities, raids, save/load, and large-mod-list compatibility still require in-game proof.

If the first runtime launch fails, resets/disables the mod, or throws new errors, obtain the fresh `Player.log` from that exact failed launch before reopening RimWorld. Diagnose the **first WNG-caused load/runtime error** rather than attributing unrelated existing mod-list errors to WNG.

## Current WNG functional continuity

Wraith roles remain Hunter, Warrior, Commander and Queen. Wraith systems include Life Force drain/starvation/torpor/recovery, Life Drain, Life-Force-scaled regeneration, missing-part regrowth, Host Seed Gestation/Living Forge flow, Wither, and Enthrall. Enthrall is implemented as actual RimWorld slavery through `SetGuestStatus(..., GuestStatus.Slave)` when Ideology is active.

Human-form Replicators retain the Neural Interface operations: recruit, imprison, enslave, copy skills/passions and create a player-aligned human-form copy. Small Replicators retain controlled/friendly colony behavior, loss-of-control feral transition, assimilation reproduction, map population cap, overflow Replicator matter and hostile swarm behavior. EMP distinctions remain: vanilla EMP for small Replicators, custom nanite disruption for human-form Replicators, and custom shielding behavior for precursor equipment where defined.

Factions remain separated into hostile/non-hostile Wraith and human-form groups plus hidden hostile Replicator swarm and player factions. Gravship content remains Odyssey-dependent and high-risk for runtime schema/API validation until tested in-game.

## Known external compatibility context

The user's large mod list previously showed a fatal `ModularWeapons` / `ModularWeapons2` initialization failure affecting global `PawnGenerator`/weapon-generation paths. WNG should not add a workaround that hides or catches that third-party global failure. If it is still present during compatibility testing, it remains an external blocker for reliable WNG pawn-generation validation.

## Next continuation

1. Complete the current clean RimWorld launch/relaunch test with the packaged WNG folder.
2. Confirm WNG remains enabled and reaches the main menu.
3. If load succeeds, test the four WNG scenarios and then the faction/PawnKind/raid/ability/Replicator/EMP/save-load matrix.
4. If load fails, capture the exact fresh `Player.log` and fix only the first demonstrated WNG issue.
5. After every source fix, require the compile/package workflow to return green for the exact commit before proceeding.

This checkpoint intentionally avoids modifying `CURRENT_CHECKPOINT.md` or any JANUS runtime file so the JANUS app continuation remains untouched.
