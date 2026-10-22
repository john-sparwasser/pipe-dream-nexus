function toggleDark() {
  document.documentElement.classList.toggle("inverted");
}

// Regex search over this bank's lines; results replace the TOC in the left pane.
function searchLogs(pattern) {
  const toc = document.getElementById("toc"), out = document.getElementById("results");
  if (!toc || !out) return;
  let re;
  try { re = new RegExp(pattern, "i"); } catch (e) { out.textContent = "Bad regex: " + e.message; return; }
  const hits = [];
  for (const el of document.querySelectorAll("#right .l, #right .c")) {
    if (!re.test(el.textContent)) continue;
    const id = el.id || (el.querySelector("a[id]") || {}).id;
    hits.push(id ? `<a href="#${id}">${el.innerHTML}</a>` : el.innerHTML);
    if (hits.length >= 500) { hits.push("... (500 shown)"); break; }
  }
  out.innerHTML = hits.length ? hits.join("\n") : "No results";
  toc.hidden = true; out.hidden = false;
}

function clearSearch() {
  const toc = document.getElementById("toc"), out = document.getElementById("results"), q = document.getElementById("q");
  if (q) q.value = "";
  if (toc) toc.hidden = false;
  if (out) { out.hidden = true; out.innerHTML = ""; }
}

document.addEventListener("DOMContentLoaded", () => {
  const q = document.getElementById("q");
  if (q) q.addEventListener("change", () => q.value ? searchLogs(q.value) : clearSearch());
});

// search.html: fetch every bank page and scan its lines for a regex.
async function searchAll() {
  const q = document.getElementById("qa").value, out = document.getElementById("all"), st = document.getElementById("status");
  let re;
  try { re = new RegExp(q, "i"); } catch (e) { out.textContent = "Bad regex: " + e.message; return; }
  out.innerHTML = ""; let n = 0;
  for (const b of BANKS) {
    st.textContent = "scanning $" + b + "...";
    const doc = new DOMParser().parseFromString(await (await fetch(b + ".html")).text(), "text/html");
    for (const el of doc.querySelectorAll("#right .l, #right .c")) {
      if (!re.test(el.textContent)) continue;
      const id = el.id || (el.querySelector("a[id]") || {}).id;
      const txt = el.textContent.replace(/&/g, "&amp;").replace(/</g, "&lt;");
      out.insertAdjacentHTML("beforeend", id ? `<a href="${b}.html#${id}">${txt}</a>\n` : txt + "\n");
      if (++n >= 2000) { st.textContent = "2000 results (truncated)"; return; }
    }
  }
  st.textContent = n + " results";
}
document.addEventListener("DOMContentLoaded", () => {
  const qa = document.getElementById("qa");
  if (qa) qa.addEventListener("keydown", e => { if (e.key === "Enter") searchAll(); });
});

// ram.html: filter the entries as you type (address, name or any word in the description).
document.addEventListener("DOMContentLoaded", () => {
  const rq = document.getElementById("rq");
  if (!rq) return;
  const all = [...document.querySelectorAll(".rv")], count = document.getElementById("rcount");
  const run = () => {
    const terms = rq.value.toLowerCase().replace(/\$/g, "").split(/\s+/).filter(Boolean);
    let n = 0;
    for (const el of all) {
      const hit = terms.every(t => el.dataset.q.replace(/\$/g, "").includes(t));
      el.classList.toggle("hide", !hit);
      n += hit;
    }
    count.textContent = terms.length ? n + " of " + all.length + " shown" : "";
  };
  rq.addEventListener("input", run);
  // "by section" view: regroup the same entries under data-s headings; "by address" restores the original order.
  const host = all[0].parentNode, jump = document.querySelector(".jump");
  document.querySelectorAll("input[name=rview]").forEach(r => r.addEventListener("change", () => {
    host.querySelectorAll(".sect").forEach(h => h.remove());
    const bySect = r.value === "sect";
    if (jump) jump.hidden = bySect;
    const other = el => el.dataset.s === "Other";
    const order = bySect ? [...all].sort((a, b) => other(a) - other(b) || a.dataset.s.localeCompare(b.dataset.s)) : all;
    let last = null;
    for (const el of order) {
      if (bySect && el.dataset.s !== last) {
        last = el.dataset.s;
        const h = document.createElement("h2"); h.className = "sect"; h.textContent = last; host.appendChild(h);
      }
      host.appendChild(el);
    }
  }));
  if (location.hash && !document.querySelector(location.hash)) rq.value = location.hash.slice(1);
  run();
});

