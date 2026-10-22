#!/usr/bin/env python3
"""Render the SMW disassembly as per-bank HTML pages, PJ's-bank-logs style.

    python3 bank/build.py [path/to/smw-disasm]   (default: ../pipe-dream/reference/smw-disasm)

Reads bank_XX.asm, merges bank/annotations/*.json (English names, summaries, rewritten
line comments), writes bank/XX.html, index.html, ram.html, search.html, copies graph.html.
Stdlib only.
"""
import html
import json
import re
import shutil
import sys
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
_arg = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None
SRC = Path(_arg) if _arg else HERE.parent.parent / "pipe-dream" / "reference" / "smw-disasm"
ANN = HERE / "annotations"

BANKS = {
    "00": "Boot, main loop, NMI/IRQ, game-mode dispatch, DMA, SPC upload, controller, status bar, Mario state &amp; block interaction",
    "01": "Core sprite engine: main loop, status dispatch, init/main tables, shared sprite subroutines, most enemy mains",
    "02": "More sprite mains, generators, cluster/extended sprites, sprite spawning from level data",
    "03": "Sprite mains $A1&ndash;$C8, bosses (Reznor, Big Boo, Bowser), bank-local utility copies",
    "04": "Overworld engine: game mode 0E, player path movement, event/path reveal, level names, OW sprites",
    "05": "Level loading: header decode, object stream decode, layer 2/3, scroll commands, level pointer tables",
    "06": "Level Layer-1 object data (no code)",
    "07": "Overflow level data, sprite tweaker tables, InitSpriteTables, sine table, misc sprite support",
    "0C": "OW Map16 definitions, cutscene/credits/enemy-parade engine, OW Layer-1 tilemaps",
    "0D": "Map16 16&times;16 definitions, object draw-routine dispatch + tile-writing primitives, credits enemy names, freespace",
}
# Raw data banks the dump appends to the end of bank_07.asm (after ".BANK 8") and bank_0D.asm (after ".BANK 14").
DATA_BANKS = {
    "07": [("08", "Graphics (GFX00&ndash;GFX0F, 4bpp/3bpp tiles)"), ("09", "Graphics (GFX10&ndash;GFX1F)"),
           ("0A", "Graphics (GFX20&ndash;GFX2F)"), ("0B", "Graphics (GFX30&ndash;GFX31, Mario/Yoshi tiles)")],
    "0D": [("0E", "Music data + SPC700 sound engine (uploaded to the APU at boot)"), ("0F", "BRR sample data for the SPC700")],
}
GITHUB = "https://github.com/john-sparwasser/pipe-dream/blob/main/reference/smw-disasm"

AUTO = re.compile(r"^(CODE|DATA|ADDR|Return|Empty)_?([0-9A-F]{6})$")
TRAIL6 = re.compile(r"([0-9A-F]{6})$")
HEXCOL = re.compile(r"^((?:[0-9A-F]{2} )+)\s*(.*)$")
LABEL = re.compile(r"^(\S+?):\s*(.*)$")
TOKEN = re.compile(r"(?<![\w$#])([A-Za-z_][A-Za-z0-9_+&?]*)")
ADDR6 = re.compile(r"\$([0-9A-F]{2})([89A-F][0-9A-F]{3})\b")
BRANCH_TGT = re.compile(r"\[\$([0-9A-F]{4})\]")
RAMHEX = re.compile(r"(?<![\w$#:;])\$(?:(7[EF]):)?([0-9A-F]{4}|[0-9A-F]{2})(?![0-9A-F:])(?!,s\b)")
HWREG = re.compile(r"\$((?:21[0-4][0-9A-F])|(?:42[01][0-9A-F])|(?:43[0-7][0-9A-F]))\b")
CODE_COL = 32   # width of the instruction field; comments start in the same column on every row (~97% of rows fit)
WRAP = 110      # wrap ;; summary text at this width
CALLS = {"JSR", "JSL", "JMP", "JML"}
FLOW_END = {"RTS", "RTL", "RTI", "JMP", "JML", "BRA", "BRL"}

