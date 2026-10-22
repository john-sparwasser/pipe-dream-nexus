# ExAnimation: how Lunar Magic's animation system works

Sources: Lunar Magic's help on ExAnimation, the Super GFX Bypass and graphics formats [LM-DOC], restated here in plain words; controlled before/after saves in LM that install one slot at a time; several LM-edited ROMs; and LM's own engine run under emulation (CONTRACT §12d-f).

## 1. The model in one paragraph

An ExAnimation **slot** is a small program the game runs during vblank: every N frames, DMA *this many bytes* from *this source* into *this VRAM (or CGRAM) destination*, cycling through a list of **frames** (one source address per frame). There are **0x20 per-level slots** (stored per level) and **0x20 global slots** (one list, runs in every level). The Map16 tiles placed in a level never change; only the 8x8 graphics under them are rewritten. Everything LM's dialog asks for (type, trigger, frames, destination, source tile numbers) is a field of that program, and LM leaves the user to compute the operands.

## 2. Sources: where frame graphics come from

| LM tile range | Storage | What it is | How it gets there |
|---|---|---|---|
| `0x600-0x77F` | RAM $7E7D00 (AN1) | vanilla animated tiles, GFX33 | always loaded |
| `0x780-0x857` | RAM $7EAD00 (AN2) | **extended animated area**, 0xD8 tiles 4bpp | Super GFX Bypass slot **AN2** (bypass record word 0): a normal compressed GFX/ExGFX file, at most 0x1A00 bytes (0xD0 tiles) |
| `0x900-0xBE7` | RAM $7E2000 | Mario's GFX32 (berry frames live here) | always loaded |
| `0xC00-0xFFF` | **ROM**, uncompressed | ExGFX **60** | "Use alternate ExGFX file for source" |
| `0x1000-0x13FF` | ROM | ExGFX **61** | same |
| `0x1400-0x17FF` | ROM | ExGFX **62** | same |
| `0x1800-0x1BFF` | ROM | ExGFX **63** | same |

Files 60-63 are up to **32KB each (0x400 4bpp tiles)**, stored **uncompressed** in a RATS block, and the engine DMAs frames **straight from ROM** (seen under emulation of LM's engine: the DMA sources are ROM addresses inside the file's RATS block). Constraints from LM:

- The alt-file flag is **per slot**, but the **file choice is one per level** (per-level list) plus **one for the global list**. So at most one of 60-63 serves a level's list, one serves the global list, and there are four files in all to choose from.
- RAM sources (AN1/AN2/Mario) and the ROM alt file can be mixed across slots in one list; the flag is per slot (dest word bit 15). Earlier readings took one global slot's frames as RAM tiles `0x680/0x700/0x780`; that was a misparse, and those values are file offsets `0x600..0x780` into the alt file.
- Within one frame the N tiles of a slot must be **consecutive in the source**: the type says how many (`N 8x8s: line`), the frame word says where the run starts.

**ROM side [CONFIRMED]:** the four file pointers are a fixed 4x3-byte table at **$03BCC0** (files 60, 61, 62, 63; `FF FF FF` = absent; vanilla is all FF; LM zeroes it when it installs the ExAnimation ASM). On an LM-edited ROM the pointer names the file's data directly, preceded by its `STAR` tag, and the data is the ExGFX60.bin bytes verbatim. A list picks its file through the **high byte of its record's first word** (index 0-3 into that table, stored to $7FC013/$7FC014); a global record starting `19 00` is 25 slots using file 60.

## 3. Destinations

VRAM 8x8 tiles `0x000-0x2FF` (layer 1/2 graphics, the FG/BG pages), `0x400-0x5FF` (sprite graphics), `0x1C00-0x1DFF` (layer 3), or a palette colour index (`0x00-0xFF`) for palette types; the advanced option is a raw VRAM word. The level then builds Map16 tiles out of the destination 8x8s exactly as with any other tile; that is the only link between the animation and the level.

Encoding: the record's dest word is the raw VRAM word for every range:

- layer 1/2: tile x $10 (BG12NBA = 0)
- sprite: $6000 + (tile - $400) x $10 (OBSEL = 3)
- layer 3: $4000 + (tile - $1C00) x 8 (BG34NBA = 4; a 2bpp tile is 8 words)

