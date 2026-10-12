---
type: doc
tags: [system/docs, system/characters]
---

# MOSAIC Goals and Pursuits - Worked Examples

A grounded exercise for [[Character Pursuits|MOSAIC]]: for four shipped scenarios, **ten
goals or pursuits per character**, so the design can be tested against real content instead
of imagined characters. The rule was to ask creative questions about each scenario and
answer them from what the scenario actually contains (its areas, items, roles and known
cast), not from generic NPC filler.

Two scenario kinds, deliberately:

- **Narrative** (mansion, The Valerious Case) - a story with a culprit and a shape. These
  have **no schedules or routines**; their characters pursue secrets, survival and each
  other, not a day.
- **Sandbox** (kraktooth_goblin_camp) - a place that runs without the player; daily life,
  work, and the pressures between a goblin camp and the village of Eldenford.

The point is not that every goal is built today. It is to see which MOSAIC pieces the
content actually demands, and which are missing.

## mansion

A country-house murder mystery. The cast's authored prose lives in the character library
(`data/library/characters/`), not the scenario file, so roles are read off their
personalities and the rooms: `elena vance`, `ghost`, `jake halloway`, `kayla jenkins`,
`kyrie johansen`, `miki`, `sammy lopez`, `the butcher`, `whiskers`. Rooms include the
foyer, library, master bedroom, nursery, servants' quarters, crypt, secret study,
slaughterhouse, wine cellar and graveyard.

**Questions I asked.** Who is the host, and who died? Is `the butcher` the killer or a red
herring? `ghost` is a character node, so the haunting is real - what does a ghost *want*?
Whiskers is a cat. Which character is the player? (kayla jenkins recurs in taco_bell_date,
so she reads as an avatar.)

### elena vance
1. Learn who killed the host before the police arrive.
2. Protect her own reputation from a secret in the study.
3. Retrieve the letter hidden in the secret study.
4. Stay away from the butcher.
5. Establish an alibi with the other guests.
6. Find out what is in the wine cellar.
7. Comfort a frightened guest.
8. Conceal an affair that the ghost witnessed.
9. Bar the doors before whoever is outside gets in.
10. Leave the estate before dawn.

### ghost
1. Find out who killed it, and why.
2. Lead a living investigator to where its body lies.
3. Be heard - cold spots, moved objects, a whisper in the crypt.
4. Haunt the one who killed it.
5. Be laid to rest.
6. Watch over the nursery, and whoever sleeps there.
7. Keep the living out of the cellar.
8. Remember the night it died, exactly.
9. Reach the one person still alive who cared about it.
10. Stop the next death if it can.

### jake halloway
1. Find the killer before anyone else dies.
2. Keep kayla safe.
3. Search the library and the study for a motive.
4. Confront the butcher.
5. Get every guest out of the house.
6. Hide the evidence he found until he is sure.
7. Steady his nerves with a drink.
8. Bar and guard the front doors.
9. Question the servants.
10. Survive the night.

### kayla jenkins
1. Survive the night.
2. Work out who the killer is.
3. Save the friend she came with.
4. Escape the estate.
5. Find the thing she came here for.
6. Get to a telephone, or outside.
7. Hide where the killer will not look.
8. Gather clues and compare them.
9. Help the ghost move on.
10. Keep her head while everyone panics.

### kyrie johansen
1. Investigate the murder as calmly as possible.
2. Protect the guests she is responsible for.
3. Guard the doors through the night.
4. Find the murder weapon.
5. Search the graveyard and the crypt.
6. Interrogate the servants.
7. Expose the affair she suspects.
8. Get paid for her trouble.
9. Leave before she is blamed.
10. Survive.

### miki
1. Uncover what everyone is hiding.
2. Survive the night.
3. Protect her friend.
4. Lock herself in a safe room.
5. Find the host, dead or alive.
6. Steal a look in the secret study.
7. Eat something from the kitchen to calm down.
8. Gossip the truth out of a guest.
9. Call the police.
10. Hide until morning.

