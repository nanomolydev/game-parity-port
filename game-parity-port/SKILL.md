---
name: game-parity-port
description: First build a tick-exact parity testing core for any existing game (the original game as an oracle, a per-tick trace of every field, an exact comparator, a passing gate check), and only then port its logic to Rust (or any other language) one piece at a time, verified against the ORIGINAL game running as an oracle. Works for any engine or build type (Unity Mono/IL2CPP, Godot, Unreal, XNA/FNA/MonoGame, Java, Lua/JS/Python scripts, GameMaker, native C/C++, emulated console games). Use this whenever someone wants to rewrite, port, remake, decompile-and-rebuild or reimplement a game and keep it identical to the original, wants per-frame/per-tick identity tests or deterministic replay comparison, a divergence report a smaller model can follow, or asks how to port a game to another language without breaking mechanics, even if they never say "oracle" or "parity".
---

# Game parity port

Port a game to a new language while proving, every frame, that the port behaves exactly like the
original. The original game code is the reference ("oracle"), not hand-written expectations.
Everything else in this skill serves that one idea.

## Start here: the testing core comes first (hard gate)

The deliverable of the first session is **the testing core, not the port**. Do not write port code,
do not run a port, do not "quickly rewrite the main loop to see it working", until the gate below
passes. This holds for small games too: a small game makes the core small (a few hundred lines), not
optional. Without the core, nothing you port can be shown identical, and the user asked for identity.

If you notice you are about to write or run port code before the gate passed, stop and go back to
the core. If the core is blocked (the original cannot be made to run, no way to read its state),
say so plainly with the reason and the options (`references/oracle.md` section 1); do not fall back
to porting without an oracle.

Build these, in this order, in a `parity/` folder of the project:

1. `parity/RECON.md`: answers from `references/recon.md` and the chosen oracle form.
2. `parity/oracle/`: runs the ORIGINAL game logic headless, fixed timestep, seeded, for N frames of
   a scenario, and writes `trace.jsonl` (every field of every game object, every frame;
   `references/trace-and-compare.md`). Plus a report of unimplemented engine calls.
3. `parity/scenarios/`: at least one scenario where the player actually does things (moves, jumps,
   uses the main mechanic) for several seconds.
4. `parity/check.sh`: from `scripts/check.sh.template`; one command builds, runs, compares.
5. The gate:

   ```sh
   # run the oracle twice on the same scenario and seed, then:
   python3 <skill>/scripts/gate_check.py parity/reports/run1/trace.jsonl parity/reports/run2/trace.jsonl
   ```

   It checks that the trace is substantial, that two runs are identical (determinism) and that a
   planted one-value change is caught at the right frame (negative control). Only `GATE PASSED`
   opens the porting phase.

Then report to the user: what the oracle runs, how many objects/fields per frame are traced, what is
stubbed or approximate, the gate output. Porting (phase 6) starts after that, one class at a time.

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

## The architecture

```
original game logic (bytecode / scripts / native)      the port (Rust, C++, ...)
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
| 0 | Recon | You know engine, version, where the logic lives and in what form, plugins, physics; oracle form chosen | `references/recon.md` |
| 1 | API inventory | A complete, generated table of every engine member the game references, with callers | `references/oracle.md` + `references/engines/<engine>.md` |
| 2 | Engine facade + engine layer | The original logic runs frames headless and seeded; unimplemented calls are counted, never silent | same |
| 3 | World from original data | Objects and their initial values come from the shipped data files, not re-typed | same |
| 4 | Trace + comparator | `scripts/gate_check.py` prints GATE PASSED (substantial trace, determinism, negative control) | `references/trace-and-compare.md` |
| 5 | Scenarios | Fixed scenarios per mechanic + randomized ones with a new seed every run | `references/scenarios.md` |
| 6 | Hybrid porting loop | A ported class runs inside the oracle and matches on every scenario | `references/porting-loop.md` |
| 7 | Live play + standalone | Play the hybrid in real time; later run the port without the original at all | `references/live-and-standalone.md` |

Phases 0-4 are the testing core; phase 6 is forbidden before the gate passes. An oracle that is not
deterministic, or a comparator that misses a planted bug, makes every later "0 divergences"
meaningless. Re-run the gate whenever the oracle, the trace writer or the comparator changes.

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

- `scripts/gate_check.py`: the gate between "testing core" and "porting". Substantial trace,
  determinism of two oracle runs, negative control. Exit 0 only on GATE PASSED.
- `scripts/trace_compare.py`: engine- and language-agnostic comparator for the delta-JSONL trace format
  (`references/trace-and-compare.md`). Exact by default, first divergence per class.field,
  optional source-line lookup. Use it as is, or as the spec for a faster native comparator.
- `scripts/fuzz_scenario.py`: makes a randomized scenario from a base scenario and an action table
  (keys, mouse, object positions, seed), prints the seed so a failure can be replayed.
- `scripts/check.sh.template`: the one-command loop (build, oracle run, hybrid run, compare, print
  first divergences). Copy it into the project and fill in the three commands.

## Engine-specific notes

The method is the same for every game; only how the oracle is built (phases 1-3) differs. After
recon, read the one file that matches the build:

| Build | File | Oracle form |
|---|---|---|
| Unity, Mono (`Managed/Assembly-CSharp.dll`) | `references/engines/unity-mono.md` | original bytecode on a facade |
| Unity, IL2CPP (`GameAssembly.dll` + `global-metadata.dat`) | `references/engines/unity-il2cpp.md` | instrumented original |
| Godot (GDScript or C#) | `references/engines/godot.md` | original scripts on the real engine, headless |
| XNA / FNA / MonoGame / custom .NET | `references/engines/dotnet-xna.md` | original bytecode on a facade |
| Unreal | `references/engines/unreal.md` | instrumented original |
| Java / Kotlin (LWJGL, libGDX) | `references/engines/jvm.md` | original bytecode on a facade |
| Lua, JS/HTML5, Python, Ruby, ActionScript | `references/engines/scripted.md` | original scripts in the same VM |
| GameMaker (`data.win`) | `references/engines/gamemaker.md` | VM bytecode, or instrumented YYC |
| Native C/C++, custom engines | `references/engines/native.md` | rebuilt / hooked / observed original |
| Console and retro (ROMs, DOS, SCUMM) | `references/engines/emulated.md` | the emulator |

Nothing listed? Use `references/oracle.md` directly: decide the oracle form (original logic on a
facade, instrumented original, emulator, or observation) and follow the generic steps.

## Legal and scope note

This is for porting a game you own for personal use, or your own game. The oracle runs the original
files locally; do not redistribute the original game's code or assets inside the port or the test
data. Keep extracted assets out of public repositories.
