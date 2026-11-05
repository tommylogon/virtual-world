---
type: doc
tags: [system/ui, system/tooling, topic/codesearch, topic/mcp]
---

# Code Search & Graph

## What you can do

Search the entire VirtualWorld repository - Python, TypeScript, JavaScript, Markdown, HTML, and plain text - by exact tokens, natural-language meaning, or both at once, and walk the relational call/reference/import graph from the CLI, an MCP server (`tools/codesearch/mcp_server.py`), or a local web UI (`http://127.0.0.1:5002`).

**Task:** [[dev_tasks/review/graph/task-927-hybrid-codesearch-with-multi-part-vectors-and-interactive-graph|task-927]]

| Surface | Entrypoint | What it provides |
|---|---|---|
| **CLI** | `python tools/codesearch.py <cmd>` | Incremental indexing, 4-part embedding, hybrid RRF search, caller/callee/reference tracing, file outlines |
| **MCP Server** | `python tools/codesearch.py mcp` | 6 FastMCP stdio tools (`search_code`, `code_neighbors`, `find_references`, `file_outline`, `get_code`, `codesearch_stats`) |
| **Web UI** | `python tools/codesearch.py serve` | Split-pane search, filter chips, `vis-network` graph with in-place 1-hop expansion, code inspector, Open in VS Code |

---

## 1. How the Index Works

All state lives in `.codesearch/codesearch.db` (gitignored, single-file SQLite with WAL mode enabled). No external graph daemon is required.

### Node kinds (9)
- **Code entities:** `file`, `class` (including TS/JS `window.Mod = { ... }` object modules and `window.Mod = (() => { ... })()` IIFE modules), `function`, `method`, `variable` (module constants and `self.x` / `this.x` instance attributes), `comment` (contiguous `#`, `//`, and `/* */` blocks that are not docstrings).
- **Document & template entities:** `section` (Markdown headings `#` through `######`, HTML `h1-h3`, and paragraph chunks in `.txt` files), `block` (fenced code blocks in Markdown), `element` (HTML elements carrying an `id`).

### Graph edges (7)
- `DEFINES`: `file -> class/function/variable/section/element` and `class -> method/variable`.
- `CALLS`: `function/method -> function/method`, resolved within the same language family (`py` vs `js`) using `self`, `recv:<Class>` (including `<Name>Impl` singletons like `graphManager -> GraphManagerImpl`), imported files, and unique repository symbols.
- `REFERENCES`: `function/method -> variable` with `meta` set to `"r"` (read) or `"w"` (write, including subscript/attribute assignments like `self.presence[who] = where` and mutating method calls like `.append()`, `.update()`, `.set()`, `.push()`). Function-local variables that shadow module globals are excluded unless declared `global`.
- `IMPORTS`: `file -> file` across Python imports, ES module imports, and HTML `<script src>` / `<link href>`.
- `INHERITS`: `class -> class`.
- `ANNOTATES`: `comment -> nearest enclosing or following symbol`.
- `LINKS_TO`: Markdown `[label](path)` and Obsidian `[[Wiki Link]]` references resolved to target `file` or `section` nodes.

### Hybrid retrieval: FTS5 BM25 + 4-part vectors + RRF (`k = 60`)
1. **Keyword index (`nodes_fts`)**: SQLite FTS5 `unicode61` table with camelCase and snake_case word splitting in `words` and column weights `name = 10.0, words = 8.0, signature = 6.0, docstring = 4.0, rel_path = 3.0, source = 1.0`. Default mode requires **all** query words (`AND`); `--any` switches to `OR`.
2. **Four separate vector indexes (`node_parts` + `vec_cache`)**:
   - `filename`: relative path, split identifier words, and file docstring/summary.
   - `function_name`: kind, qualified name, and split identifier words.
   - `function`: signature, split words, docstring summary, and leading body lines.
   - `comment`: docstrings, standalone comment blocks, and Markdown/text sections.
   Vectors are embedded via local LM Studio (`http://localhost:1234/v1`, model `text-embedding-qwen3-embedding-0.6b`, 1024-dim L2-normalized `float32`) and keyed by `(part, blake2b_hash, model)` in `vec_cache`, so re-indexing never re-embeds unchanged text.
