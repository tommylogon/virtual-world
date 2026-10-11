"use strict";
/**
 * world-export.js — World export, print, and clipboard utility module
 * Extracted from main.js. Provides WorldExport singleton.
 *
 * Dependencies:
 *   - worldState (WorldState)
 *   - window.events (EventBus)
 *   - window.llmClient (LLMClient)
 *   - window.api / window.ApiClient
 *   - Global: toastInfo, toastError (from ui-helpers.js)
 *   - DOM elements: #event-stream, #manual-prompt-content, etc.
 *
 * @module ui/world-export — export, print, and clipboard utilities
 * @contributes WorldExport: save-file dialog/downloads, world JSON export, prompt copying, print
 * @powers Export — getting data out of the app (extracted from main.js)
 * @relates uses worldState + api + events; used by saveload-view's downloadWorld
 * @docs docs/virtualWorld/UI & Settings/Event Log Export.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
window.WorldExport = (() => {
    'use strict';
    /**
     * Save a Blob to disk using the native Save As dialog (Chromium) or a fallback <a> download.
     * @param {Blob} blob - The file content as a Blob
     * @param {string} suggestedName - The suggested file name
     */
    async function saveFileWithDialog(blob, suggestedName) {
        if ('showSaveFilePicker' in window) {
            try {
                var ext = suggestedName.split('.').pop();
                var mime = ext === 'txt' ? 'text/plain' : ext === 'png' ? 'image/png' : 'application/json';
                var typeName = ext === 'txt' ? 'Text File' : ext === 'png' ? 'PNG Image' : 'JSON File';
                var accept = {};
                accept[mime] = ['.' + ext];
                var handle = await window.showSaveFilePicker({
                    suggestedName: suggestedName,
                    types: [{
                            description: typeName,
                            accept: accept
                        }]
                });
                var writable = await handle.createWritable();
                await writable.write(blob);
                await writable.close();
                return;
            }
            catch (e) {
                if (e instanceof Error && e.name === 'AbortError')
                    return; // user cancelled
            }
        }
        // Fallback: <a download> for non-Chromium browsers
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = suggestedName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    }
    /**
     * Generate a full plain-text summary of the current world state and open it
     * in a new window for printing.
     */
    function printWorld() {
        var world = worldState.data;
        if (!world)
            return toastInfo('No world data loaded.');
        var text = '========================================\n';
        text += '       VIRTUAL WORLD - WORLD SUMMARY\n';
        text += '========================================\n\n';
        // World info
        var roomNames = Object.keys(world.areas || {});
        text += 'Total Rooms: ' + roomNames.length + '\n';
        text += 'Total Characters: ' + Object.keys(world.players || {}).length + '\n';
        text += 'Tick: ' + (world.tick || 0) + '\n\n';
        // ── Characters ──
        text += '═══════════════════════════════════════\n';
        text += 'CHARACTERS\n';
        text += '═══════════════════════════════════════\n';
        for (var charName in world.players) {
            if (!world.players.hasOwnProperty(charName))
                continue;
            var player = world.players[charName];
            text += '\n  ' + charName + ' (' + (player.state || '?') + ')\n';
            text += '  📍 Area: ' + (player.current_area || '?') + '\n';
            if (player.personality)
                text += '  🧠 Personality: ' + player.personality + '\n';
            if (player.description)
                text += '  👤 Description: ' + player.description + '\n';
            if (player.emotion?.current)
                text += '  😶 Emotion: ' + player.emotion.current + ' (' + (player.emotion.intensity || 0) + '/10)\n';
            if (player.stats) {
                var stats = player.stats;
                text += '  📊 Stats: STR ' + (stats.STR || 0) + ' DEX ' + (stats.DEX || 0) + ' CON ' + (stats.CON || 0) + ' INT ' + (stats.INT || 0) + ' WIS ' + (stats.WIS || 0) + ' CHA ' + (stats.CHA || 0) + '\n';
            }
            if (player.vitals) {
                var vitals = player.vitals;
                text += '  ❤️ HP: ' + (vitals.HP || 0) + '/' + (vitals.Max_HP || 0) + '  ⚡ Energy: ' + (vitals.Energy || 0) + '  🧠 Sanity: ' + (vitals.Sanity || 0) + '\n';
                text += '     Hunger: ' + (vitals.Hunger || 0) + ' Thirst: ' + (vitals.Thirst || 0) + ' Temp: ' + (vitals.Temperature || 0) + '°C\n';
            }
            if (player.skills && Object.keys(player.skills).length) {
                text += '  🎯 Skills: ' + Object.entries(player.skills).map(function (kv) { return kv[0] + '(' + kv[1] + ')'; }).join(', ') + '\n';
            }
            if (player.traits && Object.keys(player.traits).length) {
                text += '  🏷️ Traits: ' + Object.keys(player.traits).join(', ') + '\n';
            }
            // task-632: player.inventory was hardcoded to [] in Player.to_dict, so every
            // export claimed the character carried nothing. Inventory is
            // graph-derived (carrying/equipped edges), not a Player field --
            // read it from worldState, which already resolves display names.
            var inv = (typeof worldState !== 'undefined' && worldState.getInventory)
                ? (worldState.getInventory(charName) || [])
                : (player.inventory || []);
            if (inv.length) {
                text += '  🎒 Inventory: ' + inv.join(', ') + '\n';
            }
            if (player.behaviors && player.behaviors.length) {
                text += '  🔄 Behaviors: ' + player.behaviors.map(function (b) { return b.name || b.type || b; }).join(', ') + '\n';
            }
        }
        // ── Rooms ──
        text += '\n═══════════════════════════════════════\n';
        text += 'ROOMS\n';
        text += '═══════════════════════════════════════\n';
        var sortedRoomNames = roomNames.sort();
        for (var ri = 0; ri < sortedRoomNames.length; ri++) {
            var areaName = sortedRoomNames[ri];
            var area = world.areas[areaName];
            // `floor` is a storey index (0 ground, 1 up, -1 down, unbounded) and
            // `surface` is the ground material — printing "Floor 0" on every room
            // is noise, so only a non-ground storey is called out.
            var areaFloor = Number(area.floor);
            var floorText = '';
            if (Number.isFinite(areaFloor) && Math.round(areaFloor) !== 0) {
                floorText = (areaFloor > 0 ? ' (Floor ' + Math.round(areaFloor) + ')'
                    : ' (Floor ' + Math.round(areaFloor) + ', below ground)');
            }
            else if (area.surface) {
                floorText = ' (' + area.surface + ')';
            }
            text += '\n  ■ ' + areaName + floorText + '\n';
            if (area.description)
                text += '  "' + area.description + '"\n';
            if (area.environment) {
                var env = area.environment;
                var envTemp = (env.temperature !== undefined && env.temperature !== null) ? (Math.round(Number(env.temperature) * 10) / 10) : '?';
                text += '  🌡️ Light: ' + (env.light || '?') + '  Temp: ' + envTemp + '°C  Air: ' + (env.air || '?') + '  Noise: ' + (env.noise || '?') + '  Smell: ' + (env.smell || '?') + '\n';
            }
            // Exits
            if (area.exits && Object.keys(area.exits).length) {
                text += '  🚪 Exits:\n';
                for (var dir in area.exits) {
                    if (!area.exits.hasOwnProperty(dir))
                        continue;
                    var exitData = area.exits[dir];
                    var target = typeof exitData === 'object' ? (exitData.targetAreaName || exitData.target || '?') : exitData;
                    var wayId = exitData.way_id || '';
                    var wayState = exitData.state || '';
                    text += '    ' + dir + ' → ' + target + (wayId ? ' [' + wayId + ']' : '') + (wayState ? ' (' + wayState + ')' : '') + '\n';
                }
            }
            // Items in area (from graph)
            var graphItems = worldState.getItemsInArea(areaName);
            if (graphItems.length > 0) {
                text += '  📦 Items:\n';
                for (var ii = 0; ii < graphItems.length; ii++) {
                    var item = graphItems[ii];
                    var desc = item.properties?.description || '';
                    var state = item.properties?.current_state || 'normal';
                    var hidden = item.properties?.current_state === 'hidden' ? ' [HIDDEN]' : '';
                    var locked = item.properties?.current_state === 'locked' ? ' 🔒' : '';
                    text += '    • ' + item.name + locked + hidden + ' (' + state + ')' + (desc ? ': ' + desc : '') + '\n';
                }
            }
            // Players in this area
            var presentPlayers = [];
            for (var pn in world.players) {
                if (world.players.hasOwnProperty(pn) && world.players[pn].current_area === areaName) {
                    presentPlayers.push(pn);
                }
            }
            if (presentPlayers.length) {
                text += '  👤 Present: ' + presentPlayers.join(', ') + '\n';
            }
        }
        // ── Doors ──
        var doorNodes = [];
        for (var nodeId in world.graph?.nodes || {}) {
            if (world.graph.nodes.hasOwnProperty(nodeId) && world.graph.nodes[nodeId].type === 'way') {
                doorNodes.push([nodeId, world.graph.nodes[nodeId]]);
            }
        }
        if (doorNodes.length) {
            text += '\n═══════════════════════════════════════\n';
            text += 'DOORS\n';
            text += '═══════════════════════════════════════\n';
            for (var di = 0; di < doorNodes.length; di++) {
                var doorEntry = doorNodes[di];
                var doorProps = doorEntry[1].properties || {};
                text += '  🚪 ' + doorEntry[1].name + ' (' + (doorProps.current_state || 'closed') + ')\n';
                if (doorProps.description)
                    text += '     ' + doorProps.description + '\n';
            }
        }
        // ── Other Graph Nodes (items not in rooms, triggers, etc.) ──
        var printedDoorIds = {};
        for (var pi = 0; pi < doorNodes.length; pi++) {
            printedDoorIds[doorNodes[pi][0]] = true;
        }
        var otherNodes = [];
        for (var ni in world.graph?.nodes || {}) {
            if (!world.graph.nodes.hasOwnProperty(ni))
                continue;
            var node = world.graph.nodes[ni];
            if (node.type !== 'area' && node.type !== 'character' && !printedDoorIds[ni]) {
                otherNodes.push([ni, node]);
            }
        }
        if (otherNodes.length) {
            text += '\n═══════════════════════════════════════\n';
            text += 'OTHER NODES\n';
            text += '═══════════════════════════════════════\n';
            for (var oi = 0; oi < otherNodes.length; oi++) {
                var otherEntry = otherNodes[oi];
                var otherNode = otherEntry[1];
                var otherProps = otherNode.properties || {};
                var nodeState = otherProps.current_state || '';
                text += '  [' + otherNode.type + '] ' + otherNode.name + (nodeState ? ' (' + nodeState + ')' : '') + '\n';
                if (otherProps.description)
                    text += '     ' + otherProps.description + '\n';
                if (otherNode.type === 'item') {
                    // Find location edge
                    var locationTarget = '';
                    for (var ei = 0; ei < (world.graph?.edges || []).length; ei++) {
                        var edgeEntry = world.graph.edges[ei];
                        if (edgeEntry.source === otherEntry[0] && edgeEntry.type === 'in') {
                            locationTarget = edgeEntry.target;
                            break;
                        }
                    }
                    if (locationTarget)
                        text += '     📍 ' + locationTarget + '\n';
                }
                if (otherNode.type === 'logic_trigger' && otherProps.trigger_type) {
                    text += '     ⚡ ' + otherProps.trigger_type + ' → ' + (otherProps.effect_type || '?') + '\n';
                }
            }
        }
        // ── All Edges ──
        var edges = world.graph?.edges || [];
        if (edges.length) {
            text += '\n═══════════════════════════════════════\n';
            text += 'GRAPH EDGES\n';
            text += '═══════════════════════════════════════\n';
            for (var ei2 = 0; ei2 < edges.length; ei2++) {
                var edge = edges[ei2];
                var label = edge.label || edge.type || 'connection';
                text += '  ' + edge.source + ' --[' + label + ']--> ' + edge.target + '\n';
            }
        }
        // ── Lore ──
        var lore = world.world_lore || [];
        if (lore.length) {
            text += '\n═══════════════════════════════════════\n';
            text += 'WORLD LORE\n';
            text += '═══════════════════════════════════════\n';
            for (var li = 0; li < lore.length; li++) {
                var entry = lore[li];
                text += '\n  [' + (entry.category || 'general') + '] ' + entry.title + '\n';
                text += '  ' + entry.content + '\n';
            }
        }
        text += '\n═══════════════════════════════════════\n';
        text += 'Generated: ' + new Date().toLocaleString() + '\n';
        text += '═══════════════════════════════════════\n';
        // Open in new window for printing
        var printWin = window.open('', '_blank');
        if (!printWin)
            return;
        printWin.document.write('<!DOCTYPE html><html><head><meta charset="utf-8"><title>World Summary</title><style>'
            + 'body { font-family: \'Courier New\', monospace; font-size: 11px; line-height: 1.4; white-space: pre-wrap; padding: 20px; color: #000; background: #fff; }'
            + '@media print { body { font-size: 9px; padding: 10px; } }'
            + '</style></head><body>' + text.replace(/\n/g, '<br>').replace(/  /g, '&nbsp;&nbsp;') + '</body></html>');
        printWin.document.close();
        printWin.focus();
        if (window.chrome?.runtime) {
            setTimeout(function () { printWin.print(); }, 500);
        }
    }
    // ── Event-log export (task-777): the row projection, the four renderers and
    // the consolidated modal now live in ui/event-log-export.js. These entry
    // points keep the WorldExport surface stable for the three inline buttons. ──
    /** Open the consolidated export modal, pre-set to the whole log → file. */
    function exportEventLog() {
        const lex = window.EventLogExport;
        if (lex && lex.exportEventLog)
            lex.exportEventLog();
    }
    /** Open the consolidated export modal, pre-set to the whole log → clipboard. */
    function copyEventLogToClipboard() {
        const lex = window.EventLogExport;
        return lex && lex.copyEventLogToClipboard ? lex.copyEventLogToClipboard() : undefined;
    }
    /** Open the consolidated export modal, focusing the range controls. */
    function showRangeExport() {
        const lex = window.EventLogExport;
        if (lex && lex.showRangeExport)
            lex.showRangeExport();
    }
    /** Legacy turn-range renderer — delegates to the extracted module. */
    function buildRangeLog(scenarioName, fromTurn, toTurn, ts, format) {
        const lex = window.EventLogExport;
        if (lex && lex.buildRangeLog)
            return lex.buildRangeLog(scenarioName, fromTurn, toTurn, ts, format);
        return { error: 'Event-log export module not loaded.' };
    }
    /**
     * Copy the last LLM prompt to the clipboard.
     */
    async function copyPromptToClipboard() {
        var promptText = llmClient.getLastPrompt();
        if (!promptText) {
            events.log('⚠️ No prompt captured yet. Run an agent step first.', 'system-msg');
            return;
        }
        try {
            await navigator.clipboard.writeText(promptText);
            events.log('📋 Prompt copied to clipboard! (' + promptText.length + ' chars)', 'system-msg');
        }
        catch (e) {
            // Fallback for non-HTTPS
            var ta = document.createElement('textarea');
            ta.value = promptText;
            ta.style.position = 'fixed';
            ta.style.left = '-9999px';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            events.log('📋 Prompt copied to clipboard! (' + promptText.length + ' chars)', 'system-msg');
        }
    }
    /**
     * Copy the manual prompt content from the manual-prompt modal to the clipboard.
     */
    function copyManualPrompt() {
        var contentEl = document.getElementById('manual-prompt-content');
        var text = contentEl?.textContent || '';
        if (!text)
            return;
        try {
            navigator.clipboard.writeText(text);
        }
        catch (e) {
            var ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.left = '-9999px';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
        }
        events.log('📋 Prompt copied to clipboard! (' + text.length + ' chars)', 'system-msg');
    }
    return {
        saveFileWithDialog: saveFileWithDialog,
        printWorld: printWorld,
        exportEventLog: exportEventLog,
        copyEventLogToClipboard: copyEventLogToClipboard,
        showRangeExport: showRangeExport,
        buildRangeLog: buildRangeLog,
        copyPromptToClipboard: copyPromptToClipboard,
        copyManualPrompt: copyManualPrompt
    };
})();
