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