// Instruction help: when on, mnemonics and data directives are highlighted and hovering one says
// what it does. The toggle is remembered per browser; storage can be unavailable, so it is optional.
const OPS = {
  ADC: "Add with carry: A = A + operand + carry. Clear carry (CLC) first for a plain add.",
  AND: "Bitwise AND the operand into A. Often used to keep only some bits.",
  ASL: "Shift left one bit (A, or memory). The top bit goes into carry; same as ×2.",
  BCC: "Branch if carry clear. After CMP: the value was less than the operand (unsigned).",
  BCS: "Branch if carry set. After CMP: the value was greater than or equal to the operand (unsigned).",
  BEQ: "Branch if the zero flag is set: the last result was 0, or a CMP found the values equal.",
  BIT: "Test bits: AND A with the operand to set the zero flag, without changing A. From memory it also copies the operand's top two bits into N and V.",
  BMI: "Branch if negative: the last result had its top bit set.",
  BNE: "Branch if not zero: the last result was non-zero, or a CMP found the values different.",
  BPL: "Branch if positive: the last result had its top bit clear.",
  BRA: "Branch always (short jump, up to 127 bytes away).",
  BRK: "Software interrupt (break).",
  BRL: "Branch always, long: a relative jump up to 32 KB away.",
  BVC: "Branch if the overflow flag is clear.",
  BVS: "Branch if the overflow flag is set.",
  CLC: "Clear carry. Done before ADC so nothing extra is added.",
  CLD: "Clear decimal mode (back to binary arithmetic).",
  CLI: "Clear interrupt-disable: allow IRQs again.",
  CLV: "Clear the overflow flag.",
  CMP: "Compare A with the operand (A − operand, result thrown away). Sets the flags for a following branch.",
  COP: "Coprocessor software interrupt.",
  CPX: "Compare X with the operand. Sets the flags for a following branch.",
  CPY: "Compare Y with the operand. Sets the flags for a following branch.",
  DEC: "Decrement A, or a memory value, by 1.",
  DEX: "Decrement X by 1.",
  DEY: "Decrement Y by 1.",
  EOR: "Bitwise exclusive-OR the operand into A. Flips the bits that are set in the operand.",
  INC: "Increment A, or a memory value, by 1.",
  INX: "Increment X by 1.",
  INY: "Increment Y by 1.",
  JML: "Jump long: go to a 24-bit address, which can be in another bank.",
  JMP: "Jump to an address in the same bank (in parentheses: jump through a pointer).",
  JSL: "Call a subroutine anywhere in the ROM (long call). It returns with RTL.",
  JSR: "Call a subroutine in the same bank. It returns with RTS.",
  LDA: "Load A with the operand.",
  LDX: "Load X with the operand.",
  LDY: "Load Y with the operand.",
  LSR: "Shift right one bit (A, or memory). Bit 0 goes into carry; same as ÷2, unsigned.",
  MVN: "Block move: copy A+1 bytes from address X to address Y, counting up. The operands are the two banks.",
  MVP: "Block move: copy A+1 bytes from address X to address Y, counting down. The operands are the two banks.",
  NOP: "No operation: does nothing for one instruction.",
  ORA: "Bitwise OR the operand into A. Often used to set some bits.",
  PEA: "Push a 16-bit constant onto the stack.",
  PEI: "Push the 16-bit value stored at a direct-page address onto the stack.",
  PER: "Push an address relative to this instruction onto the stack.",
  PHA: "Push A onto the stack.",
  PHB: "Push the data bank register onto the stack.",
  PHD: "Push the direct page register onto the stack.",
  PHK: "Push the program bank (the bank this code is in). Often followed by PLB so data reads use this bank.",
  PHP: "Push the processor flags onto the stack.",
  PHX: "Push X onto the stack.",
  PHY: "Push Y onto the stack.",
  PLA: "Pull A from the stack.",
  PLB: "Pull the data bank register from the stack: sets which bank plain addresses read from.",
  PLD: "Pull the direct page register from the stack.",
  PLP: "Pull the processor flags from the stack.",
  PLX: "Pull X from the stack.",
  PLY: "Pull Y from the stack.",
  REP: "Reset (clear) flag bits. REP #$20 makes A 16-bit, #$10 makes X and Y 16-bit, #$30 both.",
  ROL: "Rotate left one bit through carry: carry goes into bit 0, the top bit goes into carry.",
  ROR: "Rotate right one bit through carry: carry goes into the top bit, bit 0 goes into carry.",
  RTI: "Return from an interrupt handler.",
  RTL: "Return from a subroutine called with JSL.",
  RTS: "Return from a subroutine called with JSR.",
  SBC: "Subtract with borrow: A = A − operand − (1 − carry). Set carry (SEC) first for a plain subtract.",
  SEC: "Set carry. Done before SBC so nothing extra is subtracted.",
  SED: "Set decimal mode (BCD arithmetic for ADC and SBC).",
  SEI: "Set interrupt-disable: block IRQs.",
  SEP: "Set flag bits. SEP #$20 makes A 8-bit, #$10 makes X and Y 8-bit, #$30 both.",
  STA: "Store A to memory.",
  STP: "Stop the CPU until reset.",
  STX: "Store X to memory.",
  STY: "Store Y to memory.",
  STZ: "Store zero to memory.",
  TAX: "Copy A to X.",
  TAY: "Copy A to Y.",
  TCD: "Copy the 16-bit A to the direct page register.",
  TCS: "Copy the 16-bit A to the stack pointer.",
  TDC: "Copy the direct page register to the 16-bit A.",
  TRB: "Test and reset bits: clear, in memory, the bits that are set in A.",
  TSB: "Test and set bits: set, in memory, the bits that are set in A.",
  TSC: "Copy the stack pointer to the 16-bit A.",
  TSX: "Copy the stack pointer to X.",
  TXA: "Copy X to A.",
  TXS: "Copy X to the stack pointer.",
  TXY: "Copy X to Y.",
  TYA: "Copy Y to A.",
  TYX: "Copy Y to X.",
  WAI: "Wait for an interrupt.",
  WDM: "Reserved; does nothing.",
  XBA: "Swap the high and low bytes of A.",
  XCE: "Swap carry with the emulation flag: switches between 6502 emulation and native 65816 mode.",
  ".DB": "Data: raw bytes (8-bit values), not code.",
  ".DW": "Data: 16-bit words (often pointers within the bank), not code.",
  ".DL": "Data: 24-bit long values (often pointers to any bank), not code.",
};
const SIZES = { B: ".B: the operand is a byte (8-bit, or a direct-page address).",
                W: ".W: the operand is a word (16-bit, or an absolute address).",
                L: ".L: the operand is long (a 24-bit address, any bank)." };

