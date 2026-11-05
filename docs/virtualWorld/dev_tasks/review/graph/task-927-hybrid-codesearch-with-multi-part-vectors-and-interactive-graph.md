---
type: task
status: review
area: graph
priority: medium
wiki: "[[World Building/Graph System]]"
---

# task-927: Hybrid codesearch with multi-part vectors and interactive graph

**Filed:** 2026-11-01
**Related:** tools/build_code_graph.py, F:\AI\code\video_search

## What

Build a local, self-contained code search, graph indexer, and interactive visualizer (`tools/codesearch/`) that unifies:
1. Multi-language code and text extraction: Python (`.py`), TypeScript/JavaScript (`.ts`, `.js`, `.mjs`, `.cjs`), Markdown/text (`.md`, `.txt`), and HTML (`.html`).
2. SQLite storage (`.codesearch/codesearch.db`): relational entity nodes and indexed graph edges (`DEFINES`, `CALLS`, `REFERENCES`, `IMPORTS`, `INHERITS`, `ANNOTATES`, `LINKS_TO`), plus an FTS5 virtual table with per-column BM25 weights (`name=10.0, words=8.0, signature=6.0, docstring=4.0, rel_path=3.0, source=1.0`).
3. Multi-part vector embeddings (via local LM Studio `http://localhost:1234/v1` serving `text-embedding-qwen3-embedding-0.6b`): four separate vector parts (`filename`, `function_name`, `function`, and `comment`) stored in SQLite (`node_parts` and `vec_cache`) with 64-bit `blake2b` content hashing so re-indexing never forces re-embedding unchanged text.
4. Reciprocal Rank Fusion (RRF, k=60): combines keyword FTS5 BM25 ranks with vector cosine similarity across parts (`FTS_WEIGHT=1.6`, `MULTI_PART_DECAY=0.25`, `MIN_SIMILARITY=0.45`), supporting both AND (all words required, default) and OR (`--any`) modes, plus `--strict` keyword-only filtering.
5. Three consumption interfaces:
   - CLI (`tools/codesearch.py` / `tools/codesearch/cli.py`): instant terminal queries with snippets, score breakdowns, caller/callee inspection, variable read/write reference tracing, and file outlines.
   - FastMCP Server (`tools/codesearch/mcp_server.py`): structured tools for autonomous agents (`search_code`, `code_neighbors`, `find_references`, `file_outline`, `get_code`, `codesearch_stats`).
   - Web UI (`tools/codesearch/app.py` + `tools/codesearch/templates/index.html`): split-pane search with filter chips, an interactive `vis-network` force graph with in-place 1-hop neighbor expansion, code inspector drawer, and one-click "Open in VS Code" links (`vscode://file/<path>:<line>:1` and `POST /api/open`).

## Why

- The existing `tools/build_code_graph.py` and `F:\AI\code\utils\code_knowledge_graph.py` require a running Neo4j daemon on port 7687, making them fragile and unportable.
- Single-bucket vector embedding fails on code: a 300-line function body drowns out exact function names and concise comments.
- Keyword-only search misses intent ("how are turns scheduled"), while vector-only search misses exact variable names (`area_presence`). Combining them with RRF (as proven in `F:\AI\code\video_search`) delivers both exact token hits and semantic conceptual hits.
- Code exploration needs relational context: finding a function is only half the battle; knowing who calls it and what state it mutates prevents bugs without forcing full-file reads into LLM contexts.

## Architecture and Design

### 1. Storage (`db.py`)
- SQLite database file (`.codesearch/codesearch.db`, gitignored).
- Tables:
  - `files`: `id, rel_path, language, hash, mtime, lines`
  - `nodes`: `id, file_id, kind, name, qualified_name, parent_id, signature, docstring, source, line_start, line_end`
    - `kind` in `('file', 'class', 'function', 'method', 'variable', 'comment', 'section', 'block', 'element')`
  - `edges`: `id, source_id, target_id, kind, meta`
    - `kind` in `('DEFINES', 'CALLS', 'REFERENCES', 'IMPORTS', 'INHERITS', 'ANNOTATES', 'LINKS_TO')`
  - `refs`: raw parser references resolved into `edges` after each index run with language-family isolation (`py` vs `js`) and receiver (`self`, `recv:<Class>`, `attr`) disambiguation.
  - `node_parts` and `vec_cache`: `(node_id, part, hash)` mapped to `(part, hash, model, dim, vec)` float32 L2-normalized blobs.
  - `nodes_fts`: FTS5 virtual table indexing `name, words, signature, docstring, rel_path, source` with identifier camelCase/snake_case splitting in `words`.

