# Manufacturing foundation progress

Plan: docs/superpowers/plans/2026-10-01-seedboxes-manufacturing-upgrade.md
Base: 654303a1654a58a6b734c97d872371bb8a541c26
Branch: codex/manufacturing-foundation
Scope: first delivery batch T01–T04, as specified by the plan's execution handoff.

## Decisions

- Ruling: Use an external linked worktree under the session workspace; the review clone and main branch stay unchanged. This is an isolated, reversible implementation workspace authorized by the development request.
- Ruling: Keep SeedBoxes branding exactly. Package name `seedboxes` remains a technical identifier.
- Ruling: The first batch provides tested geometry services and a structured backend API, not the later manufacturing UI, calibration workflow or 3D renderer. These remain T05–T17.
- Runtime: environment_status tool and network-policy file are unavailable; retain inherited network/proxy settings and diagnose actual tool failures without bypassing restrictions.

## Pre-flight interfaces

- T01 -> T03: locked Boxes.py commit is the capture adapter's version contract; match exact commit.
- T02 -> T03: Project canonical parameters and stable Panel IDs must match capture outputs; use typed dataclasses with JSON serialization.
- T03 -> T04: captured local geometry must preserve joint-root origin, not normalize to bounding-box minimum; two passes pair by panelId.
- T02 -> T04: manufacturing hash excludes view/name/timestamps but includes engine, adapter, features and process settings.

## Evidence

Implementation not yet complete. Windows UI/packaging and physical cutting are not available in this Linux session.

### T01
- RED: test_lock_has_no_local_boxes_source failed on editable ../boxes-1.2/boxes-master.
- GREEN: clean Python 3.10.21 uv environment resolves the exact Git commit; baseline SVG renders.
- Observed 172 web-visible generators, not the historical README's 179. The stale lock also called this project boxes-client. Updated documentation rather than inventing coverage.
- Dependency changes follow the actual pinned release metadata: removed stale local-master-only requirements; added pytest/tomli/jsonschema development tooling. Existing common dependency locks retained by uv where valid.
- Baseline manifests for ClosedBox and ABox exclude metadata timestamps; legacy backend smoke test included.

### T02
- RED: 18 contract tests failed because serialization was not implemented.
- GREEN: 23 tests passed including baseline; schemas and example validate.
- Added JSON dataclasses, version/units/finite-number checks, detached input snapshots and stable manufacturing hash (view/name/time excluded).
- Ruling: Use jsonschema as a runtime dependency, not only a test dependency, to enforce the same contract at the backend boundary. Adds a small dependency set but avoids two diverging validators. Schemas are included in the PyInstaller resource list.
- Ruling: T02 defines only interfaces needed by this batch; later job/storage/calibration contracts stay in the plan until their implementations exist.

### T03
- RED: 12 adapter tests failed before implementation.
- GREEN: six stable roles and A–F codes; real upstream local contours agree point-for-point with an independent renderer. Rotation/mirror and move-only capture also covered.
- No upstream class methods patched. A local ClosedBox subclass captures high-level boundaries and existing Surface paths.
- Added reciprocal edge adjacency and right-handed assembly transforms. Tooth intervals remain explicitly null and capability false; T09 must extract/validate them before tooth-clearance checks.
- Ruling: First batch restricts finger settings to upstream rectangular defaults and inner_corners=corner; disallows inner dimensions below four board thicknesses. Explicit rejection is preferable to silently presenting unverified combinations.
- Legacy render and thumbnail render now share a reentrant engine gate with the new adapter; no GUI behavior changed.

### T04
- RED: 13 compensation/service cases failed before implementation.
- GREEN: full suite 50 passed. Burn changes only toolpaths; equivalent internal/external dimensions preserve geometry; enabled circle/rectangle holes pass through upstream compensation exactly once.
- Added bounded LRU snapshot cache (8 entries / 64 MiB of serialized payload), defensive copies, structured `Api.generate_model`, and diagnostic CLI. Cache byte budget describes serialized payload, not an exact Python process memory bound.
- Ruling: Implemented two zero-rotation backend hole primitives now to make T04's hole-compensation test real; feature editing UI remains T08. No enhanced manufacturing export is advertised.
- Upstream circular holes use cubic approximation: the 8 mm test hole's extrema differ from an ideal circle by approximately 0.0000024 mm. The assertion uses 0.00001 mm absolute tolerance, preserving the upstream curve instead of substituting a new circle.
- Nominal and cut contours are real paths; packing, joint intervals, hole-edge clearance and physical fit remain unverified. Results explicitly report MANUFACTURING_UNCHECKED.
- Run: `uv run --locked python scripts/generate_model.py tests/fixtures/project.json --output /tmp/seedboxes-model.json`.

## Final review and batch status

