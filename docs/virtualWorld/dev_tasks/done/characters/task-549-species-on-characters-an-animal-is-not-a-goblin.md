---
type: task
status: done
area: characters
priority: high
---

# task-549: Species on characters: an animal is not a goblin

**Filed:** 2026-09-27
**Related:** task-545,task-547

## Goal

Characters have no species or faction field at all, so an animal, a goblin and a human are the same kind of thing to the simulation. Add a species/faction identity that the need layer can read.

## Measured (2026-09-27) — there is no species anywhere

- `player.py` has **no** species, faction, or race field. `rg species engine/
  player.py` returns one hit, and it is a comment in `engine/traits.py` about
  temperature thresholds. No file in `data/library/characters/` mentions species.
- Need servicing is a **pure tag intersection**. `engine/background_simulation.py`
  `_has_tag(node, tags)` does `set(tags) & node_tags` and nothing else. The
  vocabularies are `DRINK_TAGS = ("drink", "water", "beverage")` and
  `RELIEF_TAGS = ("latrine", "toilet", "privy", "restroom", "bathroom")`.
- So the question "would an animal use a latrine?" **cannot be answered in either
  direction by the engine.** The goblin camp is tagged `latrine` and a human city
  would be tagged `bathroom`, and that distinction is authored by hand and
  invisible to the simulation. An animal, a goblin and a human all draw from the
  same list.
- The world *already* models the split — but only for narration. 31 of 272 areas
  in the Kraktooth scenario carry `goblin_description`, `human_description` and
  `goblin_knowledge` properties, so a goblin and a human in the same room already
  get different text. What is missing is the same distinction in the
  **simulation** layer, where it would decide who may use what.

## Open decisions

1. **Field or tag?** A `species` field on the character, or a `species` tag the
   existing tag machinery already reads. A tag needs no serializer change and no
   migration, and the world already uses tags this way.
2. **What granularity?** `goblin` / `human` / `animal` is probably too coarse to
   be useful; the goblin camp has a chief, a shaman, prisoners and a farmhand.
3. **What does it gate?** Minimum: need servicing. Then movement (can a goblin
   enter the village?), and narration (replacing the per-faction description
   keys, or complementing them).

## Acceptance

- [x] A character carries a species identity **readable by the need layer** —
      `Player.species`, normalised to lowercase, read from the `Player` (never
      from a bare graph node, which carries no such field).
- [x] **A species can be excluded from a service**, so "would an animal use a
      latrine" is a property of the data and not of the author's tag choices.
      `engine/species.py` profiles declare exclusions; the background relief
      handler reads one.
- [x] **Existing characters and scenarios load unchanged** — asserted against
      all 70 library characters: none declares a species, and an unspecified
      species permits every service, so every one of them behaves identically.
- [x] Species is authorable through `POST /api/players/<name>` and hydrates from
      a library definition, and round-trips in `Player.to_dict()`.
- [x] Tests in `tests/test_species.py` (18 tests), including the relief wiring.

## Implementation — 2026-10-02 (WT-characters-engine)

### A bug the live API caught and the code read did not: two player serializers

There are **two** places that serialize a player —
`Player.to_dict()` and `SerializationManager._serialize_player` — and
`/api/state` serves the *second* one. The species was added to the first. The
consequence was the worst shape a write can have:

```
POST /api/players/Kaelen%20Voss  {"species": "Forest Goblin"}  -> 200 {"status":"updated"}
GET  /api/state                                                     -> species absent
```

Accepted, stored on the `Player`, and absent from the response the client had
just been handed. `Player.to_dict()` is what the *save file* uses and
`_serialize_player` is what the *client* uses, so they had drifted apart long
before this task and `size` had to be added to both for the same reason
(comment at `serialization.py:133`). Species is now in both, and
`test_both_player_serializers_carry_the_authored_identity` compares the key sets
so the next field added does not repeat it.

### Files

- `engine/species.py` — **new**. `SPECIES_PROFILES`, `species_of`,
  `profile_for`, `can_use_service`, `excluded_services`, `describe_species`.
- `player.py` — `self.species = None`; serialised in `to_dict()`.
- `engine/serialization.py` — reads `species` back (absent → `None`).
- `engine/effects.py` — the library loader normalises and sets it.
- `engine/background_simulation.py` — the need layer reads it; `_relieve` and
  `_note_species_mismatch`.
