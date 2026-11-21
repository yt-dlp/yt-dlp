"""tango.me live streams.

The public web player is a canvas player fed by HLS.  Everything needed to
record a stream is reachable anonymously through the site's own web API:

    check-in            -> visitor cookies (Tango-VT / Tango-SD / Tango-DeviceId)
    .../stream/{id}/watch -> registers this viewer for the stream and returns the
                              stream document (settings, status, all HLS URLs)
    token-data             -> short-lived CDN token ({token, username, expireAt})

The CDN (``cinema-*.tango.me``) protects *playlists* with a cookie triplet
``tt``/``ttu``/``tte`` that expires after ~10 seconds, while media *segments*
are public.  Left alone, a live recording therefore dies a few seconds in, so
the token is re-issued on demand for as long as downloading continues.

A logged-in browser session (``--cookies-from-browser chrome``) is honoured for
streams a visitor cannot see; the token refresh still runs on top of it.
"""

import base64
import contextlib
import http.server
import json
import os
import re
import socketserver
import sys
import threading
import time
import urllib.parse
import uuid

from .common import InfoExtractor
from ..networking import Request
from ..networking.exceptions import HTTPError, TransportError
from ..utils import (
    ExtractorError,
    UserNotLive,
    int_or_none,
    traverse_obj,
    url_or_none,
)

_API_BASE = 'https://www.tango.me/api'

_STREAM_ID_RE = r'[A-Za-z0-9_-]{22}'

# The watch endpoint answers a semantic code instead of an HTTP status.  Each
# failure has a different cause and therefore a different fix, so the code is
# translated rather than echoed.
_WATCH_ERRORS = {
    'FAILED_WRONG_STREAM_ID': 'No tango.me stream has that id',
    'FAILED_TERMINATED': 'The stream has ended',
    'FAILED_BAD_REQUEST': 'tango.me refused the stream lookup; audio rooms are the usual cause',
}

# Site pages that match the URL pattern but carry no stream or profile.  tango
# sends clients without JavaScript to ``noscript.html``; ``watch`` cannot parse
# that as an id and the alias path would misreport it as a missing profile.
_NON_CONTENT_ROUTES = frozenset({'noscript.html'})


class TangoTokenRefresher:
    """Keeps the CDN auth cookies fresh.

    The CDN accepts playlists only while the cookie triplet ``tt``/``ttu``/
    ``tte`` is unexpired, and denies it after roughly ten seconds.  The token
    is therefore re-issued on demand; :class:`TangoHlsRelay` asks for one
    every time ffmpeg reloads a playlist.

    The relay sends the triplet in its own ``Cookie`` request header; it does
    not rely on yt-dlp's cookie jar, which ffmpeg cannot read.  The
    ``token-data`` reply does set ``tt``/``ttu``/``tte`` (``Max-Age=10``) and
    ``datadome`` itself, so they do land in the jar briefly;
    ``_drop_bot_cookies`` removes ``datadome`` and ``_dd_s`` at each session
    step.
    """

    # Refresh this many seconds before the token expires.  The token lives ten
    # seconds and the endpoint is rate limited, so refresh late but not last.
    MARGIN = 2.0

    # After a failed refresh, wait this long before the next attempt while
    # the cached token still works.  A failing refresh costs three token
    # calls, a check-in and three seconds of sleeps under the lock, and every
    # playlist reload would otherwise pay it again.
    COOLDOWN = 5.0
    FORCED_COOLDOWN = 2.0

    def __init__(self, ie, video_id):
        self.ie = ie
        self.video_id = video_id
        self.expires = 0.0
        self.username = None
        self._token = None
        self._failed_at = None
        self._lock = threading.Lock()

    @property
    def token(self):
        return self._token

    def _store(self, token, username, expires):
        self._token, self.username, self.expires = token, username, float(expires)

    def cookie_header(self):
        self.ensure()
        return f'tt={self._token}; ttu={self.username}; tte={int(self.expires)}'

    def refresh(self):
        # note=False, not None: yt-dlp prints its default "Downloading
        # webpage" line for None, and a refresh happens every eight seconds.
        data = self.ie._issue_token(self.video_id, note=False)
        self._store(data['token'], data['username'], data['expireAt'])
        self.ie.write_debug(f'Stream token refreshed (expires at {int(self.expires)})')

    def ensure(self, force=False):
        with self._lock:
            now = time.time()
            if not force and now < self.expires - self.MARGIN:
                return
            if self._failed_at is not None and now < self.expires:
                cooldown = self.FORCED_COOLDOWN if force else self.COOLDOWN
                if time.monotonic() - self._failed_at < cooldown:
                    return
            try:
                self.refresh()
                self._failed_at = None
            except Exception as err:  # noqa: BLE001 - never break a request over this
                self._failed_at = time.monotonic()
                self.ie.report_warning(f'Could not refresh stream token: {err}')


# What ffmpeg gets once the CDN has thrown the real media playlist away:
# structurally valid, nothing left in it, so playback finalises at once.
_ENDED_MEDIA_PLAYLIST = b'#EXTM3U\n#EXT-X-VERSION:7\n#EXT-X-TARGETDURATION:1\n#EXT-X-ENDLIST\n'


def _end_playlist(body):
    """Mark a cached media playlist as finished, so ffmpeg stops cleanly."""
    if b'#EXT-X-STREAM-INF' in body or b'#EXT-X-ENDLIST' in body:
        return body
    return body.rstrip(b'\n') + b'\n#EXT-X-ENDLIST\n'


_MEDIA_SEQUENCE_RE = re.compile(r'^#EXT-X-MEDIA-SEQUENCE:(\d+)')
_DISCONTINUITY_SEQUENCE_RE = re.compile(r'^#EXT-X-DISCONTINUITY-SEQUENCE:(\d+)')

# Playlist-level tags belong in the header.  Everything else that starts with
# '#' describes the segment that follows it (#EXTINF, EXT-X-PROGRAM-DATE-TIME,
# EXT-X-KEY, ...), so it must travel with that segment rather than stay in the
# header; otherwise a merged window lists all the segment tags before all the
# URIs, which ffmpeg reads as malformed.
_HEADER_TAGS = (
    '#EXTM3U',
    '#EXT-X-VERSION',
    '#EXT-X-TARGETDURATION',
    '#EXT-X-MEDIA-SEQUENCE',
    '#EXT-X-DISCONTINUITY-SEQUENCE',
    '#EXT-X-PLAYLIST-TYPE',
    '#EXT-X-INDEPENDENT-SEGMENTS',
    '#EXT-X-I-FRAMES-ONLY',
    '#EXT-X-START',
)


