---
type: doc
tags: [system/docs, system/characters]
---

# MOSIAC Character Profiles

What MOSIAC looks like when it is filled in. For every character of four shipped scenarios - **mansion**, **The Valerious Case**, **taco_bell_date** and **kraktooth_goblin_camp** - the six letters as the inputs, ten **Intentions**, and **Choice** as the disposition that weighs them.

Grounded in the characters as authored. Each profile is read off the character's real `personality` and `base_description` in `data/library/characters/` (and their node prose where the library has none), not from their names. That matters: the first pass at this exercise guessed roles from names, and several guesses were wrong - the mansion cast are not dinner guests, and tyler is not a rival ex, he is the cashier. The ten intentions below follow the character each one is grounded in.

The point is not that every intention is built today. It is to see which MOSIAC pieces the content actually demands and which are missing, and how the shape differs by scenario type: a narrative night that runs on obligations and attention, versus a sandbox day that runs on schedules.

## The shape of a MOSIAC

MOSIAC names six **concerns**: five inputs and one resolution.

| Letter | Concern | Reads / produces |
|---|---|---|
| **M** | Motivation | needs and drives - why the character moves at all |
| **O** | Obligations | what the character owes: missions, promises, duties, appointments |
| **S** | Schedule | when the world expects something: a routine, a deadline, a window |
| **A** | Attention | what the character notices and cares about; the salience filter |
| **I** | Intentions | what the character is committed to: goals and pursuits - **the ten live here** |
| **C** | Choice | how needs, memory and personality weigh the intentions and bind a plan |