- `routes/player_ops.py` — authorable through the existing update route.
- `tests/test_species.py` — **new**, 18 tests.

### The three open decisions, answered

1. **Field or tag?** A **field**, `Player.species`. A tag would have needed no
   serializer change, but it would also have been invisible to the need layer —
   the need layer already intersects tags, so a `species: animal` tag would have
   been read by exactly the same mechanism that cannot currently read species,
   which is the problem. A field is the thing the need layer asks for directly.
   It is *not* a second source of truth: `tags` remain the general vocabulary
   ("nobility", "faction:guard", role and circumstance), `species` answers only
   "what kind of creature is this".
2. **What granularity?** **One primary species, free text.** Closed at
   `goblin`/`human`/`animal` it is too coarse to be useful on its own (the camp
   has a chief, a shaman, prisoners and a farmhand), but the *kind* is what
   matters and role is what `tags` are already for. A compound name inherits
   from its last word, so `deep elf` gets the `elf` row without a profile being
   registered for every adjective.
3. **What does it gate?** **Need servicing only, and comfort rather than
   permission.** Movement and narration are deliberately untouched — see below.

### The two rules that make it safe to add at all

1. **An unspecified species must change nothing.** `Player.species` defaults to
   `None` and `profile_for(None)` returns `None`, which means *no opinion* and
   permits every service. This is what is asserted against all 70 library
   characters. Returning an empty-but-present profile would have read as "can do
   nothing", which is a very different and much worse mistake.
2. **Exclusion is authored, never guessed.** There is no hardcoded "animals don't
   use latrines"; a profile lists the services it *cannot* use. Only exclusions
   exist — a positive list would have to enumerate every service to stay honest,
   and the day a service is added it would silently start lying. Pinned by
   `test_every_profile_only_declares_exclusions_never_permissions`.

### On task-551: this does not reintroduce a refusal

task-551 permits relief **anywhere** and this task must not undo that. So an
exclusion changes whether a *fixture is a proper place*, not whether relief
happens: an animal that cannot use a latrine relieves where it stands, pays the
same dignity cost anybody else would pay, and the lived log records that it found
a fixture unusable for its body. Two tests hold that line — one asserts the
fixture stops counting as comfort, one asserts relief still succeeds in a world
with no latrine at all.

The mismatch is recorded rather than announced. An animal standing in a latrine
is a fact about the world a reader can discover, not an error to be shouted at
somebody every time it happens; the lived log is where the engine already puts
objective facts with a reason tag (`why="species:animal"`).

### Not done here

- **Narration** — the 31 Kraktooth areas carrying `goblin_description` /
  `human_description` are left as they are. Complementing them is a separate
  change in a layer this task does not own, and `describe_species` exists so
  that change has one place to read from when it happens.
- **Movement gating** (can a goblin enter the village?) — out of scope, and it
  belongs with task-550, which applies the same idea to areas.

### Verify

```
python -m pytest tests/test_species.py -q                            # 20 passed
python -m pytest tests/test_species.py tests/test_background_relief_and_washing.py \
  tests/test_library_character_import.py tests/test_character_identity.py \
  tests/test_health_model.py tests/test_occupancy.py -q              # 144 passed, 2 baseline
```

The two `test_character_identity` failures are the documented pre-existing ones
(task-457's canonical-node problem).

**Full suite compared by failure NAME against the clean-master baseline**: 15
failed on both, `Compare-Object` empty.

**Live — 2026-10-02, `python app.py` on `VW_PORT=4466`.**

```
GET  /api/state                     -> species key present on the player
POST /api/players/Kaelen%20Voss  {"species": "Forest Goblin"}
                                   -> 200 {"status": "updated"}
GET  /api/state                     -> "forest goblin"   (normalised to lowercase)
POST /api/players/Kaelen%20Voss  {"species": null}
GET  /api/state                     -> null  (unspecified again)
```

Written through the API and read back from the same API — which is exactly the
round trip that was broken before `_serialize_player` learned about the field.

## Related

- task-550 — faction and ownership, which is the same idea applied to areas
- task-551 — relief anywhere but indoors, which makes the species question matter
- task-653 — occupancy, the sibling reader of the size axis
- task-606 — scale-correct ability scores, which species and size both feed


