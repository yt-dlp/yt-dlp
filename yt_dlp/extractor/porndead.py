import re
import urllib.parse

from yt_dlp.utils._utils import int_or_none

from .common import InfoExtractor
from ..utils import ExtractorError


class PornDeadIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?porndead\.org/video/(?P<id>[0-9a-f]+)'
    _TESTS = [
        {
            'url': 'https://porndead.org/video/65fefcb523810',
            'info_dict': {
                'id': '65fefcb523810',
                'ext': 'mp4',
                'title': 'Hysterical Literature - Isabel Love',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # find video title ideally
        title = (
            self._html_search_regex(
                r'<div[^>]+class=["\']title_video["\'][^>]*>([^<]+)</div>',
                webpage,
                'title',
                default=None,
            )
            or self._og_search_title(webpage, default=None)
            or f'Video {video_id}'
        )

        # extract variable player_url from <script> player_url = "..." </script>
        player_rel = self._search_regex(
            r'(?is)player[_-]?url\s*=\s*(["\'])(?P<u>[^"\']+)\1',
            webpage,
            'player url',
            default=None,
            group='u',
        )

        if not player_rel:
            raise ExtractorError('Could not find player_url on page', expected=True)

        # resolve relative URL and append type=1 like the JS on the page does
        player_url = urllib.parse.urljoin(url, player_rel)
        player_endpoint = player_url + ('&type=1' if '?' in player_url else '?type=1')

        ajax_headers = {
            'Referer': url,
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (compatible)',
            'Accept': '*/*',
        }

        # get the options html
        options_html = None
        try:
            options_html = self._download_webpage(
                player_endpoint,
                video_id,
                headers=ajax_headers,
                data=b'',  # empty body to force POST where supported
            )
        except Exception as e:
            print(e)
            raise ExtractorError(
                f'Failed to download options from {player_endpoint}: {e}',
                expected=True,
            )

        formats = []

        # write options_html to a file for debugging
        with open(f'/tmp/porndead_{video_id}_options.mp4', 'w') as f:
            f.write(options_html or '')
            print(f'Wrote options HTML to /tmp/porndead_{video_id}_options.mp4')

        # try to find direct mp4 links in the returned HTML (anchors with class href_mp4)
        links = re.findall(
            r'<a[^>]+class=["\']href_mp4["\'][^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>',
            options_html or '',
            flags=re.IGNORECASE,
        )

        print(links)

        for href, label in links:
            full_url = urllib.parse.urljoin(url, href)

            # try to infer height from label (e.g., '240p', '720p') or from filename (720P_)
            m_h = re.search(r'(\d{3,4})[pP]', label) or re.search(r'(\d{3,4})P_', href)
            height = int_or_none(m_h.group(1))

            # try to infer bitrate (e.g., '4000K' or rate=500k in query)
            m_k = re.search(r'([0-9]+)[kK]', href) or re.search(r'rate=([0-9]+)k', href)
            tbr = int_or_none(m_k.group(1))

            fmt_id = f'{height}p' if height else label.strip()

            fmt = {
                'format_id': fmt_id,
                'url': full_url,
                'ext': 'mp4',
            }
            if height:
                fmt['height'] = height
            if tbr:
                fmt['tbr'] = tbr

            fmt['http_headers'] = {'Referer': url, 'User-Agent': 'Mozilla/5.0'}

            formats.append(fmt)

        # we can also get the m3u8 by GET on the player_url without &type=1
        formats.extend(
            self._extract_m3u8_formats(
                player_url,
                video_id,
                'mp4',
                entry_protocol='m3u8_native',
                m3u8_id='hls',
                fatal=False,
            ),
        )

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'age_limit': 18,
        }
