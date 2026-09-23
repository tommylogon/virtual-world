# Domain & Role Tags — the population chain

The convention that lets `engine/population.py` (task-9) auto-furnish an area from
the library. Filed by task-324.

## The chain

```
area domain tags
  -> furniture carrying a role tag (display / container / storage)
       AND at least one matching domain tag
  -> items carrying at least one matching domain tag
```

Matching is **plain set intersection**. The same domain tag must appear at all three
levels; that is the whole mechanism. Placement uses the existing spatial edges:
`on` / `beside` for `display`, `in` for `container` / `storage`, `at` for floors.

## Four kinds of tag

Tag metadata files live in `data/library/tags/`. `category` says what a tag *is*;
this doc covers the four kinds the library actually relies on.

| Kind | Examples | What it says | Used by the chain? |
|------|----------|--------------|--------------------|
| **Setting** | `interior`, `exterior`, `outdoor`, `underground`, `mansion`, `goblin_camp` | *WHERE* an area is | No |
| **Domain** | `kitchen`, `library`, `occult`, `bedroom`, `medical`, `garden`, `shrine`, `training`, `dining`, `loot`, `settlement` | What a place is *FOR* | **Yes — the chain key** |
| **Role** | `display`, `container`, `storage` | *HOW* a piece accepts placement | **Yes — selects placement targets** |
| **Descriptive** | `wooden`, `metal`, `paper`, `ritual`, `plant` | Material, theme, concept | No |

Setting and domain tags coexist on the same area. `data/library/areas/library.json`
is `["interior", "mansion", "library", "paper"]` — where it is, what it is for, what
it holds.

## Rules

1. **A domain tag must mean the same thing at all three levels.** If `library` is on
   an area, it must also be on the furniture that stores books and on the books.
2. **Generic furniture carries the role only.** `table` and `shelves` are
   `[furniture, display]`, never `[..., library]` — a domain on a generic piece makes
   it match *every* area with that domain, which is usually wrong.
3. **Domain-specific furniture carries role + domain.** `bookshelf_item` is
   `[furniture, display, library]`; `stove` is `[furniture, kitchen, cooking]`;
   `crib` is `[furniture, container, nursery, bedroom]`.
4. **Every tag used gets a tag file** in `data/library/tags/`. New files carry
   `category` / `contexts` / `implies` / `applies_to` alongside the legacy fields.
5. **Do not invent domains nothing uses.** A domain should have at least one area,
   one piece of furniture, and one item — otherwise the chain can never fire.

## Worked example — a library

```jsonc
// data/library/areas/library.json
"tags": ["interior", "mansion", "library", "paper"]

// data/library/items/bookshelf_item.json   (role + domain -> placement target)
"tags": ["book", "paper", "furniture", "display", "library"]

// data/library/items/book.json             (domain -> candidates to place)
"tags": ["knowledge", "library", "paper"]
```

Population for that area: domain set `{library, paper, interior, mansion}`; furniture
matching = `bookshelf_item` (carries `furniture` + `display` + a domain); items
matching = `book`, `journal`, `letter`, `family_photo`, `crude_map`; each placed `on`
the bookshelf (display role).

## The pass

`tools/tag_domains.py` — dry-run by default, idempotent (only ever adds tags).

```bash
python tools/tag_domains.py                              # report what would change
python tools/tag_domains.py --apply                      # write
python tools/tag_domains.py --apply --domains kitchen,library   # limit to these tags
```

The tables (`AREA_DOMAINS`, `FURNITURE_TAGS`, `ITEM_TAGS`) are keyed by **library file
id** and list the tags to *add*; existing tags are always preserved. `NEEDED_TAGS`
lists every tag the tables reference, and the script creates any missing tag file.

## Verification

```bash
python tools/lint_library.py
```

- `area_tag_gaps` (warning) must stay empty — every library area carries at least one
  tag. This is task-324's exit criterion, measured at 90/90 areas.
- `singleton_tags` (warning) is informational. A place domain legitimately appearing on
  a single unique piece — one `garden_bench` with `garden` — is not a typo and should
  not be force-connected.
- `dead_interests` (error) is a **different** check: it compares character
  `interest_tags` against the **item** tag vocabulary, not tag files. It is task-326's
  scope, not this convention's.

## Related

- [[Library System/Tags System]]
- [[Library System/Library System Overview]]
- [[dev_tasks/inprogress/library/task-324-domain-tag-schema-and-area-furniture-pass|task-324: domain tag schema + area/furniture pass]]
- `docs/virtualWorld/dev_tasks/todo/items/task-9-procedural_item_placement.md` — the population engine that consumes this chain
