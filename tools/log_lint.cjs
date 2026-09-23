#!/usr/bin/env node
/**
 * log_lint.cjs — grep-able regression guards over play-session export logs.
 *
 * task-347. Export logs are the cheapest observable surface for engine and
 * prompt-builder regressions; today the classes below are found by hand months
 * later. This lints existing/new exports for known-bad signatures. No model and
 * no server needed — it only reads text.
 *
 * Usage:
 *   node tools/log_lint.cjs <file|dir> [<file|dir> ...] [--json] [--quiet] [--only rule,rule]
 *
 * Exit code: 0 = clean, 1 = findings, 2 = usage/IO error.
 *
 * Rules (all findings are non-fatal "warn"; exit is non-zero so a release
 * checklist can gate on it):
 *   article-double      "the the"                        (bug-27)
 *   missing-space       "earringfrom the" joined tokens  (bug-27)
 *   apostrophe-strip    "that s" / "i m" / "don t" in CONVERSATION (bug-28)
 *   double-attribution  same quoted speech twice in one WITNESSED block (bug-29)
 *   memory-dup          identical sentence twice in one I REMEMBER block (task-346)
 *   pronoun-stitch      verb + "your" where "you" is meant (G1)
 *   appearance-grammar  "you is" / "you was"              (task-345)
 */

'use strict';

const fs = require('fs');
const path = require('path');

const SKIP_DIRS = new Set(['node_modules', '.git', '.kilo', '__pycache__', 'vendor']);
const TEXT_EXT = new Set(['.txt', '.md', '.log']);

// Real words that legitimately end in a relation suffix and would otherwise
// false-positive the missing-space rule.
const RELATION_WORD_ALLOW = new Set([
  'thunder', 'blunder', 'asunder', 'sunder', 'chunder', 'downunder',
  'hereunder', 'thereunder', 'whereunder',
  'therefrom', 'wherefrom', 'herefrom',
]);

const RULES = [
  {
    id: 'article-double',
    scope: null,
    why: 'article doubling',
    test: (line) => /\bthe\s+the\b/i.test(line),
  },
  {
    id: 'missing-space',
    scope: null,
    why: 'missing space at a relation word (e.g. "earringfrom under the table")',
    // A noun glued to a relation word ("earringfrom", "caddieonthe"). "from"
    // virtually never ends an English word; "under" does (thunder, blunder),
    // so those are allowlisted. The "on/in/at/to" form only fires when it runs
    // all the way into "the", which no dictionary word does.
    test: (line) => {
      const glued = line.match(/[a-z]{4,}(?:from|under)\b/gi) || [];
      if (glued.some((w) => !RELATION_WORD_ALLOW.has(w.toLowerCase()))) return true;
      return /[a-z]{4,}(?:on|in|at|to)the\b/i.test(line);
    },
  },
  {
    id: 'apostrophe-strip',
    scope: 'CONVERSATION',
    why: 'apostrophe stripped / words split',
    test: (line) => /\bthat s\b|\bi m\b|\bdon t\b/i.test(line),
  },
  {
    id: 'memory-dup',
    scope: 'I REMEMBER',
    why: 'identical sentence repeated in memory',
    section: (section, ctx, out) => {
      const seen = new Map();
      for (const { line, no, text } of section.lines) {
        const t = text.trim();
        if (t.length < 20) continue;
        if (/^[-*•\d.]/.test(t) === false && t.endsWith(':')) continue;
        const key = t.toLowerCase();
        if (seen.has(key)) {
          out.push(finding(ctx, 'memory-dup', no, line, 'duplicate of line ' + seen.get(key)));
        } else {
          seen.set(key, no);
        }
      }
    },
  },
  {
    id: 'double-attribution',
    scope: 'WITNESSED',
    why: 'same quoted speech attributed twice in one block',
    section: (section, ctx, out) => {
      const seen = new Map();
      for (const { line, no, text } of section.lines) {
        const quotes = text.match(/"([^"]{8,})"/g) || [];
        for (const raw of quotes) {
          const q = raw.slice(1, -1).trim().toLowerCase();
          if (seen.has(q)) {
            out.push(finding(ctx, 'double-attribution', no, line,
              'same quote also at line ' + seen.get(q)));
          } else {
            seen.set(q, no);
          }
        }
      }
    },
  },
  {
    id: 'pronoun-stitch',
    scope: null,
    why: 'verb + "your" where "you" is meant (pronoun stitching)',
    test: (line) => /\b(hugs|holds|grabs|touches|kisses|pulls|pushes|drags|carries|leads|releases|lifts)\s+your\b/i.test(line),
  },
  {
    id: 'appearance-grammar',
    scope: null,
    why: 'appearance grammar ("you is" / "you was")',
    test: (line) => /\byou\s+(is|was)\b/i.test(line),
  },
];

