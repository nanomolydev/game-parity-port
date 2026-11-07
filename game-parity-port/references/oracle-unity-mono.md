# Phases 1-3 for Unity (Mono): running the original Assembly-CSharp.dll as the oracle

Worked design from a real port (Unity 2022.3, Mono, PhysX, Photon). Adapt names to the project.

## Contents
1. Layout
2. API inventory (complete, generated)
3. Facade assemblies and the shim
4. The shared engine layer (native, C ABI)
5. Player loop semantics
6. Scene and prefabs from the original assets
7. Oracle report
8. Pitfalls that cost days

## 1. Layout

```
oracle/        .NET host: loads the original dlls in an AssemblyLoadContext, runs scenarios
shim/          UnityEngine API surface (generated stubs + hand implementations as partials)
facades/       generated assemblies named UnityEngine.CoreModule etc. that TypeForward into the shim
apiscan/       metadata scanner: every engine member the game references
shimgen/       generator: stubs for every referenced member, from the REAL engine dlls' metadata
engine/        native engine layer (Rust here), C ABI, used by the shim through P/Invoke
assetdump/     asset export (UnityPy + generated type trees) -> scene JSON + mesh blob
```

## 2. API inventory

Scan `Assembly-CSharp.dll` (+ firstpass and any game-side plugin dlls) with System.Reflection.Metadata:
every TypeReference and MemberReference whose assembly is engine-side (UnityEngine*, Unity.*,
Photon*, Steamworks, Discord, TMPro...), plus which game methods call each one (scan IL for call
tokens). Output a table (JSON + markdown). This is the to-do list of the shim and it is complete by
construction; never guess which APIs matter.

## 3. Facades and the shim

- Generate C# stubs for every referenced member from the real engine dll metadata (signatures,
  property getter/setter separately, explicit interface members, struct fields in metadata-token
  order). Each stub body calls `Unimpl.Hit("Type.Member")` which records the key, hit count and the
  calling game file:line, then returns a default. Never throw from a stub: a thrown exception aborts
  the frame and hides everything after it.
- Hand implementations live in separate `partial` files; regenerate stubs after each batch (the
  generator skips implemented members).
- CoreCLR binds by assembly simple name and version. Generate facade assemblies with the REAL names
  and the REAL AssemblyVersion (read it from the original dll) that `[TypeForwardedTo]` into the shim.
  A facade with version 0.0.0.0 can silently break a package (example: the Input System looked for
  1.14.2.0 and every input read returned zero, with no error).
- Load the game in a custom AssemblyLoadContext that resolves engine names to facades and game
  names to the original files.
- Third-party native SDKs (Steam, Discord, voice): stub them in the shim. Native finalizers in those
  SDKs crash the host on shutdown otherwise.

## 4. Engine layer (shared by oracle and port)

Implement Unity-native behaviour once, natively, behind a C ABI. The shim P/Invokes it; the port
links it directly. Typical modules:

- math: Vector2/3/4, Quaternion (Euler order ZXY, eulerAngles, Slerp, LookRotation...), Mathf.
  Follow the open UnityCsReference formulas exactly, in float (f32), same operation order.
- transforms: hierarchy, local/world, lossyScale, dirty flags.
- curves (AnimationCurve evaluate with weighted tangents), Gradient, random (Unity's xorshift128,
  `Random.Range` int/float rules, `insideUnitSphere`...), Perlin noise.
- input: Input System actions, bindings, composites (2DVector), press phases, per-frame deltas;
  devices are virtual and fed by scenarios.
- physics: rigidbodies, colliders, layers matrix, triggers, contacts with Unity's normal and
  relative-velocity conventions, damping as `v *= 1 - c*dt`, forces applied at simulate,
  `autoSyncTransforms=false` semantics, maxAngularVelocity, IgnoreCollision, joints.
- audio state (play/stop/time/volume per source, one-shot voices), camera projections.

Generate the FFI bindings (C# P/Invoke + Rust externs) from one table. Add an ABI self-check at
startup: struct sizes and a round trip of a known Quaternion. (A real bug: Quaternion fields emitted
alphabetically w,x,y,z instead of x,y,z,w rotated everything 180 degrees through the FFI.)

Use ordered maps (BTreeMap) or insertion-ordered structures everywhere in the engine. Hash maps with
random seeds made the oracle nondeterministic between runs.

## 5. Player loop semantics (reproduce exactly)

Per frame: time update -> Start for new behaviours -> fixed steps (FixedUpdate, physics simulate,
collision/trigger messages, WaitForFixedUpdate coroutines) -> input update -> Start -> Update ->
Invoke/InvokeRepeating -> coroutines (null, WaitForSeconds) -> LateUpdate -> WaitForEndOfFrame ->
deferred Destroy -> end of frame. Script execution order from the project settings.

Also: fake null (`destroyed == null` is true), `name + " (Clone)"` on Instantiate, Awake/OnEnable on
activation order, OnDisable on deactivation, coroutines stop when the GameObject is deactivated,
collision messages are delivered to disabled scripts too, Start runs once before the first Update
even for objects created mid-frame.

## 6. Scene and prefabs from the original assets

- Export with UnityPy. Builds strip type trees; generate them from the Managed dlls (TypeTreeGenerator).
  If generation fails on a missing assembly (example: `SingularityGroup.HotReload.Runtime`), create
  an empty stub assembly with that name.
- Resolve PPtrs across files via the externals table (script pointers often point into
  globalgamemanagers.assets).
- Export: GameObjects, components with all serialized fields, prefabs reachable from the scene
  (follow prefab refs a few levels), `Resources/` paths the game loads, mesh geometry into a binary
  blob with offsets.
- Apply serialized values with Unity serializer rules (public or [SerializeField], not
  [NonSerialized], supported types). Fields whose serialized shape differs from the property must be
  derived from the real data, not defaulted. Real examples: `Camera.cullingMask` from
  `m_CullingMask.m_Bits`, `AudioSource.spatialBlend` from `panLevelCustomCurve` key 0,
  `Light.shadows` from `m_Shadows.m_Type`. A default there silently changes what the game sees.
- Level generation: if the game builds levels procedurally, replace only the layout step with the
  test scene, and call every other original setup step in its original order.

## 7. Oracle report (after every run)

`report.json` with: unimplemented members (key, hits, game file:line, code line), exceptions in game
callbacks (file:line), data problems (unassigned fields, unknown component types, missing refs),
approximations (named, counted), missing Resources paths. Work the report down to what the test
scene needs before porting anything.

## 8. Pitfalls that cost days

- Facade assembly version mismatch: package code runs but reads defaults (input dead, no error).
- Struct field order across FFI (Quaternion w,x,y,z vs x,y,z,w).
- Nondeterministic containers in the engine layer.
- A diagnostic that triggers a full physics sync on every attachedRigidbody read: 10x slowdown.
- Spawn positions computed with a broken quaternion: the player falls through the floor and every
  later field diverges for a reason unrelated to the code being ported.
- Comparator tolerance 1e-4 hid real divergences; `inf - inf = NaN` was reported as a divergence.
- Rendering only by layer mask: the local player's own head filled the screen, because the game
  hides it with `shadowCastingMode = ShadowsOnly`, not with the camera mask.
