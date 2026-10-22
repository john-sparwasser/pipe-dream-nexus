# Lunar Magic and the SMW ROM: format reference

This page is the data contract between Lunar Magic (LM) and the Super Mario World ROM: what has to be read to open a level and render it, and what has to be written to save it in a form LM and the game both accept. It covers the level loop in depth: pointer tables, objects, Map16, graphics, palettes, layer 2, layer 3, sprites, animation and ExAnimation. It touches the overworld only where level structures are shared.

Confidence tags:

- **[CONFIRMED]**: verified against the disassembly and real ROMs (vanilla plus several LM-edited hacks).
- **[MEASURED]**: a controlled before/after save in LM, or a run on an emulator or the console.
- **[LM-DOC]**: stated in FuSoYa's LM help, restated here rather than quoted.
- **[COMMUNITY]**: well-known SMW lore that has not been byte-verified here.
- **[INFERRED]** and **[PARTIAL]**: as the words say. **DECODED** marks a format worked out from controlled diffs.

The main method throughout is a controlled diff. Save the same ROM in LM twice, with exactly one known change in between, and diff the two files. That isolates the bytes LM touches far faster than reading the disassembly. The disassembly settles the few encodings a diff cannot.

## 0. Round-trip with Lunar Magic

This section collects what LM checks, refuses and rewrites when it opens or saves a ROM that another tool has patched. Anything that wants a ROM to survive being edited in LM and in another tool has to live inside these rules.

**$0DF100 is LM's level-access flag.** Nothing in LM's help documents it. It was found by bisecting a patched ROM against LM one byte at a time. If it holds any value other than $FF, every LM operation stops with *"Lunar Magic : Access Denied! The author of this hack has chosen to restrict level access."* The byte sits inside vanilla's $FF gap in bank $0D, where Direct-Map16 object handlers also live, so code written into that gap has to step around it. LM's own code in that gap respects it: on LM-edited hacks the surrounding block ends at $0DF0F8 and leaves $0DF100 at $FF.

**LM runs two checksum checks and words them differently.**

- *"The ROM's checksum is **incorrect**"* means the stored checksum does not equal the computed one.
- *"The ROM's checksum has been **tampered with**, which means the file has either been previously modified by another program"* means the stored checksum equals the computed one, but is not the value LM knows Super Mario World has. Adding data and recomputing the checksum honestly is exactly what triggers this one.

LM skips both checks for a ROM it considers one of its own hacks. An LM hack opens silently even with its checksum deliberately set to `0000`. A plain LM save keeps vanilla's `$A0DA`, because LM's expansion is zero-filled and does not change the sum. So a tool that adds data can avoid the warning by steering the sum back to `$A0DA`: reserve a block (RATS-tagged, so LM leaves it alone) whose only job is to balance the total. The ROM is then checksum-valid by the hardware's rule and unremarkable by LM's. A ROM balanced this way opens in LM with no dialog. [CONFIRMED]

**How LM decides a ROM's graphics are 4bpp.** Byte evidence from LM 4bpp hacks: $00AA50 holds `22 80 F7 0F` (`JSL $0FF780`, LM's level-GFX loader), and $00AAE1 holds `60`. LM stubs vanilla's expand-and-upload with an `RTS` and uploads from its own routine. LM's shape is: $00AACD becomes `LDX #$10`, and the planes-0/1 loop, the tile loop and the routine's tail collapse into a plain 32-byte-per-tile copy that returns at $00AAE1. **$00AAE1 is what LM reads to decide whether a ROM's files are 4bpp.** A ROM that stores 4bpp files without that byte makes LM render every level, and the 8x8 editor, as noise. The game itself is unaffected. LM's `-ExportGFX` shows it headlessly [CONFIRMED]:

| ROM | $00AA50 | $00AAE1 | LM's exported `GFX00.bin` |
|---|---|---|---|
| vanilla | vanilla | `A2` | 4096 bytes (3bpp, widened on export) |
| LM loader hook, 3bpp files | `22 80 F7 0F` | `A2` | 4096 |
| LM loader hook, 4bpp files, no RTS | `22 80 F7 0F` | `A2` | **5456**: 4bpp data read as 3bpp |
| LM 4bpp hack | `22 80 F7 0F` | `60` | 4096 |

5456 = 170 tiles × 32 + 16. LM read a 4096-byte 4bpp file as 3bpp (4096/24 tiles) and widened it.

A detail of vanilla's 3bpp path matters to anyone converting files: the plane-3 swap at $00AA9B-$00AAC6 applies only to files `$01`/`$17` when Y is `$6E/$6F/$7E/$7F`. Y counts **down** from `$7F` while the pointer walks forward, so the affected tiles are `$00`, `$01`, `$10`, `$11`, not the Y values. Files `$08` (tileset >= `$11`) and `$1E` never reach that path, because $00AA96 sends them to a separate filter path. Under 4bpp the copy no longer synthesizes plane 3, so the swap has to be baked into the file data. See §12g "The rest of LM's 4bpp mode".

**The decompression buffer is $7EAD00**, in vanilla and in LM. The overworld also reads from it (§6a-13).

**LM's VRAM patch** ($0081E2 = `JML`) is present on LM saves. LM's BG2/BG3 bypass slots depend on it (§7d).

**LM installs hacks on save, and some as soon as a dialog opens** [LM-DOC]. The Super GFX Bypass, Layer 3 bypass and ExAnimation hacks install "immediately" when their dialogs open. The VRAM patch and FastROM install on the next level save. So an LM user who touches a ROM patched elsewhere will have LM write its own versions of anything it considers missing. One measured GUI save (change the main entrance, Ctrl+S) on a ROM carrying another tool's patches changed **375 runs**: LM installed its whole baseline suite on that save. [MEASURED]

**What happens to foreign code LM overlaps.** Where the foreign bytes matched LM's own routine, LM rewrote the same bytes over them and the hook still pointed at valid code. One example is an exit routine at $05DC50 that matches LM's byte for byte (§9d-2). Where foreign code did not match LM's, LM wiped the space to $FF and left the foreign hook jumping into cleared space. An earlier entrance-position mechanism in the free run at $05DC90 is one case: it was wiped while $05D9FE still jumped to it. LM does not merely ignore a private mechanism. It treats that space as free. [MEASURED]

**LM honours any valid RATS tag it finds**, including tags it did not write, and warns on nested ones ("Nested RATs are not allowed!!" is a hard rule) [LM-DOC]. Blocks that another tool adds past the original 512 KB survive LM only if they are RATS-tagged.

**An unrecognized patch version greys LM out silently** [LM-DOC]. Per LM's VRAM-patch help: "If Lunar Magic does not recognize the version of the patch currently installed, all options may be disabled." A stamped but unrecognized hack does not fail loudly. Its LM options just go grey.

**The restore system gates some writes.** On a GUI save of a ROM it does not consider pristine, LM can ask *"Restore System Issue: the restore system cannot locate a copy of the original unmodified ROM with header, which is required for an operation about to be performed. Would you like to browse to a copy of this file now?"*. Cancel, and the save proceeds. The layer-3 hack will not install at all until this prompt is satisfied (§12b "The install gate").

**LM's command line is scriptable**, and reading through it works on every ROM tried: `-ExportAllMap16`, `-ExportGFX` and level export all exit 0. Writing is less forgiving. `-ImportLevel` with LM's own exported level behaves like this [MEASURED]:

| target | `-ImportLevel` |
|---|---|
| vanilla, 512 KB | exit 0, ROM written |
| vanilla after LM itself expanded it and imported a level | exit 0, ROM written |
| a plain LM save | LM opens its "Open" file picker (filtered to SNES ROMs) and the call times out |
| a real LM hack | same picker, times out |
| a ROM patched by another tool | same picker, times out |

`-ImportAllMap16` behaves the same way. So the headless write path fails on LM's own saves too, and the discriminator is not "another tool touched this file". The picker is most likely the one the restore-system dialog above puts up.

## 1. ROM container

