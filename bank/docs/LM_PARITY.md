# What Lunar Magic writes into a ROM

An inventory of what Lunar Magic (LM) writes into a Super Mario World ROM: which code and tables a plain save installs, which ones install on demand, where they sit, what they are for, and how LM reacts to the structures it finds already there. Anyone writing a tool that has to coexist with LM-edited ROMs needs this list, because a ROM that has been through LM can end up with two mechanisms for one job, or with a table LM has silently moved.

## How this was produced

The baseline is a controlled before/after save in LM: a clean ROM, one level saved once in LM, and nothing else. The diff against the clean ROM is LM's minimum footprint, the set of things it installs just by saving a level. It is not one hack's ambitions. That diff is 60 changed runs. Further rows come from driving individual LM dialogs and command-line routes over known ROMs and diffing again, and from comparing the same structures across several LM-edited ROMs.

**Confidence is marked per row.** CONFIRMED means the disassembly, an emulator run or several LM ROMs agree. MEASURED means a controlled before/after save in LM. INFERRED means the address and shape say so but nothing has been run against it. LM-DOC means LM's own help says so, restated here.

## 1. Fixed-address code a plain save writes

These sites are written by every plain LM save, at the same address and with the same bytes on every LM ROM. Another tool that implements the same feature should write exactly these bytes, because LM will overwrite anything else here.

| site | what LM writes | notes |
|---|---|---|
| $05D7CE → $05DC50 | exit destination bit 8 | a hijack plus a flag layout for the 9th bit of an exit's destination level [CONFIRMED, emulated over every flag combination] |
| $00AACD | 4bpp upload | a 32-byte loop; part of LM's 4bpp graphics rework, see §2 "4bpp graphics" |
| $0DF08A, $0DFF50, $0D*FD | Direct Map16 object handlers | fixed bytes [CONFIRMED] |
| $0DA4B8 | Direct Map16 hijack | fixed table entries [CONFIRMED] |
| $0EF100 | per-level sprite bank table | with the 12-byte stub at $0EF300 and the level-word routine at $0EF550, see §2 "Sprite bank relocation" [CONFIRMED] |
| $00F478 | 43 bytes rewritten | one half reads the level height `$13D7`; the other half is LM's acts-like call path, see §2 "Block behaviour" |
| $0DE190-$0DE1FF | extended-object handlers | ext 01 and ext 03 carry the 32-row band, see §2 "How a tall level places" [CONFIRMED] |

## 2. What LM writes — the inventory

### Block behaviour ("acts like")

The vanilla game reaches the acts-like lookup through four `JSL $00F545` sites. LM reaches its own lookup through four per-site trampolines ($06F660, $06F700, $06F760, $06F7A0). The trampolines carry per-site stack reads for LM's custom-block cases and jump to a block engine in banks $95/$96 that LM installs with custom blocks. The lookup core itself sits at $06F5E4 (96 bytes) and reads the acts-like table through the 24-bit operand at $06F624. The table is 0x8000 bytes, two bytes per tile, tile-numbered. A ROM that has no table gets a fresh one from LM's Map16 save (observed at $1A8000); a ROM that already names one keeps it. See "Map16 F9" below.

**`LDA $00BA70,X → LDA $000CC6,X` is a different feature.** The seven sites ($00F50D, $019509, $029301, $0295F4, $02A6C2, $02BA79, $02D194, each also getting `$0CB6`/`$0CD6`/`$0CE6` for its three sibling tables) are vanilla's per-screen **Map16 plane-pointer** low/high byte tables. LM rebuilds them in RAM per level because the column stride is no longer a constant. They belong to the height engine (§2 "Level entry") [CONFIRMED]. Earlier readings tangled the two features together.

**The round trip through LM's command line** [MEASURED]. `-ExportAllMap16` and `-ImportAllMap16` use the `.map16` format, which carries "Act As" data as its own indexed section, two bytes per tile, tile-numbered.

- **Table → LM: exact.** Entries written for tiles `030`, `105` and `2A5` into the table, then exported: LM's Act As section holds `0E0`, `02F`, `1C0` at those tiles. The defaults are identity below 0x200 and `130` above.
- **LM → table: exact.** Editing the file's Act As bytes and importing writes them straight into the table the lookup's operand names (the diff lands on $118060, $118140, $11820A, $11854A, $118620 for tiles `030`, `0A0`, `105`, `2A5`, `310` on a ROM whose table is at $118000), and the ROM still boots and builds a level. So the address, the layout, the two-byte order and the defaults are all as described.
- **Entries chain.** LM's lookup treats an entry of 0x200 or more not as a behaviour but as another TILE, and reads ITS entry (`BCS` back to its own `TAY`). LM's import stores such an entry without complaint; tile `310` → `2A5` → `1C0` survived a full round trip. A tool that predicts block behaviour must follow the chain. A cycle hangs the game.

### Sprite stream

$02A67A, $02A826 (→ `JML $1090A3` / `$109198` / `$10917B` / `$108F2D`), $02A95B (→ `JML $108F70`) and the rest of the bank-02 hooks are LM's sprite-list loader: the per-screen index cache, the spawn-range window, the extended list (`FF nn` bands, CONTRACT §11) and per-sprite extra bytes. The targets are per-ROM (the addresses above are observed). LM registers the sprite size table at $0EF30C, with `0x42` at $0EF30F (CONTRACT §11).

### Sprite bank relocation

`$05D8E2 → JSL $0EF550` (level word → `$010B`, Y = level×2) and `$05D8F5 → JSL $0EF300` (bank from $0EF100) are LM's two routines. The stub at $0EF300 is exactly 12 bytes; LM's pointer at $0EF30C and table at $0EF310 sit right behind it, so a longer private stub at this address overruns them. $0EF550 also stores level+1 into `$FE`, early in the load, where LM's GFX loader reads it [CONFIRMED].

### Map16 machinery

