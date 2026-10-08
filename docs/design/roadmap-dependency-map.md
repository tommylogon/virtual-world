# Roadmap — Dependency Map (open work)

*Written 2026-10-07. Scope: the **102 open** cards (86 `todo` + 16 `inprogress`) in
`docs/virtualWorld/dev_tasks/`. `review`/`done`/`cancelled` are excluded. The folder
tree and `python tools/tasks.py list` stay authoritative; this file is the dependency
picture they lack.*

**How to read it.** `-->` is a real prerequisite (A needs B first). `-.->` is
related/soft. Colour is status: **blue = decisions locked / startable**, **green =
in progress**, **grey = todo**, **amber = the one-truth register**. The platform spine
(first graph) shows only tasks something else depends on; the per-area graphs show the
detail; the table is the sortable inventory.

## Legend

| marker | meaning |
|---|---|
| `-->` | hard dependency |
| `-.->` | related / soft |
| blue node | decisions locked, startable now |
| green node | in progress |
| grey node | todo |
| amber | one-truth register (not a task) |

---

## 1. Platform spine — what other work sits on

```mermaid
flowchart TB
    classDef ready fill:#0b2545,stroke:#58a6ff,color:#cfe6ff
    classDef todo fill:#1f2937,stroke:#6b7280,color:#e5e7eb
    classDef wip fill:#10261a,stroke:#3fb950,color:#d1fadf

    t446["446 - id-first identity"]:::wip
    t724["724 - one home per fact"]:::ready
    t625["625 - consolidate dup concepts"]:::todo
    t491["491 - action-verb registry"]:::todo
    t437["437 - turn order"]:::todo
    t477["477 - central check system"]:::todo
    t734["734 - knowledge = memory"]:::ready
    t352["352 - action economy"]:::ready
    t401["401 - chunk persistence"]:::todo
    t673["673 - EntityEditor frame"]:::todo
    t733["733 - character sheet"]:::todo
    t736["736 - cognitive map + recall"]:::todo
    t710["710 - scope promote/demote"]:::todo
    t675["675 - character editor"]:::todo

    t446 --> t724
    t724 --> t734
    t724 --> t733
    t625 --> t491
    t437 --> t352
    t477 --> t352
    t734 --> t736
    t734 --> t733
    t352 --> t736
    t401 --> t710
    t673 --> t675
    t675 --> t733
```

## 2. Character / mind cluster

```mermaid
flowchart LR
    classDef ready fill:#0b2545,stroke:#58a6ff,color:#cfe6ff
    classDef wip fill:#10261a,stroke:#3fb950,color:#d1fadf
    classDef todo fill:#1f2937,stroke:#6b7280,color:#e5e7eb

    t446["446 id-first"]:::wip
    t724["724 one home"]:::ready
    t619["619 relationships 2 shapes"]:::todo
    t447(["447 aliases"]):::wip
    t734["734 knowledge = memory"]:::ready
    t736["736 map + recall"]:::todo
    t730["730 memory creation"]:::todo
    t733["733 character sheet"]:::todo
    t737["737 abilities"]:::todo
    t714["714 Mind panel"]:::todo
    t729["729 move controls"]:::todo
    t404["404 life generator"]:::todo
    t704["704 GOSP selector"]:::todo
    t725["725 death/revive mem"]:::todo
    t727(["727 lived-log bridge"]):::wip
    t735["735 aging"]:::todo
    t352["352 economy"]:::ready

    t446 --> t619 --> t447
    t724 --> t733
    t734 --> t736
    t734 --> t730
    t734 --> t714
    t734 --> t733
    t735 --> t733
    t352 --> t736
    t352 --> t737
    t714 --> t729
    t404 -.-> t734
    t725 -.-> t734
    t727 -.-> t734
    t704 -.-> t714
```

## 3. The one-truth register — the recurring disease

Nine open cards are the *same* bug: two places hold one truth and only one gets
written. This is the roadmap's own Rule 1, caught again.

```mermaid
flowchart LR
    classDef dot fill:#3a2a0a,stroke:#e3b341,color:#ffe9b3
    ONE["ONE TRUTH<br/>two homes, one written"]:::dot
    t724["724 definition x3"]:::dot
    t446["446 names as keys"]:::dot
    t667["667 library by filename"]:::dot
    t619["619 relationships x2"]:::dot
    t491["491 verbs defined twice"]:::dot
    t625["625 dup concepts"]:::dot
    t713["713 dead 2nd impl"]:::dot
    t430["430 derived stores"]:::dot
    t683["683 speech to the door"]:::dot
    ONE --- t724
    ONE --- t446
    ONE --- t667
    ONE --- t619
    ONE --- t491
    ONE --- t625
    ONE --- t713
    ONE --- t430
    ONE --- t683
```

