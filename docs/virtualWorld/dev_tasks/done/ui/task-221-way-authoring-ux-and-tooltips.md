---
group: UI & Settings
wiki: "[[dev_tasks/level-design-workflow]]"
---

# Way Authoring UX — Labels, Exit Badges, Edge Tooltips, Parameter Preview

**Filed**: 2026-08-13  
**Priority**: Medium  
**Status**: In Review — implemented 2026-08-13, pending browser verify

---

## Problem

Way state UI is usable but labels mislead (e.g. "Description" reads like room prose, not closed-door appearance). Graph connection edge tooltips are thin. Agent prompt exits block doesn't show **requires climb/jump** or clearance tags. `{param:light}` in door text is easy to forget when parameters live on the way node.

Labs pain points this addresses:

- Generic `clearance` tag on doors + keycard `has_tag target clearance` (correct pattern — door tagged, not card)
- Stray tags on wrong ways (clearance on jump pit)
- Movement verbs not visible in prompt preview

## Deliverables

### 1. Inspector label pass

Apply renames from task-220 across:

- `way-view.js`
- `area-view.js` exit rows (`_renderExitItem`)
- Create-modal connection fields (if still separate)

Add **section hints** (small grey text) explaining what feeds agent vs human `look`.

### 2. Area exit row enrichment

In area inspector exit list, show badges:

| Badge | Source |
|-------|--------|
| 🔒 locked / 🟢 open / … | way state |
| 🧗 climb / 🦘 jump / 🐛 crawl | way `requires` |
| 🏷 clearance, … | way tags (first 2) |
| `{param:light}` resolved | inline preview if parameters set |

Click badge → jump to way in inspector.

### 3. Graph connection edge tooltips

Extend `network-manager.js` edge tooltips (area→way connections):

```
🔗 Living Room → way_swinging_door
Command: go "swinging door" → Kitchen
Way state: closed
Movement: go (default)
Tags: —
View when open: "Through the door you see…"
```

Way node tooltips already show state + requires — add **area_from / area_to** and tag list.

Overlaps [[todo/graph/task-129-graph-tooltips-environment-info|task-129]] — implement connection-edge portion here; area env tooltips stay in 129.

### 4. Parameter live preview

Where way description contains `{param:key}`:

- Show resolved string below textarea (uses way `parameters` dict)
- Warn if unresolved key

Same helper usable in Agent Lens (task-219) and unified way editor (task-220).

### 5. Tag sanity hints (optional, non-blocking)

Soft ⚠ in way inspector / lens — not a validator panel:

- `clearance` tag on way with `requires: jump`
- Locked way with no tags and no visible unlock trigger (heuristic only)

## Files

- `static/js/inspector/way-view.js`
- `static/js/inspector/area-view.js`
- `static/js/graph/network-manager.js`
- `static/js/inspector/helpers.js` — `resolveWayParams(text, parameters)`

## Verification

- [x] `resolveWayParams` + preview block in `helpers.js`; shared badges in `way-authoring.js`
- [x] Area exit rows show state/movement/tag/param badges (`area-view.js`)
- [x] Graph area→way edge tooltips show command/state/movement/tags/view (`network-manager.js`)
- [x] Room context exit lines append movement hints (`room-context.js`)
- [x] Create-modal connection labels renamed
- [ ] Hover area→way edge on graph → see command + state + view snippet (browser)
- [ ] Area exit row for ladder shows 🧗 climb after `requires: climb` set (browser)
- [ ] Door with `{param:light}` + `parameters.light=red` shows resolved preview (browser)
- [ ] Agent Lens exits section matches badges (browser)

## Related

- [[todo/ui/task-219-agent-lens-left-panel|task-219]]
- [[todo/ui/task-220-unified-way-editor|task-220]]
- [[review/triggers/task-keycard-clearance-target_has_tag-unlock_way-target|keycard clearance pattern]]
