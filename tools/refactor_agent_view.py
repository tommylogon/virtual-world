import re
import sys

path = "static/js/inspector/agent-view.ts"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

assert '\u2014' not in content and '—' not in content, "Em-dash in original file"

remaining_fixes = [
    (
"""        const areas = worldState.areas || {};
        let match = Object.keys(areas).find(a => a.toLowerCase() === val.toLowerCase());
        let destNode: *FIX* = null;
        if (worldState.graph?.nodes) {
            destNode = Object.values(worldState.graph.nodes).find(
                (n: *FIX*) => n.type === 'area' && (n.name?.toLowerCase() === val.toLowerCase() || n.id?.toLowerCase() === val.toLowerCase())
            );
            if (destNode && !match) match = destNode.name || destNode.id;
        }""",
"""        const areas = worldState.areas || {};
        let match = Object.keys(areas).find(a => a.toLowerCase() === val.toLowerCase());
        let destNode: Models.BaseNodeModel | null = null;
        if (worldState.graph?.nodes) {
            destNode = Object.values(worldState.graph.nodes).find(
                (n: Models.BaseNodeModel) => n.type === 'area' && (n.name?.toLowerCase() === val.toLowerCase() || n.id?.toLowerCase() === val.toLowerCase())
            ) || null;
            if (destNode && !match) match = destNode.name || destNode.id;
        }"""
    ),
    (
"""        const equipLines: string[] = [];
        for (const [slotName, items] of Object.entries(equipped as Record<string, *FIX*[]>)) {
            if (items && items.length > 0) {
                const realItems = items.filter((item: *FIX*) => item && !String(item).startsWith('__'));""",
"""        const equipLines: string[] = [];
        for (const [slotName, items] of Object.entries(equipped as Record<string, string[]>)) {
            if (items && items.length > 0) {
                const realItems = items.filter((item: string) => item && !String(item).startsWith('__'));"""
    ),
    (
"""        // Fallback: merge base_description + equipment client-side
        const slots: string[] = [];
        for (const [slotName, items] of Object.entries(equipped as Record<string, *FIX*[]>)) {
            if (items && items.length > 0) {
                const realItems = items.filter((item: *FIX*) => item && !String(item).startsWith('__'));""",
"""        // Fallback: merge base_description + equipment client-side
        const slots: string[] = [];
        for (const [slotName, items] of Object.entries(equipped as Record<string, string[]>)) {
            if (items && items.length > 0) {
                const realItems = items.filter((item: string) => item && !String(item).startsWith('__'));"""
    ),
    (
"""    AV._knownRecipeNames = function(charName: string, player: *FIX*): *FIX*[] {
        const state = worldState.data || {};
        const nodes = (state.graph?.nodes || {}) as Record<string, *FIX*>;
        const carriedNames = new Set();
        const graph = worldState.data?.graph || {};
        const pid = 'player_' + charName.replace(/\\s+/g, '_');
        for (const e of (graph.edges || [])) {
            if (e.target === pid && (e.type === 'carrying' || e.type === 'equipped')) {
                const n = worldState.getNode(e.source);
                if (n) carriedNames.add(String(n.name).toLowerCase());
            }
        }
        const known = (player.crafting_known || []).map(String);
        const out: *FIX*[] = [];""",
"""    AV._knownRecipeNames = function(charName: string, player: Models.PlayerRuntimeModel): string[] {
        const state = worldState.data || {};
        const nodes = (state.graph?.nodes || {}) as Record<string, Models.BaseNodeModel>;
        const carriedNames = new Set<string>();
        const graph = worldState.data?.graph || {};
        const pid = 'player_' + charName.replace(/\\s+/g, '_');
        for (const e of (graph.edges || [])) {
            if (e.target === pid && (e.type === 'carrying' || e.type === 'equipped')) {
                const n = worldState.getNode(e.source);
                if (n) carriedNames.add(String(n.name).toLowerCase());
            }
        }
        const known = (player.crafting_known || []).map(String);
        const out: string[] = [];"""
    ),
    (
"""        try {
            // Nothing chosen yet and no reason to propose *FIX*thing: just run the
            // deterministic path. Everything else goes to the modal first, so a
            // person sees the context the model read before *FIX*thing is worn.
            if (libraryIds) {
                const player = worldState.players?.[charName];
                const byId = new Map<string, *FIX*>(pool.map((c: *FIX*) => [c.lib_id, c]));
                const chosen = libraryIds.map(id => byId.get(id)).filter(Boolean);
                const worn: Record<string, *FIX*[]> = {};
                for (const [slot, stack] of Object.entries(player?.equipped || {})) {
                    const names = (Array.isArray(stack) ? stack : [])
                        .filter((i: *FIX*) => i && !String(i).startsWith('__'))
                        .map((i: *FIX*) => worldState.getNodeByIdentifier(i)?.name || i);
                    if (names.length) worn[slot] = names;
                }""",
"""        try {
            // Nothing chosen yet and no reason to propose anything: just run the
            // deterministic path. Everything else goes to the modal first, so a
            // person sees the context the model read before anything is worn.
            if (libraryIds) {
                const player = worldState.players?.[charName];
                const byId = new Map<string, { lib_id: string }>(pool.map((c: { lib_id: string }) => [c.lib_id, c]));
                const chosen = libraryIds.map(id => byId.get(id)).filter(Boolean);
                const worn: Record<string, string[]> = {};
                for (const [slot, stack] of Object.entries(player?.equipped || {})) {
                    const names = (Array.isArray(stack) ? stack : [])
                        .filter((i: string) => i && !String(i).startsWith('__'))
                        .map((i: string) => worldState.getNodeByIdentifier(i)?.name || i);
                    if (names.length) worn[slot] = names;
                }"""
    ),
    (
"""    AV._resolveConcept = function(concept: string, vocab: { live: Set<string>; library: Set<string>; known: Set<string> }): *FIX*[] {
        const words = String(concept ?? '').trim().toLowerCase().split(/[\\s/]+/).filter(Boolean);
        if (!words.length) return [];
        const found: *FIX*[] = [];""",
"""    AV._resolveConcept = function(concept: string, vocab: { live: Set<string>; library: Set<string>; known: Set<string> }): Array<{ id: string; status: 'live' | 'library' | 'new'; via: string }> {
        const words = String(concept ?? '').trim().toLowerCase().split(/[\\s/]+/).filter(Boolean);
        if (!words.length) return [];
        const found: Array<{ id: string; status: 'live' | 'library' | 'new'; via: string }> = [];"""
    ),
    (
"""            // arrives twice.
            const resolved: *FIX*[] = [];
            for (const concept of concepts) {
                for (const hit of AV._resolveConcept(concept, vocab)) {
                    const seen = resolved.find((r: *FIX*) => r.id === hit.id);
                    if (seen) { if (hit.status === 'live') seen.status = 'live'; continue; }
                    resolved.push(hit);
                }
            }""",
"""            // arrives twice.
            const resolved: Array<{ id: string; status: 'live' | 'library' | 'new'; via: string }> = [];
            for (const concept of concepts) {
                for (const hit of AV._resolveConcept(concept, vocab)) {
                    const seen = resolved.find((r: { id: string; status: 'live' | 'library' | 'new'; via: string }) => r.id === hit.id);
                    if (seen) { if (hit.status === 'live') seen.status = 'live'; continue; }
                    resolved.push(hit);
                }
            }"""
    ),
    (
"""            conditions: player.conditions || {},
            equipped: (() => {
                const eq: Record<string, *FIX*[]> = {};
                for (const [slot, stack] of Object.entries(player.equipped || {})) {
                    eq[slot] = (Array.isArray(stack) ? stack : []).map((id: *FIX*) => {""",
"""            conditions: player.conditions || {},
            equipped: (() => {
                const eq: Record<string, Array<{ name: string; node_id: string; library_id: string | null; properties: Record<string, unknown> }>> = {};
                for (const [slot, stack] of Object.entries(player.equipped || {})) {
                    eq[slot] = (Array.isArray(stack) ? stack : []).map((id: string) => {"""
    )
]

applied = 0
for src, dst in remaining_fixes:
    if src in content:
        content = content.replace(src, dst)
        applied += 1
    else:
        print(f"FAILED TO FIND:\n{src[:100]}...")

print(f"Applied {applied}/{len(remaining_fixes)} remaining replacements.")
remaining = content.count("*FIX*")
print(f"Remaining *FIX* markers: {remaining}")

assert '\u2014' not in content and '—' not in content, "Em-dash introduced!"

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Saved agent-view.ts successfully.")