### 2. Multi-Language Extractors (`parsers/`)
- **Python** (`parsers/py_parser.py`): stdlib `ast` + `tokenize` for classes, functions/methods, module and instance (`self.x`) variables, grouped comment blocks, `CALLS`, `IMPORTS`, `INHERITS`, and `REFERENCES` with read (`r`) and write (`w`) mode tracking (including subscript/attribute writes and mutating method calls like `.append`/`.update`, while excluding function-local variables unless declared `global`).
- **TypeScript / JavaScript** (`parsers/ts_parser.mjs` + `parsers/js_bridge.py`): batched Node 24 subprocess using `stripTypeScriptTypes(text, { mode: 'strip' })` to preserve 1-to-1 line coordinates + `acorn` for ES classes/functions, `window.Mod = { ... }` object-literal modules (`GraphNetwork`), `window.Mod = (() => { ... })()` revealing IIFE modules (`TurnQueue`), top-level named IIFEs, JSDoc attachment, and comment blocks.
- **Markdown / Text** (`parsers/md_parser.py`): heading hierarchy (`#` through `######`), fenced code blocks, paragraph-chunked plain text files, and Markdown/wikilink extraction (`[label](path)` and `[[Wiki]]`) resolved to `LINKS_TO` edges.
- **HTML** (`parsers/html_parser.py`): `<title>`, `h1-h3` sections, `[id]` elements, `<script src>`/`<link href>` imports, and inline `<script>` blocks forwarded to `js_bridge` with line offsets.

### 3. Multi-Part Vector Embedder (`embedder.py`)
- Endpoint: local LM Studio (`http://localhost:1234/v1`, model `text-embedding-qwen3-embedding-0.6b`).
- Vector parts:
  - `filename`: relative path, split identifier tokens, file docstring/summary.
  - `function_name`: kind, qualified name, split identifier words.
  - `function`: signature, split identifier words, docstring summary, and leading body lines.
  - `comment`: full docstrings, standalone comment blocks, and Markdown/text sections.
- Storage: `node_parts` and `vec_cache` tables in `.codesearch/codesearch.db`, loaded into in-memory L2-normalized `float32` numpy matrices by `VectorIndex`.

### 4. Hybrid Retriever (`search.py`)
- RRF rank fusion: combines weighted FTS5 BM25 ranks (`FTS_WEIGHT=1.6`) with multi-part cosine similarity ranks (`best_vec + 0.25 * sum(other_vecs)`).
- Auto-reloads `VectorIndex` when `vec_cache` row count changes.
- Enriches top matches with 1-hop graph relation summaries (`called_by`, `calls`, `referenced_by`, `references`, `annotates`, `links_to`, `linked_from`).

### 5. Consumption Surfaces
- **CLI** (`tools/codesearch.py` / `tools/codesearch/cli.py`):
  - `python tools/codesearch.py "query"` (or `search`, `index`, `embed`, `callers`, `callees`, `refs`, `outline`, `stats`, `serve`, `mcp`).
- **FastMCP Server** (`tools/codesearch/mcp_server.py`):
  - `search_code`, `code_neighbors`, `find_references`, `file_outline`, `get_code`, `codesearch_stats`.
- **Web UI** (`tools/codesearch/app.py` + `tools/codesearch/templates/index.html`):
  - Local Flask application on `http://127.0.0.1:5002`.
  - Split view: left query and filter chip panel, right interactive `vis-network` force graph and bottom code inspector drawer.
  - "Open in VS Code" link (`vscode://file/<absolute_path>:<line>:1`) and "Open via server" button (`POST /api/open` running `code --goto`).

## Browser UI and intended live verification

Intended UI home: `http://127.0.0.1:5002` (Code Search and Graph Visualizer web UI)

Current availability: Implemented and verified live in headless Chromium via Playwright:
- Control audit on root `document.body`: 25 interactive controls in DOM (`#q` input, 8 `kind` chips, 6 `lang` chips, 4 `index` part chips, 2 `mode` chips, 2 `depth` buttons, plus `#vsl` "Open in VS Code" and `#vsb` "Open via server" revealed on node selection).
- Query `"turn queue initiative"` returned 30 hybrid results headed by `TurnQueue::rerollInitiatives` (`static/js/agent/turn-queue.ts:291-316`, `matched: keyword, vec:comment, vec:function, vec:function_name`), `Turn Queue & Human Turns::The queue`, and `TurnQueue::initialize` (`called by 5`).
- Clicking `TurnQueue::rerollInitiatives` rendered `8 nodes, 8 edges` in the `vis-network` graph, highlighted all 26 lines (`291-316`) in `#code`, and set `#vsl` to `vscode://file/F:/AI/viwo/virtual-world/static/js/agent/turn-queue.ts:291:1`.
- Expanding neighbor node `231789` (`turnQueue`) merged its 1-hop neighborhood in place via `DataSet.update()` to `28 nodes, 29 edges` without resetting the graph.

