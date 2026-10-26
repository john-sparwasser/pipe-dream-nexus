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

AUTO = re.compile(r"^(CODE|DATA|ADDR|Return|Empty)_?([0-9A-F]{6})$")
TRAIL6 = re.compile(r"([0-9A-F]{6})$")
HEXCOL = re.compile(r"^((?:[0-9A-F]{2} )+)\s*(.*)$")
LABEL = re.compile(r"^(\S+?):\s*(.*)$")
TOKEN = re.compile(r"(?<![\w$#])([A-Za-z_][A-Za-z0-9_+&?]*)")
ADDR6 = re.compile(r"\$([0-9A-F]{2})([89A-F][0-9A-F]{3})\b")
BRANCH_TGT = re.compile(r"\[\$([0-9A-F]{4})\]")
RAMHEX = re.compile(r"(?<![\w$#:;])\$(?:(7[EF]):)?([0-9A-F]{4}|[0-9A-F]{2})(?![0-9A-F:])(?!,s\b)")
HWREG = re.compile(r"\$((?:21[0-4][0-9A-F])|(?:42[01][0-9A-F])|(?:43[0-7][0-9A-F]))\b")
SRC_HEX_COL, SRC_CODE_COL, SRC_COM_COL = 20, 34, 60  # columns of the source .asm: hex bytes, instruction, comment
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


NOTES = {"SYSTEM_NOTES": "system", "SNES_HARDWARE_NOTES": "SNES hardware",
         "LEVEL_PIPELINE_NOTES": "level pipeline", "SPRITE_ENGINE_NOTES": "sprite engine"}
notes_page = lambda stem: "notes-" + stem[:-len("_NOTES")].lower().replace("_", "-") + ".html"
# Lunar Magic write-ups. Like the notes and tool pages, their markdown lives in bank/docs.
LM_DOCS = {"LM_HOOKS": "hooks", "CONTRACT": "ROM format contract", "LM_PARITY": "what LM writes",
           "EXANIMATION": "ExAnimation", "OVERWORLD": "overworld", "LM_FILE_FORMATS": "file formats"}
lm_page = lambda stem: "lm-" + stem.lower().replace("lm_", "").replace("_", "-") + ".html"
# Tool pages: bank/docs/TOOL_<KEY>.md each.
TOOLS = {"PIXI": "PIXI", "ADDMUSICK": "AddmusicK", "GPS": "GPS"}
tool_of = {"TOOL_" + k: k.lower() for k in TOOLS}


def doc_page(stem):
    if stem in tool_of:
        return f"tool-{tool_of[stem]}.html"
    return notes_page(stem) if stem in NOTES else lm_page(stem)


def md_inline(t, post):
    """Inline markdown: `code`, **bold**, *italic*. post() adds links to the escaped text."""
    codes = []  # code spans are set aside first, so **bold** and *italic* can wrap them

    def stash(m):
        codes.append(f"<code>{post(html.escape(m.group(1)))}</code>")
        return f"\0{len(codes) - 1}\0"
    t = html.escape(re.sub(r"`([^`]*)`", stash, t), quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![*\w])\*(?![\s*])(.+?)(?<![\s*])\*(?![*\w])", r"<i>\1</i>", t)
    return re.sub(r"\0(\d+)\0", lambda m: codes[int(m.group(1))], post(t))


