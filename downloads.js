// Turns the static download links into a "Download for <your OS>" button pointing at the
// newest CI artifact. The GitHub artifacts API is public and CORS-open for public repos, so
// this needs no key and no build step — but it is unauthenticated, so it is rate limited to
// 60/hour per IP. Every failure path leaves the static markup alone.
//
// ponytail: no caching layer. Add a Vercel function proxying the API with a token if the
// rate limit ever actually bites.

var REPO = 'john-sparwasser/pipe-dream';

/// Artifact name per platform, which is NOT the RID: the Windows job uploads an installer.
/// If build.yml renames an upload, this is the line to change.
var ARTIFACT = { 'win-x64': 'PipeDream-Setup', 'linux-x64': 'PipeDream-linux-x64' };

/// Which build this visitor wants: a RID, 'osx' (supported, not packaged yet), or null for
/// anything that cannot run a desktop app. Android's UA contains "Linux", so it goes first.
function ridFor(ua, platformHint) {
  var s = ((platformHint || '') + ' ' + (ua || '')).toLowerCase();
  if (/android|iphone|ipad|ipod/.test(s)) return null;
  if (/mac|darwin/.test(s)) return 'osx';
  if (/win/.test(s)) return 'win-x64';
  if (/linux|x11/.test(s)) return 'linux-x64';
  return null;
}

/// Newest artifact of this name that is still downloadable and came from a `branch` build.
/// Expired artifacts stay in the API listing, so filtering them is the whole point.
function pickArtifact(artifacts, name, branch) {
  var wanted = branch || 'main';
  return (artifacts || [])
    .filter(function (a) {
      return a && a.name === name && !a.expired
          && ((a.workflow_run || {}).head_branch === wanted);
    })
    .sort(function (a, b) {
      return new Date(b.created_at) - new Date(a.created_at);
    })[0] || null;
}

function artifactUrl(a) {
  return 'https://github.com/' + REPO + '/actions/runs/'
       + a.workflow_run.id + '/artifacts/' + a.id;
}

// --- DOM wiring; skipped when loaded outside a browser (see check.mjs) ---------------------

if (typeof document !== 'undefined') {
  var LABEL = { 'win-x64': 'Windows', 'linux-x64': 'Linux' };
  var box = document.getElementById('dl');
  var rid = ridFor(navigator.userAgent,
                   (navigator.userAgentData || {}).platform || navigator.platform);

  if (box && rid === 'osx') {
    box.innerHTML = '<p class="dl-mac">No packaged macOS build yet — '
      + '<a href="https://github.com/' + REPO + '#native-macos-builds--in-progress">'
      + 'here is why, and how to build it yourself</a>.</p>';

  } else if (box && LABEL[rid]) {
    fetch('https://api.github.com/repos/' + REPO + '/actions/artifacts?per_page=100')
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (d) {
        var mine = pickArtifact(d.artifacts, ARTIFACT[rid]);
        if (!mine) return;                                  // nothing fresh: keep the fallback
        var other = rid === 'win-x64' ? 'linux-x64' : 'win-x64';
        var theirs = pickArtifact(d.artifacts, ARTIFACT[other]);

        box.innerHTML =
          '<a class="dl-btn" href="' + artifactUrl(mine) + '">'
          + (rid === 'win-x64' ? 'Download the Windows installer' : 'Download for Linux') + '</a>'
          + '<p class="dl-meta">' + Math.round(mine.size_in_bytes / 1048576) + '&nbsp;MB · '
          + 'self-contained · built ' + new Date(mine.created_at).toLocaleDateString(undefined,
              { year: 'numeric', month: 'short', day: 'numeric' })
          + (theirs ? ' · <a href="' + artifactUrl(theirs) + '">' + LABEL[other] + ' build</a>' : '')
          + '</p>';
      })
      .catch(function () { /* rate limited or offline: the static links are still there */ });
  }
}

if (typeof module !== 'undefined') module.exports = { ridFor: ridFor, pickArtifact: pickArtifact, ARTIFACT: ARTIFACT };
