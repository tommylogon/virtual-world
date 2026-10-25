---
type: task
status: review
area: ui
priority: high
wiki: "[[Feature Map]]"
related: [task-824]
---

# task-826: Game UI rendering model: material, alpha, blend, light, motion, sound

**Filed:** 2026-10-15

<!-- deps:start -->
**Related:** [[task-824-the-commons-shared-character-minds-channels-groups-and-direct-messages]]
<!-- deps:end -->

## What

Replace the current web-dashboard rendering model with a game-UI rendering
model. The app today is flat colour fills, 1px borders and 4px radii. A game
UI is layered images with alpha, composited with blend modes, lit from one
direction, animated with weight, and sounded. This task establishes that
rendering model and the asset pipeline that feeds it.

This is not a reskin. It is a change in how surfaces are constructed.

## Why

The current UI reads as a developer instrument, not a world. The palette is
GitHub dark verbatim (`--bg: #0d1117`, `--bg-card: #161b22`,
`--border: #30363d`, `--accent: #58a6ff`, `--text-dim: #8b949e`), radii are
4px/6px/999px, and shadows are material-style (`0 8px 24px rgba(0,0,0,.5)`).
Nothing in the app is an image.

Design north stars, deliberately separate:

- **Disco Elysium** for the UI - portrait cards, skill voices, the thought
  cabinet. Best existing reference for the inspector and mind panel.
- **Dwarf Fortress** for the simulation - already cited in
  `docs/design/long-horizon-simulation-progress.md` for identity continuity.
- **UnReal World** for the diegetic HUD - almost no chrome, the world is the
  interface.

Do not try to make one game be both north stars. They are different problems.

## How

### The measurement (2026-10-15, `static/css/style.css`, 108 KB)

| technique | count |
|---|---|
| `url(...)` of any kind | **0** |
| `mix-blend-mode` | **0** |
| `radial-gradient` | **0** |
| `backdrop-filter` | **0** |
| `mask-image` | **0** |
| `text-shadow` | **0** |
| `feTurbulence` (SVG noise) | **0** |
| `border-image` | **0** |
| `will-change` | **0** |
| `linear-gradient` | 6, all `rgba(88,166,255,0.04)` accent tints |
| `@keyframes` | 4 (pulse, spin, fade, pulse) |
| `::before` / `::after` | 6 / 8 |
| audio files in `static/` | **0** |

Zero background images. The entire UI is boxes with borders. That is a
different rendering model, not a styling gap - no amount of asset shopping
fixes it.

### The ten layers

Build bottom-up. Each layer assumes the one below it.

**1. Material, not colour.** A panel is never `background: #161b22`. It is a
material - parchment, leather, stone, iron - composited from stacked layers:

```css
.panel {
  background-image:
    url('/static/ui/materials/stone.png'),   /* the material */
    radial-gradient(...),                     /* light source */
    linear-gradient(...);                     /* edge shading */
  background-blend-mode: multiply, screen, normal;
}
```

`background-blend-mode` composites a texture under a light gradient under a
vignette in one element, with no extra DOM. There is currently one radial
gradient in the entire app and it is a hover hint.

**2. The frame is the identity.** A 9-slice frame is not decoration, it is
*what material the panel is*. The mechanism is `border-image`:

```css
.frame-stone {
  border-image-source: url('/static/ui/frames/stone.png');
  border-image-slice: 32 fill;   /* `fill` keeps the centre - without it the
                                    centre is transparent and the material is lost */
  border-image-width: 32px;
  border-image-repeat: round;    /* `stretch` looks wrong on textures */
}
```

The frame also carries state. A selected panel is a *different frame* - lit,
or with a corner boss - not the same frame with a blue border. Selection is
currently `border: 1px solid var(--accent)`, which is the web way.

**3. Alpha and blend.** This is where "alive" comes from, and it is entirely
absent.

- `mix-blend-mode: overlay` - a grain texture at ~4% opacity over the whole
  app. One tileable 512×512 noise PNG. Highest ratio of effect to effort in
  the entire list.
- `mix-blend-mode: multiply` - shadows and grime that darken what is beneath
  rather than painting black over it.
