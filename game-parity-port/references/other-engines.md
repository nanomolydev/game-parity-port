# Other engines and build types

The phases stay the same: inventory the engine API the game uses, run the original logic against a
facade over a shared engine layer, trace every field every tick, compare exactly. What changes is
how the original logic is made to run and how its state is read.

## Unity IL2CPP

Logic is AOT-compiled into `GameAssembly.dll`; `global-metadata.dat` still has type, field and method
metadata. Il2CppDumper / Cpp2IL recover class layouts and method addresses.
- Oracle option A (preferred): instrumented original. Run the real game (offline, fixed timestep:
  `Time.captureDeltaTime`, vsync off), inject a hook at the end of each frame that walks live objects
  and dumps fields using the recovered layouts, and feeds scenario input through the input system.
  Record traces; you lose "run the port inside the oracle", so verification is trace vs trace with
  the same input timeline and seed.
- Option B: Cpp2IL can sometimes produce IL stubs; useful for reading logic, not for running it.

## Godot

- GDScript: the scripts are in the `.pck` (sometimes as bytecode; decompilers exist). Run them in a
  headless Godot of the same version (`--headless`), with a scenario autoload that feeds input and a
  trace autoload that walks the scene tree and dumps every script variable each physics frame.
  The port (Rust via GDExtension, or a standalone engine) is compared trace vs trace; a hybrid is
  possible with GDExtension classes replacing scripts one at a time.
- Godot C#: like Unity Mono; the assemblies run on .NET, the GodotSharp API is the facade.

## Java (LWJGL, libGDX, custom)

Jars run as is on the JVM. Replace the native layer (LWJGL/OpenGL/OpenAL) with headless stubs, drive
the game loop with a fixed tick, and dump fields by reflection (or a Java agent). Hybrid porting
works through JNI/Panama in the same way as the .NET bridge.

## Lua / JavaScript / Python scripted engines

The script VM is the oracle host: embed the same VM version, implement the engine's script API
(the bindings table is the inventory), run the original scripts, dump globals and object tables
each tick. Hybrid: replace one script module at a time with the port behind the same API.

## Native C/C++ games

No bytecode to run on a facade. Options, from strongest to weakest:
1. Source available (open-source games, your own game): compile the original with a trace hook in
   the main loop and a fixed timestep; it is the oracle.
2. Binary with symbols: hook the frame function (Frida, a DLL proxy), read structs at known offsets.
3. No symbols: record observable state (positions, animation states, UI text, audio events) via
   memory scanning or engine debug features. Weaker, but still per-tick and automatic.

## Unreal

Blueprint and C++ gameplay are native in shipping builds. Use the instrumented-original route:
run with `-nullrhi -unattended`, fixed timestep (`-benchmark -fps=50` or a custom
`FApp::SetFixedDeltaTime`), a plugin or injected module that iterates actors/components each tick
and dumps reflected UPROPERTYs (the reflection data is in the build). Verification is trace vs trace.

## Determinism checklist (any engine)

Fixed timestep, seeded RNG with the original algorithm, no wall-clock reads (patch them to scenario
time), single-threaded game logic or deterministic job ordering, ordered containers in your code,
floats in the same precision as the original (f32 vs f64 matters), same transcendental functions
(sin/cos in double then cast, as the original runtime does).