### sammy lopez
1. Guard the guests without being seen to panic.
2. Find out who set the fire (if there is one).
3. Protect the youngest guest.
4. Search the grounds for tracks.
5. Confront the person sneaking out.
6. Bar the wine cellar.
7. Get a weapon.
8. Keep the group together.
9. Survive.
10. Tell the truth afterwards.

### the butcher
1. Hide the weapon before morning.
2. Silence the witness who saw.
3. Reach the slaughterhouse unseen.
4. Clean up the evidence.
5. Be somewhere else when the body is found.
6. Send the others looking the wrong way.
7. Kill again if cornered.
8. Retrieve what the dead one took.
9. Bar the secret door that leads to his room.
10. Get off the estate before dawn.

### whiskers
1. Catch the mouse in the pantry.
2. Find the warm spot by the fire.
3. Steal tonight's fish from the kitchen.
4. Stay well clear of the butcher.
5. Investigate the ghost (cats do).
6. Nap on the master bed.
7. Slip out to the garden for an hour.
8. Find a hiding place nothing can reach.
9. Watch the newcomer from the doorway.
10. Stay in where it is dry.

**What this scenario needs from MOSAIC.** Almost none of it is a *schedule* - as expected,
a narrative house does not run on routines. Most of it is **Obligations** (protect, guard,
be somewhere else, get the group out) and **Attention** (who noticed what; react to the
ghost, the butcher, the scream). A murder mystery is an attention-and-obligation engine.

## The Valerious Case

A snowbound investigation. Cast: `Kaelen Voss` (the investigator), `Lyrie`, and `rat`.
Rooms: an abandoned hunter's cabin, a blizzard forest, a cellar, a dark cave, a frozen
lake and stream, a hidden panic room, a study, and a nursery-like "sons bedroom".

**Questions I asked.** Who is missing? Is the rat a clue, a pet, or a disease vector? Does
Lyrie hide something in the panic room? Why is a *son's* bedroom in a wilderness cabin?

### Kaelen Voss
1. Find the missing person before the storm closes in.
2. Survive the blizzard - warmth, shelter, dry clothes.
3. Reach the hunter's cabin.
4. Search the study for a record of what happened.
5. Open the hidden panic room.
6. Follow the tracks before snow covers them.
7. Confront whoever is lying.
8. Avoid the rat (and whatever it carries).
9. Get back out of the woods alive.
10. Bring proof to whoever sent him.

### Lyrie
1. Protect Kaelen - he does not know these woods.
2. Find her father, brother or friend.
3. Keep warm and keep moving.
4. Trap the rat before it spoils the food.
5. Find food in a frozen country.
6. Discover what is hidden in the panic room.
7. Hide there if the blizzard turns.
8. Cross the frozen lake without falling through.
9. Bind a wound before it goes bad.
10. Be off the ice before dark.

### rat
1. Find food.
2. Hide in the cellar.
3. Gnaw through the grain sack.
4. Reach the pantry before it is barred.
5. Escape the trap.
6. Nest somewhere warm in the wall.
7. Flee the fire.
8. Find water.
9. Watch the humans and learn their pattern.
10. Chew the rope that holds something important.

**What this scenario needs.** A blizzard is a **live world pressure** that should change
intentions without a script (the farmer-in-bad-weather case in the design doc). The rat is
the counter-example that proves MOSAIC needs a **non-sapient drive tier** - it has urges,
not intentions or obligations.

## taco_bell_date

A fast-food first date. Cast: `jake halloway`, `miki doki`, `tyler`. Rooms: Elm Street,
oak lane, and the Taco Bell (dining room, kitchen, order counter, restrooms).

**Questions I asked.** Is tyler a rival, an ex, or a friend who wants the date to fail?
Who drives? Is the *rating* (if the world has one) affected by how the evening ends?

