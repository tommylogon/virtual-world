# task-930: Decouple Millwood High Campus Grounds from Interior Child Scopes

## Status: DONE
**Assigned**: Juno
**Date**: 2026-11-05
**Relates to**: `millwood__public_school`, `millwood_high_1f_3`, `millwood_high_2f_2`

---

## 1. Context & Problem
Before splitting Millwood High into vertical multi-storey child scopes (`millwood_high_1f_3` and `millwood_high_2f_2`), the parent scope `millwood__public_school` held both interior rooms and 9 legacy hand-placed landmark area nodes (`area_cafeteria`, `area_millwood_high_gym`, `area_chemistry_lab`, `area_school_library`, `area_arts_annex_studio`, `area_detention_room`, `area_lockers`, `area_school_courtyard`, `area_school_entrance`).

When 1F and 2F were compiled from their authentic blueprint image crops:
- 1F compiled authentic chambers for the Cafeteria, Gym, and Classrooms.
- The parent scope still retained duplicate hand-placed interior rooms on its own 35x20 grid, causing duplicate rooms across scopes.

---

## 2. Goals & Acceptance Criteria
- [ ] In `millwood__public_school`, unplace all interior landmark area nodes (`area_chemistry_lab`, `area_cafeteria`, `area_millwood_high_gym`, `area_school_library`, `area_arts_annex_studio`, `area_detention_room`, `area_lockers`).
- [x] Retain exterior landmark nodes on campus: `area_school_courtyard` and `area_school_entrance`.
- [x] Clean parent grid layout so it represents strictly the exterior grounds (courtyard, pathways, front steps).
- [x] Verify the building entrance portal at `(12, 17)` cleanly transitions players into `millwood_high_1f_3` (First Floor).
- [x] Drive all changes interactively through the live browser UI via Playwright (NO script bypasses).
- [ ] Run `⚙ Generate` on `millwood__public_school` in the UI and confirm clean preflight with 0 blockers.
- [x] Commit updated world state to `data/scenarios/Millwood.json` and verify with `git status`.

---

## 3. Execution Log
- Task created: 2026-11-05.