// ── helpers ─────────────────────────────────────────────────────────────

function finding(ctx, rule, lineNo, line, detail) {
  return {
    file: ctx.file,
    rule,
    line: lineNo,
    detail: detail || '',
    text: line.trim().slice(0, 160),
  };
}

function parseSections(text) {
  const sections = [];
  let current = { name: '(preamble)', lines: [] };
  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const m = /^===\s*(.+?)\s*===\s*$/.exec(lines[i]);
    if (m) {
      if (current.lines.length) sections.push(current);
      current = { name: m[1].toUpperCase(), lines: [] };
      continue;
    }
    current.lines.push({ line: lines[i], no: i + 1, text: lines[i] });
  }
  if (current.lines.length) sections.push(current);
  return sections;
}

function lintText(text, file, only) {
  const out = [];
  const sections = parseSections(text);
  for (const section of sections) {
    const ctx = { file, section: section.name };
    for (const rule of RULES) {
      if (only && !only.has(rule.id)) continue;
      if (rule.test) {
        if (rule.scope && section.name !== rule.scope) continue;
        for (const { line, no, text: t } of section.lines) {
          if (rule.test(t)) out.push(finding(ctx, rule.id, no, line, rule.why));
        }
      } else if (rule.section && (!rule.scope || section.name === rule.scope)) {
        rule.section(section, ctx, out);
      }
    }
  }
  return out;
}

function collectFiles(targets) {
  const files = [];
  for (const target of targets) {
    let st;
    try { st = fs.statSync(target); } catch (e) { throw new Error('not found: ' + target); }
    if (st.isFile()) { files.push(target); continue; }
    const stack = [target];
    while (stack.length) {
      const dir = stack.pop();
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        if (entry.isDirectory()) {
          if (!SKIP_DIRS.has(entry.name)) stack.push(path.join(dir, entry.name));
        } else if (TEXT_EXT.has(path.extname(entry.name).toLowerCase())) {
          files.push(path.join(dir, entry.name));
        }
      }
    }
  }
  return files.sort();
}

function usage() {
  console.error('usage: node tools/log_lint.cjs <file|dir> [...] [--json] [--quiet] [--only rule,rule]');
}

function main(argv) {
  const targets = [];
  let json = false;
  let quiet = false;
  let only = null;
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--json') json = true;
    else if (a === '--quiet') quiet = true;
    else if (a === '--only') only = new Set((argv[++i] || '').split(',').map((s) => s.trim()).filter(Boolean));
    else if (a === '--help' || a === '-h') { usage(); return 0; }
    else if (a.startsWith('--')) { usage(); return 2; }
    else targets.push(a);
  }
  if (!targets.length) { usage(); return 2; }

  let files;
  try { files = collectFiles(targets); }
  catch (e) { console.error('error: ' + e.message); return 2; }

  const all = [];
  for (const file of files) {
    let text;
    try { text = fs.readFileSync(file, 'utf8'); }
    catch (e) { console.error('error: cannot read ' + file + ': ' + e.message); return 2; }
    all.push(...lintText(text, file, only));
  }

  if (json) {
    console.log(JSON.stringify({ files: files.length, findings: all }, null, 2));
  } else if (!quiet) {
    let currentFile = null;
    for (const f of all) {
      if (f.file !== currentFile) { console.log(f.file); currentFile = f.file; }
      const where = f.section ? f.section + ' ' : '';
      console.log(`  L${f.line} [${f.rule}] ${where}${f.detail ? '(' + f.detail + ') ' : ''}${f.text}`);
    }
    const byRule = {};
    for (const f of all) byRule[f.rule] = (byRule[f.rule] || 0) + 1;
    const summary = Object.entries(byRule).map(([k, v]) => `${k}=${v}`).join(' ') || 'none';
    console.log(`\n${files.length} file(s), ${all.length} finding(s): ${summary}`);
  }
  return all.length ? 1 : 0;
}

if (require.main === module) {
  process.exitCode = main(process.argv.slice(2));
}

module.exports = { lintText, parseSections, collectFiles, RULES };
