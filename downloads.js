// Turns the static download link into a "Download for <your OS>" button pointing at the right
// asset of the latest RELEASE. Releases, not CI artifacts: an artifact needs a logged-in GitHub
// session to download and expires after 90 days, a release asset is a plain public URL that
// stays put. /releases/latest follows future releases on its own, so this needs no edit when a
// new version ships.
//
// The GitHub API is CORS-open for public repos, so this needs no key and no build step — but it
// is unauthenticated, so it is rate limited to 60/hour per IP. Every failure path leaves the
// static markup alone.
//
// ponytail: no caching layer. Add a Vercel function proxying the API with a token if the rate
// limit ever actually bites.

var REPO = 'john-sparwasser/pipe-dream';

/// Which build this visitor wants: 'win', 'linux', 'osx' (supported, not packaged yet), or null
/// for anything that cannot run a desktop app. Android's UA contains "Linux", so it goes first.
function ridFor(ua, platformHint) {
  var s = ((platformHint || '') + ' ' + (ua || '')).toLowerCase();
  if (/android|iphone|ipad|ipod/.test(s)) return null;
  if (/mac|darwin/.test(s)) return 'osx';
  if (/win/.test(s)) return 'win';
  if (/linux|x11/.test(s)) return 'linux';
  return null;
}

/// The asset a platform installs. Matched on shape rather than an exact name because the
/// Windows installer carries the version in its filename (PipeDream-Setup-0.0.2.exe) while the
/// Linux binary does not — so a fixed name would break on the next release.
function pickAsset(assets, platform) {
  return (assets || []).filter(function (a) {
    if (!a || !a.name || !a.browser_download_url) return false;
    var exe = /\.exe$/i.test(a.name);
    return platform === 'win' ? /^PipeDream-Setup/i.test(a.name) && exe
                              : /linux/i.test(a.name) && !exe;
  })[0] || null;
}

/// Release tags are written "v0.0.2"; the leading v is not part of the version.
function tagVersion(tag) {
  return (tag || '').replace(/^v/i, '');
}

// --- DOM wiring; skipped when loaded outside a browser (see check.mjs) ---------------------

if (typeof document !== 'undefined') {
  var LABEL = { win: 'Windows', linux: 'Linux' };
  var box = document.getElementById('dl');
  var platform = ridFor(navigator.userAgent,
                        (navigator.userAgentData || {}).platform || navigator.platform);

  // Header Download button: a modal with both builds. The <a> still goes to the release page
  // if this script never ran.
  var modal = document.getElementById('dl-modal');
  var dlBtn = document.getElementById('top-dl');   // not "top": that is window.top, read-only
  if (modal && dlBtn) {
    dlBtn.onclick = function (e) { e.preventDefault(); modal.showModal(); };
    modal.onclick = function (e) {
      if (e.target === modal || e.target.className === 'close') modal.close();
    };
  }

  if (box && platform === 'osx') {
    box.innerHTML = '<p class="dl-mac">No packaged macOS build yet — '
      + '<a href="https://github.com/' + REPO + '#native-macos-builds--in-progress">'
      + 'here is why, and how to build it yourself</a>.</p>';
  }

  fetch('https://api.github.com/repos/' + REPO + '/releases/latest')
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (d) {
      var version = tagVersion(d.tag_name);
      var ver = document.getElementById('ver');
      if (ver && version) ver.textContent = 'v' + version;   // the Status paragraph

      ['win', 'linux'].forEach(function (p) {              // modal links: straight to the file
        var a = pickAsset(d.assets, p), el = document.getElementById('dl-' + p);
        if (a && el) {
          el.href = a.browser_download_url;
          el.innerHTML += '<small>' + (version ? 'v' + version + ' · ' : '')
                        + Math.round(a.size / 1048576) + '&nbsp;MB</small>';
        }
      });

      if (!box || !LABEL[platform]) return;
      var mine = pickAsset(d.assets, platform);
      if (!mine) return;                          // nothing for this platform: keep the link
      var other = platform === 'win' ? 'linux' : 'win';
      var theirs = pickAsset(d.assets, other);

      box.innerHTML =
        '<a class="dl-btn" href="' + mine.browser_download_url + '">'
        + (platform === 'win' ? 'Download the Windows installer' : 'Download for Linux')
        + '</a>'
        + '<p class="dl-meta">'
        + (version ? 'Version ' + version + ' · ' : '')
        + Math.round(mine.size / 1048576) + '&nbsp;MB · self-contained'
        + (theirs ? ' · <a href="' + theirs.browser_download_url + '">' + LABEL[other]
                    + ' build</a>' : '')
        + ' · <a href="https://github.com/' + REPO + '/releases/latest">release notes</a>'
        + '</p>';
    })
    .catch(function () { /* rate limited or offline: the static markup is still there */ });
}

if (typeof module !== 'undefined')
  module.exports = { ridFor: ridFor, pickAsset: pickAsset, tagVersion: tagVersion };
