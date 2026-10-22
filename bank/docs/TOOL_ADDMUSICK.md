# AddmusicK

AddmusicK (AMK) replaces Super Mario World's music and sound effects. It compiles songs written in its MML dialect, bundles them with BRR samples and its own SPC700 sound engine, and inserts all of it into the ROM with Asar, together with a SNES-side patch that uploads songs to the sound CPU. This page describes the HertzDevil fork of AMK 1.0.5. Later releases (1.0.9, 1.0.10, 1.1) add hex commands and options that are not covered here.

The facts come from two places, and each section says which. Some come from AMK's own documentation, restated in plain words: `doc/readme_files/` holds `syntax_reference.html`, `hex_command_reference.html`, `general_basic_use.html`, `general_advanced_use.html` and `sound_effects.html`. The rest were measured by running AMK as a black box. That means compiling songs with it, then reading the bytes, the ARAM image and the `.spc` it produces, and running its engine in an SPC700 interpreter while logging every DSP register write. None of it was read from AMK's source. AMK's repository declares no licence (GitHub reports none, and the readme credits only Asar), so no code of AMK's is reproduced here.

A clean-room MIT reimplementation of AMK's compiler and engine exists in Pipe Dream.

## Files and folders

| File or folder | What it holds |
|---|---|
| `music/` | Songs, as `.txt` or `.mml` MML files |
| `samples/` | BRR samples, and `.bnk` sample banks |
| `1DF9/`, `1DFC/` | Sound-effect sources, one file per effect |
| `Addmusic_list.txt` | The song list: song numbers, global and local |
| `Addmusic_sample groups.txt` | Named sample groups (`#default`, `#optimized`, user groups) |
| `Addmusic_sound effects.txt` | The 1DF9 and 1DFC effect lists |
| `Addmusic_options.txt` | Command-line arguments read from a file instead |
| `test/1DF9/`, `test/1DFC/` | 93 small shipped effect sources |
| `test/music/` | 16 shipped test songs. `ww`, `ww2` and `ww3` name a sample the folder lacks, so they do not compile as shipped |

AMK prefers `asar.dll` over `asar.exe`, and expects either in its own program directory. Before writing, it backs the ROM up as `ROMNAME~`.

## The Lunar Magic handoff: `<ROMNAME>.msc`

AMK writes `<ROMNAME>.msc` beside the ROM. Lunar Magic reads it to list song names in its music pickers. The file has one line per song for each of its `0`/`1` variants. Any tool that manages music on an LM-edited ROM has to read or write this file.

## What AMK puts in the ROM

From the documentation:

- Song, sample and engine data go into RATS-tagged free space beyond SMW's own. On a 4 MB ROM AMK prefers banks `$40` and up. `-b` turns that preference off, and `-a` lets AMK use untagged free space too.
- `-p` writes the patch and the data files without touching the ROM. `-norom` produces `.spc` files only.
- AMK assembles two programs with Asar: a SNES-side patch for the main CPU, and the SPC700 program (engine and data) that the patch uploads in place of SMW's.

Measured:

- SMW's 20 stock samples sit in the ROM inside SMW's own sound upload at $0F8000. They are byte for byte AMK's `samples/default/*.brr`.
- AMK numbers songs differently from SMW. A song number SMW's own code writes to `$1DFB` names a different song under AMK, so every `$1DFB` write site and song table in the game has to carry AMK's numbers. This was found by playing SMW's songs against AMK's originals of them.

## The SMW side: ports and RAM

SMW talks to the sound CPU through four RAM bytes, each mirrored to an APU port.

| RAM | Role under AMK |
|---|---|
| `$1DF9` | Sound-effect bank 1. The effect plays on SPC channel 6 |
| `$1DFA` | Echo control for sound effects. `#$06` turns sound-effect echo on, and `#$05` turns it off. It is off by default |
| `$1DFB` | Song change. A song not in ARAM is uploaded first |
| `$1DFC` | Sound-effect bank 2. The effect plays on SPC channel 7 |

