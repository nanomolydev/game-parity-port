# Oracle harness examples for small games

Every example has the same five parts. Recognize them, then adapt to the game in front of you:

1. **Load the original game unchanged** (import its module, load its assembly, open its page).
2. **Replace only the platform**: window/graphics (headless), input devices (fed from the scenario),
   the clock (fixed step), random (seeded with the original algorithm). Nothing else.
3. **Drive the original main loop one frame at a time** (call its own update/step, or let its loop
   run and gate it per frame).
4. **After every frame, dump all state** of every live game object to `trace.jsonl`
   (`references/trace-and-compare.md`), using stable keys.
5. **Run N frames of a scenario** and exit. Same scenario file later drives the port.

The port side gets the same harness shape (same scenario reader, same trace writer); only the game
code underneath is the port. Then `scripts/trace_compare.py oracle.jsonl port.jsonl` compares them
frame by frame.

## Contents
- A. Python / pygame
- B. JavaScript / HTML5 in a browser
- C. Lua / LÖVE
- D. .NET (MonoGame / FNA / Unity Mono)
- E. Emulated game (BizHawk / libretro)
- F. Generic state dumper (any language with reflection)

## A. Python / pygame

The game has `main.py` with `Game().run()` doing `while running: handle events; update(dt); draw; clock.tick(60)`.

```python
# parity/oracle/run.py : python3 run.py scenario.json out/trace.jsonl
import json, os, random, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"   # headless platform
import pygame
sys.path.insert(0, "path/to/original/game")
import main as game_main                                   # the ORIGINAL code, unchanged

sc = json.load(open(sys.argv[1]))
random.seed(sc["seed"])                                    # the game's RNG, seeded
frame = 0

class FixedClock:                                          # fixed timestep instead of wall clock
    def tick(self, fps=60): return 1000 // 60
    def get_time(self): return 1000 // 60
pygame.time.Clock = FixedClock
pygame.time.get_ticks = lambda: frame * 1000 // 60

def scenario_events():                                     # input from the scenario timeline
    held = {k for e in sc["input"] if e.get("from", e.get("at")) <= frame <= e.get("to", e.get("at")) for k in e.get("hold", []) + ([e["tap"]] if "tap" in e else [])}
    return held
pressed_prev = set()
def fake_get():
    global pressed_prev
    held = scenario_events(); evs = []
    for k in held - pressed_prev: evs.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.key.key_code(k)))
    for k in pressed_prev - held: evs.append(pygame.event.Event(pygame.KEYUP, key=pygame.key.key_code(k)))
    pressed_prev = held; return evs
pygame.event.get = fake_get
pygame.key.get_pressed = lambda: KeyState(scenario_events())   # small helper mapping names to codes

out = open(sys.argv[2], "w"); prev = {}
def dump(game):                                            # every field of every object, delta only
    cur = {}
    for key, obj in walk(game):                            # walk(): game root -> lists/dicts of objects, stable keys
        for name, v in vars(obj).items():
            if is_plain(v): cur[f"{key}|{name}"] = v
    out.write(json.dumps({"f": frame, "set": {k: v for k, v in cur.items() if prev.get(k) != v},
                          "del": sorted({k.split('|')[0] for k in prev} - {k.split('|')[0] for k in cur})}) + "\n")
    prev.clear(); prev.update(cur)

g = game_main.Game()
for frame in range(sc["frames"]):
    g.step_one_frame()        # if the game only has run(): refactor nothing; instead patch clock.tick
                              # to call dump(g) and stop after N frames (it is called once per frame)
    dump(g)
```

If the original has only `run()` with its own `while` loop, do not rewrite it: hook a call that
happens exactly once per frame (`clock.tick`, `pygame.display.flip`) and do `dump(g)` there, raising
a private exception after `sc["frames"]` frames to leave the loop.

## B. JavaScript / HTML5 in a browser

Run the ORIGINAL page in headless Chromium (Playwright). Inject the platform patches before any game
script runs, then step frames yourself.