## 4. Gameplay, plans and economy

```mermaid
flowchart LR
    classDef ready fill:#0b2545,stroke:#58a6ff,color:#cfe6ff
    classDef wip fill:#10261a,stroke:#3fb950,color:#d1fadf
    classDef todo fill:#1f2937,stroke:#6b7280,color:#e5e7eb

    t437["437 turn order"]:::todo
    t477["477 check system"]:::todo
    t352["352 action economy"]:::ready
    t414["414 batch advance"]:::todo
    t430["430 retire derived stores"]:::todo
    t467["467 belief travel"]:::todo
    t482["482 timeskip follow-ups"]:::todo
    t594["594 swimming"]:::todo
    t681["681 fumble in dark"]:::todo
    t683["683 speech to a door"]:::todo
    t299["299 long-distance comms"]:::todo
    t99["99 room grids"]:::todo
    t728["728 directed control"]:::todo
    t702["702 plan executor"]:::todo
    t701["701 plan templates"]:::todo
    t426(["426 plan archetypes"]):::wip
    t703["703 recipes -> plans"]:::todo
    t716(["716 fisherman slice"]):::wip
    t731(["731 activities via object"]):::wip

    t437 --> t352
    t477 --> t352
    t701 --> t702
    t426 --> t702
    t703 --> t701
    t716 --> t731
    t731 -.-> t352
    t482 -.-> t467
    t467 -.-> t430
```

## 5. World and scale

```mermaid
flowchart LR
    classDef wip fill:#10261a,stroke:#3fb950,color:#d1fadf
    classDef todo fill:#1f2937,stroke:#6b7280,color:#e5e7eb

    t401["401 chunk persistence"]:::todo
    t402["402 projection benchmark"]:::todo
    t710["710 promote/demote"]:::todo
    t711["711 re-evaluate promoted set"]:::todo
    t589["589 worldpainter tab"]:::todo
    t591["591 capture subgraph"]:::todo
    t592(["592 hierarchy in outline"]):::wip
    t637["637 scope picker wrong"]:::todo
    t638["638 grid-coord area names"]:::todo
    t570["570 hostile distribution"]:::todo
    t694["694 HTC fixture world"]:::todo
    t735["735 aging / lifecycle"]:::todo

    t401 --> t402
    t401 --> t710
    t710 --> t711
    t591 --> t401
    t589 -.-> t401
    t592 -.-> t710
```

## 6. UI and editors

```mermaid
flowchart LR
    classDef ready fill:#0b2545,stroke:#58a6ff,color:#cfe6ff
    classDef wip fill:#10261a,stroke:#3fb950,color:#d1fadf
    classDef todo fill:#1f2937,stroke:#6b7280,color:#e5e7eb

    t673["673 EntityEditor frame"]:::todo
    t674["674 item editor"]:::todo
    t675["675 character editor"]:::todo
    t676["676 area editor"]:::todo
    t734["734 knowledge store"]:::ready
    t714["714 Mind panel"]:::todo
    t729["729 move controls"]:::todo
    t730["730 memory creation"]:::todo
    t510["510 library browser"]:::todo
    t455["455 save/load dialog"]:::todo
    t405["405 LLM inspector"]:::todo
    t580["580 uncover-scope affordance"]:::todo
    t612["612 orphaned scrim"]:::todo
    t655["655 equipment 1dd8"]:::todo
    t679["679 react wall of text"]:::todo
    t682["682 snake_case chips"]:::todo
    t698["698 react replay"]:::todo
    t712["712 scope fetch resets filter"]:::todo
    t544(["544 soak lab space-time"]):::wip
    t732(["732 sync grouping"]):::wip

    t673 --> t674
    t673 --> t675
    t673 --> t676
    t714 --> t729
    t734 -.-> t714
    t734 -.-> t730
    t732 -.-> t510
```

## 7. Library and content

```mermaid
flowchart LR
    classDef wip fill:#10261a,stroke:#3fb950,color:#d1fadf
    classDef todo fill:#1f2937,stroke:#6b7280,color:#e5e7eb

    t667["667 library by filename"]:::todo
    t646(["646 rename registry ids"]):::wip
    t509["509 batch triggers"]:::todo
    t684["684 missing light triggers"]:::todo
    t701["701 plan templates"]:::todo
    t703["703 recipes -> plans"]:::todo
    t660(["660 auto-dress tag match"]):::wip
    t589["589 worldpainter tab"]:::todo
    t591["591 capture subgraph"]:::todo

    t667 --> t646
    t509 --> t684
    t703 --> t701
    t591 -.-> t589
```

