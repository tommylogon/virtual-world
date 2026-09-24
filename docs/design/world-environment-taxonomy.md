# World Environment Taxonomy

**Status:** design reference (data-first; nothing here is engine behaviour yet)
**Related:** task-497 (WorldPainter biome/feature taxonomy), task-496 (grid→graph
compiler), task-495 (scope grids + 3-mode editor), task-398 (deterministic
generation), `engine/biomes.py`, `data/worldpainter/biomes.json`

## Purpose

A vocabulary for procedural worldbuilding that is **granular enough to author
with and structured enough to generate from**. The first shipped slice
(`data/worldpainter/biomes.json`, task-497) defined 16 biomes and 9 features.
This document expands the vocabulary to **170 environmental categories** and
fixes the record shape so the same data can drive biome placement, description
fragments, forage tables, hostiles, and biome-neighbour sanity checks.

Two distinctions this taxonomy keeps deliberately:

- **Biome / ecosystem** vs **terrain / landscape feature** vs **human-altered
  environment**. A cobblestone road is not a biome, but a world generator wants
  it in the same environmental vocabulary.
- **Gameplay category** vs **strict ecology**. "Jungle" is a useful gameplay
  bucket, not a formal ecotype; it is tagged as such.

## Record shape (target schema per entry)

Every category becomes one record. This is the shape `data/worldpainter/biomes.json`
should converge on (fields are additive; absent = unknown, never guessed):

```text
BIOME: Temperate Mixed Forest

Climate:
Temperature:
Rainfall:
Elevation:
Terrain:

Vegetation:      - ...
Resources:       - ...
Common Creatures:- ...
Rare Creatures:  - ...
Hazards:         - ...

Natural Neighbors:    - ...
Unlikely Neighbors:   - Hot Desert, Tropical Rainforest, Polar Ice
Transition Biomes:    - Forest-Steppe, Forest Meadow, Riparian Forest, Young Regrowth

Human Development:    - Hunting trails, Logging camps, Dirt roads, Farms, Villages

Engine tags:          forest, mixed, trees          # feed engine/foraging.py
Forage skills:        survival, nature
Floor:                grass
```

The generator rule this exists for: **a pine forest next to a mountain stream is
normal; a tropical rainforest directly beside an arctic tundra is bizarre unless
there is a magical/climatic reason.** `Natural Neighbors` / `Unlikely Neighbors`
/ `Transition Biomes` are what make adjacency checkable. Every biome must also
map to at least one engine area tag recognised by `engine/foraging.py` so a
painted area forages with the existing machinery (task-497 acceptance).

---

# I. Temperate forests

