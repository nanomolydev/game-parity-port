# Build manual: the parity testing core, step by step

This is the concrete procedure that produced a working oracle for a 3D Unity game (232 game
classes in the test scene, 26 million values compared per run, 0 false divergences). Follow the
steps in order. Each step lists what to build, how it works inside, how to verify it, and the bugs
that actually happened. Engine-specific details are in `engines/<engine>.md`; where this manual
says "for example (Unity)", translate to your engine using that file.

## Contents
- Step 0. Workspace layout
- Step 1. Recon and a readable copy of the original source
- Step 2. API inventory (generated)
- Step 3. Facade generator and stubs that report themselves
- Step 4. Host that loads the original code
- Step 5. Shared engine layer with a C ABI
- Step 6. The frame loop
- Step 7. The world from the original data
- Step 8. Level/scene setup without changing the original
- Step 9. Scenario input
- Step 10. The trace writer
- Step 11. The oracle report
- Step 12. Make the game actually play (liveness)
- Step 13. Comparator and the gate
- Step 14. More scenarios: fixed, bot-recorded, randomized
- Step 15. The port side and the hybrid bridge
- Step 16. Trace viewer
- Debugging playbook (real bugs and how they were found)
- Size and time expectations

---

## Step 0. Workspace layout

```
parity/
  RECON.md            answers of step 1, chosen oracle form, list of approximations
  apiscan/            step 2 tool          -> reports/api_usage.json
  facadegen/          step 3 tool          -> facade/Generated/...
  facade/             engine API surface: Generated/ (stubs) + Impl/ (hand implementations)
  oracle/             step 4 host + frame loop + scene builder + trace + report + harness
  scenarios/*.json    step 9
  data/               exported world data (step 7), game source for reading (step 1)
  reports/            oracle_<scenario>/trace.jsonl, report.json; compare_<scenario>/report.md
  check.sh            build + oracle + port + compare in one command
engine/               shared engine layer (step 5), used by the facade AND the port
port/                 the new implementation (step 15)
```

Keep extracted game data out of any public repository.

## Step 1. Recon and a readable copy of the original source

Do: answer the questions in `recon.md` into `parity/RECON.md`. Then produce a readable copy of the
game logic, used for reading only, never executed:
- .NET/Unity Mono: decompile `Assembly-CSharp.dll` with ILSpy (`ilspycmd -p -o parity/data/game/src
  --genpdb`). Generate the PDB: it maps IL offsets to lines of the decompiled files, so every report
  can say `PlayerController.cs:865`.
- Scripts: copy them; decompile bytecode (luac, `.rpyc`, `.gdc`) if needed.
- Native: Ghidra/IDA project with recovered names.

Verify: you can open the class that drives the player and read its update method.

## Step 2. API inventory (generated)

Build a small tool that reads the original binaries' metadata and lists every engine-side type and
member the game references, plus which game methods call each.

How (.NET): System.Reflection.Metadata over `Assembly-CSharp.dll` (+ firstpass/plugin dlls):
`TypeReferences` and `MemberReferences` whose resolution scope is an engine assembly (prefixes such as
`UnityEngine`, `Unity.`, `TMPro`, `Photon`, `Steamworks`, `Discord`), plus a pass over every method
body decoding `call/callvirt/newobj/ldfld/stfld/ldsfld` tokens to record callers. Output
`api_usage.json` (member key, signature, caller list) and a markdown summary.
Scripts: scan for calls into the engine binding table (global functions, module members).

Verify: the counts are plausible (hundreds of types, thousands of members for a 3D game) and the
list includes things you know the game uses (input, physics raycasts, time).

## Step 3. Facade generator and stubs that report themselves