### jake halloway
1. Impress miki.
2. Order the right thing and pay without fuss.
3. Find a good table.
4. Keep the conversation going.
5. Not mention his ex.
6. Get her number.
7. Hide how nervous he is.
8. Handle tyler turning up.
9. Walk her home.
10. Line up a second date.

### miki doki
1. Decide whether jake is worth a second date.
2. Order and not overthink it.
3. Text her friend for a verdict.
4. Share a dessert.
5. Defuse tyler.
6. Get home safe.
7. Ask about his job without cross-examining.
8. Leave early if it is going badly.
9. Actually enjoy it.
10. Be honest about what she wants.

### tyler
1. Interrupt the date.
2. Try to win miki back.
3. Start a scene loud enough to be noticed.
4. Confront jake.
5. Buy them a round (or start a fight).
6. Apologise, badly.
7. Get thrown out.
8. Leave before he is humiliated.
9. Steal the spotlight.
10. Follow how it ends.

**What this scenario needs.** Tiny, but it shows the **social/obligation** layer sharply:
every beat is about what one person owes another, and about **Attention** - who noticed
whom, and what a look means. It also wants **minutes**: a date is an evening, not a tick.

## kraktooth_goblin_camp (sandbox)

27 characters, 629 areas - a goblin camp in the deep woods beside the village of
Eldenford. This is the place that runs without the player, which is why it is the
schedules-and-pursuits case.

**Questions I asked.** What does the camp need that the village has, and vice versa? Who
holds power in the camp, and who resents it? What is a frog (Croak-Mother) or a bear doing
as a *character*? Who is a prisoner, and who is a resident?

### Arix - smug, cheerful young goblin
1. Show off in front of the camp.
2. Flirt with someone above his station.
3. Steal trinkets to trade.
4. Take a dare he should refuse.
5. Outshine Zikka.
6. Find a treasure in the deep woods.
7. Prank Thrazz's den.
8. Earn a nickname.
9. Eat his fill at the cooking area.
10. Dodge his chores.

### Belne - quiet, hardened traveller
1. Find safe passage through the woods.
2. Trade for supplies.
3. Keep clear of the camp.
4. Reach Eldenford.
5. Rest somewhere defensible.
6. Watch for threats on the road.
7. Guard his pack.
8. Sell a blade before night.
9. Be gone by morning.
10. Not be followed.

### Croak-Mother - an enormous old frog
1. Stay in the water.
2. Sun on the bank.
3. Eat whatever comes close.
4. Guard her pool.
5. Croak to answer the other frogs.
6. Watch the camp from the reeds.
7. Retreat when something large comes.
8. Lay and mind her spawn.
9. Find deeper water in the dry spell.
10. Endure.

### Cullen Rutherford - watchful forest traveller
1. Scout the camp without being seen.
2. Map the trails.
3. Take word back to Eldenford.
4. Avoid capture.
5. Trade if it is safe.
6. Find the road again.
7. Find fresh water.
8. Survive the night in the woods.
9. Learn who the warchief is.
10. Return alive.

### Eldenford Blacksmith - soot-stained, calloused
1. Keep the forge going.
2. Fill the order before the day is out.
3. Get more iron.
4. Repair the guard's gear.
5. Teach an apprentice.
6. Guard the gate if the camp comes.
7. Drink at the inn after work.
8. Pay off a debt.
9. Trade with the camp when it suits.
10. Sharpen the blade someone important asked for.

### Eldenford Elder - weathered, formal
1. Hold council.
2. Keep the peace between the village and the camp.
3. Find out who has gone missing.
4. Meet the goblin envoy.
5. Preserve the harvest.
6. Send a scout.
7. Placate the road captain.
8. Record what happens for those who come after.
9. Bless the well.
10. Groom a successor.

### Eldenford Farmer - weatherbeaten
1. Tend the fields before the weather turns.
2. Protect the crops from the camp.
3. Feed the animals.
4. Watch the treeline.
5. Sell at the market.
6. Mend the fence.
7. Hide the grain.
8. Keep the bear off the pens.
9. Fetch water before dusk.
10. Reap before the frost.

