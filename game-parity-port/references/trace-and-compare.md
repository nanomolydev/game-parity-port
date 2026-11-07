# Phase 4: trace and comparator

## Trace format (delta JSONL, one line per frame)

```json
{"f": 0, "new": {"level1/player": {"class": "Player", "name": "Player"}},
 "set": {"level1/player|stamina": 40, "level1/player|velocity": [0, -0.1962, 0], "level1/player|$pos": [0, 0.05, 1]},
 "del": []}
{"f": 1, "set": {"level1/player|stamina": 39.8}, "del": []}
```

- `key|field` -> value, only values that changed since the previous frame. `new` carries metadata
  the first time an object appears; `del` lists destroyed objects.
- Record every field (public and private) of every game object/script, plus engine state the game
  depends on, under `$` names: transform (`$pos`, `$rot`, `$scale`, `$active`), body velocity,
  sounds started this frame, input values. For form C/D oracles (emulator RAM, observation) the
  "fields" are the mapped variables. Floats as shortest round-trip text (`R` format), vectors as arrays,
  object references as stable keys or null.
- **Stable object keys** are essential: the same object must have the same key in both runs.
  Use the identity the data already has: asset ids or scene paths for placed objects, node paths
  (Godot), level path + name (Unreal), `tpl:<template id>@<n>` for the n-th spawned instance of a
  template, `<parent key>/<child>` for children, entity ids where the game assigns them
  deterministically. Never use memory addresses or
  creation counters shared across unrelated objects.
- Delta encoding keeps a 1500-frame, 26-million-value run at a few dozen MB.

## Comparator

Use `scripts/trace_compare.py` (or reimplement natively for speed with the same output):

```
python3 scripts/trace_compare.py oracle/trace.jsonl port/trace.jsonl --out compare/ [--src game_src/] [--abs 0 --rel 0]
```

It reconstructs both states frame by frame and reports:
- totals: frames, values compared, diverged, missing in port, extra in port;
- `first_per_field`: the first frame where each class.field diverged, with oracle and port values,
  the object name, and (with `--src`) the source lines that declare and assign that field;
- a markdown summary for humans and models.

Exact by default. `NaN == NaN` and `inf == inf` count as equal. Report "missing" (value only in the
oracle) separately from "diverged"; missing usually means a ported message never ran.

## Mandatory self-checks before trusting it

1. Determinism: run the oracle twice with the same seed and compare. Must be 0. If not, find the
   nondeterminism (hash maps, wall-clock time, thread scheduling, uninitialized memory) and fix it
   in the oracle.
2. Negative control: plant a one-character bug in a ported method (`+` to `-`, a changed constant)
   and confirm the comparator reports that field at the right frame with the right source line.
   Repeat after any change to the trace writer or comparator.

## Visual check without screenshots

Pixel comparison is noisy and needs a model or a human to judge. Compare the *inputs* of rendering
instead: per frame, which renderers are visible, their world matrices, materials and material
properties, light parameters, camera matrices, UI element rects/texts/colors. These are fields like
any other and go through the same exact comparator. A trace viewer that replays both traces side by
side in 3D (port drawn only where it diverges) is worth building early; people trust what they see.
