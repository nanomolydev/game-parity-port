#!/usr/bin/env python3
"""Exact per-tick comparison of two delta-JSONL game traces (oracle vs port).

    trace_compare.py ORACLE.jsonl PORT.jsonl [--out DIR] [--src DIR] [--abs 0] [--rel 0]
                     [--class NAME ...] [--max 200]

Trace line format (one per frame):
    {"f": <frame>, "new": {key: {"class": ..., "name": ...}}, "set": {"key|field": value}, "del": [key]}
"set" holds only values that changed. Values: numbers, strings, bools, null, arrays, objects.

Output (stdout summary; with --out also report.json and report.md):
    frames, values_compared, values_diverged, missing_in_port, extra_in_port,
    first_per_field: first frame where each class.field differs, with both values and, with --src,
    the source lines declaring/assigning the field (searched in DIR/<Class>.<ext>).
Exit code: 0 when identical, 1 when anything diverged or is missing.
Exact by default: floats must be equal (NaN == NaN, inf == inf). --abs/--rel loosen numbers only.
"""
import argparse, json, math, os, re, sys


def load(path):
    with open(path) as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def num_equal(a, b, abs_tol, rel_tol):
    if a == b:
        return True
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    if math.isinf(a) or math.isinf(b):
        return False
    d = abs(a - b)
    return d <= abs_tol or d <= rel_tol * max(abs(a), abs(b))


def equal(a, b, abs_tol, rel_tol):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return num_equal(float(a), float(b), abs_tol, rel_tol)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(equal(x, y, abs_tol, rel_tol) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k], abs_tol, rel_tol) for k in a)
    return a == b


