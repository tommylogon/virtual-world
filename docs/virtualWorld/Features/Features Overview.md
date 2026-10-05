---
type: moc
area: docs
tags: [system/gameplay]
---

# Features Overview

**What this is:** one page per row of the [[Feature Map]] — the canonical list of what a person
can actually *do* in VirtualWorld, in a game and in the editor. Every page here is an **entry
point**: it says what the feature is, links the deep documentation that explains it, and says
plainly how confident the map is. None of them replaces the deep doc.

Generated from the Feature Map on 2026-10-05 — `python tools/feature_pages.py --scaffold` creates a
missing page, `--check` fails when a row loses its page (or when this page stops listing one).
Status counts: `planned` 2, `unwired` 1, `wired` 73.

## In a game

| # | Feature | Status | Deep documentation |
|---|---|---|---|
| 1 | [[look-around\|Look around]] | `wired` | [[Rooms & Areas]] |
| 2 | [[examine\|Examine]] | `wired` | [[Items Overview]] |
| 3 | [[move\|Move]] | `wired` | [[Doors & Connections]] |
| 4 | [[open-close\|Open / close]] | `wired` | [[Doors & Connections]] |
| 5 | [[take-drop-give\|Take / drop / give]] | `wired` | [[Items Overview]] |
| 6 | [[use-use-on\|Use / use on]] | `wired` | [[Items Overview]] |
| 7 | [[talk-speak\|Talk / speak]] | `wired` | [[NPC Behavior System]] |
| 8 | [[whisper-shout\|Whisper / shout]] | `wired` | [[NPC Behavior System]] |
| 9 | [[attack-grapple\|Attack / grapple]] | `wired` | [[Combat System]] |
| 10 | [[eat-drink\|Eat / drink]] | `wired` | [[Items Overview]] |
| 11 | [[sleep-rest\|Sleep / rest]] | `wired` | [[Vitals System]] |
| 12 | [[search-forage\|Search / forage]] | `wired` | [[Search & Forage]] |
| 13 | [[read-write\|Read / write]] | `wired` | [[Items Overview]] |
| 14 | [[wear-equip\|Wear / equip]] | `wired` | [[Equipment & Paperdoll]] |
| 15 | [[timeskip\|Timeskip]] | `wired` | [[Turn Queue & Human Turns]] |
| 16 | [[vitals-needs\|Vitals & needs]] | `wired` | [[Vitals System]] |
| 17 | [[conditions\|Conditions]] | `wired` | [[Conditions System]] |
| 18 | [[traits\|Traits]] | `wired` | [[Traits System]] |
| 19 | [[skills\|Skills]] | `wired` | [[Skills System]] |
| 20 | [[emotion\|Emotion]] | `wired` | [[Emotion & Affect System]] |
| 21 | [[relationships\|Relationships]] | `wired` | [[Relationships System]] |
| 22 | [[memory\|Memory]] | `wired` | [[Memory System]] |
| 23 | [[temperature\|Temperature]] | `wired` | — |
| 24 | [[light\|Light]] | `wired` | [[Light System]] |
| 25 | [[time-weather\|Time & weather]] | `wired` | [[Time & Weather]] |
| 26 | [[activities-states\|Activities & states]] | `wired` | [[Activities & States]] |
| 27 | [[npc-behaviour\|NPC behaviour]] | `wired` | [[NPC Behavior System]] |
| 28 | [[background-simulation\|Background simulation]] | `wired` | [[Background Simulation]], [[Character Pursuits]] |
| 29 | [[per-agent-knowledge-fog-of-war\|Per-agent knowledge (fog of war)]] | `unwired` | [[Per-Agent Knowledge (Fog of War)]] |
| 30 | [[turn-queue\|Turn queue]] | `wired` | [[Turn Queue & Human Turns]] |
| 31 | [[the-human-turn\|The human turn]] | `wired` | [[Turn Queue & Human Turns]] |
| 32 | [[character-art\|Character art]] | `wired` | [[Character Images & Expression Packs]] |
| 33 | [[the-map\|The map]] | `wired` | [[Graph System]] |
| 34 | [[narration\|Narration]] | `wired` | [[Narration System]] |
| 35 | [[llm-calls\|LLM calls]] | `wired` | [[LLM Providers]] |
| 36 | [[the-sky\|The sky]] | `wired` | [[Time & Weather]] |
| 37 | [[spectator-mode\|Spectator mode]] | `wired` | [[Time & Weather]] |
| 38 | [[traversal-abilities\|Traversal abilities]] | `wired` | [[Doors & Connections]] |
| 39 | [[auto-description\|Auto-description]] | `wired` | [[Character Images & Expression Packs]] |
| 40 | [[taking-an-agent-over\|Taking an agent over]] | `wired` | [[NPC Behavior System]] |
| 41 | [[memory-pipeline\|Memory pipeline]] | `wired` | [[Memory System]] |
| 42 | [[prompt-lens\|Prompt lens]] | `wired` | [[LLM Providers]] |
| 43 | [[where-you-ve-been\|Where you've been]] | `wired` | [[Turn Queue & Human Turns]] |

## In the editor

| # | Feature | Status | Deep documentation |
|---|---|---|---|
| 44 | [[graph-canvas\|Graph canvas]] | `wired` | [[Graph System]] |
| 45 | [[map-layout\|Map layout]] | `wired` | [[Graph System]] |
| 46 | [[levels-layout\|Levels layout]] | `wired` | [[Graph System]] |
| 47 | [[worldpainter\|WorldPainter]] | `wired` | [[WorldPainter]] |
| 48 | [[grid-to-graph\|Grid to graph]] | `wired` | [[Grid to Graph]] |
| 49 | [[scopes\|Scopes]] | `wired` | [[World Scopes]] |
| 50 | [[node-inspectors\|Node inspectors]] | `wired` | [[Inspector Panels]] |
| 51 | [[way-authoring\|Way authoring]] | `wired` | [[Way Properties]] |
| 52 | [[trigger-effect-editor\|Trigger / effect editor]] | `wired` | [[Triggers & Effects]] |
| 53 | [[nl-editor\|NL editor]] | `wired` | [[NL Editor]] |
| 54 | [[expression-pack-editor\|Expression pack editor]] | `wired` | [[Character Images & Expression Packs]] |
| 55 | [[library\|Library]] | `wired` | [[Library System Overview]] |
| 56 | [[tags\|Tags]] | `wired` | [[Tags System]] |
| 57 | [[scenario-creation\|Scenario creation]] | `wired` | [[ScenarioCreationGuide]] |
| 58 | [[save-load\|Save / load]] | `wired` | [[Settings & Configuration]] |
| 59 | [[settings\|Settings]] | `wired` | [[Settings & Configuration]] |
| 60 | [[command-palette\|Command palette]] | `wired` | [[Rendering & UI Modules]] |
| 61 | [[help-centre\|Help centre]] | `wired` | [[Rendering & UI Modules]] |
| 62 | [[recent-edits-undo\|Recent edits / undo]] | `wired` | [[Recent Edits & Undo]] |
| 63 | [[validator-issues\|Validator & issues]] | `wired` | [[Validator & Issues]] |
| 64 | [[event-stream\|Event stream]] | `wired` | [[Event Stream]] |
| 65 | [[export\|Export]] | `wired` | [[Event Log Export]] |
| 66 | [[soak-lab\|Soak lab]] | `wired` | [[Soak Lab]] |
| 67 | [[the-human-turn-composer\|The human turn composer]] | `wired` | [[Turn Queue & Human Turns]] |
| 68 | [[turn-based-modes\|Turn-based modes]] | `wired` | [[Turn Queue & Human Turns]] |
| 69 | [[agent-overview\|Agent overview]] | `wired` | [[Rendering & UI Modules]] |
| 70 | [[action-menu\|Action menu]] | `wired` | [[Rendering & UI Modules]] |
| 71 | [[world-lore\|World lore]] | `wired` | [[Inspector Panels]] |
| 72 | [[entity-generators\|Entity generators]] | `wired` | [[NL Editor]] |
| 73 | [[library-sync\|Library sync]] | `wired` | [[Library System Overview]] |
| 74 | [[agent-behaviour-settings\|Agent behaviour settings]] | `planned` | — |
| 75 | [[graph-settings\|Graph settings]] | `planned` | — |
| 76 | [[report-a-bug\|Report a bug]] | `wired` | [[Rendering & UI Modules]] |

## How to read a feature page

- **What you can do** is the row's own sentence from the Feature Map — the denominator's wording,
  not a rewrite.
- **How it works** links the deep note. If a row had no note, this page says so rather than
  pretending.
- **Where it lives** is the code path, filled in when someone touches the feature.
- **Connected** lists the Feature Map row and its sibling features — that is the edge set the
  vault's graph view draws.

> [!warning] Thin on purpose
> A fresh page here is *thin but true*: every sentence in it is one the Feature Map already
> asserts. A page that says "Not recorded yet" is honest about its depth; it is not a defect to
> hide, and `> [!note] Status` always carries the map's own confidence word.
