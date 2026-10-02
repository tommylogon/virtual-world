"""
Item content pass 1 — the first growth: nature, food and household.

Authored content. **The tables are the work**; the record shapes come from
`item_shapes.py`, so a fix to how a consumable is authored lands in one place and
a pass that makes a claim it cannot back is refused rather than written.

    run     python tools/item_content_pass1.py
    audit   python tools/audit_item_content.py
    test    tests/test_library_content_pass.py

An id already in the library is **skipped, never overwritten** unless ``--force``.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from item_shapes import (LIB, audit, drink, emit, existing, food, pool,  # noqa: E402
                         row, thing, tool, worn, write)

PASS = "pass1"

# (id, description, hunger relief, extra tags)
VEGETABLES = [
    ("carrot", "A carrot, still with the tops on and the soil in its creases.", 20, ["vegetable", "root"]),
    ("cabbage", "A dense white cabbage, the outer leaves left on to keep it fresh.", 22, ["vegetable", "leafy"]),
    ("turnip", "A turnip, rough-skinned and faintly bitter.", 16, ["vegetable", "root"]),
    ("parsnip", "A parsnip, pale and long, sweeter than a carrot after a frost.", 20, ["vegetable", "root"]),
    ("beetroot", "A beetroot, stained purple through the cut end already.", 20, ["vegetable", "root"]),
    ("onion", "A brown onion, papery and honest-smelling.", 18, ["vegetable", "allium"]),
    ("garlic", "A bulb of garlic, the cloves tight as knuckles.", 16, ["vegetable", "allium", "spice"]),
    ("leek", "A leek, washed white and dark green at the top.", 20, ["vegetable", "allium"]),
    ("shallot", "A shallot, small and copper-skinned and sharper than an onion.", 14, ["vegetable", "allium"]),
    ("spring_onion", "A bunch of spring onions, the whites barely thick enough to chop.", 14, ["vegetable", "allium"]),
    ("potato", "A potato, the eyes already sprouting in the dark.", 30, ["vegetable", "root", "staple"]),
    ("sweet_potato", "A sweet potato, orange-fleshed and caramel-sweet once roasted.", 30, ["vegetable", "root"]),
    ("celeriac", "A celeriac root, knobbly as a fist and worth the digging.", 18, ["vegetable", "root"]),
    ("swede", "A swede, purple-topped and dense enough to need a knife.", 20, ["vegetable", "root"]),
    ("kohlrabi", "Kohlrabi, swollen above the ground like a turnip on a stick.", 18, ["vegetable", "root"]),
    ("radish", "A bunch of radishes, red and sharp enough to bring tears.", 12, ["vegetable", "root"]),
    ("beetroot_leaves", "Beetroot leaves, the greens a cook would call the best part.", 14, ["vegetable", "leafy"]),
    ("spinach", "A bundle of spinach, damp and dark green.", 18, ["vegetable", "leafy"]),
    ("swiss_chard", "Swiss chard, red-stemmed and glossy, more colour than spinach.", 18, ["vegetable", "leafy"]),
    ("lettuce", "A head of lettuce, the outer leaves gone and the heart tight.", 16, ["vegetable", "leafy"]),
    ("cos_lettuce", "Cos lettuce, tall and crisp and grown upright in the soil.", 16, ["vegetable", "leafy"]),
    ("endive", "Endive, the bitter inner leaves pale against the green.", 14, ["vegetable", "leafy"]),
    ("chicory", "A chicory, its red-veined leaves bitter enough to need fat with them.", 14, ["vegetable", "leafy"]),
    ("curly_kale", "Curly kale, the leaves so crinkled you could not stack them straight.", 18, ["vegetable", "leafy"]),
    ("broccoli", "A head of broccoli, the crown tight and dark green.", 22, ["vegetable", "flower"]),
    ("cauliflower", "A cauliflower, the curd creamy white and the leaves around it green.", 20, ["vegetable", "flower"]),
    ("brussels_sprout", "A stalk of brussels sprouts, the little heads climbing the stem.", 22, ["vegetable", "stem"]),
    ("courgette", "A courgette, long and dark and growing faster than anyone eats them.", 18, ["vegetable", "fruit"]),
    ("marrow", "A marrow, fat and dull-yellow, to be hollowed and filled.", 20, ["vegetable", "fruit"]),
    ("pumpkin", "A pumpkin, grown so heavy it rests on the soil and splits its stem.", 24, ["vegetable", "fruit"]),
    ("winter_squash", "A winter squash, hard-rinded enough to keep until spring.", 26, ["vegetable", "fruit"]),
    ("butternut_squash", "A butternut squash, bell-shaped and sweet once baked.", 26, ["vegetable", "fruit"]),
    ("peas", "A pod of peas, the little green balls lined up like a row of teeth.", 18, ["vegetable", "legume", "seed"]),
    ("broad_beans", "Broad beans, eaten young and buttered while still tender.", 22, ["vegetable", "legume", "seed"]),
    ("runner_beans", "Runner beans, the pods flat and the beans freckled inside.", 22, ["vegetable", "legume"]),
    ("asparagus", "A bundle of asparagus, pale green and woody at the ends.", 20, ["vegetable", "stem"]),
    ("artichoke", "An artichoke, the bud tight and scaly like something armoured.", 18, ["vegetable", "flower"]),
    ("okra", "Pod after pod of okra, sliced thin or the whole thing stewed.", 18, ["vegetable", "seed"]),
    ("sweetcorn", "An ear of sweetcorn, the kernels pale and dented in rows.", 26, ["vegetable", "grain"]),
    ("aubergine", "An aubergine, glossy dark and heavy for its size.", 18, ["vegetable", "fruit"]),
    ("bell_pepper", "A bell pepper, thick-walled and glossy, one side already dimpling.", 18, ["vegetable", "fruit"]),
    ("chilli_pepper", "A dried chilli, deep red and small enough to be a mistake.", 8, ["vegetable", "spice"]),
    ("cucumber", "A cucumber, cold and snapping and half the seeds already soft.", 14, ["vegetable", "fruit"]),
    ("tomato", "A tomato, ripe and slightly over, smelling of the vine.", 20, ["vegetable", "fruit"]),
    ("green_tomato", "A green tomato, hard as a fist and sour.", 12, ["vegetable", "fruit"]),
    ("tomatillo", "Tomatillos in their papery husks, which is why they do not keep.", 18, ["vegetable", "fruit"]),
    ("horseradish", "A horseradish root, dug up and smelling of nothing pleasant.", 12, ["vegetable", "root", "spice"]),
    ("parsnip_leaf", "Parsnip tops, feathery and worth more than most herbs.", 12, ["vegetable", "leafy"]),
]

# â”€â”€ 2. herbs, medicinals and garden plants â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# (id, description, [tags])
HERBS = [
    ("parsley", "A bunch of parsley, curly and deep green.", ["herb", "culinary"]),
    ("flat_parsley", "Flat-leaf parsley, the kind with the actual flavour.", ["herb", "culinary"]),
    ("thyme", "Thyme, low and woody and grey-green, the smell of it in your hand.", ["herb", "culinary", "medicinal"]),
    ("rosemary", "A sprig of rosemary, the needles stiff and resinous.", ["herb", "culinary", "medicinal"]),
    ("sage", "Grey-green sage leaves, woolly and strong enough to clear a smell.", ["herb", "culinary", "medicinal"]),
    ("oregano", "Wild oregano, pink-flowered and hotter than the potted kind.", ["herb", "culinary"]),
    ("marjoram", "Marjoram, a sweeter cousin of oregano.", ["herb", "culinary"]),
    ("basil", "Basil, the leaves bruised between your fingers smell like summer.", ["herb", "culinary"]),
    ("mint", "Mint, running all through the bed it came from.", ["herb", "culinary", "medicinal"]),
    ("spearmint", "Spearmint, the mild one, gone to seed by midsummer.", ["herb", "culinary"]),
    ("lemon_balm", "Lemon balm, smelling of lemons and doing very little else.", ["herb", "medicinal"]),
    ("chive", "A bunch of chives, the purple buds still closed.", ["herb", "culinary", "allium"]),
    ("tarragon", "Tarragon, the leaves narrow and anise-scented.", ["herb", "culinary"]),
    ("borage", "Borage, the leaves rough and cucumber-scented, the flowers blue.", ["herb", "culinary", "medicinal"]),
    ("lovage", "Lovage, tall and celery-scented, grown by people who like celery.", ["herb", "culinary"]),
    ("hyssop", "Hyssop, the spiky blue-flowered one, a mouthful of it.", ["herb", "culinary", "medicinal"]),
    ("rue", "Rue, blue-green and bitter, and dangerous in quantity.", ["herb", "medicinal", "hazard"]),
    ("wormwood", "Wormwood, bitter enough to be a medicine and a poison at once.", ["herb", "medicinal", "hazard"]),
    ("sage_brush", "Sagebrush, grey and resinous, the smell of dry country.", ["herb"]),
    ("yarrow", "A bundle of yarrow, the flat white flowerhead and the feathery leaf.", ["herb", "medicinal"]),
    ("chamomile", "Dried chamomile flowers, apple-scented and a shade of straw.", ["herb", "medicinal", "tea"]),
    ("lavender", "A bundle of lavender, the spikes purple and the scent strong enough to sting.", ["herb", "tea", "fragrant"]),
    ("lemon_verbena", "Lemon verbena, the leaves bright and sharply citrus.", ["herb", "tea"]),
    ("peppermint", "Peppermint, the square stems and the cold smell of it.", ["herb", "tea", "medicinal"]),
    ("valerian", "Valerian root, smelling famously of something unpleasant.", ["herb", "medicinal", "root"]),
    ("comfrey", "Comfrey leaves, coarse-hairy, for a poultice and nothing else.", ["herb", "medicinal"]),
    ("elecampane", "Elecampane root, cut and dried and tasting of ginger.", ["herb", "medicinal", "root"]),
    ("feverfew", "Feverfew, the daisy-like flowers and a reputation for headaches.", ["herb", "medicinal"]),
    ("henbane", "Henbane, grey and sticky and *not* to be eaten.", ["herb", "medicinal", "hazard"]),
    ("mandrake_root", "A mandrake root, split to look like a figure, wrapped in cloth.", ["herb", "medicinal", "hazard", "root"]),
    ("belladonna", "Belladonna, the berries shiny black and treacherous.", ["herb", "medicinal", "hazard", "poisonous"]),
    ("meadowsweet", "Meadowsweet, the white froth and a salicylate hidden in it.", ["herb", "medicinal"]),
    ("motherwort", "Motherwort, the lobed leaves, a bitter infusion for the after-birth.", ["herb", "medicinal"]),
    ("mugwort", "Mugwort, growing by the roadside where nobody wanted it.", ["herb", "medicinal", "tea"]),
    ("betony", "Betony, the purple flower spike and a taste like green tea.", ["herb", "medicinal", "tea"]),
    ("vervain", "Vervain, the thin spikes and a name for anything ailed.", ["herb", "medicinal"]),
    ("agrimony", "Agrimony, the yellow flowers on a slim spike, used for a sore throat.", ["herb", "medicinal"]),
    ("cinquefoil", "Cinquefoil, the five-fingered leaf, an astringent for a graze.", ["herb", "medicinal"]),
    ("plantain_leaf", "Plantain leaves, the ribbed rosette that grows by the path.", ["herb", "medicinal"]),
    ("dandelion", "A dandelion, gone to puffball, the whole thing bitter and good for you.", ["herb", "forage", "medicinal"]),
    ("nettle", "A nettle, the sting first and the greens after.", ["forage", "fibre"]),
    ("sorrel", "Sorrel, the arrow-shaped leaves and the sourness of them.", ["forage", "herb"]),
    ("wood_sorrel", "Wood sorrel, the trefoil leaf, tasting of lemon and thin air.", ["forage", "herb"]),
    ("wild_garlic", "Wild garlic, the whole field smelling of a forest in spring.", ["forage", "herb", "allium"]),
    ("yew", "Yew, the red aril with the black seed in it â€” which is the poisonous part.", ["plant", "hazard", "poisonous"]),
    ("rosehips", "Rosehips, the red fruit of the dog rose, cleared of their hairs.", ["forage", "fruit", "tea"]),
    ("dried_herb_bundle", "A bundle of dried herbs, hanging upside down in the rafters.", ["herb", "storage", "medicinal"]),
    ("herb_poultice", "A poultice of bruised leaves, wrapped in a scrap of linen.", ["medicine", "consumable", "herbal"]),
    ("herbal_tisane", "A cup of tisane, the steam carrying whatever the bag held.", ["drink", "tea", "medicinal"], 20),
]

# â”€â”€ 3. fruit, nuts and berries â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
FRUITS = [
    ("pear", "A pear, the shape of a badger and the smell of one ripening.", ["fruit"]),
    ("quince", "A quince, yellow and hard as a stone and nearly unusable raw.", ["fruit"]),
    ("damson", "Damsons, small and dark and so sour they make your jaw ache.", ["fruit"]),
    ("blackthorn_sloe", "Blackthorn sloes, the blue-black ones covered in bloom.", ["fruit"]),
    ("cherry", "A handful of cherries, two of them still joined by their stems.", ["fruit"]),
    ("black_cherry", "Black cherries, the ones too sour to eat and too good to leave.", ["fruit"]),
    ("apricot", "An apricot, downy and orange, the stone loose inside.", ["fruit"]),
    ("peach", "A peach, the fuzz rubbed off the side that was in the bag.", ["fruit"]),
    ("fig", "A fig, split open and seeping pink down your wrist.", ["fruit"]),
    ("mulberry", "Mulberries, stained to the elbow and sweeter than they look.", ["fruit"]),
    ("elderberry", "A bunch of elderberries, the stems and every one of them stained.", ["fruit"]),
    ("blackberry", "Blackberries, the big ones, still holding a dew on them.", ["fruit", "forage"]),
    ("raspberry", "Raspberries, hollow and coming away in the fingers.", ["fruit", "forage"]),
    ("wild_strawberry", "Wild strawberries, small and red all the way to the middle.", ["fruit", "forage"]),
    ("green_strawberry", "Green strawberries, hard and unripe and gone to mould.", ["fruit", "rotten"]),
    ("gooseberry", "Gooseberries, the size of a marble and prickly all over.", ["fruit"]),
    ("red_currant", "Red currants, a spray of them, sour enough to pucker.", ["fruit"]),
    ("black_currant", "Black currants, dark and heavy and smelling of their own leaves.", ["fruit"]),
    ("candied_ginger", "Candied ginger, sugar-crusted and fierce enough to wake you up.", ["food", "confection"]),
    ("cranberry", "Cranberries, from a bog, and wince-making raw.", ["fruit"]),
    ("whortleberry", "Whortleberries, the dark little ones that stain the tongue.", ["fruit", "forage"]),
    ("medlar", "A medlar, brown and soft and only edible when 'bletted' to mush.", ["fruit"]),
    ("hawthorn_berry", "Hawthorn berries, a haul of them, the seeds down one end.", ["fruit", "forage"]),
    ("barberry", "Barberries, the red oblong ones sour enough to startle.", ["forage", "fruit"]),
    ("service_berry", "Service berries, small and purple and not worth eating raw.", ["fruit"]),
    ("walnut", "A walnut, the shell like a brain, the kernel wrinkled brown.", ["nut"]),
    ("hazelnut", "Hazelnuts, still in the husk and dried brown.", ["nut"]),
    ("chestnut", "A sweet chestnut, glossy brown with a pale scar on one side.", ["nut"]),
    ("acorn", "An acorn, the cap fitting the nut like a little beret.", ["nut", "forage"]),
    ("beechmast", "Beechmast, the small triangular nuts in their soft husks.", ["nut", "forage"]),
    ("almond", "Almonds, the hard brown shells holding a pale kernel.", ["nut"]),
    ("walnut_shell", "A pile of walnut shells, ground up for dye or grit.", ["material"]),
    ("dried_apple", "Apple slices drying on a string, leathery and half shrivelled.", ["food", "preserve", "fruit"]),
    ("apple_dried", "A ring of dried apple, brittle and honey-sweet.", ["food", "preserve", "fruit"]),
    ("candied_ginger", "Candied ginger, sugar-crusted and fierce enough to wake you up.", ["food", "confection"]),
    ("leather_strip", "A strip of tanned leather, cut for a strap or a binding.", ["material", "fibre"]),
]

# â”€â”€ 4. grain, pulse, seed and fodder crops â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# (id, description, extra tags, hunger, edible?)
CROPS = [
    ("wheat", "A sheaf of wheat, the ears heavy and the straw bright.", ["crop", "grain", "plant"], 18, True),
    ("rye", "Rye, darker and tougher than wheat, and it grows where wheat will not.", ["crop", "grain", "plant"], 18, True),
    ("barley", "A bundle of barley, the long awns making it look bearded.", ["crop", "grain", "plant"], 18, True),
    ("oats", "Oats, a loose bundle of them and a smell of a stable.", ["crop", "grain", "fodder", "plant"], 18, True),
    ("millet", "Millet, the smallest grain, and the sweetest when popped.", ["crop", "grain", "plant"], 16, True),
    ("sorghum", "Sorghum, tall as a man and thick-stalked.", ["crop", "grain", "plant"], 16, True),
    ("maize", "An ear of maize, the silk still on and the kernels pale.", ["crop", "grain", "plant"], 24, True),
    ("rice", "Rice in a cloth, the grains long and pale and faintly dusty.", ["crop", "grain", "food"], 22, True),
    ("flax", "Flax, the blue flowers gone to seed bolls.", ["crop", "fibre", "plant"], 0, False),
    ("hemp", "Hemp, coarse and tall, and the fibre in it is worth the whole crop.", ["crop", "fibre", "plant"], 0, False),
    ("poppy_seed", "Poppy seeds, tiny and blue-black, from a capsule still leaking milk.", ["seed", "spice"], 8, True),
    ("mustard_seed", "Mustard seed, a spoonful of it and the heat arrives late.", ["seed", "spice"], 8, True),
    ("caraway_seed", "Caraway seeds, the little crescents, aromatic enough to chew.", ["seed", "spice"], 6, True),
    ("anise_seed", "Aniseed, sweet and liquorice and brown.", ["seed", "spice"], 6, True),
    ("fennel_seed", "Fennel seed, green and curved and smelling of anise.", ["seed", "spice"], 6, True),
    ("coriander_seed", "Coriander seed, round and ridged, faintly soapy.", ["seed", "spice"], 6, True),
    ("cumin_seed", "Cumin seed, narrow and dark and the smell of a whole kitchen.", ["seed", "spice"], 6, True),
    ("clove", "Cloves, the dried flower buds, so strong a few are a handful of medicine.", ["spice"], 4, True),
    ("cinnamon_stick", "A cinnamon stick, quilled bark rolled tight.", ["spice"], 6, True),
    ("nutmeg", "A nutmeg, whole, the surface webbed like a small planet.", ["spice"], 8, True),
    ("black_peppercorn", "Black peppercorns, shrivelled and hot.", ["spice"], 4, True),
    ("saffron", "A pinch of saffron, the most expensive thing in the room by weight.", ["spice"], 4, True),
    ("cinnamon_ground", "A pot of ground cinnamon, the smell filling the room.", ["spice"], 4, True),
    ("dried_pea", "A sack of dried peas, rattling.", ["legume", "food"], 20, True),
    ("dried_bean", "Dried beans, the hard grey ones that need a night of soaking.", ["legume", "food"], 22, True),
    ("lentil", "Lentils, the small red ones, and they cook in no time at all.", ["legume", "food"], 20, True),
    ("chickpea", "Chickpeas, hard as beads and best boiled then fried.", ["legume", "food"], 22, True),
    ("hemp_seed", "Hemp seed, a small handful of them and a great deal of oil.", ["seed", "food"], 16, True),
    ("sunflower_seed", "Sunflower seeds, black-and-white striped, in the shell.", ["seed", "food"], 14, True),
    ("hay", "A bale of hay, golden and dust-raising when you move it.", ["fodder", "plant"], 0, False),
    ("clover", "A bundle of clover, the flower heads pink and the smell of a meadow.", ["fodder", "plant", "forage"], 0, False),
    ("alfalfa", "Alfalfa, cut and drying, the best hay there is if you have a field.", ["fodder", "plant"], 0, False),
    ("thatch_reed", "A bundle of reeds, cut for thatching, still damp at the butt.", ["material", "plant"], 0, False),
    ("straw_bale", "A bale of straw, and the smell of every animal that ever ate it.", ["fodder", "plant"], 0, False),
]

# â”€â”€ 5. mushrooms, and one that is not food â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
FUNGI = [
    ("morel", "Morels, the honeycomb caps, and the only thing worth the walk for.", ["mushroom", "forage"], 24, True),
    ("chanterelle", "Chanterelles, the golden trumpets with the false gills underneath.", ["mushroom", "forage"], 24, True),
    ("porcini", "A porcini, brown and fat and heavy in the hand.", ["mushroom", "forage"], 26, True),
    ("penny_bun", "Penny buns, the pale brown ones, sliced thick.", ["mushroom", "forage"], 24, True),
    ("parasol_mushroom", "A parasol, the tall one with a shaggy cap and a ring on the stem.", ["mushroom", "forage"], 22, True),
    ("puffball", "A puffball, white and round, and there is no arguing with one.", ["mushroom", "forage"], 18, True),
    ("oyster_mushroom", "Oyster mushrooms, grey and shelved in a fan on the trunk.", ["mushroom", "forage"], 20, True),
    ("honey_fungus", "Honey fungus, golden at the top and blackening at the base.", ["mushroom", "forage"], 20, True),
    ("chicken_of_the_woods", "Chicken of the woods, the orange bracket fungus, and a chicken's colour.", ["mushroom", "forage"], 22, True),
    ("matsutake", "A matsutake, the white pine mushroom that has a smell of the woods.", ["mushroom", "forage"], 26, True),
    ("saffron_milk_cap", "Saffron milk caps, orange and bleeding white milk when cut.", ["mushroom", "forage"], 18, True),
    ("shaggy_inkcap", "Shaggy inkcaps, the tall scaly ones, and you have to be quick.", ["mushroom", "forage"], 18, True),
    ("wood_blewit", "Wood blewit, the purple one, and you can eat it raw if you dare.", ["mushroom", "forage"], 20, True),
    ("dunghill_mushroom", "Dunghill mushrooms, where the animals are â€” and that is the point.", ["mushroom", "forage"], 16, True),
    ("fly_agaric", "A fly agaric, red and white-spotted, and *not* one of the edible ones.", ["mushroom", "hazard", "poisonous"], 0, False),
    ("deathcap", "A deathcap, pale and beautiful, and the deadliest thing in the wood.", ["mushroom", "hazard", "poisonous"], 0, False),
    ("dry_sponge", "A dry sponge from the wall, going to dust when you touch it.", ["hazard"], 0, False),
    ("dried_mushroom", "Dried mushrooms, stringy and dark, kept for the winter.", ["food", "preserve", "mushroom"], 16, True),
]

# â”€â”€ 6. meat, fish, dairy, eggs, drink â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
MEAT = [
    ("venison", "A haunch of venison, dark and fine-grained, redder than beef.", ["meat"], 40, True),
    ("mutton", "A piece of mutton, grey-pink and needing a long cook.", ["meat"], 38, True),
    ("beef_roast", "A roast of beef, salted and tied, ready for the spit.", ["meat"], 44, True),
    ("pork_knuckle", "A pork knuckle, salted and boiled and better than it sounds.", ["meat"], 40, True),
    ("streak_of_bacon", "Streaky bacon, streaked white and red, hanging in a slab.", ["meat"], 32, True),
    ("pork_sausage", "Pork sausages, linked by hand and tied at the ends.", ["meat"], 36, True),
    ("salami", "A hung salami, going firm and dark where the air got at it.", ["meat", "preserve"], 32, True),
    ("duck", "A duck, plucked, and the fat around the breast worth the trouble.", ["poultry", "meat"], 40, True),
    ("goose", "A goose, a whole one, and the size of the bird is in the size of the pan.", ["poultry", "meat"], 46, True),
    ("quail", "Two quail, tiny and dark, good roasted whole and eaten whole.", ["poultry", "meat"], 22, True),
    ("rabbit", "A rabbit, skinned, and a stew if you have the patience for it.", ["meat"], 34, True),
    ("hare", "A hare, a tougher and better-tasting thing than a rabbit.", ["meat"], 32, True),
    ("pigeon", "Pigeons, two of them, roasted and small and rich.", ["poultry", "meat"], 28, True),
    ("pheasant", "A pheasant, shot and hung, the game bird of any table with a wood behind it.", ["poultry", "meat"], 36, True),
    ("boar", "Boar, dark and coarse-grained and the best meat of the forest.", ["meat"], 42, True),
    ("goat", "Goat, the smell of it strong even cooked.", ["meat"], 32, True),
    ("trout", "A trout, still scaled, the fly-line scar under the jaw.", ["fish"], 30, True),
    ("salmon", "A salmon, silver and heavy, and the bones in it are a hazard.", ["fish"], 38, True),
    ("pike", "A pike, long and green-eyed and more bones than meat.", ["fish"], 32, True),
    ("carp", "A carp, mud-flavoured until it has hung in a keep for a month.", ["fish"], 28, True),
    ("herring", "Herrings, silver and a smell, best eaten the day they are caught.", ["fish"], 20, True),
    ("cod", "A cod, white and flaky, salted already.", ["fish"], 34, True),
    ("eel", "An eel, skinned and stiff, and best eaten cold.", ["fish"], 30, True),
    ("mussel", "Mussels, the black shells, opened over steam.", ["fish", "shellfish"], 18, True),
    ("crab", "A crab, boiled and pulled apart, and a fight over the meat.", ["fish", "shellfish"], 26, True),
    ("lobster", "A lobster, red and heavy, and worth the pot it came out of.", ["fish", "shellfish"], 34, True),
    ("fresh_egg", "An egg, still warm from the nest.", ["food", "egg"], 14, True),
    ("goose_egg", "A goose egg, three of a chicken's, and thick brown.", ["food", "egg"], 22, True),
    ("milk_jug", "A jug of milk, still skinning over at the top.", ["drink", "dairy"], 26, True),
    ("fresh_cheese", "A round of fresh cheese, white and soft and wet at the rind.", ["food", "dairy"], 24, True),
    ("hard_cheese", "A hard cheese, wax-rind and the colour of a bandage.", ["food", "dairy"], 28, True),
    ("butter", "A block of butter, cold and pale and scraping badly.", ["food", "dairy"], 22, True),
    ("cream", "A pot of cream, thick enough to hold a spoon upright.", ["drink", "dairy"], 20, True),
    ("whey", "Whey, thin and yellow, the run-off from making the cheese.", ["drink", "dairy"], 16, True),
]

# â”€â”€ 7. bread, preserves, cooked food, drink â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
COOKED = [
    ("loaf", "A round loaf, dark-crusted and still ticking on the board.", ["food", "bread"], 38, True),
    ("rye_bread", "Dark rye bread, dense enough to knock a tooth out if you rush.", ["food", "bread"], 36, True),
    ("oatcake", "An oatcake, hard as a board and meant to be dunked.", ["food", "bread"], 20, True),
    ("barley_bread", "Barley bread, the husks showing in the crumb.", ["food", "bread"], 34, True),
    ("bread_rolls", "A cloth of bread rolls, gone cold and floured.", ["food", "bread"], 32, True),
    ("flatbread", "A flatbread, thin and pale and flexible enough to fold.", ["food", "bread"], 32, True),
    ("apple_tart", "A slice of apple tart, the pastry soft under the fork.", ["food", "pastry"], 36, True),
    ("mince_pie", "A mince pie, the tin of them on a board by the window.", ["food", "pastry"], 34, True),
    ("seeded_bread", "Seeded bread, so many seeds in the crust it holds together.", ["food", "bread"], 36, True),
    ("pottage", "Pottage, the thick stew, more thick than stew.", ["food", "stew"], 40, True),
    ("bean_stew", "Bean stew, pottage with beans in it and bread to soak it.", ["food", "stew", "legume"], 40, True),
    ("vegetable_soup", "A pot of vegetable soup, the whole trimmings boiled up.", ["food", "stew", "vegetable"], 34, True),
    ("rabbit_stew", "Rabbit stew, rabbit and root vegetables and a long time on the fire.", ["food", "stew", "meat"], 44, True),
    ("eel_pie", "A hot pie of eel, the pastry sealed with a crimped edge.", ["food", "pastry", "fish"], 38, True),
    ("porridge", "Porridge, grey and thick, with the salt barely making it edible.", ["food", "grain"], 26, True),
    ("oat_porridge", "Oat porridge, better than plain, and eaten with honey when there is any.", ["food", "grain"], 30, True),
    ("stewed_prunes", "Stewed prunes, in syrup gone dark and sticky.", ["food", "preserve", "fruit"], 20, True),
    ("quince_paste", "Quince paste, a block of it, and sticky enough to glue a mouth shut.", ["food", "preserve", "fruit"], 18, True),
    ("fruit_leather", "Fruit leather, a sheet of it with a sugar crust.", ["food", "preserve", "fruit"], 20, True),
    ("pickled_onion", "Pickled onions, sour enough to bring tears to an eye.", ["food", "preserve", "vegetable"], 16, True),
    ("pickled_cucumber", "Pickled cucumbers, spears in a cloudy brine.", ["food", "preserve", "vegetable"], 14, True),
    ("salted_fish", "Salted fish, split and dried and needing an hour of soaking.", ["food", "preserve", "fish"], 32, True),
    ("smoked_sausage", "Smoked sausage, hung and cured and sliced thin.", ["food", "preserve", "meat"], 30, True),
    ("dried_cod", "Dried cod, hanging in a rafter, the smell of a fishing village.", ["food", "preserve", "fish"], 30, True),
    ("tallow", "A block of tallow, waxy and pale, for soap and candles and nothing else.", ["material", "fat"], 0, False),
    ("animal_fat", "A lump of rendered fat, for cooking or for making soap.", ["material", "fat"], 0, False),
    ("salted_beef", "Salted beef, pink and dense, and it keeps for a year.", ["food", "preserve", "meat"], 36, True),
    ("candle_wax", "A cake of beeswax, pale and honey-smelling, for making candles.", ["material", "fat"], 0, False),
    ("herb_oil", "A jar of herb-infused oil, green and strong enough to taste of the herb.", ["food", "oil", "condiment"], 12, True),
    ("honeycomb", "A piece of honeycomb, the wax and a little honey caught in the cells.", ["food", "preserve", "sweet"], 18, True),
    ("dripping", "Dripping, the solid run-off from the roasting, and the best of it.", ["food", "fat"], 20, True),
    ("bacon_rasher", "A rasher of bacon, thick-cut and salted.", ["food", "meat"], 28, True),
    ("sausage_roll", "A sausage roll, the pastry flaking and the filling hot.", ["food", "pastry", "meat"], 38, True),
    ("apple_crumble", "Apple crumble, the topping browned and the fruit underneath bubbling.", ["food", "pastry", "fruit"], 40, True),
    ("honeyed_bread", "Bread with honey, the sort a worker's breakfast is made of.", ["food", "bread", "sweet"], 34, True),
    ("honeyed_oats", "Oats with honey, warm and sweet and quick.", ["food", "grain", "sweet"], 28, True),
    ("fish_pie", "A fish pie, the pastry crimped and the lid left off to lose the steam.", ["food", "pastry", "fish"], 40, True),
    ("herb_tea", "A mug of herb tea, hot enough to scold.", ["drink", "tea", "herbal"], 24, True),
    ("mead", "Mead, honey and water fermented, and stronger than it looks.", ["drink", "alcohol", "honey"], 30, True),
    ("apple_cider", "Cider, small and cloudy, pressed last month.", ["drink", "alcohol", "fruit"], 30, True),
    ("pear_perry", "Perry, the pear equivalent, and sharper than the cider.", ["drink", "alcohol", "fruit"], 30, True),
    ("small_beer", "Small beer, the weak stuff â€” thin, and a better drink than the look of it.", ["drink", "alcohol", "grain"], 20, True),
    ("gooseberry_cordial", "A jar of gooseberry cordial, the colour of a signal fire, and sharp enough to pucker the mouth shut.", ["drink", "preserve", "fruit"], 26, True),
    ("herb_wine", "A glass of herb wine, a green-gold and unnervingly strong.", ["drink", "alcohol", "herbal"], 24, True),
    ("cider_vinegar", "Cider vinegar, sharp enough to smell through a stopper.", ["condiment", "liquid", "vinegar"], 0, False),
    ("coconut_oil", "A jar of coconut oil, solid white and melting on a warm hand.", ["oil", "condiment"], 0, False),
    ("olive_oil", "A flask of olive oil, the good green-gold and the last of it.", ["oil", "condiment", "liquid"], 0, False),
    ("wine", "A skin of wine, dark and better than the cellar deserves.", ["drink", "alcohol"], 26, True),
    ("beer", "A jug of small beer gone flat, served warm, as served everywhere.", ["drink", "alcohol", "grain"], 22, True),
    ("small_ale", "A jug of ale, brown and cloudy, and the reason for most evenings in a village.", ["drink", "alcohol", "grain"], 30, True),
]

# â”€â”€ 8. natural materials â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
MATERIALS = [
    ("firewood", "A bundle of firewood, split to the thickness of a hand.", ["material", "fuel", "wooden"], 4.0),
    ("kindling", "A handful of kindling, finger-thick, the tinder under a fire.", ["material", "fuel", "wooden"], 0.4),
    ("charcoal", "A sack of charcoal, black and dusty and better for iron than wood.", ["material", "fuel"], 1.0),
    ("peat", "Peat, cut into slabs and stacked to dry for a winter's burning.", ["material", "fuel"], 3.0),
    ("sawdust", "A drift of sawdust under the bench, swept into a corner daily.", ["material", "trash"], 0.2),
    ("wood_ash", "Wood ash, swept from the hearth, the best thing to put on a garden.", ["material", "ash"], 0.5),
    ("pine_cone", "A pine cone, closed, and it opens on a windowsill over a fortnight.", ["natural", "plant"], 0.05),
    ("birch_bark", "A sheet of birch bark, peeling in one piece, waterproof and burnable.", ["material", "fibre", "wooden"], 0.3),
    ("resin", "A lump of pine resin, amber and sticky, the base of every varnish in the world.", ["material", "plant", "sticky"], 0.2),
    ("tree_sap", "Tree sap, caught in a cut and going sticky as it cools.", ["material", "plant", "sticky"], 0.2),
    ("moss", "A cushion of moss, damp and dark, and the best thing for a wound.", ["natural", "forage", "plant"], 0.1),
    ("lichen", "Lichen, grey-green and crusty, growing on a stone in the rain.", ["natural", "plant"], 0.05),
    ("feather", "A single feather, small and barred, off the midden floor.", ["natural", "fibre", "feather"], 0.02),
    ("goose_down", "A bag of goose down, the softest thing on the farm and worth a fortune.", ["natural", "fibre", "feather"], 0.5),
    ("rawhide", "A raw hide, still wet and stinking, on the frame to scrape.", ["material", "fibre", "leather"], 3.0),
    ("sinew", "A twist of sinew, dried and tough, for sewing anything at all.", ["material", "fibre"], 0.1),
    ("bone", "A cut of bone, boiled clean, for a handle or a button.", ["material"], 0.4),
    ("horn", "A horn, hollow, for a cup or a powder flask.", ["material", "container"], 0.3),
    ("bone_meal", "Bone meal, ground, for the garden and for the pigs.", ["material", "fodder"], 0.6),
    ("marrow_bone", "A marrow bone, the good end sawn off and plugging the pot.", ["meat", "fodder"], 0.8),
    ("wool_fleece", "A raw fleece, rolled and greasy, smelling strongly of the animal.", ["fibre", "wool", "fodder"], 6.0),
    ("flax_fibre", "Flax fibre, retted and hackled, soft as it will ever get.", ["fibre", "plant"], 0.5),
    ("hemp_fibre", "Hemp fibre, the strongest thread a poor person can make.", ["fibre", "plant"], 0.5),
    ("straw", "A fistful of straw, the stems, for bedding or thatch or a tether.", ["material", "plant", "fodder"], 0.2),
    ("rush", "Rushes, cut and bundled, for weaving a mat or a basket.", ["material", "plant", "fibre"], 0.3),
    ("clay", "A lump of river clay, grey and sticky, ready to be worked and fired.", ["material", "clay"], 2.0),
    ("ochre", "A stone of red ochre, ground to powder for paint and for skin.", ["material", "pigment"], 0.3),
    ("charcoal_drawing", "A stick of drawing charcoal, made of the same stuff as the fire.", ["tool", "writing"], 0.1),
    ("flint", "A core of flint, sharp-edged grey, and a way to strike a light.", ["material", "stone"], 0.5),
    ("grindstone", "A grindstone, the water-crock wet, for a blade or a scythe.", ["tool", "stone"], 8.0),
    ("whetstone", "A whetstone, dry, for touching a blade back up between cuts.", ["tool", "stone"], 0.4),
    ("slate", "A shard of slate, sharp enough to split an edge with.", ["material", "stone"], 0.2),
    ("gravel", "A barrow-load of gravel, washed and ready for a path.", ["material", "stone"], 20.0),
    ("sea_salt", "A block of sea salt, grey and crumbling, off a pan on the shore.", ["material", "salt"], 1.0),
    ("potash", "Potash, the grey ash lye, the base of every soft soap made.", ["material", "alchemical"], 1.0),
    ("glass_bead", "A single glass bead, blue, traded from somewhere much further away.", ["material", "glass", "trade"], 0.02),
    ("flint_and_steel", "Flint and steel, and the tinder-dish that goes with them.", ["tool", "fire"], 0.2),
    ("tinderbox", "A tinderbox, the charred cloth and the steel striker, kept dry.", ["tool", "fire"], 0.3),
    ("log", "A single log, bark-on, the honest unit of firewood.", ["material", "fuel", "wooden"], 8.0),
    ("kelp", "Kelp, the wet brown rope of it, and the smell of a low tide.", ["natural", "plant", "marine"], 0.5),
    # No `food` tag on the two marine weeds: they are gathered for the pot by
    # people who know what to do with them, and an edible tag here would promise
    # a character can eat a hank of bladderwrack raw.
    ("seaweed", "Seaweed, gathered at low tide and salted for the pot.", ["natural", "plant", "marine"], 0.3),
    ("bladderwrack", "Bladderwrack, the bladdered brown weed, boiled for its jelly.", ["natural", "plant", "marine"], 0.4),
    ("cockle_shell", "A cockle shell, the pink inside, from the mud at low water.", ["natural", "marine"], 0.05),
    ("pebble", "A pebble, flat and grey, and good for a game or a floor.", ["natural", "stone"], 0.1),
    ("crystal", "A quartz crystal, cloudy and faintly lit from inside.", ["material", "stone"], 0.2),
    ("cork_bark", "A strip of cork bark, taken from a standing tree and re-grown.", ["material", "wooden"], 0.2),
    ("log_holder", "A log holder, wrought iron, and a wall it will lean against for a century.", ["furniture", "metal"], 25.0),
    ("log_cutter", "A log cutter, one heavy blow a month and the kindling problem gone.", ["tool", "metal"], 6.0),
]

# â”€â”€ 9. medieval household â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
HOUSEHOLD = [
    ("wooden_bowl", "A wooden bowl, turned, the grain standing proud where it is worn.", ["container", "wooden", "kitchen"], 0.4),
    ("wooden_plate", "A wooden plate, thick, and the middle is dished from use.", ["kitchen", "wooden"], 0.3),
    ("carved_spoon", "A carved spoon, the bowl worn thin on one side.", ["kitchen", "tool", "wooden"], 0.1),
    ("brass_spoon", "A brass spoon, a guild spoon, and worth more than the plate.", ["kitchen", "metal", "valuable"], 0.2),
    ("iron_ladle", "An iron ladle, long-handled, black with use.", ["kitchen", "tool", "metal"], 0.6),
    ("cook_knife", "A cook's knife, worn to a shining edge and honed to a shaving edge.", ["kitchen", "tool", "metal"], 0.5),
    ("bread_knife", "A bread knife, the edge dulled with sliced crusts.", ["kitchen", "tool", "metal"], 0.4),
    ("earthen_pot", "An earthenware pot, round-bellied and unglazed inside.", ["container", "clay", "kitchen"], 1.2),
    ("glazed_jug", "A glazed jug, brown-glazed, with a lip poured by hand.", ["container", "clay", "kitchen"], 1.5),
    ("stoneware_pitcher", "A stoneware pitcher, heavy enough to be a weapon in a fight.", ["container", "clay", "kitchen", "heavy"], 2.0),
    ("oak_ale_cup", "An oak cup, pegged, and a leak it has never quite stopped.", ["container", "wooden", "kitchen"], 0.3),
    ("pewter_tankard", "A pewter tankard, one handle, the rim worn bright.", ["container", "metal", "kitchen"], 0.6),
    ("china_cup", "A clay cup, thin-walled, the first of its kind from the coast.", ["container", "clay", "valuable"], 0.2),
    ("iron_cauldron", "An iron cauldron, black, big enough to hang over a fire for two.", ["kitchen", "metal", "heavy"], 12.0),
    ("cooking_pot", "A cooking pot, iron with a lid and three feet so it sits in the coals.", ["kitchen", "metal"], 5.0),
    ("pot_hook", "A pot hook, a long iron rod bent into a hook, living by the fire.", ["kitchen", "tool", "metal"], 0.6),
    ("spit", "A spit, an iron bar for turning meat over a fire.", ["kitchen", "tool", "metal"], 2.0),
    ("frying_pan", "A frying pan, blackened inside, handled with a folded cloth.", ["kitchen", "tool", "metal"], 1.2),
    ("griddle", "A griddle plate, flat and seasoned, for cooking over embers.", ["kitchen", "tool", "metal"], 4.0),
    ("tripod", "A tripod of iron, for a pot over a fire.", ["kitchen", "tool", "metal"], 3.0),
    ("mortar_and_pestle", "A mortar and pestle of stone, for pounding roots and grain.", ["kitchen", "tool", "stone"], 4.0),
    ("hand_mill", "A quern, two stones, and the only flour in the house made this morning.", ["kitchen", "tool", "stone"], 8.0),
    ("grain_hopper", "A hopper for the mill, a funnel of wood feeding the stones below.", ["kitchen", "tool", "wooden"], 2.0),
    ("winnowing_basket", "A winnowing basket, a tray of woven willow, tilted in the wind.", ["kitchen", "tool", "fibre"], 0.8),
    ("kitchen_broom", "A broom of birch twigs bound with cord, sweeping in silence.", ["kitchen", "tool", "fibre"], 0.6),
    ("hearth_poker", "A hearth poker, and the end bent from a hundred prods.", ["kitchen", "tool", "metal"], 1.0),
    ("hearth_stone", "A hearth stone, a slab of flat rock, blackened in the middle.", ["kitchen", "stone", "fire"], 30.0),
    ("andiron", "An andiron, cast iron, to keep the logs off the wet floor.", ["furniture", "metal", "fire"], 6.0),
    ("fire_irons", "A pair of fire irons, one flat and one hooked, standing on a stand.", ["kitchen", "metal", "fire"], 3.0),
    ("tallow_candle", "A tallow candle, guttered and smell of mutton fat.", ["light_source", "candle", "kitchen"], 0.1),
    ("beeswax_candle", "A beeswax candle, honey-coloured, burning clean and slow.", ["light_source", "candle"], 0.1),
    ("candle_wick", "A wick, hemp, ready for dipping into tallow.", ["material", "fibre", "candle"], 0.01),
    ("rushlight", "A rushlight, a rush dipped in grease, and the cheapest light in the house.", ["light_source", "fibre"], 0.05),
    ("candlestick", "A candlestick, pewter, with a stub still burned into the socket.", ["furniture", "metal", "candle"], 0.4),
    ("lantern", "A lantern, horn-paned, and the glass fogged from the inside.", ["light_source", "glass", "kitchen"], 1.0),
    ("oil_lamp", "An oil lamp, clay, burning fish oil and smelling of it.", ["light_source", "clay", "liquid"], 0.6),
    ("wick_trimmer", "A wick trimmer, scissors on a long handle, for cutting a burnt wick.", ["tool", "kitchen"], 0.3),
    ("salt_cellar", "A salt cellar, silver, and lined with blue salt to keep it dry.", ["kitchen", "metal", "tableware"], 0.4),
    ("napkin", "A napkin of homespun linen, darned at the corner with different thread.", ["cloth", "household", "linen"], 0.1),
    ("table_cloth", "A table cloth, undyed wool, hanging to the floor.", ["cloth", "household"], 0.8),
    ("wool_blanket", "A wool blanket, coarse and grey and warmer than the bed it is on.", ["cloth", "bedroom", "insulation"], 2.0),
    ("straw_mattress", "A straw mattress, ticking worn, and it goes on shifting all night.", ["furniture", "bedroom", "fodder"], 6.0),
    ("bedroll", "A bedroll, a blanket rolled over a mat, for a night anywhere.", ["cloth", "insulation", "bedroom"], 1.5),
    ("bed_bolster", "A bolster, a flat cushion, and the only soft thing in the room.", ["furniture", "bedroom", "insulation"], 0.8),
    ("footstool", "A footstool, three-legged, and something to keep the bedclothes off the floor.", ["furniture"], 1.0),
    ("three_legged_stool", "A three-legged stool, made by someone who knows a wobbling four-legged one.", ["furniture", "wooden"], 1.5),
    ("coffered_chest", "A chest, oak and iron-bound, with a domed lid and a good lock.", ["furniture", "storage", "wooden", "container"], 30.0),
    ("iron_cornered_chest", "A travelling chest, iron-cornered, which has been moved a long way.", ["storage", "container", "metal", "heavy"], 20.0),
    ("wicker_basket", "A wicker basket, with a lid and a handle worn to a shine.", ["container", "fibre"], 0.6),
    ("oak_barrel", "An oak barrel, hooped, and big enough to be a small cask.", ["container", "wooden", "storage"], 40.0),
    ("firkin", "A firkin, a small barrel, for the butter or the beer.", ["container", "wooden"], 8.0),
    ("bucket", "A wooden bucket, with an iron handle worn bright where it is gripped.", ["container", "wooden"], 1.5),
    ("tub", "A wash tub, big enough to stand a child in, and a great deal of water.", ["container", "wooden", "bathroom"], 15.0),
    ("ewer", "An ewer, pewter, and the lid is a different pewterer's work.", ["container", "metal", "tableware"], 1.0),
    ("basin", "A basin, ceramic, chipped at the rim.", ["container", "clay", "bathroom"], 1.0),
    ("towel", "A towel, linen, and the ends are frayed to strings.", ["cloth", "household"], 0.2),
    ("comb", "A horn comb, close-grained and bought from a far coast.", ["personal", "accessory", "toilet"], 0.1),
    ("shaving_strops", "A strop and a razor, and a beard kept honest by a man who cannot afford a barber.", ["personal", "metal", "toilet"], 0.3),
    ("looking_glass", "A looking glass, a disc of polished metal, and the face in it a little green.", ["personal", "valuable", "mirror"], 0.4),
    ("mending_kit", "A mending kit â€” needle, thread, patches â€” kept together by habit.", ["tool", "cloth", "household"], 0.1),
    ("clothes_peg", "A clothes peg, split from hazel, and a jar of them by the door.", ["household", "wooden", "small"], 0.01),
    ("mop", "A mop, a bundle of rag on a stick, and a bucket standing ready.", ["tool", "household"], 2.0),
    ("broom", "A birch broom, bound and worn round at the head.", ["tool", "fibre", "household"], 1.0),
    ("wash_basin", "A washing basin on a stand, and the soap cake always left in it.", ["container", "kitchen", "bathroom"], 2.5),
    ("iron_stand", "An iron stand for a basin, folding, the way a tailor's does.", ["furniture", "metal"], 2.0),
    ("fire_wood_stack", "A stack of firewood, squared at both ends by a careful hand.", ["furniture", "storage", "wooden"], 40.0),
    ("wood_rack", "A drying rack for the washing, the bars lashed with cord.", ["household", "fibre", "wooden"], 3.0),
    ("net_curtain", "A net curtain, hung to keep the flies off the meat.", ["cloth", "household", "fibre"], 0.5),
    ("fly_net", "A fly net, thrown over the food at table to keep the flies out of it.", ["cloth", "household", "fibre"], 0.6),
    ("rush_mat", "A rush mat, woven, and cold underfoot in the morning.", ["furniture", "fibre", "household"], 2.0),
    ("wooden_tray", "A wooden tray, with a lip, carried in two hands to keep it level.", ["container", "wooden", "kitchen"], 1.0),
    ("wooden_dish", "A shallow wooden dish, for bread or for the day's washing.", ["container", "wooden", "kitchen"], 0.5),
    ("slap_and_dash", "A long-handled wooden ladle for the fire, called a slap and dash in three counties.", ["tool", "kitchen", "wooden"], 1.0),
    ("hang_iron", "A hanging iron, a triangle of bar on a chain, for a pot over the fire.", ["kitchen", "metal", "tool"], 3.0),
    ("pudding_basin", "A pudding cloth, a square of muslin, and the recipe is a family argument.", ["cloth", "kitchen"], 0.2),
    ("butter_churn", "A butter churn, standing, and the sound of it is the sound of a farm.", ["kitchen", "wooden", "tool"], 6.0),
    ("cream_jar", "A cream jar, glazed and lidded, for the morning's cream.", ["container", "clay", "kitchen"], 1.0),
    ("cheese_knife", "A cheese knife, thin-bladed, and a board with a wire to cut with.", ["kitchen", "tool", "metal"], 0.3),
    ("flour_sieve", "A flour sieve, horsehair mesh in a hoop, shaken over a bowl.", ["kitchen", "tool"], 0.3),
    ("mortar_board", "A low bench by the fire, called a settle, where an old person sits.", ["furniture", "wooden"], 8.0),
    ("step_stool", "A three-legged stool by the high bed, to climb into it.", ["furniture", "wooden"], 1.2),
    ("chest_lock_key", "A key to a chest's lock, wrought iron and worn to a nub.", ["key", "metal", "personal"], 0.05),
    ("iron_key", "An iron key, long and crude, for a lock that will outlast it.", ["key", "metal"], 0.1),
]

# â”€â”€ 10. town, road and field items â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
TOWN = [
    ("milestone", "A milestone, set in the verge, with the next town chiselled on it.", ["road", "stone"], 40.0),
    ("signpost", "A signpost, the arms gone soft with weather, pointing three ways.", ["road", "wooden", "sign"], 6.0),
    ("milepost", "A milepost, painted, and the number legible only if you know it.", ["road", "wooden"], 3.0),
    ("boundary_stone", "A boundary stone, set upright at the corner of two manors.", ["road", "stone"], 25.0),
    ("waymark", "A waymark on a tree, a blaze cut into the bark at eye height.", ["road", "wooden", "sign"], 0.3),
    ("toll_gate", "A toll gate, oak and iron, and a man who sits beside it all day.", ["road", "wooden", "metal", "toll"], 120.0),
    ("toll_bar", "A toll bar, a painted pole swung aside, and the coins that paid for it.", ["road", "wooden", "toll"], 2.0),
    ("stile", "A stile, two steps and a rail, so the sheep stay in and the feet get over.", ["road", "wooden"], 8.0),
    ("hitching_post", "A hitching post, iron, with a ring at the top for a rein.", ["road", "metal", "town"], 12.0),
    ("horse_trough", "A stone trough, brim-full and green, and the best drinking in the county.", ["road", "stone", "town"], 200.0),
    ("ford_marker", "A post at a ford, marking how deep, and wet to the knee.", ["road", "wooden"], 4.0),
    ("bridge_plank", "A bridge plank, creosoted, laid across the worst of it.", ["road", "wooden"], 12.0),
    ("kerb_stone", "A kerb stone, cut square, to set along an edge and stop the wheels.", ["road", "stone"], 25.0),
    ("paving_stone", "A paving stone, worn hollow in the middle by a century of feet.", ["road", "stone", "town"], 20.0),
    ("cobble", "A cobble, river-rounded, and four of them make a square.", ["road", "stone"], 3.0),
    ("drain_grate", "A drain grate, iron bars over the gully, and the smell coming off it.", ["road", "metal", "town"], 6.0),
    ("water_pump", "A village pump, iron, with a long handle and a wet stone beside it.", ["road", "metal", "town", "water"], 25.0),
    ("public_well", "A public well, stone-lined, with a bucket on a rope and a windlass.", ["town", "stone", "water", "container"], 300.0),
    ("market_stall", "A market stall, trestle and a cloth over the top and pegged at the corners.", ["town", "furniture", "cloth", "trading"], 15.0),
    ("awning", "An awning, striped, and the rain sounding on it all afternoon.", ["town", "cloth"], 3.0),
    ("trade_sign", "A trade sign, a painted board on a bracket, swinging when the wind gets in.", ["town", "sign", "wooden"], 2.0),
    ("shop_board", "A shop board, a painted board telling you what is sold here and what is not.", ["town", "sign", "wooden"], 1.5),
    ("guild_sign", "A guild sign, iron, hanging from a bracket, and it rings when it moves.", ["town", "sign", "metal", "trading"], 4.0),
    ("notice_board", "A notice board, cork behind glass, and the bills are weeks out of date.", ["town", "sign", "paper"], 5.0),
    ("town_crier_bell", "A hand bell, for calling the town together, and it carries a street's length.", ["town", "metal", "sound_source"], 0.8),
    ("street_lamp", "A street lamp, iron, on a bracket, lit at dusk and out at dawn.", ["town", "light_source", "metal"], 20.0),
    ("lamp_post", "A lamp post, cast iron, with a glass box at the top and a candle inside.", ["town", "light_source", "metal", "sound_source"], 30.0),
    ("bollard", "A bollard, iron, set in the paving to keep a cart out of the doorway.", ["town", "metal", "road"], 15.0),
    ("refuse_heap", "A refuse heap, at the edge, and the flies find it before anyone does.", ["town", "trash", "filth", "stench"], 20.0),
    ("dung_heap", "A dung heap, stacked against the wall, and the day's work steaming in it.", ["town", "filth", "fodder"], 25.0),
    ("water_butt", "A water butt, a big barrel under the eaves, catching the roof.", ["town", "container", "wooden", "water"], 30.0),
    ("rain_butt", "A rain barrel, brim-full, and a dipper on a string beside it.", ["town", "container", "wooden", "water"], 25.0),
    ("brazier", "A brazier, iron on legs, for a fire that has to be lit in the street.", ["town", "fire", "metal", "light_source"], 12.0),
    ("public_statue", "A statue, a man in armour on a plinth, and pigeons on his head.", ["town", "stone", "art", "monument"], 500.0),
    ("sundial", "A sundial, stone, and worth a look at noon and never at any other time.", ["town", "stone", "tool"], 40.0),
    ("stone_bridge", "A stone bridge, three arches, and the road worn into grooves on top.", ["road", "stone", "town"], 2000.0),
    ("gate_posts", "A pair of gate piers, stone, and a gate that has hung on one of them for years.", ["town", "stone", "road"], 300.0),
    ("barn_doors", "Barn doors, oak, on a track, and the gap for the hay to go through.", ["town", "wooden", "furniture"], 50.0),
    ("farm_cart", "A farm cart, four wheels, shafts, and the bed repaired with three more planks.", ["town", "wooden", "vehicle", "heavy"], 80.0),
    ("hay_wagon", "A hay wagon, tall-sided, and the load stacked higher than the man who drove it.", ["town", "wooden", "vehicle", "fodder", "heavy"], 90.0),
    ("wooden_pail", "A wooden pail, with a bail handle, and the one thing every farm has too many of.", ["container", "wooden", "town"], 1.0),
    ("shepherd_crook", "A shepherd's crook, hazel, hooked and polished at the grip.", ["town", "tool", "wooden"], 0.8),
    ("milestone_post", "A boundary post, split from a sapling, standing in a field corner.", ["road", "wooden"], 1.2),
    ("caravan_track", "A track worn into a hollow by carts, the ruts deep enough to hide a foot.", ["road", "natural", "dirt"], 0.0),
]

# â”€â”€ 11. tools of work and craft â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
TOOLS = [
    ("scythe", "A scythe, long-snouted, ground to a curl of steel at the blade.", ["tool", "metal", "farming"], 2.5),
    ("sickle", "A sickle, hooked and serrated on the inside, and the handle worn to fit one hand.", ["tool", "metal", "farming"], 0.6),
    ("rake", "A wooden rake, tines bound with withies, for the hay.", ["tool", "wooden", "farming"], 1.5),
    ("hay_rake", "A hay rake, a frame of wood with a handle, and a day of the back in it.", ["tool", "wooden", "farming"], 1.5),
    ("hoe", "A hoe, an iron blade set at an angle, for the vegetable beds.", ["tool", "metal", "farming"], 1.5),
    ("mattock", "A mattock, axe one side, pick the other, for the stony ground.", ["tool", "metal", "farming"], 3.0),
    ("dibber", "A dibber, a blunt stake for making holes for seedlings.", ["tool", "wooden", "farming"], 0.4),
    ("billhook", "A billhook, hooked and sharp, for cutting back briars.", ["tool", "metal", "gardening"], 0.7),
    ("pruning_knife", "A pruning knife, folding, with a blade like a horn.", ["tool", "metal", "gardening"], 0.2),
    ("garden_secateurs", "Secateurs, sprung steel, and every pair ends up a little crooked.", ["tool", "metal", "gardening"], 0.4),
    ("reaping_hook", "A reaping hook, a small sickle for a close crop.", ["tool", "metal", "farming"], 0.3),
    ("flail", "A flail, two sticks on a thong, and hard on the back and worse on the threshing.", ["tool", "wooden", "farming"], 3.0),
    ("pitchfork", "A pitchfork, tines sprung from the heat and bent true by a smith.", ["tool", "metal", "farming"], 3.0),
    ("water_scoop", "A water scoop, copper, and dented from being dropped in a full bucket.", ["container", "metal", "kitchen"], 0.3),
    ("yew_bow", "A yew bow, the long limbs and the string waxed with tallow.", ["tool", "wooden", "hunting", "projectile"], 1.5),
    # task-518: arrows are ammunition (tag `ammo`), not a `weapon` -- a
    # broadhead used to be auto-selected as a melee weapon and rolled 1d0.
    ("arrow", "An arrow, a goose shaft and a blunt head, made to be lost.", ["ammo", "projectile", "fletching", "hunting"], 0.1),
    ("broadhead_arrow", "A broadhead arrow, a wide steel head, and the sound it makes is a whole different thing.", ["ammo", "projectile", "fletching", "hunting"], 0.15),
    ("fishing_line", "A fishing line, waxed flax, on a wooden reel.", ["tool", "fishing", "fibre"], 0.1),
    ("fish_hook", "A fish hook, bone-and-steel, barbless for the trout.", ["tool", "fishing", "metal"], 0.01),
    ("fishing_net", "A net, knotted by hand, mended so often it is more knot than net.", ["tool", "fishing", "fibre"], 3.0),
    ("eel_spear", "An eel spear, a tine of iron, and the worst of it is the waiting.", ["tool", "fishing", "weapon", "metal"], 2.0),
    ("snare_wire", "A snare wire, thin and springy, and the correct way to set one is a matter of opinion.", ["tool", "metal", "hunting"], 0.2),
    ("bee_skep", "A bee skep, straw, domed, and the bees in it making a sound like paper.", ["container", "fibre", "farming"], 1.0),
    ("smoker", "A bee smoker, tin and bellows, for calming a hive before robbing it.", ["tool", "metal", "farming", "fire"], 1.5),
    ("honey_extractor", "A honey extractor, a drum that spins the comb and drops the honey out.", ["tool", "kitchen", "wooden", "farming"], 6.0),
    ("wax_melter", "A wax melter, a pan of water and a cloth bag, for rendering the cappings.", ["tool", "kitchen", "metal"], 2.0),
    ("cheese_press", "A cheese press, a heavy wooden screw, and the whey running out below it.", ["tool", "kitchen", "wooden"], 12.0),
    ("butter_knife", "A butter knife, thin, and used for nothing but cutting butter.", ["kitchen", "tool", "metal"], 0.2),
    ("lantern_hook", "An iron hook for a lantern, screwed into a door frame.", ["tool", "metal", "fixture"], 0.1),
    ("basket_maker", "A basket maker's knife, a bodkin with a hook at one end and a handle at the other.", ["tool", "metal", "craft", "fibre"], 0.3),
    ("weaver_reed", "A weaver's reed, a comb of split cane, and it is the reed that decides the cloth.", ["tool", "wooden", "craft", "fibre"], 0.2),
    ("spinning_drop_spindle", "A drop spindle, whorl and shaft, and the thread is going on right now.", ["tool", "wooden", "craft", "fibre"], 0.2),
    ("hand_card", "Hand cards, wire-studded leather, for teasing wool into order.", ["tool", "leather", "craft", "fibre"], 0.5),
    ("fulling_rock", "A fulling rock, a smooth stone battered in a wooden handle, to shrink the cloth.", ["tool", "stone", "craft"], 2.0),
    ("tripod_loom", "A loom part, a beater, oak, to beat the weft home.", ["tool", "wooden", "craft"], 1.0),
    ("tannery_knife", "A tannery knife, curved, for scraping a hide down to the grain.", ["tool", "metal", "craft", "leather"], 0.6),
    ("awl", "An awl, a spike in a turned handle, and the point of every leatherworking job.", ["tool", "metal", "craft"], 0.1),
    ("sewing_needle", "A bone needle, blunted and polished, threaded and ready.", ["tool", "metal", "small", "cloth"], 0.01),
    ("sinew_thread", "A length of sinew, split and prepared, for a needle that cannot go through cloth.", ["material", "fibre", "tool"], 0.05),
    ("cobblers_wax", "A lump of cobbler's wax, for the thread, and it makes the leather supple.", ["material", "clay", "craft"], 0.2),
    ("iron_shovel", "A shovel, iron, and the blade is polished silver where it digs.", ["tool", "metal"], 3.0),
    ("spade", "A spade, ash shaft and a wide blade, squared for cutting a trench.", ["tool", "metal", "farming"], 3.0),
    ("flint_and_striker", "A striker, a piece of iron with a sharp edge, and the correct sparks come off one place on it.", ["tool", "metal", "fire"], 0.2),
    ("saw_horse", "A saw horse, two trestles and a beam, to take a plank while you cut it.", ["tool", "wooden", "furniture"], 5.0),
    ("hand_axe", "A hand axe, with a hole in the poll for a hazel handle.", ["tool", "metal", "fletching"], 1.5),
    ("adze", "An adze, a blade set at right angles, for hewing a beam square.", ["tool", "metal", "wooden"], 1.8),
    ("auger", "An auger, a large bit for a brace, to bore a hole for a tenon.", ["tool", "metal", "wooden"], 0.6),
    ("chisel", "A chisel, a bevel on the end, to lever out or pare down.", ["tool", "metal", "wooden"], 0.3),
    ("mallet", "A wooden mallet, and the head swollen from ten thousand blows.", ["tool", "wooden"], 0.8),
    ("pin_hammer", "A pin hammer, small and hard, for driving small pins.", ["tool", "metal"], 0.4),
    ("plane_iron", "A plane iron, flat and polished, sitting on the bench waiting for a handle.", ["tool", "metal", "wooden"], 0.2),
    ("block_plane", "A block plane, one iron in a wooden stock, and a blade that will not shift.", ["tool", "wooden", "metal"], 1.0),
    ("drawknife", "A drawknife, two handles and a blade between, pulled toward you.", ["tool", "metal", "wooden"], 3.0),
    ("froe", "A froe, for splitting shakes for a roof without a saw.", ["tool", "metal", "wooden"], 2.0),
    ("shaving_horse", "A shaving horse, a bench with a head clamped in it, and a shaving under the blade.", ["tool", "wooden", "furniture"], 12.0),
    ("lathe_chisel", "A lathe chisel, long and with two wings, for hollowing a bowl.", ["tool", "metal"], 0.4),
    ("gouge", "A gouge, a curved blade, for cutting a groove across the grain.", ["tool", "metal", "wooden"], 0.5),
    ("file", "A file, flat and rasp-toothed, worn to a slope on one side.", ["tool", "metal"], 0.3),
    ("oil_stone", "An oilstone, a block of fine sandstone, and the slip is the oil and the water.", ["tool", "stone", "furniture"], 1.0),
    ("bow_drill", "A bow drill, a flywheel, a shaft and a bit, and a push and a pull.", ["tool", "metal", "wooden", "craft"], 1.5),
    ("stave_binder", "A stave binder, a length of withy for tying a bundle together.", ["tool", "fibre", "farming"], 0.1),
    ("whetstone_box", "A whetstone box, wooden, with a lid and a slurry of water and grit inside.", ["container", "wooden", "tool"], 0.3),
    ("snuffbox", "A snuffbox, horn, and the lid inlaid with a strip of mother-of-pearl.", ["personal", "container", "accessory", "small", "valuable"], 0.2),
    ("distaff", "A distaff, wound with unspun wool, and the spinner never sits down.", ["tool", "wooden", "craft", "fibre"], 0.6),
    ("oil_paper", "A sheet of oiled paper, translucent, for wrapping what must stay dry.", ["material", "paper"], 0.05),
    ("waxed_cloth", "A square of waxed cloth, for a pack, a roof, or a letter.", ["material", "cloth", "insulation"], 0.3),
    ("book_clasp", "A book clasp, brass, for a chained book that has to be shut against damp.", ["accessory", "metal", "book", "clothing"], 0.05),
    ("bookmark", "A bookmark of vellum, ribbon threaded through the head, and it is always lost.", ["book", "personal", "paper", "small"], 0.02),
    ("reading_glasses", "A pair of reading glasses, in a leather case, for a book held at the right distance.", ["accessory", "glass", "personal", "eyewear"], 0.1),
    ("wax_tablet", "A wax tablet, wooden frame and a stub of stick, and a page that can be scraped and used again.", ["book", "writing", "document", "paper", "tool"], 0.4),
    ("gouraud_wax", "A stick of sealing wax, red, and a stick that has been melted onto too many letters.", ["document", "writing", "small", "paper"], 0.05),
    ("document_seal", "A seal, a stamp of a device on a handle, and the wax that takes the impression.", ["document", "personal", "writing", "clothing"], 0.3),
    ("parchment_sheet", "A sheet of parchment, scraped thin, and a quill ready beside it.", ["document", "paper", "writing", "display"], 0.1),
    ("document_roll", "A roll of vellum, tied with a cord, for a deed or a charter.", ["document", "paper", "writing", "display", "container"], 0.4),
    ("copybook", "A copybook, ruled and blank, and a stub of a pen.", ["book", "writing", "paper", "document"], 0.6),
    ("quill_pen", "A quill pen, a feather cut to a nib, and the shaft chewed where it is held.", ["tool", "writing", "small", "fletching"], 0.02),
    ("chalk", "A stick of chalk, white, and dust on the slate in every schoolroom.", ["tool", "writing", "small", "display"], 0.05),
    ("inkpot", "An inkpot, horn, and the ink inside gone to tar.", ["container", "writing", "small"], 0.05),
    ("crayon", "A crayon, a stub of colour wrapped in a paper sleeve, and the paper is a lesson.", ["tool", "writing", "small", "display"], 0.02),
    ("wax_crayon_box", "A box of wax crayons, a dozen colours, and every lid is a different size.", ["toy", "writing", "small", "storage", "display"], 0.4),
    ("magnet", "A lodestone, an odd lump of iron ore that points north and turns.", ["tool", "navigational", "stone", "magic"], 0.8),
    ("compass", "A compass in a wooden box, the needle riding high and wobbling at the least breath.", ["tool", "navigational", "navigation", "small"], 0.3),
    ("sextant", "A sextant, brass, and the arc divided into degrees for a reason.", ["tool", "navigational", "navigation", "metal"], 2.0),
    ("horologium", "A horologium, a sundial-cum-water-clock, and it is right twice a day.", ["tool", "navigational", "navigation", "metal", "timed"], 4.0),
    ("water_clock", "A water clock, a float in a jar, dripping at a rate you can trust on a calm day.", ["tool", "timed", "glass", "navigation"], 1.0),
    ("sandglass", "A sandglass, the glass worn to a cloud, run out twice and not a third.", ["tool", "timed", "glass", "navigation"], 0.4),
    ("bell_rope", "A bell rope, a thick hempen line through the loft, and it goes down a long way.", ["sound_source", "fibre", "town"], 5.0),
    ("hand_bell", "A hand bell, bronze, rung for the hour or for a warning.", ["sound_source", "metal", "town", "tool"], 0.8),
    ("church_bell_note", "A written note of the bell's sound, so a deaf man can know the hour.", ["document", "information", "paper", "written"], 0.05),
    ("cushion", "A cushion, a flat bag of feathers, to lean back on.", ["furniture", "bedroom", "insulation", "feather"], 0.5),
    ("pillow", "A pillow, linen, and a good one is worth saying out loud.", ["furniture", "bedroom", "cloth", "insulation"], 0.6),
    ("blanket_roll", "A rolled blanket, and a strap over it for carrying to a market.", ["furniture", "bedroom", "insulation", "cloth"], 2.0),
    ("horsehair_bed", "A horsehair mattress, and a smell no one ever gets used to.", ["furniture", "bedroom", "insulation", "fibre"], 12.0),
    ("bolster_stool", "A stool by the bed, and somewhere to set down the water.", ["furniture", "bedroom", "wooden"], 1.0),
    ("high_bed", "A high bed, on trestles, and a ladder to get up to it.", ["furniture", "bedroom", "wooden", "heavy"], 60.0),
    ("bed_curtain", "A bed curtain, green wool on a wire, and it is a room inside the room.", ["cloth", "bedroom", "insulation"], 1.5),
    ("chest_of_drawers", "A chest of drawers, oak, and one drawer that will not shut.", ["furniture", "storage", "wooden", "container"], 25.0),
    ("linen_cupboard", "A linen cupboard, airing and shallow, and smelling of lavender.", ["furniture", "storage", "wooden", "bedroom"], 30.0),
    ("dresser", "A dresser, its plates and cups on show, and the best china is only out at a wedding.", ["furniture", "storage", "wooden", "display"], 30.0),
    ("dining_table", "A dining table, scrubbed pale, and long enough for eight.", ["furniture", "wooden", "kitchen", "heavy"], 45.0),
    ("dining_chair", "A dining chair, a plank seat and four legs, and one is a pegged repair.", ["furniture", "wooden", "kitchen"], 4.0),
    ("bench_long", "A long bench, for a table that needs one, or for a congregation.", ["furniture", "wooden", "church"], 12.0),
    ("chair_stool", "A stool, three legs, and it is a seat and a ladder and a table in turn.", ["furniture", "wooden", "kitchen"], 1.5),
    ("shelf_board", "A shelf board, plain, and the wall behind it marked with ghost squares of what stood there.", ["furniture", "wooden", "storage"], 1.0),
    ("wall_hooks", "A row of iron hooks in a board, and a coat on each one.", ["furniture", "metal", "storage", "hallway"], 2.0),
    ("hall_stand", "A hall stand, with a dish for the keys and a slot for a staff.", ["furniture", "wooden", "hallway", "container"], 8.0),
    ("door_mat", "A door mat of rushes, to scrape a night's mud off before it goes further in.", ["furniture", "fibre", "hallway", "dirty"], 1.5),
    ("hanging_lamp", "A hanging lamp, an oil lamp on a chain, and the chain has to be long to get above a table.", ["light_source", "liquid", "hallway"], 2.0),
    ("hall_robe", "A worn robe for the hall, and nobody's business whose it is.", ["clothing", "hallway", "winter"], 1.2),
    ("stair_runner", "A stair runner, a strip of beaten cloth, to keep the polish on the treads.", ["cloth", "hallway", "insulation"], 4.0),
    ("wall_tapestry", "A tapestry on the wall, faded, and the scene is someone winning something.", ["art", "display", "wall", "textile", "large", "wallmounted"], 6.0),
    ("portrait_small", "A small portrait in a wooden frame, of someone whose name is not on the frame.", ["art", "display", "wall", "small", "wallmounted"], 0.8),
    ("carved_panel", "A carved panel in the wall, and the grain of the oak worn smooth where a hand rested.", ["art", "furniture", "wall", "wooden", "large", "wallmounted"], 8.0),
    ("beam_ceiling", "A ceiling beam, old oak, and one end of it is scorched where the fire got up.", ["furniture", "wooden", "wall", "ceiling", "large"], 60.0),
]

# â”€â”€ 12. build the records â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build():
    out = {}

    # Table order is (id, description, hunger, tags) for these two â€” relief before
    # the tag list, because the relief is the number an author wants to vary and
    # the tags are boilerplate. Unpacking them the other way round binds `tags` to
    # an int, which is a confusing way to be told a table is transposed.
    for item_id, desc, hunger, tags in VEGETABLES:
        out[item_id] = food(item_id, desc, hunger, tags,
                            message="You eat it. Better than nothing and not much more.")

    for row in HERBS:
        item_id, desc, tags = row[0], row[1], row[2]
        if len(row) > 3:      # a drinkable herb
            out[item_id] = drink(item_id, desc, row[3], tags)
        else:
            out[item_id] = thing(item_id, desc, tags, weight=0.05)

    for item_id, desc, tags in FRUITS:
        if item_id in out:
            continue
        out[item_id] = food(item_id, desc, 18, tags,
                            message="You eat it, and there is a little more after.")

    for item_id, desc, tags, hunger, edible in CROPS:
        if edible:
            out[item_id] = food(item_id, desc, hunger, tags, weight=0.3,
                                message="You eat it. It is not much, but it is food.")
        elif item_id in ("flax", "hemp"):
            # A standing fibre crop: what you take from it is the fibre, and the
            # first run yielded wheat from every non-edible row, which the linter
            # has no opinion about and which was simply wrong.
            out[item_id] = pool(item_id, desc, f"{item_id}_fibre", 2, 8, tags,
                                quantity=2, weight=2.0)
        elif item_id in ("hay", "straw_bale"):
            out[item_id] = pool(item_id, desc, "straw", 3, 6, tags,
                                quantity=2, weight=2.0)
        else:
            # Clover, alfalfa and thatch reed are *cut*, not foraged: the standing
            # plant is not the resource, and a pool that hands out wheat for a field
            # of clover is a lie in the save file.
            out[item_id] = thing(item_id, desc, tags, weight=2.0)

    for item_id, desc, tags, hunger, edible in FUNGI:
        if edible:
            out[item_id] = food(item_id, desc, hunger, tags, weight=0.1,
                                message="You eat it. It is worth the walk.")
        else:
            out[item_id] = thing(item_id, desc, tags, weight=0.1)

    for item_id, desc, tags, hunger, edible in MEAT:
        if "drink" in tags:
            out[item_id] = drink(item_id, desc, hunger, tags, weight=1.0)
        elif "egg" in tags:
            out[item_id] = food(item_id, desc, hunger, tags, weight=0.05, uses=2,
                                message="You eat it, and it goes down easier than you expected.")
        else:
            out[item_id] = food(item_id, desc, hunger, tags, weight=0.6,
                                message="You eat it, and wish there were more.")

    for item_id, desc, tags, hunger, edible in COOKED:
        # `edible=False` rows are the *ingredients* that share this table because
        # they are cooked with: tallow, wax, the oils, vinegar. They are materials,
        # and the first run of this script made them food â€” which
        # `tools/lint_library.py::check_unauthored_consumables` caught, which is
        # precisely what that check is for.
        if not edible:
            out[item_id] = thing(item_id, desc, tags, weight=0.5)
        elif "drink" in tags:
            out[item_id] = drink(item_id, desc, hunger, tags, weight=0.5)
        else:
            out[item_id] = food(item_id, desc, hunger, tags, weight=0.4,
                                message="You eat it. That was worth stopping for.")

    for item_id, desc, tags, weight in MATERIALS:
        out[item_id] = thing(item_id, desc, tags, weight=weight)

    for item_id, desc, tags, weight in HOUSEHOLD:
        out[item_id] = thing(item_id, desc, tags, weight=weight)

    for item_id, desc, tags, weight in TOWN:
        out[item_id] = thing(item_id, desc, tags, weight=weight)

    for entry in TOOLS:
        # A row may carry a 5th dict of record overrides (task-518: a ranged
        # weapon declares damage/slots/actions, which the plain shape cannot).
        item_id, desc, tags, weight = entry[:4]
        extra = entry[4] if len(entry) > 4 else {}
        out[item_id] = tool(item_id, desc, tags, weight=weight, **extra)

    # The four wearables, built through `worn()` so they carry a real slot. They
    # sit in their own tables above for reading order and are emitted here.
    out["book_clasp"] = worn(
        "book_clasp", "A book clasp, brass, for a chained book that has to be shut against damp.",
        ["accessory", "metal", "book", "small", "valuable"], "accessory")
    out["document_seal"] = worn(
        "document_seal", "A seal, a stamp of a device on a handle, and the wax that takes the impression.",
        ["document", "personal", "writing", "small", "valuable"], "hand_right")
    out["hall_robe"] = worn(
        "hall_robe", "A worn robe for the hall, and nobody's business whose it is.",
        ["textile", "hallway", "winter", "insulation"], "torso", weight=1.2,
        insulation=6)
    out["quill_bed"] = worn(
        "quill_bed", "A feather bed, tickled with goose down, and the ticking is the point.",
        ["bedroom", "furniture", "insulation", "feather"], "torso", weight=6.0,
        insulation=12)

    return out

def records():
    """Every item this pass authors, as ``{{id: record}}``."""
    return build()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="overwrite ids already in the library")
    args = parser.parse_args(argv)
    return write(records(), label=PASS, force=args.force)


if __name__ == "__main__":
    main()