According to AMK's docs, the only difference between the two effect banks is the SPC channel they use (6 or 7).

Behaviour, measured against AMK and against SMW's own engine:

- Writing `$FF` to `$1DFB`, or the number of a song the ROM does not have, fades the music out over 240 ticks.
- Writing `$FF` to `$1DF9` (hurry up) adds 10 to the tempo and plays SMW's hurry-up jingle. The faster tempo lasts until a level entered from the overworld uploads its song again.
- Echo is turned off whenever a song is uploaded.

## Songs, samples and sound effects

All from the documentation.

### Global and local songs

`Addmusic_list.txt` divides songs into global and local. Global songs never transfer: they stay in ARAM from power-on and use that space permanently. Local songs are uploaded on a song change, along with their samples, unless whoever writes `$1DFB` keeps the previous sample set.

### Samples

- Samples are BRR files, grouped in `Addmusic_sample groups.txt`. `#default` is every stock SMW sample. `#optimized` is only the samples that global songs and sound effects need.
- A trailing `!` on a sample marks it important, which means it is always resident.
- Samples a song never uses are dropped for that song, unless `-u` is given. Duplicate samples are shared, unless `-d` is given.
- A `.bnk` bank is named in `#samples`. A bank is exactly `$8000` bytes and fills ARAM `$8000-$FFFF`. The 1.0.5 build crashes when it loads one, so nothing about banks could be measured.

Measured: a group's sample that is not marked important, and that nothing in the song names (an instrument definition or use, or `$F3`), is not uploaded with that song. Important samples stay in ARAM from power-on.

### Sound effects

- There are two folders, `1DF9` (SPC channel 6) and `1DFC` (channel 7). They are listed in `Addmusic_sound effects.txt` as `<hex slot> [flag] TAB <filename>`, and each filename is looked up in the folder of the same name.
- The `*` flag makes the slot a pointer to an effect already inserted, which saves ARAM. The `?` flag stops AMK from appending its automatic `$00` terminator.
- Effect commands are a subset of the song language: notes, `@x`, `@x,y` for noise, `v x,y`, raw `$xx` bytes, and `#asm` / `#jsr` for inline SPC700 code.

What the shipped effects show:

- All 93 shipped effects are written in pure `$xx` hex. Not one note letter appears in any of them. The grammar is a length byte, an optional volume, an optional second volume (giving separate left and right volumes, i.e. pan), and then a note byte of `$80` or above. A bare note reuses the previous header.
- A zero length byte ends an effect. `test/1DFC/0E L + R scroll.txt` and `1DFC/1D Time low 2.txt` each have a `$00` in the middle of the stream, followed by an exact copy of a 1DF9 effect. Those trailing blocks can never be reached, so they are dead data. This reading comes from the effect grammar alone and has not been checked against how AMK compiles effects.
- AMK 1.0.5 compiles the note syntax in effects differently from what its readme says [MEASURED]. To reproduce it, go by AMK's actual output, not the readme.

## The MML language

From the documentation.