def md_to_html(text, post=lambda s: s):
    """Just enough markdown for the notes files: headings, paragraphs, nested lists, tables, code fences.
    ponytail: hand-rolled because no markdown package is installed; swap in one if the notes outgrow this."""
    lines, out, para, i = text.splitlines(), [], [], 0
    inl = lambda t: md_inline(t, post)
    item = re.compile(r"^(\s*)([-*]|(\d+)\.)\s+(.*)")

    def flush():
        if para:
            out.append(f"<p>{inl(' '.join(para))}</p>")
            para.clear()

    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            flush(); i += 1
        elif ln.startswith("```"):
            flush()
            j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("```")), len(lines))
            out.append(f"<pre class=md>{html.escape(chr(10).join(lines[i + 1:j]))}</pre>")
            i = j + 1
        elif m := re.match(r"^(#{1,6})\s+(.*)", ln):
            flush()
            n, slug = len(m.group(1)), re.sub(r"[^a-z0-9]+", "-", m.group(2).lower()).strip("-")
            out.append(f"<h{n} id=\"{slug}\">{inl(m.group(2))}</h{n}>")
            i += 1
        elif ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|\s*$", lines[i + 1]):
            flush()
            cells = lambda r: [c.strip() for c in re.split(r"\|(?=(?:[^`]*`[^`]*`)*[^`]*$)", r.strip().strip("|"))]  # not in `code`
            rows = [f"<tr>{''.join(f'<th>{inl(c)}</th>' for c in cells(ln))}</tr>"]
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(f"<tr>{''.join(f'<td>{inl(c)}</td>' for c in cells(lines[i]))}</tr>")
                i += 1
            out.append(f"<table>{''.join(rows)}</table>")
        elif item.match(ln):
            flush()
            items = []  # [indent, tag, start, text]
            while i < len(lines) and lines[i].strip():
                m = item.match(lines[i])
                if m:
                    items.append([len(m.group(1)), "ol" if m.group(3) else "ul", m.group(3), m.group(4)])
                else:  # continuation line of the last item
                    items[-1][3] += " " + lines[i].strip()
                i += 1
            stack = []
            for ind, tag, start, txt in items:
                while stack and ind < stack[-1][0]:
                    out.append(f"</li></{stack.pop()[1]}>")
                if stack and ind == stack[-1][0]:
                    out.append("</li>")
                else:
                    out.append(f"<{tag}{f' start={start}' if start and start != '1' else ''}>")
                    stack.append((ind, tag))
                out.append(f"<li>{inl(txt)}")
            while stack:
                out.append(f"</li></{stack.pop()[1]}>")
        else:
            para.append(ln.strip()); i += 1
    flush()
    return "\n".join(out)


