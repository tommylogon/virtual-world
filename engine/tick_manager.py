from graph import EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED
from player import BLOCKING_CONDITIONS
from engine.vitals import is_drive


class TickManager:
    """Manages the game clock, action costs, vital decay, turn processing,
    and rest mechanics."""

    def __init__(self, graph, player_manager, lighting, toggleable_items, trigger_system, npc_behaviors):
        self.graph = graph
        self.player_manager = player_manager
        self.gs = player_manager  # player_manager is the VirtualWorldEngine instance
        self.lighting = lighting
        self.toggleable_items = toggleable_items
        self.trigger_system = trigger_system
        self.npc_behaviors = npc_behaviors
        self._last_sound_sources = {}  # Track sound sources to avoid duplicate notifications

    @staticmethod
    def _get_equipment_bonuses(player, graph):
        from engine.equipment_bonuses import aggregate_bonuses
        return aggregate_bonuses(player, graph)

    def apply_action(self, action_name, override_cost=None, player=None):
        """Apply action costs to a player's vitals based on action type and traits."""
        target = player or self.player_manager.player
        if not target:
            return
        base = self.player_manager.ACTION_COSTS.get(action_name, {})
        cost = dict(base)
        if override_cost:
            for k, v in override_cost.items():
                try:
                    cost[k] = int(v)
                except (ValueError, TypeError):
                    cost[k] = v
        from engine.traits import TraitSystem
        trait_mods = TraitSystem.get_action_cost_mods(target)
        for tk, tv in trait_mods.items():
            lk = str(tk).lower()
            cost[lk] = max(0, int(cost.get(lk, 0)) + tv)
        # Trait schema v2: move_cost_mod applies to movement actions only
        if action_name in ("move", "dash"):
            for mk, mv in TraitSystem.get_move_cost_mods(target).items():
                lk = str(mk).lower()
                cost[lk] = max(0, int(cost.get(lk, 0)) + mv)
        vitals_map = {k.lower(): k for k in target.vitals.keys()}
        time_ticks = int(cost.get("time", 0))
        for k, v in list(cost.items()):
            lk = str(k).lower()
            if lk == "time":
                continue
            if lk in vitals_map:
                key = vitals_map[lk]
                delta = int(v)
                total_delta = delta * (time_ticks if time_ticks > 0 else 1)
                target.vitals[key] = max(0, min(100, target.vitals[key] - total_delta))
        if time_ticks > 0:
            self.player_manager._action_time_consumed = True
        else:
            self.player_manager._action_time_consumed = False

    def advance_clock(self, ticks=1):
        """Advance the game clock by the given number of ticks.
        This only advances time - it does NOT apply baseline stat decay.
        Baseline decay now happens on turn change via tick_turn()."""
        self.player_manager.time_ticks += ticks

    def get_current_time(self):
        """Return the current in-game time as a clock (HH:MM:SS).

        Works with fractional ``time_per_tick_minutes`` (e.g. 2.5): the
        leftover fraction of a minute rolls into seconds. Clock math is
        shared with the engine facade via ``total_game_minutes()``
        (task-322 R3).
        """
        total_minutes = self.gs.total_game_minutes()
        total_seconds = int(total_minutes * 60) % (24 * 3600)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def tick_turn(self, skip_npcs=False):
        """Apply baseline vital decay and environmental effects to ALL characters.
        When skip_npcs=True, NPC behavior processing is skipped (used during rest)."""
        def get_need_message(stat, value):
            messages = {
                "Energy": {75: "You're getting a bit tired.", 50: "You're feeling quite weary.", 25: "You're exhausted and struggling.", 10: "You can barely stay awake..."},
                # Hunger/Thirst are DRIVES since the 2026-08 flip: they RISE
                # toward 100 (starving/dehydrated at max), so tiers are
                # rise-above instead of drop-below.
                "Hunger": {25: "Your stomach is beginning to rumble.", 50: "You're getting quite hungry.", 75: "You're famished - your stomach hurts.", 90: "You're so hungry you feel weak."},
                "Thirst": {25: "You're starting to feel a bit parched.", 50: "Your throat is dry.", 75: "You're very thirsty - your lips are chapped.", 90: "You're extremely dehydrated..."},
                "Hygiene": {75: "You're not as fresh as you'd like.", 50: "You're starting to feel grimy.", 25: "You're quite dirty.", 10: "You need to clean up immediately."},
                "Social": {75: "You're feeling a bit lonely.", 50: "You miss being around people.", 25: "You're feeling isolated.", 10: "You desperately crave contact."},
                "Bladder": {40: "You could use a bathroom soon.", 65: "Your bladder is getting uncomfortably full.", 75: "You really need to find a bathroom!", 90: "You're in serious discomfort and will pee yourself soon!"},
                "Sanity": {75: "You feel a bit unsettled.", 50: "The isolation is getting to you.", 25: "You're losing your grip on reality.", 10: "You can barely hold it together."},
                "Entertainment": {75: "Things are getting a bit dull.", 50: "You need something to do.", 25: "You're bored out of your mind.", 10: "The monotony is unbearable."}
            }
            return messages.get(stat, {}).get(value, f"High {stat} effects.")
        need_advice = {
            "Energy": "Consider resting.", "Hunger": "You need to find food.", "Thirst": "Find something to drink.",
            "Hygiene": "Find a way to clean up.", "Social": "Try talking to someone.",
            "Bladder": "Find a bathroom.", "Sanity": "Talk to someone or find comfort.",
            "Entertainment": "Find something fun to do."
        }

        from engine.equipment_bonuses import effective_temperature, resisted_damage

        # Process periodic condition effects (poison, sick, etc.)
        self.gs.conditions.process_tick()

        # Incapacitated grapplers let go of everyone they're holding
        # (unconscious/dead/paralysed etc. — can't keep a grip while down),
        # then run the edge⇔condition grapple sync (orphan cleanup + desync repair).
        try:
            grapple = getattr(self.gs, "grapple", None)
            if grapple:
                for gname, gplayer in list(self.player_manager.players.items()):
                    if grapple._grappling_targets(gname):
                        if set(gplayer.conditions) & set(BLOCKING_CONDITIONS):
                            grapple.release_all_for(gname)
                grapple.sync()
        except Exception:
            pass

        for pname, p in self.player_manager.players.items():
            if p.state == "dead":
                continue

            p.reset_turn_state(self.player_manager.time_ticks)

            if p.has_condition("unconscious"):
                sleeping = any(
                    inst.get("source") == "sleep"
                    for inst in p.conditions.get("unconscious", [])
                )
                if not sleeping:
                    timer = p.state_timer
                    if timer > 0:
                        p.state_timer = timer - 1
                        p.vitals["Energy"] = min(20, p.vitals.get("Energy", 0) + 4)
                        if p.state_timer == 0:
                            p.remove_condition("unconscious")
                            p.vitals["Energy"] = 20
                            if pname == self.player_manager.active_player:
                                self.player_manager.add_log_entry(f"You wake up, groggy and disoriented. Your Energy is at {p.vitals['Energy']}%.")
                    continue
                # sleeping: falls through to normal vitals decay; the activity
                # system wakes at full Energy (regen applied below)

            from engine.traits import TraitSystem
            if TraitSystem.has_effect(p, "is_slasher"):
                continue

            prev_vitals = p.vitals.copy()
            trait_multipliers = TraitSystem.get_vital_multipliers(p)
            for stat, default_decay in self.player_manager.baseline_decay.items():
                if stat in p.vitals and stat != "Temperature":
                    rate = p.decay_rates.get(stat, default_decay)
                    mult = trait_multipliers.get(stat, 1.0)
                    if is_drive(stat):
                        # drives FILL toward 100 (starving/dehydrated at max)
                        p.vitals[stat] = min(100, p.vitals[stat] + int(rate * mult))
                    else:
                        p.vitals[stat] = max(0, p.vitals[stat] - int(rate * mult))

            # Affect drift toward baseline (task-96) — cheap no-op until the
            # character's emotion map has been touched.
            if hasattr(p, 'decay_emotions'):
                p.decay_emotions()

            if TraitSystem.has_effect(p, "no_entertainment_decay"):
                if "Entertainment" in p.vitals:
                    p.vitals["Entertainment"] = min(100, p.vitals["Entertainment"] + int(p.decay_rates.get("Entertainment", 1)))

            # Trait-driven Entertainment modifiers
            if "Entertainment" in p.vitals:
                ent_mod = 0
                if TraitSystem.has_effect(p, "impatient"):
                    if p.vitals.get("Energy", 100) > 80:
                        ent_mod -= 3
                if TraitSystem.has_effect(p, "patient"):
                    ent_mod += 1
                if TraitSystem.has_effect(p, "adventurous") and p.current_area:
                    if p.current_area not in getattr(p, 'visited_areas', set()):
                        ent_mod += 2
                if ent_mod:
                    p.vitals["Entertainment"] = max(0, min(100, p.vitals["Entertainment"] + ent_mod))

            # Bladder fills over time: 0 = empty (relieved), 100 = full (need to go)
            if "Bladder" in p.vitals:
                thirst = p.vitals.get("Thirst", 50)
                # flipped Thirst semantics: HIGH thirst = parched = less
                # liquid through you = slower bladder fill
                base_fill = 2 if thirst < 25 else (0 if thirst > 75 else 1)
                mult = trait_multipliers.get("Bladder", 1.0)
                p.vitals["Bladder"] = min(100, p.vitals["Bladder"] + int(base_fill * mult))

            if p.vitals.get("Energy", 1) <= 0:
                p.add_condition("unconscious", duration=5)
                # drops_held_items — collapsing, you let go of what's in your hands
                try:
                    self.gs.item_actions.drop_held_items(self.gs, pname)
                except Exception:
                    pass
                p.exhaustion_count = getattr(p, 'exhaustion_count', 0) + 1
                if p.exhaustion_count >= 3:
                    p.state = "dead"
                    if pname == self.player_manager.active_player:
                        self.player_manager.add_log_entry("The cold has claimed you. Your body gives out one last time — you do not wake.")
                    self.gs._spawn_body_item(pname, "exposure")
                    continue
                if pname == self.player_manager.active_player:
                    self.player_manager.add_log_entry("Your vision swims... the world tilts... you collapse from exhaustion. You have passed out.")

            hp_loss = 0
            # flipped drives: Hunger/Thirst max out at 100 (starving/dehydrated)
            if p.vitals.get("Hunger", 0) >= 100:
                hp_loss += 1
            if p.vitals.get("Thirst", 0) >= 100:
                hp_loss += 2
            if p.vitals.get("Sanity", 1) <= 0:
                hp_loss += 1
            if hp_loss > 0:
                p.vitals["HP"] = max(0, p.vitals["HP"] - hp_loss)

            if p.vitals.get("Bladder", 0) >= 100 and prev_vitals.get("Bladder", 0) < 100:
                p.vitals["Hygiene"] = max(0, p.vitals["Hygiene"] - 30)

            for stat in ["Energy", "Hunger", "Thirst", "Social", "Hygiene"]:
                val = p.vitals.get(stat)
                prev = prev_vitals.get(stat, val)
                if val is not None and prev is not None:
                    for t in ([75, 50, 25, 10] if not is_drive(stat) else [25, 50, 75, 90]):
                        if is_drive(stat):
                            # rising drive crosses tiers upward
                            if prev < t and val >= t:
                                msg = get_need_message(stat, t)
                                if stat in need_advice and val >= 50:
                                    msg += " " + need_advice[stat]
                                if pname == self.player_manager.active_player:
                                    self.player_manager.add_log_entry(msg)
                        elif prev > t and val <= t:
                            msg = get_need_message(stat, t)
                            if stat in need_advice and val <= 50:
                                msg += " " + need_advice[stat]
                            if pname == self.player_manager.active_player:
                                self.player_manager.add_log_entry(msg)

            if p.vitals.get("HP", 0) <= 0:
                cause_parts = []
                if p.vitals.get("Hunger", 0) >= 100:
                    cause_parts.append("starvation")
                if p.vitals.get("Thirst", 0) >= 100:
                    cause_parts.append("dehydration")
                if p.vitals.get("Sanity", 0) <= 0:
                    cause_parts.append("madness")
                if p.vitals.get("Temperature", 37) < 30:
                    cause_parts.append("hypothermia")
                if p.vitals.get("Temperature", 37) > 42:
                    cause_parts.append("heat stroke")
                cause_of_death = " and ".join(cause_parts) if cause_parts else "unknown causes"

                p.state = "dead"
                self.player_manager.add_log_entry(f"[{pname}] GAME OVER: You have died from {cause_of_death}.")
                self.gs._spawn_body_item(pname, cause_of_death)

            player_area_name = p.current_area
            if player_area_name:
                area_node = self.graph.get_node(self.player_manager.area_node_id(player_area_name))
                if area_node:
                    env = area_node.properties.get("environment", {})
                    bonuses = self._get_equipment_bonuses(p, self.graph)
                    air = env.get("air", "fresh")
                    if air == "stale":
                        p.vitals["Energy"] = max(0, p.vitals["Energy"] - 1)
                    elif air == "humid":
                        p.vitals["Social"] = max(0, p.vitals["Social"] - 1)
                    elif air == "toxic":
                        dmg = 3
                        resisted = resisted_damage(dmg, "toxic", bonuses)
                        if resisted < dmg:
                            p.vitals["HP"] = max(0, p.vitals["HP"] - (dmg - resisted))
                    noise = env.get("noise", "quiet")
                    if noise in ["loud", "chaotic", "dripping", "scratches"]:
                        # Phase 3 — loud_noise save_on hook (paranoid, light sleepers)
                        try:
                            self.gs._emit_save_on(
                                pname, "loud_noise",
                                {"noise": noise, "source": "area", "source_type": "area"},
                            )
                        except Exception:
                            pass
                    if noise in ["loud", "chaotic", "dripping", "scratches"] and (
                        p.activity and p.activity.get("type") == "sleeping"
                    ):
                        p.vitals["Energy"] = max(0, p.vitals["Energy"] - 1)
                        # Loud noise can wake a sleeper (perception save, task-131)
                        wake_msg = self.gs.activities.wake_on_noise(pname)
                        if wake_msg and pname == self.player_manager.active_player:
                            self.player_manager.add_log_entry(wake_msg)
                    smell = env.get("smell", "neutral")
                    if smell in ["mold", "rot", "rotting food", "ferment", "urine"]:
                        p.vitals["Hygiene"] = max(0, p.vitals["Hygiene"] - 1)
                    elif smell == "perfume":
                        p.vitals["Social"] = min(100, p.vitals["Social"] + 1)
                    light = self.lighting.get_ambient_light(area_node.id, env)
                    if light < 20:
                        p.vitals["Sanity"] = max(0, p.vitals["Sanity"] - 1)
                    others_here = [n for n, op in self.player_manager.players.items() if op.current_area == player_area_name and n != pname and op.state != "dead"]
                    if len(others_here) > 0:
                        p.vitals["Social"] = min(100, p.vitals["Social"] + 1)
                    else:
                        # Phase 3 — alone_in_dark save_on hook (nyctophobic)
                        if light < 20:
                            try:
                                self.gs._emit_save_on(pname, "alone_in_dark", {"light": light})
                            except Exception:
                                pass
                    social = p.vitals.get("Social", 100)
                    ent = p.vitals.get("Entertainment", 100)
                    sanity_penalty = 0
                    if social < 25:
                        sanity_penalty += 2
                    elif social < 50:
                        sanity_penalty += 1
                    if ent < 25:
                        sanity_penalty += 2
                    elif ent < 50:
                        sanity_penalty += 1
                    if sanity_penalty > 0:
                        p.vitals["Sanity"] = max(0, p.vitals["Sanity"] - sanity_penalty)
                    area_temp = float(effective_temperature(float(env.get("temperature", 21)), bonuses))
                    core_temp = p.vitals.get("Temperature", 37.0)
                    if area_temp < 5:
                        drift = (5 - area_temp) * 0.02
                        p.vitals["Temperature"] = max(25.0, core_temp - drift)
                    elif area_temp > 35:
                        drift = (area_temp - 35) * 0.02
                        p.vitals["Temperature"] = min(45.0, core_temp + drift)
                    else:
                        if core_temp < 36.5:
                            p.vitals["Temperature"] = min(37.0, core_temp + 0.1)
                        elif core_temp > 37.5:
                            p.vitals["Temperature"] = max(37.0, core_temp - 0.1)

            core_temp = p.vitals.get("Temperature", 37.0)
            if core_temp < 37 and core_temp >= 35:
                p.vitals["Energy"] = max(0, p.vitals["Energy"] - 1)
            elif core_temp < 35 and core_temp >= 33:
                p.vitals["Energy"] = max(0, p.vitals["Energy"] - 2)
                p.vitals["HP"] = max(0, p.vitals["HP"] - 1)
            elif core_temp < 33:
                p.vitals["HP"] = max(0, p.vitals["HP"] - 3)
            elif core_temp > 37 and core_temp <= 38:
                p.vitals["Thirst"] = max(0, p.vitals["Thirst"] - 1)
            elif core_temp > 38 and core_temp <= 40:
                p.vitals["HP"] = max(0, p.vitals["HP"] - 1)
            elif core_temp > 40:
                p.vitals["HP"] = max(0, p.vitals["HP"] - 3)

            # Sleep regen toward full (net +2 after baseline decay)
            if p.activity and p.activity.get("type") == "sleeping" and "Energy" in p.vitals:
                p.vitals["Energy"] = min(100, p.vitals["Energy"] + 3)

            # ── Persistent activities progress one step per tick (task-131) ──
            if p.activity:
                try:
                    activity_output = self.gs.activities.tick_activity(pname)
                    if activity_output and pname == self.player_manager.active_player:
                        self.player_manager.add_log_entry(activity_output)
                except Exception:
                    pass

            area_node = None
            if player_area_name:
                area_node = self.graph.get_node(self.player_manager.area_node_id(player_area_name))
            # Trait schema v2: keep trait-granted conditions in sync (any path
            # that mutates player.traits reconciles here within a turn).
            TraitSystem.sync_granted_conditions(p)
            # Phase 4: acquired traits from life events (near-death/starvation/confinement)
            from engine.traits import TRAIT_DEFINITIONS
            acquired = TraitSystem.check_scripted_acquisitions(p)
            if acquired:
                names = ", ".join(
                    (TRAIT_DEFINITIONS.get(t) or {}).get("name", t) for t in acquired
                )
                if pname == self.player_manager.active_player:
                    self.player_manager.add_log_entry(f"[{pname}] gained the {names} trait.")
            trait_logs = TraitSystem.process_tick_effects(p, self.player_manager.time_ticks, area_node)
            for log_line in trait_logs:
                if pname == self.player_manager.active_player:
                    self.player_manager.add_log_entry(log_line)

            if (p.vitals.get("Energy", 0) > 25 and p.vitals.get("Hunger", 0) > 25 and
                p.vitals.get("Thirst", 0) > 25 and p.vitals.get("Sanity", 0) > 25 and
                p.vitals.get("HP", 100) < 100 and 35 <= p.vitals.get("Temperature", 37) <= 39):
                regen_base = 1
                regen_mult = TraitSystem.get_hp_regen_multiplier(p)
                p.vitals["HP"] = min(100, p.vitals["HP"] + max(1, int(regen_base * regen_mult)))

            if p.state != "dead":
                player_node_id = self.player_manager._player_node_id(pname)
                carried_items = []
                for edge_type in (EDGE_CARRYING, EDGE_EQUIPPED):
                    for edge in self.graph.get_edges_for_target(player_node_id, edge_type):
                        item_node = self.graph.get_node(edge.source)
                        if item_node and item_node.type == "item":
                            carried_items.append(item_node)

                for item_node in carried_items:
                    is_lit = item_node.properties.get("current_state") == "lit"
                    # Fire on_tick for ANY carried item with the trigger — not
                    # just lit ones — so hidden disease carriers, amulets, and
                    # ticking hazards work from inventory (the sneeze-cloud
                    # contagion pattern).
                    tick_outputs = self.trigger_system._execute_triggers(
                        item_node, "on_tick", game_state=self.gs
                    )
                    if tick_outputs:
                        for o in tick_outputs:
                            if pname == self.player_manager.active_player:
                                self.player_manager.add_log_entry(o)

                    if is_lit:
                        uses_before = item_node.properties.get("uses", -1)
                        if item_node.properties.get("uses", -1) == 0 and uses_before > 0:
                            item_node.properties["current_state"] = "unlit"
                            if pname == self.player_manager.active_player:
                                self.player_manager.add_log_entry(f"Your {item_node.name} runs out and turns off.")
                            dep_outputs = self.trigger_system._execute_triggers(item_node, "on_depleted", game_state=self.gs)
                            if dep_outputs:
                                for o in dep_outputs:
                                    if pname == self.player_manager.active_player:
                                        self.player_manager.add_log_entry(o)

        # ── Area lit items burn down (shared room objects, once per tick) ──
        # The per-player loop above only ticks carried/equipped items. Embers,
        # torches, or other lit objects dropped in a room would never deplete
        # otherwise.
        for node in list(self.graph.nodes.values()):
            if node.type != "area":
                continue
            for edge in self.graph.get_edges_for_target(node.id, EDGE_IN):
                item_node = self.graph.get_node(edge.source)
                if not item_node or item_node.type != "item":
                    continue
                if item_node.properties.get("current_state") not in ("lit", "on"):
                    continue
                uses_before = item_node.properties.get("uses", -1)
                if uses_before == -1:
                    continue  # permanent sources (e.g. a lit stove) never burn out
                tick_outputs = self.trigger_system._execute_triggers(
                    item_node, "on_tick", game_state=self.gs
                )
                if tick_outputs:
                    for o in tick_outputs:
                        self.player_manager.add_log_entry(o)
                if item_node.properties.get("uses", -1) == 0 and uses_before > 0:
                    item_node.properties["current_state"] = "unlit"
                    self.player_manager.add_log_entry(f"The {item_node.name} burns out.")
                    dep_outputs = self.trigger_system._execute_triggers(
                        item_node, "on_depleted", game_state=self.gs
                    )
                    if dep_outputs:
                        for o in dep_outputs:
                            self.player_manager.add_log_entry(o)
                    self.graph.remove_node(item_node.id)

        self.advance_clock(1)

        if not skip_npcs:
            self.npc_behaviors.process_simple_npcs()

        # ── Delayed events now due (task-90) ──
        # Fired AFTER the clock advances, so an event scheduled 5 ticks from
        # now fires on the 5th subsequent turn. Iterate a snapshot: an event's
        # effects may queue further events that are themselves already due.
        try:
            delayed_outputs = self.gs._process_delayed_events() if hasattr(self.gs, "_process_delayed_events") else []
            for line in delayed_outputs:
                self.player_manager.add_log_entry(line)
        except Exception:
            pass

        # ── Heat sources: lit items with heat_source tag push room temp ──
        from engine.environment_propagation import apply_heat_sources, propagate_temperature
        apply_heat_sources(self.graph)

        # ── Temperature propagation between connected areas ──
        propagate_temperature(self.graph)

        # ── Sound sources: items with sound_source tag emit sound ──
        self._process_sound_sources()

    def _process_sound_sources(self):
        """Process sound sources each tick - propagate sound from active items."""
        from engine.sound import get_sound_sources_in_area, get_areas_hearing_sound_source, format_heard_narration
        
        # Build areas dict
        areas_dict = {}
        for node in self.graph.nodes.values():
            if node.type == "area":
                areas_dict[node.id] = node
        
        # Track current sound sources for deduplication
        current_sources = {}
        
        # Process each area for sound sources
        for area_id, area_node in areas_dict.items():
            sources = get_sound_sources_in_area(area_id, self.graph)
            
            for item_node, sound_level, sound_pattern in sources:
                source_key = f"{item_node.id}_{sound_pattern}"
                current_sources[source_key] = {
                    "area_id": area_id,
                    "area_name": area_node.name,
                    "sound_level": sound_level,
                    "pattern": sound_pattern,
                    "item_name": item_node.name
                }
                
                # Propagate sound to adjacent areas
                hearing_areas = get_areas_hearing_sound_source(
                    area_id, sound_level, self.graph, areas_dict
                )
                
                # Notify characters in the source's own area first (no barrier)
                hearing_areas[area_id] = (sound_level, "")
                
                # Notify characters in hearing areas
                for hearing_area_id, (remaining_pen, direction) in hearing_areas.items():
                    hearing_area = areas_dict.get(hearing_area_id)
                    if not hearing_area:
                        continue
                    
                    # Find characters in this area
                    for pname, player_obj in self.player_manager.players.items():
                        if getattr(player_obj, "current_area", None) != hearing_area.name:
                            continue
                        
                        # Add to recent hearing if not already notified this tick
                        notification_key = f"{source_key}_{hearing_area_id}_{pname}"
                        if notification_key not in self._last_sound_sources:
                            if not hasattr(player_obj, "recent_hearing"):
                                player_obj.recent_hearing = []
                            
                            hearing_entry = {
                                "type": "sound_source",
                                "sound_pattern": sound_pattern,
                                "source_item": item_node.name,
                                "source_area": area_node.name,
                                "heard_from": direction,
                                "distance": 3 - remaining_pen,
                                "tick": self.player_manager.time_ticks
                            }
                            player_obj.recent_hearing.append(hearing_entry)
                            if len(player_obj.recent_hearing) > 20:
                                player_obj.recent_hearing.pop(0)
                            
                            # Log narration for active player
                            if pname == self.player_manager.active_player:
                                narration = format_heard_narration(sound_pattern, direction, is_speech=False)
                                self.player_manager.add_log_entry(narration)
        
        # Update tracking for next tick
        self._last_sound_sources = current_sources

    def tick(self, ticks=1):
        """Legacy: no longer applies baseline decay per-tick.
        Only advances the clock. Call tick_turn() at turn change for vitals decay."""
        self.advance_clock(ticks)

    def rest(self, minutes=10, target_item_name=None):
        if self.player_manager.player.state in ["unconscious", "dead"]:
            raise ValueError("You cannot rest in your current state.")
        ticks = max(1, int(minutes // self.player_manager.time_per_tick_minutes))
        actual_minutes = ticks * self.player_manager.time_per_tick_minutes
        initial_energy = self.player_manager.player.vitals.get("Energy", 0)
        player = self.player_manager.player
        player.add_condition(
            "unconscious", duration=None, source="sleep",
            ends_on=["wake", "damage", "loud_noise", "energy_full"],
            overrides={"blocks_speech": False,
                       "description": "You are asleep. You can't act until you wake."},
        )
        try:
            self.gs.item_actions.drop_held_items(self.gs, player.name)
        except Exception:
            pass
        self.player_manager._action_time_consumed = True
        for _ in range(ticks):
            self.tick_turn(skip_npcs=True)
        player.conditions.pop("unconscious", None)
        if not player.conditions:
            player.conditions["awake"] = [{"duration": None, "source": None, "level": 0}]
        final_energy = self.player_manager.player.vitals.get("Energy", 0)
        energy_restored = final_energy - initial_energy
        sign = "+" if energy_restored >= 0 else ""
        return f"You rest for {actual_minutes} minutes{' on ' + target_item_name if target_item_name else ''}. Energy restored: {sign}{energy_restored}%. Current Energy: {final_energy}%."