- **Channels.** A song has up to 8 channels, `#0`-`#7`. Channels 6 and 7 are shared with sound effects, and they are cut while an effect plays on them.
- **Notes.** `cdefgab`, `r` (rest) and `^` (tie), with `+`/`-` for sharp and flat. Lengths are note values, and `l` sets the default length. `o`, `<` and `>` set the octave (1-6), `h` sets tuning, and `{ }` makes triplets.
- **Instruments.** `@` selects an instrument: 0-18 are SMW's, 21-29 are percussion, and 30 and up are custom.
- **Other commands.** `v` and `w` are channel and global volume. `y` is pan (0-20, with optional surround flags). `q` is quantisation, `t` is tempo, `p` is vibrato, `n` is noise, and `&` is a pitch slide. `?` means no loop, and `/` marks the intro. `("x.brr",$tt)` loads a sample.
- **Loops.** `[ ]n` repeats. `(n)[ ]m` defines a labelled loop, `(n)k` calls it, and `*` recalls the last one. These loops cannot nest. `[[ ]]n` superloops can go around them, which is a second level, and remote-code event type 4 works as a third.
- **Remote code.** `(!n)[...]` defines a run of hex commands with no notes. `(!n, type, arg)` attaches one to an event: note on, N ticks into a note, before a note ends, key off, run now, or disable.
- **Replacements.** `=` replacements are greedy and recursive, and they apply only to the text after them.
- **Preprocessing.** `#define`, `#undef`, `#ifdef`, `#ifndef`, `#if`, `#endif` and `#error` run before everything else.
- **Hex commands.** `hex_command_reference.html` has 106 rows. Among them are `$DA` (instrument), `$E0`-`$E4` (volume, tempo, transpose), `$E5` (tremolo), `$E6` (subloops) and AMK's own `$FA` family. Hex commands are validated unless `-h` is given. Turning validation off also turns off echo bounds checking and AM4/AMM conversion.
- **Directives.**
  - `#samples { #group "x.brr" ... }`.
  - `#instruments { "x.brr" $aa $bb $cc $dd $ee }`. An ADSR1 byte of `$80` or above selects ADSR, and anything lower selects GAIN. `dd.ee` is the tuning.
  - `#path`, `#pad`, `#halvetempo`, and `#option tempoimmunity | dividetempo n | smwvtable | noloop`.
  - `#spc { #author ... #length }`, the `.spc` ID666 tags.
  - `#amk n`, the parser version. AMK appends it when it is missing, and `#am4` and `#amm` override it.
- **Other channel limits.** Channel 0 cannot be pitch-modulated.

## Conversion of older formats

- AddmusicM songs need an `#amm` header, and their `sXX_..` line has to be rewritten as a `#samples` list. Addmusic 4.05 songs need `#am4`. `-c` converts them.
- Measured, for `#am4` and `#amm` songs: AMK drops the header's echo-buffer writes, `$ED $80`/`$81` (Addmusic 4's own commands), stray bytes below `$80`, and notes that come before the first channel.
- Real Addmusic 4 songs compile under 1.0.5. So do the songs among AMK 1.0.6's 39 originals that 1.0.5 can compile.

## How MML compiles

Measured against AMK's output. AMK's documentation describes none of this.

- **Layout of a compiled song.** First the phrase list, then the pointer tables, then the instrument table, then the channels. Every subroutine comes after every channel.
- **`[ ]` loops** are compiled as subroutines and called with `$E9`.
- **Duration and quantisation bytes** are written only when they change, and the compiler forgets them after a loop, so the next note writes them again.
- **Intro markers** (`/`) re-select the channel.
- **Long notes** are split into halves for lengths up to 254 ticks, and into runs of 127 otherwise.
- **A slide (`&`)** splits differently from a plain long note, and it emits `$DD` before the next note.
- `h` and `@` have their own rules for which wins between loop context and text order.
- **Empty channels** are handled specially.
- **The song's option bytes** live in channel 0.
- **`$EF`'s parameters** are stored rotated, so they are not in the order they are written in the MML.
- **Tempo division** (`dividetempo`, `#halvetempo`) is applied to every duration field.
- **Hex commands** are checked by the validations the docs describe.
- **Remote code.** AMK 1.0.5 cannot compile its own documented remote-code syntax (`(!n)[...]`, `(!n, type, arg)`), so that part of the language has only the documentation behind it.
- `-v` prints the size of each channel.

## ARAM: the binding constraint

ARAM (64 KB) limits everything in AMK. Its regions are the engine, the global songs, the sample directory (aligned to `$100`), the samples, the sound effects, the local song and the echo buffer.

- Global songs never transfer, but they hold their ARAM permanently.
- The echo buffer sits at the top of ARAM, at `ESA = $100 − 8 × delay` (see Echo below), so a longer delay takes more space. It has to be reserved up front with `$FA $04`. A song that runs into it fails to build with "Echo buffer exceeded total space in ARAM".
- ARAM cost caps echo delay at `$00-$0F`. The docs warn that a rogue echo buffer "can cause irreparable damage".

