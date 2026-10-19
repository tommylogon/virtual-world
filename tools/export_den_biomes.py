import json
import os
import re

BIOMES_RAW = [
  {
    "name": "Den Entrance",
    "terrain": "outdoor",
    "tags": ["entrance", "threshold", "natural", "animal_den"],
    "surface": "earth",
    "descriptions": [
      "A low opening breaks the ground beneath tangled roots.",
      "Tracks converge on a dark entrance that smells of fur and damp soil."
    ]
  },
  {
    "name": "Den Entrance Tunnel",
    "terrain": "indoor",
    "tags": ["entrance", "passage", "tunnel", "below_ground"],
    "surface": "packed_earth",
    "descriptions": [
      "A narrow tunnel slopes inward, carrying the smell of the den.",
      "Claw marks score the earthen walls along a well-travelled passage."
    ]
  },
  {
    "name": "Main Den Chamber",
    "terrain": "indoor",
    "tags": ["room", "living", "central", "animal_den"],
    "surface": "packed_earth",
    "descriptions": [
      "A broad chamber forms the heart of the den, worn smooth by repeated use.",
      "Loose earth, fur, and scattered debris mark the centre of the animal's territory."
    ]
  },
  {
    "name": "Sleeping Hollow",
    "terrain": "indoor",
    "tags": ["sleeping", "resting", "sheltered", "animal_den"],
    "surface": "dry_leaves",
    "descriptions": [
      "A shallow hollow holds a thick layer of leaves and flattened grass.",
      "The bedding is warm with lingering body heat and the scent of fur."
    ]
  },
  {
    "name": "Nest Chamber",
    "terrain": "indoor",
    "tags": ["nest", "breeding", "young", "sheltered"],
    "surface": "twigs",
    "descriptions": [
      "A carefully shaped hollow cradles a nest of woven twigs and soft fibres.",
      "The chamber is lined with down, moss, and whatever soft material the creature could gather."
    ]
  },
  {
    "name": "Birthing Chamber",
    "terrain": "indoor",
    "tags": ["breeding", "birthing", "young", "protected", "warm"],
    "surface": "moss",
    "descriptions": [
      "Soft moss and fur cover a secluded hollow prepared for newborn young.",
      "The chamber is unusually warm, with fresh bedding and the faint sounds of small animals."
    ]
  },
  {
    "name": "Nursery",
    "terrain": "indoor",
    "tags": ["young", "nursery", "breeding", "protected", "family"],
    "surface": "dry_grass",
    "descriptions": [
      "Small bodies nestle together among grass and tufts of fur.",
      "The floor is scattered with bedding, tiny tracks, and the remnants of recent feeding."
    ]
  },
  {
    "name": "Pup Play Chamber",
    "terrain": "indoor",
    "tags": ["young", "play", "social", "family", "wolf_den"],
    "surface": "soft_earth",
    "descriptions": [
      "The earth is scuffed by small paws and the rough games of growing pups.",
      "Chewed sticks, feathers, and scraps of bedding litter the chamber."
    ]
  },
  {
    "name": "Maternal Refuge",
    "terrain": "indoor",
    "tags": ["breeding", "mother", "young", "refuge", "defensible"],
    "surface": "moss",
    "descriptions": [
      "A secluded recess protects a mother and her young from disturbances.",
      "Fresh bedding fills the narrow space, and the entrance is easy to guard."
    ]
  },
  {
    "name": "Guard Chamber",
    "terrain": "indoor",
    "tags": ["guard", "defensive", "watch", "pack", "chamber"],
    "surface": "stone",
    "descriptions": [
      "The chamber overlooks the approach, leaving little room for an intruder to pass unseen.",
      "Scuffed ground and a strong animal scent mark a place where sentries regularly pause."
    ]
  },
  {
    "name": "Bear Hibernation Chamber",
    "terrain": "indoor",
    "tags": ["sleeping", "hibernation", "bear", "seasonal", "insulated"],
    "surface": "dry_leaves",
    "descriptions": [
      "A deep, insulated hollow is packed with leaves, grass, and moss.",
      "The chamber is still and close, its bedding arranged for a long winter sleep."
    ]
  },
  {
    "name": "Bear Feeding Site",
    "terrain": "outdoor",
    "tags": ["feeding", "bear", "food", "foraging", "messy"],
    "surface": "trampled_soil",
    "descriptions": [
      "Broken branches, crushed plants, and scraps of food mark a regular feeding spot.",
      "The ground is churned beneath heavy paws, with a lingering smell of meat and berries."
    ]
  },
  {
    "name": "Bear Food Cache",
    "terrain": "indoor",
    "tags": ["food", "storage", "cache", "bear", "seasonal"],
    "surface": "dry_earth",
    "descriptions": [
      "Roots and scraps of vegetation have been gathered into a sheltered corner.",
      "A pungent collection of stored food rests beneath loose leaves and earth."
    ]
  },
  {
    "name": "Wolf Den Sleeping Chamber",
    "terrain": "indoor",
    "tags": ["sleeping", "wolf", "pack", "resting", "bedding"],
    "surface": "dry_grass",
    "descriptions": [
      "Several flattened sleeping hollows lie close together in the earth.",
      "The chamber carries the musky scent of a pack that rests here between hunts."
    ]
  },
  {
    "name": "Wolf Den Entrance Watch",
    "terrain": "indoor",
    "tags": ["wolf", "guard", "entrance", "watch", "defensive"],
    "surface": "packed_earth",
    "descriptions": [
      "The passage widens just enough for a wolf to stand watch at the entrance.",
      "Paw prints overlap around a spot from which the outside approach can be heard."
    ]
  },
  {
    "name": "Pack Gathering Chamber",
    "terrain": "indoor",
    "tags": ["social", "pack", "gathering", "central", "wolf"],
    "surface": "hard_earth",
    "descriptions": [
      "A broad open space bears the tracks of many animals moving together.",
      "The chamber is worn smooth where pack members gather, rest, and interact."
    ]
  },
  {
    "name": "Wolf Kill Cache",
    "terrain": "indoor",
    "tags": ["food", "carcass", "storage", "wolf", "pack"],
    "surface": "stone",
    "descriptions": [
      "Bones and scraps of a carcass lie in a sheltered recess.",
      "The air is heavy with the smell of meat, blood, and scavengers."
    ]
  },
  {
    "name": "Fox Sleeping Den",
    "terrain": "indoor",
    "tags": ["sleeping", "fox", "small_den", "resting", "sheltered"],
    "surface": "dry_leaves",
    "descriptions": [
      "A compact hollow is lined with leaves and fine grasses.",
      "The small chamber is tidy by animal standards, with a narrow entrance and soft bedding."
    ]
  },
  {
    "name": "Fox Prey Pantry",
    "terrain": "indoor",
    "tags": ["food", "storage", "prey", "fox", "cache"],
    "surface": "dry_earth",
    "descriptions": [
      "Small prey remains are tucked into a dry pocket beneath the earth.",
      "Feathers, fur, and tiny bones reveal a store of food gathered over several hunts."
    ]
  },
  {
    "name": "Badger Main Sett",
    "terrain": "indoor",
    "tags": ["badger", "burrow", "living", "central", "sett"],
    "surface": "packed_earth",
    "descriptions": [
      "A substantial chamber lies beneath a network of well-worn tunnels.",
      "The floor is firm and smooth, marked by generations of clawed feet."
    ]
  },
  {
    "name": "Badger Bedding Chamber",
    "terrain": "indoor",
    "tags": ["badger", "sleeping", "bedding", "burrow", "resting"],
    "surface": "dry_grass",
    "descriptions": [
      "Dry grass and leaves form a thick bed in a sheltered underground room.",
      "Old bedding has been pushed aside and replaced with fresh plant material."
    ]
  },
  {
    "name": "Badger Latrine",
    "terrain": "outdoor",
    "tags": ["latrine", "waste", "badger", "territory", "smelly"],
    "surface": "loose_soil",
    "descriptions": [
      "A shallow pit outside the living quarters serves as a communal latrine.",
      "The sharp smell and disturbed earth make the purpose of this patch unmistakable."
    ]
  },
  {
    "name": "Rabbit Whelping Burrow",
    "terrain": "indoor",
    "tags": ["rabbit", "breeding", "young", "burrow", "insulated"],
    "surface": "fur",
    "descriptions": [
      "A small chamber is lined with fur pulled from the mother's own coat.",
      "The nest is hidden behind loose soil and soft grass, far from the main passage."
    ]
  },
  {
    "name": "Rabbit Communal Warren",
    "terrain": "indoor",
    "tags": ["rabbit", "communal", "burrow", "social", "passage"],
    "surface": "packed_earth",
    "descriptions": [
      "Several narrow tunnels converge on a chamber worn smooth by many rabbits.",
      "Small tracks crisscross the floor, linking a maze of nearby burrows."
    ]
  },
  {
    "name": "Rabbit Escape Tunnel",
    "terrain": "indoor",
    "tags": ["rabbit", "escape", "tunnel", "secondary_exit", "defensive"],
    "surface": "loose_earth",
    "descriptions": [
      "A tight tunnel runs away from the main burrow toward a concealed exit.",
      "Fresh scrapes in the soil show how quickly a rabbit could disappear through here."
    ]
  },
  {
    "name": "Mole Nest Chamber",
    "terrain": "indoor",
    "tags": ["mole", "nest", "underground", "sleeping", "insulated"],
    "surface": "dry_grass",
    "descriptions": [
      "A rounded chamber sits deep in the soil, insulated by roots and packed earth.",
      "A small nest of grasses occupies the centre of this otherwise bare underground room."
    ]
  },
  {
    "name": "Mole Worm Larder",
    "terrain": "indoor",
    "tags": ["mole", "food", "storage", "worms", "larder"],
    "surface": "damp_soil",
    "descriptions": [
      "Earthworms and other small prey are gathered in a cool pocket of soil.",
      "The larder is damp and earthy, with tiny feeding marks along its edges."
    ]
  },
  {
    "name": "Groundhog Winter Chamber",
    "terrain": "indoor",
    "tags": ["groundhog", "hibernation", "sleeping", "seasonal", "burrow"],
    "surface": "dry_grass",
    "descriptions": [
      "A deep burrow ends in a chamber packed with insulating plant matter.",
      "The quiet room is built for months underground, away from winter winds."
    ]
  },
  {
    "name": "Beaver Lodge Living Chamber",
    "terrain": "indoor",
    "tags": ["beaver", "lodge", "living", "family", "raised"],
    "surface": "wood",
    "descriptions": [
      "A raised chamber rests within a mound of branches, mud, and woven sticks.",
      "The wooden floor is littered with bark and dry plant fibres."
    ]
  },
  {
    "name": "Beaver Bark Store",
    "terrain": "indoor",
    "tags": ["beaver", "food", "storage", "bark", "winter"],
    "surface": "wood",
    "descriptions": [
      "Stripped branches and bark are stacked where they can be reached from the lodge.",
      "Piles of gnawed wood form a winter store beside the damp walls."
    ]
  },
  {
    "name": "Beaver Underwater Entrance",
    "terrain": "underwater",
    "tags": ["beaver", "entrance", "underwater", "aquatic", "concealed"],
    "surface": "river_silt",
    "descriptions": [
      "A submerged passage leads beneath the lodge, hidden below the waterline.",
      "Bubbles rise from a dark opening between roots and waterlogged branches."
    ]
  },
  {
    "name": "Otter Resting Holt",
    "terrain": "indoor",
    "tags": ["otter", "resting", "holt", "water_adjacent", "bedding"],
    "surface": "dry_grass",
    "descriptions": [
      "A sheltered hollow near the water is padded with grass and reeds.",
      "Wet tracks cross the floor, but the bedding has been kept relatively dry."
    ]
  },
  {
    "name": "Otter Fish Cache",
    "terrain": "outdoor",
    "tags": ["otter", "food", "fish", "cache", "water_adjacent"],
    "surface": "river_stone",
    "descriptions": [
      "Fish scraps and scales collect among the stones beside the water.",
      "A slick feeding spot smells of river water and freshly caught prey."
    ]
  },
  {
    "name": "Hedgehog Day Nest",
    "terrain": "indoor",
    "tags": ["hedgehog", "nest", "sleeping", "small_animal", "leaves"],
    "surface": "dry_leaves",
    "descriptions": [
      "A tight ball of leaves conceals a small resting hollow.",
      "The nest is tucked beneath brush, its entrance nearly hidden by fallen foliage."
    ]
  },
  {
    "name": "Skunk Refuge",
    "terrain": "indoor",
    "tags": ["skunk", "refuge", "sleeping", "defensive", "small_den"],
    "surface": "dry_grass",
    "descriptions": [
      "A narrow, sheltered hollow offers a skunk a quiet place to rest.",
      "The chamber carries a pungent musk that warns visitors to keep their distance."
    ]
  },
  {
    "name": "Raccoon Sleeping Hollow",
    "terrain": "indoor",
    "tags": ["raccoon", "sleeping", "hollow", "tree_den", "resting"],
    "surface": "wood",
    "descriptions": [
      "A hollow tree trunk opens into a cramped nest of leaves and bark.",
      "The interior is scuffed by climbing claws and scattered with scraps carried inside."
    ]
  },
  {
    "name": "Squirrel Drey",
    "terrain": "outdoor",
    "tags": ["squirrel", "nest", "tree", "canopy", "dry"],
    "surface": "twigs",
    "descriptions": [
      "A woven ball of twigs sits among branches, lined with moss and leaves.",
      "The nest sways gently in the canopy, sheltered by overlapping foliage."
    ]
  },
  {
    "name": "Squirrel Nut Cache",
    "terrain": "indoor",
    "tags": ["squirrel", "food", "storage", "nuts", "tree_hollow"],
    "surface": "dry_leaves",
    "descriptions": [
      "Nuts and seeds fill a dry pocket inside a hollow trunk.",
      "Tiny teeth marks cover the shells piled around this well-used cache."
    ]
  },
  {
    "name": "Bat Roost",
    "terrain": "indoor",
    "tags": ["bat", "roost", "ceiling", "colony", "dark"],
    "surface": "stone",
    "descriptions": [
      "Bats cling to the ceiling above a floor scattered with droppings.",
      "The air is warm and close, disturbed by the rustle of folded wings."
    ]
  },
  {
    "name": "Bat Nursery Roost",
    "terrain": "indoor",
    "tags": ["bat", "nursery", "young", "colony", "warm"],
    "surface": "rough_stone",
    "descriptions": [
      "A sheltered pocket of the roost holds clusters of young bats.",
      "The ceiling is crowded with small shapes and the constant rustle of wings."
    ]
  },
  {
    "name": "Deer Bedding Hollow",
    "terrain": "outdoor",
    "tags": ["deer", "sleeping", "bedding", "forest_floor", "camouflage"],
    "surface": "dry_leaves",
    "descriptions": [
      "A shallow depression in the leaves marks a regular resting place.",
      "Bent grass and a scatter of deer tracks reveal where the herd beds down."
    ]
  },
  {
    "name": "Elk Calving Shelter",
    "terrain": "outdoor",
    "tags": ["elk", "calving", "young", "shelter", "vegetation"],
    "surface": "moss",
    "descriptions": [
      "Tall grass and brush conceal a sheltered patch where a calf can lie unseen.",
      "The vegetation is flattened into a warm hollow beneath the trees."
    ]
  },
  {
    "name": "Wild Boar Wallowside Den",
    "terrain": "outdoor",
    "tags": ["boar", "den", "resting", "mud", "wallowside"],
    "surface": "mud",
    "descriptions": [
      "A rough shelter lies close to a muddy wallow, surrounded by churned earth.",
      "Heavy tracks lead from the resting place to the dark, wet ground outside."
    ]
  },
  {
    "name": "Boar Farrowing Nest",
    "terrain": "indoor",
    "tags": ["boar", "breeding", "young", "nest", "insulated"],
    "surface": "dry_grass",
    "descriptions": [
      "A deep bowl of grass and leaves protects a litter of piglets.",
      "The nest is tucked behind roots and branches, thickly lined against the cold."
    ]
  },
  {
    "name": "Mountain Goat Ledge Refuge",
    "terrain": "outdoor",
    "tags": ["mountain_goat", "resting", "cliff", "ledge", "elevated"],
    "surface": "bare_rock",
    "descriptions": [
      "A narrow ledge provides a secure resting place above a steep drop.",
      "Hoof marks score the rock where mountain goats pause beyond easy reach."
    ]
  },
  {
    "name": "Hyena Den Chamber",
    "terrain": "indoor",
    "tags": ["hyena", "den", "pack", "living", "underground"],
    "surface": "hard_earth",
    "descriptions": [
      "A broad underground chamber bears the tracks of a busy clan.",
      "Bones and scraps lie along the walls where hyenas gather and rest."
    ]
  },
  {
    "name": "Hyena Bone Cache",
    "terrain": "indoor",
    "tags": ["hyena", "bones", "food", "storage", "scavenging"],
    "surface": "gravel",
    "descriptions": [
      "A heap of gnawed bones fills a dry recess in the den.",
      "Old fragments crunch underfoot, carrying the stale smell of carrion."
    ]
  },
  {
    "name": "Lion Resting Cave",
    "terrain": "indoor",
    "tags": ["lion", "resting", "cave", "pride", "sheltered"],
    "surface": "sand",
    "descriptions": [
      "A spacious cave offers shade and room for several large cats to rest.",
      "The sandy floor bears broad paw prints and flattened patches of bedding."
    ]
  },
  {
    "name": "Lion Cub Nursery",
    "terrain": "indoor",
    "tags": ["lion", "young", "nursery", "pride", "protected"],
    "surface": "dry_grass",
    "descriptions": [
      "A hidden recess shelters cubs among grass, fur, and dry leaves.",
      "Small paw prints surround a warm hollow beneath an overhanging rock."
    ]
  },
  {
    "name": "Tiger Kill Chamber",
    "terrain": "indoor",
    "tags": ["tiger", "food", "carcass", "cave", "solitary"],
    "surface": "stone",
    "descriptions": [
      "A secluded chamber contains the remains of prey dragged out of sight.",
      "Scratches and drag marks cross the floor beneath the smell of old meat."
    ]
  },
  {
    "name": "Leopard Tree Cache",
    "terrain": "outdoor",
    "tags": ["leopard", "food", "tree", "elevated", "cache"],
    "surface": "wood",
    "descriptions": [
      "A heavy branch supports the remains of prey lifted beyond the reach of scavengers.",
      "Claw marks and scraps of fur cling to the bark above the forest floor."
    ]
  },
  {
    "name": "Lynx Rock Den",
    "terrain": "indoor",
    "tags": ["lynx", "den", "rock", "solitary", "resting"],
    "surface": "stone",
    "descriptions": [
      "A rocky recess provides a quiet refuge for a solitary predator.",
      "Tufts of fur lie in the corners of a chamber with a narrow approach."
    ]
  },
  {
    "name": "Wolverine Food Cache",
    "terrain": "indoor",
    "tags": ["wolverine", "food", "cache", "cold", "scavenging"],
    "surface": "frozen_earth",
    "descriptions": [
      "Frozen scraps and bones are hidden in a cold crevice.",
      "The cache is tucked away from the sun, beneath loose stones and packed snow."
    ]
  },
  {
    "name": "Giant Raven Nest Platform",
    "terrain": "outdoor",
    "tags": ["raven", "nest", "giant_bird", "cliff", "elevated", "breeding"],
    "surface": "twigs",
    "descriptions": [
      "An enormous nest of branches occupies a broad shelf on the cliff face.",
      "Thick sticks and tangled fibres form a platform deep enough to cradle giant eggs."
    ]
  },
  {
    "name": "Giant Raven Landing Ledge",
    "terrain": "outdoor",
    "tags": ["raven", "landing", "cliff", "flight", "elevated"],
    "surface": "bare_rock",
    "descriptions": [
      "A broad stone ledge gives a giant raven room to land and fold its wings.",
      "Feathers and claw scratches mark the rock above a dizzying drop."
    ]
  },
  {
    "name": "Giant Raven Bone Cache",
    "terrain": "outdoor",
    "tags": ["raven", "bones", "food", "cache", "cliff"],
    "surface": "bare_rock",
    "descriptions": [
      "Bones and torn scraps of meat collect in a sheltered pocket of the cliff.",
      "The wind whistles through a cache littered with the remains of stolen meals."
    ]
  },
  {
    "name": "Eagle Eyrie",
    "terrain": "outdoor",
    "tags": ["eagle", "nest", "cliff", "elevated", "breeding"],
    "surface": "twigs",
    "descriptions": [
      "A massive platform of interwoven branches crowns a high rock shelf.",
      "The nest overlooks the valley, lined with grass and tufts of down."
    ]
  },
  {
    "name": "Owl Roost Hollow",
    "terrain": "indoor",
    "tags": ["owl", "roost", "tree_hollow", "dark", "resting"],
    "surface": "wood",
    "descriptions": [
      "A deep hollow in an old tree offers shelter from daylight and weather.",
      "Pellets and feathers collect below a narrow opening in the trunk."
    ]
  },
  {
    "name": "Woodpecker Nest Cavity",
    "terrain": "indoor",
    "tags": ["woodpecker", "nest", "tree_hollow", "breeding", "small_bird"],
    "surface": "wood",
    "descriptions": [
      "A clean cavity has been excavated into the heartwood of a standing tree.",
      "Wood chips gather below the entrance to a chamber just large enough for the bird and its young."
    ]
  },
  {
    "name": "Heron Rookery Nest",
    "terrain": "outdoor",
    "tags": ["heron", "nest", "wetland", "colony", "tree"],
    "surface": "sticks",
    "descriptions": [
      "A loose platform of sticks rests among the branches above the marsh.",
      "Droppings, feathers, and broken reeds mark a crowded nesting tree."
    ]
  },
  {
    "name": "Penguin Nesting Scrape",
    "terrain": "outdoor",
    "tags": ["penguin", "nest", "cold", "breeding", "colony"],
    "surface": "gravel",
    "descriptions": [
      "A shallow hollow among stones shelters an egg from the worst of the wind.",
      "Pebbles and feathers form a simple nest amid the noisy colony."
    ]
  },
  {
    "name": "Seabird Cliff Burrow",
    "terrain": "indoor",
    "tags": ["seabird", "burrow", "cliff", "breeding", "narrow"],
    "surface": "loose_soil",
    "descriptions": [
      "A narrow burrow disappears into the grassy face of the sea cliff.",
      "The passage smells of salt, feathers, and damp earth."
    ]
  },
  {
    "name": "Crocodile Nest Mound",
    "terrain": "outdoor",
    "tags": ["crocodile", "nest", "eggs", "reptile", "warm", "riverbank"],
    "surface": "sand",
    "descriptions": [
      "A mound of sand and rotting vegetation holds a clutch of buried eggs.",
      "The warm nest rises above the riverbank, surrounded by tracks and dragged vegetation."
    ]
  },
  {
    "name": "Alligator Basking Bank",
    "terrain": "outdoor",
    "tags": ["alligator", "basking", "riverbank", "reptile", "resting"],
    "surface": "mud",
    "descriptions": [
      "A sun-warmed bank slopes gently into the water.",
      "Deep grooves and broad tail marks cross the mud beside a dark pool."
    ]
  },
  {
    "name": "Snake Hibernaculum",
    "terrain": "indoor",
    "tags": ["snake", "hibernation", "reptile", "crevice", "seasonal"],
    "surface": "stone",
    "descriptions": [
      "A deep rocky fissure shelters several snakes through the cold season.",
      "The chamber is still and cool, its cracks offering countless places to coil out of sight."
    ]
  },
  {
    "name": "Snake Egg Chamber",
    "terrain": "indoor",
    "tags": ["snake", "eggs", "breeding", "reptile", "warm", "hidden"],
    "surface": "loose_soil",
    "descriptions": [
      "A warm pocket of soil holds a clutch of leathery eggs.",
      "The sheltered chamber is partly covered by decaying leaves and loose earth."
    ]
  },
  {
    "name": "Turtle Nesting Pit",
    "terrain": "outdoor",
    "tags": ["turtle", "eggs", "nest", "sand", "buried"],
    "surface": "sand",
    "descriptions": [
      "A flask-shaped pit has been dug into the warm sand above the waterline.",
      "Loose grains conceal the eggs beneath a patch of freshly disturbed ground."
    ]
  },
  {
    "name": "Frog Breeding Pool",
    "terrain": "underwater",
    "tags": ["frog", "breeding", "water", "eggs", "amphibian"],
    "surface": "mud",
    "descriptions": [
      "A shallow pool shelters clusters of eggs among reeds and submerged plants.",
      "The water is crowded with tadpoles, insects, and the soft movement of amphibians."
    ]
  },
  {
    "name": "Toad Burrow",
    "terrain": "indoor",
    "tags": ["toad", "burrow", "amphibian", "moist", "resting"],
    "surface": "damp_soil",
    "descriptions": [
      "A small burrow beneath a stone offers a cool retreat from the sun.",
      "The damp walls are pressed smooth where the toad settles during the day."
    ]
  },
  {
    "name": "Giant Spider Egg Chamber",
    "terrain": "indoor",
    "tags": ["spider", "eggs", "breeding", "web", "protected", "monster"],
    "surface": "webbing",
    "descriptions": [
      "Silken sacs hang within a chamber layered in dense webbing.",
      "The air is still, and every surface is bound in sticky threads around the egg cases."
    ]
  },
  {
    "name": "Giant Spider Lair",
    "terrain": "indoor",
    "tags": ["spider", "lair", "web", "ambush", "predator", "monster"],
    "surface": "webbing",
    "descriptions": [
      "Thick strands of webbing span the chamber from wall to wall.",
      "The floor is a trap of sticky silk, discarded husks, and wrapped prey."
    ]
  },
  {
    "name": "Webbed Prey Store",
    "terrain": "indoor",
    "tags": ["spider", "food", "storage", "wrapped_prey", "web", "monster"],
    "surface": "webbing",
    "descriptions": [
      "Wrapped bundles hang from the ceiling like pale, motionless cocoons.",
      "The chamber stores prey in layers of silk, each parcel suspended beyond easy reach."
    ]
  },
  {
    "name": "Ant Nursery",
    "terrain": "indoor",
    "tags": ["ant", "nursery", "larvae", "colony", "insect", "warm"],
    "surface": "fine_soil",
    "descriptions": [
      "Rows of larvae and pupae occupy carefully maintained pockets in the earth.",
      "Worker ants move constantly between the nursery and deeper passages."
    ]
  },
  {
    "name": "Ant Food Granary",
    "terrain": "indoor",
    "tags": ["ant", "food", "storage", "granary", "colony", "insect"],
    "surface": "dry_sand",
    "descriptions": [
      "Seeds and fragments of food are packed into dry chambers above the damp soil.",
      "The granary is orderly, with narrow paths between neatly separated stores."
    ]
  },
  {
    "name": "Ant Queen Chamber",
    "terrain": "indoor",
    "tags": ["ant", "queen", "colony", "breeding", "protected", "insect"],
    "surface": "fine_soil",
    "descriptions": [
      "A protected chamber houses the enormous queen at the centre of the colony.",
      "Workers crowd the warm, carefully maintained room around the egg-laying monarch."
    ]
  },
  {
    "name": "Termite Royal Chamber",
    "terrain": "indoor",
    "tags": ["termite", "queen", "king", "breeding", "colony", "insect"],
    "surface": "clay",
    "descriptions": [
      "A thick-walled clay chamber encloses the swollen queen and her mate.",
      "Workers tend the royal pair in a humid room deep within the mound."
    ]
  },
  {
    "name": "Termite Fungus Garden",
    "terrain": "indoor",
    "tags": ["termite", "fungus", "food", "cultivation", "humid", "colony"],
    "surface": "compost",
    "descriptions": [
      "Pale fungal growth covers carefully arranged beds of chewed plant matter.",
      "Warm, humid air hangs over a living garden tended by countless workers."
    ]
  },
  {
    "name": "Bee Brood Chamber",
    "terrain": "indoor",
    "tags": ["bee", "brood", "hive", "young", "wax", "colony"],
    "surface": "wax",
    "descriptions": [
      "Rows of wax cells hold developing brood beneath the constant movement of worker bees.",
      "The chamber hums with life and carries the warm scent of wax and honey."
    ]
  },
  {
    "name": "Bee Honey Store",
    "terrain": "indoor",
    "tags": ["bee", "honey", "food", "storage", "hive", "colony"],
    "surface": "wax",
    "descriptions": [
      "Honey-filled cells glisten along the walls of the hive.",
      "The air is thick with sweetness, while workers seal stores for leaner days."
    ]
  },
  {
    "name": "Wasp Paper Nest Core",
    "terrain": "indoor",
    "tags": ["wasp", "nest", "paper", "brood", "colony", "defensive"],
    "surface": "paper_fibre",
    "descriptions": [
      "Layered paper-like walls enclose a dense cluster of brood cells.",
      "The nest vibrates with activity, its thin walls guarding a fiercely defended core."
    ]
  },
  {
    "name": "Giant Beetle Grub Chamber",
    "terrain": "indoor",
    "tags": ["beetle", "grubs", "breeding", "organic_matter", "insect", "monster"],
    "surface": "rotting_wood",
    "descriptions": [
      "Large grubs writhe among damp wood fibres and decomposing plant matter.",
      "The chamber is rich with rot, providing food and shelter for growing larvae."
    ]
  },
  {
    "name": "Worm Colony Moisture Chamber",
    "terrain": "indoor",
    "tags": ["worm", "colony", "moist", "soil", "organic_matter"],
    "surface": "wet_soil",
    "descriptions": [
      "Soft soil glistens with moisture as worms burrow through the chamber.",
      "Decaying leaves and rich earth form a living mass beneath the surface."
    ]
  },
  {
    "name": "Giant Centipede Refuge",
    "terrain": "indoor",
    "tags": ["centipede", "refuge", "predator", "crevice", "damp", "monster"],
    "surface": "wet_stone",
    "descriptions": [
      "A narrow, damp fissure disappears beneath a slab of rock.",
      "The chamber is littered with shed exoskeletons and the remains of small prey."
    ]
  },
  {
    "name": "Giant Scorpion Burrow",
    "terrain": "indoor",
    "tags": ["scorpion", "burrow", "desert", "ambush", "dry", "monster"],
    "surface": "sand",
    "descriptions": [
      "A deep sandy burrow ends in a cool pocket beneath the sun-baked ground.",
      "Scraped sand and a pair of claw marks frame a chamber built for sudden ambush."
    ]
  },
  {
    "name": "Giant Scorpion Molting Chamber",
    "terrain": "indoor",
    "tags": ["scorpion", "molting", "growth", "sheltered", "monster"],
    "surface": "fine_sand",
    "descriptions": [
      "A secluded chamber contains the discarded shell of a growing scorpion.",
      "Loose sand cushions the floor where the creature can shed its old armour undisturbed."
    ]
  },
  {
    "name": "Cave Troll Sleeping Den",
    "terrain": "indoor",
    "tags": ["troll", "sleeping", "cave", "large_creature", "monster", "bedding"],
    "surface": "stone",
    "descriptions": [
      "A cavernous hollow holds a crude bed of moss, hides, and crushed vegetation.",
      "Deep grooves in the stone mark the resting place of a creature far larger than a man."
    ]
  },
  {
    "name": "Ogre Larder",
    "terrain": "indoor",
    "tags": ["ogre", "food", "storage", "larder", "monster", "carrion"],
    "surface": "packed_earth",
    "descriptions": [
      "Bones, salted meat, and dubious scraps are piled against the cavern wall.",
      "A sour mixture of smoke, old food, and rot hangs over the crude store."
    ]
  },
  {
    "name": "Ogre Trophy Alcove",
    "terrain": "indoor",
    "tags": ["ogre", "trophies", "storage", "decoration", "monster", "intimidation"],
    "surface": "stone",
    "descriptions": [
      "Broken weapons, skulls, and stolen objects crowd a rough alcove.",
      "The collection appears arranged to impress visitors or remind them of past victims."
    ]
  },
  {
    "name": "Troll Regeneration Pool",
    "terrain": "indoor",
    "tags": ["troll", "healing", "water", "regeneration", "monster", "magical"],
    "surface": "wet_stone",
    "descriptions": [
      "A shallow pool collects dark water beneath a ceiling furred with moss.",
      "The water ripples around old scars and fragments of shed flesh, as though the cave itself is alive."
    ]
  },
  {
    "name": "Goblin Sleeping Nook",
    "terrain": "indoor",
    "tags": ["goblin", "sleeping", "bedding", "small_humanoid", "monster", "communal"],
    "surface": "straw",
    "descriptions": [
      "A cramped nook contains a heap of straw, stolen cloth, and patched blankets.",
      "The sleeping space is crowded with small footprints and the smell of smoke."
    ]
  },
  {
    "name": "Goblin Scrap Workshop",
    "terrain": "indoor",
    "tags": ["goblin", "workshop", "crafting", "scrap", "tools", "monster"],
    "surface": "rough_wood",
    "descriptions": [
      "Bent metal, broken tools, and scavenged timber cover a makeshift workbench.",
      "The room rings with the memory of crude repairs and improvised inventions."
    ]
  },
  {
    "name": "Goblin Mushroom Farm",
    "terrain": "indoor",
    "tags": ["goblin", "food", "fungus", "cultivation", "underground", "monster"],
    "surface": "compost",
    "descriptions": [
      "Pale mushrooms grow in damp rows on beds of decaying organic matter.",
      "The low chamber smells of wet soil and fungus, providing a steady source of food."
    ]
  },
  {
    "name": "Hobgoblin Barracks",
    "terrain": "indoor",
    "tags": ["hobgoblin", "sleeping", "barracks", "military", "communal", "monster"],
    "surface": "wood_planks",
    "descriptions": [
      "Bunks and bedrolls line a chamber kept in rough military order.",
      "Weapons rest beside each sleeping place, ready for a sudden call to arms."
    ]
  },
  {
    "name": "Orc Warband Hall",
    "terrain": "indoor",
    "tags": ["orc", "gathering", "social", "warband", "central", "monster"],
    "surface": "stone",
    "descriptions": [
      "A broad hall holds fire pits, rough benches, and the scars of countless gatherings.",
      "The walls are blackened by smoke and decorated with crude trophies from raids."
    ]
  },
  {
    "name": "Orc Armoury",
    "terrain": "indoor",
    "tags": ["orc", "weapons", "storage", "armour", "defensive", "monster"],
    "surface": "packed_earth",
    "descriptions": [
      "Axes, shields, and patched armour hang from pegs driven into the walls.",
      "The equipment is battered but serviceable, stacked for rapid distribution."
    ]
  },
  {
    "name": "Kobold Egg Chamber",
    "terrain": "indoor",
    "tags": ["kobold", "eggs", "breeding", "nursery", "warm", "monster"],
    "surface": "warm_stone",
    "descriptions": [
      "Clusters of leathery eggs rest in warm hollows lined with soft debris.",
      "Kobold caretakers have arranged stones and scraps to keep the chamber at a steady temperature."
    ]
  },
  {
    "name": "Kobold Trap Workshop",
    "terrain": "indoor",
    "tags": ["kobold", "traps", "workshop", "crafting", "defensive", "monster"],
    "surface": "stone",
    "descriptions": [
      "Wire, sharpened stakes, counterweights, and scraps of metal cover the floor.",
      "Half-built traps crowd the walls, each designed to punish an unwary intruder."
    ]
  },
  {
    "name": "Lizardfolk Egg Nursery",
    "terrain": "indoor",
    "tags": ["lizardfolk", "eggs", "nursery", "reptilian", "humid", "monster"],
    "surface": "warm_mud",
    "descriptions": [
      "Eggs rest in warm mud beneath a roof of woven reeds.",
      "The chamber is humid and carefully tended, with shallow channels carrying moisture through the soil."
    ]
  },
  {
    "name": "Lizardfolk Fish Smokehouse",
    "terrain": "indoor",
    "tags": ["lizardfolk", "food", "smoking", "fish", "storage", "monster"],
    "surface": "wood_planks",
    "descriptions": [
      "Fish hang from racks above a low, smoky fire pit.",
      "The walls are stained dark by smoke, and the air carries the sharp smell of preserved catch."
    ]
  },
  {
    "name": "Dragon Hoard Vault",
    "terrain": "indoor",
    "tags": ["dragon", "treasure", "storage", "hoard", "secure", "monster", "magical"],
    "surface": "gold",
    "descriptions": [
      "Coins, jewels, and stolen treasures form deep drifts across the cavern floor.",
      "The chamber gleams with accumulated wealth, each glittering object part of a dragon's guarded hoard."
    ]
  },
  {
    "name": "Dragon Sleeping Lair",
    "terrain": "indoor",
    "tags": ["dragon", "sleeping", "lair", "large_creature", "monster", "warm"],
    "surface": "obsidian",
    "descriptions": [
      "A vast hollow bears the marks of enormous claws and a body that has rested here for centuries.",
      "The stone is warm beneath a bed of ash, scorched hides, and crushed treasure."
    ]
  },
  {
    "name": "Dragon Egg Incubation Chamber",
    "terrain": "indoor",
    "tags": ["dragon", "eggs", "breeding", "incubation", "heat", "monster", "magical"],
    "surface": "volcanic_rock",
    "descriptions": [
      "Huge eggs rest in hollows warmed by vents beneath the dark stone.",
      "Heat shimmers above a chamber carefully arranged to keep the eggs at an even temperature."
    ]
  },
  {
    "name": "Dragon Feeding Pit",
    "terrain": "indoor",
    "tags": ["dragon", "feeding", "carcass", "large_creature", "monster", "waste"],
    "surface": "blackened_stone",
    "descriptions": [
      "The floor is stained by blood and scattered with bones too large for ordinary beasts.",
      "A deep pit collects the remains of meals consumed by a creature of enormous appetite."
    ]
  },
  {
    "name": "Wyvern Roost",
    "terrain": "outdoor",
    "tags": ["wyvern", "roost", "cliff", "flight", "monster", "elevated"],
    "surface": "bare_rock",
    "descriptions": [
      "A high crag provides room for a winged predator to rest above the clouds.",
      "Claw furrows, shed scales, and scattered bones mark the exposed perch."
    ]
  },
  {
    "name": "Griffin Nest",
    "terrain": "outdoor",
    "tags": ["griffin", "nest", "cliff", "breeding", "monster", "elevated"],
    "surface": "twigs",
    "descriptions": [
      "A broad nest of branches and hides crowns a rocky summit.",
      "Feathers and fur line the nest, which overlooks open ground suitable for hunting."
    ]
  },
  {
    "name": "Roc Nest Platform",
    "terrain": "outdoor",
    "tags": ["roc", "nest", "giant_bird", "mountaintop", "monster", "breeding"],
    "surface": "logs",
    "descriptions": [
      "Trunks and enormous branches form a platform large enough to hold a small building.",
      "The nest rests on a mountain peak, surrounded by feathers as long as swords."
    ]
  },
  {
    "name": "Manticore Lair",
    "terrain": "indoor",
    "tags": ["manticore", "lair", "predator", "ambush", "monster", "bones"],
    "surface": "sandstone",
    "descriptions": [
      "A rocky lair is strewn with bones and deep gouges from a barbed tail.",
      "The sheltered chamber offers a clear view of its approach and room to spring upon prey."
    ]
  },
  {
    "name": "Basilisk Lair",
    "terrain": "indoor",
    "tags": ["basilisk", "lair", "reptile", "ambush", "monster", "mineral"],
    "surface": "limestone",
    "descriptions": [
      "A pale cavern holds the shed scales and remains of creatures that wandered too close.",
      "The chamber is quiet and cold, with a clear stretch of floor before the creature's hiding place."
    ]
  },
  {
    "name": "Chimera Nest",
    "terrain": "indoor",
    "tags": ["chimera", "nest", "breeding", "monster", "large_creature", "mixed_bedding"],
    "surface": "bone",
    "descriptions": [
      "A jumble of hides, branches, and bones forms a crude nest in the cave.",
      "The chamber carries several overlapping animal scents, each clashing with the others."
    ]
  },
  {
    "name": "Hydra Marsh Den",
    "terrain": "outdoor",
    "tags": ["hydra", "den", "marsh", "aquatic", "monster", "ambush"],
    "surface": "mud",
    "descriptions": [
      "A muddy hollow opens beside dark water beneath a tangle of reeds.",
      "Several deep tracks converge on a pool where the water scarcely moves."
    ]
  },
  {
    "name": "Troll Mushroom Pantry",
    "terrain": "indoor",
    "tags": ["troll", "food", "fungus", "storage", "cave", "monster"],
    "surface": "damp_soil",
    "descriptions": [
      "Fleshy mushrooms and roots are piled in a cool, damp corner.",
      "The store is unevenly sorted, with the freshest growth nearest a trickle of water."
    ]
  },
  {
    "name": "Undead Crypt Resting Cell",
    "terrain": "indoor",
    "tags": ["undead", "resting", "crypt", "burial", "dark", "monster"],
    "surface": "stone_slab",
    "descriptions": [
      "A stone bier stands in a narrow chamber untouched by daylight.",
      "Dust and old burial cloth cover the resting place, where the air feels unnaturally still."
    ]
  },
  {
    "name": "Ghoul Feeding Den",
    "terrain": "indoor",
    "tags": ["ghoul", "feeding", "carrion", "undead", "monster", "stench"],
    "surface": "bone",
    "descriptions": [
      "Bones and scraps of rotting flesh cover the floor of the low chamber.",
      "The stale air reeks of decay, and claw marks surround a heap of discarded remains."
    ]
  },
  {
    "name": "Vampire Coffin Chamber",
    "terrain": "indoor",
    "tags": ["vampire", "sleeping", "coffin", "undead", "secure", "monster"],
    "surface": "polished_stone",
    "descriptions": [
      "A sealed coffin rests in a shadowed chamber behind a heavy door.",
      "Dark curtains and carefully placed furnishings keep every trace of daylight away."
    ]
  },
  {
    "name": "Lich Phylactery Vault",
    "terrain": "indoor",
    "tags": ["lich", "phylactery", "vault", "magical", "undead", "secure", "monster"],
    "surface": "black_marble",
    "descriptions": [
      "Runes cover the walls around a protected niche that houses a vessel of terrible importance.",
      "The vault is unnaturally cold, and faint magical light gathers around its sealed centre."
    ]
  },
  {
    "name": "Demon Summoning Chamber",
    "terrain": "indoor",
    "tags": ["demon", "summoning", "ritual", "magical", "monster", "dangerous"],
    "surface": "obsidian",
    "descriptions": [
      "A ritual circle is carved into the black stone, surrounded by scorched offerings.",
      "The chamber smells of smoke and sulphur, while strange markings stain the walls."
    ]
  },
  {
    "name": "Imp Nest",
    "terrain": "indoor",
    "tags": ["imp", "nest", "small_creature", "bedding", "monster", "mischief"],
    "surface": "straw",
    "descriptions": [
      "A cramped hollow is stuffed with stolen trinkets, scraps of cloth, and straw.",
      "Tiny claw marks and scattered objects suggest a nest maintained by creatures that enjoy mischief."
    ]
  },
  {
    "name": "Elemental Earth Niche",
    "terrain": "indoor",
    "tags": ["earth_elemental", "resting", "mineral", "magical", "monster", "earth"],
    "surface": "raw_stone",
    "descriptions": [
      "A rough niche blends almost seamlessly into the surrounding rock.",
      "Loose pebbles tremble across the floor as though the stone itself is breathing."
    ]
  },
  {
    "name": "Fire Elemental Hearth",
    "terrain": "indoor",
    "tags": ["fire_elemental", "heat", "resting", "magical", "monster", "fire"],
    "surface": "lava_rock",
    "descriptions": [
      "A hollow of blackened stone glows with heat from cracks beneath the floor.",
      "Ash drifts around a fiery core where ordinary bedding would burn in moments."
    ]
  },
  {
    "name": "Ice Wyrm Den",
    "terrain": "indoor",
    "tags": ["ice_wyrm", "den", "cold", "monster", "hibernation", "frozen"],
    "surface": "ice",
    "descriptions": [
      "A frozen cavern winds into a deep hollow glazed with blue ice.",
      "Scales have scored the frost along a path leading to a cold, silent chamber."
    ]
  },
  {
    "name": "Frost Giant Sleeping Hall",
    "terrain": "indoor",
    "tags": ["frost_giant", "sleeping", "large_creature", "cold", "monster", "bedding"],
    "surface": "packed_snow",
    "descriptions": [
      "A bed of furs and pelts occupies a hall carved into the frozen mountain.",
      "The chamber is broad enough for a giant to stretch out without touching the walls."
    ]
  },
  {
    "name": "Stone Giant Carving Chamber",
    "terrain": "indoor",
    "tags": ["stone_giant", "workshop", "crafting", "stone", "monster", "large_creature"],
    "surface": "stone",
    "descriptions": [
      "Half-finished stone figures and chipped blocks surround a giant's work area.",
      "Stone dust blankets the floor beneath crude tools and immense carved fragments."
    ]
  },
  {
    "name": "Cyclops Livestock Pen",
    "terrain": "indoor",
    "tags": ["cyclops", "livestock", "pen", "food", "monster", "large_creature"],
    "surface": "straw",
    "descriptions": [
      "A crude enclosure holds animals destined to feed a single enormous resident.",
      "Heavy posts, trampled straw, and a broad gate mark the pen's rough construction."
    ]
  },
  {
    "name": "Minotaur Lair Chamber",
    "terrain": "indoor",
    "tags": ["minotaur", "lair", "maze", "resting", "monster", "defensive"],
    "surface": "flagstone",
    "descriptions": [
      "A stone chamber lies beyond a confusing series of turns and blind passages.",
      "Deep hoof marks and broken furnishings reveal the lair of a powerful, territorial beast."
    ]
  },
  {
    "name": "Owlbear Den",
    "terrain": "indoor",
    "tags": ["owlbear", "den", "sleeping", "predator", "monster", "large_creature"],
    "surface": "dry_leaves",
    "descriptions": [
      "A rough den is piled with leaves, torn feathers, and the remains of prey.",
      "Claw furrows score the entrance where the creature has repeatedly scraped against the rock."
    ]
  },
  {
    "name": "Dire Wolf Pack Den",
    "terrain": "indoor",
    "tags": ["dire_wolf", "den", "pack", "sleeping", "monster", "large_creature"],
    "surface": "packed_earth",
    "descriptions": [
      "A spacious den contains several deep sleeping hollows worn by massive bodies.",
      "Heavy paw prints and shredded bedding mark the territory of an oversized pack."
    ]
  },
  {
    "name": "Dire Bear Winter Den",
    "terrain": "indoor",
    "tags": ["dire_bear", "hibernation", "den", "sleeping", "monster", "insulated"],
    "surface": "moss",
    "descriptions": [
      "A deep cavern is stuffed with moss, leaves, and thick layers of fur.",
      "The floor is flattened beneath a vast sleeping hollow, sheltered from every cold draft."
    ]
  },
  {
    "name": "Giant Boar Rooting Den",
    "terrain": "outdoor",
    "tags": ["giant_boar", "den", "rooting", "feeding", "monster", "forest"],
    "surface": "churned_earth",
    "descriptions": [
      "The ground has been torn apart by enormous tusks searching for roots and grubs.",
      "A rough shelter beneath exposed roots offers a place to rest beside the feeding grounds."
    ]
  },
  {
    "name": "Giant Boar Wallows",
    "terrain": "outdoor",
    "tags": ["giant_boar", "mud", "bathing", "cooling", "territory", "monster"],
    "surface": "deep_mud",
    "descriptions": [
      "A deep muddy hollow bears the impressions of a creature far larger than an ordinary boar.",
      "Mud and churned water coat the surrounding roots, with a powerful animal scent in the air."
    ]
  },
  {
    "name": "Giant Raven Feather Store",
    "terrain": "outdoor",
    "tags": ["giant_raven", "feathers", "nest_material", "storage", "cliff", "monster"],
    "surface": "feathers",
    "descriptions": [
      "Large feathers and strips of dried grass have been gathered into a sheltered cleft.",
      "The cache contains nesting material collected from the cliff and surrounding forest."
    ]
  },
  {
    "name": "Sand Worm Resting Hollow",
    "terrain": "indoor",
    "tags": ["sand_worm", "resting", "burrow", "desert", "monster", "ambush"],
    "surface": "loose_sand",
    "descriptions": [
      "A vast pocket beneath the dunes is packed with shifting sand.",
      "The hollow is marked by smooth, curved walls and a trail leading deeper underground."
    ]
  },
  {
    "name": "Mimic Lair",
    "terrain": "indoor",
    "tags": ["mimic", "ambush", "lair", "deception", "monster", "predator"],
    "surface": "wood_planks",
    "descriptions": [
      "The chamber resembles an ordinary storage room, though its contents sit strangely still.",
      "Scratches and scraps of clothing surround an inviting space that feels unnaturally deliberate."
    ]
  },
  {
    "name": "Gelatinous Cube Nesting Pool",
    "terrain": "indoor",
    "tags": ["gelatinous_cube", "resting", "slime", "monster", "damp", "corrosive"],
    "surface": "slick_stone",
    "descriptions": [
      "A shallow depression holds a clear, viscous residue that clings to the stone.",
      "Small bones and dissolved debris collect in the stagnant pool at the end of the passage."
    ]
  },
  {
    "name": "Slime Colony Growth Chamber",
    "terrain": "indoor",
    "tags": ["slime", "colony", "growth", "moist", "monster", "organic"],
    "surface": "slime",
    "descriptions": [
      "Translucent growths spread across the damp floor in overlapping patches.",
      "The chamber glistens with mucus and broken organic matter absorbed into the colony."
    ]
  },
  {
    "name": "Fungal Beast Spore Chamber",
    "terrain": "indoor",
    "tags": ["fungal_beast", "spores", "growth", "fungus", "monster", "humid"],
    "surface": "mycelium",
    "descriptions": [
      "Pale fungal threads carpet the floor beneath clusters of swollen spore sacs.",
      "A faint haze hangs in the still air, carrying the smell of damp wood and decay."
    ]
  },
  {
    "name": "Treant Root Chamber",
    "terrain": "indoor",
    "tags": ["treant", "roots", "resting", "living_wood", "monster", "forest"],
    "surface": "roots",
    "descriptions": [
      "Thick roots intertwine to form a sheltered hollow within the living tree.",
      "The chamber is quiet except for the creaking of wood and the slow movement of roots."
    ]
  },
  {
    "name": "Dryad Heart Grove",
    "terrain": "outdoor",
    "tags": ["dryad", "sanctuary", "grove", "living", "magical", "monster"],
    "surface": "moss",
    "descriptions": [
      "A secluded grove gathers around an ancient tree whose roots form natural seats and hollows.",
      "Flowers grow in a ring beneath the branches, untouched by the surrounding wilderness."
    ]
  },
  {
    "name": "Unicorn Foaling Glade",
    "terrain": "outdoor",
    "tags": ["unicorn", "breeding", "young", "glade", "magical", "sheltered"],
    "surface": "soft_grass",
    "descriptions": [
      "A quiet glade is carpeted with soft grass and sheltered by flowering trees.",
      "Fresh hoofprints circle a sheltered hollow where a newborn foal could rest."
    ]
  },
  {
    "name": "Phoenix Ash Nest",
    "terrain": "outdoor",
    "tags": ["phoenix", "nest", "fire", "rebirth", "magical", "monster"],
    "surface": "warm_ash",
    "descriptions": [
      "A circular bed of warm ash lies among blackened stones and glowing embers.",
      "Bright feathers rest in the centre of the nest, untouched by the heat around them."
    ]
  },
  {
    "name": "Sea Serpent Underwater Lair",
    "terrain": "underwater",
    "tags": ["sea_serpent", "lair", "underwater", "aquatic", "monster", "large_creature"],
    "surface": "sea_silt",
    "descriptions": [
      "A deep hollow beneath the seabed bears broad grooves from a coiling body.",
      "Broken shells and bones collect around a sheltered pocket beneath the rock shelf."
    ]
  },
  {
    "name": "Kraken Resting Grotto",
    "terrain": "underwater",
    "tags": ["kraken", "resting", "grotto", "underwater", "monster", "tentacles"],
    "surface": "dark_sand",
    "descriptions": [
      "A cavernous underwater hollow opens into deep, lightless water.",
      "The stone is polished by enormous tentacles, and wreckage rests among the silt."
    ]
  },
  {
    "name": "Merfolk Sleeping Cove",
    "terrain": "underwater",
    "tags": ["merfolk", "sleeping", "cove", "aquatic", "communal", "sheltered"],
    "surface": "smooth_stone",
    "descriptions": [
      "A sheltered cove contains smooth stone hollows covered in woven sea grass.",
      "Shells and polished pebbles decorate the resting places along the quiet water."
    ]
  },
  {
    "name": "Siren Nesting Ledge",
    "terrain": "outdoor",
    "tags": ["siren", "nest", "coast", "cliff", "breeding", "monster"],
    "surface": "seaweed",
    "descriptions": [
      "A ledge above the surf is padded with seaweed, feathers, and tangled reeds.",
      "The rock is slick with salt spray, and scattered shells glint among the nesting material."
    ]
  },
  {
    "name": "Fey Burrow",
    "terrain": "indoor",
    "tags": ["fey", "burrow", "magical", "small_creature", "sheltered", "monster"],
    "surface": "flower_petals",
    "descriptions": [
      "A tiny chamber beneath the roots is lined with petals, moss, and delicate fibres.",
      "Soft lights flicker along the walls, illuminating a burrow that feels larger inside than out."
    ]
  },
  {
    "name": "Shadow Beast Refuge",
    "terrain": "indoor",
    "tags": ["shadow_beast", "refuge", "dark", "ambush", "magical", "monster"],
    "surface": "black_stone",
    "descriptions": [
      "A lightless recess seems to swallow the edges of everything inside it.",
      "The floor is smooth and bare, with no sign of how the creature enters or leaves."
    ]
  },
  {
    "name": "Crystal Golem Dormancy Niche",
    "terrain": "indoor",
    "tags": ["crystal_golem", "dormancy", "crystal", "magical", "monster", "mineral"],
    "surface": "crystal",
    "descriptions": [
      "A faceted recess fits the contours of a motionless crystalline figure.",
      "Prismatic light crawls over the walls as the chamber resonates with a faint hum."
    ]
  },
  {
    "name": "Gargoyle Perch",
    "terrain": "outdoor",
    "tags": ["gargoyle", "perch", "roost", "stone", "elevated", "monster"],
    "surface": "weathered_stone",
    "descriptions": [
      "A carved stone perch juts from the tower above the surrounding rooftops.",
      "The ledge is weathered and empty, though fresh scratches mar the stone beneath it."
    ]
  },
  {
    "name": "Gargoyle Dormancy Alcove",
    "terrain": "indoor",
    "tags": ["gargoyle", "dormancy", "alcove", "stone", "monster", "concealed"],
    "surface": "stone",
    "descriptions": [
      "A statue-shaped alcove conceals a resting creature among ordinary carvings.",
      "Dust covers the floor, broken only by fragments of stone shed from the motionless figure."
    ]
  },
  {
    "name": "Burrow Guardian Chamber",
    "terrain": "indoor",
    "tags": ["guardian", "guard", "defensive", "burrow", "monster", "chokepoint"],
    "surface": "packed_earth",
    "descriptions": [
      "A reinforced chamber narrows the passage to a single defensible approach.",
      "Claw marks and disturbed soil show where a guardian holds its position against intruders."
    ]
  },
  {
    "name": "Emergency Escape Chamber",
    "terrain": "indoor",
    "tags": ["escape", "secondary_exit", "tunnel", "defensive", "hidden", "animal_den"],
    "surface": "loose_earth",
    "descriptions": [
      "A cramped recess hides a narrow passage leading away from the main den.",
      "Freshly disturbed earth conceals an escape route that can be opened from within."
    ]
  },
  {
    "name": "Water Collection Chamber",
    "terrain": "indoor",
    "tags": ["water", "storage", "drainage", "resource", "den", "utility"],
    "surface": "wet_stone",
    "descriptions": [
      "Water drips from the ceiling into a shallow depression worn into the floor.",
      "A small pool collects runoff, its edges marked by mud and tracks."
    ]
  },
  {
    "name": "Drainage Channel",
    "terrain": "indoor",
    "tags": ["drainage", "water", "passage", "utility", "den", "flood_control"],
    "surface": "gravel",
    "descriptions": [
      "A narrow channel carries seepage away from the lower chambers.",
      "Pebbles and fine sediment line a groove worn by the steady movement of water."
    ]
  },
  {
    "name": "Ventilation Shaft",
    "terrain": "indoor",
    "tags": ["ventilation", "shaft", "airflow", "utility", "burrow", "vertical"],
    "surface": "raw_earth",
    "descriptions": [
      "A narrow shaft rises toward the surface, carrying a faint current of air.",
      "Roots hang from the opening, and loose soil has collected around the base."
    ]
  },
  {
    "name": "Midden Chamber",
    "terrain": "indoor",
    "tags": ["waste", "midden", "debris", "den", "storage", "smelly"],
    "surface": "compost",
    "descriptions": [
      "Bones, shed skins, broken nesting material, and old scraps have accumulated in a corner.",
      "The heap records weeks of occupation, slowly decomposing in the damp air."
    ]
  },
  {
    "name": "Territorial Scent Marking Post",
    "terrain": "outdoor",
    "tags": ["territory", "scent_marking", "boundary", "animal_den", "outdoor"],
    "surface": "tree_bark",
    "descriptions": [
      "A prominent tree bears repeated scratches and scent marks at animal height.",
      "Tracks converge on the post, where the resident repeatedly announces its presence."
    ]
  },
  {
    "name": "Scratching and Grooming Chamber",
    "terrain": "indoor",
    "tags": ["grooming", "scratching", "fur", "resting", "animal_den"],
    "surface": "rough_bark",
    "descriptions": [
      "Rough bark and stone offer surfaces for scratching and grooming.",
      "Tufts of fur and flakes of shed skin gather around the favoured spot."
    ]
  },
  {
    "name": "Molting Chamber",
    "terrain": "indoor",
    "tags": ["molting", "shedding", "growth", "sheltered", "animal_den"],
    "surface": "dry_sand",
    "descriptions": [
      "The chamber contains shed skins, scales, or fragments of an old exoskeleton.",
      "A sheltered hollow provides room for the resident to outgrow its former covering."
    ]
  },
  {
    "name": "Tool and Object Cache",
    "terrain": "indoor",
    "tags": ["storage", "tools", "objects", "cache", "intelligent_creature", "den"],
    "surface": "rough_wood",
    "descriptions": [
      "Useful sticks, stones, shells, and scavenged objects have been collected in one place.",
      "The cache is arranged according to a logic that may be practical, habitual, or entirely alien."
    ]
  },
  {
    "name": "Prey Ambush Hide",
    "terrain": "indoor",
    "tags": ["ambush", "hunting", "concealed", "predator", "den", "defensive"],
    "surface": "loose_gravel",
    "descriptions": [
      "A concealed recess overlooks a narrow approach where prey must pass close by.",
      "The ground is bare near the hiding place, leaving little to betray the predator's position."
    ]
  },
  {
    "name": "Carcass Butchering Area",
    "terrain": "outdoor",
    "tags": ["feeding", "carcass", "butchering", "predator", "waste", "outdoor"],
    "surface": "trampled_soil",
    "descriptions": [
      "Drag marks and torn vegetation surround a spot where large prey is taken apart.",
      "Bones and scraps are scattered around the remains, attracting flies and scavengers."
    ]
  },
  {
    "name": "Scavenger Gathering Ground",
    "terrain": "outdoor",
    "tags": ["scavenging", "feeding", "social", "bones", "outdoor"],
    "surface": "gravel",
    "descriptions": [
      "Scattered bones and scraps draw scavengers to this repeatedly visited patch of ground.",
      "Tracks of different sizes overlap around the remains of past meals."
    ]
  },
  {
    "name": "Sentinel Lookout",
    "terrain": "outdoor",
    "tags": ["lookout", "watch", "elevated", "defensive", "territory"],
    "surface": "bare_rock",
    "descriptions": [
      "A raised perch provides a clear view of the approaches to the den.",
      "The surface is worn by repeated visits from a creature watching over its territory."
    ]
  },
  {
    "name": "Rain Shelter",
    "terrain": "outdoor",
    "tags": ["shelter", "weather_protection", "resting", "outdoor", "den"],
    "surface": "dry_leaves",
    "descriptions": [
      "An overhanging rock and thick brush keep most of the rain from reaching the ground.",
      "The sheltered patch remains comparatively dry, even when the surrounding soil turns to mud."
    ]
  },
  {
    "name": "Sunbathing Ledge",
    "terrain": "outdoor",
    "tags": ["basking", "sunlight", "resting", "warm", "reptile"],
    "surface": "sun_warmed_rock",
    "descriptions": [
      "A broad slab of rock catches the sun for much of the day.",
      "The stone is warm beneath the scattered tracks of creatures that gather here to bask."
    ]
  },
  {
    "name": "Cold Storage Crevice",
    "terrain": "indoor",
    "tags": ["storage", "cold", "food", "crevice", "preservation"],
    "surface": "ice",
    "descriptions": [
      "A narrow crack remains cold long after the surrounding chambers have warmed.",
      "Food scraps and frozen remains lie tucked behind a screen of stone."
    ]
  },
  {
    "name": "Flood Refuge Chamber",
    "terrain": "indoor",
    "tags": ["refuge", "flood", "elevated", "safety", "den"],
    "surface": "raised_stone",
    "descriptions": [
      "A raised shelf offers shelter when water fills the lower tunnels.",
      "Mud lines on the walls show how high the last flood reached."
    ]
  },
  {
    "name": "Deep Sanctuary",
    "terrain": "indoor",
    "tags": ["sanctuary", "deep_chamber", "protected", "resting", "den"],
    "surface": "smooth_stone",
    "descriptions": [
      "A secluded chamber lies far from the entrance, sheltered by several turns of passage.",
      "The air is still and the floor undisturbed, making this the safest place in the den."
    ]
  },
  {
    "name": "Ritual or Display Chamber",
    "terrain": "indoor",
    "tags": ["ritual", "display", "social", "intelligent_creature", "magical", "den"],
    "surface": "carved_stone",
    "descriptions": [
      "Marks, objects, and carefully arranged materials give the chamber a ceremonial character.",
      "The space appears reserved for displays of status, mating rituals, or strange communal customs."
    ]
  },
  {
    "name": "Territory Boundary Passage",
    "terrain": "indoor",
    "tags": ["boundary", "passage", "territory", "defensive", "den"],
    "surface": "packed_earth",
    "descriptions": [
      "A narrow passage marks the transition between the den and the surrounding tunnels.",
      "Scratches, scent marks, and disturbed debris warn other creatures that they are nearing occupied territory."
    ]
  },
  {
    "name": "Collapsed Chamber",
    "terrain": "indoor",
    "tags": ["collapsed", "blocked", "debris", "ruin", "den", "hazard"],
    "surface": "rubble",
    "descriptions": [
      "Fallen earth and broken stone choke what was once a usable chamber.",
      "Old tracks disappear beneath the debris, leaving the fate of the former occupants uncertain."
    ]
  },
  {
    "name": "Abandoned Nest",
    "terrain": "outdoor",
    "tags": ["abandoned", "nest", "ruin", "old_bedding", "wildlife"],
    "surface": "rotting_twigs",
    "descriptions": [
      "A broken nest of twigs and leaves hangs empty among the branches.",
      "Rain and wind have loosened the structure, while moss begins to cover the old bedding."
    ]
  },
  {
    "name": "Fossil and Bone Deposit",
    "terrain": "indoor",
    "tags": ["bones", "fossils", "storage", "cave", "old_remains"],
    "surface": "limestone",
    "descriptions": [
      "Old bones and mineralised fragments lie embedded in the floor and piled against the wall.",
      "The deposit contains remains from creatures that occupied the cavern long before its current resident."
    ]
  },
  {
    "name": "Mineral Licking Site",
    "terrain": "outdoor",
    "tags": ["mineral", "feeding", "salt", "herbivore", "resource"],
    "surface": "mineral_crust",
    "descriptions": [
      "Pale mineral deposits coat a rock repeatedly visited by herbivores.",
      "The stone is roughened by tongues and hooves seeking the salts within."
    ]
  },
  {
    "name": "Medicinal Herb Cache",
    "terrain": "indoor",
    "tags": ["herbs", "storage", "medicine", "resource", "intelligent_creature"],
    "surface": "dry_grass",
    "descriptions": [
      "Bundles of dried leaves and roots hang from a dry section of the chamber.",
      "The collection includes plants gathered for healing, scent masking, or other useful effects."
    ]
  },
  {
    "name": "Waterproof Nest Chamber",
    "terrain": "indoor",
    "tags": ["nest", "waterproof", "rain_protection", "breeding", "sheltered"],
    "surface": "woven_reeds",
    "descriptions": [
      "A woven shell of reeds and leaves sheds water away from the soft bedding inside.",
      "The chamber remains dry despite damp surroundings, its walls patched with fresh vegetation."
    ]
  },
  {
    "name": "Floating Nest",
    "terrain": "surface_water",
    "tags": ["nest", "floating", "aquatic", "reeds", "breeding"],
    "surface": "woven_reeds",
    "descriptions": [
      "A floating mat of reeds and stems rises and falls with the water.",
      "The nest is anchored among aquatic plants, keeping its eggs above the shifting surface."
    ]
  },
  {
    "name": "Cliffside Crevice Refuge",
    "terrain": "indoor",
    "tags": ["refuge", "cliff", "crevice", "elevated", "sheltered"],
    "surface": "rough_stone",
    "descriptions": [
      "A narrow crack in the cliff widens into a sheltered resting pocket.",
      "The crevice is difficult to reach from below and protected from most of the wind."
    ]
  },
  {
    "name": "Tree Root Refuge",
    "terrain": "indoor",
    "tags": ["refuge", "roots", "tree", "burrow", "sheltered"],
    "surface": "roots",
    "descriptions": [
      "Interlocking roots create a dry pocket beneath the base of an old tree.",
      "Leaves and loose earth conceal a small refuge from rain and passing predators."
    ]
  },
  {
    "name": "Subterranean Nursery Garden",
    "terrain": "indoor",
    "tags": ["nursery", "cultivation", "fungus", "plants", "underground", "resource"],
    "surface": "rich_soil",
    "descriptions": [
      "Patches of moss and fungus grow beneath dim light from cracks overhead.",
      "The chamber is maintained as a living food source, with damp soil and carefully protected growth."
    ]
  },
  {
    "name": "Warm Vent Chamber",
    "terrain": "indoor",
    "tags": ["warmth", "vent", "resting", "thermal", "den", "resource"],
    "surface": "warm_stone",
    "descriptions": [
      "A natural vent warms the chamber with air rising from deep underground.",
      "Moss grows thick near the heat source, while the surrounding stone remains cool."
    ]
  },
  {
    "name": "Echo Chamber",
    "terrain": "indoor",
    "tags": ["communication", "echo", "cave", "social", "territory"],
    "surface": "bare_stone",
    "descriptions": [
      "A rounded chamber amplifies every call, growl, and movement into a deep echo.",
      "The stone walls carry sound far into the surrounding tunnels, making the space useful for signalling."
    ]
  },
  {
    "name": "Communal Grooming Pool",
    "terrain": "indoor",
    "tags": ["grooming", "water", "social", "cleaning", "communal"],
    "surface": "smooth_stone",
    "descriptions": [
      "A shallow pool is surrounded by smooth stone worn by repeated use.",
      "Fur, feathers, or shed scales collect around the water where the inhabitants clean themselves."
    ]
  },
  {
    "name": "Juvenile Training Ground",
    "terrain": "outdoor",
    "tags": ["young", "training", "play", "social", "territory"],
    "surface": "trampled_grass",
    "descriptions": [
      "The grass is flattened into a rough arena where young creatures practise movement and combat.",
      "Scattered sticks, scratches, and overlapping tracks mark repeated games and training bouts."
    ]
  },
  {
    "name": "Dominance Display Ground",
    "terrain": "outdoor",
    "tags": ["dominance", "display", "social", "territory", "mating"],
    "surface": "bare_earth",
    "descriptions": [
      "A clear patch of ground bears the scars of repeated contests and displays.",
      "Scrapes, broken branches, and scent marks identify a place where rank is established."
    ]
  },
  {
    "name": "Mating Chamber",
    "terrain": "indoor",
    "tags": ["mating", "breeding", "social", "sheltered", "animal_den"],
    "surface": "soft_moss",
    "descriptions": [
      "A secluded chamber is lined with fresh bedding and sheltered from disturbance.",
      "Scent marks and carefully cleared ground suggest a place used during courtship."
    ]
  },
  {
    "name": "Eggshell Disposal Site",
    "terrain": "outdoor",
    "tags": ["waste", "eggs", "breeding", "nest", "outdoor"],
    "surface": "gravel",
    "descriptions": [
      "Fragments of eggshell have accumulated away from the main nesting area.",
      "The scattered remains suggest recent hatching, with small tracks leading back toward shelter."
    ]
  },
  {
    "name": "Shed Antler and Horn Deposit",
    "terrain": "outdoor",
    "tags": ["antlers", "horns", "seasonal", "resource", "wildlife"],
    "surface": "dry_leaves",
    "descriptions": [
      "Shed antlers and broken horn fragments lie among the leaves at the edge of the clearing.",
      "The deposit is a seasonal reminder of the animals that frequent this part of the forest."
    ]
  },
  {
    "name": "Nest Material Collection Site",
    "terrain": "outdoor",
    "tags": ["nest_material", "foraging", "twigs", "leaves", "resource"],
    "surface": "forest_floor",
    "descriptions": [
      "Twigs, moss, grass, and soft fibres are gathered in a small pile near the den.",
      "Repeated trips have left a narrow trail through the vegetation to this useful supply."
    ]
  },
  {
    "name": "Burrow Excavation Front",
    "terrain": "indoor",
    "tags": ["excavation", "tunnel", "construction", "loose_soil", "den"],
    "surface": "loose_earth",
    "descriptions": [
      "Fresh earth piles up at the end of a tunnel still being extended.",
      "Raw claw marks and exposed roots show where excavation stopped most recently."
    ]
  },
  {
    "name": "Sealed Burrow Chamber",
    "terrain": "indoor",
    "tags": ["sealed", "burrow", "defensive", "hidden", "den"],
    "surface": "packed_earth",
    "descriptions": [
      "A wall of packed earth blocks access to a chamber beyond.",
      "The seal looks deliberate, concealing either a refuge, a cache, or something best left undisturbed."
    ]
  },
  {
    "name": "Ancient Den Core",
    "terrain": "indoor",
    "tags": ["ancient", "central", "den", "historical", "deep_chamber"],
    "surface": "worn_stone",
    "descriptions": [
      "The oldest chamber bears layers of claw marks, stains, and mineral deposits from generations of use.",
      "Its walls preserve traces of former inhabitants, long after their tracks disappeared."
    ]
  },
  {
    "name": "Sacred Beast Shrine",
    "terrain": "indoor",
    "tags": ["shrine", "sacred", "magical", "beast", "ritual", "den"],
    "surface": "carved_stone",
    "descriptions": [
      "Bones, flowers, and polished stones are arranged around a natural rock formation.",
      "The chamber is treated with unusual care, as though the inhabitants honour a guardian or ancestral spirit."
    ]
  },
  {
    "name": "Monster Transformation Chamber",
    "terrain": "indoor",
    "tags": ["transformation", "magical", "monster", "growth", "sheltered"],
    "surface": "black_stone",
    "descriptions": [
      "Deep grooves and strange residue mark the floor of a chamber used during a monstrous change.",
      "The air prickles with residual energy, and fragments of shed hide or shell cling to the walls."
    ]
  },
  {
    "name": "Monster Spawn Pool",
    "terrain": "indoor",
    "tags": ["spawning", "eggs", "breeding", "monster", "water", "protected"],
    "surface": "black_silt",
    "descriptions": [
      "A dark pool holds clusters of eggs or gelatinous spawn beneath the surface.",
      "The water is still and warm, with strange shapes moving among the submerged rocks."
    ]
  },
  {
    "name": "Predator Territory Core",
    "terrain": "outdoor",
    "tags": ["territory", "predator", "central", "scent_marking", "den"],
    "surface": "trampled_soil",
    "descriptions": [
      "Tracks from several approaches converge on a patch of ground claimed by a dominant predator.",
      "Scratches, scent marks, and remains of past kills make the boundaries unmistakable."
    ]
  },
  {
    "name": "Hidden Secondary Nest",
    "terrain": "indoor",
    "tags": ["nest", "secondary", "hidden", "backup", "breeding", "den"],
    "surface": "dry_grass",
    "descriptions": [
      "A small concealed hollow contains spare bedding and signs of occasional use.",
      "The nest is tucked away from the main chamber, ready as a refuge if the primary site is disturbed."
    ]
  },
  {
    "name": "Final Refuge Chamber",
    "terrain": "indoor",
    "tags": ["refuge", "defensive", "deep_chamber", "last_resort", "den"],
    "surface": "solid_rock",
    "descriptions": [
      "A deep chamber offers the final defensible retreat within the den.",
      "The entrance is narrow and the walls are thick, making the space difficult to reach without warning."
    ]
  }
]

def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r'[\s\-]+', '_', s)
    s = re.sub(r'[^a-z0-9_]', '', s)
    return s

def export_all():
    target_dir = os.path.join("data", "library", "biomes")
    os.makedirs(target_dir, exist_ok=True)
    created = 0
    updated = 0
    slugs = set()
    for entry in BIOMES_RAW:
        slug = slugify(entry["name"])
        if slug in slugs:
            print(f"DUPLICATE SLUG: {slug} for {entry['name']}")
        slugs.add(slug)
        filepath = os.path.join(target_dir, f"{slug}.json")
        is_update = os.path.exists(filepath)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)
        if is_update:
            updated += 1
        else:
            created += 1
    print(f"Total processed: {len(BIOMES_RAW)}")
    print(f"Created: {created}, Overwritten/Updated: {updated}")

if __name__ == "__main__":
    export_all()
