# Annotator brief: Super Mario World bank logs

You annotate one chunk of the SMWDisC disassembly so it reads like Patrick Johnston's Super Metroid bank logs
(https://patrickjohnston.org/bank/index.html): every routine has a plain-English name, a short doc comment, and every
instruction has a comment that says what the code *does* (not a restatement of the mnemonic).

## Inputs
- `bank/work/chunks.json`: list of chunks. Find yours by `id`. It gives `file` (e.g. `bank_00.asm`), `line_from`/`line_to`
  (1-indexed range in `<SRC>/<file>`, SRC = `/Users/john/projects/pipe-dream/reference/smw-disasm`), and `sections`
  (anchor, label, kind, start/end address, line count).
- Read the source range with Read (offset/limit) or sed. Read ALL of it. Also skim the surrounding routines and the
  notes in SRC (`SYSTEM_NOTES.md`, `SPRITE_ENGINE_NOTES.md`, `LEVEL_PIPELINE_NOTES.md`, `SNES_HARDWARE_NOTES.md`) when
  you need context. `RAM_*` symbols are named in the code; resolve unknown ones with `grep -h "RAM_Name" <SRC>/bank_*.asm`
  or the equation list near the top of the bank files if present. Follow JSR/JSL targets when a routine's purpose is unclear.

## Output: one file per chunk, `bank/annotations/<chunk id>.json`
```json
{
  "bank": "00",
  "sections": {
    "<anchor from chunks.json>": {
      "name": "Generate random number",
      "summary": ["One to four lines: what it does, then 'Parameters:'/'Returns:' lines where meaningful.",
                  "Mention side effects on RAM/hardware and notable quirks."]
    }
  },
  "lines": {
    "008000": "Disable IRQ",
    "008001": "Disable IRQ, NMI and joypad reading"
  }
}
```
- `sections` keys are the `anchor` strings exactly as in chunks.json. Cover EVERY section in your chunk.
  - `name`: 2-8 words, sentence case, describes behaviour ("Spawn sprite from level data", "Pointer table: sprite main routines").
    Sections titled "(unnamed code)" or "Data"/"Freespace" need a name too. If a section is unknown, say what you can
    ("Unreferenced code, purpose unclear") rather than guessing. Prefix dead code with "Unused." as PJ does.
  - `summary`: lines WITHOUT the leading `;;`. Skip for trivial data runs (name is enough) and 1-line Return stubs.
- `lines` keys are 6-hex-digit 24-bit addresses `BBAAAA` (bank must equal `bank`), the address shown in the `$BB:AAAA`
  column of the page = the line's address in the source. Values replace the existing comment on that line.
  - Comment EVERY code line you can, and every data row whose meaning you know. Replace weak/wrong/chatty/IRC-noise comments,
    keep good ones (you may tighten them). The existing comment text is on the line in the source; if it is already
    accurate and clear, re-emit it (so the overlay is complete) with light cleanup.
  - Group multi-instruction operations PJ-style: put the explanatory text on the *last* line of the group and use box
    characters on the others: `\` on the first line of the group, `|` in the middle, `}` + text on the line that carries the
    explanation, `/` on the last line. Format of a value: `"\\"`, `"|"`, `"} A = [X] * 5"`, `"/"`. (JSON-escape backslashes.)
    Single-line comments need no box character.
  - Notation: `[A]`, `[X]`, `[Y]` = register contents; `[$7E]`/`[RAM_Name]` = memory contents; `$xx = ...` assignments;
    `A: ...` etc. in Parameters/Returns. Be specific: "Mario X speed += [$7E:xxxx] (acceleration), clamped to max walk speed".
  - Say what the code is FOR in game terms (sprite state, level loading, OAM, DMA, Mario physics, ...), not "load A with #$05".
    Name magic numbers when you can (sprite status 8 = normal, 9 = carried/stunned, tileset numbers, etc.).
  - Be accurate. If you are not sure, write a hedged comment ("probably ...") or leave the line out. Never invent
    behaviour. Do not comment pure padding (`$FF` runs) beyond the section name.
  - Table data rows: comment the index/meaning once per row where known (e.g. `00 - Mario`).
- Keep comments short (under ~90 chars). No Markdown. ASCII only except `$`, `[`, `]`, `\`, `|`, `/`, `}`.

## Process
1. Read the chunk's source lines fully.
2. Write the JSON file with Write (create `bank/annotations/` if needed).
3. Validate: `python3 -I bank/annotate.py --check` must print no problems for your file. Fix and rerun if it does.
4. Do NOT edit the .asm files, build.py, annotate.py, chunks.json or anyone else's annotation file. Do not git commit.
5. Final message: chunk id, number of sections named, number of line comments, and anything you flagged as uncertain. Under 100 words.

## Scratch files
Several agents run at once. Put any helper scripts in your own directory `/private/tmp/claude-501/ann-<chunk id>/`, never in a shared folder, and delete nothing that is not yours.