3. **Reciprocal Rank Fusion (`search.py`)**:
   - Candidates are the union of FTS5 keyword matches and vector hits above `MIN_SIMILARITY = 0.45` (or restricted to keyword hits when `--strict` is set).
   - Scores fuse weighted FTS rank (`FTS_WEIGHT = 1.6`) with multi-part vector ranks (`best_vec + 0.25 * sum(other_vecs)` so 3-part methods do not drown out 1-part comments or files).

---

## 2. CLI User Guide

Run via `python tools/codesearch.py` (or `python -m tools.codesearch`). Any unrecognized first argument is treated as a `search` query.

### Build and update the index
```powershell
# Incremental scan + parse + edge resolution (~0.5s when unchanged, ~10s full)
python tools/codesearch.py index

# Force full re-parse of all files
python tools/codesearch.py index --force

# Embed all uncached node parts via LM Studio (core code tiers first)
python tools/codesearch.py embed

# Embed only a specific path prefix or cap the batch count
python tools/codesearch.py embed --path static/js
python tools/codesearch.py embed --path engine --limit 2000

# Show file, node, edge, and per-part vector counts
python tools/codesearch.py stats
```

### Hybrid search
```powershell
# Default hybrid search (all words OR semantic match across all 4 vector parts)
python tools/codesearch.py "turn queue initiative"

# Restrict to a single vector part: filename | function_name | function | comment
python tools/codesearch.py "batches the redraw" --part comment

# Filter by node kind, language, or path prefix
python tools/codesearch.py "memory" --kind method --lang typescript --path static/js

# Require keyword match (vectors only re-rank keyword hits)
python tools/codesearch.py "area_presence" --strict

# Match ANY word in the keyword leg instead of ALL words, and show full docstrings
python tools/codesearch.py "reinforce decay contradiction" --any --full --limit 20

# Emit structured JSON
python tools/codesearch.py "syncGraphData" --json
```

### Graph traversal & outlines
```powershell
# Who calls a function or method?
python tools/codesearch.py callers "GraphNetwork::syncGraphData"
python tools/codesearch.py callers "Player::add_memory"

# What does a function or method call?
python tools/codesearch.py callees "buildMemoryContext"

# Every read [READS] and write [WRITES] reference to a variable or attribute
python tools/codesearch.py refs "Player::memories"
python tools/codesearch.py refs "area_presence"

# Indented symbol and section outline of a file with line numbers
python tools/codesearch.py outline routes/memories.py
python tools/codesearch.py outline "docs/virtualWorld/AI & Narration/Memory System.md"
```

---

## 3. MCP Server Guide (`tools/codesearch/mcp_server.py`)

`tools/codesearch/mcp_server.py` exposes a stdio FastMCP server named `codesearch`. It opens `.codesearch/codesearch.db` directly and auto-reloads `VectorIndex` whenever `vec_cache` grows.

### Starting or registering the MCP server

Run directly on stdio:
```powershell
python tools/codesearch.py mcp
# or:
python tools/codesearch/mcp_server.py
```

MCP client configuration (`mcpServers` block for Claude Desktop, Cursor, Kilo, or Antigravity):
```json
{
  "mcpServers": {
    "codesearch": {
      "command": "python",
      "args": ["tools/codesearch.py", "mcp"],
      "cwd": "F:/AI/viwo/virtual-world",
      "env": {
        "CODESEARCH_EMBED_URL": "http://localhost:1234/v1",
        "CODESEARCH_EMBED_MODEL": "text-embedding-qwen3-embedding-0.6b"
      }
    }
  }
}
```

### MCP Tools Reference (6 tools)

