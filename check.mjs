// node check.mjs — the two pure bits of downloads.js, which are the only parts that can be
// silently wrong. No DOM here, so the wiring at the bottom of that file skips itself.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const { ridFor, pickArtifact } = createRequire(import.meta.url)('./downloads.js');

// Real user-agent strings, because that is where this goes wrong.
const UA = {
  win:     ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Windows'],
  mac:     ['Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15', 'macOS'],
  linux:   ['Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36', 'Linux'],
  android: ['Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36', 'Android'],
  iphone:  ['Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15', 'iOS'],
};
assert.equal(ridFor(...UA.win), 'win-x64');
assert.equal(ridFor(...UA.linux), 'linux-x64');
assert.equal(ridFor(...UA.mac), 'osx');
assert.equal(ridFor(...UA.android), null, 'Android UA says "Linux" — must not offer a build');
assert.equal(ridFor(...UA.iphone), null, 'iPhone UA says "Mac OS X" — must not offer a build');
assert.equal(ridFor('', ''), null);
assert.equal(ridFor(undefined, undefined), null);

const art = (id, name, at, opts = {}) => ({
  id, name, created_at: at, expired: opts.expired || false,
  size_in_bytes: 5e7, workflow_run: { id: 900 + id, head_branch: opts.branch || 'main' },
});
const all = [
  art(1, 'PipeDream-win-x64', '2026-08-01T00:00:00Z'),
  art(2, 'PipeDream-win-x64', '2026-08-20T00:00:00Z'),            // newest, and the answer
  art(3, 'PipeDream-win-x64', '2026-08-25T00:00:00Z', { expired: true }),
  art(4, 'PipeDream-win-x64', '2026-08-24T00:00:00Z', { branch: 'wip' }),
  art(5, 'PipeDream-linux-x64', '2026-08-19T00:00:00Z'),
];
assert.equal(pickArtifact(all, 'PipeDream-win-x64').id, 2, 'newest live artifact on main');
assert.equal(pickArtifact(all, 'PipeDream-linux-x64').id, 5);
assert.equal(pickArtifact(all, 'PipeDream-osx-arm64'), null, 'no build yet → no link');
assert.equal(pickArtifact([], 'PipeDream-win-x64'), null);
assert.equal(pickArtifact(undefined, 'PipeDream-win-x64'), null);
assert.equal(pickArtifact(all.filter(a => a.expired), 'PipeDream-win-x64'), null,
             'an expired artifact is a dead link, never the download');

console.log('ok');
