# Lunar Magic's file formats

The formats Lunar Magic (LM) uses to move data in and out of a ROM, decoded against LM 3.40. Only `.map16` has a published spec, so everything here was measured from files LM itself produced: export from a ROM, then read the bytes.

| format | state of knowledge |
|---|---|
| shared palettes (`smw.pal`) | fully decoded: a flat copy of one ROM range |
| level palette (`.pal`) | fully decoded; LM accepts a file written by another tool and stores it exactly |
| `.map16` | spec'd by LM; its "Act As" section is a useful oracle for the acts-like table (see LM_PARITY §2 "Block behaviour") |
| `.mwl` (level) | container and most sections decoded; a few fields unidentified |

## Shared palettes — `smw.pal`

A flat copy of one ROM range, and nothing else:

```
$00B0A0 .. $00B881     0x7E2 bytes
```

Verified by exporting `smw.pal` with `-ExportSharedPalette` and comparing it byte for byte against the ROM at $00B0A0: equal for its whole length.

That range is the whole of SMW's shared palette data: back-area colours ($00B0A0), the BG/FG/sprite palette sets, the layer-3 colours, `MorePalettes`, through the last sprite row. Custom per-level palettes are NOT in it. LM says so, and they live with the level (CONTRACT §7e).

## A level's palette — `.pal`

256 colours, three bytes each, red first. This is YY-CHR's layout, 768 bytes. LM also offers TPL and its own MW3; `.pal` is the one every tile editor reads.

**Each 5-bit SNES channel is shifted left 3 and NOT bit-replicated**: `0x1D` goes out as `0xE8`, where a display conversion that replicates the high bits would give `0xEF`. Every byte in an LM-written file has its low three bits clear, which is the quick tell. A tool that wants exact round trips should encode from the raw BGR555 words, not from display RGB.

Import writes the level's LM custom palette (CONTRACT §7e). Writing it IS the "use a custom palette" setting, which is why LM notes that importing turns the setting on for you. Colour 0 of the file becomes the back-area colour.

Proven in both directions: LM's `-ImportCustomPalette` accepts a file written by another tool and stores it such that re-exporting differs in **0 of 768 bytes**.

Two slots never survive a round trip, and both are expected:

- **colour 0 of each row**: the shared transparent slot, stored as zero in the blob by design.
- **CGRAM `0x64`**: the global glint, which the NMI rewrites from $00B60C every four frames. Its value on screen is the glint's, not the custom palette's.

## A level — `.mwl`  [DECODED, PARTIAL]

Self-contained: "level layout, background tile map, sprite data, palette, secondary entrances, and a few other things". No graphics, no Map16, no shared palettes. Same container shape as `.map16`.

```
+0x00  "LM"                      2      (4C 4D)
+0x02  u16 LM version            0x0340 for 3.40
+0x04  u32 offset of section table   (0x40)
+0x08  u32 size of section table     (0x40 = 8 entries)
+0x0C  u32 flags                     (0)
+0x10  0x30-byte comment         LM's version and copyright string
+0x40  8 × { u32 offset, u32 size }
```

The eight sections tile the file exactly (last offset + size == file length). **Every section except [0] starts with an 8-byte header**, then its payload:

```
u32 0 · u24 the SNES address the data came from · u8 0
```

Confirmed by following those addresses back into the ROM: section [1]'s payload is byte-identical to the level's layer-1 stream at the address it names ($0688DD for level $105, which is what the layer-1 pointer table holds), and [3]'s to the sprite stream at $07C4CA.

| # | size (level $105) | what |
|---|---|---|
| 0 | 0x40 | level info, see below; no 8-byte header |
| 1 | 8 + 0x118 | layer 1 object stream |
| 2 | 8 + 0x800 | layer 2 / BG tile map (fixed size) |
| 3 | 8 + 0x68 | sprite stream |
| 4 | 8 + 0x202 | custom palette blob, the same 0x202 shape as CONTRACT §7e |
| 5 | 8 + 8 | unidentified (`CB 01 A9 08 0E 00 00 00` for $105) |
| 6 | 8 + 0 | unidentified, empty on every level sampled |
| 7 | 8 + 0x18 | unidentified, all zero on every level sampled |

Section 0, sampled across levels `001`, `024`, `0C5`, `100`, `104`, `105`, `106`:

```
+0x00  u16 level number          0x0105, 0x0106, 0x0024 …
+0x02  u16 A                     varies: 005B, 005B, 015B, 2007, 010B
+0x04  u16 B                     varies: 009A, 000A, 0009, 000A
+0x06  9 bytes zero
+0x0F  0x1A                      same on every level
+0x10  u16 0x2000                same on every level
+0x12  zero to 0x40
```

**Still unknown:** A and B in section 0 are per-level and their ROM source is not yet identified, and sections 5, 6 and 7 are unidentified. All of them can be answered the same way the rest was: change one thing in a level in LM, re-export, and diff the two `.mwl` files. Until then, a writer of `.mwl` files would be guessing those bytes.