1. **Temperate Deciduous Forest** — oak, beech, maple, birch, ash; deer, boar, foxes, wolves, bears, rabbits, birds; mushrooms, berries, hardwood, herbs, streams. *Neighbors:* meadow, grassland, river valley, mixed forest, hills, farmland.
2. **Temperate Mixed Forest** — deciduous mixed with spruce/fir/pine; the common transitional forest. *Resources:* timber, nuts, berries, mushrooms, game, resin. *Neighbors:* deciduous forest, coniferous forest, meadow, hills, wetlands.
3. **Oak Forest** — large mature oaks, dense leaf litter, acorns, hollows. *Creatures:* deer, boar, squirrels, birds, foxes, badgers. *Neighbors:* meadow, farmland, mixed forest.
4. **Beech Forest** — tall pale trunks, heavy canopy, sparse understory. *Resources:* beechwood, nuts, fungi, leaf litter. *Neighbors:* mixed forest, hills, mountain foothills.
5. **Birch Forest** — pale bark, lighter canopy, grasses/shrubs beneath. *Creatures:* deer, hare, birds, insects. *Resources:* birch bark, sap, firewood. *Neighbors:* conifer forest, tundra transition, meadow.
6. **Maple Forest** — dense broadleaf, rich autumn colour, productive soils. *Resources:* hardwood, sap, nuts, fungi. *Neighbors:* deciduous forest, hills, river valleys.
7. **Ash Forest** — tall trees, moist rich soil, often near rivers. *Neighbors:* river forest, wetland, meadow, deciduous forest.
8. **Alder Forest** — water-loving trees, often saturated ground. *Neighbors:* marsh, swamp, riverbank, wet meadow.
9. **Riparian Forest** — forest bordering a river/stream. *Resources:* water, fish, reeds, fertile soil, timber. *Creatures:* beavers, otters, deer, amphibians, waterfowl. *Neighbors:* river, meadow, floodplain, forest.
10. **Floodplain Forest** — flat forest periodically inundated. *Resources:* exceptionally fertile soil, timber, fish, reeds. *Neighbors:* river, marsh, meadow, lake.
11. **Old-Growth Forest** — ancient trees, fallen trunks, multiple canopy layers, huge fungal networks. *Creatures:* bears, wolves, owls, deer, insects, fungi-dependent species. *Neighbors:* younger forest, hills, wetlands.
12. **Young Regrowth Forest** — dense saplings after fire/logging/storm/abandonment. *Resources:* berries, young timber, game. *Neighbors:* old forest, meadow, burned forest, farmland.
13. **Pine Forest** — mostly pine, acidic soils, needles, cones, resin. *Resources:* resin, timber, pine nuts, mushrooms. *Creatures:* deer, squirrels, wolves, birds. *Neighbors:* mixed forest, heath, hills.
14. **Spruce Forest** — dark dense conifer, low understory. *Resources:* timber, resin, mushrooms. *Neighbors:* fir forest, mixed forest, mountain forest.
15. **Fir Forest** — tall firs, shaded floor, cooler and wetter. *Neighbors:* spruce forest, mountain slopes, mixed forest.
16. **Larch Forest** — coniferous but seasonally shedding needles; colder continental climates. *Neighbors:* pine forest, mountain forest, subalpine woodland.
17. **Coniferous Woodland** — general spruce/fir/pine woodland. *Resources:* timber, resin, mushrooms, game. *Neighbors:* mixed forest, heath, mountains.
18. **Temperate Rainforest** — very wet, mosses/ferns, enormous trees. *Creatures:* deer, bears, wolves, amphibians, countless insects. *Resources:* timber, fungi, medicinal plants. *Neighbors:* coastal forest, river valleys, mountains.
19. **Moss Forest** — extremely heavy moss and lichen. *Neighbors:* rainforest, bog, wetland, mountain forest.
20. **Cloud Forest** — cool, constantly humid, often on mountains. *Resources:* orchids, moss, medicinal plants, water. *Creatures:* birds, monkeys, reptiles, amphibians. *Neighbors:* montane forest, grassland, mountain slopes.

# II. Boreal / cold forests

21. **Boreal Forest / Taiga** — huge coniferous zone, cold winters. *Creatures:* moose, wolves, bears, lynx, foxes, hares. *Resources:* timber, fur, resin, berries, mushrooms. *Neighbors:* tundra, wetlands, mountains, birch woodland.
22. **Taiga Wetland** — boreal forest over saturated ground. *Creatures:* mosquitoes, moose, waterfowl, frogs. *Neighbors:* bog, lake, taiga.
23. **Boreal Pine Woodland** — open pine-dominated northern forest. *Resources:* pine resin, timber, berries. *Neighbors:* taiga, heath, tundra.
24. **Boreal Birch Woodland** — birch at the northern forest edge. *Neighbors:* taiga, tundra, alpine terrain.
25. **Subarctic Woodland** — sparse, stunted trees. *Neighbors:* tundra, taiga, alpine meadow.
26. **Krummholz** — wind-stunted trees near treeline. *Neighbors:* alpine meadow, scree, tundra.

# III. Tropical forests

