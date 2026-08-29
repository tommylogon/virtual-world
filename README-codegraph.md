# Code Graph Tools — Semantic Codebase Search

A self-contained stack that indexes a codebase into **Neo4j** (AST-extracted
entities + relational edges + per-entity embeddings) and exposes it to agents
via an **MCP server**. Works with any MCP-capable harness (DSH, Claude Desktop,
Claude Code, Cursor, FastMCP clients, etc.).

```
repo source ──► tools/build_code_graph.py ──► Neo4j (Embeddable nodes + edges + vectors)
                                                   ▲
LM Studio (embeddings) ────────────────────────────┘
                                                   │
tools/code_graph_mcp.py (MCP server) ──tools───────┘
```

---

## Why this instead of other options

- **No native parsers.** Python via stdlib `ast`; JS via acorn (Node, shelled
  out once per file); docs via heading splitting; JSON via structure walk.
  Nothing crashes with native-DLL issues on Windows (tree-sitter, chroma, and
  onnxruntime all failed on the author's machine — that's why this exists).
- **100% coverage of indexable files.** Code + comments + docs + library data,
  each with its own embedding.
- **Hybrid retrieval.** Semantic (cosine over an ANN vector index) *and*
  keyword (token ranking) — whichever fits the query.

---

## Requirements

| Piece | What | Notes |
|---|---|---|
| Python 3.10+ | builder + MCP server | stdlib `ast`, `requests`, `neo4j` driver |
| Node 18+ | JS extraction | `acorn` + `acorn-walk` (in `package.json` of repo root) |
| Neo4j 5.x | storage | vector index must be 768-dim, nomic-compatible |
| LM Studio (or any OpenAI-compatible endpoint) | embeddings | `text-embedding-nomic-embed-text-v1.5` = 768 dim |

Install Python deps:

```bash
pip install requests neo4j
npm install   # for acorn (JS extraction)
```

---

## 1. Build the index

```bash
python tools/build_code_graph.py <root> [--clear-old] [--no-embed]
```

- `<root>` — repo root (defaults to the repo containing the script).
- `--clear-old` — delete that root's existing entities before rebuilding.
- `--no-embed` — skip the LM Studio embedding step (index metadata only).

What it does:

1. **Walks** `<root>` for `.py`, `.js`, `.mjs`, `.md`, `.json` (skips
   `node_modules`, `__pycache__`, vendor dirs).
2. **Extracts** per-language:
   - Python: modules, classes, methods, functions (with signatures, docstrings,
     call graphs, imports) via stdlib `ast`.
   - JS: classes, methods, functions, arrow functions via acorn/Node.
   - Markdown: one entity per heading section (`##`/`###`).
   - JSON: one entity per top-level library entry (items/areas/characters),
     **plus one per nested item** inside areas/containers.
   - Comments: every `#` / `//` / `/* */` comment → its own entity, tied to
     the innermost enclosing function.
3. **Stores** entities as Neo4j nodes (`:Embeddable` + a kind label) with
   `qualified_name`, `filepath`, `line_start/end`, `docstring`, `signature`,
   `source_code`, `root_path`, `language`.
4. **Wires edges**: `DEFINES` (file→symbol), `CONTAINS` (class→method),
   `CALLS` (caller→callee, by name), `IMPORTS` (file→module), `INHERITS`.
5. **Embeds** every entity via LM Studio and attaches the 768-dim vector.

### Node schema (labels)

| Label | Represents | Key props |
|---|---|---|
| `Embeddable` | every indexed entity (base label) | `qualified_name`, `vector` |
| `CodeFile` | one source/document file | `filepath`, `relative_path`, `language` |
| `CodeClass` | Python/JS class | `bases`, `decorators`, line range |
| `CodeFunction` | free function | `signature`, `source_code` |
| `CodeMethod` | class method | `signature`, `class_qname` |
| `CodeComment` | individual comment | `docstring` = comment text |
| `CodeDoc` | markdown section | `docstring` = section body, `doc_heading` |
| `CodeItem` | library JSON item | `docstring` = name + description + tags |
| `CodeModule` | import target | `name` |

### Relationship schema

| Type | Meaning |
|---|---|
| `DEFINES` | file defines a class/function |
| `CONTAINS` | class contains a method |
| `CALLS` | function/method calls another (by name) |
| `IMPORTS` | file imports a module |
| `INHERITS` | class inherits another |

