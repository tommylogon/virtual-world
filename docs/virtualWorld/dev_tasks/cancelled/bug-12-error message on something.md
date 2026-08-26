# Bug 12: 

INFO:werkzeug:127.0.0.1 - - [26/Jul/2026 00:25:33] "GET /api/library/traits HTTP/1.1" 200 -
ERROR:routes.action:Unexpected error in /api/action
Traceback (most recent call last):
  File "C:\Projects\code\virtual_world\routes\action.py", line 257, in take_action
    add_output(world.equip_item(rest))
               ~~~~~~~~~~~~~~~~^^^^^^
  File "C:\Projects\code\virtual_world\virtual_world_engine.py", line 405, in equip_item
    return self.equipment.equip_item(item_name, slot, under)
           ~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Projects\code\virtual_world\engine\equipment.py", line 131, in equip_item
    trigger_outputs = self.triggers.execute_triggers(item_node, "on_equip")
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'TriggerSystem' object has no attribute 'execute_triggers'
INFO:werkzeug:127.0.0.1 - - [26/Jul/2026 00:25:39] "POST /api/action HTTP/1.1" 500 -
INFO:werkzeug:127.0.0.1 - - [26/Jul/2026 00:25:40] "GET /api/state HTTP/1.1" 200 -
INFO:werkzeug:127.0.0.1 - - [26/Jul/2026 00:25:40] "GET /api/graph/nodes HTTP/1.1" 200 -
INFO:werkzeug:127.0.0.1 - - [26/Jul/2026 00:25:40] "GET /api/graph/edges HTTP/1.1" 200 -
INFO:werkzeug:127.0.0.1 - - [26/Jul/2026 00:25:40] "GET /api/library/traits HTTP/1.1" 200 -
ERROR:routes.action:Unexpected error in /api/action
Traceback (most recent call last):
  File "C:\Projects\code\virtual_world\routes\action.py", line 257, in take_action
    add_output(world.equip_item(rest))
               ~~~~~~~~~~~~~~~~^^^^^^
  File "C:\Projects\code\virtual_world\virtual_world_engine.py", line 405, in equip_item
    return self.equipment.equip_item(item_name, slot, under)
           ~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Projects\code\virtual_world\engine\equipment.py", line 131, in equip_item
    trigger_outputs = self.triggers.execute_triggers(item_node, "on_equip")
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'TriggerSystem' object has no attribute 'execute_triggers'
INFO:werkzeug:127.0.0.1 - - [26/Jul/2026 00:25:43] "POST /api/action HTTP/1.1" 500 -
INFO:werkzeug:127.0.0.1 - - [26/Jul/2026 00:25:43] "GET /api/state HTTP/1.1" 200 -
INFO:werkzeug:127.0.0.1 - - [26/Jul/2026 00:25:44] "GET /api/graph/nodes HTTP/1.1" 200 -
INFO:werkzeug:127.0.0.1 - - [26/Jul/2026 00:25:44] "GET /api/graph/edges HTTP/1.1" 200 -