27. **Tropical Rainforest** — extremely dense, warm, wet. *Creatures:* monkeys, big cats, snakes, parrots, insects, frogs. *Resources:* fruit, hardwood, medicinal plants, vines, latex, spices. *Neighbors:* rivers, swamps, jungle clearings, mountains.
28. **Tropical Seasonal Forest** — wet/dry seasonal tropical woodland. *Neighbors:* savanna, rainforest, grassland.
29. **Tropical Dry Forest** — pronounced dry season, many deciduous trees. *Creatures:* monkeys, deer, reptiles, birds. *Neighbors:* savanna, scrubland, seasonal forest.
30. **Monsoon Forest** — extreme seasonal rainfall. *Neighbors:* rainforest, grassland, river valleys.
31. **Jungle** — dense tropical vegetation; a *gameplay* category, not a strict ecotype. *Resources:* fruit, vines, timber, herbs, water. *Hazards:* visibility, predators, insects, disease.
32. **Tropical Cloud Forest** — high-altitude humid forest. *Creatures:* birds, monkeys, amphibians, insects. *Neighbors:* montane forest, alpine grassland.
33. **Mangrove Forest** — salt-tolerant coastal trees in tidal mud. *Creatures:* fish, crabs, crocodiles, birds. *Resources:* fish, shellfish, wood, salt. *Neighbors:* tidal flats, estuary, coral coast.
34. **Bamboo Forest** — dense bamboo stands, enormous biomass. *Resources:* bamboo, shoots, fibre. *Creatures:* rodents, insects, birds, specialised herbivores. *Neighbors:* rainforest, river valleys.
35. **Palm Forest** — palm-dominated tropical woodland. *Resources:* fruit, fibres, palm oil, nuts. *Neighbors:* rainforest, swamp, savanna.

# IV. Grasslands

36. **Temperate Grassland** — open grass plains. *Creatures:* deer, horses, wolves, rodents, birds. *Resources:* grasses, grazing animals, fertile soil. *Neighbors:* forest, farmland, river valleys.
37. **Prairie** — tall-grass temperate grassland. *Resources:* fertile soil, grasses, grazing animals. *Neighbors:* deciduous forest, river, farmland.
38. **Steppe** — dry temperate short-grass. *Creatures:* horses, antelope, wolves, rodents. *Neighbors:* semi-desert, forest-steppe, mountains.
39. **Forest-Steppe** — patchwork of grassland and forest. *Neighbors:* forest, steppe, farmland.
40. **Savanna** — tropical grassland with scattered trees. *Creatures:* large herbivores, predators, birds, reptiles. *Resources:* grasses, wood, fruit, grazing animals. *Neighbors:* dry forest, scrubland, seasonal woodland.
41. **Tropical Grassland** — strong wet/dry seasons. *Neighbors:* rainforest, savanna, wetlands.
42. **Flooded Grassland** — seasonally inundated. *Creatures:* amphibians, fish, waterfowl, grazing animals. *Neighbors:* river, marsh, wetland.
43. **Alpine Meadow** — high-altitude grass/flower meadow. *Resources:* herbs, flowers, grazing plants. *Neighbors:* mountain slopes, scree, glaciers, alpine forest.
44. **Subalpine Meadow** — below alpine zone, shrubs and shorter trees. *Neighbors:* conifer forest, alpine meadow, mountain slopes.
45. **Coastal Grassland** — windy grassland near sea cliffs or dunes. *Neighbors:* beaches, cliffs, scrubland.

# V. Shrubland / scrub

46. **Temperate Shrubland** — dense bushes, low trees, grasses. *Neighbors:* grassland, forest, farmland.
47. **Mediterranean Scrub** — dry summers, evergreen shrubs, aromatic plants. *Resources:* herbs, olives, berries, firewood. *Neighbors:* Mediterranean woodland, coast, dry grassland.
48. **Thorn Scrub** — dry thorny bushes. *Creatures:* reptiles, insects, small mammals. *Neighbors:* desert, savanna, dry grassland.
49. **Chaparral** — dense drought-adapted shrubland. *Hazards:* wildfire. *Neighbors:* dry forest, grassland, mountains.
50. **Heathland** — low shrubs, heather, acidic soils. *Resources:* berries, peat, herbs. *Neighbors:* moorland, pine forest, bog.
51. **Moorland** — open wet/cool shrub-and-grass landscape. *Resources:* peat, heather, grazing. *Neighbors:* bog, heath, upland grassland.

