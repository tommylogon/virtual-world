#!/usr/bin/env python3
"""
tools/generate_master_overview.py

Generates the exhaustive Master Overview markdown artifact:
`client_architecture_and_component_master_plan.md`
Cataloging:
- System census
- Subsystems and their responsibilities
- Duplication breakdown
- Component specifications
- Typed model contracts
- Phased refactoring roadmap
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "scratch" / "client_audit_data.json"
ARTIFACT_PATH = Path("C:/Users/Tommy/.gemini/antigravity/brain/a9c266b3-b18b-4309-bcf5-709434e70489/client_architecture_and_component_master_plan.md")

def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    records = data["records"]

    by_dir = {}
    for r in records:
        d = r["dir"]
        by_dir.setdefault(d, []).append(r)

    # Subsystem descriptions
    subsystem_desc = {
        ".": "Core application coordinator, world-state cache, API client, global event streams, and shell wiring.",
        "inspector": "Right-panel node inspectors (Item, Area, Character, Way, Behaviors, Mind, SpriteSheet, Memory).",
        "graph": "vis.js graph view, layout engines, node operations, physics toolbar, and background canvases.",
        "shared": "Cross-cutting editors (trigger editor, trigger graph, diff modal, DOM helpers, lit-bootstrap).",
        "agent": "Character agent loop, prompt builders, emote picker, turn queue management, and goal trackers.",
        "ui": "Global UI panels (engine config, settings, outliner, scenario wizard, node creation modals).",
        "commons": "The Commons simultaneous communication interface (channel UI, agent cadence, drawer).",
        "soak": "Long-running simulation soak test harness, telemetry monitors, and soak UI dashboard.",
        "nl-editor": "Natural language scenario authoring and editing tools.",
        "worldpainter": "Tile grid map authoring, visual paint tools, and 2D spatial layout editor.",
        "item-library": "Item template browser, recipe viewer, loadout editor, and placement tools.",
        "stream": "Live narrative event stream, LLM output raw view, and persistence buffers."
    }

    md = []
    md.append("# Client Architecture & Component Master Overview\n")
    md.append("**Generated:** 2026-10-26\n")
    md.append("**Scope:** Exhaustive audit across 183 TypeScript files and 101,189 lines in `static/js/`.\n")
    md.append("\n---\n")

    # Section 1: Executive Census
    md.append("## 1. Executive Census\n")
    md.append(f"- **Total TypeScript Files:** {data['total_files']}\n")
    md.append(f"- **Total Client Lines of Code:** {data['total_lines']:,}\n")
    md.append(f"- **Total Untyped `any` Instances:** {data['total_any']:,}\n")
    md.append(f"- **Direct `.innerHTML =` Assignments:** {data['total_inner_html']}\n")
    md.append(f"- **Imperative `document.createElement()` Calls:** {data['total_create_element']}\n")
    md.append(f"- **Lit-HTML Tagged Template Blocks:** {data['total_lit_blocks']}\n")
    md.append(f"- **`unsafeHTML()` Workarounds:** {data['total_unsafe_html']}\n\n")

    md.append("### Directory & Volume Breakdown\n\n")
    md.append("| Subsystem Directory | Files | Lines | `any` Count | Dominant Architecture | Primary Role |\n")
    md.append("|---|---|---|---|---|---|\n")

    for d, files in sorted(by_dir.items(), key=lambda x: len(x[1]), reverse=True):
        lines = sum(f["lines"] for f in files)
        anys = sum(f["any_count"] for f in files)
        archs = {}
        for f in files:
            archs[f["dom_arch"]] = archs.get(f["dom_arch"], 0) + 1
        dom_arch = sorted(archs.items(), key=lambda x: x[1], reverse=True)[0][0]
        desc = subsystem_desc.get(d, "Specialized client utilities.")
        md.append(f"| `static/js/{d}` | {len(files)} | {lines:,} | {anys} | `{dom_arch}` | {desc} |\n")

    md.append("\n---\n")

    # Section 2: Domain Model Registry
    md.append("## 2. Domain Model Registry (The Typed Contracts)\n")
    md.append("Viwo has 6 core domains. Currently, the client represents nearly all of them as untyped `any` dictionaries attached to `worldState.data`. Below is the required TypeScript contract for each:\n\n")

    md.append("### 2.1 Physical Entities (`WorldGraph` Nodes)\n")
    md.append("```ts\n")
    md.append("// Base Physical Node\n")
    md.append("export interface BaseNodeModel {\n")
    md.append("    id: string;\n")
    md.append("    type: 'area' | 'item' | 'way' | 'character' | 'logic_trigger';\n")
    md.append("    name: string;\n")
    md.append("    created: number;\n")
    md.append("    updated: number;\n")
    md.append("    properties: Record<string, unknown>;\n")
    md.append("}\n\n")
    md.append("export interface ItemModel extends BaseNodeModel {\n")
    md.append("    type: 'item';\n")
    md.append("    properties: {\n")
    md.append("        weight?: number;\n")
    md.append("        uses?: number;\n")
    md.append("        equip_slot?: string;\n")
    md.append("        consumable?: boolean;\n")
    md.append("        quantity?: number;\n")
    md.append("        tags?: string[];\n")
    md.append("        traits?: string[];\n")
    md.append("        description?: string;\n")
    md.append("    };\n")
    md.append("}\n\n")
    md.append("export interface AreaModel extends BaseNodeModel {\n")
    md.append("    type: 'area';\n")
    md.append("    properties: {\n")
    md.append("        environment?: string;\n")
    md.append("        description?: string;\n")
    md.append("        statuses?: string[];\n")
    md.append("        light_level?: number;\n")
    md.append("        temperature?: number;\n")
    md.append("        grid_x?: number;\n")
    md.append("        grid_y?: number;\n")
    md.append("        scope?: string;\n")
    md.append("    };\n")
    md.append("}\n\n")
    md.append("export interface WayModel extends BaseNodeModel {\n")
    md.append("    type: 'way';\n")
    md.append("    properties: {\n")
    md.append("        open?: boolean;\n")
    md.append("        locked?: boolean;\n")
    md.append("        key_id?: string;\n")
    md.append("        direction?: string;\n")
    md.append("        two_way?: boolean;\n")
    md.append("        prevent_close?: boolean;\n")
    md.append("        requires?: 'crawl' | 'climb' | 'jump';\n")
    md.append("    };\n")
    md.append("}\n")
    md.append("```\n\n")

    md.append("### 2.2 Cognitive & Actor Models (`Player`)\n")
    md.append("```ts\n")
    md.append("export interface PlayerRuntimeModel {\n")
    md.append("    id: string;\n")
    md.append("    name: string;\n")
    md.append("    node_id: string;\n")
    md.append("    vitals: {\n")
    md.append("        HP: number;\n")
    md.append("        Energy: number;\n")
    md.append("        Hunger: number;\n")
    md.append("        Thirst: number;\n")
    md.append("        Bladder: number;\n")
    md.append("        Hygiene: number;\n")
    md.append("        Mana?: number;\n")
    md.append("        Arousal?: number;\n")
    md.append("        Stimulation?: number;\n")
    md.append("        Pleasure?: number;\n")
    md.append("    };\n")
    md.append("    stats: Record<'STR'|'DEX'|'CON'|'INT'|'WIS'|'CHA', number>;\n")
    md.append("    personality_dials: Record<string, number>; // 0.0 - 1.0 trait weights\n")
    md.append("    goals: GoalModel[];\n")
    md.append("    memories: MemoryRecord[];\n")
    md.append("    conditions: Record<string, boolean | number>;\n")
    md.append("}\n\n")
    md.append("export interface MemoryRecord {\n")
    md.append("    id: string;\n")
    md.append("    text: string;\n")
    md.append("    timestamp: number;\n")
    md.append("    subject_node_id?: string;\n")
    md.append("    novelty?: number;\n")
    md.append("    valence?: number;\n")
    md.append("}\n\n")
    md.append("export interface GoalModel {\n")
    md.append("    id: string;\n")
    md.append("    what: string;\n")
    md.append("    status: 'active' | 'completed' | 'abandoned';\n")
    md.append("    motivation?: string;\n")
    md.append("    intention?: string;\n")
    md.append("}\n")
    md.append("```\n\n")

    md.append("### 2.3 Visual & Asset Models\n")
    md.append("```ts\n")
    md.append("export interface SpriteSheetModel {\n")
    md.append("    imageUrl: string;\n")
    md.append("    cellWidth: number;\n")
    md.append("    cellHeight: number;\n")
    md.append("    columns: number;\n")
    md.append("    rows: number;\n")
    md.append("    animations: Record<string, { startFrame: number; frameCount: number; speed: number }>;\n")
    md.append("}\n")
    md.append("```\n\n")

    md.append("\n---\n")

    # Section 3: Duplication Matrix
    md.append("## 3. The Duplication Matrix (Where Code is Re-invented)\n\n")

    modals = [r for r in records if r["duplication_flags"]["modal"]]
    headers = [r for r in records if r["duplication_flags"]["header_sync"]]
    dangers = [r for r in records if r["duplication_flags"]["danger_zone"]]
    tabs = [r for r in records if r["duplication_flags"]["tabs"]]
    sliders = [r for r in records if r["duplication_flags"]["slider"]]
    badges = [r for r in records if r["duplication_flags"]["badge"]]

    md.append(f"### 3.1 Modal Windows & Overlays ({len(modals)} Files)\n")
    md.append("Each of these files implements its own backdrop `div`, `position: fixed`, z-index stacking, escape-key listener, or close button:\n")
    for r in sorted(modals, key=lambda x: x['lines'], reverse=True)[:15]:
        md.append(f"- [`{r['file']}`](file:///{ROOT.as_posix()}/{r['file']}) ({r['lines']} lines) - Arch: `{r['dom_arch']}`\n")

    md.append(f"\n### 3.2 Entity Headers & ID Sync ({len(headers)} Files)\n")
    md.append("Duplicating title inputs, rename handlers, lowercase sanitization, and sync-ID buttons:\n")
    for r in sorted(headers, key=lambda x: x['lines'], reverse=True)[:15]:
        md.append(f"- [`{r['file']}`](file:///{ROOT.as_posix()}/{r['file']}) ({r['lines']} lines)\n")

    md.append(f"\n### 3.3 Danger Zones & Delete Confirmations ({len(dangers)} Files)\n")
    md.append("Duplicating delete buttons, `confirm()` dialogs, and graph node removal dispatches:\n")
    for r in sorted(dangers, key=lambda x: x['lines'], reverse=True)[:15]:
        md.append(f"- [`{r['file']}`](file:///{ROOT.as_posix()}/{r['file']}) ({r['lines']} lines)\n")

    md.append(f"\n### 3.4 Status Badges & Pills ({len(badges)} Files)\n")
    md.append("Duplicating pill styling, state colors, and dot indicators:\n")
    for r in sorted(badges, key=lambda x: x['lines'], reverse=True)[:15]:
        md.append(f"- [`{r['file']}`](file:///{ROOT.as_posix()}/{r['file']}) ({r['lines']} lines)\n")

    md.append(f"\n### 3.5 Sliders & Range Controls ({len(sliders)} Files)\n")
    md.append("Duplicating range inputs, dual-handle tracks, and value labels:\n")
    for r in sorted(sliders, key=lambda x: x['lines'], reverse=True)[:10]:
        md.append(f"- [`{r['file']}`](file:///{ROOT.as_posix()}/{r['file']}) ({r['lines']} lines)\n")

    md.append("\n---\n")

    # Section 4: Component Design System
    md.append("## 4. The Unified Component Design System\n")
    md.append("To eliminate this duplication, we extract a shared component hierarchy using vendored `lit-html 3.2.1`.\n\n")

    md.append("### 4.1 Presentational Primitives (`static/js/shared/components/primitives/`)\n")
    md.append("| Component | Props | Emits | Purpose |\n")
    md.append("|---|---|---|---|\n")
    md.append("| `ModalDialog` | `{ title, isOpen, size?, content, onClose }` | `onClose` | Standardizes backdrop, Escape key, and focus containment. |\n")
    md.append("| `StatusBadge` | `{ label, color?, icon?, active? }` | None | Replaces all 66 ad-hoc badge HTML strings. |\n")
    md.append("| `CollapsibleSection` | `{ title, defaultOpen?, badge?, content }` | `onToggle` | Standard disclosure with uniform chevron and header styling. |\n")
    md.append("| `DualRangeSlider` | `{ min, max, lowVal, highVal, unit? }` | `onChange(low, high)` | Reusable dual-thumb slider (from benchmark). |\n")
    md.append("| `ActionBtn` | `{ label, variant, icon?, disabled?, onClick }` | `onClick` | Uniform button with primary, ghost, danger variants. |\n")
    md.append("| `TabNav` | `{ tabs: string[], activeTab: string }` | `onTabChange(tab)` | Unified tab navigation strip. |\n\n")

    md.append("### 4.2 Composite Domain Widgets (`static/js/inspector/components/`)\n")
    md.append("| Component | Props | Emits | Replaces |\n")
    md.append("|---|---|---|---|\n")
    md.append("| `InspectorNodeHeader` | `{ node: BaseNodeModel, isGenerated? }` | `onRename`, `onSyncId`, `onClose` | 4 duplicated inspector header blocks (~260 lines). |\n")
    md.append("| `InspectorDangerZone` | `{ nodeName, nodeType }` | `onDelete` | 5 duplicated delete confirmation blocks (~180 lines). |\n")
    md.append("| `PropertyGrid` | `{ fields: FieldDef[], values: Record<string, unknown> }` | `onChange(key, val)` | Disorganized input groups across all inspector views. |\n")
    md.append("| `VitalsMeterGrid` | `{ vitals: Record<string, number>, decayRates? }` | None | Duplicated vitals displays in agent-view, commons, and soak. |\n")
    md.append("| `MemoryCardList` | `{ memories: MemoryRecord[] }` | `onForget`, `onEdit` | Ad-hoc memory tables in memory-view and mind-view. |\n")
    md.append("| `GoalCardList` | `{ goals: GoalModel[] }` | `onComplete`, `onAbandon` | Ad-hoc goal lists in agent-view and mind-view. |\n")

    md.append("\n---\n")

    # Section 5: Subsystem Responsibility Map
    md.append("## 5. Subsystem Responsibility Map (Every File's Role)\n\n")

    for d, files in sorted(by_dir.items(), key=lambda x: len(x[1]), reverse=True):
        md.append(f"### Subsystem: `static/js/{d}` ({len(files)} files)\n\n")
        md.append("| File | Lines | Any | Dom Arch | Exported Classes / Functions | Primary Responsibility |\n")
        md.append("|---|---|---|---|---|---|\n")
        for f in sorted(files, key=lambda x: x["lines"], reverse=True):
            cls = ", ".join(f["classes"][:2]) if f["classes"] else ""
            fn_sample = ", ".join(f["functions_sample"][:2]) if f["functions_sample"] else ""
            surface = cls or fn_sample or "-"
            md.append(f"| [`{f['name']}`](file:///{ROOT.as_posix()}/{f['file']}) | {f['lines']} | {f['any_count']} | `{f['dom_arch']}` | `{surface}` | {f['dir']} component |\n")
        md.append("\n")

    md.append("\n---\n")

    # Section 6: Phased Refactoring Roadmap
    md.append("## 6. Phased Implementation Roadmap\n\n")
    md.append("### Phase 1: Inspector Primitives (task-904 Phase 1)\n")
    md.append("- Target Files: `static/js/inspector/components.ts`, `item-view.ts`, `area-view.ts`, `way-view.ts`.\n")
    md.append("- Extract `InspectorNodeHeader` and `InspectorDangerZone` into `components.ts`.\n")
    md.append("- Eliminate 260+ lines of duplicated header and delete markup.\n")
    md.append("- Risk: Low. Pure presentational refactoring; backend contracts unchanged.\n\n")

    md.append("### Phase 2: Shared UI Primitives (`static/js/shared/components/`)\n")
    md.append("- Target Files: `ModalDialog.ts`, `StatusBadge.ts`, `CollapsibleSection.ts`, `DualRangeSlider.ts`.\n")
    md.append("- Replace 50 ad-hoc modal implementations and 66 status badge strings.\n")
    md.append("- Wire into `commons-ui.ts`, `create-modal.ts`, `diff-modal.ts`.\n")
    md.append("- Risk: Low.\n\n")

    md.append("### Phase 3: Domain Model Typing (`static/js/types/models/`)\n")
    md.append("- Target Files: `models/entities.ts`, `models/player.ts`, `models/events.ts`.\n")
    md.append("- Replaces 1,569 `: any` and `as any` casts with strict TypeScript interfaces.\n")
    md.append("- Type `worldState.data` and `worldState.runtimeData`.\n")
    md.append("- Risk: Medium (will surface latent type errors that must be resolved cleanly).\n\n")

    md.append("### Phase 4: Monolith Decomposition\n")
    md.append("- Target Monoliths: `agent-view.ts` (2,853 lines), `mind-view.ts` (2,465 lines), `trigger-graph.ts` (3,236 lines).\n")
    md.append("- Split into MVC controllers consuming the shared component library.\n")
    md.append("- Risk: Medium.\n\n")

    md.append("### Phase 5: CI & Lint Guard\n")
    md.append("- Target Files: `tools/log_lint.cjs` / ESLint.\n")
    md.append("- Enforce ban on new raw `.innerHTML =` and `unsafeHTML()` assignments.\n")
    md.append("- Enforce maximum `any` thresholds so the codebase never regresses.\n")

    ARTIFACT_PATH.write_text("".join(md), encoding="utf-8")
    print(f"Wrote complete Master Overview to {ARTIFACT_PATH}")

if __name__ == "__main__":
    main()
