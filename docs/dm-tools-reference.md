# D&D DM Tools — Extracted Tables & Rules Reference

> **Sources** (all four PDFs in `docs/`, all D&D Beyond web prints dated 27.09.2026):
> 1. `docs/dm toolbox.pdf` → **DMG (2024), Ch. 3 "DM's Toolbox"** (113 pp.)
> 2. `docs/dm tools2.pdf` → **Xanathar's Guide to Everything, Ch. 2 "Dungeon Master's Tools"** (41 pp.)
> 3. `docs/dm tools 3.pdf` → **Tasha's Cauldron of Everything, "Dungeon Master's Tools"** (61 pp.)
> 4. `docs/Monsters for Dungeons & Dragons (D&D) 5e - D&D Beyond.pdf` → **5e monster-browsing print, search = "goblin"** (17 pp., 20 results)
>
> **Purpose:** a complete, machine-checkable transcription of every roll table, DC table and
> stat block in those four books, with a per-part mapping onto this engine.
> **Status:** ✅ transcribes the source exactly · ⚠️ reconstructed across a page break
> (noted inline) · ❌ absent from the source PDF (listed, never invented)
>
> **Traceability:** every section carries its source page as `*(p. n)*` so any row can be
> checked against the PDF.

---

## How to use this document

| Want to… | Go to |
|---|---|
| find every random table at a glance | [Master index](#master-index-of-every-random-table) |
| pick a trap / hazard and read its full stat block | Part 1 → **Traps**, **Hazards** |
| generate a settlement, an NPC, a name, a secret | Part 1 → **Settlements**, **Nonplayer Characters** |
| get a DC for a check | Part 1 → **Fear and Mental Stress**, **Traps** → *Building a Trap*; Part 3 → **Monster Research** |
| set up a cursed/haunted/infested area | Part 1 → **Curses and Magical Contagions**; Part 3 → **Supernatural Regions** |
| resolve a mob instead of 12 separate NPCs | Part 1 → **Mobs** |
| see what Viwo can adopt, and in what order | [Viwo build priority](#viwo-build-priority) |
| see what is *incompatible* with the current engine | [Gaps, conflicts and known errors](#gaps-conflicts-and-known-extraction-errors) |

The four `### Viwo notes` subsections (one per part) hold the engine-level mapping. They are
terse on purpose; the consolidated, ranked list is at the end of this document.

---

## Master index of every random table

Every table in the four books that consumes a die, in one place. `★` = drop-in candidate for
`data/library/` roll tables.

### 1d4

| Table | Rows | What it rolls for | Source |
|---|---|---|---|
| **Monsters' Desires** ★ — 14 parallel tables (Aberration, Beast, Celestial, Construct, Dragon, Elemental, Fey, Fiend, Giant, Humanoid, Monstrosity, Ooze, Plant, Undead) | 4 each | the offering that pacifies a creature of that type | TCoE p. 23–27 |
| Magic Mushrooms, row 1 sub-roll | 4 | skin colour (purple/orange/green/pink) | TCoE p. 52 |

### 1d6

| Table | Rows | What it rolls for | Source |
|---|---|---|---|
| **States of Ruin** ★ | 6 | decay/occupancy state of a dungeon section → terrain, cover, stealth, noise | DMG p. 35 |
| **Party Origin** ★ | 6 | how a party came to exist | TCoE p. 4 |
| **Unearthly Road Keys** ★ | 6 | the one-shot unlock condition for a hidden gate | TCoE p. 58 |
| Far Realm 19–27, sub-roll | 6 | creature type (insect plague / raven+rats / treant / galeb duhr) | TCoE p. 32 |
| Unraveling Magic 21–25, sub-roll | 6 | damage type (acid, cold, fire, force, lightning, thunder) | TCoE p. 46 |

### 1d8

| Table | Rows | What it rolls for | Source |
|---|---|---|---|
| **Monster Personality** ★ | 8 | a group's behaviour during a fight (cowardly → bully) | XGtE p. 37 |
| **Primal Fruit** ★ | 8 | the effect of one piece of primal fruit | TCoE p. 57 |

### 1d10

| Table | Rows | What it rolls for | Source |
|---|---|---|---|
| **NPC Secrets** ★ | 10 | a hidden pressure or motive on a generated NPC | DMG p. 74 |
| **Magic Mushrooms** ★ | 10 | the effect of eating an unidentified magic mushroom | TCoE p. 53 |

### 1d12

| Table | Rows | What it rolls for | Source |
|---|---|---|---|
| **Urban Chase Complications** ★ | 7 effective | obstacle injected into an urban chase (7–12 = nothing) | DMG p. 8 |
| **Wilderness Chase Complications** ★ | 7 effective | obstacle injected into a wilderness chase (7–12 = nothing) | DMG p. 9 |
| **Current Calamities** ★ | 12 | the live pressure on a settlement | DMG p. 89 |
| **Local Leaders** ★ | 12 | who or what governs a settlement | DMG p. 90 |
| **NPC name tables** ★ — Common, Guttural, Lyrical, Monosyllabic, Sinister, Whimsical | 12 each | given name + surname (roll 1d6 to pick the table, then 1d12) | DMG p. 68–71 |
| **Enchanted Springs** ★ | 12 | the effect of one enchanted/tainted spring | TCoE p. 51 |
| Quicksand Pit, sinking rate | 4 (+1) | feet sunk per turn (1d4+1, scaling to 1d10) | DMG p. 54 |
| Poison harvest | 6 | minutes spent harvesting a venom, before the DC 20 check | DMG p. 81 |
| Contagion incubation | 4 | days before Cackle Fever / Sewer Plague effects begin | DMG p. 22 |

### d20

| Table | Rows | What it rolls for | Source |
|---|---|---|---|
| **Mob Results** ★★ | 20 × 3 × 4 | converts one d20 into a success *fraction* for a homogeneous group | DMG p. 64 |
| **Defining Traits** ★ | 11 effective | a physical descriptor for a settlement | DMG p. 88 |
| **Claims to Fame** ★ | 20 | a settlement's reputation | DMG p. 89 |
| **Tavern Names** ★ | 20 | two independent rolls → a two-part tavern name | DMG p. 90 |
| **Random Shops** ★ | 20 | which trade a settlement has | DMG p. 91 |
| Wild Magic Zone trigger | 20 | on a 20, roll the PHB *Wild Magic Surge* table | DMG p. 38 |
| Demonic Possession trigger | 20 | on a 1, the possessing entity takes control | DMG p. 21 |
| Chase opportunity, Escaped, etc. | 20 | covered by Mob Results / standard checks | — |

### 1d100

| Table | Rows | What it rolls for | Source |
|---|---|---|---|
| **Dungeon Quirks** ★ | 36 | a dungeon's origin/purpose/location tag | DMG p. 30–32 |
| **Blessed Radiance** ★ | 17 | a radiant / Upper-Planes effect in a region | TCoE p. 29 |
| **Far Realm** ★ | 13 | a reality-warping eldritch effect in a region | TCoE p. 32 |
| **Haunted** ★ | 20 | a ghostly or psychological effect in a region | TCoE p. 34 |
| **Infested** ★ | 19 | an insect/vermin hazard in a region | TCoE p. 37 |
| **Mirror Zone** ★ | 16 | a reflection/duplication effect in a region | TCoE p. 40 |
| **Psychic Resonance** ★ | 16 | a psionic/emotional effect in a region | TCoE p. 43 |
| **Unraveling Magic** ★ | 20 | a corrupted-magic effect in a region | TCoE p. 46 |

### NPC appearance

| Table | Rows | What it rolls for | Source |
|---|---|---|---|
| **NPC Appearance** ★ | 12 | one or two memorable visual traits for a generated NPC | DMG p. 73 |

### Non-roll reference tables (DC / scaling / lookup)

| Table | Shape | Use | Source |
|---|---|---|---|
| **Building a Trap** ★★ | level band × nuisance/deadly | the master trap-authoring table: attack bonus, save DC band, damage | DMG p. 112 |
| **Targets in Area of Effect** ★ | shape + size → creature count | estimate how many creatures a Fireball catches (adjust ±1d3) | DMG p. 65 |
| **Settlements by Size** ★ | 3 rows | population band + max item price in GP | DMG p. 87 |
| Trap severity bands | 8 traps × 4 bands | nuisance vs deadly per level band | DMG p. 104 |
| Hazard severity bands | 12 hazards × 4 bands | nuisance vs deadly per level band | DMG p. 50 |
| **Sample Fear DCs** | 3 rows | Wisdom save DC by how terrifying the stimulus is (10/15/20) | DMG p. 40 |
| **Sample Mental Stress Effects** | 3 rows | save DC + Psychic damage (1d6 / 3d6 / 9d6) | DMG p. 41 |
| **Doors** | 4 rows | AC, HP, DC to open (glass/metal/stone/wood) | DMG p. 27 |
| **Lock Quality** / **Lock Complexity** | 3 / 2 rows | DC to unlock (10/15/20) and time to pick (1 action / 1 minute) | DMG p. 28 |
| **Secret Doors** | 3 rows | DC to detect (barely/standard/well hidden) | DMG p. 28 |
| **Portcullises** | 3 sizes × 2 | Strength (Athletics) DC to lift (iron vs wood) | DMG p. 29 |
| **Spell Damage** | 10 spell levels | recommended damage dice, one target vs multiple | DMG p. 19 |
| **Magic Item Power by Rarity** ★ | 5 rarities | max spell level + max bonus per rarity | DMG p. 17 |
| **Level-Based Renown** ★ | 5 rows | level as shorthand for a tracked Renown Score | DMG p. 86 |
| **Maintenance Costs** | 3 rows | daily GP upkeep for a gifted fortification | DMG p. 59 |
| **Siege Equipment** | 10 objects | AC/HP, attack bonus or save DC, damage, Utilize action counts | DMG p. 94–98 |
| **Blessings** / **Charms** | 7 + 7 | permanent favour and consumable grant templates | DMG p. 100–103 |
| 14 **Sample Poisons** ★ | 14 rows | price, delivery type, save DC, damage, duration, secondary condition | DMG p. 81–84 |
| Poisonous Gas / Vicious Vine / Collapsing Roof / Poisoned Needle / Hidden Pit / Spiked Pit / Fire-Casting Statue / Poisoned Darts "At Higher Levels" | 7 × 4 bands | level scaling of damage + save DC / area / depth | DMG p. 54–112 |
| 26 **Tool Sample DC tables** ★ | 2–5 rows each | activity → DC, for every PHB tool | XGtE p. 6–23 |
| **Monster Relationships** ★ | 6 | an individual's bond to its group | XGtE p. 38 |
| **Quick Matchups** | 20 levels × 3 | monster CR for 1 / 2 / 4 monsters per character | XGtE p. 38 |
| **Solo Monster Challenge Rating** | 20 levels × 3 | CR of a legendary creature vs a party of 4/5/6 | XGtE p. 31 |
| **Multiple Monsters** × 4 tables | level rows × CR columns | character-to-monster equivalence ratios (1:12 default for missing low CR) | XGtE p. 35–36 |
| **Monster Research** ★ | 14 types | creature type → suggested skills; **DC = 10 + CR** | TCoE p. 22 |
| **Parleying** formula | — | advantage on a communication check when the offering matches a desire | TCoE p. 21 |
| **Sidekick level tables** — Expert / Spellcaster / Warrior | 20 rows each | PB, features, spell slots per level | TCoE p. 10–18 |
| **Identify a Spell** formula | — | **DC = 15 + spell level**, advantage if same class | XGtE p. 24 |
| **Emotional Echoes** ★ | 8 emotions | assign one emotion to a locale; once/day DC 16 *suggestion* | TCoE p. 48 |
| **Eldritch Storms** | 4 types | flaywind / flame storm / necrotic tempest / Thrym's howl | TCoE p. 47 |
| **Spells as Natural Hazards** | 23 rows | map a natural hazard to an existing spell effect | TCoE p. 60 |
| **Creature Traits** ★ | 23 traits | pick-and-mix trait effects for custom stat blocks | DMG p. 14 |
| **Go without a Long Rest** formula | — | DC 10 Constitution, **+5 per consecutive 24 h**, reset on a long rest | XGtE p. 3 |
| **Loyalty Score** | 0–20 | max = highest party CHA, start = half, +1d4 / −1d4 / −2d4 | DMG p. 78 |
| **Renown** thresholds | — | 3+ respect, 10+ perks, 25 / 50 major access; never below 0 | DMG p. 84 |

### Dice used as *durations and quantities* (not outcome tables)

| Expression | What | Source |
|---|---|---|
| 1d4 × 10 hours | flaywind duration | TCoE p. 47 |
| 2d4 minutes | flame storm duration | TCoE p. 47 |
| 1d4 hours / 1d4 days | necrotic tempest duration / aftermath | TCoE p. 47 |
| 2d10 hours | Thrym's howl duration | TCoE p. 48 |
| 4d6 feet | debris left in a flaywind's wake | TCoE p. 47 |
| 1d6 pieces per week | primal fruit regrowth; potent 1 week | TCoE p. 56 |
| 1d10 days | learn a cantrip; feather/eyestalk effects | TCoE p. 57 / 51 |
| 1d8 days | wildcard cantrip duration from Unraveling Magic | TCoE p. 46 |
| 1d10 minutes | an inferno with no fuel burns out | DMG p. 55 |
| 1d4 new 10-ft cubes | inferno growth per minute of strong wind | DMG p. 55 |
| 1d3 | spread vs. bunched adjustment in *Targets in Area of Effect* | DMG p. 65 |
| 1 Exhaustion per 5 minutes | buried by an avalanche | TCoE p. 58 |
| 1 Exhaustion per hour | deep water / extreme cold / bloodsucking insects | DMG p. 36; TCoE p. 37 |
| 3 days → DC 15 Constitution | shared recuperation save for all three DMG contagions | DMG p. 22 |
| 1d10 minutes | 1d10 × 10 hours of mental stress (short/long-term exposure) | DMG p. 41 |

---

## Part 1 — DMG (2024), Chapter 3: DM's Toolbox

---

Source: *Dungeon Master's Guide* (2024), Chapter 3 "DM's Toolbox" — D&D Beyond web print, 113 pages.
Boilerplate stripped: "Claim Your Free World of Warcraft Adventure", "DISMISS", "ARTIST: …", caption text in ALL CAPS, the `27.09.2026, 10:56 … - D&D Beyond` + `https://www.dndbeyond.com/sources/dnd/dmg-2024/dms-toolbox#Settlements n/113` footer pairs, and the site footer/Terms-of-Service block on p. 113.
Pages 42, 75, and 93 contain no body text in this extraction (they are the NPC Tracker, Settlement Tracker, and a full-page art plate respectively).

### Contents of this chapter, in source order

- **Alignment** — *(p. 3–4)* — character alignment, monster alignment, starting attitude, organization ethos.
- **Chases** — *(p. 4–10)* — starting a chase, dashing, ending a chase, **Escape Factors**, splitting up, role reversal, mapping, **Chase Complications** (urban + wilderness).
- **Creating a Background** — *(p. 10–12)* — the five-step background construction procedure.
- **Creating a Creature** — *(p. 12–15)* — minor alterations and the **Creature Traits** list.
- **Creating a Magic Item** — *(p. 15–17)* — modifying vs. creating, **Magic Item Power by Rarity**, attunement.
- **Creating a Spell** — *(p. 17–19)* — design checklist and the **Spell Damage** table.
- **Curses and Magical Contagions** — *(p. 19–24)* — four curse forms, Demonic Possession, three example contagions.
- **Death** — *(p. 24–27)* — fair death, scaling lethality, "Defeated, Not Dead", death scenes, TPK options.
- **Doors** — *(p. 27–30)* — common/barred/locked/secret doors, portcullises.
- **Dungeons** — *(p. 30–35)* — **Dungeon Quirks**, mapping principles, room categories, **States of Ruin**.
- **Environmental Effects** — *(p. 35–39)* — dead magic, deep water, temperature, precipitation, altitude, planar effects, slippery ice, strong wind, thin ice, wild magic.
- **Fear and Mental Stress** — *(p. 39–41)* — **Sample Fear DCs**, **Sample Mental Stress Effects**, prolonged effects.
- **Firearms and Explosives** — *(p. 43–46)* — modern/futuristic firearms tables, Burst Fire / Reload, explosive rules, alien technology.
- **Gods and Other Powers** — *(p. 46–50)* — divine rank, home plane, divine magic, intervention, creating religions.
- **Hazards** — *(p. 50–58)* — twelve example hazards, each with severity band and level scaling.
- **Marks of Prestige** — *(p. 58–62)* — fortifications, letters, medals, land, favors, rights, titles, training.
- **Mobs** — *(p. 62–66)* — mob tips, **Mob Results**, **Targets in Area of Effect**, worked examples.
- **Nonplayer Characters** — *(p. 66–79)* — six-element NPC build, six name tables, appearance/secret tables, party-member archetypes, Loyalty Score.
- **Poison** — *(p. 79–84)* — four delivery types, purchasing, harvesting, fourteen sample poisons.
- **Renown** — *(p. 84–86)* — gaining/losing renown, benefits, **Level-Based Renown**.
- **Settlements** — *(p. 86–92)* — size bands, defining traits, fame, calamities, leaders, tavern names, shops.
- **Siege Equipment** — *(p. 94–98)* — ten siege objects with AC/HP/actions.
- **Supernatural Gifts** — *(p. 99–103)* — Blessings and Charms.
- **Traps** — *(p. 104–112)* — trap anatomy, eight example traps with scaling, **Building a Trap**.

---

### Alignment *(p. 3–4)*

Alignment is a roleplaying tool, not a constraint. It helps in three ways: as a tool for player characters, as a descriptor of a creature's demeanor, and as a summary of an organization's ethos.

- **Character alignment.** Actions indicate alignment, not the reverse. It is fine to stray now and then, and players can change their characters' alignments when those alignments stop describing their characters.
- **Good and evil can cooperate.** Aligned characters often share goals but use different tactics (e.g. a Lawful Evil character bribing witnesses that a Lawful Good one would not).
- **Planes and alignment.** The Outer Planes are where alignment manifests; creatures experience those realms differently depending on their alignment.
- **Monster alignment — starting attitude.** Alignment helps determine attitude in an encounter: a Chaotic Evil monster is likely **Hostile**; a Lawful Good one is more likely **Friendly**, ready to help those in need.
- **Monster alignment — personality.** PHB ch. 2 offers a table of brief personality traits linked to alignment that can inspire an NPC or monster.
- **Organization ethos.** An alignment can be assigned to a faction, guild, or nation to describe its ethos and decide how groups interact. An organization's ethos does not dictate the alignment of its members or leaders, and a stark gap between societal ethos and leadership alignment is good adventure material (e.g. a Neutral Good queen reforming a Lawful Evil empire).

---

### Chases *(p. 4–10)*

Combat movement rules flatten chases (faster creatures always catch slower ones; equal Speed never closes distance). These rules add randomness. Know party capabilities first — Dimension Door, Fly, or Hold Monster can end a chase before it starts.

- **Beginning a chase.** Needs at least one quarry and at least one pursuer. Anyone not already in Initiative order rolls as the chase begins. Each participant takes one action and moves on its turn. Determine starting distance, track it, and designate the pursuer nearest the quarry as **the lead**; the lead can change each round.
- **Dashing.** A participant may Dash a number of times equal to **3 + its Constitution modifier** (minimum once). Each *additional* Dash during the chase requires **DC 10 Constitution saving throw** at end of turn or **1 Exhaustion level**. Dropping out at **5 Exhaustion** levels. A Short or Long Rest clears chase-caused Exhaustion.
- **Spells and attacks.** Participants may attack and cast at creatures in range. No Opportunity Attacks *between chase participants*, but creatures outside the chase (e.g. ruffians along the route) may still make them.
- **Ending a chase.** Ends when one side stops, each quarry escapes, or pursuers close enough to catch. Otherwise, on Initiative count 0 each round the **quarry makes a Dexterity (Stealth) check**. Automatic failure if never out of the lead pursuer's sight. Otherwise compare total against the pursuers' **Passive Perception**; a multi-creature quarry each makes the check separately.
- **Splitting up.** Quarry may divide; resolve each sub-chase separately, keeping one Initiative order but separate distances.
- **Role reversal.** Pursuers can become quarry; roll Initiative for new arrivals and run both chases simultaneously.
- **Mapping the chase.** Draw a rough route map; insert obstacles and complications at specific points, chosen from the Chase Complications tables. A chase map may be linear (mine cart) or heavily branched (sewer). Complications can be barriers *or* opportunities for mayhem (e.g. enrag a wasp nest to create an obstacle for pursuers).
- **Complication rolls.** Each participant rolls **1d12** at the end of its turn; the result affects the **next** participant in Initiative order, not the roller.

#### Escape Factors *(p. 6–7)*

> Caption and rows were split across the p. 6/p. 7 boundary; reconstructed into one table here.

| Factor | Check Has… |
|---|---|
| Many things to hide behind | Advantage |
| A very crowded area | Advantage |
| Few things to hide behind | Disadvantage |
| An uncrowded area | Disadvantage |

*What it is for: modifier to the quarry's Dexterity (Stealth) check when ending a chase; not a roll, just a circumstance lookup.*

Other factors may help or hinder at your discretion — a quarry under **Faerie Fire** has Disadvantage on checks to escape. If the quarry's total beats the **highest Passive Perception** among pursuers, it escapes; otherwise the chase continues a round. Escape need not mean outrunning — in a city it can mean ducking into a crowd or slipping around a corner.

#### Urban Chase Complications *(p. 8)*

| 1d12 | Complication |
|---|---|
| 1 | A cart or another large obstacle blocks your way. Make a **DC 10 Dexterity** saving throw to get past the obstacle. On a failed save, the obstacle counts as **10 feet of Difficult Terrain** for you. |
| 2 | A crowd blocks your way. Make a **DC 10 Strength, Dexterity, or Charisma** saving throw (your choice) to navigate through the crowd. On a failed save, the crowd counts as **10 feet of Difficult Terrain** for you. |
| 3 | A maze of barrels, crates, or similar obstacles stands in your way. Make a **DC 10 Dexterity or Intelligence** saving throw (your choice) to navigate the maze. On a failed save, the maze counts as **10 feet of Difficult Terrain** for you. |
| 4 | The ground is slippery with rain, spilled oil, or some other liquid. Make a **DC 10 Dexterity** saving throw. On a failed save, you have the **Prone** condition. |
| 5 | You encounter a brawl in progress. Make a **DC 15 Strength, Dexterity, or Charisma** saving throw (your choice) to get past the brawlers unimpeded. On a failed save, you take **2d4 Bludgeoning** damage, and the brawlers count as **10 feet of Difficult Terrain** for you. |
| 6 | You must make a sharp turn to avoid colliding with something impassable. Make a **DC 10 Dexterity** saving throw to navigate the turn. On a failed save, you collide with something hard and take **1d4 Bludgeoning** damage. |
| 7–12 | There is no complication. |

*What it is for: roll 1d12 per chase participant per turn to inject an obstacle into an urban chase; effects are saves and terrain, not damage tables.*

#### Wilderness Chase Complications *(p. 9–10)*

| 1d12 | Complication |
|---|---|
| 1 | You pass through a **Swarm of Insects** (see the Monster Manual, with the DM choosing whichever kind of insects makes the most sense). The swarm uses one of its actions, targeting you. |
| 2 | A stream or ravine blocks your path. Make a **DC 10 Strength or Dexterity** saving throw (your choice) to cross the impediment. On a failed save, the impediment counts as **10 feet of Difficult Terrain** for you. |
| 3 | Make a **DC 10 Constitution** saving throw. On a failed save, blowing sand, dirt, ash, snow, or pollen causes you to have the **Blinded** condition until the end of your turn. While Blinded in this way, your Speed is halved. |
| 4 | A sudden drop catches you by surprise. Make a **DC 10 Dexterity** saving throw to navigate the impediment. On a failed save, you fall **10 feet**. |
| 5 | Your path takes you near a patch of **razorvine** (see "Hazards"). Make a **DC 15 Dexterity** saving throw or use **10 feet of movement** (your choice) to avoid the razorvine. On a failed save, you take **1d10 Slashing** damage. |
| 6 | A creature native to the area notices you. (The DM chooses a creature appropriate for the terrain.) Make a **DC 10 Wisdom or Charisma** saving throw (your choice). On a failed save, the creature joins the chase, with you as its quarry. |
| 7–12 | There is no complication. |

*What it is for: wilderness counterpart of the Urban table; roll 1d12 per participant per turn.*

---

### Creating a Background *(p. 10–12)*

A background represents what a character did before becoming an adventurer. Creating one can reflect campaign theme, world elements, or a player's intended story.

1. **Choose Abilities** — pick three:
   - *Strength or Dexterity* — ideal for a background involving physical exertion.
   - *Constitution* — ideal for endurance or long hours of activity.
   - *Intelligence or Wisdom* — one or both for cerebral or spiritual matters.
   - *Charisma* — ideal for performance or social interaction.
2. **Choose a Feat** — one feat from the **Origin** category.
3. **Choose Skill Proficiencies** — two skills appropriate for the background. There need not be a relationship between the skills granted and the ability scores increased.
4. **Choose a Tool Proficiency** — one tool used in the practice of the background or often associated with it.
5. **Choose Equipment** — assemble a package worth **50 GP** (including unspent gold). Do not include martial weapons or armor (those come from class choices).

---

### Creating a Creature *(p. 12–15)*

Two approaches: **minor alterations** (tweak a stat block without changing its function) and adding **traits** (see the list below).

**Minor alterations** — any of the following without impacting functionality:

- **Size and creature type** — change freely (e.g. an Ogre stat block as a Medium Humanoid human bully).
- **Ability scores** — Intelligence, Wisdom, and Charisma are usually free to change *unless used for spellcasting* (e.g. Black Pudding as a sapient alien at Int/Cha 10). Best left alone: Strength, Dexterity, Constitution, because they alter attack bonus, damage, AC, or HP — and therefore Challenge Rating.
- **Languages** — change any or all; add telepathy or other communication forms.
- **Proficiencies** — any skill proficiencies, plus **Expertise**; can also swap or add saving throw proficiencies (one or two).
- **Senses** — Blindsight, Darkvision, Tremorsense, Truesight have **no** bearing on CR; add/remove freely.
- **Spells** — swap any spell for a different spell of the *same level*; avoid trading damaging spells for non-damaging ones or vice versa.
- **Attacks** — freely change name, flavor, and damage type (e.g. Skeleton → ice skeleton dealing Cold).
- **Resistances and immunities** — add Resistance/Immunity to one or two damage types, or change the damage type of existing ones.
- **Traits** — add traits that communicate nature, or reuse Monster Manual traits, provided they do not alter HP, confer Temporary HP, or change the damage the creature deals to others.

#### Creature Traits *(p. 14–15)*

*Presented as a table; in the source this is a running list of 23 named traits. Use as a pick-and-mix pool for custom stat blocks.*

| Trait | Effect |
|---|---|
| Aversion to Fire | If the creature takes Fire damage, it has **Disadvantage** on attack rolls and ability checks until the end of its next turn. |
| Battle Ready | The creature has **Advantage on Initiative** rolls. |
| Beast Whisperer | The creature can communicate with Beasts as if they shared a common language. |
| Death Jinx | When the creature dies, one random creature within 10 feet of the dead creature is targeted by a **Bane** spell (**save DC 13**), which lasts for its full duration. |
| Dimensional Disruption | Disruptive energy extends from the creature in a **30-foot Emanation**. Other creatures can't teleport to or from a space in that area. Any attempt to do so is wasted. |
| Disciple of the Nine Hells | When the creature dies, its body disgorges a **Hostile Imp** in the same space. |
| Disintegration | When the creature dies, its body and nonmagical possessions turn to dust. Any magic items it possessed are left behind in its space. |
| Emissary of Juiblex | When the creature dies, its body disgorges a **Hostile Ochre Jelly** in the same space. |
| Fey Ancestry | The creature has **Advantage** on saving throws it makes to avoid or end the **Charmed** condition, and magic can't put it to sleep. |
| Forbiddance | The creature can't enter a residence without an invitation from one of its occupants. |
| Gloom Shroud | Imperceptible energy channeled from the Shadowfell extends from the creature in a **20-foot Emanation**. Other creatures in that area have **Disadvantage on Charisma checks and Charisma saving throws**. |
| Light | The creature sheds **Bright Light** in a 10-foot radius and **Dim Light** for an additional 10 feet. As a **Bonus Action**, the creature can suppress this light or cause it to return. The light winks out if the creature dies. |
| Mimicry | The creature can mimic **Beast** sounds and **Humanoid** voices. A creature that hears the sounds can tell they are imitations with a successful **DC 14 Wisdom (Insight)** check. |
| Poison Tolerant | The creature has **Advantage** on saving throws it makes to avoid or end the **Poisoned** condition. |
| Resonant Connection | The creature has a supernatural connection to another creature or an object and knows the most direct route to it, provided the two are within **1 mile** of each other. |
| Siege Monster | The creature deals **double damage** to objects and structures. |
| Slaad Host | When the creature dies, a **Hostile Slaad Tadpole** bursts from its innards in the same space. |
| Steadfast | The creature has **Immunity** to the **Frightened** condition while it can see an ally within 30 feet of itself. |
| Telepathic Bond | The creature is linked psychically to another creature. While both are on the same plane of existence, they can communicate telepathically with each other. |
| Telepathic Shroud | The creature is immune to any effect that would sense its emotions or read its thoughts, as well as to spells from the school of **Divination**. As a **Bonus Action**, the creature can suppress this trait or reactivate it. |
| Ventriloquism | Whenever the creature speaks, it can choose a point within 30 feet of itself; its voice emanates from that point. |
| Warrior's Wrath | The creature has **Advantage** on melee attack rolls against any **Bloodied** creature. |
| Wild Talent | Choose one cantrip; the creature can cast that cantrip without spell components, using Intelligence, Wisdom, or Charisma as the spellcasting ability. |

*What it is for: not a roll table — a menu of 23 ready-made trait effects (each with its own DCs, emanation radii, or death triggers) to bolt onto a stat block.*

---

### Creating a Magic Item *(p. 15–17)*

**Modifying a magic item** (tweak one or more existing ones):

- **Altered Capabilities** — one capability replaces a similar one (Potion of Climbing → Potion of Swimming).
- **Altered Form** — change form, keep properties (Ring of the Ram → wand; Cloak of Protection → circlet).
- **Altered Damage Types** — Flame Tongue dealing Lightning instead of Fire.
- **Combining items** — merge properties of two items of the **same rarity**, provided no more than one requires **Attunement** (e.g. Helm of Comprehending Languages + Helm of Telepathy). More powerful and probably higher rarity, but won't break the game.
- **Special features and sentience** — see ch. 7 for histories, minor properties, quirks, sentience.

**Creating a new item:** an item should either let a character do something they couldn't do before, or improve something they can already do. Keep the approach simple; charges are fine, but "always active" or "N uses/day" is easier to manage than a large charge pool.

#### Magic Item Power by Rarity *(p. 17)*

> Header was split across lines in the extraction (`Rarity` / `Max.` / `Spell` / `Level` / `Max.` / `Bonus`); reconstructed below.

| Rarity | Max. Spell Level | Max. Bonus |
|---|---|---|
| Common | 1 | — |
| Uncommon | 3 | +1 |
| Rare | 5 | +2 |
| Very Rare | 8 | +3 |
| Legendary | 9 | +4 |

*What it is for: caps an item's power by rarity — the highest spell level it may confer as a once-per-day property, and the maximum static bonus to AC, attack rolls, saving throws, or ability checks.*

**Attunement guidelines:** require Attunement to *limit sharing* (if passing the item around for lasting benefit would be disruptive) and to *limit stacking* (if the bonus duplicates other items).

---

### Creating a Spell *(p. 17–19)*

Design checklist:

- **Name** — must be unique.
- **Balance** — if a caster would use it every time, it's too powerful for its level.
- **Identity** — must fit the casters (Sorcerers and Wizards don't typically cast healing spells).
- **Spell Duration, Range, and Area** — a longer duration, greater range, or larger area can compensate for a lesser effect.
- **Utility** — avoid very limited use (e.g. only works against Oozes).

**Spell damage.** For any damaging spell, use the Spell Damage table. The table assumes **half damage on a successful save or a missed attack**. If the spell deals no damage on a successful save, increase damage by **25 percent**. Different dice are allowed if the average matches — e.g. a cantrip's `1d10` (avg 5.5) can become `2d4` (avg 5) to lower the maximum and make averages more likely. The same table also sizes **healing** spells; a cantrip should not heal.

#### Spell Damage *(p. 19)*

| Spell Level | One Target | Multiple Targets |
|---|---|---|
| Cantrip | 1d10 | 1d6 |
| 1 | 2d10 | 2d6 |
| 2 | 3d10 | 3d6 |
| 3 | 5d10 | 6d6 |
| 4 | 6d10 | 7d6 |
| 5 | 7d10 | 8d6 |
| 6 | 10d10 | 11d6 |
| 7 | 11d10 | 12d6 |
| 8 | 12d10 | 13d6 |
| 9 | 15d10 | 16d6 |

*What it is for: not a roll — a lookup from spell level to recommended damage dice, for one target or for multiple targets; also reused for healing spell potency.*

---

### Curses and Magical Contagions *(p. 19–24)*

A **curse** is a magical burden that lasts a specified time or until ended by some means. A **magical contagion** is an adverse magical effect that is contagious by definition; an outbreak can be the basis of an adventure (search for a cure, stop the spread).

#### Curses — the four forms *(p. 20–22)*

1. **Bestow Curse** — the simplest curses, created by the Bestow Curse spell; effects are limited and can be ended by **Remove Curse**. Benchmark for gauging potency: a curse lasting **1 minute ≈ a level 3 spell**; one lasting until dispelled ≈ a **level 9 spell**.
2. **Cursed creatures** — monsters associated with curses by origin or by their ability to spread them (werewolves are the prime example). You decide how *Remove Curse* affects them (e.g. a mummy can be destroyed permanently only by *Remove Curse* cast on its corpse).
3. **Cursed magic items** — created deliberately or from supernatural events; detailed in ch. 7.
4. **Narrative curses** — supernatural punishment for a taboo violation (breaking a vow, defiling a tomb, murdering an innocent). The victim should know why they are being punished and how to end it, likely by symbolically righting the wrong. *Remove Curse* might merely suppress the effects for a time. Should feel like rare, potent magic rooted in campaign lore.
5. **Environmental curses** — locations so suffused with evil that anyone who lingers is burdened. **Demonic Possession** is the worked example.

#### Demonic Possession *(p. 21–22)*

- Arises from the chaos and evil of the **Abyss**; besets creatures that interact with demonic objects or linger in desecrated locations.
- On becoming the target: **DC 15 Charisma saving throw** or possessed by a bodiless demonic entity.
- Whenever the possessed creature rolls a **1 on a D20 Test**, the entity takes control and determines the creature's behavior thereafter.
- At the end of each of the possessed creature's *later* turns: **DC 15 Charisma saving throw**, regaining control on a success.
- After a **Long Rest**: **DC 15 Charisma saving throw**; on a success the effect ends. **Dispel Evil and Good** or any magic that removes a curse also ends it.

#### Magical Contagions *(p. 22)*

**Rest and recuperation (all three example contagions share this):** a creature infected with a magical contagion that spends **3 days** recuperating (no activities that would interrupt a Long Rest) makes a **DC 15 Constitution saving throw** at the end of the period. On a success it has **Advantage** on saving throws to fight off the contagion for the next **24 hours**.

**Cackle Fever — Magical Contagion.** Cheaply made potions and elixirs are sometimes tainted by it. Affects **Humanoids only** (gnomes are strangely immune). A creature suffers the effects **1d4 days** after infection:

- **Fever** — 1 Exhaustion level, lasting until the contagion ends on the creature.
- **Uncontrollable Laughter** — while Exhausted, the creature makes a **DC 13 Constitution** saving throw each time it takes damage other than Psychic damage. Failed save: **5 (1d10) Psychic** damage and the **Incapacitated** condition. It repeats the save at the end of each of its turns, ending the effect on a success. **After 1 minute it succeeds automatically.**
- **Fighting the contagion** — at the end of each Long Rest, **DC 13 Constitution** saving throw. After **three** successes the contagion ends and the creature is immune to Cackle Fever for **1 year**.
- **Spreading the contagion** — any **Humanoid** (other than a gnome) that starts its turn within a **10-foot Emanation** originating from an infected creature must succeed on a **DC 10 Constitution** saving throw or become infected. On a success, that Humanoid can't catch it from that particular creature for **24 hours**.

**Sewer Plague — Magical Contagion.** From fouled potions and alchemical waste; incubates in sewers and refuse heaps; spread by creatures that dwell there (otyughs, rats). Any **Humanoid** wounded by a carrier, or that contacts contaminated filth or offal, must succeed on a **DC 11 Constitution** saving throw or become infected. Effects **1d4 days** after infection:

- **Fatigue** — 1 Exhaustion level.
- **Weakness** — while Exhausted, it regains only **half** the normal number of Hit Points from spending Hit Point Dice.
- **Restlessness** — while Exhausted, finishing a Long Rest neither restores lost Hit Points nor reduces Exhaustion.
- **Fighting the contagion** — **daily at dawn**, **DC 11 Constitution** saving throw. Failure: +1 Exhaustion. Success: Exhaustion decreases by 1. At **0 Exhaustion** the contagion ends.

**Sight Rot — Magical Contagion.** Any **Beast or Humanoid** that drinks tainted water must succeed on a **DC 15 Constitution** saving throw or have the **Blinded** condition until the contagion ends.

- **Fighting the contagion** — **Heal** or **Lesser Restoration** ends it immediately. A character **proficient with an Herbalism Kit** can create one dose of nonmagical ointment in **1 hour**; applied to the eyes it suppresses the contagion for **24 hours**. Three doses/applications (i.e. **72 hours**) end it.
- **Spreading the contagion** — any **Humanoid** making **skin contact** with an infected creature must succeed on a **DC 15 Constitution** saving throw or become infected; on a success it can't catch it from that creature for **24 hours**.

---

### Death *(p. 24–27)*

Adventures carry risk. Because players get attached to characters, talk about how death is handled at the start of a new game.

**Death must be fair.** Four principles:
- **Don't cheat in the monsters' favor.** Rolling dice in the open when a situation is deadly communicates fairness.
- **Don't make it personal.** Never punish a character for a player's behavior or a personal grudge.
- **Provide fair warning.** Let characters face the consequences of foolish actions, but give enough cues to recognize self-destructive ones; ask "Are you sure?" before a potentially fatal course of action.
- **Fair encounters.** Tough encounters are fine, and letting them face monsters they can't beat is fine — but not if they have no way to know they can't win or no way to escape.

**Scaling lethality.** Adjust via ch. 4 encounter-building guidelines. Players who enjoy being tested to the utmost and can create new characters at a moment's notice: repeated high-difficulty encounters with little rest between them. All-low-difficulty encounters plus ample rest is less likely to lead to death.

#### Defeated, Not Dead *(p. 25–26)*

Optional rules if the group agrees to avoid character death. A character who would otherwise die is instead **"defeated"**:

- **Comatose** — the character has **1 Hit Point** and the **Unconscious** condition. Can regain Hit Points as normal but remains Unconscious until targeted by **Greater Restoration** or experiencing a sudden awakening.
- **Sudden Awakening** — after a **Long Rest**, the character makes a **DC 20 Constitution** saving throw. Success ends the Unconscious condition; failure means it persists.

**Death scenes.** At 0 Hit Points the player otherwise just rolls Death Saves. Prompt roleplay alongside each save — e.g. a memory surfacing in the character's mind:
- *On a successful Death Save* — a memory that inspires hope and courage; a beloved person urging them to cling to life; something to live for; a favorite childhood memory.
- *On a failed Death Save* — a memory that stirs up shame or grief; a beloved person already dead, beckoning them; weariness or despair.
- You can reward a player who describes a memory with **Advantage on the Death Save**.
- When a character dies (from failed saves or an outright killing effect), give the player ownership of the final moments — ask what the last words are, or how the character greets death.

**Dealing with death.** Consult the players. A replacement party member starts at the same level with gear of similar value. Resurrection is possible via **Revivify** / **Raise Dead**; you decide how accessible those spells are to characters who can't cast them (PHB suggests prices for spellcasting services).

**What if everyone dies?** (A "total party kill," or **TPK**.) Five options given:
- **A Fresh Start** — everyone makes new characters and the campaign starts anew (most drastic; allows new stories and dynamics).
- **Divine Council** — the characters must convince a council of deities arguing over their fate to return them to life.
- **Escape from the Underworld** — the dead wake in Hades (ch. 6) and must escape the underworld.
- **Imprisoned** — they wake in cells, kept alive by their foes for some purpose.
- **Raised by Another** — a powerful individual raises them, putting them in the rescuer's debt; they might wake decades later, returned by a **Resurrection** cast by someone who believed they had a role in this future era.
- **Rescue Mission** — the players make new, temporary characters to retrieve the bodies, for raising or proper burial. If the dead characters have **Bastions** (ch. 8), the stand-in party could be **hirelings** from those Bastions.

---

### Doors *(p. 27–30)*

The **Doors** table gives AC and Hit Points for common doors, which are **Medium objects**. With the **Utilize** action, a creature can force open a barred or locked door with a successful **Strength (Athletics)** check; the table gives the DC. **For bigger doors, double or triple the Hit Points and increase the check DC by 5.**

#### Doors *(p. 27)*

| Door | AC | HP | DC to Open |
|---|---|---|---|
| Glass door | 13 | 4 | 10 |
| Metal door | 19 | 72 | 25 |
| Stone door | 17 | 40 | 20 |
| Wooden door | 15 | 18 | 15 |

*What it is for: not a roll — object toughness and the Strength (Athletics) DC to force a door; scale by 2×/3× for bigger doors.*

**Barred door** — no lock. A creature on the barred side can take the **Utilize** action to lift the bar from its braces, allowing the door to be opened.

**Locked door** — characters without the key pick the lock with **Thieves' Tools**. The Lock Complexity table sets how long picking takes; at the end of that time the character makes a successful **Dexterity (Sleight of Hand)** check using Thieves' Tools. The DC comes from the Lock Quality table.

#### Lock Complexity *(p. 28)*

| Complexity | Time |
|---|---|
| Simple | 1 action |
| Complex | 1 minute |

*What it is for: not a roll — how long a lock-pick attempt takes before the Dexterity (Sleight of Hand) check is made.*

#### Lock Quality *(p. 28)*

| Quality | DC to Unlock |
|---|---|
| Inferior | 10 |
| Good | 15 |
| Superior | 20 |

*What it is for: the target DC for a Dexterity (Sleight of Hand) check using Thieves' Tools to pick the lock.*

**Secret doors** — crafted to blend into the surrounding wall; faint cracks or scuff marks may betray them. Otherwise identical to common doors. With the **Search** action, a character searches a **10-foot-square section of wall** and makes a **Wisdom (Perception)** check; success finds any secret door in that section plus its opening mechanism. Instead call for an **Intelligence (Investigation)** check when the challenge is *deducing a door is present* from noticeable clues rather than spotting those clues (see "Perception", ch. 2).

#### Secret Doors *(p. 28–29)*

> Caption and header fragment ("Secret Door" / "DC to Detect") sit on p. 28 while all rows fall on p. 29; reconstructed here.

| Secret Door | DC to Detect |
|---|---|
| Barely hidden secret door | 10 |
| Standard secret door | 15 |
| Well-hidden secret door | 20 |

*What it is for: target DC for a Wisdom (Perception) or Intelligence (Investigation) check over a 10-foot-square section of wall.*

**Secret door etiquette** — adventurers often fail to find them. Don't hide important treasures or locations behind secret doors unless you're comfortable with the characters not finding them, and never let an adventure grind to a halt because the only path forward is a secret door.

**Portcullises** — typically iron or wood; block a passage or archway until winched into the ceiling. Creatures within **5 feet** of a lowered portcullis can make ranged attacks or cast spells through it and have **Three-Quarters Cover** against attacks, spells, and other effects from the opposite side. A portcullis can be attacked and destroyed using the AC and HP of a **metal door** (if iron) or a **wooden door** (if wood). Winching up or down requires the **Utilize** action. If a creature can't reach the winch (usually because it's on the other side), lifting it requires **Utilize** plus a successful **Strength (Athletics)** check.

#### Portcullises *(p. 29–30)*

> Header row on p. 29, rows on p. 30; the size column and its parenthetical dimensions were split across lines. Reconstructed with the dimensions merged into the size cell.

| Portcullis Size | Iron DC | Wood DC |
|---|---|---|
| Medium (8 ft. tall × 5 ft. wide) | 20 | 15 |
| Large (10 ft. tall × 10 ft. wide) | 25 | 20 |
| Huge (20 ft. tall × 15 ft. wide) | 30 | 25 |

*What it is for: target DC for a Strength (Athletics) check to lift a portcullis whose winch is out of reach; separate values for iron and wood.*

---

### Dungeons *(p. 30–35)*

Dungeons are old strongholds, natural caves, or monster-carved lairs; they attract cults, monster groups, and reclusive creatures. Use **Dungeon Quirks** to give a dungeon (including a published one) distinctive character. Quirks reflect the creator, purpose, location, or a catastrophic event. Use one or combine several; roll or choose.

#### Dungeon Quirks *(p. 30–32)*

> Header on p. 30; the body runs across p. 30, 31 and 32 with the `1d100 | Quirk` header repeated on each page. All **36** rows are given below.

| 1d100 | Quirk |
|---|---|
| 01–02 | Abandoned after internal strife devastated its population |
| 03–04 | Abandoned because the site was cursed by a god or other powerful entity |
| 05–06 | Abandoned by its original creators when a plague spread through the dungeon |
| 07–09 | Amazingly well preserved ancient city inside a dome encased in volcanic ash, submerged underwater, or entombed in desert sands |
| 10–12 | Built as a fortress guarding a mountain pass |
| 13–15 | Built as a maze, either to protect treasure from intruders or as a gauntlet where prisoners were hunted by monsters |
| 16–18 | Built as a stronghold but abandoned after it fell to invaders |
| 19–21 | Built as a treasure vault to protect powerful magic items and great wealth |
| 22–23 | Built atop a cloud |
| 24–26 | Built beneath a city in catacombs or sewers |
| 27–29 | Built beneath or on top of a mesa or several connected mesas |
| 30–32 | Built by a religious group to serve as a temple and linked to the energy of other planes of existence |
| 33–35 | Built by dwarves and decorated with enormous dwarven faces that have been defaced by its current inhabitants |
| 36–38 | Built in a volcano |
| 39–40 | Built in or among the branches of a tree |
| 41–43 | Built to house a planar portal but abandoned when creatures or energy from the other side of the portal seeped into the dungeon |
| 44–46 | Carved into a meteorite (before or after it fell to earth) |
| 47–49 | Carved into a sheer cliff face |
| 50–52 | Caverns carved by a beholder's disintegration eye ray, with unnaturally smooth walls and vertical shafts connecting different levels |
| 53–55 | Contains something that led to the downfall of its creators or inhabitants |
| 56–58 | Dug as a burrow by a monster that might still live inside |
| 59–61 | Entrance concealed behind a waterfall |
| 62–64 | Floating on the sea |
| 65–66 | Intended as a death trap to eliminate any creature that enters, perhaps to guard a treasure or to harvest souls for a necromantic rite |
| 67–69 | Intended as a tomb |
| 70–72 | Long known as the site of a great miracle or another auspicious event |
| 73–75 | Made by amphibious creatures (such as kuo-toa or aboleths), using water to protect the innermost reaches from air-breathing intruders |
| 76–78 | Made by a powerful spellcaster (perhaps a lich) as a site for magical research and experimentation |
| 79–81 | Made by giants at a vast scale |
| 82–84 | Natural caverns featuring a range of strikingly beautiful rock and crystal formations |
| 85–87 | On an island in an underground sea |
| 88–90 | On the back of a Gargantuan creature |
| 91–93 | Originally constructed as a mine but abandoned when tunnels connected to dangerous Underdark tunnels |
| 94–96 | Secreted away in a demiplane or in a pocket dimension |
| 97–98 | Slowly abandoned as its creators died out or migrated away |
| 99–00 | Transformed by multiple events or disasters over the course of centuries |

*What it is for: roll 1d100 (or choose) to give a dungeon an origin/purpose/location tag; purely descriptive, no mechanical effect.*

**Mapping a dungeon** *(p. 32–33)*. A dungeon can range from a few chambers to a complex of rooms and passages extending hundreds of feet; the goal often lies as far from the entrance as possible. A dungeon is usually mapped on a **graph-paper grid, each square representing an area of 5 feet by 5 feet** (Appendix B has examples); that scale transfers directly to a battle grid.

Six mapping principles:
- **Asymmetry** — asymmetrical rooms and layouts make a dungeon interesting and unpredictable.
- **Three-dimensional layout** — stairs, ramps, lifts, platforms, ledges, balconies, pits and other elevation changes add interest and complicate combat there.
- **Multiple pathways** — add multiple entrances and exits, to the dungeon and to individual rooms, to present meaningful decision points.
- **Wear and tear** — collapsed passages cutting off formerly connected sections; earthquakes opening chasms that split rooms and corridors.
- **Natural features** — underground streams, variable room shapes, bridges and drains.
- **Secrets** — add secret doors and secret rooms to reward searching; consider each one's original purpose (defense against invaders? denizens scheming to keep secrets from each other?) as story development.

**Designing dungeon rooms** *(p. 33–34)*. Keep in mind: **Ceiling Support** (arched ceilings or pillars, especially in large rooms) and **Decoration** (statues, bas-reliefs, murals, mosaics; scrawled messages, marks, maps — some graffiti, some useful). Also **Exits** — creatures that can't open doors can't lair in a sealed room without external help; strong creatures smash doors down, burrowers dig their own exits.

Room categories (broad, not exhaustive):
- **Crypts** — a vault-like room, a series of rooms each with its own sarcophagus, or a long hall with recesses. Builders worried about rising undead lock and trap from *outside* (easy in, hard out); builders worried about tomb robbers make them hard to get into; some make both hard.
- **Guard Posts** — sapient, social denizens guard shared spaces; may be a room with a table where bored sentries play a dice game, or iron golems backed by spellcasters in overhead balconies. Decide how many guards are on duty, note their **Passive Perception** scores, and decide what they do on noticing intruders (rush in, negotiate, sound an alarm, flee for help) — see "Monster Behavior" ch. 4.
- **Living Quarters** — beds (if they sleep), possessions (valuable and mundane), a food preparation area (well-stocked kitchen, firepit, or a hunk of rotting meat).
- **Natural Subterranean Areas** — where built dungeons intersect natural caverns, grottoes and passages: strange rock formations, pools of water, molds, fungi, bioluminescent moss.
- **Shrines** — any sapient creature might have a worship space, humble or extensive. Likely to hold priests and cultists; wounded monsters may flee to a shrine to seek healing.
- **Vaults** — treasure, usually sealed behind a locked or secret door, often further protected by magic, monsters that survive without food and water, and traps (see "Traps").
- **Work Areas** — laboratories, workshops, libraries, forges, studios; valuable equipment, so doors often locked and sometimes warded by **Glyph of Warding** and similar.

#### States of Ruin *(p. 35)*

| 1d6 | Features |
|---|---|
| 1 | **Perilous.** The area is dangerously worn and prone to collapse. Any impacts or damage to the structure, including from spells and other areas of effect, have a **50 percent** chance of causing a collapse. |
| 2 | **Crumbling.** Areas within the dungeon section are choked with rubble and have a **50 percent** chance of being **Difficult Terrain**. Half Cover and hiding places are plentiful. |
| 3 | **Neglected.** One dungeon hazard—such as brown mold, green slime, or yellow mold (see "Hazards")—is abundant. |
| 4 | **Abandoned.** Most of the dungeon is deserted. **Dexterity (Stealth)** checks have **Disadvantage** because any sounds stand out as unusual. |
| 5 | **Secure.** Ability checks made to break down doors, open locks, or carry out similar activities have **Disadvantage**. |
| 6 | **Thriving.** The dungeon is heavily populated. Any loud noises draw the attention of nearby creatures. |

*What it is for: roll 1d6 to set the decay/occupancy state of a dungeon section; it drives terrain, cover, stealth and noise rather than a check DC.*

---

### Environmental Effects *(p. 35–39)*

Rules for handling hazards of place — extreme cold, high altitude, and the rest.

- **Dead Magic Zone** — the fabric of magic is torn. Same effect as the **Antimagic Field** spell, except it is permanent and typically covers an area no more than **300 feet in diameter**.
- **Deep Water** — more than **100 feet deep**. After **each hour** of swimming, a creature lacking a Swim Speed must succeed on a **DC 10 Constitution** saving throw or gain **1 Exhaustion** level.
- **Extreme Cold** — at **0 °F or lower**, a creature exposed must succeed on a **DC 10 Constitution** saving throw at the end of each hour or gain **1 Exhaustion** level. Resistance or Immunity to **Cold** damage auto-succeeds.
- **Extreme Heat** — at **100 °F or higher**, a creature exposed **and without access to drinkable water** must succeed on a Constitution saving throw at the end of each hour or gain **1 Exhaustion** level. **The DC is 5 for the first hour and increases by 1 for each additional hour.** Creatures in **Medium or Heavy armor** have **Disadvantage** on the save. Resistance or Immunity to **Fire** damage auto-succeeds.
- **Frigid Water** — a creature can be immersed for a number of **minutes equal to its Constitution score** before ill effects. Each additional minute requires a **DC 10 Constitution** saving throw or **1 Exhaustion** level. Cold Resistance/Immunity auto-succeeds, as does natural adaptation to ice-cold water.
- **Heavy Precipitation** — heavy rain or snowfall makes the area **Lightly Obscured**, and creatures there have **Disadvantage on all Wisdom (Perception) checks**. Heavy rain also extinguishes open flames.
- **High Altitude** — at **10,000 feet or higher** above sea level. Each hour spent traveling at high altitude counts as **2 hours** toward Travel Pace (ch. 2). Creatures can acclimate by spending **30 days or more** at that elevation, and **cannot** acclimate above **20,000 feet** unless native to such environments.
- **Slippery Ice** — is **Difficult Terrain**. A creature that moves onto it for the first time on a turn, or starts its turn there, must succeed on a **DC 10 Dexterity** saving throw or have the **Prone** condition.
- **Strong Wind** — imposes **Disadvantage** on ranged weapon attack rolls, extinguishes open flames, and disperses fog. A flying creature must land at the end of its turn or fall. In a desert it can create a **sandstorm** imposing **Disadvantage on Wisdom (Perception)** checks.
- **Thin Ice** — weight tolerance of **3d10 × 10 pounds per 10-foot-square area**. When the total weight on an area exceeds its tolerance, the ice breaks and all creatures on it fall through. Below the ice is **frigid water**.
- **Wild Magic Zone** — a past magical disaster or uncontrolled surge can unravel the fabric of magic; typically no more than **300 feet in diameter**. Whenever a creature expends a **spell slot** in the zone, roll **1d20**; on a **20**, roll on the **Wild Magic Surge** table in the *Player's Handbook*.

#### Planar Effects *(p. 37–38)*

| Plane / Effect | Effect on creatures in its influence |
|---|---|
| **Acheronian Bloodlust** (Acheron) | A creature gains **Temporary Hit Points equal to half its Hit Point maximum** whenever it reduces another creature to 0 Hit Points. |
| **Arcadian Vitality** (Arcadia) | Creatures gain **Immunity to the Frightened and Poisoned conditions**. |
| **Blessed Beneficence** (Mount Celestia) | Creatures other than **Fiends** and **Undead** gain the benefit of the **Bless** spell while in the area; a creature that finishes a **Long Rest** there also gains the benefit of **Lesser Restoration**. |
| **Gehennan Cruelty** (Gehenna) | Whenever a creature casts a spell (including healing or condition removal other than **Invisible**), the caster must succeed on a **DC 10 Charisma** saving throw or the spell fails and is wasted. |
| **Winds of Pandemonium** (Pandemonium, incl. parts of the Underdark) | A creature makes a **DC 10 Wisdom** saving throw after each hour among the winds; failure = **1 Exhaustion** level. The winds can't raise Exhaustion above **3**. A Long Rest does not reduce Exhaustion unless the creature escapes the winds. |

*What it is for: not a roll table — five region-wide auras keyed to planes, each with a specific save, benefit, or temporary-HP trigger.*

---

### Fear and Mental Stress *(p. 39–41)*

Adventurers are less susceptible to fear and mental stress than common folk, but certain creatures and effects can still terrify or fray them. Discuss these rules with players at the start of the campaign (see "Ensuring Fun for All", ch. 1).

**Fear effects.** Use the **Frightened** condition as the baseline. Typically a Wisdom saving throw, with a DC based on how terrifying the situation is. A Frightened creature normally repeats the save at the end of each of its turns, ending the effect on a success. At your discretion, while Frightened it may also:

- be required to take the **Dash** action each turn, using its movement to get farther from the source of fear;
- grant **Advantage** on attack rolls against it;
- be able to do only **one** of the following each turn: move, take an action, or take a Bonus Action.

#### Sample Fear DCs *(p. 40)*

| Example | Save DC |
|---|---|
| When the characters open a sarcophagus, a harmless yet terrifying apparition appears. | 10 |
| A character triggers a magical trap that creates an illusory manifestation of that character's worst fears, visible only to that character. | 15 |
| A portal to the Abyss opens, revealing a nightmarish realm of torment and slaughter. | 20 |

*What it is for: not a roll table — the Wisdom save DC to set for a Frightened effect, chosen by how terrifying the stimulus is.*

**Mental stress effects.** Use **Psychic damage** to emulate intense mental stress. Mental stress is usually resisted with a successful **Wisdom** save, but sometimes **Intelligence** or **Charisma** is more appropriate. On a successful save a character might take **half** damage instead of none, at your discretion.

#### Sample Mental Stress Effects *(p. 41)*

| Example | Save DC | Psychic Damage |
|---|---|---|
| A character ingests a hallucinogenic substance that distorts the character's perception of reality. | 10 | 1d6 |
| A character touches a fiendish idol that tears at the character's mind, threatening to shatter it. | 15 | 3d6 |
| A magical trap flings a character into the Far Realm until the end of that character's next turn. | 20 | 9d6 |

*What it is for: not a roll table — pairs a save DC and Psychic damage expression for a mental-stress effect; used for hazards, traps, and psychic magic.*

**Prolonged effects** of exposure to mental stress:
- **Short-Term** — the character has **Frightened, Incapacitated, or Stunned** for **1d10 minutes**, possibly with alarming behavior or hallucinations. Suppressed by **Calm Emotions**, removed by **Lesser Restoration**.
- **Long-Term** — the character has **Disadvantage on some or all ability checks for 1d10 × 10 hours**, stemming from unwillingness or inability to exert a set of abilities (enervated, unable to exert Strength; suspicious, making Charisma checks harder). Suppressed by **Calm Emotions**, removed by **Lesser Restoration**.
- **Indefinite** — a long-term effect that lasts until removed by a **Greater Restoration** spell. Can be suppressed by **Calm Emotions**.

---

### Firearms and Explosives *(p. 43–46)*

For campaigns involving a crashed spaceship or elements of modern-day Earth. Renaissance-era pistols and muskets are in the PHB. If firearms are made available for purchase (e.g. the marketplaces of the City of Brass), treat **modern items as Rare** magic items and **futuristic items as Very Rare** ones.

**Properties** in addition to PHB weapon properties:

- **Burst Fire** — as an Action, expend **10 pieces** of ammunition to spray shots in a **10-foot Cube** within the weapon's normal range. Each creature in the area must succeed on a **DC 15 Dexterity** saving throw or take damage. Roll the weapon's damage **once** and apply it to each creature that failed the save.
- **Reload** — you can make a limited number of shots, then must reload the weapon as an **Action** or a **Bonus Action**.
- **Ammunition** — **Firearm Bullets** are destroyed on use in a modern firearm. Futuristic firearms use **Energy Cells** that become depleted but could possibly be recharged with the proper equipment, at your discretion. An **Energy Cell weighs 1/2 lb.**

#### Firearms — Modern *(p. 44)*

> The table is split into a "Modern" and a "Futuristic" half in the source, each with the header `Item | Damage | Properties | Mastery | Weight` and the sub-label **Martial Ranged Weapons**. Damage and damage type arrived as separate lines in the extraction and are merged into one cell here.

| Item | Damage | Properties | Mastery | Weight |
|---|---|---|---|---|
| Automatic Rifle | 2d8 Piercing | Ammunition (Range 80/240; Bullet), Burst Fire, Reload (30 shots), Two-Handed | Slow | 8 lb. |
| Hunting Rifle | 2d10 Piercing | Ammunition (Range 80/240; Bullet), Reload (5 shots), Two-Handed | Slow | 8 lb. |
| Revolver | 2d8 Piercing | Ammunition (Range 40/120; Bullet), Reload (6 shots) | Sap | 3 lb. |
| Semiautomatic Pistol | 2d6 Piercing | Ammunition (Range 50/150; Bullet), Reload (15 shots) | Vex | 3 lb. |
| Shotgun | 2d8 Piercing | Ammunition (Range 30/90; Bullet), Reload (2 shots), Two-Handed | Push | 7 lb. |

*What it is for: not a roll — item stat lines for modern firearms; damage dice and shot counts drive combat, not a table lookup.*

#### Firearms — Futuristic *(p. 44–45)*

| Item | Damage | Properties | Mastery | Weight |
|---|---|---|---|---|
| Antimatter Rifle | 6d8 Necrotic | Ammunition (Range 120/360; Energy Cell), Reload (2 shots), Two-Handed | Sap | 10 lb. |
| Laser Pistol | 3d6 Radiant | Ammunition (Range 40/120; Energy Cell), Reload (50 shots) | Vex | 2 lb. |
| Laser Rifle | 3d8 Radiant | Ammunition (Range 100/300; Energy Cell), Reload (30 shots), Two-Handed | Slow | 7 lb. |

*What it is for: not a roll — item stat lines for futuristic firearms; Energy Cell ammunition reuses the same recharge-at-your-discretion rule as above.*

#### Explosives *(p. 45)*

> The header row sits on p. 45 in the source. "If no cost is given for an explosive, it can't typically be bought." If made available for purchase, treat all explosives as **Rare** magic items.

| Item | Cost | Weight |
|---|---|---|
| Bomb | 100 GP | 1 lb. |
| Dynamite Stick | — | 1 lb. |
| Grenade, Fragmentation | — | 1 lb. |
| Grenade Launcher | — | 7 lb. |
| Grenade, Smoke | 50 GP | 2 lb. |
| Gunpowder (keg) | 250 GP | 20 lb. |
| Gunpowder (powder horn) | 35 GP | 2 lb. |

*What it is for: not a roll — price and weight for explosives; a dash in Cost means no typical purchase price exists in the fiction.*

**Bomb.** As an Action, light it and throw it at a point up to **60 feet** away, where it explodes. Each creature in a **5-foot-radius Sphere** centered on that point makes a **DC 12 Dexterity** saving throw, taking **3d6 Fire** damage on a failure or half on a success.

**Dynamite Stick.** As an Action, light it and throw it up to **60 feet**; each creature in a 5-foot-radius Sphere makes a **DC 12 Dexterity** saving throw, taking **3d6 Force** damage on a failure or half on a success.
- Binding **two or more** sticks so they explode simultaneously takes **1 minute**. Each stick after the first adds **1d6** damage (max **10d6**) and adds **5 feet** to the radius (max **20 feet**).
- Rigging a longer fuse (e.g. 1 minute or 10 minutes) takes **1 minute**.

**Grenades and Grenade Launcher.** As an Action, either throw a grenade up to **60 feet** or use a Grenade Launcher to reach a point up to **1,000 feet** away. The grenade explodes there, creating its effect in a **20-foot-radius Sphere**.
- *Fragmentation Grenade* — each creature in the Sphere makes a **DC 15 Dexterity** saving throw, taking **17 (5d6) Piercing** damage on a failure or half on a success.
- *Smoke Grenade* — the Sphere is **Heavily Obscured** by smoke for **1 minute**; a strong wind (e.g. **Gust of Wind**) disperses it.

**Gunpowder.** Setting fire to a container of gunpowder causes it to explode. Each creature in a **10-foot-radius Sphere** centered on the container makes a **DC 12 Dexterity** saving throw, taking **10 (3d6) Fire** damage (powder horn) or **24 (7d6) Fire** damage (keg) on a failure or half on a success.

**Alien Technology** *(p. 46)*. Adventurers deduce what a non-native/non-current technology is with a successful **Intelligence (Investigation)** check, DC by complexity: **DC 10** for a relatively simple item like a calculator or a lighter; **DC 20** for a complex item such as a computer, chainsaw, or hovercraft. You may require a separate Intelligence (Investigation) check to determine whether a character can activate or operate it; a character who has observed the item in use, or has operated a similar item, either has **Advantage** on that check or succeeds automatically (your choice).

---

### Gods and Other Powers *(p. 46–50)*

Different deities rule various aspects of the cosmos and mortal life, sometimes cooperating, sometimes competing. People gather in public shrines for gods of life and wisdom, or meet in hidden places to venerate gods of deception or destruction.

**Divine rank** — the divine beings of the multiverse are categorized by relative cosmic power; a god worshipped on multiple worlds may have a different rank on each depending on local influence.
- **Greater deities** — oldest of a pantheon, responsible (at least in myth) for creating or parenting the other gods. Provinces are major areas of nature and mortal life (agriculture, the sun, death). Ultimately beyond mortal understanding, known by different names across regions, cultures and worlds, with no fixed appearance or gender, able to assume any form. Occasionally manifest and perform mythic deeds among mortals.
- **Lesser deities** — described in myth as creations, children, or servitors of the greater deities. Govern narrower provinces (activities of mortal life, limited aspects of the natural world). Equally ineffable, but more likely to manifest in mortal realms.
- **Quasi-deities** — divine origin, but they don't receive or answer prayers. Still immensely powerful, and could in theory ascend to godhood by amassing worshipers. Three subcategories:
  - **Demigods** — divine beings of mortal origin: born mortal and attained godhood, or born from the union of a deity and a mortal. Mortal parentage makes them demigods.
  - **Titans** — creations of deities: manufactured on a divine forge, born from blood spilled by a god, or otherwise brought about through divine will or substance. Some (krakens, the tarrasque) appear in the Monster Manual.
  - **Vestiges** — deities who have lost nearly all worshipers and are considered dead from a mortal perspective. Esoteric rituals can sometimes contact vestiges and draw on their latent power.

**Home plane and alignment.** Gods aren't defined by mortal conceptions of alignment, and different worshipers may read the same behavior through different lenses. Gods do tend to live on the Outer Planes that most closely match their general tendencies, so it's safe to assume that teachings of a god residing in Pandemonium encourage **Chaotic Evil** behavior, while one in Elysium encourages **Neutral Good** behavior. People can worship a god without obeying its tenets or conforming to its presumed alignment (even Cleric characters need no particular alignment to serve their gods).

**Gods and divine magic.** Divine magic — the spells of Clerics, Druids, Paladins and Rangers — is mediated through beings and forces categorized as divine: gods, primal forces of nature, ancestral spirits, a Paladin's oath, or impersonal principles like Fate or the order of the universe. Wielding divine power isn't dependent on the gods' ongoing approval or the strength of a character's devotion; once given it can't be rescinded. But the *relationships* are worth exploring, like Warlocks' relationships with their patrons — a Cleric accompanying every casting with a litany of complaints; a Paladin who has broken their oath; NPCs reacting to a character's Holy Symbol.

**Divine knowledge.** **Commune** lets its caster ask a deity (or an agent) yes-or-no questions and receive correct information; other Divination spells do similar. Gods aren't necessarily omniscient but are tremendously knowledgeable about their areas of influence (a sea god knows anything that happened in or on a sea; a martial god knows details about wars). Gods can reliably predict the future in the short term (hence **Augury** and **Divination**), and some may be unwilling to reveal ignorance, giving an unclear answer rather than admit they don't know.

**Divine intervention** — gods may meddle, send dreams, omens, or emissaries. Two principles:
- **Don't eliminate character choice.** Gods can tell characters to do things and threaten punishment, but can't control mortal actions.
- **Don't eliminate risk and danger.** Intervention should never guarantee success or victory, nor portend immediate defeat. Gods can change the balance of an encounter or offer an avenue of escape, but they count on mortal heroes to act like heroes.

Three forms given:
- **Blessings** — a god bestows a Blessing (see "Supernatural Gifts") to help a character in need.
- **Emissaries** — a god sends a Celestial, a Fiend, or another kind of emissary to aid a character with information, guidance, or combat.
- **Miracles** — simplest form: a god can produce the effect of any spell that devotees of that god might cast (typically Cleric or Druid spells). Direct intervention can take any form, often reflecting the god's nature.

**Creating religions** *(p. 49–50)*. A list of gods can get a campaign started; fleshing out belief and practice adds depth.
- **Myths** — stories about the gods' relationships with each other, with the natural world, and with the realm of mortals: familial relationships, deeds of creation, past interactions with mortals, battles with other cosmic forces. Given the incomprehensible nature of the gods, myths may reveal nothing about the gods — but they describe people's understanding of their own place in relation to the gods.
- **Religious practice** — people honor multiple gods of a pantheon in different circumstances (burn incense to a hearth or family deity at a kitchen altar in the morning; pray to a deity of the hunt while hunting in the afternoon; join a communal harvest feast at the temple of an agricultural deity in the evening). Cities and large towns host numerous temples dedicated to individual gods important to the community; smaller settlements have a single shrine devoted to any gods the locals revere. Temples and shrines outside settlements often mark places where a god (or its manifestation) appeared or caused a miracle; these become focal points for pilgrims who travel long distances to partake of the holy power assumed to linger there.

---

### Hazards *(p. 50–58)*

The PHB describes common hazards (falling, dehydration). These are the more unusual ones you can add to a location.

**Severity and level.** Each hazard is designated a **nuisance** or **deadly** hazard for characters of certain levels. A nuisance hazard is unlikely to seriously harm characters of the indicated levels; a deadly hazard can grievously damage them. Use caution introducing a hazard to characters of a *lower* level than its range — a nuisance at one band can be deadly in the next-lower band. Hazards are presented in alphabetical order.

#### Hazard severity bands *(compiled from the twelve tags below; not a separate source table)*

| Hazard | Level 1–4 | Level 5–10 | Level 11–16 | Level 17–20 |
|---|---|---|---|---|
| Brown Mold | — | Deadly | Nuisance | — |
| Fireball Fungus | — | Deadly | Deadly* | Deadly* |
| Green Slime | Nuisance | — | — | — |
| Inferno | — | Deadly | Nuisance | — |
| Poisonous Gas | Nuisance | Nuisance* | Nuisance* | Nuisance* |
| Quicksand Pit | Nuisance | Nuisance* | Nuisance* | Nuisance* |
| Razorvine | Nuisance | — | — | — |
| River Styx | — | — | Nuisance | — |
| Rockslide | Deadly | Deadly* | Deadly* | Deadly* |
| Vicious Vine | Nuisance | Nuisance* | Nuisance* | Nuisance* |
| Webs | Nuisance | — | — | — |
| Yellow Mold | Deadly | Nuisance | — | — |

\* These bands come from each hazard's own "At Higher Levels" scaling text or table rather than from an explicit severity tag.

#### The twelve example hazards

**Brown Mold** — *Deadly Hazard (Levels 5–10) or Nuisance Hazard (Levels 11–16)*. Resembles a furry, light-brown carpet; a fungus that feeds on warmth, drawing heat from anything around itself. One patch covers a **10-foot square**; the temperature within **30 feet** is always frigid. When a creature enters a space within **5 feet** of the mold for the first time on a turn, or starts its turn there, it makes a **DC 12 Constitution** saving throw, taking **22 (4d10) Cold** damage on a failure or half on a success. The mold has **Immunity to Fire** damage, and any source of fire brought within **5 feet** causes it to instantly expand across a surface and toward the fire, creating a new **10-foot-square** patch. A patch exposed to any amount of **Cold** damage is destroyed instantly.

**Fireball Fungus** — *Deadly Hazard (Levels 5–10)*. A Small, inanimate mushroom that can grow anywhere fungi are abundant. Its luminous orange cap sheds **Bright Light in a 15-foot radius** and **Dim Light** for an additional 15 feet. It has **AC 10, HP 6**, and **Immunity to Psychic** damage. At **0 HP** it explodes as if a **Fireball** spell (**save DC 15**) had been centered on it. *At Higher Levels:* the explosion causes other fireball fungi in the area of effect to explode as well; scale by **adding one additional fungus at levels 11–16** or **three additional fungi at levels 17–20**.

**Green Slime** — *Nuisance Hazard (Levels 1–4)*. Devours flesh, organic material, and metal on contact; bright green, wet, sticky, clinging to walls, floors and ceilings in patches. One patch covers a **5-foot square**. It has **Blindsight 30 feet** and drops from walls and ceilings when it detects movement below itself; beyond that it can't move. A creature aware of the slime's presence can avoid being struck with a successful **DC 10 Dexterity** saving throw. A creature that comes into contact takes **5 (1d10) Acid** damage, repeated **at the start of each of its turns** until the slime is scraped off (requires an action) or destroyed. Against wood or metal it deals **11 (2d10) Acid** damage each round, and any nonmagical wood or metal item used to scrape it off is destroyed. **Direct sunlight** or any amount of **Cold, Fire, or Radiant** damage destroys a patch.

**Inferno** — *Deadly Hazard (Levels 5–10) or Nuisance Hazard (Levels 11–16)*. Created when uncontrolled fire spreads. An inferno consists of **at least four contiguous 10-foot Cubes of fire**. Each cube can be doused with **10 gallons of water**. Exposure to a **strong wind for 1 minute** grows it, adding **1d4** new 10-foot Cubes. An inferno deprived of fuel burns itself out after **1d10 minutes**. It damages any vegetation or object that isn't being worn or carried and that it touches, dealing **22 (4d10) Fire** damage immediately and again **at the end of each minute**. Any creature that enters the inferno for the first time on a turn, or starts its turn there, takes **22 (4d10) Fire** damage and is burning.

**Poisonous Gas** — *Nuisance Hazard (Levels 1–4)*. Usually encountered in an enclosed space such as a sewer or sealed tomb. The gas fills as much space as it can, up to a maximum of **ten 10-foot Cubes**, and carries a foul odor. It is continuously or periodically replenished by some natural or magical source, though a **strong wind disperses it for 1 minute**. Any creature that enters the gas for the first time on a turn, or starts its turn there, makes a **DC 12 Constitution** saving throw, taking **5 (1d10) Poison** damage on a failure or half on a success. Creatures in the gas also have **Disadvantage on Death Saving Throws**.

#### Poisonous Gas — At Higher Levels *(p. 54)*

| Levels | Poison Damage | Save DC |
|---|---|---|
| 5–10 | 11 (2d10) | 14 |
| 11–16 | 22 (4d10) | 16 |
| 17–20 | 55 (10d10) | 18 |

*What it is for: level scaling for the Poisonous Gas hazard — increases both the damage dice and the Constitution save DC.*

**Quicksand Pit** — *Nuisance Hazard (Levels 1–4)*. **10 feet deep**, covering a **10-foot square**. A creature that enters sinks **1d4 + 1 feet** and has the **Restrained** condition; at the start of each of its turns it sinks another **1d4 feet**. As long as it isn't completely submerged, it can take an action to try to escape with a successful **Strength (Athletics)** check, **DC 10 plus the number of feet it has sunk**. A completely submerged creature has **Total Cover**, the **Blinded** condition, and risks suffocation. One creature can pull another within reach out by taking an action and succeeding on a **Strength (Athletics)** check, **DC 5 plus the number of feet the sunken creature has sunk**.

#### Quicksand Pit — At Higher Levels *(p. 54–55)*

| Levels | Pit Depth | Sinking Rate |
|---|---|---|
| 5–10 | 15 feet | 1d6 feet |
| 11–16 | 20 feet | 1d8 feet |
| 17–20 | 30 feet | 1d10 feet |

*What it is for: level scaling for the Quicksand Pit — increases pit depth and per-turn sinking rate (the escape DC follows the sunk depth).*

**Razorvine** — *Nuisance Hazard (Levels 1–4)*. A plant growing in wild tangles and hedges that also clings to buildings and other surfaces like ivy. A **10-foot-high, 10-foot-wide, 5-foot-thick** wall or hedge has **AC 11; HP 25;** and **Immunity to Bludgeoning, Piercing, and Psychic** damage. On contact for the first time on a turn, a creature must succeed on a **DC 10 Dexterity** saving throw or take **5 (1d10) Slashing** damage from the bladelike thorns.

**River Styx** — *Nuisance Hazard (Levels 11–16)*. Courses through the Lower Planes; tasting or touching its waters shatters intellect and personality and strips away memories. Certain **Fiends** are immune. Unless immune, a creature that drinks from the Styx, enters the river, or starts its turn in the river makes a **DC 20 Intelligence** saving throw. On a failure it takes **19 (3d12) Psychic** damage and **can't cast spells or take the Magic action for 30 days**; it can then drink and swim in the river without further effect. Ended only by **Greater Restoration**, **Heal**, or **Wish**. If not ended after **30 days** the effect becomes permanent and the creature loses all memories; only a **Wish** or divine intervention can undo that. Water taken from the river loses potency after **24 hours**, becoming a harmless foul-tasting liquid (fell creatures may know rituals to prolong it, at your discretion).

**Rockslide** — *Deadly Hazard (Levels 1–4)*. Every creature in its path makes a **DC 15 Dexterity** saving throw. Failure: **11 (2d10) Bludgeoning** damage, the **Prone** condition, and the creature moves with the rockslide. Success: half damage only. When the rockslide stops its space becomes **Difficult Terrain** and all Prone creatures in it are buried under rocks and debris — a buried creature has the **Restrained** condition and **Total Cover**. As an action, a buried creature can try to crawl out with a **DC 15 Strength (Athletics)** check: success ends Restrained but leaves it **Prone** atop the pile; failure means it remains buried and gains **1 Exhaustion** level. A creature with neither **Incapacitated** nor **Restrained** can spend **1 minute** freeing another buried creature. *At Higher Levels:* increase the Bludgeoning damage to **22 (4d10)** at levels 5–10, **55 (10d10)** at levels 11–16, and **99 (18d10)** at levels 17–20.

**Vicious Vine** — *Nuisance Hazard (Levels 1–4)*. Animated by magic; often clings to doorways, archways, walls and statuary, and until it moves there's nothing to distinguish it from an inanimate vine. Each vine has **AC 11; HP 16;** and **Immunity to Bludgeoning, Piercing, and Psychic** damage. When a creature enters a space within **5 feet** of the vine for the first time on a turn, or starts its turn there, the vine tries to coil around it. The target must succeed on a **DC 12 Dexterity** saving throw or have the **Grappled** condition (**escape DC 12**). While Grappled, the target takes **5 (1d10) Necrotic** damage from the vine's life-draining thorns at the start of each of its turns. **The vine can grapple only one creature at a time.** As an **Influence** action, a character under **Speak with Plants** or similar magic can try to persuade the vine to release its victim with a successful **DC 10 Charisma (Persuasion)** check; a creature released that way won't be attacked by that vine again for **24 hours**.

#### Vicious Vine — At Higher Levels *(p. 57)*

| Levels | Necrotic Damage | Save/Escape DC |
|---|---|---|
| 5–10 | 11 (2d10) | 14 |
| 11–16 | 22 (4d10) | 16 |
| 17–20 | 55 (10d10) | 18 |

*What it is for: level scaling for the Vicious Vine — one column raises both the grapple save DC and the escape DC.*

**Webs** — *Nuisance Hazard (Levels 1–4)*. Giant spiders weave thick, sticky webs across passages and at the bottom of pits to snare prey. Web-filled areas are **Difficult Terrain**. A creature entering a web-filled area for the first time on a turn, or starting its turn there, must succeed on a **DC 12 Dexterity** saving throw or have the **Restrained** condition. As an action, a Restrained creature can try to escape with a successful **DC 12 Strength (Athletics) or Dexterity (Acrobatics)** check. Each **10-foot Cube** of webs has **AC 10; HP 15; Vulnerability to Fire** damage; and **Immunity to Piercing, Poison, and Psychic** damage.

**Yellow Mold** — *Deadly Hazard (Levels 1–4) or Nuisance Hazard (Levels 5–10)*. Grows in dark places; one patch covers a **5-foot square**. If touched, the mold ejects a cloud of spores filling a **10-foot Cube**. Any creature in that area must succeed on a **DC 15 Constitution** saving throw or take **11 (2d10) Poison** damage and have the **Poisoned** condition for **1 minute**. While Poisoned this way the creature takes **5 (1d10) Poison** damage at the start of each of its turns. It repeats the save at the end of each of its turns, ending the effect on a success. **Direct sunlight** or any amount of **Fire** damage destroys a patch.

---

### Marks of Prestige *(p. 58–62)*

Sometimes the most memorable reward is prestige: fame and power, allies and enemies, and titles passed to descendants. The best rewards relate directly to the circumstances of the adventure (a merchant whose family heirloom is recovered might give the deed to the tower).

- **Fortifications** — a reward usually to seasoned adventurers showing unwavering fealty to a monarch, knighthood, or council of wizards; anything from a city fortress to a provincial keep. Governed as the characters see fit, but the **land remains the property of the crown or local ruler**, who can ask or force them to relinquish it. Distinct from **Bastions** (ch. 8), though the gift can be a pretext for acquiring a Bastion. The grantor may pay maintenance for one or more months, after which that responsibility becomes the characters'.
- **Letters of Recommendation** — from a person of impeccable reputation, granting access to NPCs they'd otherwise have trouble meeting (a duke, duchess, viceroy, monarch) and establishing a baseline of trust with local authorities. Worth only as much as the writer's reputation; no benefit where the writer holds no sway.
- **Medals** — usually gold and precious materials, but with greater symbolic value. Awarded by political figures for acts of heroism; wearing one is usually enough to earn the respect of those who understand its significance (e.g. the **Royal Badge of Valor** of Breland, shaped like a shield in ruby and electrum, for defending Brelish citizens; the **Golden Bear of Breland**, gold in the shape of a bear's head with gems for eyes, reserved for proven allegiance to the Bre Crown). A medal offers no specific in-game benefit but can affect dealings with NPCs — inside the kingdom it reads as hero of the people, outside it carries little weight except among the king's allies.
- **Parcels of Land** — come with a letter from a local ruler affirming the grant. The land usually remains the property of the local ruler or ruling body but is lent to the character, understanding it can be taken away if loyalty is questioned. Recipients are free to build and are expected to safeguard it; they may yield it as part of an inheritance but **cannot sell or trade it** without permission. Makes a fine reward for characters seeking a place to settle or with family in the region.
- **Special Favors** — a favor the characters can call on at a future date. Work best when the granter is trustworthy, and alignment predicts behavior: a **Lawful Good or Lawful Neutral** NPC will do whatever can be done to fulfill an obligation, short of breaking laws; a **Lawful Evil** NPC does the same but only because a deal is a deal; a **Neutral Good or Neutral** NPC might pay off favors to protect their reputation; a **Chaotic Good** NPC focuses on doing right, honoring obligations without worrying about personal risk or adherence to the law.
- **Special Rights** — articulated in an official document or proclamation: rights to attack pirate ships or other enemies of the crown, to lead rites or ceremonies, to negotiate on a ruler's behalf, a lifetime of free room and board from grateful citizens, or the sworn service of local soldiers. They last only as long as the document dictates and can be revoked if abused.
- **Titles** — a politically powerful figure dispenses them, often with a parcel of land (Earl of Stormriver, Countess of Dun Fjord). Archfey favor whimsical alliterative titles (Chancellor of Chocolates, Grand Duke of Giggles), which might come with minor supernatural gifts rather than land. A character can hold more than one title; in a feudal society they can be passed to or distributed among children. The holder is expected to act befittingly, and titles can be stripped by decree for failing the associated obligations.
- **Training** — not widely available, so highly desirable. The character must spend **30 days** with the trainer to receive a special benefit. Possible benefits: proficiency in a skill; proficiency with a tool; a language.

#### Maintenance Costs *(p. 59–60)*

> Caption on p. 59, header row repeated and rows on p. 60; reconstructed as one table.

| Fortification | Cost per Day |
|---|---|
| Fortified outpost or watchtower | 50 GP |
| Keep or small castle | 100 GP |
| Large castle or fortress | 400 GP |

*What it is for: not a roll — daily upkeep in GP for a gifted fortification, by fortification type.*

---

### Mobs *(p. 62–66)*

For resolving outcomes with large groups of monsters.

**Tips.**
- **Damage** — use the **average damage** specified in a monster's stat block.
- **Hit Points** — if a spell or attack reduces a monster to a handful of Hit Points, assume it's killed or otherwise out of the fight.
- **Monster Mobs** — divide a large number of identical monsters into smaller mobs and spread their turns between the characters' turns. **Mobs of five to eight identical creatures work well, but don't have more mobs than there are characters.**

#### Mob Results *(p. 64)*

Use instead of making a number of D20 Tests for identical monsters.

- **Step 1** — determine the minimum d20 roll needed: **`Roll needed = target number − monster's bonus`**.
- **Step 2** — find that roll in the table. If **all** monsters have **Advantage** (e.g. attacking with Pack Tactics, or saving against a spell with Magic Resistance), use the **With Advantage** column. If **all** have **Disadvantage** (e.g. attacking into **Blur**), use the **With Disadvantage** column. Otherwise use **Normal**.
- **Step 3** — read across to a fractional number of successes that is easy to apply to the group; that fraction of the monsters succeed on the D20 Test.

> Two-tier header in the source: a top band spanning **Roll Needed** (3 columns) and **Number of Successes** (4 columns). Reconstructed as a single flat header below; the "Roll needed" formula is `target number − monster's bonus`, and the fraction columns express *successes / monsters present*.

| Roll Needed: Normal | Roll Needed: With Advantage | Roll Needed: With Disadvantage | Number of Successes: Out of 4 | Out of 5 | Out of 6 | Out of 8 |
|---|---|---|---|---|---|---|
| 1 | 1–4 | 1 | 4/4 | 5/5 | 6/6 | 8/8 |
| 2 | 5–6 | — | 4/4 | 5/5 | 6/6 | 8/8 |
| 3 | 7–8 | 2 | 4/4 | 5/5 | 5/6 | 7/8 |
| 4 | 9 | — | 3/4 | 4/5 | 5/6 | 7/8 |
| 5 | 10 | 3 | 3/4 | 4/5 | 5/6 | 6/8 |
| 6 | 11 | — | 3/4 | 4/5 | 5/6 | 6/8 |
| 7 | 12 | 4 | 3/4 | 4/5 | 4/6 | 6/8 |
| 8 | 13 | 5 | 3/4 | 3/5 | 4/6 | 5/8 |
| 9 | 14 | — | 2/4 | 3/5 | 4/6 | 5/8 |
| 10 | — | 6 | 2/4 | 3/5 | 3/6 | 4/8 |
| 11 | 15 | 7 | 2/4 | 3/5 | 3/6 | 4/8 |
| 12 | 16 | — | 2/4 | 2/5 | 3/6 | 4/8 |
| 13 | — | 8 | 2/4 | 2/5 | 2/6 | 3/8 |
| 14 | 17 | 9 | 1/4 | 2/5 | 2/6 | 3/8 |
| 15 | 18 | 10 | 1/4 | 2/5 | 2/6 | 2/8 |
| 16 | — | 11 | 1/4 | 1/5 | 2/6 | 2/8 |
| 17 | 19 | 12 | 1/4 | 1/5 | 1/6 | 2/8 |
| 18 | — | 13 | 1/4 | 1/5 | 1/6 | 1/8 |
| 19 | 20 | 14–15 | 0 | 1/5 | 1/6 | 1/8 |
| 20 | — | 16–17 | 0 | 0 | 0 | 0 |

*What it is for: convert one d20 test into a success *fraction* for a homogeneous group, so a mob of N identical monsters needs one roll, not N. Column choice is driven by whether the whole group has Advantage or Disadvantage.*

#### Adjudicating Areas of Effect *(p. 65–66)*

When fighting many monsters, miniatures on a battle grid aren't always practical. To estimate how many monsters a **Fireball** or other area of effect catches: find the column for the **shape** of the area, read down to its **size**, then check the rightmost column for about how many creatures are caught. If you imagine the targets are **spread out**, **decrease the number by 1d3**; if they are **bunched up**, **increase it by 1d3**. An area can't encompass more creatures than are present. Judgment always outweighs these guidelines, and it's fine to err toward affecting more creatures — eight zombies crowded around a Fighter engulfed by a **Shatter** centered on the Fighter, even though a 10-foot-radius Sphere nominally includes only three creatures.

#### Targets in Area of Effect *(p. 65–66)*

> Two-tier header in the source: a top band spanning **Area Shape and Size** (4 columns) and a single **Number of Targets** column. The footnote `*Use this column for Cylinders, Emanations (using the size of the Emanation rather than its radius), and Spheres.` is repeated on both pages. A dash (—) means the shape has no entry at that size. The table deliberately skips a "7" target row (6 → 8).

| Cone | Cube | Circular* | Line | Number of Targets |
|---|---|---|---|---|
| 10-foot | 5- to 10-foot | 5-foot-radius | — | 1 |
| 15- to 20-foot | 15-foot | — | 30-foot-long, 5-foot-wide | 2 |
| 25-foot | — | 10-foot-radius | 30-foot-long, 10-foot-wide or 60-foot-long, 5-foot-wide | 3 |
| — | 20-foot | — | 90- or 100-foot-long, 5-foot-wide | 4 |
| 30-foot | — | — | 60-foot-long, 10-foot-wide or 120-foot-long, 5-foot-wide | 5 |
| 35-foot | 25-foot | 15-foot-radius | — | 6 |
| 40-foot | 30-foot | — | 90- or 100-foot-long, 10-foot-wide | 8 |
| 45-foot | — | — | — | 9 |
| 50-foot | 35-foot | 20-foot-radius | 120-foot-long, 10-foot-wide | 10 |
| 55-foot | 40-foot | — | — | 12 |
| 60-foot | 45-foot | 25-foot-radius | — | 16 |
| — | 50-foot | 30-foot-radius | — | 20 |

\* Use this column for **Cylinders, Emanations** (using the size of the Emanation rather than its radius), and **Spheres**.

*What it is for: not a roll — an approximate creature count for each area shape/size, so a spell covering a crowd doesn't require enumerating occupants. Adjust ±1d3 for spread vs. bunching.*

#### Worked examples *(p. 66)*

- **Zombie melee.** Eight Zombies attack a Fighter. Zombie attack bonus **+3**, Fighter's AC **18**, so **roll needed = 15** (18 − 3). Row 15 in **Normal** → **Out of 8** gives **2/8** — two zombies hit. At average damage **4 Bludgeoning**, the Fighter takes **8 Bludgeoning**.
- **Shatter.** The Bard centers a 10-foot-radius Sphere on the Fighter (trusting them to pass the Constitution save). The table suggests **three** zombies; the DM rules **all eight** (and the Fighter) are affected. Zombie Constitution save bonus **+3**, Bard's spell save DC **16**, so **roll needed = 13** (16 − 3). Row 13 in **Normal** → **Out of 8** gives **3/8**, so three zombies succeed on their saves.
- **Fireball.** The Wizard's 20-foot-radius Sphere. The table suggests **ten** zombies; the DM rules they're densely packed and adds **1d3**, rolling a **2**, so the spell engulfs **twelve** zombies. Zombie Dexterity modifier **−2**, spell save DC **16**, so **roll needed = 18** (16 − [−2]). Row 18 in **Normal** → **Out of 6** gives **1/6**; twelve times 1/6 = **2**, so two of the twelve succeed on the save.

---

### Nonplayer Characters *(p. 66–79)*

NPCs are supporting characters you control — the local innkeeper, the sage in the tower on the outskirts of town, the death knight out to destroy the kingdom. Monster Manual stat blocks can represent them, with distinctive details added (a no-nonsense blacksmith with a black-rose tattoo on her right shoulder; a badly dressed musician with a broken nose). They rarely need much more complexity.

#### Detailed NPCs — the six elements *(p. 67–76)*

Flesh out NPCs with prominent roles, recording them on the **NPC Tracker** (form on p. 67; no body text in this extraction). The six elements:

1. **Name** — pick a given name and a surname from any of the six accompanying tables; a name can mix tables from different sets. If you'd rather roll, roll **1d6** to pick the table, then **1d12** for the name. You can also alter or combine names, pull from a book of names, or use one inspired by a movie or book.
2. **Stat Block** — choose a Monster Manual stat block to represent the NPC's game statistics. Skip this if the NPC won't fight or use special abilities such as spellcasting. Customize it using "Creating a Creature" above.
3. **Alignment** — choose the NPC's alignment to sketch the outlines of behavior and personality.
4. **Personality** — with alignment and ability scores as a starting point, use PHB guidelines to pick a few words. Choose or randomly determine one personality trait associated with each element of the NPC's alignment, or with the NPC's **highest** and **lowest** ability scores, and combine them. Example: a **Lawful Neutral** guard the adventurers unexpectedly argue with → cooperative but laconic, happy to help but speaking curtly to end the conversation fast. Example: the **Imp** in the PHB has highest **Dexterity**, lowest **Strength** → fidgety and indirect, constantly on the move, talking in circles to reach its point.
5. **Appearance** — briefly describe the most distinctive physical features, starting with the basics (skin, hair, eye colors, species). The NPC Appearance table helps pick one or two things that stand out.
6. **Secret** — a secret the NPC is trying to hide or protect. The NPC Secrets table provides ideas.

#### 1: Common Names *(p. 68)*

| 1d12 | Common Given Name | Common Surname |
|---|---|---|
| 1 | Adrik | Brightsun |
| 2 | Alvyn | Dundragon |
| 3 | Aurora | Frostbeard |
| 4 | Eldeth | Garrick |
| 5 | Eldon | Goodbarrel |
| 6 | Farris | Greycastle |
| 7 | Kathra | Ironfist |
| 8 | Kellen | Jaerin |
| 9 | Lily | Merryweather |
| 10 | Nissa | Redthorn |
| 11 | Xinli | Stormriver |
| 12 | Zorra | Wren |

*What it is for: roll 1d6 to choose a name table, then 1d12 for given name and surname. Purely generative, no mechanical effect.*

#### 2: Guttural Names *(p. 68–69)*

> Header on p. 68, rows 1–7 there and rows 8–12 on p. 69; reconstructed as one table.

| 1d12 | Guttural Given Name | Guttural Surname |
|---|---|---|
| 1 | Abzug | Burska |
| 2 | Bajok | Gruuthok |
| 3 | Bharash | Hrondl |
| 4 | Grovis | Jarzzok |
| 5 | Gruuna | Kraltus |
| 6 | Hokrun | Shamog |
| 7 | Mardred | Skrangval |
| 8 | Rhogar | Ungart |
| 9 | Skuldark | Uuthrakt |
| 10 | Thokk | Vrakir |
| 11 | Urzul | Yuldra |
| 12 | Varka | Zulrax |

*What it is for: 1d12 given name + 1d12 surname from the "guttural" register; generative only.*

#### 3: Lyrical Names *(p. 69)*

| 1d12 | Lyrical Given Name | Lyrical Surname |
|---|---|---|
| 1 | Arannis | Arvannis |
| 2 | Damaia | Brawnanvil |
| 3 | Darsis | Daardendrian |
| 4 | Dweomer | Drachedandion |
| 5 | Evabeth | Endryss |
| 6 | Jhessail | Meliamne |
| 7 | Keyleth | Mishann |
| 8 | Netheria | Silverfrond |
| 9 | Orianna | Snowmantle |
| 10 | Sorcyl | Summerbreeze |
| 11 | Umarion | Thunderfoot |
| 12 | Velissa | Zashir |

*What it is for: 1d12 given name + 1d12 surname from the "lyrical" register; generative only.*

#### 4: Monosyllabic Names *(p. 69–70)*

> Rows 1–2 on p. 69, header repeated and rows 3–12 on p. 70; reconstructed as one table.

| 1d12 | Monosyllabic Given Name | Monosyllabic Surname |
|---|---|---|
| 1 | Chen | Dench |
| 2 | Creel | Drog |
| 3 | Dain | Dusk |
| 4 | Dorn | Holg |
| 5 | Flint | Horn |
| 6 | Glim | Imsh |
| 7 | Henk | Jask |
| 8 | Krusk | Keth |
| 9 | Nox | Ku |
| 10 | Nyx | Kung |
| 11 | Rukh | Mott |
| 12 | Shan | Quaal |

*What it is for: 1d12 given name + 1d12 surname from the "monosyllabic" register; generative only.*

#### 5: Sinister Names *(p. 70)*

| 1d12 | Sinister Given Name | Sinister Surname |
|---|---|---|
| 1 | Arachne | Doomwhisper |
| 2 | Axyss | Dreadfield |
| 3 | Carrion | Gallows |
| 4 | Grinnus | Hellstryke |
| 5 | Melkhis | Killraven |
| 6 | Morthos | Nightblade |
| 7 | Nadir | Norixius |
| 8 | Scandal | Shadowfang |
| 9 | Skellendyre | Valtar |
| 10 | Thaltus | Winterspell |
| 11 | Valkora | Xandros |
| 12 | Vexander | Zarkynzorn |

*What it is for: 1d12 given name + 1d12 surname from the "sinister" register; generative only.*

#### 6: Whimsical Names *(p. 71)*

| 1d12 | Whimsical Given Name | Whimsical Surname |
|---|---|---|
| 1 | Cricket | Borogove |
| 2 | Daisy | Goldjoy |
| 3 | Dimble | Hoddypeak |
| 4 | Ellywick | Huddle |
| 5 | Erky | Jollywind |
| 6 | Fiddlestyx | Oneshoe |
| 7 | Fonkin | Scramblewise |
| 8 | Golly | Sunnyhill |
| 9 | Mimsy | Tallgrass |
| 10 | Pumpkin | Timbers |
| 11 | Quarrel | Underbough |
| 12 | Sybilwick | Wimbly |

*What it is for: 1d12 given name + 1d12 surname from the "whimsical" register; generative only.*

#### NPC Appearance *(p. 73)*

| 1d12 | Feature |
|---|---|
| 1 | Distinctive jewelry |
| 2 | Flamboyant, outlandish, formal, or ragged clothes |
| 3 | Uses an elegant mobility device (wheelchair, brace, or cane) |
| 4 | Pronounced scar |
| 5 | Unusual eye color (or two different colors) |
| 6 | Tattoos or piercings |
| 7 | Birthmark |
| 8 | Unusual hair color |
| 9 | Bald, or braided beard or hair |
| 10 | Distinctive nose (large, bulbous, angular, small) |
| 11 | Distinctive posture (stooped or rigid) |
| 12 | Exceptionally beautiful or ugly |

*What it is for: roll 1d12 to pick one or two memorable visual traits for a generated NPC; descriptive only.*

#### NPC Secrets *(p. 74)*

| 1d10 | Secret |
|---|---|
| 1 | The NPC is in disguise, concealing their identity or some aspect of their appearance. |
| 2 | The NPC is currently planning, executing, or covering up a crime. |
| 3 | The NPC (or their family) has been threatened with harm unless the NPC does something. |
| 4 | The NPC is under a magical compulsion (perhaps a **Geas** spell or some kind of curse) to behave in a certain way. |
| 5 | The NPC is seriously ill or in terrible pain. |
| 6 | The NPC feels responsible for someone's death or ill fortune. |
| 7 | The NPC is on the brink of financial ruin. |
| 8 | The NPC is desperately lonely or harboring an unrequited passion. |
| 9 | The NPC nurses a powerful ambition. |
| 10 | The NPC is deeply dissatisfied or unhappy. |

*What it is for: roll 1d10 to give a generated NPC a driving motive or hidden pressure; the hook a player can uncover.*

*(p. 75 is the NPC Tracker form — no body text in this extraction.)*

#### Recurring NPCs *(p. 76)*

NPCs who keep showing up build the sense that the world is alive. Use different stat blocks, perhaps with tweaks, to reflect the same NPC at different points in a campaign (a villain fought as a **Mage Apprentice** on the first adventure, who escapes and returns many adventures later as a **Mage**, and still later as an **Archmage**). The trick is making sure the villain survives from one adventure to the next, or devising a plausible return from death — death is rarely the final word for adventurers, so it needn't be for their opponents.

#### NPCs as Party Members *(p. 76–77)*

NPCs may join for a share of the loot and an equal share of the risk, or out of loyalty, gratitude, or love. Delegate an NPC's action decisions to a player, especially in combat, but override the player when the NPC's motivations require it. Choose a stat block whose **Challenge Rating is no higher than half the characters' level** so the NPC doesn't overshadow the players; these NPCs don't amass Experience Points and don't become more powerful.

Six archetypes that work well as supporting characters:
- **Comic Relief** — lightens the mood, perhaps through ineptness or a gift for puns.
- **Curmudgeon** — complains humorously about the characters' terrible choices and bad planning; can occasionally suggest legitimate courses of action or share insights.
- **Dutiful Assistant** — carries equipment, looks after horses and belongings; entirely devoted, or using the overlooked position to pursue personal goals.
- **Milquetoast Healer** — in the absence of a player healer, devotion and the ability to cast **Cure Wounds** or **Revivify** matter more than personality.
- **Walking Textbook** — knowledgeable about one field, a useful information source, but unreliable in decisions or combat.
- **Wallflower Warrior** — fades into the background, doesn't chat or engage unless approached, eagerly avoids the spotlight; its main purpose is to give monsters another target.

Useful NPCs can still slow the game or overstay their welcome — consider having them stick around for **no more than a few game sessions or a single adventure** before exiting. NPCs can benefit from time away from the characters.

#### Loyalty *(p. 78–79)*

An optional rule determining how far an NPC party member will go to protect or assist the characters, even those they don't particularly like. An abused or ignored NPC is likely to abandon or betray the party; one who owes a life debt or shares their goals might fight to the death. Decide an NPC's loyalty outright, or track a **Loyalty Score**:

- **Loyalty Score** — a numerical scale from **0 to 20**. The NPC's **maximum** Loyalty Score equals the **highest Charisma score among all adventurers in the party**; its **starting** score is **half** that number. If the highest Charisma score changes (a character dies or leaves), adjust accordingly.
- **Tracking Loyalty** — keep the score secret so players won't know for sure whether the NPC is loyal or disloyal.
- **Gains** — the score **increases by 1d4** if other party members help the NPC achieve a personal goal; also **+1d4** if the NPC is treated particularly well (e.g. given a magic weapon as a gift) or rescued by another party member. It can never exceed the maximum.
- **Losses** — **−1d4** when other party members act in a manner contrary to the NPC's alignment or personality; **−2d4** if the NPC is abused, misled, or endangered by other party members for purely selfish reasons. Never below **0**.
- **Meaning** — **10 or higher**: risks anything to help fellow party members. **1 to 10**: tenuously faithful. **0**: no longer acts in the party's best interests — leaves the party (attacking characters who try to intervene) or works in secret to bring about the party's downfall.
- **Crew Loyalty and Mutiny** — if the characters own or operate a sailing ship or similar vessel, track individual crew members or the crew as a whole. If **at least half the crew's Loyalty Scores drop to 0** during a voyage, the crew turns **Hostile** and stages a **mutiny**. If the ship is berthed, disloyal crew members leave the ship and never return.

---

### Poison *(p. 79–84)*

Poisons are a favorite tool among assassins and evil creatures. Four delivery types:

- **Contact** — smeared on an object; remains potent until touched or washed off. A creature that touches it with exposed skin suffers its effects.
- **Ingested** — the creature must swallow an entire dose, delivered in food or liquid. You may decide a partial dose has a reduced effect, such as **Advantage** on the saving throw or **half damage** on a failed save.
- **Inhaled** — powders and gases; blowing the powder or releasing the gas subjects creatures in a **5-foot Cube** to its effect, and the cloud dissipates immediately afterward. Holding your breath is ineffective, because inhaled poisons affect nasal membranes, tear ducts, and other parts of the body.
- **Injury** — applied as a **Bonus Action** to a weapon, a piece of ammunition, or similar object; remains potent until delivered through a wound or washed off. A creature taking **Piercing** or **Slashing** damage from a coated object is exposed.

**Purchasing poison.** In some settings laws prohibit possession and use, but an illicit dealer or unscrupulous apothecary might keep a hidden stash. Characters with criminal contacts may acquire poison easily; others need extensive inquiries and bribes.

**Harvesting poison.** A character can attempt to harvest poison from a venomous creature that is dead or **Incapacitated**. The effort takes **1d6 minutes**, after which the character makes a **DC 20 Intelligence (Nature)** check using a **Poisoner's Kit**. Success harvests enough poison for a single dose, and no additional poison can be harvested from that creature. Failure yields nothing; **failing by 5 or more** subjects the character to the creature's own poison.

#### Sample Poisons *(p. 81–84)*

> Presented alphabetically in the source as fourteen stat blocks (`Name (price)` / type line / effect text). Rendered here as a single table with the effect text kept verbatim; every poison, price, and type from the source is included.

| Poison | Price | Type | Effect |
|---|---|---|---|
| Assassin's Blood | 150 GP | Ingested Poison | A creature subjected to Assassin's Blood makes a **DC 10 Constitution** saving throw. On a failed save, the creature takes **6 (1d12) Poison** damage and has the **Poisoned** condition for **24 hours**. On a successful save, the creature takes half as much damage only. |
| Burnt Othur Fumes | 500 GP | Inhaled Poison | A creature subjected to Burnt Othur Fumes must succeed on a **DC 13 Constitution** saving throw or take **10 (3d6) Poison** damage, and it must repeat the save **at the start of each of its turns**. On each successive failed save, the creature takes **3 (1d6) Poison** damage. **After three successful saves, the poison ends.** |
| Carrion Crawler Mucus | 200 GP | Contact Poison | A creature subjected to Carrion Crawler Mucus must succeed on a **DC 13 Constitution** saving throw or have the **Poisoned** condition for **1 minute**. The creature also has the **Paralyzed** condition while Poisoned in this way. The creature repeats the save at the end of each of its turns, ending the effect on itself on a success. |
| Essence of Ether | 300 GP | Inhaled Poison | A creature subjected to Essence of Ether must succeed on a **DC 15 Constitution** saving throw or have the **Poisoned** condition for **8 hours**. The creature also has the **Unconscious** condition while Poisoned in this way. The creature wakes up if it takes damage or if another creature takes an action to shake it awake. |
| Lolth's Sting | 200 GP | Injury Poison | A creature subjected to Lolth's Sting must succeed on a **DC 13 Constitution** saving throw or have the **Poisoned** condition for **1 hour**. If the creature fails the save **by 5 or more**, the creature also has the **Unconscious** condition while Poisoned in this way. The creature wakes up if it takes damage or if another creature takes an action to shake it awake. |
| Malice | 250 GP | Inhaled Poison | A creature subjected to Malice must succeed on a **DC 15 Constitution** saving throw or have the **Poisoned** condition for **1 hour**. The creature also has the **Blinded** condition while Poisoned in this way. |
| Midnight Tears | 1,500 GP | Ingested Poison | A creature that ingests Midnight Tears suffers **no effect until the stroke of midnight**. Any effect that ends the **Poisoned** condition neutralizes this poison. If the poison hasn't been neutralized before midnight, the creature makes a **DC 17 Constitution** saving throw, taking **31 (9d6) Poison** damage on a failed save or half as much damage on a successful one. |
| Oil of Taggit | 400 GP | Contact Poison | A creature subjected to Oil of Taggit must succeed on a **DC 13 Constitution** saving throw or have the **Poisoned** condition for **24 hours**. The creature also has the **Unconscious** condition while Poisoned in this way. It wakes up if it takes damage. |
| Pale Tincture | 250 GP | Ingested Poison | A creature subjected to Pale Tincture must succeed on a **DC 16 Constitution** saving throw or take **3 (1d6) Poison** damage and have the **Poisoned** condition. The Poisoned creature repeats the save **every 24 hours**, taking **3 (1d6) Poison** damage on a failed save. **The damage the poison deals can't be healed by any means** while the creature remains Poisoned. **After seven successful saves** against the poison, the creature is no longer Poisoned. |
| Purple Worm Poison | 2,000 GP | Injury Poison | A creature subjected to Purple Worm Poison makes a **DC 21 Constitution** saving throw, taking **35 (10d6) Poison** damage on a failed save or half as much damage on a successful one. |
| Serpent Venom | 200 GP | Injury Poison | A creature subjected to Serpent Venom must succeed on a **DC 11 Constitution** saving throw, taking **10 (3d6) Poison** damage on a failed save or half as much damage on a successful one. |
| Torpor | 600 GP | Ingested Poison | A creature subjected to Torpor poison must succeed on a **DC 15 Constitution** saving throw or have the **Poisoned** condition for **4d6 hours**. The creature's **Speed is halved** while the creature is Poisoned in this way. |
| Truth Serum | 150 GP | Ingested Poison | A creature subjected to Truth Serum must succeed on a **DC 11 Constitution** saving throw or have the **Poisoned** condition for **1 hour**. The Poisoned creature **can't knowingly communicate a lie**. |
| Wyvern Poison | 1,200 GP | Injury Poison | A creature subjected to Wyvern Poison makes a **DC 14 Constitution** saving throw, taking **24 (7d6) Poison** damage on a failed save or half as much damage on a successful one. |

*What it is for: not a roll table — fourteen ready-made poisons, each with dose price, delivery type, save DC, damage dice, duration, and the secondary condition it imposes. The saving throw DCs (11, 13, 14, 15, 16, 17, 21) and the Poisoned-condition durations are the data a poison template would need.*

---

### Renown *(p. 84–86)*

An optional rule for tracking a character's or party's standing, individually or as a party, within a particular group — a faction, organization, or community. A Renown Score **starts at 0** and increases as characters earn favor and reputation. Benefits can be tied to renown, including ranks, titles, and access to resources. **Players track renown separately for each group** their characters are associated with (e.g. Renown 5 with one faction, Renown 20 with another). Renown can be used across an entire campaign (factions or guilds with ranks and rewards) or within a single adventure (e.g. the party needs a Renown Score of **5+** with a council before it shares resources).

**Gaining renown** *(at your discretion)*:
- **Completing Missions** — advancing a group's interests increases Renown within that group by **1**. Completing a mission specifically assigned by that group, or one that directly benefits the group, increases it by **2**. Hugely significant quests might grant increases of **3 or 4** at once.
- **Group Involvement** — once a character has Renown **1+** with a group, they can gain renown by spending time between adventures on minor tasks for the group and socializing with its members. After doing so for a number of days equal to **10 times the character's current Renown Score**, the score increases by **1**.

**Benefits of renown** *(guidelines)*:
- **Recognition** — at **Renown 3+** the character is a respected member; other members are **Friendly** toward them by default and provide lodging and food in dire circumstances.
- **Rank** — groups with hierarchies let characters ascend as Renown improves; others have positions of honor they can apply for at a high enough score. Set Renown thresholds as prerequisites (not necessarily the only ones) for advancing in rank, creating ranks and titles for your campaign's groups.
- **Perks** — at **3+**: access to a reliable contact, a safe house, or a discount on adventuring gear. At **10+**: access to **Potions and Scrolls**, the ability to call in a favor, or backup on dangerous missions. At **50**: call on a small army, acquire a **Rare** magic item, gain access to a helpful spellcaster, or assign special missions to members of lower status.

**Losing renown.** Disagreements aren't enough; **serious offenses** against the group or its members can result in loss of renown and rank, with the extent left to your discretion. A Renown Score can never drop below **0**.

**Level-based renown.** If you want the benefits without tracking scores, use the character's level as a shorthand for their Renown Score with a group, assuming the character has worked with or for that group for most of their career.

#### Level-Based Renown *(p. 86–87)*

> Header row on p. 86, final row on p. 87; reconstructed as one table.

| Renown Score | Character Level |
|---|---|
| 1 | 1 |
| 3 | 3 |
| 10 | 5 |
| 25 | 11 |
| 50 | 17 |

*What it is for: not a roll — an equivalence table so character level can stand in for a tracked Renown Score when you don't want to track it.*

---

### Settlements *(p. 86–92)*

Campaign worlds include settlements characters visit — and sometimes adopt as a home base in or near which to build Bastions at high enough level (ch. 8). The Settlements by Size table gives population ranges plus the value of the most expensive item likely for sale; adjust for special circumstances (a Potion of Healing at 50 GP is too expensive for most villages, but a village with an alchemist, herbalist, or potion brewer might stock some).

#### Settlements by Size *(p. 87–88)*

> Caption on p. 87; header and rows on p. 88.

| Settlement | Population Range | Max. GP Value |
|---|---|---|
| Village | Up to 500 | 20 GP |
| Town | 501–5,000 | 2,000 GP |
| City | 5,001 and higher | 200,000 GP |

*What it is for: not a roll — size bands, each with a population range and the price ceiling of the most expensive item on local sale. Use it to gate availability of `data/library/items/` templates.*

The following tables flesh out a settlement; record the results on the **Settlement Tracker** (form on p. 87; no body text in this extraction).

#### Defining Traits *(p. 88)*

| 1d20 | Trait |
|---|---|
| 1–2 | Fortified outer wall |
| 3–4 | Lots of gardens, parks, and greenery |
| 5–6 | Lots of mud, filth, and litter |
| 7–8 | Sprawling cemetery |
| 9–10 | Lingering fog |
| 11–12 | Noise and smoke from smithies and forges |
| 13 | Canals and bridges |
| 14 | Cliffs on one or more sides |
| 15–16 | Clean streets and well-maintained buildings |
| 17–18 | Ancient ruins within the settlement |
| 19–20 | Impressive structure (such as a keep, temple, circle of standing stones, or ziggurat) |

*What it is for: roll 1d20 (some results cover a band of two) to pick a physical descriptor for a settlement; it hints at what kinds of areas, structures, and hazards the place contains.*

#### Claims to Fame *(p. 89)*

| 1d20 | Claim to Fame |
|---|---|
| 1 | Delicious food |
| 2 | Rude people |
| 3 | Friendly folk |
| 4 | Artists or writers |
| 5 | Great hero/savior |
| 6 | Flowers |
| 7 | Seasonal festival |
| 8 | Hauntings |
| 9 | Spellcasters |
| 10 | Decadence |
| 11 | Piety |
| 12 | Gambling |
| 13 | Godlessness |
| 14 | Education |
| 15 | Wines |
| 16 | High fashion |
| 17 | Political intrigue |
| 18 | Powerful guilds |
| 19 | Patriotism |
| 20 | Ancient ruins |

*What it is for: roll 1d20 for the settlement's reputation; drives NPC starting attitude, prestige, and which factions/institutions are present.*

#### Current Calamities *(p. 89–90)*

> Header on p. 89, rows 1–2 there, header repeated and rows 3–12 on p. 90; reconstructed as one table.

| 1d12 | Calamity |
|---|---|
| 1 | Monsters infest the settlement. |
| 2 | A key figure died; murder is suspected. |
| 3 | War brews between rival guilds or gangs. |
| 4 | A plague or famine sparks riots. |
| 5 | Monsters attack anyone who approaches or leaves the settlement. |
| 6 | Trade disputes cause economic hardship. |
| 7 | A natural disaster threatens the settlement. |
| 8 | A prophecy of doom has residents on edge. |
| 9 | Locals are being drafted to fight in a war. |
| 10 | Political or religious strife threatens violence. |
| 11 | The settlement is under siege. |
| 12 | Scandal threatens powerful local families. |

*What it is for: roll 1d12 for the settlement's live pressure — a hook that explains current NPC behavior, unrest, and where a party is needed.*

#### Local Leaders *(p. 90)*

| 1d12 | Leader |
|---|---|
| 1 | Respected, fair, and just leader or council |
| 2 | Feared tyrant |
| 3 | Coward manipulated by others |
| 4 | Illegitimate leader causing civil unrest |
| 5 | Powerful monster |
| 6 | Mysterious, anonymous conspirators |
| 7 | Contested leadership (with open fighting) |
| 8 | Acrimonious council unable to make decisions |
| 9 | Doltish lout |
| 10 | Dying leader (with disputed succession) |
| 11 | Iron-willed and respected leader or council |
| 12 | Religious leader or council |

*What it is for: roll 1d12 for who or what governs the settlement; determines which NPC holds authority and how a party's reputation is judged.*

#### Tavern Names *(p. 90–91)*

> Caption with footnote on p. 90, header and rows on p. 91. Footnote: **"Roll a separate d20 for each part of the tavern's name."**

| 1d20 | First Part | Second Part |
|---|---|---|
| 1 | The Golden Lyre | The Golden Lyre |
| 2 | The Silver Dolphin | The Silver Dolphin |
| 3 | The Beardless Dwarf | The Beardless Dwarf |
| 4 | The Laughing Pegasus | The Laughing Pegasus |
| 5 | The Dancing Hut | The Dancing Hut |
| 6 | The Gilded Rose | The Gilded Rose |
| 7 | The Stumbling Stag | The Stumbling Stag |
| 8 | The Wolf and Duck | The Wolf and Duck |
| 9 | The Fallen Lamb | The Fallen Lamb |
| 10 | The Leering Demon | The Leering Demon |
| 11 | The Drunken Goat | The Drunken Goat |
| 12 | The Wine and Spirit | The Wine and Spirit |
| 13 | The Roaring Horde | The Roaring Horde |
| 14 | The Frowning Jester | The Frowning Jester |
| 15 | The Barrel and Bucket | The Barrel and Bucket |
| 16 | The Thirsty Crow | The Thirsty Crow |
| 17 | The Wandering Satyr | The Wandering Satyr |
| 18 | The Barking Dog | The Barking Dog |
| 19 | The Happy Spider | The Happy Spider |
| 20 | The Witch and Dragon | The Witch and Dragon |

> **Extraction note:** the source prints a single "The …" phrase per row and the web extraction duplicated the same phrase into both the *First Part* and *Second Part* cells. Row content is therefore complete, but the two columns are not genuinely independent — the real procedure is one d20 roll per part of the name (per the footnote), so treat each row as supplying a candidate name in each register and roll twice.

*What it is for: two independent d20 rolls produce a two-part tavern name; purely generative naming for a named venue.*

#### Random Shops *(p. 91–92)*

> Header on p. 91, rows 1–3 there, header repeated and rows 4–20 on p. 92; reconstructed as one table.

| 1d20 | Type |
|---|---|
| 1 | Pawnshop |
| 2 | Apothecary |
| 3 | Grocer |
| 4 | Delicatessen |
| 5 | Potter |
| 6 | Undertaker |
| 7 | Bookstore |
| 8 | Moneylender |
| 9 | Armorer |
| 10 | Chandler |
| 11 | Smithy |
| 12 | Carpenter |
| 13 | Weaver |
| 14 | Jeweler |
| 15 | Baker |
| 16 | Mapmaker |
| 17 | Tailor |
| 18 | Ropemaker |
| 19 | Mason |
| 20 | Scribe |

*What it is for: roll 1d20 to pick which trade a settlement has; a shop type implies both a stock list and a proprietor NPC.*

*(p. 93 is a full-page art plate — no body text in this extraction.)*

---

### Siege Equipment *(p. 94–98)*

Objects designed to assail castles and other walled fortifications. Most require creatures to move them as well as load, aim, and fire. **Load** and **Aim** both cost the **Utilize** action (counts given per item below). Sizes: **Large**, **Medium**, **Gargantuan**, **Huge**.

| Equipment | Size | AC | HP | Attack / Effect | Range or Area | Action costs | Notes |
|---|---|---|---|---|---|---|---|
| **Ballista** | Large | 15 | 50 | Ballista Bolt (Requires Load and Aim). Ranged Attack Roll **+6**. Hit: **16 (3d10) Piercing** | 120/480 ft. | Load: Utilize. Aim: Utilize. | A massive crossbow firing heavy bolts. Then a crew member takes the Ballista Bolt action. |
| **Cannon** | Large | 19 | 75 | Cannonball (Requires Load and Aim). Ranged Attack Roll **+6**. Hit: **44 (8d10) Bludgeoning** | 600/2,400 ft. | Load: Utilize. Aim: Utilize. | Uses gunpowder or arcane power to propel heavy iron balls; usually on a wooden wheeled frame. Then a crew member takes the Cannonball action. |
| **Flamethrower Coach** | Large | 19 | 100 | Flamethrower. **Dexterity Saving Throw: DC 15**, each creature in a 60-foot-long, 5-foot-wide **Line**. Failure: **14 (4d6) Fire** and the creature starts burning. Success: half damage only. | 60-foot-long, 5-foot-wide Line | Driver: Utilize to move and turn (Speed **30 feet**). Gunner: Flamethrower action to aim and fire. | Powered by magic; iron coach with a turret. Crew of two (driver + gunner). Accommodates up to two Medium creatures via an iron hatch in the underbelly; narrow slits give sightlines; occupants have **Three-Quarters Cover** against outside attacks. |
| **Keg Launcher** | Large | 15 | 30 | Toxic Keg (Requires Load and Aim). **Constitution Saving Throw: DC 15**, each creature in a **20-foot-radius Sphere** centered on a point 30 to 300 feet from the launcher. Failure: **14 (4d6) Poison** damage. Success: half damage. | Sphere radius 20 ft.; impact point 30–300 ft. | Load: Utilize. Aim: Utilize. | A back-mounted wooden catapult flinging small kegs of toxic gas. |
| **Lightning Cannon** | Medium | 19 | 30 | Lightning Ball (**Requires Aim**). Ranged Attack Roll **+6**. Hit: **22 (4d10) Lightning** | 300/1,200 ft. | Aim: Utilize. (No load step.) | A small bronze cannon inlaid with arcane runes on a heavy tripod; launches crackling electricity. |
| **Mangonel** | Large | 15 | 100 | Mangonel Stone (Requires Load and Aim). Ranged Attack Roll **+5**. Hit: **27 (5d10) Bludgeoning** | 200/800 ft. (**can't hit targets within 60 feet of itself**) | Load: **two** Utilize actions. Aim: **two more** Utilize actions. | A catapult hurling heavy projectiles in a high arc, so it can hit targets behind walls. |
| **Ram** | Large | 15 | 100 | Ram (**Requires Position**). Melee Attack Roll **+8**, reach 5 ft. Hit: **16 (3d10) Bludgeoning** | Reach 5 ft. | Position: **three** Utilize actions. | A movable gallery with a heavy log suspended from two roof beams by chains; the log is iron-shod, used to batter doors and barricades. The gallery roof gives operators **Total Cover** against attacks and effects from above. |
| **Siege Tower** | Gargantuan | 15 | 200 | *(no attack; mobile structure)* | Reaches wall tops up to **40 feet high** for Medium or smaller creatures | Push or pull by soldiers or beasts of burden | Mobile wooden structure with a beam frame and slats in its walls; large wooden wheels or rollers. A creature in the tower has **Total Cover** against attacks and effects originating outside it. |
| **Suspended Cauldron** | Large | 19 | 20 | Spill (**Requires a Full Cauldron**). **Dexterity Saving Throw: DC 15**, each creature in a 10-foot square directly below the cauldron. Failure: **10 (3d6) Fire** damage. Success: half damage. | 10-foot square below | Filling: **three** Utilize actions. | An iron pot suspended so it can be tipped easily. Once emptied it must be refilled before reuse. Typically filled with boiling oil, but can hold other substances such as **acid** or **green slime** with different effects. |
| **Trebuchet** | Huge | 15 | 150 | Trebuchet Stone (Requires Load and Aim). Ranged Attack Roll **+5**. Hit: **44 (8d10) Bludgeoning** | 300/1,200 ft. (**can't hit targets within 60 feet of itself**) | Load: **two** Utilize actions. Aim: **two more** Utilize actions. | A catapult throwing its payload in a high arc so it can hit targets behind walls. |

*What it is for: not a roll table — ten siege objects, each with AC/HP, an attack bonus or save DC, damage dice, range/area, and a stated number of Utilize actions to load/aim/position. Roll the attack roll or make the save when a crew fires.*

---

### Supernatural Gifts *(p. 99–103)*

A special reward granted by a being or force of great magical power, in two forms: a **Blessing** (usually bestowed by a god or godlike being) and a **Charm** (usually the work of a powerful spirit, a magical location, or a mythic creature). Unlike a magic item, a supernatural gift **isn't an object and doesn't require Attunement**.

#### Blessings *(p. 100–102)*

Given by a deity for something momentous: restoring a god's most sacred shrine; foiling an apocalyptic plot by a god's enemies; helping a god's favored servant complete a quest. A Blessing may also be granted *in advance* of a perilous quest (e.g. a Paladin before setting out to slay a lich causing a magical plague). Give a Blessing only if it is useful to that character, and note that some come with **expectations** — a god might grant one for a particular purpose and revoke it if the character fails to pursue that purpose or acts counter to it. A character retains the benefit **forever** or until taken away by the granter. **No limit** on how many Blessings a character can receive, but it should be rare to have more than one at a time, and a character can't benefit from multiple instances of the *same* Blessing at once (e.g. two Blessings of Health). More Blessings are easy to create by mimicking the properties of a **Wondrous Item**.

#### Blessings *(p. 100–102)*

*In the source these are seven stat blocks (`Name` / `Supernatural Gift (Blessing)` / effect). Rendered as a table with the effect text verbatim.*

| Blessing | Effect |
|---|---|
| **Blessing of Health** | Your Constitution score increases by **2**, up to a maximum of **22**. |
| **Blessing of Magic Resistance** | You have **Advantage** on saving throws against spells and other magical effects. |
| **Blessing of Protection** | You gain a **+1** bonus to AC and saving throws. |
| **Blessing of Understanding** | Your Wisdom score increases by **2**, up to a maximum of **22**. |
| **Blessing of Valhalla** | Grants you the power to summon spirit warriors, as if you are blowing a silver **Horn of Valhalla**. Once used, you can't use it again until **7 days** have passed. |
| **Blessing of Weapon Enhancement** | One nonmagical weapon in your possession becomes a **+1 Weapon** while you wield it. |
| **Blessing of Wound Closure** | Grants you the benefits of a **Periapt of Wound Closure**. |

*What it is for: not a roll — seven permanent-favor templates; two raise an ability score (capped at 22), one gives a +1 bonus, one is Advantage vs. magic, and three are item-mimicking effects.*

#### Charms *(p. 102–103)*

Received in many ways — finding an eldritch secret in a dead archmage's spellbook, solving a sphinx's riddle, drinking from a magical fountain, being graced by a mythic creature, or bearing a Charm after discovering a long-lost location drenched in primeval magic. Some Charms are used **once**; others a set number of times before vanishing. If a Charm lets a character cast a spell, they do so **without expending a spell slot** and **without providing components**; unless stated otherwise the spell uses its normal casting time, range, and duration, and requires Concentration if the spell does. A Charm **can't be removed** by anything short of divine intervention or a **Wish**, and a character can't benefit from multiple instances of a Charm at once. A typical Charm mimics a **Potion** or spell, which makes more easy to create.

#### Charms *(p. 102–103)*

| Charm | Effect |
|---|---|
| **Charm of Animal Conjuring** | Allows you to cast **Conjure Animals**. Once used **three times**, the Charm vanishes from you. |
| **Charm of Darkvision** | Allows you to cast **Darkvision**. Once used **three times**, the Charm vanishes from you. |
| **Charm of Feather Falling** | Grants you the benefits of a **Ring of Feather Falling**. These benefits last for **10 days**, after which the Charm vanishes from you. |
| **Charm of Heroism** | Allows you to give yourself the benefit of a **Potion of Heroism** as a **Magic action**. Once you do so, the Charm vanishes from you. |
| **Charm of Restoration** | Has **3 charges**. Expend charges to cast **Greater Restoration** (**2 charges**) or **Lesser Restoration** (**1 charge**). Once all charges are expended, the Charm vanishes from you. |
| **Charm of the Slayer** | One weapon in your possession becomes a **Dragon Slayer** or **Giant Slayer** (DM's choice) for the next **9 days**. The Charm then vanishes from you, and the weapon returns to normal. |
| **Charm of Vitality** | Allows you to give yourself the benefit of a **Potion of Vitality** as a **Magic action**. Once you do so, the Charm vanishes from you. |

*What it is for: not a roll — seven consumable-grant templates, each with a use limit (1, 3, 3, 1, 3 charges, timed 10- or 9-day, or 1) after which the Charm vanishes. The charge/uses count is the key data for an item-charm template.*

---

### Traps *(p. 104–112)*

Use traps sparingly, or they lose their charm. A hidden pit can be a fun surprise, but too many traps make players overly cautious and slow the game. The best traps are **fleeting distractions skilled characters can overcome quickly**, or **deadly puzzles requiring quick thinking and teamwork**. Traps that are undetectable and inescapable are rarely fun.

#### Parts of a trap

Every trap description after its name includes:

- **Severity and Levels** — **nuisance** or **deadly** for characters of certain levels. A nuisance trap is unlikely to kill or seriously harm characters of the indicated levels; a deadly trap can grievously damage them.
- **Trigger** — often a creature entering an area or touching an object: a pressure plate, a trip wire, turning a doorknob, using the wrong key in a lock.
- **Duration** — expressed in rounds, minutes, or hours; or "until the trap is destroyed or dispelled"; or instantaneous.

Use caution introducing a trap to characters of a *lower* level than its range — a nuisance at one band can be deadly in the next-lower band. The eight example traps are presented alphabetically.

#### Trap severity bands *(compiled from the eight tags below; not a separate source table)*

| Trap | Level 1–4 | Level 5–10 | Level 11–16 | Level 17–20 |
|---|---|---|---|---|
| Collapsing Roof | Deadly | Deadly* | Deadly* | Deadly* |
| Falling Net | Nuisance | Nuisance* | Nuisance* | Nuisance* |
| Fire-Casting Statue | Deadly | Deadly* | Deadly* | Deadly* |
| Hidden Pit | Nuisance | Nuisance* | Nuisance* | Nuisance* |
| Poisoned Darts | Deadly | Deadly* | Deadly* | Deadly* |
| Poisoned Needle | Nuisance | Nuisance* | Nuisance* | Nuisance* |
| Rolling Stone | — | — | Deadly | Nuisance |
| Spiked Pit | Deadly | Deadly* | Deadly* | Deadly* |

\* These bands come from each trap's own "At Higher Levels" scaling text or table rather than from an explicit severity tag.

#### The eight example traps

**Collapsing Roof** — *Deadly Trap (Levels 1–4)*.
**Trigger:** a creature crosses a trip wire. **Duration:** Instantaneous.
A trip wire collapses an unstable section of ceiling. The wire is **3 inches off the ground**, stretching between two weak supports that topple when it is pulled. The first creature that crosses it topples the supports. Each creature beneath the unstable section must succeed on a **DC 13 Dexterity** saving throw, taking **11 (2d10) Bludgeoning** damage on a failure or half on a success. Rubble makes the trapped area **Difficult Terrain**.
*Detect and Disarm:* a **Search** action plus a **DC 11 Wisdom (Perception)** check detects the trip wire and the unstable ceiling; once detected the wire can be easily cut or avoided (**no ability check required**).

#### Collapsing Roof — At Higher Levels *(p. 105–106)*

| Levels | Bludgeoning Damage | Save DC |
|---|---|---|
| 5–10 | 22 (4d10) | 15 |
| 11–16 | 55 (10d10) | 17 |
| 17–20 | 99 (18d10) | 19 |

*What it is for: level scaling for the Collapsing Roof — raises both the Dexterity save DC and the damage.*

**Falling Net** — *Nuisance Trap (Levels 1–4)*.
**Trigger:** a creature crosses a trip wire. **Duration:** Instantaneous.
A trip wire releases a weighted, **10-foot-square Net** suspended from the ceiling; the wire is **3 inches off the ground** between two columns or trees. The first creature to cross it is caught. The target must succeed on a **DC 10 Dexterity** saving throw or have the **Restrained** condition until it escapes; the target **succeeds automatically if it's Huge or larger**. A creature can take an action to make a **DC 10 Strength (Athletics)** check, freeing itself or another creature within reach.
*Detect and Disarm:* a **Search** action plus a **DC 11 Wisdom (Perception)** check detects the wire and the Net; once detected the wire can be cut or avoided (no check required).
*Destroy the Net:* reducing the Net to **0 HP** frees any creature trapped in it (Net statistics are in the PHB).
*Set the Trap:* a creature with **Thieves' Tools** and all components (including a Net) can try to set it with a successful **DC 13 Dexterity (Sleight of Hand)** check; each attempt takes **10 minutes**.
*At Higher Levels:* increase the **weight of the Net**, raising both the save DC and the Strength (Athletics) DC: **DC 12** at levels 5–10, **DC 14** at levels 11–16, **DC 16** at levels 17–20.

**Fire-Casting Statue** — *Deadly Trap (Levels 1–4)*.
**Trigger:** a creature moves onto a pressure plate. **Duration:** Instantaneous.
When a creature moves onto the pressure plate for the first time on a turn, or starts its turn there, a nearby statue exhales a **15-foot Cone** of magical flame. The statue can look like anything (a dragon, a wizard). Each creature in the Cone must succeed on a **DC 15 Dexterity** saving throw, taking **11 (2d10) Fire** damage on a failure or half on a success.
*Detect and Disarm:* a **Detect Magic** spell reveals an aura of **Evocation** magic around the statue. A **Search** action within **5 feet** plus a **DC 10 Wisdom (Perception)** check detects a tiny glyph; then a **Study** action plus a **DC 15 Intelligence (Arcana)** check ascertains that the glyph means "fire". As an action, a sharp tool can deface the glyph, disarming the trap. Separately, a **Search** action plus a **DC 15 Wisdom (Perception)** check detects the pressure-plate floor section; wedging an **Iron Spike** under the plate prevents triggering.

#### Fire-Casting Statue — At Higher Levels *(p. 107)*

| Levels | Fire Damage | Area of Effect |
|---|---|---|
| 5–10 | 22 (4d10) | 30-foot Cone |
| 11–16 | 55 (10d10) | 60-foot Cone |
| 17–20 | 99 (18d10) | 120-foot Cone |

*What it is for: level scaling for the Fire-Casting Statue — raises damage and the Cone length together.*

**Hidden Pit** — *Nuisance Trap (Levels 1–4)*.
**Trigger:** a creature moves onto the pit's lid. **Duration:** Instantaneous.
A **10-foot-deep** pit has a hinged lid constructed from material identical to the surrounding floor. When a creature moves onto the lid it swings open like a trapdoor, dropping the creature in; **the lid remains open thereafter**. A creature that falls in takes **3 (1d6) Bludgeoning** damage from the fall.
*Detect and Disarm:* a **Study** action plus a **DC 15 Intelligence (Investigation)** check detects the pit; once detected, an **Iron Spike** or similar can be wedged between lid and floor to keep it shut, or the cover can be held shut using **Arcane Lock** or similar magic.
*Escape:* a creature needs a **Climb Speed**, climbing gear, or magic such as **Spider Climb** to scale the smooth walls. (You can make it easier by adding cracks serving as handholds and footholds.)

#### Hidden Pit — At Higher Levels *(p. 108)*

| Levels | Pit Depth | Bludgeoning Damage |
|---|---|---|
| 5–10 | 30 feet | 10 (3d6) |
| 11–16 | 60 feet | 21 (6d6) |
| 17–20 | 120 feet | 42 (12d6) |

*What it is for: level scaling for the Hidden Pit — raises fall depth and the fall damage.*

**Poisoned Darts** — *Deadly Trap (Levels 1–4)*.
**Trigger:** a creature moves onto a pressure plate. **Duration:** Instantaneous.
Poisoned darts shoot from tubes embedded in the surrounding walls; the housing holes are obscured by dust and cobwebs, or skillfully hidden amid bas-reliefs, murals, or frescoes. Each creature in the darts' path must succeed on a **DC 13 Dexterity** saving throw or be struck by **1d3 darts**, taking **3 (1d6) Poison** damage **per dart**.
*Detect and Disarm:* a **Search** action plus a **DC 15 Wisdom (Perception)** check detects the holes; plugging them with wax, cloth, or detritus prevents firing. A **Search** action plus a **DC 15 Wisdom (Perception)** check detects the pressure plate; wedging an **Iron Spike** under it prevents triggering.
*At Higher Levels:* increase each dart's Poison damage to **7 (2d6)** at levels 5–10, **14 (4d6)** at levels 11–16, or **24 (7d6)** at levels 17–20.

**Poisoned Needle** — *Nuisance Trap (Levels 1–4)*.
**Trigger:** a creature opens the trap's lock improperly or fails to disarm the trap. **Duration:** Instantaneous.
A poisoned needle is hidden in a lock. When a creature opens the lock with any object other than the proper key, the needle springs out and stabs it. The creature makes a **DC 11 Constitution** saving throw; on a failure it takes **5 (1d10) Poison** damage and has the **Poisoned** condition for **1 hour**; on a success, half damage only.
*Avoid:* the trap doesn't trigger if the lock is opened using **Knock** or similar magic.
*Detect and Disarm:* a **Search** action plus a **DC 15 Wisdom (Perception)** check detects the needle; once detected, a character can take an action to disarm with a **DC 15 Dexterity (Sleight of Hand)** check (failure triggers the trap).

#### Poisoned Needle — At Higher Levels *(p. 110)*

| Levels | Poison Damage | Save DC |
|---|---|---|
| 5–10 | 11 (2d10) | 13 |
| 11–16 | 22 (4d10) | 15 |
| 17–20 | 55 (10d10) | 17 |

*What it is for: level scaling for the Poisoned Needle — raises the Constitution save DC and damage; the DC 15 Sleight of Hand disarm DC is not scaled.*

**Rolling Stone** — *Deadly Trap (Levels 11–16) or Nuisance Trap (Levels 17–20)*.
**Trigger:** a creature moves onto a pressure plate. **Duration:** Until the stone stops rolling.
A hidden pressure plate releases a **5-foot-radius orb of solid stone** from a secret compartment. The stone and all creatures nearby **roll Initiative**; the stone gets a **+8** bonus on its Initiative roll. On its turn the stone moves **60 feet** in one direction, changing course if redirected by an obstacle. It can move through creatures' spaces, and creatures can move through the stone's space, treating it as **Difficult Terrain**. Whenever the stone enters a creature's space for the first time on a turn, or a creature enters the stone's space while it is rolling, that creature must succeed on a **DC 15 Dexterity** saving throw or take **55 (10d10) Bludgeoning** damage and have the **Prone** condition. The stone stops when it hits a wall or similar barrier; it can't go around corners, but creative builders incorporate curving turns into nearby passages to keep it moving.
*Detect and Disarm:* a **Study** action plus a **DC 15 Intelligence (Investigation)** check deduces the pressure plate's function; wedging an **Iron Spike** prevents triggering.
*Destroy the Stone:* the stone is a **Large** object with **AC 17, HP 100**, a **Damage Threshold of 10**, and **Immunity to Poison and Psychic** damage.
*Slow the Stone:* as an action, a **DC 20 Strength (Athletics)** check reduces the distance it moves on its turn by **15 feet**; if that distance drops to **0** it stops and is no longer a threat.

**Spiked Pit** — *Deadly Trap (Levels 1–4)*.
**Trigger:** a creature moves onto the pit's lid. **Duration:** Instantaneous.
A **10-foot-deep** pit has a hinged lid of material identical to the surrounding floor. When a creature moves onto the lid it swings open like a trapdoor, dropping the creature into a pit with **sharpened wooden or metal spikes** at the bottom; **the lid remains open thereafter**. A creature that falls in lands at the bottom and takes **3 (1d6) Bludgeoning** damage from the fall **plus 9 (2d8) Piercing** damage from the spikes.
*Detect and Disarm:* a **Study** action plus a **DC 15 Intelligence (Investigation)** check detects the pit; once detected, an **Iron Spike** or similar can be wedged between lid and floor, or the cover held shut with an **Arcane Lock** spell or similar.
*Escape:* a creature needs a **Climb Speed**, climbing gear, or magic such as **Spider Climb** to scale the smooth walls. (Add cracks as handholds and footholds to make it easier.)

#### Spiked Pit — At Higher Levels *(p. 112)*

| Levels | Pit Depth | Damage |
|---|---|---|
| 5–10 | 30 feet | 10 (3d6) Bludgeoning plus 13 (3d8) Piercing |
| 11–16 | 60 feet | 21 (6d6) Bludgeoning plus 36 (8d8) Piercing |
| 17–20 | 120 feet | 42 (12d6) Bludgeoning plus 57 (13d8) Piercing |

*What it is for: level scaling for the Spiked Pit — raises fall depth and both the fall and spike damage components.*

#### Building Your Own Traps *(p. 112)*

When designing traps, use the **Building a Trap** table to set the total damage a trap deals based on its level and severity; if the trap also applies a condition, consider reducing the damage. If the trap requires an attack roll or allows a saving throw, use the appropriate columns to set the attack bonus or save DC.

#### Building a Trap *(p. 112)*

> Two-tier header in the source: a top band spanning **Nuisance Traps** (3 columns) and **Deadly Traps** (3 columns), over a `Levels` column. Reconstructed as a single flat header below.

| Levels | Nuisance Traps: Attack Bonus | Nuisance Traps: Save DC | Nuisance Traps: Damage | Deadly Traps: Attack Bonus | Deadly Traps: Save DC | Deadly Traps: Damage |
|---|---|---|---|---|---|---|
| 1–4 | +4 | 10–12 | 5 (1d10) | +8 | 13–15 | 11 (2d10) |
| 5–10 | +4 | 12–14 | 11 (2d10) | +8 | 15–17 | 22 (4d10) |
| 11–16 | +4 | 14–16 | 22 (4d10) | +8 | 17–19 | 55 (10d10) |
| 17–20 | +4 | 16–18 | 55 (10d10) | +8 | 19–21 | 99 (18d10) |

*What it is for: not a roll — the master table for authoring custom traps. Pick a level band and a severity, then read off the attack bonus (nuisance +4 / deadly +8), the save DC band, and the damage expression.*

---

### Viwo notes

Mapping of the DMG (2024) Ch. 3 content onto Viwo engine areas. Viwo is a Python/Flask persistent-world sim, 5e-flavoured, **one turn = one in-game minute**, d20+modifier vs DC, **no armor class**, HP floor 100. Only genuinely relevant items are listed; uncertain items are flagged as candidates.

**Checks, DCs, saves**
- **Sample Fear DCs** (10 / 15 / 20) and **Sample Mental Stress Effects** (10/1d6, 15/3d6, 20/9d6) line up almost exactly with `engine/checks.py` `DCS` / `_DC_BANDS` (5 very easy, 10 easy, 15 medium, 20 hard, 25+ very hard) — use the DC column as-is and feed the dice expressions to `engine/emotion.py` as fear/stress effects.
- **Building a Trap** nuisance DCs 10–12/12–14/14–16/16–18 and deadly 13–15/15–17/17–19/19–21 bracket `DCS` cleanly; the +4/+8 attack bonuses are awkward with no AC, but the **save DC bands and damage ladders are directly reusable**.
- **Environmental Effects** save DCs (10 Constitution for cold/frigid water/deep water, 5-then-1-per-hour for heat, 10 Charisma for Gehenna, 10 Wisdom for Pandemonium) are all `checks.py`-shaped and all use **hourly** cadence, which needs rescaling to 1-minute turns.

**Movement, chases, hazards, traps**
- **Dashing in a chase** = 3 + CON mod, extra Dashes cost a DC 10 CON save or 1 Exhaustion per turn — a direct fit for `engine/movement.py` (move/dash) and `engine/conditions.py` (Exhaustion) given the 1-minute turn.
- **Escape Factors** (crowding/hiding place → Adv/Dis) is a circumstance modifier table, i.e. candidate for a per-check modifier hook in `engine/checks.py`.
- **Urban/Wilderness Chase Complications** (1d12, 7–12 = nothing) are ideal `data/library/` roll tables; **1d12 per character per turn** fits a 1-minute turn cleanly.
- **Hazards** (12) and **Traps** (8) share one shape: severity band, trigger, duration, detect/disarm DC, escape DC, "At Higher Levels" scaling. `engine/traps` does not exist yet — this chapter is the natural spec for it, with **Building a Trap** as the data source and hazard-per-biome placement.
- **Thin ice** (3d10 × 10 lb per 10-foot square), **quicksand** (escape DC = 10 + feet sunk) and **Razorvine/Vicious Vine/Webs** grappling are candidates for `engine/movement.py` terrain effects and `engine/biomes.py`.
- **Dungeon mapping** uses a 5-ft grid; `engine/world_grid.py` (WorldPainter import) will need a stated cell→metre conversion, and note the project constraint that **one cell = one minute of traversal** on the Eldenford town map — the two scales are not the same thing.

**Places, structures, world**
- **Doors / Lock Complexity / Lock Quality / Secret Doors / Portcullises** → `data/library/ways/` + `engine/structures.py`; the AC column is unusable (no AC in Viwo) but HP, DC to Open, lock time, and detect DC are all usable. **Portcullis** (winch side vs. Strength (Athletics) DC 15–30) is a good way-interaction test.
- **Siege Equipment** (10 objects) → `engine/structures.py`: AC/HP/action-costs mirror a structure record; the **Utilize action counts** (1 for load/aim, 2–3 for Mangonel/Trebuchet/Ram/Cauldron) read well as multi-turn 1-minute-turn actions.
- **Settlements by Size** (Village ≤500 / Town 501–5,000 / City 5,001+) gates item availability in `data/library/items/` via the **Max. GP Value** column (20 GP / 2,000 GP / 200,000 GP). Eldenford at 1,500–2,000 inhabitants therefore sits in the **Town** band → 2,000 GP ceiling.
- **Settlements** traits/fame/calamities/leaders/shops → `data/library/areas/` + `engine/venues.py`; **Tavern Names** (two independent d20 rolls) and **Random Shops** (1d20) are drop-in generators for named venues and their proprietors. **Claims to Fame** maps onto a settlement's baseline NPC disposition.
- **States of Ruin** (1d6) → a decay/occupancy state on an area record in `engine/venues.py` or `data/library/areas/`; it drives terrain, cover, stealth and noise rather than a check.
- **Dungeon Quirks** (50 rows) → candidate for quirk tags on `data/worldpainter/biomes.json` and `engine/biomes.py`.
- **Environmental Effects** dead magic / wild magic zones, planar auras, Heavy Precipitation and Strong Wind → `engine/environment_propagation.py`, `engine/weather_forecast.py`, `engine/lighting.py` (obscurity, flame extinguishing, Bright/Dim light from Fireball Fungus and the Light trait).
- **Curses and Magical Contagions** (Demonic Possession, Cackle Fever, Sewer Plague, Sight Rot) → `engine/conditions.py` + `data/library/conditions/`; the contagious ones give an exposure cone (10-foot Emanation) plus per-day save cadence, and the shared 3-day **DC 15 Constitution** recuperation save is a clean periodic tick.

**People, renown, promotion**
- **NPCs** six elements + six name tables (1d6 table → 1d12 name) + **NPC Appearance** (1d12) + **NPC Secrets** (1d10) → `engine/population.py` trait generation; the secret/appearance tables are ideal motive and visual-tag seeds.
- **Loyalty Score** (0–20, max = highest party CHA, start = half, ±1d4 / −2d4) → `engine/relationships.py`; a ready-made 0–20 relationship meter with the same triggers Viwo already needs for ally/betrayal.
- **Renown** (0+, thresholds 3 / 10 / 25 / 50, **Level-Based Renown** equivalence table) → `engine/promotion.py` + `engine/relationships.py`; the thresholds map directly onto Viwo's Promote button progression.
- **NPC party-member archetypes** and the CR ≤ half-level rule → candidate for `engine/soak.py` NPC tier selection and `engine/promotion.py`.
- **Marks of Prestige** (titles, special favors, special rights, land, fortifications) → `engine/promotion.py`; **Special Favors** is behaviour keyed on the granter's alignment, which is a clean input for `engine/relationships.py` NPC disposition.
- **Alignment** (monster starting attitude Hostile/Friendly, organization ethos) → candidate for `engine/soak.py` and `engine/relationships.py`; the ethos/member-alignment gap is a usable source of intra-faction tension.
- **Gods and Other Powers** (divine rank, home plane, myths, religious practice) → `engine/background_social.py` and `data/library/traits/`; shrine/temple practice is a schedule-and-venue signal, not a combat one.
- **Death / Defeated, Not Dead** (1 HP + Unconscious; **DC 20 Constitution** after a Long Rest) → `engine/combat.py` down-state, worth checking against Viwo's HP floor 100 convention.

**Skills, items, crafting**
- **Creating a Background** (3 abilities, 1 Origin feat, 2 skills, 1 tool, **50 GP** equipment) → `data/library/traits/` and `engine/background_social.py`; the 50 GP starting package is directly comparable to an item-template budget.
- **Magic Item Power by Rarity** (spell level 1/3/5/8/9, bonus —/+1/+2/+3/+4) → `data/library/items/` (282 templates): a clean validation cap per rarity.
- **Supernatural Gifts** (7 Blessings, 7 Charms) → `data/library/traits/` for the permanent Blessings and `data/library/items/` for the consumable Charms (uses = 1, 3, 3, 1, 3 charges, or 9-10 day timers). Unlike magic items they require **no attunement** — a useful distinction if Viwo ever models attunement.
- **Creating a Creature** and the **Creature Traits** list (23 traits, with their own DCs — Death Jinx Bane DC 13, Mimicry DC 14 Wisdom (Insight), Gloom Shroud 20 ft. emanation, Dimensional Disruption 30 ft.) → `data/library/traits/` as monster-modifier templates; the **Siege Monster** trait (double damage to objects and structures) and **Gloom Shroud** (Disadvantage on Charisma) both have obvious Viwo hooks.
- **Poison** (4 delivery types, harvest **DC 20 Intelligence (Nature)** with a Poisoner's Kit over 1d6 minutes, 14 sample poisons with DCs 11–21) → `data/library/items/` for the poison items and `engine/conditions.py` for **Poisoned**; Truth Serum ("can't knowingly communicate a lie") and Pale Tincture ("can't be healed by any means") are both worth having as condition flags. **Alien Technology** (**DC 10** simple / **DC 20** complex Investigation) is a clean model for investigating unfamiliar WorldPainter-imported objects.
- **Mobs** (**Mob Results**, **Targets in Area of Effect**) → `engine/combat.py`: with many NPCs in a crowded area these two tables keep resolution to a single roll per group instead of N — directly relevant to the simultaneous-mode parallel turn loop.
- **Fear and Mental Stress** prolonged effects (1d10 minutes; 1d10 × 10 hours) → `engine/conditions.py`; the short-term band is minute-denominated and therefore a good fit for a 1-minute turn.
- **No direct mapping found** for: **Firearms and Explosives** (only relevant as `data/library/items/` templates if modern tech enters the world — the Burst Fire / Reload / Energy Cell properties have no engine home today), **Spell Damage** (level-based damage scaling has no Viwo analogue), and **Renown's** campaign-scale rank ladders beyond the thresholds.

---

## Part 2 — Xanathar's Guide to Everything, Chapter 2: Dungeon Master's Tools

---

*Source: `dm_tools2.txt`, a D&D Beyond web-page print of XGtE Ch. 2 "Dungeon Master's Tools" (41 source pages, all read). Web boilerplate ("Claim Your Free World of Warcraft Adventure", "DISMISS", "ARTIST:", "A BLOB OF ANNIHILATION…", the `27.09.2026 … - D&D Beyond` / `https://www.dndbeyond.com/…` footer pairs) has been removed.*

### Chapter map (source order)

- **Simultaneous Effects** *(p. 1)*
- **Falling** — Rate of Falling; Flying Creatures and Falling *(p. 1–2)*
- **Sleep** — Waking Someone; Sleeping in Armor; Going without a Long Rest *(p. 2–3)*
- **Adamantine Weapons** *(p. 3)*
- **Tying Knots** *(p. 4)*
- **Tool Proficiencies** — Tools and Skills Together; Tool Descriptions *(p. 4–5)*
- **Tool Descriptions** (26 DC tables) *(p. 6–23)*
- **Spellcasting** — Perceiving a Caster at Work; Identifying a Spell; Invalid Spell Targets *(p. 23–24)*
- **Areas of Effect on a Grid** — Template Method; Token Method *(p. 25–29)*
- **Encounter Building** — Steps 1–5; Solo Monster CR; Multiple Monsters ×4; Monster Personality; Monster Relationships; Terrain and Traps; Random Events; Quick Matchups *(p. 30–39)*
- **Random Encounters: A World of Possibilities** *(p. 40–41)*
- **Viwo notes**

### Sections present in the printed chapter but **absent from this extraction**

The prompt's expected subject list names several sections that are **not in the extracted text at all** — no prose and no tables — so they are *not* transcribed here and nothing has been invented in their place:

`Damage` · `Healing` · `Mounted Combat` · `Underwater Combat` · `Knocking Back` · `cover and obscurement` · `Hiding` · `Light and Vision` · `Climbing` · `Group Patrons` · `Traps` · `Magic Items` · `Downtime`

Also absent: the actual **Random Encounter tables** for the 11 environment categories × 4 level tiers (p. 40–41 ends with a bare link, "Random Encounter Tables / View Random Encounter Tables by Terrain") and **Diagrams 2.1–2.6** (p. 26–27 are image-only pages with no extractable text).

---

### Chapter Introduction *(p. 1)*

As the Dungeon Master you oversee the game and weave together the story experienced by your players. The chapter is a supplement to the tools and advice in the *Dungeon Master's Guide*, offering new rules options and refined tools for creating and running adventures. It opens with optional rules for running certain parts of the game more smoothly, then goes into depth on **encounter building, random encounters, traps, magic items, and downtime**. The material is meant to make your life easier; ignore anything that doesn't help and customize what does.

---

### Simultaneous Effects *(p. 1)*

- Most effects happen in succession, in an order set by the rules or the DM. In rare cases effects happen at the same time, especially at the start or end of a creature's turn.
- If two or more things happen at the same time on a character or monster's turn, the person at the table — player or DM — who **controls that creature** decides the order. Example: two effects at the end of a player character's turn → the player picks which happens first.

---

### Falling *(p. 1–2)*

Baseline PHB rule restated: at the end of a fall you take **1d6 bludgeoning damage for every 10 feet fell, to a maximum of 20d6**, and you land **prone** unless you somehow avoid the damage. Two optional rules expand on this.

**Rate of Falling** *(p. 2)* — models a long fall as a time-consuming process that can outlast a turn:
- When you fall from a great height, you instantly descend **up to 500 feet**.
- If you're still falling on your next turn, you descend **up to 500 feet at the end of that turn**.
- This continues until the fall ends — you hit the ground, or the fall is otherwise halted.

**Flying Creatures and Falling** *(p. 2)*
- A flying creature in flight falls if knocked prone, if its speed is reduced to 0 feet, or if it otherwise loses the ability to move — unless it can hover or is being held aloft by magic (e.g. the *fly* spell).
- Optional survival rule: **subtract the creature's current flying speed from the distance it fell** before calculating falling damage. Simulates furious flapping / arrested fall. Helpful to a flier knocked prone but conscious with current flying speed > 0 ft.
- Interacts with Rate of Falling: a flier still falls 500 ft on the turn it starts falling. If it starts any later turn still falling **and prone**, it can halt the fall by spending **half its flying speed** to counter prone (as if standing up in midair).

---

### Sleep *(p. 2–3)*

While a creature sleeps it is subjected to the **unconscious** condition.

**Waking Someone** *(p. 2–3)*
- A creature **naturally** sleeping (not magically or chemically induced) wakes if it takes **any damage**, or if someone else spends an **action to shake or slap** it awake.
- A **sudden loud noise** (yelling, thunder, a ringing bell) also awakens a natural sleeper.
- **Whispers** don't disturb sleep *unless* the sleeper's **passive Wisdom (Perception) is 20 or higher** and the whispers are **within 10 feet**.
- **Speech at normal volume** awakens a sleeper if the environment is otherwise **silent** (no wind, birdsong, crickets, street sounds, or the like) **and** the sleeper's **passive Wisdom (Perception) is 15 or higher**.

**Sleeping in Armor** *(p. 3)*
- Light armor: no adverse effect.
- Medium or heavy armor: finishing a long rest in which you slept in it means you **regain only one quarter of your spent Hit Dice (minimum of one die)**.
- If you have any levels of **exhaustion**, the rest **doesn't** reduce your exhaustion level.

**Going without a Long Rest** *(p. 3)*
- Whenever you end a **24-hour period without finishing a long rest**, you must succeed on a **DC 10 Constitution saving throw** or suffer **one level of exhaustion**.
- Harder the longer you stay awake: after the first 24 hours the **DC increases by 5 for each consecutive 24-hour period** without a long rest.
- The **DC resets to 10** when you finish a long rest.

---

### Adamantine Weapons *(p. 3)*

- Adamantine is an ultrahard metal from meteorites and extraordinary mineral veins; used for adamantine armor **and** weapons.
- Melee weapons and ammunition made of **or coated with** adamantine are unusually effective at breaking objects: whenever an adamantine weapon or piece of ammunition **hits an object, the hit is a critical hit**.
- The adamantine version of a melee weapon, or of **ten pieces of ammunition**, costs **500 gp more** than the normal version (whether made of the metal or coated with it).

---

### Tying Knots *(p. 4)*

- The creature who **ties** the knot makes an **Intelligence (Sleight of Hand)** check. The **total of that check becomes the DC** for:
  - untying it with an **Intelligence (Sleight of Hand)** check, or
  - slipping out of it with a **Dexterity (Acrobatics)** check.
- This deliberately links Sleight of Hand to **Intelligence, not Dexterity** — an example of the "Variant: Skills with Different Abilities" rule (PHB ch. 7).

---

### Tool Proficiencies *(p. 4–5)*

**Tools and Skills Together** — tools have more specific applications than skills (History applies to any past event; a forgery kit makes fake objects and little else), so the text offers ways to make tool proficiencies attractive:

- **Advantage** — if both a tool and a skill apply to a check and the character is proficient with **both**, consider allowing the check **with advantage**. In the tool descriptions this is often expressed as *additional insight* (or similar), which translates into an increased chance the check succeeds.
- **Added Benefit** — for a successful check, give a character proficient with both a relevant skill and a relevant tool an added benefit: more detailed information, or the effect of a different sort of successful check. Example: a mason-tools-proficient character's successful **Wisdom (Perception)** check to find a secret door also grants an **automatic success** on the **Intelligence (Investigation)** check to determine how to open the door.

**Tool Descriptions** *(p. 5–6)* — how each PHB tool entry below is structured:
- **Components** — the first paragraph lists what a set of supplies is made of; proficiency means you know how to use all component parts.
- **Skills** — every tool potentially provides **advantage** on a check when used with certain skills, provided the character is proficient with **both**. Paragraphs beginning with skill names do this. Benefits apply only to someone with **proficiency**, not mere ownership. You can also grant extra information or an added benefit on a skill check.
- **Special Use** — proficiency usually brings a particular special use (the paragraph with that name).
- **Sample DCs** — a table at the end of each section lists activities the tool can perform and **suggested DCs for the necessary ability checks**.

---

### Tool Descriptions — Sample DC Tables *(p. 6–23)*

All 26 tables below use the same two-column layout: **Activity | DC**.

#### Alchemist's Supplies *(p. 6)*

Produce useful concoctions such as acid or alchemist's fire.
- **Components.** Two glass beakers, a metal frame to hold a beaker over an open flame, a glass stirring rod, a small mortar and pestle, and a pouch of common alchemical ingredients (salt, powdered iron, purified water).
- **Arcana.** Unlocks more information on Arcana checks involving potions and similar materials.
- **Investigation.** Additional insight into chemicals or other substances that might have been used in the area.
- **Alchemical Crafting.** Create alchemical items. Raw materials weigh **1 pound per 50 gp spent**. As part of a long rest, make **one dose** of acid, alchemist's fire, antitoxin, oil, perfume, or soap. **Subtract half the value of the created item** from the total gp worth of raw materials carried. (DM may allow the check with advantage.)

| Activity | DC |
| --- | --- |
| Create a puff of thick smoke | 10 |
| Identify a poison | 10 |
| Identify a substance | 15 |
| Start a fire | 15 |
| Neutralize acid | 20 |

*Table 1 — Alchemist's Supplies: sample DCs for alchemical activities; DC 10 for trivial work up to DC 20 to neutralize acid.*

#### Brewer's Supplies *(p. 6–7)*

Brewing produces beer and **purifies water**; takes weeks of fermentation but only a few hours of work.
- **Components.** A large glass jug, a quantity of hops, a siphon, and several feet of tubing.
- **History.** Additional insight on Intelligence (History) checks concerning events where alcohol is a significant element.
- **Medicine.** Additional insight treating alcohol poisoning, or using alcohol to dull pain.
- **Persuasion.** A stiff drink can soften the hardest heart — ply someone with just enough alcohol to mellow their mood.
- **Potable Water.** Purify otherwise-undrinkable water: as part of a **long rest, up to 6 gallons**; as part of a **short rest, 1 gallon**.

| Activity | DC |
| --- | --- |
| Detect poison or impurities in a drink | 10 |
| Identify alcohol | 15 |
| Ignore effects of alcohol | 20 |

*Table 2 — Brewer's Supplies: sample DCs for brewing-related checks, from detecting impurities (10) to ignoring alcohol's effects (20).*

#### Calligrapher's Supplies *(p. 7–8)*

Writing as a delicate, beautiful art; text pleasing to the eye in a style that is difficult to forge. Supplies also allow examining scripts and judging legitimacy.
- **Components.** Ink, a dozen sheets of parchment, and three quills.
- **Arcana.** Little help deciphering magical content, but aids identifying **who wrote** a script of a magical nature.
- **History.** Augments successful checks analyzing or investigating ancient writings, scrolls, other texts, runes etched in stone, or messages in frescoes/other displays.
- **Decipher Treasure Map.** Expertise in examining maps: an **Intelligence check** determines a map's age, whether it holds hidden messages, or similar.

| Activity | DC |
| --- | --- |
| Identify writer of nonmagical script | 10 |
| Determine writer's state of mind | 15 |
| Spot forged text | 15 |
| Forge a signature | 20 |

*Table 3 — Calligrapher's Supplies: sample DCs for script authentication; forging a signature is the hardest at DC 20.*

#### Carpenter's Tools *(p. 8–9)*

Enables construction of wooden structures: a house, a shack, a wooden cabinet, or similar.
- **Components.** A saw, hammer, nails, hatchet, square, ruler, adze, plane, chisel.
- **History.** Aids identifying the use and origin of wooden buildings and other large wooden objects.
- **Investigation.** Additional insight inspecting areas within wooden structures — you know construction tricks that conceal areas.
- **Perception.** Spot irregularities in wooden walls or floors, making it easier to find **trap doors and secret passages**.
- **Stealth.** Quickly assess weak spots in a wooden floor — avoid places that creak and groan.
- **Fortify.** With **1 minute of work** and raw materials, make a door or window harder to force open: **increase the DC needed to open it by 5**.
- **Temporary Shelter.** As part of a long rest, construct a lean-to or similar shelter to keep the group dry and in shade for the rest. Because it was fashioned quickly from whatever wood was available, it **collapses 1d3 days** after being assembled.

| Activity | DC |
| --- | --- |
| Build a simple wooden structure | 10 |
| Design a complex wooden structure | 15 |
| Find a weak point in a wooden wall | 15 |
| Pry apart a door | 20 |

*Table 4 (caption and header split across the p. 8/9 boundary — "Carpenter's Tools" caption sits at the foot of p. 8, the header and rows resume on p. 9): sample DCs for carpentry, from building a simple structure (10) to prying apart a door (20).*

#### Cartographer's Tools *(p. 9)*

Create accurate maps to make travel easier for yourself and those who come after; from mountain-range scale depictions to dungeon-level layout diagrams.
- **Components.** A quill, ink, parchment, a pair of compasses, calipers, and a ruler.
- **Arcana, History, Religion.** More detailed information from your knowledge of maps and locations — e.g. spot hidden messages in a map, identify when a map was made to see whether geographical features have changed.
- **Nature.** Familiarity with physical geography makes it easier to answer questions or solve issues relating to the terrain around you.
- **Survival.** Understanding of geography makes it easier to find paths to civilization, predict where villages or towns might be found, and avoid becoming lost. Common patterns (how trade routes evolve, where settlements arise in relation to geography) are familiar.
- **Craft a Map.** While traveling you can draw a map as you go, in addition to other activity.

| Activity | DC |
| --- | --- |
| Determine a map's age and origin | 10 |
| Estimate direction and distance to a landmark | 15 |
| Discern that a map is fake | 15 |
| Fill in a missing part of a map | 20 |

*Table 5 — Cartographer's Tools: sample DCs for map work, from dating a map (10) to filling in a missing part (20).*

#### Cobbler's Tools *(p. 10)*

A good pair of boots will see a character across rugged wilderness and through deadly dungeons.
- **Components.** A hammer, awl, knife, shoe stand, cutter, spare leather, and thread.
- **Arcana, History.** Knowledge of shoes aids identifying the magical properties of enchanted boots or the history of such items.
- **Investigation.** Footwear holds many secrets — learn where someone has recently visited from wear and accumulated dirt; easier to identify where damage might come from.
- **Maintain Shoes.** As part of a long rest, repair your companions' shoes. For the next **24 hours**, up to **six creatures** of your choice who wear shoes you worked on can travel up to **10 hours a day** without saving throws to avoid exhaustion.
- **Craft Hidden Compartment.** With **8 hours of work**, add a hidden compartment to a pair of shoes; it holds an object up to **3 inches long and 1 inch wide and deep**. You make an **Intelligence check using your tool proficiency** to set the **Intelligence (Investigation) DC** needed to find the compartment.

| Activity | DC |
| --- | --- |
| Determine a shoe's age and origin | 10 |
| Find a hidden compartment in a boot heel | 15 |

*Table 6 — Cobbler's Tools: only two activities in the source; the second uses the checker-set DC from the Craft Hidden Compartment ability.*

#### Cook's Utensils *(p. 10–11)*

Adventuring is a hard life; a cook makes meals far better than hardtack and dried fruit.
- **Components.** A metal pot, knives, forks, a stirring spoon, and a ladle.
- **History.** Assess the social patterns involved in a culture's eating habits.
- **Medicine.** When administering treatment, transform bitter or sour medicine into a pleasing concoction.
- **Survival.** When foraging, make do with scavenged ingredients others couldn't turn into nourishing meals.
- **Prepare Meals.** As part of a **short rest**, prepare a tasty meal. **You and up to five creatures of your choice regain 1 extra hit point per Hit Die spent** during that short rest, provided you have access to the utensils and sufficient food.

| Activity | DC |
| --- | --- |
| Create a typical meal | 10 |
| Duplicate a meal | 10 |
| Spot poison or impurities in food | 15 |
| Create a gourmet meal | 15 |

*Table 7 — Cook's Utensils: sample DCs for food preparation and poison detection; the tasty-meal benefit needs no check.*

#### Disguise Kit *(p. 11–12)*

The perfect tool for anyone who wants to engage in trickery — a false identity.
- **Components.** Cosmetics, hair dye, small props, and a few pieces of clothing.
- **Deception.** In certain cases a disguise improves your ability to weave convincing lies.
- **Intimidation.** The right disguise can make you look more fearsome (e.g. posing as a plague victim, or as a bully to intimidate a gang of thugs).
- **Performance.** A cunning disguise can enhance an audience's enjoyment, provided it's designed to evoke the desired reaction.
- **Persuasion.** Folk trust a person in uniform — disguising as an authority figure makes persuasion more effective.
- **Create Disguise.** As part of a long rest, create a disguise. Once created, **1 minute to don**. You can carry only **one** such disguise at a time without undue attention, unless you have a bag of holding or similar. **Each disguise weighs 1 pound.**
- Otherwise: **10 minutes** to craft a disguise involving moderate appearance changes, **30 minutes** for more extensive changes.

| Activity | DC |
| --- | --- |
| Cover injuries or distinguishing marks | 10 |
| Spot a disguise being used by someone else | 15 |
| Copy a humanoid's appearance | 20 |

*Table 8 — Disguise Kit: sample DCs, from covering distinguishing marks (10) to fully copying a humanoid's appearance (20).*

#### Forgery Kit *(p. 12–13)*

Designed to duplicate documents and make copying a person's seal or signature easier.
- **Components.** Several different types of ink, a variety of parchments and papers, several quills, seals and sealing wax, gold and silver leaf, small tools to sculpt melted wax to mimic a seal.
- **Arcana.** Used with Arcana to determine if a magic item is real or fake.
- **Deception.** A well-crafted forgery (papers proclaiming you a noble, a writ granting safe passage) lends credence to a lie.
- **History.** Combined with history knowledge, improves creating fake historical documents or telling whether an old document is authentic.
- **Investigation.** Useful for determining how an object was made and whether it is genuine.
- **Other Tools.** Knowledge of other tools makes forgeries more believable — e.g. forgery kit + cartographer's tools to make a fake map.
- **Quick Fake.** As part of a **short rest**, a forged document no more than **one page**. As part of a **long rest**, up to **four pages**. Your **Intelligence check** using the kit determines the **DC** for someone else's **Intelligence (Investigation)** check to spot the fake.

| Activity | DC |
| --- | --- |
| Mimic handwriting | 15 |
| Duplicate a wax seal | 20 |

*Table 9 (caption and header split across the p. 12/13 boundary — "Forgery Kit" caption sits at the foot of p. 12, header and rows resume on p. 13): two activities; see also Quick Fake for a checker-set DC.*

#### Gaming Set *(p. 13)*

Proficiency applies to **one type of game** — e.g. Three-Dragon Ante, or games of chance using dice.
- **Components.** All pieces needed to play a specific game or type of game — a complete deck of cards, or a board and tokens.
- **History.** Mastery of a game includes knowledge of its history, important events connected to it, and prominent historical figures involved.
- **Insight.** Playing games with someone is a good way to understand their personality, improving your ability to discern lies from truths and read their mood.
- **Sleight of Hand.** Useful for cheating — swap pieces, palm cards, alter a die roll. Alternatively, engrossing a target in a game by manipulating components with dexterous movements is a great **distraction for a pickpocketing attempt**.

| Activity | DC |
| --- | --- |
| Catch a player cheating | 15 |
| Gain insight into an opponent's personality | 15 |

*Table 10 — Gaming Set: sample DCs, both at 15 — detection and social reads.*

#### Glassblower's Tools *(p. 13–14)*

Ability to shape glass plus specialized knowledge of the methods used to produce glass objects.
- **Components.** A blowpipe, small marver, blocks, and tweezers. **You need a source of heat to work glass.**
- **Arcana, History.** Knowledge of glassmaking techniques aids examining glass objects (potion bottles, treasure-hoard glass). E.g. study how a glass potion bottle has been changed by its contents — residue, deformation, staining.
- **Investigation.** Aids studying an area when the clues include broken glass or glass objects.
- **Identify Weakness.** With **1 minute of study**, identify the weak points in a glass object. **Any damage dealt to the object by striking a weak spot is doubled.**

| Activity | DC |
| --- | --- |
| Identify source of glass | 10 |
| Determine what a glass object once held | 20 |

*Table 11 — Glassblower's Tools: two activities; the doubled-damage weak spot is a no-roll benefit.*

#### Herbalism Kit *(p. 14–15)*

Identify plants and safely collect their useful elements.
- **Components.** Pouches to store herbs, clippers and leather gloves for collecting plants, a mortar and pestle, and several glass jars.
- **Arcana.** Knowledge of the nature and uses of herbs adds insight to magical studies dealing with plants and attempts to identify potions.
- **Investigation.** Helps pick out details and clues in an area overgrown with plants.
- **Medicine.** Mastery improves treating illnesses and wounds by augmenting care with medicinal plants.
- **Nature and Survival.** Easier to identify plants and spot sources of food others might overlook.
- **Identify Plants.** Identify most plants with a quick inspection of their appearance and smell.

| Activity | DC |
| --- | --- |
| Find plants | 15 |
| Identify poison | 20 |

*Table 12 (reconstructed across the p. 14/15 boundary — caption "Herbalism Kit" and the header + first row "Find plants 15" are on p. 14, the repeated header and second row "Identify poison 20" are on p. 15): sample DCs for plant work, from finding plants (15) to identifying poison (20).*

#### Jeweler's Tools *(p. 15)*

Basic techniques for beautifying gems, plus expertise in identifying precious stones.
- **Components.** A small saw and hammer, files, pliers, and tweezers.
- **Arcana.** Knowledge of the reputed mystical uses of gems — handy for Arcana checks about gems or gem-encrusted items.
- **Investigation.** Aids picking out clues held by jeweled objects.
- **Identify Gems.** Identify gems and determine their value **at a glance**.

| Activity | DC |
| --- | --- |
| Modify a gem's appearance | 15 |
| Determine a gem's history | 20 |

*Table 13 — Jeweler's Tools: two activities; gem identification/value needs no roll.*

#### Vehicles (Land and Water Vehicles) *(p. 15–16)*

Proficiency with **land vehicles** covers a wide range of options — chariots, howdahs, wagons, carts. Proficiency with **water vehicles** covers anything that navigates waterways. Both grant the knowledge to handle vehicles of that type, and to repair and maintain them.
- A character proficient with **water vehicles** is also knowledgeable about anything a professional sailor would be familiar with: the sea and islands, **tying knots**, assessing **weather and sea conditions**.
- **Arcana.** When studying a magic vehicle, aids uncovering lore or determining how it operates.
- **Investigation, Perception.** When inspecting a vehicle for clues or hidden information, aids noticing things others miss.
- **Vehicle Handling.** When piloting a vehicle, apply your **proficiency bonus to the vehicle's AC and saving throws**.

| Activity | DC |
| --- | --- |
| Navigate rough terrain or waters | 10 |
| Assess a vehicle's condition | 15 |
| Take a tight corner at high speed | 20 |

*Table 14 — Vehicles: sample DCs for piloting and maintenance, from navigating rough terrain or waters (10) to a high-speed tight corner (20).*

#### Leatherworker's Tools *(p. 16)*

Extends to lore about animal hides and their properties, and knowledge of leather armor and similar goods.
- **Components.** A knife, small mallet, edger, hole punch, thread, and leather scraps.
- **Arcana.** Expertise working with leather adds insight when inspecting magic items crafted from leather (boots, some cloaks).
- **Investigation.** Additional insight studying leather items or clues related to them.
- **Identify Hides.** Determine the source of the leather and any special techniques used to treat it — e.g. spot the difference between dwarven-crafted and halfling-crafted leather.

| Activity | DC |
| --- | --- |
| Modify a leather item's appearance | 10 |
| Determine a leather item's history | 20 |

*Table 15 — Leatherworker's Tools: two activities, the widest DC spread in the tool set (10 vs 20).*

#### Mason's Tools *(p. 16–17)*

Allow you to craft stone structures, including walls and brick buildings.
- **Components.** A trowel, hammer, chisel, brushes, and a square.
- **History.** Aids identifying a stone building's date of construction and purpose, and who might have built it.
- **Investigation.** Additional insight inspecting areas within stone structures.
- **Perception.** Spot irregularities in stone walls or floors, making it easier to find **trap doors and secret passages**.
- **Demolition.** Knowledge of masonry lets you spot weak points in brick walls: **you deal double damage to such structures with your weapon attacks**.

| Activity | DC |
| --- | --- |
| Chisel a small hole in a stone wall | 10 |
| Find a weak point in a stone wall | 15 |

*Table 16 — Mason's Tools: two activities; double damage to structures uses this "find a weak point" check.*

#### Musical Instrument *(p. 17)*

Indicates familiarity with the techniques used to play the instrument, plus knowledge of some songs commonly performed with it.
- **Components.** Instrument-specific; the set is the instrument itself.
- **History.** Aids recalling lore related to the instrument.
- **Performance.** A better show when you incorporate the instrument into your act.
- **Compose a Tune.** As part of a long rest, compose a new tune and lyrics — to impress a noble, or to spread scandalous rumors with a catchy tune.

| Activity | DC |
| --- | --- |
| Identify a tune | 10 |
| Improvise a tune | 20 |

*Table 17 — Musical Instrument: two activities, improvised performance being the hard one.*

#### Navigator's Tools *(p. 17–18)*

Help you determine a true course from observing the stars, and grant insight into charts and maps while developing your sense of direction.
- **Components.** A sextant, compass, calipers, ruler, parchment, ink, and a quill.
- **Survival.** Helps avoid becoming lost and grants insight into the most likely location for roads and settlements.
- **Sighting.** By taking careful measurements, determine your position on a nautical chart **and the time of day**.

| Activity | DC |
| --- | --- |
| Plot a course | 10 |
| Discover your position on a nautical chart | 15 |

*Table 18 — Navigator's Tools: two activities for celestial navigation and charting.*

#### Painter's Supplies *(p. 18)*

Your ability to paint and draw, plus an understanding of art history that aids examining works of art.
- **Components.** An easel, canvas, paints, brushes, charcoal sticks, and a palette.
- **Arcana, History, Religion.** Aids uncovering lore attached to a work of art — magical properties of a painting, the origins of a strange mural in a dungeon.
- **Investigation, Perception.** Knowledge of the practices behind creating a painting grants additional insight when inspecting one.
- **Painting and Drawing.** As part of a short or long rest, produce a simple work of art: capture an image or scene, or make a quick copy of art you saw.

| Activity | DC |
| --- | --- |
| Paint an accurate portrait | 10 |
| Create a painting with a hidden message | 20 |

*Table 19 — Painter's Supplies: two activities, from a straightforward portrait (10) to a hidden-message painting (20).*

#### Poisoner's Tools *(p. 19)*

Favoured by thieves and assassins. Apply poisons and create them from various materials; knowledge of poisons also helps treat them.
- **Components.** Glass vials, mortar and pestle, chemicals, and a glass stirring rod.
- **History.** Helps recall facts about infamous poisonings.
- **Investigation, Perception.** Knowledge of poisons has taught careful handling, giving an edge when inspecting poisoned objects or extracting clues from events involving poison.
- **Medicine.** When treating the victim of a poison, knowledge grants added insight into the best care for the patient.
- **Nature, Survival.** Lore about which plants and animals are poisonous.
- **Handle Poison.** Proficiency lets you **handle and apply a poison without risk of exposing yourself to its effects**.

| Activity | DC |
| --- | --- |
| Spot a poisoned object | 10 |
| Determine the effects of a poison | 20 |

*Table 20 — Poisoner's Tools: two activities, from spotting a poisoned object (10) to determining effects (20).*

#### Potter's Tools *(p. 19–20)*

Used to create ceramic objects, most typically pots and similar vessels.
- **Components.** Potter's needles, ribs, scrapers, a knife, and calipers.
- **History.** Aids identifying ceramic objects — when they were created, their likely place or culture of origin.
- **Investigation, Perception.** Additional insight inspecting ceramics, uncovering clues others would overlook by spotting minor irregularities.
- **Reconstruction.** Examining pottery shards, determine an object's original intact form and its likely purpose.

| Activity | DC |
| --- | --- |
| Determine what a vessel once held | 10 |
| Create a serviceable pot | 15 |
| Find a weak point in a ceramic object | 20 |

*Table 21 — Potter's Tools: three activities, ending with a weak-spot check usable for deliberate breaking.*

#### Smith's Tools *(p. 20)*

Work metal — heating it to alter its shape, repair damage, or work raw ingots into useful items.
- **Components.** Hammers, tongs, charcoal, rags, and a whetstone.
- **Arcana and History.** Additional insight examining metal objects such as weapons.
- **Investigation.** Spot clues and make deductions others overlook when the investigation involves armor, weapons, or other metalwork.
- **Repair.** With access to the tools **and an open flame hot enough to make metal pliable**, restore **10 hit points to a damaged metal object for each hour of work**.

| Activity | DC |
| --- | --- |
| Sharpen a dull blade | 10 |
| Repair a suit of armor | 15 |
| Sunder a nonmagical metal object | 15 |

*Table 22 — Smith's Tools: three activities, two of them at DC 15; sundering is the offensive option.*

#### Thieves' Tools *(p. 20–21)*

Perhaps the most common tools used by adventurers; designed for picking locks and foiling traps, and proficiency also grants a general knowledge of traps and locks.
- **Components.** A small file, a set of lock picks, a small mirror on a metal handle, a set of narrow-bladed scissors, and a pair of pliers.
- **History.** Knowledge of traps grants insight when answering questions about locations renowned for their traps.
- **Investigation and Perception.** Additional insight looking for traps — you have learned common signs that betray their presence.
- **Set a Trap.** Just as you can disable traps, you can set them. As part of a **short rest**, create a trap from items on hand. **The total of your check becomes the DC** for someone else's attempt to discover or disable it. The trap deals damage appropriate to the materials used in crafting it (poison, a weapon) **or** damage equal to **half the total of your check**, whichever the DM deems appropriate.

| Activity | DC |
| --- | --- |
| Pick a lock | Varies |
| Disable a trap | Varies |

*Table 23 — Thieves' Tools: the only tool table with **no fixed numbers** — both DCs are set by the difficulty/lock or trap in question ("Varies").*

#### Tinker's Tools *(p. 21–22)*

Designed to repair many mundane objects. You can't manufacture much with them, but you can mend torn clothes, sharpen a worn sword, and patch a tattered suit of chain mail.
- **Components.** A variety of hand tools, thread, needles, a whetstone, scraps of cloth and leather, and a small pot of glue.
- **History.** Determine the age and origin of objects, even from a few remaining pieces.
- **Investigation.** Inspecting a damaged object, gain knowledge of **how** it was damaged and **how long ago**.
- **Repair.** Restore **10 hit points to a damaged object for each hour of work**. For any object you need access to the raw materials required to repair it; for **metal** objects, an **open flame hot enough to make the metal pliable**.

| Activity | DC |
| --- | --- |
| Temporarily repair a disabled device | 10 |
| Repair an item in half the time | 15 |
| Improvise a temporary item using scraps | 20 |

*Table 24 — Tinker's Tools: three activities, including halving the per-hour 10 HP repair rate.*

#### Weaver's Tools *(p. 22–23)*

Create cloth and tailor it into articles of clothing.
- **Components.** Thread, needles, and scraps of cloth. You know how to work a loom, but such equipment is too large to transport.
- **Arcana, History.** Additional insight examining cloth objects, including cloaks and robes.
- **Investigation.** Knowledge of the process of creating cloth objects lets you spot clues and make deductions others overlook when examining tapestries, upholstery, clothing, and other woven items.
- **Repair.** As part of a short rest, repair a **single** damaged cloth object.
- **Craft Clothing.** Given access to sufficient cloth and thread, create an outfit for a creature as part of a long rest.

| Activity | DC |
| --- | --- |
| Repurpose cloth | 10 |
| Mend a hole in a piece of cloth | 10 |
| Tailor an outfit | 15 |

*Table 25 (header and first rows at the foot of p. 22, rows resume on p. 23 — a single reconstructed table): three clothing activities, two at DC 10.*

#### Woodcarver's Tools *(p. 23)*

Craft intricate objects from wood, such as wooden tokens or arrows.
- **Components.** A knife, a gouge, and a small saw.
- **Arcana, History.** Additional insight examining wooden objects such as figurines or arrows.
- **Nature.** Added insight when examining trees.
- **Repair.** As part of a short rest, repair a **single** damaged wooden object.
- **Craft Arrows.** As part of a **short rest**, craft up to **five arrows**; as part of a **long rest**, up to **twenty**. You must have enough wood on hand.

| Activity | DC |
| --- | --- |
| Craft a small wooden figurine | 10 |
| Carve an intricate pattern in wood | 15 |

*Table 26 — Woodcarver's Tools: the last and smallest of the 26 tool DC tables.*

---

### Spellcasting *(p. 23–24)*

Expands on the spellcasting rules in the PHB and DMG with clarifications and new options.

**Perceiving a Caster at Work** *(p. 23–24)*
- Many spells create obvious effects (fire explosions, walls of ice, teleportation). Others — e.g. *charm person* — display no visible, audible, or otherwise perceptible sign and could easily go unnoticed by someone unaffected.
- You normally don't know a spell has been cast **unless the spell produces a noticeable effect**.
- The **act of casting** is perceptible only if it involves a **verbal, somatic, or material component**. The *form* of a material component doesn't matter for perception — a specified object, a component pouch, or a spellcasting focus are all equivalent.
- If a special ability **removes the need for components** — e.g. the sorcerer's **Subtle Spell** feature, or a creature's **Innate Spellcasting** trait — the casting is **imperceptible**.
- If an imperceptible casting produces a perceptible effect, it's normally **impossible to determine who cast the spell** absent other evidence.

**Identifying a Spell** *(p. 24)*
- Use a **reaction** to identify a spell as it's being cast, or an **action** on your turn to identify a spell by its effect **after** it is cast.
- If you perceived the casting, the effect, or both, make an **Intelligence (Arcana) check**. **DC = 15 + the spell's level.**
- If the spell is cast as a **class spell** and you are a **member of that class**, the check is made **with advantage**. Example: a spellcaster casting as a cleric → another cleric has advantage. Spells not associated with any class when cast (e.g. a monster's Innate Spellcasting) get no such benefit.
- The check represents the need for a quick mind and familiarity with the theory and practice of casting — **this is true even for a caster whose spellcasting ability is Wisdom or Charisma**. Being able to cast spells doesn't by itself make you adept at deducing what others are doing.

**Invalid Spell Targets** *(p. 24–25)*
- If you cast a spell on someone or something that **can't be affected by it, nothing happens to that target** — but if you used a **spell slot, the slot is still expended**.
- If the spell normally has **no effect on a target that succeeds on a saving throw**, the invalid target **appears to have succeeded on its saving throw**, even though it never attempted one (giving no hint that it is an invalid target).
- Otherwise, you perceive that the spell did nothing to the target.

---

### Areas of Effect on a Grid *(p. 25–29)*

The DMG's short rule: choose an intersection of squares as the point of origin of an area of effect, then follow the normal rules for that area type (PHB ch. 10, "Areas of Effect"). **If an area of effect is circular and covers at least half a square, it affects that square.** This section offers two alternatives — the **template method** and the **token method** — both assuming a grid and miniatures. Because the methods can yield **different numbers of squares** for the same area, they should **not be combined at the table**; pick whichever the group finds easier or more intuitive.

*(p. 26–27 of the source contain Diagrams 2.1–2.6 as images only; no text is extractable — `[…diagrams 2.1–2.6 not present in source text…]`.)*

#### Template Method *(p. 28–29)*

Uses 2D shapes representing different areas of effect, to accurately portray length and width and leave little doubt about which creatures are affected. You make or buy the templates.

- **Making a Template.** Paper or card stock cut to the shape of the area of effect. **Every 5 feet of area equals 1 inch of template size.** Example: the **20-foot-radius sphere** of *fireball* is 40 feet in diameter → a **circular template 8 inches in diameter**.
- **Using a Template.** Apply it to the grid. Flat terrain: lay it on the surface; otherwise hold it above and note which squares it covers or partially covers. **If any part of a square is under the template, that square is included.** If a miniature is in an affected square, the creature is in the area. Being merely *adjacent* to the template's edge is not enough — the square must be **entirely or partly covered**.
- **Without a grid:** a creature is included if **any part of the miniature's base** is overlapped by the template.
- Follow all PHB placement rules for the associated area of effect. A cone or line originating from a spellcaster should extend out from the caster and be positioned however the caster likes within the bounds of the rules. Diagrams 2.1 and 2.2 show this in action.

#### Token Method *(p. 29)*

Meant to make areas of effect **tactile and fun**, using dice or other tokens. Rather than faithfully representing the true shapes, it gives square-edged versions of them on a grid.

- **Using Tokens.** **Every 5-foot square** of an area of effect becomes a die or other token placed on the grid. Each token goes **inside** a square, **not at an intersection** of lines. If an area's token is in a square, that square is included. That's the whole rule. Diagrams 2.3–2.6 use dice as tokens.
- **Circles.** Everything is squares, and a circular area of effect becomes **square**, whether the area is a sphere, cylinder, or radius. Example: the **10-foot radius of *flame strike*** (diameter 20 feet) is expressed as a **20-foot square** (diagram 2.3). Diagram 2.4 shows that area with total cover inside it.
- **Cones.** Represented by **rows of tokens** extending from the cone's point of origin; within rows, squares adjoin **side by side or corner to corner** (diagram 2.5). **Number of rows = cone length ÷ 5** (a **30-foot cone contains six rows**). Construction: start with a square adjacent to the cone's point of origin (orthogonally *or* diagonally adjacent) and place one token; in every row beyond that, place **as many tokens as in the previous row, plus one**, each new row's squares sharing a side with a square in the previous row. If the cone is **orthogonally** adjacent to the origin you'll have one extra token — place it at **one end or the other** of the row just created (the source notes you don't have to pick the side chosen in diagram 2.5). Keep placing until all rows are created.
- **Lines.** A line can extend from its source **orthogonally or diagonally** (diagram 2.6).

---

### Encounter Building *(p. 30–39)*

New guidelines for building combat encounters, an **alternative** to "Creating Encounters" (DMG ch. 3). It uses **the same math** but adjusts presentation for flexibility. Assumes you want a clear understanding of the threat posed by a group of monsters; useful for emphasizing combat, ensuring a foe isn't too deadly, and understanding the relationship between a character's level and a monster's challenge rating.

**Step 1: Assess the Characters** *(p. 31)*
- The system uses characters' **levels** to determine the numbers and challenge ratings of creatures you can pit them against without making a fight too hard or too easy.
- Also note each character's **hit point maximum** and **saving throw modifiers**, and **how much damage the mightiest characters can deal with a single attack**. Level and CR define difficulty but don't tell the whole story; these extra statistics are used in step 4.

**Step 2: Choose Encounter Size** *(p. 31)*
- One creature against the characters → your best candidate is one of the game's **legendary creatures**, designed to fill this need.
- Multiple monsters → decide roughly how many creatures you want to use before continuing to step 3.

**Step 3: Determine Numbers and Challenge Ratings** *(p. 31–33)*
- **Solo monster** fights are simple: the **Solo Monster Challenge Rating** table gives the CR for a legendary creature opposing a party of **four to six** characters. Example: a party of **five 9th-level** characters → a **CR 12** legendary creature is optimal.
- For a **more perilous** battle, use a legendary creature whose CR is **1 or 2 higher** than optimal. For an **easy** fight, a CR **3 or more lower** than optimal.
- **Multiple monsters:** the **Multiple Monsters** tables are broken up by level range (**1st–5th**, **6th–10th**, **11th–15th**, **16th–20th**). Note the CR of each creature the party will face, then find each character's level on the appropriate table. Each table shows what **a single character of a given level is equivalent to** in terms of CR, expressed as a **ratio** comparing numbers of characters to a single monster of the listed CR: the **first number is the number of characters of the given level**, the **second is how many monsters of the listed CR those characters equal**.
- Worked example: on the 1st–5th table, a **1st-level character = two CR 1/8 monsters or one CR 1/4 monster**. The ratio reverses at higher CRs: one **CR 1/2** creature = **three** 1st-level characters; one **CR 1** opponent = **five**.
- Worked example 2: a party of **four 3rd-level** characters — one **CR 2** foe is a good match for the whole party, but they'd likely struggle with a **CR 3**. Mixing: one CR 1 (worth two 3rd-level characters) + two CR 1/4 (one character) + one CR 1/2 (one character) = **one CR 1, one CR 1/2, and two CR 1/4** creatures.
- **Mixed-level groups**, two options: (a) group all characters of the same level together, match them with monsters, then combine all creatures into one encounter; or (b) determine the group's **average level** and treat each character as being of that level for monster selection.
- **Easy / deadly scaling.** For an easier encounter that challenges without threatening defeat, treat the party as **roughly one-third smaller** than it is (e.g. a party of five faces monsters that would be a tough fight for **three** characters). For a **potentially deadly** battle that still isn't automatic defeat, treat the party as **up to half again larger** (a party of four facing an encounter designed for **six** characters).

> **Weak Monsters and High-Level Characters** *(p. 33)* — To save space and keep the tables simple, some lower challenge ratings are **missing from the higher-level tables**. For low CRs not appearing on the table, **assume a 1:12 ratio** — twelve creatures of those challenge ratings are equivalent to one character of a specific level.
>
> *Side note printed beneath: "Managing a lot of minions is hard."*

**Step 4: Select Monsters** *(p. 34)*
- More art than science. Beyond CR, look at how monsters stack up: **hit points, attacks, and saving throws** are all useful indicators.
- **Compare the damage a monster can deal to the hit point maximum of each character.** Be wary of any monster capable of **dropping a character with a single attack**, unless you are designing an especially deadly fight.
- **Compare the monsters' hit points to the damage output of the party's strongest characters**, again looking for targets that can be killed in one blow. A significant number of foes dropping in the first rounds makes an encounter too easy.
- Look at whether a monster's **deadliest abilities call for saving throws most of the party members are weak with**, and compare the characters' **offensive abilities to the monsters' saving throws**.
- If the only creatures at the desired CR aren't a good match, **go back to step 3** and alter CR targets and creature counts.

> *Side note printed beneath: "You end up getting mad and eating half of them. It's easier if you can keep an eye on each one. So stick with ten, eleven tops."*

**Step 5: Add Flavor** *(p. 37)*
- Encounters are about more than swinging weapons and casting spells. Consider monster **personality or behavior** (communicable? acting in concert?), the **physical environment** (obstacles, features that might come into play), and the ever-present possibility of something **unexpected**.
- If you have your own ideas, use them; otherwise use the subsections below.

#### Monster Personality *(p. 37)*

Assigning the same personality traits to an entire group of monsters keeps things simple — e.g. one bandit gang an unruly mob of braggarts, another gang always on edge and ready to flee at the first sign of danger. (Also usable: the Monster Personality table in DMG ch. 4, or notes from the Monster Manual description.)

| d8 | Personality |
| --- | --- |
| 1 | Cowardly; looking to surrender |
| 2 | Greedy; wants treasure |
| 3 | Braggart; makes a show of bravery but runs from danger |
| 4 | Fanatic; ready to die fighting |
| 5 | Rabble; poorly trained and easily rattled |
| 6 | Brave; stands its ground |
| 7 | Joker; taunts its enemies |
| 8 | Bully; refuses to believe it can lose |

*Table 27 — Monster Personality: a **d8** roll, one row per die face, giving a group behaviour to play during the fight.*

#### Monster Relationships *(p. 38)*

Rivalries, hatreds, and attachments among the monsters can inform combat behaviour — the death of a much-revered leader might throw followers into a frenzy; a monster might flee if its spouse is killed; a mistreated toady might be eager to surrender and betray its master in return for its life.

| d6 | Relationship |
| --- | --- |
| 1 | Has a rival; wants one random ally to suffer |
| 2 | Is abused by others; hangs back, betrays at first opportunity |
| 3 | Is worshiped; allies will die for it |
| 4 | Is outcast by group; its allies ignore it |
| 5 | Is outcast by choice; cares only for itself |
| 6 | Is seen as a bully; its allies want to see it defeated |

*Table 28 — Monster Relationships: a **d6** roll, one row per die face, giving a bond that an individual monster has to the rest of the group.*

#### Terrain and Traps *(p. 38)*

- A few elements that make a battlefield something other than a large area of flat ground spice up an encounter. Set the encounter in an area that would provide **challenges even if a fight were not taking place there**.
- Ask: what potential perils or other features might draw the characters' attention before or during the fight? Why are monsters lurking there to begin with — does it offer good hiding places?
- For random area details, use the tables in **appendix A of the DMG** for room and area features, potential hazards, obstacles, traps, and more.

#### Random Events *(p. 38)*

- Consider what might happen in an encounter area **if the characters never entered it**: do guards serve in shifts? What other characters or monsters might visit? Do creatures gather to eat or gossip? Any natural phenomena — strong winds, earth tremors, rain squalls?
- Random events add fun unpredictability; just when a fight's outcome seems evident, an unforeseen event can make things more compelling.
- Source tables: the tables for **encounter location, weird locales, and wilderness weather** (DMG ch. 5) for outdoor encounters; the **appendix A** tables — especially **obstacles, traps, and tricks** — for indoor and outdoor; and the **random encounter tables** in the next section of XGtE for inspiration.

#### Quick Matchups *(p. 38–39)*

For when you're not concerned with fine-grained balance or have little prep time. Matches a character of a certain level with a number of monsters, listing the CRs to use for **one, two, and four monsters per character**. Example: at 3rd level a **CR 1/2** monster is equivalent to one 3rd-level character, as are **two CR 1/4** monsters and **four CR 1/8** ones.

| Character Level | 1 Monster | 2 Monsters | 4 Monsters |
| --- | --- | --- | --- |
| 1st | 1/4 | 1/8 | — |
| 2nd | 1/2 | 1/4 | — |
| 3rd | 1/2 | 1/4 | 1/8 |
| 4th | 1 | 1/2 | 1/4 |
| 5th | 2 | 1 | 1/2 |
| 6th | 2 | 1 | 1/2 |
| 7th | 3 | 1 | 1/2 |
| 8th | 3 | 2 | 1 |
| 9th | 4 | 2 | 1 |
| 10th | 4 | 2 | 1 |
| 11th | 4 | 3 | 2 |
| 12th | 5 | 3 | 2 |
| 13th | 6 | 4 | 2 |
| 14th | 6 | 4 | 2 |
| 15th | 7 | 4 | 3 |
| 16th | 7 | 4 | 3 |
| 17th | 8 | 5 | 3 |
| 18th | 8 | 5 | 3 |
| 19th | 9 | 6 | 4 |
| 20th | 10 | 6 | 4 |

*Table 29 — Quick Matchups: roll/no-roll lookup giving a monster **CR** (not a ratio) for 1, 2, or 4 monsters per character, levels 1st–20th. "—" means the source gives no value.*

#### Encounter-Building Reference Tables

**Solo Monster Challenge Rating** *(p. 31–32)* — a legendary creature opposing a party of four to six characters; CR 1–2 above optimal for a perilous fight, CR 3+ below for an easy one.

| Character Level | 6 Characters | 5 Characters | 4 Characters |
| --- | --- | --- | --- |
| 1st | 2 | 2 | 1 |
| 2nd | 4 | 3 | 2 |
| 3rd | 5 | 4 | 3 |
| 4th | 6 | 5 | 4 |
| 5th | 9 | 8 | 7 |
| 6th | 10 | 9 | 8 |
| 7th | 11 | 10 | 9 |
| 8th | 12 | 11 | 10 |
| 9th | 13 | 12 | 11 |
| 10th | 14 | 13 | 12 |
| 11th | 15 | 14 | 13 |
| 12th | 17 | 16 | 15 |
| 13th | 18 | 17 | 16 |
| 14th | 19 | 18 | 17 |
| 15th | 20 | 19 | 18 |
| 16th | 21 | 20 | 19 |
| 17th | 22 | 21 | 20 |
| 18th | 22 | 21 | 20 |
| 19th | 23 | 22 | 21 |
| 20th | 24 | 23 | 22 |

*Table 30 — Solo Monster Challenge Rating: the **CR of a single legendary creature** for a party of 4, 5, or 6 characters, levels 1st–20th. (Reconstructed across the p. 31/32 boundary: the caption, the two-row header — "Character Level" spanning, "— Party Size —" band over "6 Characters / 5 Characters / 4 Characters" — and the 1st-level row are at the foot of p. 31; p. 32 repeats the header and continues with 2nd through 20th.)*

**Multiple Monsters: 1st–5th Level** *(p. 35)*

| Character Level | 1/8 | 1/4 | 1/2 | 1 | 2 | 3 | 4 | 5 | 6 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1st | 1:2 | 1:1 | 3:1 | 5:1 | — | — | — | — | — |
| 2nd | 1:3 | 1:2 | 1:1 | 3:1 | 6:1 | — | — | — | — |
| 3rd | 1:5 | 1:2 | 1:1 | 2:1 | 4:1 | 6:1 | — | — | — |
| 4th | 1:8 | 1:4 | 1:2 | 1:1 | 2:1 | 4:1 | 6:1 | — | — |
| 5th | 1:12 | 1:8 | 1:4 | 1:2 | 1:1 | 2:1 | 3:1 | 5:1 | 6:1 |

*Table 31 — Multiple Monsters, 1st–5th Level: **character-to-monster equivalence ratios**. Each cell reads `characters:monsters` — e.g. at 1st level, "one character is worth two CR 1/8 monsters" (`1:2`); at 1st level a CR 1/2 reads `3:1`, i.e. one CR 1/2 creature is equivalent to three 1st-level characters. Each row's leftmost ratio is normally `1:n` (one character = n small monsters); low CRs missing from higher tables default to **1:12**.*

**Multiple Monsters: 6th–10th Level** *(p. 36)*

| Character Level | 1/8 | 1/4 | 1/2 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6th | 1:12 | 1:9 | 1:5 | 1:2 | 1:1 | 2:1 | 2:1 | 4:1 | 5:1 | 6:1 | — |
| 7th | 1:12 | 1:12 | 1:6 | 1:3 | 1:1 | 1:1 | 2:1 | 3:1 | 4:1 | 5:1 | — |
| 8th | 1:12 | 1:12 | 1:7 | 1:4 | 1:2 | 1:1 | 2:1 | 3:1 | 3:1 | 4:1 | 6:1 |
| 9th | 1:12 | 1:12 | 1:8 | 1:4 | 1:2 | 1:1 | 1:1 | 2:1 | 3:1 | 4:1 | 5:1 |
| 10th | 1:12 | 1:12 | 1:10 | 1:5 | 1:2 | 1:1 | 1:1 | 2:1 | 2:1 | 3:1 | 4:1 |

*Table 32 — Multiple Monsters, 6th–10th Level: same `characters:monsters` ratio layout, columns running CR 1/8 through CR 8. Note 6th and 7th level are the only rows where CR 1/8 is not already 1:12.*

**Multiple Monsters: 11th–15th Level** *(p. 36)*

| Character Level | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 11th | 1:6 | 1:3 | 1:2 | 1:1 | 2:1 | 2:1 | 2:1 | 3:1 | 4:1 | 5:1 | 6:1 | — |
| 12th | 1:8 | 1:3 | 1:2 | 1:1 | 1:1 | 2:1 | 2:1 | 3:1 | 3:1 | 4:1 | 5:1 | 6 |
| 13th | 1:9 | 1:4 | 1:2 | 1:2 | 1:1 | 1:1 | 2:1 | 2:1 | 3:1 | 3:1 | 4:1 | 5 |
| 14th | 1:10 | 1:4 | 1:3 | 1:2 | 1:1 | 1:1 | 2:1 | 2:1 | 3:1 | 3:1 | 4:1 | 4 |
| 15th | 1:12 | 1:5 | 1:3 | 1:2 | 1:1 | 1:1 | 1:1 | 2:1 | 2:1 | 3:1 | 3:1 | 4 |

*Table 33 — Multiple Monsters, 11th–15th Level: same ratio layout, columns running **CR 1 through CR 12**. The low CRs (1/8, 1/4, 1/2) are absent from the header entirely and fall under the **1:12 default**. **[The last column header reads "1" in the extracted text but the 11 body cells beneath it are CR 12 values (—, 6, 5, 4, 4); the source header is "12".]***

**Multiple Monsters: 16th–20th Level** *(p. 36)*

| Character Level | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 16th | 1:5 | 1:3 | 1:2 | 1:1 | 1:1 | 1:1 | 2:1 | 2:1 | 2:1 | 3:1 | 4:1 | 4:1 |
| 17th | 1:7 | 1:4 | 1:3 | 1:2 | 1:1 | 1:1 | 1:1 | 2:1 | 2:1 | 2:1 | 3:1 | 3:1 |
| 18th | 1:7 | 1:5 | 1:3 | 1:2 | 1:1 | 1:1 | 1:1 | 2:1 | 2:1 | 2:1 | 3:1 | 3:1 |
| 19th | 1:8 | 1:5 | 1:3 | 1:2 | 1:2 | 1:1 | 1:1 | 1:1 | 2:1 | 2:1 | 2:1 | 3:1 |
| 20th | 1:9 | 1:6 | 1:4 | 1:2 | 1:2 | 1:1 | 1:1 | 1:1 | 1:1 | 2:1 | 2:1 | 2:1 |

*Table 34 — Multiple Monsters, 16th–20th Level: same ratio layout, columns running **CR 2 through CR 13**. 16th level is the only row where two consecutive high CRs both read `1:1` at CR 5 and CR 6.*

---

### Random Encounters: A World of Possibilities *(p. 40–41)*

DMG ch. 3 already gives guidance on random encounters; this section builds on it, offering a host of random encounter tables.

**Structure the source describes** (no table body is present in the extraction):
- Built on the monster lists in **appendix B of the DMG**, with a set of tables for **each of eleven environment categories**: **arctic, coastal, desert, forest, grassland, hill, mountain, swamp, Underdark, underwater, urban**.
- Within each category, **separate tables for each of the four tiers of play**: **levels 1–4, 5–10, 11–16, and 17–20**.
- Usable "out of the box", but tailoring the tables to your game reinforces campaign themes and flavor; the chapter explicitly encourages customizing the material.
- **In the tables, a name in bold refers to a stat block in the *Monster Manual*.**

**Flight, or Fight, or … ?**
- Each result represents a certain kind of **challenge or potential challenge**. A large number of monsters may be too difficult or dangerous for the characters as they are, prompting them to **flee to avoid contact**, or to **not approach any closer** after perceiving the monsters from a distance.
- You are free to adjust the numbers, but **not every encounter involving a monster needs to result in combat** — an encounter might be the prelude to a battle, a parley, or some other interaction. What happens next depends on what the characters try or what you decide is bound to occur.
- The tables also include entries for what the DMG calls **"encounters of a less monstrous nature"**. Many of these results cry out to be customized or detailed — an opportunity to connect them to the story of your campaign, and in doing so a step toward building your own personalized encounter table.

> **[The actual Random Encounter tables (11 categories × 4 tiers) are not present in the extracted text. Page 41 ends with only a navigation link: "Random Encounter Tables / View Random Encounter Tables by Terrain", after which the source is site footer boilerplate.]**

---

### Viwo notes

*Mapping of the above onto the Viwo engine (Python/Flask persistent-world sim, 5e-flavoured, one turn = one in-game minute, d20 + modifier vs DC, no armor class, HP floor 100). Terse; "candidate for …" where the engine area is a possible home rather than a confirmed fit.*

**Checks, DCs, and difficulty**
- Tying Knots (checker-set DC from an Int check) → `engine/checks.py` as a general *check-result-becomes-DC* mechanic; candidate for a generic "set DC" field alongside existing DCS bands.
- All 26 tool Sample DC tables → the natural content for a `data/library/tools/` DC table; candidate for a lookup from `engine/skills.py` proficiency → `engine/crafting.py` DC (mithral/bevel edges already use plain 10/15/20).
- `Gaming Set` / tool proficiencies and the **Advantage** and **Added Benefit** options → `engine/checks.py` advantage support (candidate for a proficiency-flag bonus rather than a literal d20 advantage).
- Spellcasting **Identify a Spell: DC = 15 + spell level**, with advantage for same-class → `engine/checks.py` as a *formulaic DC* precedent; candidate for the same DC-from-variable pattern as a skill's difficulty scaling.

**Combat and damage**
- Falling: **1d6 per 10 ft, max 20d6, land prone** → `engine/movement.py` (fall entry in the move/dash/climb/jump ladder); with a 1-minute turn this is a natural per-turn hazard.
- Rate of Falling: **500 ft per turn** → same; gives high-altitude falls a turn-by-turn cost, directly relevant to `engine/world_grid.py` altitude/z-layers.
- Flying Creatures and Falling: subtract flying speed from the fall; halve flying speed to arrest a fall → candidate for `engine/movement.py` if flying speed is modelled.
- Adamantine weapons: auto-crit vs objects, **+500 gp** → `data/library/items/` (and `engine/combat.py` if objects are breakable entities).
- Smith's / Tinker's / Woodcarver's / Mason's / Glassblower's "**10 HP per hour of work**" and "**double damage to a weak point**" → candidate for `engine/crafting.py` repair/structural-damage rules, keyed off the same DC-15 "find a weak point" check.

**Vitals, conditions, sleep**
- Sleeping in Armor: **only one quarter of spent Hit Dice, minimum one die**, and no exhaustion reduction → `engine/vitals.py` rest recovery + `engine/conditions.py` **exhaustion** gate.
- Going without a Long Rest: **DC 10 Con save, +5 per consecutive 24 hours, reset to 10** → `engine/timeskip.py` (day boundary) writing an exhaustion level into `data/library/conditions/`.
- Adamantine armor/sleep → not a Viwo concept (no armor class); ignore.

**Light, perception, and hiding**
- Waking Someone: passive **Wisdom (Perception) 20** for whispers within 10 ft, **15** for normal speech in silence; **any damage** wakes → `engine/lighting.py`/`engine/environment_propagation.py` as a noise-and-light "did this disturb the sleeper" predicate feeding `data/library/conditions/`.
- Perceiving a Caster at Work: verbal/somatic/material components make a cast perceptible; Subtle Spell / Innate Spellcasting make it **imperceptible** → candidate for an `audible`/`visible` flag on cast events.
- Invalid Spell Targets → n/a without a spell-slot system; note only.

**Movement and traversal**
- Tying Knots → `engine/traversal.py` alongside `HAZARD_SKILLS`; escaping a snared/knotted state via Dex (Acrobatics) vs a set DC.
- Token Method / Template Method (5 ft = 1 grid square or 1 inch of template; cone rows = length ÷ 5) → `engine/world_grid.py`; the 5-foot square is the natural unit if the grid is not already metric.
- Areas of Effect on a Grid (circle covers ≥ half a square) → candidate for `engine/world_grid.py` AoE resolution.

**Downtime, schedules, and time**
- One turn = one in-game minute. Every "**as part of a short rest**" / "**as part of a long rest**" ability above is a scheduling hook → `engine/timeskip.py` (rest windows) and `engine/schedule.py`.
- Cobbler's **Maintain Shoes** (6 creatures, 10 hours/day, no exhaustion saves for 24 h) and Cook's **Prepare Meals** (1 extra HP per Hit Die for 5 creatures) → candidate for `engine/vitals.py` as travel-fatigue and short-rest meal boons, flagged in `data/library/items/`.
- Brewer's **Potable Water** (6 gallons per long rest / 1 per short rest) → `engine/vitals.py` **thirst** refill rates; Cook's utensils → `engine/foraging.py` food quality.
- Temporary Shelter collapsing **1d3 days** after assembly → `engine/timeskip.py` (a structure with an expiry) and `engine/structures.py`.
- Cook's **Survival** benefit with scavenged ingredients → `engine/foraging.py` / `data/library/foraging.json` weighting.

**Foraging, biomes, and the world**
- Herbalism Kit (**Find plants 15, Identify poison 20**) → `engine/foraging.py` + `data/library/foraging.json` as a skill→tag table row; also `engine/biomes.py` / `data/worldpainter/biomes.json` for plant tags.
- Cartographer's **Nature** and **Survival** benefits; Navigator's **Survival** benefit; Cartographer's **Craft a Map** while travelling → `engine/world_grid.py` (map/discovery) and `engine/skills.py`; candidate for a discovered-landmark record per `engine/venues.py`/`engine/structures.py`.
- Painter's **hidden message** paintings → candidate for a player-authored note/lore object in `data/library/items/`.
- Cobbler's **hidden compartment** (Intelligence check sets the Investigation DC) → candidate for a hidden-slot property on items in `engine/items/`.

**Tools as occupations, not classes**
- `engine/roles.json` (occupations) is the natural home for the 26 tool proficiencies as occupation tags — e.g. brewer, calligrapher, carpenter, cobbler, cook, glassblower, herbalist, jeweler, leatherworker, mason, navigator, painter, poisoner, potter, smith, tinker, weaver, woodcarver.
- The Quick Matchups / Solo Monster CR / Multiple Monsters tables have **no direct engine home** — they are DM-facing. If anything is taken from them, the useful generalizable rule is the **1:12 default for low-CR monsters absent from a high-level table**, i.e. an explicit "not listed ⇒ default weight" convention for any spawn-cost table the sim grows.

**Absent from the source, so no mapping attempted**
- Random Encounter tables, Monster Personality (d8), Monster Relationships (d6): no zone/encounter-weighting or NPC-mood system is named in the engine list. `engine/novelty.py` and `engine/roles.json` are the only *possible* homes for a personality/relationship roll, and that is a candidate at best.
- Tool *repair* amounts (10 HP/hour) also touch `engine/soak.py` only in the sense of long-run wear; no mapping claimed.

---

## Part 3 — Tasha's Cauldron of Everything, "Dungeon Master's Tools"

---

Source: `C:\Users\TOMMYS~1\AppData\Local\Temp\kilo\pdftext\dm_tools_3.txt` — 1738 lines, `<<<PAGE n>>>` markers, **pp. 1–61** (the chapter is 61 web pages).

**Boilerplate removed:** "Claim Your Free World of Warcraft Adventure", "DISMISS", the `ARTIST:`/scene-setting caption lines ("TASHA PREPARES TO WIN ANOTHER GAME OF WIZARDLY CHESS…", "EXPERTS, LEFT TO RIGHT: …"), and every `27.09.2026, 11:02 Dungeon Master's Tools – …` / `https://www.dndbeyond.com/sources/dnd/tcoe/dungeon-masters-tools n/61` footer pair.

**Important scope finding:** this file contains **no puzzles**. The line `MAGIC ITEMS PUZZLES` on p. 1 is the chapter's navigation crumb, not a section, and the chapter text runs from "Session Zero" to "Spells as Natural Hazards" and then straight to the site footer. Tasha's Cauldron's *Puzzle Collection* is a **different chapter** (ch. 4) that is not part of this extract. See `### Puzzles` for the full statement and the evidence. No puzzle content has been invented to fill the gap.

---

### Subject map (source order)

- **Session Zero** — social contract, hard/soft limits, game customization, house rules *(p. 2)*
- **Character and Party Creation** — race/class/background restriction, party composition advice *(p. 3)*
- **Party Formation** — questions to ask players; **Party Origin** d6 table *(p. 3–4)*
- **Running a Game for One Player** — single-player guidance, sidekick foreshadowing *(p. 4)*
- **Social Contract** — explicit commitments *(p. 5)*
- **Hard and Soft Limits** — definitions, in-game and out-of-game example limits *(p. 6–7)*
- **Game Customization** — player-archetype questions *(p. 7)*
- **House Rules** — experiments that may be jettisoned *(p. 7–8)*
- **Sidekicks** — creation, level parity, HP, proficiency, ASIs *(p. 8–10)*
  - **Expert** — features + level table *(p. 10–13)*
  - **Spellcaster** — features + level table, **Spellcasting** role table, recommended 1st-level spells *(p. 13–17)*
  - **Warrior** — features + level table *(p. 17–21)*
- **Parleying with Monsters** — advantage on communication checks when you offer what it wants *(p. 21)*
- **Monster Research** — type → suggested skills, DC = 10 + CR *(p. 22–23)*
- **Monsters' Desires** — 14 d4 offering tables by creature type *(p. 23–27)*
- **Environmental Hazards** *(p. 27)*
  - **Supernatural Regions** — 7 regions, each with triggers + a d100 effects table *(p. 27–47)*
    - Blessed Radiance, Far Realm, Haunted, Infested, Mirror Zone, Psychic Resonance, Unraveling Magic
  - **Magical Phenomena** — Eldritch Storms, Emotional Echoes, Enchanted Springs, Magic Mushrooms, Mimic Colonies, Primal Fruit, Unearthly Roads *(p. 47–58)*
  - **Natural Hazards** — Avalanches, Falling into Water, Falling onto a Creature, Spell Equivalents *(p. 58–60)*

---

### Session Zero *(p. 2–8)*

- **Purpose.** A pre-game session run by the DM and players to establish expectations, outline the terms of a social contract, and share house rules. Often includes building characters together; the DM should advise players to pick options that serve the upcoming campaign.
- **Character and Party Creation.** Players choose race, class, background; the DM may restrict options unsuited to the campaign. With multiple players, encourage **different classes** so the party has a range of abilities. Multiple *backgrounds* matter less than classes (an all-soldier party or a troupe of entertainers can be deliberate). Backgrounds supply **ideals, bonds, and flaws** as roleplaying hooks — if a bond is "I'm trying to pay off an old debt I owe to a generous benefactor," the DM and player decide who the benefactor is and build storylines around them.
- **Party Formation.** Let players build their characters and explain how they came together. It helps to assume the characters already know each other. Suggested questions:
  - Are any of the characters related to each other?
  - What keeps the characters together as a party?
  - What does each character like most about every other member of the adventuring party?
  - Does the group have a patron? (see ch. 2, "Group Patrons")
  - If players can't invent a meeting, they choose from the **Party Origin** table or roll a d6. Session zero should flesh out details (identity of the common foe; identity of the deceased and each character's relationship to them).

#### Party Origin

| d6 | Origin Story |
| --- | --- |
| 1 | The characters grew up in the same place and have known each other for years. |
| 2 | The characters have united to overcome a foe. |
| 3 | The characters were brought together by a common benefactor who wishes to sponsor their adventures. |
| 4 | A funeral brings the characters together. |
| 5 | A festival brings the characters together. |
| 6 | The characters find themselves trapped together. |

*Purpose: roll or choose one seed for how a party came to exist; the party then elaborates names, relationships, and stakes during session zero. Rolls a d6, 6 outcomes.*

- **Running a Game for One Player.** Spend part of session zero building the solo character's backstory, then let the player decide whether to take a sidekick. You may need to run the sidekick for the first few sessions. Sidekicks are stalwart companions who perform tasks in and out of combat (setting up camp, carrying gear); ideally their abilities **complement** the main character (a spellcaster suits a fighter or rogue).
- **Social Contract.** D&D is a fun-for-all; if participants aren't having fun, the game won't last. Session zero is the place to discuss the intended experience and inappropriate topics/behaviors. A typical social contract includes implicit or explicit commitments:
  1. **The DM** will respect the players by running a game that is fun, fair, and tailored for them; will allow every player to contribute to the ongoing story and give every character moments to shine; when a player is talking, the DM is listening.
  2. **The players** will respect the DM and the effort it takes to create a fun game for everyone; will allow the DM to direct the campaign, arbitrate the rules, and settle arguments; when the DM is talking, the players are listening.
  3. **The players** will respect one another, listen to one another, support one another, and do their utmost to preserve the cohesion of the adventuring party.
  - Breach consequence: the group may dismiss that person from the table. The contract covers the basics but individual groups often need extra terms, and it **evolves** as members learn about one another.
- **Hard and Soft Limits.** Discussed once the social contract is agreed. A **soft limit** is a threshold one should think twice about crossing, as it is likely to create genuine anxiety, fear, and discomfort. A **hard limit** is a threshold that should never be crossed. Everyone has both, and the group should know them. Make the discussion comfortable — players may not want to speak limits aloud, especially new players or those who don't know the group well; let them share limits **privately** (e.g. write them on index cards for the DM to read aloud) and compile them into one shared list. Handle with care: even sharing a person's limits can be painful.
  - Common **in-game** limits: sex, exploitation, racial profiling, slavery, violence toward children and animals, gratuitous swearing, intra-party romance.
  - Common **out-of-game** limits: unwanted physical contact, dice-sharing, dice-throwing, shouting, vulgarity, rules lawyering, distracting use of cell phones, generally disrespectful behavior.
  - If a topic makes someone unsafe or uncomfortable, avoid it. If consented to, incorporate with care and be ready to veer away quickly. Limits surface mid-campaign too — plan periodic check-ins and keep the list current.
- **Game Customization.** Cross-reference the DMG introduction's "Know Your Players" archetypes. Questions to ask each player:
  - Which of the three pillars of adventuring (combat, exploration, roleplaying) interest you most?
  - How much humor do you like in the game?
  - What level of technology do you prefer?
  - Do you enjoy solving in-game puzzles and riddles?
  - Do you like to track experience points, or would you rather advance in level when the DM tells you to?
- **House Rules.** House rules include DMG ch. 9 optional rules plus rules you create. Present them as **experiments**; if one adversely affects enjoyment, jettison or revise it.

---

### Sidekicks *(p. 8–21)*

A sidekick is a special NPC added to the group: take a low-CR creature stat block and give it levels in one of three simple classes — **Expert, Spellcaster, Warrior**. A sidekick can join at party inception or mid-campaign (a villager, animal, or other creature the party befriends or saved). The rules also work to customize any monster.

#### Creating a Sidekick *(p. 8–10)*

- Any creature with a stat block in the Monster Manual or another D&D book, **challenge 1/2 or lower**.
- To join, the sidekick must be the **friend of at least one adventurer** — connected to a backstory or to events in play (childhood friend, pet, a creature the party saved). The DM determines whether enough trust is established.
- **Who plays it:** (a) a player as a second character — ideal with only one or two players; (b) a player as their only character — for someone wanting something simpler; (c) the players jointly; (d) the DM.
- No limit on the number of sidekicks, but more than one per player character noticeably slows the game. For encounter difficulty, **count each sidekick as a character**.

#### Progression rules *(p. 9–10)*

- **Starting Level:** the **average level of the group** (a 1st-level group's sidekick is 1st; a 10th-level group's sidekick starts at 10th).
- **Leveling Up:** whenever the group's average level goes up, the sidekick gains a level — regardless of how much of the group's adventures it experienced (adventures it shared + its own training).
- **Hit Points:** on each level gain, gain one **Hit Die** (die type from its stat block) + **Constitution modifier**, minimum 1 HP. At 0 HP and not killed outright it falls unconscious and makes **death saving throws** like a PC.
- **Proficiency Bonus:** from the class table. **Whenever the PB increases by 1, add 1 to the to-hit modifier of all attacks in its stat block and increase the DCs in its stat block by 1.**
- **Ability Score Improvement:** whenever the sidekick gains ASI, adjust everything in the stat block that relies on a changed ability modifier (e.g. Strength-based attacks get +1 to hit and damage). If it's unclear whether a melee attack uses Strength or Dexterity, **either is allowed**.

#### Expert *(p. 10–13)*

*"A master of certain tasks or knowledge, favoring cunning over brawn. It might be a scout, a musician, a librarian, a clever street kid, a wily merchant, or a burglar."* **Requirement:** at least one language in its stat block that it can speak.

| Level | Proficiency Bonus | Features |
| --- | --- | --- |
| 1st | +2 | Bonus Proficiencies, Helpful |
| 2nd | +2 | Cunning Action |
| 3rd | +2 | Expertise |
| 4th | +2 | Ability Score Improvement |
| 5th | +3 | — |
| 6th | +3 | Coordinated Strike |
| 7th | +3 | Evasion |
| 8th | +3 | Ability Score Improvement |
| 9th | +4 | — |
| 10th | +4 | Ability Score Improvement |
| 11th | +4 | Inspiring Help (1d6) |
| 12th | +4 | Ability Score Improvement |
| 13th | +5 | — |
| 14th | +5 | Reliable Talent |
| 15th | +5 | Expertise |
| 16th | +5 | Ability Score Improvement |
| 17th | +6 | — |
| 18th | +6 | Sharp Mind |
| 19th | +6 | Ability Score Improvement |
| 20th | +6 | Inspiring Help (2d6) |

*Purpose: level-by-sidekick-class progression for the Expert archetype; no roll — features unlock at fixed levels. (Table caption "The Expert" sits on p. 10; rows 15th–20th continue onto p. 11 — reconstructed across the page break.)*

**Expert features**

- **Bonus Proficiencies** (1st). Proficiency in one saving throw of your choice: Dex, Int, or Cha. Proficiency in **five skills** of your choice. Proficiency with **light armor**. If humanoid or has a simple/martial weapon in its stat block: all **simple weapons** and **two tools** of your choice.
- **Helpful** (1st). Can take the **Help action as a bonus action**.
- **Cunning Action** (2nd). On its turn in combat, can take **Dash, Disengage, or Hide as a bonus action**.
- **Expertise** (3rd). Choose two of its skill proficiencies; its **proficiency bonus is doubled** on ability checks using them. At 15th level, choose two more.
- **Ability Score Improvement** (4th, 8th, 10th, 12th, 16th, 19th). +2 to one ability or +1 to two; **cannot exceed 20** with this feature.
- **Coordinated Strike** (6th). When using *Helpful* to aid an ally's attack, the target can be up to **30 feet** away, and the sidekick can deal an **extra 2d6 damage** to it the next time it hits that target with an attack roll before end of turn. Extra damage is the same type as the attack.
- **Evasion** (7th). For effects allowing a Dex save for half damage: no damage on success, half on failure (instead of half/nothing). Lost while **incapacitated**.
- **Inspiring Help** (11th). When it takes the Help action, the helped creature also gains a **1d6 bonus to the d20 roll**; if that roll was an attack roll, the bonus may instead be added to the attack's damage against one target on a hit. **20th level: 2d6.**
- **Reliable Talent** (14th). Whenever making an ability check that includes its whole proficiency bonus, it can treat a **d20 of 9 or lower as a 10**.
- **Sharp Mind** (18th). Proficiency in one more saving throw of your choice: Int, Wis, or Cha.

#### Spellcaster *(p. 13–17)*

*"A sidekick who becomes a Spellcaster walks the paths of magic. It might be a hedge wizard, a priest, a soothsayer, a magical performer, or a person with magic in their veins."* **Requirement:** at least one language in its stat block that it can speak.

##### The Spellcaster

| Level | Proficiency Bonus | Features | Cantrips Known | 1st | 2nd | 3rd | 4th | 5th | (unlabeled col.) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1st | +2 | Bonus Proficiencies, Spellcasting | 2 | 1 | 2 | — | — | — | — |
| 2nd | +2 | — | 2 | 2 | 2 | — | — | — | — |
| 3rd | +2 | — | 2 | 3 | 3 | — | — | — | — |
| 4th | +2 | Ability Score Improvement | 3 | 3 | 3 | — | — | — | — |
| 5th | +3 | — | 3 | 4 | 4 | 2 | — | — | — |
| 6th | +3 | Potent Cantrips | 3 | 4 | 4 | 2 | — | — | — |
| 7th | +3 | — | 3 | 5 | 4 | 3 | — | — | — |
| 8th | +3 | Ability Score Improvement | 3 | 5 | 4 | 3 | — | — | — |
| 9th | +4 | — | 3 | 6 | 4 | 3 | 2 | — | — |
| 10th | +4 | — | 4 | 6 | 4 | 3 | 2 | — | — |
| 11th | +4 | — | 4 | 7 | 4 | 3 | 3 | — | — |
| 12th | +4 | Ability Score Improvement | 4 | 7 | 4 | 3 | 3 | — | — |
| 13th | +5 | — | 4 | 8 | 4 | 3 | 3 | 1 | — |
| 14th | +5 | Empowered Spells | 4 | 8 | 4 | 3 | 3 | 1 | — |
| 15th | +5 | — | 4 | 9 | 4 | 3 | 3 | 2 | — |
| 16th | +5 | Ability Score Improvement | 4 | 9 | 4 | 3 | 3 | 2 | — |
| 17th | +6 | — | 4 | 10 | 4 | 3 | 3 | 3 | 1 |
| 18th | +6 | Ability Score Improvement | 4 | 10 | 4 | 3 | 3 | 3 | 1 |
| 19th | +6 | — | 4 | 11 | 4 | 3 | 3 | 3 | 2 |
| 20th | +6 | Focused Casting | 4 | 11 | 4 | 3 | 3 | 3 | 2 |

*Purpose: level-by-class progression for the Spellcaster archetype — cantrips known plus spell slots per level; no roll. (Caption on p. 13; rows 4th–20th continue onto p. 14 — reconstructed across the page break.)*
*(Extraction caveat: the extracted header row names only **1st–5th** spell levels, but every data row carries **seven** numeric values, so the left-to-right sequence above is reproduced verbatim with the seventh value parked in an explicitly unlabeled trailing column. Do not silently re-align these columns.)*

##### Spellcasting

| Role | Spell List | Ability |
| --- | --- | --- |
| Mage | Wizard | Intelligence |
| Healer | Cleric and Druid | Wisdom |
| Prodigy | Bard and Warlock | Charisma |

*Purpose: maps a Spellcaster sidekick's chosen role to its spell list and casting ability; chosen at 1st level, no roll. (Caption split from its rows by a page break — reconstructed.)*

**Spellcaster features**

- **Bonus Proficiencies** (1st). One saving throw of your choice: Wis, Int, or Cha. **Two skills** from: Arcana, History, Insight, Investigation, Medicine, Performance, Persuasion, Religion. Proficiency with **light armor**; if humanoid or has a simple/martial weapon in its stat block, all **simple weapons**.
- **Spellcasting** (1st). Gains the ability to cast spells; if the creature already has the Spellcasting trait, this feature **replaces** it. Choose the role (Mage / Healer / Prodigy) per the Spellcasting table.
  - **Spell Slots.** The table shows slots for Spellcaster spells of 1st level and higher; to cast one, expend a slot of the spell's level or higher. All expended slots return on a **long rest**.
  - **Spells Known.** Starts with **two cantrips and one 1st-level spell** of your choice from its list. Recommended 1st-level spells by role — **Mage:** mage hand, ray of frost, thunderwave. **Healer:** cure wounds, guidance, sacred flame. **Prodigy:** eldritch blast, healing word, light. The Cantrips Known and Spells Known columns show when more spells of your choice are learned; each Spells Known entry must be a level for which the sidekick **has slots** (e.g. at 5th level it can learn one new spell of 1st or 2nd level). Additionally, on **each level gain** in this class you may swap one known class spell for another cantrip or slotted-level spell from its list.
  - **Spellcasting Ability.** Used whenever a spell refers to it, plus for the spell's save DC and attack rolls.
    - `Spell save DC = 8 + sidekick's proficiency bonus + spellcasting ability modifier`
    - `Spell attack modifier = sidekick's proficiency bonus + spellcasting ability modifier`
  - **Spellcasting Focus.** Mage: arcane focus. Healer: holy symbol. Prodigy: arcane focus **or** a musical instrument.
- **Ability Score Improvement** (4th, 8th, 12th, 16th, 18th). +2 to one ability or +1 to two; **cannot exceed 20**.
- **Potent Cantrips** (6th). Adds its spellcasting ability modifier to damage dealt with **any cantrip**.
- **Empowered Spells** (14th). Choose one school of magic; whenever casting a spell of that school **by expending a slot**, add the spellcasting ability modifier to the spell's damage or healing roll, if any.
- **Focused Casting** (20th). **Taking damage can't break concentration** on a spell.

#### Warrior *(p. 17–21)*

*"A Warrior sidekick grows in martial prowess as it fights by your side. It might be a soldier, a town guard, a battle-trained beast, or any other creature honed for combat."*

| Level | Proficiency Bonus | Features |
| --- | --- | --- |
| 1st | +2 | Bonus Proficiencies, Martial Role |
| 2nd | +2 | Second Wind (1 use) |
| 3rd | +2 | Improved Critical |
| 4th | +2 | Ability Score Improvement |
| 5th | +3 | — |
| 6th | +3 | Extra Attack (1 extra) |
| 7th | +3 | Battle Readiness |
| 8th | +3 | Ability Score Improvement |
| 9th | +4 | — |
| 10th | +4 | Improved Defense |
| 11th | +4 | Indomitable (1 use) |
| 12th | +4 | Ability Score Improvement |
| 13th | +5 | — |
| 14th | +5 | Ability Score Improvement |
| 15th | +5 | Extra Attack (2 extra) |
| 16th | +5 | Ability Score Improvement |
| 17th | +6 | — |
| 18th | +6 | Indomitable (2 uses) |
| 19th | +6 | Ability Score Improvement |
| 20th | +6 | Second Wind (2 uses) |

*Purpose: level-by-sidekick-class progression for the Warrior archetype; no roll. (Caption on p. 17; rows 3rd–20th continue onto p. 18 — reconstructed across the page break.)*

**Warrior features**

- **Bonus Proficiencies** (1st). One saving throw of your choice: Str, Dex, or Con. **Two skills** from: Acrobatics, Animal Handling, Athletics, Intimidation, Nature, Perception, Survival. Proficiency with **all armor**; if humanoid or has a simple/martial weapon in its stat block, also **shields and all simple and martial weapons**.
- **Martial Role** (1st). Choose one:
  - **Attacker.** +2 bonus to **all attack rolls**.
  - **Defender.** Reaction to impose **disadvantage** on the attack roll of a creature within **5 feet** whose target isn't the sidekick (provided the sidekick can see the attacker).
- **Second Wind** (2nd). Bonus action on its turn to regain **1d10 + its level in this class** hit points; requires a short or long rest between uses. **20th level: two uses between rests.**
- **Improved Critical** (3rd). Attack rolls score a **critical hit on 19 or 20**.
- **Ability Score Improvement** (4th, 8th, 12th, 14th, 16th, 19th). +2 to one ability or +1 to two; **cannot exceed 20**.
- **Extra Attack** (6th). Attacks **twice** instead of once on the Attack action; **three attacks at 15th level**. If it has the Multiattack action, it uses Extra Attack **or** Multiattack, not both.
- **Battle Readiness** (7th). **Advantage on initiative rolls.**
- **Improved Defense** (10th). **Armor Class increases by 1.**
- **Indomitable** (11th). **Reroll a failed saving throw** and must use the new roll; once per long rest. **18th level: two uses between long rests.**

---

### Parleying with Monsters *(p. 21)*

- Meeting a monster doesn't have to spark a fight. An **offering, like food**, can calm some hostile monsters, and sapient creatures often prefer to talk. Improvise or use the DMG social interaction rules.
- **Consider granting advantage on any ability check the characters make to communicate with a creature if they offer something it wants.** The "Monsters' Desires" section below suggests what a creature might like by type.
- Adventurers can **research** what a creature is likely to desire (see Monster Research). The DC for a relevant ability check equals **10 + the creature's challenge rating**.

#### Monster Research

| Type | Suggested Skills |
| --- | --- |
| Aberration | Arcana |
| Beast | Animal Handling, Nature, or Survival |
| Celestial | Arcana or Religion |
| Construct | Arcana |
| Dragon | Arcana, History, or Nature |
| Elemental | Arcana or Nature |
| Fey | Arcana or Nature |
| Fiend | Arcana or Religion |
| Giant | History |
| Humanoid | History |
| Monstrosity | Nature or Survival |
| Ooze | Arcana or Survival |
| Plant | Nature or Survival |
| Undead | Arcana or Religion |

*Purpose: tells the GM which skills can research a creature type; the check is **DC = 10 + that creature's CR**, not a flat number. No roll. (Caption on p. 22; rows Elemental–Undead continue onto p. 23 — reconstructed across the page break.)*

#### Monsters' Desires

Fourteen separate d4 tables, one per creature type, all headed `d4 Desired Offering`. Roll the table for the creature's type to get the offering that would pacify it (parleying it grants advantage on the communication check).

**Aberrations**

| d4 | Desired Offering |
| --- | --- |
| 1 | The brain or other organs of a rare creature |
| 2 | Flattery and obsequiousness |
| 3 | Secrets or lore it doesn't already know |
| 4 | Accepting a strange, organic graft onto your body |

**Beasts**

| d4 | Desired Offering |
| --- | --- |
| 1 | Fresh meat |
| 2 | A soothing melody |
| 3 | Brightly colored beads, cloth, feathers, or string |
| 4 | An old stuffed animal or other soft trinket |

**Celestials**

| d4 | Desired Offering |
| --- | --- |
| 1 | The tale of a heroic figure |
| 2 | An oath to do three charitable deeds before dawn |
| 3 | The crown of a defeated tyrant |
| 4 | A holy relic or treasured family heirloom |

**Constructs**

| d4 | Desired Offering |
| --- | --- |
| 1 | Oil to apply to the construct's joints |
| 2 | A magic item with charges, to be used as fuel |
| 3 | A vessel infused with elemental power |
| 4 | Adamantine or mithral components |

**Dragons**

| d4 | Desired Offering |
| --- | --- |
| 1 | Gold or gems |
| 2 | Anything from a draconic rival's hoard |
| 3 | An antique passed down at least three generations |
| 4 | A flattering artistic depiction of the dragon |

**Elementals** *(row 4 continues onto p. 25 — the caption repeats and row 4 is the only split row in this group)*

| d4 | Desired Offering |
| --- | --- |
| 1 | A gem worth at least 50 gp, which the creature eats |
| 2 | An exceedingly pure sample of a favored element |
| 3 | A way to return the elemental to its home plane |
| 4 | Performing a dance from the elemental's home plane |

**Fey**

| d4 | Desired Offering |
| --- | --- |
| 1 | The memory of your first kiss |
| 2 | The color of your eyes |
| 3 | An object of deep sentimental value to you |
| 4 | Reciting a sublime poem |

**Fiends**

| d4 | Desired Offering |
| --- | --- |
| 1 | Your soul |
| 2 | A desecrated holy object |
| 3 | Blood from a living or recently slain loved one |
| 4 | Breaking a sacred promise in the fiend's presence |

**Giants**

| d4 | Desired Offering |
| --- | --- |
| 1 | A dwarf admitting giant-craft to be superior to dwarf-craft |
| 2 | A strong working animal |
| 3 | Multiple barrels of ale |
| 4 | Treasure stolen from a rival giant |

**Humanoids** *(caption on p. 25, rows on p. 26 — reconstructed across the page break)*

| d4 | Desired Offering |
| --- | --- |
| 1 | Promising to find a lost item of great importance to their culture |
| 2 | Challenging them to a type of friendly contest, such as dancing, singing, or drinking |
| 3 | Recovering something they've lost |
| 4 | Information on a foe's secrets or weaknesses |

**Monstrosities**

| d4 | Desired Offering |
| --- | --- |
| 1 | Dislodging the stuck scraps of the creature's last meal |
| 2 | The creature's favorite food |
| 3 | Driving off the creature's rival |
| 4 | Making movements that mimic the monster's mating dance |

**Oozes**

| d4 | Desired Offering |
| --- | --- |
| 1 | A vial of putrid liquids |
| 2 | A cloth bearing a noxious odor |
| 3 | Bones or metal, which the ooze promptly absorbs |
| 4 | A gallon of any effervescent fluid |

**Plants**

| d4 | Desired Offering |
| --- | --- |
| 1 | A pound of mulch |
| 2 | Water from a spring infused with Feywild energy |
| 3 | Clearing invasive vegetation from the creature's territory |
| 4 | Destroying all axes and fire-making implements the party carries |

**Undead**

| d4 | Desired Offering |
| --- | --- |
| 1 | A vial of blood |
| 2 | A personal memento from the creature's past |
| 3 | Materials, tools, or the skills to sun-proof a crumbling mausoleum |
| 4 | Completing a task the creature was unable to finish in life |

*Purpose (all 14): roll **d4** for the creature's *type* to get one specific thing it desires; the offering feeds into the parley check (advantage on the communication check if offered). None of these are numbered as a single table in the source — they are 14 parallel d4 tables under one heading.*

---

### Environmental Hazards *(p. 27–60)*

Adds fantastical challenges to any locale and brings an adventure's setting to life. When a creature's name appears in **bold** in a table, its stat block is in the Monster Manual.

---

#### Supernatural Regions *(p. 27–47)*

A **supernatural region** is permeated by a preternatural force in an area as large or small as you wish; certain effects and brief encounters reinforce an underlying theme as characters traverse it or at a specific affected location. Each region below summarizes the region, presents a table of potential effects, and notes triggers for a random effect.

**Generic region triggers** — the effects of a region occur whenever you please, at the time each description suggests, or under one or more of these circumstances:

1. Soon after the party first enters the region
2. When a creature loses more than half its hit points
3. When a creature casts a spell of 1st level or higher
4. When a creature activates a magic item
5. When a creature makes an exceptionally loud noise or otherwise attracts attention
6. When the party spends at least 30 minutes in the same region

Each region then adds its **own** specific trigger list, which is what actually gates the table roll.

##### Blessed Radiance *(p. 28–30)*

*"The grace of the Upper Planes touches this region."* Roll when:
- A creature succeeds on a saving throw compelled by the abilities of a fiend or an undead
- A creature is the target of a cleric or paladin spell of 3rd level or higher
- A creature scores a critical hit against a fiend or an undead
- A creature experiences an epiphany or inspiring triumph in the service of righteousness or in defiance of wickedness

| d100 | Effect |
| --- | --- |
| 01–06 | Golden light fills a 20-foot-radius, 40-foot-high cylinder centered on one character in the region and then fades. That character and their friends in the cylinder gain the benefits of the *divine favor* spell for 1 hour. |
| 07–12 | Radiant energy erupts in a 10-foot-radius sphere centered on one random creature in the region. Each creature in the sphere that isn't undead regains 3d6 hit points. Each undead creature in the sphere takes 3d6 radiant damage. |
| 13–18 | Aberrations, fiends, and undead in the region have disadvantage on attack rolls and ability checks for the next 24 hours. |
| 19–24 | Each creature carrying the holy symbol of a deity from a non-evil plane while in the region gains advantage on saving throws for the next 24 hours. |
| 25–30 | One character in the region is suffused with celestial power. For 1 minute, the character's melee attacks deal an extra 2d6 radiant damage on a hit. |
| 31–36 | One simple or martial weapon that is nonmagical and carried by one character in the region gains the properties of a *mace of disruption* for 24 hours. |
| 37–42 | A flying, gleaming sword (use the **flying sword** stat block in the Monster Manual) appears within 60 feet of an aberration, a fiend, or an undead, which becomes the sword's target. The sword deals radiant damage instead of slashing damage and knows the exact location of its target while the target is within the region. The sword vanishes when it or its target is reduced to 0 hit points. |
| 43–48 | One character in the region hears whispers from celestial beings or refrains of celestial choirs. The character can ask those voices one question as if using the *commune* spell. |
| 49–54 | Aberrations, fiends, and undead in the region give off a crimson glow for 1 minute. The creatures shed dim light in a 10-foot radius, attacks against them have advantage if the attacker can see them, and the creatures can't benefit from being invisible. |
| 55–60 | Celestial power explodes in a 30-foot-radius sphere of divine light centered on an aberration, a fiend, or an undead creature within the region. Each creature in the sphere must make a **DC 15 Constitution** saving throw. On a failure, the creature takes **4d6 radiant damage** and is blinded. On a success, it takes half damage and isn't blinded. |
| 61–66 | One character in the region feels a profound sense of purpose and gains the benefit of the *bless* spell for 1 minute. They can choose two other creatures they can see to gain the spell's benefits as well. |
| 67–72 | A booming voice thunders in Celestial and can be heard throughout the region. Each creature in the region must make a **DC 15 Constitution** saving throw. On a success, the creature gains **2d10 temporary hit points**. On a failure, the creature is deafened for 1 minute. |
| 73–78 | One character in the region gains the ability to cure afflictions for 1 hour. As an action, they can cast *lesser restoration* or *greater restoration* without expending a spell slot and requiring no material components. |
| 79–84 | The effects of a *hallow* spell (save DC 17), with one of its extra effects (DM's choice), settle over the region for 24 hours. |
| 85–90 | An angelic voice rings throughout the region. Each creature there must succeed on a **DC 15 Wisdom** saving throw or perform the *grovel* option of the *command* spell. |
| 91–95 | One character in the region permanently gains resistance to necrotic damage. Reroll if you've already rolled this effect. |
| 96–00 | One character in the region gains the ability to use the **Divine Intervention** cleric feature, which succeeds automatically. The character can use the feature granted in this way only once and must use it within 7 days. Reroll if you've already rolled this effect. |

*Purpose: roll **d100** to produce a one-off or timed supernatural effect in a radiant/Upper-Planes-themed region. 17 rows, ranges sized 5 or 6 wide; 91–95 and 96–00 are "reroll if already rolled". (Caption on p. 29; rows 31–36 onward continue onto p. 30 — reconstructed across the page break.)*

##### Far Realm *(p. 30–33)*

As souls travel away from the Material Plane after death they dwell in the Astral Plane as spirits or are pulled toward an Outer Plane — but some entities find ways to travel beyond the Outer Planes to dwell in the **Far Realm**, transforming over eons into abominations or elder evils, seething in a reality with its own laws. All who stay are eventually twisted into alien shapes. The Far Realm's pernicious influence is often subtle, leaking into the Material Plane through **thin places in reality** or as **invasive thoughts** that inspire life to propagate along alien paths. Roll when:
- A warlock whose Otherworldly Patron is a **Great Old One** rolls a **1 or 20** on the d20 for an ability check, attack roll, or saving throw
- The characters take a short or long rest in the region
- A creature spends **more than an hour** reading an eldritch tome written by those who have seen or otherwise interacted with the Far Realm

| d100 | Effect |
| --- | --- |
| 01–09 | A structure in the region whispers faintly. Any creature within 60 feet of the structure that can hear it must succeed on a **DC 12 Wisdom** saving throw or be **charmed**. While charmed, it must move toward the source, avoiding obvious hazards. On reaching the source it is **incapacitated**. It can repeat the save when it takes damage and at the end of every hour, ending the effect on a success. |
| 10–18 | An elder evil turns its attention to the region. Any creature that finishes a rest in the region must succeed on a **DC 12 Charisma** saving throw or gain **no benefit** from finishing the rest. It instead finds strange scrawls, stacked stones, or its belongings arranged in intricate, abstruse patterns nearby. |
| 19–27 | Local plants and animals share a malevolent intelligence. Roll a **d6**. On a 1–2, an *insect plague* spell is centered on one random creature. On a 3–4, 1d4 swarms of ravens and 1d4 swarms of rats gather and attack any other creatures. On a 5–6, a **treant** (forested terrain) or a **galeb duhr** (rockier terrain) attacks. |
| 28–36 | Distance no longer functions in a comprehensible manner within the region. Creatures make **ranged attack rolls with disadvantage**, and the **range of those attacks is halved**. |
| 37–45 | The landscape melts into a mass of writhing flesh, eyes, and fanged mouths. From an unoccupied space in the fleshy ground arise **1d4 + 5 gibbering mouthers** that attack anyone in sight. |
| 46–54 | Unintelligible murmurings threaten to overcome the mind of one random creature. At the start of its turn it must succeed on a **DC 13 Intelligence** saving throw or use its action to make one melee attack against the nearest creature it can see. If there are no other creatures within reach, the target spends its action babbling. |
| 55–63 | Bizarre appendages squirm beneath the ground and around trees or structures. Dozens of limbs burst forth, entangling anyone within a **30-foot sphere** surrounding one random creature. Each creature in the sphere must succeed on a **DC 14 Dexterity** saving throw or take **3d6 bludgeoning** and be **restrained**. Any creature that ends its turn in the area takes 3d6 bludgeoning. A creature can free itself or someone else within reach by using an action to make a successful **DC 14 Strength or Dexterity** check (its choice). |
| 64–72 | Creatures in the region can't leave it and find themselves covering the same ground over and over. By the time they realize this, **2d10 hours** have passed with no progress. The effect then ends, and each creature must succeed on a **DC 10 Constitution** saving throw or gain **1 level of exhaustion**. |
| 73–79 | One random creature hears strange whispers and must succeed on a **DC 14 Wisdom** saving throw or become charmed. While charmed, it focuses on copying the blasphemous designs that appear in its mind using whatever medium it has available (ink, charcoal, mud, or its own blood). Unless restrained, it completes the designs in **1 hour of work**. When it finishes, it is no longer charmed, and a **death slaad** appears within 30 feet of it and attacks anyone in sight. |
| 80–85 | Natural features and structures writhe to spell out words and form strange symbols. Any creature that tries to read the messages must make a **DC 20 Intelligence (Arcana)** check. On a success, the creature gains *insight* as if it had cast *contact other plane*. On a failure, it is affected as if it failed a saving throw against *confusion*. This effect ends at the end of the creature's next turn. |
| 86–90 | In this region, circular things (buttons, crystal balls, the sun, and so on) seem appallingly wrong. One random creature that starts its turn in this region must succeed on a **DC 14 Intelligence** saving throw or spend their turn loudly trying to destroy these objects. |
| 91–95 | Glaring eyes, which weep viscid tears, appear on inanimate objects throughout the region. These eyes watch the characters, and creatures within the region **can't be surprised** by the characters for as long as the eyes exist. An eye closes and disappears if it takes any damage. Reroll if you've already rolled this effect. |
| 96–00 | A tear in reality creates a **rift** in the region, similar to *gate*, that passes through the Far Realm and connects with a random plane. Any creature that enters the rift takes **10d10 psychic** damage and appears in an empty space closest to the rift's opening on another random plane. The rift vanishes after **2d10 + 2 hours**. |

*Purpose: roll **d100** for a reality-warping eldritch effect in a Far-Realm-tainted region; one row (19–27) rolls a nested **d6** for the creature type. 13 rows with 9-wide ranges. 91–95 is "reroll if already rolled". (Caption on p. 32; the 73–79 row continues onto p. 33 — reconstructed across the page break.)*

##### Haunted *(p. 33–36)*

*"Haunted environs include homes burdened by wicked deeds, the sites of mass killings, and locations where individuals died while experiencing powerful fear, sorrow, or hatred. Haunted places bear echoes of the past and, like ghosts, harass visitors even as they seek respite from age-old traumas."* Roll when:
- A creature gains the **frightened** condition
- Multiple creatures are **unable to see**
- A creature is **alone**
- **Midnight or another ominous hour** arrives
- A ghost or other creature tied to the region's grim history **menaces the party**

| d100 | Effect |
| --- | --- |
| 01–05 | A violent thunderstorm begins, centered over the region. It doesn't end until the party leaves the region. |
| 06–10 | A random building in the region gains the benefits of *guards and wards* (save DC 13) for the next 24 hours. |
| 11–15 | A mundane part of one random character's surroundings — perhaps a tree bole or a stuffed animal head — **animates for 1 minute** and whispers a warning or threatens to reveal one of the character's secrets. |
| 16–20 | All bright light weakens to dim light for 24 hours. Sources that provide dim light, such as candles, do not shed any light. |
| 21–25 | The temperature in the region drops by **10 degrees Fahrenheit every hour** for the next **1d6 hours**, after which it returns to normal. If cold enough, ice crystals form in sinister patterns. |
| 26–30 | One random creature's **shadow acts independently** for the next 24 hours, out of sync with its owner, perhaps dramatically choking or trying to murder another shadow. |
| 31–35 | After the next sunset, the sun doesn't rise again for **36 hours**. The sky may hold a crimson moon, be obscured by roiling fog, or display blinking, alien stars. |
| 36–40 | During the next night, one random **sleeping** creature vanishes and reappears approximately **a foot** beneath where they were sleeping — buried in undisturbed dirt or beneath floorboards. The creature or someone else can free it with a successful **DC 13 Strength (Athletics)** check. |
| 41–45 | One random creature in the region is targeted by *levitate* (save DC 15) for 1 minute. |
| 46–50 | A nonviolent but unsettling ghost — a pet, an accident-prone child, a dismembered big toe — appears and follows one random creature for 24 hours before vanishing. It vanishes if reduced to 0 hit points. |
| 51–55 | One player character's **appearance changes** for 24 hours to reflect the region's haunted history (e.g. the distinctive facial scar of a notorious tyrant who died in the region). |
| 56–60 | For 24 hours, any humanoid killed in the region rapidly decomposes and **rises as a skeleton 1d10 minutes after dying**. |
| 61–65 | Over 24 hours, whenever any creature is wounded, its blood (or similar fluid) spreads to form a **short message or grisly tableau**. |
| 66–70 | A spirit inhabits one character's simple or martial weapon, making it a **sentient magic item** until the character leaves the region. Randomly generate the item's properties per the DMG's "Sentient Magic Items" section. |
| 71–75 | A spectral force manifests to one character, allowing them to ask one question and receive a short answer as through *augury*. The force manifests as a planchette moving on a talking board, writing on foggy glass, or insects swarming to create messages. |
| 76–80 | During the next night, one sleeping character receives a **vision** as if the target of *dream*. The dream is brief and unsettling, revealing some element of the environment's history and putting the character in the place of someone who suffered a grim fate there. |
| 81–85 | A coffin or small enclosed space in the region — an antique box, stone cairn, or tree stump sealed with rocks — radiates palpable malice. The **first** time a creature opens it, **roll a die**: on an **even** number, the creature receives a terrible vision and is frightened of all creatures for 24 hours; on an **odd** number, an **avatar of death** appears and attacks as though summoned by the *Skull* card from a deck of many things. |
| 86–90 | Over 24 hours, whenever any creature in the region regains hit points from a spell, the healing magic leaves **scars** — possibly with purging black bile or a spectral force tearing free. These scars can be removed only by *greater restoration* or *wish*. |
| 91–95 | For 24 hours, a luminous wisp of vapor floats above a corpse or grave. If put in a container, a creature holding the receptacle can cast *resurrection* **once**, requiring no components and causing the wisp to vanish. Any creature returned to life experiences strange dreams. |
| 96–00 | A mysterious mist rises from the shadows. Dense fog heavily obscures everything in a **50-foot-radius sphere** around one random creature. Any creature that starts its turn in the mist must succeed on a **DC 10 Constitution** saving throw or gain **1 level of exhaustion**; that exhaustion **can't be removed** while the creature is in the mist. Creatures notice unsettling sights through the fog. The mists can't be dispersed by any wind, but clear after **1 minute**. |

*Purpose: roll **d100** for a ghostly/psychological effect in a haunted region; one row (81–85) embeds a **roll a die** even/odd branch. 20 rows, 5-wide ranges throughout. (Caption on p. 34; rows 26–30 onward continue across pp. 35–36 — reconstructed.)*

##### Infested *(p. 36–39)*

*"On many worlds, the biomass of insects radically outweighs that of higher organisms… through wild population booms, magical manipulation, supernatural growth, interbreeding with otherworldly species, or stranger circumstances, insects can overrun an entire region."* Swarm insects become the dominant species, consuming plants and animals, creating elaborate hives or tunnels, and infesting structures and the earth. Roll when:
- **Webs, cocoons, hives, anthills**, or other insect dwellings are disturbed
- A creature **attacks an insect swarm** or a **Small or larger insect** (giant centipede, giant spider) in the region
- A creature **begins a short or long rest**

| d100 | Effect |
| --- | --- |
| 01–05 | Intense buzzing or grinding noises fill the region for 24 hours. Except for truly cacophonous sounds, creatures can only hear speech and noises originating **within 10 feet** of them. |
| 06–10 | A **mass migration** of insects begins, waves of Tiny bugs crawling over everything. Creatures **cannot take a short or long rest** in the region for 24 hours. |
| 11–15 | A swarm of **bioluminescent flies** converges on one random creature. For the next **minute** the creature sheds dim light in a 10-foot radius, any attack against it has advantage if the attacker can see it, and it can't benefit from being invisible. |
| 16–20 | A **boil of termites** bursts from the ground, along with dozens of bones and a treasure of the DM's choice (see "Random Treasure" in the DMG). |
| 21–25 | A **cricket-shaped creature with the statistics of a cat** bounds up to one random creature and follows it like an affectionate pet for 24 hours before scampering off. |
| 26–30 | A cluster of **1d4 + 2 faintly glowing grubs** appears in an unoccupied space within 30 feet of the party. Any creature that consumes one receives the benefits of a *potion of healing*. |
| 31–35 | A large, psychedelically colored **moth** flies over the party, dusting the characters with strange powder. Creatures the moth flies over must succeed on a **DC 16 Constitution** saving throw or be **charmed by all creatures** for 1 hour. |
| 36–45 | The region is choked with **wispy webbing, which acts as difficult terrain**. |
| 46–50 | Nearly every surface is covered with discarded **cicada-like shells** that crunch loudly when trod upon, imposing **disadvantage on Dexterity (Stealth)** checks made while moving across them. The shells vanish after 1 hour. |
| 51–55 | A massive, bloated **maggot** emerges from the ground within 10 feet of the party and bursts, covering the ground with ichor in a **10-foot square**. This region is affected by *grease* (save DC 13) for 1 minute. |
| 56–60 | The ground opens up beneath one random creature, creating a **quicksand pit** (see the DMG). |
| 61–65 | One random creature must succeed on a **DC 16 Constitution** saving throw or contract the **sight rot** disease from minute parasites. |
| 66–70 | **Dung-colored bugs** cover the ground. Creatures moving at **half their normal walking speed** can ignore the bugs; those moving faster must succeed on a **DC 16 Constitution** saving throw or become **poisoned** until the start of their next turn, speed reduced to 0. Creatures that don't need to breathe **automatically succeed**. |
| 71–75 | One of the characters must succeed on a **DC 15 Wisdom** saving throw or be transformed into a **giant spider**, as if by *polymorph*. Lasts 1 hour or until dispelled. |
| 76–80 | One random creature must succeed on a **DC 16 Constitution** saving throw or acquire a ravenous **silverfish infestation** among its gear, discovered the next time it finishes a short or long rest. If the creature has any paper material, the silverfish destroy one random book or other **nonmagical** paper item. |
| 81–85 | One random creature must succeed on a **DC 16 Constitution** saving throw or become host to a particularly aggressive **tapeworm**, gaining no benefit from eating until it receives treatment that removes a disease. A creature immune to disease **automatically succeeds**. |
| 86–90 | **Biting mites** infest creatures' clothing. Any creature wearing **medium or heavy armor** has disadvantage on attack rolls, ability checks, and saving throws for 24 hours. |
| 91–95 | **Tiny arachnids** invade unattended spaces. The next time one random creature dons its clothing or armor after finishing a long rest, it must succeed on a **DC 16 Constitution** saving throw or take **11 (2d10) poison** damage. |
| 96–00 | Countless tiny, bloodsucking insects infest the region for the next **1d6 hours**. **Every hour**, each creature in the region must succeed on a **DC 10 Constitution** saving throw or gain **1 level of exhaustion**. Creatures **immune to disease** are unaffected. |

*Purpose: roll **d100** for an insect/vermin hazard; several rows roll **1d4+2 grubs**, **1d6 hours**, or a **per-hour** repeat save, so this table suits a tick/turn scheduler. 19 rows — note the **36–45** range is double-width (10 wide) in the source. (Caption on p. 37; rows 26–30 onward continue across pp. 38–39 — reconstructed.)*

##### Mirror Zone *(p. 39–42)*

*"A mirror zone occurs where planar and magical energies converge and create a place of reflections. Creatures, objects, and energy reflect, refract, duplicate, or are transported elsewhere."* Roll when:
- A creature **shatters a mirror**
- A creature uses **any teleportation magic**
- An **illusion** appears
- A creature **impersonates** another creature

| d100 | Effect |
| --- | --- |
| 01–06 | Creatures in the region begin to **display features other than their own** for 24 hours. Affected creatures have **advantage on Charisma (Deception)** checks and ability checks made to disguise themselves. |
| 07–12 | The *hallucinatory terrain* spell (save DC 15) affects the natural terrain of the region, changing it to a different kind of terrain (DM's choice). |
| 13–18 | One random creature gains the benefits of *blink* for 1 minute, shimmering with overlapping shattered reflections. |
| 19–24 | Creatures in the region **don't cast reflections**. **Wisdom (Insight)** checks made against them have **disadvantage**, and they have disadvantage on **Charisma (Persuasion)** checks made against anyone who notices. When they leave the region, reflections return and the effect ends. |
| 25–34 | Reflections of **1d4 creatures** emerge from mirrors and attack. The reflections are two-dimensional shimmering versions of the creatures that cast them. Treat the reflections as **shadows that are fey instead of undead and vulnerable to bludgeoning damage instead of radiant**. |
| 35–40 | One character gains the benefit of *mirror image*. The images created sometimes move or speak of their own volition. |
| 41–46 | For 24 hours, certain wounds caused in the region attract **spectral slivers of glass**. Any creature (other than a construct or an undead) hit by an attack dealing **piercing or slashing** damage begins to **bleed**, losing **1d4** hit points at the start of each of its turns; another such hit increases the bleeding by 1d4. Any creature can take an action to stanch the wound with a successful **DC 10 Wisdom (Medicine)** check. Bleeding also stops if the target receives **magical healing**. |
| 47–52 | Mirrors and other highly reflective surfaces allow **magical transport**. Any creature that touches its reflection in an object it **isn't wearing or carrying** can immediately cast *misty step*, requiring no components. |
| 53–58 | One character can cast *scrying* (save DC 17) **once** within the next 24 hours, requiring no components but using a mirror or other reflective surface. |
| 59–64 | The skin of one random creature becomes **silvery and reflective** for 24 hours: **advantage on saving throws against spells**, and **spell attacks have disadvantage** against that creature. |
| 65–70 | A longsword or shortsword with a **jagged mirror** blade appears in an unoccupied space within 60 feet of a random creature. The weapon is a *sword of wounding*. If the wielder rolls a **1 or 20** on an attack roll using the weapon, the weapon **shatters and is destroyed** after that attack. |
| 71–76 | For 24 hours, when anyone in the region hits a creature with an attack roll and deals damage, the attacker must succeed on a **DC 13 Charisma** saving throw or take **force damage equal to half the damage dealt**. |
| 77–82 | Two shimmering, vertical, reflective **disks of energy** appear in unoccupied spaces for 1 minute. Each is **6 feet in diameter** and floats 1 foot above the ground. One appears within 30 feet of the party. Any creature that **moves through** a disk instantly appears within 5 feet of the other disk or the nearest unoccupied space. |
| 83–88 | The next time one character sees their reflection in the region, that reflection **comes to life** and engages its counterpart in conversation. It offers to answer one question posed to it as if the creature cast *divination*. After answering, the reflection returns to normal. |
| 89–94 | **Floating shards of broken mirrors** swirl through the region, showing reflections of creatures and places that aren't present, for the next **minute** before vanishing. On **initiative count 20** (losing all ties), the shards make a **ranged weapon attack (+6 to hit)** against one random creature. On a hit, the target takes **10 (3d6) slashing** damage. |
| 95–00 | A **duplicate** of one random creature appears in an unoccupied space within 30 feet of that creature. The duplicate's appearance, game statistics, and equipment are **identical**. It immediately attacks the creature, seeking to slay it. If the duplicate dies, it and all its equipment shatter into mirror shards. If the duplicate fails to slay the creature within **1 hour**, it vanishes. |

*Purpose: roll **d100** for a reflection/duplication effect; row 25–34 rolls **1d4** affected creatures. 16 rows — the **25–34** range is 10 wide in the source. (Caption on p. 40; rows 35–40 onward continue across pp. 41–42 — reconstructed.)*

##### Psychic Resonance *(p. 42–44)*

*"In an area of psychic resonance, magic imposes strange effects on creatures and objects. These manifestations stem from strong emotions combined with magic use or from the presence of psionic creatures."* Roll when:
- A creature **endures a powerful emotional experience**
- A creature takes psychic damage **greater than its Constitution score**
- A creature becomes **charmed or frightened**
- A creature experiences **telepathic communication**

| d100 | Effect |
| --- | --- |
| 01–06 | One random creature gains the ability to cast *detect thoughts* (save DC 13) **once** over the next 24 hours, requiring no components. Intelligence is the spellcasting ability for this spell. |
| 07–12 | One random creature is affected by *mind blank* for the next 24 hours. |
| 13–18 | For **1 minute on initiative count 20** (losing all ties), **Tiny and Small** objects in the region that aren't being worn or carried are flung by an unseen force. One random creature must succeed on a **DC 15 Dexterity** saving throw or take **2d4 bludgeoning** damage from the flung objects. |
| 19–24 | **Memories become sharp and clear for 1 hour.** During this time, each creature in the region adds **double its proficiency bonus** to Intelligence checks made to recall information. |
| 25–34 | **Headaches and nosebleeds** plague humanoids in the region, imposing **disadvantage on Wisdom (Perception)** checks for 1 hour. |
| 35–40 | **Psychic power builds** in the mind of one random creature. Once within the next minute, the creature can use a **bonus action** to magically assault the mind of another creature it can see. The target must succeed on a **DC 14 Intelligence** saving throw or take **4d10 psychic** damage. |
| 41–46 | **Lurking fears become nightmares.** Any creature that finishes a short or long rest in the region must succeed on a **DC 10 Wisdom** saving throw or **gain no benefit** for finishing the rest. |
| 47–52 | For 1 hour, each creature in the region gains the ability to **communicate telepathically** with any creature it can see within 60 feet. If the target understands any languages, it can respond telepathically. |
| 53–58 | One random creature can **sense the presence of nearby minds** for 1 hour, gaining **advantage on Wisdom (Perception)** checks made to locate other creatures within 120 feet, even creatures behind total cover. |
| 59–64 | Creatures suffer from **disjointed thoughts and difficulty concentrating** for 1 hour: **disadvantage on Intelligence checks** and **Constitution saving throws to maintain concentration** on spells. |
| 65–70 | One random creature **hears strange whispers in its mind** — fragments of thoughts from other creatures nearby. **Advantage on Wisdom (Insight)** checks for 1 hour. |
| 71–76 | One random creature gains the ability to cast *telekinesis* (save DC 15) **once** over the next 24 hours, requiring no components. Intelligence is the spellcasting ability for this spell. |
| 77–82 | Thoughts in the region attract **ambient psychic energy, forming protective fields** around creatures' minds. Creatures in the region gain **resistance to psychic damage** for the next hour. |
| 83–88 | For **1 minute on initiative count 20** (losing all ties), one random creature in the region must succeed on a **DC 15 Intelligence** saving throw or take **2d6 psychic** damage. |
| 89–94 | **Compassion and joy** fill the mind of one random creature for 1 minute. The creature has **advantage on Intelligence, Wisdom, and Charisma saving throws** and **disadvantage on attack rolls**. |
| 95–00 | The mind of every **beast** in the region is flooded with psychic energy. Each beast's **Intelligence score becomes 10** if it wasn't already higher, and it gains the ability to **speak Common and Sylvan fluently**. **These changes are permanent.** |

*Purpose: roll **d100** for a psionic/emotional effect; two rows (13–18, 83–88) fire on **initiative count 20** for a 1-minute duration, so they need a repeated-tick handler. 16 rows — the **25–34** range is 10 wide in the source. (Caption on p. 43; the 35–40 row continues onto p. 44 — reconstructed.)*

##### Unraveling Magic *(p. 45–47)*

*"The source of magic is damaged or corrupted in this region. Magic is unpredictable, and strange results occur when a creature casts a spell."* Such regions come from potent rituals gone awry (or succeeding, in the case of dangerous undertakings), the aftermath of cataclysmic magical battles, or where an artifact was destroyed. Roll when:
- Any **charges are expended** in a magic item
- A **spell slot of 1st level or higher** is expended
- A **dragon, a fey, or an elemental of challenge rating 5 or higher dies**

| d100 | Effect |
| --- | --- |
| 01–05 | All **magic items** in the region temporarily **lose their magical properties**, becoming nonmagical for 1 hour. **Artifacts are unaffected.** When the items regain their magic, a creature's **attunement to any of them is restored**. |
| 06–10 | The region becomes a **dead-magic zone** for 1 hour: the entire region is affected by *antimagic field*. |
| 11–15 | One random creature must succeed on a **DC 15 Dexterity** saving throw or be enclosed in **Otiluke's resilient sphere** for 1 minute. |
| 16–20 | One random creature that has expended spell slots **regains one** expended spell slot of a random level. |
| 21–25 | **Flares of magical energy** flash through the region for 1 minute. Each **round on initiative count 20** (losing all ties) one random creature takes **2d4 damage of a type determined by a d6**: 1, acid; 2, cold; 3, fire; 4, force; 5, lightning; or 6, thunder. |
| 26–30 | One of the characters must succeed on a **DC 15 Wisdom** saving throw or be transformed into a **blink dog**, as if by *polymorph*. Lasts 1 hour or until dispelled. |
| 31–35 | One random creature that has spell slots **expends one spell slot** of a random level in a harmless shower of sparks and sounds. |
| 36–40 | All fire in the region **freezes into ice** that gives off a blue light equal to the illumination it normally provides. In addition, the region **radiates extreme cold** for 1 day. |
| 41–45 | One random creature with spell slots becomes a **focal point for ambient magic** for 1 hour. At the end of each of the creature's turns, other creatures within 10 feet of it must succeed on a **Dexterity saving throw against the spellcaster's spell save DC** or take **1d6 force** damage. |
| 46–50 | The *flaming sphere* spell (save DC 15) spontaneously activates in an unoccupied space within 5 feet of the party. On **initiative count 20** (losing all ties), the sphere moves 30 feet toward the nearest creature. The sphere vanishes after 1 minute. |
| 51–55 | **Simple or martial weapons** in the region that are nonmagical **crackle with power**. For 1 hour they become magic weapons granting a **+1 bonus** to attack and damage rolls. |
| 56–60 | **Swirling energy** surrounds one random creature for 24 hours. It gains **resistance to force damage** and its **speed is reduced by 10 feet**. |
| 61–65 | Each character in the region **suddenly learns some magic**: one wizard cantrip of the character's choice, known for **1d8 days**. |
| 66–70 | One random creature **crackles with sparks of light** for 1 hour, magically shedding **bright light in a 10-foot radius and dim light for an additional 10 feet**. Any creature it touches (requiring an **unarmed strike** if the target is unwilling) takes **1d6 force** damage. |
| 71–75 | **Lightning arcs** in a **5-foot wide line** between two creatures within 30 feet of each other and not behind total cover. Each creature in the line (including the two) must make a **DC 13 Dexterity** saving throw, taking **4d6 lightning** damage on a failed save or half as much on a successful one. |
| 76–80 | The *reverse gravity* spell (save DC 18) activates for 1 minute, centered on the ground beneath one random creature. |
| 81–85 | On **initiative count 20** (losing all ties), **two random creatures** must each make a **DC 15 Charisma** saving throw. If **either** save fails, the creatures magically teleport, **switching places**. If both succeed, they don't teleport. |
| 86–90 | One random creature **breaks spells** for 1 hour. Whenever anyone within 20 feet of it casts a spell, the caster must succeed on a **DC 15 saving throw using its spellcasting ability**, or the spell drains away without effect. The slot, charge, or feature use that powered it is wasted. |
| 91–95 | During the next 24 hours, the **first** time a creature in the region targets another creature with a spell, the caster must make a **DC 11 saving throw using its spellcasting ability**. On a failed save, the spell **targets the caster instead**; on a successful save it functions normally. The effect then ends. |
| 96–00 | One random creature can suddenly cast ***wish*** once, within the next minute. Reroll if you've rolled this effect in the past 24 hours. |

*Purpose: roll **d100** for a corrupted-magic effect; row 21–25 rolls a nested **d6** for the damage type. 20 rows, 5-wide ranges throughout. (Caption on p. 46; rows 66–70 onward continue onto p. 47 — reconstructed.)*

---

#### Magical Phenomena *(p. 47–58)*

*"Magic has the ability to make even the most serene natural settings unpredictable."*

##### Eldritch Storms *(p. 47–49)*

When magical currents become trapped amid winds and clouds, eldritch storms can result. Four types:

- **Flaywind.** Supernaturally powerful winds (like those from planes such as Pandemonium or Minethys, the third layer of Carceri) spawn flaywinds: an intense sandstorm gathering large rocks and other debris in addition to sand or grit. The area within the storm is **heavily obscured**, and a creature exposed takes **1d4 slashing damage at the start of each of its turns**. Only **substantial cover or shelter** protects against the flensing grit. A flaywind leaves **4d6 feet** of sand or debris in its wake. A successful **DC 15 Intelligence (Arcana) or (Nature) check, or Wisdom (Survival) check**, lets a character recognize a flaywind **1 minute before it strikes**. Typically lasts **1d4 × 10 hours**.
- **Flame Storm.** Sooty thunderclouds shot through with red and orange lightning release a deluge of fiery droplets. Any creature caught in the burning rain takes **2d6 fire damage at the start of each of its turns**. Droplets ignite any flammable objects that aren't being worn or carried; otherwise they burn out immediately. Smoke, soot, crackle, and low roar impose **disadvantage on Wisdom (Perception) checks and ranged attack rolls**. Usually lasts **2d4 minutes**, though the originating storm clouds can persist for days, creating multiple flame storms.
- **Necrotic Tempest.** Storms infused with the essence of death roil with dark clouds manifesting leering skulls and bone-white lightning. Any creature exposed that isn't a construct or an undead must succeed on a **DC 13 Constitution saving throw at the end of each minute** or take **3d6 necrotic** damage. A creature that dies **rises as a skeleton or zombie (your choice) 1d10 minutes later**. Lasts **1d4 hours** and leaves crops withered and wells undrinkable for **1d4 days** after its passing.
- **Thrym's Howl.** Bone-chilling blizzards drive a wall of wind and snow like a living glacier. The storm projects **extreme cold**. Due to the howling wind and dense blue-white ice particles, the area is **heavily obscured**, and **ranged attack rolls and Wisdom (Perception) checks** made within it have **disadvantage**. Any creature exposed at the start of its turn takes **2d6 cold damage** and **can't regain hit points** until it spends at least **1 hour in a warm environment**. A creature that dies in the storm **freezes solid**. Creatures **immune to cold damage** are immune to the effects and can see normally within it. Typically lasts **2d10 hours**.

##### Emotional Echoes *(p. 48–50)*

A place becomes infused with the powerful emotions of those who once dwelt, worked, celebrated, or suffered there; an area is typically associated with **one common emotion** and might be as small as a room or as large as a forest. **Once per day**, if a creature within the area expresses even the faintest hint of the prevailing emotion, the land seeks to hold onto that creature and inspire it to produce more of the feeling: the creature is targeted by a **suggestion** spell (**DC 16**), with the intent of making it **linger in the area and perform an act related to the associated emotion**. The effect lasts **24 hours**.

*(Source presents these as a prose list; tabulated here without changing content.)*

| Emotion | Where it appears | How it typically influences creatures |
| --- | --- | --- |
| Boldness | Battlefields and echoing canyons | Encourages creatures to shout hidden truths and act out their greatest victories |
| Doubt | Around cliffs or deserts | Makes creatures hesitate, mistrusting their ability to climb or escape their current difficulties |
| Fear | Caves and ruins | Overwhelms creatures with dread and urges them to give voice to their deepest fears |
| Hatred | Volcanic regions | Provokes creatures to scream and destroy things |
| Inspiration | Around memorials or natural wonders | Causes creatures to create works of art on the spot and obsess over them |
| Joy | Glens or flowering fields | Inspires creatures to dance, relax, and sing |
| Love | Along beaches or orchards | Encourages creatures to confess their love to others and endlessly list their favorite things |
| Sorrow | Ruins and swamps, particularly around quicksand | Overwhelms creatures with sobbing and confessions of regret |

*Purpose: pick or assign one of eight **emotions** to a locale; the mechanic is a once-per-day **DC 16 suggestion** (24 h). No roll on the table itself — the table is the designer's palette.*

##### Enchanted Springs *(p. 50–52)*

Enchanted springs brim with miraculous waters, whether they tap into magical sources hidden beneath the earth or are blessed by eldritch beings. Creatures might **bathe or drink** from the pools and temporarily gain a measure of the waters' magic. All manner of protectors or covetous guardians might lurk around these springs, driving off strangers or demanding a worthy price. Some springs are **tainted** (e.g. waters long ago polluted by the ichor of an evil entity); folk still seek them out, to purify or to claim their foul powers.

- **Trigger:** creatures might need to **drink** the water, **simply touch** it, or **bathe in it for a minute** to trigger an effect.
- **Bottling** an enchanted spring's water **removes its magical properties**, unless the bottle is a specially prepared **vial blessed by whatever being enchanted the spring** in the first place.

| d12 | Effect |
| --- | --- |
| 1 | Any creature that **touches or drinks** the water of this spring feels blessed. The creature gains the benefits of a *bless* spell for 1 hour. |
| 2 | **Bathing** in the spring covers a creature with a glowing coat of **golden feathers**. While the creature isn't wearing armor, the feathers grant a **+1 bonus to AC**. The feathers vanish after **1d4 days**. |
| 3 | A creature that touches or drinks the water of this spring develops an overwhelming desire to **sing**. Every sentence the creature speaks for the next 24 hours rings with lyrical splendor, which grants it **advantage on all Charisma checks**. |
| 4 | Bathing in the spring grants the benefits of the *greater restoration* spell. As a side effect, the creature's skin, hair, and eyes become a shimmering golden color for **1d4 days**. |
| 5 | Bathing in the spring grants the benefits of the *spider climb* spell for 24 hours. |
| 6 | A creature that touches or drinks the water of this spring grows the **tail of its favorite animal**. The tail is not under the creature's control; it moves or reacts to emotions. The tail vanishes after 24 hours. |
| 7 | Any creature with an **Intelligence score of 6 or higher** that touches or drinks the water gains **advantage on Wisdom (Insight) checks** and can cast *detect thoughts* **once**, requiring no components. The effects of the spring fade when either the spell is used or 24 hours pass, whichever happens first. |
| 8 | Bathing in the spring causes **1d10 flowers** to grow from a creature's head. The flowers smell lovely and renew their vitality and scent every day. The flowers vanish after **7 days**. |
| 9 | A creature that touches or drinks the water of this spring grows **1d4 eyestalks**. These let the creature see in all directions and grant **advantage on Wisdom (Perception) checks that rely on sight**. The eyestalks vanish after **1d4 days**. |
| 10 | Bathing in the spring causes a creature's **voice to sound sinister**. For the next 24 hours the creature's voice grants **advantage on Charisma (Intimidation) checks** and **disadvantage on Charisma (Deception) and Charisma (Persuasion) checks**. |
| 11 | A creature that touches or drinks the water of this spring grows a set of **donkey ears**. The ears grant the creature **advantage on Wisdom (Perception) checks that rely on hearing**. The ears vanish after **1d4 days**. |
| 12 | Bathing in the spring causes a creature to develop a **third eye** on its forehead. The eye grants the creature **truesight out to a range of 60 feet**. The eye vanishes after 24 hours. |

*Purpose: roll **d12** for the effect of one enchanted/tainted spring; the trigger (drink / touch / bathe 1 minute) is chosen by the designer, and some rows roll nested dice (**1d10 flowers**, **1d4 eyestalks**, **1d4 days**). (Caption on p. 51; rows 7–12 continue onto p. 52 — reconstructed.)*

##### Magic Mushrooms *(p. 52–53)*

Mushrooms can be deadly, delicious, or both; some have magical properties, especially those growing in areas suffused by mystical energy, such as the Underdark and the Feywild. Creatures **proficient in the Medicine, Nature, or Survival** skills might be versed on the subject, especially the magical kind, since beneficial effects can save lives or bestow unusual powers — but when an **unknown** variety is encountered, **only an expert can identify it and determine its properties**. To determine the effects of eating such fungus, roll the table.

| d10 | Effect |
| --- | --- |
| 1 | The creature's **skin turns an unusual color**. Roll a **d4**: 1, purple with yellow splotches; 2, bright orange with tiger stripes; 3, tree-frog green with red squiggles; 4, hot pink with yellow spots. This change is **permanent** unless removed by a *greater restoration* spell or similar magic. |
| 2 | The creature gains the **enlarge or reduce** effect (**50 percent chance of either**) of the *enlarge/reduce* spell for 1 hour. |
| 3 | The creature **regains 5d8 + 20 hit points**. |
| 4 | Vocally, the creature can only **cluck and croon like a chicken**. It can also understand and speak to chickens. This curse lasts 1 hour unless ended by a *remove curse* spell or similar magic. |
| 5 | The creature can **understand and speak all languages** for 1d4 days. |
| 6 | The creature gains the benefits of the *telepathy* spell for the next 24 hours. |
| 7 | The creature gains the benefits of the *speak with plants* spell for 8 hours. |
| 8 | The creature **immediately casts *time stop***, requiring no components. **Constitution** is the spellcasting ability for this spell. |
| 9 | The creature **immediately casts *detect thoughts***, requiring no components. **Constitution** is the spellcasting ability for this spell. |
| 10 | **Magical mists** pour out of the creature's eyes and ears, acting as a ***fog cloud*** spell for 1 hour, centered on the creature and **moving with it**. |

*Purpose: roll **d10** for the effect of eating an unidentified magic mushroom; row 1 embeds a **d4** and a 50/50 coin flip, and several rows are *instant casts*. Expert (Medicine/Nature/Survival proficiency) knowledge is the gate on identification. (Caption at the bottom of p. 52, rows on p. 53 — reconstructed.)*

##### Mimic Colonies *(p. 53–56)*

Mimics imitate terrain and dungeon dressing to hunt for food. Rare specimens develop a deeper understanding of the world and can **communicate with other creatures**. In extremely rare cases groups band together into **colonies**; these bonded mimics cooperate to create larger objects than any lone mimic could approximate — **buildings, bridges, crystal formations, cliff faces, statues, and nearly anything it desires**. Entire villages appearing out of nowhere might be composed of mimics.

- **Mimic Communication.** Colony members develop **telepathy and the ability to speak**. While **within 10 miles of the colony**, any mimic can communicate telepathically with other creatures **within 120 feet** of it and can speak **Common and Undercommon** fluently (or two other languages of the DM's choice). The colony's **offspring** gain these abilities **innately** and can use them even away from the colony, as shown in the **Juvenile Mimic** stat block.
- **Confronting a Colony.** The primary goal is survival. If threatened by a force the mimics can't overcome, they are willing to **bargain**: adventurers they can't defeat can be **bought off** with information about nearby creatures or locations, **hidden treasure** (which the colony obtained from prior "food"), or even **one of their own young**.
- If the colony's survival is threatened and it thinks it has a chance of surviving a fight, it can leverage its combined might using **special lair actions**. On **initiative count 20** (losing all ties) the colony takes a lair action, causing one of the following effects; **it can't use the same effect two rounds in a row**:
  1. The colony chooses **up to three creatures within 300 feet**. Each must succeed on a **DC 15 Strength** saving throw or have its **speed reduced to 0** until initiative count 20 on the following round, as pieces of the environment grasp the target. **If a target fails the save by 5 or more, it is restrained instead** for that duration.
  2. The colony uses the **Help action**, aiding a creature of its choice within 300 feet.
  3. The colony chooses **up to three creatures within 300 feet**. Each must succeed on a **DC 15 Dexterity** saving throw or take **13 (3d8) acid** damage, as orifices appear on surfaces in the environment and launch caustic spittle.
  4. The colony chooses a **cube of nonmagical, inanimate material in physical contact with it**, up to **15 feet on a side**, and reshapes that material however it likes. The transformation lasts for **1 hour**.
- **Encounter difficulty:** consider the colony to be **one additional creature of challenge rating 2**.

###### Juvenile Mimic *(p. 54–56)*

*(Stat block split across three page breaks: the header block ends on p. 54, the traits/actions continue on p. 55, and the "Primal Fruit" caption for the next section appears at the top of p. 56 — reassembled here.)*

**Tiny monstrosity (shapechanger)**

| Field | Value |
| --- | --- |
| Armor Class | 11 |
| Hit Points | 7 (2d4 + 2) |
| Speed | 10 ft., climb 10 ft. |
| STR | 1 (-5) |
| DEX | 12 (+1) |
| CON | 13 (+1) |
| INT | 10 (+0) |
| WIS | 13 (+1) |
| CHA | 10 (+0) |
| Skills | Stealth +3 |
| Damage Immunities | acid |
| Condition Immunities | prone |
| Senses | darkvision 60 ft., Passive Perception 11 |
| Languages | Common, Undercommon, telepathy 120 ft. |
| Challenge | 0 (10 XP) |
| Proficiency Bonus | +2 |

*Purpose: the offspring stat block for a mimic colony — challenge 0, shapechanger, telepathic 120 ft. No roll to use; the only check is a **Bite** at **+3 to hit, 1 piercing + 2 (1d4) acid**.*

**Traits**

- **False Appearance (Object Form Only).** While the mimic remains motionless, it is indistinguishable from an ordinary object.
- **Spider Climb.** The mimic can climb difficult surfaces, including upside down on ceilings, without needing to make an ability check.

**Actions**

- **Bite.** Melee Weapon Attack: **+3 to hit**, reach 5 ft., one target. Hit: **1 piercing damage plus 2 (1d4) acid damage**.
- **Shape-Shift.** The mimic polymorphs into an object or back into its true, amorphous form. Its statistics are the same in each form. Any equipment it is wearing or carrying isn't transformed. It reverts to its true form if it dies.

##### Primal Fruit *(p. 56–57)*

In wild places brimming with nature's power, wizard-tended gardens, and blessed groves touched by divine providence, plants can produce fruit bursting with primal magic. Plants that do bear it show obvious signs: colors more vibrant or shifting randomly, skin that sparkles in the light or glows in the dark, soft hums, or a peculiar feel to the touch.

- A magic fruit-bearing plant might produce **1d6 pieces of primal fruit every week**. Primal fruit remains potent for **1 week**, after which it loses its magical properties but remains edible.
- As an **action**, a creature can **eat** a piece of primal fruit to gain its effects. It can be **squeezed into juice or cooked into a dish** and retains its magic. Choose an effect or roll the table. An **identify** spell or similar magic reveals the **beneficial** effect before it is eaten, but **doesn't reveal a curse or side effect**.

| d8 | Effect |
| --- | --- |
| 1 | The creature **regains 3d8 + 4 hit points**, and its skin sheds **bright light in a 5-foot radius and dim light for an additional 5 feet** for 1 hour. |
| 2 | The creature feels a **surge of might**. For 1 hour it has **advantage on attack rolls using Strength, Strength checks, and Strength saving throws**. When the effect ends, it gains **1 level of exhaustion**. |
| 3 | **Waves of vitality** crash over the creature. Its **hit point maximum increases by 2d10**, and it gains the same number of hit points. The increase lasts **until the creature finishes a long rest**, at which time the creature must succeed on a **DC 15 Charisma** saving throw or be **cursed with a random form of lycanthropy** (see "Lycanthropes" in the Monster Manual). |
| 4 | The creature's **skin prickles faintly**. For 1 hour it gains **resistance to one damage type** (chosen by the DM). |
| 5 | **Euphoric visions of bright light** swim through the creature's mind. The creature gains the benefits of ***death ward*** for 8 hours and must succeed on a **DC 13 Constitution** saving throw or be **poisoned** for the duration. |
| 6 | A **faint humming** drones in the background of everything the creature hears for 1 hour, during which it has **advantage on saving throws against spells**. |
| 7 | The creature **doesn't require food, drink, or sleep for 1d4 days**. It can't be put to sleep by magic, and its dreams intrude on its waking thoughts, imposing **disadvantage on Wisdom (Perception) checks**. |
| 8 | **Whispers intrude** on the creature's mind for 24 hours. The creature can **telepathically communicate** with any creature it can see within 120 feet. If the other creature understands at least one language, it can respond telepathically. |

*Purpose: roll **d8** for the effect of one piece of primal fruit; row 3 embeds **2d10** and a delayed **DC 15 Charisma** save at long rest, so it's a great deferred-consequence node. (Caption on p. 56, rows on p. 57 — reconstructed.)*

##### Unearthly Roads *(p. 57–58)*

Currents of magic run through the world — invisible, artery-like networks that exert subtle influence and connect disparate lands. The greatest are persistent paths, often known by colloquial names, or simply as **unearthly roads**. An unearthly road acts like a sort of **planar portal** stretching from one place to another, be they sites on the same world or different planes. They allow creatures to cross great distances rapidly, moving from an **entrance gate to an exit gate** or vice versa. The paths operate like long tunnels, and a creature that travels on an unearthly road **progresses 21 miles of distance in the time it would normally take it to travel 1 mile**. While on the road, glimpses of the world beyond might be visible in blurred or distorted visions of scenery or especially prominent landmarks. **Creatures or specific details are not visible beyond an unearthly road.**

- Some unearthly roads serve as **trade routes or secret connections** between distant lands. Others **shift locations at noteworthy times** or in response to external phenomena (specific anniversaries, **phases of the moon**). Some might also **require a particular item, ritual, or action to open their gates**.

| d6 | Key |
| --- | --- |
| 1 | Throwing a silver orb through an ancient arch |
| 2 | Spilling a pint of humanoid blood |
| 3 | Calling the name of a specific archfey three times |
| 4 | Wearing the regalia of a lost royal dynasty |
| 5 | Permanently sacrificing a memory of joy |
| 6 | Being the descendant of a legendary hero |

*Purpose: roll **d6** for the key that opens an unearthly road's gate; each key is a one-shot unlock condition worth modelling as a puzzle/flag check. (Caption and rows both on p. 58.)*

---

#### Natural Hazards *(p. 58–60)*

*"Even without the threats of supernatural environments, the world is a dangerous place."* These expand on the DMG's hazards.

##### Avalanches *(p. 58–59)*

A typical **avalanche (or rockslide) is 300 feet wide, 150 feet long, and 30 feet thick**. Creatures in its path can avoid or escape it if they're close to its edge, but **outrunning one is almost impossible**.

- When an avalanche occurs, **all nearby creatures must roll initiative**. **Twice each round, on initiative counts 10 and 0**, the avalanche **travels 300 feet** until it can travel no more.
- When the avalanche **moves**, any creature in its space moves along with it and **falls prone**, and the creature must make a **DC 15 Strength** saving throw, taking **1d10 bludgeoning** on a failed save, or half as much on a successful one.
- When the avalanche **stops**, snow and debris settle and **bury** creatures. A buried creature is **blinded and restrained**, and has **total cover**. It gains **1 level of exhaustion for every 5 minutes** spent buried. It can try to dig itself free as an action, breaking the surface and ending the blinded and restrained conditions with a successful **DC 15 Strength (Athletics)** check. A creature that **fails this check three times** can't attempt to dig itself out again.
- A creature that is **not restrained or incapacitated** can spend **1 minute** freeing a buried creature. Once free, it is no longer blinded or restrained by the avalanche.

##### Falling into Water *(p. 59)*

A creature that falls into water or another liquid can use its **reaction** to make a **DC 15 Strength (Athletics) or Dexterity (Acrobatics)** check to hit the surface head or feet first. On a successful check, **any damage resulting from the fall is halved**.

##### Falling onto a Creature *(p. 59)*

If a creature falls into the space of a second creature and **neither of them is Tiny**, the second creature must succeed on a **DC 15 Dexterity** saving throw or be impacted by the falling creature, and **any damage resulting from the fall is divided evenly between them**. The impacted creature is also **knocked prone**, unless it is **two or more sizes larger** than the falling creature.

##### Spells as Natural Hazards *(p. 60)*

*"Numerous spells emulate the wrath of nature, and you can use spell effects to represent a variety of natural hazards."*

| Natural Hazard | Approximate Spell |
| --- | --- |
| Ball lightning | Chromatic orb |
| Blizzard | Cone of cold, ice storm, sleet storm |
| Earthquake | Earthquake |
| Falling debris | Conjure barrage, conjure volley |
| Flood | Control water, tsunami |
| Fog | Fog cloud |
| Lava bomb | Fireball, produce flame |
| Lightning | Call lightning, lightning bolt |
| Meteor | Fireball, meteor swarm |
| Mirage | Hallucinatory terrain |
| Pyroclastic flow | Incendiary cloud |
| Radiation | Blight, circle of death |
| Smoke | Fog cloud |
| St. Elmo's fire | Faerie fire |
| Swamp gas | Dancing lights |
| Tidal wave | Tsunami |
| Toxic eruption | Acid splash |
| Toxic gas | Cloudkill, stinking cloud |
| Thunder | Thunderwave |
| Volcanic lightning | Storm of vengeance |
| Whirlpool | Control water |
| Wildfire | Fire storm, wall of fire |
| Windstorm | Gust of wind |

*Purpose: a designer's lookup mapping a natural hazard to an existing spell effect instead of a bespoke mechanic; 23 rows, no roll — pick the row, then use the named spell. (Caption and rows both on p. 60.)*

---

### Puzzles

**No puzzles appear in this source file.** Stated plainly rather than padded: the extract runs `<<<PAGE 1>>>`–`<<<PAGE 61>>>` and the chapter's content ends at **Spells as Natural Hazards** on p. 60, followed only by the dndbeyond site footer on p. 61. The string `MAGIC ITEMS PUZZLES` on p. 1 is the chapter navigation crumb, not a heading, and no puzzle, clue list, or solution table appears anywhere in the 1738 lines.

The puzzle content the task anticipated — puzzles with setup text, visible clues, and solution/target tables — is Tasha's Cauldron of Everything **chapter 4, "Puzzle Collection"** (with "Puzzle Elements" as its introductory section), which is a separate chapter and a separate extract. If the puzzle collection was expected in this file, the wrong file was supplied; the puzzles would need to be transcribed from that chapter's own text.

**Nearest puzzle-shaped mechanics that *are* in this chapter**, offered as engine-usable stand-ins rather than puzzles (each is already transcribed in full above):

- **Unearthly Road Keys** (d6, p. 58) — six one-shot unlock conditions for a hidden gate, the closest thing to a keyed puzzle in the chapter.
- **Mimic Colonies** (p. 53–56) — a bargaining puzzle with a stat-block payoff: the colony trades information, treasure, or a juvenile for its survival; the lair actions are a stateful 4-option rotation.
- **Mirror Zone** effects (p. 39–42) and **Haunted** effects (p. 33–36) — discovery/interpretation challenges gated on **DC 13 Strength (Athletics)**, **DC 20 Intelligence (Arcana)**, **DC 10 Wisdom (Medicine)**, and one **roll-a-die even/odd** branch, which resolve into reveal-or-consequence outcomes much like puzzle nodes.
- **Party Origin** (d6, p. 4) and **Monsters' Desires** (14× d4, p. 23–27) — roll-once-per-creation tables that fit a "random but committed" generator pattern rather than a puzzle.

---

### Viwo notes

*Mapping to the consuming Python/Flask persistent-world sim (5e-flavoured, one turn = one in-game minute, d20 + modifier vs DC, no armor class, HP floor 100). Only genuinely relevant items; unverified targets are phrased as "candidate for".*

**Checks and DCs**

- **Monster Research** — the `DC = 10 + creature CR` formula is a direct model for a **CR-scaled DC** helper next to `engine/checks.py`; candidate for adding a `dc_for_cr(cr)` alongside the existing `DCS` band dict (which stops at trivial 5 → near_impossible 30).
- **Region/Haunted/Infested save DCs** cluster at **DC 10 / 12 / 13 / 14 / 15 / 16 / 17 / 18 / 20** — every one maps onto `DCS` bands already present (`easy` 10, `medium` 15, `hard` 20); candidate for expressing them as band names rather than literals at call sites.
- **Sidekick "PB +1 ⇒ +1 to every attack and every stat-block DC"** is exactly the kind of global modifier sweep `engine/checks.py` would need; candidate for a `recompute_dc_offsets` pass.
- **Proficiency bonus doubling (Expert's Expertise)** and **Reliable Talent's "treat 9 or lower as a 10"** are candidate overrides for the d20 roll floor — the latter directly parallels a 100-HP floor style clamp.
- **Abolishing armor class** collides with *Martial Role: Defender*, *Improved Defense (AC +1)*, *Coordinated Strike*, and *Enchanted Spring #2 (+1 AC)*. Candidate for retargeting these to an evasion/mitigation stat instead of AC.

**Conditions** (`engine/conditions.py` + `data/library/conditions/`, ~39 files)

- Region effects are a ready-made condition list: **charmed, frightened, exhausted** (multi-level), **restrained, prone, blinded, deafened, incapacitated, hidden, invisible, grappled, poisoned** (multiple bespoke poison flavors: silt, mites, silverfish, tapeworm, bloodsucking insects).
- **Exhaustion** appears with explicit cadence ("1 level per 5 minutes buried", "1 level per hour of bloodsucking insects") — a strong candidate for a per-tick stacking condition in `conditions.py`.
- **Wounds that bleed 1d4 at the start of each turn, escalating by 1d4 on re-hit, stanchable by a DC 10 Wisdom (Medicine) action, cured by magical healing** (Mirror Zone 41–46) is a near-complete template for a condition definition in `data/library/conditions/`.
- **Polymorph-style transformations** (giant spider, blink dog) and *fey/undead/vulnerable* stat-swap are candidate condition payloads, though they exceed what a boolean/multiplier condition likely supports.

**Traits** (`data/library/traits/`, ~71 files)

- Direct trait candidates: **Eldritch Storms** (flaywind, flame storm, necrotic tempest, Thrym's howl), **Enchanted Spring** effects (golden feathers +1 AC, eyestalks all-around sight, donkey ears, third eye/truesight 60 ft., animal tail), **Primal Fruit** effects (surge of might, death ward, no food/drink/sleep need, telepathic reach 120 ft.), **Magic Mushroom** effects (permanent skin color, chicken voice, omni-linguism), **Hallow/Divine-favor-style auras**, **Emotional Echoes** (per-emotion compulsion).
- **Emotional Echoes** in particular read as a single trait with a parameterized `emotion` field and an `area_scope` of room→forest.
- **Emotional Echo / Inspiration / Hatred** style emotions are also candidate **disposition modifiers** for `engine/relationships.py` rather than traits.

**Triggers** (`engine/trigger_system.py` + `engine/triggers/` + `data/library/triggers/`)

- The **generic region trigger list is a ready-made trigger-template set**: on region entry; on a creature dropping below half HP; on casting a spell of 1st level or higher; on activating a magic item; on a loud noise; on 30 minutes elapsed in region. All six are one-turn-friendly given a 1-minute turn.
- Region-specific triggers map just as cleanly: Great Old One warlock rolling **1 or 20**; short/long rest begun; over an hour reading an eldritch tome; a save succeeded against a fiend/undeed compel; a cleric/paladin 3rd+ spell targeting; a critical hit against a fiend/undead; frightened condition gained; multiple creatures unable to see; creature alone; midnight/ominous hour; a mirror shattered; teleportation magic used; illusion appearing; impersonation; a charge expended; a 1st+ spell slot expended; a CR 5+ dragon/fey/elemental dying; psychic damage exceeding CON score; charmed or frightened; telepathic communication.
- **Recurring-tick effects** are the strongest template fits: "every hour, DC 10 CON save or 1 exhaustion" (Infested 96–00), "at the end of each of the creature's turns" (Unraveling 41–45), "at the start of each of its turns, 1d4/2d6/3d6 damage" (every eldritch storm), "each round on initiative count 20" (Unraveling 21–25), "once per day" (Emotional Echoes).

**Items and toggles** (`data/library/items/`, 525 files; `engine/toggleable_items.py`; `engine/items/use_actions.py`)

- **Toggleable / per-tick-drain candidates:** the sentient magic item created by a Haunted region (66–70), the nonmagical weapon that becomes a *mace of disruption* (Blessed Radiance 31–36), nonmagical weapons that become **+1 magic weapons for 1 hour** (Unraveling 51–55), the *flaming sphere* that self-moves and vanishes (46–50), the *reverse gravity* 1-minute instance (76–80), the mirror-twin teleport disks (Mirror Zone 77–82), **buff items with a per-hour expiration** (enchanted spring 1, 2, 4, 5, 6, 8, 9, 10, 11, 12; primal fruit 1, 2, 4, 5, 6, 7, 8; mushroom 2, 4, 5, 6, 7, 10).
- **Long-duration states with a hard expiry** (1d4 days, 1d8 days, 7 days, 24 hours, "within 7 days") are a clean fit for an item `expires_after` field in `data/library/items/`.
- **Asymmetric use actions** (per-item valid actions) match: *eat* a piece of primal fruit, *drink/touch/bathe* a spring, *pour* a vial of bottled spring water, *bottle* a spring, *eat* a mushroom, *squeeze/cook* primal fruit into juice or a dish.
- **Items whose magical properties are removed or restored** (Unraveling 01–05: all magic items go nonmagical for 1 hour, artifacts unaffected, attunement restored on return) is a direct model for a global item-state toggle.
- **Poison-damage items**: the glowing grubs (26–30) grant *potion of healing* on consumption — a consumable with a benefit; the infested region's "silverfish destroy one random nonmagical paper item" is a candidate item-destruction trigger.

**Crafting** (`engine/crafting.py`)

- **Enchanted spring bottling** (blessed-vial prerequisite, magic lost when bottled) is a recipe node with a special-component requirement.
- **Earth-vein / primal-fruit propagation** — "1d6 pieces per week" and "primal fruit can be squeezed into juice or cooked into a dish and retains its magic" — is a candidate two-step recipe chain (fruit → juice/dish).
- **Bone/metal consumed by an ooze** and "oil to apply to the construct's joints" / "a magic item with charges used as fuel" are candidate material-consumption recipes tied to parley.
- **Earth-glass/"spectral slivers of glass"** and the *jagged mirror* sword are candidate craftable component drops.

**Foraging** (`engine/foraging.py` + `data/library/foraging.json`)

- **Foraging nodes:** fresh meat, brightly colored beads/cloth/feathers/string, a pound of mulch, Feywild-energized spring water, gemstone worth 50 gp, an exceedingly pure sample of a favored element, multiple barrels of ale, bones or metal, a vial of blood, dramatics mushrooms (Medicine/Nature/Survival gate), primal fruit (weekly regrowth), a desecrated holy object.
- **Expert-gated identification** — "proficient in Medicine, Nature, or Survival … only an expert can identify an unknown variety" — is a direct fit for a skill-gated `foraging.json` reveal entry.
- **Glow-in-the-dark / bioluminescent** produce (flies, grubs) fits a per-turn light-emitting item state.

**Skills and progression** (`engine/skills.py` + `engine/skill_progress.py`)

- **Parleying** is the cleanest skills win: *"consider granting advantage on any ability check they make to communicate with a creature if they offer something it wants"* — an advantage-granting check conditioned on an offering match.
- **Insight/Perception/Persuasion/Deception/Intimidation** are each mechanically swung by region effects with explicit advantage/disadvantage — good regression coverage for `SKILL_ABILITY` keys (all 18 skills appear across the tables; the full list is already in `checks.py`).
- **Bonus Proficiencies** for sidekicks (5 skills for Expert, 2 from a restricted list for Spellcaster, 2 from a restricted list for Warrior) are candidate restricted-list proficiency definitions.

**Relationships and social** (`engine/relationships.py`, `engine/background_social.py`, `engine/agent_memory.py`)

- **Social contract, hard/soft limits, and house rules** are candidate per-session/per-player config surfaces, not runtime entities — flag as a scope question rather than an existing feature.
- **Parleying / bartering with a mimic colony** (information, treasure, or a juvenile for survival) is a candidate negotiation branch keyed off a creature's disposition.
- **Emotional Echoes** (Boldness, Love, Sorrow, Inspiration…) are candidate disposition/trait modifiers on inhabitants of a tagged area.
- **Perfect Advantage**-style conditions — a character's ideal, bond, or flaw becoming a campaign storyline, and "the criminal background's bond" being resolved into a named NPC — are candidate `agent_memory.py` long-arc goals built at session zero.

**Roles** (`engine/roles.json`)

- **Expert / Spellcaster / Warrior** map onto role archetypes; **Mage / Healer / Prodigy** (spell list + casting ability) and **Martial Role: Attacker / Defender** map onto role variants. All three sidekick classes require a speakable language, which pairs with a language capability check.

**Spells and effect handlers** (`engine/spell/`, `engine/effect_handlers/spells.py`)

- A very large list of spells are invoked as effects and would need handler coverage: *divine favor, bless, commune, hallow, greater/lesser restoration, guard and wards, levitate, confusion, gate, gate-shaped rifts, contact other plane, insect plague, polymorph, misty step, scrying, mirror image, blink, hallucinatory terrain, detect thoughts, mind blank, telekinesis, death ward, antimagic field, Otiluke's resilient sphere, flaming sphere, reverse gravity, wish, disintegrate-scale force half damage, grease, quicksand, sighting rot, turn to grease, time stop, fog cloud, spider climb, telepathy, speak with plants, identify, commune, augury, dream, divination, contact other plane, control water, tsunami, storm of vengeance, fire storm, wall of fire, gust of wind, and the whole 23-row Spells as Natural Hazards table.*
- **Mundane-ability item-granted casts** (Enchanted Spring 7, 12; Haunted 73–78; Mirror Zone 53–58; Unraveling 96–00) are a candidate "one-shot, no-components, expire-after-use" spell grant.
- **Concentration-breaking** (Focused Casting 20th) and **spell-draining** (Unraveling 86–90: DC 15 spellcasting-ability save or the slot is wasted) are candidate effect-handler hooks in the cast pipeline.

**Promotion** (`engine/promotion.py`)

- **Party Origin → Background/Ideal/Bond/Flaw hooks** and the sidekick **level-parity rule** (a sidekick's level equals the party's average level) are the promotion-adjacent mechanics here. *Verify whether `promotion.py` models party-average advancement before assuming a fit.*

**Interiors, venues, structures, world grid, population**

- **Mimic colonies building buildings, bridges, crystal formations, cliff faces, and statues** is the standout structure-generation candidate for `engine/structures.py`; the lair action that **reshapes a 15-foot cube of nonmagical inanimate material for 1 hour** is a direct terrain-rewrite primitive for `engine/world_grid.py`.
- **Enchanted springs, unearthly road entrance/exit gates, and the secret underground-town style of location** are candidate `engine/venues.py` / `engine/interior_gen.py` site types; unearthly roads' **21× distance compression** and "shifting locations at noteworthy times or by moon phase" are candidate fast-travel/temporal-scheduling hooks.
- **Undead desire 3 ("materials, tools, or the skills to sun-proof a crumbling mausoleum")** and **construct desire 1 (oil for joints)** are candidate `engine/population.py` service-demand templates for sapient settlements.
- **Snow/debris 4d6 feet of wake, quicksand pits, and a 10-foot square of grease** are candidate hazard tiles for `engine/world_grid.py`.
- **Emotional Echoes scoped "as small as a room in a house or as large as a forest"** and **region triggers gated on "the party spends at least 30 minutes in the same region"** are candidate area-modifier and per-turn residency fields.

**Scenarios** (`data/scenarios/`)

- Candidate seed content: an Eldenford-scale *haunted* or *mirror zone* town, a *far realm* incursion, a mimic-colony village, a set of *enchanted springs* as a map feature set, and *primal fruit* groves as a renewable forage node. *Phrased as candidates; no existing scenario was inspected for these concepts.*

**Not mapped** — `engine/soak.py` and `engine/player_manager.py` have no clear hook in this chapter; the chapter's material is a DM-facing toolbox rather than a soak/identity surface.

---

## Part 4 — 5e Monster Stat Blocks (D&D Beyond goblin-filtered export)

---

> **What this file actually is.** This is a browser **print-out of the D&D Beyond monster-browsing page**, taken on `27.09.2026 10:50`, with the search box filled in with the word **"goblin"**. It is *not* an export of the Monster Manual, not an SRD dump, and not a complete list of 5e monsters. It is a filtered, paginated web page captured as PDF and flattened to text: the printed output interleaves the left-hand *search-results column* (CR badge, name, source book, type/size/alignment, `Tags:` / `Habitat:` / `Treasure:` lines) with the right-hand *detail pane* (the actual stat block, plus a `Description` block and sidebars). Because the two columns overlap in the text layer, several lines are visibly mangled where the two collide — those are reproduced verbatim below and flagged rather than silently repaired. It is also paginated at 20 results per page, so it is **only the first page of results**; the pagination footer on p. 16 reads `1 2 Next`, which is itself evidence that results 2 and beyond were never printed. Four results are **locked marketplace previews** with no stat block at all (three `Phandelver and Below: The Shattered Obelisk` entries and one `Stranger Things: Welcome to the Hellfire Club` entry). The file contains **20 result entries covering 16 distinct stat blocks** — the difference is entirely the duplicated "Volo's-era" vs "2014 print" renderings of the same creatures that D&D Beyond shows side by side, plus 4 locked entries. As a reference for a game engine, it is therefore a *good sample of one creature family*, not a corpus.

Source file: `C:\Users\TOMMYS~1\AppData\Local\Temp\kilo\pdftext\Monsters_for_Dungeons_and_Dragons_DandD_.txt` (884 lines, 17 pages).

### Index table

| # | Creature | Source | CR | AC | HP | Tags/Habitat |
|---|----------|--------|----|----|----|--------------|
| 1 | Goblin | Basic Rules (2014) *(Legacy)* | 1/4 (50 XP) | 15 (leather armor, shield) | 7 (2d6) | Tags: GOBLINOID · Habitat: FOREST GRASSLAND HILL UNDERDARK |
| 2 | Goblin Boss | Monster Manual (Volo's-era render) | 1 (200 XP) | 17 | 21 (6d6) | Habitat: FOREST GRASSLAND HILL PLANAR (ACHERON) PLANAR (FEYWILD) UNDERDARK · Treasure: Implements, Individual |
| 3 | Goblin Boss | Monster Manual (2014) *(Legacy)* | 1 (200 XP) | 17 (chain shirt, shield) | 21 (6d6) | Tags: GOBLINOID · Habitat: FOREST GRASSLAND HILL UNDERDARK |
| 4 | Goblin Boss (Variant) | Phandelver and Below: The Shattered Obelisk | 1 (badge only) | — | — | Aberration (Goblinoid) Small Any Alignment — **locked, no stat block** |
| 5 | Goblin Commoner | Tales from the Yawning Portal | 0 (10 XP) | 10 | 3 (1d6) | Tags: NPC · Habitat: ARCTIC COASTAL DESERT FOREST GRASSLAND HILL URBAN |
| 6 | Goblin Gang Member | Guildmasters' Guide to Ravnica | 1/4 (50 XP) | 14 (leather armor) | 10 (3d6) | *(no tag/habitat line printed)* |
| 7 | Goblin Hexer | Monster Manual (Volo's-era render) | 3 (700 XP) | 13 | 45 (10d6 + 10) | Habitat: FOREST GRASSLAND HILL PLANAR (ACHERON) PLANAR (FEYWILD) UNDERDARK · Treasure: Implements, Individual |
| 8 | Goblin Minion | Monster Manual (Volo's-era render) | 1/8 (25 XP) | 12 | 7 (2d6) | Habitat: FOREST GRASSLAND HILL PLANAR (ACHERON) PLANAR (FEYWILD) UNDERDARK · Treasure: Implements, Individual |
| 9 | Goblin Psi Brawler | Phandelver and Below: The Shattered Obelisk | 2 (badge only) | — | — | Aberration (Goblinoid) Small Any Alignment — **locked, no stat block** |
| 10 | Goblin Psi Commander | Phandelver and Below: The Shattered Obelisk | 4 (badge only) | — | — | Aberration (Goblinoid) Small Any Alignment — **locked, no stat block** |
| 11 | Goblin Warrior | Monster Manual (Volo's-era render) | 1/4 (50 XP) | 15 | 10 (3d6) | Habitat: FOREST GRASSLAND HILL PLANAR (ACHERON) PLANAR (FEYWILD) UNDERDARK · Treasure: Implements, Individual |
| 12 | Goblin Warrior (Stranger Things variant) | Stranger Things: Welcome to the Hellfire Club | 1/4 (badge only) | — | — | Fey (Goblinoid) Small Chaotic Neutral — **locked, no stat block** |
| 13 | Hobgoblin | Basic Rules (2014) *(Legacy)* | 1/2 (100 XP) | 18 (chain mail, shield) | 11 (2d8 + 2) | Tags: GOBLINOID · Habitat: DESERT FOREST GRASSLAND HILL UNDERDARK |
| 14 | Hobgoblin Captain | Monster Manual (Volo's-era render) | 3 (700 XP) | 17 | 58 (9d8 + 18) | Habitat: DESERT FOREST GRASSLAND HILL MOUNTAIN PLANAR (ACHERON) UNDERDARK · Treasure: Armaments, Individual |
| 15 | Hobgoblin Captain | Monster Manual (2014) *(Legacy)* | 3 (700 XP) | 17 (half plate) | 39 (6d8 + 12) | Tags: GOBLINOID · Habitat: DESERT FOREST GRASSLAND HILL UNDERDARK |
| 16 | Hobgoblin Devastator | Mordenkainen's Presents: Monsters of the Multiverse | 4 (1,100 XP) | 13 (studded leather) | 45 (7d8 + 14) | Habitat: FOREST GRASSLAND HILL |
| 17 | Hobgoblin Devastator | Volo's Guide to Monsters *(Legacy)* | 4 (1,100 XP) | 13 (studded leather) | 45 (7d8 + 14) | Tags: GOBLINOID · Habitat: FOREST GRASSLAND HILL |
| 18 | Hobgoblin Iron Shadow | Mordenkainen's Presents: Monsters of the Multiverse | 2 (450 XP) | 15 (unarmored defense) | 32 (5d8 + 10) | Habitat: FOREST GRASSLAND HILL |
| 19 | Hobgoblin Iron Shadow | Volo's Guide to Monsters *(Legacy)* | 2 (450 XP) | 15 | 32 (5d8 + 10) | Tags: GOBLINOID · Habitat: FOREST GRASSLAND HILL |
| 20 | Hobgoblin Warlord | Monster Manual (Volo's-era render) | 6 (2,300 XP) | 20 | 112 (15d8 + 45) | Habitat: DESERT FOREST GRASSLAND HILL MOUNTAIN PLANAR (ACHERON) UNDERDARK · Treasure: Armaments, Individual |

### Full stat blocks

---

#### 1. Goblin *(p. 1)*

- **Source:** Basic Rules (2014) — marked **Legacy**
- **Tags:** GOBLINOID · **Habitat:** FOREST, GRASSLAND, HILL, UNDERDARK
- **Search-result meta:** `1/4 Goblin` · Humanoid (Goblinoid) · Small · Neutral Evil

**Description**

> Goblins are small, black-hearted humanoids that lair in despoiled dungeons and other dismal settings. Individually weak, they gather in large numbers to torment other creatures.

*Tags: GOBLINOID Habitat:FOREST GRASSLAND HILL UNDERDARK Basic Rules (2014)*

| Field | Value |
|---|---|
| Size/Type/Alignment | Small Humanoid (Goblinoid), Neutral Evil |
| Armor Class | 15 (leather armor, shield) |
| Hit Points | 7 (2d6) |
| Speed | 30 ft. |

| | STR | DEX | CON | INT | WIS | CHA |
|---|---|---|---|---|---|---|
| Score | 8 | 14 | 10 | 10 | 8 | 8 |
| Mod | −1 | +2 | +0 | +0 | −1 | −1 |

*(No save/DC column is printed in the Basic Rules 2014 rendering — only the ability modifiers.)*

- **Skills** Stealth +6
- **Senses** Darkvision 60 ft., Passive Perception 9
- **Languages** Common, Goblin
- **Challenge** 1/4 (50 XP) · Proficiency Bonus +2

**Traits**

- **Nimble Escape.** The goblin can take the Disengage or Hide action as a bonus action on each of its turns.

**Actions**

- **Scimitar.** Melee Weapon Attack: +4 to hit, reach 5 ft., one target. Hit: 5 (1d6 + 2) slashing damage.
- **Shortbow.** Ranged Weapon Attack: +4 to hit, range 80/320 ft., one target. Hit: 5 (1d6 + 2) piercing damage.

*No Gear line. No Bonus Actions / Reactions section is printed for this rendering (Nimble Escape is given as a Trait here rather than as a Bonus Action).*

**Extraction notes for this block**

- Line 42 of the source is a collided two-column fragment: `A ti Shortbow RangedWeaponAttack:+4 tohit range`. It is the result of the detail pane's action text overlapping the search-results column; the authoritative, complete `Shortbow` action is printed on p. 2 (lines 65–66) and is the version transcribed above.
- The block itself is split across the page 1 / page 2 boundary: header + Traits on p. 1, `Actions` on p. 2. Nothing is missing; the two halves are joined here.

---

#### 2. Goblin Boss — Monster Manual (Volo's-era render) *(p. 2)*

- **Source:** Monster Manual (the D&D Beyond "Volo's-era" presentation, signalled by the `AC` / `HP` shorthand and the `MOD`/`SAVE` split table). This render carries **no `Tags:` line**.
- **Search-result meta:** `1 Goblin Boss` · Fey (Goblinoid) · Small · Chaotic Neutral
- **Habitat:** FOREST, GRASSLAND, HILL, PLANAR (ACHERON), PLANAR (FEYWILD), UNDERDARK · **Treasure:** Implements, Individual

| Field | Value |
|---|---|
| Size/Type/Alignment | Small Fey (Goblinoid), Chaotic Neutral |
| AC | 17 · *Initiative +2 (12)* |
| HP | 21 (6d6) |
| Speed | 30 ft. |

| | STR | DEX | CON | INT | WIS | CHA |
|---|---|---|---|---|---|---|
| Mod | +0 | +2 | +0 | +0 | −1 | +0 |
| **Save** | **+0** | **+2** | **+0** | **+0** | **−1** | **+0** |

*(The `MOD` / `SAVE` header pair is printed twice in the extracted text — a repeating table header artefact — and is collapsed to one table here. The block prints bare modifiers, not base scores; base scores are recoverable by inverting the modifier.)*

- **Skills** Stealth +6
- **Gear** Chain Shirt, Scimitar, Shield, Shortbow
- **Senses** Darkvision 60 ft.; Passive Perception 9
- **Languages** Common, Goblin
- **CR** 1 (XP 200; PB +2)

**Actions**

- **Multiattack.** The goblin makes two attacks, using Scimitar or Shortbow in any combination.
- **Scimitar.** Melee Attack Roll: +4, reach 5 ft. Hit: 5 (1d6 + 2) Slashing damage, plus 2 (1d4) Slashing damage if the attack roll had Advantage.
- **Shortbow.** Ranged Attack Roll: +4, range 80/320 ft. Hit: 5 (1d6 + 2) Piercing damage, plus 2 (1d4) Piercing damage if the attack roll had Advantage.

**Bonus Actions**

- **Nimble Escape.** The goblin takes the Disengage or Hide action.

**Reactions**

- **Redirect Attack.** Trigger: A creature the goblin can see makes an attack roll against it. Response: The goblin chooses a Small or Medium ally within 5 feet of itself. The goblin and that ally swap places, and the ally becomes the target of the attack instead.

*No Traits, no Description, no Legendary Actions/Resistances for this rendering.*

---

#### 3. Goblin Boss — Monster Manual (2014) *(p. 3)*

- **Source:** Monster Manual (2014) — marked **Legacy**
- **Tags:** GOBLINOID · **Habitat:** FOREST, GRASSLAND, HILL, UNDERDARK
- **Search-result meta:** `1 Goblin Boss` · Humanoid (Goblinoid) · Small · Neutral Evil

| Field | Value |
|---|---|
| Size/Type/Alignment | Small Humanoid (Goblinoid), Neutral Evil |
| Armor Class | 17 (chain shirt, shield) |
| Hit Points | 21 (6d6) |
| Speed | 30 ft. |

| | STR | DEX | CON | INT | WIS | CHA |
|---|---|---|---|---|---|---|
| Score | 10 | 14 | 10 | 10 | 8 | 10 |
| Mod | +0 | +2 | +0 | +0 | −1 | +0 |

- **Skills** Stealth +6
- **Senses** Darkvision 60 ft., Passive Perception 9
- **Languages** Common, Goblin
- **Challenge** 1 (200 XP) · Proficiency Bonus +2

**Traits**

- **Nimble Escape.** The goblin can take the Disengage or Hide action as a bonus action on each of its turns.

**Actions**

- **Multiattack.** The goblin makes two attacks with its scimitar. The second attack has disadvantage.
- **Scimitar.** Melee Weapon Attack: +4 to hit, reach 5 ft., one target. Hit: 5 (1d6 + 2) slashing damage.
- **Javelin.** Melee or Ranged Weapon Attack: +4 to hit, reach 5 ft. or range 30/120 ft., one target. Hit: 5 (1d6 + 2) piercing damage.

**Reactions**

- **Redirect Attack.** When a creature the goblin can see targets it with an attack, the goblin chooses another goblin within 5 feet of it. The two goblins swap places, and the chosen goblin becomes the target instead.

*No Gear line, no Bonus Actions section, no Description, no Legendary Actions/Resistances. Note this 2014 print is a materially different creature from #2: no advantage-damage riders, a second attack with disadvantage instead of a free Shortbow, and Javelin instead of Shortbow.*

---

#### 4. Goblin Boss (Variant) — Phandelver and Below: The Shattered Obelisk *(p. 3)*

- **Source:** Phandelver and Below: The Shattered Obelisk — **LOCKED, NO STAT BLOCK PRINTED**
- **Search-result meta:** `1 Goblin Boss (Variant)` · Aberration (Goblinoid) · Small · Any Alignment

> This monster is part of the Phandelver and Below: The Shattered Obelisk book. You can unlock this monster by purchasing the book in our marketplace. — VIEW MARKETPLACE

**Status:** the export prints only the search-result row. AC, HP, Speed, ability scores, skills, senses, languages, CR text, traits and actions are **entirely absent** — D&D Beyond gated them behind the marketplace purchase. Nothing was cut off by a page break; the data simply is not in this document. `[…not printed in source…]`

---

#### 5. Goblin Commoner *(p. 4)*

- **Source:** Tales from the Yawning Portal
- **Tags:** NPC · **Habitat:** ARCTIC, COASTAL, DESERT, FOREST, GRASSLAND, HILL, URBAN
- **Search-result meta:** `0 Goblin Commoner` · Humanoid (Goblinoid) · Small · Any Evil Alignment

**Description**

> Commoners include peasants, serfs, servants, pilgrims, merchants, artisans, and hermits.

*Tags: NPC Habitat:ARCTIC COASTAL DESERT FOREST GRASSLAND HILL URBAN Tales from the Yawning Portal*

| Field | Value |
|---|---|
| Size/Type/Alignment | Small Humanoid (Goblinoid), Any Evil Alignment |
| Armor Class | 10 |
| Hit Points | 3 (1d6) |
| Speed | 30 ft. |

| | STR | DEX | CON | INT | WIS | CHA |
|---|---|---|---|---|---|---|
| Score | 10 | 10 | 10 | 10 | 10 | 10 |
| Mod | +0 | +0 | +0 | +0 | +0 | +0 |

*(Printed as a flat `10 (+0)` across all six — the classic NPC "no distinguishing traits" row. No save column.)*

- **Senses** Passive Perception 10 *(no darkvision)*
- **Languages** Goblin *(no Common)*
- **Challenge** 0 (10 XP) · Proficiency Bonus +2

**Actions**

- **Club.** Melee Weapon Attack: +1 to hit, reach 5 ft., one target. Hit: 1 (1d4 − 1) bludgeoning damage.

*No Skills, no Gear, no Traits, no Description of behaviour beyond the one-line commoner sentence, no Legendary Actions/Resistances.*

---

#### 6. Goblin Gang Member *(p. 4)*

- **Source:** Guildmasters' Guide to Ravnica
- **Search-result meta:** `1/4 Goblin Gang Member` · Humanoid (Goblinoid) · Small · Neutral Evil
- **Tags/Habitat:** *none printed in the export* (the book's name is truncated in the results column as `Guildmasters' Guide To Ravnic`; the full title is confirmed on p. 5 as `Guildmasters' Guide to Ravnica`)

| Field | Value |
|---|---|
| Size/Type/Alignment | Small Humanoid (Goblinoid), Neutral Evil |
| Armor Class | 14 (leather armor) |
| Hit Points | 10 (3d6) |
| Speed | 30 ft. |

| | STR | DEX | CON | INT | WIS | CHA |
|---|---|---|---|---|---|---|
| Score | 8 | 16 | 10 | 10 | 10 | 8 |
| Mod | −1 | +3 | +0 | +0 | +0 | −1 |

- **Skills** Stealth +5
- **Senses** Darkvision 60 ft., Passive Perception 10
- **Languages** Common, Goblin
- **Challenge** 1/4 (50 XP) · Proficiency Bonus +2

**Traits**

- **Nimble Escape.** The goblin can take the Disengage or Hide action as a bonus action on each of its turns.

**Actions**

- **Dagger.** Melee or Ranged Weapon Attack: +5 to hit, reach 5 ft. or range 20/60 ft., one target. Hit: 5 (1d4 + 3) piercing damage.
- **Light Crossbow.** Ranged Weapon Attack: +5 to hit, range 80/320 ft., one target. Hit: 7 (1d8 + 3) piercing damage.

*No Gear, no Description, no Reactions, no Legendary Actions/Resistances.*

---

#### 7. Goblin Hexer — Monster Manual (Volo's-era render) *(p. 5)*

- **Source:** Monster Manual (Volo's-era render) — no `Tags:` line
- **Search-result meta:** `3 Goblin Hexer` · Fey (Goblinoid) · Small · Chaotic Neutral
- **Habitat:** FOREST, GRASSLAND, HILL, PLANAR (ACHERON), PLANAR (FEYWILD), UNDERDARK · **Treasure:** Implements, Individual

| Field | Value |
|---|---|
| Size/Type/Alignment | Small Fey (Goblinoid), Chaotic Neutral |
| AC | 13 · *Initiative +3 (13)* |
| HP | 45 (10d6 + 10) |
| Speed | 30 ft. |

| | STR | DEX | CON | INT | WIS | CHA |
|---|---|---|---|---|---|---|
| Mod | −1 | +3 | +1 | +3 | +0 | +0 |
| **Save** | **−1** | **+3** | **+1** | **+3** | **+0** | **+0** |

- **Skills** Sleight of Hand +5, Stealth +7
- **Senses** Darkvision 60 ft.; Passive Perception 10
- **Languages** Common, Goblin
- **CR** 3 (XP 700; PB +2)

**Actions**

- **Multiattack.** The goblin makes two Hex Stick attacks. It can replace one attack with a use of Spellcasting.
- **Hex Stick.** Melee or Ranged Attack Roll: +5, reach 5 ft. or range 60 ft. Hit: 12 (2d8 + 3) Psychic damage.
- **Spellcasting.** The goblin casts one of the following spells, using Intelligence as the spellcasting ability (spell save DC 13):
  - At Will: Minor Illusion
  - 1/Day Each: Blindness/Deafness, Faerie Fire, Grease

**Reactions**

- **Jinx.** Trigger: A creature the goblin can see hits it with an attack roll. Response—Wisdom Saving Throw: DC 13, the triggering creature. Failure: The attack misses instead.

*No Traits, no Gear, no Description, no Bonus Actions, no Legendary Actions/Resistances.*

**Extraction notes for this block**

- Line 272 of the source is a collided fragment reading `Jinx Trigger: Acreaturethegoblincanseehitsitwithan triggeringcreature Failure: Theattackmissesinstead` (words run together, one clause duplicated). The clean, complete `Jinx` text is printed at the top of p. 6 (lines 279–281) and is what is transcribed above. The block spans the p. 5 / p. 6 break but is complete.
- Note the 5e-typography variant spelling: the Volo-era render uses `1/Day Each` rather than the 2014 print's `1/day each`.

---

#### 8. Goblin Minion — Monster Manual (Volo's-era render) *(p. 6)*

- **Source:** Monster Manual (Volo's-era render) — no `Tags:` line
- **Search-result meta:** `1/8 Goblin Minion` · Fey (Goblinoid) · Small · Chaotic Neutral
- **Habitat:** FOREST, GRASSLAND, HILL, PLANAR (ACHERON), PLANAR (FEYWILD), UNDERDARK · **Treasure:** Implements, Individual

| Field | Value |
|---|---|
| Size/Type/Alignment | Small Fey (Goblinoid), Chaotic Neutral |
| AC | 12 · *Initiative +2 (12)* |
| HP | 7 (2d6) |
| Speed | 30 ft. |

| | STR | DEX | CON | INT | WIS | CHA |
|---|---|---|---|---|---|---|
| Mod | −1 | +2 | +0 | +0 | −1 | −1 |
| **Save** | **−1** | **+2** | **+0** | **+0** | **−1** | **−1** |

- **Skills** Stealth +6
- **Gear** Daggers 3
- **Senses** Darkvision 60 ft.; Passive Perception 9
- **Languages** Common, Goblin
- **CR** 1/8 (XP 25; PB +2)

**Actions**

- **Dagger.** Melee or Ranged Attack Roll: +4, reach 5 ft. or range 20/60 ft. Hit: 4 (1d4 + 2) Piercing damage.

**Bonus Actions**

- **Nimble Escape.** The goblin takes the Disengage or Hide action.

*No Traits, no Description, no Reactions, no Legendary Actions/Resistances.*

---

#### 9. Goblin Psi Brawler — Phandelver and Below: The Shattered Obelisk *(p. 6)*

- **Source:** Phandelver and Below: The Shattered Obelisk — **LOCKED, NO STAT BLOCK PRINTED**
- **Search-result meta:** `2 Goblin Psi Brawler` · Aberration (Goblinoid) · Small · Any Alignment

> This monster is part of the Phandelver and Below: The Shattered Obelisk book. You can unlock this monster by purchasing the book in our marketplace. — VIEW MARKETPLACE

**Status:** only the search-result row is printed; the body begins on p. 7 and contains nothing but the marketplace notice. AC/HP/Speed/abilities/skills/senses/languages/CR/traits/actions are **absent from the source**. `[…not printed in source…]`

---

#### 10. Goblin Psi Commander — Phandelver and Below: The Shattered Obelisk *(p. 7)*

- **Source:** Phandelver and Below: The Shattered Obelisk — **LOCKED, NO STAT BLOCK PRINTED**
- **Search-result meta:** `4 Goblin Psi Commander` · Aberration (Goblinoid) · Small · Any Alignment

> This monster is part of the Phandelver and Below: The Shattered Obelisk book. You can unlock this monster by purchasing the book in our marketplace. — VIEW MARKETPLACE

**Status:** only the search-result row is printed. AC/HP/Speed/abilities/skills/senses/languages/CR/traits/actions are **absent from the source**. `[…not printed in source…]`

---

#### 11. Goblin Warrior — Monster Manual (Volo's-era render) *(p. 7)*

- **Source:** Monster Manual (Volo's-era render) — no `Tags:` line
- **Search-result meta:** `1/4 Goblin Warrior` · Fey (Goblinoid) · Small · Chaotic Neutral
- **Habitat:** FOREST, GRASSLAND, HILL, PLANAR (ACHERON), PLANAR (FEYWILD), UNDERDARK · **Treasure:** Implements, Individual

| Field | Value |
|---|---|
| Size/Type/Alignment | Small Fey (Goblinoid), Chaotic Neutral |
| AC | 15 · *Initiative +2 (12)* |
| HP | 10 (3d6) |
| Speed | 30 ft. |

| | STR | DEX | CON | INT | WIS | CHA |
|---|---|---|---|---|---|---|
| Mod | −1 | +2 | +0 | +0 | −1 | −1 |
| **Save** | **−1** | **+2** | **+0** | **+0** | **−1** | **−1** |

**Printed column order (as it appears in the source, preserved for fidelity):**

```
MOD SAVE
STR 8  −1 −1
DEX 15 +2 +2
MOD SAVE
INT 10 +0 +0
WIS 8  −1 −1
MOD SAVE
CON 10 +0 +0
MOD SAVE
CHA 8  −1 −1
```

*(i.e. the extract interleaves the STR/DEX, INT/WIS, CON and CHA row-pairs with repeated header rows, so the raw text order is STR, DEX, INT, WIS, CON, CHA rather than the usual STR, DEX, CON, INT, WIS, CHA. Reordered to the canonical order in the table above; all six values are unambiguous.)*

- **Skills** Stealth +6
- **Gear** Leather Armor, Scimitar, Shield, Shortbow
- **Senses** Darkvision 60 ft.; Passive Perception 9
- **Languages** Common, Goblin
- **CR** 1/4 (XP 50; PB +2)

**Actions**

- **Scimitar.** Melee Attack Roll: +4, reach 5 ft. Hit: 5 (1d6 + 2) Slashing damage, plus 2 (1d4) Slashing damage if the attack roll had Advantage.
- **Shortbow.** Ranged Attack Roll: +4, range 80/320 ft. Hit: 5 (1d6 + 2) Piercing damage, plus 2 (1d4) Piercing damage if the attack roll had Advantage.

**Bonus Actions**

- **Nimble Escape.** The goblin takes the Disengage or Hide action.

*No Traits, no Description, no Reactions, no Legendary Actions/Resistances.*

**Extraction notes for this block**

- Line 357 of the source is a collided fragment: `CR1/4(XP50PB 2) ShortbowRangedAttackRoll:+4 range80/320ft Hit: 5`. The authoritative `CR 1/4 (XP 50; PB +2)` line is repeated cleanly at the top of p. 8 (line 364), and the complete `Shortbow` action is at p. 8 lines 369–371. Both are transcribed above; nothing is lost.

---

#### 12. Goblin Warrior (Stranger Things variant) — Stranger Things: Welcome to the Hellfire Club *(p. 8)*

- **Source:** Stranger Things: Welcome to the Hellfire Club — **LOCKED, NO STAT BLOCK PRINTED**
- **Search-result meta:** `1/4 Goblin Warrior (Stran…` *(name truncated in the results column by the source's own ellipsis)* · Fey (Goblinoid) · Small · Chaotic Neutral

> This monster is part of the Stranger Things: Welcome to the Hellfire Club book. You can unlock this monster by purchasing the book in our marketplace. — VIEW MARKETPLACE

**Status:** only the search-result row and the marketplace notice are printed. AC/HP/Speed/abilities/skills/senses/languages/CR/traits/actions are **absent from the source**. `[…not printed in source…]` The creature name itself is truncated in the source as `Goblin Warrior (Stran…`.

---

#### 13. Hobgoblin *(p. 8)*

- **Source:** Basic Rules (2014) — marked **Legacy**
- **Tags:** GOBLINOID · **Habitat:** DESERT, FOREST, GRASSLAND, HILL, UNDERDARK
- **Search-result meta:** `1/2 Hobgoblin` · Humanoid (Goblinoid) · Medium · Lawful Evil

**Description**

> Hobgoblins are large goblinoids with dark orange or red-orange skin. A hobgoblin measures virtue by physical strength and martial prowess, caring about nothing except skill and cunning in battle.

*Tags: GOBLINOID Habitat:DESERT FOREST GRASSLAND HILL UNDERDARK Basic Rules (2014)*

| Field | Value |
|---|---|
| Size/Type/Alignment | Medium Humanoid (Goblinoid), Lawful Evil |
| Armor Class | 18 (chain mail, shield) |
| Hit Points | 11 (2d8 + 2) |
| Speed | 30 ft. |

| | STR | DEX | CON | INT | WIS | CHA |
|---|---|---|---|---|---|---|
| Score | 13 | 12 | 12 | 10 | 10 | 9 |
| Mod | +1 | +1 | +1 | +0 | +0 | −1 |

*(No save column in this rendering.)*

- **Senses** Darkvision 60 ft., Passive Perception 10
- **Languages** Common, Goblin
- **Challenge** 1/2 (100 XP) · Proficiency Bonus +2

**Traits**

- **Martial Advantage.** Once per turn, the hobgoblin can deal an extra 7 (2d6) damage to a creature it hits with a weapon attack if that creature is within 5 feet of an ally of the hobgoblin that isn't incapacitated.

**Actions**

- **Longsword.** Melee Weapon Attack: +3 to hit, reach 5 ft., one target. Hit: 5 (1d8 + 1) slashing damage, or 6 (1d10 + 1) slashing damage if used with two hands.
- **Longbow.** Ranged Weapon Attack: +3 to hit, range 150/600 ft., one target. Hit: 5 (1d8 + 1) piercing damage.

*No Skills, no Gear, no Description beyond the one paragraph, no Reactions, no Legendary Actions/Resistances.*

**Extraction notes for this block**

- Line 407 of the source is a collided fragment reading `Ch ll 1/2(100XP) P fi i B 2 A ti` (OCR-damaged "Challenge 1/2 (100 XP) Proficiency Bonus +2 Actions"). The clean `Challenge 1/2 (100 XP) Proficiency Bonus +2` is repeated at the top of p. 9 (line 417) and the `Actions` heading at p. 9 line 423. Both transcribed above; the block is complete.
- Note the source's own Description text says "large goblinoids" for a creature statted **Medium** — a wording slip in the 2014 Basic Rules, preserved as printed.

---

#### 14. Hobgoblin Captain — Monster Manual (Volo's-era render) *(p. 9)*

- **Source:** Monster Manual (Volo's-era render) — no `Tags:` line
- **Search-result meta:** `3 Hobgoblin Captain` · Fey (Goblinoid) · Medium · Lawful Evil
- **Habitat:** DESERT, FOREST, GRASSLAND, HILL, MOUNTAIN, PLANAR (ACHERON), UNDERDARK · **Treasure:** Armaments, Individual

| Field | Value |
|---|---|
| Size/Type/Alignment | Medium Fey (Goblinoid), Lawful Evil |
| AC | 17 · *Initiative +4 (14)* |
| HP | 58 (9d8 + 18) |
| Speed | 30 ft. |

| | STR | DEX | CON | INT | WIS | CHA |
|---|---|---|---|---|---|---|
| Mod | +2 | +2 | +2 | +1 | +0 | +1 |
| **Save** | **+2** | **+2** | **+2** | **+1** | **+0** | **+1** |

- **Gear** Greatsword, Half Plate Armor, Longbow
- **Senses** Darkvision 60 ft.; Passive Perception 10
- **Languages** Common, Goblin
- **CR** 3 (XP 700; PB +2)

**Traits**

- **Aura of Authority.** While in a 10-foot Emanation originating from the hobgoblin, the hobgoblin and its allies have Advantage on attack rolls and saving throws, provided the hobgoblin doesn't have the Incapacitated condition.

**Actions**

- **Multiattack.** The hobgoblin makes two attacks, using Greatsword or Longbow in any combination.
- **Greatsword.** Melee Attack Roll: +4, reach 5 ft. Hit: 9 (2d6 + 2) Slashing damage plus 3 (1d6) Poison damage.
- **Longbow.** Ranged Attack Roll: +4, range 150/600 ft. Hit: 6 (1d8 + 2) Piercing damage plus 5 (2d4) Poison damage.

*No Description, no Skills, no Reactions, no Bonus Actions, no Legendary Actions/Resistances. This Volo-era rendering is substantially weaker than the 2014 print (#15) despite the higher HP: 58 vs 39, but no Javelin, no Leadership, and smaller per-hit damage.*

---

#### 15. Hobgoblin Captain — Monster Manual (2014) *(p. 10)*

- **Source:** Monster Manual (2014) — marked **Legacy**
- **Tags:** GOBLINOID · **Habitat:** DESERT, FOREST, GRASSLAND, HILL, UNDERDARK
- **Search-result meta:** `3 Hobgoblin Ca…` *(name truncated in the results column)* · Humanoid (Goblinoid) · Medium · Lawful Evil

| Field | Value |
|---|---|
| Size/Type/Alignment | Medium Humanoid (Goblinoid), Lawful Evil |
| Armor Class | 17 (half plate) |
| Hit Points | 39 (6d8 + 12) |
| Speed | 30 ft. |

| | STR | DEX | CON | INT | WIS | CHA |
|---|---|---|---|---|---|---|
| Score | 15 | 14 | 14 | 12 | 10 | 13 |
| Mod | +2 | +2 | +2 | +1 | +0 | +1 |

*(No save column in this rendering.)*

- **Senses** Darkvision 60 ft., Passive Perception 10
- **Languages** Common, Goblin
- **Challenge** 3 (700 XP) · Proficiency Bonus +2

**Traits**

- **Martial Advantage.** Once per turn, the hobgoblin can deal an extra 10 (3d6) damage to a creature it hits with a weapon attack if that creature is within 5 feet of an ally of the hobgoblin that isn't incapacitated.

**Actions**

- **Multiattack.** The hobgoblin makes two greatsword attacks.
- **Greatsword.** Melee Weapon Attack: +4 to hit, reach 5 ft., one target. Hit: 9 (2d6 + 2) piercing damage.
- **Javelin.** Melee or Ranged Weapon Attack: +4 to hit, reach 5 ft. or range 30/120 ft., one target. Hit: 5 (1d6 + 2) piercing damage.
- **Leadership (Recharges after a Short or Long Rest).** For 1 minute, the hobgoblin can utter a special command or warning whenever a nonhostile creature that it can see within 30 feet of it makes an attack roll or a saving throw. The creature can add a d4 to its roll provided it can hear and understand the hobgoblin. A creature can benefit from only one Leadership die at a time. This effect ends if the hobgoblin is incapacitated.

*No Gear line, no Skills, no Description, no Reactions, no Bonus Actions, no Legendary Actions/Resistances.*

---

#### 16. Hobgoblin Devastator — Mordenkainen's Presents: Monsters of the Multiverse *(p. 10)*

- **Source:** Mordenkainen's Presents: Monsters of the Multiverse — no `Tags:` line
- **Search-result meta:** `4 Hobgoblin Devastator` · Fey (Goblinoid) · Medium · Typically Lawful Neutral
- **Habitat:** FOREST, GRASSLAND, HILL

**Description**

> Hobgoblins with a prodigious talent for magic sometimes undergo grueling training to become hobgoblin devastators. Devastators are spellcasters who call down fireballs and other destructive magic in the defense of the court they serve, whether that court is in the Feywild or the Material Plane. A hobgoblin devastator on the battlefield is a boon to their allies and a threat to every foe around them.
>
> Far from being cloistered academics, hobgoblin devastators are masters of the battlefield. In addition to tactical applications of the magical arts, they learn the basics of weapon use, and they measure their deeds by the enemies defeated though their magic. They have the respect of other members of the host and receive obedience and deference from many quarters.
>
> In the Feywild, many archfey seek to bolster their armies' might with the services of hobgoblin devastators.

| Field | Value |
|---|---|
| Size/Type/Alignment | Medium Fey (Goblinoid), Typically Lawful Neutral |
| Armor Class | 13 (studded leather) |
| Hit Points | 45 (7d8 + 14) |
| Speed | 30 ft. |

| | STR | DEX | CON | INT | WIS | CHA |
|---|---|---|---|---|---|---|
| Score | 13 | 12 | 14 | 16 | 13 | 11 |
| Mod | +1 | +1 | +2 | +3 | +1 | +0 |

*(No save column in this rendering.)*

- **Skills** Arcana +5
- **Senses** Darkvision 60 ft., Passive Perception 11
- **Languages** Common, Goblin
- **Challenge** 4 (1,100 XP) · Proficiency Bonus +2

**Traits**

- **Army Arcana.** When the hobgoblin casts a spell that causes damage or that forces other creatures to make a saving throw, it can choose itself and any number of allies to be immune to the damage caused by the spell and to succeed on the required saving throw.

**Actions**

- **Multiattack.** The hobgoblin makes two Quarterstaff or Devastating Bolt attacks.
- **Quarterstaff.** Melee Weapon Attack: +3 to hit, reach 5 ft., one target. Hit: 4 (1d6 + 1) bludgeoning damage, or 5 (1d8 + 1) bludgeoning damage if used with two hands, plus 13 (3d8) force damage.
- **Devastating Bolt.** Ranged Spell Attack: +5 to hit, range 60 ft., one target. Hit: 21 (4d8 + 3) force damage, and the target is knocked prone.
- **Spellcasting.** The hobgoblin casts one of the following spells, using Intelligence as the spellcasting ability (spell save DC 13):
  - At will: mage hand, prestidigitation
  - 2/day each: fireball, fly, fog cloud, gust of wind, lightning bolt

*No Gear line, no Description beyond the three paragraphs above, no Reactions, no Bonus Actions, no Legendary Actions/Resistances.*

**Sidebox: GOBLINOIDS OF THE FEYWILD** *(printed below this stat block, p. 11)*

> The goblinoid peoples—goblins, hobgoblins, and bugbears—first appeared in the Feywild millennia ago, and they resided there until the god Maglubiyet conquered them. They then spread throughout the multiverse, with many of them ending up on the worlds of the Material Plane. Most goblinoids encountered on those worlds are members of families that have been away from the Feywild for centuries and over time those lineages have become Humanoid. Fey goblinoids, who still bear the magic of the Feywild, are rare on the Material Plane but not unheard of. Hobgoblin devastators are examples of such Fey folk, as are hobgoblin iron shadows and nilbogs.

*The first sentence of paragraph one is split by the p. 11 / p. 12 page break at `…those lineages have` / `members of families that have been away from…`; it is joined above. This identical sidebox is printed a second time on p. 14 under Hobgoblin Iron Shadow, in a cleaned-up form with the missing comma restored (`…for centuries, and over time, those lineages have become Humanoid.`).*

---

#### 17. Hobgoblin Devastator — Volo's Guide to Monsters *(p. 12)*

- **Source:** Volo's Guide to Monsters — marked **Legacy**
- **Tags:** GOBLINOID · **Habitat:** FOREST, GRASSLAND, HILL
- **Search-result meta:** `4 Hobgoblin De…` *(name truncated in the results column)* · Humanoid (Goblinoid) · Medium · Lawful Evil

| Field | Value |
|---|---|
| Size/Type/Alignment | Medium Humanoid (Goblinoid), Lawful Evil |
| Armor Class | 13 (studded leather) |
| Hit Points | 45 (7d8 + 14) |
| Speed | 30 ft. |

| | STR | DEX | CON | INT | WIS | CHA |
|---|---|---|---|---|---|---|
| Score | 13 | 12 | 14 | 16 | 13 | 11 |
| Mod | +1 | +1 | +2 | +3 | +1 | +0 |

*(No save column in this rendering.)*

- **Skills** Arcana +5
- **Senses** Darkvision 60 ft., Passive Perception 11
- **Languages** Common, Goblin
- **Challenge** 4 (1,100 XP) · Proficiency Bonus +2

**Traits**

- **Arcane Advantage.** Once per turn, the hobgoblin can deal an extra 7 (2d6) damage to a creature it hits with a damaging spell attack if that target is within 5 feet of an ally of the hobgoblin and that ally isn't incapacitated.
- **Army Arcana.** When the hobgoblin casts a spell that causes damage or that forces other creatures to make a saving throw, it can choose itself and any number of allies to be immune to the damage caused by the spell and to succeed on the required saving throw.
- **Spellcasting.** The hobgoblin is a 7th-level spellcaster. Its spellcasting ability is Intelligence (spell save DC 13, +5 to hit with spell attacks). It has the following wizard spells prepared:
  - Cantrips (at will): acid splash, fire bolt, ray of frost, shocking grasp
  - 1st level (4 slots): fog cloud, magic missile, thunderwave
  - 2nd level (3 slots): gust of wind, Melf's acid arrow, scorching ray
  - 3rd level (3 slots): fireball, fly, lightning bolt
  - 4th level (1 slot): ice storm

**Actions**

- **Quarterstaff.** Melee Weapon Attack: +3 to hit, reach 5 ft., one target. Hit: 4 (1d6 + 1) bludgeoning damage, or 5 (1d8 + 1) bludgeoning damage if used with two hands.

*[…continues…] — the export ends this block mid-page-12. The MotM version (#16) is a different, weaker creature; it does **not** supply the missing text. The official 2014 Volo's version of Hobgoblin Devastator has additional actions after Quarterstaff (a shortbow, a `Devastating Bolt`-style ranged spell attack, and the `Spellcasting` action line), but those lines are **not present in this document** and must not be reconstructed from the print edition if the document is to remain faithful.]*

**Extraction notes for this block**

- The `Tags: GOBLINOID Habitat:FOREST GRASSLAND HILL Volo's Guide to Monsters` line for this entry is printed at the top of **p. 13**, not with the block itself, because the two-column layout defers the results-column metadata. It is attributed here.
- No `Description` prose is printed for the Volo's rendering of this creature (only the MotM rendering, #16, carries one).

---

#### 18. Hobgoblin Iron Shadow — Mordenkainen's Presents: Monsters of the Multiverse *(p. 13)*

- **Source:** Mordenkainen's Presents: Monsters of the Multiverse — no `Tags:` line
- **Search-result meta:** `2 Hobgoblin Iron Shad…` *(name truncated in the results column)* · Fey (Goblinoid) · Medium · Typically Lawful Neutral
- **Habitat:** FOREST, GRASSLAND, HILL

**Description**

> Iron shadows are hobgoblin martial artists who serve fey and mortal courts as secret police, scouts, and assassins. They spy to ferret out treachery, rebellion, and betrayal and deal with it ruthlessly. Iron shadows possess agility and stamina matched only by their ironclad commitment to the will of their masters. They wield a deadly combination of unarmed fighting techniques and shadow magic to deceive and defeat their foes. While on secret missions, they wear masks crafted to resemble monsters, both to conceal their identities and to strike fear into their foes.
>
> An iron shadow is usually recruited from the ranks of the Feywild's hobgoblin armies or from among the hobgoblins who have resided in the Material Plane for centuries. A candidate for admission undergoes a series of tests designed to reveal any potential for treachery. Those who fail are slain, while those who pass receive secret training in the arts of magic and stealth. This indoctrination is a slow and arduous process; many aspirants don't finish it, and years might go by during which the iron shadows welcome no new members into their ranks. When a recruit's training is complete, they are tasked with conducting assassinations and spy missions.

*(The second paragraph starts on p. 13 and is completed on p. 14 after the p. 13 / p. 14 page break; both halves are joined above.)*

| Field | Value |
|---|---|
| Size/Type/Alignment | Medium Fey (Goblinoid), Typically Lawful Neutral |
| Armor Class | 15 (unarmored defense) |
| Hit Points | 32 (5d8 + 10) |
| Speed | 40 ft. |

| | STR | DEX | CON | INT | WIS | CHA |
|---|---|---|---|---|---|---|
| Score | 14 | 16 | 15 | 14 | 15 | 11 |
| Mod | +2 | +3 | +2 | +2 | +2 | +0 |

*(No save column in this rendering.)*

- **Skills** Acrobatics +5, Athletics +4, Stealth +5
- **Senses** Darkvision 60 ft., Passive Perception 12
- **Languages** Common, Goblin
- **Challenge** 2 (450 XP) · Proficiency Bonus +2

**Traits**

- **Unarmored Defense.** While the hobgoblin is wearing no armor and wielding no shield, its AC includes its Wisdom modifier.

**Actions**

- **Multiattack.** The hobgoblin makes four attacks, each of which can be an Unarmed Strike or a Dart attack. It can also use Shadow Jaunt once, either before or after one of the attacks.
- **Unarmed Strike.** Melee Weapon Attack: +5 to hit, reach 5 ft., one target. Hit: 5 (1d4 + 3) bludgeoning damage.
- **Dart.** Ranged Weapon Attack: +5 to hit, range 20/60 ft., one target. Hit: 5 (1d4 + 3) piercing damage.
- **Shadow Jaunt.** The hobgoblin teleports, along with any equipment it is wearing or carrying, up to 30 feet to an unoccupied space it can see. Both the space it leaves and its destination must be in dim light or darkness.
- **Spellcasting.** The hobgoblin casts one of the following spells, using Intelligence as the spellcasting ability (spell save DC 12):
  - At will: minor illusion, prestidigitation
  - 1/day each: charm person, disguise self, silent image

*No Gear line, no Reactions, no Bonus Actions, no Legendary Actions/Resistances.*

*Sidebox: the identical **GOBLINOIDS OF THE FEYWILD** text as in #16, printed again on p. 14 in its comma-corrected form.*

---

#### 19. Hobgoblin Iron Shadow — Volo's Guide to Monsters *(p. 14)*

- **Source:** Volo's Guide to Monsters — marked **Legacy**
- **Tags:** GOBLINOID · **Habitat:** FOREST, GRASSLAND, HILL
- **Search-result meta:** `2 Hobgoblin Iro…` *(name truncated in the results column)* · Humanoid (Goblinoid) · Medium · Lawful Evil

| Field | Value |
|---|---|
| Size/Type/Alignment | Medium Humanoid (Goblinoid), Lawful Evil |
| Armor Class | 15 *(no armour source given; see Unarmored Defense below)* |
| Hit Points | 32 (5d8 + 10) |
| Speed | 40 ft. |

| | STR | DEX | CON | INT | WIS | CHA |
|---|---|---|---|---|---|---|
| Score | 14 | 16 | 15 | 14 | 15 | 11 |
| Mod | +2 | +3 | +2 | +2 | +2 | +0 |

*(No save column in this rendering.)*

- **Skills** Acrobatics +5, Athletics +4, Stealth +5
- **Senses** Darkvision 60 ft., Passive Perception 12
- **Languages** Common, Goblin
- **Challenge** 2 (450 XP) · Proficiency Bonus +2

**Traits**

- **Spellcasting.** The hobgoblin is a 2nd-level spellcaster. Its spellcasting ability is Intelligence (spell save DC 12, +4 to hit with spell attacks). It has the following wizard spells prepared:
  - Cantrips (at will): minor illusion, prestidigitation, true strike
  - 1st level (3 slots): charm person, disguise self, expeditious retreat, silent image
- **Unarmored Defense.** While the hobgoblin is wearing no armor and wielding no shield, its AC includes its Wisdom modifier.

**Actions**

- **Multiattack.** The hobgoblin makes four attacks, each of which can be an unarmed strike or a dart attack. It can also use Shadow Jaunt once, either before or after one of the attacks.
- **Unarmed Strike.** Melee Weapon Attack: +5 to hit, reach 5 ft., one target. Hit: 5 (1d4 + 3) bludgeoning damage.
- **Dart.** Ranged Weapon Attack: +5 to hit, range 20/60 ft., one target. Hit: 5 (1d4 + 3) piercing damage.
- **Shadow Jaunt.** The hobgoblin magically teleports, along with any equipment it is wearing or carrying, up to 30 feet to an unoccupied space it can see. Both the space it is leaving and its destination must be in dim light or darkness.

*No Gear line, no Description prose for this rendering, no Reactions, no Bonus Actions, no Legendary Actions/Resistances.*

**Extraction notes for this block**

- Line 757 of the source is a collided fragment reading `1stlevel(3slots):charmperson disguiseself expeditious alsouseShadowJauntonce eitherbeforeorafterone`. It is two unrelated strings overlaid: the tail of the `1st level (3 slots): charm person, disguise self, expeditious retreat, silent image` spell list (the clean version is printed at the top of p. 15, lines 764–765) **and** the trailing fragment of the `Multiattack` sentence `…also use Shadow Jaunt once, either before or after one [of the attacks]`. Both are reproduced in their correct positions above; nothing is lost.

---

#### 20. Hobgoblin Warlord — Monster Manual (Volo's-era render) *(p. 15)*

- **Source:** Monster Manual (Volo's-era render) — no `Tags:` line
- **Search-result meta:** `6 Hobgoblin Warlord` · Fey (Goblinoid) · Medium · Lawful Evil
- **Habitat:** DESERT, FOREST, GRASSLAND, HILL, MOUNTAIN, PLANAR (ACHERON), UNDERDARK · **Treasure:** Armaments, Individual

| Field | Value |
|---|---|
| Size/Type/Alignment | Medium Fey (Goblinoid), Lawful Evil |
| AC | 20 · *Initiative +5 (15)* |
| HP | 112 (15d8 + 45) |
| Speed | 30 ft. |

| | STR | DEX | CON | INT | WIS | CHA |
|---|---|---|---|---|---|---|
| Mod | +3 | +2 | +3 | +2 | +0 | +2 |
| **Save** | **+3** | **+5** | **+3** | **+5** | **+3** | **+5** |

**⚠ Internal inconsistency in the source, transcribed as printed:** the save column runs `+3 / +5 / +3 / +5 / +3 / +5` in ability order (STR, DEX, CON, INT, WIS, CHA), but the WIS row reads `WIS 11 +0 +3` — a save bonus of **+3 on a +0 Wisdom**, while the neighbouring CHA row carries a +5 save on +2 Charisma. This is almost certainly a PDF text-layer/OCR artefact rather than an authored value, but it is reproduced verbatim rather than silently normalised. The `MOD` / `SAVE` header pair is printed twice (repeating table header) and is collapsed into one table.

- **Gear** Javelins (9), Longsword, Plate Armor, Shield
- **Senses** Darkvision 60 ft.; Passive Perception 10
- **Languages** Common, Goblin
- **CR** 6 (XP 2,300; PB +3)

**Traits**

- **Aura of Authority.** While in a 30-foot Emanation originating from the hobgoblin, the hobgoblin and its allies have Advantage on attack rolls and saving throws, provided the hobgoblin doesn't have the Incapacitated condition.

**Actions**

- **Multiattack.** The hobgoblin makes three attacks, using Javelin or Longsword in any combination.
- **Javelin.** Melee or Ranged Attack Roll: +6, reach 5 ft. or range 30/120 ft. Hit: 11 (2d6 + 4) Piercing damage, and the target's Speed decreases by 10 feet until the start of the hobgoblin's next turn.
- **Longsword.** Melee Attack Roll: +6, reach 5 ft. Hit: 12 (2d8 + 3) Slashing damage.

**Reactions**

- **Parry.** Trigger: The hobgoblin is hit by a melee attack roll while holding a weapon: Response: The hobgoblin adds 3 to its AC against that attack, possibly causing it to miss.

*No Skills, no Description prose, no Bonus Actions, no Spellcasting, no Legendary Actions/Resistances. This is the only creature in the entire export with HP above 100.*

**Extraction notes for this block**

- The `6 Hobgoblin Warlord / Monster Manual` results-column row is printed **after** the stat block (lines 819–823), because the results column for the last item is flushed below the detail pane at the bottom of the page. The stat block itself (lines 783–818) precedes it and is complete apart from the `Parry` reaction, whose text is split by the p. 15 / p. 16 page break.
- Line 818 of the source ends the reaction mid-word-runs: `3toitsACagainstthatattack possiblycausingitto`. The continuation is at the top of p. 16 (lines 868–869): `3 to its AC against that attack, possibly causing it to` / `miss.` The full sentence is reassembled above.

---

### Cross-block note: creatures with no data at all

Four of the twenty results are **marketplace-locked** and contain zero stat data in this export: Goblin Boss (Variant), Goblin Psi Brawler, Goblin Psi Commander (all *Phandelver and Below: The Shattered Obelisk*) and Goblin Warrior (Stranger Things variant) (*Stranger Things: Welcome to the Hellfire Club*). Only their CR badges, creature types, sizes and alignments were printed.

### Cross-block note: no Legendary anything

**No creature in this export has Legendary Actions, Legendary Resistances, a Reaction-based legendary turn, or a `Recharge` mechanic on an action** — the only `Recharges` text in the whole document is Hobgoblin Captain (2014)'s `Leadership (Recharges after a Short or Long Rest)`. This is normal for goblinoids (they are CR 0–6 with no legendaries) but it means this export provides **no examples of 5e's legendary-action design** for engine reference.

### Viwo notes

Mapping this export onto a persistent-world sim whose combat model is **`d20 + STR` (offence) vs `d20 + DEX` (defence), with no armor class**, whose **HP floor is 100**, and which resolves everything else as **`d20 + ability mod vs DC`** against a DC band table.

#### 1. Trivially usable — drop these in as-is

- **Ability modifiers.** This is the cleanest possible fit. The model is literally `d20 + STR` vs `d20 + DEX`, and 5e prints exactly `STR <score> (<mod>)`. The whole goblinoid family is a *DEX-favoured* set (`DEX 14–16, +2/+3` against `STR 8–17, −1/+3`), which means in this engine a goblin simply loses to a hobgoblin captain in a footrace and wins nothing offensively. Store the modifier, discard the base score (or keep the score for flavour only — the engine never needs it). Sample: Goblin `DEX 14 (+2)`; Goblin Gang Member `DEX 16 (+3)`; Hobgoblin Warlord `STR 17 (+3)`.
- **The `MOD`/`SAVE` split column.** Directly usable as a per-ability defensive value *if and only if* a "does this stat block get a save bonus" decision is made explicitly. Caveat: in 8 of the 9 blocks that print it, the save equals the mod (save is a no-op); only Hobgoblin Warlord has save ≠ mod, and even there the values look like an OCR artefact. **Recommendation: ignore the save column entirely and use the mod**, then verify nothing in the engine depends on a separate save track.
- **HP dice expression.** The *expression* is directly parseable and is the right authoring format: `7 (2d6)`, `45 (10d6 + 10)`, `112 (15d8 + 45)`, `39 (6d8 + 12)`. It is worth keeping as an authored string because it is the only part of 5e HP that scales coherently with CON.
- **Damage dice expressions.** Same story: `5 (1d6 + 2)`, `21 (4d8 + 3)`, `9 (2d6 + 2)`, `11 (2d6 + 4)` are all directly runnable. Note the Volo-era print appends damage *types* (`Slashing`, `Piercing`, `Psychic`, `Force`, `Poison`) — see the damage-type caveat below.
- **Senses.** `Darkvision 60 ft.` and `Passive Perception 9/10/11/12` are trivially portable. Passive Perception is literally `10 + WIS mod` (+5 when proficient) and can be recomputed rather than stored. Darkvision 60 ft. maps cleanly onto a sight-radius / light-level flag in a grid world.
- **Languages.** A flat tag set: `Common, Goblin`. Two entries are usefully *negative* data points: Goblin Commoner has `Goblin` only (no Common, no darkvision, no skills) — that is a ready-made "NPC that cannot be negotiated with" flag.
- **Gear / Equipment.** `Chain Shirt, Scimitar, Shield, Shortbow`; `Daggers 3`; `Greatsword, Half Plate Armor, Longbow`; `Javelins (9), Longsword, Plate Armor, Shield`. The *quantities* (`3`, `(9)`) are the useful bit and are routinely dropped by hand-transcribers.
- **Speed.** `30 ft.` / `40 ft.` → cells, with the engine's own scale deciding the cell size.
- **CR and XP as pure bookkeeping.** Not as mechanics — but `(50 XP)`, `(100 XP)`, `(200 XP)`, `(450 XP)`, `(700 XP)`, `(1,100 XP)`, `(2,300 XP)` are a ready-made difficulty budget table for spawning, *provided* the budget is not tied to the HP/AC values below.

#### 2. No counterpart at all — needs new engine concepts

- **Armor Class (AC).** The single largest incompatibility. There is no AC in the `d20 + STR` vs `d20 + DEX` model, and AC is doing a great deal of load-bearing work in these blocks: it is the *only* mechanical difference between a CR 1/4 Goblin (AC 15, leather + shield) and a CR 1/4 Goblin Gang Member (AC 14, leather only) and between that and a Goblin Commoner (AC 10, nothing). If AC is dropped, those three become mechanically identical, because the `+4 to hit` attack bonus is `DEX mod + PB` in all three cases. Every armour string in the export — `leather armor, shield`; `chain shirt, shield`; `leather armor`; `chain mail, shield`; `half plate`; `studded leather`; `plate armor, shield`; and the trait `Unarmored Defense` — is data with nowhere to go. **If the engine wants to keep AC, it needs a new concept for it (a defense target, a fixed difficulty tier, or a damage-reduction bucket) and a way to derive it from the armour string.** Note also that 5e AC is a *dodge-to-hit* target, not a hit-point budget, so even a faithful implementation is not the same thing as a defence stat the engine can compare STR/DEX rolls against.
- **HP values themselves — this is where the floor bites.** With a floor of 100, **19 of the 20 results in this export clamp to exactly 100 HP**: Goblin Commoner 3, Goblin 7, Goblin Minion 7, Goblin Gang Member 10, Goblin Warrior 10, Hobgoblin 11, Goblin Boss 21, Hobgoblin Iron Shadow 32, Hobgoblin Captain (2014) 39, Goblin Hexer 45, Hobgoblin Devastator 45 (both versions), Hobgoblin Captain (Volo's) 58 — and only Hobgoblin Warlord at 112 survives above the floor. That collapses a deliberate CR 0 → CR 6 spread and a 37× HP range into a single number. Nothing in a 100-HP-floor engine can distinguish a goblin commoner from a hobgoblin captain by health; **the engine would need a different axis entirely** (a damage-output-per-turn axis, a tier/tag axis, or a percentage-of-max-HP damage model) or the 5e HP column is simply discarded. It is not a matter of rescaling: rescaling would require abandoning the 100 floor, which is a stated engine constant.
- **Challenge Rating (CR).** No engine concept corresponds. CR is a *design-budget* label; in this engine the budget axis is STR-vs-DEX plus HP, and as shown above the HP axis is flattened. Options: (a) store CR as a pure difficulty/tier tag used only by the spawner, and never let it touch a resolution rule; (b) introduce a `tier` concept and map CR onto it. Do **not** try to make CR mean "how many d20s of damage this thing deals" without a full 5e-accurate math engine behind it.
- **Proficiency Bonus (PB).** `+2` for everything CR 0–4, `+3` for Hobgoblin Warlord. The model has no PB, but 5e uses PB *everywhere*: attack rolls (`+4 to hit` = `STR/DEX mod + PB` for a proficient attack), spell save DC (`8 + PB + INT mod` = 13 for the Hexer/Devastator, 12 for the Iron Shadow), Passive Perception (+5 when proficient), and Skills. Dropping PB outright is the worst option available: it flattens the Golbin (`+4`) and the Hobgoblin Warlord (`+6`) to a difference of *modifiers only*, and it makes every 5e attack bonus in the export un-derivable. **The engine needs either a PB/training constant, or a documented decision to fold PB into the published to-hit numbers and stop storing ability scores as if they were the whole story.** Note that a *skill* total like `Stealth +6` is itself a 5-formula (`+3 DEX +2 proficiency`); if the engine computes skills from ability mods alone it will under-report them by 2–5 across this entire set.
- **Multiattack.** No counterpart — a `d20 + STR vs d20 + DEX` contest resolves **one** exchange. `Multiattack` appears in 6 blocks (Goblin Boss ×2, Goblin Hexer, Goblin Warrior 2014, Hobgoblin Captain ×2, Hobgoblin Devastator, Hobgoblin Iron Shadow ×2, Hobgoblin Warlord) with attack counts of **2, 3 and 4** — and the Iron Shadow's *four* attacks against a single STR/DEX roll is a completely different shape of problem. A persistent-world engine needs either (a) an explicit "extra attacks per resolution" field that multiplies the damage roll, or (b) an accepted loss where higher-CR creatures simply do proportionally more damage in one roll.
- **Advantage / Disadvantage.** Not in the model (which is a flat `d20 + mod` with no second roll). This export leans on it hard and in *two* distinct ways, both unmodelable: (i) the **damage rider** `plus 2 (1d4) Slashing damage if the attack roll had Advantage` (Goblin Boss Volo's, Goblin Warrior) — an expected-value swing, not a die; and (ii) **"the second attack has disadvantage"** (Goblin Boss 2014) and **"Aura of Authority … have Advantage on attack rolls"** (Hobgoblin Captain ×2, Hobgoblin Warlord). Every one of these is a *conditional d20 modifier the engine has no slot for*.
- **Bonus Actions.** `Nimble Escape` (Disengage or Hide as a bonus action) appears on Goblin, Goblin Boss ×2, Goblin Minion, Goblin Gang Member, Goblin Warrior. The engine's one-action-per-resolution model has no bonus-action economy, so this is a **whole action-category concept** (or an accepted drop). Note the 5e-2014 render puts Nimble Escape in *Traits* while the Volo-era render puts it in *Bonus Actions* — the same ability, two different taxonomies, which is a hazard for any importer.
- **Reactions.** Three distinct reactions in the export — `Redirect Attack` (Goblin Boss ×2: swap places with a Small/Medium ally, becoming the target instead), `Jinx` (Goblin Hexer: the *attacker* makes a WIS save or the attack misses), `Parry` (Hobgoblin Warlord: +3 AC against the triggering melee attack). All three are **intercept-the-outcome** hooks, i.e. they modify a roll that has already been declared. None is expressible as a `d20 + mod vs DC` check. `Jinx` is the nastiest case because it inverts the flow — it makes the *target* of the attack spend a reaction to save.
- **Spellcasting / spell slots.** `At will`, `1/Day Each`, `2/day each`, and full 7th-level / 2nd-level prepared lists with per-level slot counts (`1st level (4 slots)`, `4th level (1 slot)`) and 24-hour-class recharge. Goblin Hexer, Hobgoblin Devastator ×2 and Hobgoblin Iron Shadow ×2 all use this. A persistent-world sim with no daily-turn cycle has no slot-recharge clock; this needs a resource-regeneration concept or a flat "cast X times ever" flag.
- **`Recharges after a Short or Long Rest`** (Hobgoblin Captain 2014, `Leadership`) — a rest-cycle concept the engine does not have.
- **Auras / Emana­tions.** `Aura of Authority` (10 ft. and 30 ft. radii) is a persistent area effect granting Advantage to self and allies, gated on the `Incapacitated` condition. A grid engine *could* express this as a per-tick aura scan; the engine here has no such pass described.
- **Conditions.** `Incapacitated` gates Martial Advantage, Army Arcana, Aura of Authority and Leadership. `Knocked Prone` (Devastating Bolt), `Darkvision`-conditional teleport (Shadow Jaunt requires both origin and destination in dim light or darkness), and the `Speed decreases by 10 feet` rider on the Warlord's Javelin, are all state the engine would need. **Shadow Jaunt in particular requires the grid to model light level at two cells at once** — a real feature request, not a stat.
- **Damage types.** The Volo-era print tags every attack (`Slashing`, `Piercing`, `Bludgeoning`, `Psychic`, `Force`, `Poison`) and Hobgoblin Captain's attacks are *dual-type* (`9 (2d6 + 2) Slashing damage plus 3 (1d6) Poison damage`). The 2014 print tags nothing and instead has typeless riders. If the engine has no resistance/immunity/vulnerability layer, **the type tags are dead metadata and the Poison rider becomes meaningless** — the Captain's 12 damage becomes an undifferentiated 12.
- **Turn structure / initiative.** `Initiative +2 (12)`, `+3 (13)`, `+4 (14)`, `+5 (15)` are D&D Beyond's computed DEX-mod-plus-PB display values, not raw modifiers. In an engine where DEX also *is* the defence stat, initiative and defence collapse into one number — a goblin that is good to dodge is also first in line, which is a design consequence the engine has to accept, not a transcription problem.
- **XP-based encounter budgeting.** `Challenge 1 (XP 200; PB +2)` pairs CR with XP. If the engine ever wants to spend XP to gate a fight, note that the same XP is attached to two materially different creatures in this very export: Goblin Boss 2014 (21 HP, no advantage riders) and Goblin Boss Volo's (21 HP, +2 (1d4) riders, bonus action, Redirect Attack) are both CR 1 / 200 XP. **XP is not a reliable difficulty signal even within 5e**, so it should not become one here.
- **Gear as a mechanical source.** The `Armor Class 17 (chain shirt, shield)` parenthetical is the *only* place the gear's mechanical effect appears; the Gear line itself is inert. If gear is dropped, the AC value must be kept as a literal number or the block loses its entire defensive identity.

#### 3. Concrete recommended import mapping

| 5e field | Engine disposition |
|---|---|
| Ability modifier | **Use directly.** Discard base score. |
| HP dice expression | **Keep as authored string**, but the *evaluated value* is dead — 19/20 results clamp to the 100 floor. |
| Speed | Use directly (ft → cell). |
| Skills totals | **Recompute or re-derive**; published totals silently include a +2/+5 proficiency the engine does not model. |
| Senses, Languages | Use directly as flags/numbers. |
| Gear quantities | Use directly. Gear *names* are inert; the `Armor Class N (gear)` parenthetical is the only mechanical payload. |
| Damage dice expressions | Use directly, **minus damage types** unless a resistance layer is added. |
| **AC** | **No counterpart.** Needs a defense-target concept or must be discarded entirely. |
| **CR** | **No counterpart.** Keep as a spawner-only difficulty tag at most. |
| **XP** | **No counterpart.** Even as a difficulty tag it is unreliable (see Goblin Boss). |
| **Proficiency Bonus** | **No counterpart, and load-bearing everywhere.** Needs a training constant or an explicit fold-in. |
| **Multiattack** | **No counterpart.** Needs an attacks-per-resolution field or an accepted loss. |
| **Legendary Actions / Resistances** | **No counterpart, and no examples in this export** — nothing to transcribe, so nothing to port from this file. |
| Advantage / Disadvantage | **No counterpart.** Affects damage riders, attack count, and auras. |
| Bonus Actions, Reactions | **No counterpart.** Need an action-economy and an intercept-the-outcome hook. |
| Spellcasting, slots, rests | **No counterpart.** Needs a resource-recharge concept or a flat budget. |
| Auras, conditions, light-level gating | **No counterpart.** `Shadow Jaunt` and `Aura of Authority` need grid passes. |

**Bottom line:** roughly a third of each block (the six ability modifiers, the dice expressions, senses, languages, gear counts, speed) ports across untouched. The remaining two-thirds — CR, XP, PB, AC, Multiattack, advantage, bonus actions, reactions, spell slots, auras and conditions — are all *layered on top of* the AC + PB + action-economy system that `d20 + STR vs d20 + DEX` deliberately replaces, and each would need a genuinely new engine concept rather than a translation. The HP floor of 100 is the sharpest single incompatibility: it erases the entire CR 0–3 power gradient in this export and leaves only Hobgoblin Warlord (112 HP) distinguishable by health at all.

---

## Viwo build priority

The four `### Viwo notes` sections map content to modules. This is the same material,
**ranked**, with the tables that cost almost nothing to adopt first. Every "add" below is a
data file or a small table in an existing module — no new subsystems.

### Tier 0 — pure data, drop into `data/library/`, no engine change

| Content | Lands in | Why first |
|---|---|---|
| **26 Tool Sample DC tables** (XGtE p. 6–23) | new `data/library/tools/` DC table | 60+ activity→DC pairs already shaped like `engine/checks.py` `DCS` bands; also the natural seed for the 18 occupations in `data/library/roles.json` |
| **14× Monsters' Desires d4** (TCoE p. 23–27) | `data/library/` + `engine/background_social.py` | the single cleanest social mechanic in the set: *offering match ⇒ advantage on the communication check* |
| **8× d100 Supernatural Regions** (TCoE p. 27–47) | `data/library/areas/` + `engine/trigger_system.py` | ~130 usable effects that are already written as trigger + effect + duration; several are per-tick ("1 exhaustion per hour") |
| **12 hazards + 8 traps + Building a Trap** (DMG p. 50–112) | new trap/hazard registry | `engine/traps` does not exist; *Building a Trap* is a complete authoring spec (attack bonus, DC band, damage ladder per level) |
| **NPC generators** — 6 name tables, Appearance 1d12, Secrets 1d10 (DMG p. 68–74) | `engine/population.py` | the cheapest possible NPC texture; the Secrets table is a ready-made motive seed |
| **Settlements by Size** (DMG p. 87) | `data/library/areas/` | gates item availability by the **Max. GP Value** column (20 / 2,000 / 200,000 GP). Eldenford at 1,500–2,000 inhabitants = **Town band ⇒ 2,000 GP ceiling** |
| **14 poisons** (DMG p. 81–84) | `data/library/items/` + `data/library/conditions/` | complete data: price, delivery type, save DC 11–21, damage, duration, secondary condition |
| **Dungeon Quirks 1d100** (36 rows) | `data/worldpainter/biomes.json` | descriptive tags, zero mechanical cost |
| **Blessings (7) / Charms (7)** (DMG p. 100–103) | `data/library/traits/` / `data/library/items/` | Charms already carry a use count (1, 3, 3 charges, 9/10-day timers) — a perfect fit for the existing item-charge model |

### Tier 1 — small table or hook in an existing module

| Content | Lands in | Note |
|---|---|---|
| **Mob Results** + **Targets in Area of Effect** (DMG p. 64–66) | `engine/combat.py` | keeps resolution to **one roll per group**, not N. Directly relevant to the simultaneous-mode parallel turn loop |
| **Loyalty Score 0–20** (DMG p. 78) | `engine/relationships.py` | max = highest party CHA, start = half, +1d4 / −1d4 / −2d4, 0 = betrayal. A ready-made ally/betrayal meter |
| **Renown thresholds** (DMG p. 84–86) | `engine/promotion.py`, `engine/relationships.py` | 3+ / 10+ / 25 / 50 map onto the existing **Promote** entry point |
| **Mark of Prestige** (DMG p. 58–62) | `engine/promotion.py` | titles, favours, rights, land; **Special Favors** is behaviour keyed on the granter's alignment — clean input for NPC disposition |
| **Chase complication 1d12** tables (DMG p. 8–9) | `data/library/` roll table | one roll per participant per turn — a clean fit for a 1-minute turn |
| **Escape Factors** (DMG p. 7) | `engine/checks.py` | Adv/Dis by crowding: a circumstance-modifier lookup, exactly what a check-modifier hook wants |
| **Environmental hazard clocks** (DMG p. 36) | `engine/environment_propagation.py`, `engine/weather_forecast.py` | extreme heat = **DC 5, +1 per extra hour**; frigid water = minutes equal to CON; deep water / extreme cold = DC 10 CON per hour → 1 Exhaustion |
| **Emotional Echoes** (TCoE p. 48) | `data/library/traits/` | one trait with a parameterised `emotion` and an `area_scope` of room→forest; once/day DC 16 |
| **Monster Research DC = 10 + CR** (TCoE p. 22) | `engine/checks.py` | a CR-scaled DC helper beside the existing `DCS` band dict |
| **Identify a Spell: DC = 15 + level** (XGtE p. 24) | `engine/checks.py` | precedent for *formulaic* DCs, not band DCs |
| **Doors / locks / secret doors / portcullises** (DMG p. 27–29) | `data/library/ways/`, `engine/structures.py` | AC column unusable, but HP, open-DC, pick time and detect DC all port |
| **Siege Equipment** (DMG p. 94–98) | `engine/structures.py` | the **Utilize action counts** (1 to 3) read well as 1-minute-turn multi-turn actions |
| **Enchanted Springs / Primal Fruit / Magic Mushrooms** (TCoE p. 50–57) | `data/library/foraging.json`, `engine/foraging.py` | renewable forage nodes with a skill-gated identification step |

### Tier 2 — needs a new concept, worth filing a dev-task for

| Concept | Why | Source |
|---|---|---|
| **Proficiency Bonus** | 5e uses it *everywhere* — attack rolls, save DCs, Passive Perception, skills. Without it, every 5e attack bonus in the monster export is un-derivable, and skills silently under-report by 2–5 | Part 4 |
| **A defence target / armor class** | the largest single incompatibility; AC is the only mechanical difference between Goblin, Goblin Gang Member and Goblin Commoner | Part 4 |
| **Advantage / Disadvantage** | loads on damage riders, attack counts and auras; the engine's flat `d20 + mod` has no slot for a conditional d20 modifier | Part 1, Part 4 |
| **Multiattack / bonus actions / reactions** | an action-economy concept, and an "intercept the outcome" hook (`Redirect Attack`, `Jinx`, `Parry`) | Part 4 |
| **Per-tick / recurring hazard scheduler** | "1 Exhaustion per hour", "1d4 at the start of each turn", "each round on initiative count 20", "once per day" — all of these need a repeating-tick handler distinct from the 1-minute action flow | TCoE |

---

## Gaps, conflicts and known extraction errors

### Content missing from the source PDFs

Recorded so nobody goes hunting for it in this document and finds nothing.

| Book | What is missing | Why |
|---|---|---|
| XGtE Ch. 2 | **Damage, Healing, Mounted Combat, Underwater Combat, Knocking Back, cover and obscurement, Hiding, Light and Vision, Climbing, Group Patrons, Traps, Magic Items, Downtime** — no prose and no tables | the printed chapter simply stops before them |
| XGtE Ch. 2 | **all 44 Random Encounter tables** (11 environments × 4 tiers) | p. 40–41 ends in a bare navigation link to the D&D Beyond random-encounter viewer |
| XGtE Ch. 2 | **Diagrams 2.1–2.6** (areas of effect on a grid) | image-only pages, no extractable text |
| TCoE | **the Puzzle Collection** | that is **chapter 4**, not this chapter. The `MAGIC ITEMS PUZZLES` on p. 1 is a navigation crumb, not a heading. If puzzles were expected, the wrong chapter was exported |
| DMG Ch. 3 | **NPC Tracker** (p. 67) and **Settlement Tracker** (p. 87) forms; p. 42, 75, 93 | blank form pages / full-page art plates with no body text |
| Monster export | results **2 and beyond** (footer reads `1 2 Next`) | the print is page 1 of a 20-per-page paginated view |
| Monster export | stat blocks for **Goblin Boss (Variant)**, **Goblin Psi Brawler**, **Goblin Psi Commander**, **Goblin Warrior (Stranger Things variant)** | marketplace-locked previews; only CR badge, type, size and alignment printed |
| Monster export | **Hobgoblin Devastator (Volo's)** after the `Quarterstaff` action | block cut off at the page 12 boundary |

### Source-side inconsistencies, left as printed

- **Hobgoblin Warlord** prints `WIS 11 +0 +3` — a +3 save on +0 Wisdom. Almost certainly an
  OCR artefact; transcribed as printed.
- **Tavern Names** (DMG p. 90): the web extraction duplicated each single "The …" phrase into
  both the *First Part* and *Second Part* columns. The real procedure is one d20 per part
  (per the source footnote), so the two columns are not independent.
- **Goblin Warrior** (monster export): raw text interleaves STR/DEX, INT/WIS, CON, CHA.
  Reordered to canonical order; the raw order is preserved in the note.
- **Spellcaster sidekick level table** (TCoE p. 13): the extracted header names 1st–5th spell
  levels but every row carries seven values. The seventh is parked in an explicitly
  unlabelled trailing column rather than silently re-aligned.

### Reconstruction notes

Thirty-one tables had their caption or header split from their rows by a page break in the
source PDF. All were rebuilt and each says so in a parenthetical. The two **compiled**
severity-band tables (hazards, traps) are not in the source — they were derived from each
entry's own severity tag and "At Higher Levels" text, and are labelled as compiled.

### Reconstructed from a two-column collision

- **Goblin** (monster export, line 42), **Goblin Warrior** (line 357), **Hobgoblin** (line 407:
  `Ch ll 1/2(100XP) P fi i B 2 A ti`), **Goblin Hexer** (line 272), **Hobgoblin Iron Shadow**
  Volo's (line 757), **Hobgoblin Warlord** (line 818). Each has a clean authoritative
  rendering elsewhere in the same export; the mangled fragments are reproduced and flagged.

---

*Compiled 2026-09-28 from the four PDFs in `docs/`. Source page numbers (`*(p. n)*`) are
browser-print page numbers, not book page numbers.*