These are vanilla's CHR bases, which LM keeps; the engine passes the word to VMADD unchanged (verified against the running engine). All three ranges stay below $8000, so bit 15 stays free for the alt-file flag.

## 4. Slot types (what one slot can move per frame)

- `1..0x20 8x8s: line`: N consecutive tiles to N consecutive destination tiles. The workhorse; `4 8x8s: line` plus a Map16 tile pointing at the 4 dest tiles gives an animated 16x16.
- `2 8x8s: stacked`, `4 8x8s: 16x16`, `8 8x8s: 32x16`: the same, with the destination arranged as a block (top row then bottom row). The source is still a line. Slightly more CPU than `line`.
- `1 8x8 2bpp`: layer 3.
- Palette family: `Palette` (N colours from frame data), `+Working`, `+Working stop on fade`, `Back area colour`, `Rotate right/left` (with or without reverse on trigger). Frames are colours or a file offset to a colour run; "Colors" is the count.

## 5. Triggers

`None` (continuous), `POW`, `Silver POW`, `ON/OFF`, `Have Star`, `Timer<100` (with or without one shot), `≥5 Yoshi coins` (with or without one shot), `Precision timer palette rotate`, `Manual 0-F` (frame byte at $7FC070+n, set by custom blocks), `Custom 0-F` (bit flags), `One shot 0-F`. Triggered types double the frame list: the first half is untriggered, the second half triggered. The per-level "Trigger Init" sets manual/custom initial states on level load.

## 6. Timing and budget

- The base rate is 7.5 fps: the game spreads animation over 8 consecutive frames. Slot *k* runs on game frame *k mod 8*; slots `k, k+8, k+16, k+24` run on the **same** frame (and the global list's on the same frames as the level's). So per game frame, 4 level slots and 4 global slots run.
- Faster animation means the same destination in slots 4 apart (15 fps: 0 and 4; 30 fps: 0, 2, 4, 6; 60 fps: 0-7).
- Vblank is the hard limit: total DMA bytes per game frame across the up to 8 slots that run then. LM's own test [LM-DOC]: 0x40 slots of `4 8x8s: line` fit with a couple of scanlines to spare on a layer-2-image level. One 4bpp tile is 0x20 bytes.
- Frame values are readable at $7FC080 + slot (level) and $7FC080 + 0x20 + slot (global), for custom blocks.

## 7. The record format

Decoded and pinned by a series of controlled saves in LM, one change each (CONTRACT §12e "SLOT FORMAT PINNED"). Both lists, level and global, use the same record:

- a header: slot count, alt-file index (high byte of the first word, §2), masks and a selector
- an offset table, one entry per slot
- per slot: type, trigger, frames - 1, dest word (bit 15 = alt file, §3), then the frame words (twice as many for stateful triggers, §5)

The per-slot rate and phase are not in the record: they come from the engine's scheduling by slot number (§6). An LM-edited ROM's 13 global slots decode under this format and agree with the timeline the emulated engine produces.

## 8. The engine LM installs

On an LM save that first adds a slot, LM installs its engine as one blob (observed at $108640, 0xC30 bytes) with seven hooks into the game, and zeroes the alt-file table at $03BCC0. Run under emulation, that engine resolves a slot written to the record format of §7. A ROM with records written this way opens in LM and shows the same slots in LM's own dialog.

## 9. How sure the format is

- Types, triggers, list doubling, palette colour count, alt-file flag and slot placement each rest on a controlled save [MEASURED].
- The line-code to tile-count table is read off LM's own engine [CONFIRMED].
- The palette variants 14-17 and 19-1B and triggers 05-0F rest on the order of LM's dialog lists rather than on a save [INFERRED].

## 10. The overworld's animations: Lunar Magic's second hack

The overworld does not use the engine §1-§9 describe. Lunar Magic 2.40 added a SEPARATE ASM hack for it, "based on the same system as the one for levels" [LM-DOC]: its own blob, its own record table, its own global list, its own hooks. A submap's list is edited in LM's *Overworld > Edit Submap ExAnimated Frames* dialog. Settled by installing slots through that dialog and diffing; every number below was measured, none inferred [MEASURED].