| Tool | Parameters | Returns |
|---|---|---|
| `search_code` | `query: str`, `part: str = ""` (`filename` \| `function_name` \| `function` \| `comment`), `kind: str = ""` (comma-separated kinds), `language: str = ""`, `path: str = ""`, `match_all: bool = True`, `strict: bool = False`, `limit: int = 15` | Ranked results with `id`, `kind`, `name`, `qualified_name`, `file`, `line_start`, `line_end`, `signature`, `docstring`, `score`, `matched` sources, and 1-hop `relations` summary |
| `code_neighbors` | `symbol: str \| int` (node id, `name`, `Class::method`, or `path::Class::method`), `direction: str = "both"` (`in` \| `out` \| `both`), `depth: int = 1`, `edge_kinds: str = ""` | `center` node, `callers`, `callees`, `relations`, and the subgraph `{nodes, edges, truncated}` |
| `find_references` | `name: str`, `mode: str = ""` (`""` \| `"r"` \| `"w"`) | All matching variable/symbol definitions plus every `[r]` read and `[w]` write site with file and line numbers |
| `file_outline` | `rel_path: str` | Ordered list of all symbols, sections, blocks, and comments defined in `rel_path` with `id`, `kind`, `name`, `parent_id`, `signature`, `line_start`, `line_end` |
| `get_code` | `path: str`, `start: int`, `end: int` | Numbered source lines (`start..end` of `total_lines`) from disk |
| `codesearch_stats` | *(none)* | Total `files`, `nodes`, `edges`, `nodes_by_kind`, `edges_by_kind`, `files_by_language`, `vectors_by_part`, `cached_vectors`, and `indexed_at` |
| `render_code_graph` | `symbol: str \| int`, `depth: int = 1`, `expand: str = ""` (comma-separated `#id` or symbol names), `edge_kinds: str = ""`, `return_image: bool = False` | Renders a Set-of-Mark (`#id`) dark-theme PNG to `.codesearch/renders/`, returning `image_path`, deep-link `url` (`http://127.0.0.1:5002/?node=<id>&expand=<ids>`), `nodes` (with `mark: "#id"`), `edges`, and optional inline FastMCP `Image` block when `return_image=True` |

---

## 4. Web UI Guide (`http://127.0.0.1:5002`)

Start the local web server:
```powershell
# Double-click or run from the repo root (runs incremental index, opens browser, starts server):
.\start_codesearch.bat
# Or via tools\codesearch.bat (no args -> index + open browser + serve; with args -> CLI):
.\tools\codesearch.bat
# Or directly via Python:
python tools/codesearch.py serve
# Optional flags: --host 127.0.0.1 --port 5002
```

### Layout and interactions (28 controls)
- **Cold-start overview graph (`GET /api/overview?scope=runtime|code|docs`)**:
  - Loads `overview (runtime)` automatically on startup (**408 connected runtime files, 961 edges**), separating the frontend (`templates/` in red, `static/js/` in blue) from the backend (`engine/` in green, `routes/` in orange, root `.py` in cyan).
  - `#graphbar` includes three `overview` buttons (`runtime`, `all code`, `docs` - **192 connected docs files, 1,678 `LINKS_TO` edges**) so you can switch or return to the codebase overview at any time.
- **Left pane (`#searchbar` + `#results`)**:
  - Search input `#q` (press `Enter` to run hybrid search).
  - Filter chip rows:
    - `kind`: `file`, `class`, `function`, `method`, `variable`, `comment`, `section`, `block` (multi-select).
    - `lang`: `python`, `typescript`, `javascript`, `markdown`, `html`, `text` (multi-select).
    - `index`: `filename`, `function_name`, `function`, `comment` (single-select vector part).
    - `mode`: `any word` (`OR` keyword matching) and `strict` (require keyword match).
  - Clicking a result card selects it, centers the graph on that node, and opens its source in the bottom code inspector.
