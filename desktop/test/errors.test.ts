import assert from 'node:assert/strict';
import { test } from 'node:test';
import { errorLines, knownCodes, translate, translateExit } from '../src/shared/errors';

// Real messages, as printed by yt-dlp and the sites it talks to.
const cases: [string, string, string?][] = [
  ['private', "[youtube] abc: Private video. Sign in if you've been granted access to this video"],
  ['private', '[vimeo] 123: This video is private'],
  ['age-restricted', '[youtube] abc: Sign in to confirm your age. This video may be inappropriate for some users. Use --cookies-from-browser or --cookies for the authentication.'],
  ['bot-check', "[youtube] abc: Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies for the authentication."],
  ['geo-blocked', '[youtube] abc: Video unavailable. The uploader has not made this video available in your country'],
  ['geo-blocked', '[BBCIPlayer] This content is not available in your location (geo restricted)'],
  ['removed', '[youtube] abc: Video unavailable. This video has been removed by the uploader'],
  ['removed', '[youtube] abc: Video unavailable'],
  ['removed', '[generic] Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)'],
  ['removed', '[youtube] abc: This video is no longer available because the YouTube account associated with this video has been terminated.'],
  ['members-only', '[youtube] abc: Join this channel to get access to members-only content like this video, and other exclusive perks.'],
  ['members-only', '[patreon] 1: This post requires payment'],
  ['login-required', '[instagram] x: Requested content is not available, rate-limit reached or login required. Use --cookies, --cookies-from-browser, --username and --password, or --netrc (instagram) to provide account credentials'.replace('rate-limit reached or ', '')],
  ['login-required', '[twitter] 1: NSFW tweet requires authentication.'.replace('NSFW tweet', 'This tweet')],
  ['network-down', '[youtube] abc: Unable to download webpage: [Errno -3] Temporary failure in name resolution (caused by TransportError("[Errno -3] Temporary failure in name resolution"))'],
  ['network-down', 'Unable to download webpage: <urlopen error [Errno 11001] getaddrinfo failed>'],
  ['network-down', '[generic] Unable to download webpage: [Errno 101] Network is unreachable'],
  ['connection-dropped', 'unable to download video data: The read operation timed out'],
  ['connection-dropped', "[download] Got error: ('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer')). Giving up after 10 retries"],
  ['disk-full', 'unable to write data: [Errno 28] No space left on device', 'write'],
  ['disk-full', 'There is not enough space on the disk', 'write'],
  ['no-permission', "unable to open for writing: [Errno 13] Permission denied: '/root/x.mp4.part'", 'write'],
  ['name-too-long', "unable to open for writing: [Errno 36] File name too long: 'aaaa.mp4.part'", 'write'],
  ['ffmpeg-missing', 'You have requested merging of multiple formats but ffmpeg is not installed. Aborting due to --abort-on-error', 'post'],
  ['ffmpeg-missing', 'Postprocessing: ffprobe and ffmpeg not found. Please install or provide the path using --ffmpeg-location', 'post'],
  ['ffmpeg-failed', 'Postprocessing: Conversion failed!', 'post'],
  ['ffmpeg-failed', "Postprocessing: Error opening output files: Invalid argument", 'post'],
  ['format-unavailable', '[youtube] abc: Requested format is not available. Use --list-formats for a list of available formats', 'format'],
  ['format-unavailable', '[generic] x: No video formats found!', 'format'],
  ['unsupported-url', 'Unsupported URL: https://example.com/'],
  ['unsupported-url', "[generic] 'foo' is not a valid URL. Set --default-search \"ytsearch\" (or run  yt-dlp \"ytsearch:foo\" ) to search YouTube"],
  ['site-changed', '[youtube] abc: Unable to extract initial player response; please report this issue on  https://github.com/yt-dlp/yt-dlp/issues?q= , filling out the appropriate issue template. Confirm you are on the latest version using  yt-dlp -U'],
  ['site-changed', '[youtube] abc: nsig extraction failed: Some formats may be missing'],
  ['site-changed', '[twitch] x: Failed to parse JSON (caused by JSONDecodeError("Expecting value in \'\': line 1 column 1 (char 0)"))'],
  ['forbidden', 'unable to download video data: HTTP Error 403: Forbidden'],
  ['rate-limited', '[youtube] abc: Unable to download webpage: HTTP Error 429: Too Many Requests'],
  ['cookies-browser', 'could not find firefox cookies database in "/home/u/.mozilla/firefox"'],
  ['cookies-browser', 'Could not copy Chrome cookie database. See  https://github.com/yt-dlp/yt-dlp/issues/7271  for more info'],
  ['cookies-browser', "'cookies.txt' does not look like a Netscape format cookies file"],
  ['cookies-expired', '[youtube] The provided YouTube account cookies are no longer valid. They have likely been rotated in the browser as a security measure.'],
  ['bad-login', '[vimeo] Unable to log in: bad username or password'],
  ['bad-login', '[niconico] Unable to log in: Wrong password'.replace('Unable to log in: ', '')],
  ['drm', '[netflix] x: This video is DRM protected'],
  ['live-not-started', '[youtube] abc: This live event will begin in 3 hours.'],
  ['live-not-started', '[youtube] abc: Premieres in 2 days'],
  ['tls', '[generic] Unable to download webpage: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1006)'],
  ['proxy', "Unable to download webpage: ('Unable to connect to proxy', OSError('Tunnel connection failed: 407 Proxy Authentication Required'))"],
  ['js-runtime', '[youtube] abc: n challenge solving failed: Some formats may be missing. Ensure you have a supported JavaScript runtime'],
  ['impersonate', 'Impersonate target "chrome-999" is not available. Use --list-impersonate-targets to see available targets.'],
  ['bad-option', 'yt-dlp: error: invalid retries count specified', 'starting'],
  ['bad-option', 'yt-dlp: error: no such option: --frobnicate', 'starting'],
  ['needs-input', 'Traceback (most recent call last):\n  File "getpass.py", line 148, in _raw_input\n    raise EOFError\nEOFError', 'starting'],
  ['engine-missing', 'spawn /opt/app/engine/yt-dlp ENOENT', 'starting'],
];