# VI. Wetlands

52. **Freshwater Marsh** — shallow standing water, reeds and grasses. *Creatures:* frogs, fish, waterfowl, insects. *Resources:* reeds, fish, medicinal plants. *Neighbors:* lake, river, meadow.
53. **Salt Marsh** — tidal coastal wetland. *Creatures:* crabs, fish, birds. *Neighbors:* estuary, mudflat, coast.
54. **Swamp** — standing water with trees/shrubs. *Creatures:* crocodiles, snakes, frogs, insects, birds. *Resources:* reeds, fish, timber, medicinal plants. *Neighbors:* river, lake, floodplain, wet forest.
55. **Mangrove Swamp** — tropical coastal tidal swamp. *Neighbors:* ocean, estuary, mangrove forest.
56. **Bog** — acidic, nutrient-poor, peat and moss. *Resources:* peat, berries, moss, medicinal plants. *Hazards:* unstable ground. *Neighbors:* heath, taiga, forest.
57. **Fen** — groundwater-fed wetland, more nutrient-rich than bog. *Resources:* reeds, grasses, medicinal plants. *Neighbors:* meadow, marsh, river.
58. **Peatland** — general peat-forming wet environment. *Resources:* peat, moss, water, berries. *Neighbors:* bog, fen, moorland.
59. **Reedbed** — dense tall reeds around shallow water. *Resources:* reeds, fish, bird eggs, thatching material. *Neighbors:* marsh, lake, river.
60. **Floodplain** — flat land periodically flooded by a river. *Resources:* exceptionally fertile soil, fish, reeds. *Neighbors:* river, forest, meadow, farmland.
61. **River Delta** — multiple distributary channels and wetlands. *Resources:* fish, fertile soil, reeds, waterfowl. *Neighbors:* river, marsh, coast.
62. **Estuary** — freshwater meets saltwater. *Creatures:* fish, shellfish, birds. *Neighbors:* river, ocean, mudflat, salt marsh.

# VII. Deserts & arid environments

63. **Hot Sand Desert** — large dunes, sparse vegetation. *Creatures:* snakes, lizards, insects, desert mammals. *Resources:* sand, salt, minerals, oasis potential. *Neighbors:* rocky desert, scrubland, oasis.
64. **Rocky Desert** — bare rock, gravel, sparse vegetation. *Resources:* stone, ore, fossils. *Neighbors:* mountains, sand desert, scrub.
65. **Gravel Desert / Reg** — flat expanses of stones. *Neighbors:* rocky desert, dunes, dry mountains.
66. **Salt Flat** — extremely saline flat terrain. *Resources:* salt, minerals. *Hazards:* extreme heat, lack of water. *Neighbors:* desert; salt marsh only in unusual transitional regions.
67. **Dry Basin** — enclosed arid depression. *Resources:* salt, clay, mineral deposits. *Neighbors:* mountains, desert.
68. **Semi-Desert** — grass and shrubs mixed with bare soil. *Neighbors:* steppe, desert, scrubland.
69. **Thorn Desert** — extremely dry thorn-dominated landscape. *Neighbors:* thorn scrub, savanna, rocky desert.
70. **Cold Desert** — very low precipitation, cold climate. *Creatures:* hardy rodents, foxes, birds. *Neighbors:* tundra, mountains, steppe.
71. **Oasis** — permanent water in arid terrain. *Resources:* freshwater, palms, fruit, reeds, fish. *Neighbors:* desert. *Special:* extremely important settlement location.
72. **Desert Wadi** — dry river channel that floods seasonally. *Resources:* groundwater, fertile sediment, vegetation. *Neighbors:* desert, oasis, mountains.
73. **Desert Scrub** — low drought-resistant shrubs. *Neighbors:* semi-desert, rocky desert.