def _md_check():
    h = md_to_html("# T\n\nA *b* **c** `d*`\n\n1. one\n   more\n2. two\n  - sub\n3. three\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n```\nx < y\n```")
    assert '<h1 id="t">T</h1>' in h and "<i>b</i>" in h and "<b>c</b>" in h and "<code>d*</code>" in h, h
    assert "<ol><li>one more</li><li>two<ul><li>sub</li></ul></li><li>three</li></ol>" in h.replace("\n", ""), h
    assert "<td>2</td>" in h and "<pre class=md>x &lt; y</pre>" in h, h
    assert md_inline("**`a` b** `c*` *d*", lambda x: x) == "<b><code>a</code> b</b> <code>c*</code> <i>d</i>"
    assert "<td><code>a | b</code></td><td>c</td>" in md_to_html("| x | y |\n|---|---|\n| `a | b` | c |")


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
                          f'<title>{title}</title><link rel=icon href="/favicon.png"><link rel=stylesheet href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap">'
                          f'<link rel=stylesheet href="bank.css"><script defer src="bank.js"></script></head><body>')
    brand = '<a class=brand href="/"><img src="/favicon.png" alt=""><b>Pipe</b><span>Dream</span></a><a href=".">SMW decomp</a>'
    nav = (f'<div id=header>{brand}<a href="ram.html">RAM map</a><a href="graph.html">Call graph</a>'
           '<button id=help-btn aria-pressed=false onclick="toggleHelp()">Instruction help</button>'
           '<span class=grp><input id=q placeholder="Search regex (this bank)" size=26> <button onclick="clearSearch()">Clear</button></span>'
           '<a href="search.html">Search all banks</a></div>')

    def render_line(ln, b):
        if ln.kind == "blank":
            return ""
        if ln.kind == "comment":
            ind = len(ln.raw) - len(ln.raw.lstrip())
            if ind < SRC_HEX_COL:  # flush-left block comment between routines
                return f'<span class=c>{linkify(ln.comment, b)}</span>'
            # Comment-only row indented into the code area: map the source's code and comment columns onto
            # ours, so its "; |" lines up with the comments above and below.
            if ind >= SRC_COM_COL - 6:  # starts in the comment column already
                split = ind
            else:  # starts in the code column; a later "; " near the comment column is its trailing comment
                split = next((i for i in range(SRC_COM_COL - 6, len(ln.raw))
                              if ln.raw[i] == ";" and ln.raw[i - 1] == " "), None)
            left = ln.raw[ind:split].rstrip()
            right = ln.raw[split:] if split is not None else ""
            left = " " * max(0, ind - SRC_CODE_COL) + left
            pad = " " * max(1, CODE_COL - len(left)) if right else ""
            return (f'<span class=l><span class=gut><span class=rom>{" " * 8}</span> <span class=hx>{" " * 12}</span> </span>'
                    f'<span class=cd><span class=c>{linkify(left, b)}</span>{pad}</span>'
                    + (f'<span class=c>{linkify(right.rstrip(), b)}</span>' if right else "") + '</span>')
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
            hdr = [f'<span class=c>;;; <a id="{anchor}" href="#{anchor}">{rng}</a>: {title} ;;;</span>']
            summary = ann.get("summary") or []
            if isinstance(summary, str):
                summary = summary.splitlines()
            for l in summary:
                l = str(l).rstrip()
                if not l.strip():
                    continue
                indent = len(l) - len(l.lstrip())  # keep "Parameters:" style indents, wrap with a hanging one
                for i, w in enumerate(textwrap.wrap(l.strip(), WRAP - 3 - indent) or [""]):
                    hdr.append(f'<span class=c>;; {" " * (indent + (4 if i else 0))}{linkify(w, b)}</span>')
            seen, parts = set(), []
            for cb, ca, cs in callers.get((b, s["anchor"]), []):
                if (cb, ca) not in seen:
                    seen.add((cb, ca))
                    href = f"#{ca & 0xFFFF:04X}" if cb == b else f"{cb}.html#{ca & 0xFFFF:04X}"
                    parts.append(f'<a href="{href}">${cb}:{ca & 0xFFFF:04X}</a>: {html.escape(title_of(cb, cs))}')
            if parts:
                hdr.append('<span class=c>;; Called by:</span>')
                hdr += [f'<span class=c>;;     {p}</span>' for p in parts[:12]]
                if len(parts) > 12:
                    hdr.append(f'<span class=c>;;     ... and {len(parts) - 12} more</span>')
            # One block, newlines included, so bank.css can colour it and keep it out of a drag-select.
            body.append('<span class=hd>' + "\n".join(hdr) + '</span>')
            body += [r for r in (render_line(ln, b) for ln in s["lines"]) if r is not None] + [""]
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
Descriptions were drafted from the code. Where the code only shows <i>how</i> a byte is used and not <i>why</i>, the
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
<div id=header>{brand}<span class=grp><input id=qa placeholder="Search regex, all banks" size=30> <button onclick="searchAll()">Search</button> <span id=status></span></span></div>
<div id=right><pre id=all></pre></div>
<script>const BANKS={bank_list};</script>
</body></html>""", encoding="utf-8")

    # Index: standalone page styled like pipedream.nexus (not bank.css, whose dark mode inverts the page).
    card = lambda b, d: f'<a class="card bank" href="{b}.html"><span class="addr">${b}</span><p>{d}</p></a>'
    items = "\n".join(card(b, d) for b, d in sorted(all_banks.items()) if b in parsed)
    nsec = sum(len(s) for s in parsed.values())
    links = lambda pairs: " &middot; ".join(f'<a href="{h}">{t}</a>' for h, t in pairs)
    discord = "https://discord.gg/xwS9Ngp6CD"
    (HERE / "index.html").write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>SMW decomp: Super Mario World, bank by bank</title>
<meta name="description" content="The Super Mario World disassembly split by ROM bank, with English names, summaries, callers and a comment on every instruction.">
<link rel="icon" href="/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
:root{{--bg:#0b0b0c;--panel:#121214;--line:rgba(255,255,255,.08);--fg:#fff;--text:#e3e1ea;--dim:#888890;--ok:#34d399;
  --sans:"Geist",ui-sans-serif,system-ui,"Segoe UI",sans-serif;--mono:"JetBrains Mono",ui-monospace,Consolas,monospace}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 var(--sans);letter-spacing:-.01em;-webkit-font-smoothing:antialiased}}
a{{color:inherit}}
p{{color:var(--dim);margin:0}}
code{{font-family:var(--mono);font-size:.88em;color:var(--fg)}}
.wrap{{max-width:1120px;margin:0 auto;padding:0 24px}}
h1,h2{{margin:0;color:var(--fg);font-weight:500;letter-spacing:-.04em;line-height:1.1}}
h2{{font-size:clamp(1.9rem,4vw,2.5rem)}}
section{{padding:88px 0;border-top:1px solid var(--line)}}
.sub{{margin-top:12px;max-width:62ch}}
.btn{{display:inline-block;background:#fff;color:#000;font-weight:500;font-size:.94rem;border-radius:99px;padding:10px 24px;text-decoration:none}}
.btn:hover{{background:#e5e5e5}}
.btn.ghost{{background:none;color:var(--fg);border:1px solid rgba(255,255,255,.14)}}
.btn.ghost:hover{{background:rgba(255,255,255,.05);border-color:rgba(255,255,255,.28)}}
nav{{position:sticky;top:0;z-index:10;background:rgba(11,11,12,.8);backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}}
nav .wrap{{height:56px;display:flex;align-items:center;justify-content:space-between}}
.brand{{display:flex;align-items:center;gap:8px;text-decoration:none;color:var(--fg);font-size:1.1rem}}
.brand img{{width:22px;height:22px;image-rendering:pixelated}}
.brand b{{font-weight:600}}.brand span{{color:var(--dim)}}
nav .right{{display:flex;align-items:center;gap:22px}}
nav .link{{color:var(--dim);text-decoration:none;font-size:.88rem}}nav .link:hover{{color:var(--fg)}}
nav .pill{{border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.03);border-radius:99px;padding:4px 14px;
  font:500 .75rem var(--mono);color:var(--fg);text-decoration:none}}
nav .pill:hover{{border-color:rgba(255,255,255,.3)}}
/* Pipe Dream's level desk, toned down: diamonds on #101010, tips touching every 32px */
.hero{{padding:88px 0 80px;text-align:center;
  background:#101010 url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32'%3E%3Cpath d='M16 0 32 16 16 32 0 16z' fill='%23161616'/%3E%3C/svg%3E") 0 0/32px 32px}}
.eyebrow{{font:500 .75rem var(--mono);letter-spacing:.12em;color:var(--dim)}}
.hero h1{{font-size:clamp(2.4rem,6vw,4rem);margin-top:14px}}
.hero .lede{{font-size:1.1rem;margin:22px auto 0;max-width:60ch}}
.hero .lede a{{color:var(--text)}}
.stats{{display:flex;justify-content:center;flex-wrap:wrap;gap:10px;margin-top:28px}}
.stats span{{border:1px solid var(--line);background:rgba(255,255,255,.03);border-radius:99px;padding:3px 12px;
  font:500 .75rem var(--mono);color:var(--dim)}}
.stats b{{color:var(--fg);font-weight:500}}
.acts{{display:flex;justify-content:center;gap:12px;flex-wrap:wrap;margin-top:32px}}
.grid{{display:grid;gap:12px;margin-top:40px;grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px 20px;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.05);transition:border-color .15s,transform .15s;text-decoration:none}}
.card:hover{{border-color:rgba(255,255,255,.22)}}
a.card:hover{{transform:translateY(-2px)}}
.card p{{font-size:.88rem;line-height:1.5}}
.bank .addr{{display:block;font:500 1.15rem var(--mono);color:var(--ok);margin-bottom:6px}}
.card h3{{margin:0 0 6px;color:var(--fg);font-weight:500;font-size:1.05rem;letter-spacing:-.02em}}
.card .links{{margin-top:10px;font-size:.88rem;color:var(--dim)}}
.card .links a{{color:var(--text);text-decoration:none;border-bottom:1px solid rgba(255,255,255,.2)}}
.card .links a:hover{{color:var(--fg);border-color:var(--fg)}}
.credits{{padding:56px 0;font-size:.85rem}}
.credits p{{max-width:80ch}}
@media(max-width:640px){{nav .right .link{{display:none}}.hero{{padding-top:56px}}section{{padding:64px 0}}}}
</style></head><body>
<nav><div class="wrap">
  <a class="brand" href="/"><img src="/favicon.png" alt=""><b>Pipe</b><span>Dream</span></a>
  <div class="right">
    <a class="link" href="#banks">Banks</a>
    <a class="link" href="ram.html">RAM map</a>
    <a class="link" href="graph.html">Call graph</a>
    <a class="pill" href="search.html">&#8981; Search</a>
  </div>
</div></nav>
<header class="hero"><div class="wrap">
  <div class="eyebrow">SMW DECOMP</div>
  <h1>Super Mario World,<br>bank by bank.</h1>
  <p class="lede">The community <a href="https://www.smwcentral.net/?p=section&amp;a=details&amp;id=4352">SMWDisC</a> disassembly,
    split per bank and rendered as browsable logs in the style of
    <a href="https://patrickjohnston.org/bank/index.html">PJ's Super Metroid bank logs</a>.
    Every <code>JSR</code>/<code>JSL</code>/branch target and every named table is a link, each routine lists its callers,
    and hardware registers show their name on hover.</p>
  <div class="stats"><span><b>{nsec}</b> sections</span><span><b>{len(parsed)}</b> banks</span><span><b>{named_count}</b> named &amp; summarised</span></div>
  <div class="acts"><a class="btn" href="search.html">Search all banks</a><a class="btn ghost" href="ram.html">RAM map</a></div>
</div></header>
<section id="banks"><div class="wrap">
  <h2>Choose a bank.</h2>
  <p class="sub">Code, data and graphics, one page per 32&nbsp;KB ROM bank.</p>
  <div class="grid">
{items}
  </div>
</div></section>
<section><div class="wrap">
  <h2>Also here.</h2>
  <p class="sub">Cross-bank tools, and write-ups traced from the code.</p>
  <div class="grid">
    <a class="card" href="search.html"><h3>Search all banks</h3><p>One regex across every page.</p></a>
    <a class="card" href="ram.html"><h3>RAM map</h3><p>What every RAM address does, with the instructions that touch it.</p></a>
    <a class="card" href="graph.html"><h3>Call graph</h3><p>Interactive graph of the named routines (735 nodes, 53 communities).</p></a>
    <div class="card"><h3>Notes</h3><p>How the game runs, traced from the code.</p>
      <div class="links">{links((notes_page(k), v) for k, v in NOTES.items())}</div></div>
    <div class="card"><h3>Lunar Magic</h3><p>Every place LM hooks into SMW, and the formats it writes.</p>
      <div class="links">{links((lm_page(k), v) for k, v in LM_DOCS.items())}</div></div>
    <div class="card"><h3>Tools</h3><p>What each tool puts in the ROM, and how Pipe Dream does the same job.</p>
      <div class="links">{links((f"tool-{k.lower()}.html", name) for k, name in TOOLS.items())}</div></div>
  </div>
</div></section>
<section class="credits"><div class="wrap">
  <p>SMWDisC was written on etherpad by Smallhacker, 1024, lolcats439, Roy, YoshiCookieZeus, Imamelia, Nicol Bolas, Buster Beetle,
  Gekko, Kernigh, Maxx, Edit1754, Alcaro and others; all.log by MikeyK250. Super Mario World is &copy; Nintendo.
  Corrections are welcome on <a href="{discord}">the Discord</a>.</p>
</div></section>
</body></html>""", encoding="utf-8")

    # Notes and Lunar Magic docs: markdown write-ups as pages here. $BBAAAA addresses link to their line,
    # and a mention of another of these files (FOO.md) links to its page.
    def note_links(t):
        t = re.sub(r"\$([0-9A-F]{2})([0-9A-F]{4})\b", lambda m: f'<a href="{m.group(1)}.html#{m.group(2)}">{m.group(0)}</a>'
                   if m.group(1) in parsed and int(m.group(2), 16) in addrs[m.group(1)] else m.group(0), t)
        return re.sub(r"\b(?:reference/)?(\w+)\.md\b", lambda m: f'<a href="{doc_page(m.group(1))}">{m.group(0)}</a>'
                      if m.group(1) in NOTES or m.group(1) in LM_DOCS or m.group(1) in tool_of else m.group(0), t)
    notes_nav = (f'<div id=header>{brand}<a href="ram.html">RAM map</a><a href="graph.html">Call graph</a>'
                 '<span class=grp>Notes: ' + " &middot; ".join(f'<a href="{notes_page(k)}">{v}</a>' for k, v in NOTES.items())
                 + '</span><span class=grp>Lunar Magic: ' + " &middot; ".join(f'<a href="{lm_page(k)}">{v}</a>' for k, v in LM_DOCS.items())
                 + '</span><span class=grp>Tools: ' + " &middot; ".join(f'<a href="tool-{k.lower()}.html">{name}</a>' for k, name in TOOLS.items())
                 + '</span></div>')
    for stem in [*NOTES, *LM_DOCS, *tool_of]:
        md_src = (HERE / "docs" / f"{stem}.md").read_text(encoding="utf-8")
        title = next((l[2:].strip() for l in md_src.splitlines() if l.startswith("# ")), stem)
        (HERE / doc_page(stem)).write_text(f"""{head(html.escape(title))}
{notes_nav}
<div class="page notes">{md_to_html(md_src, note_links)}</div></body></html>""", encoding="utf-8")

    g = SRC / "graph" / "graph.html"
    if g.exists():
        shutil.copy(g, HERE / "graph.html")
    print(f"ram.html  {len(ram_blocks)} addresses ({described} described); {named_count} named sections; "
          f"{len(comments)} overlay comments; index.html + search.html written")


if __name__ == "__main__":
    _md_check()
    main()