### Eldenford Merchant - sharp-eyed
1. Find goods worth selling.
2. Buy low and sell high.
3. Trade with the camp - carefully.
4. Guard the wagon.
5. Get to the next village.
6. Find a customer for the odd item.
7. Reach the market first.
8. Avoid the bandits on the road.
9. Sell something to the warchief.
10. Close the deal.

### Eldenford Road Guard Captain - tired, armoured
1. Patrol the road.
2. Guard the travellers.
3. Stop the goblin raids.
4. Repair the watchtower.
5. Recruit more guards.
6. Report to the elder.
7. Escort the merchant.
8. Keep the peace in the village.
9. Find the missing patrol.
10. Train the recruits.

### Gribba - goblin cook, sharp nose, sharper memory
1. Cook for the whole camp.
2. Find ingredients worth cooking.
3. Feed the warchief first.
4. Keep a grudge and settle it in the stew.
5. Hoard the good spices.
6. Remember exactly who insulted her.
7. Trade at the village market.
8. Guard the pantry.
9. Try a new recipe.
10. Feed the prisoners just enough.

### Kiala - nervous goblin squire
1. Serve Thrazz without being hit.
2. Run an errand through the camp.
3. Prove he is not a coward.
4. Stay out of Zikka's way.
5. Fetch water.
6. Guard the chief's den.
7. Learn to hold a blade.
8. Carry a message no one else will.
9. Hide when it gets loud.
10. Earn a real sword.

### Krikka - fast, quiet climber
1. Climb the cliff nobody else can.
2. Steal from the village.
3. Scout a route for the raid.
4. Retrieve something from a high place.
5. Spy on Thrazz's meeting.
6. Pick a lock.
7. Slip out of a bad situation.
8. Find an escape route for the camp.
9. Carry the loot back.
10. Show off, quietly.

### Leslie - captive human
1. Escape.
2. Find the road to Eldenford.
3. Get home.
4. Hide in the deep woods.
5. Befriend a goblin who might help.
6. Steal a key.
7. Survive another day.
8. Signal the village for rescue.
9. Find food without being caught.
10. Stay out of the warchief's sight.

### Mikka - wiry goblin tinkerer
1. Repair what is broken in the camp.
2. Invent something nobody asked for.
3. Gather parts from the woods and the village.
4. Trade gadgets.
5. Fix the camp gate.
6. Build a trap.
7. Find scrap worth having.
8. Pick a lock - for someone else.
9. Sell to the camp.
10. Improve the cookpot.

### Old Iron-Back - a massive old bear
1. Find honey.
2. Fish the stream.
3. Sleep in the sun.
4. Guard his territory.
5. Keep clear of the camp.
6. Eat enough to last.
7. Mark the boundary.
8. Retreat from anything loud.
9. Den before the cold.
10. Drive off anything that presses in.

### Rag-Tail - lean wolf alpha
1. Hunt for the pack.
2. Feed the cubs.
3. Mark the territory.
4. Keep the bear out.
5. Find the den.
6. Track prey before dawn.
7. Drive off a rival pack.
8. Watch the humans from the ridge.
9. Lead the hunt.
10. Howl the pack in.

### Rikka - loud chaotic entertainer
1. Put on a show.
2. Get applause.
3. Work a con on a villager.
4. Pick a pocket.
5. Buy a drink.
6. Sell a story.
7. Start a brawl when the mood suits.
8. Win a bet.
9. Steal the spotlight from anyone.
10. Slip away with the coin.

### Shadow-Pelt - a large dark worg
1. Hunt.
2. Guard the warchief.
3. Track a scent across days.
4. Patrol the camp perimeter.
5. Feed when fed.
6. Obey Thrazz alone.
7. Protect the den.
8. Scent intruders before anyone sees them.
9. Chase down a fleeing quarry.
10. Rest close to the fire.

