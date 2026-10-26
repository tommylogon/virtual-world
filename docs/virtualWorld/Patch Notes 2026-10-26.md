---
type: doc
tags: [surface/docs]
---

# Living Voices & The Proving Ground - 26 October 2026

Four days of work across the simulation, written for anyone who plays or builds in VirtualWorld. Two major areas change how the world feels: characters in The Commons now talk like real people instead of clockwork metronomes, and a new Proving Ground lets you test how different AI models play your characters before loading them into a live scenario.

---

## Characters that talk like people

Until now, characters in **The Commons** all shared a single, rigid timer. When you unpaused, every character waited twenty-five seconds and spoke at the exact same moment.

That mechanical rhythm is gone:

- **Desynchronized conversations:** Characters start talking at different times. An eager character might speak after a couple of seconds; a reserved one might wait a minute before chiming in.
- **Direct mentions wake people up:** When you send someone a private letter or mention their name with an `@` in a group chat, they notice. Instead of waiting for their regular cooldown, they react quickly, usually within a few seconds.
- **Double-texting and conversational bursts:** Real people do not speak in single, neat paragraphs. Excited, talkative, or impulsive characters will sometimes send two or three quick thoughts in a row before stopping.
- **Knowing when to yield the floor:** After someone drops a stream of thoughts, they pause so others have space to respond. A safety cap ensures nobody monologues endlessly.
- **Asleep means asleep:** Characters who are knocked out, resting, or unconscious in the simulation will no longer chat on their phones or post to town notice boards.
- **Clear roles:** Background townspeople and human-controlled characters are never forced onto AI timers.

The result is a conversation that breathes naturally, with sudden lively exchanges, quiet pauses, and room for cross-talk.

---

## The Proving Ground: benchmark your AI models

Before you set an AI model loose in your campaign, you can now test it in a dedicated workbench at `/bench`.

- **Model size range slider:** A new two-dot slider lets you filter models by size, whether you are running lightweight 3B models or heavy 70B flagships. Drag the min and max dots to set your target range.
- **Instant model search:** Quickly filter your installed models by name, quantization format, or vision capabilities.
- **Direct engine validation:** When a model decides to act (for instance, trying to open a door or pick up a key), the Proving Ground runs that decision against the actual physics and rules of the room. It tells you immediately whether the model made a legal move or hallucinated an object that is not there.
- **Rerolls and comparison:** Roll multiple responses for the exact same scene to compare consistency, formatting adherence, and response speed across models.
- **Memory safety:** Built-in automatic unloading between runs keeps your graphics card from running out of memory when benchmarking large model collections.
- **Run exports:** Export detailed performance summaries with token speeds, latency, and rule adherence to JSON with one click.

---

## A cleaner, sharper world

- **Grounded character perception:** Characters perceive their own stamina, hunger, and physical condition cleanly, without repetitive prompt clutter or confused stats.
- **Sightlines and exploration:** Sight is calculated by true line of sight over terrain. Landmarks on the horizon look like distant silhouettes until you walk close enough to chart the ground yourself.
- **Dark theme for the inner drawer:** Inspecting a character's thoughts and inner world inside The Commons now matches the rest of the dark interface instead of displaying a bright white box.