PPU = {
    0x2100: "INIDISP: screen display / brightness", 0x2101: "OBSEL: OBJ size and tile base", 0x2102: "OAMADDL", 0x2103: "OAMADDH",
    0x2104: "OAMDATA: OAM write", 0x2105: "BGMODE: BG mode / tile size", 0x2106: "MOSAIC", 0x2107: "BG1SC: BG1 tilemap address",
    0x2108: "BG2SC: BG2 tilemap address", 0x2109: "BG3SC: BG3 tilemap address", 0x210A: "BG4SC", 0x210B: "BG12NBA: BG1/2 chr base",
    0x210C: "BG34NBA: BG3/4 chr base", 0x210D: "BG1HOFS: BG1 H scroll", 0x210E: "BG1VOFS: BG1 V scroll", 0x210F: "BG2HOFS",
    0x2110: "BG2VOFS", 0x2111: "BG3HOFS", 0x2112: "BG3VOFS", 0x2113: "BG4HOFS", 0x2114: "BG4VOFS", 0x2115: "VMAIN: VRAM increment mode",
    0x2116: "VMADDL: VRAM address low", 0x2117: "VMADDH: VRAM address high", 0x2118: "VMDATAL: VRAM write low", 0x2119: "VMDATAH: VRAM write high",
    0x211A: "M7SEL: mode 7 settings", 0x211B: "M7A", 0x211C: "M7B", 0x211D: "M7C", 0x211E: "M7D", 0x211F: "M7X: mode 7 center X",
    0x2120: "M7Y: mode 7 center Y", 0x2121: "CGADD: CGRAM address", 0x2122: "CGDATA: CGRAM write", 0x2123: "W12SEL: window mask BG1/2",
    0x2124: "W34SEL: window mask BG3/4", 0x2125: "WOBJSEL: window mask OBJ/color", 0x2126: "WH0: window 1 left", 0x2127: "WH1: window 1 right",
    0x2128: "WH2: window 2 left", 0x2129: "WH3: window 2 right", 0x212A: "WBGLOG", 0x212B: "WOBJLOG", 0x212C: "TM: main screen layers",
    0x212D: "TS: sub screen layers", 0x212E: "TMW: main screen window mask", 0x212F: "TSW: sub screen window mask",
    0x2130: "CGWSEL: color math control A", 0x2131: "CGADSUB: color math control B", 0x2132: "COLDATA: fixed color",
    0x2133: "SETINI: screen mode select", 0x2134: "MPYL", 0x2135: "MPYM", 0x2136: "MPYH", 0x2137: "SLHV: latch H/V counter",
    0x2138: "OAMDATAREAD", 0x2139: "VMDATALREAD", 0x213A: "VMDATAHREAD", 0x213B: "CGDATAREAD", 0x213C: "OPHCT", 0x213D: "OPVCT",
    0x213E: "STAT77", 0x213F: "STAT78", 0x2140: "APUIO0: SPC700 port 0", 0x2141: "APUIO1: SPC700 port 1", 0x2142: "APUIO2: SPC700 port 2",
    0x2143: "APUIO3: SPC700 port 3", 0x2180: "WMDATA: WRAM data port", 0x2181: "WMADDL", 0x2182: "WMADDM", 0x2183: "WMADDH",
    0x4016: "JOYSER0: joypad 1 serial", 0x4017: "JOYSER1: joypad 2 serial",
    0x4200: "NMITIMEN: NMI / IRQ / auto-joypad enable", 0x4201: "WRIO", 0x4202: "WRMPYA: multiplicand", 0x4203: "WRMPYB: multiplier (starts 8x8 multiply)",
    0x4204: "WRDIVL: dividend low", 0x4205: "WRDIVH: dividend high", 0x4206: "WRDIVB: divisor (starts 16/8 divide)",
    0x4207: "HTIMEL: H-count IRQ timer low", 0x4208: "HTIMEH", 0x4209: "VTIMEL: V-count IRQ timer low", 0x420A: "VTIMEH",
    0x420B: "MDMAEN: start DMA channels", 0x420C: "HDMAEN: enable HDMA channels", 0x420D: "MEMSEL: FastROM", 0x4210: "RDNMI: NMI flag (read to ack)",
    0x4211: "TIMEUP: IRQ flag (read to ack)", 0x4212: "HVBJOY: V-blank / H-blank / joypad-busy flags", 0x4213: "RDIO",
    0x4214: "RDDIVL: quotient low", 0x4215: "RDDIVH: quotient high", 0x4216: "RDMPYL: product / remainder low", 0x4217: "RDMPYH",
    0x4218: "JOY1L: joypad 1 low", 0x4219: "JOY1H: joypad 1 high", 0x421A: "JOY2L", 0x421B: "JOY2H", 0x421C: "JOY3L", 0x421D: "JOY3H",
    0x421E: "JOY4L", 0x421F: "JOY4H",
}
_DMA = ["DMAPx: DMA control (direction/mode)", "BBADx: B-bus address ($21xx)", "A1TxL: A-bus address low", "A1TxH: A-bus address high",
        "A1Bx: A-bus bank", "DASxL: byte count low", "DASxH: byte count high", "DASBx: HDMA indirect bank", "A2AxL: HDMA table address low",
        "A2AxH: HDMA table address high", "NTRLx: HDMA line counter", "UNUSEDx"]
