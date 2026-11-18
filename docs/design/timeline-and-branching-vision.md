# Timeline & Branching Vision Guide

Source: Handwritten Vision Guide (`14/11 2026 Timeline`).

## Goal

Turn VirtualWorld into a navigable, branchable, multi-month timeline system where authors and players can jump to any point in scenario time (e.g., May -> August -> September -> October), fork variations ("go back and redo a character's actions"), play or soak from that branch, and never contaminate sibling timelines or leak future memories into the past.

## Core Principles

1. **Dates, Not Arbitrary Day Counters:**
   - Events, world snapshots, Commons messages, and memories carry real calendar timestamps (`world_datetime`, ISO-8601) derived from `VirtualWorld`'s existing calendar (`game_year`, `game_month`, `game_day`, `get_current_time()`), or an anchored real-time clock in standalone Commons mode.
   - Phone/chat UIs (The Commons) render phone-style `HH:MM` + calendar date headers, never `Day N`.
2. **Time-Locked Memory Recall (No Future Leaks):**
   - When the world clock is positioned at timestamp `T` (e.g., `2016-05-14` or `2016-08-01`), memory retrieval and prompt assembly **lock memories by time** and deny recall of any memory with `world_datetime > T`.
3. **Zero Cross-Timeline Contamination:**
   - Every branch has an explicit `branch_id` (default `main`) and parent `(parent_branch_id, fork_datetime)`.
   - Reads on a branch walk its ancestor chain up to `fork_datetime` plus its own events/memories after `fork_datetime`, isolating edits, deaths, entity existence, and memories from sibling branches.
4. **Single Unified Branching Model:**
   - Viwo scenario branching and Commons conversation branching share `(branch_id, world_datetime)` semantics rather than inventing two incompatible history systems.

## Phased Breakdown

### Phase 1: Dated Memories & Phone-Style Calendar Time (Current)
- **task-976:** Stamp `world_datetime` on `Memory` records from `VirtualWorld`'s existing calendar, format calendar dates + relative ages in Mind View and recall prompts, and enforce future-memory time-locking (`world_datetime <= current_world_datetime`).
- **task-977:** Replace `Day N` with real calendar dates and phone-style timestamps across `/commons`, `routes/commons.py`, and `commons-agent.ts`.

### Phase 2: Commons Standalone Mode & Anchored Clock
- **task-978:** `Use Viwo State` toggle in `/commons` (Connected mode vs Standalone SillyTavern-style mode with isolated sessions, branching, and reset).
- **task-979:** Anchored real-time clock (`anchor_datetime + real_elapsed_seconds`) with manual date/time controls so historical eras like 2016 Millwood tick in real time without jumping to 2026.

### Phase 3: Scenario Timeline Engine & Branching
- Track entity existence across time (spawn/entry/exit/death windows).
- Support branching at any historical point ("redo a character's actions"), incorporating manual edits, weather changes (`SkyScape`), `PlayMode`, `run_sim`, `soak`, and `timeskip` on the active branch.
- Save/load timeline trees by default with the scenario, expand current timeline, and connect past/future timelines where possible without cross-branch contamination.

### Phase 4: Interactive Timeline UI (`Replaces EventStream?`)
- Zoomable, scrollable, searchable, filterable multi-month timeline (`May -> August -> September -> October`) showing who did what, hover-to-reveal event details, branch/fork actions, and `PlayMode` entry at any node.
