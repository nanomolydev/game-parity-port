# GameMaker (GML)

Recognize: `data.win` (Windows), `game.ios`/`game.droid`/`game.unx` next to the runner.
Two build types: **VM** (GML compiled to bytecode inside `data.win`) and **YYC** (GML compiled to
native C++).

- VM builds (form A): UndertaleModTool reads and decompiles `data.win` (rooms, objects, events,
  scripts, sprites, sounds). An open GML VM / runner reimplementation, or a headless build of an
  open-source runner, executes the original bytecode; the inventory is the set of built-in functions
  the bytecode calls. Reproduce the event order exactly (Begin Step, Alarm, Step, collision events,
  End Step, Draw...) and the instance creation/destroy rules.
- YYC builds: form B (instrumented original) or D; the decompiler cannot recover GML.
- Determinism: `random_set_seed`, `randomize()` patched, fixed `room_speed`/`game_set_speed`,
  `current_time`/`get_timer` patched to scenario time.
- Trace: every instance's variables per step, keyed by instance id (stable within a scenario) and
  object name.
