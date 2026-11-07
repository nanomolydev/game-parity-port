# Phase 4: trace and comparator

## Trace format (delta JSONL, one line per frame)

```json
{"f": 0, "new": {"lvl:1360": {"class": "PlayerController", "asm": "Assembly-CSharp", "go": "lvl:1355", "name": "Controller"}},
 "set": {"lvl:1360|EnergyCurrent": 40, "lvl:1360|Velocity": [0, -0.1962, 0], "lvl:1355|$pos": [0, 0.05, 1]},
 "del": []}
{"f": 1, "set": {"lvl:1360|EnergyCurrent": 39.8}, "del": []}
```

- `key|field` -> value, only values that changed since the previous frame. `new` carries metadata
  the first time an object appears; `del` lists destroyed objects.
- Record every field (public and private) of every game behaviour, plus engine state the game
  depends on: transform (`$pos`, `$rot`, `$scale`, `$active`), rigidbody velocity, audio voices
  started this frame, input values. Floats as shortest round-trip text (`R` format), vectors as arrays,
  object references as stable keys or null.
- **Stable object keys** are essential: the same object must have the same key in both runs.
  Use the asset identity (`file:pathId`) for scene objects, `tpl:<prefab gid>@<n>` for the n-th
  instance of a prefab, `<parent key>/<child path>` for children. Never use memory addresses or
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