The artifacts those concerns produce belong to the *world*, not the letters: a **plan** (the next approach - Choice's output), an **activity** (the visible doing), a **recipe** (the transformation rule the world resolves).

**Tiers.** Not every character has intentions and obligations.

- `sapient` - needs, obligations, intentions. An LLM agent or a simple NPC.
- `drive` - urges only, no intentions: hunger, territory, fear. Animals and the undead.

A boar is not pursuing a goal; it is hungry. Give it intentions and MOSIAC dresses instinct up as choice.

### The structured forms

```yaml
# An Intention, when it is a full pursuit
pursuit:
  template: scout-and-report        # a reusable kind (task-701)
  status: active                    # proposed | active | done | abandoned
  actor: vekka
  goal: learn whether humans use the northern road
  reason: <prose the character and the LLM both weigh>
  objective: {observe: <world fact>, report_to: <character>}
  when: {start: <condition>, deadline: <clock>}
  where: {route: <area>, return_to: <area>}
  requirements: {carried: [...], knowledge: [...]}
  progress: {step: <validated from world state>}
  stop_when: [<condition>, <condition>]
  interruption: {decide_from: perception, needs, memory, personality, danger}
```

```yaml
# An Obligation
mission:
  from: zikka
  to: vekka
  charge: learn where the human tracks lead
  can: [accept, alter, refuse, forget]
  deadline: tomorrow morning
```

```yaml
schedule:  {at: "06:00", every: day, suggests: prepare food}
attention: {watches: [threats, a scream, ones own name]}
choice:    {disposition: {bold: +0.6, caution: -0.3}, on_conflict: obligations interrupt}
```

## How to read a profile

Each block gives the **inputs** (M / O / S / A), the **ten intentions** each tagged with the letter it serves, and the **disposition** Choice resolves them with. `drive` characters carry no O and no S - they have urges, not commitments.

---

## mansion

A paranormal investigation gone wrong. Six people entered the Macmillan estate: the investigator elena vance and her partner miki, and four teenagers - jake, kayla, kyrie and sammy - dragged along by jake. A restless ghost is bound to the house and a slasher, evan macmillan, still hunts its halls. Whiskers the cat was here first. There are **no schedules**: it is one night.

### elena vance - the investigator
`mansion / sapient` - seasonal case leader, decade of fieldwork
- **M** close the Blackwood case; document everything; believe the evidence, not the story
- **O** to miki, the partner she brought; to the family of seven who vanished in 1891
- **S** none
- **A** instruments and readings; the occult; anything that contradicts or confirms the record
- **C** methodical and brave-but-cautious; trusts her equipment over her gut

1. Work the house systematically, room by room - I
2. Get a conclusive reading on something - I
3. Explain the 1891 disappearance - I
4. Keep miki close and out of the dark alone - O
5. Photograph or record hard proof - I
6. Stay skeptical while the kids panic - M
7. Locate the source of the cold spots and sounds - I
8. Catalog everything before it changes - M
9. Decide whether to leave before the night is out - I
10. Bring both of them out alive - O

### miki - the partner who insisted on coming
`mansion / sapient` - chaotic asmr artist, elena's partner
- **M** be useful; stay close to elena; hear the thing no one else hears
- **O** to elena, who let her tag along
- **S** none
- **A** subtle sounds; the detail everyone misses; where elena is
- **C** rambles and hums when scared, but is right about the sound

1. Stay with elena - O
2. Listen for what the others miss - I
3. Prove she was right to come - M
4. Record the haunting as audio - I
5. Hum to keep the fear down - M
6. Keep the kids from panicking - O
7. Find the room the sound is coming from - I
8. Don't get separated in the dark - I
9. Tell elena what she heard, even if it sounds crazy - O
10. Get out with the others - O

### jake halloway - the one who thought this was fun
`mansion / sapient` - IT support drone, hobby coder, gremlin
- **M** curiosity; make it an adventure; follow the interesting thing
- **O** to sammy and kayla, who came because he asked
- **S** none
- **A** mechanisms, patterns, hidden things; anything that clicks, whirs or opens
- **C** impulsive and chaotic; locks onto a detail and won't let go

1. Get the group to the interesting room - M
2. Pick the lock or crack the mechanism - I
3. Keep sammy close - O
4. Find the source of the noise - I
5. Make the others laugh so it stays fun - M
6. Pull back when it stops being a game - O
7. Grab the odd object that nobody noticed - I
8. Keep kayla from biting his head off - O
9. Apologise for dragging them here - O
10. Get everyone back out through the front door - O

### kayla jenkins - the one with no patience for this
`mansion / sapient` - sharp-tongued teen, reads people
- **M** survive; stay three steps ahead; not die in a dusty house
- **O** to the friends she came with
- **S** none
- **A** people, their tells, the things they miss; who is lying
- **C** sharp and defiant; watches everything, says the thing anyway

1. Read the room and find who knows more than they say - I
2. Keep sammy from falling apart - O
3. Survive the night - M
4. Find the way out - I
5. Call jake out for the idiot idea - M
6. Watch the adults for the lie - I
7. Not be the one left behind - I
8. Grab something to defend herself - I
9. Keep her head when everyone else loses theirs - M
10. Get the group out - O

### kyrie johansen - the one who assesses
`mansion / sapient` - teen wrestler, mechanic's daughter, bandaged arm
- **M** keep them alive; be the capable one; use leverage
- **O** to sammy, who needs someone sensible; to jake, who asked
- **S** none
- **A** angles, footing, threats; what can be used as a weapon; her injured left arm
- **C** assess, plan, act; calm where the others panic

1. Assess the house like a ring: exits and threats - I
2. Keep sammy under her wing - O
3. Find something to fight with - I
4. Guard the group's back - O
5. Manage the bad arm - I
6. Do not let jake lead them into trouble - O
7. Check the rooms the others skipped - I
8. Hold a door against whatever is out there - I
9. Get sammy to the exit first - O
10. Bring everyone out - O

### sammy lopez - the one who watches
`mansion / sapient` - teenager out of her depth, jake's girlfriend
- **M** not be the weak link; stay near jake; be useful
- **O** to jake, and to the friends who came
- **S** none
- **A** small details; the thing everyone walked past
- **C** quiet, deferential, nearly invisible; terrified but stubborn

1. Stay near jake - O
2. Find something useful to do - M
3. Notice the detail nobody else did - I
4. Stay quiet and out of sight - I
5. Not be the reason they fail - M
6. Sit down and breathe for a minute - M
7. Keep hold of the group's belongings - O
8. Point out the odd thing she saw - I
9. Follow kyrie's lead - O
10. Get out without anyone having to save her - O

### ghost - the restless spirit
`mansion / sapient` - a spirit bound to the house
- **M** be heard; be laid to rest; finish what bound it here
- **O** to whoever it was before it died
- **S** none
- **A** the people in its house; the objects it can move; the ones who hurt it
- **C** patient and repetitive; nudges a thing until it is noticed

1. Make itself known - M
2. Move something a living person will find - I
3. Lead them toward what it needs found - I
4. Answer the one who speaks to it - I
5. Push the people away from the butcher - I
6. Guard the place it died - I
7. Replay the night, again - M
8. Find the one person still alive who cared - I
9. Be understood, not just felt - M
10. Be laid to rest - I

### the butcher - evan macmillan
`mansion / sapient` - slasher, unstoppable, feels nothing else
- **M** kill every intruder; the kill is the only drive
- **O** none - there is nothing else
- **S** none
- **A** sound, movement, the ones who stray from the group
- **C** relentless and silent; no hesitation, no deliberation, no plan changing

1. Hunt whoever is in the house - I
2. Separate one from the group - I
3. Cut off the exits - I
4. Drive them toward the tunnels - I
5. Kill without stopping - I
6. Follow the shouting - I
7. Wait in the dark for the straggler - I
8. Bar the path back - I
9. Take the one who ran - I
10. Leave none of them breathing - I

### whiskers - the cat
`mansion / drive`
- **M** warmth; food; territory
- **O** none
- **S** none
- **A** movement, especially small moving things; the high place; the butcher
- **C** aloof and curious; watches from above before it acts

1. Claim the best warm spot - I
2. Hunt the pantry mouse - I
3. Steal food that is left out - I
4. Get up somewhere nothing can reach - I
5. Watch the newcomers from the shadow - I
6. Stay far from the big one (the butcher) - I
7. Investigate the cold spot - I
8. Nap on the best bed - I
9. Slip outside and back for an hour - I
10. Stay dry and warm - I

---

## taco_bell_date

A fast-food first date that jake decided - out loud - was a date. **No schedules**: one evening.

### jake halloway - the one who decided this was a date
`taco_bell_date / sapient` - notices a person and locks on
- **M** make tonight happen; follow the interesting thing; not get bored
- **O** to miki, now that he has said the word "date" out loud
- **S** none (the evening)
- **A** miki's reactions; the mechanism of the moment; anything to grab onto
- **C** chaotic and sincere; says the uncalibrated thing and grins through it

1. Make miki laugh - M
2. Order something and not fuss - I
3. Keep the conversation running - I
4. Not derail it with an unprompted lecture - M
5. Notice what she likes - I
6. Get her number - I
7. Steal a fry off her tray - M
8. Not say the awkward thing - M
9. Walk her home - O
10. Turn this into a second date - I

### miki doki - the one deciding
`taco_bell_date / sapient` - asmr artist; self-deprecating, bratty, shy
- **M** enjoy herself without overthinking; figure out if jake is real
- **O** to herself - she owes no one a verdict tonight
- **S** none (the evening)
- **A** jake's tells; the tone under the joke; every sound
- **C** bratty and self-conscious; tests, teases, holds the curtain

1. Decide whether jake is worth a second look - I
2. Order without panic - I
3. Text a friend for the verdict - O
4. Mock him a little - M
5. Actually enjoy it instead of narrating it - M
6. Keep the mask up a bit longer - M
7. Ask the real question under the chat - I
8. Leave early if it turns - I
9. Get home safe - O
10. Be honest about what she wants - M

### tyler - the cashier
`taco_bell_date / sapient` - sixteen, closing the counter, out of joules
- **M** get to the end of the shift; save every joule; reach the ride home
- **O** to the job - the register is open and the shift is not over
- **S** the closing shift; clock out when the ride arrives
- **A** the customers; the door; the clock
- **C** deadpan endurance; does exactly enough and no more

1. Process the order - O
2. Ring up the weird shout without reacting - M
3. Keep the counter clean - O
4. Watch the door for his ride - I
5. Not get dragged into the drama - M
6. Restock what ran out - O
7. Survive the last customers - M
8. Clock out the moment he can - I
9. Remember the story for later - I
10. Get home - I

---

## The Valerious Case

A snowbound investigation in a fantasy winter (the curse of 1584). Cast: **Kaelen Voss**, a disgraced investigator; **Lyrie**, an elven airhead; and a **rat**. **No schedules** - it is one night in the snow.

### Kaelen Voss - the disgraced investigator
`The Valerious Case / sapient` - exiled from the Galser Office of Justice, clockwork leg, dry humor
- **M** find the truth of what happened here; be right, this time, in the open
- **O** to whoever sent him; to the stray he keeps
- **S** none
- **A** fine print, distant horizons, anything that does not add up; the small animal
- **C** dry and unflappable; reads the detail before the scene

1. Find the missing person before the storm closes - I
2. Survive the blizzard: warmth, shelter, dry clothes - M
3. Reach the hunter's cabin - I
4. Search the study for the record - I
5. Open the hidden panic room - I
6. Follow the tracks before snow covers them - I
7. Confront whoever is lying - I
8. Keep the rat alive, and out of his food - O
9. Get back out of the woods - M
10. Bring proof to whoever sent him - O

### Lyrie - the elven airhead
`The Valerious Case / sapient` - sweet, clumsy, disastrous, no self-preservation
- **M** help, cheerfully; be liked; follow whatever is interesting
- **O** to whoever she is with - she would never let them down on purpose
- **S** none
- **A** whatever catches her eye; nothing for long
- **C** jumps to a bizarre conclusion and acts on it with total sincerity

1. Stay with Kaelen, and lose him anyway - O
2. Help with something and break it - M
3. Follow a weird idea to its ridiculous end - M
4. Find something pretty in the snow - I
5. Ask a question that makes no sense - M
6. Cry, then carry on - M
7. Wander somewhere she should not - I
8. Try to feed the rat - I
9. Get lost, and be found - I
10. Be there at the end without meaning to be - O

### rat - the rat
`The Valerious Case / drive`
- **M** food; warmth; safety
- **O** none
- **S** none
- **A** the gap under the door; crumbs; movement
- **C** instinct; curious before it is afraid

1. Sniff under the kitchen door - I
2. Find food - I
3. Hide in the cellar - I
4. Gnaw the grain sack - I
5. Reach the pantry - I
6. Escape the trap - I
7. Nest in the wall - I
8. Flee the fire - I
9. Find water - I
10. Watch the humans - I

## kraktooth_goblin_camp

The sandbox: a goblin camp in the deep woods beside Eldenford, 27 characters, run without the player. **Schedules bite here** - the cook, the forge, the patrol. Note the `drive` cast: the frog, the bear, the two wolves, the boar, the raven and the three undead carry urges, not intentions.

### Arix - the runaway
`kraktooth / sapient` - young goblin, not of this tribe, smug and greedy
- **M** sparkle; amusement; follow her whims
- **O** none - she is not from this tribe and owes it nothing
- **S** camp day (meals, the evening crowd)
- **A** anything shiny or expensive; a face worth mocking
- **C** lighthearted and capricious; does the fun thing without weighing consequences

1. Get her hands on something shiny - M
2. Mouth off at someone important - I
3. Trade a trinket with the village - I
4. Take a dare she should refuse - I
5. Outshine a local - I
6. Find treasure in the woods - I
7. Prank a den - I
8. Earn a nickname - M
9. Eat and drink her fill - M
10. Dodge any work expected of a resident - O

### Belne - banished for kindness
`kraktooth / sapient` - wanderer, rejected by her own tribe
- **M** find somewhere to belong; survive the road
- **O** to the simple quests she takes - she finishes what she agrees to
- **S** the road; camps by safe hours
- **A** who trusts her and who does not; the prejudice behind the greeting
- **C** quiet and hardworking; wants in, but does not trust easily

1. Find a place that will have her - M
2. Take a job that pays in food - O
3. Trade for supplies - I
4. Keep clear of the goblin camp - I
5. Reach Eldenford - I
6. Find defensible shelter - I
7. Guard her pack - I
8. Do not let a good deed cost her again - M
9. Be gone before anyone decides she is trouble - I
10. Trust someone, maybe - M

### Croak-Mother - the marsh's great frog
`kraktooth / drive` - ancient, locally legendary, the marsh's barometer
- **M** hunger; water; spawn; the mud she owns
- **O** none
- **S** none
- **A** movement at the water's edge
- **C** instinct - though she is unnervingly intelligent for a frog, and the shaman knows it

1. Stay deep in the water - I
2. Sun on the bank - I
3. Take whatever comes to the edge - I
4. Guard her pool - I
5. Answer the other frogs - I
6. Watch the camp from the reeds - I
7. Retreat from anything large - I
8. Mind her spawn - I
9. Find deeper water in the dry spell - I
10. Endure - I

### Cullen Rutherford - the explorer
`kraktooth / sapient` - cautious human in the woods, no fixed goal
- **M** survive; explore; see what is here
- **O** none formal
- **S** woodcraft; moves by daylight
- **A** the camp's watch; trails; what lies over the next ridge
- **C** cautious and practical; observes, then withdraws

1. Scout the camp without being seen - I
2. Map the trails - I
3. Find water - I
4. Avoid capture - I
5. Trade if it is safe - I
6. Find the road back - I
7. Survive the night in the open - M
8. Learn who leads the camp - I
9. Get out of the territory - I
10. Return alive - I

### Eldenford Blacksmith - the smith
`kraktooth / sapient` - gruff, proud, counting his losses to the camp
- **M** good work; good metal; settle the score of stolen tools
- **O** to the village - their gear and their orders
- **S** the forge day
- **A** the quality of metal; what went missing and who has it
- **C** gruff and practical; finishes the job, resents the interruption

1. Keep the forge going - I
2. Fill the day's order - O
3. Get more iron - I
4. Repair the guard's gear - O
5. Recover tools the goblins took - I
6. Guard the gate if the camp comes - O
7. Drink at the inn after work - M
8. Pay off a debt - O
9. Deal with the camp when it suits - I
10. Make something worth handing down - M

### Eldenford Elder - the one keeping the balance
`kraktooth / sapient` - pragmatic, tired, distrusts goblins but needs trade
- **M** keep the village safe and solvent; be remembered for holding it
- **O** to the village; conditionally, to the arrangement with the camp
- **S** council, markets, the day's business
- **A** the camp's intentions; the treasury; who has gone missing
- **C** pragmatic above all; weighs a cost against the village before he speaks

1. Hold council - O
2. Keep the peace with the camp - O
3. Find out who has gone missing - I
4. Meet the goblin envoy - I
5. Protect the harvest and the stores - O
6. Send a scout when it is quiet - I
7. Manage the road captain - O
8. Record it all for whoever comes after - M
9. Hold the trade that keeps the village fed - O
10. Groom someone to take this from him - O

### Eldenford Farmer - the one still standing
`kraktooth / sapient` - stubborn; fears the silence and being forgotten
- **M** prove that care can outlast ruin; still be here in ten years
- **O** to the ground; to the household; to the dogs
- **S** dawn-to-dusk field work; lanterns at dusk
- **A** the moment the birds stop; the treeline; the last farm
- **C** stubborn and quietly brave; keeps setting the snare

1. Work the ground before the weather turns - O
2. Set another snare - I
3. Keep the animals fed and safe - O
4. Watch the treeline - I
5. Sell what he can at market - I
6. Mend what the goblins broke - I
7. Hide the grain - I
8. Keep the bear off the pens - I
9. Light every lantern at dusk - M
10. Be here, still, in ten years - M

### Eldenford Merchant - the one who knows a man
`kraktooth / sapient` - talkative, calculating; buys information
- **M** profit; information; never be the one standing where it resolves
- **O** to his customers; to the debts he owes and is owed
- **S** market days; travel between villages
- **A** prices; rumours; the dwarven ruins; who hired whom
- **C** calculating and cheerful by tool; becomes very interested in paperwork when frightened

1. Buy the information nobody else has - I
2. Sell at the best price - I
3. Trade with the camp, carefully - I
4. Get to the next village - I
5. Find a buyer for the odd item - I
6. Reach the market first - I
7. Keep the second set of accounts hidden - I
8. Not be ruined by what he hired goblins to do - M
9. Stay solvent with the Elder - O
10. Be elsewhere when it resolves - M

### Eldenford Road Guard Captain - the arrangement
`kraktooth / sapient` - holds the road on an unspoken deal with the raiders
- **M** keep the road; keep the village alive; not think about what that costs
- **O** to the Elder - answered precisely - and, silently, to the camp
- **S** the patrol he has never written down
- **A** where the goblins cross - north of the mill, the ford, the cliff foot
- **C** disciplined to the point of scar; does the thing and does not name it

1. Patrol the road - O
2. Guard the travellers who pass - O
3. Keep the crossings clear - I
4. Report to the Elder, precisely - O
5. Keep the arrangement invisible - I
6. Train the ones he has - I
7. Find the missing patrol - I
8. Hold the road one day without doubt - M
9. Drink, but not on duty - M
10. Stop needing the arrangement - M

### Gribba - the cook who remembers
`kraktooth / sapient` - controls the food; trades meals for everything else
- **M** be indispensable; never forget a debt
- **O** to the camp she feeds; to the chief, fed first
- **S** the cook day - meals at the Cooking Area
- **A** who has been stealing rations; which mushrooms are safe; who owes her
- **C** calm and patient; settles accounts quietly

1. Cook for the whole camp - O
2. Find ingredients worth cooking - I
3. Feed the warchief first - O
4. Trade a meal for a favour - I
5. Hoard the good spices - I
6. Work out who is stealing rations - I
7. Trade at the village market - I
8. Guard the stores - O
9. Try something new - I
10. Feed the prisoners just enough - O

### Kiala - the squire looking for her master
`kraktooth / sapient` - timid, world-wise, far from the Guild
- **M** find the human master she lost; prove she is worth keeping
- **O** to the master she trained under - still, even now
- **S** none fixed - she wanders
- **A** rumours; anyone who might know the road her master took
- **C** timid but determined; flinches, then tries again

1. Ask after her master - I
2. Follow a rumour - I
3. Learn the local roads - I
4. Prove she can hold a blade - M
5. Keep out of the fighters' way - I
6. Carry a message nobody else will - O
7. Find food and shelter without trouble - I
8. Not be taken for a runaway - M
9. Earn a reason for someone to keep her - M
10. Keep moving toward the last place he was seen - O

### Krikka - the climber
`kraktooth / sapient` - fast, silent, restless; goes where no one else can
- **M** climb; collect; see from above
- **O** to the camp - she is the one who can reach the roofs
- **S** none fixed - works by night
- **A** high places; locks; anything small and shiny
- **C** restless and quick; watches from above before she drops

1. Climb the cliff - M
2. Take shiny things and hide them high - I
3. Steal from the village - I
4. Scout a route for the raid - O
5. Retrieve something from a height - I
6. Pick a lock - I
7. Slip out of a bad corner - I
8. Find the camp a way out - O
9. Carry the loot back - I
10. Show off, quietly - M

### Leslie - the captive
`kraktooth / sapient` - human prisoner, craving attention and purpose
- **M** matter to someone; be seen; find a place in a place she does not fit
- **O** none formal - but she will bargain, flirt or obey to earn one
- **S** none - captivity has only the guards' rhythm
- **A** who is approaching; whose mood can be worked
- **C** adaptive; reads the room and plays to it

1. Read whoever approaches - I
2. Bargain for something better - I
3. Flirt for leniency - M
4. Find a goblin who might help - I
5. Learn the rules she keeps breaking - I
6. Steal a key - I
7. Survive another day - M
8. Signal the village if she can - I
9. Earn a purpose worth staying for - M
10. Be treated as a person, once - M

### Mikka - the fixer with a secret
`kraktooth / sapient` - always building; has a hidden project
- **M** build, fix, improve - almost past the point of sense
- **O** to the camp - the gate, the cookpot, the things that break
- **S** workshop day
- **A** scrap; broken things; other people's equipment
- **C** curious and quick-handed; follows the problem wherever it goes

1. Fix what is broken in the camp - O
2. Invent something nobody asked for - M
3. Gather parts from the woods and the village - I
4. Trade gadgets - I
5. Fix the camp gate - O
6. Work on the hidden project - I
7. Quietly improve someone else's gear - I
8. Find scrap worth having - I
9. Sell to the camp - I
10. Improve the cookpot - I

### Old Iron-Back - the bear
`kraktooth / drive` - scarred, solitary; the camp leaves offerings
- **M** food; territory; a den for the cold
- **O** none
- **S** seasonal - dens before winter
- **A** noise; anything that presses in
- **C** instinct; charges what it can, leaves what it cannot

1. Raid for food - I
2. Fish the stream - I
3. Sleep in the sun - I
4. Guard his range - I
5. Take the offerings left for him - I
6. Eat enough to last - I
7. Mark the boundary - I
8. Retreat from anything loud - I
9. Den before the cold - I
10. Drive off anything that presses in - I

### Rag-Tail - the wolf alpha
`kraktooth / drive` - smart, cautious, opportunistic
- **M** hunt; feed the pack
- **O** to the pack
- **S** hunts before dawn
- **A** goblin traps and ambushes; prey; rival packs
- **C** instinct led by experience; takes the opening, avoids the snare

1. Hunt for the pack - I
2. Feed the cubs - I
3. Mark the territory - I
4. Avoid the goblin traps - I
5. Take a goblin when it is safe - I
6. Track prey before dawn - I
7. Drive off a rival pack - I
8. Watch the camp from the ridge - I
9. Lead the hunt - I
10. Howl the pack in - I

### Rikka - the distraction
`kraktooth / sapient` - chaos on purpose; not taken seriously, on purpose
- **M** redirect attention; make noise; be the one they watch
- **O** to the camp - useful in a raid, an escape, a negotiation
- **S** evenings; market days
- **A** the room's attention; the mark; the moment to create friction
- **C** deliberately chaotic; makes the crowd look where she wants

1. Put on a show - M
2. Create a distraction on cue - O
3. Work a con on a villager - I
4. Pick a pocket mid-act - I
5. Buy a drink with the takings - M
6. Sell a story nobody can verify - I
7. Start a brawl because the timing is right - O
8. Win a bet - I
9. Steal the spotlight - I
10. Slip away with the coin - I

### Shadow-Pelt - the worg leader
`kraktooth / drive` - intelligent, dangerous, competitive
- **M** hunt; patrol; hold the river territory
- **O** none formal - competes with the goblins rather than serving them
- **S** the patrol
- **A** intruders (scent first); food; rival packs
- **C** instinct, sharpened; takes what it can hold

1. Hunt - I
2. Patrol the river bank - I
3. Contest the goblins for food - I
4. Track a scent across days - I
5. Feed when fed - I
6. Drive off a rival pack - I
7. Guard the den - I
8. Scent intruders first - I
9. Run down fleeing quarry - I
10. Rest somewhere warm - I

### Silver-Talon - the raven
`kraktooth / drive` - fed by the camp; Vekka's messenger
- **M** scavenge; shiny things; curiosity
- **O** none - but Vekka has trained it to carry messages
- **S** none
- **A** food scraps; shiny objects; whoever is watching
- **C** instinct; takes, then flees

1. Find scraps near the camp - I
2. Take something shiny for the nest - I
3. Land where people will look - I
4. Cache food - I
5. Watch whoever is talking - I
6. Follow the scout (Vekka) - I
7. Carry a message for Vekka - O
8. Flee anything larger - I
9. Take a ring off a sleeping hand - I
10. Watch, and remember where it went - I

### Thrazz - the warchief
`kraktooth / sapient` - holds the camp by fear, reputation and spite
- **M** hold the camp; stay in front of Zikka's rising name; leave something behind
- **O** to the clan - and to an old feud with Eldenford
- **S** the chief's day - holds court, receives, punishes
- **A** dissent; his daughter's prestige; the specialists he cannot dominate
- **C** politically sharp; spends others before himself, never shows the doubt

1. Hold the camp together - O
2. Plan the raid on Eldenford - I
3. Settle a feud between clansmen - O
4. Keep the specialists under him - I
5. Feed the clan before winter - O
6. Deal with Zikka's rise - M
7. Punish a thief publicly - O
8. Guard the chief's den - O
9. Take Eldenford's stores - I
10. Die well, when it comes - M

### Tusker - the boar
`kraktooth / drive` - massive, aggressive, territorial
- **M** food; mate; his patch of forest
- **O** none
- **S** seasonal
- **A** threats; the scent of corn
- **C** instinct; charges, then forgets it

1. Root for food - I
2. Charge what threatens - I
3. Wallow - I
4. Mate - I
5. Guard his patch - I
6. Flee what he cannot fight - I
7. Sleep in the shade - I
8. Dig a wallow - I
9. Gore a challenger - I
10. Follow the scent of corn - I

### Vekka - the scout
`kraktooth / sapient` - quiet, poisonous, effective; resents the name she is given
- **M** know the land; be her own person and not only the chief's daughter; be indispensable
- **O** to the tribe as its scout - and to no one else
- **S** the patrol
- **A** tracks; the patrols; the camp's secret ways; her hidden cache
- **C** silent and precise; reports exactly, resents the credit

1. Scout the deep woods - O
2. Read the tracks first - I
3. Report back exactly - O
4. Avoid the hunters and the wolves - I
5. Check the hidden cache outside the camp - I
6. Map a safe route - I
7. Watch the village from cover - I
8. Lead a raid by a hidden path - O
9. Keep the camp's secret ways secret - O
10. Be known for something that is hers - M

### Zikka - the warchief's daughter
`kraktooth / sapient` - best fighter in the camp; tired of being the heir
- **M** make the tribe stronger, smarter and more feared; be seen as more than her father's enforcer
- **O** to the tribe as its fighter - and to the raid
- **S** training; guard shifts
- **A** challengers; Vekka - the other one who runs operations; her father's eye
- **C** loud and direct; takes the front and the credit

1. Prove her strength - M
2. Win a duel - I
3. Guard the camp's fight - O
4. Raid Eldenford - O
5. Train the next fighter hard - O
6. Beat Vekka at something that matters - I
7. Win a bet on herself - I
8. Take a trophy worth showing - I
9. Run the operation, not just the charge - I
10. Be the one they name next - M

### james - the river fisherman
`kraktooth / sapient` - patient, practical; talks to the river more than to people
- **M** fish; keep the household; be left alone
- **O** to the household he feeds
- **S** the fishing day - out at dawn, the pools each hold fish at their own hour
- **A** the water; his net; the goblins on the bank
- **C** slow to anger and unhurried; avoids trouble rather than facing it

1. Fish the day's pools - O
2. Get home before dark - O
3. Feed the household - O
4. Mend the net - I
5. Trade the catch - I
6. Find clean water - I
7. Keep clear of the goblins - I
8. Fix the boat - I
9. Teach a child to fish - M
10. Be left in peace on the river - M

### zombie (three) - the shambling dead
`kraktooth / drive` - hunger with the dim echo of a person
- **M** feed; move toward warmth and noise
- **O** none
- **S** none - only the faint routine of a life it no longer has
- **A** sound; the living; warmth
- **C** instinct; walks until something stops it

1. Turn toward noise - I
2. Attack the living - I
3. Linger where it died - I
4. Moan - I
5. Feed - I
6. Fall, and rise again - I
7. Walk the routine it cannot forget - I
8. Follow the others - I
9. Drift toward warmth - I
10. Nothing else - I

---

## What this shows

1. **Grounding changes the character, not just the words.** Read off names, mansion looked like a dinner-party whodunit and tyler looked like a rival ex. Read off the library, mansion is a paranormal investigation with a slasher and a haunting, and tyler is the boy at the register counting minutes to his ride. The inputs (M / O / A / C) are what re-ground the ten - and they move a lot.
2. **The cast is shared across scenarios.** jake, miki and kayla carry the same authored person across mansion and taco_bell_date. A MOSIAC is the *character's*, not the scenario's, so the same inputs travel with them - which is the argument for a character-level, not scene-level, definition.
3. **Obligations are everywhere and have no home.** Protect, guard, report, feed, keep-close, do-not-abandon - most intentions across all four scenarios are owed to someone. The most demanded letter is the one with no code.
4. **The drive tier is not binary.** Nine kraktooth characters plus the cat have urges, not intentions - but two of them are the counter-example: **Silver-Talon** carries messages for Vekka, and **Croak-Mother** is "unnervingly intelligent" and deals with the shaman. A flat `drive` tier would flatten a bond and a legend into instinct. The tier needs a seam for the exceptional animal.
5. **The eldenford three are the richest case.** The Farmer, the Merchant and the Road Guard Captain each carry a private load - the farmer's fear of the silence, the merchant's second set of accounts and the men who did not come back, the captain's unspoken arrangement with the raiders. None of it is a schedule or a goal; all of it is **Attention** and **Choice**. MOSIAC's hardest job is not the chores, it is the thing they are not saying.

### One data note

`james` carries a mismatched `base_description` in the library: the personality is a river fisherman, but the base description reads "a composed, middle-aged man trained in clinical work; a therapist...". One of the two is wrong. Flagged, not reconciled here.

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes** — [[Character Pursuits]]

<!-- connected:end -->