def _split_media_playlist(text):
    """Split a media playlist into header, segment chunks, and end marker.

    A chunk is the block of tags that applies to one segment plus its URI,
    so a key rotation, a date stamp or a discontinuity stays attached to the
    right segment.
    """
    header, chunks, pending = [], [], []
    ended = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == '#EXT-X-ENDLIST':
            ended = True
        elif line.startswith(_HEADER_TAGS):
            header.append(line)
        elif line.startswith('#'):
            pending.append(line)
        else:
            chunks.append((pending, line))
            pending = []
    return header, chunks, ended


def _segment_number(uri):
    """Media sequence for a playlist that omits EXT-X-MEDIA-SEQUENCE.

    tango names each segment after its sequence number (``5123.ts``), which
    is the only ordering signal left once the tag is missing.
    """
    name = urllib.parse.urlsplit(uri).path.rsplit('/', 1)[-1].split('.')[0]
    return int_or_none(name)


class _MediaWindow:
    """Rolling union of recent media playlists for one live stream.

    The CDN serves an eight-segment sliding window.  ffmpeg asks for the
    segment after the last one it played, so a playlist reload that arrives
    late makes it skip whatever slid out in the meantime; ffmpeg logs those
    as ``skipping N segments`` and the recording ends up short.  Serving the
    union of recent playlists removes the gap.  The relay never polls; it
    merges only when ffmpeg asks for a playlist, so the window covers ffmpeg
    running up to about ``size`` seconds behind the live edge, but a gap of
    more than the CDN's ~8 s window between two reloads still loses the
    segments in between.

    ``size`` is bounded by the CDN's segment retention (measured at ~70 s:
    a segment still downloads at 60 s old and comes back zero-length at 80),
    so old entries must be dropped well before they expire.
    """

    def __init__(self, size):
        self.size = size
        self._chunks = {}  # media sequence -> (tag lines, uri)
        self._carried = []  # key/map tags of the last pruned segment
        self._discontinuities = 0  # EXT-X-DISCONTINUITY lines pruned away
        self._ended = False

    def merge(self, text):
        header, chunks, ended = _split_media_playlist(text)
        if not chunks:
            return text
        base = None
        for line in header:
            match = _MEDIA_SEQUENCE_RE.match(line)
            if match:
                base = int(match.group(1))
                break
        if base is None:
            base = _segment_number(chunks[0][1])
        if base is None:
            base = 0

        fresh = {base + index: chunk for index, chunk in enumerate(chunks)}
        if self._chunks and max(fresh) < min(self._chunks):
            # The numbering restarted (a new broadcast on the same URL), so
            # the old segments cannot be stitched onto the new ones.
            self._chunks.clear()
            self._carried = []
            self._discontinuities = 0
        self._chunks.update(fresh)
        self._ended = self._ended or ended
        self._prune()
        return self._render(header)

    def _prune(self):
        while len(self._chunks) > self.size:
            tags, _ = self._chunks.pop(min(self._chunks))
            key_map = [tag for tag in tags if tag.startswith(('#EXT-X-KEY:', '#EXT-X-MAP:'))]
            if key_map:
                self._carried = key_map
            self._discontinuities += sum(tag == '#EXT-X-DISCONTINUITY' for tag in tags)

    def _render(self, header):
        first = min(self._chunks)
        has_sequence = any(_MEDIA_SEQUENCE_RE.match(line) for line in header)
        has_discontinuities = any(_DISCONTINUITY_SEQUENCE_RE.match(line) for line in header)
        lines = []
        for line in header:
            match = _MEDIA_SEQUENCE_RE.match(line)
            if match:
                lines.append(f'#EXT-X-MEDIA-SEQUENCE:{first}')
            elif _DISCONTINUITY_SEQUENCE_RE.match(line):
                start = int(_DISCONTINUITY_SEQUENCE_RE.match(line).group(1))
                lines.append(f'#EXT-X-DISCONTINUITY-SEQUENCE:{start + self._discontinuities}')
            else:
                lines.append(line)
                if line.startswith('#EXT-X-TARGETDURATION') and not has_sequence:
                    lines.append(f'#EXT-X-MEDIA-SEQUENCE:{first}')
        if not has_sequence and not any(line.startswith('#EXT-X-TARGETDURATION') for line in header):
            lines.append(f'#EXT-X-MEDIA-SEQUENCE:{first}')
        if self._discontinuities and not has_discontinuities:
            lines.append(f'#EXT-X-DISCONTINUITY-SEQUENCE:{self._discontinuities}')
        # A key or init map still applies to the segments after the one that
        # declared it, so it is re-emitted when that segment is pruned away.
        first_tags = self._chunks[first][0]
        lines.extend(tag for tag in self._carried if tag not in first_tags)
        for seq in sorted(self._chunks):
            tags, uri = self._chunks[seq]
            lines.extend(tags)
            lines.append(uri)
        if self._ended:
            lines.append('#EXT-X-ENDLIST')
        return '\n'.join(lines) + '\n'


class _TangoRelayHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'
    # A stalled ffmpeg request must not hold a handler thread forever.
    timeout = 30

    def _respond(self, send_body):
        try:
            status, content_type, body = self.server.relay.fetch(self.path)
        except Exception as err:  # noqa: BLE001
            self.send_error(502, str(err))
            return
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        if send_body:
            self.wfile.write(body)

    def do_GET(self):
        self._respond(send_body=True)

    def do_HEAD(self):
        self._respond(send_body=False)

    def log_message(self, *args):
        pass


class _TangoRelayServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        # ffmpeg hanging up mid-response (Ctrl-C, end of input) is routine;
        # the default handler prints a traceback for it.
        if isinstance(sys.exc_info()[1], ConnectionError):
            return
        super().handle_error(request, client_address)


# Hosts ffmpeg reaches the relay on.  Both loopback spellings are listed
# because the bypass list is matched as text, not resolved.
_LOOPBACK_HOSTS = ('127.0.0.1', 'localhost')


