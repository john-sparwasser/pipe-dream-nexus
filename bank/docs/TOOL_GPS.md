# GPS

Gopher Popcorn Stew (GPS) is the standard custom block inserter for Super Mario World. It assembles each block's ASM with Asar, puts it in free space, and makes a chosen Map16 tile run that code whenever Mario or a sprite touches it. It also sets the tile's acts-like. This page describes GPS V1.4.5, with `main.asm` and the tool's `src.zip` (`main.cpp` plus Asar's DLL loader). GPS 1.4.5 ships Asar 1.91's DLL.

GPS's files carry no licence text, so this page describes behaviour and formats in its own words and quotes none of GPS's code. The findings come from GPS's documented formats, from its files, and from its observed output on LM-edited ROMs.

A clean-room reimplementation of the block driver and inserter exists in Pipe Dream.

## Files

| File | What it is |
|---|---|
| `list.txt` | The insertion list: Map16 tile (or range) → block `.asm`, with an optional acts-like. The shipped copy is empty apart from a comment |
| `blocks/` | One `.asm` file per block |
| `blocks/template.asm` | The block API contract: the header and one entry point per contact, each a bare `RTL` |
| `main.asm` | The block driver: the dispatch stubs, `block_execute` and the tables |
| `defines.asm` | The address map that blocks are written against. It is SA-1 aware, and it is the important one |
| `routines/` | The shared routine library: 27 routines covering Map16 changes, spawning, shattering and score |
| `src.zip` | The tool's source (`main.cpp`, about 30 KB) |
| `README.txt`, `Changes.txt` | The format and command-line docs |

## What GPS does, step by step

