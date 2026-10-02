/**
 * prompt-builder/room-context.js — Area/room context assembler.
 *
 * Split from the monolithic prompt-builder.js (2026-08-09). The "assembler"
 * that pulls together lighting, items, exits, people, events into the area
 * context string that starts every user message. Exports merge into
 * window.PromptBuilder.
 *
 * Cross-file calls use PromptBuilder.<fn>(...).
 *
 * @module prompt-builder/room-context — the area/room context assembler
 * @contributes buildRoomContext, buildRoomContextParts, buildCharacterPreamble, viewerExits, buildNarratedRoomContext
 * @powers the room block that opens every user message (lighting, items, exits, people, witnessed)
 * @relates uses helpers + conversation-context; its output is assembled by turn-prompts
 * @docs docs/virtualWorld/World Building/Rooms & Areas.md
 */

interface PromptBuilderWindowSurface { PromptBuilder: Record<string, any> }
(window as unknown as PromptBuilderWindowSurface).PromptBuilder = (window as unknown as PromptBuilderWindowSurface).PromptBuilder || {};
(() => {
    'use strict';

    // Social-recall re-feel: when a character HEARS a line that references one of
    // their own memories, re-feel that memory's emotions (affect + subtle vitals)
    // and — when the speaker resolves to a known person — nudge the relationship.
    // Rate-limited per character so repeated chatter doesn't endlessly stack.
    const _socialRecallGuard: Record<string, number> = {};

    /**
     * shared/emotion-mapper.js attaches EmotionMapper to window at its own load
     * time, which may be after this script runs, so it is resolved per call and
     * never cached. globals.d.ts does not declare it.
     */
    function emotionMapper(): EmotionMapperApi | undefined {
        return (window as unknown as { EmotionMapper?: EmotionMapperApi }).EmotionMapper;
    }

    /** story-mode.js, likewise optional and late-bound. */
    function narrationUi(): NarrationUiApi | undefined {
        return (window as unknown as { narrationUI?: NarrationUiApi }).narrationUI;
    }

    /**
     * shared/item-containment.js and embedding-client.js attach themselves to
     * window at their own load time, which may be after this script runs, so
     * both are resolved per call and never cached. Neither is on the declared
     * Window surface.
     */
    function itemContainment(): ItemContainmentApi {
        return (window as unknown as { ItemContainment: ItemContainmentApi }).ItemContainment;
    }

    /** ApiClient's declared surface in globals.d.ts omits playerSpeak. */
    function apiClient(): ApiClientWithSpeak {
        return ApiClient as unknown as ApiClientWithSpeak;
    }

    function embeddingClient(): EmbeddingClientApi {
        return (window as unknown as { EmbeddingClient: EmbeddingClientApi }).EmbeddingClient;
    }

    async function _matchMemory(memories: MemoryEntry[], text: string, charName: string): Promise<MemoryEntry | null> {
        if (!text) return null;
        // Semantic via the embedding store when configured.
        if (embeddingClient() && EmbeddingClient.configured()) {
            try {
                const vec = await EmbeddingClient.embed(text);
                if (vec) {
                    const resp = await fetch('/api/memory/embeddings/search', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ vector: vec, character: charName, k: 3 })
                    });
                    const data = await resp.json();
                    for (const r of ((data.results || []) as Array<Record<string, any>>)) {
                        const key = r.key || '';
                        const memId = key.includes('::') ? key.split('::').pop() : key;
                        const entry = memories.find(m => String(m.id) === String(memId));
                        if (entry && (Number(r.score) || 0) >= 0.5) return entry;
                    }
                }
            } catch (e) { /* fall through to keyword */ }
        }
        // Keyword overlap fallback.
        const words = text.toLowerCase().split(/\s+/).filter((w: string) => w.length > 2);
        if (words.length === 0) return null;
        let best: MemoryEntry | null = null, bestScore = 0;
        for (const m of memories) {
            if (!m || !m.text) continue;
            const mt = m.text.toLowerCase();
            let overlap = 0;
            for (const w of words) if (mt.includes(w)) overlap++;
            const score = overlap / words.length;
            if (score > bestScore) { bestScore = score; best = m; }
        }
        return bestScore >= 0.5 ? best : null;
    }

    async function _fireSocialRecall(charName: string, seeds: SocialSeed[]): Promise<void> {
        try {
            const player = worldState.data?.players?.[charName];
            const memories = (player && player.memories) || [];
            if (!seeds.length || !memories.length) return;
            const now = Date.now();
            if (now - (_socialRecallGuard[charName] || 0) < 12000) return;
            for (const seed of seeds) {
                if (!seed || !seed.text) continue;
                const entry = await _matchMemory(memories, seed.text, charName);
                if (!entry) continue;
                const emos = (Array.isArray(entry.memory_emotions) && entry.memory_emotions.length)
                    ? entry.memory_emotions : (entry.emotion ? [entry.emotion] : []);
                if (!emos.length) continue;
                const mapped: Record<string, number> = {};
                for (const e of emos as MemoryEmotion[]) {
                    let dim = null;
                    if (emotionMapper()) {
                        const r = await emotionMapper()!.resolve(e.label as string);
                        dim = r && r.dimension;
                    } else if (e.label) {
                        dim = e.label;
                    }
                    if (!dim) continue;
                    const intens = Math.max(1, Math.min(10, Number(e.intensity) || 5));
                    mapped[dim] = (mapped[dim] || 0) + intens;
                }
                if (!Object.keys(mapped).length) continue;
                const body: Record<string, unknown> = { mapped };
                // Name-gated relationship nudge: only when the speaker is a known
                // player. An anonymized voice label stays a pure re-feel.
                if (typeof seed.speaker === 'string' && seed.speaker.trim() && worldState.players?.[seed.speaker]) {
                    body.toward = seed.speaker.trim();
                }
                _socialRecallGuard[charName] = now;
                fetch(`/api/players/${encodeURIComponent(charName)}/emotions/map`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                }).catch(() => {});
                break; // one social recall per turn so chatter doesn't stack
            }
        } catch (e) { /* non-critical */ }
    }

    function buildCharacterPreamble(charName: string, player: PlayerState | null): string {
        if (!player || !player.personality) return '';
        const fixNewlines = (s: unknown): string => ((s || '') as string).replace(/\\n/g, '\n');
        const personality = fixNewlines(player.personality).trim();
        if (!personality) return '';
        return `You are ${charName}. Personality: ${personality}`;
    }

    function normalizeVisibleItems(raw: unknown): string[] {
        if (raw == null) return [];
        if (Array.isArray(raw)) return (raw as unknown[]).map((name) => String(name).trim()).filter(Boolean);
        const text = String(raw).trim();
        return text ? [text] : [];
    }

    /**
     * Per-viewer exits for the PROMPT. The serialized `exits` view is keyed to
     * the server's single active player, which mis-filters for everyone else in
     * a multi-agent run (the butcher couldn't see his own hidden passage
     * because the state was built for whoever was active at fetch time). We
     * rebuild from `exits_authoring` (all ways) + THIS character's knowledge:
     * slashers see everything hidden, and authored `known` entities (way id /
     * area name / area id) count from the start. Runtime discoveries still
     * apply on top.
     */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
    function viewerExits(state: PromptState, charName: string, currentArea: CurrentArea | null | undefined): Record<string, ExitEntry> {
        const areaName = currentArea?.name || state?.current_area || '';
        const p = state?.players?.[charName];
        const all = (state?.areas?.[areaName]?.exits_authoring) || currentArea?.exits || {};
        const slasher = !!(p?.traits?.is_slasher || p?.traits?.slasher);
        const known = new Set<string>((p?.known || []).map(String));
        const areaIdGuess = 'area_' + String(areaName).toLowerCase().replace(/\s+/g, '_');
        const discovered = new Set<string>((p?.discovered_exits || []).map((d: [string, string]) => `${d[0]}|${d[1]}`));
        const out: Record<string, ExitEntry> = {};
        for (const [label, e] of Object.entries(all || {}) as Array<[string, ExitEntry]>) {
            if (!e || !e.hidden) { out[label] = e; continue; }
            if (slasher || known.has(String(e.way_id || '')) || known.has(areaName) || known.has(areaIdGuess)) {
                out[label] = e; continue;
            }
            if (discovered.has(`${areaName}|${e.direction || ''}`)) { out[label] = e; continue; }
        }
        return out;
    }

    /** True when the viewer is authored/runtime-known to another person. */
    function characterKnown(state: PromptState, charName: string, otherName: string): boolean {
        const p = state?.players?.[charName];
        const known = new Set((p?.known || []).map(String));
        const knownLower = new Set([...known].map((value: string) => value.toLowerCase()));
        const otherKey = String(otherName || '').toLowerCase().replace(/\s+/g, '_');
        return knownLower.has(String(otherName || '').toLowerCase())
            || knownLower.has('player_' + otherKey)
            || knownLower.has('character_' + otherKey);
    }

    function collectItemsInAreaByNames(areaName: string, allowedNames: unknown): string[] {
        const allowed = new Set(normalizeVisibleItems(allowedNames).map((name: string) => name.toLowerCase()));
        if (!allowed.size) return [];
        return worldState.getItemsInArea(areaName)
            .filter((item: ItemNode) => allowed.has(String(item.name || '').toLowerCase()))
            .map((item: ItemNode) => item.name as string);
    }

    function buildBeyondSuffix(state: PromptState, charName: string, exitData: ExitEntry,
                             targetAreaName: string, doorNode: GraphNode | null): string {
        const allowChars = !!exitData.allow_see_characters;
        const visibleItems = normalizeVisibleItems(exitData.visible_items);
        if (!allowChars && !visibleItems.length) return '';
        const wayState = exitData.state || 'closed';
        const seeThrough = !!doorNode?.properties?.see_through;
        if (wayState !== 'open' && !seeThrough) return '';

        const parts: string[] = [];
        if (allowChars && targetAreaName) {
            const allPlayers = state.players || {};
            Object.entries(allPlayers as Record<string, PlayerState>).forEach(([name, pdata]) => {
                if (name === charName || pdata.current_area !== targetAreaName) return;
                const desc = pdata.description || '';
                const displayName = PromptBuilder.anonymousName(charName, name, desc);
                if (pdata.activity) {
                    parts.push(`${displayName} (${PromptBuilder.describeActivity(pdata.activity)})`);
                } else if (pdata.state && pdata.state !== 'awake') {
                    parts.push(`${displayName} (${pdata.state})`);
                } else {
                    parts.push(displayName);
                }
            });
        }
        if (visibleItems.length && targetAreaName) {
            collectItemsInAreaByNames(targetAreaName, visibleItems).forEach(name => {
                parts.push(`the ${name}`);
            });
        }
        if (!parts.length) return '';
        return ` Beyond you can see: ${parts.join(', ')}.`;
    }

    function resolveAreaNode(areaName: string): GraphNode | null {
        if (!areaName) return null;
        for (const [nodeId, node] of Object.entries(worldState.graph?.nodes || {}) as Array<[string, GraphNode]>) {
            if (node.type === 'area' && (node.name === areaName || nodeId === areaName)) {
                return { id: nodeId, ...node };
            }
        }
        return worldState.getNodeByIdentifier(areaName);
    }

    function getContainedItems(parentItemId: string): ItemNode[] {
        // task-493: the ONE containment walk, shared with world-state.js and
        // mirroring the engine's item_reach. This used to be a single flat
        // level with no state check at all, so a part inside a closed device
        // was listed in the prompt and one nested two deep was invisible.
        return itemContainment().collectReachable([parentItemId], {
            getNode: (id: string) => worldState.getNode(id),
            edges: worldState.graph?.edges || [],
        }).filter((item: ItemNode) => (item.depth as number) > 0);
    }

    /**
     * Build the full area context as NAMED PARTS for a character — tick head,
     * personality preamble, appearance, carrying, room lead-in/body, exits,
     * items, people (with inline relationship labels), available actions,
     * witnessed events, and plan. The turn-prompt builders re-order these
     * parts so the state/memory blocks sit at the top (see turn-prompts.js),
     * while `buildRoomContext` assembles them in the new order for standalone
     * use (human turns, narration, lens previews).
     * @param {Object} state - Full world state data
     * @param {string} charName - Character name
     * @param {Object} player - Player data object
     * @param {Object} currentArea - Current area data object
     * @param {boolean|Object} [includePlanOrOptions=true] - boolean legacy flag, or
     *   `{ includePlan, agentFraming }`. When `agentFraming` is false (area/way/item
     *   lens), omits tick, personality, inventory, and plan — room content only.
     * @returns {Object} Named parts (agentFraming) OR { agentFraming:false, authoringText }
     */
    function buildRoomContextParts(state: PromptState, charName: string, player: PlayerState,
                                   currentArea: CurrentArea, includePlanOrOptions = true): RoomContextParts {
        let includePlan = true;
        let agentFraming = true;
        let preview = false;
        const opts = (typeof includePlanOrOptions === 'object' && includePlanOrOptions !== null)
            ? includePlanOrOptions as RoomContextOptions : null;
        if (opts) {
            includePlan = opts.includePlan !== false;
            agentFraming = opts.agentFraming !== false;
            preview = opts.preview === true;
        } else {
            includePlan = includePlanOrOptions !== false;
        }
        const light = (currentArea as Record<string, any>)?.ambient_light
            ?? (currentArea as Record<string, any>)?.environment?.light ?? 50;
        const level = PromptBuilder.lightToLevel(light);
        // Check for dark_vision trait
        const traits: Record<string, any> = player?.traits || {};
        const hasDarkVision = traits.dark_vision === true || traits.darkvision === true;
        // Blind characters are effectively pitch-black regardless of light — their
        // observation is rebuilt from sound/smell/touch, not sight (they aren't told
        // to "pretend"; the visual data is simply not presented to them).
        const isBlind = !!((player as Record<string, any>)?.conditions?.blind);
        let warn = '', items = '';
        // Authored `known` registry: hidden items flagged for this character
        // show up in their attention list (a cache she knows about is never
        // "hidden" to her).
        const knownItems = new Set<string>((player?.known || []).map(String));
        const areaItems = ((currentArea?.name ? worldState.getItemsInArea(currentArea.name) : []) as ItemNode[])
            .filter((it: ItemNode) => it.properties?.current_state !== 'hidden' || knownItems.has(it.id as string));
        const relationMap = PromptBuilder.buildRelationMap(areaItems);
        // Prepend a spatial relation ("on the table is a ...") for items that
        // sit on/under/behind/beside/inside another item in the area.
        const relateItem = (roomItem: ItemNode): string => {
            const rel = relationMap[roomItem.id as string];
            if (rel) return `${rel.prep} the ${rel.anchorName} is ${PromptBuilder.indefiniteArticle(roomItem.name)} ${roomItem.name}`;
            return roomItem.name as string;
        };
        // Rich item listing — full descriptions in good light (like the backend
        // area narration used to provide), names only in dim/dark conditions.
        // Each item carries a [bracket] of its allowed actions so the agent sees
        // what it can do with it at a glance.
        const itemBracket = (roomItem: ItemNode): string =>
            PromptBuilder.formatActionBrackets(PromptBuilder.computeItemActions(roomItem, player));
        const fmtItems = (list: ItemNode[], withDescriptions: boolean): string => {
            if (list.length === 0) return '';
            if (!withDescriptions) return list.map((roomItem: ItemNode) => `${relateItem(roomItem)} ${itemBracket(roomItem)}`.trim()).join(', ');
            return list.map((roomItem: ItemNode) => {
                const desc = String(roomItem.properties?.description || '').trim();
                const label = relateItem(roomItem);
                const bracket = itemBracket(roomItem);
                const head = bracket ? `${label} ${bracket}` : label;
                return desc ? `- ${head}: ${desc}` : `- ${head}`;
            }).join('\n');
        };
        // Interest-based attention: items matching the character's interest_tags
        // (exact tag +2, keyword-in-name +1) surface first, then everything else,
        // each ordered by weight (bigger = easier to see). Examined/taken items
        // drop off the attention list entirely — their facts live in the
        // investigation notes. Capped at ATTENTION_MAX; no truncation, just a
        // natural trailing line.
        const interestTags = ((player as Record<string, any>)?.interest_tags || []).map((tag: unknown) => String(tag).toLowerCase().trim()).filter(Boolean);
        const discoveredItems = new Set<string>(((player as Record<string, any>)?.discovered_items || []).map((name: unknown) => String(name).toLowerCase().trim()));
        const attentionScore = (roomItem: ItemNode): number => {
            const name = String(roomItem.name || '').toLowerCase();
            const itemTags = (roomItem.properties?.tags || []).map((tag: unknown) => String(tag).toLowerCase().trim());
            let score = 0;
            for (const tag of interestTags) {
                if (itemTags.includes(tag)) score += 2;
                else if (name.includes(tag)) score += 1;
            }
            return score;
        };
        const itemWeight = (roomItem: ItemNode): number => parseFloat(String(roomItem.properties?.weight)) || 0;
        const ATTENTION_MAX = 15;
        // Build the attention list from unexamined, non-hidden items.
        const buildAttention = (roomItems: ItemNode[], withDescriptions: boolean): string => {
            const unexamined = roomItems.filter((roomItem: ItemNode) => !discoveredItems.has(String(roomItem.name).toLowerCase().trim()));
            if (unexamined.length === 0) return '';
            const byAttention = (a: ItemNode, b: ItemNode) => attentionScore(b) - attentionScore(a) || itemWeight(b) - itemWeight(a);
            const attention = [...unexamined].sort(byAttention).slice(0, ATTENTION_MAX);
            const listLines = fmtItems(attention, withDescriptions);
            const hasMore = unexamined.length > attention.length;
            const trailer = hasMore
                ? 'There are more items around that you can look for.'
                : 'and nothing else catches your attention right now.';
            return `${listLines}\n${trailer}`;
        };
        if (isBlind) {
            warn = '⚠️ BLIND — It is pitch black to you no matter the light. You navigate by sound, smell, and touch. Fumble or search the area to locate things, listen to hear beyond your reach, and moving blind is risky without a cane or a guide.';
            const known = areaItems.filter((roomItem: ItemNode) =>
                discoveredItems.has(String(roomItem.name || '').toLowerCase().trim())
                && roomItem.properties?.current_state !== 'hidden'
            );
            items = known.length ? known.map((roomItem: ItemNode) => `${relateItem(roomItem)} ${itemBracket(roomItem)}`.trim()).join(', ') : '';
        } else if (hasDarkVision) {
            items = buildAttention(areaItems.filter(roomItem => roomItem.properties?.current_state !== 'hidden'), false);
        } else if (level === 'pitch_black') {
            warn = '⚠️ PITCH BLACK — You cannot see anything. Try to go back to a brighter area or use a light source.';
        } else if (level === 'dim') {
            items = buildAttention(areaItems.filter(roomItem => roomItem.properties?.current_state !== 'hidden' && (roomItem.properties?.weight||1)>=3), false);
            warn = '⚠️ Dim light — only large objects visible. Fine actions limited. Use a light source or move to a brighter area.';
        } else {
            items = buildAttention(areaItems.filter((roomItem: ItemNode) => roomItem.properties?.current_state !== 'hidden'), true);
        }
        const exitLines: string[] = [];
        const movementSuffix = (doorNode: GraphNode | null, handle: string): string => {
            if (typeof WayAuthoring !== 'undefined') {
                return WayAuthoring.movementHint(doorNode, handle);
            }
            const req = (doorNode?.properties?.requires || '').toLowerCase();
            if (req === 'crawl') return ` (crawl: go ${handle} auto-crawls)`;
            if (req === 'climb') return ` (climb: climb ${handle})`;
            if (req === 'jump') return ` (jump: jump ${handle})`;
            return '';
        };
        const areaNode = resolveAreaNode(currentArea?.name as string);
        // task-313: the old transit branch renamed a way's handle to the literal
        // "back"/"forward" in this prompt, so an agent was told to walk to a door
        // that had no such name. It could never fire anyway — the `transit` tag
        // was declared for ways while this read it off the AREA. Relative facing
        // is now the default and needs no tag, so the branch is gone and the
        // prompt keeps the authored handle, exactly like the server-side
        // description does.
        // Per-viewer exit map: authored `known` + slasher exemption + own
        // discoveries beat the server's single-active-player filtering
        // (the butcher sees his hidden passage; everyone else sees only what
        // THEY have discovered/learned).
        const viewerExitMap = PromptBuilder.viewerExits(state, charName, currentArea);
        const spatialPositionSuffix = (person: PresenceInfo): string => {
            const pos = person?.spatial_position;
            if (pos?.target_name && pos?.relation) {
                const label = pos.target_name;
                switch (pos.relation) {
                    case 'on': return ` on the ${label}`;
                    case 'under': return ` under the ${label}`;
                    case 'behind': return ` behind the ${label}`;
                    case 'beside': return ` beside the ${label}`;
                    default: return ` at the ${label}`;
                }
            }
            if (!person?.at_way_id || !currentArea?.exits) return '';
            for (const [dir, exitData] of Object.entries(viewerExitMap) as Array<[string, ExitEntry]>) {
                if (exitData.way_id !== person.at_way_id) continue;
                const doorNode = worldState.getNode(person.at_way_id);
                const handle = PromptBuilder.wayHandle({ ...exitData, label: dir }, doorNode, currentArea?.name as string);
                return ` at the ${handle}`;
            }
            return ' at the door';
        };
        if (viewerExitMap) {
            for (const [dir, exitData] of Object.entries(viewerExitMap) as Array<[string, ExitEntry]>) {
                if (exitData.hidden) continue;
                const doorNode = worldState.getNode(exitData.way_id);
                const handle = PromptBuilder.wayHandle({ ...exitData, label: dir }, doorNode, currentArea?.name);
                if (isBlind) {
                    // Blind characters sense a way by sound/draft, not by seeing it;
                    // traversing it blind is risky unless they have a cane or are led.
                    exitLines.push(`To the ${handle} — you sense an opening that way by sound and moving air. Going through blind is risky; a cane or a guide helps.`);
                    continue;
                }
                if (!doorNode) { exitLines.push(`To the ${dir}: ${exitData.target||'(unknown)'}`); continue; }
                const wayState = exitData.state || 'closed';
                const seeThrough = !!doorNode.properties?.see_through;
                const beyondSuffix = buildBeyondSuffix(state, charName, exitData, exitData.target as string, doorNode);
                const moveHint = movementSuffix(doorNode, handle);
                const preventClose = !!doorNode.properties?.prevent_close;
                const doorTags = (doorNode.properties?.tags || []).map((t: unknown) => String(t).toLowerCase().trim());
                const req = (doorNode.properties?.requires || '').toLowerCase();
                // Only reveal lock/force/block state the CHARACTER actually knows
                // (learned by examining or trying) — never the raw door state, which
                // would leak hidden info before they've discovered it (task-333).
                const forced = !!exitData.needs_force_known;
                const locked = !!exitData.known_locked;
                const blocked = !!exitData.known_blocked;
                let doorHint = ' (you can go through it, approach it, dash, or open it)';
                if (forced) doorHint = ' (you can force it open)';
                else if (locked) doorHint = " (it's locked — you'd need to unlock it first)";
                else if (blocked) doorHint = ' (it is blocked — you will need to clear it)';
                const openHint = doorHint;
                // task-243/109: item-gated paths (requires_item on the way) —
                // the agent should see the gear requirement, not just fail.
                const rawReq = doorNode.properties?.requires_item || '';
                const needsItem = rawReq
                    ? ` (needs: ${String(rawReq).split(',').map(s => s.trim().replace(/^tag:/i, 'the ')).join(' & ')})`
                    : '';
                if (wayState === 'open') {
                    const viewDirection = exitData.visible_in_direction || '';
                    const doorTags = (doorNode.properties?.tags || []).map((t: unknown) => String(t).toLowerCase().trim());
                    const openWord = doorTags.includes('exterior') || doorTags.includes('natural') ? 'is clear' : 'is open';
                    const closeHint = preventClose ? '' : ' or close it';
                    const actionHint = ` (you can go through it, approach it, dash, examine${closeHint})`;
                    if (viewDirection) {
                        exitLines.push(`[${handle}] ${openWord} — ${viewDirection}${beyondSuffix}${moveHint}${actionHint}${needsItem}`);
                    } else {
                        const targetArea = resolveAreaNode(exitData.target as string);
                        const clues = [];
                        if (targetArea?.properties?.environment) {
                            const targetEnv = targetArea.properties.environment;
                            const lightValue = parseInt(targetEnv.light) || 50;
                            if (lightValue <= 20) clues.push('pitch dark');
                            else if (lightValue <= 40) clues.push('dimly lit');
                            else if (lightValue >= 90) clues.push('brightly lit');
                            const noiseLevel = targetEnv.noise||'';
                            if (noiseLevel && !['quiet','silence','silent'].includes(noiseLevel)) clues.push(`${noiseLevel} audible`);
                            const temperatureValue = parseInt(targetEnv.temperature)||21;
                            if (temperatureValue >= 35) clues.push('very hot');
                            else if (temperatureValue >= 30) clues.push('hot');
                            else if (temperatureValue >= 25) clues.push('warm');
                            else if (temperatureValue >= 18) clues.push('pleasant');
                            else if (temperatureValue >= 12) clues.push('cool');
                            else if (temperatureValue >= 5) clues.push('chilly');
                            else if (temperatureValue >= 0) clues.push('cold');
                            else clues.push('freezing');
                        }
                        const clueString = clues.length ? ` (${clues.join(', ')})` : '';
                        exitLines.push(`To the ${handle}, the ${exitData.target} is visible beyond${clueString}.${beyondSuffix}${moveHint}${actionHint}${needsItem}`);
                    }
                } else {
                    const viewDirection = exitData.visible_in_direction || '';
                    const doorRawDescription = exitData.description || doorNode.properties?.description || `A way here.`;
                    const doorDescription = typeof InspectorHelpers?.resolveWayParams === 'function'
                        ? InspectorHelpers.resolveWayParams(doorRawDescription, doorNode.properties?.parameters || {})
                        : doorRawDescription;
                    if (seeThrough && viewDirection) {
                        exitLines.push(`[${handle}] is closed — through it you can see ${viewDirection}${beyondSuffix}${moveHint}${openHint}`);
                    } else if (beyondSuffix && seeThrough) {
                        exitLines.push(`[${handle}] ${doorDescription} It is currently closed.${beyondSuffix}${moveHint}${openHint}`);
                    } else {
                        exitLines.push(`[${handle}] ${doorDescription} It is currently closed.${moveHint}${openHint}`);
                    }
                }
            }
        }
        const exitsStr = exitLines.length ? '\nFrom where you stand, you can see the following paths:\n' + exitLines.join('\n') : '\n(no visible exits)';
        // task-313: relative facing. Only offered when this character actually
        // has a heading — otherwise "go left" would fail, and a prompt that
        // advertises a word the engine refuses is worse than silence. The
        // words ALIAS the paths above; they never replace their names.
        const _facing = player?.facing ?? state.players?.[charName]?.facing ?? null;
        const facingStr = _facing
            ? `\nYou are facing ${_facing}, so you can also use relative directions: ` +
              `forward (${_facing}), and left/right/back turn you from there. ` +
              `These name the same paths as the directions above.`
            : '';
        // Carrying line with per-item action brackets (drop/use/wear/examine...).
        // task-330-ish polish: each carried/worn item also shows its FULL
        // description (never truncated) plus whether you know what it is
        // (discovered/examined) — items you own are things you should be able
        // to reason about, not just name-drop.
        const carriedItems = PromptBuilder.carriedItemNodes(charName) as ItemNode[];
        const wornItems = carriedItems.filter((c: ItemNode) => c.equipped);
        const notWornItems = carriedItems.filter((c: ItemNode) => !c.equipped);
        // Known = equipped/worn-now (direct interaction), authored "Known by"
        // entity ids (player.known), runtime discovery (examined/taken ->
        // discovered_items, matched by name), or an intrinsic ability.
        // Anything else has not been examined/used with this character.
        const knownIds = new Set((player?.known || []).map(String));
        const isKnown = (item: ItemNode, wornNow: boolean): string =>
            wornNow ||
            PromptBuilder.isDiscovered(player, item.name) ||
            PromptBuilder.isIntrinsicAbility(item.properties) ||
            knownIds.has(String(item.id));
        // Durability in plain words (task-161): worn gear degrades on hits and
        // the agent should read condition, never numbers.
        const durTag = (item: ItemNode): string => {
            const maxUses = parseInt(item.properties?.max_uses, 10) || 0;
            const uses = parseInt(item.properties?.uses ?? -1, 10);
            if (maxUses <= 0 || uses < 0) return '';
            const ratio = uses / maxUses;
            if (uses <= 0) return '[broken]';
            if (ratio <= 0.25) return '[about to break]';
            if (ratio <= 0.5) return '[battered]';
            if (ratio <= 0.9) return '[worn]';
            return '[pristine]';
        };
        // Freshness in plain words (task-191): spoiled food is a fact the
        // agent must reason about without numbers.
        const freshTag = (item: ItemNode): string => {
            if (!item.properties?.perishable) return '';
            const state = item.properties.freshness_state || '';
            if (state === 'cooked') return '(cooked)';
            if (state === 'spoiled') return '(spoiled)';
            return '(fresh)';
        };
        const buildItemTree = (items: ItemNode[], equipped: boolean): string[] => {
            const lines = [];
            for (const c of items) {
                const b = PromptBuilder.formatActionBrackets(PromptBuilder.computeItemActions({ id: c.id, name: c.name, properties: c.properties }, player, { equipped }));
                const d = durTag(c as ItemNode);
                const f = freshTag(c as ItemNode);
                const desc = (c.properties?.description || '').trim();
                const knownTag = isKnown(c as ItemNode, equipped) ? '(known)' : '(not yet examined)';
                const descPart = desc ? ` — ${desc}` : '';
                lines.push(`${c.name} ${b}${d ? ' ' + d : ''} ${f ? f + ' ' : ''}${knownTag}${descPart}`.trim());
                // Indent by depth (task-493): a part is legible as a part of
                // the thing above it, and a part of a part reads the same way.
                for (const ci of getContainedItems(c.id as string)) {
                    const cb = PromptBuilder.formatActionBrackets(PromptBuilder.computeItemActions({ id: ci.id, name: ci.name, properties: ci.properties }, player, { equipped: false }));
                    const cd = durTag(ci);
                    const cf = freshTag(ci);
                    const cdesc = (ci.properties?.description || '').trim();
                    const cknownTag = isKnown(ci, false) ? '(known)' : '(not yet examined)';
                    const cdescPart = cdesc ? ` — ${cdesc}` : '';
                    const pad = '    '.repeat(Math.max(1, ci.depth || 1));
                    lines.push(`${pad}${ci.name} ${cb}${cd ? ' ' + cd : ''} ${cf ? cf + ' ' : ''}${cknownTag}${cdescPart}`.trim());
                }
            }
            return lines;
        };
        const wornStr = wornItems.length
            ? `Wearing:\n${buildItemTree(wornItems, true).join(',\n')}`
            : '';
        const carryStr = notWornItems.length
            ? `Carrying:\n${buildItemTree(notWornItems, false).join(',\n')}`
            : '';
        const knownAbilities = PromptBuilder.knownAbilityNodes(charName);
        const knownAbilityLines = knownAbilities.map((ab: ItemNode) => {
            const b = PromptBuilder.formatActionBrackets(PromptBuilder.computeItemActions({ id: ab.id, name: ab.name, properties: ab.properties }, player));
            const desc = (ab.properties?.description || '').trim();
            const head = b ? `${ab.name} ${b}` : ab.name;
            return desc ? `- ${head}: ${desc}` : `- ${head}`;
        });
        const knownStr = knownAbilityLines.length
            ? `Known Abilities:\n${knownAbilityLines.join('\n')}`
            : '';
        const invStr = [wornStr, carryStr, knownStr].filter(Boolean).join('\n');
        const appearanceDesc = player?.description || '';
        const equipStr = appearanceDesc ? `Your appearance: ${PromptBuilder.secondPersonDesc(appearanceDesc)}` : '';
        const others = state.players_in_area || [];
        const allPlayers = state.players || {};
        let peopleStr = '';
        if (others.length > 0) {
            const peopleLines = others.map(person => {
                let desc = person.description || '';
                if (isBlind) {
                    desc = `You can hear them nearby — ${desc.split('.')[0]}.`;
                } else if (level === 'pitch_black') {
                    desc = `You can hear them nearby — ${desc.split('.')[0]}.`;
                } else if (level === 'dim') {
                    desc = `A vague shape in the gloom — ${desc.split('.')[0]}.`;
                } else {
                    // First impression: the first sentence is the highlight of
                    // what you see at a glance — the rest comes from examining.
                    desc = desc.split('.')[0].trim() + (desc.includes('.') ? '.' : '');
                }
                const isMet = worldState.hasMet(charName, person.name);
                // Anonymize strangers — hide the database name if character hasn't met them
                const displayName = PromptBuilder.anonymousName(charName, person.name, desc);
                // The short label (the man) is just a handle — what someone looks like
                // is how you perceive them, met or not, so keep the description for both.
                const descSuffix = desc ? ` — ${desc}` : '';
                const actSuffix = person.activity ? ` (${PromptBuilder.describeActivity(person.activity)})` : '';
                const atSuffix = spatialPositionSuffix(person);
                // Relationship type inline ("a close friend") when known; strangers get no label.
                const relLabel = PromptBuilder.buildRelationshipLabel(player, person.name);
                const relPart = relLabel ? ` - ${relLabel} - ` : ' ';
                return `  - ${displayName}${relPart}(${person.state})${actSuffix}${atSuffix}${descSuffix}`;
            });
            peopleStr = '\nPeople here:\n' + peopleLines.join('\n');
        } else {
            peopleStr = '\nYou see no one else here.';
        }
        let witnessedEvents = '';
        const witnessedLines: string[] = [];
        const socialSeeds: SocialSeed[] = [];

        // Include recent_hearing for cross-room sound propagation
        const recentHearing = ((player as Record<string, any>)?.recent_hearing || []) as HearingEntry[];
        // N3: hearing is a rolling buffer — lines must age out, or a guest's
        // instruction stays in WITNESSED five turns later. Entries now carry a
        // real tick (engine speech.py); anything older than 8 ticks is stale.
        const curTick = (worldState.data?.time_ticks) || 0;
        const hearingFresh = (h: HearingEntry) => !h.tick || (curTick - Number(h.tick)) <= 8;
        const heardSpeech = recentHearing.filter((h: HearingEntry) => h.type !== 'sound_source' && h.speaker !== charName && hearingFresh(h)).slice(-5);
        // Sound sources (alarms, ringing phones) propagate too — characters should perceive them
        const heardSounds = recentHearing.filter((h: HearingEntry) => h.type === 'sound_source' && hearingFresh(h)).slice(-3);

        // Dedupe seen speech so a line isn't shown both as a local event and as heard speech
        const seenSpeechKeys = new Set<string>();
        // Plain lowercase texts seen so far (for contains-match dedupe — a heard
        // echo like "hello lyrie!" is often nested inside a narrated local event).
        const seenSpeechTexts: string[] = [];
        // task-360 polish: identical witnessed lines collapse — a character's
        // decide emote and react emote are often the same gesture, and both
        // land in turn_events; showing it twice reads as a glitch.
        const seenWitnessKeys = new Set<string>();
        const witnessKey = (actor: string | undefined, text: unknown): string =>
            `${actor || ''}|${String(text || '').toLowerCase().replace(/\s+/g, ' ').trim()}`;

        // Local events from turn_events (same area, other actors) WITHIN the
        // character's presence window (task-360): the per-area ledger records
        // entry_tick, so events before you arrived are never witnessed — the
        // window ends at your next turn because turn_events are per-turn.
        // Back-and-forth is the memory system's job (no auto-replay).
        const entryTick = (state.area_presence?.[currentArea?.name as string]?.[charName] as number | undefined) ?? 0;
        const recentEvents = (state.turn_events || []).filter((evt: TurnEvent) =>
            evt.area === currentArea?.name &&
            evt.actor !== charName &&
            (evt.tick ?? 0) >= entryTick &&
            (!isBlind || evt.action === 'speak'));
        recentEvents.slice(-10).forEach((evt: TurnEvent) => {
            const actorDesc = allPlayers[evt.actor as string]?.description || '';
            const anon = PromptBuilder.anonymousName(charName, evt.actor, actorDesc);
            // N12: emote/action descriptions are stored with the RAW actor name
            // ("Lyrie stamps snow off boots") — anonymize the inside too while
            // the name is unknown, so pre-introduction rows never leak it.
            const firstSighting = (player as Record<string, any>)?.relationships?.[evt.actor as string]?.first_sighting;
            const nameKnown = firstSighting === false;
            let descText = String(evt.description || '');
            if (!nameKnown && evt.actor) {
                const escActor = String(evt.actor).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                descText = descText.replace(new RegExp(escActor, 'gi'), anon);
            }
            let line = `[${anon}] ${descText}`;
            const wKey = witnessKey(anon, descText);
            if (seenWitnessKeys.has(wKey)) return;
            seenWitnessKeys.add(wKey);
            // Salience-mark direct speech so the character notices lines aimed at them.
            if (evt.action === 'speak' && evt.description) {
                const textMatch = evt.description.match(/said: "(.+)"/);
                if (textMatch) {
                    const spoken = textMatch[1].toLowerCase();
                    seenSpeechKeys.add(`${evt.actor}|${spoken}`);
                    seenSpeechTexts.push(spoken);
                    line = PromptBuilder.markSpeechLine(line, textMatch[1], charName, player);
                    socialSeeds.push({ speaker: evt.actor, text: textMatch[1] });
                }
            }
            witnessedLines.push(line);
        });

        // Heard speech from other rooms — skip any already shown as local events
        heardSpeech.forEach(h => {
            const heardText = String(h.text || '');
            const dedupeKey = `${h.speaker}|${heardText.toLowerCase()}`;
            if (seenSpeechKeys.has(dedupeKey)) return;
            // Contains-match: the heard echo is often a fragment of a narrated
            // local event (e.g. ...say "hello lyrie! i'm miki!"...), so collapse
            // those rather than render the same greeting twice.
            const heardLower = heardText.toLowerCase();
            const contained = seenSpeechTexts.some(seen =>
                heardLower && (heardLower.includes(seen) || seen.includes(heardLower)));
            if (contained) return;
            seenSpeechKeys.add(dedupeKey);
            seenSpeechTexts.push(heardLower);
            // Voice-based label — the listener can't see the speaker's body
            const anon = PromptBuilder.voiceLabel(charName, h.speaker);
            const direction = h.heard_from ? ` from the ${h.heard_from}` : '';
            let line = `[Heard${direction}] ${anon} said: "${h.text}"`;
            line = PromptBuilder.markSpeechLine(line, h.text, charName, player);
            witnessedLines.push(line);
            socialSeeds.push({ speaker: h.speaker, text: h.text });
        });

        // Heard sound sources (alarms, ringing phones, etc.) from this or adjacent areas
        heardSounds.forEach(h => {
            const pattern = h.sound_pattern || 'a sound';
            const sourceName = h.source_item ? ` from the ${h.source_item}` : '';
            const direction = h.heard_from ? ` from the ${h.heard_from}` : '';
            const line = `[Heard${direction}${sourceName}] ${pattern}.`;
            const wKey = witnessKey('sound', line);
            if (seenWitnessKeys.has(wKey)) return;
            seenWitnessKeys.add(wKey);
            witnessedLines.push(line);
        });

        // No fallback to the frontend room-event log (task-360): that
        // accumulator is a designer's log for the inspector, not a perception
        // channel — watching stale rows would leak pre-entry knowledge and
        // pollute the presence window. Trust the memory system instead.

        // Always render the WITNESSED header — placeholder when nothing to report
        witnessedEvents = witnessedLines.length > 0
            ? '\n\n=== WITNESSED ===\n' + witnessedLines.join('\n')
            : '\n\n=== WITNESSED ===\nNothing unusual happened while you were looking.';
        // Social recall: if something heard references one of this character's
        // memories, re-feel it (and nudge the relationship when known). Preview
        // mode (Agent Lens) never fires this — it embeds the seeds and POSTs
        // affect, so a preview must not do either.
        if (!preview && socialSeeds.length) _fireSocialRecall(charName, socialSeeds);
        // Build narrative lead-in — use feels_like from backend state if available
        const feelsLike = (player as Record<string, any>)?.feels_like ?? (currentArea as Record<string, any>)?.environment?.temperature;
        const tempFeel = feelsLike != null
            ? (feelsLike >= 35 ? 'very hot' : feelsLike >= 30 ? 'hot' : feelsLike >= 25 ? 'warm' : feelsLike >= 18 ? 'pleasant' : feelsLike >= 12 ? 'cool' : feelsLike >= 5 ? 'chilly' : feelsLike >= 0 ? 'cold' : feelsLike >= -10 ? 'freezing' : feelsLike >= -25 ? 'bitterly cold' : 'arctic')
            : '';
        const lightFeel = level === 'pitch_black' ? 'pitch dark'
            : level === 'dim' ? 'dimly lit'
            : level === 'normal' ? 'well lit'
            : level === 'bright' ? 'bright'
            : level === 'blinding' ? 'blindingly bright'
            : '';
        const smellNote = (currentArea as Record<string, any>)?.environment?.smell
            ? ` The air smells of ${(currentArea as Record<string, any>).environment.smell}.` : '';
        let leadIn: string;
        if (isBlind) {
            const soundNote = (currentArea as Record<string, any>)?.environment?.noise
                ? ` You hear ${(currentArea as Record<string, any>).environment.noise}.` : '';
            leadIn = `You are in the ${currentArea?.name || '(none)'}, though you cannot see it — it is pitch black to you. It feels ${tempFeel}.${smellNote}${soundNote}`;
        } else {
            leadIn = `You are currently in the ${currentArea?.name || '(none)'}. It is ${lightFeel} and ${tempFeel}.${smellNote}`;
        }

        const preamble = buildCharacterPreamble(charName, player);

        const tickNum = window.VW?.state?.tick ?? 0;

        const bodyDesc = isBlind
            ? '(You cannot see the room. What you know of it comes only from sound, smell, and touch.)'
            : (currentArea?.description || '');
        const itemHeader = isBlind ? 'Things you\'ve touched or found:' : 'Items that catch your attention:';
        const noItemsLine = isBlind
            ? "Things you've located: none yet — try fumble or search."
            : "Items that catch your attention: (nothing you haven't already examined)";

        const body = `${bodyDesc}
${warn ? `\n${warn}` : ''}
${items ? `${itemHeader}\n` + items : noItemsLine}
${peopleStr}${exitsStr}${facingStr}${witnessedEvents ? `${witnessedEvents}` : ''}`;

        if (!agentFraming) {
            const envLine = `${currentArea?.name || 'Area'} — ${lightFeel}, ${tempFeel}.${smellNote}`;
            return { agentFraming: false, authoringText: `${envLine}\n\n${body.trim()}` };
        }

        const availableActions = PromptBuilder.buildAvailableActionsBlock(state, charName, player, currentArea);

        const itemsBlock = items ? `${itemHeader}\n` + items : noItemsLine;
        const roomBody = `${bodyDesc}${warn ? `\n${warn}` : ''}`;

return {
            agentFraming: true,
            tickHead: `[Tick ${tickNum}]`,
            preamble,
            appearance: equipStr,
            carrying: invStr,
            leadIn,
            roomBody,
            items: itemsBlock,
            people: peopleStr,
            exits: exitsStr,
            facing: facingStr,
            availableActions,
            witnessed: witnessedEvents || '',
            conversation: PromptBuilder.buildConversationInstinct(player, charName),
            plan: includePlan ? PromptBuilder.buildPlanContext(charName) : '',
        };
    }

    /**
     * Build the full area context string for a character — assembled from
     * buildRoomContextParts in the new section order (tick, personality,
     * appearance, carrying, room, exits, items, people, actions, witnessed,
     * plan). Used by standalone callers (human turns, narration, lens
     * previews); the agent turn-prompt builders use the parts directly so the
     * state/memory blocks can be inserted at the top.
     * @param {Object} state - Full world state data
     * @param {string} charName - Character name
     * @param {Object} player - Player data object
     * @param {Object} currentArea - Current area data object
     * @param {boolean|Object} [includePlanOrOptions=true] - boolean legacy flag, or
     *   `{ includePlan, agentFraming }`. When `agentFraming` is false (area/way/item
     *   lens), omits tick, personality, inventory, and plan — room content only.
     * @returns {string} Formatted area context string
     */
    function buildRoomContext(state: PromptState, charName: string, player: PlayerState,
                              currentArea: CurrentArea, includePlanOrOptions = true): string {
        const parts = buildRoomContextParts(state, charName, player, currentArea, includePlanOrOptions);
        if (!parts.agentFraming) return parts.authoringText;
        const blocks: Array<unknown> = [
            parts.tickHead,
            parts.preamble,
            parts.appearance,
            parts.carrying,
            parts.leadIn,
            parts.roomBody,
            parts.exits,
            parts.items,
            parts.people,
            parts.availableActions,
            parts.witnessed,
            parts.conversation,
            parts.plan,
        ];
        return blocks.map(block => String(block || '').trim()).filter(Boolean).join('\n\n');
    }

    /**
     * Build a narrated area context (async — may call the LLM for narration).
     * Falls back to the standard area context if narration mode is off.
     * @param {Object} state - Full world state data
     * @param {string} charName - Character name
     * @param {Object} player - Player data object
     * @param {Object} currentArea - Current area data object
     * @returns {Promise<string>} Narrated or standard area context string
     */
    async function buildNarratedRoomContext(state: PromptState, charName: string, player: PlayerState,
                                          currentArea: CurrentArea): Promise<string> {
        const narrationMode = narrationUi()?.getMode();
        let contextString = buildRoomContext(state, charName, player, currentArea);
        if (narrationMode && narrationMode !== 'none') {
            try {
                const items = (currentArea?.name ? worldState.getItemsInArea(currentArea.name) : []) as ItemNode[];
                const contextObject = { areaName: currentArea?.name || '', description: currentArea?.description || '', items: items.filter((item: ItemNode) => item.properties?.current_state !== 'hidden').map(item => item.name as string) || [], characters: state.players_in_area?.map(person => person.name).filter(name => name !== charName) || [], exits: Object.keys(viewerExitMap || {}).join(', ') };
                const narratedDescription = await narrationUi()!.getNarratedRoomContext(contextObject, charName);
                if (narratedDescription) { contextString = contextString.replace(/^Description: .*/m, `Description: ${narratedDescription}`); try { await apiClient().playerSpeak(charName, `*${narratedDescription}*`, currentArea?.name as string); } catch(innerError) {} }
            } catch(error) {}
        }
        return contextString;
    }


    Object.assign((window as unknown as PromptBuilderWindowSurface).PromptBuilder, {
        buildCharacterPreamble,
        buildRoomContext,
        buildRoomContextParts,
        buildNarratedRoomContext,
        viewerExits,
        characterKnown
    });
})();

