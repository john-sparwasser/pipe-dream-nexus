# Lunar Magic's hooks into SMW

This page lists every place where Lunar Magic (LM) changes Super Mario World's own code. That means a JSL/JML/JMP written over vanilla instructions, a vanilla operand repointed to LM code, or an instruction LM changes or NOPs where it sits. It also covers the vanilla tables LM moves elsewhere or fills in itself. People call these hooks or hijacks. All addresses are SNES LoROM addresses written as $BBAAAA, and they are vanilla addresses unless the row says otherwise. Each hook's target is LM's own code. Where that code sits at a fixed address, the address is given. Where LM allocates it per ROM (usually in RATS-protected expanded banks), the address is the one observed on real LM-saved ROMs and is marked as observed.

Each claim keeps the confidence tag of the note it comes from. **[CONFIRMED]** means verified against the disassembly, a test or several LM ROMs. **[MEASURED]** means a controlled before/after save in LM, or a run on an emulator or console. **[LM-DOC]** means LM's own help says so (restated here in our own words). **[INFERRED]** means the address and shape suggest it but nothing has been run against it. **[PARTIAL]** means only partly decoded. Each row cites the note and section it comes from, for example (CONTRACT §7a-rev), and those notes have the full write-ups. The sources are CONTRACT, LM_PARITY, EXANIMATION, OVERWORLD, LM_FILE_FORMATS, PATCHES, GPS_PORT, PIXI_PORT and LUNAR_MAGIC. A few rows convert an address that a note gives as a headered file offset, or as the operand byte of an instruction, into the SNES address of the instruction. Those rows say so, and the vanilla instruction was checked against the SMW disassembly.

Most hooks are not there in a clean ROM. LM installs a baseline set on the first level save. Other hacks go in when you first open a dialog or first save a given editor. See "Installed on demand" at the end.

## Level loading and LM's level engine