1. Reads `list.txt`. Each line maps a Map16 tile, a range (`R203-214`) or a rectangle to a block file, optionally with an acts-like after a colon (`200:0130 above.asm`).
2. Assembles each block with Asar. It runs one Asar patch per block file, so a hack with a couple of hundred block files takes seconds to insert.
3. Puts each routine from `routines/` that a block calls (as `%name()`) into free space once. Blocks get a macro that `JSL`s to it.
4. Writes the per-tile tables (`block_bank_byte`, `block_pointers_1`, `block_pointers_2`) and the contact stubs at $06F690. The driver is `main.asm`.
5. Sets each tile's acts-like.
6. On re-insertion, finds the previous run by its `"GPS_VeRsIoN"` marker and frees what that run claimed (RATS, Asar's `autoclean`) before claiming space again. Asar frees autocleaned space in its first pass, so a new insertion can reuse the old space.

Two tiles that list the same block file share one copy of its code at one address.

## Block IDs

- Custom block IDs run from `0x200` to `0x7FFF`, and acts-like must be below `0x8000`. The README only implies these bounds.
- IDs of `$4000` and above (Lunar Magic's FG pages 40-7F) use the second pointer table. Pages 40 and up need LM to have created them: GPS checks that $06F63C is not `FF`.

## The block format and API

A block begins with a one-byte header, followed by one three-byte `JMP` per contact type. Each entry point is a routine that ends in `RTL`. An entry whose `JMP` lands on a bare `RTL` handles nothing.

| Header | Meaning |
|---|---|
| `db $42` | A normal block: the ten standard contacts |
| `db $37` | A wall-run block: the ten standard contacts plus WallFeet and WallBody |

The entry points, in header order, are:

| # | Contact | Offset (`id*3+1`) |
|---|---|---|
| 0 | Mario below | `$01` |
| 1 | Mario above | `$04` |
| 2 | Mario side | `$07` |
| 3 | Sprite vertical | `$0A` |
| 4 | Sprite horizontal | `$0D` |
| 5 | Cape | `$10` |
| 6 | Fireball | `$13` |
| 7 | Mario top corner | `$16` |
| 8 | Mario body inside | `$19` |
| 9 | Mario head inside | `$1C` |
| 10 | WallFeet (`$37` only) | `$1F` |
| 11 | WallBody (`$37` only) | `$22` |

The order comes from GPS's documented header layout. The offsets are derived from it, because `db $xx` is followed by three-byte `JMP`s.

A block's first `print` statement serves as its description.

### Inputs a block can rely on

- The block's position is in `$98-$99` (Y) and `$9A-$9B` (X), in level coordinates. `$1933` is the layer being processed.
- `X` holds the value from `$15E9` (the current sprite slot), loaded by `block_execute` before it jumps.
- In a vertical level (`$5B` bit 0 set), the routines `get_map16` and `change_map16` swap `$99` and `$9B` internally. A `swap_XY` routine exists only to undo that swap. Check which convention a routine uses before trusting it.

## The driver: how a block is reached

GPS blocks run through Lunar Magic's custom-block contact handlers. GPS refuses a ROM that LM has not saved, because it reads LM's acts-like pointer at $06F624. It also repoints that pointer to its own table.

### The contact stubs

GPS writes twelve identical 16-byte stubs in $06F690-$06F7E0, one per contact type (Below, Above, Side, SpriteV, SpriteH, WallFeet, WallBody, ...). LM's dispatch calls into this range when Mario or a sprite touches a custom tile. Each stub:

1. loads `id*3+1`, the byte offset of that contact type's `JMP` in the block header;
2. does `JSL block_execute`.

The stubs only run on a ROM that carries LM's custom-block dispatch. On a base without it, nothing calls them, and blocks never fire [MEASURED].

### `block_execute`

1. Checks `block_bank_byte` for the tile. A value of 0 means no block is inserted there.
2. Fetches a 16-bit pointer from `block_pointers_1`. For IDs of `$4000` and up it uses `block_pointers_2-$8000` instead. The already-shifted index is negative for those IDs, and that negative value is itself the range test.
3. Adds the contact offset.
4. Runs `LDX $15E9`.
5. Jumps through `JML [$0000|!dp]` into the block.

### Wall-run

Contact offsets of `#$001E` and above (WallFeet and WallBody) are honoured only when the block's first byte is `$37`. That byte is the whole opt-in mechanism. Two extra hijacks support wall-run:

| Address | Hijack |
|---|---|
| $06F67B | `WallRun`, a `JML` into the driver |
| $06F717 | `FixSpriteH`, a `JML` into the driver |

## The on-ROM format and markers

- **The `"GPS_VeRsIoN"` marker.** GPS finds its own data in an already-patched ROM through this string. The table addresses and sizes are embedded after it.
  - Asm version 1 has no pages-40+ byte.
  - Asm version 2 and later carry that byte and both pointer tables.
  - One LM-edited hack examined used asm version 3 with the pages-40+ layout. It had 965 blocks over 229 code addresses, 606 of them on FG pages 40-7F.
- **Cross-check.** Following the `JSL` in the $06F690 stub leads to `block_execute`, whose operands name the same tables the marker gives.
- **The tables.**
  - `block_bank_byte` holds one bank byte per tile, where 0 means not inserted.
  - `block_pointers_1` holds the 16-bit pointers for IDs below `$4000`.
  - `block_pointers_2` holds those for IDs `$4000` and up.
- **The acts-like table pointer** at $06F624 is repointed by GPS. GPS writes the bank byte at $06F626 as a FastROM mirror (`$91`). LM's Map16 save normalises it to `$11`, which names the same table.
- **BTSD removal.** GPS can detect Blocktool Super Deluxe by scanning for the string "Blocktool Super Deluxe" and strip it, but only BTSD hack version `$3136`.

### What Lunar Magic does to a GPS insertion

The following comes from a controlled before/after test in LM 3.40 [MEASURED]. The test covered a level save, the 16x16 editor's F9, `-ImportLevel` and `-ImportAllMap16`.

- None of these saves touch GPS's bytes. The stubs at $06F690 and up, the two `JML` hijacks at $06F67B and $06F717, the marker, the tables and the block code are all byte-identical afterwards. The four acts-like sites still `JSL` to LM's trampolines.
- The two Map16 routes (F9 and `-ImportAllMap16`, which give identical diffs) upgrade the LM dispatch they find:
  - the dispatch marker goes from `LM 11 01` to `LM 12 01`;
  - the fourth trampoline, at $06F7A0, is rewritten to LM 3.40's 20-byte shape;
  - $06F626 is normalised from `$91` to `$11`.
- Blocks keep working through all four saves.

## SA-1 handling

`defines.asm` resolves SA-1 at assembly time, the same way UberASMTool does.

- `read1($00FFD5)==$23` detects SA-1.
- `$00FFD7==$0D` then picks `fullsa1rom` over `sa1rom`.
- The detection flips these defines:

| Define | LoROM | SA-1 |
|---|---|---|
| `!dp` | `$0000` | `$3000` |
| `!addr` | `$0000` | `$6000` |
| `!bank` | `$800000` | `$000000` |
| `!sprite_slots` | `$0C` | `$16` |

The `define_sprite_table` macro emits two aliases for each sprite table, a named one (`!sprite_status`) and a raw one (`!14C8`). That is why routines can be written with raw vanilla addresses and still be SA-1 correct. No SA-1 ROM has been checked against GPS's output here.

## Command line and build quirks

- **`-O2` is a documented crash risk.** It truncates the bank-byte table, so undefined block IDs end up with no bank byte, and they **crash if Mario touches them**.
- **`-O2` silently implies `-O1`.** The README does not say so.
- **`-O3` is accepted by the parser,** but it then errors as unimplemented.
- **The README is out of date on `-nw`.** The option was added in V1.4.5. It appears in the tool's own `-h` output but not in the README.
- **GPS works in the current directory.** It expects `main.asm`, `defines.asm`, `routines/`, `blocks/` and `list.txt` beside the executable and the Asar library.
- **`main.cpp` is portable.** Its Asar loader `dlopen`s `./libasar.dylib` on macOS, and it expects Asar API 303. It builds from `src.zip` against an Asar 1.9x shared library and runs on macOS. `main.cpp` is dated the day before the shipped `gps.exe`, and the two builds have not been byte-compared.
- **The ROM has to be ready.** GPS refuses a ROM Lunar Magic has not saved, so it will not insert into a vanilla ROM. Pages 40 and up need LM to have created them.
- **One Asar patch per block file.** Because each file is its own patch, macros and defines in one block file never leak into another [INFERRED].

## Sharp edges in the routine library

- `$185E` is used for different things in three routines.
- `move_spawn_above_block` does a `TAX` with no `PHX`, so it clobbers the caller's X. Its four sibling routines all preserve X.
- `rainbow_shatter_block` differs from `shatter_block` by exactly one omitted `LDA #$00`.