for _ch in range(8):
    for _i, _n in enumerate(_DMA):
        PPU[0x4300 + _ch * 0x10 + _i] = _n.replace("x", str(_ch)) + f" (channel {_ch})"


def is_named(label):
    return not AUTO.match(label) and not label.startswith("$")


def label_addr(label, bank):
    """Address encoded in the label (CODE_01800B, Ptrs009329, $008000), if in this bank."""
    if label.startswith("$") and len(label) == 7:
        return int(label[1:], 16)
    m = TRAIL6.search(label)
    if m and m.group(1)[:2] == bank:
        return int(m.group(1), 16)
    return None


def data_bytes(code):
    """Byte count of a .db/.dw row that has no hex column."""
    m = re.match(r"\.d([bw])\s+(.*)$", code.strip())
    if not m:
        return 0
    size = 1 if m.group(1) == "b" else 2
    items = [i for i in m.group(2).split(",") if i.strip()]
    return size * len(items) + (1 if " .db " in m.group(2) else 0)  # ".dw X .db :$X" long pointers


class Line:
    __slots__ = ("label", "addr", "hex", "code", "comment", "raw", "kind", "mn", "no")

    def __init__(self, raw, no):
        self.label = self.addr = self.hex = None
        self.code = self.comment = self.mn = ""
        self.raw, self.kind, self.no = raw, "raw", no


def parse_bank(path, bank):
    """-> (lines of this bank, trailing raw data rows appended after a .BANK directive)."""
    lines, tail, next_addr, in_tail = [], [], None, False
    for no, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        ln = Line(raw, no)
        s = raw.lstrip()
        if s.startswith(".BANK"):
            in_tail = True
            continue
        if in_tail:
            if ".db" in s:
                tail.append(s.split(".db", 1)[1].split(";")[0].strip())
            continue
        if not s:
            ln.kind = "blank"
        elif s.startswith(";"):
            ln.kind, ln.comment = "comment", s
        else:
            m = LABEL.match(s)
            if m and not s.startswith("."):
                ln.label, rest = m.group(1), m.group(2)
                a = label_addr(ln.label, bank)
                ln.addr = a if a is not None else next_addr
            elif raw[:1].isspace() and (HEXCOL.match(s) or s.startswith(".d")):
                ln.addr, rest = next_addr, s
            else:
                lines.append(ln)  # stray prose: consumes no bytes
                continue
            hm = HEXCOL.match(rest)
            if hm:
                ln.hex, rest = hm.group(1).strip(), hm.group(2)
            code, _, comment = rest.partition(";")
            ln.code, ln.comment, ln.kind = code.rstrip(), comment.rstrip(), "asm"
            ln.mn = ln.code.strip().split(" ")[0].split(".")[0].upper() if ln.code.strip() else ""
            nbytes = len(ln.hex.split()) if ln.hex else data_bytes(ln.code)
            next_addr = ln.addr + nbytes if ln.addr is not None and nbytes else None
        lines.append(ln)
    return lines, tail


def data_bank_lines(rows, bank):
    """Synthesize Line objects for a raw data bank from ".db" item strings (8 bytes/row)."""
    out, addr = [], int(bank, 16) << 16 | 0x8000
    for r in rows:
        ln = Line("", 0)
        ln.kind, ln.addr, ln.code, ln.mn = "asm", addr, f".db {r}", ".DB"
        if addr & 0xFFF == 0:
            ln.label = f"DATA_{addr:06X}"
        out.append(ln)
        addr += len([i for i in r.split(",") if i.strip()])
    return out


