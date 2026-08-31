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
 */

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
                var mime = ext === 'txt' ? 'text/plain' : 'application/json';
                var handle = await window.showSaveFilePicker({
                    suggestedName: suggestedName,
                    types: [{
                        description: ext === 'txt' ? 'Text File' : 'JSON File',
                        accept: (function() { var obj = {}; obj[mime] = ['.' + ext]; return obj; })()
                    }]
                });
                var writable = await handle.createWritable();
                await writable.write(blob);
                await writable.close();
                return;
            } catch (e) {
                if (e.name === 'AbortError') return; // user cancelled
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
        setTimeout(function() { URL.revokeObjectURL(url); }, 1000);
    }

    /**
     * Generate a full plain-text summary of the current world state and open it
     * in a new window for printing.
     */
    function printWorld() {
        var world = worldState.data;
        if (!world) return toastInfo('No world data loaded.');

        var text = '========================================\n';
        text +=    '       VIRTUAL WORLD - WORLD SUMMARY\n';
        text +=    '========================================\n\n';

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
            if (!world.players.hasOwnProperty(charName)) continue;
            var player = world.players[charName];
            text += '\n  ' + charName + ' (' + (player.state || '?') + ')\n';
            text += '  📍 Area: ' + (player.current_area || '?') + '\n';
            if (player.personality) text += '  🧠 Personality: ' + player.personality + '\n';
            if (player.description) text += '  👤 Description: ' + player.description + '\n';
            if (player.emotion?.current) text += '  😶 Emotion: ' + player.emotion.current + ' (' + (player.emotion.intensity || 0) + '/10)\n';
            if (player.stats) {
                var stats = player.stats;
                text += '  📊 Stats: STR ' + (stats.STR||0) + ' DEX ' + (stats.DEX||0) + ' CON ' + (stats.CON||0) + ' INT ' + (stats.INT||0) + ' WIS ' + (stats.WIS||0) + ' CHA ' + (stats.CHA||0) + '\n';
            }
            if (player.vitals) {
                var vitals = player.vitals;
                text += '  ❤️ HP: ' + (vitals.HP||0) + '/' + (vitals.Max_HP||0) + '  ⚡ Energy: ' + (vitals.Energy||0) + '  🧠 Sanity: ' + (vitals.Sanity||0) + '\n';
                text += '     Hunger: ' + (vitals.Hunger||0) + ' Thirst: ' + (vitals.Thirst||0) + ' Temp: ' + (vitals.Temperature||0) + '°C\n';
            }
            if (player.skills && Object.keys(player.skills).length) {
                text += '  🎯 Skills: ' + Object.entries(player.skills).map(function(kv) { return kv[0] + '(' + kv[1] + ')'; }).join(', ') + '\n';
            }
            if (player.traits && Object.keys(player.traits).length) {
                text += '  🏷️ Traits: ' + Object.keys(player.traits).join(', ') + '\n';
            }
            if (player.inventory && player.inventory.length) {
                text += '  🎒 Inventory: ' + player.inventory.join(', ') + '\n';
            }
            if (player.behaviors && player.behaviors.length) {
                text += '  🔄 Behaviors: ' + player.behaviors.map(function(b) { return b.name || b.type || b; }).join(', ') + '\n';
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
            text += '\n  ■ ' + areaName + (area.floor !== undefined ? ' (Floor ' + area.floor + ')' : '') + '\n';
            if (area.description) text += '  "' + area.description + '"\n';
            if (area.environment) {
                var env = area.environment;
                var envTemp = (env.temperature !== undefined && env.temperature !== null) ? (Math.round(Number(env.temperature) * 10) / 10) : '?';
                text += '  🌡️ Light: ' + (env.light||'?') + '  Temp: ' + envTemp + '°C  Air: ' + (env.air||'?') + '  Noise: ' + (env.noise||'?') + '  Smell: ' + (env.smell||'?') + '\n';
            }
            // Exits
            if (area.exits && Object.keys(area.exits).length) {
                text += '  🚪 Exits:\n';
                for (var dir in area.exits) {
                    if (!area.exits.hasOwnProperty(dir)) continue;
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
                if (doorProps.description) text += '     ' + doorProps.description + '\n';
            }
        }

        // ── Other Graph Nodes (items not in rooms, triggers, etc.) ──
        var printedDoorIds = {};
        for (var pi = 0; pi < doorNodes.length; pi++) {
            printedDoorIds[doorNodes[pi][0]] = true;
        }
        var otherNodes = [];
        for (var ni in world.graph?.nodes || {}) {
            if (!world.graph.nodes.hasOwnProperty(ni)) continue;
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
                if (otherProps.description) text += '     ' + otherProps.description + '\n';
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
                    if (locationTarget) text += '     📍 ' + locationTarget + '\n';
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
        printWin.document.write('<!DOCTYPE html><html><head><meta charset="utf-8"><title>World Summary</title><style>'
            + 'body { font-family: \'Courier New\', monospace; font-size: 11px; line-height: 1.4; white-space: pre-wrap; padding: 20px; color: #000; background: #fff; }'
            + '@media print { body { font-size: 9px; padding: 10px; } }'
            + '</style></head><body>' + text.replace(/\n/g, '<br>').replace(/  /g, '&nbsp;&nbsp;') + '</body></html>');
        printWin.document.close();
        printWin.focus();
        if (window.chrome?.runtime) setTimeout(function() { printWin.print(); }, 500);
    }

    /**
     * Export the visible event stream as a text file.
     */
    function exportEventLog() {
        var streamEl = document.getElementById('event-stream');
        if (!streamEl) return;

        var scenarioName = (document.body.dataset.scenarioName || 'unnamed').trim() || 'unnamed';
        var ts = new Date().toISOString().slice(0, 19).replace(/:/g, '-');

        // Each stream row is labelled with a "[Tick N]" event-sequence id (a
        // global line counter) — NOT the world clock (time_ticks, per-turn).
        // Pick the highest sequence present so the filename tracks the log's
        // own numbering; fall back to the world clock if none are found.
        var maxTick = 0;
        var tickRe = /\[\s*Tick\s+(\d+)\s*\|/;
        var tickSpans = streamEl.querySelectorAll('.bubble-tick');
        for (var i = 0; i < tickSpans.length; i++) {
            var m = (tickSpans[i].textContent || '').match(tickRe);
            if (m) maxTick = Math.max(maxTick, parseInt(m[1], 10));
        }
        if (!maxTick) maxTick = worldState.tick || 0;

        var filename = scenarioName + '_tick_' + maxTick + '_event_log_' + ts + '.md';
        var content = buildMarkdownLog(scenarioName, maxTick, ts, streamEl);
        var blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
        saveFileWithDialog(blob, filename);
        events.log('📥 Event log exported (Markdown).', 'system-msg');
    }

    /**
     * Render the event stream into a tidy Markdown file. Walks the actual
     * bubbles (not element.textContent of whole turn cards, which would keep
     * filter-hidden rows like raw-LLM chips), skipping any row hidden by a
     * visibility filter, groups rows under their world-turn ("Turn N") heading,
     * and emits each remaining event as its own bullet with newlines intact.
     */
    function buildMarkdownLog(scenarioName, maxTick, ts, streamEl) {
        var buf = '';
        var openHeading = '';
        var lastTurn = 0;

        function emitBubble(bubble) {
            if (!bubble || bubble.style.display === 'none') return;
            // Raw-LLM chips: the stream FILTERS decide what gets exported (any
            // chip hidden by a filter already returned above). A VISIBLE raw-LLM
            // chip's full payload is included — header line + the complete
            // prompt/response body — so enabling the LLM filter restores the old
            // "full logs in the export" behavior instead of a header-only note.
            if (bubble.classList.contains('msg-bubble-rawllm')) {
                var headEl = bubble.querySelector('.rawllm-chip-header');
                var head = headEl ? headEl.textContent.trim() : 'LLM request/response';
                var line = '- _' + head + '_\n';
                var bodyEl = bubble.querySelector('.rawllm-chip-body');
                var body = bodyEl ? (bodyEl.textContent || '').trim() : '';
                if (body) {
                    line += '  <details><summary>payload</summary>\n\n  ```text\n'
                        + body.split('\n').map(function (l) { return '  ' + l; }).join('\n')
                        + '\n  ```\n  </details>\n';
                }
                buf += line;
                return;
            }
            var textEl = bubble.querySelector('.bubble-text')
                || bubble.querySelector('.bubble-phase-pill');
            var text = (textEl ? textEl.textContent : bubble.textContent || '') || '';
            text = text.replace(/^\s+/, '').trim();
            if (!text) return;
            var iconEl = bubble.querySelector('.bubble-icon');
            var actorEl = bubble.querySelector('.bubble-actor');
            var icon = iconEl ? iconEl.textContent.trim() : '';
            var actor = actorEl ? actorEl.textContent.trim() : (bubble.getAttribute('data-actor') || '');
            var line = '';
            if (icon) line += icon + ' ';
            if (actor) line += '**' + actor + '** — ';
            buf += '- ' + line + text + '\n';
        }

        function heading(title) {
            if (title === openHeading) return;
            buf += '\n## ' + title + '\n\n';
            openHeading = title;
        }

        for (var i = 0; i < streamEl.children.length; i++) {
            var child = streamEl.children[i];
            if (!child || child.style.display === 'none') continue;

            var cardHeader = child.querySelector('.turn-card-header');
            var cardBody = child.querySelector('.turn-card-body');
            if (cardHeader && cardBody) {
                var turn = 0, time = '';
                var turnEl = child.querySelector('.turn-card-tick');
                if (turnEl) {
                    var tm = (turnEl.textContent || '').match(/Turn\s+(\d+)(?:\s*\|\s*([^)]*))?/);
                    if (tm) {
                        turn = parseInt(tm[1], 10) || 0;
                        time = (tm[2] || '').trim();
                    }
                }
                if (turn > lastTurn) lastTurn = turn;
                var actorEl = child.querySelector('.turn-card-actor');
                var actor = actorEl ? actorEl.textContent.trim() : '';
                heading('Turn ' + turn + (actor ? ' — ' + actor : '') + (time ? ' · ' + time : ''));
                var bubbles = cardBody.querySelectorAll('.msg-bubble');
                for (var b = 0; b < bubbles.length; b++) emitBubble(bubbles[b]);
            } else {
                // System rows / area transitions that sit directly in the stream.
                if (!openHeading) heading('Setup');
                emitBubble(child);
            }
        }

        var header = '# ' + scenarioName + ' — event log\n\n'
            + '> Run tick ' + maxTick + ' · final turn ' + (lastTurn || '?') + ' · exported ' + ts + '\n\n';
        return header + buf;
    }

    /**
     * Copy the visible event stream text to the clipboard.
     */
    async function copyEventLogToClipboard() {
        var streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        // Clipboard now emits the SAME Markdown as the file download (task: export
        // parity), so copying paste straight into an editor is a clean log.
        var scenarioName = (document.body.dataset.scenarioName || 'unnamed').trim() || 'unnamed';
        var ts = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
        var content = buildMarkdownLog(scenarioName, worldState.tick || 0, ts, streamEl);
        try {
            await navigator.clipboard.writeText(content);
            events.log('📋 Event stream copied to clipboard! (' + content.length + ' chars)', 'system-msg');
        } catch (e) {
            var ta = document.createElement('textarea');
            ta.value = content;
            ta.style.position = 'fixed';
            ta.style.left = '-9999px';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            events.log('📋 Event stream copied to clipboard! (' + content.length + ' chars)', 'system-msg');
        }
    }

    // ───────────────────────── Turn-range export (new) ─────────────────────────

    /** Range bounds present in the stream: {min, max} world turns (or nulls). */
    function rangeBounds() {
        var streamEl = document.getElementById('event-stream');
        var min = Infinity, max = -Infinity, found = false;
        if (streamEl) {
            streamEl.querySelectorAll('.turn-card-tick').forEach(function (el) {
                var m = (el.textContent || '').match(/Turn\s+(\d+)/);
                if (m) {
                    var t = parseInt(m[1], 10) || 0;
                    found = true;
                    if (t < min) min = t;
                    if (t > max) max = t;
                }
            });
        }
        return found ? { min: min, max: max } : null;
    }

    /**
     * Build a log for turns [fromTurn, toTurn] (inclusive). format:
     * 'markdown' (same as the full export) or 'plain' (bare lines).
     */
    function buildRangeLog(scenarioName, fromTurn, toTurn, ts, format) {
        var streamEl = document.getElementById('event-stream');
        if (!streamEl) return { error: 'Event stream not found.' };
        var plain = format === 'plain';
        var buf = '';
        var openHeading = '';
        var lastTurn = 0;
        var included = 0;

        function emitBubble(bubble) {
            if (!bubble || bubble.style.display === 'none') return;
            var textEl = bubble.querySelector('.bubble-text') || bubble.querySelector('.bubble-phase-pill');
            var text = (textEl ? textEl.textContent : bubble.textContent || '') || '';
            text = text.replace(/^\s+/, '').trim();
            if (!text) return;
            var iconEl = bubble.querySelector('.bubble-icon');
            var actorEl = bubble.querySelector('.bubble-actor');
            var icon = iconEl ? iconEl.textContent.trim() : '';
            var actor = actorEl ? actorEl.textContent.trim() : (bubble.getAttribute('data-actor') || '');
            if (plain) {
                buf += (actor ? '[' + actor + '] ' : '') + text + '\n';
            } else {
                var line = '';
                if (icon) line += icon + ' ';
                if (actor) line += '**' + actor + '** — ';
                buf += '- ' + line + text + '\n';
            }
        }

        function heading(title) {
            if (plain) { buf += '\n' + title + '\n' + (new Array(title.length + 1).join('—')) + '\n'; }
            else if (title !== openHeading) { buf += '\n## ' + title + '\n\n'; openHeading = title; }
        }

        for (var i = 0; i < streamEl.children.length; i++) {
            var child = streamEl.children[i];
            if (!child || child.style.display === 'none') continue;
            var cardHeader = child.querySelector('.turn-card-header');
            var cardBody = child.querySelector('.turn-card-body');
            if (cardHeader && cardBody) {
                var turn = 0, time = '';
                var turnEl = child.querySelector('.turn-card-tick');
                if (turnEl) {
                    var tm = (turnEl.textContent || '').match(/Turn\s+(\d+)(?:\s*\|\s*([^)]*))?/);
                    if (tm) { turn = parseInt(tm[1], 10) || 0; time = (tm[2] || '').trim(); }
                }
                if (turn < fromTurn || turn > toTurn) continue;
                lastTurn = Math.max(lastTurn, turn);
                var actorEl = child.querySelector('.turn-card-actor');
                var actor = actorEl ? actorEl.textContent.trim() : '';
                heading('Turn ' + turn + (actor ? ' — ' + actor : '') + (time ? ' · ' + time : ''));
                var bubbles = cardBody.querySelectorAll('.msg-bubble');
                for (var b = 0; b < bubbles.length; b++) emitBubble(bubbles[b]);
                included += 1;
            } else if (included > 0) {
                emitBubble(child); // system rows after the first included card
            }
        }

        if (!included) return { error: 'No turns in range ' + fromTurn + '–' + toTurn + '.' };
        var header = (plain ? '' : '# ' + scenarioName + ' — event log (turns ' + fromTurn + '–' + toTurn + ')\n\n')
            + (plain ? '' : '> Run tick ' + (worldState.tick || 0) + ' · exported ' + ts + '\n\n');
        return { text: header + buf, turns: included };
    }

    /**
     * Range modal: from-to turn picker with Copy / Save. Opens from the
     * ⏩ stream button.
     */
    function showRangeExport() {
        var overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:15000;';
        var box = document.createElement('div');
        box.style.cssText = 'background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:18px;width:380px;display:flex;flex-direction:column;gap:10px;';
        overlay.appendChild(box);
        document.body.appendChild(overlay);

        var bounds = rangeBounds();
        var fromInput = document.createElement('input');
        fromInput.type = 'number';
        fromInput.min = '0';
        fromInput.value = bounds ? bounds.min : '0';
        fromInput.placeholder = 'from turn';
        var toInput = document.createElement('input');
        toInput.type = 'number';
        toInput.min = '0';
        toInput.value = bounds ? bounds.max : '';
        toInput.placeholder = 'to turn (blank = latest)';
        var formatSel = document.createElement('select');
        ['markdown', 'plain'].forEach(function (f) {
            var o = document.createElement('option');
            o.value = f; o.textContent = f === 'markdown' ? 'Markdown (like full export)' : 'Plain lines';
            formatSel.appendChild(o);
        });

        function build() { return buildRangeLog(
            (document.body.dataset.scenarioName || 'unnamed').trim() || 'unnamed',
            parseInt(fromInput.value, 10) || 0,
            toInput.value === '' ? 999999 : (parseInt(toInput.value, 10) || 0),
            new Date().toISOString().slice(0, 19).replace(/:/g, '-'),
            formatSel.value
        ); }

        function copyText() {
            var res = build();
            if (res.error) { toastError(res.error); return; }
            navigator.clipboard.writeText(res.text).then(function () {
                toastInfo('Copied ' + res.turns + ' turn' + (res.turns === 1 ? '' : 's') + ' to clipboard.');
                overlay.remove();
            }).catch(function () {
                var ta = document.createElement('textarea');
                ta.value = res.text; ta.style.position = 'fixed'; ta.style.left = '-9999px';
                document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove();
                toastInfo('Copied ' + res.turns + ' turn' + (res.turns === 1 ? '' : 's') + ' to clipboard.');
                overlay.remove();
            });
        }
        function saveFile() {
            var res = build();
            if (res.error) { toastError(res.error); return; }
            var name = (document.body.dataset.scenarioName || 'unnamed') + '_turns_' +
                (parseInt(fromInput.value, 10) || 0) + '-' +
                (toInput.value === '' ? (bounds ? bounds.max : '?') : toInput.value) + '.md';
            saveFileWithDialog(new Blob([res.text], { type: 'text/markdown;charset=utf-8' }), name);
            toastInfo('Saved turns ' + (parseInt(fromInput.value, 10) || 0) + '–' +
                (toInput.value === '' ? (bounds ? bounds.max : '?') : toInput.value) + ' to file.');
            overlay.remove();
        }

        var header = document.createElement('h3');
        header.style.cssText = 'margin:0;font-size:14px;';
        header.textContent = '⏩ Export Turns Range' + (bounds ? ' (log: ' + bounds.min + '–' + bounds.max + ')' : '');
        var row = document.createElement('div');
        row.style.cssText = 'display:flex;gap:6px;align-items:center;';
        var fromL = document.createElement('label'); fromL.textContent = 'From'; fromL.style.cssText = 'font-size:11px;';
        var toL = document.createElement('label'); toL.textContent = 'To'; toL.style.cssText = 'font-size:11px;';
        row.appendChild(fromL); row.appendChild(fromInput); row.appendChild(toL); row.appendChild(toInput);
        var actions = document.createElement('div');
        actions.style.cssText = 'display:flex;gap:6px;justify-content:flex-end;';
        var copyBtn = document.createElement('button'); copyBtn.className = 'btn btn-sm'; copyBtn.textContent = '📋 Copy';
        copyBtn.onclick = copyText;
        var saveBtn = document.createElement('button'); saveBtn.className = 'btn btn-sm btn-green'; saveBtn.textContent = '📥 Save file';
        saveBtn.onclick = saveFile;
        var closeBtn = document.createElement('button'); closeBtn.className = 'btn btn-sm'; closeBtn.textContent = '✕';
        closeBtn.onclick = function () { overlay.remove(); };
        actions.appendChild(copyBtn); actions.appendChild(saveBtn); actions.appendChild(closeBtn);
        box.appendChild(header); box.appendChild(row); box.appendChild(formatSel); box.appendChild(actions);
        overlay.addEventListener('mousedown', function (ev) { if (ev.target === overlay) overlay.remove(); });
        setTimeout(function () { fromInput.focus(); }, 20);
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
        } catch (e) {
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
        if (!text) return;
        try {
            navigator.clipboard.writeText(text);
        } catch (e) {
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