Generate the engine API surface from the REAL engine binaries (load them with
`MetadataLoadContext`, or read the engine's documented API), restricted to the inventory:
- exact namespaces, type names, signatures, overloads, property getters/setters separately,
  explicit interface implementations, nested types, enums with real values, struct fields in the
  original declaration order;
- every member body is a stub: `Unimpl.Hit("UnityEngine.Rigidbody.get_velocity"); return default;`.
  `Unimpl.Hit` records the key, a hit count, and the first game caller (walk the stack trace to the
  first frame inside the game assembly; with the PDB you get file and line). Never throw from a stub.
- hand implementations go into separate files as `partial` members (or overrides in your language);
  re-run the generator after each batch, it skips members that are already implemented.
- pure data properties (a component's serialized settings) get a generic store: the initial value
  comes from the exported data (step 7), setters write to the store, getters read it.

Facade assemblies (.NET): CoreCLR binds by simple name and version. Emit one small assembly per
original engine assembly (same name, same AssemblyVersion as the original, read it from the file)
containing only `[TypeForwardedTo]` attributes into your facade assembly. Getting the version wrong
does not crash: a package simply fails to find its types and reads defaults (in the real port every
input read returned zero until the version was fixed).

Verify: the original game assembly loads and all its types resolve (step 4).

## Step 4. Host that loads the original code

A console program that:
1. creates an isolated load context whose resolver maps engine assembly names to the facade
   assemblies and game names to the ORIGINAL files;
2. loads the game assemblies, registers them for type lookup (the scene builder resolves component
   class names to types);
3. initializes the engine layer (step 5), loads the world (step 7), sets up the scenario (steps 8-9);
4. runs `for frame in 0..N: frame_loop.step(fixed_dt); trace.write(frame)`;
5. writes the report (step 11).

Options worth having from day one: `--scenario`, `--out`, `--frames`, `--seed`, `--port <lib>
--classes A,B` (hybrid, step 15), `--live <http port>`.

Third-party SDKs with native parts (Steam, Discord, voice) must be stubbed in the facade: their
finalizers crash the host on exit otherwise.

## Step 5. Shared engine layer with a C ABI

One native library (Rust in the reference port) implementing engine behaviour, used by the facade
through P/Invoke/FFI and linked directly by the port. Modules that were needed for one 3D room:

| module | contents |
|---|---|
| math | vectors, quaternion (Euler order, eulerAngles, Slerp, LookRotation, FromToRotation), Mathf, Color; formulas from the engine's reference source, f32, same operation order |
| world/transform | ids, parent/child, local/world TRS, lossyScale, TransformPoint/Direction, sibling order |
| curve/gradient | AnimationCurve evaluate (Hermite with weighted tangents, wrap modes), Gradient evaluate |
| random | the engine's algorithm (Unity: xorshift128 with its seeding, Range int/float rules, insideUnitSphere), Perlin noise |
| input | virtual devices (buttons, vec2 controls), actions, bindings, composites, press/release frames, per-frame delta reset |
| physics | bodies, colliders (box/sphere/capsule/mesh), layers and collision matrix, raycasts/overlaps/sweeps, triggers and contacts with the engine's conventions, joints, damping and gravity rules, forces applied at simulate |
| audio | per-source state (playing, time, volume, pitch, loop), one-shot voices for the trace |
| camera | projection, WorldToScreen/ScreenToWorld, ViewportPointToRay |

Rules learned the hard way:
- Generate the FFI declarations for both sides from ONE table; add an ABI self-check at startup
  (struct sizes, a round trip of a known quaternion). A struct emitted with fields in alphabetical
  order (w,x,y,z instead of x,y,z,w) rotated everything 180 degrees.
- Ordered containers everywhere (BTreeMap or insertion order). A hash map with a random seed made
  two oracle runs differ.
- Physics engine differences are real (rapier vs PhysX). Both oracle and port use YOUR physics, so
  game logic still compares exactly; list "physics engine" under approximations.
- Watch hot paths: one accessor that triggered a full physics sync made 300 frames take 32 s.

Verify: unit tests of the engine layer against known engine outputs (these unit tests are fine:
they test YOUR engine layer, not the game).

## Step 6. The frame loop

Reproduce the engine's frame order exactly. The Unity version that worked:

```
frame(dt):
  time += dt
  run Start for behaviours that are enabled and not started
  accumulate dt; while accumulator >= fixed_dt:
      FixedUpdate (all, in execution order)
      physics.simulate(fixed_dt); deliver trigger/collision messages
      resume coroutines waiting for WaitForFixedUpdate
  input.update()                       (Input System samples here)
  run Start again for behaviours created during fixed steps
  Update (all) ; Invoke/InvokeRepeating due ; coroutines (null, WaitForSeconds, nested)
  LateUpdate (all) ; coroutines waiting for WaitForEndOfFrame
  deferred Destroy ; engine end-of-frame (audio tick, input delta reset) ; frame_count += 1
```

Inside: a registry of behaviours with their sort key (execution order, then creation sequence); a
per-type cache of which message methods exist; activation rules (Awake + OnEnable when an object
becomes active, OnDisable when inactive, coroutines stop on deactivation); a coroutine runner with a
stack per routine (nested IEnumerators, waiting on another coroutine, custom yield instructions);
exceptions inside a callback are recorded with location and the loop continues (Unity behaviour).
Engine quirks to reproduce: fake null for destroyed objects, `" (Clone)"` suffix on instantiate,
collision messages sent to disabled scripts too.

Verify with tiny probe scripts if needed, then with the real game in step 12.

## Step 7. The world from the original data

Export the scene(s) and the templates (prefabs) the test scene needs from the shipped files:
- Unity: UnityPy + type trees generated from the Managed dlls (builds strip them; TypeTreeGenerator;
  if it fails on a missing assembly, create an empty stub assembly with that name). Resolve
  cross-file references via the externals table.
- Export format that worked: `objects: {gid: {type, name, components: [gid], fields: {...}}}`, assets
  separately, meshes into one binary blob with offsets, follow template references a few levels,
  plus every `Resources.Load` path the game asks for (collect them from the report of step 11).
- Building: create objects and components in file order, assign serialized fields with the engine's
  serializer rules (which fields are serialized, type conversions for vectors, colors, curves,
  references, arrays, nested serializable classes), then activate in the engine's order.
- Native component properties whose stored shape differs from their API shape must be derived from
  the data, never defaulted. Real examples: camera layer mask stored as `{m_Bits}`, audio spatial
  blend stored as a curve's first key, light shadow type nested in a struct. A wrong default here
  changed what the game saw (the camera rendered everything, 3D sounds became 2D).
- Instantiate = deep clone of a template with the same rules, then activation.

Verify: object counts match the data; spot-check a few serialized values on live objects.

## Step 8. Level/scene setup without changing the original

If the game builds levels procedurally, do NOT re-implement the generator. Replace only the step
that decides the layout (spawn the test room/items yourself at the positions the generator would
use) and call every other original setup method in its original order, with the waits it uses
(the reference harness: wait 0.4 s, EnvironmentDirector.Setup, PostProcessing.Setup, LevelMusic.Setup,
ConstantMusic.Setup, wait until the player list exists, PlayerSpawn, GenerateDone). Put these steps
in the scenario file so they are data.

## Step 9. Scenario input

A JSON timeline of control states per frame (`scenarios.md`), applied at the exact point of the frame
where the engine samples input (step 6). Keep the oracle and the port reading the same file through
the same input code (the engine layer's input module).

## Step 10. The trace writer

After every frame:
- walk every live object of the game's own types (Unity: every MonoBehaviour from the game
  assemblies) and read EVERY instance field by reflection, public and private, declared in the game
  type and its game base types;
- add engine state under `$` names: `$pos`, `$rot`, `$scale`, `$active`, `$enabled`, rigidbody
  `$vel`/`$angVel`, animator state, audio voices started this frame (clip, source, volume, pitch);
- convert values: floats with the shortest round-trip format, vectors/quaternions/colors as arrays,
  enums as numbers, object references as stable keys (or null; destroyed counts as null),
  collections as arrays of converted values, nested serializable structs as objects;
- write only values that changed since the previous frame (`set`), objects that disappeared (`del`),
  and metadata the first time an object appears (`new`: class, name, owning object).

Stable keys: the object's id in the exported data (`level0:1360`); the n-th instance of a template
`tpl:<template gid>@<n>`; children of an instance `<template child gid>@<n>`. Never memory addresses,
hash codes or a global creation counter.

Verify: a 300-frame run of a 3D scene gave about 5 million compared values and a 26 MB file;
`trace_compare.py run1 run1` reports 0; spot-check that the player's position field changes while
the scenario holds the forward key.

## Step 11. The oracle report

Write `report.json` after every run and print a summary:
- unimplemented members: key, hits, first game caller with file:line and the code line;
- exceptions inside game callbacks: where, message, count, file:line;
- data: fields assigned, unmatched, failed conversions, unknown component types, missing references,
  template references not exported;
- approximations: named and counted (for example "NavMesh.SamplePosition: floor raycast");
- missing resources (paths `Resources.Load` asked for), accumulated into an export wish-list.

Then implement in order of what blocks the test scene. Do not chase the whole list.

## Step 12. Make the game actually play (liveness)

The oracle is useless if the game sits in a menu, a loading screen or an exception loop. Read the
trace and confirm, with numbers, that the scenario's actions happened. In the reference port:
- the game director reached state `Main` around frame 45 (before the fix it was stuck in `Start`
  because an audio snapshot asset type was not mapped);
- holding forward moved the player (`$pos` z decreased), sprint drained stamina 40 to 26.4, the jump
  reached an apex of about 1.2 m, crouch toggled the crouch flag;
- the bot grabbed the vase at frame 185, the cart counted it (`itemsInCartCount` 1, haul 100) at 260.

Write these as a short checklist in RECON.md and re-check them after oracle changes. A field that
never changes during a scenario that should change it is a red flag.

## Step 13. Comparator and the gate

Use `scripts/trace_compare.py` and pass `scripts/gate_check.py` (two oracle runs identical, a planted
change caught, trace substantial and alive). Only then port.

## Step 14. More scenarios

Fixed scenarios per mechanic; a bot that runs on the oracle only, steering by reading oracle state,
whose produced input is saved and replayed as a plain scenario (check replay == bot run once);
randomized scenarios with a fresh seed every check (`scripts/fuzz_scenario.py`). Details in
`scenarios.md`.

## Step 15. The port side and the hybrid bridge

`porting-loop.md`. In short: the port is a shared library; the oracle routes chosen classes'
callbacks to it; the port reads and writes the live original objects through a host function table
(get/set field, invoke, statics), through wrappers generated from the original metadata; the same
trace writer records the hybrid run; compare hybrid vs oracle.

## Step 16. Trace viewer

A small web page that loads two traces and the exported meshes, replays them in 3D (original grey,
port red only where it diverges), lists the first divergences and shows every field of the selected
object per frame. People and models trust what they can see; it also finds "the player spawned
outside the room" in seconds.

---

## Debugging playbook (real bugs and how they were found)

| Symptom | Cause | How it was found |
|---|---|---|
| all input reads 0, no errors | facade assembly version 0.0.0.0 instead of the original 1.14.2.0 | the input package's own type lookup failed silently; compared the referenced version in metadata |
| everything rotated 180 degrees | quaternion fields crossed the FFI in alphabetical order | ABI self-check with a known quaternion |
| player falls through the floor | spawn position computed with the broken quaternion, outside the room | `--diag`: raycast down from the spawn, list floors with their bounds |
| game stuck before gameplay | an asset type alias missing (`AudioMixerSnapshotController` vs `AudioMixerSnapshot`) so a director's Start threw | the report's exceptions list with file:line |
| two oracle runs differ | hash map with random seed in the engine layer | determinism check of the gate |
| 300 frames in 32 s | an accessor triggered a full physics sync | profiling the host |
| bot cannot find the cart | instantiated objects are named `"X (Clone)"` | reading the object names in the trace |
| real divergences hidden | comparator tolerance 1e-4 | negative control with a planted 1e-6 change |
| `inf` fields reported as divergent | `inf - inf = NaN` in the comparator | first divergence list showed identical values |
| first-person view filled by the own head | local body rendered with shadow-only mode, not hidden by the camera mask | a "closest renderers to the camera" debug endpoint |

## Size and time expectations

For the reference 3D game: inventory 432 types / 753 members; the facade took the most time; a first
running oracle with the game reaching gameplay took several focused sessions; logic per frame about
2 ms, a 1500-frame scenario about 20 s including load. For a small 2D or script-based game the same
steps are a fraction of that, but none of them is skipped.
