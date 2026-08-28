#!/usr/bin/env node
/**
 * extract_js.mjs <file>
 * Emit JSON: {entities: [...], imports: [[mod, names, is_from], ...], file_doc}
 * Uses acorn to parse modern JS (classes, arrows, optional chaining, etc.).
 * Entities use the same shape as build_code_graph.py:
 *   {kind, name, qualified_name, docstring, signature, source_code,
 *    filepath, relative_path, line_start, line_end, decorators, calls,
 *    bases, class_qname, parent_qname}
 * Qualified names are "rel::Class::method" style, ending "<comment>N" for comments
 * (comments are attached in Python via extract_comments; Node only adds a flag).
 */
import { parse } from 'acorn';
import { fullAncestor } from 'acorn-walk';
import { readFileSync } from 'fs';
import { resolve, dirname, basename } from 'path';
import { fileURLToPath } from 'url';

const file = process.argv[2];
const rel = process.argv[3] || file;
const src = readFileSync(file, 'utf8');

let ast;
try {
  ast = parse(src, {
    ecmaVersion: 'latest',
    sourceType: 'module',
    allowHashBang: true,
    locations: true,
    onComment: null,
  });
} catch (e) {
  process.stdout.write(JSON.stringify({ error: String(e), entities: [], imports: [], file_doc: '' }));
  process.exit(0);
}

const entities = [];

function qnameOf(parentChain, name) {
  return [...parentChain, name].join('::');
}

function classChain(ancestors) {
  return ancestors.slice(0, -1)
    .filter((n) => n.type === 'ClassDeclaration' || n.type === 'ClassExpression')
    .map((n) => (n.id && n.id.name) || (n.key && (n.key.name || n.key.value)) || '<anon>');
}

fullAncestor(ast, function cb(node, stateOrAncestors, ancestors, type) {
  // stateOrAncestors === ancestors for this walker
  const anc = Array.isArray(stateOrAncestors) ? stateOrAncestors : (ancestors || []);
  if (node.type === 'FunctionDeclaration') {
    const name = node.id ? node.id.name : '<anonymous>';
    const parents = classChain(anc);
    const qn = qnameOf(parents, name);
    entities.push({
      kind: parents.length ? 'CodeMethod' : 'CodeFunction',
      name,
      qualified_name: qn,
      docstring: '',
      signature: '',
      source_code: src.slice(node.start, node.end).split('\n').slice(0, 40).join(' ').slice(0, 1200),
      filepath: file,
      relative_path: rel,
      line_start: node.loc.start.line,
      line_end: node.loc.end.line,
      decorators: [],
      calls: [],
      bases: [],
      class_qname: parents.length ? qnameOf(parents.slice(0, -1), parents[parents.length - 1]) : null,
      parent_qname: parents.length ? qnameOf(parents.slice(0, -1), parents[parents.length - 1]) : null,
    });
  } else if (node.type === 'ClassDeclaration') {
    const name = node.id ? node.id.name : '<anonymous>';
    const parents = classChain(anc);
    const qn = qnameOf(parents, name);
    entities.push({
      kind: 'CodeClass',
      name,
      qualified_name: qn,
      docstring: '',
      signature: '',
      source_code: '',
      filepath: file,
      relative_path: rel,
      line_start: node.loc.start.line,
      line_end: node.loc.end.line,
      decorators: [],
      calls: [],
      bases: node.superClass ? [node.superClass.name || '<expr>'] : [],
      class_qname: qn,
      parent_qname: parents.length ? qnameOf(parents.slice(0, -1), parents[parents.length - 1]) : null,
    });
  } else if (node.type === 'ArrowFunctionExpression') {
    let name = null;
    for (const a of anc) {
      if (a.type === 'VariableDeclarator' && a.init === node && a.id && a.id.type === 'Identifier') {
        name = a.id.name;
        break;
      }
    }
    if (!name) return;
    const parents = classChain(anc);
    const qn = qnameOf(parents, name);
    entities.push({
      kind: 'CodeFunction',
      name,
      qualified_name: qn,
      docstring: '',
      signature: '',
      source_code: src.slice(node.start, node.end).split('\n').slice(0, 30).join(' ').slice(0, 1200),
      filepath: file,
      relative_path: rel,
      line_start: node.loc.start.line,
      line_end: node.loc.end.line,
      decorators: [],
      calls: [],
      bases: [],
      class_qname: parents.length ? qnameOf(parents.slice(0, -1), parents[parents.length - 1]) : null,
      parent_qname: parents.length ? qnameOf(parents.slice(0, -1), parents[parents.length - 1]) : null,
    });
  } else if (node.type === 'MethodDefinition') {
    const name = node.key ? (node.key.name || node.key.value || '<anon>') : '<anon>';
    const parents = classChain(anc);
    const qn = qnameOf(parents, name);
    if (!parents.length) return;
    entities.push({
      kind: 'CodeMethod',
      name,
      qualified_name: qn,
      docstring: '',
      signature: '',
      source_code: src.slice(node.start, node.end).split('\n').slice(0, 30).join(' ').slice(0, 1200),
      filepath: file,
      relative_path: rel,
      line_start: node.loc.start.line,
      line_end: node.loc.end.line,
      decorators: [],
      calls: [],
      bases: [],
      class_qname: qnameOf(parents.slice(0, -1), parents[parents.length - 1]),
      parent_qname: qnameOf(parents.slice(0, -1), parents[parents.length - 1]),
    });
  }
});

// imports
const imports = [];
function walkImports(node) {
  if (!node || typeof node !== 'object') return;
  if (node.type === 'ImportDeclaration' && node.source) {
    imports.push([node.source.value, node.specifiers.map((s) => s.imported && s.imported.name || s.local.name).filter(Boolean), false]);
  } else if (node.type === 'VariableDeclaration') {
    for (const d of node.declarations) {
      if (d.init && d.init.type === 'CallExpression' && d.init.callee && d.init.callee.name === 'require' && d.init.arguments[0] && d.init.arguments[0].value) {
        imports.push([d.init.arguments[0].value, [], false]);
      }
    }
  }
  for (const k of Object.keys(node)) {
    const v = node[k];
    if (Array.isArray(v)) for (const c of v) walkImports(c);
    else if (v && typeof v === 'object') walkImports(v);
  }
}
walkImports(ast);

// file doc: first comment-ish? acorn dropped comments; keep empty.
const out = { error: null, entities, imports, file_doc: '' };
process.stdout.write(JSON.stringify(out));
