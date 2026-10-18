# Millwood, Oklahoma - Scenario Design Doc (v1)

## 1. Premise

Small working-class close-knit community on the northeast side of Oklahoma City. Mundane suburban life side-by-side with hidden unsettling supernatural phenomena.

Map is about 3 to 3.5 km west to east and 3 km north to south. West Birch Lane to I-44 is 35 to 45 min on foot. Tone is grounded suburban horror.

Off the scale bar: 1 km bar, Birch Ln to I-44 is about 3 bars, so 3 to 3.5 km. 35 to 45 min at 5 km/h, closer to an hour with stops.


Player starts as a local teen tied to one of the named houses. Free movement, no railroaded ending.

## 2. Scopes (top level only)

Settlement `millwood` with 8 district siblings. World scope is placement surface only. All roads, houses, biomes, interiors live inside child scopes.

1. north_millwood (Zoe's House child on Willow St)
2. west_millwood (Jake's on Maple St, Sammy's on Birch Ln)
3. school_campus (North Wing, South Wing, Courtyard, Main Entrance, Arts Annex, field; 2-cell footprint)
4. lakeshore_drive (Lulu's Mansion child)
5. commercial_23rd (Aroma Cafe, 7-Eleven, The Grid, strip mall)
6. east_millwood (skate park child at east edge)
7. south_millwood (Kayla's, Kyrie's, Riverview Cemetery)
8. millwood_woods (trails; wilderness sibling test case)


Not top level: houses, shop interiors, school wings, Lulu interior, skate bowl. Child scopes under task-401 settlement gates, not siblings.

## 3. World Grid (6x4, 8 occupied)

- (1,0) north_millwood
- (2,0) school_campus, grows to (2,0)+(3,0) with footprints
- (3,0) lakeshore_drive
- (1,1) west_millwood
- (2,1) commercial_23rd
- (3,1) east_millwood
- (1,2) south_millwood
- (2,2) millwood_woods, optionally +(3,2)

I-44 east is wall except the skate cell. River south and lake east are natural walls. Woods treeline is soft wall with one or two trail exits. 23rd Street is the seam: paint crossings on both sides.

## 4. Traversal (task-775)

Per passable edge cell, not whole edge. Unpainted edge is wall. Reuse compiler adjacency plus task-401 gateway ways. Unequal widths map by fractional position. Passable facing empty is flagged leads-nowhere and plays dead end. Strict mode. One way per region pair. No world leg. Build commercial_23rd to east_millwood first, or east_millwood to millwood_woods.

## 5. District Notes

All painted inside the district. North: older homes, Willow spine. West: bungalows, Maple and Birch. School: lots, courtyard ring, wings, field, fenced with gaps. Lakeshore: curves, lake edge, mansion grounds. Commercial: strip, lots, back alley. East: loops, skate child, highway wall. South: Oakwood, Cedar, two houses, cemetery, river wall. Woods: trails, gradient, unmarked sites.

## 6. Roster and Lore

Core teens Zoe, Jake, Sammy, Kayla, Kyrie. Lulu. 23rd staff. School staff. Caretaker, dog-walker, skate locals. Lore: mill roots, bungalows, 23rd strip, I-44 cut, class split, school center, phenomena as rumors with mundane covers, Edmond north, Downtown OKC south.

## 7. Runtime

1 min per turn. Start 15:30 school day. Oklahoma fall. Active player is a core teen. Ghost mode off.

## 8. Acceptance

8 districts on 6x4. Nothing painted at world level. School 2-cell footprint. Houses and shops are children. First seam crosses with no world leg. Empty facing edge dead-ends. Proportional mapping on unequal widths. I-44 wall except skate cell. West-east feels like 35 to 45 min.