$06F540 (260 B), $06F65C, $06F690 (218 B), $06F780 (80 B), $06FA00 (1536 B, `$20` fill). [INFERRED] These cover all eight ladder ranges plus per-tileset page tables, for extended Map16 pages beyond `$3FFF`. The ladder slots are at $06F553 (CONTRACT §7a-rev).

All eight ladder slots are decoded [CONFIRMED, against an LM ROM using ranges 4 and 5]. Ranges 4-7 are LM's FG tiles 0x4000-0x7FFF. LM's own Direct Map16 objects cannot address those high FG tiles.

### Level load

$0580C0/C4/C8 (level-mode tables in LM's bank-$1F block), $058DA4 (→ `JSL $0EFD00`), $0586A1, $00A6B8/$00A6CC (→ $0EF560, $05DD00), $05DCB0, $05DD30, $0EFD00. All part of the level engine (sections below). This is not a GFX loader; LM's GFX loader is separate (§2 "4bpp graphics", CONTRACT §7).

### Entrance positions — "method 2" is installed by every save  [CONFIRMED, plain save and several LM-edited ROMs]

The limits on where an entrance can put Mario are **vanilla's**. LM's help calls the bank-05 tables "method 1" and describes method 2 as an enhancement LM inserts [LM-DOC]. What the help does not say is that method 2 is not a rival table. It **reinterprets the record's own two index nibbles as 16px steps** and adds a flags byte and a Y-high byte per level. A PLAIN save installs it, for main and secondary entrances alike:

| site | vanilla | after any LM save |
|---|---|---|
| $05D97D | `LSR : STA $192A` | `JSL $05DD30` — main entrance, method 2 |
| $05D833 | `LDA $FE00,Y : AND #$07 : STA $192A` | `LDA $FE00,Y : TYX : JSL $03BCE0` — secondary, method 2 + 9-bit destination |
| $05DC80/85/8A | `$FF` | `LDA $05FE00,X : RTL`, then two `LDA long,X : RTL` whose operands are per-ROM tables |
| $05D9C3 | `STA $13CD` | `LDA $13CD` (see below) |
| $05D9E7 | `STA $95 : JMP $05DA17` | `STA $01 : NOP NOP NOP` — midway screen through the shared tail |
| $05DE00, $06FC00 | `$FF` | zeroed (bit 5 of `$FF` would switch method 2 on everywhere) |
| $06FE00 | `$FF` | `$1A` per level |

Both routines are **byte-identical** across every LM ROM examined ($05DD30, 0x46 bytes; $03BCE0, 0xB6 bytes) and sit at fixed addresses in vanilla free space. Running them in an emulator over known records puts Mario where LM's editor says.

**Main entrance** ($05DD30): `$05DE00+lvl` bit 5 = method 2, bit 3 = X bit 7, bit 4 = X bit 8 (vertical levels), bits 6-7 → `$192A`; `$06FC00+lvl` bits 0-5 = Y high; then `$94 = F200 bits 0-2 << 4 | bit3 << 7`, `$96 = F000 bits 0-3 << 4`, `$97 = Y high`. The screen still arrives through the vanilla tail (`$05D9EC: LDA $01 : AND #$1F : STA $95`), so Mario's X is `screen << 8 | xHigh << 7 | xIndex << 4`. `$06FE00+lvl` goes to `$13CD`, LM's FG/BG-relative setting, consumed by its per-ROM tail hook at $05DA17. Vanilla put the midway screen in `$13CD`, and its only reader ($00F2D8, the midway tape) tests it for zero. That is what LM's `$1A` default and the `STA`→`LDA` at $05D9C3 are for.

**Secondary entrance** ($03BCE0): `$05FE00` bit 3 → `$0F` = destination bit 8 (LM's save sets it on every record `$100-$1FF`), bits 4-5 = X bits 7-8, bit 6 = method 2, bit 7 → `$192A`; the fifth table (reader at $05DC85) bits 0-5 = Y high; `$94 = FC00 bits 5-7 << 4 | bit4 << 7`, `$96 = FA00 bits 0-3 << 4`. The sixth table (reader at $05DC8A) carries FG/BG bits and an "exit to overworld" flag. LM allocates the two tables per ROM, each its own 0x1FE-byte block (observed at $1086C9/$1088CF and $10F0C5/$10F1CB). The last two records read into the next RATS tag. Read them through the reader operands, never at a fixed address.

### Separate midway settings — installed on demand

A plain save does not carry it. ROMs that use the feature carry one 0xC4-byte routine that is byte-identical across them apart from four table operands and its own address (observed at $11FA63, $10FDDF, $12EF20):

| site | vanilla | with the feature |
|---|---|---|
| $05D9E3 | `LSR x4` | `JSL routine` — A = `$F400` byte in, screen out |
| $05D979 | `AND #$38 : LSR : LSR` | `JSL routine+$A0` — an exit flagged for the midway (`$192A` bit 6, `$141A != 0`) arrives at it |
| tables | — | one RATS block of 4 × 0x200: flags, position, FG/BG, Y high (observed at $138008, $128008) |

Flags: bit 5 = separate settings on, bit 4 = midway screen bit 4, bit 3 → `$95` = X bit 8 (vertical levels), bits 0-2/6-7 → `$192A`. Position: low nibble = X bits 4-7 (the WHOLE nibble, unlike method 2's 3+1 split), high nibble = Y bits 4-7. FG/BG: $05F400's layout in bits 0-3, bits 6-7 → `$13CD`, bit 5 = "redirect midway to another level" (position byte = that level, FG/BG bit 0 its high bit; the routine restarts the load at $05D8B7). Y high: bits 0-5; LM sets bit 6 on every record it writes. With bit 5 clear the routine hands the screen back and touches nothing, so a level without the setting plays as vanilla with a fifth screen bit. Running the routine in an emulator places Mario from its own record [CONFIRMED].

LM's own copy of the routine sits in a 0xD0-byte RATS block of its own: tag, the 0xC4-byte routine, eight `$FF`, `LM 10 01` (observed at $10FDD7). See "RATS block shapes" for why that matters.

### The tables need a RATS block of their OWN  [MEASURED]

LM follows the routine's own operand to the four midway tables and expects a RATS tag 8 bytes ahead of them with the size it uses itself (`STAR`, 0x800, data at tag + 8; observed at $128000/$128008). Anything else is refused: **every LM level save reports "Existing data format or size not recognized! Midway entrance data"**, once per write attempt, so the box returns as fast as it is dismissed. With the tables in a block of exactly that shape the save goes through silently. With "separate settings" off, LM writes the midway screen into vanilla's own $05F400 table.

### LM can RELOCATE the four vanilla secondary tables  [MEASURED]

*Modify Secondary Entrances* + save can copy $05F800/$05FA00/$05FC00/$05FE00 into bank $10, 0xCC5 apart, and repoint the four readers ($0DE191/$0DE198/$0DE19F in LM's reader block, $05DC81 in its secondary readers). It copies the contents across and raises no warning. The same save on a different LM ROM left the vanilla four alone and only re-allocated the two extension tables 2 bytes lower, so not every save does it; what triggers it is unprobed. Once it has happened, the vanilla address holds a stale copy and writing there goes where the game no longer looks. Read the tables through the reader's operand when the reader is present, and at the vanilla address when it is not.

On some LM-edited ROMs the midway branch also goes through a bank-$14 block (`$05D9DA JML $14EE49`, keyed on RAM `$7FB426` that a larger `$7FB4xx` engine fills). Other ROMs lack it and their midway works, so it is a different feature, not decoded here. LM's per-ROM hooks at $05D9A1 (vertical check) and $05DA17 (FG/BG init) are part of the level-entry engine below.

LM does not preserve code it does not recognise at these sites. Private stubs on the two `JMP $05DA17` sites were wiped by an LM save, which left $05D9FE jumping into cleared space.

### Level entry — height, FG/BG initial position, "relative to player"  [CONFIRMED, plain save and several LM-edited ROMs]

Method 2 puts Mario anywhere, but the camera's first frame would still be one of vanilla's four fixed offsets ($05F400 bits 0-3 → `$1C`/`$20`). LM's answer is its **level-entry engine**: two code blocks a plain save installs, fed by fourteen hooks.

- **Block A** (observed at $108141, 0x510) is the $05DA17 tail: the layer-2 scroll setting, `$1443-$1452`, then the FG/BG initial position, from vanilla's table or **relative to Mario's Y** when `$13CD` bit 7 is set. It also holds the $009708 level start (width from the header, `$142A`/`$F9`), the layer-2 scroll bounds ($00F871/$00F77B/$00F79D) and two bounds checks ($05BCA5, $00E966).
- **Block B** (observed at $108AD5, 0x3C0) holds a per-level height byte, a height LUT (index 0 = `$1B0`), and the code that gives the level a height in RAM: `$13D7`, `$1936`, and the per-screen tilemap pointer tables `$0BF6`/`$0C56` ($05DA8A/$05DB5F, $0C9436, $02950B/$0295BE, $00F70D, and the $05D9A1 vertical check).

LM relocates the blocks per ROM, and the ONLY bytes that change are 16-bit in-bank operands (two jump tables, `JSR`/`JMP`) and the bank byte of four long operands. Two LM ROMs with the blocks at different addresses ($108141 vs $139F01, $108AD5 vs $10F4D1) differ nowhere else. So the blocks can be moved to another bank by patching those four bank bytes and the fourteen hooks' bank bytes. $06FA00 is LM's extended layer-2 scroll byte, initially `$20`.

**The relative camera, decoded** (block A +0x8D onward): with `$13CD` bit 7 set, `$1C` (FG Y) = Mario's `$96` + the entrance's $05F400 low nibble ×16, negative when `$06FC00` bit 6 is set (`ORA #$FF00`), clamped to the level height less a screen. `$20` (BG Y) then comes from the layer-2 scroll rate handler (`JSR ($8334,X)`, indexed by `$1414`) and the BG height in `$13CD` bits 0-5; `$13CD` bit 6 = "BG relative to FG only". The main entrance's byte is $06FE00 (LM default `$1A` = 26 BG tiles), the midway's is its FG/BG table byte, and a secondary entrance's is the sixth table. Running the tail hook in an emulator sets the camera relative to Mario when asked [CONFIRMED].

**The height half.** Block C (observed at $108EED) is LM's sprite-stream loader with its per-screen cache and spawn-range tables. Three small blocks (observed at $108E9D, $108EC5, $1092AD) and twenty-one hooks go with it, plus every in-place edit that reads the height from RAM:

- the object engine's column stride (`ADC/SBC #$B0` → `$13D7` at $0DA963/96B/9D6/9F7/9F9, $0DBB16);
- the loader's plane-pointer maps ($00BDA8 onward → `$0BF6`/`$0C26`/`$0C56`/`$0C86`), with vanilla's ROM-to-RAM copy skipped at $00A873;
- the block-probe tables (`$BA60`… → `$0CB6`…) in banks 00/01/02;
- the sprite Y compares and the layer-scroll bounds ($00F478 onward);
- LM's $05DD00/$0EF560 level-init routines;
- LM's extended-object handlers ($0DA112, $0DE1AC).

Block C differs between two LM ROMs in eight in-bank operands and five bank bytes; the rest is identical. Run at LUT index 0x17, the chain leaves `$13D7 = $950`, the pointer tables at that stride, and the block-probe copies in RAM [CONFIRMED].

**How a tall level places past row 31** [CONFIRMED, decoded by running tall LM levels through the loader with attribution]. Standard-object Y stays 5 bits. LM's ext 01 handler ($0DE1D0) sets `$8B` = X-nibble × 2 besides the screen, and its ext 03 ($0DE1E0) sets `$8B` = Y × 2 and the screen from X. The object loader adds `$8A` (16-bit: band × 0x200 bytes = 32 rows) to every object's plane pointer ($0586A1) and zeroes it at layer start ($0583C7 → $0DE1F0). So the stream carries a **32-row band**: `row = band × 32 + Y`, set by a jump before the objects that use it. A one-column level 896 rows tall reads `ext03 y=17 … objects … ext03 y=18 …`. Ext 01 carries the band in X below 16; ext 03 is needed above that, which only happens in one-column levels, where ext 03's 4-bit screen is enough.

**The height LUT is the width×height trade.** Block B's 32 heights are exactly those with `columns × height ≤ 0x3800` (the tilemap RAM): `1B0` (32 columns) … `950` (6) … `3800` (1). Width is the header's screen count, so a width/height pair that does not fit has no entry. Height byte bits: 0-4 LUT index, 5 extended sprite stream, 7 "vertical positioning" (LM sets it on every level).

**The render half.** Drawing a tall level to VRAM past row 27 is LM's redraw engine in its bank-$1F block (observed at $1F8008-$1FB397, 13 KB):

- $0586F7 → $1FB00F tracks layer positions in `$7F830B`… and redraws columns via $1FA70E/$1FA777;
- the level-mode tables at $1FA41C/$1FA626/$1FA69A (read from $0580C0/C4/C8), $0580A9 → $1FAFF1, $008751 → $1FA2D2, $00A5A2 → $1FA28D;
- the layer-2 scroll code at $1FAFA0/$1FAFC4 (from $00F6E4/$00F7E8);
- LM's VRAM patch ($0081E2 → $1F8008), which is what makes the BG2/BG3 GFX bypass upload in game.

Scanned for cross-bank operands, the block references only itself and fixed bank-0E/05 addresses, so it can be copied verbatim as one RATS block. It calls these fixed pieces:

- $0EFD00/$0EFD50: VRAM column stride `$1B0`/`$200` by the layer-3 flag LM keeps in `$7FC00B`;
- $0EF510: the $05803B hook that sets that flag from a per-level byte at $0EF310;
- the 12-byte sprite-bank stub at $0EF300 with its $05D8E2 → $0EF550 level-word mirror (§2 "Sprite bank relocation");
- the Direct Map16 handlers ($0DF08A onward, $0DFEA0 onward, whole regions);
- the exit/secondary plumbing: readers at $05D7E2/$05D7EA/$05D81C, $05DBC2 → $03BB00, $01E762 → $03BCA0 (overworld exit), $04E5F1 → $05DCB0, $0DA536;
- extra FG/BG init entries ($05D718/$05D728);
- small bank-00/01/05 tweaks alongside: $00BF3C onward, $00AF4C onward, $00C07D onward + $00C25C through the ladder entry, $05BAAA onward.

**The rest of a plain save's footprint here:** the Map16 ladder body ($06F540 onward), the per-site acts-like pointers ($019534, $02961B, $02A6EC, $00F4DE, with the $00F4A0/$00F4EB fallback tied to it), the loader-side ladder calls ($058A65 onward, with their `$3F` masks), the overworld helper at $04DCFA, LM's metadata ($0FEFCD, $0FFFE6 onward), and the re-saved level itself. LM's extended sprite LIST (header bit 5, `FF nn` bands) is CONTRACT §11.

**A gotcha when copying LM code.** Copying LM code by vanilla-vs-LM diff RUNS is unsafe wherever another patch already sits: a byte that happens to equal vanilla's (`$FF` in `JSR $FF10`) splits the run and leaves the other patch's byte behind. Copy whole regions instead.

Two RAM effects worth knowing: block A sets bit 15 of `$5A` as its marker, and `$13CD` stops being "midway screen" (vanilla) and becomes the FG/BG byte. That is why every LM save also turns $05D9C3's `STA $13CD` into a load (§2 "Entrance positions").

### Object handlers with $13D7

$0DA963, $0DA9D6: vanilla's `ADC #$B0 / ADC #$01` screen stride becomes a 16-bit `ADC $13D7`, the level height the entry engine keeps in RAM. Part of the height half (above).

### Bank 03 — new code in vanilla free space

$03BB00, $03BCA0, $03BCDC (196 B of new code, `JML $1092AD`, `JSL $05DC80`), $03FDFF (513 B). [INFERRED] Overworld and level-entry support; $03BB00, $03BCA0 and $03BCE0 are the exit and secondary-entrance pieces above. The rest is unmapped.

### Tables LM initialises

$05D718 (20 B), $05FACE / $05FCCE / $05FECE (inside the secondary entrance tables; data), $0EFD50, $0FEFCD (371 B), $0FFFE6, $05DE00, $03FDFF. Mixed data and unknown; the entrance ones are explained above, the rest are not.

### Not in a plain save, but LM installs on demand

From LM's help [LM-DOC], these install when their dialog is merely OPENED, so any LM user will add them: Super GFX Bypass, Layer 3 GFX bypass and ExAnimation. The VRAM patch and FastROM go in on the next level save. Until the VRAM patch is in, BG2/BG3 bypass slots have no effect in game.

### 4bpp graphics  [CONFIRMED, several LM-edited ROMs vs a clean ROM and a plain LM save]

LM's 4bpp mode reworks how the game decompresses and uploads graphics. Part of it is visible on the overworld first.

- **The overworld reads the decompression buffer.** The OW copies eleven tiles (three water, then cloud frames) out of the **GFX decompression buffer** into `$0AF6`, on load and then every frame, frame-indexed, with its own reader: an offset table at $048000 (67 words, `$AD00 + tile*24`), bank hard-coded `$7E` ($048095, $04814F), and a 3bpp expander at $0480B9. The file it reads is whatever was decompressed last (GFX14 on Yoshi's Island). So the buffer must stay at `$7EAD00`, and the reader must agree with the buffer's bit depth. Moving the buffer, or putting 4bpp data behind the 3bpp reader, garbles the OW's animated tiles. Tracing this in an emulator: bank-04 code writes RAM through `$04:xxxx`, which a breakpoint on `$00:`/`$7E:` addresses never sees.
- **LM's overworld 4bpp changes** (identical across LM-edited ROMs, absent from a plain save): the buffer stays at `$7EAD00`; the table is rescaled to `tile*32`; the expander copies 16 word rows ($0480BD: `08→10`) and drops its plane-2 loop ($0480D0: → `RTS`); and because a 4bpp file now runs to `$7EBCFF`, the OW sprite tables at `$7EB9xx/$7EBAxx` move to `$7FC5xx/$7FC6xx`: 21 two-byte operands in $04F2B8-$04F3D0, all of bank 04's references. The layer-2 tile buffer at `$7EB900` is overrun by LM too; every LM hack lives with it.
- **The rest of the mode** [CONFIRMED]: the $00AA80 dispatch becomes `CPY #$08/#$1E → #$32`, with the extra plane baked into the files themselves; GFX33 is read as 4bpp ($00B895 `LDY #$2000 → #$7D00`), which is why art drawn from AN1 looks garbled in LM on a ROM that keeps GFX33 at 3bpp; the GFX0F/00 RAM expanders go through $00A830 → $0EFC00 with the vanilla loops kept; and the GFX14 decompress at $00A149 is NOPped (the loader then owns the buffer's last file).
- **The baked data** [MEASURED]: LM's stock GFX1E is the plain 4bpp conversion with plane 3 = `p0|p1|p2` on every tile. Its GFX08 is the same on exactly 24 tiles (0x37-3B, 0x47-4B, 0x56-5B, 0x60, 0x6E-70, 0x7A-7B, 0x7E-7F), the ones the overworld draws; a level's GFX08 tiles stay as they were. That is a compromise: one file cannot serve both tilesets, and it is why an LM-saved ROM's overworld tile graphics differ from stock vanilla's in VRAM `$2000-$2FFF`. Its GFX33 is the plain conversion. All three are identical across several LM ROMs; hacks that redraw GFX08 and GFX33 differ, which is where a "hand-made" reading came from.
- **Layout**: LM keeps GFX33 at $088000 with GFX32 behind it, compressing the 4bpp blob to 0x1C68 bytes (vanilla's footprint there is 0x59F9). The three pointer operands are $00B88B, $00B890, $00B8D8, and LM follows them: a ROM that parks these files elsewhere and repoints those operands exports GFX08/1E/32/33 correctly.
- **LM's GFX loader** (observed): $00AA50 → $0FF780, $00AA6C → $0FF160, records at $12AD08, pointers at $0FF200.
- **The palette engine**: the $0EFC00 block, $0095E9, and $00A5BF → $0EF570, byte-identical across LM ROMs.

### Per-submap GFX  [MEASURED]

Each submap can have its own FG/SP file list, in LM's table at LM's index with LM's record layout (OVERWORLD §4, CONTRACT §7d). LM's *Overworld ▸ Submap GFX* dialog reads and writes it:

- LM's install of this hack replaces its whole GFX loader block: $0FF02A, $0FF15C, $0FF780, $0FF8A0, $0FF9C0, $0FFAB0, $0FFAF0, $0FFB20, $0FFD80, $0FFE93, $0FFFE7.
- But **with LM's layout stamp `4C 4D 03 01` at $0FF15C present, LM never installs any of that.** It reads the seven records, writes an edited slot straight into the table, and leaves the loader, stub and records alone. An LM overworld save over such a ROM changed 55 runs, none of them in $0FF7xx-$0FFDxx, and the one byte it wrote in the table was the slot the dialog changed.
- **The table address comes from the stub at $0FFAB0, and only from it.** LM parses its `ADC #imm` at +9/+10 and `LDA #imm` at +18. With the stamp present but other bytes in those fields, the dialog reads the address those bytes happen to spell and shows every slot as 0. The stub is 35 bytes.
- **An LM save does NOT lose the lists.** Without the stamp, LM's overworld save is a no-op for them (0 changed runs, records untouched); with it, LM updates the slot it was asked to and leaves the other six records alone.
- LM's first overworld save does install its own overworld hack suite, settled under "The overworld-ExAnimation settings" below.

AN2 (record w0): LM NOPs the `JSL $00BA28` in the overworld's `LDY #$14 : JSL $00BA28` at $00A147.

### The LEVEL Super GFX Bypass dialog  [MEASURED]

LM's *Level ▸ Super GFX Bypass* dialog shows `0` for all eleven slots unless two things hold:

- **LM takes the table's address from a FIXED offset**: the 24-bit operand of the `LDA base,X` in its own loader at $0FF7FF, the one place in an LM save where that address appears at all. It does not scan. A loader with the identical fetch idiom 0x67 bytes earlier makes the dialog read whatever sits at $0FF7FF as an address.
- **The record layout** is w7 FG1, w6 FG2, w5 BG1, w4 FG3, w3 BG2, w2 BG3, w11-w8 SP1-SP4, w0 AN2 (CONTRACT §7d). On a ROM without the layout stamp (`LM 03 01`), LM reads an OLDER record layout, which looks one word off. With the stamp, a record whose word k holds `0x10+k` reads back as FG1=0x17, FG2=0x16 … AN2=0x10.

Measured with level $105's FG1/BG1/SP1 set: the dialog shows `F` / `3` / `C` with the rest "7F Skip File", and a slot changed in LM lands at `base + 0x105*0x20 + 0x0C` (w6), with the other slots untouched.

Every LM level save also applies two routine bank-00 patches, $00F4A0 (`PLX : LDY #$25` → `STY $1693`) and $00F4EB, on its own ROMs as on any other.

### RATS block shapes  [MEASURED, against LM-edited ROMs as controls]

Lunar Magic validates the SHAPE of a block it owns: a dedicated block, data at tag + 8, the size LM itself would allocate. Byte-correct data in the wrong shape fails in one of three ways: a refusal box, a silent relocation, or a silent release that zeroes the block. LM honours RATS tags it did not write. The table below records LM's own shape for each structure, how LM finds it, and what LM's save does to it.

| structure | LM's own shape | LM finds it via | what LM's save does |
|---|---|---|---|
| separate-midway tables | own block, 0x800 (observed at $128008) | the routine's operand | level save writes the flags in place; any other shape is refused (above) |
| separate-midway routine | own 0xD0 block: tag + 0xC4 routine + 8×`FF` + `LM 10 01` (observed at $10FDD7) | hook operands $05D9E3/$05D979 | left alone in its own block; wiped if it shares a block LM releases (below) |
| secondary Y-high / FG-BG | two 0x1FE blocks (observed at $10F0C5/$10F1CB) | reader operands $05DC85/$05DC8A | *Modify Secondary Entrances* can re-allocate both into bank $10 (3261-byte blocks), repoint the readers and **release the old block: tag AND all data zeroed**; the four vanilla tables can move too; no warning either way |
| level ExAnimation table | own 0x600 block (`STAR FF05 00FA`) | the ExAnimation engine's operand | *Edit Level ExAnimated Frames* + save writes the 17-byte record as its own block and repoints the entry in place; tag untouched |
| OW ExAnimation record table | own 0x15 block | the setup operand | untouched by two overworld saves |
| OW ExAnimation settings | own 7-byte block | routine + 0x4A | re-installed by LM's first OW save (below) |
| GFX bypass records | 0x40E0 standalone, or 0x2D08 into one 0x6E00 block at $108000 (ExGFX pointers first) | $0FF7FF operand | Super GFX Bypass save writes the slot in place; the size rule is EXACT (below) |
| ExGFX 0x100+ pointers | first 0x2D00 of that 0x6E00 block | $0FF873 operand | `-ImportExGFX` writes the entry in place, whatever the block shape (below) |
| extended Map16 defs | one full bank per range | ladder slots | Map16 F9 save drops range 0 to "no defs" and populates ranges of its own; frees a block in range 0 (below) |
| acts-like table | 0x8000 | its lookup's operand at $06F624 | untouched by every save tried; the Map16 save keeps an existing address |
| level engine blocks, render bank $1F, ExAnimation engine, OW ExAnimation routine | LM's code, data at tag + 8 | hook operands | untouched by level, secondary, ExAnimation, overworld and Map16 saves |
| sprite size table | 0x400 (LM's help, "Custom Sprite List Sizes") | $0EF30C + `0x42` | not exercised |
| ExGFX 0x80-0xFF pointers $0FF600, palette table $0EF600, sprite bank table $0EF100, alt-ExGFX $03BCC0, method-2 bytes $05DE00/$06FC00/$06FE00 | vanilla-space tables at fixed addresses | fixed | not RATS blocks; nothing to shape |

**The midway ROUTINE and the secondary-entrance save.** *Modify Secondary Entrances* + save can re-allocate the two extension tables into fresh blocks, repoint $05DC85/$05DC8A, and RELEASE the block they came from. LM's release zeroes the tag AND the data. Anything else that shares that block goes with it: a midway routine placed in the tail of the secondary block was zeroed, so $05D9E3 and $05D979 then JSL into zeros (`BRK`). LM raised nothing; a release is not an error to it. LM's own routine has a 0xD0-byte block of its own (tag, routine, eight `$FF`, `LM 10 01`), and the same save leaves it alone. In that shape the routine block, its tag and both hooks survive the release, and a Main/Midway save with "separate settings" on writes `0x20` into the flags table and nothing else.

**The overworld-ExAnimation settings — LM re-installs, once; not a shape problem.** LM's FIRST overworld save installs its whole overworld hack suite (55 runs: bank 03/04/05 hooks, three big bank-$10 blocks). As part of it LM writes the seven settings bytes into a fresh 7-byte block of its own (observed at $10CF82, `STAR 0600 F9FF`, the same shape as a correct existing one), repoints the routine's `LDA long,X` at +0x4A to it, and releases the previous block by zeroing its tag. The record table and its tag are untouched. A second overworld save changed two bytes, the slot edited and one in $0FF06F, so this is not a per-save relocation. Read the settings through the operand at routine + 0x4A (the hook at $048086 names the routine), never at a fixed address. No LM-authored control exists: none of the LM-edited ROMs examined carries the overworld ExAnimation hack ($048086 is vanilla in all of them).

**The GFX bypass table — LM's size check is EXACT, and 0x40E0 is the size.** With the tag's size word set to 0x1000, 0x4000, 0x5000, or the tag removed, LM's Super GFX Bypass dialog showed `0` for every slot. Only 0x40E0 reads: 0x207 records of 0x20, the count LM's layout stamp `LM 03 01` defines. LM's own table is not a block of its own at all: on several LM ROMs it sits 0x2D08 into one 0x6E00 block at $108000 (ExGFX 0x100+ pointers, then 0x40E0 of records, then a 0x20 default record). So LM accepts either its own layout or a standalone block of the exact standalone size.

### `-ImportExGFX`  [MEASURED]

- **LM re-initialises its ExGFX 0x80-0xFF pointer table** ($0FF600, 0x180 bytes) on import. Anything parked in it is lost; code at $0FF770, the table's last sixteen bytes (ids 0xFB-0xFF), was zeroed by an import and the ROM stopped building levels.
- **The JSL at $0583B8 is part of how LM decides its GFX bypass is installed.** With vanilla's bytes at $0583B8, the same import installs LM's ENTIRE loader: $0FF780-$0FFE93, a 0x6E00 pointers+records block, `$0583B8 → JSL $0FF7F0`, and the five Direct Map16 dispatch entries. With a JSL at $0583B8, to any target, it does not. LM's own target, $0FF7F0, is its record-cache fetch (0x43 bytes): it stores the record into `$7FC006/8/9`, then compares `$1925` with `#$09` and returns. LM's layout leaves a gap between its loader group ($0FF780-$0FF884) and the slot tables at $0FF8A0, which its installs leave untouched.
- **The 4bpp/palette bundle.** An import onto a ROM without LM's 4bpp mode installs it: $0EFC00-$0EFCAF (176 bytes, byte-identical across LM ROMs), $0095E9 → `JML $0EFC50 : JSR LoadPalette : JML $0EFC80 : NOP NOP`, $00A830/$03DDC9 → `JML $0EFC00` (its GFX00/0F RAM expander), $00AB0B's filter body, $00B895 `LDY #$2000 → #$7D00` (GFX33 read as 4bpp), $0093F7 → `JSL` a per-ROM 13-byte NMI-wait routine (it waits on `$4212`, writes `$4200`, returns, and is followed by `LM 00 01`; observed at $108150 and $10EE10), $00A149 NOPped, and 373 bytes of bookkeeping at $0FEFCB. The import does NOT write the $00A5BF → `JSL $0EF570` fade-in hook or its 0x57-byte routine, which LM's full palette engine has. On a ROM that already has all of this, an import writes only its file, the bookkeeping at $0FEFAD, $0FFFE7 and the size byte: no code.
- **Where the 0x100+ pointer goes.** LM takes the ExGFX 0x100+ table's address from the 24-bit operand at the fixed $0FF873 and writes the new file's pointer there. It does not validate the block. On a ROM whose bytes at $0FF873 were some other instruction's (`A5 8A 25`, read as $258AA5), LM wrote the pointer into that address, unprotected in the expansion it had just grown the ROM into, and allocated the file at $208000. Planting the address at $0FF937 (LM's *other* copy of it) changes nothing. Every LM ROM carrying the feature holds its own table's address at $0FF873 behind a `BF` opcode; a ROM without the feature has `FF` there.
- The import needs the file as `ExGraphics/ExGFX100.bin` (and so on) beside the ROM.
- **Diff tooling gotcha:** a diff that compares only up to the smaller file misses everything LM writes into an expansion. When LM grows a 1 MB ROM to 2 MB, scan the whole file.

### Map16 F9 — LM's acts-like core

*Editors ▸ 16x16 Tile Map Editor*, F9, no edits, on a ROM that has a custom acts-like remap but not LM's core: LM wrote 13 runs. They were the ladder slots at $06F553, its acts-like core at $06F5E4 (96 B, over whatever sat at $06F5E4-$06F643), hooks at $04DCFA and $058A65/B45/C33/D2A, $06F65C/$06F70B/$06F7A0, a 0x8000 acts-like table at $1A8000, and slot 0 of the ladder set to `$00:F000` ("no defs"). Any code still jumping into that region then meets LM's `STA $65 : LDY #$0000 : RTL`. On a ROM that already has the core, F9 changes nothing. $06F800 onward, behind LM's trampolines, is free on every LM ROM examined. With the core present, LM keeps an existing acts-like table (its lookup's operand stays where it was), and a second F9 writes nothing.

- **The marker is a promise.** LM's *Map16* marker is `LM 12 01` at $06F65C. With it present, LM reads the extended-def block as its own to manage, and frees it. Claim only the hack you carry.
- **LM's install is staged.** Once the acts-like core is present, the save moves on to the next piece: it stops writing the $04DCFA/$058A65 hooks and instead populates ladder ranges 1 and 2 (banks $1A/$1C, two fresh 0x8000 blocks) with its per-tileset pages, leaving range 0 at "no defs". Holes in the ladder are legal (CONTRACT §7a-rev).

### Map16 F9 (LM 3.40)  [MEASURED]

LM 3.40 (by its version resource and by the header it writes into `.map16` files; a readme beside the same exe said 3.33). F9, no edits, compared on two ROMs: one carrying a custom-block dispatch with the older `LM 11 01` marker, and one without any dispatch.

| check | ROM with an `LM 11 01` dispatch | ROM without |
|---|---|---|
| marker $06F65C | `4C 4D 11 01` → `4C 4D 12 01` | `FF FF FF FF` → `4C 4D 12 01` |
| trampolines $06F660/$06F700/$06F760 | unchanged | FF, except $06F70B 15 B: `C9 D2 F0 11 C9 93 F0 1D C9 7F F0 19 4C 02 F6` (the tail of the second) |
| trampoline $06F7A0 | rewritten, 20 B: `20 08 F6 A5 0F F0 04 A3 0A 80 02 A3 06 C9 DA F0 0F 4C 02 F6` | the same 20 B, over FF |
| slots $06F690-$06F7CF | unchanged, `4C 02 F6 EA` ×4 each | FF |
| $06F624 operand | unchanged | unchanged |
| the four vanilla sites | unchanged | unchanged |
| ext-def block in range 0 | **FREED**: tag and all 2056 bytes zeroed | FREED, byte for byte the same |
| ladder $06F553 | slot 0 → `$00:F000` ("no defs"); slots 1-3 → three fresh 0x8000 blocks at $1A8000/$1C8000/$208000 (ROM expanded to 2 MB) | the same |
| acts-like table | kept, tag and operand | kept |
| a second F9 | writes nothing | — |
| `-ImportAllMap16` of the ROM's own export | byte-identical to the F9 | — |
| the same export with tile `$200` edited, imported | the F9's bytes plus one 8-byte block at $108150 holding the edited def, slot 0 → `$10:7150` | — |
| a GPS block after the F9 | still fires | — |

So the save does not mistake `LM 11 01` for its own install: it upgrades it. The only dispatch bytes it touches are the marker's version byte and the fourth trampoline, rewritten to 3.40's shape whether or not one is there. The dispatch survives: slots, three trampolines, sites and $06F624 untouched, and blocks still fire.

The extended-def block in range 0 is freed **with no marker present at all**, so 3.40 frees it on every plain F9, marker or not. An earlier observation, against a version said to be 3.33, had LM leave the block alone without a marker; either that LM differed or that observation was wrong.

**With 3.40's marker and trampoline already in place.** A ROM carrying `$06F65E` = `12` and the 20-byte fourth trampoline at $06F7A0 goes through the same F9 with **zero bytes changed in $06F650-$06F7FF**. The remaining changes are LM's Map16 install (the ladder and range 0's block, as above) and LM's bookkeeping at $0FEFE9. A second F9 writes nothing.

**Reading the ladder on a 3.40-saved ROM.** After the edited-tile import above, the ladder reads the edited tile as `070 p7 072 p7 071 p7 073 p7`, from the 8-byte block at $108150. Tile `$201`, untouched by the edit, reads `000 p0` ×4 there: LM's range 0 holds only the edited tile, and a reader following the slot runs past its 8 bytes into zeros. So after such a save, unedited page-2 tiles no longer draw what the freed block drew.

**`sysLMRestore`.** LM keeps `sysLMRestore/` beside the ROM, one `.lrp` per ROM name but ONE `smwOrig.smc` per folder. A different ROM opened in a folder where another had already been saved came back with vanilla's GFX pointer table at $00B992, 209 changed runs and most of the upper half zeroed, after LM offered to expand a 1 MB ROM "to 1 MB": a restore, not a save. Keep one ROM per folder, or delete `sysLMRestore` between runs.

## 2b. LM's write routes  [MEASURED]

Every way Lunar Magic writes to a ROM that was driven and diffed, with the number of changed runs on a ROM that already carries LM's level engine, 4bpp mode and acts-like core.

| route | runs | what it writes |
|---|---|---|
| Level save (Ctrl+S) | — | the level, plus the routine bank-00 patches; refuses if the midway tables are in the wrong shape (§2) |
| Secondary entrances save | — | can relocate the vanilla tables and the extension tables and repoint the readers (§2 "LM can RELOCATE") |
| Main/midway entrance save | — | the entrance tables in place |
| ExAnimated frames save | — | the record, as its own block (§2 "RATS block shapes") |
| Overworld save | 55 | the overworld hack suite on first save; nothing in the GFX loader block, records or $0FF15C when the layout stamp is present |
| Map16 F9 save | 25 | the ladder, range blocks and dispatch pieces (§2 "Map16 F9") |
| Submap GFX / Submap Layer 3 dialogs | — | the records in place; both round-trip |
| `-ImportExGFX` | 6 | the file, bookkeeping, the pointer through $0FF873 (§2 "-ImportExGFX") |
| `-ImportAllMap16` | 34 | Map16 data and acts-like into the table the lookup names |
| `-ImportCustomPalette` | — | the custom palette, byte for byte (LM_FILE_FORMATS) |
| `-ImportSharedPalette` | 2 | the shared palette range |
| `-ExpandROM 2MB` | 3 | the expansion |
| `-TransferLevelGlobalExAnim` | 2 | the ExAnimation entries |
| `-ImportLevel` (MWL) | 28 | the level, plus the secondary-entrance machinery (below) |
| `-ImportMultLevels` | 32 | the same set |
| `-ImportGFX` | 11 | takes over graphics management wholesale (below) |

**Routes that take over a structure:**

- **`-ImportGFX` takes over graphics management.** It re-inserts every file from the `Graphics` folder, moves the GFX32/GFX33 boot blobs back to its own layout ($088000 / $089C68), rewrites the three pointer tables at $00B992, and FREES blocks holding converted graphics elsewhere. Anything that reads those files through the operands rather than at constant addresses keeps working: after the import the files decode at their new homes, the $00B895 4bpp load is untouched, the ROM boots, and the overworld's tile graphics still match.
- **`-ImportLevel` / `-ImportMultLevels` touch the secondary-entrance machinery**: $05DC81 and $0DE191 (the table readers) and the block holding the extension tables. This is the silent relocation recorded under "RATS block shapes". Read the tables through the operands.
- They also set the imported level's entry in **$0EF100**, LM's per-level sprite bank table, which is the table being used as intended.

**Not exercised:** `-ImportMap16` (needs a single-level `.map16`, which only the GUI produces); `-ImportTitleMoves`/`-ExportTitleMoves` (refused with "ASM code not detected" when the title-screen playback hack is not installed); and the GUI-only title-screen, credits and recording saves.

## 2c. The same routes on a ROM carrying GPS blocks  [MEASURED, LM 3.40]

A ROM with LM's custom-block dispatch (`LM 11 01`) and GPS's stubs and hijacks in it (two blocks, one placed in level $105), with the block's firing in an emulator as the in-game check:

| route | runs | what it touched | result |
|---|---|---|---|
| Level save (Ctrl+S, level dirtied) | 8 | $0EF205, the per-level sprite bank entry | block fires |
| Map16 F9 save | 38 | the five below | **upgrades the dispatch in place**; block fires |
| `-ImportAllMap16` (file carries page-2 tiles) | 38 | the same five | identical to F9, byte for byte; a second import writes nothing |
| `-ImportLevel` | 28 | the §2b set | block fires |

The five Map16 writes: $06F65E (marker version `11` → `12`), $06F7A3 len 17 (the fourth trampoline rewritten to LM 3.40's shape, one byte longer than the older version's), $06F626 (`$91` → `$11`: GPS points $06F624 at the FastROM mirror of the table and LM normalises it), $06F553 len 34 (ladder range operands), and the range-0 ext-def block (freed, with LM's three 32 KB ranges allocated). The last two happen without a dispatch too, so they are §2 "Map16 F9", not the dispatch. GPS's own bytes ($06F67B, $06F690 onward, $06F717, marker, tables, code) and the four vanilla sites are untouched by every route. With the `LM 12 01` marker and 3.40's trampoline already in place, the import leaves $06F65C-$06F7EF alone entirely.

Two LM facts from driving it: a level number after the ROM on its command line makes LM exit at once, and *Save Level to ROM* writes nothing for an unmodified level. Neither GUI save raised a dialog.
