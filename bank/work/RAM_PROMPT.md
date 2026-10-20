# RAM annotator brief: what does this address do?

You write the explanations for a Super Mario World RAM map, in the spirit of Patrick Johnston's Super Metroid RAM
map (https://patrickjohnston.org/bank/index.html, "RAM map"). A reader who sees `$1540` in some routine wants to
know what the byte *means*, not who touches it. The call-site list is generated separately; your job is the
explanation above it.

## Inputs
- `bank/work/ram_batches/<NN>.json`: your batch (NN given in your task). A list of addresses, each with: `address`,
  `key`, `symbol` (the `RAM_Name` the source uses, or null), use counts, read/write/modify split, whether it is
  indexed with `,X`/`,Y` (a table) or used as a pointer, and up to 16 sample call sites. Each sample is
  `$BB:AAAA MNEMONIC in "<routine name>" xN ; <comment>`. The routine names and comments are the English ones
  already written for the bank logs, so they are the best evidence you have.
- The disassembly: `/Users/john/projects/pipe-dream/reference/smw-disasm/bank_XX.asm`, plus its notes
  (`SYSTEM_NOTES.md`, `SPRITE_ENGINE_NOTES.md`, `LEVEL_PIPELINE_NOTES.md`, `SNES_HARDWARE_NOTES.md`). Grep
  `RAM_Name` or the address (`grep -h '\$1540' bank_*.asm`) to find more context, especially where a write sets a
  meaningful value (`LDA #$xx : STA $addr`), a read tests a bit, or a table is indexed by sprite slot.
- The rendered logs at `bank/0X.html` are not needed. Do not read files under `bank/annotations/` wholesale; grep them
  for the address if you want the comments agents wrote for the routines.

## Output: `bank/ram/<batch>.json`, e.g. `bank/ram/ram-12.json`
```json
{
  "addresses": {
    "1540": {
      "name": "Sprite timer 1",
      "kind": "byte table, one per sprite slot (index X)",
      "desc": [
        "General-purpose countdown timer for each sprite slot. Sprites set it to a frame count and the main",
        "routine counts it down by one per frame (when sprites are not locked) and acts when it reaches zero.",
        "Meaning is per sprite type: Koopa shell stun time, Boo fade timer, Thwomp wait, ...",
        "Values: 0 = timer expired / not running."
      ]
    }
  }
}
```
- Keys are the `key` strings from the batch (4 hex digits, or 6 for `$7E:xxxx` / `$7F:xxxx`). Cover EVERY address in the batch.
- `name`: 2-6 words, sentence case. If the source already has a `RAM_Name`, give the English meaning, not the label again.
- `kind`: one short phrase: `byte`, `word (little endian, low/high pair)`, `flag byte`, `bit flags`, `byte table indexed by
  sprite slot`, `pointer (24-bit)`, `scratch`, `counter`, `timer`, `index`, `state`, etc. Say which bits if it is bit flags.
- `desc`: 1 to 5 lines (each under ~110 chars, no Markdown), then, where useful, lines starting `Values:` or `Bits:` that list
  the meaningful values/bits (`Bit 7: ...`). Lead with what the byte *is and does in the game*. Then who writes it and
  who reads it in game terms ("set when Mario touches a P-switch, read by the sprite status routines"). If it is
  indexed by sprite slot, say so, and if its meaning differs per sprite type say that and give two or three examples
  from the samples.
- Tie related addresses together by naming them: "High byte of Mario's X position ([$94] is the low byte)". Mention the
  partner address as `$0094` so it can be found.
- Be accurate. You have the code, so check a claim in the source before writing it. If you can only see how it is used and
  not what it means, say what it does in the code ("set to 1 by X, tested by Y to skip Z") rather than guessing a purpose,
  and mark real uncertainty with "probably". Never invent a feature. Do not pad.
- ASCII only, apart from `$`, `[`, `]`, `,`, `:`, `;`.

## Process
1. Read your batch JSON. Skim related notes once.
2. For each address grep the source as needed, then write its entry. Work in address order; neighbours are often related.
3. Write the JSON with Write (create `bank/ram/` if needed). Put helper scripts only in `/private/tmp/claude-501/ram-<batch>/`.
4. Validate: `python3 -I bank/ramscan.py --check` must not report problems for your keys (it prints counts for everyone;
   only your own keys matter).
5. Do NOT edit any other file and do NOT git commit.
6. Final message: batch id, number of addresses described, and the addresses you were unsure about. Under 80 words.
