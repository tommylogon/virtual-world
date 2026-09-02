---
type: task
status: done
area: environment
priority: medium
---

# task-379: env-presets-zone-apply

**Filed**: 2026-08-30
**Status**: Todo
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md — P3 — Environment presets & zone apply ('Arctic: -12° bright fresh' → apply to a selection; preset manager stores named presets).

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.

## Implemented (2026-09-02, this audit)

`static/js/shared/env-presets.js` + a Presets row in the area inspector's
Environment section. Save captures the current area's environment (light,
temperature, air, smell, noise, weather, wind, humidity) into a named preset
stored in localStorage (no new world-state storage). Apply writes through the
same `api.updateNode` path as the env editors — undo snapshots cover it — with
three zone scopes: this area, area + neighbours through open ways, all areas.
The inspector also gained weather/wind/humidity editors so presets have
something to capture.