// ---------------------------------------------------------------------------
// PRE-EXISTING DEFECT, PRESERVED DELIBERATELY.
//
// `buildNarratedRoomContext` references `viewerExitMap` at the exits: field of
// its contextObject, but the only declaration is a `const` inside
// `buildRoomContextParts` -- a different function. At runtime that is a
// ReferenceError, swallowed by the surrounding empty `catch`, so the narrated
// path silently never narrates. Verified present in the committed original,
// so it is not introduced by this conversion.
//
// It is NOT fixed here: making it work changes what a player sees, which is a
// product decision rather than a type-level one. This ambient declaration lets
// the pre-existing reference type-check; the inner `const` shadows it.
// ---------------------------------------------------------------------------
declare const viewerExitMap: Record<string, ExitEntry>;

/** ApiClient plus the one method this module calls. */
interface ApiClientWithSpeak {
    playerSpeak(charName: string, text: string, areaName: string): Promise<unknown>;
}

// ---------------------------------------------------------------------------
// Local types. Declared after the IIFE so the leading JSDoc block stays the
// first thing in the emitted .js and `@module` remains discoverable.
// ---------------------------------------------------------------------------

/** A memory entry, as the recall matcher and re-feel read it. */
interface MemoryEntry {
    id?: unknown;
    text?: string;
    memory_emotions?: MemoryEmotion[];
    emotion?: MemoryEmotion;
    [key: string]: unknown;
}