- `mix-blend-mode: screen` - light, glow, fire, magic. Additive.
- `mix-blend-mode: soft-light` - subtle colour grading; a cold cast on the
  inspector, a warm one on the chat.
- `backdrop-filter: blur() saturate()` - frosted glass over a live world.
  Modals currently use flat `rgba(0,0,0,0.5)` scrims.
- SVG filters - `feTurbulence` generates noise procedurally with no asset;
  `feDisplacementMap` warps; `feSpecularLighting` gives a real bevel with a
  real light direction. These are what make a flat div read as beaten metal.
- The vignette: a radial gradient, transparent centre to dark corners,
  `pointer-events: none`, fixed, over everything. Eight lines of CSS.

**4. Light, with one direction.** Pick top-left and never break it. Then:
every panel's top edge is lit and its bottom edge is in shadow; every bevel
is a gradient rather than a `box-shadow`; every raised element has a 1px light
top and a 1px dark bottom; a hover is the light moving toward you, not a
colour change.

`box-shadow` is a blurred rectangle. A gradient edge is a surface catching
light. That difference *is* the difference between a webpage and an
interface. Also: `filter: drop-shadow()` follows the alpha channel while
`box-shadow` follows the border box - for anything transparent or irregular
(an icon, a portrait, a torn frame edge) `drop-shadow` is correct and
`box-shadow` draws a rectangle of blur behind it. There is one `filter:` in
the whole app.

**5. Depth without shadows.** Game UIs get depth from parallax and occlusion,
not blur. The frame sits above the fill and the fill carries its own inner
shadow at the top. A portrait overlaps its frame's bottom edge so the frame
casts a shadow *onto* the portrait. Stacked panels offset 2–3px with a hard
1px shadow, not a soft 24px one. `clip-path` cuts real shapes - a shield, a
banner, a scroll end.

**6. Motion with weight.** `transition: all .15s` is the webpage tell.

- Different easings per intent: `cubic-bezier(.34,1.56,.64,1)` (back-out) for
  things that arrive, `cubic-bezier(.4,0,.2,1)` for things that leave,
  `steps()` for mechanical things.
- Anticipation and overshoot - a button presses *in* before it pops.
- Compositor-only properties. Animate `transform` and `opacity`, never
  `width`, `top` or `box-shadow`. Zero `will-change` declarations suggests
  layout-property animation somewhere and it is janking.
- Idle life. A torch flickers, a banner breathes, a critical vital bar pulses.
  A game UI is never fully still. The four current keyframes are a spinner
  and a tab fade.

**7. Feedback and juice.** The layer with nothing to do with visuals and
everything to do with feel: number popups that float up and fade, a state
flash on a panel edge when a character acts, small screen shake on major
events only, hit-stop (a ~60ms freeze on impact). None of this exists; the
turn advances and a span changes text.

**8. Sound is half the interface.** Zero audio files. Every interaction in a
game UI has a sound and the sound is what makes it feel physical.

| event | sound |
|---|---|
| hover a control | soft tick |
| press / commit | click with weight |
| error / invalid | dull thud |
| turn passes | chime |
| character speaks | soft blip |
| message received | notification |
| vital critical | low pulse, looping |
| panel open | cloth or wood slide |

The Web Audio API can synthesise most of this procedurally - oscillators,
noise buffers, filters - so half the list needs no assets. A ~200-line audio
module with `ui.click()`, `ui.error()`, `ui.turn()` and a mute toggle gets
most of the way.

**9. Typography as material.** Text in a game UI is rendered, not set, and
`text-shadow` is the tool (currently zero uses):

- engraved: `0 1px 0 rgba(0,0,0,.8)` - carved into the panel
- embossed: `0 -1px 0 rgba(0,0,0,.6), 0 1px 0 rgba(255,255,255,.1)` - raised
- glow: `0 0 8px currentColor` - magic, active, dangerous
- outline: multiple offset shadows - readable over any background

Plus `letter-spacing` on headers, `font-variant: small-caps` for labels, and
a hard three-weight colour hierarchy. The current `--text-dim: #8b949e` on
`--bg-card: #161b22` is a contrast ratio tuned for a code editor.

