// node check.mjs — the pure bits of downloads.js, which are the only parts that can be silently
// wrong. No DOM here, so the wiring at the bottom of that file skips itself.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const { ridFor, pickAsset, tagVersion } = createRequire(import.meta.url)('./downloads.js');

// Real user-agent strings, because that is where this goes wrong.
const UA = {
  win:     ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Windows'],
  mac:     ['Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15', 'macOS'],
  linux:   ['Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36', 'Linux'],
  android: ['Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36', 'Android'],
  iphone:  ['Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15', 'iOS'],
};
assert.equal(ridFor(...UA.win), 'win');
assert.equal(ridFor(...UA.linux), 'linux');
assert.equal(ridFor(...UA.mac), 'osx');
assert.equal(ridFor(...UA.android), null, 'Android UA says "Linux" — must not offer a build');
assert.equal(ridFor(...UA.iphone), null, 'iPhone UA says "Mac OS X" — must not offer a build');
assert.equal(ridFor('', ''), null);
assert.equal(ridFor(undefined, undefined), null);

// The real asset list from the v0.0.2 release. The installer carries its version in the
// filename and the Linux binary does not, which is why matching is by shape not by name.
const asset = (name) => ({ name, size: 5e7, browser_download_url: 'https://x.invalid/' + name });
const v002 = [asset('PipeDream-linux-x64'), asset('PipeDream-Setup-0.0.2.exe')];

assert.equal(pickAsset(v002, 'win').name, 'PipeDream-Setup-0.0.2.exe');
assert.equal(pickAsset(v002, 'linux').name, 'PipeDream-linux-x64');

// A future release renames the installer with its own version: still found, no edit needed.
assert.equal(pickAsset([asset('PipeDream-Setup-1.12.0.exe')], 'win').name,
             'PipeDream-Setup-1.12.0.exe');

// Windows must never be handed the Linux binary, and Linux must never be handed a .exe.
assert.equal(pickAsset([asset('PipeDream-linux-x64')], 'win'), null);
assert.equal(pickAsset([asset('PipeDream-Setup-0.0.2.exe')], 'linux'), null);
assert.equal(pickAsset([asset('PipeDream-win-x64.exe')], 'linux'), null);

// Source archives GitHub attaches to every release are not downloads we offer.
assert.equal(pickAsset([asset('Source code (zip)')], 'win'), null);
assert.equal(pickAsset([asset('Source code (zip)')], 'linux'), null);

assert.equal(pickAsset([], 'win'), null);
assert.equal(pickAsset(undefined, 'win'), null);
assert.equal(pickAsset([{ name: 'PipeDream-Setup-0.0.2.exe' }], 'win'), null,
             'an asset with no download url is not a link');

assert.equal(tagVersion('v0.0.2'), '0.0.2');
assert.equal(tagVersion('0.0.2'), '0.0.2');
assert.equal(tagVersion(''), '');
assert.equal(tagVersion(undefined), '');

console.log('ok');