interface MemoryEmotion {
    label?: string;
    intensity?: unknown;
    [key: string]: unknown;
}

/** One heard line that may reference one of the listener's own memories. */
interface SocialSeed {
    text?: string;
    /** A known player name gates the relationship nudge; an anonymized voice
     *  label stays a pure re-feel. */
    speaker?: unknown;
    [key: string]: unknown;
}

interface PlayerState {
    personality?: string;
    description?: string;
    memories?: MemoryEntry[];
    traits?: Record<string, unknown>;
    /** Entity keys the player is authored/runtime-known by. */
    known?: unknown[];
    discovered_exits?: Array<[string, string]>;
    interest_tags?: unknown[];
    discovered_items?: unknown[];
    conditions?: Record<string, unknown>;
    recent_hearing?: HearingEntry[];
    [key: string]: unknown;
}

/** One authored way, as the prompt builders read it. */
interface ExitEntry {
    hidden?: boolean;
    way_id?: string;
    direction?: string;
    state?: string;
    target?: string;
    allow_see_characters?: boolean;
    visible_items?: unknown;
    [key: string]: unknown;
}

interface AreaEntry {
    name?: string;
    description?: string;
    exits?: Record<string, ExitEntry>;
    /** All ways regardless of discovery state; the prompt view rebuilds from
     *  this plus the viewer's own knowledge. */
    exits_authoring?: Record<string, ExitEntry>;
    [key: string]: unknown;
}

