# Console and retro games: the emulator is the oracle (form C)

Recognize: a ROM/disc image (NES, SNES, Game Boy, Genesis, N64, PS1, GBA, DS...) or a PC game that
already runs in an accurate emulator (DOSBox for DOS games, ScummVM for adventure games: ScummVM
itself is a port verified this way in spirit).

- Accurate emulators are deterministic and already have what this method needs: frame stepping,
  input movies (BizHawk `.bk2`, FCEUX `.fm2`, libretro), save states, RAM access and Lua scripting.
  Use the movie format as the scenario format.
- Map game variables to RAM addresses (community RAM maps, decompilation projects such as the
  pret/n64decomp families, or your own search) and trace them per frame: player position, velocity,
  timers, RNG state, entity tables.
- If a matching decompilation exists, it is a form-1 native oracle (see `native.md`) and the
  strongest possible reference.
- Port verification: run the port on the same input movie and compare the mapped variables per
  frame, exactly (integer/fixed-point math makes exact parity very achievable here).
- Only use ROMs/images you dumped from media you own.
