---
type: doc
tags: [system/characters, prompting, interiority]
---

# Interiority and Subtext

## The Consciousness Problem

A real human being living through a day does not have structured database fields in their head. Nobody walks down a street thinking:

```text
=== YOUR MIND ===
Motivation: Starving for physical warmth...
Intention: Lock in a weekend movie night...
Pursuit: Asking Jake directly via text...
```

Dumping structured GIMP keys or telemetry into a prompt makes an LLM reason like an actor reading a script breakdown instead of a human living in a body. As diagnosed in task-905, models will literally parrot the prompt headers back into their inner monologues (for example, models quoting vital numbers or stating "My current pursuit is to...").

## What Lives in a Human Mind

When we inspect authentic character turns in the simulation (such as Miki Doki in `taco_bell_date_tick_179`), real human consciousness consists of three distinct layers:

### 1. Somatic Sensation and Bodily Urgency
Immediate, unfiltered biological feedback:
- The raw dryness of a throat like sandpaper when nervous.
- Stomach cramping from hunger or nausea.
- The chill of Oklahoma autumn air against skin where a hoodie rides up.
- Pulse pounding in the ears, trembling fingers, involuntary muscle tension.

### 2. Associative Memory and Relational Dread
Past trauma and emotional baggage projecting onto the present moment:
- The bent clasp of a missing butterfly earring feeling like a phantom limb of an absent mother.
- Terror that learning a boy's name means "this is how it starts, this is how they find out and leave."
- Flashes of previous rejections (being left on the sidewalk at night) coloring a kind gesture.

### 3. Immediate Defensive Self-Talk and Coping
The internal voice managing anxiety and deciding the next micro-step:
- "Stop spiraling. Breathe. One step."
- "Just go inside and get food, do not make it a second date."
- Fidgeting with a necklace, adjusting posture, checking exits.

## The Architecture: GIMP as Spine, Not Transcript

GIMP (**Goal, Intention, Motivation, Pursuit**) is the engine's cognitive spine and simulation telemetry. It is the persistent, inspectable, schedulable truth of what characters want over time.

| System Layer | Role | Representation |
|---|---|---|
| **Authoring & Ledger** (GIMP) | What the character wants, why they move, how they pursue it over days/weeks | Structured records, dependencies, progress counts, blockers |
| **Engine Decision State** (MOSIAC) | What the character balances right now (drives, obligations, schedules, immediate attention) | Weighted priority, salience filters, gated action sets |
| **Agent Prompt Presentation** | What the character actually experiences in their conscious mind | Visceral somatic sensation, evocative associative subtext, immediate emotional friction |

## Translation Rules for Prompt Engineering

When constructing character prompts:

1. **Never print raw telemetry or field labels in the mental state.**
   Replace labels like `Motivation:` or `Social: 20` with subjective narrative sensations.
   - *Wrong*: `Motivation: Starving for physical warmth. Intention: Lock in movie night.`
   - *Right*: `A hollow ache sits in your chest. You keep looking at his hands, wondering if asking him over for a movie will scare him away or if you can actually say the words.`

2. **Ground motivations in tangible physical objects and actions.**
   Desire is not abstract. It fixes on specific things in the scene: the worn leather of a guitar strap, the glow of a Prusa heatbed, a cold deadbolt, the smell of PB Blaster, or the sound of footsteps on the porch.

3. **Subtext over exposition.**
   Dialogue should rarely state the real motivation directly. The real motivation lives in the hesitation, the change of subject, the nervous emote, the defensive joke, and the silence between lines.