function opHelp(text) {
  const t = text.trim().toUpperCase();
  if (t.startsWith(".")) return OPS[t] || "";
  const [mn, size] = t.split(".");
  return OPS[mn] ? OPS[mn] + (SIZES[size] ? "\n" + SIZES[size] : "") : "";
}

function setHelp(on) {
  document.documentElement.classList.toggle("help", on);
  const b = document.getElementById("help-btn");
  if (b) b.setAttribute("aria-pressed", on);
  try { localStorage.setItem("bankHelp", on ? "1" : ""); } catch (e) {}
}
function toggleHelp() { setHelp(!document.documentElement.classList.contains("help")); }

document.addEventListener("DOMContentLoaded", () => {
  if (!document.getElementById("help-btn")) return;
  try { if (localStorage.getItem("bankHelp")) setHelp(true); } catch (e) {}
  const tip = document.createElement("div");
  tip.id = "tip"; tip.hidden = true; document.body.appendChild(tip);
  document.addEventListener("mouseover", e => {
    const el = e.target.closest && e.target.closest(".op, .d");
    const text = el && document.documentElement.classList.contains("help") && opHelp(el.textContent);
    if (!text) { tip.hidden = true; return; }
    tip.textContent = text; tip.hidden = false;
    const r = el.getBoundingClientRect();
    tip.style.left = Math.min(r.left, innerWidth - tip.offsetWidth - 8) + "px";
    tip.style.top = (r.bottom + tip.offsetHeight + 12 > innerHeight ? r.top - tip.offsetHeight - 6 : r.bottom + 6) + "px";
  });
});