Live steps when available:
1. Start the web server: `python tools/codesearch.py serve`.
   - expected: Server listens on `http://127.0.0.1:5002`.
2. Type query `"turn queue initiative"` into `#q` and press Enter.
   - expected: Results show ranked cards split by match kind (`TurnQueue::rerollInitiatives`, `Turn Queue & Human Turns::The queue`, `TurnQueue::initialize`, and related comments).
3. Click the result card for `TurnQueue::rerollInitiatives`.
   - expected: The right pane renders an interactive graph centered on `rerollInitiatives` (`8 nodes, 8 edges`), and the code inspector highlights `static/js/agent/turn-queue.ts:291-316`.
4. Click the "Open in VS Code" link (`#vsl`) on the code inspector header.
   - expected: Link targets `vscode://file/F:/AI/viwo/virtual-world/static/js/agent/turn-queue.ts:291:1` (or `POST /api/open` invokes `code --goto`).
5. In the graph view, double-click a connected node (such as `turnQueue`).
   - expected: Graph expands 1-hop neighbors in place (`28 nodes, 29 edges`) without full reload.

## Steps to verify

1. Extractor test: run `python -m pytest tests/test_codesearch_parsers.py` to verify AST, comments, calls, and variables across `.py`, `.ts`, `.md`, `.txt`, and `.html`.
   - expected: All 11 parser tests pass.
2. Database, RRF, and MCP test: run `python -m pytest tests/test_codesearch_db.py`.
   - expected: All 10 database, incremental index, RRF union/strict, vector cache, and MCP tool tests pass.
3. Hybrid search test: run CLI search `python tools/codesearch.py search "syncGraphData"` and `python tools/codesearch.py callers "GraphNetwork::syncGraphData"`.
   - expected: Returns `static/js/graph/network-manager.ts::GraphNetwork::syncGraphData` and its caller `GraphManagerImpl::syncGraphData`.
4. Follow the live browser verification steps on `http://127.0.0.1:5002`.

## Acceptance Criteria

- [x] Extractor parses Python files into Files, Classes, Functions, Variables, Comments, and Edges (`DEFINES`, `CALLS`, `REFERENCES`, `IMPORTS`, `INHERITS`).
- [x] Extractor parses TypeScript and JavaScript files via Node without external runtime dependencies beyond existing project modules.
- [x] Extractor parses Markdown headings, code fences, and cross-file links into interconnected nodes.
- [x] SQLite database stores all nodes, edges, and FTS5 index with triggers or bulk update routines.
- [x] Embedding pipeline produces 4 separate normalized vector stores (`filename`, `function_name`, `function`, `comment`) with blake2b caching.
- [x] Hybrid search fuses FTS5 BM25 and vector parts with RRF (k=60).
- [x] CLI supports hybrid search, filter flags, caller/callee inspection, and variable reference tracing.
- [x] FastMCP server exposes `search_code`, `code_neighbors`, `find_references`, and `file_outline`.
- [x] Web UI displays search results, an interactive graph with expandable neighbors, a code viewer, and functional "Open in VS Code" links.
- [x] No em-dashes anywhere in code, comments, or documentation.

## Files

- `tools/codesearch/__init__.py`
- `tools/codesearch/__main__.py`
- `tools/codesearch/config.py`
- `tools/codesearch/db.py`
- `tools/codesearch/parsers/__init__.py`
- `tools/codesearch/parsers/py_parser.py`
- `tools/codesearch/parsers/ts_parser.mjs`
- `tools/codesearch/parsers/js_bridge.py`
- `tools/codesearch/parsers/md_parser.py`
- `tools/codesearch/parsers/html_parser.py`
- `tools/codesearch/embedder.py`
- `tools/codesearch/indexer.py`
- `tools/codesearch/search.py`
- `tools/codesearch/graph.py`
- `tools/codesearch/cli.py`
- `tools/codesearch/mcp_server.py`
- `tools/codesearch/app.py`
- `tools/codesearch/templates/index.html`
- `tools/codesearch.py`
- `tests/test_codesearch_parsers.py`
- `tests/test_codesearch_db.py`
