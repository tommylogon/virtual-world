# Cold Rooms, Graph-Bound Gear, One Tick

**Project:** VirtualWorld Engine
**Mode:** rp
**Voices:** Mara, Elias
**Length:** 938 words (~6.3 min at 150 wpm)
**Sources:** 155 documents indexed
**Focus:** a cold room, two people who know the rules of it
**Generated:** 2026-09-30T14:24:21.165Z

---

Elias: I’m in Millbrook Falls with wind through a door, and insulation is a coat ticket to you?

Mara: Room and body temperatures stay separate. Core body starts at 37°C and drifts each world tick.

Elias: Ambient defaults to 21°C. Insulation stacks, wind chill bites, and humidity colors what I feel.

Mara: Effective feels-like temperature combines room ambient temperature, stacked insulation, wind chill, and humidity; it does not replace room state.

Elias: So set_environment replaces the value, while adjust_environment applies a relative change clamped to -50–100°C?

Mara: Exactly. temperature_below and temperature_above read the room’s current environment.

Elias: You reject unsafe graph mutations. That is the whole job.

Mara: Step back. This episode asks how a local, single-player VirtualWorld keeps its property graph authoritative without making rooms inert.

Elias: Schemas, audits, safe writes, and tests enforce that.

Mara: Weather, doors, body state, actions, and ongoing play must survive it.

Elias: Insulation can help in cold and worsen exposure in heat. Don’t sand out that tension.

Mara: Strict graph. Survivable world.

Mara: I seal the cold-room calibration rig in audit mode. Millbrook Falls begins with room ambient at its default 21°C; my core starts at 37°C in the player stats, a separate vital.

Elias: I watch two needles pretend to be one verdict. The room-info panel says where the air is; my stats say where my body is, and discomfort is only a complaint.

Mara: I call set_environment, which replaces the room’s current environment temperature. I compare temperature_below and temperature_above against that current room value, never at my core.

Elias: I call adjust_environment for a relative change, clamped between -50°C and 100°C. I add worn, stacked insulation, wind chill, and humidity modifiers to the current ambient; that combined total becomes my feels-like temperature, and insulation that helps in cold can worsen exposure in heat.

Mara: I fasten the layers, then reject your easy equation. The cold room may be freezing while my body is only uncomfortable, but I will not erase either reading to make the test tidy.

Elias: I watch each world tick drift my 37°C core. I can call myself uncomfortable while the trigger says freezing; I risk my commission before I erase that disagreement.

Mara: I will verify both displays. Next, we test a relative drop.

Elias: I let the drop stand; we enter Millbrook’s gear room. Make you my caretaker: equip me; recover the lamp before the room doubles us.

Mara: Your location is one graph-edge anchor, only at the room’s waypoint. I move him there; his edge changes. At, on, under, behind, and beside are relations, never duplicates.

Elias: I take the gloves: their in edge leaves the room, and carrying points from item to me. Get and pickup alias take; engine operations entirely ignore legacy Player.inventory.

Mara: I equip them across thirteen visual body areas, checking stacking limits and the unlimited accessory slot. Two-handed weapons and full-body suits occupy these layers.

Elias: I feel the equipment edges settle. Mara, move to the lamp; it has an in edge to this room, not some invisible private inventory cache.

Mara: I move to the target, updating location from at the waypoint to beside the lamp. Taking it removes its room edge and creates carrying to me.

Elias: I enter lamp as the named item; the engine validates it. Toggling records its state; consume or deplete actions can fire its attached triggers.

Mara: I keep the lamp carried, not duplicated, with one recorded state. Next we test whether equipped items can trigger the room’s logic.

Mara: I get one action this turn, no more; the queue closes when my turn is done. I will not let the lamp trigger another decision in me.

Elias: I keep a hand on the cold-room door, and opening it spends my turn. I feel Millbrook Falls still waiting just beyond this cold door.

Mara: I hear sequential, random, and d20+DEX initiative set queue order without changing the rule: one decision per character per turn. I apply it equally to autonomous and human participation.

Elias: I know every player action triggers a full tick_turn: engine default, one minute per tick; this scenario, five. I watch one completed queue cycle advance turn number, world clock, and tick effects exactly once.

Mara: I check the threshold, where a temperature warning uses effective feels-like temperature. I reject any decorative reading because the core-temperature bar maps 25–45°C to 0–100%.

Elias: I feel the cold working through that scale, not appearing on glass. I read HP damage, regeneration gates, and resistances as limits on what action remains possible.

Mara: I mark hypothermia onset from 33–34.9°C and heat stroke above 40°C. I reject this harmless bar display as permission. I mark death below thirty or above forty-two Celsius.

Elias: I spend it. I open it.

Mara: I let the open door stand as the record of your one action. I do not call that surrender; I call it the tick made visible. The room must reject unsafe mutations, yet leave every accepted action meaningful.

Elias: I feel it at the threshold: play does not come from removing limits, but from making people care what those limits permit. A closed door becomes a wall, and I lose the person beyond it.

Mara: I still reject mercy that falsifies the graph. Humane play begins where the state remains authoritative and the choice remains honest.

Elias: I would build the next scenario around this choice: another cold-room threshold where the final action opens the way for someone instead of merely advancing the world.

Mara: I would calibrate every rule until its answer is clear, even when that answer is no.

Elias: I would make the threshold leave room for a human voice.

Mara: I will hold the line.

Elias: I will make the crossing matter.

Mara: Thank you for keeping the cold alive.

Elias: Thank you for making its edges true. I'll see you next time.
