# Near-Term Project Focus (Q4 2026)

Strategic direction for VirtualWorld: shifting from broad mechanic accumulation
to depth, system wiring, vertical slice stability, and performance.

---

## The Core Problem: Breadth vs Depth

VirtualWorld has accumulated an enormous breadth of simulation engines: weather
curves, floor-plan compilers, vital decay, emotional states, pursuit drives,
hazard checks, turn queues, and graph projections.

However, the repo currently suffers from **unwired or half-digested systems**:
mechanics that compile and pass unit tests, but are unauthored in scenarios,
unconnected to active player loops, or blocked behind review backlogs.

For the next phase, focus shifts to **four operational pillars**.

---

## Pillar 1: Digestion Over Addition (Review Drain & System Wiring)

- **Drain the Review Queue**: There are over 200 cards sitting in `review`. Until
  cards in `review` are verified or closed, the backlog lies about its own state.
- **Wire What Already Exists**: Stop adding new subsystem engines when existing
  ones lack callers or authored data.
  - `lived_log` (task-811 / `lived-log-format.md`): Designed and structured, but
    needs runtime emission and consumer verification.
  - Pursuit drives (task-860): Needs concrete harness execution via
    `tools/drive_sim.py` instead of ad-hoc scratch scripts.
  - Persona reader fields (task-850): MBTI, alignment, birthdays, and media must
    be ingested by prompt constructors and sim tickers, not left as inert fields.
- **Rule of Thumb**: A feature is not done when the class compiles; it is done
  when a live scenario exercises it and records the output.

---

## Pillar 2: Triaging Audience Priority

Every proposed task must explicitly identify its primary beneficiary among three
distinct audiences:

1. **The World Author / DM**:
   - Needs: Ergonomic WorldPainter editing, robust interior/grid compilers,
     scenario management (task-374), and clear validation feedback.
2. **The Interactive Player**:
   - Needs: Clean Human Turn Console (HTC) UX, turn modal clarity, immediate
     sensory and verb feedback, intuitive movement/inspection.
3. **The Autonomous LLM Agent**:
   - Needs: Deterministic world state serialization, prompt compression without
     loss of spatial grounding, consistent personality/voice drivers, and clean
     event streams.

When trade-offs occur, the simulation model remains authoritative: UI and prompts
are projections of the graph, never alternate sources of truth.

---

## Pillar 3: The "Kraktooth Standard" (The Vertical Slice)

Rather than scattering mechanics across synthetic tests, establish one living,
canonical reference scenario: **Kraktooth Tribe** (`data/scenarios/goblin_camp.json`).

The benchmark for the next quarter is the **100-Turn Kraktooth Run**:
- 10+ NPCs and 1 human player operate simultaneously.
- Characters forage, eat, drink, seek warmth, sleep in designated beds, and
  converse according to their traits.
- Vitals decay according to calibrated rates without sudden starvation or
  inexplicable death spirals.
- The turn queue processes smoothly without getting stuck or racing.
- Spatial navigation respects doors, climbing tiers, and light/hazard conditions.

If a mechanic does not function inside the Kraktooth slice, it is treated as
unproven.

---

## Pillar 4: Performance, Concurrency, and Seams

1. **Client Performance & State Poll Racing**:
   - Resolve task-715: Ensure SSE (`/api/events`) and spectator polling do not
     collide or trigger duplicate `worldState.fetch()` passes.
   - Address WorldPainter paint latency (bug-545) on large grid scopes.
2. **Integration at the Seams**:
   - Unit tests are thorough (3,000+ tests), but cross-system seams are fragile.
   - Focus on end-to-end integration: save/load round-trips preserving state,
     timeskip determinism, and trigger cascade safety.
