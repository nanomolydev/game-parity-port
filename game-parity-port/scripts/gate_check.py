#!/usr/bin/env python3
"""Gate check: is the parity testing core trustworthy enough to start porting?

    gate_check.py ORACLE_RUN1.jsonl ORACLE_RUN2.jsonl [--port PORT.jsonl] [--min-frames 60] [--min-values 1000]

Checks, in order (all must pass; prints GATE PASSED or GATE FAILED with the reason):
  1. the oracle trace exists, parses, has at least --min-frames frames and --min-values compared values
     (an empty or near-empty trace means the oracle is not really recording the game);
  2. determinism: two oracle runs of the same scenario and seed compare with 0 divergences;
  3. negative control: one numeric value planted in a copy of run 2 (+1e-6 mid-run) is reported by the
     comparator at exactly that frame and key;
  4. optional --port: the port side produces a trace in the same format (it may diverge or be empty
     of game fields; this only proves the plumbing exists).
Exit code 0 only when the gate passes. Run it again whenever the trace writer, the oracle or the
comparator changes.
"""
import argparse, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
COMPARE = os.path.join(HERE, "trace_compare.py")


def fail(msg):
    print(f"GATE FAILED: {msg}")
    sys.exit(1)


def compare(a, b, out):
    r = subprocess.run([sys.executable, COMPARE, a, b, "--out", out], capture_output=True, text=True)
    path = os.path.join(out, "report.json")
    if not os.path.exists(path):
        fail(f"comparator produced no report:\n{r.stdout}\n{r.stderr}")
    return r.returncode, json.load(open(path))


def frames_of(path):
    try:
        with open(path) as f:
            return [json.loads(l) for l in f if l.strip()]
    except Exception as e:
        fail(f"cannot read trace {path}: {e}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run1"); ap.add_argument("run2")
    ap.add_argument("--port")
    ap.add_argument("--min-frames", type=int, default=60)
    ap.add_argument("--min-values", type=int, default=1000)
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="gate_")

    fr = frames_of(a.run1)
    if len(fr) < a.min_frames:
        fail(f"{a.run1} has {len(fr)} frames (need {a.min_frames}); run a real scenario: setup, then the player acting for a few seconds")
    print(f"[1] oracle trace: {len(fr)} frames")

    code, rep = compare(a.run1, a.run2, os.path.join(tmp, "det"))
    if rep["values_compared"] < a.min_values:
        fail(f"only {rep['values_compared']} values recorded; trace every field of every game object (see trace-and-compare.md)")
    if code != 0 or rep["values_diverged"] or rep["missing_in_port"] or rep["extra_in_port"]:
        first = rep["first_per_field"][:3]
        fail("oracle is not deterministic: two runs differ. First differences:\n" + "\n".join(
            f"  frame {d['frame']} {d['class']}.{d['field']}: {json.dumps(d['oracle'])[:80]} vs {json.dumps(d['port'])[:80]}" for d in first)
            + "\nFind the source (hash maps, wall-clock time, threads, unseeded random) and fix the oracle.")
    print(f"[2] determinism: {rep['values_compared']} values, 0 divergences")

    fr2 = frames_of(a.run2)
    target = None
    for i in range(len(fr2) // 2, len(fr2)):
        for k, v in (fr2[i].get("set") or {}).items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and "|" in k:
                target = (i, k, v)
                break
        if target:
            break
    if not target:
        fail("no numeric field changes in the second half of the run; the scenario does not exercise the game")
    i, k, v = target
    fr2[i]["set"][k] = v + 1e-6 if isinstance(v, float) else v + 1
    bad = os.path.join(tmp, "planted.jsonl")
    with open(bad, "w") as f:
        for x in fr2:
            f.write(json.dumps(x) + "\n")
    code, rep = compare(a.run1, bad, os.path.join(tmp, "neg"))
    hit = [d for d in rep["first_per_field"] if d["object"] == k.split("|", 1)[0] and d["field"] == k.split("|", 1)[1]]
    if code == 0 or not hit or hit[0]["frame"] != fr2[i].get("f", i):
        fail(f"negative control missed: planted a change in {k} at frame {fr2[i].get('f', i)}, comparator reported {hit[:1] or 'nothing'}")
    print(f"[3] negative control: planted change in {k} at frame {hit[0]['frame']} was caught")

    if a.port:
        pf = frames_of(a.port)
        if not pf or "set" not in pf[0]:
            fail(f"{a.port} is not a trace in the same format")
        code, rep = compare(a.run1, a.port, os.path.join(tmp, "port"))
        print(f"[4] port trace plumbing: {len(pf)} frames, comparator ran (diverged={rep['values_diverged']} missing={rep['missing_in_port']})")

    print("GATE PASSED: the testing core is trustworthy; porting may start.")


if __name__ == "__main__":
    main()