## The engine, as measured

These findings come from running AMK's own engine in an SPC700 interpreter and logging every DSP register write. The interpreter's instruction and timer timing match blargg's snes_spc (libgme) cycle for cycle.

### Where AMK's engine misbehaves

- **It falls behind under load.** With many channels running effects, it cannot finish a song tick inside one timer tick, and it loses ticks. That is about 1% with six channels of vibrato, 5% on one eight-channel test song, and 23% on an eight-channel song at `t192`. snes_spc shows the same losses, so real hardware would too.
- **`$DD` right after a loop's end, or before any note, stops the song for good.**
- **`$E5` with depth `$FF` after a note hangs it.**

### Timing

- Timer 0 runs at 500 Hz (target 16). Every timer tick adds `tempo + 1` to a one-byte accumulator, and each carry out of it is one song tick. So **song ticks per second = 500/256 × (T+1)**. A quarter note is 48 ticks. With no `t` command, the tempo is **53**.
- Effects (vibrato, bends, pan fades, tremolo) update on every *timer* tick. The time into a note counts song ticks plus the accumulator's fraction. Bends, tremolo and pan fades run one timer tick (or one tick) ahead.
- The first channel to reach the end of its data ends the phrase for every channel. Notes other channels started on that tick are dropped, and the next phrase starts on the same tick. A new phrase keeps each channel's instrument, volume, pan and `q`.

### Notes

- **Quantisation.** A note is released at tick `max(len × T[q] >> 8, 1)`, and released again at `len − 2`, where T = `33 66 80 99 B3 CC E6 FF`. Rests are released at their start, and they get the same two releases. The release is skipped when a tie follows. Durations, `q` bytes and other commands are stepped over when looking for that tie, but a call, a loop, an arpeggio or the end of the data counts as no tie.
- **Pitch.** The top octave comes from a 12-entry table (`085F ... 0FCD`, then `10BE`). A fraction of a semitone interpolates between neighbouring entries, truncated. Each octave below is half the one above. The result is then multiplied by the instrument's tuning: `P × whole + (P × fraction >> 8)`.
- **Transposition.** `$FA $02` (one channel) and `$E4` (all channels) add semitones. The sum wraps in **seven** bits, so `$85` is +5 and `$7B` is −5. A result past the top note plays at pitch 0. Percussion is transposed too.
- **`$EE f`** detunes every note by f/256 of a semitone.
- **Instruments.** @0-@18 are SMW's. **@19 and @20 leave the instrument unchanged.** @21-@29 are percussion. Each plays a fixed note (`A8 A4 A1 A4 A4 9C A6 A6 A1`) on its own instrument (tuning `3 7 7 7 8 2 8 8 3`), and the channel keeps that instrument for the notes after it. A channel with no `@` at all plays @0.
- **`$ED`.** When `aa < $80`, it sets ADSR1 = `aa | $80` and sets ADSR2. With `$80 gg`, it sets ADSR1 = 0 and GAIN = gg. **`$FA $01 gg`** clears bit 7 of ADSR1 (ADSR1 &= `$7F`) and sets GAIN = gg. **`$F4 $09`** or a new `@` undoes both.

### Volume

- `P = ((((v × vel) >> 8) × w) >> 8)² >> 9`. `$FA $03 a` turns that into `P + (P × a >> 8)`.
- Then left = `P × pan[y] >> 7` and right = `P × pan[20 − y] >> 7`, with pan = `00 01 03 07 0D 15 1E 29 34 42 51 5E 67 6E 73 77 7A 7C 7D 7E 7F`. While a pan fade runs, the table is interpolated and truncated. A surround bit flips the sign of that side.
- The defaults are `w` 192, `v` 255 and `y` 10, with N-SPC's velocity table.
- A change to `v`, `y`, `w` or `$FA $03` is sent on its own tick, even in the middle of a note.