# VIII. Mountains

74. **Mountain Foothills** — lower slopes transitioning to plains/forest. *Neighbors:* grassland, forest, valleys.
75. **Low Mountains** — moderate elevation, forest and valleys. *Resources:* timber, stone, ore, game. *Neighbors:* forest, foothills, high mountains.
76. **High Mountains** — steep rocky terrain. *Resources:* metals, stone, gems, snowmelt. *Creatures:* goats, eagles, bears, mountain predators. *Neighbors:* foothills, alpine meadow, glaciers.
77. **Alpine Mountains** — above treeline. *Resources:* stone, ore, herbs. *Hazards:* avalanches, cold, falls. *Neighbors:* alpine meadow, glaciers, scree.
78. **Volcanic Mountains** — volcanic peaks and slopes. *Resources:* obsidian, sulphur, metals, fertile volcanic soil. *Hazards:* eruptions, gas, lava. *Neighbors:* volcanic plains, forest, ash fields.
79. **Mountain Valley** — long valley enclosed by mountains. *Resources:* water, fertile soil, timber, game. *Neighbors:* mountains, river, forest, meadow.
80. **Alpine Valley** — high cold valley. *Neighbors:* alpine meadow, mountain slopes, glacier.
81. **Mountain Pass** — natural route through mountains. *Resources:* strategic travel corridor. *Neighbors:* two valleys or mountain regions.
82. **Mountain Scree** — loose broken rock on steep slopes. *Creatures:* mountain goats, birds, small mammals. *Hazards:* rockfalls.
83. **Rocky Plateau** — high flat terrain. *Neighbors:* mountains, valleys, steppe, desert.
84. **Mountain Cliff** — exposed steep rock. *Creatures:* eagles, vultures, mountain goats. *Resources:* stone, nesting sites.
85. **Glacier** — permanent ice. *Resources:* freshwater, ice, rare minerals. *Neighbors:* alpine mountains, snowfields.
86. **Glacial Valley** — valley carved by glaciers; U-shaped, lakes, moraines. *Neighbors:* mountains, forests, alpine meadows.
87. **Volcanic Crater** — depression around a volcanic vent. *Resources:* minerals, sulphur, geothermal activity. *Hazards:* toxic gases.
88. **Geothermal Region** — hot springs, fumaroles, steam vents. *Resources:* minerals, hot water. *Creatures:* specialised organisms. *Neighbors:* volcanic terrain, mountains.

# IX. Tundra & polar

89. **Arctic Tundra** — treeless cold plain. *Creatures:* reindeer, foxes, hares, birds. *Resources:* berries, moss, lichens, fur. *Neighbors:* taiga, mountains, ice.
90. **Alpine Tundra** — treeless high-altitude terrain. *Neighbors:* alpine meadow, mountains, scree.
91. **Coastal Tundra** — cold tundra near ocean. *Creatures:* seabirds, nearby seals, foxes. *Neighbors:* Arctic coast, tundra.
92. **Permafrost Plain** — permanently frozen soil. *Hazards:* unstable thaw zones. *Neighbors:* tundra, taiga.
93. **Polar Ice Sheet** — permanent massive ice. *Creatures:* extremely specialised wildlife. *Neighbors:* polar coast.
94. **Snowfield** — seasonal or permanent snow-covered terrain. *Neighbors:* mountains, tundra, glacier.
95. **Arctic River Valley** — short seasonal rivers through tundra. *Resources:* freshwater, fish, migration routes. *Neighbors:* tundra, mountains.

# X. Coastal environments

