Ideas backlog. Each idea has a task file (2026-08-19) â€” work from the task file, not this list.

1. pack logic for simple npcs to allow nultiple of the same type to coordinate togehter via code. examples rats, wolfsand other such animals â€” task-294
2. select what item from the library to use as a template when doing sync from library or save to library â€” task-295
3. warn of missmatch between instanced entity and selected template from library â€” task-296
4. new triggers and conditions for using vitals readout as condition,getting vital readout as a message (example thermostat to see own core temp, hunger, conditions etc) â€” task-297
5. trigger effect to create a new item inside another on use, for example a camera taking a photo of a target, a voice recorder that can record what has been said in the area or trigger a random recording like evp device on use random chance to make a static noise or a spooky voice â€” task-298
6. triggers to allow long distance comunication. like phones, walkie talkies, radios? â€” task-299
7. allow me to change the scenario clock start time â€” task-300
8. default time per turn to be 1 minute instead of 5 â€” task-301
9. optimising: we got the new hide items unless clicking on parent but new addition is keep "siblings" open too. so click on area shows all items in that area, click on one of those items right now hides the other items again, but i want the items in the area to stay open. same for when we click a character, or a item with items inside it.  default to hide items on, not off. â€” task-302
10. hide areas with no characters, new toggle button. on click ways reveal areas. again a optimisation related task. â€” task-303
11. centralized config menu for alll constants like sound pen values, heat progigation, lightspill and any other values that would require code change to test and adjust minor changes. â€” task-304
12. warnon way missing cardinal, view from direction, descriptin, pasmessage â€” task-305
13. warn on emptry triggers (no effects or empty messages) â€” task-306
14. warn on having mecanics tag (insulation, weapon, clothing, etc) but no values set or missing equip slots for tags that should have it. â€” task-307
15.  condition to check if self has item in relationshop, or check if item has other tiem of a certain relatinship type, example if coat has item in, effect is param: pocket gets message "the pocket is buldging" else "the pockets are empty" â€” task-308
16.  make the ghost in mansion a invisible or ghost character? aka dead ghost? add traits liek undead? â€” task-309
17. when using random order in turn based, reroll the initiative list at end of turn. â€” task-310
18. in the initiative list, allow me to click the area name next to the agents. â€” task-311
19. graph search to hide non matches only showing the matches â€” task-312
20. mapping of forward, left, right and back to a character, like the suggested transit tag on areas, based on cardinal directins and origin ways. â€” task-313
21.     example: if you come from south, right is east, left is west etc. if you comef rom west, right is south, left is north. (same idea as 20)

Procedural population cluster (2026-08-21) â€” hub: task-9. Recommended order:
lint â†’ interests â†’ domain tags â†’ engines.

22. character interest-tag data pass: fill 7 empty + rewrite 5 dead lists + top up thin ones (full proposal table in task file), delete duplicate violet halloway file and empty `?` character â€” task-326
23. library lint script: dead interest tags, wearables missing equip_slots, tag case drift, singleton tags, broken contents refs, area tag coverage â€” task-323
24. domain tag convention (same tag on area + furniture + item) plus backfill: 35/58 areas lack tags, no `display` role tag exists yet â€” task-324
25. auto-dressing characters from interest tags: slot coverage rules, underwearâ†’outer layer order, weather/insulation gating â€” task-325
26. bug: spawn_item/spawn_character effects drifted from library data (ember uses regression, _hydrate_item drops triggers, lowercase arrival names) â€” bug-13