**The table, and the index.** Seven entries of three bytes, `FF 00 00` = that submap has no list, indexed by **the submap number itself**: 0 the main map, 1-6 the six others in LM's dialog order (Yoshi's Island, Vanilla Dome, Forest of Illusion, Bowser's Valley, Special World, Star Road). Two ROMs that differ only in which submap holds one slot move the pointer from entry 1 to entry 4, and the hack's own setup agrees:

```
+0x000  SEP #$30 : LDX $0DB3 : LDY $1F11,X     ; the submap the current player stands on
+0x01A  STY $03                                 ; ...kept in $03
+0x0CF  LDA $03 : ASL : ADC $03 : TAX           ; X = 3 * submap, no "- 1"
+0x0D5  LDA.L table+1,X                         ; operands +0x0D6 and +0x0E1 name
+0x0E0  LDA.L table,X                           ; the table
```

That missing `- 1` is the whole difference from the level engine's `[$FE] - 1` (CONTRACT §12e). The record itself is byte-identical to a level's (§7); only the table differs. The table can be found through that multiply, anchored on the `LDA #$0010 : TSB $C00A` at `+0x0C9` just ahead of it, which keeps the search from matching the level engine's own fetch.

**What else the hack has.** A second table of seven bytes, one flags byte per submap (LM's *Edit Animation Settings* dialog), OR'd into $7FC00A by the setup (`+0x04A`). Its own global list, as two baked immediates (`+0x57` bank word, `+0x61` low 16 bits, zero = none), exactly as the level engine bakes its own.

**The hooks**, all three on the overworld's own paths, each a `JSL blob : RTS` over five displaced bytes:

- $048086, the per-load setup (the overworld reaches it through `JSR $048086` at $048EEB)
- $0480E0, `OW_Tile_Animation`, the per-frame tick
- $00A4E3, the animated-tile VRAM upload

LM also moves three reads of the frame counter `$13` to `$14` in what is left of `OW_Tile_Animation` ($048102, $04810D, $04813B), and zeroes $03BCC0-$03BCCF as it does for the level engine. None of these is a level-engine hook site, so LM installs the overworld hack into a ROM that already carries a level engine and leaves that engine alone.

**The blob.** LM's overworld blob is 0xC20 bytes (observed at $10EE94). It relocates cleanly: a second install of the same hack landed 0x148 bytes further on, and re-pointing the first copy by that delta reproduces the second **byte for byte**. All 266 differing bytes are 12 in-bank 16-bit operands, the 108-word handler table at `+0xB3B`, and 13 long operands (10 inside the blob, 3 naming the two tables). The blob's only `PLB` sites load `$7F`, not its own bank, so it can move across banks as well as within one.

**Source tile numbers.** The overworld dialog's RAM source is the overworld's own animated-tile buffer $7EAD00, not the level's $7E7D00, and its alternate files start at 0x700 rather than 0xC00, so the same frame word means a different tile number here. Read off LM 3.40's dialog, which is the only reliable direction: it CLAMPS what is typed into a range (everything from 0x500 to 0x600 stored `$AD00`) but displays what is stored, so `$AD00` shows as 600 and an alternate file's offset 0 shows as 700. LM's help says the overworld's numbers run 0x100 under the level dialog's; 3.40 shows the RAM source at the same 600 in both, so the help holds only where the dialog agrees with it.

**Other documented differences** [LM-DOC]: triggers 8-F become **Event Manual 8-F** (they fire on an overworld event number taken from the Manual frame of the same number, up to 8 per submap, set with *Trigger Init*); the four *Stop on Fade* triggers are marked **[Do Not Use]**; the palette *Back Area Colour* type must not be used (the overworld uses it for menus and the exit-tile transition); and $7FC004 is unavailable.

**What is not checked.** LM 3.40 opens a list written into this table and shows the slot, and a ROM carrying the hack boots and runs frame-for-frame identically to one without it in an emulator. The overworld tick itself has not been run under a CPU emulator (it waits on hardware such emulators do not model, on LM's own install as well), and watching a submap's animation play would need a save state walked onto the map.
