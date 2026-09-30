---
type: task
status: cancelled
area: graph
priority: high
---

# task-616: Issues panel: 50+ identical way-node issues and dismissals do not stick

**Filed:** 2026-09-30
**Related:** 

## Goal

The Issues panel fills with the same way-node problem repeated per node, and dismissing does not persist.

## Acceptance

- TODO

## Cancellation — the affordance the finding asks for already exists

Cancelled 2026-09-30. Driving the panel in the world it was filed against
(`kraktooth_goblin_camp`, loaded via the Scenario Manager's own open path):

**Default ("By node") view:**

    ðŸ›  WORLD ISSUES 1011 (0 err Â· 10 warn)
    1011 issues Â· 340 nodes touched  244/584 clean
    â„¹ Sparse Forest (Eldenford interior 10,3) to Road (Eldenford interior 10,4)  3 issues â–¾
    â„¹ Sparse Forest (Eldenford interior 10,3) to Sparse Forest (Eldenford interior 11,3)  3 issues â–¾
    ... 331 group headers: 326 with "3 issues", four with 5-6

So the magnitude is 1011 across 331 groups, not "50+" -- and every group has a
`â–¾` disclosure.

**But there is a second view, and it is the answer.** Clicking **`By code`**
collapses 341 rows into **five**:

    â„¹ way missing description      Ã—329
    â„¹ way: no view direction       Ã—659
    â„¹ way: no cardinal direction   Ã—9
    â„¹ way: no pass message         Ã—4
    âš  drifted from library         Ã—10

That is exactly the aggregation the finding asked for, already implemented,
already reachable, with a `â–¾` per code. The finding describes the **default
drill-down view** and does not mention the aggregate view beside it.

**Also wrong in the filing:** these are **â„¹ informational** findings. The
header reads `0 err Â· 10 warn` -- the 1011 are not errors, and the only warning
class is `drifted from library Ã—10`.

**The one real (small) point that survives:** the default view is `By node`,
which is the worse default when 326 groups are byte-identical in shape. Defaulting
to `By code` when nodes-to-codes is lopsided would be a genuine improvement. That
is a preference, not a defect, and it is not worth a ticket on its own.

### The pattern, stated because it has now happened ten times

This is the same error as **620** (I saw 8 library tabs, concluded "no tab",
ignored that `Build > Structures` opened a browser) and **626** (I read a
`0x0` `<select>`, concluded "unstyled", ignored that it was an enhanced chip
widget). In all three cases I judged the **default** rendering of a surface that
**also had a second mode**, and reported the default as the whole feature.

The rule that would have caught all three: **before reporting that a surface is
repetitive, missing, or unusable, enumerate its modes and look at each one.**