def sections(lines):
    """Split a bank into sections: every named label starts one. Runs of DATA_/Empty rows
    after a control-flow end (RTS/JMP/...) become 'Data'/'Freespace' sections; a multi-row
    table gets its own. Code resuming after data without a name is '(unnamed code)'."""
    out, cur, prev_asm = [], None, None

    def start(title, kind, ln):
        nonlocal cur
        anchor = ln.label if ln.label and is_named(ln.label) else f"s{ln.addr:06X}" if ln.addr is not None else f"s{len(out)}"
        cur = {"title": title, "kind": kind, "anchor": anchor, "lines": []}
        out.append(cur)

    for ln in lines:
        if ln.kind == "asm" and ln.label:
            if is_named(ln.label):
                start(ln.label, "code", ln)
            else:
                m = AUTO.match(ln.label)
                want = {"DATA": "data", "Empty": "free"}.get(m.group(1) if m else "", "code")
                ended = prev_asm is None or prev_asm.mn in FLOW_END or prev_asm.mn.startswith(".")
                multirow = cur and cur["kind"] == want == "data" and prev_asm and prev_asm.label is None
                if cur is None or (want != "code" and cur["kind"] != want and ended) or \
                        (want == "code" and cur["kind"] != "code") or multirow:
                    start({"data": "Data", "free": "Freespace", "code": "(unnamed code)"}[want], want, ln)
        elif cur is None:
            start("(preamble)", "code", ln)
        cur["lines"].append(ln)
        if ln.kind == "asm":
            prev_asm = ln
    for s in out:
        addrs = [l.addr for l in s["lines"] if l.addr is not None]
        s["start"], s["end"] = (addrs[0], addrs[-1]) if addrs else (None, None)
    return out


def parse_all():
    """-> {bank: sections} for the code banks plus the appended raw data banks."""
    parsed, tails = {}, {}
    for b in BANKS:
        p = SRC / f"bank_{b}.asm"
        if not p.exists():
            sys.exit(f"missing {p}")
        lines, tail = parse_bank(p, b)
        parsed[b] = sections(lines)
        tails[b] = tail
    for host, subs in DATA_BANKS.items():
        rows, per = tails.get(host, []), 0x8000 // 8
        for i, (b, _) in enumerate(subs):
            chunk = rows[i * per:(i + 1) * per]
            if chunk:
                parsed[b] = sections(data_bank_lines(chunk, b))
    return parsed


def load_annotations():
    """Merge bank/annotations/*.json -> (names[(bank, anchor)] = {name, summary}, comments[(bank, addr)] = text)."""
    names, comments = {}, {}
    for f in sorted(ANN.glob("*.json")) if ANN.exists() else []:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"skip {f.name}: {e}", file=sys.stderr)
            continue
        b = d.get("bank")
        for anchor, v in d.get("sections", {}).items():
            if isinstance(v, dict) and (v.get("name") or v.get("summary")):
                names[(b, anchor)] = v
        for a, c in d.get("lines", {}).items():
            try:
                comments[(b, int(a, 16))] = str(c).strip()
            except ValueError:
                pass
    return names, comments


