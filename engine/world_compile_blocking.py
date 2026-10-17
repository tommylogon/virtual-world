BLOCKED_WAY_PERCENT = 12

#: What a blocked way reads as, keyed by the terrain class either side of it
#: (:func:`terrain_class`). Prose is a full sentence because it is what the
#: refusal and the description both quote - a blocked way must say *why*, or the
#: character meets a wall of nothing.
#:
#: Keyed by terrain class rather than by biome id so a new biome joins by
#: declaring its terrain. `road` is its own class (:func:`terrain_class` returns
#: it for a road cell) and gets the one blocker a road plausibly has.
BLOCKERS_BY_TERRAIN: Dict[str, List[Tuple[str, str]]] = {
    "woods": [
        ("fallen_tree", "A fallen tree has come down across the path, its roots "
                        "shearing a whole section of ground up with it."),
        ("thicket", "A thicket of bramble has swallowed the way through, green "
                    "and interwoven as if it had been planted."),
        ("deadfall", "Years of deadfall lie across the ground here, layered deep "
                     "enough that nothing has walked through since."),
    ],
    "rock": [
        ("rockslide", "A rockslide has come down from above, the scree still "
                     "loose underfoot where the whole face let go."),
        ("boulder", "A boulder the size of a cottage has rolled to a stop across "
                    "the way, bedded into the ground and not going anywhere."),
    ],
    "water": [
        ("flood", "Floodwater has cut a channel here and left it ankle-deep and "
                  "brown, drifting fast enough to carry a careless boot."),
        ("washout", "The ground has washed out from under the path, leaving a "
                    "gap you can see the bottom of."),
    ],
    "cultivated": [
        ("fence_down", "A stretch of field fence has come down across the way, "
                       "rails and wire in a tangle in the weeds."),
        ("ditch", "An irrigation ditch has opened along the track and the water "
                  "is far too deep to step across."),
    ],
    "road": [
        ("washout", "The road has washed out here, the surface broken away into "
                    "a channel of mud and loose stone."),
        ("fallen_tree", "A tree has come down across the road and taken a length "
                        "of the verge with it."),
    ],
    "open": [
        ("bramble", "Bramble is grown thick across the way, interwoven and "
                    "unwilling to be pushed through."),
        ("trench", "A trench has been cut across the way, deep and straight, and "
                   "long since filled with standing water."),
    ],
}

#: The blocker used when a way's terrain is unknown, so a blocker is always
#: nameable. `open`'s first entry, deliberately.
DEFAULT_BLOCKER = ("bramble", BLOCKERS_BY_TERRAIN["open"][0][1])

