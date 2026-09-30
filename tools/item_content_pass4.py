"""
Item content pass 4 — the trades and the tools that go with each.

Authored content. **The tables are the work**; the record shapes come from
`item_shapes.py`, so a fix to how a consumable is authored lands in one place and
a pass that makes a claim it cannot back is refused rather than written.

    run     python tools/item_content_pass4.py
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
    "content_pass3", os.path.join(_HERE, "item_content_pass3.py"))
_pass3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_pass3)
b1 = _pass1
_row = row

PASS = "pass4"

# ── mining and stone ──────────────────────────────────────────────────────
T_MINER = [
    ("iron_ore", "Iron ore, a lump of it, red-brown and heavy enough to be worth carrying.", 4.0, ["ore", "mining", "stone"]),
    ("copper_ore", "Copper ore, green-streaked, and the first metal anybody mastered.", 3.5, ["ore", "mining", "stone"]),
    ("tin_ore", "Tin ore, dark and heavy, and it is what put a bronze age between two others.", 3.5, ["ore", "mining", "stone"]),
    ("lead_ore", "Lead ore, dense and grey, and it poisons the water and everybody in it.", 4.0, ["ore", "mining", "stone", "hazard"]),
    ("silver_ore", "Silver ore, and the veins in it are thin and bright and worth a man's life.", 4.0, ["ore", "mining", "stone", "valuable"]),
    ("gold_ore", "Gold ore, and it is flecked rather than solid, which is why people dig.", 4.0, ["ore", "mining", "stone", "valuable"]),
    ("coal", "Coal, black and dusty, and it is the fuel of every fire in a smithy.", 3.0, ["fuel", "mining", "stone"]),
    ("ore_cage", "An ore cage, a wicker-and-wood basket that goes up a shaft full of spoil.", 12.0, ["mining", "container", "fibre", "wooden"]),
    ("pit_prop", "A pit prop, a squared timber wedged across a gallery, and it is holding up the roof.", 40.0, ["mining", "wooden", "tool"]),
    ("mine_hammer", "A miner's hammer, a heavy head on a short haft, and the handle is chewed.", 3.0, ["mining", "tool", "metal"]),
    ("mine_hammer_pick", "A miner's pick, and it is for breaking ore out of the face.", 2.5, ["mining", "tool", "metal"]),
    ("mine_lamp", "A miner's lamp, a candle behind a sheet of horn, and it burns low in a bad seam.", 1.0, ["mining", "tool", "light_source", "candle"]),
    ("mine_rope", "A mine rope, hemp, and it is the only thing between a man and the sump.", 12.0, ["mining", "tool", "fibre"]),
    ("mine_cart", "A mine cart, wooden on an iron frame, and it runs on a plank of a road.", 40.0, ["mining", "vehicle", "wooden", "metal", "heavy"]),
    ("ore_washer", "An ore washer, a wooden trough where the gravel is washed and the gold stays.", 20.0, ["mining", "tool", "wooden"]),
    ("shaft_ladder", "A ladder down a shaft, with a platform at the top and no idea what is below.", 30.0, ["mining", "tool", "wooden", "furniture"]),
    ("shaft_timber", "Shaft timbering, a frame of oak set in a square, and it is the roof of a hole.", 80.0, ["mining", "wooden", "building"]),
    ("mine_shaft", "A mine adit, a mouth cut into a hillside, and the timbering is the first thing out there.", 0.0, ["mining", "natural", "opening"]),
    ("ore_wheel", "An ore wheel, a big notched wheel for lifting a cage, and it is turned by a horse or a child.", 60.0, ["mining", "tool", "wooden", "machine"]),
    ("mine_tipple", "A tipple, a screen at the shaft head, and it sorts the spoil as the cage comes up.", 200.0, ["mining", "wooden", "building", "machine"]),
    ("pick_axe", "A pick, and every stone wall in the county was made by somebody with one.", 2.5, ["tool", "metal", "mining", "heavy"]),
    ("mattock_pick", "A mattock, for the stony ground, and the head is set to a shallow angle.", 3.0, ["tool", "metal", "mining", "farming"]),
    ("geologist_hammer", "A stone hammer, a hard iron head on a short shaft, for knocking a specimen off a face.", 1.5, ["mining", "tool", "metal", "geology"]),
    ("mineral_specimen", "A mineral specimen, a labelled box of them, and each is a small miracle.", 0.3, ["mining", "rock", "valuable", "geology"]),
    ("ore_assay", "An assay, a weighed sample and a written result, and it decides what a mine is worth.", 0.1, ["document", "mining", "writing", "paper"]),
    ("mine_shaft_water", "Sump water, and it is cold and brown and nobody wants to stand in it.", 0.0, ["mining", "liquid", "water", "filth"]),
    ("pit_head_frame", "A pit head frame, two legs and a wheel on top, and it is the shape of every coal mine.", 400.0, ["mining", "wooden", "building", "machine", "large"]),
    ("lamp_oil_miner", "A lamp of whale oil, brighter than the candle and it smells for a week.", 0.5, ["mining", "light_source", "liquid"]),
]

# ── smith, miller, cooper, wheelwright ─────────────────────────────────────
T_SMITH = [
    ("smith_hammer", "A smith's hammer, cross-peen, and the handle is hickory because it will not split.", 2.0, ["smith", "tool", "metal"]),
    ("cross_peen_hammer", "A cross-peen hammer, and it has a face on one side and a peen on the other.", 1.8, ["smith", "tool", "metal"]),
    ("tongs", "Tongs, a long pair, and the jaws are set to grip a bar flat.", 1.2, ["smith", "tool", "metal"]),
    ("punch", "A punch, for sinking a hole in hot iron with a hammer that has no business doing that.", 0.6, ["smith", "tool", "metal"]),
    ("swage_block", "A swage block, a block of iron with holes and a shoulder, to shape bar stock over.", 8.0, ["smith", "tool", "metal", "heavy"]),
    ("anvil", "An anvil, on an oak block, and it weighs more than the man who works it.", 80.0, ["smith", "furniture", "metal", "heavy"]),
    ("forge", "A forge, a hearth and a bellows, and the coal is kept banked rather than burning bright.", 200.0, ["smith", "furniture", "fire", "building", "heavy"]),
    ("bellows", "Bellows, a great leather wedge, and two men work them on the biggest forges.", 12.0, ["smith", "tool", "leather", "fire"]),
    ("trug", "A smith's trug, a shallow wooden tub of water, and the hot iron goes in and the sound is the trade.", 20.0, ["smith", "tool", "wooden"]),
    ("quench_trough", "A quenching trough, and the steam comes up and hides the smith for a moment.", 25.0, ["smith", "tool", "wooden", "water"]),
    ("steel_bar", "A bar of steel, folded and welded a hundred times, and it is what an edge is made from.", 2.0, ["material", "metal", "smith"]),
    ("iron_ingot", "An iron ingot, tapped from the bloomery and hammered to a bar.", 5.0, ["material", "metal", "smith", "heavy"]),
    ("horseshoe", "A horseshoe, and it is a piece of bent iron and every hoof on the road is proof.", 0.4, ["smith", "metal", "farms"]),
    ("horseshoe_nails", "A handful of horseshoes, cold-shoed, and they are worth more than the shoes.", 2.0, ["smith", "metal", "farming"]),
    ("nail_pile", "A nail, one of ten thousand, and a nail is a job a person can be reduced to.", 0.02, ["smith", "metal", "small", "building"]),
    ("hand_hammer_small", "A small hammer, for a fitter's bench, and the face is polished by use.", 0.8, ["smith", "tool", "metal"]),
    ("bellows_handle", "A handle of a bellows, replaced, and the tool outlives the man and the handle.", 0.5, ["smith", "tool", "wooden"]),
    ("iron_bar_stock", "A length of iron bar, the raw stock, and it comes from a bloomery in lumps.", 8.0, ["material", "metal", "smith", "heavy"]),
    ("steel_ingot", "An ingot of steel, and a village that makes these is a village with a future.", 6.0, ["material", "metal", "smith"]),
    ("hammer_handle", "A hickory hammer handle, fitted and wedged, and it is the part you replace.", 0.4, ["smith", "tool", "wooden"]),
    ("trough_iron", "A trough of wrought iron, cold-worked in an honest fire, and it is soft and tough.", 4.0, ["material", "metal", "smith"]),
    ("bellows_spit", "The fire shovel and a poker, and the whole shop knows where they are.", 1.5, ["smith", "tool", "metal", "fire"]),
    ("anvil_horn", "The anvil's horn, and it is the only part of a smithy that a farrier fights over.", 0.0, ["smith", "furniture", "metal"]),
    ("iron_rod", "An iron rod, drawn out and squared, and it is what a nail is made from.", 1.0, ["material", "metal", "smith"]),
    ("bar_steel_scales", "The scales of a hot bar, grey-black and brittle, and they fall off the hammer.", 0.0, ["smith", "waste", "metal", "filth"]),
    ("smith_ledger", "The smith's ledger, a book of work done and what is owed for it.", 0.4, ["document", "smith", "writing", "paper", "book"]),
    ("tool_temper", "A tempering trough, a shallow one, and the blade goes in and comes out at a colour.", 15.0, ["smith", "tool", "wooden", "fire"]),
    ("trip_hammer", "A trip hammer, a beam on two posts with a catch, and one man can work it with a treadle.", 150.0, ["smith", "tool", "wooden", "machine", "heavy"]),
    ("bellows_pump", "A bellows pump, a lever and a cylinder, and it is the first of its kind and a marvel.", 20.0, ["smith", "tool", "wooden", "machine"]),
    ("iron_chain", "A length of chain, wrought link by link, and every one was made by hand.", 6.0, ["smith", "metal", "container", "heavy"]),
    ("iron_pot", "A cauldron of iron, and it weighs more than three men and has for four hundred years.", 30.0, ["smith", "kitchen", "metal", "heavy"]),
    ("hearth_tool_iron", "A fire iron, a long bar with a hook, and it is the only thing between you and the fire.", 1.5, ["smith", "tool", "metal", "fire"]),
    ("tongs_pair_steel", "A pair of tongs, the jaws bright where the steel burns, and the hinge is a rivet.", 1.2, ["smith", "tool", "metal"]),
]

T_MILL = [
    ("millstone", "A millstone, a disc of stone with grooves cut in it, and it takes a week to dress.", 400.0, ["miller", "stone", "tool", "heavy", "machine"]),
    ("mill_rind", "The upper millstone, the one that turns, and it is lifted off and turned on edge to dress.", 400.0, ["miller", "stone", "machine", "heavy"]),
    ("hopper", "The mill hopper, a wooden funnel, and it is fed by hand and watched by hand.", 2.0, ["miller", "tool", "wooden", "container"]),
    ("meal_sieve_mill", "A sieve, for the meal, and the mesh is horsehair and it is the last job before sale.", 0.3, ["miller", "tool", "fibre"]),
    ("windmill_sail", "A mill sail, a lattice of wood on an arm, and it is a sail because it is on a mill.", 60.0, ["miller", "wooden", "building", "machine", "large"]),
    ("windmill_cap", "A mill cap, a dome that turns the whole roof into a vane.", 80.0, ["miller", "wooden", "building", "large"]),
    ("water_mill_wheel", "A mill wheel, undershot, and the mill race is cut to make it turn all year.", 200.0, ["miller", "wooden", "machine", "water", "large"]),
    ("mill_bucket", "A mill bucket, a wooden scoop on a chain, and it lifts the grain to the top.", 2.0, ["miller", "tool", "wooden", "container"]),
    ("bolter", "A bolter, a wooden chute that separates the flour from the bran, and its noise is the mill's.", 6.0, ["miller", "tool", "wooden", "machine"]),
    ("furmiser", "A furmiser, a long box of cloth, and the flour is dressed in it to remove the seed.", 4.0, ["miller", "tool", "textile", "machine"]),
    ("meal_measure", "A measure, a wooden bushel, and every sack of meal in the district goes through it.", 1.5, ["miller", "tool", "wooden", "container"]),
    ("grain_dust", "Grain dust, and a miller breathes it daily and the cough is a trade disease.", 0.0, ["miller", "filth", "waste", "grain"]),
    ("stone_dress_pick", "A millstone dresser, a heavy hammer, and the grooves are cut with it.", 3.0, ["miller", "tool", "metal", "stone"]),
    ("miller_sack", "A miller's sack, a great coarse thing, and it takes four bushels.", 0.8, ["miller", "container", "textile", "fodder"]),
    ("meal_bin", "A meal bin, a wooden bin with a sliding floor, and the sliding floor is the whole design.", 8.0, ["miller", "container", "wooden", "storage"]),
    ("horse_mill", "A horse mill, a round track and a post in the middle, and the horse walks it for hours.", 150.0, ["miller", "wooden", "building", "machine", "large"]),
    ("miller_hand", "A miller's hand, and it is the sample he takes from every batch to judge it.", 0.0, ["miller", "tool", "wooden", "small"]),
    ("grain_chute", "A grain chute, a board down which the grain runs to the stones, and worn smooth in a stripe.", 3.0, ["miller", "tool", "wooden"]),
    ("milling_race", "A mill race, the channel of water, and it is a leat and it is a legal right.", 0.0, ["miller", "water", "natural", "opening"]),
    ("screen_mill", "A screen, a sieve of wire, and the finest flour goes through it and the rest does not.", 0.5, ["miller", "tool", "metal", "fibre"]),
    ("kiln_drying_grain", "A drying kiln, and the smell of a drying kiln is the smell of a working mill.", 20.0, ["miller", "building", "fire", "grain"]),
    ("mill_dust_sweep", "A broom of the mill dust, and the mill floor is white underfoot.", 0.0, ["miller", "waste", "grain", "filth"]),
]

T_COOPER = [
    ("barrel_stave", "A barrel stave, an oak board bent round a block, and it is a week's work per stave.", 0.4, ["cooper", "wooden", "material"]),
    ("barrel_head", "A barrel head, a disc of boards, and it is cut and joined without a single joint in the grain.", 1.5, ["cooper", "wooden", "material"]),
    ("cooper_axe", "A cooper's axe, one blade and a flat poll, and it cuts a stave to a line.", 1.5, ["cooper", "tool", "metal", "wooden"]),
    ("cooper_sun", "A sun, a fire of shavings, to bend the staves over, and it makes a room smell of a brewery.", 3.0, ["cooper", "tool", "fire", "wooden"]),
    ("hoop_iron", "An iron hoop, and the hoops go on wet and are driven tight as the wood dries.", 0.5, ["cooper", "material", "metal"]),
    ("barrel_wheel", "A flagging wheel, to take the old hoops off a barrel, and it is set on its end and spun.", 3.0, ["cooper", "tool", "wooden", "machine"]),
    ("barrel_press", "A press, to force the staves together before the hoop goes on.", 25.0, ["cooper", "tool", "wooden", "machine", "heavy"]),
    ("drawknife_cooper", "A cooper's drawknife, for the bevel on the inside of a stave.", 1.2, ["cooper", "tool", "metal", "wooden"]),
    ("barrel_chime", "A chime, the groove round a barrel's middle, and the chime keeps a barrel strong.", 0.0, ["cooper", "wooden", "tool"]),
    ("cask_hoop_steel", "A steel hoop, and it is better than iron because it does not rust and rust ruins a cask.", 0.6, ["cooper", "material", "metal"]),
    ("oak_board_seasoned", "A board of oak, a year seasoned, and it is split not sawn so it will not check.", 6.0, ["cooper", "wooden", "material"]),
    ("tannin_bark", "Tannin bark, and a cooper soaks his staves in it or the beer eats them.", 2.0, ["cooper", "material", "dye", "fibre"]),
    ("barrel_stand", "A barrel stand, and it is the difference between a barrel that rolls and one that does not.", 6.0, ["cooper", "tool", "wooden", "furniture"]),
    ("pitch_mop", "A pitch mop, and a cask is pitched inside to keep the beer from the wood.", 0.3, ["cooper", "tool", "fibre", "fletching"]),
    ("oak_peg", "An oak peg, and a barrel is pegged to the chime and the peg swells in the wet.", 0.01, ["cooper", "wooden", "small", "building"]),
    ("brewery_tun", "A brewing tun, a big open vat, and it is where the wort lives for a week.", 100.0, ["cooper", "kitchen", "wooden", "container", "liquid", "large"]),
    ("cooper_bench", "A cooper's bench, long and scarred, and every scar is a stave that slipped.", 40.0, ["cooper", "furniture", "wooden", "heavy"]),
    ("barrel_jig", "A jig, a frame of iron hoops on a fire, and a stave is bent to it in a minute.", 20.0, ["cooper", "tool", "metal", "fire", "machine"]),
    ("tar_pitch", "Pitch, black and sticky, and it is what a barrel bottom is lined with.", 2.0, ["material", "cooper", "tar", "waste"]),
]

T_WHEEL = [
    ("felloe", "A felloe, the curved segment of a wheel, and it is cut from one piece so it will not break at a joint.", 3.0, ["wheelwright", "wooden", "material"]),
    ("spoke", "A spoke, shaved from oak, and its thickness is a judgement made by thumb.", 0.8, ["wheelwright", "wooden", "material"]),
    ("hob", "A hob, the iron band round a wheel's centre, and it is shrunk on hot and holds the spokes.", 2.0, ["wheelwright", "material", "metal"]),
    ("tyre", "A tyre, an iron band, and it is what a wheel wears out on the road.", 3.0, ["wheelwright", "material", "metal", "heavy"]),
    ("wheelwright_axe", "A wheelwright's axe, and the blade is ground on one side only for shaping.", 2.0, ["wheelwright", "tool", "metal", "wooden"]),
    ("lathe_wheelwright", "A lathe, and a wheel hub is turned on it while it is hot.", 60.0, ["wheelwright", "tool", "wooden", "machine", "heavy"]),
    ("wheel_stock", "A wheel stock, a stout oak collar, and a wagon axle is set in it and pinned.", 12.0, ["wheelwright", "wooden", "material", "heavy"]),
    ("linchpin", "A linchpin, an iron peg, and it is the only thing keeping a wheel on an axle.", 0.1, ["wheelwright", "material", "metal", "vehicle"]),
    ("axle_tree", "An axle tree, a bar of ash, and it is the part that breaks and the part that is cheap.", 20.0, ["wheelwright", "wooden", "vehicle", "material", "heavy"]),
    ("wheel_wand", "A breaking wheel, an iron tool, and it makes the noise a wheelwright is known for.", 2.5, ["wheelwright", "tool", "metal"]),
    ("tire_upset", "An upset, a tool for shrinking a tyre on, and it is hit with a sledge all day.", 3.0, ["wheelwright", "tool", "metal"]),
    ("axle_box", "An axle box, and it is greased every day and it is what tells you the axle is turning.", 4.0, ["wheelwright", "vehicle", "wooden", "metal"]),
    ("wooden_gudgeon", "A wooden gudgeon, a brass-capped pivot in the hub, and it runs silent on a well-kept wheel.", 0.6, ["wheelwright", "wooden", "metal", "vehicle"]),
    ("wheel_nail", "A wheel nail, square-shanked, and it is clinched over and it is stronger than a horseshoe nail.", 0.02, ["wheelwright", "material", "metal", "small", "vehicle"]),
    ("pale_wheel", "A cart wheel, built, dished, and leaning against a wall in a cooper's yard.", 25.0, ["wheelwright", "wooden", "vehicle", "heavy"]),
    ("wheel_truing_stand", "A truing stand, and the wheel goes in and is trued spoke by spoke.", 30.0, ["wheelwright", "tool", "wooden", "machine"]),
    ("hub_axle_cap", "An axle cap, a round of iron, and it keeps the grease in and the dirt out.", 0.5, ["wheelwright", "material", "metal", "vehicle"]),
    ("cart_body", "A cart body, the sides and the floor, boarded and ribbed the way a wheelwright does it.", 80.0, ["wheelwright", "wooden", "vehicle", "heavy", "large"]),
    ("shaft_beam", "A cart shaft, a curved ash pole, and it is the part a horse leans against.", 5.0, ["wheelwright", "wooden", "vehicle"]),
    ("cart_ironwork", "A set of cart irons, forged, and they are all made to one pattern in a shop.", 20.0, ["wheelwright", "material", "metal", "vehicle", "heavy"]),
    ("wagon_tarp", "A wagon tarp, waxed, and it is the difference between a dry load and a ruined one.", 6.0, ["wheelwright", "textile", "vehicle", "insulation"]),
    ("wheel_dust", "The dust a wheel throws on a dry road, and a cart following makes two of it.", 0.0, ["wheelwright", "waste", "road", "filth"]),
]

# ── tanner, weaver, dyer, fuller ──────────────────────────────────────────
T_LEATHER = [
    ("hide_beam", "A hide on a beam, scraped, and the beam is where a tanner works from the inside out.", 30.0, ["tanner", "furniture", "wooden", "heavy"]),
    ("flesh_spade", "A fleshing knife, curved, and it is a one-edge tool used entirely the wrong way.", 0.5, ["tanner", "tool", "metal"]),
    ("beam_slap", "A beam slap, a blunt axe, and it is used to work the hide over the beam.", 2.0, ["tanner", "tool", "metal", "wooden"]),
    ("bark_pit", "A bark pit, a pit of oak bark and water, and a hide is in it for a month.", 200.0, ["tanner", "building", "leather", "liquid", "large"]),
    ("tanning_vat", "A tanning vat, and the smell of a tanyard is a smell you do not forget.", 150.0, ["tanner", "container", "wooden", "liquid", "leather", "large"]),
    ("tawed_leather", "Tawed leather, white and suede-soft, and it is what a glove is cut from.", 0.6, ["tanner", "leather", "material"]),
    ("tanned_hide", "A tanned hide, the colour of tea, and it is what a belt and a book are made from.", 2.0, ["tanner", "leather", "material"]),
    ("oak_bark_tannin", "Oak bark for tanning, and one oak makes both a roof and a pair of shoes.", 2.0, ["tanner", "material", "dye", "fibre"]),
    ("alum", "Alum, the salt used in tanning, and it is what makes a white hide white.", 0.5, ["tanner", "material", "alchemical", "salt"]),
    ("currier_knife", "A currier's knife, and it shaves a hide to the thickness leather wants.", 0.4, ["tanner", "tool", "metal"]),
    ("bark_stripping", "Bark stripping, and a man in an apron and a knife in a wood doing it for a wage.", 0.0, ["tanner", "material", "fibre"]),
    ("tannery_rake", "A rake for the vat, and it is used to lift a hide out without tearing it.", 0.8, ["tanner", "tool", "metal", "leather"]),
    ("hide_slip", "A slippery stone, an adze-shaped tool for knocking a hair off a hide.", 1.2, ["tanner", "tool", "stone", "leather"]),
    ("glove_pair", "A pair of gloves, doeskin, and they are the reason a tanner is not a pauper.", 0.2, ["clothing", "leather", "hands", "winter", "accessory"]),
    ("belt_leather", "A leather belt, cut and punched, and it is the plainest thing a person owns.", 0.3, ["clothing", "leather", "accessory", "waist"]),
    ("pouch_leather", "A small leather pouch, on a string, and it holds coins or a whistle or a tooth.", 0.1, ["clothing", "leather", "accessory", "container", "small"]),
    ("shoe_spatchock", "An overshoe of leather, and it is the answer to mud in a country with mud.", 0.4, ["clothing", "leather", "footwear", "water"]),
    ("bellows_leather", "A bellows side of leather, and it is the only part of a pair that gets replaced.", 0.5, ["tanner", "leather", "material", "tool"]),
    ("leather_scraps", "Leather offcuts, and a cobbler is made of these and nothing else.", 0.3, ["tanner", "leather", "waste"]),
    ("tannery_waste", "The waste of a tanyard, and it goes on the land and stinks for a year.", 0.0, ["tanner", "waste", "filth", "fodder"]),
]

T_TEXTILE = [
    ("warp_beam", "A warp beam, wound with a hundred threads, and it is the length of a whole piece.", 15.0, ["weaver", "tool", "wooden", "machine", "large"]),
    ("weft_spool", "A spool of weft, wound on a quill, and it goes into the shuttle at every pass.", 0.1, ["weaver", "tool", "fibre", "fletching", "small"]),
    ("shuttle", "A shuttle, a wooden boat with the bobbin in it, and it crosses the loom and back.", 0.3, ["weaver", "tool", "wooden", "fibre", "machine"]),
    ("loom", "A loom, and it takes two people and a room and it is the centre of a cloth town.", 120.0, ["weaver", "furniture", "wooden", "machine", "heavy", "large"]),
    ("warp_weight", "A warp weight, a hanging stone, and it keeps the tension in the threads.", 8.0, ["weaver", "tool", "stone", "machine"]),
    ("reed_hook", "A hook for the reed, and a reed is changed to change the cloth.", 0.2, ["weaver", "tool", "metal", "fibre"]),
    ("spinning_wheel", "A spinning wheel, and the wheel is the great invention because it turns the wheel for you.", 8.0, ["weaver", "tool", "wooden", "machine", "craft"]),
    ("distaff_loaded", "A loaded distaff, a hank of wool, and it is the only part of spinning that cannot be hurried.", 0.3, ["weaver", "tool", "fibre", "craft"]),
    ("cloth_bolt", "A bolt of finished cloth, wound on a board, and a bolt is a day's work.", 20.0, ["weaver", "textile", "material", "container", "large"]),
    ("woven_wool", "A web of woollen cloth, off the loom, and it is stiff with size and it softens.", 3.0, ["weaver", "textile", "material", "wool", "insulation"]),
    ("linen_cloth", "Linen, a fine cloth, and it is what a rich person's shirt is made of.", 1.5, ["weaver", "textile", "material", "linen", "cloth"]),
    ("heddle", "A heddle, and the loom has hundreds and they are all different thicknesses.", 0.1, ["weaver", "tool", "fibre", "fletching", "small"]),
    ("loom_comb", "A comb, a weaving comb, and it beats the weft home and a man can be judged on it.", 0.2, ["weaver", "tool", "fibre", "fletching"]),
    ("dye_stuff", "A vat of dye, and the colour goes in twice because one is never enough.", 30.0, ["dyer", "container", "liquid", "dye", "large"]),
    ("dye_well", "A dye well, and it is heated with a fire under it and never boils.", 25.0, ["dyer", "container", "liquid", "dye", "fire", "large"]),
    ("alum_mordant", "Alum, the mordant, and without it the dye washes out in three washes.", 0.5, ["dyer", "material", "alchemical", "dye"]),
    ("woad_vat", "A woad vat, and the smell of a woad vat is like a fart in a church.", 40.0, ["dyer", "container", "liquid", "dye", "plant", "large"]),
    ("fulling_bowl", "A fulling bowl, a wooden one, and the cloth is shrunk in it with water and feet.", 25.0, ["fuller", "container", "wooden", "water", "textile", "large"]),
    ("fulling_rock_stone", "A fulling rock, smooth stone, and it is worked in a bowl to shrink the cloth.", 1.5, ["fuller", "tool", "stone", "textile"]),
    ("napping_cloth", "Napping, raising the nap with teasels, and afterwards the cloth catches the light.", 0.0, ["fuller", "textile", "tool", "fibre"]),
    ("teasel_head", "A teasel head, mounted, and the burrs are the only thing that raises a nap.", 0.2, ["fuller", "tool", "fibre", "farming"]),
    ("warp_thread", "A warp thread, linen, and it is stronger than the weft because it takes the tension.", 0.01, ["weaver", "fibre", "material", "thread"]),
    ("weft_thread", "A weft thread, and it crosses the warp and does the work of holding it together.", 0.01, ["weaver", "fibre", "material", "thread"]),
    ("wool_sheared", "Fleece shorn, greasy and in a heap, and it weighs a man more than he does.", 6.0, ["weaver", "fibre", "wool", "material", "farming"]),
    ("warp_weight_stone", "A stone for a warp weight, and the loom needs one for every ten threads.", 8.0, ["weaver", "tool", "stone", "machine"]),
    ("clay_beam_mould", "A mould, a wooden one, and a beam is cast in it and dried for a year.", 3.0, ["weaver", "tool", "wooden", "trade", "document"]),
    ("dyers_reed", "A weaver's reed, and the dyer borrows the weaver's to beat the cloth down in the vat.", 0.2, ["dyer", "tool", "fibre", "trade"]),
    ("cloth_shears", "Cloth shears, and a tailor's are the only shears that will cut a thread cleanly.", 0.4, ["weaver", "tool", "metal", "fletching"]),
    ("dye_waste", "The dregs of a vat, and a river below a tanyard or a dye works is poisoned for a year.", 0.0, ["dyer", "waste", "filth", "liquid"]),
    ("cloth_stapler", "A cloth press, a heavy screw, and it is how a bolt of cloth is pressed into a chest.", 60.0, ["weaver", "tool", "wooden", "machine", "heavy"]),
]

# ── potter, glazier, plumber, thatcher, slater, sawyer ────────────────────
T_CRAFT = [
    ("potters_wheel", "A potter's wheel, two discs, and it is the one tool that made a thousand jobs.", 15.0, ["potter", "tool", "wooden", "machine", "craft"]),
    ("clay_ball", "A ball of clay, wedged, and wedging is what stops an explosion in the kiln.", 1.0, ["potter", "material", "clay"]),
    ("potter_knife", "A potter's knife, wooden, and a metal one would cut your thumb on the wheel.", 0.3, ["potter", "tool", "wooden"]),
    ("rib_bone", "A rib, a bone, and it curves a wall of clay to a shape nothing else will.", 0.1, ["potter", "tool", "bone"]),
    ("kiln", "A kiln, a brick chamber, and it is fired for two days and watched for both.", 300.0, ["potter", "building", "stone", "fire", "large", "heavy"]),
    ("glaze_pot", "A pot of glaze, and it is mixed from ash and metal and only a fool licks it.", 3.0, ["glazier", "material", "alchemical", "liquid", "hazard"]),
    ("kiln_slip", "A slip, a wash of clay and water, and it is painted onto the pot to keep the glaze off the foot.", 1.0, ["potter", "material", "clay", "liquid"]),
    ("sagger", "A sagger, a fireproof tray, and the pot sits in it and the sagger takes the heat.", 2.0, ["potter", "tool", "clay", "fire"]),
    ("potter_wheel_head", "A wheel head, a disc of plaster, and it is what gives a pot its roundness.", 2.0, ["potter", "tool", "clay", "craft"]),
    ("glaze_brush", "A glaze brush, of hogbristle, and it is a poor brush and a good painter's tool.", 0.1, ["glazier", "tool", "fibre", "fletching"]),
    ("crazing_cup", "A cup with crazing, the fine cracks in the glaze, and collectors pay for it.", 0.3, ["glazier", "valuable", "clay"]),
    ("stoneware_jar_big", "A big stoneware jar, and it holds a barrel of ale and a family of rats.", 40.0, ["potter", "container", "clay", "large", "heavy"]),
    ("tile_roof", "A roof tile, a flat clay tile, and a thousand of them are a roof.", 1.0, ["potter", "building", "clay", "roofing"]),
    ("brick", "A brick, and a house is a great many of them and a good brick is a week's drying.", 3.0, ["potter", "building", "clay", "stone"]),
    ("plumber_solder", "A pot of solder, and a tinker is named for it and it is the hottest thing he owns.", 0.5, ["plumber", "material", "metal", "fire", "hazard"]),
    ("plumber_brush", "A soldering iron, and it is a wedge of iron in a handle and it lives in the fire.", 0.8, ["plumber", "tool", "metal", "fire"]),
    ("lead_sheet", "A sheet of lead, and a lead roof is lighter than a slate one and lasts longer.", 12.0, ["plumber", "material", "metal", "roofing", "heavy"]),
    ("plumber_wax", "A stick of plumber's wax, and it is what a joint is set with and it stays put.", 0.1, ["plumber", "material", "wax", "tool"]),
    ("thatching_knife", "A thatching knife, and it is a long blade on a stick and it is used from a ladder.", 0.6, ["thatcher", "tool", "metal", "wooden"]),
    ("thatch_reed_bundle", "A bundle of reeds for thatching, and it is twenty pounds on a shoulder.", 20.0, ["thatcher", "fodder", "plant", "fibre", "material"]),
    ("ridge_tile", "A ridge tile, bent over a roof to stop the water going down the middle of it.", 2.0, ["potter", "building", "clay", "roofing"]),
    ("slate_axe", "A slater's axe, a pick on one side and a blade on the other, and it is on the roof not in the shed.", 2.0, ["slater", "tool", "metal", "wooden", "roofing"]),
    ("slate_punch", "A slate punch, and it makes a hole in slate without splitting it.", 0.4, ["slater", "tool", "metal", "stone"]),
    ("saw_pit", "A saw pit, a pit over which a long saw is worked, and two men are needed and one is in the pit.", 20.0, ["sawyer", "furniture", "wooden", "building", "large"]),
    ("sawyers_saw", "A saw, eight feet of toothed iron, and it is worked up and down in a pit by two men.", 25.0, ["sawyer", "tool", "metal", "heavy"]),
    ("plank_frame", "A plank frame, a mould for cutting boards to a width, and it is the whole of a sawmill.", 10.0, ["sawyer", "tool", "wooden", "machine"]),
    ("carpenter_square", "A carpenter's square, a try square with a brass fence, and it is the mark of a craftsman.", 0.3, ["carpenter", "tool", "metal", "wooden"]),
    ("mortise_chisel", "A mortise chisel, thick and strong, and it is struck and never pushed.", 0.6, ["carpenter", "tool", "metal"]),
    ("cabinet_rasp", "A cabinet rasp, a half-round file, and it is for a flush fit and nothing else.", 0.4, ["carpenter", "tool", "metal"]),
    ("worm_brace", "A brace and bit, a crank with a bit in it, and it is how a hole is bored by one man.", 0.8, ["carpenter", "tool", "metal", "wooden", "craft"]),
    ("plank_foot", "A plank, a board sawn and dressed, and the mark of a saw is on the face of it.", 8.0, ["sawyer", "wooden", "material"]),
    ("timber_oak_baulk", "A baulk of oak, and it is the size a house frame is cut from.", 200.0, ["sawyer", "wooden", "material", "building", "heavy", "large"]),
    ("kiln_firewood", "A kiln's worth of firewood, and it is stacked under a lean-to and kept dry.", 60.0, ["potter", "fuel", "wooden", "fire", "material", "heavy"]),
    ("glaze_crush", "A crushed glaze, a pot of it, and it is ground wet in a mill and it stains everything.", 2.0, ["glazier", "material", "alchemical", "dye"]),
    ("potter_wheelspinning", "A spinning top, on a string, and it is a toy and a potter's steadying hand both.", 0.0, ["potter", "toy", "fletching", "small"]),
    ("limewash_bucket", "A bucket of limewash, and it is the cheapest way ever found to make a room bright.", 20.0, ["plasterer", "container", "wooden", "building", "liquid", "heavy"]),
    ("plasterer_float", "A plasterer's float, a board on a handle, and it is the difference between a wall and a good wall.", 0.8, ["plasterer", "tool", "wooden", "building"]),
    ("lath_bundle", "A bundle of laths, thin riven strips, and there are a thousand of them in a ceiling.", 8.0, ["plasterer", "wooden", "building", "fodder"]),
    ("plaster_sand", "Sand for the plaster, and it is sieved or the wall will crack in a year.", 20.0, ["plasterer", "material", "building", "stone"]),
    ("nail_lath", "A lath nail, a three-inch cut nail, and it is the longest nail made.", 0.02, ["plasterer", "material", "metal", "small", "building"]),
    ("thatch_bundle_weight", "A spar, a hazel wand, and it is the thing that pins a thatch down.", 0.3, ["thatcher", "tool", "fibre", "plant", "wooden"]),
    ("sparrow_clamp", "A spar clamp, and it drives a spar into a bundle of reeds without splitting them.", 0.5, ["thatcher", "tool", "metal", "fletching"]),
    ("lime_stone", "Lime, a lump of it, and it is slaked with water and makes a week of nothing but whitewash.", 3.0, ["plasterer", "material", "stone", "building", "alchemical"]),
]


def build():
    out = {}
    tables = (T_MINER, T_SMITH, T_MILL, T_COOPER, T_WHEEL, T_LEATHER, T_TEXTILE,
              T_CRAFT)
    for table in tables:
        for row in table:
            # Through `_row()`, never a hand-written unpack. Four batches in, the
            # same two columns (tags / weight) have been transposed against each
            # other four separate times, and each transposition fails differently:
            # a `food` tag on a fishing tool, a `str` where an `int` was expected, a
            # float where a list belonged. One normaliser, one reading of the row.
            item_id, desc, tags, weight = _row(row)
            out[item_id] = thing(item_id, desc, tags, weight=weight or 1.0)

    # The four leather wearables, built through `worn()` so each declares the slot
    # it actually goes on. The linter refuses a `clothing` tag with no slot, and it
    # is right to: "a pair of gloves" with nowhere to put them is a label on
    # nothing. Slot names are the library's own (`hands`, `waist`, `accessory`,
    # `feet`).
    out["glove_pair"] = worn(
        "glove_pair", "A pair of gloves, doeskin, and they are the reason a tanner is not a pauper.",
        ["leather", "hands", "winter", "accessory"], "hands", weight=0.2,
        insulation=3)
    out["belt_leather"] = worn(
        "belt_leather", "A leather belt, cut and punched, and it is the plainest thing a person owns.",
        ["leather", "accessory", "waist", "metal"], "waist", weight=0.3)
    out["pouch_leather"] = worn(
        "pouch_leather", "A small leather pouch, on a string, and it holds coins or a whistle or a tooth.",
        ["leather", "accessory", "container", "small"], "accessory", weight=0.1)
    out["shoe_spatchock"] = worn(
        "shoe_spatchock", "An overshoe of leather, and it is the answer to mud in a country with mud.",
        ["leather", "footwear", "water", "winter"], "feet", weight=0.4,
        insulation=2)
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
