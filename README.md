# pipe-dream-nexus

Static site for [Pipe Dream](https://github.com/john-sparwasser/pipe-dream) — live at
[pipedream.nexus](https://pipedream.nexus).

One `index.html`, no build step. Vercel serves it as-is and redeploys on every push to `main`.

`downloads.js` upgrades the download links to a "Download for <your OS>" button by asking the
public GitHub artifacts API for the newest CI build. Unauthenticated, so it is rate limited to
60/hour per IP; every failure path leaves the static links in place.

```
node check.mjs     # platform detection + artifact picking
npx serve .        # local preview
```