96. **Sandy Beach** — sand coast, dunes, tidal zone. *Resources:* shellfish, driftwood, fish. *Neighbors:* dunes, ocean, coastal grassland.
97. **Pebble Beach** — rocky/pebbly shoreline. *Resources:* stones, shellfish, driftwood. *Neighbors:* cliffs, sea, coastal woodland.
98. **Rocky Coast** — exposed rock shoreline. *Creatures:* seabirds, seals, crabs, tidepool organisms. *Neighbors:* cliffs, ocean.
99. **Sea Cliffs** — high coastal cliffs. *Resources:* stone, bird nests. *Hazards:* falls, erosion. *Neighbors:* rocky coast, grassland.
100. **Coastal Dunes** — wind-shaped sand hills. *Resources:* grasses, salt-tolerant plants, groundwater. *Neighbors:* beach, coastal grassland, scrub.
101. **Tidal Flats** — mud/sand exposed at low tide. *Creatures:* worms, shellfish, crabs, birds. *Neighbors:* estuary, salt marsh, ocean.
102. **Coral Reef** — warm shallow marine ecosystem. *Creatures:* fish, corals, crustaceans, molluscs. *Resources:* fish, shells, coral. *Neighbors:* tropical coast, lagoon.
103. **Coastal Lagoon** — shallow water separated from ocean by a barrier. *Creatures:* fish, birds, shellfish. *Neighbors:* dunes, beach, reef, marsh.
104. **Rocky Tidepool** — small pools trapped between tides. *Creatures:* crabs, anemones, shellfish, small fish. *Neighbors:* rocky coast.
105. **Kelp Forest** — cold nutrient-rich coastal waters. *Creatures:* fish, seals, otters, crustaceans. *Neighbors:* rocky coast, open ocean.

# XI. Rivers & freshwater

106. **Mountain Stream** — cold, fast, clear water. *Resources:* freshwater, fish, stone. *Neighbors:* mountains, forest, alpine meadow.
107. **Forest Stream** — small shaded stream. *Creatures:* fish, frogs, insects, otters. *Neighbors:* forest, meadow, wetlands.
108. **River** — major freshwater channel. *Resources:* fish, drinking water, fertile soil, transport. *Neighbors:* floodplain, riparian forest, meadow, farmland.
109. **Slow River** — wide, slower lowland river. *Neighbors:* marsh, floodplain, farmland, forest.
110. **Rapids** — fast turbulent river section. *Resources:* fish, water power. *Hazards:* drowning.
111. **Waterfall** — vertical drop in a river. *Resources:* freshwater, fish, sometimes caves. *Neighbors:* forest, cliffs, river.
112. **Oxbow Lake** — former river channel isolated from the main river. *Creatures:* fish, frogs, birds. *Neighbors:* floodplain.
113. **Freshwater Lake** — large inland body of water. *Resources:* fish, reeds, freshwater, clay. *Neighbors:* forest, meadow, marsh, mountains.
114. **Mountain Lake** — cold high-altitude lake. *Resources:* freshwater, fish, stone. *Neighbors:* mountains, alpine meadow.
115. **Marsh Lake** — shallow lake surrounded by wetlands. *Creatures:* amphibians, fish, birds. *Neighbors:* marsh, reedbed.

# XII. Caves & underground

116. **Limestone Cave** — dissolution caves; stalactites, underground streams. *Resources:* limestone, minerals, groundwater. *Creatures:* bats, insects.
117. **Lava Tube** — cave formed by ancient lava flows. *Resources:* volcanic rock. *Neighbors:* volcanic terrain.
118. **Karst Cavern** — large interconnected limestone cave system. *Resources:* minerals, groundwater. *Hazards:* collapses, underground water.
119. **Underground River** — river flowing beneath the surface. *Creatures:* cave-adapted fish/invertebrates. *Neighbors:* cave systems.
120. **Underground Lake** — subterranean standing water. *Resources:* freshwater, cave fish, minerals. *Neighbors:* caves, underground rivers.
121. **Crystal Cave** — unusually abundant crystals/mineral deposits. *Resources:* crystals, gemstones, minerals.
122. **Deep Cave** — extremely dark, deep cave network. *Creatures:* bats, cave insects, strange adapted fauna. *Hazards:* darkness, collapse, isolation.
123. **Mine** — artificial underground excavation. *Resources:* ore, coal, gems, stone. *Neighbors:* mountains, hills.
124. **Abandoned Mine** — old mine reclaimed by nature. *Creatures:* bats, rodents, possibly monsters. *Resources:* abandoned tools, ore, scrap, timber.