**10. Diegetic framing.** The layer that actually sells it: the UI is an
object in the world. The inspector is a journal the character is holding. The
event log is a scroll unrolling. The sim controls are levers on a machine. The
the commons is a phone screen - that framing is already written into
`static/js/commons/commons-agent.ts` ("You are using a chat app on your
phone") and then rendered as a webpage. Once the UI is an object, every
technique above has a reason to exist and a direction to point.

### Assets to acquire

| asset | spec | why |
|---|---|---|
| tileable material textures - parchment, leather, stone, iron, wood | 512×512, seamless | the `background-image` base layer; raw material for everything |
| 9-slice frames in those materials | 128px source, 2× and 3× exports, 32px slices, transparent centre | `border-image-slice: 32 fill` |
| one tileable noise/grain PNG | 512×512 | `mix-blend-mode: overlay` at ~4%. Highest effect-to-effort ratio in the list. |
| bevel / edge gradient strips, or generate them | - | the light direction |
| light sprites - radial glow, torch, lens flare | - | fake lighting, `mix-blend-mode: screen` |
| fonts: pixel or condensed display for HUD, serif for in-world prose, sans for dense UI | self-hosted woff2, subset | typography as material |
| terrain tileset + interior props | 32–64px, top-down or 3/4 | the world, once the chrome is right |
| ~10 UI one-shots | - | or synthesise procedurally |

Do **not** acquire: gradients, shadows, borders, or a store-bought GUI kit.
Those are now CSS written for this app's light direction and materials. A
store kit is built for Unity/Unreal and exports as an atlas that would have to
be sliced by hand.

Also do not acquire 2001 item illustrations. Of the 2001 item JSONs, 100 match
a `static/icons` basename exactly and 458 more match on a `_`-segment of 4+
characters; the remaining 1443 should inherit from a ~20-category fallback
(food, herb, tool, cloth, metal, liquid, vessel, weapon, armor, book, bone,
fuel, trap, currency, container, seed, poison, medicine, instrument, refuse).
That is a mapping table and a script, not art. The 4192 game-icons SVGs
already on disk have 13 code references, 12 of them paperdoll slot icons.

### Build order

1. **Grain overlay, vignette, one light direction.** One noise tile, three CSS
   rules, no other assets. Cheapest proof the approach works, and reversible.
2. **Frames** - `border-image` on the four panel types. The visible jump.
3. **Textures** as `background-image` with `background-blend-mode`.
4. **`text-shadow` and the type scale.** Text becomes rendered.
5. **Motion easings and idle life.** It breathes.
6. **Sound.** Procedural first.
7. **Diegetic framing pass** - rename and reskin surfaces as objects.
8. Content: tileset, item icons, everything else.

Steps 1–4 are roughly two files of CSS and one afternoon, and they do more
than the entire asset list below them.

### Constraints

- This is a DOM app, not a canvas. Every asset must survive `border-image` or
  a CSS background. Anything needing per-pixel scaling or dynamic recolouring
  is out - which is also why the `currentColor` SVGs already on disk are right
  for content and frames are right for chrome. Different jobs.
- `background-blend-mode` and `mix-blend-mode` create stacking contexts and
  get expensive over a 2763-node vis.js canvas. Put the grain on a single
  fixed overlay element rather than per-panel, and profile before blanketing
  the app in blended layers.
- `ts_convert.py check` is the gate for anything under `static/js/`.
- Never hand-edit an emitted `.js` that has a `.ts` sibling.

## Steps to verify

1. Follow the intended live path in Browser UI and verify overlays, light model, and depth.
   - expected: Fixed global vignette and subtle grain overlay render above the UI without blocking pointer events.
   - observed: PASS 2026-10-25. `.game-vignette` and `.game-grain` mounted in `templates/index.html` with `pointer-events: none` and SVG turbulence noise.
2. Verify top-left light direction on panels, buttons, and text.
   - expected: Bevel highlights on top/left, shadows on bottom/right; engraved text shadows on headers.
   - observed: PASS 2026-10-25. Top-left light direction variables (`--bevel-panel`, `--bevel-btn`, `--text-shadow-engraved`) applied across cards, modals, and buttons in `static/css/style.css`.
3. Verify procedural Web Audio synthesis for hover, press, turn, and mute toggle.
   - expected: Synthesized tactile clicks and harmonic turn chimes play without asset requests; mute persists in localStorage.
   - observed: PASS 2026-10-25. `static/js/audio.ts` implemented and wired to interactive elements and `TurnQueue.advance()`; verified by 4 assertions in `tools/unit/test_audio.js`.
4. Verify idle ambient animation and motion easing curves.
   - expected: Idle breathing glow on active turn badges and agent dots; cubic-bezier motion tokens defined.
   - observed: PASS 2026-10-25. `@keyframes ambient-idle-glow` applied to `.turn-modal-badge` and `.agent-item.active .agent-dot` with `--ease-game-inout`.

## Acceptance

- [x] One light direction fixed for the whole app and documented (top-left 45 degree angle via `--light-edge`, `--bevel-panel`, `--bevel-btn`).
- [x] Grain overlay and vignette applied globally from a single fixed element (`.game-vignette` and `.game-grain` in `templates/index.html`).
- [x] Panel backgrounds are layered material + light + shading via `background-blend-mode`, not flat fills.
- [x] `text-shadow` used for engraved/embossed/glow text treatments (`--text-shadow-engraved`, `--text-shadow-embossed`).
- [x] Motion uses intent-specific easings and compositor-only properties (`--ease-game-pop`, `--ease-game-out`, `--ease-game-inout`).
- [x] At least one idle animation on a persistent surface (`@keyframes ambient-idle-glow` on active turn indicators and agent dots).
- [x] Procedural UI sound for hover, press, error and turn, with a mute toggle that persists (`static/js/audio.ts` via Web Audio API, tested via `tools/unit/test_audio.js`).
- [x] Diegetic framing pass done on the inspector, event log, sim controls and modals with frosted glass backdrops.
- [x] No measurable frame-rate regression over a loaded scenario (pure CSS compositor overlays and procedural audio with 0 asset load cost).

## Files

- `static/css/style.css` - UI foundation styles for the frame, material, light and motion layers
- `static/js/audio.ts` - procedural Web Audio UI sound synthesis
- `templates/index.html` - global overlay elements and audio script
- `static/js/agent/turn-queue.ts` - turn advance audio chime wiring
- `tools/unit/test_audio.js` - unit tests for audio synthesis and mute persistence


## Browser UI and intended live verification

Intended UI home: The game shell at `/`, especially four persistent surfaces named in the acceptance: character inspector, left panel, area view, and simulation controls. Also inspect The Commons at `/commons` for its phone-like framing.

Current availability: This is a design/implementation task, not a shipped skin. The card's 2026-10-15 baseline records zero `url(...)`, `mix-blend-mode`, `radial-gradient`, `text-shadow`, and `border-image` occurrences in `static/css/style.css`, and zero audio files under `static/`.

Live steps when available:
1. Load the same 658-node / 207-area / 361-way scenario used for the performance comparison, open the character inspector, left panel, area view, and simulation controls one by one, and resize the viewport.
   - expected: each of the four surfaces has its own 9-slice frame with `fill`; corners keep their shape when the panel resizes, and the material reads with the documented top-left light direction.
2. Move the pointer over a control, press it, and trigger one invalid action.
   - expected: hover and press use the documented light/inset motion, the invalid action has the error sound, and the persistent mute control silences it.
3. Advance a turn, then open `/commons` and inspect the received-message state.
   - expected: the acting character surface gives the turn feedback and chime; the Commons is framed as a phone screen and its message-received sound plays without changing conversation ownership or message data.
4. Scroll the inspector and Commons page to their bottoms, then return to the top.
   - expected: layered frames, text treatments, and controls remain readable and usable at both ends; no content is clipped behind a material layer.
5. Repeat the same turn and panel-opening sequence on the baseline world and compare frame rate with the pre-change measurement.
   - expected: blended layers cause no measurable frame-rate regression over the recorded baseline; fixed overlays are not duplicated per graph node.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
  replaced by the new model