- **Copier header** [CONFIRMED]: if the file size mod `0x8000` is `0x200`, a 512-byte header is present. Subtract `0x200` from every file offset to get the PC/ROM offset. Clean SMW is `524800 = 0x200 + 0x80000` bytes. Detect the header; don't assume it.
- **Mapping**: SMW is **LoROM** [CONFIRMED via the SNES header's map mode `0x20`]. SNES to PC: `pc = ((bank & 0x7F) << 15) | (addr & 0x7FFF)` for `addr >= 0x8000`. File offset = `pc + (headered ? 0x200 : 0)`.
- **SNES internal header** at $00FFC0 (PC `0x7FC0`, headered file offset `0x81C0`) [CONFIRMED]: a 21-byte title `"SUPER MARIOWORLD     "`, `$FFD5` map mode, `$FFD6` cart type, `$FFD7` ROM size (`log2(KB)`: `0x0B` = 2 MB, `0x09` = 512 KB), `$FFD8` SRAM size, `$FFDC/DD` checksum complement, `$FFDE/DF` checksum.
- **Expansion**: LM expands to 1, 2 or 4 MB (2 MB = `0x200000`). The original data lives in the first `0x80000` bytes. Everything LM adds goes past that and is RATS-protected.

## 2. RATS — ROM Allocation Tag System  [CONFIRMED live: 232 tags in one LM hack]

LM prefixes every block it inserts past the original `0x80000` with an 8-byte tag:
```
"STAR"            4 bytes  (ASCII 53 54 41 52 — "RATS" reversed)
size-1            2 bytes  little-endian, size of protected data (NOT incl. tag)
~(size-1)         2 bytes  = (size-1) XOR 0xFFFF   ← validity check
```
Validate with `(word4 XOR word6) == 0xFFFF`, or it's a false positive. The check is **required**: random data contains the bytes `53 54 41 52`, and overlapping fake "STAR" runs turn up inside real ROMs. One tag protects 1 to 0x10000 bytes. To scan for free space, look for runs of `0x00` and skip over every valid tag. Data inside the original 512 KB is **not** RATS-tagged, so LM or other tools can move it without warning. On LM ROMs the first real tag is at PC `0x80000` (file `0x80200`), size `0x6DFF`.

## 3. Level data — pointer tables  [CONFIRMED in clean ROM]

There are 512 level slots (`0x000`–`0x1FF`) and three parallel tables in bank $05:

| Data | SNES table | file (clean, headered) | stride | entry 0 |
|---|---|---|---|---|
| Layer 1 | $05E000 | `0x2E200` | 3 B | `54 86 06` → $068654 |
| Layer 2 | $05E600 | `0x2E800` | 3 B | `74 E6 FF` → bank `$FF` |
| Sprites | $05EC00 | `0x2EE00` | 2 B | `07 C4` → $07C407 (bank fixed at `$07`) |

- The layer-1 pointer is 24-bit and points at the level's header and object stream.
- The layer-2 pointer: bank `$FF` means layer 2 is a *background image* (it uses the BG pointer data and BG Map16), not an object layer [CONFIRMED pattern]. Any other bank means layer-2 object data, except for LM custom backgrounds (§10b).
- The sprite pointer is 16-bit within the fixed bank `$07` in vanilla. LM changes that (§11).
- LM relocation: for edited or new levels, LM repoints these entries into expanded banks (`$08` and up), where the target data carries a RATS tag. The tables themselves stay put.

## 4. Level header + object stream  [CONFIRMED via disassembly — bank 05 `LoadLevelData` $058601]

Layer-1 data begins with a **5-byte level header** (screen count, FG/BG palette, background colour, level mode, music, sprite GFX set, FG/BG GFX set, timer, and so on), which the loader consumes before the object loop. Then comes a stream of 3-byte objects, terminated by `0xFF`.

A standard object is 3 bytes. This is checked against the decode at $058601, which moves the bytes into `$0A`, `$0B`, `$59` and adds 3 to the pointer at `$65/$66`:
```
byte1: N B B y YYYY   bit7 = new-screen flag; bits6-5 = obj# high 2 bits;
                      bits4-0 = Y position 0..0x1F (bit4 is the Y-high/page bit)
byte2: O O O O X X X X bits7-4 = obj# LOW 4 bits;  bits3-0 = X position 0..0xF (col in screen)
byte3: settings       size/extra, passed to the object handler; = ext-object id when obj#==0
```
The exact maths from the ROM:
```
obj# ($5A) = ((byte1 & 0x60) >> 1) | (byte2 >> 4)          ; range 0x00-0x3F
pos  ($57) = ((byte1 & 0x0F) << 4) | (byte2 & 0x0F)        ; Y in high nibble, X in low
new screen  = byte1 & 0x80
Y high/page = byte1 & 0x10   (bumps the Map16 dest pointer down one screen)
```
byte2's **high** nibble holds the low bits of the object number and its **low** nibble holds X. `obj# == 0` means an **extended object** (`LevLoadExtObj` → `JSL $0DA100`). Any other number is a **normal object** (`LevLoadNrmObj` → `JSL $0DA40F`). The loop repeats `LoadLevelData` until the next byte is `0xFF`.

Objects decode to **Map16 tiles** that the bank-0D handlers write into the level's 16×16 tilemap: $0DA40F for normal objects and $0DA100 for extended ones. The sprite stream (bank `$07` in vanilla) is a separate list (§11).

### 4a. Object → Map16 expansion  [CONFIRMED via disassembly — bank 0D]

Each object is expanded to Map16 tiles by a **two-level dispatch**:

1. The normal object handler $0DA40F → $0DA415 reads the **FG tileset** `$1931` (0–E) and jumps through the tileset table at $0DA41E to a per-tileset routine (Normal, Castle, Rope, Underground, Switch Palace, Ghost House, Cloud/Forest, and so on). **The same object number produces different tiles in different tilesets**, so object rendering has to key on `(tileset, object#)`, not on the object number alone.
2. The per-tileset routine (Normal is $0DA44B) does `LDX $5A` (object number), then `DEX`, then jumps through a per-object table (Normal's is at $0DA455) to the object's own handler: coins, blocks, pipes, slopes, ledges, water, nets, bushes and so on.

Each handler writes into the level's Map16 tilemap with this primitive ($0DA648):
```
LDA $0C          ; the Map16 tile's low byte
STA [$6B],Y      ; Y = $57 (packed position); [$6B..$6D] = low-byte plane base
```
The tilemap is stored as **two parallel byte planes**: low bytes through `[$6B]` and the tile's high byte (its page) through `[$6E]` (`StzTo6ePointer` writes page 0, `Sta1To6ePointer` page 1). A cell's full Map16 index is `high_plane[pos]<<8 | low_plane[pos]`. `[$6B]` and `[$6E]` are the two planes of one layer. `LoadLevelData` sets them up from the `LoadBlkPtrs`/`LoadBlkTable2` tables, which are separate from the layer-1/layer-2 *data* pointers in §3. Simple single-tile objects just look the tile up, `tile = DATA_0DA548[object# - 0x10]`, with item-memory logic that swaps a `?` block to the used block `$32` once it has been hit.

There are about 0x3F normal objects across several tilesets, but many share code such as $0DA8C3.

### 4b. Rectangular objects — byte3 = size  [CONFIRMED via disassembly — `$0DA8C3`]

The shared handler $0DA8C3 covers most "rectangle of one repeated tile" objects: water, coins, cement/turn/note/throw blocks, walk-through dirt and others. It decodes **byte3 (`$59`)** like this:
```
width  = byte3 & 0x0F      ; low nibble
height = byte3 >> 4        ; high nibble
```
It fills a **(width+1) × (height+1)** rectangle (both loops are inclusive) with one Map16 tile taken from `DATA_0DA8B4[object# - 1]`. That table gives the low byte; the high byte (page) is 0 if the object index is below 7, else 1. So byte3 is the object's drag size in LM: low nibble = tiles wide − 1, high nibble = tiles tall − 1.

Fill order: the inner loop lays tiles left to right (`INY`, with a screen-boundary fixup that adds `0xB0` to the map pointer and bumps the screen counter every 16 columns). The outer loop drops one row by adding `0x10` to the packed position `$57`. Single-tile objects (§4a) are the degenerate `width=height=0` case, with a per-object tile table (`DATA_0DA548`) instead of a fill. Other object families (pipes, slopes, ledges, nets, diagonals) have their own handlers and their own readings of byte3.

## 5. Map16 — the tile layer  [LM-DOC + file format CONFIRMED]

A level's geometry is a grid of **16×16 tiles**, and each 16×16 tile is **4 SNES 8×8 tiles**. The `.map16` file layout:

- A `0x40`-byte header: `"LM16"`, format version (`0x100`), game ID (1 = SMW), program ID (1 = LM), a pointer to the offset+size table, size X (max `0x10`), size Y, base coordinates, flags.
- Data block 0 is the Map16 itself: **8 bytes per 16×16 tile**, four 16-bit SNES tilemap words in the order **TL, BL, TR, BR**.
- Data block 1 is "Act As", 2 bytes per tile: which vanilla tile this one behaves as (`<0x200`).

Each 8×8 tilemap word is the standard SNES `vhopppcc cccccccc`: tile number (10 bits, `cc…`), palette (3 bits, `ppp`), priority (1 bit, `o`), H-flip `h`, V-flip `v`. **This word, the GFX and the palette are everything a renderer needs per 8×8.**

## 6. Graphics (GFX)  [LM-DOC]

- Files `GFX00.bin`–`GFX33.bin`. The original game stores most as 3bpp (0xC00 bytes for a full 128-tile file). LM installs an optional 4bpp mode (§0). Files `28-2B` and `2F` are 2bpp, `27` is Mode 7, and `32` is 4bpp at 23.2 KB.
- ExGFX `80`–`FFF` are user-supplied. ExGFX `60-63` are stored uncompressed (up to 32 KB each) for ExAnimation (§12e).
- In-ROM GFX is **compressed with LC_LZ2** (LM's default) or **LC_LZ3**, the "Lunar Compress" formats. LM exposes a decompressor at **JSL $0FF900** (A = file number, `$00` = 24-bit destination), but an external tool has to implement LC_LZ2/LZ3 itself. The open-source Lunar Compress library and SMW Central's docs describe both. Files 32/33 cannot be decompressed through that JSL.
- Which GFX file loads into which VRAM slot is set by the level header's FG/BG/SP GFX-set bytes and a GFX-list lookup. LM's per-level GFX override (Super GFX Bypass, §7d) repoints these.
- **GFX32 and GFX33 are not in the pointer tables.** The three pointer tables ($00B992/$00B9C4/$00B9F6) are 0x32 bytes each and adjacent, so "entry 0x32" of one table is entry 0 of the next. The two animation blobs load from fixed operands at $00B88B instead (§12a). A tool that writes `table + 0x32` lands on GFX00/GFX01's entries.
- **Bit depth is ROM-wide, not per file** (§7d). A 4bpp ROM needs every file the vanilla expander serves converted (decompress, widen 3bpp to 4bpp, recompress, repoint), not just its upload code changed.

## 7. Palettes  [LM-DOC]

- SNES 15-bit BGR555 colours, little-endian words (`0bbbbbgg gggrrrrr`).
- A level's palette comes from the header's palette indices into shared palette data. LM can add a custom per-level palette that it stores separately (§7e). `.mw3` is raw 16-bit colours; `.pal` is YY-CHR format.

## 8. Other exposed LM entry points (only relevant if hijacking, not for a clean reimpl)

- JSL $0FF900: decompress GFX/ExGFX to RAM. [LM-DOC]
- JSL $03BCDC: the screen-exit "which screen is Mario on" calculation. [LM-DOC]
- Map16 gameplay JSL hooks at PC `0x37890`–`0x379C0` (custom block-interaction behaviour). [LM-DOC]

## 6. Rendering assets — ROM locations  [located via disassembly; vanilla ROM]

This is the vanilla map of the three subsystems that turn a Map16 grid into pixels. LM relocates or expands most of it into RATS-protected expanded ROM on edited ROMs (see the per-item notes), but the vanilla layout is the baseline and what a clean ROM uses.

### 6a-13. The decompression buffer and the overworld's reader  [CONFIRMED in Mesen]

The GFX decompression buffer is $7EAD00 in vanilla and in LM. The overworld reads its animated tiles (water, clouds) out of that buffer every frame with its own bank-04 reader, from whatever file was decompressed last. The reader uses an offset table at $048000 (67 words), bank `$7E` hard-coded, and a 3bpp expander at $0480B9.

LM's 4bpp mode changes exactly that reader, byte-compared against LM 4bpp hacks:

- the offset table is rescaled to 32 bytes per tile;
- the expander gets $0480BD = `$10` and $0480D0 = `RTS`;
- the overworld sprite tables move from `$7EB9xx/$7EBAxx` to `$7FC5xx/$7FC6xx` (21 operands in $04F2B8-$04F3D0), so a 4bpp file's overrun of the buffer, up to $7EBCFF, hits nothing.

LM_PARITY §2 "4bpp graphics" lists the rest of LM's 4bpp mode.

### 6a. GFX files + decompression

- **Pointer tables** (indexed by GFX file number 0x00–0x33): three parallel byte tables in bank $00, low $00B992, high $00B9C4, bank $00B9F6. File N's source address is `B9F6[N]<<16 | B9C4[N]<<8 | B992[N]` (`CODE_00BA28`).
- **Decompressor**: the wrapper $00BA28 looks up the pointer and sets the destination, then calls the core at $00B8DE. Output goes to the GFX buffer at $7EAD00 and is then DMA'd to VRAM.
- **Format**: SMW's native LZ is **LC_LZ2** (the community format is named after it). $00B8DE is the exact command set.
- **LM note**: LM re-inserts GFX (LC_LZ2/LZ3) and adds ExGFX (files 0x80–0xFFF). Its own decompressor is JSL $0FF900. On a clean ROM the vanilla tables above are authoritative.

### 6b. Map16 (16×16 → 8×8) definitions

- **Runtime tilemap** (what the object engine writes): low-byte plane $7EC800, high-byte plane $7FC800. Full index = `high<<8 | low`. The current-tile scratch is `$1693`.
- **FG tile definitions**: 8 bytes per 16×16 tile (four 8×8 tilemap words, §5). `CODE_0581FB` assembles them per level from **`TilesetMAP16Loc` at $058000**, a per-tileset table of addresses (`$8B70,$BC00,$C800,$D400,…` in bank 05), plus the shared regions $05E55E and $05E5C8. A per-page bitmap at $0581BB decides, for each Map16 page, whether it comes from the tileset-specific block or the shared block. Reconstructing the full 0x000–0x1FF FG table means following that per-page source selection, not reading one contiguous table.
- **LM note**: LM stores an expanded Map16 table in its own RATS region and repoints the game to it (§7a-rev). The `.map16` file format (§5) is that data serialized.

### 6c. Palettes

- **Load routine**: $00ABED (`LoadPalette`) → `LoadColors`. It writes BGR555 words into the CGRAM buffer at `$0703+`.
- **Vanilla palette data** in bank $00: back-area colour table $00B0A0. Row bases: BG $00B0B0, FG/object $00B190, sprite $00B318, layer 3 $00B170. Shared colours 9–F at $00B674. The row-offset table `DATA_00ABD3` is at $00ABD3.
- **The header selects rows**: `$1930` BG palette, `$192D` FG palette, `$192E` sprite palette, `$192F` back-area colour. All are 15-bit BGR555 little-endian words.
- **LM note**: LM adds optional per-level custom palettes, stored separately (§7e). Its palette export formats are `.mw3` and `.pal`.

## 7. Lunar Magic read path (edited 2MB ROMs)  [PARTIAL — entry points located]

LM-edited ROMs relocate and expand Map16 and GFX, so rendering them needs LM's tables. The entry points come from diffing clean SMW against LM hacks:

- **Map16 lookup hijack**: LM patches the Map16 → 8×8 consumer at $00C17A with `JSL $06F5D0` (vanilla had `REP #$20` there). `TilesetMAP16Loc` ($058000) is left unchanged and becomes vestigial.
- $00F545 is the gameplay **acts-like** handler (it works on `$1693`), not the graphics definitions.
- **Graphics defs**: LM stores the 16×16 definitions (8 bytes = 4 words TL/BL/TR/BR, §5) in RATS-protected blocks. §7a-rev has the full read contract.

### 7a-rev. LM extended Map16 defs — CORRECTED CONTRACT  [CONFIRMED on 7 ROMs]

The real contract comes from the in-game consumer: LM's Map16 lookup hijack, which is identical code in every LM ROM.

- $00C17A = `JSL $06F5D0`. The detector is byte $00C17A == `0x22` with operand $06F5D0.
- $06F5D0 is a small wrapper (`LDY $0B : STY $05` for the vanilla hook) into piecewise definition-pointer maths in a "ladder" at the **fixed address $06F540**. The ladder's entry is `CMP #$0400`, and entry A = tile × 2:
  - tile < 0x200: the vanilla path through the RAM table at `$0FBE`. The definition bank is $0D, or a per-ROM bank for LM custom tilesets (`$1930 >= 0x1000`).
  - tile 0x200 and up: **def = bank:((imm + tile×8 + carry) & 0xFFFF)**, where `imm` is the 16-bit `ADC` operand and `bank` is the high byte of the `LDY` operand of the SLOT covering that tile's range (`69 imm16 A0 bank<<8`). bank == 0 means that range has no definitions installed.
- LM's render engine (its bank-$1F block) JSLs the ladder entry $06F540 about 150 times and reads the bank from `$0B`. A second LM wrapper at $06F5E4 is its per-site acts-like path (§12g "Acts-like core").

**The carry.** LM's ladder reaches the `ADC #imm` of ranges 2 and 3 (and 6 and 7) with C = 1, because the second `ASL` shifts tile bit 13 out and nothing clears it. So those slots store **imm − 1** (LM's defaults are `FFFF`/`7FFF`), and the pointer is `imm + tile*8 + 1`. A reader that ignores the carry is one byte off for every tile >= 0x2000.

**The ladder has one slot per 0x1000 tiles.** `imm + tile*8` is 16-bit addressing into a 32 KB LoROM window, so one slot can address at most `$8000/8` = 0x1000 definitions. That is the whole reason LM has a ladder rather than one slot. It is a hard hardware limit, not an LM policy:

| range | tiles | slot | | range | tiles | slot |
|---|---|---|---|---|---|---|
| 0 | 0x200-0x0FFF | $06F552 | | 4 | 0x4000-0x4FFF | $06F593 |
| 1 | 0x1000-0x1FFF | $06F55B | | 5 | 0x5000-0x5FFF | $06F59C |
| 2 | 0x2000-0x2FFF | $06F566 | | 6 | 0x6000-0x6FFF | $06F5A7 |
| 3 | 0x3000-0x3FFF | $06F56F | | 7 | 0x7000-0x7FFF | $06F5B0 |

Ranges 4-7 are a second chain further along. A slot's opcode bytes (`69`/`A0`) are present even when it is unused, with junk immediates (`$FFFF`, `$7FFF`, `$8000`) and bank 0. So **only the bank tells a populated slot from an empty one**, never the immediate.

Observed range-0 slots across LM ROMs: $107008, $147000, $158274, $15CB42, $10DE94, and $00F000 (bank 0 = none) on a plain LM save. Populated high ranges seen: r0 $1DAEAE with r1 $1D4E5E on one hack; r1 $1B2C3A on another; r4 $89C770 with r5 $895778 on a third, the only sampled use of the second chain. Everything else leaves ranges 1 and up at bank 0.

**Holes are legal.** One hack's range 0 stops well short of 0xFFF while its range 1 is populated, and another populates ranges 0 (partly), 1, 2, 5, 6 and 7. So reaching ranges 4-7 is a matter of per-range existence, not of a larger contiguous tile count.

- Unedited tiles in a populated region read `FF`, which gives a definition of `FFFF`×4 (it renders as tile 3FF, palette 7, both flips). Levels don't reference them. LM's `.s16` export stores such tiles as zeros.
- A FULL range needs all 0x8000 bytes of its window, which leaves no room for a RATS tag at the start of the bank. A full range therefore takes two banks, with its tag parked in the first bank's tail.
- **Numbering is LM's.** FG tiles are 0x0000-0x7FFF (ranges 4-7 are LM's pages 40-7F). BG tiles are 0x8000 and up (§10b). LM's Direct-Map16 objects reach 0x4000-0x7FFF: object 0x29 is object 0x27 with `page|0x40` (§9d).

Earlier readings took the definition base from a pointer at $02C2E1. That held on only one ROM: on LM hacks the block $02C2E1 points at is a stale `FF`-filled allocation, while the game reads definitions through the ladder. The ladder above is the contract.

### 7a. LM extended Map16 table  [SUPERSEDED by 7a-rev — kept for the diff history]

This decode came from editing one Map16 tile (0x300) in LM and diffing before and after. Its base address (a pointer at $02C2E1, also $049371, with definitions at `base + 8 + (tile - 0x200) * 8`) is a coincidence of that one ROM. §7a-rev's ladder is the corrected layout. What still stands from it:

- Word layout confirmed as in §5: tile number in bits 0-9, palette bits 10-12, priority bit 13, X-flip 14, Y-flip 15. The edit to 0x300 = `00DA 08DC 04DB 0CDD`, which is tiles DA/DC/DB/DD with palettes 0/2/1/3.
- A blank fill of unused extended tiles seen as `1004`×4.
- Tiles below 0x200 use the vanilla/tileset path. LM's handler splits on `CMP #$0200` there.
- The 2-byte-per-tile table at $118000 is acts-like (§7b).

### 7b. Page-1 (tileset-specific) Map16 + acts-like  [CONFIRMED via 2nd diff]

The test edited tile 0x166 (a copy of 0x300) with acts-as 0x130:

- Page-1 tiles (0x100-0x1FF) are **tileset-specific, and LM writes them back into the vanilla bank-$0D table in place** (tile 0x166 went to $0D90C0 for tileset 7). The vanilla definition reader therefore reads LM's page-1 edits with no extra logic.
- **Acts-like** (behaviour and hitbox) is a separate 2-byte-per-tile table at **$118000**: `actsAs(tile) = word[$118000 + tile*2]`. It is identity for unedited tiles; 0x166 → 0x130 here. Entries of 0x200 and up are chains (§12g "Acts-like chains").

So the Map16 read side for LM hacks is: tiles below 0x200 from vanilla bank $0D (edits land in place), 0x200 and up through the ladder (§7a-rev), and acts-like from $118000.

### 7c. LM per-level GFX bypass  [PARTIAL — located, layout not confirmed]

The first controlled diff (level 0x105's Super GFX Bypass set to FG1-3 = 28/29/2A, BG1-3 = 2B/2C/2D, SP1-4 = 2E/2F/30/31, AN2 = 01) showed that LM stores per-level GFX assignments as fixed **0x20-byte records of 16 16-bit words** in its expanded data region. The entries are 16-bit, so they can name ExGFX. `0x7F` means "slot off, use the tileset default". Some words carry high-bit flags. Ascending test values could not pin the slot order, and one of them collided with the identity table at $118000. §7d has the confirmed layout.

### 7c (confirmed). GFX bypass record layout

A second diff with distinct per-slot values decoded the slot words. It read the record from an offset 8 bytes too early, so it showed four vanilla layer-3 words (`2B 2A 29 28`) at the front as a "constant". §7d gives the record with the correct alignment, and §12b explains those four words.

### 7d. GFX bypass + ExGFX — COMPLETE READ CONTRACT  [CONFIRMED via ASM trace, validated on 4 hacks]

This is traced from LM's installed loader. LM hooks the vanilla level-GFX loader with $00AA50 = `JSL $0FF780` (`22 80 F7 0F`, identical in every LM hack checked). That byte pattern is the **bypass-installed detector**. A decompress call at $00AA6C is redirected from $00BA28 to $0FF160.

**Record fetch** ($0FF7F0): `LDA $FE (=level+1) : BEQ off : DEC : ASL x5 : TAX : LDA $10AD08,X`, so **record = tableBase + level×0x20**. tableBase is baked into the `BF` operand, per ROM: $12AD08, $10AD08 and $11AD00 were all observed. Find it with the signature `A5 FE F0 ?? 3A 0A 0A 0A 0A 0A AA BF <base:3>`, or read the operand at the fixed offset LM itself uses (§12g "Super GFX Bypass dialog"). The record's long pointer is cached at `$7FC006/8`. The enabled-flag byte is at `$7FC009` (`0x42` = enabled).

**Record layout**, 16 words:
```
w0 = AN2 (bit15 = BYPASS ENABLED flag)   w1 = AN1
w2 = BG3   w3 = BG2   w4 = FG3   w5 = BG1   w6 = FG2   w7 = FG1
w8 = SP4   w9 = SP3   w10 = SP2   w11 = SP1
w12 = LG4  w13 = LG3   w14 = LG2   w15 = LG1  <- layer-3 GFX, gated by w0 bit 14 (§12b)
```
Each word is 16-bit. Its low 12 bits are the GFX/ExGFX file number, and `0x7F` means the slot uses the tileset default. The high nibbles carry other settings: w0's three enable bits (§12b) and the advanced layer-3 group (§12b "The ADVANCED BYPASS"). Words 12-15 are not a constant tail. They are the vanilla layer-3 set, explained in §12b. The LM 3.x record layout for submaps (records 0x200 and up) is the same (§12g).

**Named slot → VRAM pages**. From LM's help ("FG1=14") and the vanilla `OBJECTGFXLIST`: FG1 → page 0 (8×8 tiles 0x000-07F), FG2 → page 1 (0x080-0FF), BG1 → page 2 (0x100-17F), FG3 → page 3 (0x180-1FF). So the FG files are `[w7, w6, w5, w4]` = `[FG1, FG2, BG1, FG3]`, replacing `OBJECTGFXLIST[tileset*4+0..3]`. **BG2 and BG3 are pages 4-5** (0x200-0x27F and 0x280-0x2FF), words `[w3, w2]`. These are the two extra background slots that LM's VRAM patch adds. Per LM's help, "anything in slots BG2 and BG3 will not be loaded" without it. They have no vanilla `OBJECTGFXLIST` entry, so they come only from the bypass (`0x7F` or absent means blank). Pages 6-7 are the animated region. Checked on a hack whose level 105 sets BG2 = ExGFX 0x310 and BG3 = 0x311: its block graphics in tiles 0x200 and up render correctly only with pages 4-5 loaded.

**File number → data resolver** ($0FF903, slot word `AND #$0FFF`):

- 0x00-0x33: the vanilla pointer tables $00B992/$00B9C4/$00B9F6.
- 0x7F: slot skipped (keep the tileset default, load nothing).
- 0x80-0xFF: a 3-byte pointer at **$0FF600 + (n&0x7F)×3** (a fixed address in every hack).
- 0x100-0xFFF: a 3-byte pointer at **exgfxBase + (n-0x100)×3**, with exgfxBase baked per ROM ($128008, $108008 and $118000 observed). Signature: `38 E9 00 01 85 8A 0A 18 65 8A AA BF <base:3>`. LM's own tools take this address from the operand at a fixed offset (§12g "ExGFX 0x100+ table").
- All pointers lead to LC_LZ2-compressed GFX. The loader's tail JMLs into the vanilla decompressor at $00BA47 with `$8A-8C` = the pointer. An entry of `0x000000` or `0xFFFFFF` means the file is not inserted.

**A GFX file is 0x80 tiles, and bit depth is ROM-wide, not per file.** A "pick the depth from the decompressed length" heuristic is wrong for PARTIAL ExGFX: a 0x800-byte file is 128 tiles at 2bpp, 85 at 3bpp or 64 at 4bpp, and size cannot tell them apart. SMW stores every GFX/ExGFX file at one depth. Vanilla is 3bpp (a full file is 0xC00 bytes). LM re-normalizes all graphics to 4bpp on save (a full file is 0x1000), but not on every LM-touched ROM: a ROM edited only for something like the GFX bypass keeps 3bpp base GFX. So probe one full base file (GFX00) once and decode every slot at that depth. AN2 is special: up to 0xD0 tiles (0x1A00 bytes). Layer-3 slots are always 2bpp (§12b).

### 7e. LM per-level custom palettes  [CONFIRMED via .pal cross-check, 3 hacks]

LM leaves `LoadPalette` ($00ABED) and all the vanilla colour tables untouched. Its palette engine hooks the caller instead. Vanilla $0095E9 `JSR UploadSpriteGFX : JSR LoadPalette` becomes `JML $0EFC50 : JSR LoadPalette : JML $0EFC80`, so **byte $0095E9 == `0x5C` is the palette-engine-installed detector**. It is present on LM hacks and absent on a plain save and on vanilla. The hooks save and restore `$7E2000` (LM's relocated CGRAM staging buffer) around the vanilla loads. The custom palette itself is applied from ROM data:

- **A pointer table at the fixed address $0EF600** (the bank-$0E twin of the ExGFX table at $0FF600): 3 bytes per level, 0x200 entries. A zero entry means the level has no custom palette, and the vanilla assembly applies. `0xFFFFFF` is also seen as "none", but LM's own apply routine at $0EF583 treats only a zero pointer as none. Every non-zero entry on the hacks checked points at a valid RATS blob.
- Each entry leads to a RATS `STAR` tag plus 0x202 bytes of data: **word 0 = back-area colour**, then **256 BGR555 words, a complete CGRAM image** that replaces the whole vanilla §6c assembly. Each row's colour 0 is stored as 0 (transparent in-engine).
- Cross-checked against LM's own `.pal` exports (RGB888, 0x300 bytes): the ROM words equal `(b>>3)<<10 | (g>>3)<<5 | (r>>3)` of the .pal triplets for every colour except the 16 row-0 slots, which are zeroed in the ROM.

**There is a SECOND hook site.** The fade-in mode step at $00A5B9 re-runs `JSR UploadSpriteGFX : JSR LoadPalette`, which rebuilds the vanilla staging and wipes the custom palette. Every palette-engine LM ROM repoints the vanilla `JSL $05BE8A` at **$00A5BF** (immediately after that second `LoadPalette`) to `JSL $0EF570`, an LM routine that re-applies the blob (§12g "Palette engine"). An installer that hooks only $0095E9 shows the custom palette in stills but loses it on the real fade-in.

The back-area colour's runtime path: the staging word at **$0701** feeds COLDATA `$2132` every frame ($00AE47: `LDA $0701 … STA $2132`). The fade system snapshots `$0701/$0703+` into `$0903/$0905+` ($00A5D8). The back colour is NOT CGRAM colour 0.

A level with no custom palette and no bypass record can legitimately render washed out: an almost empty level slot looks like that.

## 9. Object engine — full dispatch contract  [CONFIRMED from disassembly + LM ASM traces]

### 9a. Tileset dispatch

$0DA41E + tileset×3 leads to a per-tileset dispatcher. There are 5 distinct ones: Normal $0DA44B for tilesets 0/7/C, Castle $0DC190, Rope $0DCD90 for 2/6/8, Underground $0DD990 for 3/9/A/B/E, and Ghost/Switch Palace $0DE890 for 4/5/D. Each per-object handler table is at dispatcher + 0xA, entry (obj−1)×3. Handlers are SHARED across tilesets (the theming comes from the per-tileset Map16 definitions), so object handlers are best identified by their address.

### 9b. Extended-object dispatch

There is ONE global table, $0DA10F + ext#×3 (0x00-0xFF; dispatcher at $0DA106). Notable handlers: $0DA57B/$0DA64D single tile (`DATA_0DA548[ext-0x10]`, page 1 when the index >= 0x13); $0DA68E midway bar (tile 035 at x−1, plus 038); $0DCE94 line guides 0x51-54; $0DCEA6/$0DCEC0/$0DDA80 vertical pairs; $0DDA68 decorations 0x75-7B.

### 9c. Screen jumps (parse-critical)

Vanilla extended object 0x01 ($0DA53D) sets screen := `b1 & 0x1F` (the Y bits). LM's extended object 0x03 ($0DE1E0) sets screen := `b2`. Screen sequences are therefore NON-MONOTONIC. Anything that walks screen boundaries, such as a merge on save, has to handle repeated screens. LM also uses these two objects to carry a 32-row band (§9d-3).

### 9d. LM reserved objects 0x22/0x23/0x26/0x27/0x28/0x29 (all 5 tileset tables repointed identically; vanilla had placeholder $0DB3E3)

- 0x22 → $0DF08A: Direct Map16, page 0. 4 bytes (b1, b2, size, tileLow); tile = `0x000|low`.
- 0x23 → $0DF08E: Direct Map16, page 1, the same 4-byte form.
- 0x26 → $0DF130: a no-tile directive (pokes `$0DDA`; music-related).
- 0x27 → $0DF150 and 0x29 → $0DFF50: VARIABLE LENGTH. The form is b1, b2, size, pageByte, tileLow (5 bytes), plus 1 run byte if pageByte bit 7 is set, plus 1 height-override byte if bits 7 and 6 are both set. Width switches to `size & 0x7F` only when bits 7 and 6 are BOTH set (bit 7 alone keeps the nibble sizes). Object 0x29 writes `page|0x40` words through the same plane writes as 0x27 (`$0DFF58 ORA #$40 : STA $01 : JMP $F094`, the same layer tile path 0x27 takes), so these are LM's **FG pages 40-7F, not BG**. An earlier reading called them BG pages. One large hack places 738 of them, on pages up to 0x7F, where its custom blocks are.
- The bit-7 "run byte" is NOT inert. It is a **stamp descriptor**: low nibble = stamp width − 1, high nibble = stamp height − 1, and the fill cycles `tileLow + (col % W) + 0x10*(row % H)`. This was decoded by footprint probes against an LM save and checked with screen-crossing fills.
- 0x28 → $0DF160: a no-tile directive (entrance/position, `$0F31-33`).
- LM extended object 0x02 ($0DE1B0): a secondary exit. It consumes 2 EXTRA stream bytes, the exit word (§9d-2).

Parse lengths must match exactly or the whole object stream desyncs. Some hacks build levels almost entirely from extended 0x27 forms.

**A calling-convention trap for anything hooked at these sites.** Code hooked at the sprite-pointer site ($05D8F5) or at the acts-like call sites (the four vanilla `JSL $00F545`s) MUST preserve the accumulator's HIGH byte (B). The entrance decode after $05D909 does `TAX` with 16-bit X, so a leaked B shifts every entrance-table index by +0x100 for levels >= 0x100. The symptom is garbage spawn or scroll state, such as an instant TIME UP. Vanilla $00F545 is purely 8-bit and leaves B alone, so a replacement must too. LM's own lookup does not keep B either (§12g "Custom-block dispatch"); in its configuration that is harmless.

### 9d-2. A screen exit's destination bit 8  [CONFIRMED from disassembly + emulated parity]

Vanilla has **no field** for the destination level's ninth bit. $05D7BD reads the destination byte into `$0E`, then takes the high byte from where the PLAYER is:

```
$05D7BD  LDA $19B8,X : STA $0E          ; destination low byte
$05D7C5  LDA $0DD6 : LSR : LSR : TAY
$05D7CB  LDA $1F11,Y                    ; the player's submap flag
$05D7CE  BEQ +2 : LDA #$01 : STA $0F    ; high byte = "am I on a submap?"
```

So the same exit lands in $005 from the main map and in $105 from a submap, and "exit to $105" cannot be expressed in vanilla data. The same is true of the secondary route: `$05F800,Y` is a low byte too.

`$19D8,X` (the exit flags the handler writes) has **no reader anywhere in the vanilla image**, only the store at $0DA533, so its upper bits are free. LM uses them, at two sites:

| site | vanilla | LM |
|---|---|---|
| $0DA531 | `AND #$01` (keep the water bit) | `AND #$0F` (keep the whole X nibble) |
| $05D7CE | `BEQ +2 : LDA #$01` | `JSL $05DC50` (4 bytes, an exact fit) |

The routine at $05DC50 (in vanilla's `$FF` run from $05DC46, 954 bytes) reads `$19D8,X`:

- **bit 2**: extended exit. When it is clear the routine falls back, so every untouched exit keeps its behaviour.
- **bit 0**: destination bit 8. **bit 1**: use the secondary table (`$1B93`).
- **bit 3**: entrance action → `$192A` bit 6. **bits 4-7**: further high bits, reachable only through LM's word form (extended object 0x02), since the nibble form masks to 4 bits.
- The high byte is `(flags >> 4) << 1 | bit0`. The fallback is `$13BF >= $25` (is this a main level), which replaces the submap test and no longer depends on how the player arrived.

Extended object 0x02 ($0DE1B0) is the same two tables in one object: `LDA [$65] : STA $19B8,X : XBA : STA $19D8,X`. The "exit word" is `destination | flags << 8`, NOT a 16-bit destination.

Any other tool's routine at that address has to decide the high byte exactly as LM's does. Running both routines under a 65816 emulator over every flag combination is a direct check that the two ROMs are interchangeable.

### 9d-3. Where an entrance puts Mario  [CONFIRMED from the decode]

No entrance record stores a position. It stores a SCREEN and two indices into small bank-05 tables, and the three kinds of entrance keep the screen in three different places:

| kind | screen | X index | Y index |
|---|---|---|---|
| main | $05F600 bits 0-4 ($05D9EC: `LDA $01 : AND #$1F`) | $05F200 bits 0-2 | $05F000 bits 0-3 |
| midway | $05F400 bits 4-7 ($05D9E1: `LDA $02 : LSR x4`) | shares the main's | shares the main's |
| secondary | $05FC00 bits 0-4 (stashed to `$01`, same tail) | $05FC00 bits 5-7 | $05FA00 bits 0-3 |

Position = `screen * 0x100 + DATA_05D750[xIndex]`, and `DATA_05D730/40[yIndex]`. `DATA_05D758` supplies an X high byte too, but the horizontal tail overwrites it with the screen. That is why indices 0-3 and 4-7 collapse to the same five distinct offsets on a horizontal level, and why a screen field exists at all. Vertical levels take the other branch at $05D9A7 and keep the table's high byte.

Two consequences, **for vanilla data only**. An entrance can only sit at one of **8 × 16 spots per screen**, so a drag snaps. And a **midway entrance carries only a screen**: its position inside that screen is the main entrance's, so it moves a screen at a time and never vertically.

**Lunar Magic lifts the first restriction** [LM-DOC]. Its help calls the tables "method 1", and says method 2 does not use table-based coordinates and is an enhancement inserted by LM. Method 2 is not a second table. It reinterprets the SAME two index nibbles as 16 px steps and adds a flags byte and a Y-high byte:

- **Main entrance**: per-level tables $05DE00 and $06FC00, routine $05DD30, hooked at $05D97D.
- **Secondary entrances**: the spare bits of $05FE00 plus a fifth table, routine $03BCE0, hooked at $05D833.

Every LM save installs both, byte-identical across a plain LM save and every hack checked. The positions decode as `X = screen << 8 | xHigh << 7 | xIndex << 4` and `Y = yHigh << 8 | yIndex << 4`. Two side effects come with the routines:

- LM writes `$1A` into $06FE00. It lands in `$13CD`, which the midway tape at $00F2D8 tests for zero. Vanilla kept the midway screen there, so $05D9C3 becomes a load.
- Every secondary record for `$100-$1FF` carries destination bit 8 in $05FE00 bit 3, because $03BCE0 takes the ninth bit from the record where vanilla took it from the submap flag.

**The midway gets a position of its own too**, through LM's "separate midway settings". This is a 0xC4-byte routine hooked at $05D9E3 (and at $05D979, for exits that target the midway). It reads four per-level tables: flags, position, FG/BG, and Y high. LM installs it on demand: hacks have it, a plain save does not. The midway's X is a whole nibble (`screen << 8 | nibble << 4`), and it gains a fifth screen bit. Until a level opts in, the routine hands back the screen and the midway borrows the main entrance's spot as before. The four tables must sit in a RATS block of their own, and the routine in another (§12g "Separate midway").

**The camera follows, through LM's level-entry engine.** A free position is only half of it. Vanilla starts the camera at one of four fixed offsets, so an entrance far from them puts Mario off screen. LM's "set FG/BG relative to player" ($06FE00 bit 7 for the main entrance; the FG/BG byte for midway and secondary entrances) starts the FG at Mario's Y plus the entrance's offset nibble × 16. It lives in a two-block engine that every LM save installs (LM_PARITY "Level entry"). At vanilla height the engine leaves RAM identical to vanilla's.

**Variable level height, LM's way** (LM_PARITY "Level entry"). A horizontal level trades width for height. The header's screen count is the width, and the entrance record's height index (LM's per-level height byte, block B of the engine) picks one of 32 LUT heights with `columns × height ≤ 0x3800`. Objects reach rows past 31 through LM's 32-row BANDS: extended object 01 carries a band in its X nibble and extended object 03 a band in Y. The loader adds `band × 0x200` to every plane pointer, and a parser has to track the band and re-derive these jumps on save the same way it does screen jumps. LM's whole level engine has three parts: entry (blocks A/B), height (block C plus edits to the loader, sprites and objects), and render (its bank-$1F block plus the VRAM patch).

### 9e. Level connections  [CONFIRMED in-game, two-room hack in Mesen]

The chain screen exit ($0DA512) → secondary entrance ($05F800/$05FA00/$05FC00/$05FE00) → destination level was played end to end in a built two-room hack. A door in level $0C5 warps to level $0C6, and the destination's GFX slots are overridden to an imported ExGFX. Mario arrives standing, alive, with the custom graphics applied.

Three things make a connection *look* broken while the data is correct:

- **Enterable vs decorative pipes.** The LOW nibble of object $0F's settings picks the pipe kind, and only kind 1 is enterable. In vanilla, pipes standing on a screen that has an exit are overwhelmingly `$x1` ($21×29, $11×11, $51×10). Decorative pipes elsewhere are `$x0` ($20×50, $10×29). A kind-0 pipe produces Map16 tiles byte-identical to a kind-1 pipe (mouth $137/$138, shaft $135/$136), so a level render cannot tell them apart. Pipes also need Mario pixel-centred on the mouth. Extended object $10 (a door, entered with Up) is the reliable choice for a test.
- **The entrance's camera bits are not optional.** With $05FA00 bits 4-5 (screen boundary Y) and 6-7 (vertical scroll) at 0, Mario spawns outside the visible area and falls out of the level. The warp fires but looks like a crash. Copy the values the source level uses.
- **Time index 0.** Level $0C5's vanilla header has Time = 0. Nothing notices in vanilla, because the opening message box holds the timer, but a rebuilt level without that box dies to TIME UP within seconds.

## 10. Layer 2  [CONFIRMED from bank 05 loader]

If the layer-2 pointer's bank (§3) is not `$FF`, layer 2 is in **object mode**: the same stream format as layer 1, with its OWN 5-byte header copy, which the game skips ($0583FB "address +5"). The screen counter resets to 0. The game loads it only when the header's level mode is a layer-2 mode, that is, not one of {0, 0A, 0C, 0D, 0E, 11, 1E}. LM custom backgrounds also use a real bank, and a per-level settings byte tells the two apart (§10b).

If the bank is `$FF`, layer 2 is a **background image** ($05803B). The data is at `$0C:(ptr&FFFF)` (all vanilla backgrounds are in bank $0C), decoded by the RLE at $058126 into a tile map of two screens, each 16 wide × **27 tall** (0x1B0 tiles per screen, the same screen stride as the layer-1 tilemap planes; a 0x200 stride shows the second screen shifted up 5 tiles). The map repeats horizontally:
```
cmd  = byte;  cmd==FF && next==FF → end
bit7 set: run  — next byte repeated (cmd&0x7F)+1 times
bit7 clr: copy — next cmd+1 bytes literal
```
The buffer is initialized to tile 0x25. The high byte (page) for ALL tiles is 0, or 1 when `(ptr&FFFF) >= 0xE8FF` ($058046). **BG Map16 definitions are at the fixed address $0D9100 + idx×8** (idx = `page<<8 | low`, 0x000-0x1FF), from the `$0FBE` refill at $05819B. The word format is the same as §5. Draw order is backdrop, then layer 2, then layer 1.

### 10a. Background images: codec + why they cannot grow  [MEASURED on vanilla]

The RLE above can be inverted losslessly, and a straightforward encoder never does worse than vanilla's own output: all **17** distinct vanilla backgrounds re-encode 0-50 bytes SMALLER than the streams they came from.

That slack is the entire budget, because under vanilla's loader a background cannot move:

- The page byte is not in the data. The loader derives it from the address (`>= $E8FE` = page 1), so moving a stream across that boundary recolours every tile in it.
- The stream must live in **bank $0C**. The loader hard-codes that bank.

Free space in bank $0C, by page side (runs of 32 bytes or more of `$00`/`$FF` fill):

| page | free runs | largest |
|---|---|---|
| 0 (`< $E8FE`) | `$B66E` 402 B, `$D86F` 145 B | 402 B |
| 1 (`>= $E8FE`) | ten fragments, 32-58 B each | 58 B |

Backgrounds are 200-900 bytes, so a page-1 background has nowhere to go and page 0 only fits the small ones. Growing a background therefore needs LM's custom-background hook (§10b), not just an encoder. Without it, the only safe change is SELECTION: pointing a level at one of the 17 addresses already in use, which needs no allocation. The `$FF` bank in the pointer IS the mode.

The MODE is the pointer's bank, so writing a real bank converts a background-image level to object mode. There is no separate flag in vanilla. Checked against vanilla: 26 levels are in object mode, and **all 26** have a level mode that loads layer-2 objects, so the level-mode set above is consistent in both directions. Levels $0C4, $0EB, $0F0, $0FB, $1DA, $1E6, $1E7 and $1F9 are object mode with an EMPTY stream. Conversely, background-image levels usually sit on a mode that never loads layer-2 objects (that is *why* they use a background), so converting one also needs a level-mode change, or the objects are written and never read.

Vanilla backgrounds are heavily shared: level $105 shares its stream at `$D900` with **282 other levels**. An in-place rewrite of a shared stream changes the background of all of them.

### 10b. LM custom backgrounds  [CONFIRMED — controlled saves]

§10a's "a background cannot move" is true of *vanilla's* loader only. LM does not rewrite a shared background in place. Per its help it "will save the current level's background as a custom background as soon as you modify it", and that custom background is an ordinary relocatable block. Decoded from controlled saves in LM 3.33: the same ROM saved twice, level $105, the second time with exactly one BG tile deleted in the Background Layer 2 Editor, plus two more saves changing only the BG Map16 bank.

| field | finding |
|---|---|
| layer-2 pointer | $05E600 + level×3 holds a REAL 24-bit address with a bank other than `$FF` ($105: `00 D9 FF` became `CC 94 10` = $1094CC). |
| block | RATS: `STAR` + (len−1) word + its inverse, immediately before the stream (`53 54 41 52 B1 01 4E FE` → 0x1B2 payload bytes). It can be allocated anywhere. |
| codec | UNCHANGED from vanilla $058126 (§10): bit 7 set = run of the next byte, (cmd&0x7F)+1 times; bit 7 clear = literal copy of cmd+1 bytes; `FF FF` ends. |
| geometry | 2 screens × 16 wide × **32 tall, stride 0x200**: LM's 512 px backgrounds (432 px → 512 px, "5 extra rows" per its help), NOT vanilla's 27-row 0x1B0. LM's custom screen 1 at stride 0x200 equals the vanilla background's screen 1 at stride 0x1B0 for all 432 tiles, with 0 mismatches. The one edited tile lands at idx 0x065 = screen 0, row 6, column 5, the position LM's status bar reported. |
| mode flag | $0EF310 + level (the per-level layer-2/3 settings byte that LM's $05803B hook reads into `$7FC00B`) went `00` → `06`. Bit 1 set = do not fall through to $058074; bit 2 set = skip the layer-2 map fill. Without it a non-`$FF` bank would be read as an object stream, so this byte IS what separates a custom background from layer-2 objects. |
| BG Map16 bank | The SAME byte, **bits 4-6**: the background's Map16 bank 0-7. Bank N covers BG pages `0x80 + N*0x10`. LM's "Change BG Map16 Bank" dialog lists exactly Bank 00 = pages 80-8F through Bank 07 = pages F0-FF; per its help, "1 bank = 0x10 pages or 0x1000 tiles", one bank per background. Two more saves confirmed it: bank 01 gives byte `16`, bank 07 gives `76`. |
| page byte | No longer derived from the stream address. There are **TWO POSITIONAL PLANES in ONE RLE run** [MEASURED, all three saves]: the 0x1B2 payload decodes to **0x800 bytes** for a 0x400-tile map. `[0x000..0x3FF]` is the low byte per tile, and `[0x400..0x7FF]` is the page within the bank per tile. It is one continuous run with no `FF FF` between the planes, so the boundary is positional (0x400), not delimited. In all three saves plane 2 is entirely `0x00` (the whole background on bank-relative page 0), while plane 1 holds 47 distinct values 0x00-0x2E. An interleaved lo/hi layout would split into two similar distributions, and it does not. LM's help fixes the background at 512×512 px = 32×32 = 0x400 tiles, so 0x800 bytes is 2 bytes per tile and nothing else. A background can therefore reach all 0x10 pages of its bank. Whether the loader masks the plane byte to 4 bits is untested. |
| numbering | LM numbers BG tiles 0x8000 + i (pages 0x80-0xFF). The three streams are **byte-identical**, so the bank lives only in $0EF310 bits 4-6 and never in the stream. |
| relocation | LM allocates a FRESH RATS block on every save (the pointer walked $1094CC → $10980E → $109B50 across three saves). It does not rewrite the previous block in place. |

The runtime half is LM's $05803B hook (its code at $0EF510) together with the $0EF310 table, both part of LM's level engine. Writing a custom background therefore needs no new code once that hook is present ($05803B holding a `JML`/`JSL`):

1. Re-lay the map into LM's geometry (32 rows at stride 0x200; LM's five extra rows go out blank).
2. Add a page plane and RLE-encode all 0x800 bytes as ONE run, with no trailing trim. A vanilla encoder can trim, because vanilla's loader pre-fills the map with tile 0x25. The page plane has no such pre-fill.
3. Allocate a RATS block for it.
4. Write a real 24-bit pointer to $05E600 + level×3.
5. Set `$0EF310[level] |= 0x06`, with the BG Map16 bank in bits 4-6.

This also removes §10a's size limit, and it makes edits FORK as LM's do. Only the edited level gets the new block, and the other levels that shared its vanilla stream keep the `$FF` pointer, since the pointer and the settings byte are both per level.

### 10c. What can go in a background  [LM-DOC — `editor_back.htm`]

The two restrictions are independent, and LM's help states both outright:

- **Map16 numbering.** Each background can only access the tiles within a single bank of the 16x16 editor (1 bank = 0x10 pages, or 0x1000 tiles). Pasting a tile from outside the bank is not an error: the help says LM *may paste the equivalent tile number of the current bank instead*. The bank is switched with Page Up/Page Down in the BG editor (or the Change BG Map16 Bank dialog), and it is per background, not per tile.
- **8x8 graphics.** FG and BG Map16 are separate namespaces but share one pool of 8x8 tiles. FG Map16 cannot be used in backgrounds or BG Map16 in level objects, but both reach the same 8x8 tiles, so FG Map16 tiles can be copied into the BG Map16 area and vice versa and still appear with the correct graphics. The VRAM ceiling is therefore §7d's 10-bit tile number over 8 pages of 0x80. That includes BG2/BG3 (0x200-0x2FF), which need LM's VRAM patch, and pages 6-7 (0x300-0x3FF), which the animation engine re-uploads every frame.

So an editor should limit a background to its bank's whole page range (`0x80 + bank*0x10` to `+0x0F`), all 0x10 pages, not just one, and should remap an out-of-bank paste the way LM does rather than reject it.

## 11. Sprites  [CONFIRMED from disassembly + LM ASM trace]

The pointer table in §3 ($05EC00, 2 bytes per level, bank fixed at $07) is **vanilla only**. LM relocates sprite data and replaces the bank setup at $05D8F5 (vanilla `LDA #$07 : STA $D0`) with a JSL to `PHB : PHK : PLB : LDY $0E : LDA $xxxx,Y : STA $D0`. The operand is a per-level BANK table ($0EF100 on the hacks checked; level 105 → bank $13). The full sprite pointer is `bank<<16 | $05EC00 word`. Reading bank $07 on such a ROM returns STALE pre-move data, which parses plausibly (the screens even come out sorted) but is wrong. The same LM stub stores the level number to `$010B`, which PIXI per-level customs read. The stream ($05D8F9 + $02A82C):
```
header    1 byte   bits5-0 = sprite memory ($1692), bits7-6 = buoyancy ($190E)
entry     3 bytes  b1 = YYYYEEsy  (Y = (y<<4)|YYYY, EE = extra bits, s = screen bit4)
                   b2 = XXXXSSSS  (X nibble within screen, screen = (s<<4)|SSSS)
                   b3 = sprite number (>= 0xE7 → scroll command, $02A866)
0xFF      terminator (lead byte)
```

**Extended list (Lunar Magic)  [CONFIRMED on three levels of one hack + block C decode].** LM narrows the memory field to bits 4-0 ($05D8FC: `AND #$3F` → `#$1F`) to free header bit 5, which then marks the list as extended. LM's loader (block C of the level engine, `$0BF5` bit 5) reads `FF nn` as "the 32-row BAND for the entries that follow" (`nn` < $FE; Y high byte = band×2 | Y bit 4, so row = band × 32 + Y, exactly the object stream's ext 01/03 bands). `FF FE` (or `FF FF`) ends the list. A vanilla list is the degenerate case: no bit 5, and a lone `FF` ends it. LM writes the list as groups per band with a marker before each change, and leaves the first group unmarked when it is band 0. One such level reads `20 | FF 18 | 3 entries | FF 19 | … | FF FE`. Anything that spawns a sprite past row 31 outside the normal load has to open its list with the marker, and set `$0A` = band×2, which the loader's skipped head would otherwise have set.

**LM/PIXI extra bytes.** LM hijacks the sprite advance (vanilla `INY INY INX` at $02A846 becomes a JML into LM's relocatable code bank). The entry size comes from a byte table at **sizeBase + (EE<<8 | sprite#)**: 0x400 bytes, per ROM, sizes including the 3 base bytes (vanilla entries are 3, customs 4-13). Locate it with the signature `4A 4A 29 03 EB C8 C8 B7 CE 88 88 08 C2 10 DA AA 98 18 7F <base:3>`. It is absent on clean ROMs and on LM ROMs without the feature, where every entry is 3 bytes. Sizes MUST be honoured or the stream desyncs.

**Registration [CONFIRMED on two hacks]**: LM's help ("Custom Sprite List Sizes") puts the table's SNES address at PC 0x7750C and 0x42 at 0x7750F. Those are headered offsets, so they are **$0EF30C / $0EF30F**, which is exactly what block C of LM's level engine reads (`LDA $0EF30C..0E` → `$0C-$0E`, `$0EF30F + $BE` → `$0F`; zero = enabled). Observed registrations: $909F52 and $928F4B; a plain LM save has none (`FF`). Read the registration first and fall back to the signature. To author the table the same way: 0x400 bytes of 3 in a RATS block, the pointer plus 0x42 at $0EF30C/$0EF30F, and one entry per (extra bits, number). A placed sprite's record must be padded to the table's size, or it comes up short and the stream desyncs.

**Entrance flags (LM dialog) [CONFIRMED]**: `$192A` bit 7 = slippery (`$86 = $80`) and bit 6 = water (`$85 = 1`). LM's $05DD00 (hooked from $00A6CC) consumes and clears them. Main record: $05DE00 bits 6-7 feed those bits (`TSB $192A` at $05DD48). Secondary record: $05FE00 bit 7 feeds bit 7, and the sixth table's bit 5 feeds bit 6. **Face left** is $06FE00 bit 6 (→ `$13CD`; block A at $1083C1: `BIT $13CD : BVC : STZ $76`). It was previously misread as "BG relative to FG only". Vanilla actions 5/7 still set the flags by themselves ($00A6D5).

### 11a. PIXI custom sprites + spawn emulation  [CONFIRMED on two hacks]

- **Custom-ness is per PLACEMENT, not per number.** PIXI's spawn hijack stores `b1 & $0C` (extra bits << 2) to `$7FAB10,X` and the raw number to `$7FAB9E,X`. Both hooks ($018172/$0185C3 → the PIXI bank) gate on `$7FAB10,X & $08` and dispatch on `$7FAB9E,X`. The config-table pointer canNOT detect customs: PIXI shares one routine across numbers and fills unreplaced entries with $018021 (an RTL).
- **PIXI config table**: base `$B166` + num×16 in the hijack bank (a pointer-dispatch scan finds `$B171` = +0x0B). Fields: +0 type (0 = tweak-only), +1 acts-like, +2..+7 tweakers, +8 init pointer (3 bytes), +0x0B main pointer (3 bytes), +0x0E extra props. The hook trick: `PLA : PLA` pops 2 of the JSL frame's 3 bytes, then `PEA $85C1`, and the custom routine ends in RTL. The leftover JSL bank byte completes the PEA into a long return to $0185C2 (an RTS). The stack stays balanced.
- **Spawning one sprite through the ROM's own loader**, outside a level load: build a 1-record stream (header + record + `FF`) in RAM (for example `$7F0100`) and point `$CE-$D0` at it. Enter the record-spawn body at **$02A84E** with Y = 2 (the b2 offset), X = 0 (the record index), DBR = **2** (the slot-range tables at $02A773 onward are DBR-relative), and `$00`/`$01` = load column/screen (CreateSprite takes the position's high bytes from `$01`). This skips LM 3.x's rewritten walker ($10FA9F), which needs level-load state (`$0BF4` flags, the per-screen stream index `$0CF6/$0D36`). The status value flows through `$04` to `STA $14C8,X` at $02A975. The slot search is at $02A918 (start and end per sprite memory `$1692`, from the tables at $02A773/$02A7AC; `$1692` = 0 is safe). After the spawn: seed `$15E9` = slot, clear `$15A0,X` each frame (the spawn marks sprites offscreen), and run frames with X = slot.
- LM and PIXI hijack chains JML into the `$80`+ FastROM mirror banks, so a top-level RTS can come back with the program bank = bank | `$80`. An emulator's return sentinel has to compare `& 0x7F`.

## 12. Tile animations — the header-dependent Map16 appearance  [DECODED]

Some Map16 tiles look different depending on the header (LM: "The FG/BG index also alters which animated tiles are used"). The reason: 8x8 VRAM tiles in the ranges below are re-uploaded EVERY FRAME by NMI DMA, and their static content in the GFX files is a placeholder (such as the 'COIN' text that shows up in a naive render). LM displays animation frame 0. Decoded from `CODE_05BB39` (bank 05):

- Per frame: group = `frame&7`, phase = `(frame&0x18)>>3` (0-3). Each group drives 3 DMA slots.
- **VRAM destinations**: a word table at $05B93B + group×6 (3 words). Each slot uploads **4 consecutive 8x8 tiles** (0x80 bytes, 4bpp) at word/16. Groups 0-6 cover 8x8 tiles 0x40-0x83, 0xDA-0xDD and 0xEA-0xED (destination 0 = slot unused).
- **Animation id** = group×3 + slot, modified by the behaviour byte `$05B96B[group*3+slot]`: 0 = as is; 1 = POW-dependent ($05B97D, +0x26 when a POW is active); anything else **+= `$05B98B[tileset]`**. That is the header-dependent part, with offsets per tileset 0-D of 0, 5, 10, 15, 20, 20, 25, 20, 10, 20, 0, 5, 0, 20.
- **Frame source**: `AnimatedTileData` ($05B999)`[id*8 + phase*2]` is the 16-bit bank-$7E RAM address of the 0x80-byte 4bpp source block. Frame 0 (LM's static view) is the first word. The observed source range is `$6D80-$AC20`.
- Map16 DEFINITIONS also animate for tilesets other than 0/7. `CODE_0581FB` leaves tiles 0x1C4-7/0x1EC-F definition-animated through the source list at $05E55E ($05E5C8, plus static definitions at $0D8A70 for tilesets 0/7). The animated definition frames are written per frame elsewhere (targets cached at `$1430/$1431`).

LM's bypass AN2 slot (§7d w0) replaces GFX33 for custom levels.

### 12a. RESOLVED: the animated-GFX buffer  [CONFIRMED]

`CODE_00B888`: GFX32 and GFX33 are NOT in the pointer tables. They decompress from a fixed pointer whose operands live at **$00B88B (16-bit) / $00B890 (bank)**. Vanilla's is $08BFC0. Read it per ROM, because LM repoints it when Mario or animated GFX are edited. The data is decompressed as 3bpp (0x2400 bytes) to $7E2000, then expanded from 3bpp to 4bpp backwards to fill **$7E7D00-$7EACFF**. The expansion zero-fills plane 3, so an `AnimatedTileData` address A maps to 3bpp source tile `(A - 0x7D00)/0x20` (24 bytes per tile) on a 3bpp ROM.

On an LM 4bpp ROM that blob is packed 4bpp (32 bytes per tile). LM decompresses GFX33 straight to $7E7D00 as four planes (§12g "The rest of LM's 4bpp mode"). A reader has to decode at the ROM's depth, or animated tiles garble.

The NMI consumer at $00A3A4 moves 0x80 bytes (4 tiles) per slot. Destination word $0800 is special-cased into two 0x40 transfers, at $0800 and $0900 (tiles 0x80, 0x81, 0x90, 0x91). Sources below $7D00 (such as id 5, the berries) come from the second blob (§12b, below).

### 12b. Second animated blob — berries etc.  [CONFIRMED]

$00B8D7, the fall-through after the GFX32 conversion, decompresses a second blob from `bank:(operand at $00B8D8)` (vanilla $088000) to $7E2000. The decompressor writes through `[$00],Y` without advancing `$00`, so blob 2 lands over blob 1's spent 3bpp source. It is stored RAW 4bpp (0x5D00 bytes). The DMA-visible RAM is therefore `$2000-$7CFF` = blob 2 (the berries at id 5's `$6D80` are at offset 0x4D80) and `$7D00-$ACFF` = converted blob 1. Resolve sources >= `$7D00` from blob 1 and sources >= `$2000` from blob 2 as 4bpp.

## 12b. Layer 3  [vanilla path CONFIRMED; LM's own records PARTIAL]

**The geometry is fixed by the PPU setup, not by the level**  [CONFIRMED — `SetUpScreen` $008A7F]. `$2109` (BG3SC) = `$53`, so the layer-3 tilemap is **64×64 tiles at VRAM word `$5000`**: four 32×32 screens in the order left-top, right-top, left-bottom, right-bottom. `$210C` (BG34NBA) = `$04`, so its character data starts at **word `$4000`**. $00A993 uploads GFX **28, 29, 2A, 2B** back to back from there, `$400` words each, so the four slots LM calls LG1-LG4 fill exactly the **512 2bpp tiles** a tilemap word can name. A layer 3 is therefore **512×512 pixels**. That is also where the ExAnimation destination range `1C00-1DFF` comes from (§12e), and why LM's tilemap-bypass file size defaults to `0x2000` = 64×64 words.

**The tilemap is picked by (level mode, option), and it is a stripe image**  [CONFIRMED]. `CODE_009FB8` computes `index = $1931*3 + ($1BE3-1)`, the level mode times three plus the Layer 3 Options value below, which is why option 0 means no layer 3 at all. That index reads the 3-byte `Layer3Ptr` at **$059000** (not $058FFD), and $00A02F hands the block to the **stripe-image uploader $00871E**. The table is exactly **45 entries**: it ends where the first tilemap block, `DATA_059087`, begins, so it covers level modes 0-14 only. Vanilla has six distinct blocks in $059087-$05A221, and the default is $059549.

A stripe-image entry is 4 bytes and then data, the format $00871E consumes:

| bytes | meaning |
|---|---|
| +0, +1 | VRAM word address, **big-endian** |
| +2 | bit 7 = step DOWN a column (+32 words, one row of a screen) instead of across; bit 6 = RLE; bits 5-0 = high bits of the length |
| +3 | low bits of the length. The length is in **BYTES, minus one**. |
| data | the tilemap words, low byte first; or, for RLE, ONE word repeated to fill the length |
| end | a first header byte with bit 7 set (`$FF`) |

Words the script never writes are **not** tile 0. The console still has whatever the last level left in that VRAM, plus the status bar it redraws every frame, and tile 0 of GFX28 is a font glyph. Filling the gaps with tile 0 draws a screen of noise the game never shows. Treat unwritten cells as empty (back-area colour).

**Not the same thing as the layer-3 SCROLL strips.** `CODE_058955` (`$1925` → `PtrsLong05895E` → `CODE_058D7A` / `CODE_058B8D` / `CODE_058C71` / `Return058C70`) does NOT read `Layer3Ptr`. It builds the per-column/row strips in `$1CE8`/`$1D68` by expanding the **layer-2 RAM map** ($7EB900/$7EBD00) through the **same BG Map16 definitions at $0D9100** (§10). That is why LM warns that tides and layer-2 data cannot be used in the same level. The layer-3 priority flag is header byte 2, bit 7.

**LM's two dialogs** (field sets confirmed by opening them, both in the Level menu):

*Change Layer 3 Settings* has Layer 3 Options, exactly four: `Blank Layer 3`, `Water, high and low tides`, `Water, low tide only (smasher if tileset is 1)` and `Tileset Specific (current tileset is N:<name>)`. It also has "Make tides act as", a "Force Layer 3 tiles with priority" flag, an "Enable advanced bypass settings" flag, and the advanced group: CGADSUB, Move Layer 3 to Subscreen, Fix scroll sync, Vertical Scroll, Horizontal Scroll, Initial Y Position/Offset and Initial X Position/Offset. Selecting a tides option raises a **destructive** confirmation ("will cause Lunar Magic to delete objects and sprites beyond the new lower max screens limit"), because tides halve the screen count.

*Layer 3 GFX/Tilemap Bypass* has "Enable bypass of standard Layer 3 GFX for this level" with four slots, **LG1-LG4, defaulting to GFX 28/29/2A/2B** (shown with their vanilla source addresses `05C26C`/`05C8A3`/`05CD7B`/`05D2F0`). It also has "Enable bypass of standard Layer 3 tilemap" with a GFX tilemap file **LT3** (default `7F Skip File`), a Destination for File (default `Under Status Bar`) and a File Size (default `0x2000 bytes 512x512`). The dialog notes that standard GFX are 0-31, ExGFX 80-FF and Super ExGFX 100-FFF.

**A tilemap file is too big for the shared decompression buffer  [MEASURED].** A tilemap file is `0x2000` bytes, **twice any GFX file**. The shared buffer at $7EAD00 has room up to $7EBCFF, which a 4bpp GFX file fills exactly (§6a-13; LM accepts overrunning into the layer-2 buffer at $7EB900 there). Decompressing `0x2000` bytes into it runs to $7ECCFF and writes straight through:

| region | |
|---|---|
| $7EB900 layer-2 Map16 map | clobbered |
| $7EBD00 layer-2 page plane | clobbered |
| **$7EC800 layer-1 Map16 map** | **clobbered** |

The level then comes up with **one Map16 tile repeating in a grid**: the tilemap's own bytes read as map entries. Nothing in VRAM is wrong, so VRAM-side checks pass while the level is visibly broken. The fault is in RAM, one buffer over. A loader for LT3 files needs its own buffer. `$7FA000` works: `0x2000` bytes there end at $7FBFFF, clear of LM's record cache at `$7FC006` and the Map16 page plane at $7FC800.

**The blank tile, and what a flat LT3 file must pad with  [MEASURED on vanilla].** Of the 512 tiles LG1-LG4 supply, exactly **two** are fully transparent (every pixel on colour 0): **`0x0FC`**, in LG2, the blank that SMW's own status bar pads with, and `0x179`, in LG3. LG1 and LG4 have none. A flat tilemap file cannot say "untouched", so its gaps have to name one of those tiles, in palette 0 with **priority clear**.

**0xFFFF is not a safe filler.** It looks safe in an editor that skips tile numbers >= 512. On the console every bit of it matters. BG3's character base is word `$4000` and a 2bpp tile is 8 words, so tile `0x3FF` fetches its graphics from word `$5FF8`, *inside the tilemap region itself*. `0xFFFF` also sets bit 13, the **priority** bit, which draws the result in FRONT of layer 1. A full `0x2000` map at "Start of Layer 3" filled with `0xFFFF` covers the level in garbage.

**LM's advanced layer-3 reader** sits at **$0FFD9F** (`5A AF 06 C0 7F ...` = `PHY : LDA.l $7FC006`) in every LM ROM that has the layer-3 hack installed. It is `FF FF` in vanilla. Without it, the advanced settings packed into the record (below) are read by nobody.

**The install gate  [CONFIRMED — this is why the first three saves wrote nothing].** LM will not install its layer-3 hack until its restore system can find *the original unmodified ROM with header*. It prompts "Restore System Issue ... browse to a copy of this file now?" and creates an Auto Full Restore Point first. Until that prompt is answered, opening *Change Layer 3 Settings*, changing the option and saving the level produces a **byte-identical ROM**. That was verified three times, even though LM's editor re-renders with the new tilemap. Any controlled save for layer 3 has to satisfy the restore system first.

Once it is satisfied, enabling the GFX bypass and saving installs the hack: **~24 KB across 7871 runs**. The hook sites are listed under Step A below. The bank-$0F block includes the bytes `4C 4D 03 01` ("LM" + version) at $0FF15C, LM's layout marker (§12g "Submap GFX dialog").

**The GFX bypass: NOT a new table — the tail of §7d's record  [CONFIRMED]**

An earlier reading put the record boundary 0x18 bytes too early and concluded that a second per-level table existed. Both halves of that were wrong. Aligned to `tableBase + level*0x20`, the LG slots fall exactly on **words 12-15 of the Super GFX Bypass record**. `2B 2A 29 28` was never a constant. It is the vanilla LG4/LG3/LG2/LG1 default set, and a ROM saved before the layer-3 hack existed already carries it.

| field | finding |
|---|---|
| words | w12 = LG4, w13 = LG3, w14 = LG2, **w15 = LG1**: reverse slot order, the same convention as the rest of the record. `& 0xFFF` = GFX/ExGFX file, `0x7F` = keep the vanilla file. w13 bits 13-14 also carry the Layer 3 Option (below). |
| file size | An LG slot's file is **0x800 bytes = 128 tiles of 2bpp**, whatever the ROM's depth. The layer-3 pass copies a fixed `0x400` words straight through (`LDX #$03FF`, no expansion). Padding such a file to the ROM's 4bpp size of `0x1000` gives 0x800 bytes the slot can never use, and makes the decompressor write that much extra into the shared $7EAD00 buffer on every level load. **This is invisible from the slot itself**: the upload takes the first 0x800 either way, so layer 3 renders correctly while the overshoot lands elsewhere. Measured symptom: pointing LG4 at an imported ExGFX padded to 0x1000 corrupted **layer 1** in game, and clearing that one override fixed it. Size a file for the slot that consumes it, not for the ROM's depth. |
| enable | **w0 bit 14**, separate from the FG/BG/SP bypass on w0 bit 15. LM's loader at $0FF9E0 is literally `LDA [record] : ASL : BPL default`, and its "default" is a fixed record at $0FFA6F whose tail is `2B 2A 29 28`. So `w0 = $407F` means layer-3 bypass only, and `$8008` means the FG/BG/SP bypass only. Reading either bit as "the record is in use" breaks the other kind of ROM. |
| location | The same table and the same plain `LDA.l base,X` reader at $0FF7F0 as §7d. LM allocates the table on the save that first needs it. |
| VRAM | LM's own destination table at $0FFA7F holds `$4C00 $4800 $4400 $4000` for slot index 0-3, so **LG1 → word $4000, LG2 → $4400, LG3 → $4800, LG4 → $4C00**, 0x400 words each. That independently confirms the 128-tiles-per-slot layout. |

**The TILEMAP bypass  [CONFIRMED — all four fields]**, from six controlled saves, each moving one control. The whole thing is **word 1**, gated by **w0 bit 13**.

| field | finding |
|---|---|
| enable | **w0 bit 13** (`0x2000`). Ticking "Enable bypass of standard Layer 3 tilemap" alone moved exactly that bit, `407F` → `607F`, and nothing else in the record. So w0 carries THREE independent enables: bit 15 FG/BG/SP, bit 14 layer-3 GFX, bit 13 layer-3 tilemap. |
| w1 bits 0-11 | the LT3 file (`0x7F` = Skip File). One save ended at `w1 = 8080`, LT3 = ExGFX 80. |
| w1 bits 12-13 | file size: **0 = 0x2000 (512x512), 1 = 0x1000 (512x256), 2 = 0x800 (256x256), 3 = "Do not use"**. Read off four saves: `807F 907F A07F B07F`. |
| w1 bits 14-15 | destination: **0 = Under Status Bar, 1 = Start of Layer 3, 2 = Last Line of Status Bar, 3 = Bottom Half of Layer 3**. Four saves gave `007F 507F 907F D07F`, whose high nibbles are `dest<<2 | size`. A bit 12 that first looked like a stray "not default" flag was the size field, which LM's dialog had quietly left on 0x1000 from an earlier step. |

LM VALIDATES on OK. An LT3 file that is not inserted is refused ("Graphics file not found in ROM"), and so is a file larger than the declared size ("larger than it should be for the slot it's in"), including against "Do not use", which permits 0 bytes.

**Destinations [CONFIRMED — LM's own table].** $0FFEBC holds the four VRAM words **`$50A0 $5000 $5080 $5800`** for destinations 0-3. Under Status Bar is +`$A0` (five rows of 32, clearing the status bar), Start of Layer 3 is the window base, Last Line of Status Bar is +`$80` (four rows), and Bottom Half is +`$800`. Next to it, $0FFEB4 holds the sizes (`$2000 $1000 $0800 $0000`), and $0FFEC4 holds the status bar tilemap's own size, `$0140` = 320 bytes = 32×5 words. LM's help names the last two by file offset ("0x800BC holds the 2 byte layer 3 VRAM destination for that setting, 0x800C4 the 2 byte size of the layer 3 status bar tilemap"), which independently gives the same bytes.

**Destination 0 exists to protect the status bar.** The status bar is the first 32×5 words of the same window, so a full 0x2000 map at "Start of Layer 3" (`$5000`) copies its own top five rows over the score, coins, time and lives. A custom layer 3 normally sets the tilemap priority bit (that is how mist draws in front of the level), so it covers the HUD rather than blending with it. Under Status Bar avoids that without shifting the picture: the offset applies to the SOURCE as well as the destination, so the file's row 5 still lands on row 5 and only its first `$140` bytes are not uploaded. A screenshot cannot settle this, because a full 0x2000 file fills the whole window and all four destinations look the same.

**w1 is ALSO AN1: an overlap.** §7d and §12d read w1's low bits as the ExAnimation AN1 slot, traced from LM's loader at $0FF7F0. The tilemap bypass reads the same bits as the LT3 file. Both cannot hold a file at once. Either one of the readers masks differently, or LM treats the two features as mutually exclusive per level. Which is not established.

**Which palettes layer 3 can use  [MEASURED over every vanilla layer-3 tilemap].** All EIGHT. The common assumption that a layer 3 is limited to one palette is wrong twice over: the group is per TILE (bits 10-12 of each tilemap word), and every group is addressable. 2bpp makes a group four colours, so layer 3's whole reach is CGRAM `00-1F`, 32 colours.

What differs between the groups is what SMW puts in them:

| groups | contents |
|---|---|
| 2, 3, 6, 7 | Layer 3's OWN colours: the $00B170 block, which lands at CGRAM `08-0F` and `18-1F`. It loads from a fixed address that no header byte indexes, so these four are identical on every level in the ROM. Per-level changes need an LM custom palette, which overrides all 256 colours. |
| 0, 1, 4, 5 | CGRAM `00-07` and `10-17`: the backdrop, colour 1's white, and the level's own BACKGROUND palette ($00B0B0 indexed by the header's BG palette byte). A layer-3 tile drawn with one of these TINTS WITH THE LEVEL. |

The game's own maps use both sets. Cell counts per group:

| tilemap | groups used |
|---|---|
| tides (option 2) | `6x1982`, plus 2 cells of group 0 |
| ghost house (mode 2, option 3) | `6x190 7x136`, plus 18 cells of group 0 |
| scrolling rocks (mode 14) | `4x194 5x94`, then `1x16 6x10 3x2` |

So the tides live in layer 3's own block, and the scrolling rocks deliberately live in the level's background palette. Group 2 is the only one nothing in the ROM uses.

**The Layer 3 Options field  [CONFIRMED for 0 and 3; 1/2 by dropdown order]**, isolated by two saves that change only that dropdown (Blank Layer 3 → Tileset Specific) with the hack installed on both. Exactly TWO semantic bytes moved, and LM writes the value to both:

- $05F200 + level, **bits 6-7**: the VANILLA per-level byte, read into `$1BE3` at $05D928 and indexed straight into `Layer3Ptr` above. LM's *Change Layer 3 Settings* dialog writes it, and it selects the layer-3 tilemap. It has nothing to do with layer 2, despite an older name for it.
- bypass record **+3, bits 5-6** (w1's high byte): the same value mirrored into LM's own record.

Values: 0 = Blank Layer 3 [CONFIRMED], 1 = Water, high and low tides, 2 = Water, low tide only (smasher if tileset is 1), 3 = Tileset Specific [CONFIRMED]. Readback: Blank gives $05F200+105 = `00` and rec+3 = `00`; Tileset Specific gives `C0` / `60`. 1 and 2 are INFERRED from the dropdown's order. Both are tides options, and selecting either raises LM's destructive "Max Screens Mode Change Alert".

**The ADVANCED BYPASS  [CONFIRMED]**, the group that answers "I don't want the tileset's default". LM's help explains why it exists: the tilemap can be bypassed from the Layer 3 GFX/Tilemap Bypass dialog, but the behaviour and scrolling of the original setting remain unless the advanced bypass settings are enabled. So a custom tilemap on a Tileset Specific level still scrolls like the vanilla beta cage until this group is on, and there is no other per-level override. LM has no "use tileset N's layer 3" control at all.

It costs no new table. It rides the **spare high nibble of nine of the record's sixteen words**, which are free because a slot's file id is only 12 bits. LM's reader at **$0FFD9F** (gated on `$7FC009` being `$41`/`$42`, that is, the record is in use) glues them into four variables through a helper at $0FFE82 that reads a nibble pair (`LDA [$8A],Y : AND #$F0 : DEY DEY : LDA [$8A],Y : LSR x4 : ORA`), leaving Y two lower each call:

| variable | built from | meaning |
|---|---|---|
| `$7FC01A` | nib(w11) | bits 0-1 initial X index, bit 2 CGADSUB, bit 3 layer 3 to subscreen |
| `$7FC01B` | `nib(w3)<<4 | nib(w2)` | never non-zero in nine controlled saves. Bits 0-5 unknown, most likely "Make tides act as", which is greyed out on every level without tides |
| `$7FC01C` | `nib(w10)<<4 | nib(w9)` | bits 0-5 = the Y offset's high bits, **bit 6 = the vertical scroll's bit 4, bit 7 = the horizontal's** |
| `$145E` | `nib(w15)<<12 | nib(w14)<<8 | nib(w13)<<4 | nib(w12)` | bit 0 **enable**, bit 1 scroll-sync fix, bit 2 unused, bits 3-7 the Y offset's low bits, bits 8-11 horizontal scroll bits 0-3, bits 12-15 vertical scroll bits 0-3 |

- **The advanced group has no enable bit in w0.** Its enable is `$145E` bit 0 = nib(w12) bit 0. That was the one thing the first controlled save moved (one record byte `00` → `10`), and nothing else changed in the ROM except relocated level data.
- Y is stored **times 8** in a 14-bit signed field (`$7FC01C` bits 0-5 : `$145E` bits 3-7), which is exactly the -0x400..0x3FF the dialog accepts. $109964 turns it into `$146C`, layer 3's Y position in pixels = Y×16. X is a 2-bit INDEX into `00 04 08 10` tiles, not a value: the game computes index×`$40` pixels and special-cases index 3 to `$100`, which is why the list skips `0C`. `$146A` gets the result.
- **Scroll codes** are 5 bits, and LM's dropdown order is NOT the code order. Measured with one save per entry (21 of them), the list index → code map is `00 01 02 03 18 19 04 1A 05 | 06 07 08 09 10 11 | 0A 0B 0C 0D 0E 0F` for `None, Constant, Medium, Medium 2, Medium 3, Medium 4, Slow, Slow 2, Fast | Auto-Scroll Up/Left Slow..Fast 4 | Auto-Scroll Down/Right Slow..Fast 4`. The code space explains the order: 0-5 are six rate handlers, 6-0x11 are the twelve auto-scroll speeds sharing one handler ($109D3B holds them: ±`$40 $80 $100 $200 $300 $400` per frame), and 0x18-0x1A are three later rate handlers appended to the codes rather than to the list.

"Make tides act as" and LM's mirror of the priority flag are not located.

**How LM's advanced engine works**, in three pieces, measured from LM's code and in Mesen:

| piece | behaviour |
|---|---|
| reader | $0FFD9F, described above. It must take the record for the level being loaded. LM reads its own `$7FC006` cache. A reimplementation that derives the record from `$FE` has to run before anything clears `$FE`; LM's fade-in hook at $00A5BF does (§12g "Palette engine"), so `$010B` is the reliable level number at that point. |
| engine | LM's $109964 replaces `LDA $1BE3` at $00A01F. It applies colour math (`$40` bit 2), the subscreen move (`$0D9D` bit 10 plus `$212C`/`$212E`), initial X (index×`$40`, index 3 → `$100`) into `$146A`, and initial Y (the 14-bit signed Y×8 field sign-extended to Y×16, by `ASL ASL : CMP #$8000 : ROR`) into `$146C`, then resolves the two 5-bit scroll codes. |
| dispatcher | hooked at vanilla's own per-frame layer-3 scroll site $05C40C (`LDA $1403 : BEQ +3`, 5 bytes → `JSL : RTS`). It recomputes `$22`/`$24` from layer 1's camera (`$1A`/`$1C`), and mirrors into `$1B78`/`$1B7A` when the scroll-sync-fix bit is set. When the group is off, control has to return to $05C414/$05C494 so an unbypassed level keeps vanilla's exact behaviour. |

**The rate ladder, measured from LM's handlers.** The rates are a shift ladder off layer 1's camera, not a table of speeds: `$22 = $146A + ($1A >> n)`. Codes `02 03 18 19 04 1A` are `n = 1..6`, exactly the dropdown order Medium, Medium 2, Medium 3, Medium 4, Slow, Slow 2. Code `00` (None) holds at the offset, `01` (Constant) is 1:1, and `05` (Fast) is `offset + cam + cam/5` through the hardware divider (`$4204`/`$4206`/`$4214`), which is 1.2×. LM's unused codes `12-17` fall through to Constant. LM dispatches through two 27-entry pointer tables, $109CBB (horizontal) and $109CFB (vertical). LM's help confirms the ladder from the other side: "Variable" is 1/2 the position of layer 1, "Variable 2" is 1/4, and "Slow" is 1/32, which are shifts 1, 2 and 5. A console check: with `$1A` forced to `$0800` at the dispatcher's entry and code `18`, `$22` reads back `$0100`, which is `$800 >> 3`, the Medium 3 rung. [CONFIRMED]

**The twelve auto-scroll rates (codes `06-11`)** come from LM's handlers at $109AB4 (horizontal) and $109B78 (vertical), which both pointer tables send all twelve codes to. They are not a fraction of the camera at all. They are a SPEED in 8.8 fixed point, accumulated:

```
fraction += speed                       ; one byte of fraction, per axis
position += (whole pixels carried out) + $17BD/$17BC
```

`$1458`/`$145A` hold the speed and `$145C`/`$145D` the fraction. Their layout lets one routine serve both axes: the pairs are alternately two bytes apart (`$1458`, `$146A`, `$22`) and one byte apart (`$145F`, `$145C`, `$0BE6`), so X = axis×2 and Y = axis index works for all six. The one pair in REVERSED order is `$17BD` (horizontal) / `$17BC` (vertical), vanilla's accumulated camera delta, computed at $05BC0C in the very routine that then calls the dispatcher.

| item | behaviour |
|---|---|
| table | $109D3B, indexed by code×2. Codes `06-09` and `10-11` climb `+$40 +$80 +$100 +$200 +$300 +$400` (Up/Left Slow..Fast 4), and `0A-0F` are the same six negated (Down/Right). `$40` is a quarter pixel a frame (LM's help names it as the fog/goldfish drift), and `$400` is four pixels, the tide speed. |
| seeding | At level load: the speed; the fraction (0, or the speed's own LOW BYTE when the speed is negative, through LM's `BMI` past its `LDA #$0000`, which delays that rate's first whole pixel by three frames at `$40`); the position from `$146A`/`$146C` (for auto-scroll LM's help calls the X/Y fields "actual positions", not offsets); and bit 7 of `$0BE6`/`$0BE7`, LM's skip-one-frame flag, so the level opens exactly where it was seeded. |
| guards | `$9D` (sprites locked / paused) freezes it, holding the position rather than writing one. LM returns without touching `$22` there. |

The TIDE variant of the same handler (`$1403` non-zero) is a different routine behind the same codes.

**The two blend switches CANCEL OUT  [LM-DOC + CONFIRMED on the console].** LM's help says the CGADSUB checkbox decides whether layer 3 appears translucent against layers on the subscreen, and that this *assumes layer 3 is on the main screen* (which it normally is) and that there are layers on the subscreen to be translucent against. The other box moves layer 3 ONTO the subscreen, where there is nothing left to blend it against, so the layer comes out opaque. Ticking both is the natural thing to do for translucent mist, and it is the one combination that cannot produce it. Screenshots of the same level settle it. With CGADSUB alone, the mist's black areas vanish (adding black is transparent) and its clouds blend over the level. With both ticked, the mist draws as solid blobs.

LM's help also names what the level header's layer-3 priority flag is for: "Force layer 3" shows layer-3 tiles that have the priority bit set above all other layers and sprites, and it does not work if layer 3 is only on the subscreen.

**Two hazards in the vanilla code around the hook sites  [CONFIRMED in Mesen].**

| item | finding |
|---|---|
| `$13D5` | Vanilla's "this level's layer 3 does not move" flag. $00A012 sets it for every (mode, option) whose entry in the byte table at $009F88 is NEGATIVE, and for **mode 0, option 3** that entry is `C0`. That is an ordinary horizontal level set to Tileset Specific, which is every level the advanced group exists for. Its only reader is $05BC3F, and it gates the `JSR $C40C` that reaches the per-frame scroll routine at $05C40C. Exec counts over a whole level: **0 hits on $05C40C** with the flag up, 250 with it forced to 0. LM clears it at **$109A65** (`STX $13D5`, X = 0 on the path every horizontal level takes). That site is `STX`, not `STA`/`STZ`, so a scan for stores to `$13D5` that looks only at `STA`/`STZ` misses it. LM raises it again for one vertical-level case (`$1403` = 0 AND `$5B` negative AND `$1413 & $F0`). |
| `$00` | LIVE ACROSS THE $00A01F SEAT. $009FC0 puts the level's `mode*3` there, and $00A026, two instructions after the JSL returns, adds it to the option to index `Layer3Ptr`. LM's nibble-pair helper uses `$00` as scratch, which is harmless when it is reached from the GFX loader but fatal if called from this seat: the stripe uploader then runs on a pointer that is not a script and the whole screen comes up dark, which looks like "the settings do nothing" rather than a crash. Code at this seat has to preserve `$00`. `$01` and `$02` are safe, because that routine WRITES both before reading them. |

**LM's layer-3 install — the measured footprint  [ISOLATED]**

Two controlled saves isolate exactly what LM stamps, and they are two SEPARATE installs, not one.

*Step A: layer-3 GFX bypass and the record machinery* (a 1 MB ROM, 32 runs). Triggered by ticking "Enable bypass of standard Layer 3 GFX".

| site | vanilla | LM |
|---|---|---|
| $009471 | `AE C6 13 A9 18` | `JSL $0FF9C0 : NOP` |
| $00A140 | `85 20 E2 20` | `JSL $0FFAB0` |
| $00AA06 / $00AA47 | `F0 03` | `EA EA` (two early-outs removed) |
| $00AA50 | `A2 03 B5 04 9D` | `JSL $0FF780 : RTS` |
| $00AA6C | `28 BA 00` | `60 F1 0F` |
| $049DFE | operand | → $0FFAF0 |
| $0583B8 | `AD 25 19 C9 09` | `JSL $0FF7F0 : NOP` |
| bank 0D | five `E3 B3` | `E0 F0`/`F0 F0` at $0DA4BE, $0DC203, $0DCE03, $0DDA03, $0DE903, plus 25 new bytes at $0DF0E0 |

New blocks in bank $0F (start and length in bytes): $0FEFC3 (25), $0FF15C (139), $0FF200 (1448), $0FF7D0 (15), $0FF7F0 (134), $0FF8A0 (71), $0FF900 (111), $0FF9C0 (11), $0FF9E0 (175), $0FFAB0 (36), $0FFAF0 (17), $0FFB20 (523), $0FFD80 (332). The record table is a RATS block at $128008 (28160 bytes).

The layer-3 upload rides the level-GFX loader at $00AA50: a copy of 0x400 words per slot (vanilla's own $00A9AC shape, no 3bpp-to-4bpp expansion, because layer 3 is two bit planes by construction), with destinations from $0FFA7F. It has to run on EVERY level load, bypassed or not, falling back to GFX 28-2B per slot as LM's default record does. Otherwise the first bypassed level's layer 3 follows the player into the next level. LG1 (GFX 28, the status bar's own font) is the one slot that draws on every level, which makes it the clearest console test: point it at 0x800 bytes of `FF`, and the status bar and the title logo's layer-3 tiles draw as solid blocks. [CONFIRMED in Mesen]

*Step B: layer-3 TILEMAP bypass* (a 1 MB ROM, **11 runs, a clean isolate**). Triggered by ticking "Enable bypass of standard Layer 3 tilemap", with LT3 left at 7F Skip File.

| site | vanilla | LM |
|---|---|---|
| $00A01F | `AD E3 1B F0 20 3A` | `22 64 99 10 F0 1F`: `JSL $109964` in place of `LDA $1BE3 : ... : DEC`. The routine does that work itself, and the following `BEQ` shortens by one because a JSL is a byte longer than the LDA. |
| $00A153 | `A9 06 85 12` | `JSL $109DE4` |
| $0194B6 | `A9 00 8D 93 16` | `JML $109E04 : RTS` |
| $05C40C | `AD 03 14 F0 03` | `JSL $109D7B : RTS` |

Blocks: RATS in bank $10 at $109844 (280 bytes), $109964 (1216) and $109E2C (104).

**The advanced group belongs to step B, not step A.** $109964, the routine that replaces `LDA $1BE3`, opens `LDA $145E : LSR : BCS`. It returns the layer-3 option when the advanced group is off, and otherwise applies the whole advanced group first. So the tilemap hook is also the scroll/blend engine. **CORRECTED**: an earlier reading said the advanced path "takes the option from `$7FC01A` bits 0-1 instead". It does not. The `AND #$0003` at $1099A4 is the initial-X INDEX (it feeds `XBA : LSR : LSR : STA $146A`), and the group does not change the option answer. That matters because the option gates the tilemap upload, so reading it out of the X-position bits would blank layer 3 on three levels out of four. Only the nibble READER ($0FFD80 block) ships with step A, which is why a ROM can have the reader and not step B. The settings are then gathered into RAM that nothing reads.

**Where the tilemap copy can hang  [MEASURED].** **$00A153 is never executed on the level-load path** (a Mesen exec callback saw 0 hits over a whole load), while $00A01F and the tail of the same routine run three times each. A copy placed at $00A153 also runs before vanilla's stripe script, which then overwrites it. The order that works is after vanilla's upload: the uploader call at the tail of the picker, $00A041 (`JSR $871E : RTS`), runs the vanilla upload and can then copy the bypass over the top. At that point the level number is in `$010B`. `$FE` is the GFX loader's arm flag at $00AA50 and is gone by then. And because the copy rides that routine, **option 0 still means no layer 3**: $00A022 branches past the whole picker, so a bypassed map on an option-0 level never loads. A console check of this placement: at the instant the routine returns, VRAM word `$5000` holds the authored map byte for byte. [CONFIRMED in Mesen]

### Where layer 3 lands on screen is the LEVEL MODE's screen registers, not priority alone  [CONFIRMED]

$058505-$058517 reads three 0x20-byte tables, indexed by the **level mode**, into `$0D9D` (main screen, `$212C`), `$0D9E` (subscreen, `$212D`) and `$40` (CGADSUB, `$2131`).

For **mode 0**, the ordinary horizontal level, those bytes are `main $15`, `sub $02`, `cgadsub $24`:

| register | value | meaning |
|---|---|---|
| `$212C` main | `$15` | BG1 + **BG3** + sprites |
| `$212D` sub | `$02` | **BG2 only** |
| `$2131` CGADSUB | `$24` | backdrop and **BG3** add the subscreen; no half bit, so it saturates |

So **the background image is not on the main screen at all**. It cannot cover layer 3. Layer 3 sits above it, and the image *adds into* layer 3 through colour math, which is the opposite of what mode 1's priority order alone would suggest. Modes with `main $17` / `sub $00` (mode 2 and similar) put the image back on the main screen with no subscreen, and there layer 3 is the one underneath, with nothing to blend against.

The level header's **Layer 3 Priority** is a separate axis. $058566 reads header byte 3 bit 7 into `$3E` as `$09` rather than `$01`, which is mode 1's BG3-priority bit. It does not lift the whole layer. It lifts the cells whose **own** priority bit (tilemap word bit 13) is set, and leaves the rest at the very back. Vanilla's tide levels (`002`, `0BE`, `0C1`, `102`, `127`) are the levels that set it. A hack can rewrite the three tables, so read them rather than assume them.

## 13. Object expansion via emulation  [CONFIRMED on vanilla-layout ROMs]

Instead of porting every bank-0D handler by hand, a tool can EXECUTE the ROM's own `LoadLevelData` ($0585FF) in a small 65816 interpreter: RAM banks $7E/$7F emulated, the low-RAM mirror for banks 00-3F/80-BF, ROM through the LoROM map, PPU writes ignored. Setup:

- the two planes filled with 0x25 / 0x00;
- `$65-$67` = the layer data (+5, past the header);
- `$1925`, `$1931`, `$1930`, `$192B` from the header;
- `$5B` from the vertical-level table;
- `$1933` = the layer.

Read the result back through the loader's own plane tables ($00BEA8/$00BEAC → per-mode screen tables, with a 3-byte base per screen; screen layout = rows 0-15 at +0x000, rows 16-26 at +0x100). The tiles are exact for every object and tileset by construction: slopes, mud edges and context blends all come out right.

On LM-saved ROMs LM patches the loader and rebuilds the plane pointers at runtime (§9d-3, LM_PARITY "Level entry"), so the static tables are dead. Entering without LM's init puts the screen-0 low plane at $7E0000. Entering through the full chain ($05801E: BG clear + decode + LoadLevel, RTL exit, GameMode >= 0x22 to skip sprite init) and capturing `$6B`/`$6E` per screen with a CPU write hook avoids needing any table knowledge.

### 12c. Global palette exanimation  [CONFIRMED]

The animation NMI tail ($00A418) rewrites **CGRAM colour 0x64** (palette row 6, colour 4) every 4 frames from `MorePalettes` ($00B60C): 8 BGR555 words at byte offset `(frame & 0x1C) >> 1`, a gold-to-white glint cycle (`02DF 035F 27FF 5FFF 73FF 5FFF 27FF 035F`). It applies on top of LM custom palettes too, since the NMI write happens regardless. LM can disable it per level (§12d, `$7FC00A`).

### 12d. LM ExAnimation / AN1-AN2 slots  [INVESTIGATED — NOT the vanilla path]

The bypass AN1 (record w1) and AN2 (w0) slots are the source GFX for LM's rewritten ExAnimation engine, NOT for the vanilla animated-tile system in §12/§12a. Traced from LM's loader:

- The bypass record reader is at $0FF7F0 (`LDA.l <bypassBase>,X`, X = level×0x20). Each slot word is masked with `AND #$0FFF` to a file number, then decompressed through $0FF900.
- $0FF900 resolves file to source exactly as §7d's resolver does (vanilla $00B992/$00B9C4/$00B9F6, ExGFX 80 at $0FF600, ExGFX 100+ per ROM), then JMLs the vanilla decompressor at $00BA47. AN files resolve the same way.
- The AN/extended-animated loader (around $0FF8B8) sets the decompress destination to **$7EAD00** (`LDA #$AD : STA $01 / LDA #$7E : STA $02`), which matches LM's help ("$AD00 = start of the extended animated tile area").
- But the vanilla frame table `AnimatedTileData` ($05B999) tops out at **`$AC20`**. NOTHING in it points at `$AD00`, so the vanilla path never samples the extended area. AN tiles are consumed only by LM's ExAnimation slot engine (§12e/§12f). The OLD "Extend Animated Tile GFX" feature did use `$AD00` through manually edited $05B999 entries, so a ROM that uses it WOULD show $05B999 entries >= `$AD00`.

**The engine.** LM overwrites the vanilla DMA setup at **$00A390** (was `REP #$20 : LDY #$80 : STY $2115`) with **`JSL $138170`** on the hack checked (an expanded bank). That routine performs the animated-tile VRAM DMA itself (it sets DP = `$4300` and writes `$2116`/`$22`/`$420B` from the `$0D7x` parameters) and layers its own slots on top. The vanilla dispatch at $05BB39 is UNTOUCHED.

- **$138170** (NMI DMA) blits the vanilla animated tiles (from the `$0D7x` parameters), then the ExAnimation slots. It reads **8 per-slot DMA parameter records in RAM at `$7FC0C0`, stride 7** (control word at +0, VRAM destination word at +2, 3-byte source pointer at +4). These are already resolved for the current frame; the NMI half only blits.
- The colour-0x64 glint lives here too ($138487: CGRAM 0x64 ← `$00B60C + ((frame&1C)>>1)`, as in §12c), gated by a per-level "disable colour-64 animation" flag at **`$7FC00A`** (bit 7). The ExAnimation frame counter is **`$7FC004` = `$7FC019` >> 3**.
- A per-tick PROCESSOR fills the `$7FC0C0` records. Its init/clear routine zeroes all 8 slots. It reads the slot definitions from ROM and dispatches per slot (§12f "Engine trace").

### 12e. LM ExAnimation slot record  [DECODED via controlled diff]

**The slot format**, pinned by a series of controlled saves. Per-level and global records share ONE format. This supersedes an earlier tentative layout and the "7-byte opaque header" first read for the global list.

| field | meaning |
|---|---|
| record +0 word | low byte = slot-entry count; high byte = alt-ExGFX file index (0-3 → files 60-63 through $03BCC0) |
| record +2 / +4 | AND / OR masks (→ `$7FC0FC`) |
| record +6 | selector word; one trailing byte follows per set bit |
| section | `count` offset words (in slot-number order, relative to the section start, 0 = unused), then the slot blocks |
| slot +0 byte | TYPE: `01-08` = 1-8 8x8s line; `09-0E` = 12/16/20/24/28/32 8x8s line ("20 8x8s" saves as `0E`); `0F` = one 2bpp 8x8 (DMA 0x10 bytes); `10` = 2 stacked; `11` = 4 as 16x16; `12` = 8 as 32x16; `13` = Palette; `18` = Palette Rotate Right. From LM's list order (not saved): `14` +Working, `15` +Working stop, `16` back area, `17` back area stop, `19` rotate right reverse, `1A` rotate left, `1B` rotate left reverse. |
| slot +1 byte | TRIGGER: `00` none, `01` POW, `02` Silver POW, `03` ON/OFF, `04` Have Star, `10+n` Manual n, `20+n` Custom n, `30+n` One-Shot n. `05-0F` are Timer/Yoshi variants by list order (not saved). |
| slot +2 byte | frames − 1 |
| slot +3 word | DEST: a raw VRAM word, passed to VMADD unchanged for every type. LM's dialog numbering: layer 1/2 tile = word/16 (BG12NBA = 0); sprite tiles 400-5FF = `$6000 + (t−400)×10` (OBSEL = 3); layer-3 2bpp tiles 1C00-1DFF = `$4000 + (t−1C00)×8` (BG34NBA = 4). For palette types: low byte = first colour, high byte = colours − 1 (`0385` = 4 colours at 85). **Bit 15 = "use alternate ExGFX file"**: the frame words are then BYTE OFFSETS into that file; otherwise they are bank-$7E RAM addresses. |
| slot +5 .. | frame words: `frames` of them, doubled for a stateful trigger (`01-0F` and Custom `20-2F`; confirmed for POW, Silver POW, Star and Custom; Manual and One-Shot are not doubled). The second half is the triggered animation, and LM zero-fills the unset half. Palette ROTATE types (`18-1B`) store NO frame words; their frames value is the delay. |
| slot placement | with count 6 and offsets `0000`×5 then `000C`, slot 5's block sits at section + 0x0C (verified) |

Examples: an alternate-file slot with destination word `$8A00` and frames `0020/00A0/0140` = (C01/C05/C0A − C00)×20, with $03BCC0 = `00 80 20`, meaning ExGFX60 at $208000. A palette slot: type 13, destination word `0085`, frames = raw SNES colours `7FFF 001F 06AA`. 16 frames give 16 words, and 1 frame gives 1 word.

For RAM sources, the frame source address is **$7D00 + (srcTile − 0x600) × 0x20** (CONFIRMED on 4 values: 0x601 → 7D20, 0x655 → 87A0, 0x6AA → 9240, 0x633 → 8360). Source tile 0x600 is $7E7D00 (the animated-GFX area, §12a), 0x20 bytes per tile at 4bpp.

**The per-level table [CONFIRMED]**: 3 bytes per level (a 24-bit pointer to the level's record), with the sentinel `FF 00 00` = no ExAnimation. It is located per ROM: LM's level-setup reader (`LDA table,X`) signature-scans as `A5 FE F0 ?? 3A 0A 18 65 FE 3A AA BF <base+1>` (subtract 1 from the operand). Observed bases: $109278, $12A312 and $14A4E2. LM relocates a level's record on every save, and the table entry tracks it ($10A92E, then $10AAD3, across saves). The setup reader confirms the record header: +0 = slot count, +2/+4 = AND/OR masks into `$7FC0FC`, +6 = 16-bit selector filling `$7FC070`, and it sets `$7FC000` = the slot array. Clamp record reads to the ROM, because a stray pointer can otherwise run off the end.

**Real hacks have ZERO per-level slots.** They use LM's GLOBAL ExAnimation list, which runs in all levels and is a separate structure (§12f).

### 12f. LM GLOBAL ExAnimation list  [resolved via engine emulation, rendered + animating]

The pointer and outer format come straight from the engine's setup routine:

- **The pointer is baked as two immediates**: `LDA #bankword : STA $01 : STA $C017 : LDA #low16 : STA $00`, so record = `bankword.hi<<16 | low16`. A zero bankword `BEQ`s past it, meaning no global list. Byte-stable anchor: `A9 <bankword> F0 ?? 85 01 8D 17 C0 A9 <low16>`. The engine address is per ROM (observed in banks $10 and $13). Observed records: $10F331 and $12FFCB.
- **The record's outer form**, exactly as the engine consumes it (DP/DBR = $7F, the `$7FCxxx` scratch page), is §12e's record header. The slot section starts at +8 + popcount(+6). On one hack +6 = 0, so the section starts at +8; that is the only reason an earlier "+8 fixed" reading looked right. The section is COUNT 16-bit offsets indexed by global slot number (relative to the section start, `0x0000` = unused), then the packed slot blocks. One hack has 25 slots (count 0x19), 13 of them used.
- A reader should RATS-bound the last block, so it cannot bleed into the next `STAR` block.

**Engine trace:**

- The init/clear routine zeroes the 8 stride-7 slots at `$7FC0C0/C7/CE/D5/DC/E3/EA/F1`, then RTLs. **CORRECTION**: a "dispatch table ~$10F32D" reported earlier was a misread. That region is the record's RATS tag (`STAR` at $10F329, size $00B6+1) followed by the record itself ($10F331).
- A global loop and a per-level loop walk the offset table through the section pointer the setup stashed (`$7FC016` global, `$7FC000` per level). For each used slot they call a per-slot handler with X = the runtime slot number, `[$05]` = the slot data pointer and `($08)` = per-slot state at `$7FC0A0` + slot.
- The per-slot handler reads word 0 of the slot. The LOW byte (the type) goes through a jump table whose entry 0 is RTS (off) and whose entries 1-11 all reach the same code. The real behaviour split is a sub-dispatch on word 0's HIGH byte (the trigger), through 7 sub-handlers that run a frame-timer compare (state `($08)` against the slot's rate byte) and advance the current frame. It then fills the stride-7 record: +0 control from a table (0x20-scaled), +2 the VRAM destination word, +5 the `$7E` source bank.

**Running LM's own engine resolves it.** Two engine routines can be located per ROM by their shared DBR prologue `8B A2 7F DA AB` (PHB / LDX #$7F / PHX / PLB). SETUP is the prologue followed by `A9 FF 8D 19 C0`, and the PROCESSOR is the prologue followed by `A4 14 CC 03 C0`. Seed `$FE` = 1 (non-zero sends setup down the global path; `$FE` = 0 sets the skip-global bit `$7FC00A`.4 and emits nothing) and `$14` = the frame counter. Call setup once, then the processor once per frame, and read the eight stride-7 records at `$7FC0C0`: +0 control (0 = tile not rewritten this frame; otherwise the DMA byte count, so control/0x20 consecutive tiles), +2 VRAM destination word (tile = word/0x10), +4 the 3-byte source.

On real hacks the source is a **ROM GFX address**, advancing per frame (for example $209Exx-$20A4xx), not the $7EAD00 buffer. One hack resolves 52 tile updates over 32 frames, destination tiles {28, 38, B0-F4}, all sourced from ROM. The engine spreads its VRAM writes over frames, so a static snapshot per display phase has to carry each tile's last source forward.

**Alt-ExGFX files 60-63 [CONFIRMED].** The stride-3 table at $03BCC0, indexed by the record's word 0 HIGH byte, is the pointer table for LM's uncompressed ExAnimation source files 60-63 (4 × 24-bit; `FF FF FF` = absent). Vanilla has all `FF`, and LM zeroes it when it installs the ExAnimation code. On one hack $03BCC0 = `E4 9E 20`, so file 60 is at $209EE4 inside a `STAR` block, and its bytes are identical to the hack's `ExGFX60.bin` (0x1000 bytes). Its global record's word 0 = `0x0019`: 25 slots, file index 0 = file 60. That is why the global sources are ROM addresses: they are alt-file DMAs. All 13 used global slots there read alt file 60 (destination bit 15 set; frames = file offsets). Slot 6, for example, is a 4-tile line with offsets 600/680/700/780, and $209EE4 + 600 = $20A4E4 is exactly the source the engine reported for destination tile 038. Alt-file slots and RAM-source slots can coexist in one list. EXANIMATION.md has the full model.

Per-slot periods vary, and some are longer than 8 frames, so an approximation of "8 frames per display phase" puts fast or slow animations slightly off cadence.

### 12g. ExAnimation WRITE side

This section covers what LM's ExAnimation install puts in the ROM. It also collects other write-side findings about how LM saves and installs over a ROM: what it reads, where it looks for it, and what it overwrites.

**Level ExAnimation engine.** LM's engine is a 0xC30-byte block. Two copies, from two different ROMs, differ only by relocation (269 bytes): 12 in-bank 16-bit operands, the 108-word handler table at +B4A, 6 in-block long operands, the per-level table's longs (+DF = table+1, +EA = table), and the global-list immediates (+5B bankword, +65 low16). LM's install footprint is exactly the engine plus these hooks:

- $0583AD → setup;
- $00A390 → the NMI DMA (+RTS);
- the three vanilla `JSL $05BB39` sites, $0095B6, $00A2A6 and $00A5FE → the processor (engine +4B0);
- a helper using MVN, hooked at $00A5E1;
- a helper that clears `$7FC0C0`, hooked at $008A4E;
- $03BCC0-$03BCCF zeroed (the alt-file pointer table, §12f);
- an empty per-level table: 0x600 bytes of `FF 00 00`.

LM also writes metadata bytes at $0FEFDB whose meaning is not known. A slot written by hand runs correctly under LM's engine.

**Overworld ExAnimation (added in LM 2.40).** This is a separate hack, not the level engine. It is a 0xC20-byte blob, a 7-entry record table, and seven per-submap settings bytes. Two installs at different addresses differ in 266 bytes, all relocations: 12 in-bank 16-bit operands, the 108-word handler table at +B3B, 13 long operands (+D6 = table+1, +E1 = table, +4A = settings, ten in-blob), and the global immediates (+57 bankword, +61 low16). The hooks:

- $048086 → setup;
- $0480E0 (OW_Tile_Animation) → tick;
- $00A4E3 → the animated-tile upload;
- each of those as JSL + RTS;
- $048102/$04810D/$04813B changed to use `$14` instead of `$13`;
- $03BCC0-$03BCCF zeroed.

The record index is the SUBMAP NUMBER, with no −1 (EXANIMATION.md §10). The overworld tick spins on hardware that a simple emulator does not model, on LM's own install too.

**Submap GFX lists.** LM's *Overworld ▸ Submap GFX* keeps the seven submap lists in the per-level bypass table (§7d) itself, at entry **0x200 + submap**. Each record is byte for byte a level's (w0 AN2, w2/w3 = FG6/FG5, w4-w7 = FG4-FG1, w8-w11 = SP4-SP1, w12-w15 layer 3), with `0x7F` = skip and **no enable bit**: every submap reads its record once the hack is in. The table is therefore 0x207 records long, 0x40E0 bytes, which is also the one size LM accepts for that standalone block. The hook is $00A140's `STA $20 : SEP #$20` → `JSL $0FFAB0`. OVERWORLD.md §4 has the probe.

**Submap GFX dialog: LM's layout marker and stub.** Two things decide whether LM's Submap GFX dialog uses those records [MEASURED in both directions]:

1. LM's layout marker `4C 4D 03 01` ("LM" 03 01) at $0FF15C. Without it, the dialog shows the vanilla lists and its save does nothing. With it, LM reads the records, writes an edited slot into the table, and, believing the hack is installed, installs none of its own loader: `$0FF7xx-$0FFDxx` and the records come back untouched.
2. The 35-byte stub at $0FFAB0. The dialog takes the record address from the `ADC #imm` at $0FFAB0 +9/+10 and the `LDA #imm` at +18, and from nowhere else.

**Super GFX Bypass dialog: the table address comes from one fixed operand.** LM's *Level ▸ Super GFX Bypass* dialog takes the record table's address from ONE fixed offset: the operand of the `LDA base,X` in its own loader at **$0FF7FF**. It does not scan, so the same fetch idiom anywhere else is ignored. With the layout marker in, LM reads the eleven slots off exactly §7d's words. [MEASURED]

**Separate midway: the tables need their own RATS block.** LM follows the separate-midway routine's table operand and expects a `STAR` tag 8 bytes ahead of the tables, with its own size of 0x800. If that is missing, LM refuses every level save with *"Existing data format or size not recognized! Midway entrance data"*, once per write attempt. With a proper block, LM saves silently and writes the midway screen into vanilla's $05F400. [MEASURED]

**Separate midway: the routine needs its own RATS block too.** LM's *Modify Secondary Entrances* save re-allocates the two secondary-extension tables it finds through the $05DC85/$05DC8A operands, and RELEASES the block they were in, zeroing its tag and data along with anything else in it. It gives no warning; a released block is not an error to LM. LM's own separate-midway routine lives in a 0xD0-byte block of its own (tag, the 0xC4-byte routine, eight `$FF`, then `LM 10 01`) and survives that save, while $05D9E3/$05D979 keep calling it. [MEASURED]

**LM can relocate the four vanilla secondary-entrance tables.** A *Modify Secondary Entrances* save on one ROM copied $05F800/$05FA00/$05FC00/$05FE00 into bank $10 and repointed the four readers ($0DE191, $0DE198, $0DE19F, $05DC81). The same save on an LM hack left them alone, so it is not universal. Afterwards the vanilla addresses hold a stale copy, so follow each reader's operand where the reader exists. [MEASURED]

**Other block-shape results** (LM_PARITY §2 "RATS block shapes"): LM's first overworld save installs its overworld suite and relocates the overworld-ExAnimation settings, while leaving the record table alone. The level-ExAnimation table takes an LM save in place.

**The ExGFX 0x80-0xFF table, and LM's "bypass installed" test.** The ExGFX 80-FF pointer table at $0FF600 is 0x180 bytes, so its last sixteen bytes ($0FF770-$0FF77F) are ids 0xFB-0xFF. LM's `-ImportExGFX` re-initialises the table, zeroing anything else kept in it. LM's own stub at $0EF550, hooked at $05D8E2, stores level+1 into `$FE` early in each level load, which is what the GFX loader reads. **A JSL at $0583B8 is part of LM's "GFX bypass installed" test.** With vanilla bytes there, the same import installed LM's ENTIRE GFX-bypass loader over whatever was in $0FF780-$0FFE93: a 0x6E00 pointers-and-records block, `$0583B8 → JSL $0FF7F0`, and the Direct-Map16 dispatch entries. With a JSL there, to any target, it did not. LM's own layout leaves a gap between its loader group ($0FF780-$0FF884) and its slot tables at $0FF8A0, and LM installs over other ROMs leave that gap alone. An import onto a ROM without LM's palette engine also installs the palette/4bpp bundle (next items). [MEASURED]

**Palette engine.** LM installs its palette engine as one unit [MEASURED]:

- the 176-byte block $0EFC00-$0EFCAF, identical across hacks;
- the 12-byte hook `$0095E9 → JML $0EFC50 : JSR LoadPalette : JML $0EFC80 : NOP NOP` (§7e's detector byte is its first);
- an NMI-enable fix, $0093F7 → JSL to a 13-byte routine in a 0x20 block of its own;
- the fade-in hook `$00A5BF → JSL $0EF570`, a 0x57-byte routine. `$FE` names the level, $0EF583 copies that level's $0EF600 blob into the `$0701` staging, then it does `STZ $FE` and the displaced `JSL $05BE8A`.

The first-load apply, `$05809E → $1FAFF1`, belongs to LM's level engine. Clearing `$FE` there is safe for the GFX loader: no `UploadSpriteGFX` runs after $00A5BF inside a level ($0094D7/$009658/$009840 are title and credits paths), the overworld skips that block on `$0D9B` at $00A5B2, and the next level load re-arms through $0EF550. $0EFC00 itself is LM's 4bpp RAM-expander wrapper (next item).

**The rest of LM's 4bpp mode.** These are the bytes an ExGFX import writes once the palette engine is in place, together with the data those bytes expect [MEASURED]:

- $00A830 and $03DDC9 (the GFX0F expander's and bank 03's sprite-GFX `JSL $00BA28`) go through LM's $0EFC00 wrapper, which decompresses and then folds the 4bpp buffer back to three planes in place. The expanders themselves keep vanilla's bytes.
- The dispatch's `CPY #$08` / `#$1E` become `#$32`, so nothing reaches the filter path (§0), and the filter body is LM's.
- $00B895 decompresses GFX33 straight to $7E7D00 as four planes and jumps to the vanilla tail for GFX32.
- $00A149 is NOPped. In vanilla it decompresses GFX14, which the overworld's bank-04 tile reader uses, so the loader has to leave the AN2 file in $7EAD00 instead.

Data:

- GFX1E carries plane 3 = `p0|p1|p2` on every tile.
- GFX08 carries it on the 24 tiles LM's own conversion chooses: 0x37-3B, 0x47-4B, 0x56-5B, 0x60, 0x6E-70, 0x7A-7B and 0x7E-7F. One file cannot suit both tilesets, and this is LM's compromise; some hacks redraw the file instead.
- GFX33 is four planes, with plane 3 zero.

GFX32 and GFX33 share the one bank byte at $00B890. LM keeps both at $088000 with its own compressor, which fits the 4bpp GFX33 in 0x1C68 bytes, and LM reads both through the operands. Mode 7's GFX27 stays 3bpp on every ROM, LM's included. The depth of GFX33 can be read off the $00B894 operand (`$7D00` = four planes).

**Acts-like core.** *Editors ▸ 16x16 Tile Map Editor ▸ F9* writes LM's 96-byte acts-like core over $06F5E4-$06F643 [MEASURED]. It contains:

- the wrapper that $04DCFA calls;
- the `LM 10 01` marker at $06F5FC;
- the `TYA : JML $00F545` tail at $06F602;
- the overworld bail at $06F608;
- the acts-like lookup at $06F617.

The core is identical across every LM ROM checked, apart from the table bank at $06F626 (normally the bank of $118000). Anything else in that span is overwritten. On LM's own ROMs the four vanilla `JSL $00F545` sites go to per-site trampolines (next items), but LM leaves a foreign hook at those sites alone, as it does at $0583B8. A foreign hook that relied on code in $06F5E4-$06F643 then meets LM's `STA $65 : LDY #$0000 : RTL` and the level renderer gets a clobbered stream pointer. $06F800-$06F9FF is `FF` in every LM ROM measured. On a save, LM also points $04DCFA at `JSL $06F5E4`, and $058A65/$058B45/$058C33/$058D2A at `JSL $06F540`, four more render paths through the ladder. LM 3.40's Map16 save also populates ladder ranges 1-2 with its per-tileset pages and leaves range 0 at "no defs", and it frees a foreign extended-definition block, marker or no marker (LM_PARITY §2, Map16 F9).

**ExGFX 0x100+ table: one fixed operand.** LM takes the ExGFX 0x100+ pointer table's address from the 24-bit operand of a `LDA table,X` at the FIXED offset **$0FF873** (the instruction is at $0FF872), the same arrangement as the bypass records at $0FF7FF. If those bytes are not a table address, `-ImportExGFX` writes the inserted file's pointer wherever they happen to point. A copy of the address at $0FF937 is not what LM reads: planting a value there alone changes nothing. The block shape does not matter; on an LM hack the import writes straight to the address at $0FF873 without validating the block. LM ROMs that lack the feature have `FF` there. [MEASURED]

**Acts-like chains.** An entry of 0x200 or more in the acts-like table at $118000 is not a behaviour but another TILE, whose entry is read in turn. LM's lookup at $06F617 branches back to its own `TAY` on `CMP #$0200 : BCS`. A cycle hangs the game. The table's defaults (identity below 0x200, `0x130` above) resolve on the first read. LM's `-ExportAllMap16` / `-ImportAllMap16` round-trip a chain (for example `310 → 2A5 → 1C0`) byte for byte and store it without complaint. [MEASURED]

**Submap layer-3 tilemap.** LM's *Overworld ▸ Submap Layer 3 GFX/Tilemap Bypass* dialog reads and writes the submap records: the GFX half through w0 bit 14 and words 15-12, and the tilemap through w0 bit 13 and w1 (file in bits 0-11, size index in bits 12-13, destination index in bits 14-15, the same encoding as a level's). One save wrote `w0 = 0x2014` and `w1 = 0x6028`. The overworld's own layer-3 upload is a bank-04 routine that sets VRAM word `$3000` and DMAs 0x2000 bytes there from $7F4000 (or $7F6000 for a submap, per `$1F11`). Its tail is `LDA #$02 : STA $420B : RTL` at $04D76A. That was found in the disassembly and confirmed by mutating the DMA's source byte, which moved VRAM `$6000-$7FFF` on the map. So the destinations rebase from a level's `$5000` window to the overworld's `$3000`, and the submap number comes from `$0DD6`/`$1F11`. LM's own equivalent lives inside its overworld suite and leaves $04D730-$04D7A0 vanilla. OVERWORLD.md §4. [MEASURED]

**Custom-block dispatch (what GPS's blocks run from).** On an LM ROM, the four `JSL $00F545` sites go to per-site trampolines at $06F660/$06F700/$06F760/$06F7A0, behind an `LM 11 01` marker at $06F65C. Each one:

1. does `JSR $F608` into LM's lookup (the acts-like core, so the table is the one $06F624 names);
2. reads the caller's return-address low byte, which the lookup leaves in A;
3. `BEQ`s to a 16-byte slot in $06F690-$06F7EF.

Each slot is `JMP $F602 : NOP` ×4 by default, and holds GPS's stubs once blocks are inserted. The fall-throughs at $06F67B/$06F717, which GPS overwrites, are INFERRED as `JMP $F602`. The pages-40+ operand is at $06F63B. On FastROM hacks the bank is `$86`. Without this dispatch, GPS's blocks insert and never run. LM's lookup does not keep the caller's B (§9d). Every LM ROM runs it that way, and sprite interaction through $019533/$02A6EB is unaffected. Tool page: GPS. [MEASURED in Mesen: a block fires in level $105 with the dispatch and not without it]

LM 3.40 behaviour on this dispatch (the exe's version resource says 3.40; its readme says 3.33) [MEASURED]:

- A level save, Map16 F9, `-ImportLevel` and `-ImportAllMap16` all leave GPS's stubs, hijacks and tables and the four sites alone, and the block still fires after each.
- The two Map16 routes upgrade the dispatch in place. The marker goes `LM 11 01` → `LM 12 01`, and the fourth trampoline at $06F7A0 is rewritten to 3.40's 20-byte form: `JSR $F608 : LDA $0F : BEQ +4 : LDA $0A,s : BRA +2 : LDA $06,s : CMP #$DA : BEQ $06F7C0 : JMP $F602`. Older LMs write a shorter form.
- With marker byte $06F65E already `12` and the 20-byte trampoline in place, 3.40's Map16 save (F9 or `-ImportAllMap16`) changes nothing in $06F650-$06F7FF, a second F9 writes nothing, and the ROM boots. GPS reads neither of those bytes.
- Regardless of the marker, the Map16 save still frees a foreign extended-definition block and installs LM's own ladder ranges.

**Overworld palettes.** LM's Overworld Palette Editor works through a hook at $00AD32 (`JSL <hook> : RTS`). The hook sits in a 0x30-byte RATS block, and its table in a 0x1C00-byte RATS block in a single bank, because the hook copies it with one `MVN` that cannot cross a bank. The table holds submaps 0-6, then 0-6 again with the special world passed, 0x200 bytes each. LM's `-TransferOverworld` keeps the hook in place but rewrites its operands, frees the existing table and allocates its own, so the table's address is whatever the hook says, never a constant. LM's own conversion fills the table like this: the colours the overworld itself loads keep their words, the leftovers are `0000`, and `0x86`-`0x8F` hold Mario's palette from $00B2C8, which the game re-uploads every frame. Colour `0x86` is Mario's first colour in every LM table measured. OVERWORLD.md §4. [MEASURED in Mesen: a one-colour change to the table reaches CGRAM]

## 14. Sprite graphics via OAM capture  [CONFIRMED by emulation]

There is no unified sprite → tile table. Each sprite's look comes from its own graphics routine. The reliable way to get it is to emulate the ROM's own load flow per sprite. Seed slot 0: `$9E` number, `$E4/$14E0` + `$D8/$14D4` position, `$15EA = $30` OAM index, `$64` priority, `$187B` extra bits, and the screen boundary `$1A/$1C` near the sprite. Then:

1. `InitSpriteTables` ($07F7D2, RTL) loads the tweaker and palette RAM (`$1656-$1686`, `$15F6`) from ROM. Without it every sprite draws with palette 0.
2. Seed status `$14C8` = **1** (init), or **9** (stationary) for shells, see below.
3. Run up to 16 frames of `HandleSprite` ($018127), the per-slot STATUS dispatcher: 0 → erase, 1 → CallSpriteInit $018172, 8 → CallSpriteMain $0185C3, 9/A/B → stunned/kicked/carried at $01953C/$019913/$019F71. Calling CallSpriteMain directly misses every carryable sprite. The POW's number-dispatched main ($01E75B) only handles the message-box timer; the visible POW draws from the status-9 handler. Each frame: fill OAM Y with `$F0`, increment `$13/$14`, and re-pin the position. The first frame that yields OAM tiles wins. A frame that overruns its instruction budget (wait loops, such as the castle fireball's init) is skipped, not fatal.

**DBR**: the sprite engine runs with **data bank = 1** in game (PHK/PLB in the bank-1 sprite loop). Absolute table reads (`SprTilemap` $019B83, `SprTilemapOffset` $019C7F, every bank-1 tile and animation table) silently read bank-0 garbage with DBR = 0. That produces "close but wrong" tiles: koopas drawn with one tile, and shells drawing GFX00's P-switch. Set DBR = 1 before the HandleSprite frames.

**Ground seeding**: the sprite block probe ($019441) treats any position whose screen number is >= **`$5D` (screens in level)** as "no blocks". Left unseeded, nothing is ever solid, so walkers run their in-air path forever: a 2 px/frame gravity sag, the stay-on-ledge direction flip ($018B98), and a walk animation frozen on the standing pose. Seed `$5D` and write solid tiles (Map16 $130: $7EC800 = `$30`, $7FC800 = `$01`) a few rows below the sprite. The `$C800` layout matches the probe's ROM pointer tables `DATA_00BA60/BA9C` (horizontal: screen×`$1B0`, rows 16-26 at +`$100`) and `DATA_00BA80/BABC` (vertical: band×`$200`, right 16 columns at +`$100`). The horizontal bottom bound is a hard-coded `$01B0` ($0194D6), not `$13D7`.

**Mario seeding**: `SubHorizPos`/`SubVertPos` ($01AD30/$01AD42) read Mario from the **`$D1-$D4` mirrors**, not `$94-$97`, so seed both. Park Mario at sprite X **−0x140**. That is truly LEFT of the sprite (Banzai Bill's init erases itself when Mario is to its right, $01838B; this also matches LM's face-left convention), yet it aliases to −0x40 in the LOW byte, which matters because proximity gates such as Monty Mole's ($01E2E3) compare only the low byte of the 16-bit distance.

**Sprite-list number classes** ($02A866-$02A8D8):

- 00-C8: normal sprites.
- C9-CA: shooters (the `$1783` system).
- CB-D9: generators (`$18B9`).
- **DA-DD and DF: koopa shells**, loaded as sprite (num−$DA)+4 with initial status 9 ($02A97E; `$1EEB` can colour-swap 04↔07 and 05↔06).
- DE: 5 Eeries. E0: 3 chain platforms. E1-E6: cluster specials.
- E7 and up: scroll commands.

Tiles resolve through SP1-4 (`SPRITEGFXLIST` $00A8C3, or bypass words 11-8). Palettes are CGRAM rows 8-F. A 16x16 is assembled from T/T+1/T+16/T+17 with the flip swapping quadrants. Entries draw in reverse OAM order. Some sprites are genuinely invisible in game at rest: the invisible mushroom C7, warp blocks 8E and the static net door 54. Hidden Monty Moles draw their in-ground dirt pose.

### 14a. Sprite OAM specifics  [verified against bank_01]

- Sprite GFX routines write tiles to the **`$0300` half** of the `$0200-$03FF` OAM buffer (each 4-byte entry is X, Y, tile, `YXPPCCCT` props). The size table **`$0420-$049F` holds ONE byte per OAM entry**. `FinishOAMWriteRt` ($01B7BB) shifts the `$0300`-relative byte offset right twice and indexes `$0460` = `$0420` + entry index (consecutive per-tile stores at $01BC08 confirm it). Bit 1 = 16x16. **Bit 0 = the 9th X bit, meaning the tile hangs off the LEFT edge**: subtract 0x100, don't add it (it is set by the DEX/offscreen check at $01B7F5-$01B811). Unwritten entries must default to 0 (8x8), or garbage neighbour tiles appear.
- **Priority**: earlier-drawn OAM tiles sit in FRONT of later ones regardless of the PP priority bits (PP only orders sprites against BG layers). Drawing a captured list in reverse makes slot order win, which matches the hardware.
- **Palette**: OAM CCC addresses only the SECOND half of CGRAM, so sprite palettes are rows 8-F (colour base 0x80 + CCC×16). The CCC value itself comes from `$15F6,x`, which `InitSpriteTables` loads. That is why step 1 above is needed.
