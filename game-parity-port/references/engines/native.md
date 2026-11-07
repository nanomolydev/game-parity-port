# Native games: C, C++, custom engines, id Tech, Source, and others (forms B and D)

Recognize: a big native executable, no bytecode or script layer that holds the logic.

From strongest to weakest:

1. **Source available** (open-source games, released engine source, your own game). Compile the
   original with a trace hook in the main loop and a fixed timestep: it IS the oracle. Many classic
   engines are already deterministic by design (demo/replay systems in id Tech and Source are exactly
   the per-tick input playback this method needs; reuse them as the scenario format).
2. **Binary with symbols or RTTI** (PDB, DWARF, RTTI class names, a modding SDK). Hook the frame
   function (Frida, a proxy DLL, `LD_PRELOAD`), read structures at known offsets each tick, and feed
   input by hooking the input poll. Ghidra/IDA plus RTTI recover class layouts.
3. **No symbols**. Find state by memory scanning (Cheat Engine style) and observe positions, health,
   timers, UI text, audio events per tick. This is form D: weaker coverage, still automatic.

Determinism: hook time sources (`QueryPerformanceCounter`, `clock_gettime`, `SDL_GetTicks`) to scenario
time, seed or hook `rand`, force single-threaded simulation if possible, disable frame-rate dependent
logic by running at a fixed tick.

The port is verified trace vs trace. Hybrid porting is possible in form 1 (link the port into the
original build and switch functions one at a time) and sometimes in form 2 (detour individual
functions to the port).
