"""Single source of truth for the VirtualWorld app version.

Written into every save's ``_save_metadata`` and shown in the save/load modal
so a save can be compared against the app that created it.
"""

APP_VERSION = "1.3.0"

# Format version of the save/scenario *payload* — distinct from APP_VERSION,
# which is the build that wrote it. Bump only on a breaking payload change and
# register a migration in engine/schema.py.
#
#   1: pre-bladder-flip. Bladder vital stored 100 = empty, 0 = full.
#   2: current. Bladder inverted to 0 = empty, 100 = full.
SCHEMA_VERSION = 2