interface CurrentArea {
    name?: string;
    description?: string;
    exits?: Record<string, ExitEntry>;
    [key: string]: unknown;
}

/** One row of the per-area event ledger. */
interface TurnEvent {
    area?: string;
    actor?: string;
    action?: string;
    description?: string;
    tick?: number;
    [key: string]: unknown;
}

/** One entry of a character's rolling `recent_hearing` buffer. */
interface HearingEntry {
    type?: string;
    speaker?: string;
    text?: string;
    tick?: number;
    [key: string]: unknown;
}

/** Somebody present in the area, for the spatial-position suffix. */
interface PresenceInfo {
    at_way_id?: string;
    spatial_position?: { target_name?: string; relation?: string };
    [key: string]: unknown;
}

/** The subset of /api/state this module reads. */
interface PromptState {
    players?: Record<string, PlayerState>;
    areas?: Record<string, AreaEntry>;
    current_area?: string;
    players_in_area?: Array<{
        name: string;
        description?: string;
        activity?: string;
        state?: string;
    }>;
    /** Per-area ledger of when each character entered, so events before you
     *  arrived are never witnessed. */
    area_presence?: Record<string, Record<string, number>>;
    turn_events?: TurnEvent[];
    [key: string]: unknown;
}

interface GraphNode {
    id?: string;
    name?: string;
    type?: string;
    properties?: Record<string, any>;
    [key: string]: unknown;
}