---

## The complete inventory

Status: `todo`, `wip` = in progress, `ready` = decisions locked / startable now.

### Characters

| Task | Status | Depends on | Summary |
|---|---|---|---|
| bug-519 | todo | — | editorial rewrite notes stored inside memories |
| task-404 | todo | 734 (soft) | character life-experience generator |
| task-409 | todo | — | background schedules, work, coarse social |
| task-619 | todo | 446 | relationships stored in two shapes in one field |
| task-665 | todo | — | Kraktooth cast rework half-migrated |
| task-704 | todo | 714 (soft) | GOSP selector needs memory and personality |
| task-725 | todo | 734 (soft) | memories lack death / travel / resurrection |
| task-733 | todo | 724, 735, 734 | character sheet: WorldGraph form → primitives |
| task-734 | **ready** | — | knowledge is memory; per-kind lifecycles |
| task-736 | todo | 734, 352 | cognitive map + `recall` |
| task-737 | todo | 352 | intrinsic abilities: grant/revoke, not droppable |
| task-447 | wip | — | nicknames / aliases |
| task-534 | wip | — | missing body reaction: sneeze |
| task-727 | wip | 734 (soft) | lived-log → memory bridge |

### Gameplay

| Task | Status | Depends on | Summary |
|---|---|---|---|
| task-299 | todo | — | long-distance communication |
| task-352 | **ready** | 437, 477 | action economy, free / minor / major |
| task-414 | todo | — | batch time advance, non-blocking human |
| task-430 | todo | — | retire `visited_areas` / `discovered_items` |
| task-437 | todo | — | turn order source of truth and modes |
| task-467 | todo | — | belief-based travel, heading, hearsay |
| task-477 | todo | — | combat and grapple on the central check system |
| task-482 | todo | — | timeskip follow-ups, leisure vendors |
| task-594 | todo | — | swimming navigation, diving, air vital |
| task-681 | todo | — | fumbling in the dark, partial result |
| task-683 | todo | — | witnessed speech attributed to a door |
| task-702 | todo | 701, 426 | plan executor runtime |
| task-728 | todo | — | directed control mode |
| task-99 | todo | — | room grids and movement |
| task-426 | wip | — | plan archetypes and group goals |
| task-671 | wip | — | timeskip intent that cannot be carried out |
| task-716 | wip | 731 | fisherman vertical slice |
| task-731 | wip | — | activities entered through their object |

### World

| Task | Status | Depends on | Summary |
|---|---|---|---|
| task-401 | todo | — | chunk persistence and gateway ways |
| task-402 | todo | 401 | world scale projection benchmark |
| task-570 | todo | — | hostile distribution consumer |
| task-637 | todo | — | area scope picker shows the wrong scope |
| task-638 | todo | — | areas named after grid coordinates |
| task-694 | todo | — | HTC fixture world |
| task-710 | todo | 401 | scope selection drives the promoted set |
| task-711 | todo | 710 | re-evaluate the promoted set every tick |
| task-735 | todo | — | aging and lifecycle for long-horizon soaks |

### UI and editors

| Task | Status | Depends on | Summary |
|---|---|---|---|
| task-405 | todo | — | LLM raw request/response inspector |
| task-455 | todo | — | save/load dialog UX |
| task-510 | todo | — | library browser UI overhaul |
| task-580 | todo | — | uncover-scope generate affordance |
| task-612 | todo | — | person context menu orphaned scrim |
| task-655 | todo | — | equipment readout renders 1dd8 |
| task-673 | todo | — | EntityEditor frame |
| task-674 | todo | 673 | item editor actions matrix |
| task-675 | todo | 673 | character editor three-column |
| task-676 | todo | 673 | area editor split view |
| task-679 | todo | — | react phase is one wall of text |
| task-682 | todo | — | scene chips leak snake_case ids |
| task-698 | todo | — | react phase replay |
| task-712 | todo | — | failed scope fetch resets the filter |
| task-714 | todo | 734, 691 | character Mind panel |
| task-729 | todo | 714 | move relationship/emotion/memory editors into Mind |
| task-730 | todo | 734 | interactive memory creation |
| task-544 | wip | — | soak lab space-time view |
| task-592 | wip | — | one hierarchy: scopes at the top of the outline |
| task-732 | wip | 526 | sync grouping and review queue |

### Library and content

