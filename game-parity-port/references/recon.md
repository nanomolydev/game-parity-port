# Phase 0: recon

Goal: decide which oracle strategy is possible before writing any code. Spend an hour here; it
saves weeks.

## Questions to answer (write the answers into the project README)

1. **Engine and exact version.** Unity: `strings -n 8 <Game>_Data/globalgamemanagers | grep -m1 -E '^20[0-9]{2}\.'`.
   Godot: the `.pck` header / executable version string. Unreal: `Engine/Binaries` and the
   `.uproject` / pak version. Custom: look for script files, a VM, or a big native exe.
2. **Where the game logic lives and in what form.**
   - Unity Mono: `<Game>_Data/Managed/Assembly-CSharp.dll` (+ `-firstpass`). Readable IL. Best case.
   - Unity IL2CPP: `GameAssembly.dll` + `global-metadata.dat`. Logic is native code; see `other-engines.md`.
   - Godot: GDScript/C# inside the `.pck`.
   - Java: jars. Lua/JS/Python engines: script files, often in an archive.
   - Native C/C++: only the binary. Oracle = instrumented original (see `other-engines.md`).
3. **Native plugins** (`Plugins/`, `*.dll`/`*.so` next to the exe): Steam, Discord, voice, video,
   physics. Each one needs a stub or an engine-layer implementation in the oracle.
4. **Networking stack** (Photon, Mirror, Netcode, Steam P2P, custom). In the oracle you almost always
   run offline / single player; make sure the game supports an offline path or stub the transport so
   that calls loop back locally.
5. **Physics engine** (PhysX in Unity, Jolt/Godot physics, Box2D, custom). If the port uses a
   different physics library, physics-driven fields will diverge. Decide early: either implement the
   physics in the shared engine layer (both sides use it, so game logic still compares exactly), or
   accept that physics parity is a separate, approximate track.
6. **Asset format** and an extraction tool: Unity (UnityPy, AssetRipper, AssetStudio), Godot
   (`.pck` explorers), Unreal (pak tools). You need serialized field values, not just meshes.
7. **Shaders/graphics API** in the build (Unity: DXBC for D3D11, SPIR-V for Vulkan, MSL for Metal).
   This decides the renderer track later; it does not block logic parity.

## Decide the oracle strategy

| Situation | Oracle |
|---|---|
| Logic in managed bytecode (Mono, .NET, Java, Lua, GDScript) | Run the original bytecode headless on an engine facade (best: full field access) |
| Logic native (IL2CPP, C++) but debuggable | Instrumented original: hook the frame loop, dump fields via known offsets / metadata |
| Only a closed native binary, no symbols | Record/replay of observable state (positions, UI, audio events) from the running original; weaker, but still per-tick |

Write down what will be approximate from day one (for example "physics: rapier instead of PhysX").
Every approximation must be listed in the oracle report, never silent.

## Pick the test scene

A small, concrete scene that exercises the core loop of the game (for example: one room, the player,
one pickup item, one container that counts items). Port and verify that scene end to end before
widening. Define it in words with the user: what must look, sound and behave identical.
