# .NET games without Unity: XNA, FNA, MonoGame, custom .NET engines (form A)

Recognize: the game exe/dll is a .NET assembly (`file` / a PE with a CLI header), references
`Microsoft.Xna.Framework`, `FNA`, `MonoGame.Framework`, or the studio's own engine dll.

This is the friendliest case after Godot: the whole game, often including its engine, is bytecode.
- Decompile with ILSpy (with PDB generation, so reports can point to source lines).
- Oracle: load the game assemblies in your own .NET host; replace only the platform layer
  (graphics device, audio device, windowing, input devices) with a headless facade. XNA/FNA/MonoGame
  have a small, well-documented API; FNA is open source and is itself a good reference.
- `Game.IsFixedTimeStep = true`, `TargetElapsedTime` fixed; call `Tick()`/`Update(GameTime)` yourself
  with synthetic time; seed every `System.Random` the game creates (hook the constructor or patch
  with Harmony/MonoMod).
- Trace by reflection over the game's object graph from a few roots (the Game instance, scene/world
  lists, static singletons). Choose stable keys (entity ids, list paths), not object hash codes.
- Hybrid porting works exactly as in `../porting-loop.md`: route chosen methods to the port with
  Harmony/MonoMod detours instead of a custom player loop.
