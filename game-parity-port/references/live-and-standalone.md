# Phase 7: live play and the standalone runtime

## Live play of the hybrid (cheap, early, motivating)

Add a `--live <port>` mode to the oracle: after the scenario setup, instead of a fixed frame count,
serve a tiny HTTP endpoint. A browser page posts held controls (Input System paths from
`KeyboardEvent.code`, mouse buttons) and the pointer-locked mouse delta; the server advances whole
fixed-length frames to follow wall-clock time (cap the catch-up, e.g. 5 frames per request) and
answers with what the main camera sees: visible renderers (mesh id, world matrix, material color),
lights, camera pose and FOV, a few HUD values. The page draws them with three.js (mirror Z once for
Unity's left-handed space; the Unity camera looks down +Z).

Lessons:
- Send mesh definitions per client ("have N meshes" in the request), never "once globally": a probe
  request or a page reload otherwise gets positions without geometry and shows a black screen.
- Respect the game's own visibility rules: camera culling mask from the real data, and skip
  `ShadowsOnly` renderers (that is how first-person games hide the local body).
- Keep the light pool fixed size (shader recompiles on count change), pixel ratio 1, cheap
  materials; label the page as a debug view, not the game's renderer.
- Add a `/near` debug endpoint (closest visible renderers with names, layers, distances); it finds
  "what is in front of my eyes" in one request.

## Standalone runtime (the actual goal: no original code at runtime)

Implement the same host function table natively in the new language:
- object store (objects, classes, fields) loaded from the same exported scene data;
- class defaults: field initializers live in the original constructors; dump them once from the
  oracle as data (instantiate each class, record every field) instead of re-typing them;
- the player loop, coroutines, invokes and messages, ported from the oracle's loop;
- engine members dispatched straight to the engine layer; game methods dispatched to the ported
  functions (so non-message methods need registry entries too);
- every call to something not ported yet is recorded and reported like the oracle's `Unimpl`.

Because the ported code only talks to the host table, it runs unchanged in both modes. The
standalone run writes the same trace format, and the comparator checks it against the oracle. The
"not ported yet" list from standalone runs is the remaining work queue.

## Renderer and audio (separate tracks)

Do them after logic parity of the test scene. Compare render inputs (see trace-and-compare.md), not
pixels. Shaders from a Windows build are usually DXBC; a workable route is DXBC -> SPIR-V
(vkd3d-shader) -> the target (naga, SPIRV-Cross to MSL/GLSL). Built-in engine shaders often have
public source and are easier to rebuild than to translate.
