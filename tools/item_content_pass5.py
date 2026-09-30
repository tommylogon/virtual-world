"""
Item content pass 5 — materials, and the medieval household and town.

Authored content. **The tables are the work**; the record shapes come from
`item_shapes.py`, so a fix to how a consumable is authored lands in one place and
a pass that makes a claim it cannot back is refused rather than written.

    run     python tools/item_content_pass5.py
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

PASS = "pass5"

# â”€â”€ GOAL 4: materials and trade goods â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
MATERIALS = [
    # metal, worked and raw
    ("copper_ingot", "An ingot of copper, the green sheen of it only on the fracture.", 4.0, ["material", "metal"]),
    ("bronze_ingot", "An ingot of bronze, and every tool in the world is a little bit of it.", 4.5, ["material", "metal", "trade"]),
    ("brass_ingot", "A brass ingot, and it is copper and tin and it is what a poor man's silver is made of.", 4.0, ["material", "metal", "trade"]),
    ("tin_ingot", "An ingot of tin, and it came from the far coast and it cost more than the thing it makes.", 4.0, ["material", "metal", "trade"]),
    ("lead_ingot", "A lead ingot, soft and heavy, and it is a plumber's material and a poison.", 6.0, ["material", "metal", "hazard"]),
    ("silver_ingot", "A silver ingot, and the only metal a man will kill a stranger for.", 5.0, ["material", "metal", "valuable"]),
    ("gold_ingot", "A gold ingot, and a village that has one is a village that can be left alone.", 5.0, ["material", "metal", "valuable"]),
    ("steel_scrap", "Scrap steel, and it is the roof of an old house and a nail at a time.", 3.0, ["material", "metal", "waste"]),
    ("iron_filing", "Iron filings, and they are the waste of a grindstone and they will not wash off a hand.", 0.05, ["material", "metal", "waste", "magnetic"]),
    ("rust_iron", "Rusted iron, and it is the fate of every bar left in the rain for a month.", 2.0, ["material", "metal", "rotten", "waste"]),
    ("slag", "Slag, the waste off a bloomery, and it is full of iron and gets tipped in a heap.", 5.0, ["material", "metal", "waste", "filth"]),
    # glass
    ("glass_vial", "A glass vial, and it is the most expensive thing a poor alchemist owns.", 0.1, ["container", "glass", "alchemical", "small", "valuable"]),
    ("glass_beaker", "A glass beaker, thin-walled, and it is hand-blown and never quite true.", 0.3, ["container", "glass", "alchemical", "valuable"]),
    ("glass_flask", "A round-bottomed flask, and the bubble is blown and the neck is worked by hand.", 0.4, ["container", "glass", "alchemical", "valuable"]),
    ("glass_blowpipe", "A blowpipe, iron, and the end is a blob of molten glass the size of a fist.", 2.0, ["tool", "glass", "fire", "metal"]),
    ("glass_rod", "A rod of glass, drawn out, and it is the first stage of every bead and bottle.", 0.5, ["material", "glass", "trade"]),
    ("cullet", "Cullet, broken glass, and it is melted again and it is the only thing a glazier has for nothing.", 1.0, ["material", "glass", "waste"]),
    ("window_glass_pane", "A pane of glass, and it is set in a lead came and it is the whole art of glazing.", 0.8, ["material", "glass", "building", "valuable"]),
    ("lead_came", "A lead came, an H-shaped strip, and glass is held in a lattice of it.", 0.2, ["material", "metal", "glass", "building", "small"]),
    ("frit_glass", "Frit, ground glass, and it is the opaque white and gold in a window.", 0.2, ["material", "glass", "dye", "trade"]),
    ("mirrored_silver", "Silvered glass, and a mirror is a tin of tinfoil and a great deal of luck.", 0.5, ["material", "glass", "metal", "valuable"]),
    # dye, pigment, mordant
    ("dye_vat_ash", "Woad ash, and the blue comes out of it only after a fermentation that stinks for a week.", 5.0, ["material", "dye", "plant", "alchemical"]),
    ("brazil_wood", "Brazil wood, a billet of it, and it dyes a red nobody else can match and it comes from a long way off.", 2.0, ["material", "dye", "wooden", "trade"]),
    ("kermes", "Kermes, the dried scale insects, and the most valuable dye there was before cochineal.", 0.1, ["material", "dye", "alchemical", "valuable", "small"]),
    ("cochineal", "Cochineal, and the dye is a beetle and it is a brighter red than anything else on earth.", 0.05, ["material", "dye", "alchemical", "valuable", "small"]),
    ("ochre_pigment", "Ochre, ground, and it is the earth itself and it is the oldest pigment there is.", 0.5, ["material", "dye", "stone", "pigment"]),
    ("verdigris", "Verdigris, the green crust on old copper, and it is poison and it is a beautiful green.", 0.1, ["material", "dye", "alchemical", "hazard", "valuable"]),
    ("vermilion", "Vermilion, and it is mercury boiled with sulphur and it is beautiful and it eats the maker.", 0.1, ["material", "dye", "alchemical", "hazard", "valuable"]),
    ("bone_black", "Bone black, and it is calcined bone and it is the blackest black there is.", 0.1, ["material", "dye", "bone", "pigment"]),
    ("lampblack", "Lampblack, the soot off an oil lamp, and it is a black you can grind into ink.", 0.1, ["material", "dye", "fibrous", "pigment"]),
    ("ultramarine", "Ultramarine, ground lapis, and it is worth more than the gold frame it is painted in.", 0.1, ["material", "dye", "stone", "valuable", "pigment"]),
    ("minium", "Minium, the red lead, and it is the common man's vermilion and it is still poison.", 0.2, ["material", "dye", "metal", "hazard", "pigment"]),
    # rope, cordage, nets
    ("rope_hemp", "A rope of hemp, three strands laid up, and it is the most useful thing in a barn.", 3.0, ["material", "fibre", "trade", "tool"]),
    ("cordage_bench", "A rope walk, and the ropes are made there by the hundred in one go.", 0.0, ["material", "fibre", "trade", "building", "large"]),
    ("twine", "Twine, a ball of it, and it is for tying a parcel and mending a fence.", 0.2, ["material", "fibre", "tool", "small"]),
    ("net_cordage", "Netting, a mesh of cord, and it is a sheet of it and it is for a fish or a bed.", 0.5, ["material", "fibre", "trade", "bedroom"]),
    ("marline", "Marline, a small stuff of tarred hemp, and it is what a sailor knots with.", 0.3, ["material", "fibre", "trade", "marine"]),
    ("tow_line", "A tow line, thick, and it is what a cart is pulled with and what a barge is moored by.", 6.0, ["material", "fibre", "trade", "vehicle", "heavy"]),
    ("rigging_rope", "A length of rigging, and a ship's whole tackle is a hundred of them.", 5.0, ["material", "fibre", "trade", "marine", "heavy"]),
    # soap, wax, pitch, tallow
    ("hard_soap", "A cake of hard soap, grey-white, and it lasts a month in a wet household.", 0.4, ["material", "cleaning", "personal", "alchemical"]),
    ("soft_soap", "Soft soap, a pot of it, and it is a potash and oil soup and it smells of the pot.", 0.6, ["material", "cleaning", "personal", "alchemical", "liquid"]),
    ("lye", "Lye, potash and water, and it is what eats a pair of hands and it is what soap is.", 0.8, ["material", "alchemical", "hazard", "cleaning", "liquid"]),
    ("wax_bees", "Beeswax, a cake of it, and it is the only wax that will burn clean and smell sweet.", 0.6, ["material", "wax", "farming", "honey"]),
    ("wax_seal_stick", "A stick of sealing wax, and it is the same wax and it is a different job entirely.", 0.05, ["material", "wax", "document", "writing", "small"]),
    ("pitch_block", "A block of pitch, and it is tar boiled until it is thick enough to stand up.", 3.0, ["material", "tar", "waste", "trade", "heavy"]),
    ("tar_bucket", "A bucket of tar, and the lid is nailed down and it is never quite shut.", 8.0, ["container", "metal", "tar", "trade", "heavy", "liquid"]),
    ("pitch_sprinkler", "A tar pot, and it is set alight and walked round the hull and it is the one piece of theatre a yard gets.", 12.0, ["container", "metal", "tar", "trade", "fire", "heavy"]),
    # timber, by species
    ("oak_board", "A board of oak, and it is the timber for a door, a beam or a bucket.", 12.0, ["material", "wooden", "trade", "building"]),
    ("ash_board", "A board of ash, and it is the timber for a wheel and a shaft and a plough stile.", 9.0, ["material", "wooden", "trade", "building", "farming"]),
    ("elm_board", "A board of elm, and it is the timber for a cart bed and a water trough.", 10.0, ["material", "wooden", "trade", "building", "vehicle"]),
    ("yew_longbow_stave", "A stave of yew, and it is the best bow timber and there is not much of it.", 3.0, ["material", "wooden", "trade", "weapon", "hunting"]),
    ("alder_board", "A board of alder, and it is cheap and it takes water, so it is a trough and a well lid.", 6.0, ["material", "wooden", "trade", "water", "building"]),
    ("birch_board", "A board of birch, and it is a peel of bark and a fine cheese box and a bed of splints.", 6.0, ["material", "wooden", "trade", "building"]),
    ("beech_board", "A board of beech, and it is a tool handle and a bread board and a plate.", 9.0, ["material", "wooden", "trade", "tool", "kitchen"]),
    ("hazel_stick", "A hazel stick, straight and springy, and it is a rod and a handle and a beanpole.", 0.6, ["material", "wooden", "farming", "tool"]),
    ("withy", "Withy, a wand of hazel, and it is a withe for tying a bundle and a rod for a basket.", 0.3, ["material", "fibre", "farming", "tool"]),
    ("osier_bundle", "Withies, a bundle of them, and they are soaked before they will bend.", 2.0, ["material", "fibre", "farming", "trade"]),
    ("charcoal_draw", "A charcoal burner, and the turf stack smokes for a week and nobody can live there.", 0.0, ["material", "fuel", "building", "smoke", "large"]),
    ("shavings_bundle", "Shavings, a double handful, and the first thing into a kitchen fire.", 0.2, ["material", "fuel", "wooden", "fire"]),
    # paper, parchment, boards
    ("parchment_scraps", "Parchment scraps, and a scribe's offcuts are a firelighter and a child a book.", 0.2, ["material", "paper", "writing", "waste"]),
    ("paper_ream", "A ream of paper, and a ream is twenty quires and a quire is twenty-four sheets.", 1.0, ["material", "paper", "writing", "trade", "book"]),
    ("paper_wheel", "A wheel of paper, and it is what an illuminator starts with.", 0.5, ["material", "paper", "writing", "trade", "book"]),
    ("vellum", "Vellum, a skin dressed for writing, and it is calf and it is smoother than paper.", 0.2, ["material", "paper", "writing", "leather", "book"]),
    ("wooden_board_book", "A writing board, waxed, and it is wiped and written on again a hundred times.", 0.4, ["material", "paper", "writing", "trade", "book"]),
    ("scribal_knife", "A scribal penknife, and it cuts a quill and a bookbinder cuts a leather strap with it.", 0.1, ["tool", "writing", "metal", "small"]),
    # rope, glass and metal finished goods
    ("iron_strap", "A strap of iron, and it is a hoop and a hinge and a buckle and a repair.", 0.6, ["material", "metal", "trade", "building"]),
    ("hinge_iron", "A hinge, wrought, and it is pinned and it is made to be oiled every year.", 0.2, ["material", "metal", "building", "trade"]),
    ("lock_iron", "A lock, and it is the most expensive thing on a house and the least replaceable.", 0.5, ["material", "metal", "key", "trade", "valuable"]),
    ("clasp_bronze", "A bronze clasp, and the fitting on a belt or a book or a chest lid.", 0.2, ["material", "metal", "trade", "accessory", "small"]),
    ("rivet_iron", "A rivet, and it is headed and set hot and it holds a boat together.", 0.02, ["material", "metal", "trade", "small", "building", "boat"]),
    ("chain_link", "A link of chain, and a chain is a hundred of them and a bad link spoils the lot.", 0.2, ["material", "metal", "trade", "tool"]),
    ("bell_metal", "A bell, cast bronze, and the metal is a third copper for the ring.", 80.0, ["material", "metal", "sound_source", "trade", "heavy", "large"]),
    ("wire_draw", "A spool of drawn wire, and wire drawing is a trade and a hole and a team of horses.", 0.5, ["material", "metal", "trade", "small"]),
]

# â”€â”€ GOAL 5: medieval household and town, in layers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
HOUSE = [
    # --- clothing by class
    ("peasant_smock", "A linen smock, belted with a rope, and it is dyed madder and it is the whole of a dress.", 0.6, ["clothing", "top", "linen", "dress", "torso"]),
    ("peasant_tunic", "A woollen tunic, undyed, and the shoulders are worn shiny and the elbows are mended.", 0.9, ["clothing", "top", "wool", "torso", "dress"]),
    ("wool_hose", "Hose, full leggings of thick wool, and they are the warmest thing a poor man owns.", 0.5, ["clothing", "bottom", "wool", "legs", "winter", "insulation"]),
    ("coif_linen", "A coif, a close linen cap, and it keeps the sun off a field and the cold off a head.", 0.1, ["clothing", "head", "linen", "private"]),
    ("wimple", "A wimple, cloth over the chin and neck, and it is modesty as much as warmth.", 0.2, ["clothing", "head", "linen", "private", "dress"]),
    ("kirtle", "A kirtle, a full skirt and bodice in one, and it is what a woman of the manor wears all day.", 1.2, ["clothing", "bottom", "wool", "dress", "skirt"]),
    ("surcoat", "A surcoat, a sleeveless overgown open at the sides, and it shows the kirtle underneath.", 1.0, ["clothing", "top", "wool", "dress", "torso"]),
    ("dalmatica", "A dalmatica, a wide-sleeved tunic, and it is a vestment and it is very heavy.", 1.5, ["clothing", "top", "religious", "torso", "dress", "large"]),
    ("cassock", "A cassock, black wool, and a man wears it who takes orders and eats off the same plate.", 1.0, ["clothing", "top", "religious", "wool", "torso", "dress"]),
    ("habit_frock", "A habit, undyed wool over a leather belt, and the rope is knotted at the side.", 1.2, ["clothing", "top", "religious", "wool", "torso", "dress", "insulation"]),
    ("noble_robe", "A noble's robe, cloth of a colour that had to be made with woad and alum and money.", 3.0, ["clothing", "top", "dress", "wool", "large", "torso", "rich"]),
    ("fur_trimmed_gown", "A gown trimmed with sable, and the fur is the most expensive thing on it.", 4.0, ["clothing", "top", "dress", "fur", "large", "torso", "rich", "insulation"]),
    ("merchant_doublet", "A doublet, quilted, and a man of the town wears one and thinks himself somebody.", 1.5, ["clothing", "top", "doublet", "torso", "dress", "layered"]),
    ("hose_wool", "Hose, a pair of hose, and they are cut in one with the breeches and laced at the leg.", 0.6, ["clothing", "bottom", "legs", "wool", "layered"]),
    ("jerkin_leather", "A jerkin, a leather jerkin, sleeveless, worn over a doublet and rained on as a shield.", 1.0, ["clothing", "top", "leather", "torso", "layered"]),
    ("gown_cloth", "A gown of cloth, sleeveless over a kirtle, and it is tied with a sash at the waist.", 2.0, ["clothing", "top", "dress", "torso", "layered", "rich"]),
    ("hose_canions", "Canions, tight linen leggings worn under the hose, and they are a shoemaker's product.", 0.3, ["clothing", "bottom", "legs", "linen", "layered", "small"]),
    ("stomacher", "A stomacher, a stiffened panel over the chest, and it is padded to make a flat front.", 0.5, ["clothing", "top", "torso", "dress", "accessory"]),
    ("partlet", "A partlet, a padded shoulder piece, and it is a bad fashion and a cold one.", 0.4, ["clothing", "top", "torso", "dress", "insulation", "accessory"]),
    ("tippet", "A tippet, a long narrow scarf of fur or cloth, and it is over the arms and over nothing else.", 0.6, ["clothing", "top", "insulation", "accessory", "dress"]),
    ("sleeve_under", "An undersleeve, linen, and the showy sleeve is over it and the hand stays cool.", 0.2, ["clothing", "arms", "linen", "under", "layered"]),
    ("hose_leg_shoe", "A patten, a wooden overshoe, and it lifts a hem out of the mud on a walk.", 0.5, ["clothing", "footwear", "wooden", "feet", "water"]),
    ("straw_sandals", "Sandals of straw, and they are worn until the foot's shape is in the straw.", 0.2, ["clothing", "footwear", "fodder", "feet", "summer"]),
    ("worsted_stockings", "Stockings, worsted, and they are a knitted afterthought and they cost a day's wage.", 0.2, ["clothing", "bottom", "legs", "wool", "knit", "winter"]),
    ("kneed_breeches", "Breeches, close to the knee, and they are the newest thing in a town.", 0.6, ["clothing", "bottom", "legs", "doublet", "layered", "dress"]),
    ("leather_jacket", "A jerkin of leather, soft and dark, and it is a soldier's coat and a tradesman's.", 1.2, ["clothing", "top", "leather", "torso", "insulation"]),
    ("quilted_gambeson", "A gambeson, quilted linen, and it stops an arrow that has lost its head.", 3.0, ["clothing", "top", "insulation", "military", "large", "torso", "layered"]),
    ("padded_cap", "A cap, wool-lined, and it is the difference between a cold ear and a lost one.", 0.2, ["clothing", "head", "wool", "winter", "insulation"]),
    ("friar_hood", "A hood, a great one, and it is a cowl and it covers the head and the shoulders together.", 0.5, ["clothing", "head", "wool", "religious", "insulation", "hooded"]),
    ("travel_cloak", "A travelling cloak, waxed wool, and it is the same cloak in every weather.", 1.5, ["clothing", "top", "wool", "insulation", "travel", "hooded", "large", "layered"]),
    ("hunting_horn_horn", "A hunting horn, a cow's, and it is a bugle with a leather strap and a lord on it.", 0.8, ["accessory", "sound_source", "fletching", "hunting", "small", "horn"]),
    # --- textiles and soft furnishings
    ("wool_floor_cover", "A floor cover, a big woollen carpet, and it is the most valuable thing in a house.", 8.0, ["furniture", "textile", "wool", "floor", "large", "insulation"]),
    ("table_runner", "A runner on the table, and it is the difference between a bare board and a laid one.", 1.0, ["furniture", "textile", "table", "cloth", "dining"]),
    ("bed_curtain_rod", "A rod, iron, and a curtain on it, and the curtain is what makes a bed a room.", 1.2, ["furniture", "metal", "bedroom", "bed", "small"]),
    ("blanket_striped", "A striped blanket, and the stripes are woven in, not printed.", 3.0, ["furniture", "textile", "bedroom", "insulation", "wool", "heavy"]),
    ("linen_sheet", "A sheet, of linen, and it is the whitest thing in a house with money in it.", 0.8, ["furniture", "textile", "bedroom", "linen", "cloth", "bed"]),
    ("pillowcase", "A pillowcase, and the stitching is the part a bride is judged on.", 0.2, ["furniture", "textile", "bedroom", "linen", "small", "cloth"]),
    ("sacking_coarse", "Sacking, coarse cloth, and everything is carried in it and it lasts forever.", 1.5, ["material", "textile", "trade", "container"]),
    ("webbing_tape", "Webbing, a strong tape, and it is what a strap is sewn from and it will not cut.", 0.2, ["material", "textile", "fibre", "trade", "small"]),
    ("felt_pad", "A felt pad, and it goes under a pot or a bed or a lamp and it saves the wood.", 0.1, ["material", "textile", "furniture", "small", "insulation"]),
    ("wool_felt", "A sheet of felt, and it is what a hat is blocked on and it is also a roof in Wales.", 0.6, ["material", "textile", "wool", "trade", "insulation"]),
    ("hemp_sheet", "A sheet of hemp, and it is a sail and a tent and a grain sack and it lasts forever.", 2.0, ["material", "textile", "fibre", "trade", "large", "insulation"]),
    # --- kitchen and household
    ("wood_salt_cellar", "A salt pot, and the brine in it is the one thing nobody sells you.", 0.6, ["container", "kitchen", "salt"]),
    ("iron_trivet", "A trivet, three feet of iron, and it stands a pot in the fire so the pot does not have to.", 1.2, ["kitchen", "tool", "metal", "fire"]),
    ("grate_bars", "A grate, iron bars, and it lets the air through a fire and the heat into a room.", 3.0, ["kitchen", "fire", "metal", "building"]),
    ("hearth_dogs", "Andirons, a pair of them, and the fire is built between them and not against them.", 6.0, ["furniture", "fire", "metal", "kitchen", "heavy"]),
    ("bellows_smalldomestic", "A pair of small bellows, and they are a chair by the fire in every hall.", 3.0, ["tool", "fire", "leather", "kitchen"]),
    ("hearth_hooker", "A fire hook, long, and its only job is to be in the fire so a hand is not.", 1.0, ["tool", "fire", "metal", "kitchen", "heavy"]),
    ("sconce", "A sconce, an iron bracket for a candle, and it is one per room and it is a job for a smith.", 0.8, ["light_source", "candle", "metal", "hallway", "wall", "fixture"]),
    ("wall_bracket_candle", "A candle bracket, and the socket is a spike because a candle must not fall.", 0.4, ["light_source", "candle", "metal", "hallway", "wall", "fixture", "small"]),
    ("pricket_candlestick", "A pricket, a spike standing in a dish, and it is for a wood splinter and a rush.", 0.1, ["light_source", "candle", "metal", "furniture", "small", "fuel"]),
    ("candle_stub", "A candle stub, and a household keeps a jar of them for exactly one thing.", 0.02, ["light_source", "candle", "small", "fuel"]),
    ("lamp_chimney", "A lamp chimney, horn, and it is the difference between smoke and a light.", 0.3, ["light_source", "glass", "small", "liquid"]),
    ("wick_trim_scissors", "A pair of scissors, and they are for trimming a wick and they cost more than a hen.", 0.1, ["tool", "metal", "kitchen", "small", "household"]),
    ("wick_wick", "A wick, and it is hemp and it is the last thing to burn out of a candle.", 0.01, ["light_source", "candle", "fibre", "small", "fuel"]),
    ("tinder_stuff", "Tinder, charred linen and dry moss, and without it a fire is a lot of smoke.", 0.05, ["tool", "fire", "fibre", "small", "fuel"]),
    ("fire_ember", "Embers, a scoop of them, and a bowl of live coals is a gift and a fire to come back to.", 0.5, ["material", "fire", "fuel", "kitchen"]),
    ("hearth_rake", "A hearth rake, long-handled, and it pulls the fire out flat to rake the ashes.", 1.0, ["tool", "fire", "metal", "kitchen", "heavy"]),
    ("ash_scoop", "An ash scoop, a shovel for the bottom of a fire, and it goes under the grate.", 0.6, ["tool", "fire", "metal", "kitchen", "waste"]),
    ("kindling_cup", "A kindling bundle, and it is dry wood and a rush and a kitchen fire in one.", 0.3, ["material", "fire", "fuel", "kitchen", "fibre"]),
    ("fire_wood_basket", "A fireside basket, and it holds the night's wood and it is the furniture by the fire.", 4.0, ["container", "furniture", "wooden", "fireplace", "hallway", "heavy"]),
    ("bellows_bellows", "A pair of bellows, and the leather is nailed to the boards and it leaks until it is dressed.", 3.0, ["tool", "fire", "leather", "kitchen", "heavy"]),
    ("warming_pan", "A warming pan, a long handle and a footed pan, and it is put in a bed before the person is.", 2.0, ["kitchen", "tool", "metal", "bedroom", "fire", "insulation"]),
    ("chafing_pan", "A chafing pan, and it stands over coals at a table and keeps a dish hot in front of a lord.", 3.0, ["kitchen", "tool", "metal", "dining", "fire", "large"]),
    ("candle_box", "A candle box, a wooden one, and it is a soldier's and it lives in a hauberk.", 0.4, ["container", "wooden", "light_source", "candle", "small", "military"]),
    ("clay_lamp", "A clay lamp, and the wick sits in a spout and the whole thing is baked in a hearth.", 0.4, ["light_source", "clay", "liquid", "small", "kitchen"]),
    ("wood_spoon_large", "A big wooden spoon, and it is a thing you stir with and a thing you eat with.", 0.1, ["kitchen", "wooden", "tool", "small"]),
    ("table_dressing", "A laid table, cloth and boards and a knife for every person, and it is done for a feast.", 0.0, ["furniture", "table", "dining", "display", "large"]),
    ("knife_horn_handle", "A knife with a horn handle, and the horn is boiled and pressed and it is the mark of a good one.", 0.2, ["kitchen", "tool", "metal", "wooden", "dining"]),
    ("plate_wooden_coarse", "A wooden plate, and it is a disc on a stem and it is what a peasant eats off.", 0.2, ["container", "wooden", "kitchen", "dining", "tableware"]),
    ("cup_wood", "A wooden cup, pegged, and it leaks and it is the cup in every farmhouse.", 0.2, ["container", "wooden", "kitchen", "dining", "tableware"]),
    ("plate_pewter", "A pewter plate, and it is dented from a century of knives and elbows.", 0.4, ["container", "metal", "kitchen", "dining", "tableware"]),
    ("knife_trenchers", "A trencher, a wooden disc, and it is a plate that is eaten off and then burned.", 0.05, ["container", "wooden", "kitchen", "dining", "waste", "small"]),
    ("napkin_silk", "A napkin of silk, and it is in a rich man's house and it is never used.", 0.1, ["furniture", "textile", "silk", "table", "dining", "cloth", "rich"]),
    ("ewer_wine", "A silver ewer, and the wine in it is the second reason for a feast.", 1.0, ["container", "metal", "table", "dining", "rich", "valuable"]),
    ("beaker_horn", "A beaker of horn, and it is a drinking vessel of a kind that is nearly unbreakable.", 0.2, ["container", "fletching", "table", "dining", "tableware"]),
    ("basket_food", "A food basket, and it goes to the fields with the bread and the cheese and the ale.", 0.8, ["container", "fibre", "kitchen", "farming"]),
    ("mug_earthenware", "An earthenware mug, and it is a man's own and it lives by the fire.", 0.4, ["container", "clay", "kitchen", "dining", "tableware"]),
    ("chair_settle", "A settle, a bench with a high back and a chest under it, and it is a seat and storage.", 60.0, ["furniture", "wooden", "hallway", "hearth", "large", "heavy"]),
    ("foot_stool_pair", "A pair of footstools, and a gentleman's feet do not reach the floor at a long table.", 2.0, ["furniture", "wooden", "hallway", "dining", "small"]),
    ("hearth_chair", "A chair by the fire, an armchair, and the arms are where a person's hands live in winter.", 12.0, ["furniture", "wooden", "hearth", "hallway", "insulation", "heavy"]),
    ("cradle", "A cradle, a hooded one on rockers, and the hood is the whole of the design.", 8.0, ["furniture", "bedroom", "wooden", "baby", "large", "heavy"]),
    ("child_stool", "A child chair, at the table on a high seat, and it rocks on the two front feet.", 2.0, ["furniture", "bedroom", "wooden", "child", "small"]),
    ("clothes_chest", "A press, a cupboard for clothes, and it is carved and it is the biggest thing in a bedroom.", 40.0, ["furniture", "storage", "bedroom", "wooden", "large", "heavy"]),
    ("bed_bed", "A bed, a great one with a feather mattress and a canopy, and it is furniture for showing off.", 150.0, ["furniture", "bedroom", "wooden", "bed", "large", "heavy", "insulation", "rich"]),
    ("bed_boarding", "Boards, a board bed, and it is a plank on trestles and a straw tick on top.", 40.0, ["furniture", "bedroom", "wooden", "bed", "heavy"]),
    ("mat_woven", "A woven mat, of reeds, and it is a floor and a bed and a place to sit.", 2.5, ["furniture", "textile", "fibre", "floor", "small", "insulation"]),
    ("broom_handle_reed", "A broom handle, a cut hazel, and a broom is a broom only if the handle is right.", 0.8, ["furniture", "wooden", "kitchen", "tool", "small"]),
    ("mop_head", "A mop head, rags wound on a string, and it is the least dignified tool in a house.", 0.3, ["tool", "textile", "kitchen", "small", "household"]),
    ("pail_water_lidded", "A lidded pail, and the lid is what keeps the well water from being the soup it starts as.", 2.0, ["container", "wooden", "water", "kitchen", "household"]),
    ("hanging_shelf", "A hanging shelf, and it is a board on two brackets and it is where a pot of nothing goes.", 1.0, ["furniture", "wooden", "kitchen", "storage", "wall"]),
    ("pestle_wood", "A wooden pestle, and it is for a pot as much as a mortar and it never chips the glaze.", 0.4, ["kitchen", "tool", "wooden", "small"]),
    ("candle_holder_iron", "An iron candle holder, and it is a spike and a foot and it does not tip.", 0.5, ["light_source", "candle", "metal", "furniture", "small"]),
    ("broom_house", "A besom, a birch broom, and it is a bundle of twigs on a stick and it lasts a decade.", 1.0, ["tool", "fibre", "kitchen", "household", "farming"]),
    ("linen_press", "A linen press, and it is a heavy screw and it is how a household owns one good tablecloth.", 40.0, ["furniture", "textile", "bedroom", "kitchen", "wooden", "machine", "heavy", "large"]),
    ("distaff_standing", "A standing distaff, fixed in a post, and it frees a spinner's hands to do something else.", 4.0, ["tool", "textile", "fibre", "wooden", "craft", "heavy"]),
    ("candlestick_pair", "A pair of candlesticks, prickets of iron, and they are the oldest furniture in a room.", 0.8, ["light_source", "candle", "metal", "furniture", "tableware"]),
    ("wick_scissors_swan", "Wick scissors, and the curved ones are for a wick in a castlestick.", 0.1, ["tool", "metal", "kitchen", "small", "household"]),
    ("wick_trimmer_hook", "A wick trimmer, a hook on a long handle, and it pulls a burnt wick out without touching the hot wax.", 0.1, ["tool", "metal", "kitchen", "small", "light_source"]),
    ("plate_earthen", "An earthenware plate, glazed brown, and it is chipped at the rim and it is a Tuesday plate.", 0.4, ["container", "clay", "kitchen", "dining", "tableware"]),
    ("salt_mill", "A salt mill, and it is two stones and a hopper and the cost of it is a corner of the street.", 30.0, ["kitchen", "tool", "stone", "kitchen", "machine", "heavy"]),
    ("quern_hand", "A quern, a small hand-mill for a kitchen, and it grinds what the big mill will not.", 12.0, ["kitchen", "tool", "stone", "machine", "heavy"]),
    ("water_wheel_kitchen", "A small water wheel, and it drives a mill or a bellows or a grindstone, depending.", 60.0, ["kitchen", "tool", "wooden", "machine", "water", "heavy", "large"]),
    ("stone_sink", "A stone sink, a slab with a drain, and it is where the washing water goes.", 40.0, ["furniture", "kitchen", "stone", "large", "heavy", "water"]),
    ("wooden_pail_brew", "A brewing pail, big, and it holds the wort in the first stage of beer.", 30.0, ["container", "wooden", "kitchen", "liquid", "large", "heavy", "brew"]),
    ("churn_stand", "A butter churn, on a stand, and the stand is what lets a churn be turned without lifting it.", 8.0, ["kitchen", "wooden", "dairy", "heavy", "container"]),
    ("cheese_vat_wood", "A cheese vat, and the milk is curds in a cloth over a month and then it is a wheel.", 40.0, ["kitchen", "wooden", "dairy", "container", "large", "heavy"]),
    ("hearth_cradle_small", "A small fire pan, a warming pan, and it is carried up to a sick child and back.", 2.0, ["kitchen", "tool", "metal", "bedroom", "fire", "small"]),
    ("ladder_wood", "A ladder, of oak, and it is rungs in two rails and the rails are joined by a mortise.", 15.0, ["furniture", "wooden", "building", "tool", "large", "heavy"]),
    ("step_ladder", "A step ladder, four steps, and it is a thing you stand on to reach a high shelf.", 6.0, ["furniture", "wooden", "kitchen", "tool", "small", "household"]),
    ("beam_bread", "A bread beam, a long knife, and it is the only thing that cuts a crust without crushing it.", 0.6, ["kitchen", "tool", "wooden", "dining", "small"]),
    ("dish_cloth", "A dish cloth, and it is a square of linen that has been a cloth for four years.", 0.05, ["kitchen", "textile", "linen", "cloth", "small", "household"]),
    ("escutcheon", "An escutcheon, a brass plate for a keyhole, and it stops the key working on the door.", 0.1, ["furniture", "metal", "door", "hallway", "wall", "small", "fixture"]),
    ("door_iron_hinge", "A door, and it is oak boards and strap hinges and it is a door for four hundred years.", 30.0, ["furniture", "wooden", "door", "hallway", "large", "heavy"]),
    ("window_shutter", "A shutter, and it closes over a window in a storm and the wind stops making a liar of it.", 6.0, ["furniture", "wooden", "window", "hallway", "large", "fixture"]),
    ("window_leadlight", "A leaded light, and it is glass in a lattice and it lets in a fifth of the light.", 10.0, ["furniture", "glass", "window", "hallway", "large", "building"]),
    ("door_lintel", "A lintel, a beam over a door, and it is the piece that stops a wall coming down on a man's head.", 12.0, ["furniture", "wooden", "door", "building", "large", "heavy"]),
    ("threshold_stone", "A threshold stone, worn hollow by a century of feet crossing it.", 8.0, ["furniture", "stone", "door", "hallway", "floor", "heavy"]),
    ("hanging_herb", "A hanging bunch of herbs, upside down from a roof beam, and the kitchen smells of it.", 0.3, ["material", "herb", "kitchen", "hanging", "strewing", "fibre", "medicinal"]),
    ("herb_bunch_dried", "A dried herb bunch, and it is a bundle on a string and it is a date in a kitchen.", 0.2, ["material", "herb", "kitchen", "hanging", "fibre", "medicinal"]),
]

# --- town
TOWN = [
    ("town_cross", "A market cross, and the steps are worn and it is where the market is held.", 150.0, ["town", "stone", "furniture", "display", "large", "heavy", "market"]),
    ("market_cross_step", "A step on the cross, worn into a hollow by three hundred years of standing.", 20.0, ["town", "stone", "furniture", "market", "wear", "small"]),
    ("pillory_post", "A pillory, and the holes are waist-high and the wood is worn smooth by necks.", 20.0, ["town", "wooden", "furniture", "punishment", "legal", "large"]),
    ("stocks_foot", "The stocks, and the leg irons are worn and it is a punishment that is mostly a humiliation.", 12.0, ["town", "metal", "furniture", "punishment", "legal", "small"]),
    ("gaol_door", "A gaol door, barred, and the bar is on the outside and that is the whole of the argument.", 40.0, ["town", "wooden", "door", "legal", "large", "building", "punishment"]),
    ("guild_hall", "A guildhall, and the door is wider than a man and the hall is full of a thing the town is proud of.", 400.0, ["town", "building", "stone", "large", "heavy", "trade", "civic"]),
    ("market_hall", "A market hall, open-sided, and the stalls are under it and the rain does not reach the meat.", 300.0, ["town", "building", "stone", "market", "large", "heavy", "trade"]),
    ("carnary", "A carvery, an open shed, and it is where a joint is bought and it is not hung there.", 120.0, ["town", "building", "wooden", "trade", "large", "heavy", "kitchen"]),
    ("granary_town", "A granary, a store of grain, and it is raised off the ground so the rats cannot get at it.", 200.0, ["town", "building", "stone", "storage", "grain", "large", "heavy"]),
    ("wardrobe_town", "A wardrobe, a box on legs, and it is a town's armoury in a wooden chest.", 90.0, ["town", "building", "wooden", "military", "storage", "large", "heavy"]),
    ("conduit_town", "A conduit, a stone spout, and it is the only clean water in a town with a well.", 80.0, ["town", "stone", "water", "furniture", "water", "civic"]),
    ("town_pump_iron", "A pump, a village pump, and the handle is worn and the stone around it is wet.", 25.0, ["town", "metal", "water", "furniture", "civic", "heavy"]),
    ("town_ducking_stool", "A ducking stool, a ducking stool, and it is a cucking stool for a scold and nobody remembers why.", 8.0, ["town", "wooden", "furniture", "punishment", "legal", "small"]),
    ("cucking_stool", "A ducking stool, and a scold is put on it and the town comes out to look at the cuckoo.", 8.0, ["town", "wooden", "furniture", "punishment", "legal", "small", "civic"]),
    ("stocks_bread_water", "A bread and water diet, and it is what a serf gets and what a town gives for a week.", 0.0, ["document", "punishment", "legal", "civic", "paper", "small"]),
    ("gaol_rope", "A gaol rope, a knotted rope hanging from a beam, and a prisoner can climb it out and is right to.", 3.0, ["town", "fibre", "punishment", "legal", "small", "building"]),
    ("manor_door", "A door, oak and iron, and the studs are in a diamond and the door is four inches thick.", 20.0, ["furniture", "wooden", "door", "large", "heavy", "manor", "hallway"]),
    ("manor_window_lead", "A window, leaded, and the glass is green and wavy and it is the best glass in the county.", 15.0, ["furniture", "glass", "window", "large", "manor", "hallway", "rich"]),
    ("manor_garden_herbary", "A herbary, a walled kitchen garden, and it is for the things a house needs not the things it eats.", 100.0, ["furniture", "plant", "garden", "large", "building", "herb"]),
    ("manor_orchard_tree", "A fruit tree, in an orchard, and the grass under it is the best on the estate.", 60.0, ["furniture", "plant", "tree", "garden", "large", "fruit", "outdoor"]),
    ("manor_pond_weed", "A pond, a weedy one, and a heron stands in it and regards you.", 200.0, ["furniture", "water", "garden", "large", "natural"]),
    ("manor_fish_pond", "A fish pond, and the water is still and the fish are in it and the heron knows.", 300.0, ["furniture", "water", "garden", "large", "fish", "natural"]),
    ("manor_dovecote", "A dovecote, a tower of nesting boxes, and it is the fastest way to move a letter anywhere.", 120.0, ["building", "stone", "farming", "large", "small", "trade", "pigeon"]),
    ("manor_kitchen_bench", "A kitchen bench, long, and the family ate off it and the servants sat on it.", 12.0, ["furniture", "wooden", "kitchen", "long", "dining", "heavy"]),
    ("manor_screens", "A screen, wooden, and it keeps the draught out of a room and the kitchen's noise out of the hall.", 10.0, ["furniture", "wooden", "hallway", "kitchen", "insulation", "large"]),
    ("manor_wall_garden", "A wall, a garden wall, and it is warm on the south side and everything grows in the cracks.", 40.0, ["furniture", "stone", "garden", "wall", "large", "outdoor", "outdoorwall"]),
    ("manor_gate_iron", "A gate, iron, and it is a vehicle gate and a postern gate and they do not open the same week.", 25.0, ["furniture", "metal", "door", "large", "manor", "heavy", "wall"]),
    ("manor_ledger_book", "A ledger, a great book, and it records every sack of grain and every head of sheep.", 3.0, ["document", "paper", "book", "writing", "manor", "civic", "records"]),
    ("manor_charter_box", "A charter box, and a charter is a document with a seal and it is worth a war.", 2.0, ["container", "wooden", "document", "manor", "writing", "valuable", "records"]),
    ("manor_signet_ring", "A signet ring, and the seal on it opens a letter that the law has to answer.", 0.05, ["clothing", "accessory", "metal", "valuable", "document", "hands", "manor", "noble"]),
    ("manor_key_ring", "A ring of keys, and the biggest one opens the undercroft and nobody else is given it.", 0.2, ["key", "metal", "manor", "accessory", "small", "container"]),
    ("manor_larder_key", "A larder key, and it hangs on a nail by the kitchen door and everybody knows.", 0.05, ["key", "metal", "kitchen", "manor", "small"]),
    ("manor_servant_bell", "A bell, a hand bell, and it is rung in the hall to call a servant and the whole house jumps.", 0.8, ["tool", "metal", "sound_source", "manor", "small", "hallway"]),
    ("manor_window_curtain", "A curtain, heavy wool, and it is drawn at a funeral and open otherwise.", 3.0, ["furniture", "textile", "window", "manor", "hallway", "large", "insulation"]),
    ("manor_table_cloth", "A table cloth, and it is the finest thing in the house and it is never sat on.", 4.0, ["furniture", "textile", "table", "manor", "dining", "rich", "large"]),
    ("manor_candle_stick_silver", "A candlestick, silver, and the pair of them is a dowry and not a gift.", 1.0, ["light_source", "candle", "metal", "manor", "dining", "valuable", "rich"]),
    ("manor_goblet_gold", "A gold cup, and it is the kind of object that starts a war over a will.", 0.4, ["container", "metal", "manor", "table", "valuable", "rich", "dining"]),
    ("manor_salt_cellar_gold", "A gold salt cellar, and the salt went in it and the salt came out and it went back.", 0.3, ["container", "metal", "kitchen", "manor", "valuable", "rich", "dining"]),
    ("manor_hunting_bow", "A bow, yew, and a lord's bow is a war bow and it is kept in a case in a hall.", 2.0, ["tool", "wooden", "weapon", "hunting", "manor", "military", "projectile"]),
    ("manor_mastiff", "A mastiff, a great dog on a chain, and it is a household's answer to everything.", 40.0, ["animal", "farming", "guard", "manor", "large", "heavy"]),
    ("manor_hound", "A hound, one of a pack, and it is fed better than the people who own it.", 30.0, ["animal", "farming", "hunting", "manor", "large", "heavy"]),
    ("manor_sparrow_hawk", "A sparrowhawk on a jesses, and it sits on a fist and turns its head at everything.", 2.0, ["animal", "hunting", "manor", "fletching", "small", "bird"]),
    ("manor_gong", "A hall gong, and it is rung for a meal and for a death and nobody rings it otherwise.", 15.0, ["tool", "metal", "sound_source", "manor", "hallway", "large", "heavy"]),
]


def build():
    out = {}
    for table in (MATERIALS, HOUSE, TOWN):
        for row in table:
            item_id, desc, tags, weight = _row(row)
            out[item_id] = thing(item_id, desc, tags, weight=weight or 1.0)

    # Clothing needs a slot, and a `clothing` tag without one is a linter error
    # for a good reason: gloves with nowhere to go are a label on nothing. Each is
    # routed by the part of the body it goes on, using the library's own slot
    # names â€” and the four the previous batch forgot are included, because the
    # linter named them and a fix that is only in a comment is not a fix.
    for item_id, slot in (
        ("peasant_smock", "torso"), ("peasant_tunic", "torso"),
        ("wool_hose", "legs"), ("kirtle", "bottom"), ("surcoat", "torso"),
        ("dalmatica", "torso"), ("cassock", "torso"), ("habit_frock", "torso"),
        ("noble_robe", "torso"), ("fur_trimmed_gown", "torso"),
        ("merchant_doublet", "torso"), ("hose_wool", "legs"),
        ("jerkin_leather", "torso"), ("gown_cloth", "torso"),
        ("hose_canions", "legs"), ("stomacher", "accessory"),
        ("partlet", "accessory"), ("tippet", "accessory"),
        ("sleeve_under", "arms"), ("hose_leg_shoe", "feet"),
        ("straw_sandals", "feet"), ("worsted_stockings", "legs"),
        ("kneed_breeches", "legs"), ("leather_jacket", "torso"),
        ("quilted_gambeson", "torso"), ("padded_cap", "head"),
        ("friar_hood", "head"), ("travel_cloak", "torso"),
        ("coif_linen", "head"), ("wimple", "head"),
        ("manor_signet_ring", "hands"),
        # `glove_pair`, `belt_leather`, `pouch_leather` and `shoe_spatchock` are
        # batch 4's and are slotted there. Listing them here would be a false
        # positive from the guard below, since this batch skips anything already
        # on disk — and a guard that cries wolf is a guard that gets deleted.
    ):
        if item_id not in out:
            # A typo in a wearables list is **silent**: the item is written with a
            # `clothing` tag and no slot, and the linter catches it seven items
            # later without saying which line was wrong. Refusing is the only way
            # to hear about it here.
            raise KeyError("no item %r in this batch to give a %r slot to"
                           % (item_id, slot))
        out[item_id] = worn(item_id, out[item_id]["description"],
                             [t for t in out[item_id]["tags"]
                              if t != "clothing"], slot,
                             weight=out[item_id]["weight"])
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