A plain LM save installs a level-entry engine and a height engine. The level-entry engine sets the camera and the FG/BG start position, including "relative to player". The height engine stores a per-level height byte and lets a horizontal level trade width for height. It also installs a large render block in its own bank that redraws tall levels. The code blocks are relocated per ROM. Between ROMs, only 16-bit in-bank operands and the bank bytes of a few long operands change [CONFIRMED] (LM_PARITY §2 "Level entry").

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $05D8E2 | JSL $0EF550 | Copies the level number to $010B (Y = level×2) and puts level+1 into $FE early in the load, where LM's GFX loader reads it [CONFIRMED] | LM_PARITY §2 "Sprite bank relocation"; CONTRACT §12g |
| $00A6B8 | Hook to $0EF560 | One of LM's level-init routines [CONFIRMED] | LM_PARITY §2 "Level load" |
| $00A6CC | Hook to $05DD00 | Applies, then clears, the entrance's slippery/water flags in $192A bits 7/6 [CONFIRMED] | CONTRACT §11 "Entrance flags"; LM_PARITY §2 "Level load" |
| $009708 | Hook into the level-entry engine (block A) | Level start: width from the header ($142A/$F9) [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $05DA17 | Tail hook into block A (per-ROM) | Layer-2 scroll setting, $1443-$1452, then the FG/BG initial position, taken from vanilla's table or relative to Mario's Y when $13CD bit 7 is set [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $05BCA5 | Hook into block A | A bounds check (not described further) [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $00E966 | Hook into block A | A bounds check (not described further) [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $05D9A1 | Hook into block B (per-ROM) | Vertical-level check in the height engine [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $05DA8A | Hook into block B | Builds the per-screen tilemap pointer tables $0BF6/$0C56 for the level's height [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $05DB5F | Hook into block B | As $05DA8A [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $0C9436 | Hook into block B | As $05DA8A. Also listed as hooked but not traced in the overworld notes [CONFIRMED] | LM_PARITY §2 "Level entry"; OVERWORLD §11 "Lunar Magic's overworld hooks" |
| $02950B | Hook into block B | As $05DA8A [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $0295BE | Hook into block B | As $05DA8A [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $00F70D | Hook into block B | As $05DA8A [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $00A873 | Vanilla's ROM-to-RAM plane-pointer copy skipped | The loader's plane pointers now come from RAM tables built for the level's height [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $00BDA8 | Plane-pointer map reads (from $00BDA8 on) repointed to RAM $0BF6/$0C26/$0C56/$0C86 | Per-level plane pointers, because the column stride is no longer a constant [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $00F50D | LDA $00BA70,X becomes LDA $000CC6,X (sibling tables to $0CB6/$0CD6/$0CE6) | Block-probe plane-pointer tables rebuilt in RAM per level [CONFIRMED] | LM_PARITY §2 "Block behaviour" |
| $019509 | As $00F50D | As $00F50D [CONFIRMED] | LM_PARITY §2 "Block behaviour" |
| $029301 | As $00F50D | As $00F50D [CONFIRMED] | LM_PARITY §2 "Block behaviour" |
| $0295F4 | As $00F50D | As $00F50D [CONFIRMED] | LM_PARITY §2 "Block behaviour" |
| $02A6C2 | As $00F50D | As $00F50D [CONFIRMED] | LM_PARITY §2 "Block behaviour" |
| $02BA79 | As $00F50D | As $00F50D [CONFIRMED] | LM_PARITY §2 "Block behaviour" |
| $02D194 | As $00F50D | As $00F50D [CONFIRMED] | LM_PARITY §2 "Block behaviour" |
| $0DA963 | ADC #$B0 becomes a 16-bit ADC $13D7 | Object engine's screen stride follows the level height kept in RAM [CONFIRMED] | LM_PARITY §2 "Object handlers with $13D7" and "Level entry" |
| $0DA96B | As $0DA963 | As $0DA963 [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $0DA9D6 | As $0DA963 (vanilla ADC #$B0 / ADC #$01) | As $0DA963 [CONFIRMED] | LM_PARITY §2 "Object handlers with $13D7" |
| $0DA9F7 | As $0DA963 | As $0DA963 [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $0DA9F9 | As $0DA963 | As $0DA963 [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $0DBB16 | As $0DA963 | As $0DA963 [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $00F478 | 43 bytes rewritten | Layer-scroll bounds that read the level height ($13D7). The same rewrite also touches the acts-like call at $00F4DD (see Map16) [CONFIRMED] | LM_PARITY §1, §2 "Level entry" |
| $0586A1 | Object loader adds $8A (band × $200) to every object's plane pointer | Lets objects reach rows past 31 in 32-row bands, set by extended objects 01/03 [CONFIRMED] | LM_PARITY §2 "How a tall level places past row 31" |
| $0583C7 | Hook to $0DE1F0 | Zeroes the band ($8A) at the start of each layer [CONFIRMED] | LM_PARITY §2 "How a tall level places past row 31" |
| $058DA4 | JSL $0EFD00 | Level engine. $0EFD00/$0EFD50 pick the VRAM column stride ($1B0 or $200) from LM's per-level flag in $7FC00B [CONFIRMED] | LM_PARITY §2 "Level load" and "The render half" |
| $0586F7 | Hook to $1FB00F (observed) | Render engine: tracks layer positions in $7F830B… and redraws columns past row 27 via $1FA70E/$1FA777 [CONFIRMED] | LM_PARITY §2 "The render half" |
| $0580A9 | Hook to $1FAFF1 (observed) | Render-engine entry on first load. It also applies the custom palette on the first load (see Palettes) [CONFIRMED] | LM_PARITY §2 "The render half"; CONTRACT §12g gives this site as $05809E |
| $008751 | Hook to $1FA2D2 (observed) | Part of the render engine [CONFIRMED] | LM_PARITY §2 "The render half" |
| $00A5A2 | Hook to $1FA28D (observed) | Part of the render engine [CONFIRMED] | LM_PARITY §2 "The render half" |
| $00BF3C | Small edit (from $00BF3C on) | One of the "small tweaks LM makes alongside" the render engine. Purpose not described | LM_PARITY §2 "The render half" |
| $00AF4C | Small edit (from $00AF4C on) | As $00BF3C. Purpose not described | LM_PARITY §2 "The render half" |
| $00C07D | Small edit (from $00C07D on) | As $00BF3C. Purpose not described | LM_PARITY §2 "The render half" |
| $00C25C | Call through the Map16 ladder entry ($06F540) | Listed with the render tweaks. Purpose not described | LM_PARITY §2 "The render half" |
| $05BAAA | Small edit (from $05BAAA on) | As $00BF3C. Purpose not described | LM_PARITY §2 "The render half" |

Tables and data:

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $0580C0 | Level-mode table operands moved into LM's render bank ($1FA41C/$1FA626/$1FA69A observed for $0580C0/$0580C4/$0580C8) | Per-level-mode tables the render engine owns [CONFIRMED] | LM_PARITY §2 "Level load" and "The render half" |
| $05E000 | Layer-1 pointer table stays put, but entries are repointed to RATS-tagged data in expanded banks | Level data relocation [CONFIRMED] | CONTRACT §3 |
| $06FA00 | Initialised to $20 | LM's extended layer-2 scroll byte, per LM_PARITY "Level entry". The earlier "Map16 machinery" list counts it as a 1536-byte $20 fill [CONFIRMED] | LM_PARITY §2 "Level entry" and "Map16 machinery" |

The per-level height byte and its LUT of 32 heights (all with columns × height ≤ $3800) live in block B. Height byte bits: 0-4 = LUT index, 5 = extended sprite list, 7 = "vertical positioning" [CONFIRMED] (LM_PARITY §2 "The height LUT").

## Map16 and block behaviour

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $00C17A | REP #$20 becomes JSL $06F5D0 | The Map16-to-8×8 lookup. $06F5D0 is a wrapper (`LDY $0B : STY $05`) into the definition-pointer ladder at the fixed $06F540. Tiles below $200 use the vanilla RAM table path. Tiles $200 and up get bank:(imm + tile×8) from the slot that covers their $1000-tile range. Byte $00C17A = $22 is the "installed" test [CONFIRMED on 7 ROMs] | CONTRACT §7a-rev |
| $058A65 | JSL $06F540 | Loader-side path through the ladder (with $3F masks). Written by LM's Map16 save [MEASURED] | CONTRACT §12g; LM_PARITY §2 "Map16 F9" |
| $058B45 | JSL $06F540 | As $058A65 [MEASURED] | CONTRACT §12g |
| $058C33 | JSL $06F540 | As $058A65 [MEASURED] | CONTRACT §12g |
| $058D2A | JSL $06F540 | As $058A65 [MEASURED] | CONTRACT §12g |
| $00F4DD | JSL $00F545 becomes JSL to a per-site trampoline | Acts-like lookup for Mario's block contact. The notes cite the operand byte, $00F4DE [CONFIRMED] | LM_PARITY §1, §2 "Block behaviour"; CONTRACT §12g |
| $019533 | JSL $00F545 becomes JSL to a per-site trampoline | Acts-like lookup (sprite/block). The notes cite operand $019534 [CONFIRMED] | LM_PARITY §2 "Level entry"; CONTRACT §12g |
| $02961A | JSL $00F545 becomes JSL to a per-site trampoline | Acts-like lookup. The notes cite operand $02961B [CONFIRMED] | LM_PARITY §2 "Level entry"; CONTRACT §12g |
| $02A6EB | JSL $00F545 becomes JSL to a per-site trampoline | Acts-like lookup. The notes cite operand $02A6EC [CONFIRMED] | LM_PARITY §2 "Level entry"; CONTRACT §12g |
| $00F4A0 | `PLX : LDY #$25` becomes `STY $1693` | Patch LM applies on every level save, tied to the $00F4DD site's fallback [MEASURED] | LM_PARITY §2 "The LEVEL Super GFX Bypass dialog" and "Level entry" |
| $00F4EB | Patched on every level save | As $00F4A0. Exact change not described [MEASURED] | LM_PARITY §2 "The LEVEL Super GFX Bypass dialog" |
| $04DCFA | JSL $06F5E4 | Overworld path into LM's acts-like core wrapper [MEASURED] | CONTRACT §12g; OVERWORLD §11 |
| $0DA4B8 | Object 22's pointer (vanilla placeholder $0DB3E3) repointed to $0DF08A. Objects 23/26/27/28/29 go the same way, identically in all five tileset tables | Direct Map16 objects. 22 = page-0 tile (4 bytes). 23 = page-1 tile ($0DF08E). 26 = no-tile directive ($0DF130, pokes $0DDA, music-related). 27 = variable-length Direct Map16 with stamp descriptor ($0DF150). 28 = no-tile directive, entrance/position ($0DF160). 29 = like 27 on FG pages 40-7F ($0DFF50) [CONFIRMED] | CONTRACT §9d; LM_PARITY §1 |
| $0DA112 | Extended object 01's pointer (vanilla $0DA53D) taken over by LM's handler (LM's ext-01 handler is at $0DE1D0) | Screen jump that also carries the 32-row band in its X nibble [CONFIRMED]. That this table entry is what points at $0DE1D0 is [INFERRED] | LM_PARITY §2 "Level entry" and "How a tall level places" |
| $0DA115 | Extended object 02 (vanilla: null entry) runs $0DE1B0 | Secondary exit in word form: consumes 2 extra bytes, `destination | flags<<8`. The entry address comes from the table position, base $0DA10F + 2×3 [INFERRED] | CONTRACT §9d, §9d-2 |
| $0DA118 | Extended object 03 (vanilla: null entry) runs $0DE1E0 | Screen jump to screen = byte 2, with band in Y. Entry address from table position [INFERRED] | CONTRACT §9c; LM_PARITY §2 "How a tall level places" |
| $0DE1AC | Edited | Listed among LM's extended-object handler edits. Purpose not described [CONFIRMED] | LM_PARITY §2 "Level entry" |

LM's own Map16 code and tables (fixed addresses in bank $06):

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $06F540 | Ladder entry (`CMP #$0400`) and eight range slots. Slot k sits at $06F552/$06F55B/$06F566/$06F56F/$06F593/$06F59C/$06F5A7/$06F5B0, each `69 imm16 A0 bank<<8`, and bank 0 means the range is empty | Extended Map16 definitions, one slot per $1000 tiles (a 32 KB LoROM window). Ranges 2/3/6/7 reach their ADC with carry set, so the stored imm is one less [CONFIRMED] | CONTRACT §7a-rev |
| $06F5E4 | 96-byte acts-like core: the wrapper, `LM 10 01` marker at $06F5FC, `TYA : JML $00F545` tail at $06F602, overworld bail at $06F608, lookup at $06F617 | Acts-like lookup. An entry ≥ $200 is another tile, whose entry is read in turn (a chain). Written by the Map16 save [MEASURED] | CONTRACT §12g, §12g |
| $06F624 | Operand of the lookup's table read (bank byte at $06F626). Default table $118000 | Where the 2-byte-per-tile acts-like table lives. GPS reads this operand to find the table [MEASURED] | CONTRACT §12g; GPS_PORT "The local oracle" |
| $06F63B | Operand for the pages-40+ acts-like table | Second acts-like table for FG pages 40-7F. GPS needs $06F63C ≠ $FF [MEASURED] | CONTRACT §12g; GPS_PORT "The local oracle" |
| $06F65C | Marker `LM 11 01` (older LM) or `LM 12 01` (LM 3.40) | Custom-block dispatch version. A 3.40 Map16 save upgrades `11` to `12` in place [MEASURED] | CONTRACT §12g; LM_PARITY §2 "Map16 F9 (LM 3.40)" |
| $06F660 | Trampoline 1 of 4 (others at $06F700, $06F760, $06F7A0) | Each does `JSR $F608` into the lookup, reads the caller's return-address low byte and branches to a 16-byte contact slot. 3.40 writes the fourth as a 20-byte form (`JSR $F608 : LDA $0F : BEQ +4 : LDA $0A,s : BRA +2 : LDA $06,s : CMP #$DA : BEQ $06F7C0 : JMP $F602`). The fall-throughs at $06F67B/$06F717 are [INFERRED] as `JMP $F602` [MEASURED] | CONTRACT §12g |
| $06F690 | Contact slots $06F690-$06F7EF, default `JMP $F602 : NOP` ×4 each | Where custom-block tools (GPS) put their per-contact stubs. LM's help gives these block-interaction JSL hooks as PC $37890-$379C0 (headered), which is $06F690-$06F7C0 [LM-DOC], [MEASURED] | CONTRACT §8, §12g; GPS_PORT "What GPS does" |
| $06F7D0 | FF in measured LM ROMs ($06F800-$06F9FF too) | Free run behind the trampolines [MEASURED] | CONTRACT §12g; LM_PARITY §2 "Map16 F9 (LM 3.40)" |

Tables and data:

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $118000 | 2 bytes per tile, $8000-byte block (identity below $200, $130 above by default) | Acts-like table. A Map16 save may put it elsewhere, for example $1A8000 when no core was present [CONFIRMED] | CONTRACT §7b; LM_PARITY §2 "Map16 F9" |
| $0D8000 | Page-1 tiles ($100-$1FF) written back into the vanilla bank-$0D definitions in place | Tileset-specific Map16 [CONFIRMED] | CONTRACT §7b |
| $058000 | TilesetMAP16Loc left unchanged | Vestigial once the lookup is hooked [CONFIRMED] | CONTRACT §7 |

## Graphics, ExGFX and the Super GFX Bypass

The Super GFX Bypass hack is LM's per-level graphics record: $20 bytes per level, plus $207 records once overworld submaps are added. Its record layout and its file resolver are in CONTRACT §7d. LM installs it together with the layer-3 GFX bypass ("step A", 32 runs in a controlled save) (CONTRACT §12b "layer-3 install").

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $00AA50 | `A2 03 B5 04 9D` becomes JSL $0FF780 : RTS | LM's level-GFX loader, which loads each slot from the record. The same bytes appear on every bypass-installed ROM, so this is the "installed" test [CONFIRMED] | CONTRACT §7d, §12b |
| $00AA6C | Operand of a decompress call: $00BA28 becomes $0FF160 | Redirects a decompression into LM's resolver [CONFIRMED] | CONTRACT §7d, §12b |
| $00AA06 | BEQ (`F0 03`) becomes NOP NOP | Kills the "don't upload sprite GFX" early-out [CONFIRMED] | CONTRACT §12b "Step A" |
| $00AA47 | BEQ (`F0 03`) becomes NOP NOP | Kills the "don't upload FG/BG" early-out [CONFIRMED] | CONTRACT §12b "Step A" |
| $0583B8 | `LDA $1925 : CMP #$09` becomes JSL $0FF7F0 : NOP | Record-cache fetch: caches the level's record pointer at $7FC006/8 and the enable byte at $7FC009, then redoes the displaced compare. Some JSL here is part of how LM decides its bypass is already installed [MEASURED] | CONTRACT §12b "Step A", §12g; LM_PARITY §2 "-ImportExGFX" |
| $009471 | `LDX $13C6 : LDA #$18` becomes JSL $0FF9C0 : NOP | Installed with step A. Purpose not described (vanilla loads the cutscene number here) [CONFIRMED] | CONTRACT §12b "Step A" |
| $049DFE | Operand of the JSL at $049DFD (vanilla $05DBF2) becomes $0FFAF0 | Installed with step A. Purpose not described [CONFIRMED] | CONTRACT §12b "Step A" |
| $0DA4BE | Object 24's pointer in tileset table 1 (`E3 B3` becomes `E0 F0`/`F0 F0`), with 25 new bytes at $0DF0E0 | Installed with step A. The same change is made at $0DC203, $0DCE03, $0DDA03 and $0DE903 (the other four tileset tables). Later notes call these "the DM16 dispatch entries". The object number comes from the table position [INFERRED] | CONTRACT §12b "Step A"; LM_PARITY §2 "-ImportExGFX" |
| $0DC203 | As $0DA4BE | As $0DA4BE | CONTRACT §12b "Step A" |
| $0DCE03 | As $0DA4BE | As $0DA4BE | CONTRACT §12b "Step A" |
| $0DDA03 | As $0DA4BE | As $0DA4BE | CONTRACT §12b "Step A" |
| $0DE903 | As $0DA4BE | As $0DA4BE | CONTRACT §12b "Step A" |
| $0081E2 | JML $1F8008 (observed) | The VRAM patch. Without it, LM's BG2/BG3 bypass slots (VRAM pages 4-5, tiles $200-$2FF) do not load [CONFIRMED], [LM-DOC] | CONTRACT §0, §7d; LM_PARITY §2 "The render half" |

LM's 4bpp graphics mode (stores all GFX at 4bpp):

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $00AACD | LDX #$10, with the plane loops collapsed into a straight 32-byte-per-tile copy | 4bpp upload [CONFIRMED] | CONTRACT §0 |
| $00AAE1 | RTS ($60) | Stubs vanilla's expand-upload. LM checks this byte to decide that a ROM's files are 4bpp [MEASURED] | CONTRACT §0 |
| $00AA8C | CPY #$08 becomes CPY #$32 | Nothing reaches the plane-3 filter path any more, because plane 3 is baked into GFX08/GFX1E [CONFIRMED] | CONTRACT §12g; LM_PARITY §2 "4bpp graphics" |
| $00AA90 | CPY #$1E becomes CPY #$32 | As $00AA8C [CONFIRMED] | CONTRACT §12g |
| $00AB0B | Filter body replaced with LM's | Filter path code (now unreached) [CONFIRMED] | CONTRACT §12g; LM_PARITY §2 "-ImportExGFX" |
| $00A830 | GFX0F expander's JSL $00BA28 redirected to $0EFC00 | LM's wrapper: decompress, then fold the 4bpp buffer back to three planes for vanilla's RAM expanders [CONFIRMED] | CONTRACT §12g; LM_PARITY §2 "-ImportExGFX" |
| $03DDC9 | Bank 03's sprite-GFX JSL $00BA28 redirected to $0EFC00 | As $00A830 [CONFIRMED] | CONTRACT §12g |
| $00B895 | LDY #$2000 becomes LDY #$7D00 | GFX33 (AN1) decompressed straight to $7E7D00 as four planes [CONFIRMED] | CONTRACT §12g; LM_PARITY §2 "-ImportExGFX" |
| $00A149 | The JSL $00BA28 after LDY #$14 is NOPped | The GFX14 load moves to the bypass record's AN2 slot [CONFIRMED] | CONTRACT §12g; OVERWORLD §4 |

LM's fixed-address code, operands it reads and tables it owns:

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $0FF780 | Loader group $0FF780-$0FF884, record-cache fetch at $0FF7F0, resolver at $0FF903 | Bypass loader. The resolver maps 00-33 to vanilla tables, 7F to "skip", 80-FF to $0FF600 + (n&$7F)×3 and 100-FFF to the per-ROM ExGFX table; it then JMLs to vanilla's decompressor at $00BA47 [CONFIRMED] | CONTRACT §7d, §12d |
| $0FF7FF | 24-bit operand of the record fetch `LDA base,X` | LM's GFX Bypass dialog takes the record table's address from this one offset and does not scan for it [MEASURED] | LM_PARITY §2 "The LEVEL Super GFX Bypass dialog"; CONTRACT §12g |
| $0FF873 | 24-bit operand of the ExGFX 100+ `LDA table,X` | LM's ExGFX import writes new pointers into whatever this operand names [MEASURED] | LM_PARITY §2 "-ImportExGFX"; CONTRACT §12g |
| $0FF15C | Layout stamp `4C 4D 03 01` ("LM" + version) | Tells LM which record layout is installed. With it present, LM reads and writes the records and installs none of its own loader [MEASURED] | CONTRACT §12g; LM_PARITY §2 "Per-submap GFX" |
| $0FF900 | Decompressor entry, `JSL $0FF900` with A = file and $00 = 24-bit destination (files 32/33 excluded) | Public entry point for custom code [LM-DOC] | CONTRACT §6, §8 |
| $0FF600 | 3-byte pointers for ExGFX 80-FF ($180 bytes) | Fixed ExGFX 80-FF table. An ExGFX import re-initialises it [CONFIRMED], [MEASURED] | CONTRACT §7d; LM_PARITY §2 "-ImportExGFX" |
| $0FEFC3 | Step-A code blocks in bank $0F at $0FEFC3, $0FF15C, $0FF200, $0FF7D0, $0FF7F0, $0FF8A0, $0FF900, $0FF9C0, $0FF9E0, $0FFAB0, $0FFAF0, $0FFB20 and $0FFD80 | The bypass and layer-3 machinery [CONFIRMED] | CONTRACT §12b "Step A" |
| $00B992 | The three GFX pointer tables ($00B992/$00B9C4/$00B9F6) rewritten by LM's GFX import | Inserted GFX00-33 [MEASURED] | LM_PARITY §2b |
| $00B88B | Operands of the GFX32/GFX33 blob pointer ($00B88B low word, $00B890 bank) and the second blob ($00B8D8) | LM repoints these when Mario or animated GFX are edited. Its own layout is $088000/$089C68 [CONFIRMED] | CONTRACT §12a, §12b "Second animated blob"; LM_PARITY §2b |

The bypass record table itself is per ROM. It is often $2D08 bytes into one $6E00 block that starts with the ExGFX 100+ pointers, then $40E0 bytes of records, then a $20-byte default record [MEASURED] (LM_PARITY §2 "RATS block shapes").

## Palettes

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $0095E9 | `JSR UploadSpriteGFX : JSR LoadPalette` becomes `JML $0EFC50 : JSR LoadPalette : JML $0EFC80 : NOP NOP` (12 bytes) | LM's palette engine: saves and restores $7E2000 around the vanilla loads, then applies the level's custom palette. $0095E9 = $5C is the "installed" test [CONFIRMED] | CONTRACT §7e, §12g |
| $00A5BF | JSL $05BE8A becomes JSL $0EF570 | Fade-in step: the vanilla code reloads the palette at $00A5B9 and would wipe the custom one. $0EF583 copies the level's blob into the $0701 staging buffer, clears $FE, then runs the displaced JSL [CONFIRMED] | CONTRACT §7e, §12g |
| $0580A9 | Hook to $1FAFF1 | First-load palette apply (see Level loading) [CONFIRMED] | CONTRACT §12g (as $05809E); LM_PARITY §2 "The render half" |
| $0093F7 | JSL to a per-ROM 13-byte routine (`LDA #$81 : BIT $4212 … STA $4200 : RTL` + `LM 00 01`) | NMI-enable/wait fix, installed with the palette/4bpp bundle [CONFIRMED] | CONTRACT §12g; LM_PARITY §2 "-ImportExGFX" |

Tables and data:

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $0EF600 | Pointer table, 3 bytes per level, $200 entries | Per-level custom palette. Each entry points at a RATS blob of $202 bytes: the back-area colour, then 256 BGR555 words [CONFIRMED] | CONTRACT §7e |
| $0EFC00 | 176-byte block $0EFC00-$0EFCAF | Palette engine ($0EFC50/$0EFC80) and the 4bpp expander wrapper ($0EFC00). Identical across LM ROMs [CONFIRMED] | CONTRACT §12g |
| $00B0A0 | Vanilla shared palettes left in place | LM's shared-palette file is a flat copy of $00B0A0-$00B881 [CONFIRMED] | LM_FILE_FORMATS "Shared palettes" |

## Layer 2 and backgrounds

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $05803B | Hook to $0EF510 | Reads the per-level byte at $0EF310 into $7FC00B. Bit 1 = do not fall through to $058074. Bit 2 = skip the layer-2 map fill. Bits 4-6 = BG Map16 bank. This byte is what tells a custom background from layer-2 objects [CONFIRMED] | CONTRACT §10b; LM_PARITY §2 "The render half" |
| $00F6E4 | Hook to $1FAFA0 (observed) | Layer-2 scroll code. PIXI checks for $5C here as its "VRAM patch present" test [CONFIRMED] | LM_PARITY §2 "The render half"; PIXI_PORT "Open questions" |
| $00F7E8 | Hook to $1FAFC4 (observed) | Layer-2 scroll code [CONFIRMED] | LM_PARITY §2 "The render half" |
| $00F871 | Hook into block A | Layer-2 scroll bounds [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $00F77B | Hook into block A | Layer-2 scroll bounds [CONFIRMED] | LM_PARITY §2 "Level entry" |
| $00F79D | Hook into block A | Layer-2 scroll bounds [CONFIRMED] | LM_PARITY §2 "Level entry" |

Tables and data:

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $05E600 | A real 24-bit pointer (bank ≠ $FF) per edited level | Custom background: an RLE stream in its own RATS block, decoded to $800 bytes (a low-byte plane, then a page plane) over 32 rows at stride $200. Each save allocates a fresh block [CONFIRMED] | CONTRACT §10b |
| $0EF310 | One settings byte per level (see $05803B) | Background mode and BG Map16 bank [CONFIRMED] | CONTRACT §10b |

## Layer 3

LM's layer-3 support comes in two separate installs. Step A is the layer-3 GFX bypass and the record machinery. It is triggered by "Enable bypass of standard Layer 3 GFX" and its hooks are under Graphics above. Step B is the layer-3 tilemap bypass, triggered by "Enable bypass of standard Layer 3 tilemap" (11 runs in a controlled save). Step B also carries the advanced scroll/blend group. LM will not install either until its restore system has found the original unmodified ROM [CONFIRMED] (CONTRACT §12b "The install gate", "layer-3 install").

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $00A01F | `AD E3 1B F0 20 3A` becomes `22 64 99 10 F0 1F`: JSL $109964 in place of `LDA $1BE3 … DEC`, with the following BEQ shortened by one | Returns the Layer 3 Option, after first applying the advanced bypass group when $145E bit 0 is set. So this hook is also the scroll/blend engine [CONFIRMED] | CONTRACT §12b "Step B" |
| $00A153 | `A9 06 85 12` becomes JSL $109DE4 | Tilemap bypass copy. On a level load this site was measured as never executed [CONFIRMED], [MEASURED] | CONTRACT §12b "Step B", "Step B" (load-path measurement) |
| $0194B6 | `A9 00 8D 93 16` becomes JML $109E04 : RTS | Installed with step B. Purpose not described [CONFIRMED] | CONTRACT §12b "Step B" |
| $05C40C | `LDA $1403 : BEQ +3` becomes JSL $109D7B : RTS | Per-frame layer-3 scroll dispatcher for the advanced group's rate and auto-scroll codes. Off, it returns to vanilla's $05C414/$05C494 [CONFIRMED] | CONTRACT §12b "Step B", "advanced group" (dispatcher) |

LM's fixed-address layer-3 code and tables:

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $0FF9E0 | Layer-3 GFX loader: `LDA [record] : ASL : BPL default` | Gate on record w0 bit 14. Otherwise it uses the default record at $0FFA6F, whose tail is LG4-LG1 = 2B 2A 29 28 [CONFIRMED] | CONTRACT §12b "The GFX bypass" |
| $0FFA7F | VRAM destinations $4C00 $4800 $4400 $4000 for slot index 0-3 | LG1 goes to word $4000 … LG4 to $4C00, $400 words each [CONFIRMED] | CONTRACT §12b "The GFX bypass" |
| $0FFD9F | Advanced-group reader (`PHY : LDA.l $7FC006 …`), gated on $7FC009 = $41/$42. Nibble-pair helper at $0FFE82 | Packs the spare high nibbles of nine record words into $7FC01A/$7FC01B/$7FC01C/$145E [CONFIRMED] | CONTRACT §12b "The ADVANCED BYPASS" |
| $0FFEBC | Tilemap destination words $50A0 $5000 $5080 $5800 | Under Status Bar / Start of Layer 3 / Last Line of Status Bar / Bottom Half. LM's help gives this as file offset $800BC [CONFIRMED], [LM-DOC] | CONTRACT §12b "The TILEMAP bypass" |
| $0FFEB4 | Sizes $2000 $1000 $0800 $0000 | Tilemap file size per size code [CONFIRMED] | CONTRACT §12b "The TILEMAP bypass" |
| $0FFEC4 | $0140 | Size of the status-bar tilemap (32×5 words). LM's help gives file offset $800C4 [CONFIRMED], [LM-DOC] | CONTRACT §12b "The TILEMAP bypass" |
| $109D3B | Auto-scroll speeds, ±$40 $80 $100 $200 $300 $400 per frame (observed address) | Speed codes 06-11. Handlers at $109AB4 (horizontal) and $109B78 (vertical). Pointer tables at $109CBB/$109CFB [CONFIRMED] | CONTRACT §12b "The rate ladder", "The twelve auto-scroll rates" |
| $109A65 | `STX $13D5` inside LM's code (observed address) | Clears vanilla's "layer 3 does not move" flag, so the per-frame scroll site is reached [MEASURED] | CONTRACT §12b "Two things the emulator could not see" |
| $05F200 | Bits 6-7 = Layer 3 Option (the vanilla byte, read into $1BE3 at $05D928). LM mirrors it into the bypass record at +3 bits 5-6 | 0 = blank and 3 = tileset-specific [CONFIRMED]. 1 = tides and 2 = low tide [INFERRED from the dialog's order] | CONTRACT §12b "The Layer 3 Options field" |

The tilemap bypass record fields are: w0 bit 13 = enable, w1 bits 0-11 = LT3 file, bits 12-13 = size, bits 14-15 = destination [CONFIRMED] (CONTRACT §12b). The same w1 bits are read as the AN1 slot by the GFX loader. The notes leave this unresolved; see "Contradictions" below.

## Sprites

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $05D8F5 | `LDA #$07 : STA $D0` becomes JSL $0EF300 | Sprite data bank from the per-level bank table at $0EF100 (`PHB : PHK : PLB : LDY $0E : LDA table,Y : STA $D0`). After LM moves a level's sprites, reading bank $07 gives stale data [CONFIRMED] | CONTRACT §11; LM_PARITY §2 "Sprite bank relocation" |
| $05D8FC | AND #$3F becomes AND #$1F | Narrows the sprite-memory field so header bit 5 can flag LM's extended sprite list (`FF nn` band markers, `FF FE` end) [CONFIRMED] | CONTRACT §11 "Extended list" |
| $02A846 | `INY INY INX` becomes a JML into LM code | Sprite record advance. Record length comes from the size table, $400 bytes indexed by `(extra bits << 8) | number`, 3 for vanilla sprites [CONFIRMED] | CONTRACT §11 "LM/PIXI extra bytes" |
| $02A67A | Hook into LM's sprite-list loader (block C) | Per-screen index cache, spawn-range window, extended list and extra bytes. Observed JML targets on this group include $1090A3, $109198, $10917B and $108F2D [CONFIRMED] | LM_PARITY §2 "Sprite stream" |
| $02A826 | Hook into block C | As $02A67A [CONFIRMED] | LM_PARITY §2 "Sprite stream" |
| $02A95B | JML $108F70 (observed) | As $02A67A [CONFIRMED] | LM_PARITY §2 "Sprite stream" |
| $02ABF3 | Operand $7F (vanilla clears 64 bytes) | Level-load clear of the sprite load table $1938 covers 128 bytes [MEASURED] | PIXI_PORT §5 "255 sprites a level" |

Tables and data:

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $0EF100 | One bank byte per level | Sprite data bank for $05D8F5's hook. Level imports write their entry [CONFIRMED] | CONTRACT §11; LM_PARITY §2b |
| $0EF30C | 24-bit pointer to the sprite size table, with $42 at $0EF30F meaning enabled (help: PC $7750C/$7750F, headered) | Custom sprite list sizes. Without a registration the value is $FF [CONFIRMED], [LM-DOC] | CONTRACT §11 "Registration" |
| $0FFFE0 | Bit 0 cleared means a level may hold 255 sprites (help: PC $801E0, headered) | Per-level sprite limit flag. PIXI ROMs have $FE here and LM-saved hacks without PIXI have $FF [LM-DOC], [MEASURED] | PIXI_PORT §5 "255 sprites a level" |

## ExAnimation

The level ExAnimation engine. LM's footprint in a controlled save is exactly these hooks plus the engine blocks, which are relocated per ROM (CONTRACT §12g). The record format is in CONTRACT §12e "SLOT FORMAT PINNED" and in EXANIMATION.

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $00A390 | `REP #$20 : LDY #$80 : STY $2115` becomes JSL to the engine's NMI part ($138170 observed), plus RTS | Does the animated-tile VRAM DMA itself: the vanilla tiles from the $0D7x parameters, then the eight resolved slot records at $7FC0C0. Also runs the colour-$64 glint, which a per-level flag at $7FC00A bit 7 can turn off [CONFIRMED] | CONTRACT §12d "ENGINE LOCATED", §12g |
| $0583AD | Hook to the engine's setup | Per-level setup. It reads the level's record from the per-level table (indexed by [$FE]−1) and the global list from two baked immediates [CONFIRMED] | CONTRACT §12g, §12e, §12f |
| $0095B6 | JSL $05BB39 redirected to the engine's per-frame processor | Resolves slot frames each tick [CONFIRMED] | CONTRACT §12g |
| $00A2A6 | As $0095B6 | As $0095B6 [CONFIRMED] | CONTRACT §12g |
| $00A5FE | As $0095B6 | As $0095B6 [CONFIRMED] | CONTRACT §12g |
| $00A5E1 | Hook to an MVN helper | Engine helper [CONFIRMED] | CONTRACT §12g |
| $008A4E | Hook to a clear helper | Clears the $7FC0C0 DMA records [CONFIRMED] | CONTRACT §12g |

Tables and data:

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $03BCC0 | Zeroed on install. Then 4 × 24-bit pointers (FF FF FF = absent) | Uncompressed ExAnimation source files ExGFX 60-63, which the engine DMAs straight from ROM. A list picks one by its record's first-word high byte [CONFIRMED] | CONTRACT §12f "ALT-EXGFX FILES 60-63"; EXANIMATION §2 |

The per-level table holds 3 bytes per level, with FF 00 00 meaning none. Its base is per ROM and is found through the engine's setup code. The global list's address is baked into the setup as two immediates [CONFIRMED] (CONTRACT §12e, §12f). The vanilla dispatch at $05BB39 itself is untouched [CONFIRMED] (CONTRACT §12d).

## Overworld

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $00A140 | `STA $20 : SEP #$20` becomes JSL $0FFAB0 | Submap GFX: a 35-byte stub with X = submap×2 that sets $7FC006/8 to the submap's record (entry $200 + submap of the bypass table) and $7FC009 = $42 (overworld; $41 means a level). LM's dialog reads the record address from the stub's ADC #imm at +9/+10 and LDA #imm at +18. Installed with step A [MEASURED] | OVERWORLD §4; CONTRACT §12b "Step A", §12g |
| $00A149 | JSL $00BA28 NOPped (the LDY #$14 at $00A147 stays) | GFX14 now comes from the record's AN2 slot [MEASURED] | OVERWORLD §4 |
| $00AD32 | `STY $00 : LDA $1931` becomes a JSL, with RTS at $00AD36 | LM's overworld palettes: one MVN copies a whole $200-byte palette per submap (and a second set once the special world is passed) into the CGRAM mirror, so the vanilla loads never run. Installed on the first overworld palette save [MEASURED] | OVERWORLD §4 "LM's overworld palettes" |
| $048000 | Offset table rescaled to 32 bytes per tile | The overworld's animated-tile reader, in 4bpp mode [CONFIRMED] | CONTRACT §6a-13; LM_PARITY §2 "4bpp graphics" |
| $0480BD | $08 becomes $10 | The expander copies 16 word rows (4bpp) [CONFIRMED] | CONTRACT §6a-13; LM_PARITY §2 "4bpp graphics" |
| $0480D0 | RTS | Drops the expander's plane-2 loop [CONFIRMED] | CONTRACT §6a-13; LM_PARITY §2 "4bpp graphics" |
| $04F2B8 | 21 two-byte operands in $04F2B8-$04F3D0 moved from $7EB9xx/$7EBAxx to $7FC5xx/$7FC6xx | Moves the OW sprite tables clear of a 4bpp file's overrun of the $7EAD00 buffer (to $7EBCFF) [CONFIRMED] | CONTRACT §6a-13; LM_PARITY §2 "4bpp graphics" |
| $048086 | JSL blob : RTS over five displaced bytes | Overworld ExAnimation (a separate hack since LM 2.40): per-load setup, indexed by the submap number itself [MEASURED] | EXANIMATION §10; CONTRACT §12g |
| $0480E0 | JSL blob : RTS | Overworld ExAnimation per-frame tick (OW_Tile_Animation) [MEASURED] | EXANIMATION §10 |
| $00A4E3 | JSL blob : RTS | Overworld ExAnimation animated-tile VRAM upload [MEASURED] | EXANIMATION §10 |
| $048102 | Frame counter read $13 becomes $14 | Left in what remains of OW_Tile_Animation [MEASURED] | EXANIMATION §10 |
| $04810D | As $048102 | As $048102 [MEASURED] | EXANIMATION §10 |
| $04813B | As $048102 | As $048102 [MEASURED] | EXANIMATION §10 |
| $04D7F2 | Block rewritten. Two LZ2 blobs are decompressed with vanilla $00B8DE: translevel per tile to $7ED000 ($1000 bytes), and layer-1 high bytes to $7FC800 | "Level number to use for this tile" replaces vanilla's scan order. 16-bit layer-1 tiles [CONFIRMED] | OVERWORLD §11 |
| $04E9F1 | JSL to LM's silent-event code (observed $129353) | Silent events with 16-bit tiles from LM's own tables. Its four long operands are the event index, flags, tile and destination [CONFIRMED] | OVERWORLD §11 |
| $048509 | JSL to a hook. The entry count is the LDX #$n×2 at hook+$11 | Star/pipe warps (the table stays in place at $048431) [CONFIRMED] | OVERWORLD §11 |
| $04EEC3 | JSL to a hook that indexes the level-tile flags table (operand at $04EEC8) by LM's translevel | Level-tile flags ($04E587 relocated) [CONFIRMED] | OVERWORLD §11 |
| $04DCA5 | `INC $0F : LDA $0F` replaced | Replays passed events' silent steps from LM's tables in the load loop. Not fully traced [CONFIRMED] | OVERWORLD §11 |
| $04E5F1 | Hook to $05DCB0 | Exit/event plumbing. Not traced on the overworld side [CONFIRMED] | LM_PARITY §2 "The render half"; OVERWORLD §11 |
| $049882 | JMP $04FFB1 | Level-name rewrite, seen on one hack only. Not traced | OVERWORLD §11 |
| $049AC2 | JMP $04FFB1 | As $049882 | OVERWORLD §11 |
| $04DBB9 | Hooked | Not yet traced | OVERWORLD §11 |
| $04E6C5 | Hooked | Not yet traced | OVERWORLD §11 |
| $04EDDD | Hooked | Not yet traced | OVERWORLD §11 |
| $04EEF1 | Hooked | Not yet traced | OVERWORLD §11 |
| $009F0E | New-game flags loop replaced by a table at $05DDA0 + translevel | Eight initial level-tile flags [INFERRED, unverified against an LM-saved ROM] | OVERWORLD §11 "Modify Level Tile Settings" |

Overworld data LM relocates. Each table moves, and the vanilla loader's operands are repointed. The vanilla bytes are left behind as stale copies [CONFIRMED] (OVERWORLD §11 "Lunar Magic's overworld hooks"):

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $04DC71 | LDA #addr operand, with the bank at $04DC78 shared by both streams | Layer-2 tile stream (vanilla $04A533) | OVERWORLD §11 |
| $04DC8C | LDA #addr operand | Layer-2 property stream (vanilla $04C02B), packed after the tile stream | OVERWORLD §11 |
| $04DCBB | LDX #addr operand, with the bank at $04DCBF (also read at $04DC3B) | Layer-1 Map16 definitions (vanilla $05D000, $C1 tiles), expanded to $200 tiles | OVERWORLD §11 |
| $04E49E | Long operands at $04E49E/$04E4A3 and $04E708/$04E70F | Standard event steps (vanilla $04DD8D) | OVERWORLD §11 |
| $04E4AF | Bank LDA at $04E4AF, address LDA at $04E4BA | Event piece tiles (vanilla $0C8000) | OVERWORLD §11 |
| $04DD44 | LDY #addr, with the bank at $04DD49 | Event piece properties (vanilla $0C8D00) | OVERWORLD §11 |
| $04E67C | Long operands at $04E67C and $04E69C | Destroy events (vanilla $04E5D6/$04E5B6…) | OVERWORLD §11 |
| $04DA73 | Long operands at $04DA73, $04EC8B and $04ED96 | Reveal list (vanilla $04D85D) | OVERWORLD §11 |

Edited in place, at their vanilla addresses: base events $05D608, exit directions $04D678, exit tiles $049964…, Koopa teleports $048E49, OW sprites $04F625, music $048D8A and no-auto-move $04906C. LM's overworld save reads a packed exit-direction block of its own instead of $04D678 [CONFIRMED] (OVERWORLD §11).

## Screen exits and entrances

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $0DA531 | AND #$01 becomes AND #$0F | Keeps the whole X nibble of the screen-exit byte in $19D8,X, which has no other vanilla reader [CONFIRMED] | CONTRACT §9d-2 |
| $05D7CE | `BEQ +2 : LDA #$01` becomes JSL $05DC50 (4 bytes, exact fit) | Destination level bit 8. $19D8,X bit 2 = extended exit, bit 0 = bit 8, bit 1 = secondary table, bit 3 = entrance action, bits 4-7 = more high bits. The fallback is "is this a main level" ($13BF ≥ $25) instead of vanilla's submap test [CONFIRMED] | CONTRACT §9d-2; LM_PARITY §1 |
| $05D97D | `LSR : STA $192A` becomes JSL $05DD30 | Main entrance "method 2": the index nibbles become 16px steps, plus a flags byte ($05DE00) and a Y-high byte ($06FC00) per level [CONFIRMED] | CONTRACT §9d-3; LM_PARITY §2 "Entrance positions" |
| $05D833 | `LDA $FE00,Y : AND #$07 : STA $192A` becomes `LDA $FE00,Y : TYX : JSL $03BCE0` | Secondary entrance method 2, plus destination bit 8 from $05FE00 bit 3 (replacing vanilla's submap guess) [CONFIRMED] | CONTRACT §9d-3; LM_PARITY §2 "Entrance positions" |
| $05DC80 | New code: `LDA $05FE00,X : RTL`, then two `LDA long,X : RTL` readers at $05DC85/$05DC8A | Readers for the secondary tables and LM's two extension tables (Y high; FG/BG and "exit to overworld"). The extension tables are per ROM [CONFIRMED] | LM_PARITY §2 "Entrance positions" |
| $05D9C3 | STA $13CD becomes LDA $13CD | $13CD becomes LM's FG/BG byte, not the midway screen [CONFIRMED] | CONTRACT §9d-3; LM_PARITY §2 "Entrance positions" |
| $05D9E7 | `STA $95 : JMP $05DA17` becomes `STA $01 : NOP NOP NOP` | Midway screen goes through the shared tail [CONFIRMED] | LM_PARITY §2 "Entrance positions" |
| $05D9E3 | LSR ×4 becomes JSL to the separate-midway blob (per ROM, $C4 bytes in its own RATS block) | "Separate midway settings": the midway gets its own position, FG/BG and Y high from four per-level tables. Installed on demand [CONFIRMED] | CONTRACT §9d-3; LM_PARITY §2 "Separate midway settings" |
| $05D979 | `AND #$38 : LSR : LSR` becomes JSL blob+$A0 | Exits flagged for the midway arrive at it. Installed on demand [CONFIRMED] | LM_PARITY §2 "Separate midway settings" |
| $05D9DA | JML $14EE49 (observed on some hacks) | Routes the midway branch through a block keyed on RAM $7FB426. A different feature, not mapped | LM_PARITY §2 "LM can RELOCATE" |
| $05D7E2 | Exit plumbing reader | Part of the exit/secondary plumbing. Not described further [CONFIRMED] | LM_PARITY §2 "The render half" |
| $05D7EA | Exit plumbing reader | As $05D7E2 [CONFIRMED] | LM_PARITY §2 "The render half" |
| $05D81C | Exit plumbing reader | As $05D7E2 [CONFIRMED] | LM_PARITY §2 "The render half" |
| $05DBC2 | Hook to $03BB00 | Exit/secondary plumbing [CONFIRMED] | LM_PARITY §2 "The render half" |
| $01E762 | Hook to $03BCA0 | Overworld exit [CONFIRMED] | LM_PARITY §2 "The render half" |
| $0DA536 | Edited | Exit plumbing. Not described further [CONFIRMED] | LM_PARITY §2 "The render half" |
| $0DE191 | Operand of LM's reader repointed (also $0DE198, $0DE19F and $05DC81) | LM can copy the four vanilla secondary-entrance tables ($05F800/$05FA00/$05FC00/$05FE00) into bank $10 and repoint their readers. After that, the vanilla tables are stale. Not every save does it [MEASURED] | CONTRACT §12g; LM_PARITY §2 "LM can RELOCATE" |

Tables and data:

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $05DE00 | Zeroed, then one flags byte per level | Main entrance: bit 5 = method 2, bit 3 = X bit 7, bit 4 = X bit 8, bits 6-7 go to $192A (slippery/water) [CONFIRMED] | LM_PARITY §2 "Entrance positions"; CONTRACT §11 |
| $06FC00 | Zeroed, then one byte per level | Main entrance Y high (bits 0-5). Bit 6 = FG offset negative [CONFIRMED] | LM_PARITY §2 "Entrance positions", "Level entry" |
| $06FE00 | $1A per level by default | Goes to $13CD. Bit 7 = FG/BG relative to player, bit 6 = face left, bits 0-5 = BG height [CONFIRMED] | LM_PARITY §2 "Entrance positions"; CONTRACT §11 |
| $05FE00 | Spare bits used. LM sets bit 3 on every record $100-$1FF | Secondary entrance: bit 3 = destination bit 8, bits 4-5 = X bits 7-8, bit 6 = method 2, bit 7 to $192A [CONFIRMED] | LM_PARITY §2 "Entrance positions"; CONTRACT §9d-3 |
| $05D718 | 20 bytes initialised (with $05D728) | LM's extra FG/BG init entries [CONFIRMED] | LM_PARITY §2 "The render half", "Tables LM initialises" |
| $05FACE | Initialised (also $05FCCE, $05FECE) | Tails of the secondary entrance tables [CONFIRMED] | LM_PARITY §2 "Tables LM initialises" |

LM checks the separate-midway tables' block shape. It expects a STAR tag 8 bytes ahead of the four $200 tables, sized $800. Anything else makes every level save fail with "Existing data format or size not recognized! Midway entrance data" [MEASURED] (LM_PARITY §2 "The tables need a RATS block of their OWN").

## Other entry points and fixed bytes

| Vanilla address | What LM puts there | What it's for | Source |
|---|---|---|---|
| $03BCDC | New code (with $03BB00, $03BCA0 and $03FDFF, 513 bytes): 196 bytes, `JML $1092AD`, `JSL $05DC80` | LM documents `JSL $03BCDC` as the screen-exit "which screen is Mario on" calculation [LM-DOC]. The rest of bank 03's new code is overworld/level-entry support [INFERRED] | CONTRACT §8; LM_PARITY §2 "Bank 03" |
| $0DF100 | Must stay $FF | LM's level-access flag. Any other value makes every LM operation fail with "Access Denied!". LM's own bank-$0D code stops short of it [MEASURED] | LUNAR_MAGIC "Measured facts"; CONTRACT §0 |
| $0FEFCB | About 371-373 bytes of bookkeeping (also listed as $0FEFCD, $0FEFDB, $0FEFE9) | LM metadata. Meaning unknown | LM_PARITY §2 "Tables LM initialises", "-ImportExGFX"; CONTRACT §12g |
| $0FFFE6 | Initialised ($0FFFE6/$0FFFE7) | LM metadata/size byte. Meaning unknown | LM_PARITY §2 "Tables LM initialises", "-ImportExGFX" |
| $0EFD50 | Initialised | Listed among tables LM initialises. Elsewhere it is the $200-stride half of $0EFD00's VRAM column code | LM_PARITY §2 "Tables LM initialises", "The render half" |

## Installed on demand

A level save installs the baseline set: the level and height engines, the render block and VRAM patch, method-2 entrances, the exit bit 8, the sprite bank and loader hooks, and the Map16 lookup (LM_PARITY §2). The other hacks go in when a feature is first used:

| Feature | When LM installs it | What lands | Source |
|---|---|---|---|
| Super GFX Bypass, Layer 3 GFX bypass ("step A") | As soon as the dialog is opened, per LM's help. In a controlled save, ticking the bypass and saving | The $00AA50/$00AA6C/$0583B8/$009471/$00A140/$049DFE hooks, the five bank-$0D table entries and the bank-$0F blocks [LM-DOC], [CONFIRMED] | CONTRACT §0, §12b "Step A" |
| Layer 3 tilemap bypass ("step B") | Ticking "Enable bypass of standard Layer 3 tilemap" | $00A01F, $00A153, $0194B6 and $05C40C, plus three RATS blocks in bank $10 [CONFIRMED] | CONTRACT §12b "Step B" |
| ExAnimation | As soon as the dialog is opened, per LM's help | $00A390, $0583AD, $0095B6/$00A2A6/$00A5FE, $00A5E1, $008A4E, $03BCC0 zeroed [LM-DOC], [CONFIRMED] | CONTRACT §0, §12g |
| VRAM patch, FastROM | On the next level save, per LM's help | $0081E2 for the VRAM patch [LM-DOC] | CONTRACT §0; LM_PARITY §2 "Not in a plain save" |
| Palette engine and 4bpp mode | Seen arriving as one bundle on an ExGFX import | $0095E9, $00A5BF, $0093F7, $00A830/$03DDC9, $00AA8C/$00AA90, $00AB0B, $00B895, $00A149 [MEASURED] | LM_PARITY §2 "-ImportExGFX"; CONTRACT §12g |
| Acts-like core and custom-block dispatch | Map16 editor save (F9) | $06F5E4 core, the trampolines and contact slots, the $06F65C marker, $04DCFA, $058A65/$058B45/$058C33/$058D2A, and ladder ranges. It is staged: what one save writes depends on what is already there [MEASURED] | CONTRACT §12g; LM_PARITY §2 "Map16 F9" |
| Separate midway settings | When a level uses the feature (not in a plain save) | $05D9E3, $05D979, the $C4-byte blob and four tables [CONFIRMED] | LM_PARITY §2 "Separate midway settings" |
| Overworld suite | First overworld save (55 runs: bank 03/04/05 hooks, three bank-$10 blocks) | The overworld rows above. The overworld palette hook comes on the first overworld palette save [MEASURED] | LM_PARITY §2 "The overworld-ExAnimation settings"; OVERWORLD §4 |
| Overworld ExAnimation | Using the overworld ExAnimation dialog | $048086, $0480E0, $00A4E3, the $13→$14 reads, $03BCC0 zeroed [MEASURED] | EXANIMATION §10 |

Two cautions from LM's help that the notes repeat. LM honours any valid RATS tag, including ones it did not write, and it warns about nested RATS tags. And if LM does not recognise the version of an installed patch, it may silently grey out its options instead of raising an error [LM-DOC] (CONTRACT §0).

## Contradictions in the notes

Where the notes disagree, this page follows the later or explicitly corrected reading:

1. Extended Map16 location. CONTRACT §7a reads the definitions through a pointer at $02C2E1 (and $049371), in a linear block. §7a-rev shows that this holds on only one ROM, and that the real contract is the ladder at $06F540 reached from $00C17A. Followed: §7a-rev. CONTRACT §7's early reading of $06F5D0 as "remap through $118000, then JML $00F545" is also superseded. $06F5D0 is the ladder wrapper, and acts-like is LM's core at $06F617.
2. Bypass record layout. §7c puts the record 8 bytes early and calls w12-w15 a "constant" tail. §7d moves it, and §12b shows that w12-w15 are LG4-LG1 (layer-3 GFX). Followed: §7d and §12b.
3. ExAnimation dispatch table. §12d's "handler table at ~$10F32D" was a misread. §12f shows it is the global record's RATS tag and the record itself. §12e's tentative slot fields and its $7D00-RAM frame reading are superseded by "SLOT FORMAT PINNED" and by §12f (the global list DMAs from ROM alt files). EXANIMATION §2 also corrects an earlier RAM reading of one slot's frames to file offsets.
4. Layer-3 advanced path. An earlier reading said the option comes from $7FC01A bits 0-1. CONTRACT §12b's "CORRECTED" note says those bits are the initial-X index and the option answer is unchanged. Followed: corrected.
5. Object 29. It was once read as BG pages. CONTRACT §9d corrects it to FG pages 40-7F. Followed: §9d.
6. Entrance byte $06FE00 bit 6. CONTRACT §11 says it is "face left" and that "BG relative to FG only" was a mis-read. LM_PARITY §2 "Level entry" still calls $13CD bit 6 "BG relative to FG only". Followed: CONTRACT §11, the explicit correction.
7. Who writes $010B. CONTRACT §11 says the $05D8F5 sprite-bank stub also stores the level number to $010B. LM_PARITY §2 splits this into two routines, with $05D8E2 → $0EF550 doing the level word. Followed: LM_PARITY (later, and byte-compared).
8. First-load palette site. CONTRACT §12g gives $05809E → $1FAFF1, and LM_PARITY §2 "The render half" gives $0580A9 → $1FAFF1. These are different vanilla instructions (PHP versus STA $4D). Not resolved. The table lists $0580A9 and notes the other.
9. Custom palette "none" value. CONTRACT §7e says 000000 or FFFFFF means no custom palette. CONTRACT §12g measured that LM's $0EF583 treats only a zero pointer as "none". Followed: the later measurement.
10. Map16 marker and the extended-def block. A September (LM 3.33-era) note says that without the `LM 12 01` marker, LM leaves an existing extended-def block alone. Under LM 3.40, an F9 save frees the block with or without the marker. Followed: the 3.40 measurement (LM_PARITY §2 "Map16 F9 (LM 3.40)").
11. Record word w1. CONTRACT §7d/§12d read w1's low bits as the AN1 slot, and §12b's tilemap decode reads the same bits as the LT3 file. The notes say this is unresolved. Both readings are given above.
12. Overworld ExAnimation tile numbers. LM's help says overworld source numbers run $100 below the level dialog's. LM 3.40's dialog shows the RAM source at 600 in both. EXANIMATION §10 follows the dialog.
13. $06FA00. LM_PARITY lists it once as a 1536-byte $20 fill under "Map16 machinery", and once as "LM's extended layer-2 scroll byte" under "Level entry". Both readings are given above.