# XIII. Special / extreme biomes

125. **Burned Forest** — recently burned woodland. *Resources:* charcoal, surviving roots, ash, exposed minerals. *Creatures:* scavengers, insects. *Neighbors:* forest, grassland, regrowth.
126. **Fire-Regrowth Zone** — young forest recovering from wildfire. *Resources:* berries, herbs, young timber. *Neighbors:* burned forest, mature forest.
127. **Ash Plain** — ground covered by volcanic or fire ash. *Resources:* minerals, eventual fertile soil. *Hazards:* dust, toxic compounds. *Neighbors:* volcano, grassland, forest.
128. **Badlands** — deeply eroded dry terrain. *Resources:* fossils, clay, exposed minerals. *Creatures:* reptiles, hardy mammals. *Neighbors:* desert, steppe.
129. **Canyon** — deep erosion-cut valley. *Resources:* stone, sheltered watercourses. *Creatures:* birds, reptiles, mountain wildlife. *Neighbors:* desert, plateau, river.
130. **Ravine** — smaller steep-sided valley. *Neighbors:* forest, hills, river.
131. **Sinkhole Region** — karst terrain with sudden depressions. *Hazards:* collapses, underground entrances. *Neighbors:* limestone forest, karst caves.
132. **Mudflat** — soft wet sediment, coastal or riverine. *Creatures:* worms, shellfish, birds. *Neighbors:* marsh, estuary, tidal flats.
133. **Landslide Zone** — recently disturbed steep terrain. *Resources:* exposed stone, minerals, fallen timber. *Hazards:* unstable ground. *Neighbors:* mountains, hills, forest.
134. **River Gravel Bar** — deposited stones and sand in river channels. *Resources:* gravel, sand, occasionally gemstones. *Neighbors:* river, floodplain.
135. **Natural Hot Spring** — geothermal spring with warm water. *Resources:* warm freshwater, minerals. *Neighbors:* volcanic/geothermal terrain, mountains.

# XIV. Human / civilised landscapes

Human-altered environments; not biomes, but part of the same generator vocabulary.

136. **Dirt Footpath** — narrow repeatedly used path. *Neighbors:* any inhabited/well-travelled terrain.
137. **Forest Trail** — narrow natural trail through woodland. *Expected:* roots, mud, branches, tracks. *Neighbors:* forest.
138. **Animal Trail** — narrow irregular path created by wildlife. *Expected:* tracks, droppings, feeding signs. *Neighbors:* forest, grassland, mountains.
139. **Hunting Trail** — human/goblin-maintained wilderness path. *Expected:* traps, markers, camps. *Neighbors:* forest, hills, hunting grounds.
140. **Gravel Road** — compacted gravel road. *Traffic:* carts, horses, travellers. *Neighbors:* villages, farms, towns, major roads.
141. **Dirt Road** — wider unpaved road. *Traffic:* wagons, livestock, travellers. *Neighbors:* farmland, villages, forests.
142. **Mud Road** — poorly maintained dirt road. *Hazards:* deep mud, ruts, flooding. *Neighbors:* wetlands, farmland, villages.
143. **Sand Road** — road across sandy terrain. *Expected:* dunes, scrub, desert vegetation. *Neighbors:* desert, coast.
144. **Cobblestone Road** — constructed stone road. *Traffic:* carts, horses, merchants. *Neighbors:* towns, villages, cities.
145. **Paved Road** — engineered durable road (stone, brick, or similar). *Neighbors:* major settlements, cities, trade routes.
146. **Ancient Road** — old constructed road partially reclaimed by nature. *Expected:* broken stones, weeds, trees, ruins. *Neighbors:* forest, ruins, abandoned settlements.
147. **Roman-Style Stone Road** — large engineered road with drainage and substantial foundation. *Expected:* milestones, bridges, roadside structures. *Neighbors:* major settlements.
148. **Farm Track** — narrow route between agricultural fields. *Expected:* fences, irrigation ditches, barns. *Neighbors:* farmland, villages.
149. **Caravan Route** — long-distance trade corridor. *Expected:* camps, wells, waystations, wagon ruts. *Neighbors:* roads, desert, steppe, settlements.
150. **Mountain Pass Road** — engineered route crossing mountains. *Expected:* switchbacks, retaining walls, bridges, guard posts. *Neighbors:* mountains, valleys.