| Task | Status | Depends on | Summary |
|---|---|---|---|
| task-509 | todo | 684 | batch generate triggers for selected items |
| task-589 | todo | 401 (soft) | worldpainter category tab |
| task-591 | todo | 401 | structures: capture a subgraph |
| task-667 | todo | 446 | library entries keyed by filename |
| task-684 | todo | — | matches/candlestick light triggers missing |
| task-701 | todo | — | plan template library |
| task-646 | wip | 667 | rename space-separated registry ids |

### Refactor and engine health

| Task | Status | Depends on | Summary |
|---|---|---|---|
| task-332 | todo | 625 | migrate legacy item effect props to triggers |
| task-440 | todo | — | split backend runner-up files |
| task-441 | todo | — | split frontend giants and trigger tests |
| task-454 | todo | — | save list must not parse every save |
| task-456 | todo | — | split saveload view concerns |
| task-491 | todo | 625 | single source for action verbs (scoped registry) |
| task-625 | todo | — | duplicated concepts across the engine |
| task-696 | todo | — | server log file, route identity |
| task-713 | todo | — | `attention.py` dead second implementation |
| task-715 | todo | — | live update transport will not scale |
| task-724 | **ready** | 446 (soft) | player state in multiple homes |
| task-83 | todo | — | code readability refactor |
| task-446 | wip | — | id-first node identity |

### Prompting and narration

| Task | Status | Depends on | Summary |
|---|---|---|---|
| bug-517 | todo | 692 (soft) | AI narration broadcast as character speech |
| bug-523 | todo | 692 (soft) | plan grounding uses unmasked real names |
| task-692 | todo | — | narration v2: DM layer, not a client rewriter |

### Graph editor

| Task | Status | Depends on | Summary |
|---|---|---|---|
| task-290 | todo | — | template variants and override tracking |
| task-422 | todo | — | NL editor LLM budget controls |
| task-435 | todo | — | offline generators still mint way templates |
| task-461 | wip | — | NL editor validation gate |

### Testing and docs

| Task | Status | Depends on | Summary |
|---|---|---|---|
| task-693 | todo | — | e2e verification harness |
| task-697 | todo | 693 (soft) | validate gate requires a checked acceptance box |
| task-668 | todo | — | `room-context.js` body mojibaked UTF-8 |
| task-669 | todo | — | doc headers on 162 Python modules |
| task-672 | todo | — | inspector-panels doc describes controls that do not exist |
| task-695 | todo | 587 | live verification playbook |
| task-574 | wip | — | test guide: the worldpainter session |
| task-587 | wip | — | executable manual test plan |

### Misc (conditions / engine / environment / items)

| Task | Status | Depends on | Summary |
|---|---|---|---|
| task-705 | todo | — | requirement condition leaves quantity/area/knowledge/ownership |
| task-708 | todo | — | despawn effect: remove a character from a trigger |
| task-555 | todo | — | wind gets a direction |
| task-556 | todo | — | weather reaches the world, snow accumulation |
| task-703 | todo | 701 | recipes become plan templates |
| task-660 | wip | — | auto-dress deterministic tag matching |

---

## Startable now (no unmet dependency)

- **task-352** action economy — decisions locked.
- **task-734** knowledge = memory — independent, and the load-bearing one.
- **task-735** aging / lifecycle — needs only the time/soak clock.
- **task-731** activities via object — in flight.
- **task-732** sync grouping — continues on the landed bug-526 fix.

## Critical path

```
446 ─▶ 724 ─▶ 734 ─▶ 736
              └────▶ 733 ◀─ 735
352 ─▶ 736, 737
673 ─▶ 675 ─▶ 733
401 ─▶ 710 ─▶ 711
```

**734 is the linchpin**: the mind panel, the map, the sheet's biography and the memory
creation flow all read/write it. Build it before piling more authoring (733) or more
views (736/714) on top, or each consumer relearns five separate knowledge stores.

## Landed this session (uncommitted)

- **bug-524** fix: node is the authored home; live read publishes it;
  `to_scenario_dict` strips the duplicate; inspector edit mirrors to the node.
  Live-verified.
- **bug-525** fix: death ends the character's activity (no forced `wake`).
- **bug-526** fix: Sync All is tab-scoped and skips generated entities.
- **task-731** core: furniture templates wired to activities; bare `fish` deleted.
- **task-732** core: item instances collapse into template rows.
- Docs: `AGENTS.md` invariant rewritten; `docs/design/character-inner-life-threads.md`.

*Python/library changes need a server restart to be live; frontend changes are live on
reload.*
