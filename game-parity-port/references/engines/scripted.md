# Script-driven games: Lua, JavaScript/HTML5, Python, Ruby, Haxe, ActionScript (form A)

Many games keep their logic in scripts on top of a native engine: LÖVE, Defold, Solar2D/Corona,
custom Lua engines; HTML5/Phaser/PixiJS/Construct/RPG Maker MV-MZ (JS); Ren'Py and Pygame (Python);
RPG Maker XP-VX Ace (Ruby); Flash/AIR (ActionScript 3, runnable with Ruffle or an AS3 VM).

Recognize: script files or an archive of them (`.love` is a zip, `game.rgss*a`, `www/js/`, `*.rpy/.rpyc`,
`.swf`), sometimes precompiled bytecode (luac, `.rpyc`, AVM2) that decompiles well.

- Oracle host: embed the SAME VM and version (Lua 5.1 vs LuaJIT behave differently; a JS engine with
  the same number semantics; CPython of the same minor version). Implement the engine's script API
  (the binding table is your inventory) as a headless facade over the shared engine layer.
- Determinism: replace `math.random`/`Math.random`/`random` with the original algorithm and a seed;
  patch `os.time`, `Date.now`, `performance.now`, `love.timer` to scenario time; drive the update
  callback (`love.update(dt)`, `requestAnimationFrame`, game loop) with fixed steps.
- Trace: walk the globals and the object tables/graphs reachable from the game's roots every tick;
  give tables stable keys (entity ids, paths from roots). Ignore functions and engine handles.
- Hybrid porting: replace one module/function at a time with the port exposed through the VM's FFI
  (LuaJIT FFI, N-API/WASM for JS, a CPython extension).
- Browser games: the oracle can also be the original page in headless Chromium with the same
  patches injected before the game script loads, tracing through `page.evaluate` each tick.