# XV. Agricultural landscapes

151. **Crop Fields** — large cultivated grain/vegetable fields. *Resources:* grain, vegetables, straw. *Neighbors:* farms, villages, roads.
152. **Wheat Fields** — large grain fields. *Resources:* wheat, straw. *Neighbors:* farmland, villages.
153. **Barley Fields** — hardier grain cultivation. *Resources:* barley, straw. *Neighbors:* farmland, grassland.
154. **Rice Paddies** — flooded agricultural fields. *Resources:* rice, fish, reeds. *Neighbors:* wetlands, rivers, tropical/subtropical settlements.
155. **Vegetable Gardens** — small cultivated plots. *Resources:* vegetables, herbs, fruit. *Neighbors:* houses, farms, villages.
156. **Orchard** — fruit trees in organised rows. *Resources:* apples, pears, plums, cherries. *Neighbors:* farms, villages, meadows.
157. **Vineyard** — grape cultivation. *Resources:* grapes, wine. *Neighbors:* Mediterranean/temperate farmland, hills.
158. **Pasture** — managed grazing land. *Resources:* livestock, grass, manure. *Neighbors:* farms, grassland, villages.
159. **Hay Meadow** — grass grown for livestock feed. *Resources:* hay, flowers, insects. *Neighbors:* farmland, pasture, forest.
160. **Terraced Agriculture** — crops on constructed hillside terraces. *Resources:* crops, stone, water management. *Neighbors:* mountains, hills, villages.

# XVI. Settlement transitions

161. **Rural Homestead** — single house plus fields/pens. *Neighbors:* farmland, forest, road.
162. **Farmstead** — house, barn, stable, fields, pasture. *Neighbors:* crop fields, pasture, farm tracks.
163. **Hamlet** — tiny cluster of houses. *Neighbors:* farms, roads, woodland.
164. **Village** — larger permanent settlement; houses, wells, livestock, workshops, fields. *Neighbors:* farmland, roads, forest.
165. **Frontier Village** — settlement at the edge of civilisation; palisade, militia, hunters, traders. *Neighbors:* wilderness.
166. **Abandoned Village** — settlement reclaimed by nature. *Resources:* old tools, timber, stone, food remnants. *Creatures:* rats, foxes, birds, monsters. *Neighbors:* forest, farmland.
167. **Ruined Settlement** — collapsed structures and scattered debris. *Resources:* stone, metal, artefacts. *Neighbors:* wilderness.
168. **Walled Town** — fortified settlement with dense buildings; gates, markets, workshops, guards. *Neighbors:* farmland, roads.
169. **City Outskirts** — transition between city and countryside; workshops, poor housing, farms, roads, refuse.
170. **Urban District** — dense constructed environment; streets, buildings, markets, sewers, alleys.

---

## Deliberately out of scope

This stops at 170 rather than pretending "biome" covers every possible terrain
feature. Further growth should be **new data, not new categories by fiat**:
an added biome must ship the record shape above and validate against
`engine/biomes.py`. See `docs/design/worldpainter-knowledge-and-fog.md` for how
grids, per-agent fog of war, and belief-based travel consume this vocabulary.
