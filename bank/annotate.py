#!/usr/bin/env python3
"""Work-list helper for the annotation pass.

    python3 bank/annotate.py --chunks   # write bank/work/chunks.json (section -> chunk assignment)
    python3 bank/annotate.py --todo     # list chunk ids with no bank/annotations/<id>.json yet
    python3 bank/annotate.py --check    # validate every annotations file against the parsed sections

A chunk is a run of consecutive sections in one bank, about TARGET asm lines. Pure data
sections count 1/8 (they only need a name), so data-heavy banks make few chunks.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

WORK = build.HERE / "work"
TARGET = 700


def chunk_plan():
    parsed = build.parse_all()
    chunks = []
    for b, secs in parsed.items():
        cur, weight = [], 0
        for s in secs:
            asm = [l for l in s["lines"] if l.kind == "asm"]
            w = len(asm) if s["kind"] == "code" else max(1, len(asm) // 8)
            if cur and weight + w > TARGET:
                chunks.append((b, cur))
                cur, weight = [], 0
            cur.append(s)
            weight += w
        if cur:
            chunks.append((b, cur))
    out = []
    for i, (b, secs) in enumerate(chunks):
        src_lines = [l.no for s in secs for l in s["lines"] if l.no]
        out.append({
            "id": f"{b}-{i:03d}",
            "bank": b,
            "file": f"bank_{b}.asm" if b in build.BANKS else None,
            "line_from": min(src_lines) if src_lines else None,
            "line_to": max(src_lines) if src_lines else None,
            "asm_lines": sum(1 for s in secs for l in s["lines"] if l.kind == "asm"),
            "sections": [{
                "anchor": s["anchor"], "label": s["title"], "kind": s["kind"],
                "start": f"${s['start']:06X}" if s["start"] is not None else None,
                "end": f"${s['end']:06X}" if s["end"] is not None else None,
                "lines": sum(1 for l in s["lines"] if l.kind == "asm"),
            } for s in secs],
        })
    return out


def main():
    WORK.mkdir(exist_ok=True)
    plan_file = WORK / "chunks.json"
    if "--chunks" in sys.argv or not plan_file.exists():
        plan = chunk_plan()
        plan_file.write_text(json.dumps(plan, indent=1), encoding="utf-8")
        print(f"{len(plan)} chunks -> {plan_file}")
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    if "--todo" in sys.argv:
        todo = [c["id"] for c in plan if not (build.ANN / f"{c['id']}.json").exists()]
        print("\n".join(todo) if todo else "all done")
    if "--check" in sys.argv:
        anchors = {(c["bank"], s["anchor"]) for c in plan for s in c["sections"]}
        bad = 0
        for f in sorted(build.ANN.glob("*.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                print(f"{f.name}: invalid JSON: {e}")
                bad += 1
                continue
            for a in d.get("sections", {}):
                if (d.get("bank"), a) not in anchors:
                    print(f"{f.name}: unknown section anchor {a!r}")
                    bad += 1
            for a in d.get("lines", {}):
                if not (len(a) == 6 and a[:2] == d.get("bank")):
                    print(f"{f.name}: bad line address {a!r}")
                    bad += 1
        print("ok" if not bad else f"{bad} problems")


if __name__ == "__main__":
    main()
