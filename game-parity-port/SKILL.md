---
name: game-parity-port
description: Build a tick-exact parity testing core for an existing game and port its logic to Rust (or any other language) one class at a time, verified against the ORIGINAL game running as an oracle. Use this whenever someone wants to rewrite, port, remake or reimplement a game (Unity, Godot, a C#/.NET, Java, Lua or custom engine game) and keep it identical to the original, wants "Horizon-style" or per-frame/per-tick identity tests, deterministic replay comparison, a divergence report a smaller model can follow, or asks how to port a game to Rust without breaking mechanics, even if they never say "oracle" or "parity".
---

# Game parity port

Port a game to a new language while proving, every frame, that the port behaves exactly like the
original. The original game code is the reference ("oracle"), not hand-written expectations.
Everything else in this skill serves that one idea.

## Why this shape works

Hand-written tests only check what someone thought of. A game has thousands of interacting fields
(timers, lerps, physics state, flags), and the bugs live in the ones nobody wrote a test for. If the
original code runs next to the port on the same input and every field of every object is compared
on every tick, nothing can hide: the first divergence points at the exact field, frame and source
line. That also makes the work safe for smaller models, because the report tells them what is wrong
instead of them having to judge it.

Three rules make the comparison meaningful:

1. **The oracle is the original binary/bytecode, unchanged.** Never "re-implement the original to
   test against". If the original cannot run as is, build the environment it needs (the engine
   layer below), not a copy of its logic.
2. **Split engine from game.** Engine-native behaviour (math, transforms, physics, input, audio,
   time, random) is implemented once and shared by oracle and port. Only game logic is compared.
   Otherwise every engine difference shows up as noise in every class.
3. **Exact by default.** Compare floats bit-for-bit (abs = rel = 0). A tolerance hides real bugs
   (operand order, double vs float, a missed clamp). Only loosen it for a field with a written reason.

## The architecture (build in this order)

```
original game code (dll / bytecode / scripts)          the port (Rust, C++, ...)
        |                                                      |
   engine API facade  ---------- same calls ------------  typed wrappers
        |                                                      |
        +-----------> shared ENGINE LAYER (native) <-----------+
                      math, transforms, physics, input, time, random, audio state
        |                                                      |
   player loop (frame order) + scene loader from original assets
        |
   TRACE: every field of every object, every frame (delta JSONL)
        |
   COMPARATOR: oracle trace vs port trace -> first divergence per field + source lines
```

Phases, each with a definition of done. Read the reference file for a phase when you start it.

| # | Phase | Done when | Reference |
|---|---|---|---|
| 0 | Recon | You know engine, version, scripting backend, where the logic lives, what native plugins exist | `references/recon.md` |
| 1 | API inventory | A complete, generated table of every engine member the game references, with callers | `references/oracle-unity-mono.md` (or `other-engines.md`) |
| 2 | Engine facade + engine layer | The original code loads and runs frames headless; unimplemented calls are counted, never silent | same |
| 3 | Scene from original assets | Objects, components and serialized values come from the shipped asset files, not re-typed | same |
| 4 | Trace + comparator | Two oracle runs with the same seed give 0 divergences; a deliberate one-line bug is caught | `references/trace-and-compare.md` |
| 5 | Scenarios | Fixed scenarios per mechanic + randomized ones with a new seed every run | `references/scenarios.md` |
| 6 | Hybrid porting loop | A ported class runs inside the oracle and matches on every scenario | `references/porting-loop.md` |
| 7 | Live play + standalone | Play the hybrid in real time; later run the port without the original at all | `references/live-and-standalone.md` |

Do not skip phase 4's two checks. An oracle that is not deterministic, or a comparator that misses
a planted bug, makes every later "0 divergences" meaningless.

## Working rules (tell these to any model doing the porting)

- Read the whole original source file of a class before porting it. Partial reads produce ports that
  miss a branch two screens down.
- Port line for line, in the same order, with the same float operation order
  (`a + (b - a) * t` is not `a * (1 - t) + b * t`). Re-read a field after writing it if the original
  does; another object may change it in between.
- Pass default arguments explicitly; port helper methods as plain functions called from the port.
- Never change the oracle, the engine layer, scenarios or tolerances to make a port pass. If the
  oracle is wrong, fix the oracle (then re-check its determinism), and say so.
- "Done" = 0 divergences and 0 missing values on every fixed scenario AND on several fresh random
  runs. Always pass the full list of already-ported classes, so regressions show up.
- A divergence report is the only feedback a porting model needs. No screenshots, no "looks right".

## Bundled scripts

- `scripts/trace_compare.py`: engine-agnostic comparator for the delta-JSONL trace format
  (`references/trace-and-compare.md`). Exact by default, first divergence per class.field,
  optional source-line lookup. Use it as is, or as the spec for a faster native comparator.
- `scripts/fuzz_scenario.py`: makes a randomized scenario from a base scenario and an action table
  (keys, mouse, object positions, seed), prints the seed so a failure can be replayed.
- `scripts/check.sh.template`: the one-command loop (build, oracle run, hybrid run, compare, print
  first divergences). Copy it into the project and fill in the three commands.

## When the target is not Unity/Mono

The method is the same for any engine; only phases 1-3 change. `references/other-engines.md` covers
IL2CPP and native builds, Godot (GDScript/C#), Java/LWJGL games, Lua-scripted engines and custom C++
engines, including the cases where the oracle has to be an instrumented original build instead of
the original code running on a facade.

## Legal and scope note

This is for porting a game you own for personal use, or your own game. The oracle runs the original
files locally; do not redistribute the original game's code or assets inside the port or the test
data. Keep extracted assets out of public repositories.
