"""
Item content pass 2 — farming and kitchen, in depth.

Authored content. **The tables are the work**; the record shapes come from
`item_shapes.py`, so a fix to how a consumable is authored lands in one place and
a pass that makes a claim it cannot back is refused rather than written.

    run     python tools/item_content_pass2.py
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
b1 = _pass1
_row = row

PASS = "pass2"

# â”€â”€ vegetables, second pass: salad, pot herbs, roots, period English â”€â”€â”€â”€â”€â”€â”€
VEG2 = [
    ("sorrel_leaf", "Sorrel leaves, the arrow-shaped ones, sour enough to be a salad on their own.", 12, ["vegetable", "leafy"]),
    ("lambs_lettuce", "Lamb's lettuce, the small loose heads that come earliest and are gone by June.", 14, ["vegetable", "leafy"]),
    ("chervil", "Chervil, the feathery leaves, and it is the only herb that tastes of anise and parsley both.", 10, ["vegetable", "herb"]),
    ("salad_burnet", "Salad burnet, the cucumber-flavoured leaves, used in a sauce with chives.", 12, ["vegetable", "herb"]),
    ("watercress", "Watercress, from the cold stream, peppery and wet.", 12, ["vegetable", "leafy"]),
    ("mustard_green", "Mustard greens, the leaves gone to seed and worth more for it.", 14, ["vegetable", "leafy"]),
    ("turnip_top", "Turnip tops, the leaves cut with the root, and a meal in themselves.", 12, ["vegetable", "leafy"]),
    ("beetroot", "Beetroot, the roots dug and stacked in a clamp for the winter.", 20, ["vegetable", "root"]),
    ("mangold", "Mangold, the rainbow chard, stems in a dozen colours and the leaf like spinach.", 18, ["vegetable", "leafy"]),
    ("salsify", "Salsify, the black root, and it tastes of oysters when it is cooked in milk.", 18, ["vegetable", "root"]),
    ("skirret", "Skirret, the pale roots, sweetest of anything in the garden and hard to dig up.", 22, ["vegetable", "root"]),
    ("lovage_leaf", "Lovage leaves, the big celery-scented ones, and two make a broth.", 12, ["vegetable", "herb"]),
    ("sea_kale", "Sea kale, the big blue-grey leaves that grow on a shingle beach.", 16, ["vegetable", "leafy"]),
    ("winter_cabbage", "A winter cabbage, the hard one that stands in a field through snow.", 20, ["vegetable", "leafy"]),
    ("dwarf_kale", "Dwarf kale, the curly kind, frost-bettered and sweeter after a hard night.", 18, ["vegetable", "leafy"]),
    ("alexanders", "Alexanders, the wild umbellifer, a whole town's worth of potherb in March.", 14, ["forage", "herb"]),
    ("hogweed", "Hogweed, the big coarse umbel, edible young and a blister if you are not careful.", 10, ["forage", "hazard"]),
    ("sweet_corn_cob", "An ear of sweetcorn, silk stripped, and the kernels dented where they meet.", 24, ["vegetable", "grain"]),
    ("onion_seed", "Onion seed, black and fine, sown in a tray and moved on in spring.", 4, ["seed", "vegetable"]),
    ("leek_seed", "Leek seed, a dusting of it, and the smell of it on the fingers for a week.", 4, ["seed", "vegetable"]),
    ("clove_garlic", "A single clove of garlic, lifted out of a bulb that will keep.", 8, ["vegetable", "allium", "spice"]),
    ("garlic_braid", "A braid of garlic bulbs, hung in the kitchen and used a clove at a time.", 6, ["vegetable", "allium", "preserve"]),
    ("braising_onion", "A braising onion, a small sweet one for the pot and not for the store.", 20, ["vegetable", "allium"]),
    ("pickled_walnut", "Pickled walnuts, green and in their shells, an acquired taste acquired early.", 14, ["food", "preserve", "nut"]),
    ("herb_butter", "Herb butter, a slab of it flecked green, going soft by the fire.", 22, ["food", "dairy", "condiment"]),
    ("garlic_butter", "Garlic butter, pale and faintly green, and it goes on everything.", 22, ["food", "dairy", "condiment"]),
    ("dripping_toast", "Toast and dripping, the fat going through the bread while you watch.", 30, ["food", "bread", "dairy"]),
    ("bread_and_cheese", "Bread and cheese, the farmer's lunch, and the whole of it in one hand.", 44, ["food", "bread", "dairy"]),
    ("raw_milk_cheese", "A raw-milk cheese, the rind tasting of the barn it was made in.", 26, ["food", "dairy"]),
    ("smoked_cheese", "Smoked cheese, cold-smoked over green wood, and the colour of a saddle.", 26, ["food", "dairy", "preserve"]),
    ("pressed_cheese", "Pressed cheese, hard and pale, and it rings when you knock it.", 28, ["food", "dairy"]),
    ("soft_cheese", "A soft white cheese, the rind going wrong if you look at it too long.", 24, ["food", "dairy"]),
    ("cheddar", "A round of cheddar, waxed, and a tunnel bored through the middle for keeping.", 28, ["food", "dairy"]),
    ("whey_butter", "Butter made from whey, the last of the milk and the best of the butter.", 22, ["food", "dairy"]),
    ("clotted_cream", "Clotted cream, the thick skin on the top of the pot.", 20, ["food", "dairy"]),
    ("sour_milk", "Sour milk, gone over deliberately, and the taste of a deliberate mistake.", 14, ["drink", "dairy"]),
    ("whey_broth", "Whey broth, what is left in the vat, drunk warm by whoever made the cheese.", 20, ["drink", "dairy"]),
    ("barley_water", "Barley water, boiled and strained and drunk cold, and the sick-day drink.", 22, ["drink", "grain"]),
    ("barm", "Barm, the yeast skimmed off the brewing vat, and it makes a fine bread.", 12, ["food", "grain", "yeast"]),
    ("treacle", "A pot of treacle, dark and bitter enough to be a medicine as well as a treat.", 24, ["food", "sweet", "preserve"]),
    ("molasses", "Molasses, the dregs left in the pan, black and sticky and prized.", 20, ["food", "sweet", "preserve"]),
    ("honey_garret", "A comb of honey with the cappings, wax and all, chewed.", 20, ["food", "sweet", "preserve"]),
    ("foraged_salad", "A foraged salad, sorrel and dandelion and young nettle, washed and dressed.", 22, ["food", "vegetable", "forage"]),
    ("dandelion_leaves", "Dandelion leaves, blanched in a minute and the bitterness gone out of them.", 16, ["food", "vegetable", "forage"]),
]

# â”€â”€ herbs, second pass: medicinal, dyeing, incense, strewing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
HERB2 = [
    ("strawberry_leaf", "Strawberry leaves, dried, for the astringent tea.", ["herb", "medicinal", "tea"]),
    ("raspberry_leaf", "Raspberry leaves, the best-tasting of all the leaf teas.", ["herb", "medicinal", "tea"]),
    ("blackcurrant_leaf", "Blackcurrant leaves, and the smell of them is the smell of a hedgerow in June.", ["herb", "medicinal", "tea"]),
    ("sage_dried", "Dried sage, grey-green and brittle, for stuffing and for tea.", ["herb", "culinary", "tea"]),
    ("rosemary_dried", "Dried rosemary, the needles fallen off and the stem like a wire.", ["herb", "culinary", "tea"]),
    ("thyme_dried", "Dried thyme, the little leaves gone to dust between your fingers.", ["herb", "culinary", "tea"]),
    ("marjoram_dried", "Dried marjoram, for the bean pot.", ["herb", "culinary"]),
    ("wild_garlic_bulb", "A wild garlic bulb, and the whole hillside stinks of it in April.", ["forage", "herb", "allium"]),
    ("wood_sorrel_bunch", "A bunch of wood sorrel, the trefoil leaves and a little of the flowers.", ["forage", "herb"]),
    ("pennyroyal", "Pennyroyal, a mint of a mint, and it makes a tea that clears the head and the stomach.", ["herb", "tea", "medicinal"]),
    ("southernwood", "Southernwood, the grey aromatic shrub by the door, used to keep the moths out of a chest.", ["herb", "strewing", "fragrant"]),
    ("woodruff", "Woodruff, the whorl of leaves and the smell of new-mown hay cut with it.", ["forage", "herb", "fragrant"]),
    ("gromwell", "Gromwell, the hound's tongue, blue seed and a hard root for a salve.", ["herb", "medicinal"]),
    ("soapwort", "Soapwort, the root that lathers in water and the saponin that does it.", ["herb", "medicinal", "cleaning"]),
    ("liverwort", "Liverwort, growing on wet stone, named for a liver and a belief.", ["herb", "medicinal"]),
    ("goldenrod", "Goldenrod, a spike of yellow at the field edge, and good for a wound.", ["forage", "herb", "medicinal"]),
    ("hyssop_hedge", "A hedge of hyssop, clipped flat, and the bees on it all summer.", ["herb", "plant"]),
    ("costmary", "Costmary, the big aromatic leaf used to scent a chest of cloth.", ["herb", "strewing", "fragrant"]),
    ("scented_geranium", "Scented geranium, the leaf that smells of rose and is not one.", ["herb", "fragrant", "pot"]),
    ("lemon_balm_sprig", "A sprig of lemon balm, for the tea pot.", ["herb", "tea"]),
    ("clove_bud_dried", "Dried clove buds, the spice and the perfume and the toothache cure.", ["herb", "spice", "medicinal"]),
    ("orris_root", "Orris root, dried and sliced, and it smells of a sweet dusty violet.", ["herb", "fragrant", "root"]),
    ("benzoin_resin", "Benzoin resin, a lump of it, and it burns sweet enough to sweeten a room.", ["herb", "incense", "fragrant"]),
    ("frankincense", "Frankincense resin, the pale tears, and the smoke of it going up.", ["herb", "incense", "fragrant"]),
    ("myrrh", "Myrrh, a dark resin, bitter and ancient and burned in a house.", ["herb", "incense", "fragrant"]),
    ("labdanum", "Labdanum, a sticky resin scraped from a rock, and the best-smelling thing in the box.", ["herb", "incense", "fragrant"]),
    ("juniper_bark", "Juniper bark, shredded, and the smell of a clean room.", ["herb", "incense", "strewing"]),
    ("rose_petal_dried", "Dried rose petals, pink and papery, and they keep the smell of the pot.", ["herb", "fragrant", "strewing"]),
    ("lavender_bundle", "A bundle of lavender, hung upside down to dry in the dark.", ["herb", "fragrant", "strewing"]),
    ("madder_root", "Madder root, and it dyes wool a red that has not faded in three hundred years.", ["herb", "dye", "root"]),
    ("woad_leaves", "Woad leaves, the big blue-green ones, for a blue that cost a fortune.", ["herb", "dye"]),
    ("weld", "Weld, the dye plant, and a yellow to startle anybody's socks.", ["herb", "dye"]),
    ("straw_bale_dye", "Weld, the dye plant, and a yellow to startle anybody's socks.", ["herb", "dye", "plant"]),
    ("logwood_chip", "Logwood chips, dark and red-tinged, and a black dye from the far coast.", ["herb", "dye", "wooden"]),
    ("indigo_cake", "Indigo cake, the fermented sediment, and the blue that is not woad.", ["herb", "dye", "alchemical"]),
    ("lichen_dye", "Orchil, a lichen, and the purple dye taken from it is worth the walk.", ["herb", "dye"]),
    ("walnut_husk", "Walnut hulls, a heap, and they dye a brown that needs no mordant at all.", ["herb", "dye"]),
    ("saffron_bulb", "A saffron crocus bulb, and three of its threads are a season's work.", ["herb", "spice", "plant"]),
    ("camomile_head", "Chamomile heads, picked and dried, still showing yellow in the middle.", ["herb", "tea", "medicinal"]),
    ("after_dinner_mint", "Peppermint after dinner, and the breath is improved for an hour.", ["herb", "culinary", "fresh"]),
    ("salt_herb", "Samphire, grown on a salt marsh, and the stems are salty enough to eat raw.", ["forage", "vegetable", "marine"]),
    ("sea_samphire", "Samphire, growing out of a salt marsh, pickled by the fishermen who cut it.", ["forage", "vegetable", "marine", "food"], 14, True),
    ("samphire_jelly", "Samphire jelly, set in a pot and gone the colour of the marsh it came from.", ["food", "preserve", "marine"], 12, True),
    ("sea_holly", "Sea holly, the blue flower on a dune, and the roots were candied like Alexanders.", ["forage", "herb", "plant"]),
    ("sea_beet_root", "Sea beet root, washed, and the coastal cook boils it and dresses it in oil.", ["forage", "vegetable", "marine", "food"], 16, True),
    ("sea_beet_leaf", "Sea beet leaves, the thick green ones, salted and cooked like spinach.", ["forage", "vegetable", "marine", "food"], 14, True),
    ("sea_angelica", "Sea angelica, the big umbel that grows on a shingle bank and smells of nothing.", ["forage", "herb", "plant"]),
    ("sea_holly_jelly", "Sea holly roots, candied, and a sweet that tastes of the sea it was dug from.", ["food", "sweet", "marine", "preserve"], 12, True),
]

# â”€â”€ fruit, second pass: orchard, hedgerow, soft fruit â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
FRUIT2 = [
    ("apple_pear_cake", "A pear and apple cake, the fruit gone soft and the top cracked.", ["food", "pastry", "fruit"], 40, True),
    ("baked_apple", "A baked apple, the skin split and the inside spooned out with cream.", ["food", "fruit", "sweet"], 30, True),
    ("apple_roast", "Roast apple, the smell of which is the smell of a kitchen in autumn.", ["food", "fruit"], 28, True),
    ("damson_jam", "Damson jam, purple and seedless, and it sets to a tremble.", ["food", "preserve", "fruit"], 24, True),
    ("plum_jam", "Plum jam, the golden kind, and better than any red.", ["food", "preserve", "fruit"], 24, True),
    ("blackberry_jam", "Blackberry jam, seeded, and it keeps a year in a cold cupboard.", ["food", "preserve", "fruit"], 24, True),
    ("apricot_jam", "Apricot jam, orange and sweet, and it goes to bread like nothing else.", ["food", "preserve", "fruit"], 24, True),
    ("cherry_jam", "Cherry jam, the stoned kind, dark red and full of whole cherries.", ["food", "preserve", "fruit"], 24, True),
    ("gooseberry_jam", "Gooseberry jam, the pale green kind with the seeds left in.", ["food", "preserve", "fruit"], 22, True),
    ("elderberry_jam", "Elderberry jam, the purple kind, and it needs a babysitter on the stove.", ["food", "preserve", "fruit"], 22, True),
    ("blackcurrant_jam", "Blackcurrant jam, dark and astringent, and the best of them.", ["food", "preserve", "fruit"], 24, True),
    ("red_currant_jam", "Red currant jam, pink and sharp, and it goes on cold mutton.", ["food", "preserve", "fruit"], 22, True),
    ("quince_jam", "Quince jam, the pink, set hard, and it has to be cut with a knife.", ["food", "preserve", "fruit"], 22, True),
    ("damson_cheese", "Damson cheese, the fruit set in blocks, and it goes on a hot scone.", ["food", "preserve", "fruit", "sweet"], 24, True),
    ("apple_cheese", "Apple cheese, the same trick, and it tastes like the fruit it came from.", ["food", "preserve", "fruit", "sweet"], 22, True),
    ("medlar_cheese", "Medlar cheese, brown and soft, and eaten in thin slices.", ["food", "preserve", "fruit", "sweet"], 20, True),
    ("orange", "An orange, the skins stacked in a net, and the first one in a month.", ["food", "fruit"], 18, True),
    ("lemon", "A lemon, the yellow one, and its rind is in everything.", ["food", "fruit", "citrus"], 12, True),
    ("lemon_curd", "Lemon curd, in a pot, and it is the yellowest thing in the house.", ["food", "preserve", "citrus", "sweet"], 22, True),
    ("lemon_bottled", "Bottled lemon juice, and it is what a ship carries for scurvy.", ["food", "preserve", "citrus", "liquid"], 16, True),
    ("orange_slices_dried", "Dried orange slices, and they are sold by the string.", ["food", "preserve", "citrus"], 14, True),
    ("candied_orange_peel", "Candied orange peel, sugared and cut in strips.", ["food", "sweet", "citrus", "preserve"], 14, True),
    ("grapes", "A bunch of grapes, the black kind, and the wasps have opinions.", ["food", "fruit"], 18, True),
    ("vine_shoot", "A vine shoot, the young growth, and the vine it came from is years older.", ["plant", "fruit"], 0, False),
    ("melon", "A melon, the ridged kind, and it knocks like a drum when it is ripe.", ["food", "fruit"], 26, True),
    ("water_melon", "A slice of watermelon, so cold it hurts the teeth.", ["food", "fruit", "sweet"], 24, True),
    ("melon_slice", "A slice of melon, the green flesh and a line of seeds down the middle.", ["food", "fruit", "sweet"], 22, True),
    ("damson_cheese_round", "A round of damson cheese, the top sugared.", ["food", "preserve", "fruit", "sweet"], 24, True),
    ("pomegranate", "A pomegranate, and getting the seeds out of one is an evening's work.", ["food", "fruit"], 20, True),
    ("fig_dried", "Dried figs, the black ones, and they are sticky and worth it.", ["food", "preserve", "fruit", "sweet"], 20, True),
    ("raisin", "Raisins, the seeded ones, and a fistful is a day's fruit.", ["food", "preserve", "fruit", "sweet"], 18, True),
    ("currant_dried", "Dried currants, small and black and sour enough to wake you.", ["food", "preserve", "fruit", "sweet"], 18, True),
    ("walnut_kernel", "A cracked walnut, the kernel in halves, and the skin stains the fingers.", ["food", "nut"], 16, True),
    ("hazelnut_kernel", "Hazelnut kernels, blanched, and they go into a stew like a secret.", ["food", "nut"], 16, True),
    ("almond_kernel", "Blanched almond kernels, and they are the cook's private supply.", ["food", "nut"], 16, True),
    ("pine_nut", "Pine nuts, and getting them out of the cone is a winter's evening's work.", ["food", "nut", "seed"], 16, True),
    ("toasted_nuts", "Toasted nuts, a handful, salted and still warm.", ["food", "nut", "snack"], 18, True),
    ("mixed_nuts", "A twist of fried nuts, the shop kind, wrapped in paper.", ["food", "nut", "snack"], 20, True),
    ("sesame_seed", "Sesame seed, a spoonful, and it goes on the top of a bun.", ["seed", "food", "spice"], 8, True),
    ("mixed_seed", "Mixed seed, hemp and flax and poppy, and it makes everything better.", ["seed", "food"], 12, True),
    ("pumpkin_seed", "Pumpkin seeds, dried, and they are the best thing in a handful of them.", ["seed", "food"], 14, True),
]

# â”€â”€ pulses, oilseeds, more crops â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
CROP2 = [
    ("turnip_seed", "Turnip seed, the pods drying on a stalk.", ["seed"], 4, True),
    ("swede_seed", "Swede seed, and a sowing is a week of shelling.", ["seed"], 4, True),
    ("cabbage_seed", "Cabbage seed, black and round, and enough for a whole field.", ["seed"], 4, True),
    ("onion_bulb", "A stored onion, sound and papery, and it keeps to spring.", ["vegetable", "allium", "store"], 16, True),
    ("garlic_bulb_stored", "A stored garlic bulb, the cloves drying to paper.", ["vegetable", "allium", "store"], 14, True),
    ("potato_sack", "A sack of seed potatoes, and they are all going to blight together.", ["vegetable", "root", "farming", "store"], 0, False),
    ("clover_seed", "Clover seed, the fine brown dust of it, and a field of clover from that.", ["seed", "fodder"], 4, True),
    ("vetch_seed", "Vetch seed, small and round, for a field that fixes the nitrogen.", ["seed", "legume", "fodder"], 6, True),
    ("broad_bean_seed", "Broad bean seed, the big flat ones, and they come up in three days.", ["seed", "legume"], 6, True),
    ("lupin_seed", "Lupin seed, the small mottled ones, and a poor man's green manure.", ["seed", "legume", "fodder"], 6, True),
    ("colza_seed", "Colza seed, the small black ones, and a field of it is a gold sight.", ["seed", "oil"], 8, True),
    ("rapeseed", "Rapeseed, a heap of it, and it is what the oil presses.", ["seed", "oil"], 8, True),
    ("flax_retting_pond", "A retting pond, and the water going the colour of weak tea over weeks.", ["plant", "fibre", "farming"], 0, False),
    ("hemp_field", "A field of hemp, tall as a man and moving in a wind you cannot feel at ground level.", ["plant", "fibre", "crop"], 0, False),
    ("wheat_sheaf", "A wheat sheaf, tied in a bundle with a straw band, to hang in a barn.", ["crop", "grain", "farming", "store"], 0, False),
    ("barley_grain_sack", "A sack of barley, the grain at the top of it like a floor.", ["grain", "food", "store"], 0, False),
    ("rye_straw_loaf", "A loaf of rye straw, and the smell of it in a stable is a smell of plenty.", ["grain", "fodder", "store"], 0, False),
    ("malt", "Malt, the sprouted barley dried on a kiln floor, and it is the start of the beer.", ["grain", "food", "brewing", "store"], 0, False),
    ("hops", "Hops, the green bines, and the smell of one in a hop yard is unmistakable.", ["plant", "brewing", "crop", "food"], 10, True),
    ("hop_bine", "A hop bine, the sticky green shoot, and it climbs anything put near it.", ["plant", "brewing", "crop"], 0, False),
    ("grapes_vine", "A grapevine, the old wood, and it bears where the frost does not sit.", ["plant", "fruit", "crop"], 0, False),
    ("vine_shoot_fruit", "A bunch of vine shoots, and they are edible when the spring is late.", ["forage", "vegetable", "food"], 10, True),
    ("apricot_tree", "An apricot tree, the grafted kind, and it fruits at seven years old.", ["plant", "fruit", "tree"], 0, False),
    ("cherry_tree", "A cherry tree in blossom, and there is nothing else in the world like the smell.", ["plant", "fruit", "tree"], 0, False),
    ("plum_tree", "A plum tree, the old kind, its bark dark and cracked all over.", ["plant", "fruit", "tree"], 0, False),
    ("pear_tree", "A pear tree, and it outlives the man who planted it and the man who grafted it.", ["plant", "fruit", "tree"], 0, False),
    ("fig_tree", "A fig tree, and it needs a wall and it will get into the wall given time.", ["plant", "fruit", "tree"], 0, False),
    ("walnut_tree", "A walnut tree, and a thousand of them and none of them young.", ["plant", "nut", "tree"], 0, False),
    ("hazel_hedge", "A hazel hedge, and a good one is a living fence that grows its own nuts.", ["plant", "nut", "fence"], 0, False),
    ("fruit_basket", "A basket of fruit, the picking brought in and set down where it will be seen.", ["container", "basket", "fruit"], 0, False),
]

# â”€â”€ kitchen and bakehouse â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
KITCHEN2 = [
    ("dough_bowl", "A dough bowl, wooden, and the bottom of it worked round from years of the same job.", ["container", "wooden", "kitchen"], 1.5, True),
    ("flour_sack", "A sack of flour, the top folded over and the tie a strip of cloth.", ["container", "textile", "kitchen", "store"], 0, False),
    ("meal_sack", "A sack of meal, coarser than flour, and darker.", ["container", "textile", "kitchen", "store"], 0, False),
    ("salt_pot", "A salt pot, and the pot is the reason the salt is dry.", ["container", "kitchen"], 0.6, True),
    ("grater", "A grater, sheet iron punched with holes, and it is a tool that outlives the maker.", ["kitchen", "tool", "metal"], 0.2, True),
    ("spice_grinder", "A spice grinder, a box with a handle and a crank for the lid.", ["kitchen", "tool", "metal", "spice"], 0.5, True),
    ("pepper_mill", "A pepper mill, of oak, with a small iron grinder inside.", ["kitchen", "tool", "wooden", "spice"], 0.3, True),
    ("dough_knife", "A dough knife, a scraper of iron for cutting dough off the bench.", ["kitchen", "tool", "metal"], 0.1, True),
    ("bread_board", "A bread board, scored with a hundred cuts, and it is the one thing every kitchen has.", ["kitchen", "wooden", "tool"], 1.5, True),
    ("proofing_basket", "A proofing basket, cane, and a loaf turned out of it has the pattern on its top.", ["kitchen", "fibre", "baking"], 0.8, True),
    ("dough_rope", "A rope of dough, proving under a cloth, and a child's job to keep it in shape.", ["food", "bread", "baking"], 20, True),
    ("rye_loaf_dark", "A dark rye loaf, so heavy it is eaten in slices with soup.", ["food", "bread", "baking"], 40, True),
    ("barley_loaf", "A barley loaf, heavy and dark, and it keeps a fortnight.", ["food", "bread", "baking"], 38, True),
    ("white_loaf", "A white loaf, still warm, and the crust crackles when you break it.", ["food", "bread", "baking"], 42, True),
    ("baker's_bread", "A baker's loaf, a big round one, and it costs a day's flour.", ["food", "bread", "baking"], 46, True),
    ("manchet_loaf", "A manchet, the fine white loaf, and it costs four times the flour it uses.", ["food", "bread", "baking", "rich"], 44, True),
    ("pretzel", "A pretzel, twisted and boiled then baked, and the crust chews.", ["food", "bread", "baking"], 30, True),
    ("biscuit_rolled", "A rolled biscuit, the dough thin as paper and cut with a wheel.", ["food", "pastry", "baking", "sweet"], 26, True),
    ("shortbread", "Shortbread, the crumbly Scottish kind, and it melts in the hand.", ["food", "pastry", "baking", "sweet"], 30, True),
    ("gingerbread", "Gingerbread, the dark treacle kind, and it keeps for a month.", ["food", "pastry", "baking", "sweet"], 32, True),
    ("sugar_loaf", "A sugar loaf, white, cone-topped, and the only way to keep sugar dry.", ["food", "sweet", "store", "kitchen"], 0, False),
    ("treacle_pot", "A pot of treacle, stopped with a cloth and a weight on top.", ["container", "kitchen", "sweet"], 0, False),
    ("honey_pot", "A pot of honey, and the lid is a disc of wood to keep the damp out.", ["container", "kitchen", "sweet"], 0, False),
    ("cheese_board", "A cheese board, and the knife beside it is not for cutting anything else.", ["kitchen", "wooden", "dairy", "tool"], 0, False),
    ("butter_dairy", "A dairy, the stone slab where the butter is worked, and it is cold even in July.", ["furniture", "kitchen", "stone", "dairy"], 200, True),
    ("cheese_hoop", "A cheese hoop, wooden, and the curds go in wet and come out as a wheel.", ["kitchen", "tool", "wooden", "dairy"], 2, True),
    ("cheese_rack", "A cheese rack, slatted, and the whole room smells of a dairy for a year.", ["furniture", "kitchen", "wooden", "dairy"], 8, True),
    ("milk_pail", "A milk pail, wooden, hooped, and the lid is a leather and a weight.", ["container", "wooden", "kitchen", "dairy"], 2, True),
    ("cream_jar_small", "A small cream jar, for the top of the milk before it is drawn off.", ["container", "clay", "kitchen", "dairy"], 1, True),
    ("cheddar_cheese", "A cheese, a whole wheel, waxed and scraped and the better for it.", ["food", "dairy"], 28, True),
    ("cheese_slices", "Sliced cheese, thin as paper, and a stagecoach traveller eats a shilling's worth standing up.", ["food", "dairy", "store"], 24, True),
    ("cottage_cheese", "Cottage cheese, drained in a cloth, and it goes on toast.", ["food", "dairy"], 22, True),
    ("ricotta", "Ricotta, drained overnight, and it is the softest thing in the dairy.", ["food", "dairy"], 22, True),
    ("butter_churn_small", "A small butter churn, for one household's worth of cream.", ["kitchen", "wooden", "tool", "dairy"], 3, True),
    ("kitchen_basket", "A kitchen basket, for the day's bread and eggs on the way home.", ["container", "fibre", "kitchen"], 1, True),
    ("egg_basket", "An egg basket, straw-lined, and the eggs come out clean.", ["container", "fodder", "kitchen"], 0.5, True),
    ("root_cellar_bin", "A bin of sand and dry ash, for storing roots over the winter.", ["container", "storage", "kitchen", "fodder"], 0, False),
    ("preserving_jar", "A preserving jar, and the rim is a ring of greased clay so the seal takes.", ["container", "clay", "kitchen", "preserve"], 0.8, True),
    ("preserve_jar_sealed", "A sealed jar, waxed lid, and it will be there in March.", ["container", "clay", "kitchen", "preserve"], 0, False),
    ("water_jug_sized", "A water jug, a big one, and it takes two to lift when it is full.", ["container", "clay", "kitchen", "water"], 4, True),
    ("hearth_bread_pot", "A bread pot, a covered crock, and the loaf inside stays warm for hours.", ["container", "clay", "kitchen", "baking"], 3, True),
    ("salt_crock", "A salt crock, a wooden tub with a lid and a hole, and the salt keeps dry over the sea air.", ["container", "wooden", "kitchen"], 4, True),
    ("larder_key", "A larder key, a long iron key on a loop of cord, and it hangs by the door.", ["key", "metal", "kitchen"], 0.1, True),
    ("larder", "A larder, a cool cupboard, and its shelves are slatted to let the air move.", ["furniture", "storage", "kitchen", "wooden"], 60, True),
    ("drying_rack", "A drying rack, and the herb bundles hang from it in a dark room.", ["furniture", "kitchen", "fibre", "wooden"], 6, True),
    ("stone_ground_flour", "Stone-ground flour, and the bran still in it is why it keeps.", ["food", "grain", "baking", "store"], 0, False),
    ("rye_meal", "Rye meal, darker than flour and heavier, and it makes a black bread.", ["food", "grain", "baking"], 26, True),
    ("oatmeal", "Oatmeal, coarse, and it thickens a pot of stew as well as a bowl of porridge.", ["food", "grain", "baking"], 24, True),
    ("barley_meal", "Barley meal, and a porridge made of it will thicken on its own.", ["food", "grain", "baking"], 24, True),
    ("bread_crumbs", "Bread crumbs, dried in a cloth, for binding a meatball.", ["food", "bread", "kitchen"], 14, True),
    ("fried_bread", "Fried bread, in fat, and it goes with a stew the way a spoon does not.", ["food", "bread", "kitchen", "fat"], 32, True),
    ("fried_onion", "Fried onion, and it is the top of everything.", ["food", "vegetable", "allium", "kitchen"], 16, True),
    ("fried_bacon_rind", "A piece of fried bacon rind, and the best part is the crisp edge.", ["food", "meat", "kitchen"], 20, True),
    ("scrambled_eggs", "Scrambled eggs, taken off the heat before they are done, and the pan sauce is the point.", ["food", "egg", "kitchen"], 28, True),
    ("soft_boiled_egg", "A soft-boiled egg, the white set and the yolk still moving when you break it.", ["food", "egg", "kitchen"], 18, True),
    ("poached_egg", "A poached egg, and getting it out of the water in one piece is a skill.", ["food", "egg", "kitchen"], 18, True),
    ("baked_egg_dish", "A baked egg dish, the whites set hard and the cream under them.", ["food", "egg", "kitchen"], 26, True),
    ("custard", "Custard, set and pale yellow, and it trembles when you carry it.", ["food", "sweet", "dairy", "kitchen"], 24, True),
    ("cream_sauce", "A cream sauce, and it is the only sauce a household can make without herbs.", ["food", "dairy", "kitchen", "sauce"], 22, True),
    ("cheese_sauce", "A cheese sauce, made of the end of a hard cheese and a little milk.", ["food", "dairy", "kitchen", "sauce"], 24, True),
    ("herb_sauce", "A green herb sauce, pounded in a mortar and stiff with bread.", ["food", "herb", "kitchen", "sauce"], 18, True),
    ("mustard_sauce", "A mustard sauce, sharp and made with hot water and a spoon of mustard.", ["food", "spice", "kitchen", "sauce"], 20, True),
    ("stock", "Stock, the pot kept going and topped up, and a house runs on it.", ["food", "kitchen", "liquid", "liquid"], 24, True),
    ("broth_jelly", "Broth, and a good one sets to a jelly in a cold bowl.", ["food", "kitchen", "liquid"], 24, True),
    ("stew_can", "A stew can, an earthenware pot with a lip, and it goes to the fire and comes back.", ["container", "clay", "kitchen", "liquid"], 1.5, True),
    ("tripod_chain", "A chain for the tripod, and it is the shortest thing in the kitchen.", ["tool", "kitchen", "metal"], 0.3, True),
    ("kitchen_footman", "A kitchen jack, a wrought bar to lift a hot pan off a fire.", ["tool", "kitchen", "metal"], 1.5, True),
    ("egg_beater", "An egg beater, twigs bound in a ring, and it makes more foam than a fork.", ["tool", "kitchen", "fibre", "fletching"], 0.1, True),
    ("whisk", "A whisk, twigs bound in a ring, for beating and for a pot of tea.", ["tool", "kitchen", "fibre", "fletching"], 0.1, True),
    ("butter_churn_dairy", "A butter churn, and the sound of one going is the sound of a household doing well.", ["tool", "kitchen", "wooden", "dairy"], 6, True),
    ("grain_hopper_dairy", "A hopper, feeding the mill stones, and it is a funnel you keep clear.", ["tool", "kitchen", "wooden"], 2, True),
    ("grain_scoop_wooden", "A wooden grain scoop, and it is cut from one piece so no seam to hold grain.", ["tool", "kitchen", "wooden"], 0.1, True),
    ("wooden_chopping_block", "A chopping block, end grain, and the knife goes blunt in it.", ["kitchen", "wooden", "tool"], 8, True),
    ("meat_saw", "A meat saw, and it is the difference between a butcher and a housewife.", ["tool", "kitchen", "metal"], 1.5, True),
    ("hang_meat_hook", "A hook in a beam, for a side of bacon, and it is a thing every farmhouse has.", ["tool", "metal", "kitchen", "hook"], 0.2, True),
    ("firedog", "A firedog, an iron bar, for pulling logs out of a fire without burning your hands.", ["tool", "kitchen", "metal", "fire"], 2, True),
    ("fire_hose_leather", "A leather fire hose, for throwing water on a fire that has got out of hand.", ["tool", "kitchen", "leather", "water"], 1, True),
    ("leather_water_bucket", "A leather bucket, oak-bound, and it survives being thrown on a fire.", ["container", "kitchen", "leather", "water"], 2, True),
    ("kitchen_scrub", "A kitchen scrub, hog bristles and a handle, and it is the one tool that never breaks.", ["tool", "kitchen", "fibre", "fletching"], 0.1, True),
]


def build():
    out = {}

    def emit(item_id, desc, tags, relief, edible):
        """Route a row by what it *claims* to be, and refuse a claim it cannot back.

        Two mistakes showed up in the first run of this batch, both of them the
        table's fault rather than the data's, and both silent in the output:

        - a `drink`-tagged row sitting in a table whose loop only ever emitted
          food, so it got an `on_eat` trigger and a linter error demanding
          `on_drink`;
        - a **store** row (malt, stone-ground flour, a sugar loaf) tagged `food`
          with a relief of `0`, which is not relief: `check_unauthored_consumables`
          wants a *negative* `adjust_vital` on the right drive, and a zero says
          "this changes nothing" while the tag says "you can eat this".

        So the tag decides the shape, a non-positive relief on a consumable is a
        hard error naming the item and the number, and a row that is not edible
        loses the claim instead of being written half-right.
        """
        tags = [t for t in tags]
        if not edible:
            out[item_id] = thing(item_id, desc,
                                 [t for t in tags if t not in ("food", "drink")]
                                 or ["material"], weight=0.4)
            return
        if "drink" in tags and "food" not in tags:
            if relief <= 0:
                raise ValueError("%s: a drink needs positive thirst relief, got %r"
                                 % (item_id, relief))
            out[item_id] = drink(item_id, desc, relief, tags, weight=0.4)
            return
        if relief <= 0:
            raise ValueError("%s: a food needs positive hunger relief, got %r"
                             % (item_id, relief))
        out[item_id] = food(item_id, desc, relief, tags, weight=0.3,
                            message="You eat it. Better than nothing and not much more.")

    for item_id, desc, hunger, tags in VEG2:
        emit(item_id, desc, tags, hunger, True)

    for row in HERB2:
        item_id, desc, tags = row[0], row[1], row[2]
        if len(row) > 3:
            emit(item_id, desc, tags, row[3], True)
        else:
            out[item_id] = thing(item_id, desc, tags, weight=0.05)

    for item_id, desc, tags, hunger, edible in FRUIT2:
        emit(item_id, desc, tags, hunger, edible)

    for item_id, desc, tags, hunger, edible in CROP2:
        emit(item_id, desc, tags, hunger, edible)

    for item_id, desc, tags, hunger, edible in KITCHEN2:
        emit(item_id, desc, tags, hunger, edible)
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
