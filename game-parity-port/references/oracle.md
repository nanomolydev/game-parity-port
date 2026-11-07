# Phases 1-3: building the oracle (any engine)

The oracle is the original game logic running under your control: headless, fixed timestep,
seeded, fed by scenario input, with every field readable each tick. This file is the generic
recipe; `engines/<engine>.md` says how each step looks for a specific engine or build type.

## Contents
1. Pick the oracle form
2. API inventory
3. Facade + shared engine layer
4. Frame loop semantics
5. World from the original data
6. Oracle report
7. Generic pitfalls

## 1. Pick the oracle form

| Form | When | What you can compare |
|---|---|---|
| **A. Original logic on a facade** | logic is bytecode/scripts: .NET/Mono, JVM, Lua, JS, Python, GDScript, GameMaker VM, Flash AS3 | every field of every object, and hybrid porting (port runs inside the oracle) |
| **B. Instrumented original** | logic is native (C/C++, IL2CPP, Unreal, Source...) but you can hook it (source, symbols, metadata, debugger) | every field you can locate by layout/reflection; port compared trace vs trace |
| **C. Emulated original** | console/retro game: an accurate emulator already runs it deterministically | RAM/registers per frame mapped to game variables; trace vs trace |
| **D. Observed original** | closed native binary, no symbols | observable state (positions, UI, audio events) per tick; weakest, still automatic |

Prefer the highest form you can reach. Form A is worth weeks of effort because it enables hybrid
porting: one class at a time, verified in place.

## 2. API inventory (form A and B)

List every engine/runtime member the game logic references, with its callers, generated from the
binary/bytecode metadata, never from guessing:
- managed bytecode: scan type and member references (and call sites in the method bodies);
- scripts: scan calls into the engine's binding table (globals, modules, native functions);
- native: imported symbols, vtables, reflection tables (Unreal UFUNCTIONs, IL2CPP metadata).

Output a table (JSON + markdown). It is the complete to-do list of the facade.

## 3. Facade + shared engine layer

- **Facade**: the engine API surface the original code links/calls against, generated from the real
  engine's signatures (names, overloads, versions, struct layouts). Every member starts as a stub
  that records "called, not implemented" with the calling game location and returns a default.
  Never throw from a stub: an exception hides the rest of the frame.
- **Engine layer**: one native implementation of engine behaviour (math, transforms/scene graph,
  physics, collision events, input, time, random, audio state, animation sampling, camera math)
  used by BOTH the facade and the port. Follow the original engine's formulas exactly (open
  reference sources exist for many: UnityCsReference, Godot source, Box2D, Bullet...), in the same
  float precision, same operation order, same RNG algorithm.
- Expose the engine layer through a C ABI; generate both sides of the bindings from one table and
  self-check struct layouts at startup.
- Third-party SDKs (Steam, Discord, analytics, voice, ads): stub them; run multiplayer games in their
  offline/local path, or loop the transport back locally.

## 4. Frame loop semantics

Reproduce the engine's frame order exactly; it decides which value a script sees. Write it down from
the engine documentation and verify with small probes. Typical elements: time update, fixed/physics
steps (with their own callbacks and collision events), input sampling point, per-frame update,
late update, timers/invokes, coroutines or async continuations and the points where they resume,
deferred destruction, object creation/activation callbacks and their order, script execution order
settings. Engine quirks matter (Unity's fake null, Godot's `_ready` order, GameMaker event order).

## 5. World from the original data

Load objects and their initial values from the shipped data files, never by re-typing values:
scene/level files, prefabs/templates, serialized fields, resource tables, string tables, meshes and
collision shapes. Use an existing extractor for the format (`engines/<engine>.md`). Apply values with
the engine's own deserialization rules (which fields are serialized, defaults, type conversions).
Properties whose stored shape differs from their API shape must be derived from the stored data, not
defaulted (for example a bitmask stored as `{bits: n}`).

If the game generates levels procedurally, replace only the layout step with the test scene and run
every other original setup step, in the original order.

## 6. Oracle report (after every run)

Machine-readable, sorted by frequency: unimplemented members (with game call sites), exceptions in
game callbacks (with source locations), data problems (unassigned fields, unknown component types,
missing references), named approximations, missing resources. Work it down to what the test scene
needs before porting anything. Approximations are listed, never silent.

## 7. Generic pitfalls

- Version mismatch between what the game expects and what the facade claims (assembly version,
  module version, API level): code runs but reads defaults, with no error.
- Struct field order or packing across the FFI.
- Hash maps with random seeds, wall-clock reads, thread scheduling: nondeterministic oracle.
- An expensive call inside a hot accessor (a full physics sync on every read): 10x slowdowns.
- A wrong spawn transform makes everything diverge for reasons unrelated to the code being ported:
  sanity-check the scene before trusting divergences.
- Visibility rules that are not where you expect them (the local player's body hidden by a
  shadow-only render mode, not by the camera mask).
