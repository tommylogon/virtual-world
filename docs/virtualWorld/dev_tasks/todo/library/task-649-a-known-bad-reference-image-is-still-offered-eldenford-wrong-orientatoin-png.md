---
type: task
status: todo
area: library
priority: low
---

# task-649: A known-bad reference image is still offered: eldenford - wrong orientatoin.png

**Filed:** 2026-09-30
**Related:** 

## Goal

The WorldPainter reference-image picker lists 19 backgrounds including 'eldenford - wrong orientatoin.png' -- a file whose name says it is the wrong orientation. It sits next to the correct eldenford.png, so an author tracing over the map can pick the wrong one and get a mirrored map. Either rename it out of the directory or have the picker mark it.

## Acceptance

- TODO

## Sweep of the backgrounds directory (2026-09-30) — leaving this one to Tommy

`/api/world/painter/backgrounds` lists 19 files in `static/images/backgrounds`,
nearly all ~4 MB. Beyond the known-bad entry, the sweep found:

| file | size | note |
|---|---|---|
| `eldenford - wrong orientatoin.png` | 4,158,067 | named as wrong; sits beside the correct `eldenford.png` |
| `ChatGPT_Image_Sep_22_2026_10_11_21_AM-1790064744611-1790163792966.png` | 4,063,401 | **byte-identical pair** with the row below |
| `ChatGPT_Image_Sep_22_2026_10_11_21_AM-1790064744611.png` | 4,063,401 | |
| `valerious-house-interior-1790164455523.png` | 2,951,917 | timestamped variant of `valerious-house-interior.png` |
| `deep_forest-1790288542838.png` | 4,083,322 | timestamped variant |

**Not actioned deliberately.** Deleting or renaming these is a judgement about
which reference art the author wants to keep, and a wrong guess destroys work.
Two things worth deciding separately:

1. Whether the reference picker should filter. It is a *reference* list used
   while tracing a grid by eye, so a wrong-orientation image in it does real
   damage -- the author traces faithfully onto a mirrored map. Marking rejected
   art (a `rejected: true` sidecar, or a `_rejected/` subdirectory the endpoint
   skips) is safer than deletion and is reversible.
2. Roughly 4 MB of exact duplicates is dead weight in the repo regardless of
   which are kept.