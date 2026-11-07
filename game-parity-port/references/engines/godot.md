# Godot (GDScript or C#)

Recognize: a `.pck` next to the executable (or embedded), `project.godot` inside it.
Extract with gdsdecomp (Godot RE Tools): scenes (`.tscn/.scn`), resources, scripts; compiled
GDScript bytecode (`.gdc`) decompiles back to readable GDScript. Note the exact engine version.

## GDScript: the real engine is the facade (form A, cheapest anywhere)

Godot is open source, so the oracle can be the same Godot version run headless (`--headless`,
`--fixed-fps 60`, `--write-movie`-style deterministic stepping or a fixed `physics_ticks_per_second`
and an autoload that drives frames). Add two autoloads:
- **scenario**: seeds `RandomNumberGenerator`/`seed()`, feeds `Input.parse_input_event` from the
  input timeline at exact physics frames;
- **trace**: after every physics frame walks the scene tree and dumps every script variable
  (`get_property_list()` with `PROPERTY_USAGE_SCRIPT_VARIABLE`) plus node transforms, keyed by node
  path (stable keys come for free).

The engine layer is the engine itself. If the port targets a different engine, either keep Godot's
physics (Godot Physics / Jolt) behind the port as the shared layer, or accept physics parity as a
separate approximate track.

## Hybrid porting

GDExtension classes (Rust via godot-rust, C++ via godot-cpp) can replace one script at a time on the
same node, so ported classes run inside the oracle exactly like the hybrid loop in `../porting-loop.md`.

## Godot C#

Assemblies run on .NET with GodotSharp; the same as Unity Mono in spirit, but the facade is the real
engine, so form A needs no shim at all.