### Silver-Talon - raven, silver-marked talon
1. Find something shiny.
2. Steal a trinket for the nest.
3. Land where people will watch.
4. Cache food.
5. Spy on whoever is talking.
6. Follow the scout.
7. Perch high above the road.
8. Flee a hawk.
9. Take a ring from a sleeping hand.
10. Simply watch.

### Thrazz - old, scarred warchief
1. Hold the camp together.
2. Plan a raid on Eldenford.
3. Settle a feud between clansmen.
4. Feed the clan before winter.
5. Meet the village elder.
6. Choose an heir.
7. Punish a thief publicly.
8. Guard the chief's den.
9. Take Eldenford's stores.
10. Die well, when it comes.

### Tusker - a massive boar
1. Root for food.
2. Charge anything that threatens.
3. Wallow in the mud.
4. Mate.
5. Guard his patch.
6. Flee what he cannot fight.
7. Sleep in the shade.
8. Dig a wallow.
9. Gore a challenger.
10. Follow the scent of corn.

### Vekka - quiet scout, sharper silences
1. Scout the deep woods.
2. Read the tracks before anyone else.
3. Report back exactly.
4. Avoid the hunters.
5. Find water for the camp.
6. Map a safe route.
7. Watch the village from cover.
8. Lead the raid along a hidden path.
9. Warn the warchief in time.
10. Keep the camp's secret ways secret.

### Zikka - loud, strong fighter
1. Prove his strength.
2. Win a duel.
3. Guard Thrazz.
4. Raid Eldenford.
5. Train Kiala - hard.
6. Intimidate someone into respect.
7. Win a bet on himself.
8. Take a trophy from a fight.
9. Lead the charge.
10. Be the one they name next.

### james
1. Fish enough for the day.
2. Get home before dark.
3. Feed his household.
4. Mend his net.
5. Trade the catch.
6. Find clean water.
7. Keep clear of the goblins.
8. Reach the hut.
9. Fix the boat.
10. Teach a child to fish.

### zombie (three)
1. Shamble toward sound.
2. Attack the living.
3. Guard the place it died.
4. Moan.
5. Feed.
6. Fall and rise again.
7. Wander without purpose.
8. Linger where it was buried.
9. Follow the others.
10. Nothing else.

**What this scenario needs from MOSAIC.** This is the one that genuinely runs a day, so
**Schedules** bite here (the blacksmith's forge, the farmer's field, the scout's patrol).
But most of the cast, most of the time, is driven by **Motivation** (hunger, sleep,
territory), **Intentions** (raid, escape, court, succeed), and the **Obligations** between
camp and village. And six of the cast - the frog, the bear, the two wolves, the boar, the
raven - plus the three zombies are **not** pursuers at all: they need a **drive tier**
below intentions and obligations, or MOSAIC will dress up instinct as choice.

## What the exercise reveals

1. **Obligations are everywhere and have no home.** "Protect Kayla", "guard the gate",
   "report to the elder", "feed the clan", "escort the merchant" - the missing letter is
   the most demanded of the six across all four scenarios.
2. **Attention is a first-class driver, not flavour.** Murder mystery, date and raid all
   turn on who noticed what. The mansion's threat-system origin is the right ancestor.
3. **Schedules fit sandboxes, not stories.** Confirmed: kraktooth needs routines; mansion
   and The Valerious Case need none. A routine is one input, never a requirement.
4. **Non-sapient characters need a lower tier.** Eleven of the kraktooth cast are animals
   or undead. MOSAIC as written would give a boar "intentions". It needs a drive tier.
5. **Everything is minutes.** "Patrol the road", "work the forge", "hibernate", "a date" -
   durations are hours and evenings, never ticks.
6. **The units are a small rotation.** Watch a visitor, work a shift, escape, court, guard,
   hunt, investigate, deliver. Twelve-ish shapes cover ~40 characters - which is exactly
   the argument for a shared **pursuit template** library (task-701) over bespoke scripts.

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes** — [[Character Pursuits]], [[MOSAIC Character Profiles]]

<!-- connected:end -->
