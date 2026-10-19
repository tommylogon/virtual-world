---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Gameplay/Action Resolution System]]"
---

# task-594: Swimming as a navigation type, with diving and a limited air vital

**Filed:** 2026-09-30
**Related:** 

## What

Add swimming as a movement/navigation type alongside walking. Moving over water should be possible at the surface; deep water should require diving, which costs air. Dive duration is bounded by a new Air vital that depletes underwater and refills at the surface, and reaching zero has a defined consequence (drowning damage, forced surfacing, or death - the design decision is the point of the task). Check whether an existing vital or condition can carry this before adding anything new, and reuse the existing movement/action machinery rather than branching inside it.

## Acceptance

- TODO

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: game view at a shoreline → character movement/action controls → water traversal result, air vital, and event stream. The swim and dive actions use the existing navigation/action surface; the water cell/area remains part of the world graph.

Current availability: swimming, deep-water diving, an air vital, and the zero-air consequence are proposed. The card correctly leaves the consequence as a design decision, and this section does not pick one or claim a working water mechanic.

Live steps when available:
1. In a scratch scenario with authored shallow and deep water, move a character from shore across shallow water and inspect the resulting location and event.
   - expected: surface swimming reaches the adjacent water location using the normal movement resolution.
2. From deep water, attempt to move without diving, then begin a dive and inspect the air vital after each tick.
   - expected: deep-water movement is gated by the dive rule; air decreases only while submerged and refills at the surface.
3. Continue until the chosen zero-air consequence fires, then inspect the event stream, vital panel, and final position/state.
   - expected: the selected design outcome is explicit and occurs once; no unbounded dive or silent air underflow occurs.
4. Surface before air is exhausted and repeat the dive.
   - expected: air replenishes at the surface and the next dive starts from the documented amount.

This section is not a claim that planned UI exists or works today.
