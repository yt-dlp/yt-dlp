import re

from .common import InfoExtractor
from ..utils import (
    decode_packed_codes,
    int_or_none,
    js_to_json,
    url_or_none,
    urlencode_postdata,
)


class DarkiboxIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?darkibox\.com/(?:embed-|d/|e-|e/)?(?P<id>[a-zA-Z0-9]{12})(?:[/.].*)?'
    _EMBED_REGEX = [r'<iframe[^>]+\bsrc=(?P<q1>[\'"])(?P<url>(?:https?:)?//(?:www\.)?darkibox\.com/embed-[a-zA-Z0-9]{12}\.html)(?P=q1)']
    _TESTS = [{
        'url': 'https://darkibox.com/rg6ipk9esayj',
        'only_matching': True,
    }, {
        'url': 'https://darkibox.com/d/rg6ipk9esayj',
        'only_matching': True,
    }, {
        'url': 'https://darkibox.com/embed-rg6ipk9esayj.html',
        'only_matching': True,
    }, {
        'url': 'https://darkibox.com/e-rg6ipk9esayj',
        'only_matching': True,
    }, {
        'url': 'https://darkibox.com/e/rg6ipk9esayj',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # Step 1: POST to embed endpoint to get the player page with video sources
        embed_url = f'https://darkibox.com/embed-{video_id}.html'
        embed_page = self._download_webpage(
            embed_url, video_id, note='Downloading embed page')

        # The embed page (emb.html) contains a form that POSTs to /dl.
        # We submit that form to get the actual player page.
        player_page = self._download_webpage(
            'https://darkibox.com/dl', video_id,
            note='Downloading player page',
            data=urlencode_postdata({
                'op': 'embed',
                'file_code': video_id,
                'auto': '1',
                'referer': '',
            }),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': embed_url,
                'Origin': 'https://darkibox.com',
            })

        # Step 2: The player JS may be packed with Dean Edwards packer.
        # Try to unpack any packed JS in the page.
        packed_code = self._search_regex(
            r"(eval\(function\(p,a,c,k,e,d\)\{.*?\}\(.*?\)\))",
            player_page, 'packed code', default=None)
        if packed_code:
            player_page += '\n' + decode_packed_codes(packed_code)

        # Step 3: Extract video sources.
        # PlayerJS uses: new Playerjs({..., file:"URL", ...})
        # The file value can be:
        #   - A single HLS URL (master.m3u8)
        #   - A comma-separated list of [label]URL pairs for multiple qualities
        #   - A single direct MP4 URL

        formats = []
        subtitles = {}

        # Try to find the Playerjs file parameter
        file_url = self._search_regex(
            r'''(?x)
                (?:file|src)\s*[:=]\s*
                ["\']([^"\']+)["\']
            ''',
            player_page, 'video url', default=None)

        if not file_url:
            # Try alternative patterns used by other players (JW8, VideoJS, etc.)
            file_url = self._search_regex(
                r'''(?x)
                    (?:sources\s*:\s*\[\s*\{\s*(?:file|src)\s*:\s*["\']([^"\']+)["\']\s*)
                ''',
                player_page, 'video url', default=None)

        if not file_url:
            # Try to find any m3u8 or mp4 URL
            file_url = self._search_regex(
                r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4|urlset)[^\s"\'<>]*)',
                player_page, 'video url')

        if file_url:
            # Handle PlayerJS multi-quality format: [label1]url1,[label2]url2
            if re.match(r'\[.+?\]https?://', file_url):
                for m in re.finditer(r'\[(?P<label>[^\]]+)\](?P<url>https?://[^,\s"\']+)', file_url):
                    video_url = m.group('url')
                    label = m.group('label')
                    height = int_or_none(re.search(r'(\d+)p', label), group=1) if re.search(r'(\d+)p', label) else None
                    if '.m3u8' in video_url or '.urlset' in video_url:
                        fmts, subs = self._extract_m3u8_formats_and_subtitles(
                            video_url, video_id, ext='mp4', fatal=False,
                            m3u8_id=f'hls-{label}')
                        formats.extend(fmts)
                        self._merge_subtitles(subs, target=subtitles)
                    else:
                        formats.append({
                            'url': video_url,
                            'format_id': label,
                            'height': height,
                        })
            elif '.m3u8' in file_url or '.urlset' in file_url:
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    file_url, video_id, ext='mp4', fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.append({
                    'url': file_url,
                })

        # Step 4: Extract metadata
        title = self._search_regex(
            r'<Title>([^<]+)</Title>',
            player_page, 'title', default=None, flags=re.IGNORECASE)
        if not title:
            title = self._search_regex(
                r'title\s*:\s*["\']([^"\']+)["\']',
                player_page, 'title', default=None)
        if not title:
            # Try the regular page
            title = self._search_regex(
                r'<h1[^>]*>([^<]+)</h1>',
                player_page, 'title', default=video_id)

        # Clean up title
        if title:
            title = re.sub(r'\s*-\s*Darkibox\.com\s*$', '', title, flags=re.IGNORECASE).strip()
            title = re.sub(r'^Watch\s+', '', title, flags=re.IGNORECASE).strip()

        thumbnail = self._search_regex(
            r'poster\s*:\s*["\']([^"\']+)["\']',
            player_page, 'thumbnail', default=None)
        if not thumbnail:
            thumbnail = self._og_search_thumbnail(player_page, default=None)

        duration = int_or_none(self._search_regex(
            r'duration\s*:\s*["\']?(\d+)["\']?',
            player_page, 'duration', default=None))

        return {
            'id': video_id,
            'title': title or video_id,
            'thumbnail': thumbnail,
            'duration': duration,
            'formats': formats,
            'subtitles': subtitles,
        }
