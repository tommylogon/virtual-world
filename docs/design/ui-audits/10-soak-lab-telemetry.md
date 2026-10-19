# Soak Lab & Simulation Telemetry UI Audit & Redesign Specification

> **Status: UNVERIFIED DRAFT (2026-10-19).** Written from file headers and partial reads. Line counts, wireframes and several failure claims were NOT measured or reproduced live. Treat every claim here as a lead to check, not a finding. Verified findings live in the task cards, not in this document.


**Surfaces:**
- Soak UI & Dashboards (`static/js/soak/soak-ui.ts`) - 1,519 lines
- Soak Charts (`static/js/soak/soak-charts.ts`) - 820 lines
- Soak Space-Time Ribbon (`static/js/soak/soak-spacetime.ts`) - 640 lines
- Soak State Controller (`static/js/soak/soak-state.ts`) - 590 lines
**Rendering Tech:** Dedicated SPA route (`/soak`) using HTML5 Canvas line graphs and CSS grid metrics.

---

## 1. Measured Ground Truth & Architecture

The Soak Lab executes long-horizon headless simulations (1,000 to 50,000 ticks) to evaluate:
- Vital decay rates (Hunger, Thirst, Stamina, Body Temp)
- Character death cascades and causes
- Memory growth and token bloat over time
- Space-time traversal ribbon (who was where across 10,000 minutes)

### Telemetry Pipeline
- Driven by `POST /api/soak/run` or websocket live-streaming.
- `soak-charts.ts` renders custom lightweight canvas charts (vital curves, death histograms) without external D3/Chart.js dependencies.

---

## 2. Usability & Layout Critique

### A. The "Wall of Charts" Sensory Overload
- Opening `/soak` renders 6 full-width canvas graphs stacked vertically.
- On standard screens, comparing a vital dip (e.g. cold spike at Tick 400) with a character death requires scrolling up and down repeatedly.

### B. Space-Time Ribbon Legend Truncation
- The Space-Time ribbon maps time (X-axis) against areas (Y-axis) with colored character ribbons.
- When a scenario contains more than 15 characters, the ribbon colors cycle and repeat, making it impossible to distinguish Thorne from Jerry without hovering every single ribbon segment.

---

## 3. Redesign Specification & Layout Blueprint

### Target Layout: Telemetry Command Center

```
+----------------------------------------------------------------------------------------------------+
| 🧪 SOAK LAB: Long-Horizon Telemetry Run #412                  [ Export Run Data ] [ New Soak Run ] |
| Scenario: Eldenford (5,000 Ticks · 83h Game Time)             Duration: 42s Real Time              |
+----------------------------------------------------------------------------------------------------+
| RUN SUMMARY KPI TILES                                                                              |
| [ Survival Rate: 87.5% ]   [ Deaths: 2 (Hypothermia) ]   [ Peak Memories: 412 ]   [ OOM Risk: Low ]|
+----------------------------------------------------+-----------------------------------------------+
| SYNCHRONIZED CHARTS VIEW (Crosshair Linked)        | EVENT & DEATH LOG                             |
|                                                    |                                               |
| 1. Population & Survival Curve                     | 💀 TICK 1,420: Jerry (Bartender)              |
|    [=======================-\______________]       |    Cause: Freezing (Body Temp dropped < 20°C) |
|                                                    |    Location: Eldenford North Cellar           |
| 2. Average Body Temperature (°C)                   |                                               |
|    [~~~~~~\___________/~~~~~~~~~~~~~~~~~~~~]       | 💀 TICK 2,890: Goblin Scout                   |
|           ^ Tick 1,400 (Cold Snap)                 |    Cause: Starvation (0 Food in Camp)         |
|                                                    |                                               |
| 3. Memory Ledger Growth (Linear, No Leaks)         | [ 🔍 Filter by Actor ▾ ] [ Export CSV ]       |
|    [/--------------------------------------]       |                                               |
+----------------------------------------------------+-----------------------------------------------+
| TIMELINE SCRUBBER: Tick [ 1,420 ] (Click chart to jump inspection)                                 |
+----------------------------------------------------------------------------------------------------+
```

### Core Architecture Upgrades

1. **Synchronized Cursor Scrubbing**
   - Hovering over any point on the temperature chart renders a vertical indicator needle across all 4 charts simultaneously, instantly correlating cause and effect.

2. **Semantic Death Cause Attribution**
   - Automatically group character deaths into actionable simulation flags:
     `[ 2x Cold Exposure in Cellar -> Needs Heat Source ]`.
