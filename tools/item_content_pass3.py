"""
Item content pass 3 — the wild: forage, game and fishing.

Authored content. **The tables are the work**; the record shapes come from
`item_shapes.py`, so a fix to how a consumable is authored lands in one place and
a pass that makes a claim it cannot back is refused rather than written.

    run     python tools/item_content_pass3.py
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

# Sibling passes, for the helpers these tables borrow. `b1` and
# `_row` are the names the `build()` body below refers to.
spec = importlib.util.spec_from_file_location(
    "content_pass1", os.path.join(_HERE, "item_content_pass1.py"))
_pass1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_pass1)
spec = importlib.util.spec_from_file_location(
    "content_pass2", os.path.join(_HERE, "item_content_pass2.py"))
_pass2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_pass2)
b1 = _pass1
_row = row

PASS = "pass3"

# â”€â”€ forage: the edible wild, by where it grows â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
FORAGE = [
    ("wild_sorrel", "Wild sorrel, a fistful, and the sourness of it is the whole point.", 12, ["forage", "herb"]),
    ("sorrel_jelly", "A jelly made of wild sorrel, green and set in a pot, and it is a delicacy nobody admits to.", 16, ["food", "preserve", "forage"]),
    ("wood_sorrel_raw", "Wood sorrel, the whole plant, eaten raw and tasting of lemon and thin air.", 10, ["forage", "herb"]),
    ("nettle_top", "Nettle tops, the youngest, cooked and they are worth the sting they cost.", 16, ["forage", "vegetable", "fibre"]),
    ("nettle_cord", "A cord of nettle fibre, and it makes a rope that survives the wet.", 0, ["forage", "fibre"]),
    ("wild_garlic_bunch", "A bunch of wild garlic, the leaves pulled from a wood in April.", 16, ["forage", "herb", "allium"]),
    ("ramsons_pesto", "Pesto of wild garlic and oil and hard cheese, and it is green enough to stain.", 24, ["food", "herb", "preserve"]),
    ("dandelion_clock", "A dandelion clock, and the seeds go up in a cloud if you breathe on it.", 0, ["forage", "plant", "natural"]),
    ("dandelion_root_dried", "Dried dandelion root, sliced, and it is the coffee substitute of the poor.", 0, ["forage", "herb", "medicinal", "root"]),
    ("dandelion_root_roasted", "Roasted dandelion root, ground, and it brews like a dark weak coffee.", 14, ["drink", "forage", "root"]),
    ("chicory_root", "Chicory root, roasted and ground, bitter enough to be taken black.", 0, ["forage", "herb", "root"]),
    ("chicory_coffee", "Chicory coffee, roasted chicory root in water, and it is drunk for the look of coffee.", 16, ["drink", "forage", "root"]),
    ("burdock_root", "Burdock root, dug and scrubbed, and the reason it is in a bottle of headache water.", 0, ["forage", "herb", "medicinal", "root"]),
    ("burdock_leaf", "Burdock leaves, the big grey undersides, and they are edible young.", 12, ["forage", "vegetable", "plant"]),
    ("alexanders_leaf", "Alexanders leaves, gathered while the ground is still cold.", 10, ["forage", "herb"]),
    ("ground_ivy", "Ground ivy, the creeping plant, and it smells of mint and makes a tea for a head.", 10, ["forage", "herb", "tea"]),
    ("wild_thyme_bunch", "Wild thyme, a bunch of it, cut from a bank where the bees are on it too.", 10, ["forage", "herb"]),
    ("wild_marjoram_bunch", "Wild marjoram, the pink-flowered kind, and it is hotter than the potted one.", 10, ["forage", "herb"]),
    ("meadow_grass_handful", "A handful of meadow grass, pulled green because the cattle have not had it.", 0, ["forage", "fodder", "plant"]),
    ("reeds_shoot", "Reed shoots, the young roots, and they taste of a marsh and are worth the digging.", 14, ["forage", "vegetable", "plant"]),
    ("sea_bean", "Sea beans, the little ones on the strand line, and they taste of the sea and anise.", 10, ["forage", "marine", "vegetable"]),
    ("sea_holly_root_raw", "Sea holly root, the dark thing under a shingle beach.", 10, ["forage", "root", "plant"]),
    ("sea_salt_crust", "A crust of dried sea salt on a rock, and it is scraped off with a knife.", 0, ["forage", "salt", "marine"]),
    ("dried_seaweed_rope", "Dried seaweed, the bladdered kind, and it goes in a stew as a thickener.", 12, ["forage", "marine", "plant"]),
    ("spruce_tip", "A spruce tip, the soft new growth, and it is the best part of the tree to eat.", 8, ["forage", "plant"]),
    ("young_pine_cone", "A young pine cone, the first-year one, and it is soft and sweet before the resin sets.", 8, ["forage", "plant", "natural"]),
    ("birch_sap", "Birch sap, tapped in March, and a cup of it is a spring morning in a glass.", 18, ["forage", "drink", "plant", "tree"]),
    ("birch_sap_jar", "A jar of birch sap, and it will have gone fizzy and sour by tomorrow.", 16, ["forage", "drink", "plant", "tree"]),
    ("maple_syrup_pot", "A pot of maple syrup, the sap boiled down, and it is the whole reason to tap a tree.", 26, ["food", "sweet", "preserve", "tree"]),
    ("maple_syrup_pour", "Maple syrup poured over something, and it goes gold in the cold.", 30, ["food", "sweet", "tree"]),
    ("acorn_flesh", "Acorn flesh, the green bitter part inside, and it must be leached before it is food.", 0, ["forage", "nut", "hazard"]),
    ("acorn_meal", "Acorn meal, and the bitterness is mostly gone and what is left is the point of it.", 20, ["food", "nut", "grain"]),
    ("acorn_coffee", "Roasted acorn coffee, and it tastes of a wood in autumn, which is a compliment.", 14, ["drink", "nut", "forage"]),
    ("beech_nut_pile", "Beechmast, a double handful, and the squirrels have not got them all.", 12, ["forage", "nut"]),
    ("hazelnut_husk", "Hazelnut husks, a heap, and the nuts inside are pale and hard.", 0, ["forage", "nut", "plant"]),
    ("hazel_nut_kernel", "A hazelnut cracked, and the kernel is white and sweet and the best of the nut.", 14, ["food", "nut"]),
    ("hazel_nut_pickled", "Pickled hazelnuts, in brine, and they go further than you would think.", 12, ["food", "preserve", "nut"]),
    ("walnut_husk_whole", "A walnut husk, the whole green thing, before it is anything else.", 0, ["forage", "nut", "plant"]),
    ("sweet_chestnut_roast", "Roast chestnuts, the scored shells, and the flesh is floury and sweet.", 24, ["food", "nut", "sweet"]),
    ("sweet_chestnut_raw", "A raw sweet chestnut, and it is fine raw and better roasted.", 14, ["food", "nut"]),
    ("horse_chestnut", "A horse chestnut, glossy and brown, and it is not a chestnut and will sicken you.", 0, ["forage", "hazard", "poisonous", "plant"]),
    ("rowan_berry", "Rowan berries, the orange bunches, and they are too sour raw and good in a syrup.", 0, ["forage", "fruit", "plant"]),
    ("rowan_berry_syrup", "Rowan berry syrup, the autumn bitter made into a medicine.", 18, ["food", "preserve", "medicinal", "fruit"]),
    ("wayfarer_tree_berry", "A wayfarer's berry, the tiny scarlet one on a roadside, and it stains the tongue.", 8, ["forage", "fruit"]),
    ("whitebriar_berry", "A whitebriar berry, the small blue-black one, and there is one mouthful in a bush.", 10, ["forage", "fruit"]),
    ("hawthorn_leaf_tea", "Hawthorn leaves, dried, for a tea, and the berries are better for the heart.", 0, ["forage", "herb", "tea", "medicinal"]),
    ("linden_leaf", "Linden leaves, the heart-shaped ones, and the smell of the tree in June is why they are picked.", 0, ["forage", "herb", "fragrant", "plant"]),
    ("linden_honey", "Honey from a linden, and it is the pale and perfumed kind.", 20, ["food", "sweet", "preserve", "tree"]),
    ("meadow_flower_bunch", "A bunch of meadow flowers, the ox-eye daisies and the cornflowers, and it is a posy.", 0, ["forage", "plant", "fragrant", "flower"]),
    ("cornflower", "A cornflower, blue as a bruise, and it is bitter enough to be a fever cure.", 10, ["forage", "plant", "medicinal", "flower"]),
    ("ox_eye_daisy", "An ox-eye daisy, the big white one, and there is no bee that ignores it.", 0, ["forage", "plant", "flower", "fragrant"]),
    ("meadow_foam", "Meadow foam, the white flower of wet ground, and it tastes of nothing and looks of cream.", 0, ["forage", "plant", "flower"]),
    ("wild_pansy", "A wild pansy, the little heart-faced flower, and it is called heartsease for a reason.", 0, ["forage", "plant", "flower"]),
    ("pansy_candy", "Pansies candied, on sticks, and a market stall sells them to a child in winter.", 16, ["food", "sweet", "flower"]),
    ("heather_honey", "Heather honey, the dark one, and it tastes of the moor it came from.", 20, ["food", "sweet", "preserve"]),
    ("heather_sprig", "A sprig of heather, purple and sticky, and a bee working it is worth the watch.", 0, ["forage", "plant", "flower", "fragrant"]),
    ("bog_myrtle", "Bog myrtle, the shrub on a wet peat bog, and its scent carries a mile.", 0, ["forage", "plant", "fragrant"]),
    ("bogbean_leaf", "Bogbean leaves, the three-lobed ones on a bog, bitter as gall.", 0, ["forage", "plant", "medicinal"]),
    ("cattail", "A cattail, the brown sausage of a spike, and it is not food but it is a bed of them.", 0, ["forage", "plant", "natural"]),
    ("sedge_bunch", "A bunch of sedge, cut and bundled, and it is the thatcher's first material.", 0, ["forage", "plant", "fodder"]),
    ("rush_light_reed", "Reeds for rushlights, a handful, and they are dipped in tallow and lit.", 0, ["forage", "fibre", "plant"]),
    ("peat_bog_peat", "A block of peat cut from a bog, and it is the fuel of a place with no wood.", 0, ["forage", "fuel", "natural"]),
    ("gorse", "Gorse, the spiny yellow thing on waste ground, and it burns hot and smells of scorched sugar.", 0, ["forage", "fuel", "plant", "hazard"]),
    ("bracken", "Bracken, the fern, cut and dried for bedding or for burning, and the stalks make a green dye.", 0, ["forage", "fuel", "fibre", "dye", "plant"]),
    ("bracken_stalk_dye", "Bracken stalk dye, boiled to a green that fixes on wool with alum.", 0, ["forage", "dye", "fibre"]),
    ("hazel_dye_bark", "Hazel bark, and a yellow-brown dye from it, and it is what most medieval cloth is.", 0, ["forage", "dye", "plant"]),
]

# â”€â”€ eggs, birds and small game â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
GAME = [
    ("wild_duck_egg", "A duck egg, speckled blue-green, and it needs boiling or it will not be argued with.", 18, ["food", "egg", "forage"]),
    ("partridge_egg", "A partridge egg, small and buff, and there were a dozen in the nest.", 16, ["food", "egg", "forage"]),
    ("pheasant_egg", "A pheasant egg, the pale one, and it is bigger than a hen's.", 18, ["food", "egg", "forage"]),
    ("pigeon_egg", "A pigeon's egg, small and white, and a city eats them and calls it a pigeon pie.", 16, ["food", "egg", "forage"]),
    ("robin_egg", "A robin's egg, the blue one, and you need a good argument for taking it.", 12, ["forage", "egg", "hazard", "fletching"]),
    ("snipe_egg", "A snipe egg, pointed at both ends, and a moorland thing worth the walk.", 14, ["food", "egg", "forage"]),
    ("plover_egg", "A plover's egg, laid in a scrape in the ground with no nest at all.", 14, ["food", "egg", "forage"]),
    ("gull_egg", "A gull egg, mottled brown, and a cliff ledge is a bad place to be caught taking one.", 16, ["food", "egg", "forage", "hazard"]),
    ("swan_egg", "A swan's egg, a fist of a thing, and it is a feast and a theft at the same time.", 26, ["food", "egg", "forage"]),
    ("hen_egg_brown", "A hen's egg, brown-shelled, and the yolks are darker than a hen's at the same age.", 18, ["food", "egg", "farming"]),
    ("sparrow_meat", "A sparrow, plucked and skewered, and it is two mouthfuls and a bone.", 10, ["food", "meat", "forage", "fletching"]),
    ("woodpigeon_meat", "Woodpigeon, the squab, and it is a delicacy and there are a great many of them.", 24, ["food", "meat", "poultry", "forage"]),
    ("hare_dung", "Hare dung, a heap of it, and a farmer would call that a crop.", 0, ["forage", "fodder", "filth"]),
    ("rabbit_pelt", "A rabbit pelt, and the skin is worth more than the meat to anyone who knows.", 0, ["forage", "fibre", "fletching", "leather"]),
    ("fox_pelt", "A fox pelt, and it is worth a great deal to a man who has the use of it.", 0, ["forage", "fibre", "fletching", "leather"]),
    ("squirrel_skin", "A squirrel skin, and the pelt is a quarter of what the animal was.", 0, ["forage", "fibre", "fletching", "leather"]),
    ("deer_hide", "A deer hide, and it is the best leather there is, and the animal was not.", 0, ["forage", "fibre", "leather", "large"]),
    ("wolf_pelt", "A wolf pelt, and one pays a bounty on it and the pelt is the price.", 0, ["forage", "fibre", "fletching", "leather"]),
    ("bird_egg_collection", "A nest of eggs, a dozen of them, packed in straw and the straw is warm.", 0, ["forage", "egg", "container", "fodder"]),
    ("grub", "A fat grub, a woodlouse, and it goes on a hook and it is what a pike eats.", 8, ["forage", "bait", "fishing"]),
    ("earthworm", "An earthworm, dug and put in a pot, and a pike will not look at anything else.", 4, ["forage", "bait", "fishing", "fodder"]),
    ("maggot", "Maggots, a handful, in a bait tin, and a man in a bad place is glad of them.", 6, ["forage", "bait", "fishing"]),
    ("crayfish", "A crayfish, boiled, and the tail meat is the only part anybody wants.", 14, ["forage", "fish", "shellfish", "food"]),
    ("freshwater_crab", "A freshwater crab, and you have to boil it before the claws will let go.", 12, ["forage", "fish", "shellfish", "food"]),
    ("snail", "A snail, and there is a way to eat them and it is not one for the impatient.", 8, ["forage", "food", "small"]),
    ("hedgehog", "A hedgehog, curled, and it is a pest in a garden and a meal in a bad month.", 18, ["forage", "meat", "food", "fletching"]),
    ("frog", "A frog, and a frog's legs are a treat and a frog is not.", 12, ["forage", "food", "water"]),
    ("snake_skin", "A snake skin, cast, and it is a curiosity and a strap.", 0, ["forage", "fibre", "fletching", "leather"]),
    ("feather_bed_stocking", "A bed of feathers and down, and it is stuffed by a woman with a whole winter of work.", 0, ["forage", "fibre", "feather", "bedroom"]),
    ("wild_feather", "A wild feather, barred, and a fly-tyer would give a year for a good one.", 0, ["forage", "fibre", "fletching", "fletching"]),
    ("goose_egg_ducked", "A duck's egg, and a whole clutch of them is a week of eating.", 18, ["food", "egg", "forage"]),
]

# â”€â”€ fishing catch â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
FISH = [
    ("tench", "A tench, a dark green pond fish, and it is the fish of a still water.", 28, ["fish", "food", "fishing"]),
    ("perch_fish", "A perch, striped and spiny, and it tastes of the water it came from.", 26, ["fish", "food", "fishing"]),
    ("roach", "Roach, a shoal of them, and they are bony and free and good fried small.", 20, ["fish", "food", "fishing"]),
    ("bream", "A bream, deep-bodied and silver, and a coarse fish until it is smoked.", 24, ["fish", "food", "fishing"]),
    ("rudd", "A rudd, red-finned, and the cruellest fish to be hooked.", 20, ["fish", "food", "fishing"]),
    ("dace", "A dace, the silver flash of a fish and it is the first of the season.", 20, ["fish", "food", "fishing"]),
    ("gudgeon", "Gudgeon, a bottom-feeder, and there are a hundred of them in a net.", 18, ["fish", "food", "fishing"]),
    ("chub", "A chub, a fat river fish, and it is best smoked over oak.", 30, ["fish", "food", "fishing"]),
    ("barbel", "A barbel, and it is a coarse fish that a whole village will queue for.", 28, ["fish", "food", "fishing"]),
    ("pike_roast", "A pike, roasted whole, and the flesh is firm and faintly muddy and worth it.", 32, ["fish", "food", "fishing"]),
    ("seabass", "A sea bass, silver and black-backed, and the best fish on a coast.", 34, ["fish", "food", "fishing", "marine"]),
    ("mackerel", "Mackerel, striped like a barrel hoop, and it goes off the oil in a day.", 26, ["fish", "food", "fishing", "marine"]),
    ("sardine", "Sardines, a netful, and they are the cheapest fish and the fastest.", 20, ["fish", "food", "fishing", "marine"]),
    ("plaice", "A plaice, flat and orange-spotted, and it needs lemon and more lemon.", 26, ["fish", "food", "fishing", "marine"]),
    ("sole", "A sole, the flat fish, and it is the most expensive thing on a stall by weight.", 30, ["fish", "food", "fishing", "marine"]),
    ("hake", "Hake, a pale fish, and the sea bass of poor households.", 26, ["fish", "food", "fishing", "marine"]),
    ("whelk", "A whelk, the big sea snail, and it is boiled and eaten with a pin.", 12, ["forage", "food", "marine", "shellfish"]),
    ("limpet", "A limpet, off a rock at low water, and it tastes of the rock.", 8, ["forage", "food", "marine", "shellfish"]),
    ("sea_bean_jelly", "Sea beans, pickled in vinegar, and they are a pickle for the poor.", 12, ["food", "preserve", "marine", "fish"]),
    ("pickled_herring", "Pickled herring, in a barrel with the onions, and it is the smell of a port.", 26, ["food", "preserve", "fish", "marine"]),
    ("red_caviar", "Red caviar, a pot of it, and it is roe with salt and nothing else.", 12, ["food", "preserve", "fish", "marine"]),
    ("fish_roe", "Fish roe, a sack of it, and salted down it keeps till spring.", 14, ["food", "preserve", "fish"]),
    ("dried_fish_stock", "A stock made of dried fish bones, and it is the cheapest stock there is.", 22, ["food", "liquid", "fish", "kitchen"]),
    ("fish_scale", "Fish scales, a tin of them, and the brightness of a scale is the sign of a fine fish.", 0, ["fish", "fodder", "waste"]),
    ("fish_gut", "Fish guts, and they go to the kennel and a dog will tell you.", 0, ["fish", "waste", "filth"]),
    ("net_float", "A cork float on a net, and the net is set by where the floats sit.", 0, ["tool", "fishing", "container"]),
    ("fish_trap", "A fish trap, wicker, and it works best in a run of a stream.", 0, ["tool", "fishing", "fibre"]),
    ("creel", "A creel, a wicker basket for fish, and it is carried on the back and set overnight.", 0, ["tool", "fishing", "fibre", "container"]),
    ("angling_rod", "An angling rod, a hazel rod and a line, and it is the cheapest of all sporting goods.", 0, ["tool", "fishing", "wooden"]),
    ("bait_bucket", "A bait bucket, wooden, and the lid is a board so the water stays out.", 0, ["container", "wooden", "fishing", "bait"]),
    ("bait_tin", "A bait tin, and the worms are in it and the water is not.", 0, ["container", "metal", "fishing", "bait"]),
    ("feather_lure", "A feather lure, a hackle and a small hook, and it is a lie told well.", 0, ["tool", "fishing", "fletching", "bait"]),
    ("spoon_lure", "A spoon, a bright metal leaf on a length of wire, and it turns in the water.", 0, ["tool", "fishing", "metal", "bait"]),
    ("salmon_trout_rod", "A long rod for salmon, two men to carry it, and the line is forty fathoms.", 0, ["tool", "fishing", "wooden"]),
    ("angler_lantern", "An angler's lantern, hooded, and it hangs on the punt and the fish come to it.", 0, ["tool", "fishing", "light_source", "metal"]),
    ("punt_pole", "A punt pole, long and flat-ended, and a punt is a flat boat pushed along a fen.", 0, ["tool", "fishing", "wooden", "boat"]),
    ("fishing_basket_weave", "A wicker fish basket, woven wet and worked round, and it goes in the water for years.", 0, ["tool", "fishing", "fibre", "container"]),
    ("gudgeon_bait_pot", "A pot of worm bait, dug the night before, and a cold morning needs a hot cup.", 0, ["container", "bait", "fishing", "forage"]),
    ("weather_glass", "A weather glass, a sealed tube of spirit, and the column rises before a wet day.", 0, ["tool", "navigational", "glass", "navigation"]),
    ("tide_table", "A tide table, a printed sheet, and the whole harbour works by it.", 0, ["document", "navigation", "book", "navigational"]),
    ("fish_mark", "A fish mark, a piece of lead with a stamp, and it proves which fish.", 0, ["tool", "fishing", "lead", "metal"]),
    ("fisher_greats", "Fisher's grease, a jar of it, and the boats smell of it all winter.", 0, ["material", "fishing", "fat", "marine"]),
    ("tarred_rope", "Tarred rope, and the smell of a tarred rope is a harbour in one breath.", 0, ["material", "fibre", "marine", "fishing"]),
    ("net_mender_needle", "A netting needle, a flat bone needle, and a mend takes a hundred of them.", 0, ["tool", "fishing", "fibre", "marine"]),
    ("hanging_net", "A net hung out to dry, and it is a wall you cannot see through.", 0, ["tool", "fishing", "fibre", "marine", "large"]),
    ("fish_offal", "Fish offal, a bowl of it, and it goes to the poor or to the pigs.", 12, ["fish", "waste", "filth", "food"]),
    ("seagull_egg_guano", "Gull guano, a barrow of it, and it is the coast's answer to a dung heap.", 0, ["forage", "fodder", "marine", "filth"]),
]


def _row(item):
    """Normalise a table row to ``(id, description, tags, relief)``.

    Both shapes appear in these tables and both are legible: a 4-tuple is
    *consumable* (relief is a number) and a 3-tuple is a plain thing. The first
    version of this batch unpacked every row into four names, which put 28
    fishing tools through `food()` and gave each of them a `food` tag â€” caught by
    `check_unauthored_consumables`, which is the third time this exact shape of
    mistake has been made across the three batches. Deciding on the **row's
    shape** rather than on a flag in a fixed position is what stops it recurring.
    """
    item_id, desc = item[0], item[1]
    if len(item) >= 4 and isinstance(item[2], (int, float)):
        return item_id, desc, list(item[3]), int(item[2])
    tags = list(item[2]) if len(item) >= 3 and isinstance(item[2], list) else []
    return item_id, desc, tags, None


def build():
    out = {}

    def add(item):
        item_id, desc, tags, relief = _row(item)
        if relief is None or relief <= 0:
            # A row that is not made edible must not keep saying it is. These
            # tables carry `food` on honeys, syrups and offal that were given a
            # relief of `0` as a placeholder, and the first version wrote them as
            # things that still claimed to be food — which is precisely the "a tag
            # is enough to make an item edible" bug task-506 retired, and the
            # linter names every one. Strip the unbacked claim rather than
            # inventing a number for it; the ones that really are food get a
            # number in the table.
            out[item_id] = thing(item_id, desc,
                                 [t for t in tags if t not in ("food", "drink")]
                                 or ["material"], weight=0.4)
            return
        if "drink" in tags and "food" not in tags:
            out[item_id] = b1.drink(item_id, desc, relief, tags, weight=0.3)
        else:
            out[item_id] = b1.food(item_id, desc, relief, tags, weight=0.2,
                                    message="You eat it, gathered and not much cleaned.")

    for row in FORAGE:
        add(row)
    for row in GAME:
        add(row)
    for row in FISH:
        add(row)
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