- **Top-right pane (`#graphwrap`)**:
  - Interactive `vis-network` canvas (`static/js/vendor/vis-network/vis-network-9.1.9.min.js`).
  - `depth` buttons (`1` or `2` hops) and color legend by edge kind (`DEFINES`, `CALLS`, `REFERENCES`, `IMPORTS`, `INHERITS`, `ANNOTATES`, `LINKS_TO`).
  - **Single-click** a graph node to inspect its source code in the bottom drawer without resetting the graph.
  - **Double-click** any graph node to fetch its 1-hop neighborhood (`/api/graph/<id>?depth=1`) and merge new nodes/edges **in place** via `DataSet.update()`.
- **Bottom-right pane (`#inspector`)**:
  - Shows `file:line_start-line_end [kind] name` and numbered source lines with the node's span highlighted (`.ln.hit1`).
  - **Open in VS Code (`#vsl`)**: `vscode://file/<abs_path>:<line_start>:1` URI link.
  - **Open via server (`#vsb`)**: `POST /api/open` which invokes `code --goto <abs_path>:<line_start>:1` on the host.

---

## 5. Indexing Another Folder (`--root` / `CODESEARCH_ROOT`)

You do not need to copy `tools/codesearch/` into another directory to give that directory its own isolated search index and graph. Pass `-r` / `--root <folder>` (or set `CODESEARCH_ROOT=<folder>`) and `codesearch` stores `<folder>/.codesearch/codesearch.db` inside the target folder while serving `vis-network` and parsers from this repository:

```powershell
# 1. Index a separate folder (e.g. a story/notes folder of .md and .txt files)
python F:\AI\viwo\virtual-world\tools\codesearch.py --root "C:\Users\Tommy\Documents\Books\millwood" index

# 2. Embed its sections, filenames, and prose via LM Studio
python F:\AI\viwo\virtual-world\tools\codesearch.py --root "C:\Users\Tommy\Documents\Books\millwood" embed

# 3. Search from the CLI
python F:\AI\viwo\virtual-world\tools\codesearch.py --root "C:\Users\Tommy\Documents\Books\millwood" "your search query"

# 4. Launch the Web UI on that folder (falls back automatically to the docs/section overview graph)
python F:\AI\viwo\virtual-world\tools\codesearch.py --root "C:\Users\Tommy\Documents\Books\millwood" serve --port 5003
```

---

## Where it lives

- `tools/codesearch.py` - CLI wrapper script
- `tools/codesearch/config.py` - paths, ignore rules, LM Studio endpoint/model settings, BM25 and RRF weights
- `tools/codesearch/db.py` - SQLite schema (`files`, `nodes`, `edges`, `refs`, `node_parts`, `vec_cache`, `nodes_fts`), identifier word splitter, stats
- `tools/codesearch/indexer.py` - incremental scanner, parser dispatcher, and cross-file edge resolver
- `tools/codesearch/embedder.py` - 4-part text builder, path-tier ordering, parallel LM Studio batch embedder, `VectorIndex`
- `tools/codesearch/search.py` - `Searcher` combining FTS5 BM25 and 4-part cosine similarity via RRF
- `tools/codesearch/graph.py` - symbol lookup, `callers`, `callees`, `references`, `neighborhood`, `outline`
- `tools/codesearch/cli.py` - CLI subcommands and output formatting
- `tools/codesearch/mcp_server.py` - FastMCP stdio server with 6 agent tools
- `tools/codesearch/app.py` & `tools/codesearch/templates/index.html` - Flask web UI and `vis-network` visualizer
- `tools/codesearch/parsers/py_parser.py` - Python `ast` + `tokenize` extractor
- `tools/codesearch/parsers/ts_parser.mjs` & `tools/codesearch/parsers/js_bridge.py` - Node 24 TypeScript/JavaScript extractor
- `tools/codesearch/parsers/md_parser.py` - Markdown and plain-text extractor
- `tools/codesearch/parsers/html_parser.py` - HTML and inline `<script>` extractor
- `tests/test_codesearch_parsers.py` & `tests/test_codesearch_db.py` - 21 unit and integration tests

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply`  -  relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes**  -  [[Engine Config]], [[Event Log Export]], [[Event Stream]], [[Inspector Panels]], [[NL Editor]], [[Recent Edits & Undo]]

<!-- connected:end -->