def _exempt_loopback_from_proxy(environ=None):
    """Keep the loopback relay out of an inherited HTTP proxy.

    ffmpeg applies ``--proxy`` (and ``http_proxy``) to every request it makes,
    including the local HLS relay, so a proxied ffmpeg never reaches the relay
    and the recording stalls.  The bypass list is extended instead of
    overridden, and both variable spellings are set because ffmpeg reads the
    lowercase one while other tools read the uppercase one.  Entries already
    present are kept as they are, so a second call changes nothing.
    """
    environ = os.environ if environ is None else environ
    for name in ('no_proxy', 'NO_PROXY'):
        entries = [entry.strip() for entry in environ.get(name, '').split(',')]
        entries = [entry for entry in entries if entry]
        present = {entry.lower() for entry in entries}
        missing = [host for host in _LOOPBACK_HOSTS if host not in present]
        if missing:
            environ[name] = ','.join(entries + missing)


class TangoHlsRelay:
    """Local HLS relay in front of the tango CDN.

    yt-dlp always hands live HLS to ffmpeg, and ffmpeg cannot refresh
    cookies, so its playlist reloads would die with the token.  ffmpeg is
    pointed at this loopback server instead: the HLS manifest is fetched with
    a fresh token every time, and the (unauthenticated) media segments are
    rewritten to go straight to the CDN.
    """

    IDLE_TIMEOUT = 900

    # If the token endpoint throttles us, keep ffmpeg alive by replaying the
    # last playlist that did load.  Measured throttles lasted ~90 s, and the
    # window is keyed by media sequence, so ffmpeg sees an unchanged playlist
    # and stalls until the token returns; segments are lost only if that
    # takes longer than the CDN keeps them.
    STALE_PLAYLIST_MAX_AGE = 120

    # Segments kept in the merged media playlist (one second each).  The CDN
    # refuses segments older than ~70 s, so this leaves room for the merge to
    # lag behind the live edge without serving an empty body.
    PLAYLIST_WINDOW = 45

    def __init__(self, refresher, master_url):
        self.refresher = refresher
        parts = urllib.parse.urlsplit(master_url)
        # Every upstream request carries the CDN token, and the watch
        # document names the host, so only tango's own hosts are relayed.
        if not (parts.hostname or '').endswith('.tango.me'):
            raise ExtractorError(f'tango.me returned a playlist on another host ({parts.hostname})', expected=True)
        self.upstream = f'{parts.scheme}://{parts.netloc}'
        self.master_path = parts.path + (f'?{parts.query}' if parts.query else '')
        # Monotonic, so a laptop that sleeps mid-recording does not wake to
        # an idle timeout.
        self._last_request = time.monotonic()
        self._cache = {}
        self._served = set()
        self._windows = {}
        self._state = threading.RLock()
        self._closed = threading.Event()
        self._warned_stale = False
        self._warned_ended = False
        self._server = _TangoRelayServer(('127.0.0.1', 0), _TangoRelayHandler)
        self._server.relay = self
        self.port = self._server.server_address[1]
        threading.Thread(target=self._server.serve_forever, daemon=True, name='tango-hls-relay').start()
        threading.Thread(target=self._reap, daemon=True, name='tango-hls-relay-reaper').start()

    def url(self):
        return f'http://127.0.0.1:{self.port}{self.master_path}'

    def close(self):
        self._closed.set()
        try:
            self._server.shutdown()
            self._server.server_close()
        except Exception:  # noqa: BLE001
            pass

    def _reap(self):
        while not self._closed.wait(60):
            if time.monotonic() - self._last_request > self.IDLE_TIMEOUT:
                self.close()
                return

    def fetch(self, path):
        # An origin-form path is the only shape this relay serves.  Anything
        # else (absolute-form, or an '@' authority) would be concatenated onto
        # the upstream host and could carry the token cookie elsewhere.
        if not path.startswith('/') or path.startswith('//'):
            return 400, 'text/plain', b'bad request path\n'
        self._last_request = time.monotonic()
        with self._state:
            cached = self._cache.get(path)
        # A playlist this relay already ended stays ended: the CDN would only
        # answer 404 again, so ffmpeg is served from the cache.
        if cached and b'#EXT-X-ENDLIST' in cached[0]:
            return 200, 'application/vnd.apple.mpegurl', cached[0]
        url = f'{self.upstream}{path}'
        last_error = None
        # Two tries: the token may have expired between playlist reloads.  The
        # token path already retries internally, so more here only adds load
        # to a throttled endpoint.
        for attempt in range(2):
            if attempt:
                self.refresher.ensure(force=True)
                time.sleep(1)
            request = Request(
                url,
                headers={
                    'Cookie': self.refresher.cookie_header(),
                    'Origin': 'https://www.tango.me',
                    'Referer': 'https://www.tango.me/',
                    'Accept': '*/*',
                },
                extensions={'timeout': 30},
            )
            try:
                with self.refresher.ie._downloader.urlopen(request) as response:
                    body = response.read()
                    content_type = response.headers.get('Content-Type') or 'text/plain'
                break
            except HTTPError as err:
                last_error = err
                # The CDN throws playlists away when the broadcast stops, so
                # a 404/410 for one this relay already served or emitted means
                # the stream is over: end the recording instead of failing it.
                # Checked before the retry decision, so an ended stream does
                # not burn a token refresh.
                if err.status in (404, 410):
                    with self._state:
                        served = path in self._served
                    if served:
                        body = _end_playlist(cached[0] if cached else _ENDED_MEDIA_PLAYLIST)
                        with self._state:
                            self._cache[path] = (body, 'application/vnd.apple.mpegurl', time.time())
                        if not self._warned_ended:
                            self.refresher.ie.report_warning(
                                'The stream has ended (the CDN answered 404); finishing the recording',
                            )
                            self._warned_ended = True
                        return 200, 'application/vnd.apple.mpegurl', body
                if err.status not in (401, 403, 500, 502, 503, 504):
                    raise
            except TransportError as err:
                last_error = err
        else:
            if cached:
                age = time.time() - cached[2]
                if age < self.STALE_PLAYLIST_MAX_AGE:
                    if not self._warned_stale:
                        self.refresher.ie.report_warning(
                            'Stream token refresh is being throttled; replaying the last playlist until it recovers',
                        )
                        self._warned_stale = True
                    return 200, cached[1], cached[0]
                # Too long without a token.  End the playlist so ffmpeg
                # finalises the file instead of failing a long recording.
                self.refresher.ie.report_warning(
                    'Could not refresh the stream token for over '
                    f'{self.STALE_PLAYLIST_MAX_AGE}s; ending the recording '
                    'cleanly',
                )
                return 200, cached[1], _end_playlist(cached[0])
            raise last_error

        self._warned_stale = False

        with self._state:
            self._served.add(path)
            if body.lstrip().startswith(b'#EXTM3U'):
                body = self._rewrite_playlist(body, url, path)
                content_type = 'application/vnd.apple.mpegurl'
            self._cache[path] = (body, content_type, time.time())
        return 200, content_type, body

    def _merge_media_playlist(self, path, text):
        """Serve the union of recent playlists for this stream.

        Only for media playlists; the caller keeps masters on their own
        rewrite path because their entries are variants, not segments.
        """
        with self._state:
            window = self._windows.get(path)
            if window is None:
                window = self._windows[path] = _MediaWindow(self.PLAYLIST_WINDOW)
            return window.merge(text)

    def _rewrite_playlist(self, body, upstream_url, path=None):
        """Point ffmpeg at the CDN for segments, at the relay for playlists.

        Media segments are public, so ffmpeg can fetch them directly (no
        Python in the video path).  Variant playlists still need a fresh
        token, so they stay behind the relay.
        """
        text = body.decode('utf-8', 'replace')
        if '#EXT-X-STREAM-INF' in text:

            def relay_relative(match):
                uri = urllib.parse.urljoin(upstream_url, match.group(1))
                parts = urllib.parse.urlsplit(uri)
                path = parts.path + (f'?{parts.query}' if parts.query else '')
                # The variant now counts as served: if the CDN later answers
                # 404 for it, the recording ends instead of failing.
                self._served.add(path)
                return path

            return re.sub(r'^(?!#)(\S+)$', relay_relative, text, flags=re.MULTILINE).encode()

        if path is None:
            parts = urllib.parse.urlsplit(upstream_url)
            path = parts.path + (f'?{parts.query}' if parts.query else '')
        # A playlist that already ends on first sight is a finished recording:
        # complete as served, and the live window would cut it.  A live stream
        # that ends still merges, or a lagging ffmpeg loses the segments
        # between the last merged reload and this one.
        if '#EXT-X-ENDLIST' not in text or path in self._windows:
            text = self._merge_media_playlist(path, text)

        def absolute(match):
            prefix, uri, suffix = match.groups()
            return f'{prefix}{urllib.parse.urljoin(upstream_url, uri)}{suffix}'

        text = re.sub(r'(#EXT-X-(?:MAP|KEY):[^\n]*?URI=")([^"]+)(")', absolute, text)
        lines = []
        for line in text.splitlines():
            if line and not line.startswith('#'):
                line = urllib.parse.urljoin(upstream_url, line)
            lines.append(line)
        return ('\n'.join(lines) + '\n').encode()