### Effects

- **Vibrato `$DE d r a`.** After d ticks, phase = (t − d) × r. The wave is a triangle: +a/256 semitone at a quarter of the period and −a/256 at three quarters. **`$EA n`** fades the depth in from 0 at key-on over n ticks. **`$DF`** returns the note to its own pitch.
- **Bend `$DD d l n`** is read together with the note just before it. The pitch goes from that note to n, starting d ticks in and lasting l ticks, linear in semitones. It then holds at n.
- **`$EB d l s` / `$EC d l s`.** With `$EB`, every later note bends by s semitones at release. With `$EC`, every later note starts at note − s and bends back up at attack. A length of 0 turns either one off.
- **Tremolo `$E5 d r a`.** Volume is multiplied by (1 − a/256 × u), where u is a triangle rising from 0 to 1 at half a period, with phase (t + 1 − d) × r. Tremolo also applies at key-on. A depth of 0 turns it off.
- **Fades** (`$E8` volume, `$DC` pan, `$E1` global volume, `$E3` tempo) step by a signed 8.8 amount every tick. The first step happens on the tick the command is read, and the fade lands exactly on the target. **A length of 0 does nothing.** Volume steps once per tick, while a pan fade also glides between ticks.

### Echo

- At song start, and **every time the phrase list loops**, the engine writes FLG `$60`, ESA `$FF`, EDL 0, FLG `$40`, FLG `$00`. Any buffer reserved before is forgotten.
- **`$EF`** writes its compiled bytes (channels, left, right) to EON, EVOL L and EVOL R, in the order AMK stores them.
- **`$F1 d f n`.** If d needs a bigger buffer than the one already made, the engine writes FLG `$60`, ESA = `$100 − 8d` (`$FF` when d is 0) and EDL = d. The whole song then stands still for 13 × d timer ticks, writes FLG `$40`, waits another 13 × d, and writes FLG `$00`. If the buffer is already big enough, it writes only EDL. Either way it then writes EFB = f, the eight FIR coefficients of filter n, and the echo volumes again. The filters are:
  - 0: `FF 08 17 24 24 17 08 FF`
  - 1: `7F 00 ...`
  - 2: `5F 08 DE 08 65 09 F4 09`
- **`$FA $04 n`** makes the buffer for delay n up front, with the same wait, so later `$F1` commands up to delay n do not pause the song.
- **`$F0`** writes EON, EVOL 0 and FLG `$20`.
- **`$F2 l L R`** fades the echo volume. It takes one step fewer than l, so it does not land on the target.
- **`$F5`** writes the eight FIR coefficients.
- **`$F4 $03`** toggles the current channel's echo bit.
- PMON, NON and EON are written on every song tick.

### Not yet measured

These commands have no measured behaviour here:

- `$F4` subcommands `$01` (legato), `$02` (light staccato), `$08` (velocity table), `$00`/`$06` (Yoshi drums), `$05` (sync) and `$07` (tempo hike)
- `$F6` (DSP write), `$F8` (noise) and `$FA $00` (pitch modulation)
- `$FB` (arpeggio, trill, glissando), `$FC` (remote commands), `$F3` (sample load) and `$F9` (data send)
- the effect channels' own playback, and the port protocol in detail

## Quirks

- Channels 6 and 7 are cut whenever a sound effect plays on them.
- Loops cannot nest. `[[ ]]` is the second level, and remote event type 4 is an effective third.
- `-h` turns off more than hex validation: it also turns off echo bounds checking and AM4/AMM conversion.
- The 1.0.5 build cannot compile its own documented remote-code syntax, and it crashes when it loads a `.bnk` bank.
- Effect note syntax compiles differently from the readme [MEASURED].
- Two shipped 1DFC effects carry unreachable data after an early `$00`.
- A song with `$DD` straight after a loop end, or before any note, stops for good. A song with `$E5` at depth `$FF` after a note hangs.
- Under heavy effect load the engine loses song ticks, so busy songs play slower than their tempo says.