interface ItemNode {
    id?: unknown;
    name?: string;
    /** Containment depth; only depth > 0 counts as "inside" something. */
    depth?: number;
    properties?: Record<string, any>;
    [key: string]: unknown;
}

/** The `{ includePlan, agentFraming, preview }` form of the legacy flag. */
interface RoomContextOptions {
    includePlan?: boolean;
    agentFraming?: boolean;
    preview?: boolean;
}

/** The block set buildRoomContextParts assembles, keyed on `agentFraming`.
 *  false means this is an authoring surface: only `authoringText` is set.
 *  true is the agent-facing branch, which carries the block set below. */
type RoomContextParts =
    | {
        agentFraming: false;
        authoringText: string;
      }
    | {
        agentFraming: true;
        tickHead: string;
        preamble: string;
        appearance: string;
        carrying: string;
        leadIn: string;
        roomBody: string;
        items: string;
        people: string;
        exits: string;
        facing: string;
        availableActions: unknown;
        witnessed: string;
        conversation: unknown;
        plan: string;
      };


/** The single method shared/emotion-mapper.js exposes on window. */
interface EmotionMapperApi {
    resolve(label: string): Promise<{ dimension?: string } | null>;
}

/** story-mode.js, as the narrated context path uses it. */
interface NarrationUiApi {
    getMode(): string | null | undefined;
    getNarratedRoomContext(context: unknown, charName: string): Promise<string | null>;
}