- Independent read-only review completed for base `654303a` through T04 `67d6c05`; no critical or high-severity issue found. One medium issue was reproduced: generated path schemas accepted arbitrary command tokens/arity/coordinate types.
- RED: four malformed-command cases were accepted. FIX: shared pathCommand definition limits M/L/C/Z, exact lengths and numeric coordinates. GREEN: 54 tests passed; contracts and geometry-diff checks passed.
- Packaging investigation: existing PyInstaller `collect_all('boxes')` already includes distribution metadata; no duplicate metadata-copy change retained. This is a static review, not proof that a Windows executable runs.
- Review scope rulings: hole containment/overlap/edge clearance/physical fit and tooth intervals remain T09; storage/UI/packing/export/3D remain subsequent tasks. Very large off-panel feature coordinates are not a validated use case; later feature/manufacturing validation must enforce practical geometric limits. This foundation does not expose an enhanced cutting export.
- Batch T01–T04 complete as a software foundation. Public capability flags remain conservative: no manufacturing checks, no 3D, no enhanced export. No claim of production readiness or successful physical cutting.
- Next entry: T05 project/profile persistence, then T06 calibration and T07 scheduling/UI; preserve this geometry baseline during integration.
- Git delivery: independent feature branch, per-task commits and a separate review-fix commit; do not merge main automatically.

## T05 — project and process-profile persistence

Base: `c8e96bed1ca9dfaea95501ab7edb1ccfd9576ae8` (remote first-batch head).

- Ruling: Continue with T05 as the next reviewable delivery, as proposed in the progress reply; scheduling/editor integration is T06, calibration cards T07. Earlier informal replies reversed T06/T07; the checked-in plan is authoritative. Cost if misunderstood: UI delivery remains a subsequent task, not implied by these backend interfaces.
- Pre-flight T02 -> T05: retain the original minimal profile snapshot contract so saved baseline projects remain valid; add a strict process-profile contract for editable global profiles, where unknown burn remains null until explicitly supplied.
- Pre-flight T05 -> T06: expose native load/save, recovery and profile methods now. The 2-second recovery timer and exit lifecycle are owned by the forthcoming editor/scheduler; no claim that the unchanged legacy form autosaves.
- Ruling: `ProjectStore.load` returns `Project | ReadOnlyProject` for future schemas. A raw read-only envelope preserves unknown fields, while save rejects it and also refuses overwriting an existing future-version file. No earlier supported schema exists, so no guessed migration is installed. Cost: a newer file can be inspected but not edited by this build.
- Ruling: At least five thickness readings (up to 100) derive min/max and a median representative value; raw readings remain in the immutable version. Median is explicit in data. Cost: an application that prefers a mean must introduce an explicit measurement policy.
- Ruling: Formal project writes use a process-wide lock, flush/close, same-directory replacement and a raw previous-file .bak. Profile versions publish with an exclusive hard link so competing writers cannot overwrite the same version; unsupported local filesystems return an error. Cost: general shared/network-filesystem collaboration is not promised, and sudden power-loss durability still depends on the filesystem/device.
- RED: 25 storage/profile cases failed before implementation; six desktop/API and safe-error tests then failed before integration.
- GREEN: Chinese paths, interrupted flush/backup/replace, future read-only, malformed/duplicate JSON, 20 MiB import/save limit, detached recovery and cleanup identity, immutable profiles, stale-version rejection, five-point records, calibration invalidation, native-picker cancellation and legacy preview coexistence.
- Formal files and recovery snapshots remain independent. Cleanup compares the saved file and recovery payload hash, preserving newer or externally changed work. Corrupt recovery candidates are listed with errors instead of hiding all candidates.
- Material presets are names only; no machine, speed, power or burn recommendation is manufactured. Reference profiles can be saved with missing measurements. Calibrated status requires matching evidence, five readings and explicit processing values.
- Added `seedboxes/desktop/persistence.py` to keep storage handling out of the legacy rendering class; backend remains a thin bridge. Dialog tests substitute only the native picker; filesystem IO stays real.
- Schema errors now report the field/rule without echoing potentially large user documents. This was reproduced by a failing privacy/size test.
- Windows native dialogs, packaged executable behavior and power-loss recovery remain untested in this Linux session.

### T05 independent review and fixes

- Review of `c8e96be..b3d563e` reproduced P1 backup loss when restoring a corrupt formal file followed by a sharing violation, and P2 inconsistent handling of integral JSON schema versions (`1.0` / `99.0`).
- Fixed P1: `test_failed_restore_preserves_last_valid_backup` RED→GREEN. A corrupt or invalid formal document is backed up separately as `.corrupt.bak`; a valid `.bak` is not overwritten during repair, including if final replacement fails.
- Fixed P2: `test_integral_schema_version_round_trips_consistently` RED→GREEN. Accepted integral versions use a consistent load/save gate; current project/profile integer fields normalize to integers. Future integral-float versions remain read-only and overwrite-protected.
- Final verification: 90 tests passed; schema validation passed; baseline geometry comparison remains 662 points with zero error.
- Final Ruling: Windows native-dialog/packaged behavior and sudden power-loss durability remain unverified because this session is Linux and failure injection models software IO errors only. Cost: Windows acceptance remains required before a release claim.
- Final Ruling: General shared/network-filesystem collaboration remains outside this desktop task; immutable profile publication fails explicitly where hard links are unsupported. Cost: such deployments need a different storage strategy.
- Final Ruling: Physical calibration validity and card provenance belong to T07; persisted evidence must match the profile hash but is a user-supplied record, not machine-attested proof. Cost: a matching record does not guarantee physical fit.
- Final Ruling: T06 owns editor buttons, autosave timing and exit lifecycle; T05 delivers tested callable persistence interfaces. Cost: the unchanged legacy form still does not autosave. No other review issues deferred.
