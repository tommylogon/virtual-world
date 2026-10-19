---
type: doc
tags: [system/gameplay, system/grid, system/vision]
---

# Grid Line of Sight & Charted Memory

## What you can do

Every grid layer in the simulation (world grids, settlement maps, and interior floorplans) models physical sight using a 2.5D angular slope-sweep viewshed algorithm. Standing behind a stone wall, solid barrier, or dense tree line blocks visibility to anything behind it. Moving to high ground (ridges, hills, second-story parapets, or watchtowers) elevates your eye line, allowing you to look over low barriers into valleys and open fields.

As your character traverses the world, cells you see or visit are stamped into persistent charted memory (`player.charted_cells`). The turn minimap visualizes this through four distinct visibility tiers (live sight, horizon visibility, charted memory, and uncharted fog). You can click any charted cell to travel there directly via timeskip, or use the zero turn-cost `recall` action (`recall path to <target>` / `recall map`) to query your character's spatial memory without spending major or minor action slots. Autonomous LLM agents use the same sightlines and memory model: instead of flooding prompt context with raw coordinate matrices, agents receive a single bounded horizon line (~25 tokens) and query paths on demand.

## Where it lives

- `engine/world_grid.py` - [`viewshed_slope_sweep`](file:///f:/AI/viwo/virtual-world/engine/world_grid.py), [`calculate_2_5d_los`](file:///f:/AI/viwo/virtual-world/engine/world_grid.py), obstruction heights, and elevation calculations.
- `static/js/worldpainter/grid-model.ts` (and `.js`) - client-side TypeScript port of the 2.5D raycast and viewshed algorithm for zero-latency client rendering.
- `player.py` - [`Player.charted_cells`](file:///f:/AI/viwo/virtual-world/player.py) persistent dictionary holding explored coordinates per scope.
- `engine/character_record.py` - [`CharacterRecord.charted_cells`](file:///f:/AI/viwo/virtual-world/engine/character_record.py) dataclass field definition.
- `engine/serialization.py` - save and load round-tripping for charted memory across game sessions.
- `engine/observation.py` - [`update_charted_memory`](file:///f:/AI/viwo/virtual-world/engine/observation.py) observer hook updating visibility on player arrival and turns.
- `engine/spatial_memory.py` - [`recall_path`](file:///f:/AI/viwo/virtual-world/engine/spatial_memory.py) and [`recall_landmarks`](file:///f:/AI/viwo/virtual-world/engine/spatial_memory.py) A* pathfinding and landmark retrieval from charted memory.
- `routes/action_handlers.py` - `recall` action dispatcher mapped to the `FREE` action tier.
- `static/js/agent/turn-minimap.ts` (and `.js`) - 4-tier visual rendering lattice (`tmn-now`, `tmn-visible`, `tmn-charted`, `tmn-cell`) with interactive destination popups.
- `static/js/agent/prompt-builder/room-context.ts` (and `.js`) - compact horizon context injector for agent prompts.
- `tests/test_world_grid.py`, `tests/test_player_map.py`, `tests/test_spatial_memory.py` - unit and integration tests.

**Tasks:** [[dev_tasks/review/world/task-882-elevation-and-obstruction-2-5d-raycast-line-of-sight-on-world-and-settlement-grids|task-882]] · [[dev_tasks/review/world/task-677-grid-to-graph-elevation-and-multi-level-ways|task-677]]

---

## 2.5D Elevation & Obstruction Model

### Mathematical Formulation

Grid entities exist on a 2D integer lattice `(x, y)` augmented with floor tiers and fine elevation. The effective physical altitude of any point is calculated as:

$$\text{Effective Elevation} = (\max(\text{floor}, 0) \times 3.0) + (\text{elevation} \times 1.5)$$

- Each building floor tier represents standard vertical clearance ($3.0\text{ m}$).
- Each contour elevation increment represents $1.5\text{ m}$ of terrain rise.
- The observer eye height is set to $\text{Effective Elevation} + 1.8\text{ m}$.

### Obstacle Heights

Obstacles project physical blocking height above the ground surface:

| Terrain / Feature Type | Height Added | Visibility Effect |
|---|---|---|
| Plain grass, dirt, floor | $0.0\text{ m}$ | Completely open |
| Low wall, fence, hedgerow | $1.5\text{ m}$ | Blocks ground-level sight; cleared from horseback or high ground |
| Stone wall, closed palisade | $3.0\text{ m}$ | Blocks standard ground eye line; cleared from second floor |
| Standard building / roof | $4.0\text{ m}$ | Requires tower or hill elevation to overlook |
| Dense forest canopy, fortress | $5.0\text{ m}$ | Tall horizon obstruction |
| Mountain peak, high spire | $8.0\text{ m}+$ | Prominent landmark visible across long distances |

### Angular Slope-Sweep Algorithm

Line of sight between observer $(x_0, y_0)$ and target $(x_1, y_1)$ at distance $d$ is determined by comparing tangent angles (slopes):

$$\text{Target Slope} = \frac{\text{Target Top Altitude} - \text{Eye Altitude}}{d}$$

For every intermediate cell along the Bresenham or sampled ray at distance $d_i < d$:

$$\text{Obstacle Slope} = \frac{\text{Ground Altitude}_i + \text{Obstacle Height}_i - \text{Eye Altitude}}{d_i}$$

If any intermediate cell has $\text{Obstacle Slope} \ge \text{Target Slope}$, the target falls inside the obstruction's geometric shadow and is invisible. If the observer ascends, $\text{Eye Altitude}$ increases, reducing the intermediate obstacle slopes and expanding the visible footprint.

---

## The Four Visibility Tiers

The grid renderer and perceptual filters evaluate every coordinate against four mutually exclusive tiers:

```
[ Uncharted Fog ] ---> [ Charted Memory ] ---> [ Horizon Visible ] ---> [ Live View (Now) ]
 (Pitch black)         (Static terrain)        (Tall landmarks)          (Entities & actors)
```

1. **`tmn-now` (Live View):**
   - The cell is within immediate line of sight and within sensory range.
   - Renders brightly highlighted in gold or blue.
   - Shows active characters, dropped items, interactive furniture, open doors, and current terrain.
   - Any event occurring here produces real-time notifications and logs.

2. **`tmn-visible` (Horizon Sight):**
   - The cell is beyond immediate interaction distance but has an unobstructed sightline that clears the angular slope threshold.
   - Highlights landmark terrain (spires, watchtowers, settlements, mountain ridges).
   - Shows static geographic contours; mobile actors and small items remain concealed.

3. **`tmn-charted` (Spatial Memory):**
   - The cell was previously seen or traversed, but is currently out of direct line of sight or behind an obstruction.
   - Renders in muted slate grey.
   - Displays terrain and static architecture as they were when last observed.
   - Mobile entities, dynamic item changes, and ambushes are hidden.

4. **`tmn-cell` (Uncharted Fog of War):**
   - The cell has never been reached, viewed from high ground, or revealed by a map item.
   - Renders as dark, uncharted grid cells with minimal dot guides.
   - Completely withheld from prompt observations and player inspection.

---

## Charted Memory Persistence

Exploration state is stored directly on the character model in `player.charted_cells`:

```python
player.charted_cells = {
    "world:12,14": {
        "terrain": "road",
        "label": "Old King's Highway",
        "seen_at": 1729350000,
        "elevation": 1
    },
    "world:12,15": {
        "terrain": "stone_wall",
        "label": "Town Perimeter",
        "seen_at": 1729350010,
        "elevation": 1
    }
}
```

- Keys use the canonical format `"{scope_id}:{x},{y}"`.
- Entries record terrain type, recognized labels, observation timestamp, and recorded elevation.
- Serialized in `engine/serialization.py` as part of the standard save format.
- Stamping occurs automatically in `engine/observation.py` whenever a character finishes a step or executes a survey action.

---

## Turn Minimap UI & Interaction

The turn minimap (`static/js/agent/turn-minimap.ts`) operates directly on the turn composer surface:

### Interactive Navigation
- **Clicking a Charted Cell:** Opens a modal popover displaying the cell's recorded name, terrain type, and elevation.
- **`⏩ Walk here` Action:** Evaluates an A* path through charted territory and triggers the timeskip transit system (`static/js/agent/timeskip-dialog.ts`), moving the character turn by turn along the path.
- **Fog Prevention:** Clicking an uncharted cell displays a "Terrain unknown" notice; blind automated timeskip travel into uncharted fog is disabled.

---

## Cognitive Agency & The `recall` Action

To prevent prompt bloat and eliminate psychic agent behavior, spatial intelligence is modeled as an active character capability rather than static background data.

### Action Tier: `FREE`
- Recall actions belong to the `FREE` action tier (3 free actions allowed per round).
- Performing a recall action does not consume minor movement or major combat/interaction action slots.

### Available Verbs

| Command | Engine Handler | Result |
|---|---|---|
| `recall map` | `engine/spatial_memory.py` | Summarizes boundaries, discovered landmarks, and total charted area. |
| `recall path to <target>` | `engine/spatial_memory.py` | Runs internal A* on `charted_cells` and outputs step-by-step directions. |
| `recall landmarks` | `engine/spatial_memory.py` | Lists known prominent landmarks and their relative headings and distances. |

Example console output for `recall path to tavern`:
```text
[Spatial Memory] Path to The Boar's Tusk Tavern:
1. Walk North 3 cells along Town Square (road)
2. Turn East 2 cells past Bakery (cobblestone)
Total distance: 5 cells. Terrain is clear.
```

---

## LLM Agent Integration: Zero Prompt Flooding

Autonomous agents operating via LLM loops must balance spatial awareness against token budgets.

### The Problem
Injecting hundreds of raw grid coordinates, elevation heights, and neighbor lists into an LLM prompt costs between 1,500 and 3,000 tokens every single turn. This wastes budget, degrades reasoning focus, and leads to coordinate hallucination.

### The Solution: Horizon Context Hook
Instead of raw grids, `static/js/agent/prompt-builder/room-context.ts` parses the 2.5D viewshed and generates a single bounded horizon line:

```text
On the horizon: You can spot Kraktooth Spire (mountain, to the north-east, ~12 cells away)
```

- **Cost:** ~20 to 25 tokens total.
- **Perception Bounds:** The agent understands large landmarks in the distance without knowing what is behind every intermediate hedge.
- **No Psychic Cheating:** Characters on the far side of an obstruction (e.g. bandits behind an alley wall) are omitted from the agent's room perception. The agent only learns of them when it rounds the corner or achieves direct line of sight.
- **Autonomous Pathfinding:** When the agent needs to travel to a known location, it issues `recall path to <location>` as a free action, receives discrete verified steps, and executes movement cleanly.

---

## Verification & Test Suite

The system is tested across unit, mathematical, and integration layers:

- `tests/test_world_grid.py`: Verifies `calculate_2_5d_los`, angular slope calculations, low wall occlusion, high watchtower clearance, and perimeter ray bounds.
- `tests/test_player_map.py`: Verifies `player.charted_cells` save/load round-tripping, de-duplication, and observation stamping.
- `tests/test_spatial_memory.py`: Verifies `recall_path` A* execution through charted territory and handling of uncharted barriers.
- `tests/test_action_tiers.py`: Verifies `recall` consumes free action slots without touching major/minor turn slots.
- `tools/unit/run.cjs`: TypeScript compilation and unit tests for client-side raycast and minimap rendering.
