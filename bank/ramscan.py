#!/usr/bin/env python3
"""Find every WRAM address the code touches, from the operand bytes of each instruction.

    python3 bank/ramscan.py --batches   # write bank/work/ram_batches/NN.json for the annotators
    python3 bank/ramscan.py --check     # validate bank/ram/*.json against the scanned addresses

Imported by build.py (scan) to render ram.html. Keys: 0x0000-0x1FFF for low RAM ($7E:0000-1FFF is
the same memory), 0x7E0000|off / 0x7F0000|off for the extended WRAM areas.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

SKIP = {"BEQ", "BNE", "BCC", "BCS", "BPL", "BMI", "BVC", "BVS", "BRA", "BRL", "JSR", "JSL", "JMP", "JML",
        "PEA", "PEI", "PER", "MVN", "MVP", "REP", "SEP"}
WRITE = {"STA", "STX", "STY", "STZ"}
MODIFY = {"INC", "DEC", "ASL", "LSR", "ROL", "ROR", "TSB", "TRB"}
CODE_BANKS = set(build.BANKS)
MIN_USES = 3          # addresses used fewer times than this get call sites but no written description
BATCH = 45


def fmt(key):
    return f"${key:04X}" if key < 0x10000 else f"${key >> 16:02X}:{key & 0xFFFF:04X}"


def anchor(key):
    return f"{key:04X}" if key < 0x10000 else f"{key:06X}"


def mode_of(mn):
    return "W" if mn in WRITE else "M" if mn in MODIFY else "R"


def scan(parsed, sec_title):
    """-> {key: {"sym": RAM_ name or None, "uses": [dict]}} for every WRAM operand in the code banks."""
    out = defaultdict(lambda: {"sym": None, "syms": set(), "uses": []})
    for b, secs in parsed.items():
        if b not in CODE_BANKS:
            continue
        for s in secs:
            title = sec_title(b, s)
            for ln in s["lines"]:
                if ln.kind != "asm" or not ln.hex or not ln.code.strip() or ln.addr is None:
                    continue
                code = ln.code.strip()
                if ln.mn in SKIP or code.startswith(".") or "#" in code or ",s" in code.lower():  # .dw/.db rows have an empty mnemonic
                    continue
                by = [int(x, 16) for x in ln.hex.split()]
                if len(by) == 2:
                    key = by[1]
                elif len(by) == 3:
                    key = by[1] | by[2] << 8
                    if key >= 0x2000:
                        continue
                elif len(by) == 4:
                    a = by[1] | by[2] << 8 | by[3] << 16
                    if a >> 16 not in (0x7E, 0x7F):
                        continue
                    key = a & 0xFFFF if (a >> 16 == 0x7E and a & 0xFFFF < 0x2000) else a
                else:
                    continue
                opnd = code.partition(" ")[2]
                idx = "X" if re.search(r",\s*X\b", opnd, re.I) else "Y" if re.search(r",\s*Y\b", opnd, re.I) else None
                ptr = "(" in opnd or "[" in opnd
                e = out[key]
                for m in re.finditer(r"RAM_\w+", code):
                    e["syms"].add(m.group(0))
                    e["sym"] = e["sym"] or m.group(0)
                e["uses"].append({"bank": b, "addr": ln.addr, "anchor": s["anchor"], "sec": title, "mn": ln.mn,
                                  "mode": mode_of(ln.mn), "idx": idx, "ptr": ptr, "code": code,
                                  "comment": (ln.comment or "").strip()})
    return out


def load_ram_annotations(ram_dir):
    """bank/ram/*.json -> {key: {"name", "kind", "desc": [lines]}}. Keys in the files are hex strings."""
    ann = {}
    for f in sorted(ram_dir.glob("*.json")) if ram_dir.exists() else []:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"skip {f.name}: {e}", file=sys.stderr)
            continue
        for k, v in d.get("addresses", {}).items():
            try:
                ann[int(k.replace("$", "").replace(":", ""), 16)] = v
            except ValueError:
                pass
    return ann


def _context():
    parsed = build.parse_all()
    names, comments = build.load_annotations()

    def sec_title(b, s):
        n = names.get((b, s["anchor"]), {}).get("name")
        return n or s["title"]

    # overlay comments replace the source comment, so the digest shows the readable one
    scanned = scan(parsed, sec_title)
    for e in scanned.values():
        for u in e["uses"]:
            u["comment"] = comments.get((u["bank"], u["addr"]), u["comment"]).strip()
    return scanned


def write_batches(scanned, first=0, after=-1):
    """Write batches numbered from `first`, covering addresses above `after` (earlier batch files are left alone)."""
    wd = build.HERE / "work" / "ram_batches"
    wd.mkdir(parents=True, exist_ok=True)
    keys = sorted(k for k, e in scanned.items() if len(e["uses"]) >= MIN_USES and not (k < 0x10) and k > after)  # $00-$0F: scratch
    for f in wd.glob("*.json"):
        if int(f.stem) >= first:
            f.unlink()
    n = first
    for i in range(0, len(keys), BATCH):
        chunk = []
        for k in keys[i:i + BATCH]:
            e = scanned[k]
            uses = e["uses"]
            modes = Counter(u["mode"] for u in uses)
            idx = Counter(u["idx"] for u in uses if u["idx"])
            by_sec = defaultdict(list)
            for u in uses:
                by_sec[(u["bank"], u["sec"])].append(u)
            sample = []
            # one sample per routine, preferring lines that carry a real comment, spread across banks
            for (b, title), us in sorted(by_sec.items(), key=lambda kv: -len(kv[1])):
                us.sort(key=lambda u: (len(re.sub(r"^[\\|/}\s]+", "", u["comment"])) < 4, u["addr"]))  # skip bare box characters
                u = us[0]
                sample.append(f'${u["bank"]}:{u["addr"] & 0xFFFF:04X} {u["mn"]}{"," + u["idx"] if u["idx"] else ""} in "{title}" x{len(us)}'
                              + (f' ; {re.sub(r"^[\\|/}]+ ?", "", u["comment"])[:110]}' if len(re.sub(r"^[\\|/}\s]+", "", u["comment"])) >= 4 else ""))
                if len(sample) >= 16:
                    break
            chunk.append({"key": anchor(k), "address": fmt(k), "symbol": e["sym"], "uses": len(uses),
                          "reads": modes["R"], "writes": modes["W"], "modifies": modes["M"],
                          "indexed": dict(idx), "pointer_uses": sum(1 for u in uses if u["ptr"]),
                          "routines": len(by_sec), "samples": sample})
        (wd / f"{n:02d}.json").write_text(json.dumps(chunk, indent=1), encoding="utf-8")
        n += 1
    print(f"{len(keys)} addresses with >= {MIN_USES} uses (excluding $00-$0F, above {after:#x}) -> batches {first}..{n - 1} in {wd}")


def check(scanned):
    ann = load_ram_annotations(build.HERE / "ram")
    bad = [k for k in ann if k not in scanned]
    for k in bad:
        print(f"annotation for an address nothing uses: {fmt(k)}")
    want = {k for k, e in scanned.items() if len(e["uses"]) >= MIN_USES and k >= 0x10}
    missing = sorted(want - set(ann))
    print(f"{len(ann)} described, {len(missing)} of {len(want)} wanted addresses still missing"
          + (f" (first: {', '.join(fmt(k) for k in missing[:8])})" if missing else ""))
    empty = [fmt(k) for k, v in ann.items() if not v.get("desc")]
    if empty:
        print("no description text:", ", ".join(empty[:10]))
    print("ok" if not bad and not empty else f"{len(bad) + len(empty)} problems")


if __name__ == "__main__":
    sc = _context()
    if "--batches" in sys.argv:
        args = dict(zip(sys.argv[2:], sys.argv[3:]))
        write_batches(sc, int(args.get("--first", 0)), int(args.get("--after", "-1"), 0))
    if "--check" in sys.argv:
        check(sc)
    if len(sys.argv) == 1:
        print(f"{len(sc)} WRAM addresses, {sum(len(e['uses']) for e in sc.values())} uses")