def main():
    parsed = parse_all()
    names, comments = load_annotations()
    all_banks = {**BANKS, **{b: d for subs in DATA_BANKS.values() for b, d in subs}}

    symbols = defaultdict(set)      # named label -> {banks defining it}
    sec_at = {}                     # (bank, addr) -> section anchor
    addrs = defaultdict(set)        # bank -> {16-bit addresses that have a line}
    for b, secs in parsed.items():
        for s in secs:
            if s["start"] is not None:
                sec_at.setdefault((b, s["start"]), s["anchor"])
            for ln in s["lines"]:
                if ln.addr is not None:
                    addrs[b].add(ln.addr & 0xFFFF)
                if ln.label and is_named(ln.label):
                    symbols[ln.label].add(b)

    def title_of(b, s):
        n = names.get((b, s["anchor"]), {}).get("name")
        return f'{n} ({s["title"]})' if n and s["kind"] == "code" and not s["title"].startswith("(") else (n or s["title"])

    def resolve(tok, bank):
        """Label token -> (href, text, (bank, section anchor or None)) or None."""
        base, suffix = tok, ""
        m = re.match(r"^(.*?)([+-]\d+)$", tok)
        if m and (m.group(1) in symbols or AUTO.match(m.group(1))):
            base, suffix = m.group(1), m.group(2)
        am = AUTO.match(base)
        if am:
            tb, lo = am.group(2)[:2], am.group(2)[2:]
            if tb not in parsed or int(lo, 16) not in addrs[tb]:
                return None  # dangling auto label: leave as text
            href = f"#{lo}" if tb == bank else f"{tb}.html#{lo}"
            return href, f"${lo}{suffix}", (tb, sec_at.get((tb, int(am.group(2), 16))))
        if base in symbols:
            tb = bank if bank in symbols[base] else sorted(symbols[base])[0]
            href = f"#{base}" if tb == bank else f"{tb}.html#{base}"
            return href, base + suffix, (tb, base)
        return None

    # Every WRAM address the code touches, with its call sites (see ramscan.py), plus written descriptions.
    sys.path.insert(0, str(HERE))  # python -I does not put the script's folder on the path
    import ramscan
    ram = ramscan.scan(parsed, lambda b, s: names.get((b, s["anchor"]), {}).get("name") or s["title"])
    for e in ram.values():
        for u in e["uses"]:
            u["comment"] = comments.get((u["bank"], u["addr"]), u["comment"]).strip()
    ram_ann = ramscan.load_ram_annotations(HERE / "ram")
    sym_key = {}
    for key, e in sorted(ram.items()):
        for sym in e["syms"]:
            sym_key.setdefault(sym, key)

    def ram_link(key, text):
        t = ram_ann.get(key, {}).get("name")
        return f'<a class=ram href="ram.html#{ramscan.anchor(key)}"{f" title={chr(34)}{html.escape(t)}{chr(34)}" if t else ""}>{text}</a>'

    def plain(seg, regs=True, prose=False):
        """Escape a text segment; link raw RAM addresses ($1540, $0094, $7E:B900) that have a RAM map entry.
        In prose a bare two-digit $xx is usually a value ("timer = $40"), so only [$xx] is linked there."""
        seg = html.escape(seg)
        if not regs:
            return seg

        def sub(m):
            key = int(m.group(2), 16) if not m.group(1) else int(m.group(1), 16) << 16 | int(m.group(2), 16)
            if prose and not m.group(1) and len(m.group(2)) == 2 and m.string[max(0, m.start() - 1):m.start()] != "[":
                return m.group(0)
            if key in ram:
                return ram_link(key, m.group(0))
            return m.group(0)
        return RAMHEX.sub(sub, seg)

    def linkify(text, bank, regs=False):
        """Escape text; link known labels, RAM_ symbols and $BBAAAA addresses; title hardware registers."""
        pieces, pos = [], 0
        for m in TOKEN.finditer(text):
            tok, rep = m.group(1), None
            if tok.startswith("RAM_"):
                base = tok.split("+")[0]
                key = sym_key.get(base)
                if key is None:
                    continue
                rep = ram_link(key, html.escape(tok))
            elif (r := resolve(tok, bank)):
                rep = f'<a href="{html.escape(r[0])}">{html.escape(r[1])}</a>'
            if rep:
                pieces += [plain(text[pos:m.start()], regs), rep]
                pos = m.end()
        pieces.append(plain(text[pos:], regs))
        out = "".join(pieces)
        out = ADDR6.sub(lambda m: f'<a href="{m.group(1)}.html#{m.group(2)}">{m.group(0)}</a>'
                        if m.group(1) in parsed and int(m.group(2), 16) in addrs[m.group(1)] else m.group(0), out)
        if regs:
            out = HWREG.sub(lambda m: f'<span class=hw title="{html.escape(PPU[int(m.group(1), 16)])}">{m.group(0)}</span>'
                            if int(m.group(1), 16) in PPU else m.group(0), out)
        return out

    # Pass 1: callers of each section, RAM symbol addresses (from the operand bytes).
    callers = defaultdict(list)                 # (bank, anchor) -> [(bank, addr, title)]
    for b, secs in parsed.items():
        for s in secs:
            for ln in s["lines"]:
                if ln.kind != "asm" or not ln.code:
                    continue
                opnd = ln.code.strip().partition(" ")[2].strip()
                tm = TOKEN.search(opnd)
                if not tm:
                    continue
                tok = tm.group(1)
                if tok.startswith("RAM_"):
                    continue
                if ln.mn in CALLS and ln.addr is not None:
                    r = resolve(tok, b)
                    if r and r[2][1]:
                        callers[r[2]].append((b, ln.addr, s))

    head = lambda title: (f'<!DOCTYPE html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width">'
                          f'<title>{title}</title><link rel=stylesheet href="bank.css"><script defer src="bank.js"></script></head><body>')
    nav = ('<div id=header><a href=".">Index</a> &mdash; <a href="ram.html">RAM map</a> &mdash; <a href="graph.html">Call graph</a>'
           ' &mdash; <a href="#" onclick="toggleDark();return false;">Toggle dark mode</a>'
           ' &mdash; <input id=q placeholder="Search regex (this bank)" size=26> <button onclick="clearSearch()">Clear</button>'
           ' &mdash; <a href="search.html">Search all banks</a></div>')

    def render_line(ln, b):
        if ln.kind == "blank":
            return ""
        if ln.kind == "comment":
            return f'<span class=c>{linkify(ln.comment, b)}</span>'
        if ln.kind == "raw":  # stray prose left in the dump: show it as a comment, not bare text
            return f'<span class=c>; {html.escape(ln.raw.strip())}</span>'
        idattr = f' id="{ln.addr & 0xFFFF:04X}"' if ln.addr is not None else ""
        addr = f'<span class=rom>${b}:{ln.addr & 0xFFFF:04X}</span>' if ln.addr is not None else " " * 8
        code = ln.code.strip()
        codeh = ""
        if code:
            mn, _, opnd = code.partition(" ")
            codeh = f'<span class={"d" if mn.startswith(".") else "op"}>{html.escape(mn)}</span> {linkify(opnd.strip(), b, regs=True)}'
            codeh = BRANCH_TGT.sub(lambda m: f'[<a href="#{m.group(1)}">${m.group(1)}</a>]'
                                   if int(m.group(1), 16) in addrs[b] else m.group(0), codeh)
        comment = comments.get((b, ln.addr), ln.comment) if ln.addr is not None and code else ln.comment
        if comment and (b, ln.addr) in comments and not comment.startswith(" "):
            comment = " " + comment
        if not code and not ln.hex:  # label-only row: the section header already shows it
            return f'<span class=c>;{linkify(comment, b)}</span>' if comment else None
        vis = len(html.unescape(re.sub(r"<[^>]+>", "", codeh)))  # visible width: links shorten labels
        pad = " " * max(1, CODE_COL - vis) if comment else ""
        com = f'<span class=c>;{linkify(comment, b)}</span>' if comment else ""
        # Address and opcode bytes sit in an unselectable gutter, so a copied block is just the code and comments.
        # Each column is its own span so bank.css can tint it as a band.
        return (f'<span{idattr} class=l><span class=gut>{addr} <span class=hx>{(ln.hex or ""):<12}</span> </span>'
                f'<span class=cd>{codeh}{pad}</span>{com}</span>')

    named_count = 0
    for b, secs in parsed.items():
        toc, body = [], []
        for s in secs:
            lo = f"${s['start'] & 0xFFFF:04X}" if s["start"] is not None else "$????"
            rng = lo if s["kind"] == "code" or s["end"] is None else f"{lo}..{s['end'] & 0xFFFF:04X}"
            title, anchor = html.escape(title_of(b, s)), html.escape(s["anchor"])
            ann = names.get((b, s["anchor"]), {})
            named_count += bool(ann.get("name"))
            toc.append(f';;; <a href="#{anchor}">{rng}</a>: {title} ;;;')
            body += [f'<span class=c>;;; <a id="{anchor}" href="#{anchor}">{rng}</a>: {title} ;;;</span>', "{"]
            summary = ann.get("summary") or []
            if isinstance(summary, str):
                summary = summary.splitlines()
            for l in summary:
                l = str(l).rstrip()
                if not l.strip():
                    continue
                indent = len(l) - len(l.lstrip())  # keep "Parameters:" style indents, wrap with a hanging one
                for i, w in enumerate(textwrap.wrap(l.strip(), WRAP - 3 - indent) or [""]):
                    body.append(f'<span class=c>;; {" " * (indent + (4 if i else 0))}{linkify(w, b)}</span>')
            seen, parts = set(), []
            for cb, ca, cs in callers.get((b, s["anchor"]), []):
                if (cb, ca) not in seen:
                    seen.add((cb, ca))
                    href = f"#{ca & 0xFFFF:04X}" if cb == b else f"{cb}.html#{ca & 0xFFFF:04X}"
                    parts.append(f'<a href="{href}">${cb}:{ca & 0xFFFF:04X}</a>: {html.escape(title_of(cb, cs))}')
            if parts:
                body.append('<span class=c>;; Called by:</span>')
                body += [f'<span class=c>;;     {p}</span>' for p in parts[:12]]
                if len(parts) > 12:
                    body.append(f'<span class=c>;;     ... and {len(parts) - 12} more</span>')
            body += [r for r in (render_line(ln, b) for ln in s["lines"]) if r is not None] + ["}", ""]
        page = (f'{head(f"SMW ${b}")}\n{nav}\n<div id=body><div id=left><pre id=toc>{chr(10).join(toc)}</pre>'
                f'<pre id=results hidden></pre></div>\n<div id=right><pre>{chr(10).join(body)}</pre></div></div>\n</body></html>')
        (HERE / f"{b}.html").write_text(page, encoding="utf-8")
        print(f"{b}.html  {len(secs):5} sections  {len(page) / 1e6:.1f} MB")

    # RAM map: what each address does, then a collapsed list of every instruction that touches it.
    def desc_html(lines):
        """Join wrapped description lines into paragraphs; Values:/Bits:/Bit N lines start their own row."""
        rows, cur = [], []
        for l in lines:
            l = str(l).strip()
            if not l:
                continue
            if cur and re.match(r"^(Values?:|Bits?:|Bit \d|\d+\s*[-:=]|\$[0-9A-F]+\s*[-:=]|[-*] )", l):
                rows.append(cur)
                cur = [l]
            else:
                cur.append(l)
        if cur:
            rows.append(cur)
        return "".join(f"<p>{plain(' '.join(r), prose=True)}</p>" for r in rows)

    def use_row(u):
        com = re.sub(r"^[\\|/}\s]+", "", u["comment"])
        mode = {"R": "R", "W": "W", "M": "RW"}[u["mode"]]
        return (f'<div class=u><span class="m m{mode}">{mode}</span> '
                f'<a href="{u["bank"]}.html#{u["addr"] & 0xFFFF:04X}">${u["bank"]}:{u["addr"] & 0xFFFF:04X}</a> '
                f'<code>{html.escape(u["code"])}</code>'
                f'{f" <span class=c>; {html.escape(com[:110])}</span>" if len(com) >= 4 else ""}</div>')

    # Alternate "by section" view: first topic whose pattern hits the name, else the description.
    topics = [("Cape", r"cape"), ("Yoshi", r"yoshi"), ("Bowser", r"bowser"), ("Credits", r"credit"),
              ("Bonus game", r"bonus"), ("Score and coins", r"score|coin|lives|1-?up"), ("Controller input", r"joypad|button|controller"),
              ("Overworld", r"overworld|submap|translevel"), ("OAM and graphics", r"\boam\b|palette|color|tile|stripe|vram|graphics|dma|hdma|window"),
              ("Layer scrolling", r"layer|scroll|screen|camera"), ("Extended and cluster sprites", r"extended|cluster|minor|smoke|bounce|shooter"),
              ("Sprites", r"sprite"), ("Mario", r"mario|player|pose|powerup|\bpow"), ("Timers", r"timer|counter|delay"),
              ("Level and blocks", r"level|block|object|platform|map16"), ("Audio", r"music|sound|spc|\bapu")]
    def section_of(name, desc):
        for text in (name.lower(), " ".join(desc).lower()):
            for t, pat in topics:
                if re.search(pat, text):
                    return t
        return "Other"
    ram_blocks, described, page_first = [], 0, {}
    for key in sorted(ram):
        e, a = ram[key], ram_ann.get(key, {})
        uses = e["uses"]
        modes = Counter(u["mode"] for u in uses)
        groups = defaultdict(list)
        for u in sorted(uses, key=lambda u: (u["bank"], u["addr"])):
            groups[(u["bank"], u["anchor"], u["sec"])].append(u)
        use_html = "".join(
            f'<div class=g><a href="{gb}.html#{html.escape(ga)}">${gb} {html.escape(gt)}</a> '
            f'<span class=n>{len(us)}x</span></div>' + "".join(use_row(u) for u in us)
            for (gb, ga, gt), us in groups.items())
        name = a.get("name") or (e["sym"] and e["sym"][4:]) or ""
        has_desc = bool(a.get("desc"))
        described += has_desc
        aliases = "".join(f'<a id="{html.escape(s)}"></a>' for s in sorted(e["syms"]))
        syms = " ".join(f"<code>{html.escape(s)}</code>" for s in sorted(e["syms"]))
        counts = ", ".join(f"{modes[m]} {w}" for m, w in (("R", "read"), ("W", "write"), ("M", "read-modify-write")) if modes[m])
        q = " ".join([ramscan.fmt(key), name, " ".join(e["syms"]), " ".join(a.get("desc", []))]).lower()
        ram_blocks.append(
            f'<section class=rv id="{ramscan.anchor(key)}" data-s="{section_of(name, a.get("desc", []))}" data-q="{html.escape(q, quote=True)}">{aliases}'
            f'<h3><a class=addr href="#{ramscan.anchor(key)}">{ramscan.fmt(key)}</a> '
            f'{f"<b>{html.escape(name)}</b>" if name else ""} {syms}'
            f'{f" <span class=kind>{html.escape(a["kind"])}</span>" if a.get("kind") else ""}</h3>'
            + (f'<div class=desc>{desc_html(a["desc"])}</div>' if has_desc else
               '<p class=none>No description written yet. The instructions below show how it is used.</p>')
            + f'<details><summary>{len(uses)} use{"s" if len(uses) != 1 else ""} in {len(groups)} '
              f'routine{"s" if len(groups) != 1 else ""} ({counts})</summary><div class=uses>{use_html}</div></details></section>')
        page_first.setdefault(key >> 8 if key < 0x10000 else key >> 16, ramscan.anchor(key))
    jump = " ".join(f'<a href="#{page_first[p]}">${p:02X}{"xx" if p < 0x100 else ":xxxx"}</a>' for p in sorted(page_first))
    (HERE / "ram.html").write_text(f"""{head("SMW RAM map")}
{nav}
<div class="page wide"><h1>RAM map</h1>
<p>Every byte of work RAM the code reads or writes, found from the instruction operands. Each entry says what the address
holds and how it is used, then lists every instruction that touches it (expand the list; <b>R</b> reads, <b>W</b> writes,
<b>RW</b> modifies in place). <code>$00xx</code> is the direct page, <code>$0100</code> and up is normal RAM, and
<code>$7E:</code> and <code>$7F:</code> are the extended areas. {len(ram_blocks)} addresses, {described} with a written description.
Descriptions were drafted from the code with Claude. Where the code only shows <i>how</i> a byte is used and not <i>why</i>, the
text says so.</p>
<p><input id=rq placeholder="Filter by address, name or words (e.g. 1540, timer, yoshi)" size=48 autofocus>
<span id=rcount></span>
View: <label><input type=radio name=rview value=addr checked> by address</label>
<label><input type=radio name=rview value=sect> by section</label></p>
<p class=jump>{jump}</p>
{"".join(ram_blocks)}
</div></body></html>""", encoding="utf-8")

    # Cross-bank search: fetches every bank page client-side and scans it.
    bank_list = json.dumps(sorted(parsed))
    (HERE / "search.html").write_text(f"""{head("SMW search")}
<div id=header><a href=".">Index</a> &mdash; <a href="#" onclick="toggleDark();return false;">Toggle dark mode</a>
 &mdash; <input id=qa placeholder="Search regex, all banks" size=30> <button onclick="searchAll()">Search</button> <span id=status></span></div>
<div id=right><pre id=all></pre></div>
<script>const BANKS={bank_list};</script>
</body></html>""", encoding="utf-8")

    # Index
    items = "".join(f'<p><code>$<a href="{b}.html">{b}</a></code> &ndash; {d}</p>' for b, d in sorted(all_banks.items()) if b in parsed)
    nsec = sum(len(s) for s in parsed.values())
    (HERE / "index.html").write_text(f"""{head("SMW bank logs")}
<div id=header><a href="/">pipedream.nexus</a> &mdash; <a href="search.html">Search all banks</a> &mdash; <a href="#" onclick="toggleDark();return false;">Toggle dark mode</a></div>
<div class=page>
<h1>Super Mario World &ndash; choose a bank</h1>
<p>The community <a href="https://www.smwcentral.net/?p=section&amp;a=details&amp;id=4352">SMWDisC</a> disassembly, split per bank and
rendered as browsable logs in the style of <a href="https://patrickjohnston.org/bank/index.html">PJ's Super Metroid bank logs</a>.
Every <code>JSR</code>/<code>JSL</code>/branch target and every named table is a link; each routine lists its callers; hardware
registers show their name on hover. {nsec} sections across {len(parsed)} banks, {named_count} with English names and summaries.</p>
{items}
<h2>Additional</h2>
<ul>
<li><a href="search.html">Search all banks</a> &ndash; one regex across every page</li>
<li><a href="ram.html">RAM map</a> &ndash; what every RAM address does, with the instructions that touch it</li>
<li><a href="graph.html">Call graph</a> &ndash; interactive graph of the named routines (735 nodes, 53 communities)</li>
<li>Notes: <a href="{GITHUB}/SYSTEM_NOTES.md">system</a>, <a href="{GITHUB}/SNES_HARDWARE_NOTES.md">SNES hardware</a>,
<a href="{GITHUB}/LEVEL_PIPELINE_NOTES.md">level pipeline</a>, <a href="{GITHUB}/SPRITE_ENGINE_NOTES.md">sprite engine</a></li>
<li><a href="{GITHUB}">Source bank_XX.asm files</a></li>
</ul>
<h2>Credits</h2>
<p>SMWDisC was written on etherpad by Smallhacker, 1024, lolcats439, Roy, YoshiCookieZeus, Imamelia, Nicol Bolas, Buster Beetle,
Gekko, Kernigh, Maxx, Edit1754, Alcaro and others; all.log by MikeyK250. English routine names, summaries and rewritten comments
were produced with Claude and reviewed against the code. Super Mario World is &copy; Nintendo.</p>
</div></body></html>""", encoding="utf-8")

    g = SRC / "graph" / "graph.html"
    if g.exists():
        shutil.copy(g, HERE / "graph.html")
    print(f"ram.html  {len(ram_blocks)} addresses ({described} described); {named_count} named sections; "
          f"{len(comments)} overlay comments; index.html + search.html written")


if __name__ == "__main__":
    main()
