# Phase 5: scenarios

A scenario is data: which scene/objects to spawn, the RNG seed, the number of frames, and an input
timeline. Both oracle and port read the same file.

```json
{
  "name": "walk_look_jump", "frames": 300, "seed": 1,
  "spawn": [{"prefab": "resources.assets:178007", "pos": [0, 0, 0]}],
  "input": [
    {"from": 0, "to": 9999, "mousePosition": [960, 540]},
    {"from": 30, "to": 120, "hold": ["<Keyboard>/w"]},
    {"from": 60, "to": 90, "mouseDelta": [6, 0]},
    {"at": 210, "tap": "<Keyboard>/space"}
  ]
}
```

## Three kinds, all needed

1. **Fixed mechanic scenarios**: one per mechanic of the test scene (walk/sprint/crouch/jump,
   pick up, drop, throw, put into container, container counts it, break on impact...). Name them after
   the mechanic. Never edit an existing scenario to make a port pass; add a new one instead.
2. **Bot scenarios (closed loop) recorded to open loop**: aiming at a moving object by hand-written
   frame numbers is hopeless. Write a small bot that runs only on the oracle (reads oracle state,
   steers input toward goals: "walk to the vase, aim, grab, walk to the cart, release"), record the
   inputs it produced, and save them as a plain input timeline. The replay is then a normal open-loop
   scenario for both sides. Check that replay == bot run (0 divergences) once.
3. **Randomized scenarios, new data every run**: `scripts/fuzz_scenario.py` builds a scenario from a
   base and an action table: random hold segments, taps, mouse deltas, object positions inside safe
   bounds, a fresh engine seed. It prints the generator seed; a failing seed is kept and replayed
   exactly. Run several per check. This is what catches the branches the fixed scenarios never reach
   (sliding after sprint + crouch, double jump timing, stamina at zero...).

After a divergence is fixed on one scenario, re-run all fixed scenarios and fresh random ones: a fix
that only works on the failing data is not a fix.

## Coverage of systems, including AI

Monsters and other autonomous systems need scenarios too: spawn the enemy next to the player, let it
run its state machine with the player idle, moving, hiding; record seeds. NavMesh, perception
raycasts and timers all show up as fields in the trace.