class TangoBase(InfoExtractor):
    _API_BASE = _API_BASE

    # ------------------------------------------------------------------ HTTP

    def _api_headers(self, **extra):
        headers = {
            'Accept': 'application/json',
            'Origin': 'https://www.tango.me',
            'Referer': 'https://www.tango.me/',
            'foreground-id': str(uuid.uuid4()),
            'interaction-id': str(uuid.uuid4()),
            'x-app-client-session-id': str(uuid.uuid4()),
        }
        headers.update(extra)
        return headers

    def _retry(self, func, *, fatal=True):
        """Run a control call through yt-dlp's extractor retry budget.

        ``fatal=False`` warns and returns ``None`` when the budget runs out.
        ``fatal=True`` re-raises the last failure as unexpected: yt-dlp marks
        transport errors 'expected' (not a bug in yt-dlp), but for a control
        call the site is at fault, not the URL.  401 and 403 are answers,
        not transient failures, so they are not retried.
        """
        try:
            for retry in self.RetryManager(fatal=fatal):
                try:
                    return func()
                except ExtractorError as err:
                    if getattr(err.cause, 'status', None) in (401, 403):
                        raise
                    retry.error = err
        except ExtractorError as err:
            raise ExtractorError(err.orig_msg, cause=err.cause, video_id=err.video_id) from err
        return None

    def _api_json(self, path, video_id, note, query=None, data=None, headers=None, fatal=True, expected_status=None):
        return self._download_json(
            f'{self._API_BASE}{path}',
            video_id,
            note=note,
            query=query,
            data=data,
            fatal=fatal,
            expected_status=expected_status,
            headers=self._api_headers(**(headers or {})),
        )

    # --------------------------------------------------------------- session

    # Cookies that only make sense to the JavaScript player.  ``datadome`` /
    # ``_dd_s`` are bound to the browser's TLS fingerprint; replaying them
    # from Python invites a bot challenge.
    _DROP_COOKIES = {'datadome', '_dd_s'}

    # Cookies that identify the anonymous visitor.  The token endpoint
    # throttles per identity, and a fresh identity recovers where a retry of
    # the throttled one keeps getting 403.
    _VISITOR_COOKIES = {'Tango-VT', 'Tango-SD', 'Tango-DI', 'Tango-DeviceId'}

    # Whether this extractor issued the visitor token itself (a check-in), as
    # opposed to reusing one found in the jar.
    _checked_in = False

    def _jar_lock(self):
        """The jar's own lock: relay threads write it while we read it."""
        return getattr(self._downloader.cookiejar, '_cookies_lock', None) or contextlib.nullcontext()

    def _jar_cookies(self):
        """A snapshot of the shared jar, safe against concurrent writes."""
        jar = self._downloader.cookiejar
        with self._jar_lock():
            try:
                return list(jar)
            except RuntimeError:
                # Every write here takes the lock, so this only covers a jar
                # without one, changed by another writer mid-iteration.
                return list(jar)

    def _drop_cookies(self, names, keep_domain_prefix=None):
        jar = self._downloader.cookiejar
        with self._jar_lock():
            for cookie in self._jar_cookies():
                if cookie.name not in names and cookie.name.lower() not in names:
                    continue
                if keep_domain_prefix and cookie.domain.startswith(keep_domain_prefix):
                    continue
                with contextlib.suppress(KeyError):
                    jar.clear(cookie.domain, cookie.path, cookie.name)

    def _drop_bot_cookies(self):
        self._drop_cookies(self._DROP_COOKIES)

    def _reset_visitor(self):
        """Forget the anonymous identity, keeping any account session.

        A logged-in browser stores its session descriptor on ``.www.tango.me``
        while the visitor one lands on ``www.tango.me``, so the dot-prefixed
        cookie is kept.
        """
        self._drop_cookies(self._VISITOR_COOKIES, keep_domain_prefix='.www.')

    def _has_visitor_token(self):
        """Whether the jar holds an unexpired visitor JWT (``Tango-VT``).

        A token whose expiry cannot be read is not usable: a check-in is
        cheaper than a run that fails at ``watch``.
        """
        for cookie in self._jar_cookies():
            if cookie.name == 'Tango-VT' and cookie.value:
                try:
                    payload = cookie.value.split('.')[1]
                    payload += '=' * (-len(payload) % 4)
                    expires = json.loads(base64.urlsafe_b64decode(payload))['exp']
                except (IndexError, KeyError, TypeError, ValueError):
                    return False
                if isinstance(expires, bool) or not isinstance(expires, (int, float)):
                    return False
                return expires > time.time()
        return False

    def _account_cookies(self):
        # The account session descriptor is the dot-prefixed Tango-SD; the
        # visitor one is left to the server.
        return [
            cookie
            for cookie in self._jar_cookies()
            if cookie.name in ('Tango-ST', 'Tango-RT', 'Tango-WST')
            or (cookie.name == 'Tango-SD' and cookie.domain.startswith('.www.'))
        ]

    def _check_in(self, video_id, note='Registering visitor'):
        # The check-in reply expires the client copies of the account tokens
        # (epoch Set-Cookie), which would log a --cookies-from-browser session
        # out before `watch`.  Restored even when the reply is unusable.
        account = self._account_cookies()
        try:
            data = self._api_json(
                '/visitor-lobby/api/public/visitors/v1/check-in',
                video_id,
                note=note,
                query={'appId': 'tango'},
                data=b'{}',
                headers={'Content-Type': 'application/json'},
            )
            if not isinstance(data, dict):
                raise ExtractorError('tango.me visitor registration failed')
            self._checked_in = True
        finally:
            self._restore_account_cookies(account)

    def _restore_account_cookies(self, snapshot):
        """Re-add snapshotted account cookies that are no longer in the jar.

        Only a missing (domain, path, name) is re-added, so a cookie the
        server rotated in the meantime wins over the snapshot.
        """
        jar = self._downloader.cookiejar
        with self._jar_lock():
            present = {(c.domain, c.path, c.name) for c in self._jar_cookies()}
            for cookie in snapshot:
                if (cookie.domain, cookie.path, cookie.name) not in present:
                    jar.set_cookie(cookie)

    def _ensure_session(self, video_id, force=False):
        """Make sure the cookie jar holds a visitor identity.

        The token endpoint is a *visitor* endpoint: even a logged-in browser
        session has to check in before it can be issued a CDN token.  The
        check-in expires the account cookies, so they are restored after it
        and a private stream still sees them.
        """
        self._drop_bot_cookies()
        if not force and self._has_visitor_token():
            # The instance outlives a run (--wait-for-video re-extracts), so
            # an earlier run's check-in must not disable _watch's self-heal.
            self._checked_in = False
            return
        if force:
            self._reset_visitor()
        self._check_in(video_id, note=('Re-registering visitor' if force else 'Registering visitor'))

    def _issue_token(self, video_id, note='Obtaining stream token'):
        """Fetch a CDN token, retrying with a fresh visitor identity.

        The endpoint answers 403 when it throttles an identity.  A new visitor
        check-in gets a token where retrying the throttled identity does not,
        so the second attempt resets it.  Errors are swallowed here and
        reported once by the caller, to keep the log readable.

        The account cookies are left in the jar.  This runs on a daemon relay
        thread every few seconds, so taking them out and restoring them would
        leave a window in which a Ctrl-C saves a --cookies file without them.
        The endpoint is a visitor endpoint, the measured cure for a 403 is a
        fresh visitor identity (``_reset_visitor``), and with the account
        cookies an account-bound token can be issued, which a followers-only
        stream may need.  Whether they change the 403 recovery is unmeasured.
        """
        last_error = None
        for attempt in range(3):
            try:
                data = self._api_json(
                    '/stream/token-data/v1/web/visitor', video_id, note=note if not attempt else 'Retrying stream token',
                )
            except ExtractorError as err:
                last_error = err
                data = None
            if isinstance(data, dict) and data.get('token'):
                return {
                    'token': data['token'],
                    'username': data.get('username') or '',
                    'expireAt': int(data['expireAt']),
                }
            if attempt == 0:
                try:
                    self._ensure_session(video_id, force=True)
                except ExtractorError as err:
                    last_error = err
            if attempt < 2:
                time.sleep(2**attempt)
        raise last_error or ExtractorError('tango.me did not return a stream token')

    # -------------------------------------------------------------- resolving

    @staticmethod
    def _id_from_body(body):
        """Accept a response body only when it is shaped like a tango id.

        The lookups answer 404 with whatever the gateway or CDN sent; an HTML
        error page must read as "no profile" rather than travel on as if it
        were an id.
        """
        body = (body or '').strip()
        return body if re.fullmatch(_STREAM_ID_RE, body) else ''

    def _not_live(self, label, account_id=None):
        """A ``UserNotLive`` that says what to do about it.

        The hint is omitted when the caller already asked yt-dlp to wait, so
        the per-cycle warning does not repeat instructions back at them.
        """
        note = ''
        if account_id and account_id != label:
            note = f' (account {account_id})'
        elif account_id and re.fullmatch(_STREAM_ID_RE, label):
            # A 22-char value that the alias lookup rejected is used as the
            # account id; saying so turns a typo into a diagnosable answer.
            note = ' (treated as an account id)'
        hint = '' if self.get_param('wait_for_video') else ('; retry with --wait-for-video 60 to wait for it')
        return UserNotLive(f'tango.me profile "{label}" is not live{note}{hint}', video_id=label)

    def _resolve_stream_id(self, alias_or_id, *, is_profile=False):
        """Resolve an identifier to its current live stream.

        Returns ``(stream_id, account_id)``.  A profile page accepts either
        the alias or the 22-char account id, so the account id is returned
        for metadata lookup even when the URL carried the alias.

        A stream URL carries a 22-char stream id; a profile URL carries an
        alias or, just as validly, the 22-char account id from the site's own
        profile data.  The two id shapes are indistinguishable, so the URL form
        decides: ``is_profile`` never reads its identifier as a stream id.
        """
        identifier = urllib.parse.unquote(alias_or_id or '').lstrip('@')
        if not is_profile and re.fullmatch(_STREAM_ID_RE, identifier):
            return identifier, None
        # A rejected alias or an offline broadcaster answers 404, which is a
        # semantic answer rather than a transport failure: accept it so the
        # retry budget is not spent on it.
        account_id = self._id_from_body(
            self._retry(
                lambda: self._download_webpage(
                    f'{self._API_BASE}/visitors/profilealias/api/alias/convert',
                    identifier,
                    note='Resolving profile alias',
                    query={'alias': identifier},
                    fatal=True,
                    expected_status=404,
                    headers=self._api_headers(),
                ),
            ),
        )
        if not account_id and is_profile and re.fullmatch(_STREAM_ID_RE, identifier):
            # Profile pages accept the account id directly; there is no alias
            # to convert in that case.
            account_id = identifier
        if not account_id:
            raise ExtractorError(f'No tango.me profile found for "{identifier}"', expected=True)
        stream_id = self._id_from_body(
            self._retry(
                lambda: self._download_webpage(
                    f'{self._API_BASE}/showroom-streams/api/public/stream/v1/id',
                    identifier,
                    note='Looking for a live stream',
                    query={'broadcasterId': account_id},
                    fatal=True,
                    expected_status=404,
                    headers=self._api_headers(),
                ),
            ),
        )
        if not stream_id:
            raise self._not_live(identifier, account_id)
        return stream_id, account_id

    def _watch(self, stream_id, *, profile=None):
        """Register as a viewer and return the stream document.

        A visitor token reused from the jar can be unexpired yet refused by
        the server, so a 401 or 403 for one re-registers once and retries
        before blaming the stream's visibility.
        """
        for attempt in range(2):
            try:
                data = self._retry(
                    lambda: self._api_json(
                        f'/visitors/stream/client/v2/stream/{stream_id}/watch',
                        stream_id,
                        note='Joining stream',
                        query={'requestId': ''},
                        data=b'',
                        headers={'Content-Type': 'application/json'},
                    ),
                )
                break
            except ExtractorError as err:
                if getattr(err.cause, 'status', None) not in (401, 403):
                    raise
                if attempt or self._checked_in:
                    raise ExtractorError(
                        'tango.me refused the stream lookup. For a followers-only '
                        'or private stream, retry with --cookies-from-browser chrome',
                        expected=True,
                        cause=err,
                    ) from err
                self._ensure_session(stream_id, force=True)
        if not isinstance(data, dict):
            raise ExtractorError('tango.me stream lookup failed', expected=True)
        code = data.get('code')
        if code != 'OK' or not data.get('details', {}).get('stream'):
            # A profile can point at the stream that just ended.  For a
            # profile URL that means "not live now", so --wait-for-video can
            # re-resolve; a stream URL keeps the explicit "has ended" answer.
            if profile and code == 'FAILED_TERMINATED':
                raise self._not_live(profile)
            raise ExtractorError(
                (_WATCH_ERRORS.get(code) if isinstance(code, str) else None)
                or f"tango.me returned {code or 'no data'}",
                expected=True,
            )
        return data

    def _profile_metadata(self, video_id, alias=None):
        """Best-effort metadata from the server-rendered profile or stream page.

        A profile page (``tango.me/<alias>``) renders a schema.org
        ``ProfilePage`` with the display name, alias, avatar, bio and follower
        count, and it does so whether the broadcaster is live or offline.  A
        stream page only carries the live title, which names the broadcaster
        and their alias; that is the fallback when only a stream id is known.
        """
        if alias:
            url = f"https://www.tango.me/{urllib.parse.quote(alias, safe='')}"
            note = 'Downloading profile page'
        else:
            url = f'https://www.tango.me/stream/{video_id}'
            note = 'Downloading stream page'
        html = self._download_webpage(url, video_id, note=note, fatal=False) or ''
        title = self._og_search_property('title', html, default='') or ''
        name = profile_alias = description = thumbnail = followers = None
        for data in self._yield_json_ld(html, video_id, default=None):
            items = data.get('@graph')
            items = items if isinstance(items, list) else [data]
            for item in items:
                main = item.get('mainEntity') if isinstance(item, dict) else None
                for entity in main if isinstance(main, list) else [main]:
                    if not isinstance(entity, dict):
                        continue
                    if isinstance(entity.get('identifier'), str):
                        profile_alias = entity['identifier'] or profile_alias
                    if isinstance(entity.get('name'), str):
                        name = entity['name'] or name
                    if isinstance(entity.get('description'), str):
                        description = entity['description'] or description
                    if isinstance(entity.get('image'), str):
                        thumbnail = url_or_none(entity['image']) or thumbnail
                    for stat in entity.get('interactionStatistic') or []:
                        if isinstance(stat, dict) and 'FollowAction' in str(stat.get('interactionType')):
                            count = int_or_none(stat.get('userInteractionCount'))
                            if count is not None:
                                followers = count
        match = re.search(r'\(@([^)\s]+)\)', title)
        if match:
            profile_alias = profile_alias or match.group(1)
            # The title carries the display name as the site renders it,
            # including emoji the schema.org name may have dropped.
            name = re.sub(r'\s*\(@[^)]*\).*$', '', title).strip() or name
        return {
            'name': name,
            'alias': profile_alias,
            'description': self._og_search_property('description', html, default=None) or description,
            'thumbnail': url_or_none(self._og_search_property('image', html, default=None)) or thumbnail,
            'followers': followers,
        }

    # --------------------------------------------------------------- formats

    def _hls_formats(self, playlist_url, video_id, live):
        # yt-dlp's --proxy map is {'all': proxy} with no 'no' entry, and
        # select_proxy only consults no_proxy when 'no' is present.  Its own
        # request to the loopback relay would therefore be tunnelled through
        # an off-host proxy, which cannot reach this machine's 127.0.0.1.
        # Fetching the master playlist with an explicit proxy bypass keeps
        # --proxy working; ffmpeg gets no_proxy for the rest.
        response = self._request_webpage(
            Request(playlist_url, proxies={'all': '__noproxy__'}),
            video_id,
            note='Downloading HLS manifest',
            fatal=False,
        )
        formats, subtitles = [], {}
        if response is not False:
            try:
                body = response.read().decode('utf-8', 'replace')
            finally:
                response.close()
            if body.lstrip().startswith('#EXTM3U'):
                formats, subtitles = self._parse_m3u8_formats_and_subtitles(
                    body, playlist_url, ext='mp4', live=live, fatal=False, video_id=video_id,
                )
        for f in formats:
            # 'm3u8' selects ffmpeg, which honours no_proxy.  The parser's
            # 'm3u8_native' lets yt-dlp pick its native HLS downloader for a
            # recording, and that sends the loopback relay through --proxy.
            f['protocol'] = 'm3u8'
            f['http_headers'] = dict(
                f.get('http_headers') or {}, Origin='https://www.tango.me', Referer='https://www.tango.me/',
            )
        return formats, subtitles

    def _relayed_formats(self, refresher, playlist_url, video_id, live, error):
        """Serve ``playlist_url`` through a new relay and read its formats.

        The relay must keep serving ffmpeg when extraction succeeds, so it is
        only closed here when we are about to leave without returning.
        """
        relay = TangoHlsRelay(refresher, playlist_url)
        try:
            _exempt_loopback_from_proxy()
            formats, subtitles = self._hls_formats(relay.url(), video_id, live=live)
            if not formats:
                raise ExtractorError(error, expected=True)
        except BaseException:
            relay.close()
            raise
        return formats, subtitles

    # ---------------------------------------------------------------- shared

    def _extract_stream(self, url, video_id, is_profile=False):
        self._ensure_session(video_id)
        # A profile URL identifies the broadcaster, by alias or account id;
        # either form is a profile page, so it supplies name and followers.
        profile_label = urllib.parse.unquote(video_id or '').lstrip('@') if is_profile else None
        stream_id, account_id = self._resolve_stream_id(video_id, is_profile=is_profile)

        data = self._watch(stream_id, profile=profile_label)
        details = data.get('details') or {}
        stream = details.get('stream') or {}
        settings = details.get('settings') or {}
        view_info = details.get('viewInfo') or {}
        hls_info = view_info.get('hlsStreamInfo') or {}

        status = stream.get('status') or ''
        is_live = status == 'LIVING'
        if not is_live:
            # A profile URL always means "the current live stream", so an
            # ended stream becomes a wait (--wait-for-video re-resolves the
            # alias).  A stream URL may still want its finished recording.
            if is_profile:
                raise self._not_live(profile_label)
            complete = stream.get('completeListUrl')
            if not complete:
                raise UserNotLive(video_id=stream_id)
            self.report_warning(
                f"Stream is not live (status: {status or 'unknown'}); falling back to the complete recording",
            )

        profile = self._profile_metadata(stream_id, alias=profile_label)
        alias = profile.get('alias') or profile_label
        name = profile.get('name') or alias or stream_id

        refresher = TangoTokenRefresher(self, stream_id)
        refresher.ensure(force=True)
        if not refresher.token:
            raise ExtractorError('tango.me did not issue a CDN token; retry the download', expected=True)

        master_url = traverse_obj(hls_info, 'masterUrl') or stream.get('masterListUrl') or stream.get('completeListUrl')
        if not master_url:
            raise ExtractorError('tango.me returned no HLS URL', expected=True)

        sep = '&' if '?' in master_url else '?'
        master_url = f'{master_url}{sep}accountId=&tech=lhls&label=pwatcf'
        if refresher.username:
            master_url = f"{master_url}&username={urllib.parse.quote(refresher.username, safe='')}"
        kind = 'live stream' if is_live else 'recording'
        formats, subtitles = self._relayed_formats(
            refresher,
            master_url,
            stream_id,
            is_live,
            f'The {kind} HLS manifest could not be read. '
            'For a followers-only or private stream retry with '
            '--cookies-from-browser chrome',
        )

        title = f'{name} (@{alias})' if alias and alias != name else name
        if is_live:
            title = f'{title} - Tango live'
        else:
            title = f'{title} - Tango recording'

        info = {
            'id': stream_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': is_live,
            'live_status': 'is_live' if is_live else 'was_live',
            'uploader': name,
            'uploader_id': alias,
            'display_id': alias,
            'channel': name,
            'channel_id': traverse_obj(details, ('anchor', 'encryptedAccountId'))
            or traverse_obj(stream, 'encryptedAccountId')
            or account_id,
            'channel_url': (f"https://www.tango.me/{urllib.parse.quote(alias, safe='')}" if alias else None),
            'uploader_url': (f"https://www.tango.me/{urllib.parse.quote(alias, safe='')}" if alias else None),
            'webpage_url': url,
            'thumbnail': traverse_obj(stream, 'thumbnail') or profile.get('thumbnail'),
            'description': profile.get('description'),
            'channel_follower_count': profile.get('followers'),
            'concurrent_view_count': int_or_none(details.get('viewerCount')),
            'view_count': int_or_none(details.get('uniqueViewerCount')),
            'tags': traverse_obj(details, ('tags', ...)),
            # Policy, not payload: six catalog items sampled on 2026-11-21 all
            # had isNsfw false and moderationLevel 2, so nothing to derive from.
            'age_limit': 18,
        }
        # The watch document reports how long the broadcast has been running,
        # so a live recording can be dated.  A finished recording's timestamp
        # would be its start, which the document does not carry.
        duration_ms = int_or_none(stream.get('duration')) if is_live else None
        if duration_ms is not None:
            info['timestamp'] = int(time.time()) - duration_ms // 1000
        if not settings.get('videoEnabled', True) or settings.get('audioRoom'):
            self.to_screen('This stream is audio-only')
        return info


