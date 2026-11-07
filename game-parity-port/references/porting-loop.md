# Phase 6: hybrid porting loop

The port is not tested in a separate program. Ported classes run **inside the oracle**: for those
classes the player loop calls the new-language implementation instead of the original method, on
the live objects; every other class keeps running the original. So a class can be verified alone,
the moment it is written.

## The bridge

- The new-language side is a shared library exporting:
  `init(host_api)`, `ported_count/ported_get(i)` (names like `"PlayerController.FixedUpdate"`),
  `call(entry, this, arg)`, `coroutine_resume(id, this, out)`, `coroutine_drop(id)`, `last_panic`.
- The host passes a function table: `get_field`, `set_field`, `get_static`, `set_static`,
  `invoke(obj, type, method, args)`, string read/new, `last_error`. Values cross as a small tagged
  union (null, bool, int, float, double, string handle, vec2/3/4, quaternion, color, object handle,
  enum).
- Object handles are valid for the outermost call only. Clear the handle table when the outermost
  call returns, not on nested calls (port -> original -> port), or nested calls corrupt the outer one.
- Route Unity messages with an argument (OnCollisionEnter(Collision), OnTriggerEnter(Collider)) as
  well as plain ones; collision messages are a big part of gameplay.
- Coroutines: the port implements a state machine (one state per `yield return`) and starts it
  through the host, which wraps it in an IEnumerator calling `coroutine_resume`. The state machine
  must not keep object handles between steps; the owner is passed in again on each step.
- Overload resolution in `invoke`: skip generic method definitions; prefer exact tag matches.
- Panics in the port surface as recorded exceptions with the message, not as crashes.

## Typed wrappers (generated)

Generate wrappers for every game and engine type from the real metadata, with the original names:
`PlayerController::instance(w).EnergyCurrent(w)`, `this.set_JumpImpulse(w, true)`,
`Time::get_fixedDeltaTime(w)`, enums as `GameDirector_gameState::Main` with the real underlying
values. A porting model then writes code that reads almost like the original, and the compiler
catches typos in names.

## The loop for one class

1. Read the whole original class.
2. Write the port, one function per message, same order, same float operation order.
3. Register the entries.
4. Run the check script on every fixed scenario and N fresh random ones, with the full list of
   ported classes.
5. Read the first divergence: frame, class.field, oracle vs port value, assigning source lines. Fix
   the port. Repeat.

Big classes: port one message at a time (`--port PhysGrabber.Update`); the registry accepts
`Class.Method`.

## Ordering

Start with leaves the player feels (camera, movement), then the core mechanic of the test scene,
then visuals/HUD/audio logic, and the global managers/directors last (they touch everything and are
easiest when their callees are already ported). Keep a roadmap file with the ordered queue and what
is not suitable for a small model (bridge/engine/renderer work).

## Division of labour between models

Small models: line-for-line class ports driven by the report, new scenario files, fuzz action
tables. Big models (or a human): the bridge, engine layer, player loop, trace format, renderer,
standalone runtime, and any change to the oracle. Make this explicit in the porting guide, together
with the rule that the oracle, scenarios and tolerances are never edited to make a port pass.
