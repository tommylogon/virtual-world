#!/usr/bin/env node
/**
 * stream_read.cjs - Standalone event-stream reader CLI (task-778).
 *
 * Query an exported event-stream JSON/JSONL run without the app or server.
 *
 * Usage:
 *   node tools/stream_read.cjs <file> [options]
 *
 * Options:
 *   --actor <name>      Filter by actor name (case-insensitive)
 *   --area <name>       Filter by area name (case-insensitive)
 *   --type <type>       Filter by event type (speech, action, system, etc.)
 *   --from <seq>        Minimum tick sequence number (inclusive)
 *   --to <seq>          Maximum tick sequence number (inclusive)
 *   --mode <mode>       Output mode: timeline (default), summary, raw
 *   --json              Output result as JSON
 *   --help, -h          Show help message
 *
 * Exit codes: 0 = success, 2 = usage or IO error.
 */

'use strict';

const fs = require('fs');
const path = require('path');

function parseEvents(text) {
  const trimmed = text.trim();
  if (!trimmed) return [];

  // Try parsing as single JSON document first (envelope or array)
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    try {
      const parsed = JSON.parse(trimmed);
      if (Array.isArray(parsed)) return parsed;
      if (parsed && Array.isArray(parsed.events)) return parsed.events;
    } catch {
      // Not a single JSON doc; fall back to JSONL parsing
    }
  }

  // Parse as JSONL (one JSON object per line)
  const lines = trimmed.split(/\r?\n/);
  const events = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    try {
      events.push(JSON.parse(line));
    } catch (e) {
      throw new Error(`Invalid JSON on line ${i + 1}: ${e.message}`);
    }
  }
  return events;
}

function filterEvents(events, opts = {}) {
  return events.filter((e) => {
    if (opts.actor != null && opts.actor !== '') {
      const actorStr = String(e.actor || '').toLowerCase();
      if (actorStr !== opts.actor.toLowerCase()) return false;
    }
    if (opts.area != null && opts.area !== '') {
      const areaStr = String(e.area || '').toLowerCase();
      if (areaStr !== opts.area.toLowerCase()) return false;
    }
    if (opts.type != null && opts.type !== '') {
      const typeStr = String(e.type || '').toLowerCase();
      if (typeStr !== opts.type.toLowerCase()) return false;
    }
    const seq = e.seq != null ? Number(e.seq) : null;
    if (opts.from != null && seq != null) {
      if (seq < Number(opts.from)) return false;
    }
    if (opts.to != null && seq != null) {
      if (seq > Number(opts.to)) return false;
    }
    return true;
  });
}

function summarizeEvents(events) {
  const actorMap = new Map();
  const areaMap = new Map();
  const typeMap = new Map();

  for (const e of events) {
    const actor = e.actor || '(none)';
    actorMap.set(actor, (actorMap.get(actor) || 0) + 1);

    const area = e.area || '(none)';
    areaMap.set(area, (areaMap.get(area) || 0) + 1);

    const type = e.type || '(none)';
    typeMap.set(type, (typeMap.get(type) || 0) + 1);
  }

  const actors = Array.from(actorMap.entries())
    .map(([actor, count]) => ({ actor, count }))
    .sort((a, b) => b.count - a.count || a.actor.localeCompare(b.actor));

  const areas = Array.from(areaMap.entries())
    .map(([area, count]) => ({ area, count }))
    .sort((a, b) => b.count - a.count || a.area.localeCompare(b.area));

  const types = Array.from(typeMap.entries())
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => b.count - a.count || a.type.localeCompare(b.type));

  return {
    total: events.length,
    actors,
    areas,
    types,
  };
}

function formatTimelineEvent(e) {
  const parts = [];
  if (e.seq != null && e.seq >= 0) parts.push(`Seq ${e.seq}`);
  if (e.turn != null) parts.push(`Turn ${e.turn}`);
  if (e.time) parts.push(e.time);
  const header = parts.length ? `[${parts.join(' | ')}] ` : '';
  const typeTag = e.type ? `[${e.type}] ` : '';
  const actorTag = e.actor ? `${e.actor}` : '';
  const areaTag = e.area ? ` @ ${e.area}` : '';
  const source = actorTag || areaTag ? `${actorTag}${areaTag}: ` : '';
  return `${header}${typeTag}${source}${e.text || ''}`;
}

function usage() {
  console.error('usage: node tools/stream_read.cjs <file> [--actor <name>] [--area <name>] [--type <type>] [--from <seq>] [--to <seq>] [--mode timeline|summary|raw] [--json]');
}

function main(argv) {
  let file = null;
  const opts = {
    actor: null,
    area: null,
    type: null,
    from: null,
    to: null,
    mode: 'timeline',
    json: false,
  };

  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--help' || a === '-h') {
      usage();
      return 0;
    } else if (a === '--json') {
      opts.json = true;
    } else if (a === '--actor') {
      opts.actor = argv[++i];
    } else if (a === '--area') {
      opts.area = argv[++i];
    } else if (a === '--type') {
      opts.type = argv[++i];
    } else if (a === '--from') {
      opts.from = Number(argv[++i]);
    } else if (a === '--to') {
      opts.to = Number(argv[++i]);
    } else if (a === '--mode') {
      opts.mode = argv[++i] || 'timeline';
    } else if (a.startsWith('--')) {
      console.error(`Unknown option: ${a}`);
      usage();
      return 2;
    } else {
      if (!file) file = a;
      else {
        console.error(`Unexpected argument: ${a}`);
        usage();
        return 2;
      }
    }
  }

  if (!file) {
    usage();
    return 2;
  }

  let text;
  try {
    text = fs.readFileSync(path.resolve(file), 'utf8');
  } catch (e) {
    console.error(`error: cannot read ${file}: ${e.message}`);
    return 2;
  }

  let events;
  try {
    events = parseEvents(text);
  } catch (e) {
    console.error(`error: parse failure in ${file}: ${e.message}`);
    return 2;
  }

  const filtered = filterEvents(events, opts);

  if (opts.mode === 'summary') {
    const summary = summarizeEvents(filtered);
    if (opts.json) {
      console.log(JSON.stringify(summary, null, 2));
    } else {
      console.log(`Matched ${summary.total} event(s):`);
      console.log('Actors:');
      for (const a of summary.actors) {
        console.log(`  ${a.actor}: ${a.count}`);
      }
      console.log('Areas:');
      for (const a of summary.areas) {
        console.log(`  ${a.area}: ${a.count}`);
      }
      console.log('Types:');
      for (const t of summary.types) {
        console.log(`  ${t.type}: ${t.count}`);
      }
    }
    return 0;
  }

  if (opts.mode === 'raw') {
    if (opts.json) {
      console.log(JSON.stringify(filtered, null, 2));
    } else {
      for (const e of filtered) {
        console.log(JSON.stringify(e));
      }
    }
    return 0;
  }

  // Default mode: timeline
  if (opts.json) {
    console.log(JSON.stringify(filtered, null, 2));
  } else {
    for (const e of filtered) {
      console.log(formatTimelineEvent(e));
    }
  }
  return 0;
}

if (require.main === module) {
  process.exitCode = main(process.argv.slice(2));
}

module.exports = { parseEvents, filterEvents, summarizeEvents, formatTimelineEvent, main };