class TangoFeedIE(TangoBase):
    """tango.me/live — the front-page feed of currently live streams."""

    IE_NAME = 'tango:live'
    _VALID_URL = r'https?://(?:www\.|m\.)?tango\.me/(?i:live)/?(?:[?#]|$)'
    _TESTS = [
        {
            'url': 'https://www.tango.me/live',
            'info_dict': {
                'id': 'live',
                'title': 'Tango live feed',
            },
            'playlist_mincount': 1,
            'params': {'extract_flat': True, 'skip_download': True},
        },
    ]

    def _real_extract(self, url):
        self._ensure_session('live')
        data = self._retry(
            lambda: self._api_json(
                '/showroom-streams/api/public/web/catalog/v1',
                'live',
                note='Downloading live feed',
                query={'traceId': str(uuid.uuid4())},
                data=json.dumps({'size': 30, 'platform': 'web_desktop', 'hMarketingCampaign': False}).encode(),
                headers={'Content-Type': 'application/json'},
            ),
        )
        items = traverse_obj(data, ('catalogItems', ...)) or []
        entries = []
        for item in items:
            stream_id = traverse_obj(item, 'encryptedStreamId')
            if not stream_id:
                continue
            broadcaster = traverse_obj(item, ('broadcaster', 'name')) or stream_id
            entries.append(
                self.url_result(
                    f'https://www.tango.me/stream/{stream_id}', TangoIE, stream_id, f'{broadcaster} - Tango live',
                ),
            )
        if not entries:
            raise ExtractorError('No live streams on the tango.me feed', expected=True)
        return self.playlist_result(entries, 'live', 'Tango live feed')


