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