```js
// parity/oracle/run.mjs : node run.mjs scenario.json out/trace.jsonl
import { chromium } from "playwright"; import fs from "fs";
const sc = JSON.parse(fs.readFileSync(process.argv[2])); const out = fs.createWriteStream(process.argv[3]);
const browser = await chromium.launch(); const page = await browser.newPage();
await page.addInitScript(seed => {
  let s = seed >>> 0; Math.random = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 2 ** 32);  // or the original PRNG if the game ships one
  let t = 0; performance.now = () => t; Date.now = () => 1.7e12 + t;
  const cbs = []; window.requestAnimationFrame = cb => cbs.push(cb);
  window.__step = () => { t += 1000 / 60; const run = cbs.splice(0); run.forEach(cb => cb(t)); };
}, sc.seed);
await page.goto("file:///path/to/original/index.html");
let prev = {};
for (let f = 0; f < sc.frames; f++) {
  for (const e of sc.input) /* dispatch keydown/keyup for keys entering/leaving the held set at frame f */;
  await page.evaluate(() => window.__step());              // exactly one original frame
  const cur = await page.evaluate(() => window.__dumpState()); // injected walker over the game's root objects
  const set = {}; for (const k in cur) if (JSON.stringify(cur[k]) !== JSON.stringify(prev[k])) set[k] = cur[k];
  out.write(JSON.stringify({ f, set, del: [] }) + "\n"); prev = cur;
}
await browser.close();
```

`__dumpState` (injected too) walks from the game's roots (`window.game`, the scene/stage, entity
arrays) and returns `{ "<stable key>|<field>": value }` for every own enumerable plain field.

## C. Lua / LÖVE

Embed the same Lua/LuaJIT version, provide a headless `love` table (graphics no-ops, keyboard from the
scenario, `love.timer.getDelta()` fixed, `love.math.random` seeded with LÖVE's algorithm), `dofile`
the original `main.lua`, call `love.load()`, then per frame `love.update(1/60)` and dump: walk `_G`
and tables reachable from the game's root objects, keyed by path (`player`, `enemies[3]`), skipping
functions and userdata.

## D. .NET (MonoGame / FNA / Unity Mono)

Load the original assemblies into your own host process. Replace the platform types (graphics device,
window, audio, keyboard/mouse) with a headless facade (`references/engines/dotnet-xna.md`,
`references/engines/unity-mono.md`). Call the game's own `Update(GameTime)` (or the engine's player
loop) with a fixed `GameTime` once per frame, then dump by reflection over every live object.

## E. Emulated game

```lua
-- BizHawk Lua: run with the ROM loaded and the scenario's input movie
local out = io.open("trace.jsonl", "w")
local vars = { player_x = 0x0086, player_y = 0x00CE, lives = 0x075A, timer = 0x07F8 }  -- RAM map
for f = 0, 3599 do
  emu.frameadvance()                                       -- exactly one original frame
  local set = {}
  for name, addr in pairs(vars) do set["ram|" .. name] = memory.readbyte(addr) end
  out:write(string.format('{"f":%d,"set":%s,"del":[]}\n', f, json_encode(set)))
end
```

## F. Generic state dumper (any language with reflection)

```
dump(frame):
  cur = {}
  for (key, obj) in live_objects():          # from the game's roots; key is stable (path, id, asset id)
    for field in all_fields(obj):            # public AND private, including inherited
      v = read(obj, field)
      if plain(v): cur[key|field] = v        # numbers, bools, strings, vectors, enums
      elif is_object_ref(v): cur[key|field] = key_of(v) or null
      elif is_collection(v): cur[key|field] = [plain or key_of(x) for x in v]
  write {"f": frame, "set": changed(cur, prev), "del": gone(cur, prev)}
```

Things that must be in every dump: positions/rotations/velocities, every timer and counter, every
state-machine state, every flag, the score/health/inventory, the RNG state if readable, and the input
the frame consumed. If a field exists in the game, it belongs in the trace.