class TangoIE(TangoBase):
    IE_NAME = 'tango'
    # Route names are matched case-insensitively (the site folds them);
    # aliases keep their case.  ``/v2/<hash>/`` on the site host is the SPA,
    # not the CDN and not an alias.
    _VALID_URL = (
        r'https?://(?:www\.|m\.)?tango\.me/'
        r'(?!v2/[0-9a-fA-F]{32}/)'
        r'(?:(?P<kind>(?i:stream|live|profile))/)?'
        r'(?!(?i:live|stream|profile|search|explore|login|signup|gifts|store|settings|wallet)'
        r'(?:[/?#]|$))'
        r'(?P<id>[^/?#&]+)'
    )
    # The ids and alias are fake: a pinned stream ends and the test rots, and a
    # pinned account is somebody's profile.  Only the URL routing is tested.
    _TESTS = [
        {
            'url': 'https://tango.me/stream/noscript.html',
            'info_dict': {'id': 'noscript.html'},
            'expected_exception': 'ExtractorError',
        },
        {
            'url': 'https://www.tango.me/stream/AAAABBBBCCCCDDDDEEEEFF',
            'only_matching': True,
        },
        {
            'url': 'https://www.tango.me/tango_tester',
            'only_matching': True,
        },
        {
            'url': 'https://www.tango.me/@tango_tester',
            'only_matching': True,
        },
        {
            'url': 'https://www.tango.me/profile/tango_tester',
            'only_matching': True,
        },
        {
            'url': 'https://www.tango.me/live/AAAABBBBCCCCDDDDEEEEFF',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        match = self._match_valid_url(url)
        if match.group('id').lower() in _NON_CONTENT_ROUTES:
            raise ExtractorError(
                f"tango.me served its no-JavaScript page ({match.group('id')}), "
                "which carries no stream id. Pass the original "
                "https://www.tango.me/stream/<id> URL or a profile URL",
                expected=True,
            )
        return self._extract_stream(
            url, match.group('id'), is_profile=(match.group('kind') or '').lower() not in ('stream', 'live'),
        )


class TangoCdnIE(TangoBase):
    """A CDN playlist URL copied out of the browser's network tab.

    yt-dlp issue #11433 documents this as the workaround for a site with no
    extractor: copy a ``master.m3u8?token=...`` request and hand it over.  The
    copied link dies with the browser's ten-second token, so it is served
    through the same relay as a resolved stream.

    Nothing in the copied URL names the broadcaster, and the token endpoint is
    not stream-scoped, so no lookup is made: a visitor check-in plus a fresh
    token authorises the copied path.  Measured 2026-11-21: master and
    rendition answer 200 with a fresh triplet and no prior ``watch``.
    """

    IE_NAME = 'tango:cdn'
    # The site hosts are excluded so only one extractor owns a URL.  Any
    # playlist name is accepted because the CDN does not validate it.
    _VALID_URL = (
        r'https?://(?!(?:www|m)\.)[a-z0-9-]+\.tango\.me/v2/'
        r'(?P<id>[0-9a-fA-F]{32})/[a-z0-9_]+\.m3u8(?:[?#]|$)'
    )
    _TESTS = [
        {
            # A real CDN URL cannot be pinned: its token dies in ten seconds and the
            # cinema-* host name changes per session.  Only the routing is tested.
            'url': 'https://cinema-in41.tango.me/v2/0123456789abcdef0123456789abcdef'
            '/live.m3u8?token=expired&username=expired',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        self._ensure_session(video_id)
        refresher = TangoTokenRefresher(self, video_id)
        refresher.ensure(force=True)
        if not refresher.token:
            raise ExtractorError('tango.me did not issue a CDN token; retry the download', expected=True)
        parts = urllib.parse.urlsplit(url)
        # The query is dropped: its token expires in about ten seconds and the
        # CDN authorises on the cookie triplet instead.  The path is kept as
        # copied, because the file name is what selects the variant list (the
        # master hash) or one rendition (a rendition hash).
        playlist_url = f'{parts.scheme}://{parts.netloc}{parts.path}'
        formats, subtitles = self._relayed_formats(
            refresher,
            playlist_url,
            video_id,
            True,
            'The CDN playlist could not be read; the stream has probably '
            'ended. A followers-only stream needs --cookies-from-browser chrome',
        )
        return {
            'id': video_id,
            'title': f'Tango live {video_id}',
            'formats': formats,
            'subtitles': subtitles,
            'is_live': True,
            'live_status': 'is_live',
            'age_limit': 18,
            # Query-free, so the copied token and username never reach tags.
            'webpage_url': playlist_url,
        }