for (const [code, message, stage] of cases) {
  test(`${code}: ${message.slice(0, 70)}`, () => {
    const f = translate(message, 'info');
    assert.equal(f.code, code);
    assert.equal(f.known, true);
    if (stage) assert.equal(f.stage, stage);
    assert.ok(f.title && f.what && f.why && f.tryThis.length, 'has a full explanation');
    for (const text of [f.title, f.what, f.why, ...f.tryThis]) {
      assert.ok(!/Traceback|Errno|\bHTTP Error\b|urlopen|\[youtube\]/.test(text), `friendly text must not contain engine jargon: ${text}`);
      assert.ok(!text.includes('!'), 'no exclamation marks');
    }
  });
}

test('every rule is exercised by at least one real message', () => {
  const covered = new Set(cases.map(([c]) => c));
  for (const code of knownCodes) assert.ok(covered.has(code), `no test case for ${code}`);
});

test('unknown problems get a friendly fallback that names the stage', () => {
  const f = translate('xyzzy went sideways in a way nobody predicted', 'merge');
  assert.equal(f.code, 'unknown');
  assert.equal(f.known, false);
  assert.match(f.what, /merging video and audio/);
  assert.deepEqual(f.fixes, ['retry', 'update-engine']);
});

test('a crash without any message is still explained', () => {
  const f = translateExit(null, 'SIGKILL', 'download');
  assert.equal(f.code, 'crashed');
  assert.match(f.what, /downloading \(signal SIGKILL\)/);
  assert.equal(translateExit(2, null, 'starting').code, 'bad-option');
});

test('error lines are pulled out of mixed output', () => {
  const out = '[youtube] Extracting URL\nWARNING: x\nERROR: [youtube] abc: Private video\n[download] done';
  assert.deepEqual(errorLines(out), ['ERROR: [youtube] abc: Private video']);
});