/** shared/item-containment.js: the one containment walk (task-493). */
interface ItemContainmentApi {
    collectReachable(roots: string[], graph: {
        getNode: (id: string) => GraphNode | null;
        edges: unknown[];
    }): ItemNode[];
}

/** embedding-client.js, as the recall matcher uses it. */
interface EmbeddingClientApi {
    configured(): boolean;
    embed(text: string): Promise<number[] | null>;
}

/** ApiClient plus the one method this module calls. */
interface ApiClientWithSpeak {
    playerSpeak(charName: string, text: string, areaName: string): Promise<unknown>;
}

// ---------------------------------------------------------------------------
// PRE-EXISTING DEFECT, PRESERVED DELIBERATELY.
//
// `buildNarratedRoomContext` references `viewerExitMap` at the exits: field of
// its contextObject, but the only declaration is a `const` inside
// `buildRoomContextParts` -- a different function. At runtime that is a
// ReferenceError, swallowed by the surrounding empty `catch`, so the narrated
// path silently never narrates. Verified present in the committed original
// (git HEAD), so it is not introduced by this conversion.
//
// It is NOT fixed here: making it work changes what a player sees, which is a
// product decision rather than a type-level one. This ambient declaration lets
// the pre-existing reference type-check; the inner `const` shadows it.
// ---------------------------------------------------------------------------