### Vector index

```cypher
CREATE VECTOR INDEX embaddable_vector IF NOT EXISTS
FOR (n:Embeddable) ON (n.vector)
OPTIONS { indexConfig: { `vector.dimensions`: 768, `vector.similarity_function`: 'cosine' } }
```

---

## 2. Serve via MCP

```bash
python tools/code_graph_mcp.py
```

Serves over **stdio** by default (the standard MCP transport). Register it in
any harness; example DSH `cordis.patch.yml` row:

```yaml
- id: mcp-code-graph
  name: '@deepseek-ai/dsh-mcp-client'
  config:
    serverName: code-graph
    transport: stdio
    command: C:\ProgramData\miniconda3\python.exe
    args: ['F:/AI/viwo/virtual-world/tools/code_graph_mcp.py']
    env:
      NEO4J_URI: 'bolt://localhost:7687'
      NEO4J_USERNAME: 'neo4j'
      NEO4J_PASSWORD: 'password'
      EMBEDDING_BASE_URL: 'http://localhost:1234/v1'
      EMBEDDING_MODEL: 'text-embedding-nomic-embed-text-v1.5'
```

### Environment variables

| Var | Default | Purpose |
|---|---|---|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j endpoint |
| `NEO4J_USERNAME` | `neo4j` | auth |
| `NEO4J_PASSWORD` | `password` | auth |
| `EMBEDDING_BASE_URL` | `http://localhost:1234/v1` | OpenAI-compatible embeddings endpoint |
| `EMBEDDING_MODEL` | `text-embedding-nomic-embed-text-v1.5` | must match index dim (768) |
| `CODEGRAPH_INDEX` | `embeddable_vector` | Neo4j vector index name |
| `CODEGRAPH_ROOT` | `F:\AI\viwo\virtual-world` | default search scope |

---

## 3. Tools (the agent-facing API)

| Tool | What it does |
|---|---|
| `search_code(query, top_k, kind, root)` | Semantic search. Embed the query, ANN search the vector index, return hits with score/path/line/doc. `kind` filters to file/class/function/method/comment/doc/item. `root` scopes to a repo (default = `CODEGRAPH_ROOT`, `"all"` = every indexed repo). |
| `search_keywords(query, top_k, root)` | Keyword search over names/qnames/docstrings/signatures. Good for exact identifiers. |
| `code_callers(name)` | Who calls a function/method (via `CALLS`). |
| `code_callees(name)` | What a function/method calls. |
| `file_structure(path)` | Everything a file defines, with line ranges. |
| `graph_stats()` | Health: entity counts, vector coverage, edge counts. |

Every tool takes plain-text args and returns plain text — its full contract is
exposed to MCP clients (names, descriptions, params).

### MCP resources

| URI | Returns |
|---|---|
| `codegraph://stats` | Health snapshot (same as `graph_stats`). |
| `codegraph://docs` | This document's essentials (schema, tools, usage). |

---

## 4. Maintenance

**Rebuild after code changes:**

```bash
python tools/build_code_graph.py <root> --clear-old
```

**Backfill missing vectors** (safe, idempotent — only touches vector-less nodes):

```bash
python tools/backfill_embeddings.py [root]
```

**Verify:**

```bash
python -c "import asyncio, code_graph_mcp as cg; asyncio.run(cg.mcp.get_tool('graph_stats'))"
```
or just call `graph_stats` from any MCP client.

---

## 5. Troubleshooting

- **"No results" on semantic search but graph has entities** — LM Studio down,
  or the vector index isn't ONLINE: `SHOW VECTOR INDEXES`.
- **Dimension mismatch on query** — index is 768; ensure
  `EMBEDDING_MODEL` returns 768-dim vectors (nomic). Qwen3-embed (1024-dim)
  will NOT match a 768 index.
- **JS files missing** — ensure `node` + `acorn` installed, and
  `tools/extract_js.mjs` exists. The builder shells `node extract_js.mjs <file> <rel>`.
- **Comments missing** — they're line-based; a comment must be `#`/`//`
  (block `/* */` single-line supported).
- **Search picks up stale docs** — docs are section-chunks; the `qualified_name`
  is `<path>::<section title>`. Clearing a root with `--clear-old` then
  rebuilding resets everything.