def detail(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return f"|d|={abs(float(a) - float(b)):.6e}"
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        parts = [f"[{i}] |d|={abs(float(x) - float(y)):.6e}" for i, (x, y) in enumerate(zip(a, b))
                 if isinstance(x, (int, float)) and isinstance(y, (int, float)) and x != y]
        return ", ".join(parts) or "different"
    return "different"


def apply(state, fr):
    dead = set(fr.get("del") or [])
    if dead:
        for k in [k for k in state if k.split("|", 1)[0] in dead]:
            del state[k]
    state.update(fr.get("set") or {})


class Sources:
    """field -> declaring / assigning lines in <src>/<Class>.<ext> (any C-like language)."""

    def __init__(self, root):
        self.root, self.cache = root, {}

    def lines(self, cls):
        if cls in self.cache:
            return self.cache[cls]
        found = None
        if self.root:
            base = cls.replace(".", "/")
            for ext in (".cs", ".gd", ".java", ".lua", ".cpp", ".h", ".ts", ".js", ".py"):
                p = os.path.join(self.root, base + ext)
                if os.path.exists(p):
                    found = (p, open(p, encoding="utf-8", errors="replace").read().splitlines())
                    break
        self.cache[cls] = found
        return found

    def find(self, cls, field):
        f = self.lines(cls)
        if not f or field.startswith("$"):
            return None, []
        path, lines = f
        name = re.escape(field.split(".")[0])
        decl, assigned = None, []
        for i, l in enumerate(lines, 1):
            s = l.strip()
            if decl is None and re.search(rf"\b{name}\s*(=[^=]|;|$)", s) and re.match(r"(public|private|internal|protected|static|readonly|\[|var |let |local |[A-Za-z_][\w<>\[\],. ]*\s+" + name + ")", s):
                decl = f"{path}:{i}: {s}"
            elif re.search(rf"\b{name}\s*([+\-*/]?=)[^=]", s) or re.search(rf"\b{name}\s*(\+\+|--)", s):
                assigned.append(f"{path}:{i}: {s}")
        return decl, assigned[:8]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("oracle"); ap.add_argument("port")
    ap.add_argument("--out"); ap.add_argument("--src")
    ap.add_argument("--abs", type=float, default=0.0); ap.add_argument("--rel", type=float, default=0.0)
    ap.add_argument("--class", dest="classes", action="append", default=[])
    ap.add_argument("--max", type=int, default=200)
    a = ap.parse_args()

    meta, so, sp = {}, {}, {}
    compared = diverged = missing = extra = frames = 0
    first, per_class = {}, {}
    src = Sources(a.src)
    for fo, fp in zip(load(a.oracle), load(a.port)):
        meta.update(fo.get("new") or {})
        meta.update({k: v for k, v in (fp.get("new") or {}).items() if k not in meta})
        apply(so, fo); apply(sp, fp)
        frame = fo.get("f", frames)
        # compare only what changed this frame on either side (unchanged values stay equal or stay different)
        touched = set(fo.get("set") or {}) | set(fp.get("set") or {})
        if frames == 0 or fo.get("del") or fp.get("del"):
            touched |= set(so) | set(sp)
        for k in touched:
            obj, field = k.split("|", 1) if "|" in k else (k, "")
            m = meta.get(obj, {})
            cls = m.get("class", "?")
            if a.classes and cls not in a.classes:
                continue
            if k not in so:
                if k in sp: extra += 1
                continue
            compared += 1
            if k not in sp:
                missing += 1; bad = True; pv = None
            else:
                pv = sp[k]; bad = not equal(so[k], pv, a.abs, a.rel)
                if bad: diverged += 1
            if bad:
                per_class[cls] = per_class.get(cls, 0) + 1
                fk = (cls, field)
                if fk not in first:
                    decl, assigned = src.find(cls, field)
                    first[fk] = {"frame": frame, "class": cls, "field": field, "object": obj,
                                 "object_name": m.get("name", obj), "oracle": so[k], "port": pv,
                                 "detail": "missing in port" if k not in sp else detail(so[k], pv),
                                 "declared_at": decl, "assigned_at": assigned}
        frames += 1
    # values that stayed unchanged are not re-counted per frame; report the per-frame-change count
    firsts = sorted(first.values(), key=lambda d: (d["frame"], d["class"], d["field"]))
    rep = {"oracle": a.oracle, "port": a.port, "frames": frames, "values_compared": compared,
           "values_diverged": diverged, "missing_in_port": missing, "extra_in_port": extra,
           "classes": per_class, "first_per_field": firsts[: a.max]}
    print(f"frames={frames} compared={compared} diverged={diverged} missing={missing} extra={extra} classes_with_divergence={len(per_class)}")
    for d in firsts[:8]:
        print(f"\n  frame {d['frame']}  {d['class']}.{d['field']}  on {d['object_name']}")
        print(f"    oracle {json.dumps(d['oracle'])[:120]}")
        print(f"    port   {json.dumps(d['port'])[:120]}   ({d['detail']})")
        if d["declared_at"]: print(f"    declared {d['declared_at']}")
        for s in d["assigned_at"][:4]: print(f"    assigned {s}")
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        json.dump(rep, open(os.path.join(a.out, "report.json"), "w"), indent=1, allow_nan=True)
        with open(os.path.join(a.out, "report.md"), "w") as f:
            f.write(f"# Parity report\n\nframes {frames}, compared {compared}, diverged {diverged}, missing {missing}, extra {extra}\n\n")
            for d in firsts[: a.max]:
                f.write(f"## frame {d['frame']}: {d['class']}.{d['field']} on {d['object_name']}\n\n")
                f.write(f"- oracle: `{json.dumps(d['oracle'])[:300]}`\n- port: `{json.dumps(d['port'])[:300]}` ({d['detail']})\n")
                if d["declared_at"]: f.write(f"- declared: `{d['declared_at']}`\n")
                for s in d["assigned_at"]: f.write(f"- assigned: `{s}`\n")
                f.write("\n")
    sys.exit(1 if (diverged or missing) else 0)


if __name__ == "__main__":
    main()
